// softsolver.js - vertex-based soft/deformable structure solver (XPBD, small-steps variant).
// No dependencies. Deterministic: fixed constraint order, fixed iteration order, seeded PRNG only.
// Units: SI (m, kg, s, Pa, N). Particles are point masses with a collision radius.
//
// Constraint families
//   distance : bar/spring between 2 particles, compliance = L0/(E*A); optional plastic yield + brittle fracture (strain based)
//   tetra    : volume-preserving constraint (bulk compliance), used for chunky blocks
//   weld     : 3-axis point joint (mortar / glue / nails); breaks by force
// Contacts: heightfield callback, spheres, oriented boxes (all can report reaction impulses), particle-particle between
//           different connected components (rubble vs rubble, chunk vs structure).

export function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// damping in [0,1] maps to Rayleigh stiffness-proportional beta (s) and to a mass-proportional drag (1/s)
const BETA_PER_DAMP = 0.02, DRAG_PER_DAMP = 1.5;

export function makeMaterial(d) {
  const youngs = d.youngs, poisson = d.poisson ?? 0.3;
  const yieldS = d.yield == null ? Infinity : d.yield;
  const fracS = d.fracture == null ? Infinity : d.fracture;
  return Object.freeze({
    name: d.name || 'mat', density: d.density, youngs, poisson,
    yield: yieldS, fracture: fracS, damping: d.damping ?? 0.1,
    scatter: d.scatter ?? 0.05,
    snap: !!d.snap,                                // brittle: when one bar of a cut section fails the whole section snaps                    // +/- relative scatter of strength per constraint (seeded)
    shear: youngs / (2 * (1 + poisson)),
    bulk: youngs / (3 * (1 - 2 * poisson)),
    yieldStrain: yieldS / youngs, fracStrain: fracS / youngs,
    beta: (d.damping ?? 0.1) * BETA_PER_DAMP, drag: (d.damping ?? 0.1) * DRAG_PER_DAMP,
  });
}

// Reference material descriptors (rough, ranged for game use; bending/tension strengths in Pa)
export const MATERIALS = {
  wood:   { name: 'wood',   density: 600,  youngs: 1.0e10, yield: 4.0e7, fracture: 6.0e7, damping: 0.2, snap: true },
  steel:  { name: 'steel',  density: 7800, youngs: 2.0e11, yield: 2.5e8, fracture: 4.0e8, damping: 0.1 },
  rope:   { name: 'rope',   density: 900,  youngs: 5.0e8,  yield: 1.0e12, fracture: 8.0e7, damping: 0.4 },
  cloth:  { name: 'cloth',  density: 400,  youngs: 5.0e7,  yield: 1.0e12, fracture: 5.0e7, damping: 0.5 },
  stone:  { name: 'stone',  density: 2500, youngs: 3.0e10, yield: 1.0e13, fracture: 5.0e6, damping: 0.2, snap: true },
  mortar: { name: 'mortar', density: 1900, youngs: 1.0e9,  yield: 1.0e13, fracture: 3.0e5, damping: 0.2 },
};

const SQ = Math.sqrt;

export class SoftWorld {
  constructor(o = {}) {
    this.gravity = o.gravity ? o.gravity.slice() : [0, -9.81, 0];
    this.substeps = o.substeps ?? 8;               // fixed substeps per frame ...
    this.substepHz = o.substepHz ?? 0;              // ... or (if > 0) a fixed substep RATE, so h is the same at 30/60/120 Hz
    this.iterations = o.iterations ?? 1;
    this.seed = o.seed ?? 1;
    this.rng = mulberry32(this.seed);
    this.friction = o.friction ?? 0.6;
    this.crushRatio = o.crushRatio ?? 4;            // compression breaks at crushRatio x the tension strain
    this.pairs = o.pairs ?? true;                   // particle-particle contacts between different connected pieces (once per frame)
    this.checkEvery = o.checkEvery ?? 2;            // plasticity/fracture checks every N substeps (and always on the last)
    this.groundMargin = 0.0;
    this.heightfield = null;                        // (x,z) => height
    this.heightfieldMax = Infinity;                 // optional upper bound of the heightfield: particles above it skip the callback
    this.colliders = [];                            // {type:'sphere',c,r,v} | {type:'box',c,h,q,v}; impulse in .j/.tq
    this.wind = null;                               // [wx,wy,wz] or (x,y,z)=>[wx,wy,wz]
    this.airDensity = 1.2;
    this.onBreak = null;                            // ({kind,a,b,index}) => void
    this.time = 0; this.stepCount = 0;
    this.n = 0; this.cap = 0;
    this._allocP(o.capacity || 512);
    this.nd = 0; this.capD = 0; this._allocD(o.capacity ? o.capacity * 3 : 1536);
    this.nt = 0; this.capT = 0; this._allocT(128);
    this.nw = 0; this.capW = 0; this._allocW(128);
    this.nTri = 0; this.tri = new Int32Array(0); this.triCd = new Float64Array(0);
    this.nextGroup = 1; this.nextBay = 1; this.nBroken = 0;
    this._compDirty = true; this.comp = new Int32Array(0); this.nComp = 0; this.compV = new Float64Array(0); this.compM = new Float64Array(0); this.compPin = new Uint8Array(0); this.supPrev = new Uint8Array(0); this.supNow = new Uint8Array(0);
    this._hHead = new Int32Array(8192); this._hNext = new Int32Array(0);
    this._sweep = 0; this._adjDirty = true; this.stepMax = o.stepMax ?? 0.25; this.omega = o.omega ?? 0.75; this.maxSpeed = o.maxSpeed ?? 80; this.adjStart = null; this.maxRadius = 0.01;
    this.stats = { contacts: 0, pairContacts: 0 };
  }

  // ---------- storage ----------
  _allocP(c) {
    const g = (old, k, T) => { const a = new T(c * k); if (old) a.set(old.subarray(0, Math.min(old.length, a.length))); return a; };
    this.pos = g(this.pos, 3, Float64Array); this.prev = g(this.prev, 3, Float64Array); this.vel = g(this.vel, 3, Float64Array);
    this.ext = g(this.ext, 3, Float64Array); this.aeroF = g(this.aeroF, 3, Float64Array);
    this.mass = g(this.mass, 1, Float64Array); this.invM = g(this.invM, 1, Float64Array); this.rad = g(this.rad, 1, Float64Array);
    this.drag = g(this.drag, 1, Float64Array); this.xt = g(this.xt, 3, Float64Array); this.group = g(this.group, 1, Int32Array); this.pinned = g(this.pinned, 1, Uint8Array);
    this.cap = c;
  }
  _allocD(c) {
    const g = (old, T) => { const a = new T(c); if (old) a.set(old.subarray(0, Math.min(old.length, a.length))); return a; };
    this.da = g(this.da, Int32Array); this.db = g(this.db, Int32Array); this.dRest = g(this.dRest, Float64Array);
    this.dAlpha = g(this.dAlpha, Float64Array); this.dBeta = g(this.dBeta, Float64Array); this.dYield = g(this.dYield, Float64Array);
    this.dFrac = g(this.dFrac, Float64Array); this.dAct = g(this.dAct, Uint8Array); this.dLam = g(this.dLam, Float64Array);
    this.dK = g(this.dK, Float64Array); this.dTag = g(this.dTag, Int32Array); this.dBay = g(this.dBay, Int32Array); this.dSnap = g(this.dSnap, Uint8Array);
    this.capD = c;
  }
  _allocT(c) {
    const g = (old, T, k = 1) => { const a = new T(c * k); if (old) a.set(old.subarray(0, Math.min(old.length, a.length))); return a; };
    this.tv = g(this.tv, Int32Array, 4); this.tV0 = g(this.tV0, Float64Array); this.tAlpha = g(this.tAlpha, Float64Array);
    this.tAct = g(this.tAct, Uint8Array); this.tLam = g(this.tLam, Float64Array);
    this.capT = c;
  }
  _allocW(c) {
    const g = (old, T, k = 1) => { const a = new T(c * k); if (old) a.set(old.subarray(0, Math.min(old.length, a.length))); return a; };
    this.wa = g(this.wa, Int32Array); this.wb = g(this.wb, Int32Array); this.wR = g(this.wR, Float64Array, 3);
    this.wAlpha = g(this.wAlpha, Float64Array); this.wBeta = g(this.wBeta, Float64Array); this.wMax = g(this.wMax, Float64Array);
    this.wAct = g(this.wAct, Uint8Array); this.wLam = g(this.wLam, Float64Array, 3); this.wK = g(this.wK, Float64Array);
    this.capW = c;
  }

