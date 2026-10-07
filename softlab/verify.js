// verify.js - headless quantitative verification of softsolver.js against analytical results.
//   node softlab/verify.js            (all tests, prints a table and writes verify-results.json)
//   node softlab/verify.js --quick    (shorter runs)
// Exit code 0 only if every test passes. Numbers are printed as measured; nothing is tuned per test beyond the
// documented material/geometry of each scenario.
import { SoftWorld, makeMaterial, MATERIALS, buildBeam, buildRope, buildCloth, buildBlockCluster, buildJelly } from './softsolver.js';
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const QUICK = process.argv.includes('--quick');
const results = [];
const G = 9.81;
const fmt = (x, d = 3) => (Math.abs(x) >= 1e4 || (Math.abs(x) < 1e-3 && x !== 0) ? x.toExponential(d - 1) : x.toFixed(d));
function report(name, pass, lines, data = {}) { results.push({ name, pass, lines, data }); console.log(`\n[${pass ? 'PASS' : 'FAIL'}] ${name}`); for (const l of lines) console.log('   ' + l); }

// ---------------------------------------------------------------- shared cantilever scenario
const BEAM = { L: 1.2, W: 0.1, H: 0.1 };               // slenderness L/h = 12
const woodElastic = (extra = {}) => makeMaterial({ ...MATERIALS.wood, yield: 1e12, fracture: 1e12, crush: 1e12, snap: false, damping: 1.0, scatter: 0, ...extra });
const I_BEAM = BEAM.W * BEAM.H ** 3 / 12;
function ebTip(mat, L = BEAM.L) { const q = mat.density * BEAM.W * BEAM.H * G; return q * L ** 4 / (8 * mat.youngs * I_BEAM); }

function runCantilever({ hz, substepHz = 480, seconds, mat, L = BEAM.L, iterations = 1, fixedSubsteps = 0 }) {
  const w = new SoftWorld({ substepHz: fixedSubsteps ? 0 : substepHz, substeps: fixedSubsteps || 8, iterations });
  const b = buildBeam(w, { a: [0, 5, 0], b: [L, 5, 0], width: BEAM.W, height: BEAM.H, mat, pin: 'start' });
  const dt = 1 / hz, trace = [];
  const steps = Math.round(seconds * hz);
  for (let i = 0; i < steps; i++) { w.step(dt); if ((i + 1) % Math.round(hz / 2) === 0) trace.push([(i + 1) * dt, 5 - w.pos[b.tip.c * 3 + 1]]); }
  return { w, b, trace, tip: 5 - w.pos[b.tip.c * 3 + 1] };
}

