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
    yield: yieldS, fracture: fracS, crush: d.crush ?? fracS * 4, damping: d.damping ?? 0.1,   // crush: compressive strength (Pa)
    scatter: d.scatter ?? 0.05,
    snap: !!d.snap,                                // brittle: when one bar of a cut section fails the whole section snaps                    // +/- relative scatter of strength per constraint (seeded)
    shear: youngs / (2 * (1 + poisson)),
    bulk: youngs / (3 * (1 - 2 * poisson)),
    yieldStrain: yieldS / youngs, fracStrain: fracS / youngs, crushStrain: (d.crush ?? fracS * 4) / youngs,
    beta: (d.damping ?? 0.1) * BETA_PER_DAMP, drag: (d.damping ?? 0.1) * DRAG_PER_DAMP,
  });
}

// Reference material descriptors (rough, ranged for game use; bending/tension strengths in Pa)
export const MATERIALS = {
  wood:   { name: 'wood',   density: 600,  youngs: 1.0e10, yield: 4.0e7, fracture: 6.0e7, crush: 1.2e8, damping: 0.2, snap: true },
  steel:  { name: 'steel',  density: 7800, youngs: 2.0e11, yield: 2.5e8, fracture: 4.0e8, damping: 0.1 },
  rope:   { name: 'rope',   density: 900,  youngs: 5.0e8,  yield: 1.0e12, fracture: 8.0e7, damping: 0.4 },
  cloth:  { name: 'cloth',  density: 400,  youngs: 5.0e7,  yield: 1.0e12, fracture: 5.0e7, damping: 0.5 },
  stone:  { name: 'stone',  density: 2500, youngs: 3.0e9, yield: 6.0e7, fracture: 5.0e6, crush: 6.0e7, damping: 1.0, snap: true },
  mortar: { name: 'mortar', density: 1900, youngs: 1.0e9,  yield: 1.0e13, fracture: 3.0e5, crush: 1.0e7, damping: 1.0 },
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
    this.sleepOn = o.sleep ?? false; this.sleepSpeed = o.sleepSpeed ?? 2e-5; this.sleepTime = o.sleepTime ?? 1.0; this.nAsleep = 0;
    this.maxColliderStrain = o.maxColliderStrain ?? 0.05; this.maxSubstepBoost = o.maxSubstepBoost ?? 4; this.minBar = 0.1;
    this.maxPush = o.maxPush ?? 0.01; this._limitPush = false;   // per-substep depenetration cap for colliders (ground contacts are not capped)
    this.pairs = o.pairs ?? true;                   // particle-particle contacts between different connected pieces (once per frame)
    this.persist = o.persist ?? 6;                  // an over-limit bar/weld must stay over the limit for this many checks before it breaks ...
    this.hardFactor = o.hardFactor ?? 5;            // ... unless it is over by this factor (then it breaks at once). Filters solver noise.
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
    this.nct = 0; this.cta = new Int32Array(192); this.ctr = new Float64Array(64); this._bc = new Float64Array(3);
    this.nce = 0; this.cea = new Int32Array(64); this.ceb = new Int32Array(64); this.cer = new Float64Array(64); this._qn = new Float64Array(3);
    this.nd = 0; this.capD = 0; this._allocD(o.capacity ? o.capacity * 3 : 1536);
    this.nt = 0; this.capT = 0; this._allocT(128);
    this.nw = 0; this.capW = 0; this._allocW(128);
    this.nTri = 0; this.tri = new Int32Array(0); this.triCd = new Float64Array(0);
    this.nextGroup = 1; this.nextBay = 1; this.nBroken = 0;
    this._compDirty = true; this.comp = new Int32Array(0); this.nComp = 0; this.compSp = new Float64Array(0); this.compAsleep = new Uint8Array(0); this.compSleepT = new Float64Array(0); this.actList = new Int32Array(0); this.nAct = 0; this.compV = new Float64Array(0); this.compM = new Float64Array(0); this.compPin = new Uint8Array(0); this.supPrev = new Uint8Array(0); this.supNow = new Uint8Array(0);
    this._hHead = new Int32Array(8192); this._hNext = new Int32Array(0);
    this._sweep = 0; this._adjDirty = true; this.stepMax = o.stepMax ?? 0.25; this.omega = o.omega ?? 0.6; this.maxSpeed = o.maxSpeed ?? 80; this.adjStart = null; this.maxRadius = 0.01;
    this.stats = { contacts: 0, pairContacts: 0 }; this.nanGuard = 0;
  }

  // ---------- storage ----------
  _allocP(c) {
    const g = (old, k, T) => { const a = new T(c * k); if (old) a.set(old.subarray(0, Math.min(old.length, a.length))); return a; };
    this.pos = g(this.pos, 3, Float64Array); this.prev = g(this.prev, 3, Float64Array); this.vel = g(this.vel, 3, Float64Array);
    this.ext = g(this.ext, 3, Float64Array); this.aeroF = g(this.aeroF, 3, Float64Array);
    this.mass = g(this.mass, 1, Float64Array); this.invM = g(this.invM, 1, Float64Array); this.rad = g(this.rad, 1, Float64Array);
    this.drag = g(this.drag, 1, Float64Array); this.dead = g(this.dead, 1, Uint8Array); this.xt = g(this.xt, 3, Float64Array); this.group = g(this.group, 1, Int32Array); this.pinned = g(this.pinned, 1, Uint8Array);
    this.cap = c;
  }
  _allocD(c) {
    const g = (old, T) => { const a = new T(c); if (old) a.set(old.subarray(0, Math.min(old.length, a.length))); return a; };
    this.da = g(this.da, Int32Array); this.db = g(this.db, Int32Array); this.dRest = g(this.dRest, Float64Array);
    this.dAlpha = g(this.dAlpha, Float64Array); this.dBeta = g(this.dBeta, Float64Array); this.dYield = g(this.dYield, Float64Array);
    this.dFrac = g(this.dFrac, Float64Array); this.dCrush = g(this.dCrush, Float64Array); this.dAct = g(this.dAct, Uint8Array); this.dLam = g(this.dLam, Float64Array);
    this.dK = g(this.dK, Float64Array); this.dTag = g(this.dTag, Int32Array); this.dBay = g(this.dBay, Int32Array); this.dOver = g(this.dOver, Uint8Array); this.dSnap = g(this.dSnap, Uint8Array);
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
    this.wN = g(this.wN, Float64Array, 3); this.wSh = g(this.wSh, Float64Array); this.wAct = g(this.wAct, Uint8Array); this.wOver = g(this.wOver, Uint8Array); this.wLam = g(this.wLam, Float64Array, 3); this.wK = g(this.wK, Float64Array);
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
    if (o.tag !== 1 && rest > 0.02) { this._barSum = (this._barSum || 0) + rest; this._barN = (this._barN || 0) + 1; this.minBar = this._barSum / this._barN; }   // mean bar length (ignores very short section bars)
    this.da[c] = a; this.db[c] = b; this.dRest[c] = rest; this.dK[c] = k; this.dAlpha[c] = 1 / k;
    this.dBeta[c] = mat.beta; this.dYield[c] = mat.yieldStrain * sc; this.dFrac[c] = (o.fracStrain ?? mat.fracStrain) * sc; this.dCrush[c] = mat.crushStrain * sc;
    this.dAct[c] = 1; this.dLam[c] = 0; this.dTag[c] = o.tag ?? 0; this.dBay[c] = o.bay ?? 0; if (o.tag === 1) { this.dFrac[c] = Infinity; this.dCrush[c] = Infinity; } this.dSnap[c] = mat.snap && o.bay ? 1 : 0;   // tag 1 = section-shape bars of beams: they never fracture themselves
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
    const k = o.k ?? mat.youngs * area / gap, sc = 1 + mat.scatter * (2 * this.rng() - 1);
    this.wK[w] = k; this.wAlpha[w] = 1 / k; this.wBeta[w] = mat.beta;
    this.wMax[w] = (o.maxForce ?? mat.fracture * area) * sc; this.wAct[w] = 1;
    // optional joint normal (unit, pointing from a to b): tension and compression are then treated differently
    const nn = o.normal || [0, 0, 0]; this.wN[w * 3] = nn[0]; this.wN[w * 3 + 1] = nn[1]; this.wN[w * 3 + 2] = nn[2]; this.wSh[w] = o.shearRatio ?? 1.5;
    this.wLam[w * 3] = 0; this.wLam[w * 3 + 1] = 0; this.wLam[w * 3 + 2] = 0;
    this._compDirty = true; this._adjDirty = true;
    return w;
  }
  addCollisionEdge(a, b, radius) {
    if (this.nce >= this.cea.length) { const g = (o, T) => { const x = new T(o.length * 2); x.set(o); return x; }; this.cea = g(this.cea, Int32Array); this.ceb = g(this.ceb, Int32Array); this.cer = g(this.cer, Float64Array); }
    const e = this.nce++; this.cea[e] = a; this.ceb[e] = b; this.cer[e] = radius; return e;
  }
  addCollisionTri(a, b, c, radius) {
    if (this.nct * 3 >= this.cta.length) { const x = new Int32Array(this.cta.length * 2); x.set(this.cta); this.cta = x; const y = new Float64Array(this.ctr.length * 2); y.set(this.ctr); this.ctr = y; }
    const e = this.nct++; this.cta[e * 3] = a; this.cta[e * 3 + 1] = b; this.cta[e * 3 + 2] = c; this.ctr[e] = radius; return e;
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
    let S = this.substepHz ? Math.max(1, Math.round(dt * this.substepHz)) : this.substeps;
    // a fast collider must not push a particle further than a fraction of a bar length in one substep (the neighbours
    // cannot follow in a single sweep): add substeps while it is fast. Costs nothing when no collider moves.
    if (this.colliders.length && this.maxColliderStrain > 0) {
      let vmax = 0; for (const c of this.colliders) { const v = c.v; vmax = Math.max(vmax, Math.hypot(v[0], v[1], v[2])); }
      const need = Math.ceil(dt * vmax / (this.maxColliderStrain * this.minBar)); if (need > S) S = Math.min(need, S * this.maxSubstepBoost);
    }
    const h = dt / S;
    if (this._compDirty) this._buildComponents();
    if (this._adjDirty) this._buildAdj();
    if (this.sleepOn && this.nAsleep) this._wakeScan();
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
    else if (this.sleepOn) this._sleepUpdate(dt);
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
    const g = this.gravity, gx = g[0], gy = g[1], gz = g[2], useA = this.nTri > 0 && this.wind, h2 = h * h, al = this.actList, na = this.nAct;
    for (let q = 0; q < na; q++) {
      const i = al[q], k = i * 3; pr[k] = p[k]; pr[k + 1] = p[k + 1]; pr[k + 2] = p[k + 2];
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
    const al = this.actList, na = this.nAct;
    for (let q = 0; q < na; q++) {
      const i = rev ? al[na - 1 - q] : al[q]; if (im[i] === 0) continue;
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
    const cu = this._cull, al = this.actList, na = this.nAct;
    for (let q = 0; q < na; q++) {
      const i = al[q]; if (im[i] === 0) continue;
      const k = i * 3, r = rad[i], px = p[k], py = p[k + 1], pz = p[k + 2];
      if (hf && py - r < hfMax) {
        const x = px, z = pz, gh = hf(x, z), pen = gh + r - py;
        if (pen > 0) {
          contacts++; this.supNow[this.comp[i]] = 1;
          // normal from central differences (only on contact)
          const e = 0.05, gx = (hf(x + e, z) - gh) / e, gz = (hf(x, z + e) - gh) / e;
          const il = 1 / SQ(gx * gx + gz * gz + 1), nx = -gx * il, ny = il, nz = -gz * il;
          const d = pen * ny; // move along the normal so the particle ends at distance r above the surface
          this._resolve(k, nx, ny, nz, d, 0, 0, 0, h);
          this._friction(k, nx, ny, nz, d, mu, 0, 0, 0, h);
        }
      }
      for (let c = 0; c < nc; c++) {
        const o = c * 6; if (px < cu[o] || px > cu[o + 3] || py < cu[o + 1] || py > cu[o + 4] || pz < cu[o + 2] || pz > cu[o + 5]) continue;
        if (this._colliderContact(cols[c], i, k, r, mu, h)) { contacts++; this.supNow[this.comp[i]] = 1; }
      }
    }
    if (this.nce || this.nct) this._collideSkin(h);
    this.stats.contacts = contacts;
  }

  // Push a penetrating particle out along the unit normal n by pen WITHOUT turning the push into velocity (the previous
  // position moves with it), and make the contact inelastic: the particle's normal velocity relative to the surface
  // (surface velocity cv) is raised to the surface's. Returns the normal velocity change (>= 0) given to the particle.
  _resolve(k, nx, ny, nz, pen, cvx, cvy, cvz, h) {
    const p = this.pos, pr = this.prev, ih = 1 / h;
    const lim = Math.max(this.maxPush, 1.5 * Math.hypot(cvx, cvy, cvz) * h); if (pen > lim && this._limitPush) pen = lim;
    const vn = ((p[k] - pr[k]) * nx + (p[k + 1] - pr[k + 1]) * ny + (p[k + 2] - pr[k + 2]) * nz) * ih, cvn = cvx * nx + cvy * ny + cvz * nz;
    p[k] += nx * pen; p[k + 1] += ny * pen; p[k + 2] += nz * pen; pr[k] += nx * pen; pr[k + 1] += ny * pen; pr[k + 2] += nz * pen;
    if (vn < cvn) { const dv = (cvn - vn) * h; pr[k] -= nx * dv; pr[k + 1] -= ny * dv; pr[k + 2] -= nz * dv; return cvn - vn; }
    return 0;
  }

  _friction(k, nx, ny, nz, pen, mu, cvx, cvy, cvz, h) {
    const p = this.pos, pr = this.prev;
    let tx = (p[k] - pr[k]) - cvx * h, ty = (p[k + 1] - pr[k + 1]) - cvy * h, tz = (p[k + 2] - pr[k + 2]) - cvz * h;
    const dn = tx * nx + ty * ny + tz * nz; tx -= dn * nx; ty -= dn * ny; tz -= dn * nz;
    const tm = SQ(tx * tx + ty * ty + tz * tz); if (tm < 1e-14) return;
    const f = mu * pen, s = tm < f ? 1 : f / tm;
    p[k] -= tx * s; p[k + 1] -= ty * s; p[k + 2] -= tz * s;
  }

  // closest-feature query of one collider against a sphere (centre px,py,pz, radius r): returns penetration depth (0 = none)
  // and leaves the unit push-out normal in this._qn
  _cq(c, px, py, pz, r) {
    const qn = this._qn; let nx, ny, nz, pen;
    if (c.type === 'sphere') {
      const dx = px - c.c[0], dy = py - c.c[1], dz = pz - c.c[2], R = c.r + r;
      const d2 = dx * dx + dy * dy + dz * dz; if (d2 >= R * R) return 0;
      const d = SQ(d2); if (d < 1e-9) { nx = 0; ny = 1; nz = 0; pen = R; } else { nx = dx / d; ny = dy / d; nz = dz / d; pen = R - d; }
    } else {
      // oriented box: local frame via conjugate quaternion
      const q = c.q || [0, 0, 0, 1], qx = q[0], qy = q[1], qz = q[2], qw = q[3];
      const rx = px - c.c[0], ry = py - c.c[1], rz = pz - c.c[2];
      const lx = this._rot(-qx, -qy, -qz, qw, rx, ry, rz, 0), ly = this._rot(-qx, -qy, -qz, qw, rx, ry, rz, 1), lz = this._rot(-qx, -qy, -qz, qw, rx, ry, rz, 2);
      const hx = c.h[0], hy = c.h[1], hz = c.h[2];
      const cx = Math.max(-hx, Math.min(hx, lx)), cy = Math.max(-hy, Math.min(hy, ly)), cz = Math.max(-hz, Math.min(hz, lz));
      const ox = lx - cx, oy = ly - cy, oz = lz - cz, d2 = ox * ox + oy * oy + oz * oz;
      let lnx, lny, lnz;
      if (d2 > 1e-18) { if (d2 >= r * r) return 0; const d = SQ(d2); lnx = ox / d; lny = oy / d; lnz = oz / d; pen = r - d; }
      else { // centre inside the box: exit through the nearest face
        const ax = hx - Math.abs(lx), ay = hy - Math.abs(ly), az = hz - Math.abs(lz);
        lnx = lny = lnz = 0;
        if (ax <= ay && ax <= az) { lnx = lx >= 0 ? 1 : -1; pen = ax + r; } else if (ay <= az) { lny = ly >= 0 ? 1 : -1; pen = ay + r; } else { lnz = lz >= 0 ? 1 : -1; pen = az + r; }
      }
      nx = this._rot(qx, qy, qz, qw, lnx, lny, lnz, 0); ny = this._rot(qx, qy, qz, qw, lnx, lny, lnz, 1); nz = this._rot(qx, qy, qz, qw, lnx, lny, lnz, 2);
    }
    qn[0] = nx; qn[1] = ny; qn[2] = nz; return pen;
  }

  _colliderContact(c, i, k, r, mu, h) {
    const p = this.pos, pen = this._cq(c, p[k], p[k + 1], p[k + 2], r); if (pen <= 0) return false;
    const nx = this._qn[0], ny = this._qn[1], nz = this._qn[2];
    const v = c.v; this._limitPush = true; const dvn = this._resolve(k, nx, ny, nz, pen, v[0], v[1], v[2], h); this._limitPush = false;
    if (v[0] !== 0 || v[1] !== 0 || v[2] !== 0 || mu > 0) this._friction(k, nx, ny, nz, pen, mu, v[0], v[1], v[2], h);
    // reaction impulse on the collider = minus the momentum the contact gave the particle along the normal; torque about its centre
    const m = this.mass[i], s = m * dvn, jx = -nx * s, jy = -ny * s, jz = -nz * s;
    c.j[0] += jx; c.j[1] += jy; c.j[2] += jz;
    const rx = p[k] - c.c[0], ry = p[k + 1] - c.c[1], rz = p[k + 2] - c.c[2];
    c.tq[0] += ry * jz - rz * jy; c.tq[1] += rz * jx - rx * jz; c.tq[2] += rx * jy - ry * jx;
    return true;
  }

  // Colliders versus the collision SKIN: edges (ropes, beam chords) and triangles (beam faces). A contact point on a skin
  // element is a virtual particle with barycentric weights over 2 or 3 real particles, so a ball or box cannot slip
  // between widely spaced section particles and the push is shared by the real particles in inverse-mass proportion.
  _applyVirtual(col, ia, ib, ic, ua, ub, uc, px, py, pz, nx, ny, nz, pen, h) {
    const p = this.pos, pr = this.prev, im = this.invM, ih = 1 / h;
    const ka = ia * 3, kb = ib * 3, kc = ic >= 0 ? ic * 3 : 0, wa = im[ia], wb = im[ib], wc = ic >= 0 ? im[ic] : 0;
    let den = wa * ua * ua + wb * ub * ub + wc * uc * uc; if (den === 0) return false;
    // a contact point sitting (mostly) on a pinned/static vertex cannot be pushed by moving its free neighbours: skip it
    if ((wa === 0 && ua > 0.4) || (wb === 0 && ub > 0.4) || (wc === 0 && ic >= 0 && uc > 0.4)) return false;
    { const cv = col.v, lim = Math.max(this.maxPush, 1.5 * Math.hypot(cv[0], cv[1], cv[2]) * h); if (pen > lim) pen = lim; }   // soft push: deep penetrations are resolved over several substeps
    let sp = pen / den; { const wm = Math.max(wa * ua, wb * ub, wc * uc); if (sp * wm > 3 * pen) sp = 3 * pen / wm; }   // never move a vertex more than 3x the penetration
    const ca = sp * wa * ua, cb = sp * wb * ub, cc = sp * wc * uc; den = Math.max(den, 1e-12);
    p[ka] += nx * ca; p[ka + 1] += ny * ca; p[ka + 2] += nz * ca; p[kb] += nx * cb; p[kb + 1] += ny * cb; p[kb + 2] += nz * cb;
    pr[ka] += nx * ca; pr[ka + 1] += ny * ca; pr[ka + 2] += nz * ca; pr[kb] += nx * cb; pr[kb + 1] += ny * cb; pr[kb + 2] += nz * cb;      // the push is not velocity
    if (ic >= 0) { p[kc] += nx * cc; p[kc + 1] += ny * cc; p[kc + 2] += nz * cc; pr[kc] += nx * cc; pr[kc + 1] += ny * cc; pr[kc + 2] += nz * cc; }
    let vx = ua * (p[ka] - pr[ka]) + ub * (p[kb] - pr[kb]), vy = ua * (p[ka + 1] - pr[ka + 1]) + ub * (p[kb + 1] - pr[kb + 1]), vz = ua * (p[ka + 2] - pr[ka + 2]) + ub * (p[kb + 2] - pr[kb + 2]);
    if (ic >= 0) { vx += uc * (p[kc] - pr[kc]); vy += uc * (p[kc + 1] - pr[kc + 1]); vz += uc * (p[kc + 2] - pr[kc + 2]); }
    const v = col.v, vn = (vx * nx + vy * ny + vz * nz) * ih, cvn = v[0] * nx + v[1] * ny + v[2] * nz;
    if (vn < cvn) {                                        // inelastic: raise the contact point's normal velocity to the collider's
      const dv = cvn - vn, k2 = dv * h / den, da = k2 * wa * ua, db = k2 * wb * ub, dc = k2 * wc * uc;
      pr[ka] -= nx * da; pr[ka + 1] -= ny * da; pr[ka + 2] -= nz * da; pr[kb] -= nx * db; pr[kb + 1] -= ny * db; pr[kb + 2] -= nz * db;
      if (ic >= 0) { pr[kc] -= nx * dc; pr[kc + 1] -= ny * dc; pr[kc + 2] -= nz * dc; }
      const J = dv / den, jx = -nx * J, jy = -ny * J, jz = -nz * J;   // momentum delivered along n = effective mass * dv
      col.j[0] += jx; col.j[1] += jy; col.j[2] += jz;
      const rx = px - col.c[0], ry = py - col.c[1], rz = pz - col.c[2];
      col.tq[0] += ry * jz - rz * jy; col.tq[1] += rz * jx - rx * jz; col.tq[2] += rx * jy - ry * jx;
    }
    this.supNow[this.comp[ia]] = 1;
    return true;
  }

  _collideSkin(h) {
    const cols = this.colliders, nc = cols.length; if (!nc || (!this.nce && !this.nct)) return;
    const p = this.pos, asl = this.compAsleep, cmp = this.comp, cu = this._cull, anyA = this.nAsleep > 0;
    for (let e = 0; e < this.nce; e++) {
      const a = this.cea[e], b = this.ceb[e]; if (anyA && asl[cmp[a]]) continue;
      const ka = a * 3, kb = b * 3, rr = this.cer[e];
      const lox = Math.min(p[ka], p[kb]) - rr, hix = Math.max(p[ka], p[kb]) + rr, loy = Math.min(p[ka + 1], p[kb + 1]) - rr, hiy = Math.max(p[ka + 1], p[kb + 1]) + rr, loz = Math.min(p[ka + 2], p[kb + 2]) - rr, hiz = Math.max(p[ka + 2], p[kb + 2]) + rr;
      for (let c = 0; c < nc; c++) {
        const o = c * 6; if (hix < cu[o] || lox > cu[o + 3] || hiy < cu[o + 1] || loy > cu[o + 4] || hiz < cu[o + 2] || loz > cu[o + 5]) continue;
        const col = cols[c], len = SQ((p[ka] - p[kb]) ** 2 + (p[ka + 1] - p[kb + 1]) ** 2 + (p[ka + 2] - p[kb + 2]) ** 2);
        const reach = col.type === 'sphere' ? col.r : Math.min(col.h[0], col.h[1], col.h[2]) + 0.05, ns = Math.max(1, Math.ceil(len / Math.max(0.03, 0.3 * reach)));
        for (let sI = 1; sI < ns; sI++) {           // interior samples (the end points are ordinary particles)
          const t = sI / ns, u = 1 - t, px = u * p[ka] + t * p[kb], py = u * p[ka + 1] + t * p[kb + 1], pz = u * p[ka + 2] + t * p[kb + 2];
          const pen = this._cq(col, px, py, pz, rr); if (pen <= 0) continue;
          this._applyVirtual(col, a, b, -1, u, t, 0, px, py, pz, this._qn[0], this._qn[1], this._qn[2], pen, h);
        }
      }
    }
    for (let e = 0; e < this.nct; e++) {
      const a = this.cta[e * 3], b = this.cta[e * 3 + 1], d = this.cta[e * 3 + 2]; if (anyA && asl[cmp[a]]) continue;
      const ka = a * 3, kb = b * 3, kd = d * 3, rr = this.ctr[e];
      const lox = Math.min(p[ka], p[kb], p[kd]) - rr, hix = Math.max(p[ka], p[kb], p[kd]) + rr, loy = Math.min(p[ka + 1], p[kb + 1], p[kd + 1]) - rr, hiy = Math.max(p[ka + 1], p[kb + 1], p[kd + 1]) + rr, loz = Math.min(p[ka + 2], p[kb + 2], p[kd + 2]) - rr, hiz = Math.max(p[ka + 2], p[kb + 2], p[kd + 2]) + rr;
      for (let c = 0; c < nc; c++) {
        const o = c * 6; if (hix < cu[o] || lox > cu[o + 3] || hiy < cu[o + 1] || loy > cu[o + 4] || hiz < cu[o + 2] || loz > cu[o + 5]) continue;
        const col = cols[c];
        if (col.type === 'sphere') {                // exact: closest point on the triangle to the sphere centre
          const bc = this._closestOnTri(col.c[0], col.c[1], col.c[2], ka, kb, kd); const u = bc[0], v = bc[1], w = bc[2];
          const px = u * p[ka] + v * p[kb] + w * p[kd], py = u * p[ka + 1] + v * p[kb + 1] + w * p[kd + 1], pz = u * p[ka + 2] + v * p[kb + 2] + w * p[kd + 2];
          const pen = this._cq(col, px, py, pz, rr); if (pen <= 0) continue;
          this._applyVirtual(col, a, b, d, u, v, w, px, py, pz, this._qn[0], this._qn[1], this._qn[2], pen, h);
        } else {                                    // box: lattice of sample points
          const reach = Math.min(col.h[0], col.h[1], col.h[2]) + 0.05, step = Math.max(0.03, 0.4 * reach);
          const e1 = SQ((p[kb] - p[ka]) ** 2 + (p[kb + 1] - p[ka + 1]) ** 2 + (p[kb + 2] - p[ka + 2]) ** 2), e2 = SQ((p[kd] - p[ka]) ** 2 + (p[kd + 1] - p[ka + 1]) ** 2 + (p[kd + 2] - p[ka + 2]) ** 2);
          const n1 = Math.max(1, Math.ceil(e1 / step)), n2 = Math.max(1, Math.ceil(e2 / step));
          for (let i = 0; i <= n1; i++) for (let j = 0; j <= n2; j++) {
            let v = i / n1, w = j / n2; if (v + w > 1) continue; const u = 1 - v - w; if (u > 0.999 || v > 0.999 || w > 0.999) continue;
            const px = u * p[ka] + v * p[kb] + w * p[kd], py = u * p[ka + 1] + v * p[kb + 1] + w * p[kd + 1], pz = u * p[ka + 2] + v * p[kb + 2] + w * p[kd + 2];
            const pen = this._cq(col, px, py, pz, rr); if (pen <= 0) continue;
            this._applyVirtual(col, a, b, d, u, v, w, px, py, pz, this._qn[0], this._qn[1], this._qn[2], pen, h);
          }
        }
      }
    }
  }

  // barycentric coordinates (into this._bc) of the point on triangle (ka,kb,kd) closest to (x,y,z)   [Ericson, RTCD 5.1.5]
  _closestOnTri(x, y, z, ka, kb, kd) {
    const p = this.pos, bc = this._bc;
    const ax = p[ka], ay = p[ka + 1], az = p[ka + 2], abx = p[kb] - ax, aby = p[kb + 1] - ay, abz = p[kb + 2] - az, acx = p[kd] - ax, acy = p[kd + 1] - ay, acz = p[kd + 2] - az;
    const apx = x - ax, apy = y - ay, apz = z - az, d1 = abx * apx + aby * apy + abz * apz, d2 = acx * apx + acy * apy + acz * apz;
    if (d1 <= 0 && d2 <= 0) { bc[0] = 1; bc[1] = 0; bc[2] = 0; return bc; }
    const bpx = x - p[kb], bpy = y - p[kb + 1], bpz = z - p[kb + 2], d3 = abx * bpx + aby * bpy + abz * bpz, d4 = acx * bpx + acy * bpy + acz * bpz;
    if (d3 >= 0 && d4 <= d3) { bc[0] = 0; bc[1] = 1; bc[2] = 0; return bc; }
    const vc = d1 * d4 - d3 * d2;
    if (vc <= 0 && d1 >= 0 && d3 <= 0) { const v = d1 / (d1 - d3); bc[0] = 1 - v; bc[1] = v; bc[2] = 0; return bc; }
    const cpx = x - p[kd], cpy = y - p[kd + 1], cpz = z - p[kd + 2], d5 = abx * cpx + aby * cpy + abz * cpz, d6 = acx * cpx + acy * cpy + acz * cpz;
    if (d6 >= 0 && d5 <= d6) { bc[0] = 0; bc[1] = 0; bc[2] = 1; return bc; }
    const vb = d5 * d2 - d1 * d6;
    if (vb <= 0 && d2 >= 0 && d6 <= 0) { const w = d2 / (d2 - d6); bc[0] = 1 - w; bc[1] = 0; bc[2] = w; return bc; }
    const va = d3 * d6 - d5 * d4;
    if (va <= 0 && (d4 - d3) >= 0 && (d5 - d6) >= 0) { const w = (d4 - d3) / ((d4 - d3) + (d5 - d6)); bc[0] = 0; bc[1] = 1 - w; bc[2] = w; return bc; }
    const den = 1 / (va + vb + vc), v = vb * den, w = vc * den; bc[0] = 1 - v - w; bc[1] = v; bc[2] = w; return bc;
  }

  _rot(qx, qy, qz, qw, vx, vy, vz, axis) { // rotate v by quaternion q, return one component
    const tx = 2 * (qy * vz - qz * vy), ty = 2 * (qz * vx - qx * vz), tz = 2 * (qx * vy - qy * vx);
    if (axis === 0) return vx + qw * tx + (qy * tz - qz * ty);
    if (axis === 1) return vy + qw * ty + (qz * tx - qx * tz);
    return vz + qw * tz + (qx * ty - qy * tx);
  }

  _pairs(h) {
    const n = this.n; if (n < 2 || this.nComp < 2) return;
    const p = this.pos, pr = this.prev, im = this.invM, rad = this.rad, comp = this.comp, HS = this._hHead.length, head = this._hHead;
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
          p[kj] -= dx * s * wj; p[kj + 1] -= dy * s * wj; p[kj + 2] -= dz * s * wj; cnt++;
          { // the push must not become velocity; contact is inelastic along the normal
            pr[k] += dx * s * wi; pr[k + 1] += dy * s * wi; pr[k + 2] += dz * s * wi; pr[kj] -= dx * s * wj; pr[kj + 1] -= dy * s * wj; pr[kj + 2] -= dz * s * wj;
            const nx = dx / d, ny = dy / d, nz = dz / d, vrn = (((p[k] - pr[k]) - (p[kj] - pr[kj])) * nx + ((p[k + 1] - pr[k + 1]) - (p[kj + 1] - pr[kj + 1])) * ny + ((p[k + 2] - pr[k + 2]) - (p[kj + 2] - pr[kj + 2])) * nz) / h;
            if (vrn < 0) { const dl = -vrn * h / ws; pr[k] -= nx * dl * wi; pr[k + 1] -= ny * dl * wi; pr[k + 2] -= nz * dl * wi; pr[kj] += nx * dl * wj; pr[kj + 1] += ny * dl * wj; pr[kj + 2] += nz * dl * wj; }
          }
          { // Coulomb friction on the relative tangential motion over the last substep
            const nx = dx / d, ny = dy / d, nz = dz / d, pen = R - d;
            let tx = (p[k] - pr[k]) - (p[kj] - pr[kj]), ty = (p[k + 1] - pr[k + 1]) - (p[kj + 1] - pr[kj + 1]), tz = (p[k + 2] - pr[k + 2]) - (p[kj + 2] - pr[kj + 2]);
            const dn = tx * nx + ty * ny + tz * nz; tx -= dn * nx; ty -= dn * ny; tz -= dn * nz;
            const tm = SQ(tx * tx + ty * ty + tz * tz);
            if (tm > 1e-12) { const lim = this.friction * pen, f = (tm < lim ? 1 : lim / tm) / ws; p[k] -= tx * f * wi; p[k + 1] -= ty * f * wi; p[k + 2] -= tz * f * wi; p[kj] += tx * f * wj; p[kj + 1] += ty * f * wj; p[kj + 2] += tz * f * wj; }
          } this.supNow[ci] = 1; this.supNow[comp[j]] = 1; if (this.nAsleep) { if (this.compAsleep[ci] || this.compAsleep[comp[j]]) this._wakeComp(ci), this._wakeComp(comp[j]); }
        }
      }
    }
    this.stats.pairContacts = cnt;
  }

  // velocity update, adaptive-initialisation bookkeeping, plasticity and fracture
  _finish(h, check) {
    const n = this.n, p = this.pos, pr = this.prev, v = this.vel, ih = 1 / h;
    const cv = this.compV, cm = this.compM, comp = this.comp, ms = this.mass, vm2 = this.maxSpeed * this.maxSpeed; cv.fill(0); cm.fill(0);
    const al = this.actList, na = this.nAct, cs = this.compSp; cs.fill(0);
    for (let q = 0; q < na; q++) {
      const i = al[q], k = i * 3, c = comp[i], m = ms[i];
      v[k] = (p[k] - pr[k]) * ih; v[k + 1] = (p[k + 1] - pr[k + 1]) * ih; v[k + 2] = (p[k + 2] - pr[k + 2]) * ih;
      const sp2 = v[k] * v[k] + v[k + 1] * v[k + 1] + v[k + 2] * v[k + 2];
      if (!(sp2 < 1e9)) { p[k] = pr[k]; p[k + 1] = pr[k + 1]; p[k + 2] = pr[k + 2]; v[k] = v[k + 1] = v[k + 2] = 0; this.nanGuard++; continue; }   // NaN / runaway: freeze the particle at its last good position
      if (sp2 > vm2) { const f = this.maxSpeed / SQ(sp2); v[k] *= f; v[k + 1] *= f; v[k + 2] *= f; p[k] = pr[k] + v[k] * h; p[k + 1] = pr[k + 1] + v[k + 1] * h; p[k + 2] = pr[k + 2] + v[k + 2] * h; }   // runaway guard
      const s2 = sp2; if (s2 > cs[c]) cs[c] = s2;
      cv[c * 3] += m * v[k]; cv[c * 3 + 1] += m * v[k + 1]; cv[c * 3 + 2] += m * v[k + 2]; cm[c] += m;
    }
    for (let c = 0; c < this.nComp; c++) { const m = cm[c] || 1; cv[c * 3] /= m; cv[c * 3 + 1] /= m; cv[c * 3 + 2] /= m; }
    this.supPrev.set(this.supNow); this.supNow.fill(0);
    for (let c = 0; c < this.nComp; c++) if (this.compPin[c]) this.supPrev[c] = 1;
    if (!check) return;
    const nd = this.nd, A = this.da, B = this.db, R = this.dRest, Y = this.dYield, F = this.dFrac, CR = this.dCrush, ACT = this.dAct, OV = this.dOver;
    let broke = false;
    const asl = this.compAsleep, cmp = this.comp, anyAsleep = this.nAsleep > 0;
    for (let c = 0; c < nd; c++) {
      if (ACT[c] === 0) continue;
      if (anyAsleep && asl[cmp[A[c]]]) continue;
      const ka = A[c] * 3, kb = B[c] * 3, dx = p[ka] - p[kb], dy = p[ka + 1] - p[kb + 1], dz = p[ka + 2] - p[kb + 2];
      const len = SQ(dx * dx + dy * dy + dz * dz), r0 = R[c], eps = (len - r0) / r0;
      const lim = eps > 0 ? F[c] : CR[c], ex_ = (eps > 0 ? eps : -eps) / lim;
      if (ex_ > 1) { OV[c]++; if (ex_ < this.hardFactor && OV[c] < this.persist) continue; } else { OV[c] = 0; }
      if (ex_ > 1) {
        ACT[c] = 0; this.nBroken++; broke = true; this._broke('distance', A[c], B[c], c);
        if (this.dSnap[c]) { const bay = this.dBay[c]; for (let q = 0; q < nd; q++) if (ACT[q] && this.dBay[q] === bay) { ACT[q] = 0; this.nBroken++; this._broke('distance', A[q], B[q], q); } }   // brittle snap: the whole cut section lets go
        continue;
      }
      const ae = eps < 0 ? -eps : eps;
      if (ae > Y[c]) R[c] = len - (eps < 0 ? -Y[c] : Y[c]) * r0;          // plastic flow: rest length follows, strain clamped to yield
    }
    const nw = this.nw;
    if (nw) {
      const WM = this.wMax, WA = this.wAct, WK = this.wK, WR = this.wR, WN = this.wN;
      for (let w = 0; w < nw; w++) {
        if (WA[w] === 0) continue;
        if (anyAsleep && asl[cmp[this.wa[w]]]) continue;
        const ka = this.wa[w] * 3, kb = this.wb[w] * 3;
        const cx = p[ka] - p[kb] - WR[w * 3], cy = p[ka + 1] - p[kb + 1] - WR[w * 3 + 1], cz = p[ka + 2] - p[kb + 2] - WR[w * 3 + 2], nx = WN[w * 3], ny = WN[w * 3 + 1], nz = WN[w * 3 + 2];
        let fail;
        if (nx === 0 && ny === 0 && nz === 0) fail = SQ(cx * cx + cy * cy + cz * cz) * WK[w] > WM[w];
        else {            // joint with a normal: tension and shear break it, compression does not (friction adds shear capacity)
          const cn = cx * nx + cy * ny + cz * nz, ten = cn < 0 ? -cn * WK[w] : 0, comp = cn > 0 ? cn * WK[w] : 0;
          const tx = cx - cn * nx, ty = cy - cn * ny, tz = cz - cn * nz, sh = SQ(tx * tx + ty * ty + tz * tz) * WK[w];
          fail = ten > WM[w] || sh > WM[w] * this.wSh[w] + this.friction * comp;
        }
        if (!fail) this.wOver[w] = 0;
        if (fail) { if (++this.wOver[w] < this.persist) continue; WA[w] = 0; this.nBroken++; broke = true; this._broke('weld', this.wa[w], this.wb[w], w); }
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
    this.compSp = new Float64Array(cnt); this.compAsleep = new Uint8Array(cnt); this.compSleepT = new Float64Array(cnt); this.nAsleep = 0; this.compV = new Float64Array(cnt * 3); this.compM = new Float64Array(cnt); this.compPin = new Uint8Array(cnt); this.supPrev = new Uint8Array(cnt); this.supNow = new Uint8Array(cnt);
    for (let i = 0; i < n; i++) if (this.pinned[i]) this.compPin[this.comp[i]] = 1;
    for (let c = 0; c < cnt; c++) this.supPrev[c] = this.compPin[c];
    this._buildAct();
  }
  componentCount() { if (this._compDirty) this._buildComponents(); return this.nComp; }
  // component sizes (particles) in id order; useful for "did a chunk separate"
  componentSizes() { if (this._compDirty) this._buildComponents(); const s = new Array(this.nComp).fill(0); for (let i = 0; i < this.n; i++) s[this.comp[i]]++; return s; }

  // ---------- sleeping (optional) ----------
  _buildAct() {
    const n = this.n; if (this.actList.length < n) this.actList = new Int32Array(this.cap);
    let m = 0; const asl = this.compAsleep, comp = this.comp, al = this.actList;
    const dd = this.dead; for (let i = 0; i < n; i++) if (!asl[comp[i]] && !dd[i]) al[m++] = i;
    this.nAct = m;
  }
  _wakeComp(c) { if (this.compAsleep[c]) { this.compAsleep[c] = 0; this.nAsleep--; this._actDirty = true; } this.compSleepT[c] = 0; }
  wakeAll() { this.compAsleep.fill(0); this.compSleepT.fill(0); this.nAsleep = 0; this._buildAct(); }
  wakeParticle(i) { this._wakeComp(this.comp[i]); this._buildAct(); this._actDirty = false; }
  _wakeScan() {   // a collider reaching a sleeping piece wakes it
    const cols = this.colliders; if (!cols.length) { if (this._actDirty) { this._buildAct(); this._actDirty = false; } return; }
    const p = this.pos, n = this.n, comp = this.comp, asl = this.compAsleep, R = this.maxRadius * 1.5;
    for (let c = 0; c < cols.length; c++) {
      const o = cols[c], e = (o.type === 'sphere' ? o.r : Math.hypot(o.h[0], o.h[1], o.h[2])) + R, cx = o.c[0], cy = o.c[1], cz = o.c[2];
      for (let i = 0; i < n; i++) { if (!asl[comp[i]]) continue; const k = i * 3; if (Math.abs(p[k] - cx) < e && Math.abs(p[k + 1] - cy) < e && Math.abs(p[k + 2] - cz) < e) this._wakeComp(comp[i]); }
    }
    if (this._actDirty) { this._buildAct(); this._actDirty = false; }
  }
  _sleepUpdate(dt) {
    const nC = this.nComp, cs = this.compSp, st = this.compSleepT, asl = this.compAsleep, sup = this.supPrev, lim = this.sleepSpeed * this.sleepSpeed, ex = this.ext, comp = this.comp;
    if (!this._forced || this._forced.length < nC) this._forced = new Uint8Array(nC); this._forced.fill(0);
    for (let i = 0; i < this.n; i++) { const k = i * 3; if (ex[k] !== 0 || ex[k + 1] !== 0 || ex[k + 2] !== 0) this._forced[comp[i]] = 1; }
    let changed = false;
    for (let c = 0; c < nC; c++) {
      if (asl[c]) continue;
      if (sup[c] && cs[c] < lim && !this._forced[c] && !(this.nTri && this.wind)) { st[c] += dt; if (st[c] >= this.sleepTime) { asl[c] = 1; this.nAsleep++; changed = true; } } else st[c] = 0;
    }
    if (changed) { const v = this.vel, n = this.n; for (let i = 0; i < n; i++) if (asl[comp[i]]) { v[i * 3] = v[i * 3 + 1] = v[i * 3 + 2] = 0; } this._buildAct(); }
  }

  // ---------- pieces (for handing broken chunks to a rigid-body engine) ----------
  // One entry per connected piece: {comp, count, mass, com, vel, lo, hi, pinned, supported}. Unpinned, unsupported pieces are
  // in free flight and are the ones a host would convert into rigid bodies.
  pieces() {
    if (this._compDirty) this._buildComponents();
    const nC = this.nComp, out = new Array(nC), p = this.pos, v = this.vel;
    for (let c = 0; c < nC; c++) out[c] = { comp: c, count: 0, mass: 0, com: [0, 0, 0], vel: [0, 0, 0], lo: [Infinity, Infinity, Infinity], hi: [-Infinity, -Infinity, -Infinity], pinned: !!this.compPin[c], supported: !!this.supPrev[c] };
    for (let i = 0; i < this.n; i++) {
      if (this.dead[i]) continue; const o = out[this.comp[i]], m = this.mass[i], k = i * 3; o.count++; o.mass += m;
      for (let a = 0; a < 3; a++) { o.com[a] += m * p[k + a]; o.vel[a] += m * v[k + a]; if (p[k + a] < o.lo[a]) o.lo[a] = p[k + a]; if (p[k + a] > o.hi[a]) o.hi[a] = p[k + a]; }
    }
    for (const o of out) if (o.mass > 0) for (let a = 0; a < 3; a++) { o.com[a] /= o.mass; o.vel[a] /= o.mass; }
    return out.filter(o => o.count > 0);
  }
  // delete a piece from the simulation (its constraints stop, its particles stop colliding and being drawn)
  removePiece(comp) {
    const cmp = this.comp;
    for (let c = 0; c < this.nd; c++) if (cmp[this.da[c]] === comp) this.dAct[c] = 0;
    for (let w = 0; w < this.nw; w++) if (cmp[this.wa[w]] === comp) this.wAct[w] = 0;
    for (let t = 0; t < this.nt; t++) if (cmp[this.tv[t * 4]] === comp) this.tAct[t] = 0;
    for (let i = 0; i < this.n; i++) if (cmp[i] === comp) { this.dead[i] = 1; this.invM[i] = 0; this.pinned[i] = 1; this.vel[i * 3] = this.vel[i * 3 + 1] = this.vel[i * 3 + 2] = 0; }
    this._compDirty = true;
  }

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
      w.addCollisionTri(S0.k[k], S0.k[k2], S1.k[k2], 0.005); w.addCollisionTri(S0.k[k], S1.k[k2], S1.k[k], 0.005);                // the four faces of the bay are the collision skin
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
    const c = w.addDistance(ids[i], ids[i + 1], mat, A), dl = w.dRest[c]; len += dl; w.addCollisionEdge(ids[i], ids[i + 1], r);
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
  const stone = o.mat, mortar = o.mortar, [bx, by, bz] = o.size, [nx, ny, nz] = o.counts, O = o.origin.slice(), gap = o.joint ?? 0.01;
  const blocks = [], key = new Map();
  const rad = o.radius ?? Math.min(bx, by, bz) * 0.12;
  if (o.groundY !== undefined) O[1] = o.groundY + rad + 1e-4;     // rest the lowest course on a flat ground at height groundY (a 1 mm drop already overloads the joints)
  for (let k = 0; k < nz; k++) for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
    const grp = w.newGroup(), base = [O[0] + i * bx, O[1] + j * by, O[2] + k * bz], c = [], nb0 = w.nd;
    for (let q = 0; q < 8; q++) { const px = q & 1, py = (q >> 1) & 1, pz = (q >> 2) & 1; c.push(w.addParticle(base[0] + px * bx, base[1] + py * by, base[2] + pz * bz, 0, rad, grp, stone.drag)); }
    const vol = bx * by * bz, m = stone.density * vol; for (const q of c) w.addMass(q, m / 8);
    const A = Math.min(bx * by, by * bz, bx * bz) * 0.25;
    for (let q = 0; q < 8; q++) for (let r = q + 1; r < 8; r++) { const d = (q ^ r); if (d === 1 || d === 2 || d === 4 || d === 3 || d === 5 || d === 6) w.addDistance(c[q], c[r], stone, A); }
    if (o.volume) for (const [p0, p1, p2, p3] of [[0, 1, 2, 4], [3, 1, 2, 7], [5, 1, 4, 7], [6, 2, 4, 7], [1, 2, 4, 7]]) w.addTetra(c[p0], c[p1], c[p2], c[p3], stone);   // optional volume preservation
    if (!o.breakBlocks) for (let q = nb0; q < w.nd; q++) { w.dFrac[q] = Infinity; w.dCrush[q] = Infinity; }   // by default the stone itself does not fracture: the mortar joints do
    blocks.push({ i, j, k, c, grp }); key.set(i + ',' + j + ',' + k, blocks[blocks.length - 1]);
  }
  const weld = (A, B, qa, qb, area, nrm) => { w.addWeld(A.c[qa], B.c[qb], mortar, area, gap, { normal: nrm, k: Math.min(mortar.youngs * area / gap, o.weldK ?? 3.2e8 * area) }); };   // joint stiffness capped at 3.2e8 N/m per m2 of bond (about 1e7 N/m per 0.03 m2): position noise x stiffness must stay below the break force
  for (const B of blocks) {
    const R = key.get((B.i + 1) + ',' + B.j + ',' + B.k), U = key.get(B.i + ',' + (B.j + 1) + ',' + B.k), F = key.get(B.i + ',' + B.j + ',' + (B.k + 1));
    if (R) for (let q = 0; q < 8; q++) if (q & 1) weld(B, R, q, q & ~1, by * bz / 4, [1, 0, 0]);
    if (U) for (let q = 0; q < 8; q++) if (q & 2) weld(B, U, q, q & ~2, bx * bz / 4, [0, 1, 0]);
    if (F) for (let q = 0; q < 8; q++) if (q & 4) weld(B, F, q, q & ~4, bx * by / 4, [0, 0, 1]);
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