  // ---------- construction ----------
  addParticle(x, y, z, mass = 0, radius = 0.03, group = 0, drag = 0) {
    if (this.n >= this.cap) this._allocP(this.cap * 2);
    const i = this.n++, k = i * 3;
    this.pos[k] = x; this.pos[k + 1] = y; this.pos[k + 2] = z;
    this.prev[k] = x; this.prev[k + 1] = y; this.prev[k + 2] = z;
    this.mass[i] = mass; this.invM[i] = mass > 0 ? 1 / mass : 0; this.rad[i] = radius; this.group[i] = group; this.drag[i] = drag;
    if (radius > this.maxRadius) this.maxRadius = radius;
    this._compDirty = true; this._adjDirty = true;
    return i;
  }
  addMass(i, m) { this.mass[i] += m; this.invM[i] = this.pinned[i] ? 0 : 1 / this.mass[i]; }
  pin(i, on = true) { this.pinned[i] = on ? 1 : 0; this.invM[i] = on || this.mass[i] <= 0 ? 0 : 1 / this.mass[i]; }
  newGroup() { return this.nextGroup++; }
  newBay() { return this.nextBay++; }

  addDistance(a, b, mat, area, o = {}) {
    if (this.nd >= this.capD) this._allocD(this.capD * 2);
    const c = this.nd++, p = this.pos;
    const dx = p[a * 3] - p[b * 3], dy = p[a * 3 + 1] - p[b * 3 + 1], dz = p[a * 3 + 2] - p[b * 3 + 2];
    const L = SQ(dx * dx + dy * dy + dz * dz), rest = o.rest ?? L;
    const k = mat.youngs * area / Math.max(rest, 1e-9);
    const sc = 1 + mat.scatter * (2 * this.rng() - 1);
    this.da[c] = a; this.db[c] = b; this.dRest[c] = rest; this.dK[c] = k; this.dAlpha[c] = 1 / k;
    this.dBeta[c] = mat.beta; this.dYield[c] = mat.yieldStrain * sc; this.dFrac[c] = (o.fracStrain ?? mat.fracStrain) * sc;
    this.dAct[c] = 1; this.dLam[c] = 0; this.dTag[c] = o.tag ?? 0; this.dBay[c] = o.bay ?? 0; this.dSnap[c] = mat.snap && o.bay ? 1 : 0;
    this._compDirty = true; this._adjDirty = true;
    return c;
  }
  addTetra(a, b, c, d, mat, o = {}) {
    if (this.nt >= this.capT) this._allocT(this.capT * 2);
    const t = this.nt++, p = this.pos;
    const V = this._vol(a, b, c, d);
    this.tv[t * 4] = a; this.tv[t * 4 + 1] = b; this.tv[t * 4 + 2] = c; this.tv[t * 4 + 3] = d;
    this.tV0[t] = V; this.tAlpha[t] = Math.abs(V) / (o.bulk ?? mat.bulk); this.tAct[t] = 1; this.tLam[t] = 0;
    this._compDirty = true; this._adjDirty = true;
    return t;
  }
  _vol(a, b, c, d) {
    const p = this.pos, A = a * 3, B = b * 3, C = c * 3, D = d * 3;
    const bx = p[B] - p[A], by = p[B + 1] - p[A + 1], bz = p[B + 2] - p[A + 2];
    const cx = p[C] - p[A], cy = p[C + 1] - p[A + 1], cz = p[C + 2] - p[A + 2];
    const dx = p[D] - p[A], dy = p[D + 1] - p[A + 1], dz = p[D + 2] - p[A + 2];
    return (bx * (cy * dz - cz * dy) + by * (cz * dx - cx * dz) + bz * (cx * dy - cy * dx)) / 6;
  }
  // strength: tension capacity as stress (Pa), area: bond area (m2), gap: joint thickness (m) for stiffness
  addWeld(a, b, mat, area, gap, o = {}) {
    if (this.nw >= this.capW) this._allocW(this.capW * 2);
    const w = this.nw++, p = this.pos;
    this.wa[w] = a; this.wb[w] = b;
    this.wR[w * 3] = p[a * 3] - p[b * 3]; this.wR[w * 3 + 1] = p[a * 3 + 1] - p[b * 3 + 1]; this.wR[w * 3 + 2] = p[a * 3 + 2] - p[b * 3 + 2];
    const k = mat.youngs * area / gap, sc = 1 + mat.scatter * (2 * this.rng() - 1);
    this.wK[w] = k; this.wAlpha[w] = 1 / k; this.wBeta[w] = mat.beta;
    this.wMax[w] = (o.maxForce ?? mat.fracture * area) * sc; this.wAct[w] = 1;
    this.wLam[w * 3] = 0; this.wLam[w * 3 + 1] = 0; this.wLam[w * 3 + 2] = 0;
    this._compDirty = true; this._adjDirty = true;
    return w;
  }
  addAeroTri(a, b, c, cd = 1.2) {
    const n = this.nTri++;
    if (n * 3 >= this.tri.length) { const t = new Int32Array(Math.max(96, this.tri.length * 2)); t.set(this.tri); this.tri = t; const d = new Float64Array(t.length / 3); d.set(this.triCd); this.triCd = d; }
    this.tri[n * 3] = a; this.tri[n * 3 + 1] = b; this.tri[n * 3 + 2] = c; this.triCd[n] = cd;
  }
  setForce(i, fx, fy, fz) { const k = i * 3; this.ext[k] = fx; this.ext[k + 1] = fy; this.ext[k + 2] = fz; }
  addCollider(c) { c.j = [0, 0, 0]; c.tq = [0, 0, 0]; c.v = c.v || [0, 0, 0]; this.colliders.push(c); return c; }
  clearImpulses() { for (const c of this.colliders) { c.j[0] = c.j[1] = c.j[2] = 0; c.tq[0] = c.tq[1] = c.tq[2] = 0; } }

  // ---------- stepping ----------
  // One frame = `substeps` implicit-Euler steps. Each is solved by `iterations` Gauss-Seidel sweeps of Vertex Block
  // Descent: every free particle does a local 3x3 Newton step on (inertia + all incident constraint energies).
  step(dt) {
    const S = this.substepHz ? Math.max(1, Math.round(dt * this.substepHz)) : this.substeps, h = dt / S;
    if (this._compDirty) this._buildComponents();
    if (this._adjDirty) this._buildAdj();
    this._aero();
    for (let s = 0; s < S; s++) {
      this._predict(h);
      for (let it = 0; it < this.iterations; it++) {
        this._vbd(h, (this._sweep++ & 1) === 1);
        this._collide(h);
      }
      if (this.pairs && s === S - 1) this._pairs(h);       // rubble/chunk contacts: once per frame
      this._finish(h, s === S - 1 || (s + 1) % this.checkEvery === 0);
    }
    this.time += dt; this.stepCount++;
    if (this._compDirty) this._buildComponents();
  }