// ---------------------------------------------------------------- (1) cantilever vs Euler-Bernoulli
{
  const mat = woodElastic();
  const eb = ebTip(mat);
  const T = QUICK ? 12 : 30;
  const r = runCantilever({ hz: 60, seconds: T, mat });
  // Timoshenko shear correction for the same load (uniform q): add q L^2 / (2 kappa G A)
  const q = mat.density * BEAM.W * BEAM.H * G, shear = q * BEAM.L ** 2 / (2 * (5 / 6) * mat.shear * BEAM.W * BEAM.H);
  const err = (r.tip - eb) / eb;
  const settle = r.trace.find(([t, d]) => Math.abs(d - r.tip) < 0.05 * eb);
  report('(1) cantilever tip deflection vs Euler-Bernoulli', Math.abs(err) <= 0.10, [
    `beam ${BEAM.L} m x ${BEAM.W} x ${BEAM.H} m wood (E=${fmt(mat.youngs)} Pa, rho=${mat.density}), ${r.b.segments} bays, ${r.w.n} particles, ${r.w.nd} bars, root pinned`,
    `analytical (EB, self weight) tip = ${fmt(eb * 1000)} mm   (Timoshenko with shear = ${fmt((eb + shear) * 1000)} mm)`,
    `simulated tip after ${T} s = ${fmt(r.tip * 1000)} mm   error vs EB = ${fmt(err * 100, 2)} %   (vs Timoshenko ${fmt((r.tip - eb - shear) / (eb + shear) * 100, 2)} %)`,
    `trace (s:mm) ${r.trace.filter((_, i) => i % 6 === 5).map(([t, d]) => t.toFixed(0) + ':' + fmt(d * 1000, 3)).join('  ')}`,
    `time to within 5% of the final value: ${settle ? settle[0].toFixed(1) + ' s' : 'n/a'}`,
  ], { eb, tip: r.tip, err });
  // a soft variant (large, visible deflection) to check the formula is not a small-number accident
  const matS = woodElastic({ youngs: 2e7 }), ebS = ebTip(matS), rS = runCantilever({ hz: 60, seconds: QUICK ? 12 : 30, mat: matS });
  report('(1a) same cantilever, soft material (E=2e7 Pa, large deflection)', Math.abs(rS.tip - ebS) / ebS <= 0.10, [`EB tip = ${fmt(ebS * 1000)} mm (${fmt(ebS / BEAM.L * 100, 2)} % of span), simulated ${fmt(rS.tip * 1000)} mm, error ${fmt((rS.tip - ebS) / ebS * 100, 2)} %`]);
  // longer / more slender beam shows the convergence limit honestly
  const L2 = 1.6, mat2 = woodElastic();
  const r2 = runCantilever({ hz: 60, seconds: QUICK ? 12 : 40, mat: mat2, L: L2 });
  const eb2 = ebTip(mat2, L2);
  report('(1b) informational: L/h=16 cantilever, same solver settings', true, [
    `EB tip = ${fmt(eb2 * 1000)} mm, simulated after ${QUICK ? 12 : 40} s = ${fmt(r2.tip * 1000)} mm, ratio ${fmt(r2.tip / eb2, 3)}`,
    `trace ratio (s:ratio) ${r2.trace.filter((_, i) => i % 8 === 7).map(([t, d]) => t.toFixed(0) + ':' + fmt(d / eb2, 2)).join('  ')}`,
    'This is the known Gauss-Seidel limit: a long stiff chain needs ~N^2 * stiffness-ratio sweeps to reach static equilibrium; see NOTES.md.',
  ]);
}

// ---------------------------------------------------------------- (2) catenary
{
  const span = 6, len = 6.9, N = 24, y0 = 5;
  const mat = makeMaterial({ ...MATERIALS.rope, damping: 1.0, scatter: 0 });
  const w = new SoftWorld({ substepHz: 480, iterations: 1 });
  const r = buildRope(w, { a: [0, y0, 0], b: [span, y0, 0], slack: len / span, segments: N, radius: 0.02, mat, pin: 'both' });
  const T = QUICK ? 15 : 40;
  for (let i = 0; i < T * 60; i++) w.step(1 / 60);
  // analytical catenary for arc length S (the simulated rope's actual unstretched length) between level supports
  const S = r.length;
  let lo = 0.05, hi = 1000; for (let k = 0; k < 200; k++) { const a = (lo + hi) / 2; if (2 * a * Math.sinh(span / (2 * a)) > S) lo = a; else hi = a; }
  const a = (lo + hi) / 2, yA = (x) => a * (Math.cosh((x - span / 2) / a) - Math.cosh(span / (2 * a)));
  const sagA = -yA(span / 2);
  let maxDev = 0, sumDev = 0;
  for (const id of r.ids) { const x = w.pos[id * 3], y = w.pos[id * 3 + 1] - y0, d = Math.abs(y - yA(x)); maxDev = Math.max(maxDev, d); sumDev += d; }
  const midSag = y0 - w.pos[r.ids[N / 2] * 3 + 1];
  // elastic stretch correction: mean tension ~ H/cos; report the strain so the comparison is fair
  const Hh = a * mat.density * Math.PI * 0.02 ** 2 * G, strain = Hh / (mat.youngs * Math.PI * 0.02 ** 2);
  report('(2) hanging chain vs catenary', maxDev / sagA <= 0.05, [
    `rope span ${span} m, length ${fmt(S)} m, ${N} links, ${w.n} particles (E=${fmt(mat.youngs)}, r=20 mm)`,
    `analytical catenary: a=${fmt(a)} m, mid sag ${fmt(sagA * 1000, 1)} mm; simulated mid sag ${fmt(midSag * 1000, 1)} mm (${fmt((midSag - sagA) / sagA * 100, 2)} %)`,
    `max node deviation from the analytical curve = ${fmt(maxDev * 1000, 2)} mm = ${fmt(maxDev / sagA * 100, 2)} % of the sag (mean ${fmt(sumDev / r.ids.length * 1000, 2)} mm); horizontal-tension strain ~${fmt(strain, 2)}`,
    `residual kinetic energy ${fmt(w.energy().kinetic)} J after ${T} s`,
  ], { maxDevPct: maxDev / sagA * 100 });
}

