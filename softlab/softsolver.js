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
    scatter: d.scatter ?? 0.05,                    // +/- relative scatter of strength per constraint (seeded)
    shear: youngs / (2 * (1 + poisson)),
    bulk: youngs / (3 * (1 - 2 * poisson)),
    yieldStrain: yieldS / youngs, fracStrain: fracS / youngs,
    beta: (d.damping ?? 0.1) * BETA_PER_DAMP, drag: (d.damping ?? 0.1) * DRAG_PER_DAMP,
  });
}

// Reference material descriptors (rough, ranged for game use; bending/tension strengths in Pa)
export const MATERIALS = {
  wood:   { name: 'wood',   density: 600,  youngs: 1.0e10, yield: 4.0e7, fracture: 6.0e7, damping: 0.2 },
  steel:  { name: 'steel',  density: 7800, youngs: 2.0e11, yield: 2.5e8, fracture: 4.0e8, damping: 0.1 },
  rope:   { name: 'rope',   density: 900,  youngs: 5.0e8,  yield: 1.0e12, fracture: 8.0e7, damping: 0.4 },
  cloth:  { name: 'cloth',  density: 400,  youngs: 5.0e7,  yield: 1.0e12, fracture: 5.0e7, damping: 0.5 },
  stone:  { name: 'stone',  density: 2500, youngs: 3.0e10, yield: 1.0e13, fracture: 5.0e6, damping: 0.2 },
  mortar: { name: 'mortar', density: 1900, youngs: 1.0e9,  yield: 1.0e13, fracture: 3.0e5, damping: 0.2 },
};

const SQ = Math.sqrt;

export class SoftWorld {
  constructor(o = {}) {
    this.gravity = o.gravity ? o.gravity.slice() : [0, -9.81, 0];
    this.substeps = o.substeps ?? 8;
    this.iterations = o.iterations ?? 1;
    this.seed = o.seed ?? 1;
    this.rng = mulberry32(this.seed);
    this.friction = o.friction ?? 0.6;
    this.pairInterval = o.pairInterval ?? 2;        // particle-particle contact pass every N substeps (0 = off)
    this.groundMargin = 0.0;
    this.heightfield = null;                        // (x,z) => height
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
    this.nextGroup = 1; this.nBroken = 0;
    this._compDirty = true; this.comp = new Int32Array(0); this.nComp = 0;
    this._hHead = new Int32Array(8192); this._hNext = new Int32Array(0);
    this._sweep = 0; this._hCache = -1; this.maxRadius = 0.01;
    this.stats = { contacts: 0, pairContacts: 0 };
  }

  // ---------- storage ----------
  _allocP(c) {
    const g = (old, k, T) => { const a = new T(c * k); if (old) a.set(old.subarray(0, Math.min(old.length, a.length))); return a; };
    this.pos = g(this.pos, 3, Float64Array); this.prev = g(this.prev, 3, Float64Array); this.vel = g(this.vel, 3, Float64Array);
    this.ext = g(this.ext, 3, Float64Array); this.aeroF = g(this.aeroF, 3, Float64Array);
    this.mass = g(this.mass, 1, Float64Array); this.invM = g(this.invM, 1, Float64Array); this.rad = g(this.rad, 1, Float64Array);
    this.drag = g(this.drag, 1, Float64Array); this.group = g(this.group, 1, Int32Array); this.pinned = g(this.pinned, 1, Uint8Array);
    this.cap = c;
  }
  _allocD(c) {
    const g = (old, T) => { const a = new T(c); if (old) a.set(old.subarray(0, Math.min(old.length, a.length))); return a; };
    this.da = g(this.da, Int32Array); this.db = g(this.db, Int32Array); this.dRest = g(this.dRest, Float64Array);
    this.dAlpha = g(this.dAlpha, Float64Array); this.dBeta = g(this.dBeta, Float64Array); this.dYield = g(this.dYield, Float64Array);
    this.dFrac = g(this.dFrac, Float64Array); this.dAct = g(this.dAct, Uint8Array); this.dLam = g(this.dLam, Float64Array);
    this.dK = g(this.dK, Float64Array); this.dTag = g(this.dTag, Int32Array);
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
    this._compDirty = true;
    return i;
  }
  addMass(i, m) { this.mass[i] += m; this.invM[i] = this.pinned[i] ? 0 : 1 / this.mass[i]; }
  pin(i, on = true) { this.pinned[i] = on ? 1 : 0; this.invM[i] = on || this.mass[i] <= 0 ? 0 : 1 / this.mass[i]; }
  newGroup() { return this.nextGroup++; }