  _aero() {
    const nT = this.nTri; if (!nT || !this.wind) return;
    const F = this.aeroF, p = this.pos, v = this.vel, tri = this.tri; F.fill(0, 0, this.n * 3);
    const w = this.wind, rho = this.airDensity;
    for (let t = 0; t < nT; t++) {
      const a = tri[t * 3] * 3, b = tri[t * 3 + 1] * 3, c = tri[t * 3 + 2] * 3;
      const e1x = p[b] - p[a], e1y = p[b + 1] - p[a + 1], e1z = p[b + 2] - p[a + 2];
      const e2x = p[c] - p[a], e2y = p[c + 1] - p[a + 1], e2z = p[c + 2] - p[a + 2];
      let nx = e1y * e2z - e1z * e2y, ny = e1z * e2x - e1x * e2z, nz = e1x * e2y - e1y * e2x;
      const ar2 = SQ(nx * nx + ny * ny + nz * nz); if (ar2 < 1e-12) continue;
      nx /= ar2; ny /= ar2; nz /= ar2; const area = 0.5 * ar2;
      let W = w; if (typeof w === 'function') W = w((p[a] + p[b] + p[c]) / 3, (p[a + 1] + p[b + 1] + p[c + 1]) / 3, (p[a + 2] + p[b + 2] + p[c + 2]) / 3);
      const rx = W[0] - (v[a] + v[b] + v[c]) / 3, ry = W[1] - (v[a + 1] + v[b + 1] + v[c + 1]) / 3, rz = W[2] - (v[a + 2] + v[b + 2] + v[c + 2]) / 3;
      const vn = rx * nx + ry * ny + rz * nz;
      const f = 0.5 * rho * this.triCd[t] * area * Math.abs(vn) * vn / 3;
      for (const q of [a, b, c]) { F[q] += f * nx; F[q + 1] += f * ny; F[q + 2] += f * nz; }
    }
  }

  // inertial target xt (it is what the energy is anchored to) and the sweep's initial guess.
  // Initial guess: previous state + velocity (so a resting structure is a fixed point of the sweep: no sag bias).
  // Exception: a connected piece with NO support (nothing pinned, no contact last substep) is in free flight; stiff
  // Gauss-Seidel converges slowly on rigid translation, so it starts from the full inertial prediction instead.
  _predict(h) {
    const n = this.n, p = this.pos, pr = this.prev, v = this.vel, im = this.invM, ex = this.ext, ae = this.aeroF, dr = this.drag, xt = this.xt, comp = this.comp, sup = this.supPrev, cv = this.compV;
    const g = this.gravity, gx = g[0], gy = g[1], gz = g[2], useA = this.nTri > 0 && this.wind, h2 = h * h;
    for (let i = 0; i < n; i++) {
      const k = i * 3; pr[k] = p[k]; pr[k + 1] = p[k + 1]; pr[k + 2] = p[k + 2];
      const w = im[i]; if (w === 0) { v[k] = v[k + 1] = v[k + 2] = 0; xt[k] = p[k]; xt[k + 1] = p[k + 1]; xt[k + 2] = p[k + 2]; continue; }
      const dm = 1 / (1 + dr[i] * h), cc = comp[i];
      // mass-proportional damping acts on the velocity relative to the piece's own centre-of-mass motion when the piece
      // is in free flight (so a falling chunk is not slowed like in air) and relative to rest when it is supported
      let rx = 0, ry = 0, rz = 0; if (!sup[cc]) { rx = cv[cc * 3]; ry = cv[cc * 3 + 1]; rz = cv[cc * 3 + 2]; }
      const vx = rx + (v[k] - rx) * dm, vy = ry + (v[k + 1] - ry) * dm, vz = rz + (v[k + 2] - rz) * dm;
      let ax = gx + ex[k] * w, ay = gy + ex[k + 1] * w, az = gz + ex[k + 2] * w;
      if (useA) { ax += ae[k] * w; ay += ae[k + 1] * w; az += ae[k + 2] * w; }
      xt[k] = p[k] + h * vx + h2 * ax; xt[k + 1] = p[k + 1] + h * vy + h2 * ay; xt[k + 2] = p[k + 2] + h * vz + h2 * az;
      if (sup[comp[i]]) { p[k] += h * vx; p[k + 1] += h * vy; p[k + 2] += h * vz; } else { p[k] = xt[k]; p[k + 1] = xt[k + 1]; p[k + 2] = xt[k + 2]; }
    }
  }