// ---------------------------------------------------------------- (3) energy, free fall, no collisions
{
  const mat = makeMaterial({ ...MATERIALS.wood, yield: 1e12, fracture: 1e12, crush: 1e12, snap: false, damping: 0, scatter: 0 });
  const rows = [];
  let allPass = true;
  for (const [label, sub, it, bend] of [['60 Hz, 8 substeps, pre-bent 1 mm', 8, 1, 0.001], ['60 Hz, 4 substeps (phone tier), pre-bent 8 mm (0.6 % fibre strain = wood fracture strain)', 4, 1, 0.008], ['60 Hz, 8 substeps, violent pre-bend 20 mm (1.5 % fibre strain, 2.5x past fracture)', 8, 1, 0.02]]) {
    const w = new SoftWorld({ substeps: sub, iterations: it });
    const b = buildBeam(w, { a: [0, 20, 0], b: [0.8, 20, 0], width: 0.1, height: 0.1, mat });
    for (let i = 0; i < w.n; i++) { const x = w.pos[i * 3]; w.pos[i * 3 + 1] += bend * Math.sin(Math.PI * x / 0.8); w.prev[i * 3 + 1] = w.pos[i * 3 + 1]; }
    const e0 = w.energy(), c0 = w.centreOfMass();
    let emax = e0.total, ecur = e0.total, vcomMax = 0; const T = 2.0, steps = Math.round(T * 60);
    let zeroMean = 0;
    for (let i = 0; i < steps; i++) { w.step(1 / 60); const e = w.energy(); ecur = e.total; if (e.total > emax) emax = e.total; }
    const c1 = w.centreOfMass(), t = steps / 60;
    const fall = c0[1] - c1[1], expected = 0.5 * G * t * t;
    const growth = (emax - e0.total) / Math.max(1e-9, e0.elastic);
    const ok = growth <= 0.001 && Math.abs(fall - expected) / expected < 0.02;
    allPass = allPass && ok;
    rows.push(`${label}: E0 total ${fmt(e0.total)} J (elastic ${fmt(e0.elastic)}), max E over 2 s = E0 ${emax - e0.total >= 0 ? '+' : ''}${fmt(emax - e0.total)} J (${fmt(growth * 100, 3)} % of elastic), final E ${fmt(ecur - e0.total)} J vs E0, COM fall ${fmt(fall, 4)} m vs ${fmt(expected, 4)} m (g t^2/2)  [${ok ? 'ok' : 'BAD'}]`);
  }
  report('(3) free fall, no collisions: energy never grows', allPass, rows);
}