  addDistance(a, b, mat, area, o = {}) {
    if (this.nd >= this.capD) this._allocD(this.capD * 2);
    const c = this.nd++, p = this.pos;
    const dx = p[a * 3] - p[b * 3], dy = p[a * 3 + 1] - p[b * 3 + 1], dz = p[a * 3 + 2] - p[b * 3 + 2];
    const L = SQ(dx * dx + dy * dy + dz * dz), rest = o.rest ?? L;
    const k = mat.youngs * area / Math.max(rest, 1e-9);
    const sc = 1 + mat.scatter * (2 * this.rng() - 1);
    this.da[c] = a; this.db[c] = b; this.dRest[c] = rest; this.dK[c] = k; this.dAlpha[c] = 1 / k;
    this.dBeta[c] = mat.beta; this.dYield[c] = mat.yieldStrain * sc; this.dFrac[c] = (o.fracStrain ?? mat.fracStrain) * sc;
    this.dAct[c] = 1; this.dLam[c] = 0; this.dTag[c] = o.tag ?? 0;
    this._compDirty = true;
    return c;
  }
  addTetra(a, b, c, d, mat, o = {}) {
    if (this.nt >= this.capT) this._allocT(this.capT * 2);
    const t = this.nt++, p = this.pos;
    const V = this._vol(a, b, c, d);
    this.tv[t * 4] = a; this.tv[t * 4 + 1] = b; this.tv[t * 4 + 2] = c; this.tv[t * 4 + 3] = d;
    this.tV0[t] = V; this.tAlpha[t] = Math.abs(V) / (o.bulk ?? mat.bulk); this.tAct[t] = 1; this.tLam[t] = 0;
    this._compDirty = true;
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
    this._compDirty = true;
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
  step(dt) {
    const S = this.substeps, h = dt / S, g = this.gravity, n = this.n;
    if (this._compDirty) this._buildComponents();
    this._aero();
    for (let s = 0; s < S; s++) {
      this._predict(h, g);
      this._zeroLam();
      for (let it = 0; it < this.iterations; it++) {
        const rev = (this._sweep++ & 1) === 1;
        this._solveWelds(h, rev); this._solveTets(h, rev); this._solveDistance(h, rev);
      }
      this._collide(h);
      if (this.pairInterval > 0 && ((s + 1) % this.pairInterval === 0 || s === S - 1)) this._pairs(h);
      this._finish(h);
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

  _predict(h, g) {
    const n = this.n, p = this.pos, pr = this.prev, v = this.vel, im = this.invM, ex = this.ext, ae = this.aeroF, dr = this.drag;
    const gx = g[0], gy = g[1], gz = g[2], useA = this.nTri > 0 && this.wind;
    for (let i = 0; i < n; i++) {
      const k = i * 3; pr[k] = p[k]; pr[k + 1] = p[k + 1]; pr[k + 2] = p[k + 2];
      const w = im[i]; if (w === 0) { v[k] = v[k + 1] = v[k + 2] = 0; continue; }
      let ax = gx + ex[k] * w, ay = gy + ex[k + 1] * w, az = gz + ex[k + 2] * w;
      if (useA) { ax += ae[k] * w; ay += ae[k + 1] * w; az += ae[k + 2] * w; }
      const dm = 1 / (1 + dr[i] * h);
      v[k] = (v[k] + h * ax) * dm; v[k + 1] = (v[k + 1] + h * ay) * dm; v[k + 2] = (v[k + 2] + h * az) * dm;
      p[k] += h * v[k]; p[k + 1] += h * v[k + 1]; p[k + 2] += h * v[k + 2];
    }
  }
  _zeroLam() {
    this.dLam.fill(0, 0, this.nd); this.tLam.fill(0, 0, this.nt); this.wLam.fill(0, 0, this.nw * 3);
  }

  _solveDistance(h, rev) {
    const nd = this.nd, p = this.pos, pr = this.prev, im = this.invM, A = this.da, B = this.db, R = this.dRest, AL = this.dAlpha, BE = this.dBeta, ACT = this.dAct, LAM = this.dLam;
    const h2 = h * h, ih = 1 / h;
    for (let q = 0; q < nd; q++) {
      const c = rev ? nd - 1 - q : q; if (ACT[c] === 0) continue;
      const a = A[c], b = B[c], wa = im[a], wb = im[b], ws = wa + wb; if (ws === 0) continue;
      const ka = a * 3, kb = b * 3;
      const dx = p[ka] - p[kb], dy = p[ka + 1] - p[kb + 1], dz = p[ka + 2] - p[kb + 2];
      const len = SQ(dx * dx + dy * dy + dz * dz); if (len < 1e-12) continue;
      const il = 1 / len, nx = dx * il, ny = dy * il, nz = dz * il;
      const at = AL[c] / h2, gm = AL[c] * BE[c] * ih;        // gamma = alphaTilde * beta / h (Macklin XPBD damping)
      const rel = ((p[ka] - pr[ka]) - (p[kb] - pr[kb])) * nx + ((p[ka + 1] - pr[ka + 1]) - (p[kb + 1] - pr[kb + 1])) * ny + ((p[ka + 2] - pr[ka + 2]) - (p[kb + 2] - pr[kb + 2])) * nz;
      const dl = (-(len - R[c]) - at * LAM[c] - gm * rel) / ((1 + gm) * ws + at);
      LAM[c] += dl;
      const sa = dl * wa, sb = dl * wb;
      p[ka] += sa * nx; p[ka + 1] += sa * ny; p[ka + 2] += sa * nz;
      p[kb] -= sb * nx; p[kb + 1] -= sb * ny; p[kb + 2] -= sb * nz;
    }
  }

  _solveTets(h, rev) {
    const nt = this.nt; if (!nt) return;
    const p = this.pos, im = this.invM, V = this.tv, V0 = this.tV0, AL = this.tAlpha, ACT = this.tAct, LAM = this.tLam, h2 = h * h;
    for (let q = 0; q < nt; q++) {
      const t = rev ? nt - 1 - q : q; if (ACT[t] === 0) continue;
      const a = V[t * 4] * 3, b = V[t * 4 + 1] * 3, c = V[t * 4 + 2] * 3, d = V[t * 4 + 3] * 3;
      const bx = p[b] - p[a], by = p[b + 1] - p[a + 1], bz = p[b + 2] - p[a + 2];
      const cx = p[c] - p[a], cy = p[c + 1] - p[a + 1], cz = p[c + 2] - p[a + 2];
      const dx = p[d] - p[a], dy = p[d + 1] - p[a + 1], dz = p[d + 2] - p[a + 2];
      // gradients of V wrt b, c, d
      const gbx = (cy * dz - cz * dy) / 6, gby = (cz * dx - cx * dz) / 6, gbz = (cx * dy - cy * dx) / 6;
      const gcx = (dy * bz - dz * by) / 6, gcy = (dz * bx - dx * bz) / 6, gcz = (dx * by - dy * bx) / 6;
      const gdx = (by * cz - bz * cy) / 6, gdy = (bz * cx - bx * cz) / 6, gdz = (bx * cy - by * cx) / 6;
      const gax = -(gbx + gcx + gdx), gay = -(gby + gcy + gdy), gaz = -(gbz + gcz + gdz);
      const wa = im[a / 3], wb = im[b / 3], wc = im[c / 3], wd = im[d / 3];
      const den = wa * (gax * gax + gay * gay + gaz * gaz) + wb * (gbx * gbx + gby * gby + gbz * gbz) + wc * (gcx * gcx + gcy * gcy + gcz * gcz) + wd * (gdx * gdx + gdy * gdy + gdz * gdz);
      const Cv = (bx * (cy * dz - cz * dy) + by * (cz * dx - cx * dz) + bz * (cx * dy - cy * dx)) / 6 - V0[t];
      const at = AL[t] / h2, dl = (-Cv - at * LAM[t]) / (den + at); LAM[t] += dl;
      p[a] += dl * wa * gax; p[a + 1] += dl * wa * gay; p[a + 2] += dl * wa * gaz;
      p[b] += dl * wb * gbx; p[b + 1] += dl * wb * gby; p[b + 2] += dl * wb * gbz;
      p[c] += dl * wc * gcx; p[c + 1] += dl * wc * gcy; p[c + 2] += dl * wc * gcz;
      p[d] += dl * wd * gdx; p[d + 1] += dl * wd * gdy; p[d + 2] += dl * wd * gdz;
    }
  }

  _solveWelds(h, rev) {
    const nw = this.nw; if (!nw) return;
    const p = this.pos, pr = this.prev, im = this.invM, A = this.wa, B = this.wb, R = this.wR, AL = this.wAlpha, BE = this.wBeta, ACT = this.wAct, LAM = this.wLam, h2 = h * h, ih = 1 / h;
    for (let q = 0; q < nw; q++) {
      const w = rev ? nw - 1 - q : q; if (ACT[w] === 0) continue;
      const a = A[w], b = B[w], wa = im[a], wb = im[b], ws = wa + wb; if (ws === 0) continue;
      const ka = a * 3, kb = b * 3, at = AL[w] / h2, gm = AL[w] * BE[w] * ih, den = (1 + gm) * ws + at;
      for (let k = 0; k < 3; k++) {
        const C = p[ka + k] - p[kb + k] - R[w * 3 + k];
        const rel = (p[ka + k] - pr[ka + k]) - (p[kb + k] - pr[kb + k]);
        const dl = (-C - at * LAM[w * 3 + k] - gm * rel) / den; LAM[w * 3 + k] += dl;
        p[ka + k] += dl * wa; p[kb + k] -= dl * wb;
      }
    }
  }

  // ---------- contacts ----------
  _collide(h) {
    const n = this.n, p = this.pos, pr = this.prev, im = this.invM, rad = this.rad, hf = this.heightfield, mu = this.friction;
    const cols = this.colliders, nc = cols.length; let contacts = 0;
    for (let i = 0; i < n; i++) {
      if (im[i] === 0) continue;
      const k = i * 3, r = rad[i];
      if (hf) {
        const x = p[k], z = p[k + 2], gh = hf(x, z), pen = gh + r - p[k + 1];
        if (pen > 0) {
          contacts++;
          // normal from central differences (only on contact)
          const e = 0.05, gx = (hf(x + e, z) - hf(x - e, z)) / (2 * e), gz = (hf(x, z + e) - hf(x, z - e)) / (2 * e);
          const il = 1 / SQ(gx * gx + gz * gz + 1), nx = -gx * il, ny = il, nz = -gz * il;
          const d = pen * ny; // move along normal so the particle ends at distance r above the surface (vertical pen -> normal pen)
          p[k] += nx * d; p[k + 1] += ny * d; p[k + 2] += nz * d;
          this._friction(k, nx, ny, nz, d, mu, 0, 0, 0, h);
        }
      }
      for (let c = 0; c < nc; c++) this._colliderContact(cols[c], i, k, r, mu, h) && contacts++;
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
    const next = this._hNext, cell = 2 * this.maxRadius, ic = 1 / cell; head.fill(-1);
    const hash = (x, y, z) => ((x * 73856093) ^ (y * 19349663) ^ (z * 83492791)) & (HS - 1);
    for (let i = 0; i < n; i++) { const k = i * 3, hh = hash(Math.floor(p[k] * ic), Math.floor(p[k + 1] * ic), Math.floor(p[k + 2] * ic)); next[i] = head[hh]; head[hh] = i; }
    let cnt = 0;
    for (let i = 0; i < n; i++) {
      const k = i * 3, cx = Math.floor(p[k] * ic), cy = Math.floor(p[k + 1] * ic), cz = Math.floor(p[k + 2] * ic), wi = im[i], ci = comp[i];
      for (let ox = -1; ox <= 1; ox++) for (let oy = -1; oy <= 1; oy++) for (let oz = -1; oz <= 1; oz++) {
        for (let j = head[hash(cx + ox, cy + oy, cz + oz)]; j >= 0; j = next[j]) {
          if (j <= i || comp[j] === ci) continue;
          const wj = im[j], ws = wi + wj; if (ws === 0) continue;
          const kj = j * 3, dx = p[k] - p[kj], dy = p[k + 1] - p[kj + 1], dz = p[k + 2] - p[kj + 2], R = rad[i] + rad[j], d2 = dx * dx + dy * dy + dz * dz;
          if (d2 >= R * R || d2 < 1e-14) continue;
          const d = SQ(d2), s = (R - d) / (d * ws);
          p[k] += dx * s * wi; p[k + 1] += dy * s * wi; p[k + 2] += dz * s * wi;
          p[kj] -= dx * s * wj; p[kj + 1] -= dy * s * wj; p[kj + 2] -= dz * s * wj; cnt++;
        }
      }
    }
    this.stats.pairContacts = cnt;
  }

  // velocity update, plasticity and fracture
  _finish(h) {
    const n = this.n, p = this.pos, pr = this.prev, v = this.vel, ih = 1 / h;
    for (let i = 0; i < n * 3; i++) v[i] = (p[i] - pr[i]) * ih;
    const nd = this.nd, A = this.da, B = this.db, R = this.dRest, Y = this.dYield, F = this.dFrac, ACT = this.dAct;
    let broke = false;
    for (let c = 0; c < nd; c++) {
      if (ACT[c] === 0) continue;
      const ka = A[c] * 3, kb = B[c] * 3, dx = p[ka] - p[kb], dy = p[ka + 1] - p[kb + 1], dz = p[ka + 2] - p[kb + 2];
      const len = SQ(dx * dx + dy * dy + dz * dz), r0 = R[c], eps = (len - r0) / r0, ae = eps < 0 ? -eps : eps;
      if (ae > F[c]) { ACT[c] = 0; this.nBroken++; broke = true; this._broke('distance', A[c], B[c], c); continue; }
      if (ae > Y[c]) R[c] = len - (eps < 0 ? -Y[c] : Y[c]) * r0;          // plastic flow: rest length follows, strain clamped to yield
    }
    const nw = this.nw;
    if (nw) {
      const WL = this.wLam, WM = this.wMax, WA = this.wAct, h2 = h * h;
      for (let w = 0; w < nw; w++) {
        if (WA[w] === 0) continue;
        const fx = WL[w * 3], fy = WL[w * 3 + 1], fz = WL[w * 3 + 2], f = SQ(fx * fx + fy * fy + fz * fz) / h2;
        if (f > WM[w]) { WA[w] = 0; this.nBroken++; broke = true; this._broke('weld', this.wa[w], this.wb[w], w); }
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
  }
  componentCount() { if (this._compDirty) this._buildComponents(); return this.nComp; }
  // component sizes (particles) in id order; useful for "did a chunk separate"
  componentSizes() { if (this._compDirty) this._buildComponents(); const s = new Array(this.nComp).fill(0); for (let i = 0; i < this.n; i++) s[this.comp[i]]++; return s; }

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
  const seg = o.segments || Math.max(1, Math.round(L / Math.max(W, H, 1e-6)));
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
  const dArea = (span) => { const d = SQ(dx * dx + span * span); return Math.max(A * 0.02, G * kappa * A * d * d * d / (2 * mat.youngs * span * span * dx)); };
  const secArea = A * 0.5;
  const sectionBars = (S) => {
    for (let k = 0; k < 4; k++) { w.addDistance(S.k[k], S.k[(k + 1) % 4], mat, secArea, { tag: 1 }); w.addDistance(S.c, S.k[k], mat, secArea, { tag: 1 }); }
    w.addDistance(S.k[0], S.k[2], mat, secArea, { tag: 1 }); w.addDistance(S.k[1], S.k[3], mat, secArea, { tag: 1 });
  };
  if (!o.start) sectionBars(sections[0]);
  for (let i = 0; i < seg; i++) {
    const S0 = sections[i], S1 = sections[i + 1], par = i & 1;
    for (let k = 0; k < 4; k++) w.addDistance(S0.k[k], S1.k[k], mat, Ac, { tag: 0 });
    w.addDistance(S0.c, S1.c, mat, Acentre, { tag: 0 });
    for (let k = 0; k < 4; k++) {                                  // face diagonals, alternating direction per bay
      const k2 = (k + 1) % 4, span = (k === 0 || k === 2) ? W : H;
      if (par) w.addDistance(S0.k[k2], S1.k[k], mat, dArea(span), { tag: 2 }); else w.addDistance(S0.k[k], S1.k[k2], mat, dArea(span), { tag: 2 });
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
  const L = SQ(dot(sub(b, a), sub(b, a))), len = L * (o.slack ?? 1), dl = len / seg, group = o.group ?? w.newGroup();
  const ids = [];
  for (let i = 0; i <= seg; i++) {
    const f = i / seg, p = add(a, mul(sub(b, a), f)); const sag = o.sag ? -4 * o.sag * f * (1 - f) : 0;
    ids.push(w.addParticle(p[0], p[1] + sag, p[2], 0, r, group, mat.drag));
  }
  for (let i = 0; i < seg; i++) { w.addDistance(ids[i], ids[i + 1], mat, A, { rest: dl }); const m = mat.density * A * dl; w.addMass(ids[i], m / 2); w.addMass(ids[i + 1], m / 2); }
  if (o.pin === 'start' || o.pin === 'both') w.pin(ids[0]); if (o.pin === 'end' || o.pin === 'both') w.pin(ids[seg]);
  return { ids, length: len, group, segLen: dl };
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
    if (i + 2 < nu) bar(id(i, j), id(i + 2, j), 0.05); if (j + 2 < nv) bar(id(i, j), id(i, j + 2), 0.05);
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

// Masonry-like block cluster: nx*ny*nz stacked blocks (stack bond). Each block = 8 corner particles, 18 stone bars and
// 5 volume tets (so it is a stiff deformable chunk). Facing corners of neighbouring blocks are held by mortar welds that
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
    for (const [p0, p1, p2, p3] of [[0, 1, 2, 4], [3, 1, 2, 7], [5, 1, 4, 7], [6, 2, 4, 7], [1, 2, 4, 7]]) w.addTetra(c[p0], c[p1], c[p2], c[p3], stone);
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