  // one Gauss-Seidel sweep over all free particles
  _vbd(h, rev) {
    const n = this.n, p = this.pos, pr = this.prev, im = this.invM, ms = this.mass, xt = this.xt;
    const dS = this.adjDS, dC = this.adjDC, dO = this.adjDO, wS = this.adjWS, wC = this.adjWC, wO = this.adjWO, tS = this.adjTS, tC = this.adjTC;
    const DR = this.dRest, DK = this.dK, DBe = this.dBeta, DAc = this.dAct;
    const WA = this.wa, WK = this.wK, WBe = this.wBeta, WR = this.wR, WAc = this.wAct;
    const TV = this.tv, TAl = this.tAlpha, TV0 = this.tV0, TAc = this.tAct;
    const h2 = h * h, ih = 1 / h, STEPMAX = this.stepMax, om = this.omega;
    for (let q = 0; q < n; q++) {
      const i = rev ? n - 1 - q : q; if (im[i] === 0) continue;
      const k = i * 3, xi = p[k], yi = p[k + 1], zi = p[k + 2], mh = ms[i] / h2;
      let fx = -mh * (xi - xt[k]), fy = -mh * (yi - xt[k + 1]), fz = -mh * (zi - xt[k + 2]);
      let hxx = mh, hyy = mh, hzz = mh, hxy = 0, hxz = 0, hyz = 0;
      const vix = (xi - pr[k]) * ih, viy = (yi - pr[k + 1]) * ih, viz = (zi - pr[k + 2]) * ih;
      for (let e = dS[i], e1 = dS[i + 1]; e < e1; e++) {         // distance bars
        const c = dC[e]; if (DAc[c] === 0) continue;
        const kj = dO[e] * 3;
        const dx = xi - p[kj], dy = yi - p[kj + 1], dz = zi - p[kj + 2];
        const len = SQ(dx * dx + dy * dy + dz * dz); if (len < 1e-12) continue;
        const il = 1 / len, nx = dx * il, ny = dy * il, nz = dz * il, kk = DK[c], r0 = DR[c], bt = DBe[c];
        let fs = -kk * (len - r0), ka = kk;
        if (bt > 0) {                                              // stiffness-proportional (Rayleigh) damping along the bar
          const kd = kk * bt, vr = (vix - (p[kj] - pr[kj]) * ih) * nx + (viy - (p[kj + 1] - pr[kj + 1]) * ih) * ny + (viz - (p[kj + 2] - pr[kj + 2]) * ih) * nz;
          fs -= kd * vr; ka += kd * ih;
        }
        fx += fs * nx; fy += fs * ny; fz += fs * nz;
        const tc = len > r0 ? kk * (1 - r0 * il) : 0, dd = ka - tc;   // tc: geometric stiffness (PSD part only)
        hxx += dd * nx * nx + tc; hyy += dd * ny * ny + tc; hzz += dd * nz * nz + tc;
        hxy += dd * nx * ny; hxz += dd * nx * nz; hyz += dd * ny * nz;
      }
      for (let e = wS[i], e1 = wS[i + 1]; e < e1; e++) {          // welds (3-axis point joints)
        const c = wC[e]; if (WAc[c] === 0) continue;
        const sgn = WA[c] === i ? 1 : -1, kj = wO[e] * 3, kk = WK[c], kd = kk * WBe[c];
        const cx = xi - p[kj] - sgn * WR[c * 3], cy = yi - p[kj + 1] - sgn * WR[c * 3 + 1], cz = zi - p[kj + 2] - sgn * WR[c * 3 + 2];
        const vx = vix - (p[kj] - pr[kj]) * ih, vy = viy - (p[kj + 1] - pr[kj + 1]) * ih, vz = viz - (p[kj + 2] - pr[kj + 2]) * ih;
        fx -= kk * cx + kd * vx; fy -= kk * cy + kd * vy; fz -= kk * cz + kd * vz;
        const ka = kk + kd * ih; hxx += ka; hyy += ka; hzz += ka;
      }
      for (let e = tS[i], e1 = tS[i + 1]; e < e1; e++) {          // tetra volume constraints
        const c = tC[e]; if (TAc[c] === 0) continue;
        const o0 = TV[c * 4], o1 = TV[c * 4 + 1], o2 = TV[c * 4 + 2], o3 = TV[c * 4 + 3];
        // (i,B,C,D) = even permutation of the stored order, so the signed volume is unchanged
        let B, C, D; if (o0 === i) { B = o1; C = o2; D = o3; } else if (o1 === i) { B = o0; C = o3; D = o2; } else if (o2 === i) { B = o3; C = o0; D = o1; } else { B = o2; C = o1; D = o0; }
        const kb = B * 3, kc = C * 3, kdd = D * 3;
        const bx = p[kb] - xi, by = p[kb + 1] - yi, bz = p[kb + 2] - zi, cx = p[kc] - xi, cy = p[kc + 1] - yi, cz = p[kc + 2] - zi, dx = p[kdd] - xi, dy = p[kdd + 1] - yi, dz = p[kdd + 2] - zi;
        const Vol = (bx * (cy * dz - cz * dy) + by * (cz * dx - cx * dz) + bz * (cx * dy - cy * dx)) / 6;
        const gx_ = -(((cy * dz - cz * dy) + (dy * bz - dz * by) + (by * cz - bz * cy)) / 6), gy_ = -(((cz * dx - cx * dz) + (dz * bx - dx * bz) + (bz * cx - bx * cz)) / 6), gz_ = -(((cx * dy - cy * dx) + (dx * by - dy * bx) + (bx * cy - by * cx)) / 6);
        const kv = 1 / TAl[c], Cv = Vol - TV0[c];
        fx -= kv * Cv * gx_; fy -= kv * Cv * gy_; fz -= kv * Cv * gz_;
        hxx += kv * gx_ * gx_; hyy += kv * gy_ * gy_; hzz += kv * gz_ * gz_; hxy += kv * gx_ * gy_; hxz += kv * gx_ * gz_; hyz += kv * gy_ * gz_;
      }
      // solve H dx = f (symmetric 3x3, cofactor inverse)
      const c00 = hyy * hzz - hyz * hyz, c01 = hxz * hyz - hxy * hzz, c02 = hxy * hyz - hxz * hyy;
      const det = hxx * c00 + hxy * c01 + hxz * c02; if (!(Math.abs(det) > 1e-300)) continue;
      const id = 1 / det, c11 = hxx * hzz - hxz * hxz, c12 = hxy * hxz - hxx * hyz, c22 = hxx * hyy - hxy * hxy;
      let dx = (c00 * fx + c01 * fy + c02 * fz) * id, dy = (c01 * fx + c11 * fy + c12 * fz) * id, dz = (c02 * fx + c12 * fy + c22 * fz) * id;
      const dl = dx * dx + dy * dy + dz * dz;
      if (dl > STEPMAX * STEPMAX) { const s = STEPMAX / SQ(dl); dx *= s; dy *= s; dz *= s; }
      p[k] = xi + om * dx; p[k + 1] = yi + om * dy; p[k + 2] = zi + om * dz;
    }
  }

  // CSR adjacency per constraint family (deterministic order = creation order)
  _buildAdj() {
    const n = this.n;
    const csr = (m, ends) => {
      const st = new Int32Array(n + 1);
      for (let c = 0; c < m; c++) for (const q of ends(c)) st[q + 1]++;
      for (let i = 0; i < n; i++) st[i + 1] += st[i];
      const fill = st.slice(0, n), tot = st[n], ci = new Int32Array(tot), ot = new Int32Array(tot);
      for (let c = 0; c < m; c++) { const e = ends(c); for (let a = 0; a < e.length; a++) { const q = fill[e[a]]++; ci[q] = c; ot[q] = e.length === 2 ? e[1 - a] : -1; } }
      return [st, ci, ot];
    };
    [this.adjDS, this.adjDC, this.adjDO] = csr(this.nd, (c) => [this.da[c], this.db[c]]);
    [this.adjWS, this.adjWC, this.adjWO] = csr(this.nw, (c) => [this.wa[c], this.wb[c]]);
    [this.adjTS, this.adjTC] = csr(this.nt, (t) => [this.tv[t * 4], this.tv[t * 4 + 1], this.tv[t * 4 + 2], this.tv[t * 4 + 3]]);
    this._adjDirty = false;
  }

  // ---------- contacts ----------
  _collide(h) {
    const n = this.n, p = this.pos, im = this.invM, rad = this.rad, hf = this.heightfield, hfMax = this.heightfieldMax, mu = this.friction;
    const cols = this.colliders, nc = cols.length; let contacts = 0;
    // axis-aligned reach of every collider (inflated by the largest particle radius) for a cheap inline cull
    if (nc) { if (!this._cull || this._cull.length < nc * 6) this._cull = new Float64Array(nc * 6); const R = this.maxRadius * 1.01, cu = this._cull;
      for (let c = 0; c < nc; c++) { const o = cols[c], e = o.type === 'sphere' ? o.r : Math.hypot(o.h[0], o.h[1], o.h[2]); for (let a = 0; a < 3; a++) { cu[c * 6 + a] = o.c[a] - e - R; cu[c * 6 + 3 + a] = o.c[a] + e + R; } } }
    const cu = this._cull;
    for (let i = 0; i < n; i++) {
      if (im[i] === 0) continue;
      const k = i * 3, r = rad[i], px = p[k], py = p[k + 1], pz = p[k + 2];
      if (hf && py - r < hfMax) {
        const x = px, z = pz, gh = hf(x, z), pen = gh + r - py;
        if (pen > 0) {
          contacts++; this.supNow[this.comp[i]] = 1;
          // normal from central differences (only on contact)
          const e = 0.05, gx = (hf(x + e, z) - hf(x - e, z)) / (2 * e), gz = (hf(x, z + e) - hf(x, z - e)) / (2 * e);
          const il = 1 / SQ(gx * gx + gz * gz + 1), nx = -gx * il, ny = il, nz = -gz * il;
          const d = pen * ny; // move along the normal so the particle ends at distance r above the surface
          p[k] += nx * d; p[k + 1] += ny * d; p[k + 2] += nz * d;
          this._friction(k, nx, ny, nz, d, mu, 0, 0, 0, h);
        }
      }
      for (let c = 0; c < nc; c++) {
        const o = c * 6; if (px < cu[o] || px > cu[o + 3] || py < cu[o + 1] || py > cu[o + 4] || pz < cu[o + 2] || pz > cu[o + 5]) continue;
        if (this._colliderContact(cols[c], i, k, r, mu, h)) { contacts++; this.supNow[this.comp[i]] = 1; }
      }
    }
    this.stats.contacts = contacts;
  }

  _friction(k, nx, ny, nz, pen, mu, cvx, cvy, cvz, h) {
    const p = this.pos, pr = this.prev;
    let tx = (p[k] - pr[k]) - cvx * h, ty = (p[k + 1] - pr[k + 1]) - cvy * h, tz = (p[k + 2] - pr[k + 2]) - cvz * h;
    const dn = tx * nx + ty * ny + tz * nz; tx -= dn * nx; ty -= dn * ny; tz -= dn * nz;
    const tm = SQ(tx * tx + ty * ty + tz * tz); if (tm < 1e-14) return;
    const f = mu * pen, s = tm < f ? 1 : f / tm;
    p[k] -= tx * s; p[k + 1] -= ty * s; p[k + 2] -= tz * s;
  }