// ---------------------------------------------------------------- (4) yield and fracture
{
  const L = BEAM.L, h = BEAM.H;
  const sy = 4.0e7, sf = 6.0e7;                         // wood-like (bending) yield and fracture stress, Pa
  const S = I_BEAM / (h / 2);                            // section modulus
  const Py = sy * S / L, Pf = sf * S / L;
  const tipForce = (w, b, P) => { for (const q of b.tip.all) w.setForce(q, 0, -P / 5, 0); };
  const trial = (mat, targetDrop, name, rampSeconds) => {
    const w = new SoftWorld({ substepHz: 480, iterations: 1 });
    const b = buildBeam(w, { a: [0, 5, 0], b: [L, 5, 0], width: BEAM.W, height: BEAM.H, mat, pin: 'start' });
    for (let i = 0; i < 90; i++) w.step(1 / 60);                // settle under own weight first
    const drop0 = 5 - w.pos[b.tip.c * 3 + 1];
    let t = 0, peak = 0, released = false, loadAtRelease = 0, steps = 0, P = 0;
    const rate = Py / rampSeconds;
    while (!released && steps < 60 * 30) {
      P += rate / 60; tipForce(w, b, P); w.step(1 / 60); steps++;
      const d = 5 - w.pos[b.tip.c * 3 + 1] - drop0; peak = Math.max(peak, d);
      if (d >= targetDrop) { released = true; loadAtRelease = P; }
    }
    tipForce(w, b, 0);
    for (let i = 0; i < 60 * (QUICK ? 10 : 14); i++) w.step(1 / 60);
    const residual = 5 - w.pos[b.tip.c * 3 + 1] - drop0;
    return { peak, residual, loadAtRelease, released, drop0, w, b, broke: w.nBroken };
  };
  const dy = Py * L ** 3 / (3 * woodElastic().youngs * I_BEAM);       // elastic tip deflection at first yield
  const target = 3 * dy;
  const elastic = trial(woodElastic(), target, 'elastic', 4.0);
  const plastic = trial(makeMaterial({ ...MATERIALS.wood, yield: sy, fracture: 1e13, crush: 1e13, snap: false, damping: 1.0, scatter: 0 }), target, 'plastic', 4.0);
  const springback = plastic.loadAtRelease * L ** 3 / (3 * woodElastic().youngs * I_BEAM);
  const expectResidual = plastic.peak - Math.min(springback, dy * 1.2);
  report('(4a) beam loaded past yield stays bent', plastic.residual > 0.4 * plastic.peak && elastic.residual < 0.05 * elastic.peak, [
    `analytical first-yield tip load P_y = sigma_y*S/L = ${fmt(Py, 1)} N, elastic deflection at first yield = ${fmt(dy * 1000, 1)} mm; loaded until tip drops ${fmt(target * 1000, 1)} mm, then released and settled`,
    `elastic control (no yield): peak ${fmt(elastic.peak * 1000, 2)} mm -> residual ${fmt(elastic.residual * 1000, 3)} mm (${fmt(elastic.residual / elastic.peak * 100, 2)} % of peak)`,
    `plastic beam (sigma_y=${fmt(sy)} Pa): peak ${fmt(plastic.peak * 1000, 2)} mm at load ${fmt(plastic.loadAtRelease / Py, 2)} P_y -> residual ${fmt(plastic.residual * 1000, 2)} mm (${fmt(plastic.residual / plastic.peak * 100, 1)} % of peak, permanent bend)`,
    `elastic-perfectly-plastic hinge theory: residual ~ peak - elastic recovery (<= ${fmt(Math.min(springback, dy * 1.2) * 1000, 1)} mm) = ${fmt(expectResidual * 1000, 1)} mm`,
  ], { residualPlastic: plastic.residual, residualElastic: elastic.residual });
  // fracture: brittle (no yield), ramp until it breaks. Compare breaking load to sigma_f*S/L minus the self-weight moment
  const brittle = makeMaterial({ ...MATERIALS.wood, yield: 1e13, fracture: sf, damping: 1.0, scatter: 0 });
  const w = new SoftWorld({ substepHz: 480, iterations: 1 });
  const b = buildBeam(w, { a: [0, 5, 0], b: [L, 5, 0], width: BEAM.W, height: BEAM.H, mat: brittle, pin: 'start' });
  const events = []; w.onBreak = (e) => events.push(e);
  for (let i = 0; i < 90; i++) w.step(1 / 60);
  // stepped quasi-static ramp: +2 % of the predicted breaking load every 3 s hold, starting at 60 % (the beam needs ~3 s to settle)
  const PfGuess = (sf * S - brittle.density * BEAM.W * BEAM.H * G * L * L / 2) / L;
  let P = 0.6 * PfGuess, breakLoad = null, steps = 0;
  while (!events.length && P < 3 * PfGuess) { tipForce(w, b, P); for (let i = 0; i < 180 && !events.length; i++) { w.step(1 / 60); steps++; } if (!events.length) P += 0.02 * PfGuess; }
  breakLoad = P; tipForce(w, b, 0);                          // the load (a hung weight) is gone once the beam lets go
  for (let i = 0; i < 60 * 8; i++) w.step(1 / 60);            // let it fall apart
  const q = brittle.density * BEAM.W * BEAM.H * G, Mgrav = q * L * L / 2, PfNet = (sf * S - Mgrav) / L;
  const comps = w.componentSizes();
  const tipY = w.pos[b.tip.c * 3 + 1], rootY = 5;
  report('(4b) beam loaded past fracture breaks and chunks separate', events.length > 0 && Math.abs(breakLoad - PfNet) / PfNet < 0.15 && comps.length >= 2, [
    `analytical breaking tip load = (sigma_f*S - M_selfweight)/L = ${fmt(PfNet, 1)} N; first break at ${fmt(breakLoad, 1)} N (${fmt((breakLoad - PfNet) / PfNet * 100, 2)} %)`,
    `bars broken ${w.nBroken}, separate connected pieces ${comps.length} (sizes ${comps.join(',')}), tip chunk fell to y=${fmt(tipY, 2)} m from 5 m`,
  ], { breakLoad, PfNet });
}

// ---------------------------------------------------------------- (5) time-step independence
{
  const mat = woodElastic();
  const eb = ebTip(mat), T = QUICK ? 12 : 30;
  const out = [];
  for (const hz of [30, 60, 120]) { const r = runCantilever({ hz, seconds: T, mat }); out.push({ hz, tip: r.tip, at2: r.trace.find(([t]) => t >= 2)?.[1] ?? NaN }); }
  const ref = out[1];
  const spread = Math.max(...out.map(o => Math.abs(o.tip - ref.tip) / ref.tip));
  const spreadT = Math.max(...out.map(o => Math.abs(o.at2 - ref.at2) / ref.at2));
  // honest second variant: the same number of substeps per frame (8) at every frame rate, so h varies 4x
  const out2 = [];
  for (const hz of [30, 60, 120]) { const r = runCantilever({ hz, seconds: T, mat, fixedSubsteps: 8 }); out2.push({ hz, tip: r.tip, at2: r.trace.find(([t]) => t >= 2)?.[1] ?? NaN }); }
  const ref2 = out2[1];
  const spread2 = Math.max(...out2.map(o => Math.abs(o.tip - ref2.tip) / ref2.tip));
  report('(5) time-step independence (cantilever, 30/60/120 Hz)', spread <= 0.10, [
    `A) fixed substep rate 480 Hz (8 substeps @60, 16 @30, 4 @120): tip after ${T} s = ${out.map(o => o.hz + ' Hz: ' + fmt(o.tip * 1000, 4) + ' mm').join(' | ')}  max spread ${fmt(spread * 100, 3)} %`,
    `   transient value at t=2 s: ${out.map(o => o.hz + ' Hz: ' + fmt(o.at2 * 1000, 4) + ' mm').join(' | ')}  spread ${fmt(spreadT * 100, 2)} %`,
    `B) fixed 8 substeps per frame (h varies 4x): ${out2.map(o => o.hz + ' Hz: ' + fmt(o.tip * 1000, 4) + ' mm').join(' | ')}  max spread ${fmt(spread2 * 100, 3)} %  [informational]`,
    `   all within ${fmt(Math.max(...out.map(o => Math.abs(o.tip - eb) / eb)) * 100, 2)} % of Euler-Bernoulli (${fmt(eb * 1000, 3)} mm)`,
  ], { spread, spread2 });
}

// ---------------------------------------------------------------- (7) volume constraint (extra)
{
  const mat = makeMaterial({ density: 1100, youngs: 5e5, poisson: 0.45, damping: 0.6, scatter: 0, yield: 1e12, fracture: 1e12 });
  const w = new SoftWorld({ substepHz: 480, iterations: 1 });
  w.heightfield = () => 0;
  const j = buildJelly(w, { mat, size: [0.5, 0.5, 0.5], counts: [4, 4, 4], origin: [0, 0.02, 0] });
  const v0 = j.volume();
  for (let i = 0; i < 60 * (QUICK ? 4 : 8); i++) w.step(1 / 60);
  const v1 = j.volume(), com = w.centreOfMass()[1];
  // compare: same jelly with volume constraints removed (bulk modulus ~0)
  report('(7) tetra volume constraints: jelly cube resting on ground', Math.abs(v1 / v0 - 1) < 0.03 && com > 0.05, [`volume ${fmt(v0 * 1000, 2)} L -> ${fmt(v1 * 1000, 2)} L (${fmt((v1 / v0 - 1) * 100, 2)} %), centre height ${fmt(com, 3)} m (nu=0.45, E=0.5 MPa, ${w.n} particles, ${w.nt} tets, ${w.nd} bars)`]);
}