  _colliderContact(c, i, k, r, mu, h) {
    const p = this.pos; let nx, ny, nz, pen;
    if (c.type === 'sphere') {
      const dx = p[k] - c.c[0], dy = p[k + 1] - c.c[1], dz = p[k + 2] - c.c[2], R = c.r + r;
      const d2 = dx * dx + dy * dy + dz * dz; if (d2 >= R * R) return false;
      const d = SQ(d2); if (d < 1e-9) { nx = 0; ny = 1; nz = 0; pen = R; } else { nx = dx / d; ny = dy / d; nz = dz / d; pen = R - d; }
    } else {
      // oriented box: local frame via conjugate quaternion
      const q = c.q || [0, 0, 0, 1], qx = q[0], qy = q[1], qz = q[2], qw = q[3];
      const rx = p[k] - c.c[0], ry = p[k + 1] - c.c[1], rz = p[k + 2] - c.c[2];
      const lx = this._rot(-qx, -qy, -qz, qw, rx, ry, rz, 0), ly = this._rot(-qx, -qy, -qz, qw, rx, ry, rz, 1), lz = this._rot(-qx, -qy, -qz, qw, rx, ry, rz, 2);
      const hx = c.h[0], hy = c.h[1], hz = c.h[2];
      const cx = Math.max(-hx, Math.min(hx, lx)), cy = Math.max(-hy, Math.min(hy, ly)), cz = Math.max(-hz, Math.min(hz, lz));
      let ox = lx - cx, oy = ly - cy, oz = lz - cz; const d2 = ox * ox + oy * oy + oz * oz;
      let lnx, lny, lnz;
      if (d2 > 1e-18) { if (d2 >= r * r) return false; const d = SQ(d2); lnx = ox / d; lny = oy / d; lnz = oz / d; pen = r - d; }
      else { // centre inside the box: exit through the nearest face
        const px = hx - Math.abs(lx), py = hy - Math.abs(ly), pz = hz - Math.abs(lz);
        lnx = lny = lnz = 0;
        if (px <= py && px <= pz) { lnx = lx >= 0 ? 1 : -1; pen = px + r; } else if (py <= pz) { lny = ly >= 0 ? 1 : -1; pen = py + r; } else { lnz = lz >= 0 ? 1 : -1; pen = pz + r; }
      }
      nx = this._rot(qx, qy, qz, qw, lnx, lny, lnz, 0); ny = this._rot(qx, qy, qz, qw, lnx, lny, lnz, 1); nz = this._rot(qx, qy, qz, qw, lnx, lny, lnz, 2);
    }
    p[k] += nx * pen; p[k + 1] += ny * pen; p[k + 2] += nz * pen;
    const v = c.v; if (v[0] !== 0 || v[1] !== 0 || v[2] !== 0 || mu > 0) this._friction(k, nx, ny, nz, pen, mu, v[0], v[1], v[2], h);
    // reaction impulse on the collider (momentum given to the particle by the contact), torque about collider centre
    const m = this.mass[i], s = m / h, jx = -nx * pen * s, jy = -ny * pen * s, jz = -nz * pen * s;
    c.j[0] += jx; c.j[1] += jy; c.j[2] += jz;
    const rx = p[k] - c.c[0], ry = p[k + 1] - c.c[1], rz = p[k + 2] - c.c[2];
    c.tq[0] += ry * jz - rz * jy; c.tq[1] += rz * jx - rx * jz; c.tq[2] += rx * jy - ry * jx;
    return true;
  }
  _rot(qx, qy, qz, qw, vx, vy, vz, axis) { // rotate v by quaternion q, return one component
    const tx = 2 * (qy * vz - qz * vy), ty = 2 * (qz * vx - qx * vz), tz = 2 * (qx * vy - qy * vx);
    if (axis === 0) return vx + qw * tx + (qy * tz - qz * ty);
    if (axis === 1) return vy + qw * ty + (qz * tx - qx * tz);
    return vz + qw * tz + (qx * ty - qy * tx);
  }

  _pairs(h) {
    const n = this.n; if (n < 2 || this.nComp < 2) return;
    const p = this.pos, im = this.invM, rad = this.rad, comp = this.comp, HS = this._hHead.length, head = this._hHead;
    if (this._hNext.length < n) this._hNext = new Int32Array(this.cap);
    const next = this._hNext, cell = 4 * this.maxRadius, ic = 1 / cell; head.fill(-1);
    const hash = (x, y, z) => ((x * 73856093) ^ (y * 19349663) ^ (z * 83492791)) & (HS - 1);
    for (let i = 0; i < n; i++) { const k = i * 3, hh = hash(Math.floor(p[k] * ic), Math.floor(p[k + 1] * ic), Math.floor(p[k + 2] * ic)); next[i] = head[hh]; head[hh] = i; }
    let cnt = 0; const R0 = this.maxRadius; /* cell = 4 R0 and query reach = r_i + R0 <= 2 R0 -> at most 2 cells per axis */
    for (let i = 0; i < n; i++) {
      const k = i * 3, wi = im[i], ci = comp[i], Q = rad[i] + R0;
      const x0 = Math.floor((p[k] - Q) * ic), x1 = Math.floor((p[k] + Q) * ic), y0 = Math.floor((p[k + 1] - Q) * ic), y1 = Math.floor((p[k + 1] + Q) * ic), z0 = Math.floor((p[k + 2] - Q) * ic), z1 = Math.floor((p[k + 2] + Q) * ic);
      for (let cx = x0; cx <= x1; cx++) for (let cy = y0; cy <= y1; cy++) for (let cz = z0; cz <= z1; cz++) {
        for (let j = head[hash(cx, cy, cz)]; j >= 0; j = next[j]) {
          if (j <= i || comp[j] === ci) continue;
          const wj = im[j], ws = wi + wj; if (ws === 0) continue;
          const kj = j * 3, dx = p[k] - p[kj], dy = p[k + 1] - p[kj + 1], dz = p[k + 2] - p[kj + 2], R = rad[i] + rad[j], d2 = dx * dx + dy * dy + dz * dz;
          if (d2 >= R * R || d2 < 1e-14) continue;
          const d = SQ(d2), s = (R - d) / (d * ws);
          p[k] += dx * s * wi; p[k + 1] += dy * s * wi; p[k + 2] += dz * s * wi;
          p[kj] -= dx * s * wj; p[kj + 1] -= dy * s * wj; p[kj + 2] -= dz * s * wj; cnt++; this.supNow[ci] = 1; this.supNow[comp[j]] = 1;
        }
      }
    }
    this.stats.pairContacts = cnt;
  }