// ---------------------------------------------------------------- determinism (extra)
{
  const build = () => {
    const w = new SoftWorld({ seed: 7, substepHz: 480, iterations: 1 });
    w.heightfield = (x, z) => 0.05 * Math.sin(x * 2) * Math.cos(z * 1.5);
    buildBlockCluster(w, { mat: makeMaterial(MATERIALS.stone), mortar: makeMaterial(MATERIALS.mortar), size: [0.5, 0.25, 0.25], counts: [3, 4, 1], origin: [0, 0.1, 0] });
    buildBeam(w, { a: [3, 3, 0], b: [4, 3, 0], width: 0.1, height: 0.1, mat: makeMaterial(MATERIALS.wood) });
    return w;
  };
  const a = build(), b = build(); for (let i = 0; i < 240; i++) { a.step(1 / 60); b.step(1 / 60); }
  const c = new SoftWorld({ seed: 8 }); // different seed must differ (strength scatter) -> use same build with other seed
  report('(extra) determinism: identical seed gives bit-identical state', a.checksum() === b.checksum(), [`checksum run A ${a.checksum()}  run B ${b.checksum()}  (240 frames, ${a.n} particles, ${a.nBroken} breaks)`]);
}

// ---------------------------------------------------------------- (6) frame cost
function buildBench(opts) {
  const w = new SoftWorld({ seed: 3, ...opts });
  w.heightfield = (x, z) => 0.15 * Math.sin(x * 0.7) * Math.cos(z * 0.5) * Math.min(1, Math.max(0, (2.5 - x) / 1.5)); w.heightfieldMax = 0.15;   // bumpy for x<1, flat under the masonry
  w.addCollider({ type: 'sphere', c: [4, 1.2, 4], r: 0.6 });
  w.addCollider({ type: 'box', c: [8, 0.5, 2], h: [1, 0.5, 1], q: [0, 0.38, 0, 0.92] });
  const wood = makeMaterial(MATERIALS.wood), rope = makeMaterial(MATERIALS.rope), cloth = makeMaterial(MATERIALS.cloth), stone = makeMaterial(MATERIALS.stone), mortar = makeMaterial(MATERIALS.mortar);
  for (let k = 0; k < 10; k++) buildBeam(w, { a: [-6, 1 + 0.3 * k, -6 + k * 1.2], b: [-5.2, 1 + 0.3 * k, -6 + k * 1.2], width: 0.1, height: 0.1, mat: wood, pin: 'start' });   // 8-bay cantilevers
  for (let k = 0; k < 10; k++) buildRope(w, { a: [-4, 4, -6 + k * 1.2], b: [-1, 4, -6 + k * 1.2], slack: 1.1, segments: 24, mat: rope, pin: 'both' });
  buildCloth(w, { origin: [0, 6, -6], du: [6, 0, 0], dv: [0, -4, 0], nu: 32, nv: 28, mat: cloth, pin: ['top'] });
  w.wind = [2, 0, 1.5];
  buildBlockCluster(w, { mat: stone, mortar, size: [0.5, 0.25, 0.25], counts: [6, 10, 3], origin: [3, 0.0301, -3] });
  return w;
}
{
  const rows = []; let primary = null;
  for (const [label, cfg] of [['phone tier   (4 substeps x 1 sweep)', { substeps: 4, iterations: 1 }], ['default tier (8 substeps x 1 sweep)', { substeps: 8, iterations: 1 }], ['quality tier (8 substeps x 2 sweeps)', { substeps: 8, iterations: 2 }]]) {
    const w = buildBench(cfg);
    for (let i = 0; i < 60; i++) w.step(1 / 60);             // warm up JIT + settle
    const N = QUICK ? 120 : 300, times = [];
    for (let i = 0; i < N; i++) { const t0 = performance.now(); w.step(1 / 60); times.push(performance.now() - t0); }
    times.sort((a, b) => a - b);
    const mean = times.reduce((a, b) => a + b, 0) / N, p95 = times[Math.floor(N * 0.95)], max = times[N - 1];
    rows.push(`${label}: ${w.n} particles, ${w.nd} bars, ${w.nw} welds, ${w.nt} tets | mean ${fmt(mean, 2)} ms, p95 ${fmt(p95, 2)} ms, max ${fmt(max, 2)} ms per 60 Hz frame (${w.stats.contacts} ground/collider contacts)`);
    if (label.startsWith('phone')) primary = { mean, p95, n: w.n };
  }
  {
    const w = buildBench({ substeps: 4, iterations: 1, sleep: true }); w.wind = null;
    for (let i = 0; i < 60 * (QUICK ? 25 : 40); i++) w.step(1 / 60);
    const N = 120, times = []; for (let i = 0; i < N; i++) { const t0 = performance.now(); w.step(1 / 60); times.push(performance.now() - t0); }
    rows.push(`phone tier, sleeping on, scene at rest (no wind): ${w.nAsleep}/${w.nComp} pieces asleep, ${w.nAct}/${w.n} particles awake | mean ${fmt(times.reduce((a, b) => a + b, 0) / N, 2)} ms per frame`);
  }
  const BUDGET_MS = 5.5;       // one third of a 16.7 ms frame on THIS PC (node) for the phone tier; a phone core is typically 3-5x slower (estimate, not measured)
  report('(6) frame cost, ~3000 particles', primary.mean <= BUDGET_MS, [
    ...rows,
    `budget: phone tier mean <= ${BUDGET_MS} ms on this PC (node ${process.version}); estimated phone cost = ${fmt(primary.mean * 3, 1)}-${fmt(primary.mean * 5, 1)} ms (3-5x slower core, NOT measured on a phone)`,
  ], { ms: primary.mean, p95: primary.p95, particles: primary.n });
}