  // velocity update, adaptive-initialisation bookkeeping, plasticity and fracture
  _finish(h, check) {
    const n = this.n, p = this.pos, pr = this.prev, v = this.vel, ih = 1 / h;
    const cv = this.compV, cm = this.compM, comp = this.comp, ms = this.mass, vm2 = this.maxSpeed * this.maxSpeed; cv.fill(0); cm.fill(0);
    for (let i = 0; i < n; i++) {
      const k = i * 3, c = comp[i], m = ms[i];
      v[k] = (p[k] - pr[k]) * ih; v[k + 1] = (p[k + 1] - pr[k + 1]) * ih; v[k + 2] = (p[k + 2] - pr[k + 2]) * ih;
      const sp2 = v[k] * v[k] + v[k + 1] * v[k + 1] + v[k + 2] * v[k + 2];
      if (sp2 > vm2) { const f = this.maxSpeed / SQ(sp2); v[k] *= f; v[k + 1] *= f; v[k + 2] *= f; p[k] = pr[k] + v[k] * h; p[k + 1] = pr[k + 1] + v[k + 1] * h; p[k + 2] = pr[k + 2] + v[k + 2] * h; }   // runaway guard
      cv[c * 3] += m * v[k]; cv[c * 3 + 1] += m * v[k + 1]; cv[c * 3 + 2] += m * v[k + 2]; cm[c] += m;
    }
    for (let c = 0; c < this.nComp; c++) { const m = cm[c] || 1; cv[c * 3] /= m; cv[c * 3 + 1] /= m; cv[c * 3 + 2] /= m; }
    this.supPrev.set(this.supNow); this.supNow.fill(0);
    for (let c = 0; c < this.nComp; c++) if (this.compPin[c]) this.supPrev[c] = 1;
    if (!check) return;
    const nd = this.nd, A = this.da, B = this.db, R = this.dRest, Y = this.dYield, F = this.dFrac, ACT = this.dAct;
    let broke = false;
    for (let c = 0; c < nd; c++) {
      if (ACT[c] === 0) continue;
      const ka = A[c] * 3, kb = B[c] * 3, dx = p[ka] - p[kb], dy = p[ka + 1] - p[kb + 1], dz = p[ka + 2] - p[kb + 2];
      const len = SQ(dx * dx + dy * dy + dz * dz), r0 = R[c], eps = (len - r0) / r0;
      if (eps > F[c] || eps < -F[c] * this.crushRatio) {
        ACT[c] = 0; this.nBroken++; broke = true; this._broke('distance', A[c], B[c], c);
        if (this.dSnap[c]) { const bay = this.dBay[c]; for (let q = 0; q < nd; q++) if (ACT[q] && this.dBay[q] === bay) { ACT[q] = 0; this.nBroken++; this._broke('distance', A[q], B[q], q); } }   // brittle snap: the whole cut section lets go
        continue;
      }
      const ae = eps < 0 ? -eps : eps;
      if (ae > Y[c]) R[c] = len - (eps < 0 ? -Y[c] : Y[c]) * r0;          // plastic flow: rest length follows, strain clamped to yield
    }
    const nw = this.nw;
    if (nw) {
      const WM = this.wMax, WA = this.wAct, WK = this.wK, WR = this.wR;
      for (let w = 0; w < nw; w++) {
        if (WA[w] === 0) continue;
        const ka = this.wa[w] * 3, kb = this.wb[w] * 3;
        const cx = p[ka] - p[kb] - WR[w * 3], cy = p[ka + 1] - p[kb + 1] - WR[w * 3 + 1], cz = p[ka + 2] - p[kb + 2] - WR[w * 3 + 2];
        if (SQ(cx * cx + cy * cy + cz * cz) * WK[w] > WM[w]) { WA[w] = 0; this.nBroken++; broke = true; this._broke('weld', this.wa[w], this.wb[w], w); }
      }
    }
    if (broke) this._compDirty = true;
  }
  _broke(kind, a, b, index) {
    if (kind === 'distance' && this.nt) { // volume constraints containing both ends no longer make sense
      const V = this.tv;
      for (let t = 0; t < this.nt; t++) { let ha = false, hb = false; for (let k = 0; k < 4; k++) { const q = V[t * 4 + k]; if (q === a) ha = true; if (q === b) hb = true; } if (ha && hb) this.tAct[t] = 0; }
    }
    if (this.onBreak) this.onBreak({ kind, a, b, index });
  }

  // ---------- connectivity ----------
  _buildComponents() {
    const n = this.n, par = new Int32Array(n); for (let i = 0; i < n; i++) par[i] = i;
    const find = (x) => { while (par[x] !== x) { par[x] = par[par[x]]; x = par[x]; } return x; };
    const uni = (a, b) => { a = find(a); b = find(b); if (a !== b) { if (a < b) par[b] = a; else par[a] = b; } };
    for (let c = 0; c < this.nd; c++) if (this.dAct[c]) uni(this.da[c], this.db[c]);
    for (let w = 0; w < this.nw; w++) if (this.wAct[w]) uni(this.wa[w], this.wb[w]);
    for (let t = 0; t < this.nt; t++) if (this.tAct[t]) { const q = this.tv; uni(q[t * 4], q[t * 4 + 1]); uni(q[t * 4], q[t * 4 + 2]); uni(q[t * 4], q[t * 4 + 3]); }
    if (this.comp.length < n) this.comp = new Int32Array(this.cap);
    let cnt = 0; const roots = new Map();
    for (let i = 0; i < n; i++) { const r = find(i); if (!roots.has(r)) roots.set(r, cnt++); this.comp[i] = roots.get(r); }
    this.nComp = cnt; this._compDirty = false;
    this.compV = new Float64Array(cnt * 3); this.compM = new Float64Array(cnt); this.compPin = new Uint8Array(cnt); this.supPrev = new Uint8Array(cnt); this.supNow = new Uint8Array(cnt);
    for (let i = 0; i < n; i++) if (this.pinned[i]) this.compPin[this.comp[i]] = 1;
    for (let c = 0; c < cnt; c++) this.supPrev[c] = this.compPin[c];
  }
  componentCount() { if (this._compDirty) this._buildComponents(); return this.nComp; }
  // component sizes (particles) in id order; useful for "did a chunk separate"
  componentSizes() { if (this._compDirty) this._buildComponents(); const s = new Array(this.nComp).fill(0); for (let i = 0; i < this.n; i++) s[this.comp[i]]++; return s; }

  // run n sweeps without advancing time (settle a freshly built structure into its static equilibrium)
  relax(frames = 60, dt = 1 / 60) { const v = this.vel; for (let f = 0; f < frames; f++) this.step(dt); this.vel.fill(0, 0, this.n * 3); }

  // ---------- diagnostics ----------
  energy() {
    const n = this.n, p = this.pos, v = this.vel, m = this.mass, g = this.gravity; let ke = 0, pe = 0, el = 0;
    for (let i = 0; i < n; i++) {
      const k = i * 3; ke += 0.5 * m[i] * (v[k] * v[k] + v[k + 1] * v[k + 1] + v[k + 2] * v[k + 2]);
      pe -= m[i] * (g[0] * p[k] + g[1] * p[k + 1] + g[2] * p[k + 2]);
    }
    for (let c = 0; c < this.nd; c++) { if (!this.dAct[c]) continue; const ka = this.da[c] * 3, kb = this.db[c] * 3; const dx = p[ka] - p[kb], dy = p[ka + 1] - p[kb + 1], dz = p[ka + 2] - p[kb + 2]; const e = SQ(dx * dx + dy * dy + dz * dz) - this.dRest[c]; el += 0.5 * this.dK[c] * e * e; }
    for (let w = 0; w < this.nw; w++) { if (!this.wAct[w]) continue; const ka = this.wa[w] * 3, kb = this.wb[w] * 3; for (let k = 0; k < 3; k++) { const e = p[ka + k] - p[kb + k] - this.wR[w * 3 + k]; el += 0.5 * this.wK[w] * e * e; } }
    for (let t = 0; t < this.nt; t++) { if (!this.tAct[t]) continue; const e = this._vol(this.tv[t * 4], this.tv[t * 4 + 1], this.tv[t * 4 + 2], this.tv[t * 4 + 3]) - this.tV0[t]; el += 0.5 * e * e / this.tAlpha[t]; }
    return { kinetic: ke, potential: pe, elastic: el, total: ke + pe + el };
  }
  centreOfMass() { let M = 0, x = 0, y = 0, z = 0; for (let i = 0; i < this.n; i++) { M += this.mass[i]; x += this.mass[i] * this.pos[i * 3]; y += this.mass[i] * this.pos[i * 3 + 1]; z += this.mass[i] * this.pos[i * 3 + 2]; } return [x / M, y / M, z / M, M]; }
  checksum() { // FNV-1a over the raw bits of the positions: determinism checks
    const u = new Uint32Array(this.pos.buffer, 0, this.n * 6); let hsh = 2166136261 >>> 0;
    for (let i = 0; i < u.length; i++) { hsh ^= u[i]; hsh = Math.imul(hsh, 16777619) >>> 0; }
    return hsh.toString(16);
  }
}