// ---------------------------------------------------------------- (9a) rigid <-> soft impulse exchange on a plank
{
  const rows = []; let ok = true;
  for (const [label, sub, damp, v0] of [['8 substeps, damping 0.2, 3 m/s', 8, 0.2, 3], ['8 substeps, damping 0.2, 6 m/s', 8, 0.2, 6], ['4 substeps, damping 1, 10 m/s', 4, 1, 10]]) {
    const w = new SoftWorld({ substeps: sub, seed: 11, gravity: [0, 0, 0] });
    buildBeam(w, { a: [-1, 0, 0.3], b: [1, 0, 0.3], width: 0.3, height: 0.1, mat: makeMaterial({ ...MATERIALS.wood, damping: damp }), up: [0, 0, 1] });
    const ball = w.addCollider({ type: 'sphere', c: [0, 0, -1.5], r: 0.25, v: [0, 0, v0] }); ball.mass = 80;
    const ke0 = 0.5 * 80 * v0 * v0, p0 = 80 * v0; let keMax = 0, pErr = 0, bounced = false;
    for (let i = 0; i < 240; i++) {
      for (let a = 0; a < 3; a++) ball.c[a] += ball.v[a] / 60; w.clearImpulses(); w.step(1 / 60); for (let a = 0; a < 3; a++) ball.v[a] += ball.j[a] / ball.mass;
      const e = w.energy(); let pz = 0; for (let q = 0; q < w.n; q++) pz += w.mass[q] * w.vel[q * 3 + 2];
      keMax = Math.max(keMax, e.kinetic + 0.5 * 80 * (ball.v[0] ** 2 + ball.v[1] ** 2 + ball.v[2] ** 2)); pErr = Math.max(pErr, Math.abs(pz + 80 * ball.v[2] - p0) / p0);
    }
    const good = keMax <= ke0 * 1.05 && pErr <= 0.15; ok = ok && good;
    rows.push(`${label}: max total KE / initial ball KE = ${fmt(keMax / ke0, 3)}, max |momentum error| = ${fmt(pErr * 100, 1)} % (free plank, no gravity)  [${good ? 'ok' : 'BAD'}]`);
  }
  report('(9a) rigid ball hits a free plank: energy does not grow, momentum is exchanged', ok, rows);
}