// ======================================================================
// Builders. All take a material descriptor made by makeMaterial().
// ======================================================================
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const mul = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = (a) => { const l = SQ(dot(a, a)) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };

// Prismatic beam / plank. Each cross-section = 4 corner particles + 1 centre particle.
// The 4 corner bars carry exactly the second moment of area I = w h^3 / 12 (A_c = w h / 12 each, so
// sum A_c y^2 = I about both axes), the centre bar carries the remaining axial area, and one alternating
// diagonal per face per bay is sized so the truss has the Timoshenko shear stiffness kappa*G*A.
export function buildBeam(w, o) {
  const mat = o.mat, W = o.width, H = o.height, A = W * H;
  const a = o.a, b = o.b, ax = sub(b, a), L = SQ(dot(ax, ax)), t = norm(ax);
  let up = o.up || [0, 1, 0]; if (Math.abs(dot(t, up)) > 0.98) up = [1, 0, 0];
  const s = norm(cross(t, up)), u = cross(s, t);                 // s: width direction, u: height direction
  const seg = o.segments || Math.max(1, Math.round(L / ((o.bayRatio ?? 1.5) * Math.max(W, H, 1e-6))));
  const dx = L / seg, group = o.group ?? w.newGroup(), rad = o.radius ?? Math.min(W, H) * 0.5;
  const sx = [-1, 1, 1, -1], sy = [-1, -1, 1, 1];
  const mk = (i) => {
    const c = add(a, mul(t, dx * i)), pts = [];
    const ci = w.addParticle(c[0], c[1], c[2], 0, rad, group, mat.drag);
    const corners = [];
    for (let k = 0; k < 4; k++) { const q = add(c, add(mul(s, sx[k] * W / 2), mul(u, sy[k] * H / 2))); corners.push(w.addParticle(q[0], q[1], q[2], 0, rad, group, mat.drag)); }
    return { c: ci, k: corners, all: [ci, ...corners] };
  };
  const sections = [];
  for (let i = 0; i <= seg; i++) sections.push(i === 0 && o.start ? o.start : mk(i));
  const Ac = W * H / 12, Acentre = A - 4 * Ac, nu = mat.poisson, G = mat.shear, kappa = 5 / 6;
  const dArea = (span) => { const d = SQ(dx * dx + span * span); return (o.diagScale ?? 0.7) * Math.max(A * (o.diagMin ?? 0.02), G * kappa * A * d * d * d / (2 * mat.youngs * span * span * dx)); };
  const secArea = A * (o.sectionFrac ?? 0.01);
  const sectionBars = (S) => {
    for (let k = 0; k < 4; k++) { w.addDistance(S.k[k], S.k[(k + 1) % 4], mat, secArea, { tag: 1 }); w.addDistance(S.c, S.k[k], mat, secArea, { tag: 1 }); }
    w.addDistance(S.k[0], S.k[2], mat, secArea, { tag: 1 }); w.addDistance(S.k[1], S.k[3], mat, secArea, { tag: 1 });
  };
  if (!o.start) sectionBars(sections[0]);
  for (let i = 0; i < seg; i++) {
    const S0 = sections[i], S1 = sections[i + 1], par = i & 1, bay = w.newBay();
    for (let k = 0; k < 4; k++) w.addDistance(S0.k[k], S1.k[k], mat, Ac, { tag: 0, bay });
    w.addDistance(S0.c, S1.c, mat, Acentre, { tag: 0, bay });
    for (let k = 0; k < 4; k++) {                                  // face diagonals, alternating direction per bay
      const k2 = (k + 1) % 4, span = (k === 0 || k === 2) ? W : H;
      if (par) w.addDistance(S0.k[k2], S1.k[k], mat, dArea(span), { tag: 2, bay }); else w.addDistance(S0.k[k], S1.k[k2], mat, dArea(span), { tag: 2, bay });
    }
    sectionBars(S1);
  }
  // mass: each bay's mass split between its two sections, then 1/5 per particle
  const mBay = mat.density * A * dx;
  for (let i = 0; i < seg; i++) for (const S of [sections[i], sections[i + 1]]) for (const q of S.all) w.addMass(q, mBay * 0.5 / 5);
  if (o.pin === 'start' || o.pin === 'both') for (const q of sections[0].all) w.pin(q);
  if (o.pin === 'end' || o.pin === 'both') for (const q of sections[seg].all) w.pin(q);
  return { sections, length: L, dx, segments: seg, group, width: W, height: H, I: W * H * H * H / 12, area: A, tip: sections[seg], root: sections[0] };
}
export function buildPlank(w, o) { return buildBeam(w, { ...o, up: o.up || [0, 1, 0], width: o.width, height: o.thickness }); }

// Rope / cable: chain of particles joined by distance constraints. slack >= 1 multiplies the straight length.
export function buildRope(w, o) {
  const mat = o.mat, r = o.radius ?? 0.02, a = o.a, b = o.b, seg = o.segments || 20, A = Math.PI * r * r;
  const D = SQ(dot(sub(b, a), sub(b, a))), slack = o.slack ?? 1, group = o.group ?? w.newGroup();
  // slack > 1: start on the parabola whose arc length is D*slack (arc ~ D + 8 s^2 / (3 D)), so initial strains are ~0
  const sag = slack > 1 ? SQ(3 * D * (D * slack - D) / 8) : 0, ids = [];
  for (let i = 0; i <= seg; i++) {
    const f = i / seg, p = add(a, mul(sub(b, a), f));
    ids.push(w.addParticle(p[0], p[1] - 4 * sag * f * (1 - f), p[2], 0, r, group, mat.drag));
  }
  let len = 0;
  for (let i = 0; i < seg; i++) {
    const c = w.addDistance(ids[i], ids[i + 1], mat, A), dl = w.dRest[c]; len += dl;
    const m = mat.density * A * dl; w.addMass(ids[i], m / 2); w.addMass(ids[i + 1], m / 2);
  }
  if (o.pin === 'start' || o.pin === 'both') w.pin(ids[0]);
  if (o.pin === 'end' || o.pin === 'both') w.pin(ids[seg]);
  return { ids, length: len, group, area: A };
}