// ---------------------------------------------------------------- (9) masonry: stands, then is hit by a ball (rigid <-> soft exchange)
{
  const stone = makeMaterial(MATERIALS.stone), mortar = makeMaterial(MATERIALS.mortar);
  const w = new SoftWorld({ substepHz: 480, seed: 11 }); w.heightfield = () => 0; w.heightfieldMax = 0.1;
  buildBlockCluster(w, { mat: stone, mortar, size: [0.5, 0.25, 0.5], counts: [2, 10, 2], origin: [-0.5, 0.0305, -0.5] });
  for (let i = 0; i < 60 * 6; i++) w.step(1 / 60);
  const stands = w.nBroken === 0 && w.componentCount() === 1, top0 = Math.max(...Array.from({ length: w.n }, (_, i) => w.pos[i * 3 + 1]));
  const ball = w.addCollider({ type: 'sphere', c: [0, 1.2, -4], r: 0.25, v: [0, 0, 6] }); ball.mass = 80;
  const ke0 = 0.5 * ball.mass * 36, p0 = ball.mass * 6; let keMax = 0, pMax = 0;
  for (let i = 0; i < 60 * 4; i++) {
    for (let a = 0; a < 3; a++) ball.c[a] += ball.v[a] / 60; w.clearImpulses(); w.step(1 / 60); for (let a = 0; a < 3; a++) ball.v[a] += ball.j[a] / ball.mass;
    const e = w.energy(); let pz = 0; for (let q = 0; q < w.n; q++) pz += w.mass[q] * w.vel[q * 3 + 2];
    keMax = Math.max(keMax, e.kinetic + 0.5 * ball.mass * (ball.v[0] ** 2 + ball.v[1] ** 2 + ball.v[2] ** 2)); pMax = Math.max(pMax, pz + ball.mass * ball.v[2]);
  }
  report('(9) masonry tower: stands, then 80 kg ball at 6 m/s (rigid<->soft impulse exchange)', stands && keMax <= ke0 * 1.10 && pMax <= p0 * 1.5, [
    `standing 6 s: breaks ${stands ? 0 : 'some'}, pieces ${stands ? 1 : w.componentCount()}, height ${fmt(top0, 3)} m (2.53 m nominal)`,
    `after the hit: max total kinetic energy (soft + ball) ${fmt(keMax)} J vs ball energy ${fmt(ke0)} J (ratio ${fmt(keMax / ke0, 2)}); max z-momentum ${fmt(pMax)} vs ${fmt(p0)} kg m/s (ratio ${fmt(pMax / p0, 2)}); breaks ${w.nBroken}, pieces ${w.componentCount()}`,
    'KNOWN LIMITATION when this fails: stiff stone blocks + one Gauss-Seidel sweep do not conserve momentum/energy in violent impacts (see NOTES.md).',
  ]);
}

// ---------------------------------------------------------------- (8) sleeping (optional feature)
{
  const mat = woodElastic(), eb = ebTip(mat);
  const w = new SoftWorld({ substepHz: 480, sleep: true });
  const b = buildBeam(w, { a: [0, 5, 0], b: [BEAM.L, 5, 0], width: BEAM.W, height: BEAM.H, mat, pin: 'start' });
  let sleepT = null;
  for (let i = 0; i < 60 * 60; i++) { w.step(1 / 60); if (sleepT === null && w.nAsleep) sleepT = w.time; }
  const tip = 5 - w.pos[b.tip.c * 3 + 1], asleep = w.nAsleep, tAsleep = sleepT;
  const t0 = performance.now(); for (let i = 0; i < 300; i++) w.step(1 / 60); const cost = (performance.now() - t0) / 300;
  w.addCollider({ type: 'sphere', c: [BEAM.L * 0.9, 5 - 0.12, 0], r: 0.1, v: [0, 0, 0] });   // a ball arrives under the tip
  w.step(1 / 60); const woke = w.nAsleep === 0;
  report('(8) sleeping: settles, sleeps, wakes on contact (opt-in)', Math.abs(tip - eb) / eb <= 0.10 && asleep === 1 && woke, [
    `tip ${fmt(tip * 1000)} mm vs EB ${fmt(eb * 1000)} mm (${fmt((tip - eb) / eb * 100, 2)} %), fell asleep at t=${tAsleep ? tAsleep.toFixed(1) : 'never'} s, asleep cost ${fmt(cost, 4)} ms/frame, woke when a collider arrived: ${woke}`,
  ]);
}

// ---------------------------------------------------------------- summary
const failed = results.filter(r => !r.pass);
console.log(`\n==== ${results.length - failed.length}/${results.length} passed ====`);
if (failed.length) console.log('FAILED: ' + failed.map(f => f.name).join('; '));
writeFileSync(join(dirname(fileURLToPath(import.meta.url)), 'verify-results.json'), JSON.stringify(results, null, 1));
process.exit(failed.length ? 1 : 0);