// Cloth / sail: nu x nv grid spanned by du, dv. Structural + shear + skip-one bend bars, aero triangles.
export function buildCloth(w, o) {
  const mat = o.mat, nu = o.nu, nv = o.nv, th = o.thickness ?? 0.002, O = o.origin, du = o.du, dv = o.dv, group = o.group ?? w.newGroup();
  const sU = SQ(dot(du, du)) / (nu - 1), sV = SQ(dot(dv, dv)) / (nv - 1), rad = o.radius ?? Math.min(sU, sV) * 0.3;
  const id = (i, j) => ids[j * nu + i], ids = [];
  for (let j = 0; j < nv; j++) for (let i = 0; i < nu; i++) { const p = add(O, add(mul(du, i / (nu - 1)), mul(dv, j / (nv - 1)))); ids.push(w.addParticle(p[0], p[1], p[2], 0, rad, group, mat.drag)); }
  const bar = (a, b, f) => { const pa = w.pos, ka = a * 3, kb = b * 3; const L = Math.hypot(pa[ka] - pa[kb], pa[ka + 1] - pa[kb + 1], pa[ka + 2] - pa[kb + 2]); w.addDistance(a, b, mat, th * L * f); };
  for (let j = 0; j < nv; j++) for (let i = 0; i < nu; i++) {
    if (i + 1 < nu) bar(id(i, j), id(i + 1, j), 1); if (j + 1 < nv) bar(id(i, j), id(i, j + 1), 1);
    if (i + 1 < nu && j + 1 < nv) { bar(id(i, j), id(i + 1, j + 1), 0.5); bar(id(i + 1, j), id(i, j + 1), 0.5); }
    if (o.bend) { if (i + 2 < nu) bar(id(i, j), id(i + 2, j), 0.05); if (j + 2 < nv) bar(id(i, j), id(i, j + 2), 0.05); }   // optional skip-one bending bars
  }
  for (let j = 0; j + 1 < nv; j++) for (let i = 0; i + 1 < nu; i++) {
    const q = mat.density * th * sU * sV; for (const k of [id(i, j), id(i + 1, j), id(i, j + 1), id(i + 1, j + 1)]) w.addMass(k, q / 4);
    if (o.aero !== false) { w.addAeroTri(id(i, j), id(i + 1, j), id(i, j + 1), o.cd ?? 1.2); w.addAeroTri(id(i + 1, j), id(i + 1, j + 1), id(i, j + 1), o.cd ?? 1.2); }
  }
  const pins = o.pin || []; // list of 'top' | 'left' | 'right' | 'bottom' | 'corners'
  for (const pn of pins) {
    if (pn === 'top') for (let i = 0; i < nu; i++) w.pin(id(i, nv - 1)); if (pn === 'bottom') for (let i = 0; i < nu; i++) w.pin(id(i, 0));
    if (pn === 'left') for (let j = 0; j < nv; j++) w.pin(id(0, j)); if (pn === 'right') for (let j = 0; j < nv; j++) w.pin(id(nu - 1, j));
    if (pn === 'corners') for (const [i, j] of [[0, 0], [nu - 1, 0], [0, nv - 1], [nu - 1, nv - 1]]) w.pin(id(i, j));
  }
  return { ids, nu, nv, group, id };
}

// Masonry-like block cluster: nx*ny*nz stacked blocks (stack bond). Each block = 8 corner particles and 18 stone bars
// (12 edges + 6 face diagonals = rigid cube; add 5 volume tets with volume:true). Facing corners of neighbouring blocks are held by mortar welds that
// break by force (tension strength * share of the face area) and then the blocks separate and collide (pair contacts).
export function buildBlockCluster(w, o) {
  const stone = o.mat, mortar = o.mortar, [bx, by, bz] = o.size, [nx, ny, nz] = o.counts, O = o.origin, gap = o.joint ?? 0.01;
  const blocks = [], key = new Map();
  const rad = o.radius ?? Math.min(bx, by, bz) * 0.12;
  for (let k = 0; k < nz; k++) for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
    const grp = w.newGroup(), base = [O[0] + i * bx, O[1] + j * by, O[2] + k * bz], c = [];
    for (let q = 0; q < 8; q++) { const px = q & 1, py = (q >> 1) & 1, pz = (q >> 2) & 1; c.push(w.addParticle(base[0] + px * bx, base[1] + py * by, base[2] + pz * bz, 0, rad, grp, stone.drag)); }
    const vol = bx * by * bz, m = stone.density * vol; for (const q of c) w.addMass(q, m / 8);
    const A = Math.min(bx * by, by * bz, bx * bz) * 0.25;
    for (let q = 0; q < 8; q++) for (let r = q + 1; r < 8; r++) { const d = (q ^ r); if (d === 1 || d === 2 || d === 4 || d === 3 || d === 5 || d === 6) w.addDistance(c[q], c[r], stone, A); }
    if (o.volume) for (const [p0, p1, p2, p3] of [[0, 1, 2, 4], [3, 1, 2, 7], [5, 1, 4, 7], [6, 2, 4, 7], [1, 2, 4, 7]]) w.addTetra(c[p0], c[p1], c[p2], c[p3], stone);   // optional volume preservation
    blocks.push({ i, j, k, c, grp }); key.set(i + ',' + j + ',' + k, blocks[blocks.length - 1]);
  }
  const weld = (A, B, qa, qb, area) => { w.addWeld(A.c[qa], B.c[qb], mortar, area, gap); };
  for (const B of blocks) {
    const R = key.get((B.i + 1) + ',' + B.j + ',' + B.k), U = key.get(B.i + ',' + (B.j + 1) + ',' + B.k), F = key.get(B.i + ',' + B.j + ',' + (B.k + 1));
    if (R) for (let q = 0; q < 8; q++) if (q & 1) weld(B, R, q, q & ~1, by * bz / 4);
    if (U) for (let q = 0; q < 8; q++) if (q & 2) weld(B, U, q, q & ~2, bx * bz / 4);
    if (F) for (let q = 0; q < 8; q++) if (q & 4) weld(B, F, q, q & ~4, bx * by / 4);
  }
  if (o.pinBase) for (const B of blocks) if (B.j === 0) for (let q = 0; q < 8; q++) if (!(q & 2)) w.pin(B.c[q]);
  return { blocks, key };
}

// Soft solid ("jelly" / foam / clay): nx*ny*nz cells, 6 Kuhn tets per cell with volume constraints plus edge bars.
export function buildJelly(w, o) {
  const mat = o.mat, [sx, sy, sz] = o.size, [nx, ny, nz] = o.counts, O = o.origin, group = o.group ?? w.newGroup(), rad = o.radius ?? Math.min(sx, sy, sz) / Math.max(nx, ny, nz) * 0.3;
  const ix = (i, j, k) => (k * (ny + 1) + j) * (nx + 1) + i, ids = [];
  for (let k = 0; k <= nz; k++) for (let j = 0; j <= ny; j++) for (let i = 0; i <= nx; i++) ids.push(w.addParticle(O[0] + sx * i / nx, O[1] + sy * j / ny, O[2] + sz * k / nz, 0, rad, group, mat.drag));
  const edges = new Set(), cellV = sx * sy * sz / (nx * ny * nz), tets = [[0, 1, 3, 7], [0, 1, 5, 7], [0, 2, 3, 7], [0, 2, 6, 7], [0, 4, 5, 7], [0, 4, 6, 7]];
  const hx = sx / nx, hy = sy / ny, hz = sz / nz, aE = Math.min(hx * hy, hy * hz, hx * hz) * 0.25;
  for (let k = 0; k < nz; k++) for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
    const c = []; for (let q = 0; q < 8; q++) c.push(ids[ix(i + (q & 1), j + ((q >> 1) & 1), k + ((q >> 2) & 1))]);
    for (const t of tets) {
      w.addTetra(c[t[0]], c[t[1]], c[t[2]], c[t[3]], mat);
      for (let a = 0; a < 4; a++) for (let b = a + 1; b < 4; b++) { const A = Math.min(c[t[a]], c[t[b]]), B = Math.max(c[t[a]], c[t[b]]), key = A * 1e7 + B; if (!edges.has(key)) { edges.add(key); w.addDistance(A, B, mat, aE); } }
    }
    for (const q of c) w.addMass(q, mat.density * cellV / 8);
  }
  if (o.pin === 'top') for (let k = 0; k <= nz; k++) for (let i = 0; i <= nx; i++) w.pin(ids[ix(i, ny, k)]);
  return { ids, ix, volume: () => { let V = 0; for (let t = 0; t < w.nt; t++) if (w.tAct[t]) V += Math.abs(w._vol(w.tv[t * 4], w.tv[t * 4 + 1], w.tv[t * 4 + 2], w.tv[t * 4 + 3])); return V; }, volume0: sx * sy * sz };
}
