// Air distortion engine check (v9.9.6). usage: node qa/distort-check.mjs
// The software renderer runs about one frame a second, so everything is stepped by hand inside single page evaluations (nothing else can run in between):
//   tick(dt) -> renderer.render -> DIST.main(), the same three calls the frame loop makes.
// Asserts: the pass runs only with a live source, a big blast makes a ring and a small one does not, the ring is dead after 0.4 s, caps hold under 50 blasts and 100 haze feeds,
// an empty bend map leaves the picture identical, a live ring and a live haze change the picture, Off and reduced motion disable it, the phone edition is Off by default but runs
// when turned on, and the three station sensor modes still render (and bend) with no GL error.
import { sleep, startServer, launch, loadGame, PROFILES } from './harness.mjs';
const T0 = Date.now(), log = (m) => console.log(`[${((Date.now() - T0) / 1000).toFixed(0)}s] ${m}`); setTimeout(() => { console.log('ERR watchdog: the distortion check took over 20 minutes'); process.exit(2); }, 1200000).unref();
const fail = []; const ok = (name, cond, detail) => { console.log((cond ? '  ok   ' : '  FAIL ') + name + (detail !== undefined ? '  ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)) : '')); if (!cond) fail.push(name); };
const prof = { ...PROFILES.desktop, w: 640, h: 400 };
const srv = await startServer(); const b = await launch({ ...prof, extraArgs: ['--autoplay-policy=no-user-gesture-required'] });
const J = async (expr) => { const r = await b.ev(`JSON.stringify((()=>{ ${expr} })())`); return r ? JSON.parse(r) : null; };
const url = (ed) => `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=${ed}`;
// shared page helpers: grab(): render one frame the way the loop does and read back the canvas pixels
const HELP = `window.__grab = (useMain) => { const sc = __sc, gl = sc.renderer.getContext(), W = gl.drawingBufferWidth, H = gl.drawingBufferHeight; sc.renderer.render(sc.scene, sc.camera); let ran = false; if (useMain) ran = sc.DIST.main(); const px = new Uint8Array(W * H * 4); gl.readPixels(0, 0, W, H, gl.RGBA, gl.UNSIGNED_BYTE, px); return { px, ran, W, H }; };
  window.__diff = (a, b) => { let n = 0, mx = 0, sum = 0; for (let i = 0; i < a.length; i += 4) { const d = Math.max(Math.abs(a[i] - b[i]), Math.abs(a[i + 1] - b[i + 1]), Math.abs(a[i + 2] - b[i + 2])); if (d > 2) n++; if (d > mx) mx = d; sum += d; } return { n, mx, mean: +(sum / (a.length / 4)).toFixed(4) }; };
  window.__ahead = (d) => { const sc = __sc, c = sc.camera, v = new sc.THREE.Vector3(); c.getWorldDirection(v); const l = Math.hypot(v.x, v.z) || 1; const x = c.position.x + v.x / l * d, z = c.position.z + v.z / l * d; return { x, z, y: Math.max(sc.heightAt(x, z), 0) }; }; 1`;
try {
  if (!await loadGame(b, url('desktop'))) throw new Error('no load');
  await b.ev("document.getElementById('help').hidden=true; 1");
  await b.ev(HELP);
  await b.ev("__sc.enterFP(); 1"); await sleep(1500);
  await b.ev("__sc.fp.pitch = -0.05; __sc.DIST.noMirage = true; 1"); await sleep(500);
  let r = await J("return __sc.DIST.status()"); ok('the engine is supported here (WebGL2 float targets)', r.ok === true && r.pref === true, r);
  const errs0 = b.errs.length;

  // ---- idle: no source, no pass
  r = await J("const D = __sc.DIST; D.reset(); D.ts = 1; D.tick(0.016); const p0 = D.passes, d0 = D.bendDraws, g = __grab(true); return { ran: g.ran, dp: D.passes - p0, db: D.bendDraws - d0, nr: D.nr, nh: D.nh }");
  ok('idle: the pass does not run (pass count unchanged, no bend map drawn)', r.ran === false && r.dp === 0 && r.db === 0, r);
  // ---- an empty bend map is the identity: the copy + composite path reproduces the normal picture
  r = await J("const D = __sc.DIST; D.reset(); D.tick(0.016); const a = __grab(false); D.force = true; D.tick(0.016); const p0 = D.passes; const c = __grab(true); D.force = false; const df = __diff(a.px, c.px); return { ran: c.ran, dp: D.passes - p0, df, W: a.W, H: a.H }");
  ok('the composite with an empty bend map leaves the picture identical (golden compare)', r.ran === true && r.dp === 1 && r.df.mx <= 3 && r.df.n === 0, r);

  // ---- blasts
  r = await J("const sc = __sc, D = sc.DIST, p = __ahead(40); D.reset(); sc.blast(p.x, p.y, p.z, { R: 7, dmg: 10, crater: 0, depth: 0, owner: null, quiet: true }); const small = D.shocks.length; sc.blast(p.x, p.y, p.z, { R: 20, dmg: 10, crater: 0, depth: 0, owner: null, quiet: true }); const big = D.shocks.length; D.reset(); sc.heavyBlast({ x: p.x, y: p.y, z: p.z, dmg: 10 }); const heavy = D.shocks.length; D.reset(); sc.blast(p.x, p.y, p.z, { R: 9, dmg: 10, crater: 0, depth: 0, owner: null, quiet: true, heavy: true }); const hv = D.shocks.length; return { small, big, heavy, hv }");
  ok('a small blast makes no shockwave; R 20, heavyBlast and a heavy flag do', r.small === 0 && r.big === 1 && r.heavy === 1 && r.hv === 1, r);
  r = await J("const sc = __sc, D = sc.DIST, p = __ahead(40); D.reset(); sc.fxG.update(5); sc.blast(p.x, p.y, p.z, { R: 24, dmg: 10, crater: 0, depth: 0, owner: null, quiet: true }); D.ts = 0; D.tick(0.05); D.shocks[0].age = 0.09; const gl = sc.renderer.getContext(); const a = __grab(false); const p0 = D.passes, d0 = D.bendDraws, c = __grab(true); const df = __diff(a.px, c.px); const e = gl.getError(); D.ts = 1; return { ran: c.ran, dp: D.passes - p0, db: D.bendDraws - d0, nr: D.nr, df, err: e }");
  ok('a big blast: the bend-map pass runs once, draws one ring, bends the picture and leaves no GL error', r.ran === true && r.dp === 1 && r.db === 1 && r.nr === 1 && r.df.n > 50 && r.err === 0, r);
  r = await J("const D = __sc.DIST; D.reset(); const sc = __sc, p = __ahead(40); sc.blast(p.x, p.y, p.z, { R: 24, dmg: 10, crater: 0, depth: 0, owner: null, quiet: true }); D.ts = 1; D.tick(0.05); const alive1 = D.shocks.length; D.tick(0.05); D.tick(0.05); D.tick(0.05); D.tick(0.05); D.tick(0.05); D.tick(0.05); D.tick(0.05); const alive2 = D.shocks.length; const p0 = D.passes; const g = __grab(true); return { alive1, alive2, ran: g.ran, dp: D.passes - p0 }");
  ok('the shockwave is alive at 0.05 s and dead after 0.4 s, and the pass stops with it', r.alive1 === 1 && r.alive2 === 0 && r.ran === false && r.dp === 0, r);
  r = await J("const sc = __sc, D = sc.DIST, p = __ahead(40); D.reset(); for (let i = 0; i < 50; i++) sc.blast(p.x + (i % 7) - 3, p.y, p.z + (i % 5) - 2, { R: 24, dmg: 10, crater: 0, depth: 0, owner: null, quiet: true }); const s1 = D.shocks.length; D.ts = 0; D.tick(0.01); const g = __grab(true); const err = sc.renderer.getContext().getError(); D.ts = 1; const o = { s1, nr: D.nr, err }; D.reset(); return o");
  ok('50 blasts: at most 8 shockwaves are kept and drawn', r.s1 <= 8 && r.nr >= 1 && r.nr <= 8 && r.err === 0, r);

  // ---- haze
  r = await J("const sc = __sc, D = sc.DIST, p = __ahead(22); D.reset(); D.ts = 1; for (let i = 0; i < 12; i++) { D.haze(777, p.x, p.y + 0.5, p.z, 0.9, 5, 3.5); D.tick(0.05); } const a = __grab(false); const p0 = D.passes; D.haze(777, p.x, p.y + 0.5, p.z, 0.9, 5, 3.5); D.tick(0.05); const c = __grab(true); const df = __diff(a.px, c.px); const slot = D.slots.get(777); return { ran: c.ran, dp: D.passes - p0, nh: D.nh, a: slot && +slot.a.toFixed(2), df, err: sc.renderer.getContext().getError() }");
  ok('a fire feeds a haze volume that fades in, runs the pass and shimmers the picture', r.ran === true && r.dp === 1 && r.nh === 1 && r.a >= 0.9 && r.df.n > 20 && r.err === 0, r);
  r = await J("const sc = __sc, D = sc.DIST, p = __ahead(30); D.reset(); for (let k = 0; k < 6; k++) { for (let i = 0; i < 100; i++) D.haze(1000 + i, p.x + (i % 10) * 3 - 15, p.y + 0.5, p.z + Math.floor(i / 10) * 3 - 15, 0.5 + (i % 5) / 10, 4, 3); D.tick(0.05); } const slots = D.slots.size; D.ts = 0; const g = __grab(true); D.ts = 1; const o = { slots, nh: D.nh, err: sc.renderer.getContext().getError() }; D.reset(); return o");
  ok('100 haze feeds: at most 24 volumes drawn, slots bounded', r.nh <= 24 && r.slots <= 36 && r.err === 0, r);
  r = await J("const D = __sc.DIST, p = __ahead(22); D.reset(); for (let i = 0; i < 12; i++) { D.haze(778, p.x, p.y + 0.5, p.z, 0.9, 5, 3.5); D.tick(0.05); } for (let i = 0; i < 12; i++) D.tick(0.05); return { slots: D.slots.size }");
  ok('a haze volume that stops being fed fades out and is removed', r.slots === 0, r);

  // ---- switch off
  r = await J("const sc = __sc, D = sc.DIST, p = __ahead(40); D.setPref(false); D.tick(0.05); sc.blast(p.x, p.y, p.z, { R: 24, dmg: 10, crater: 0, depth: 0, owner: null, quiet: true }); D.haze(5, p.x, p.y, p.z, 1, 5, 3); const s = D.shocks.length; D.tick(0.05); const p0 = D.passes; const g = __grab(true); return { s, live: D.live, ran: g.ran, dp: D.passes - p0, stored: localStorage.getItem('squall-cove-airdistort') }");
  ok('Air distortion Off: no shockwave kept, no pass, remembered as 0', r.s === 0 && r.live === false && r.ran === false && r.dp === 0 && r.stored === '0', r);
  r = await J("const D = __sc.DIST; D.setPref(true); D.noMirage = true; D.tick(0.05); const el = document.getElementById('mDistort'); return { live: D.live, stored: localStorage.getItem('squall-cove-airdistort'), btn: !!el, text: el && el.textContent.trim().slice(0, 40) }");
  ok('switching it back On works, the Settings button exists', r.live === true && r.stored === '1' && r.btn, r);
  r = await J("const D = __sc.DIST; D.govTrip(); const g = D.status(); D.setPref(true); return { govOffBest: g.govOff }");
  ok('the governor does not trip in Best smoothness mode (test runs with gov=best)', r.govOffBest === false, r);

  // ---- the gunship station: all three modes render, distorted, no GL error
  await b.ev("__sc.exitFP(); 1"); await sleep(600);
  r = await J("const sc = __sc; sc.DIST.reset(); const res = sc.stnOpenFor('blue'); return { res, on: sc.STN.on }");
  ok('the station opens (sandbox)', r.res && r.on, r);
  for (const m of ['thermal', 'night', 'colour']) {
    r = await J(`const sc = __sc, D = sc.DIST, S = sc.STN; sc.stnSetMode('${m}', true); sc.stnStep(0.05); D.reset(); D.ts = 1; sc.stnRender(); D.tick(0.01); D.shock(S.ax, S.ay + 1, S.az, 26); for (let i = 0; i < 12; i++) { for (let j = 0; j < 8; j++) D.haze(900 + j, S.ax + j * 2 - 6, S.ay + 0.5, S.az + 3, 0.9, 5, 3.5); D.tick(0.02); D.shocks[0] && (D.shocks[0].age = 0.1); } D.ts = 0; const sp0 = D.stationPasses; sc.stnRender(); const gl = sc.renderer.getContext(); const o = { mode: S.mode, dsp: D.stationPasses - sp0, nr: D.nr, nh: D.nh, err: gl.getError(), rtNull: sc.renderer.getRenderTarget() === null }; D.ts = 1; return o`);
    ok('station ' + m + ': the scene is bent before the sensor shader (pass ran, ring and haze drawn), no GL error', r.mode === m && r.dsp === 1 && r.nr === 1 && r.nh >= 1 && r.err === 0 && r.rtNull, r);
  }
  r = await J("const sc = __sc, D = sc.DIST; D.reset(); const sp0 = D.stationPasses; sc.stnRender(); return { dsp: D.stationPasses - sp0 }");
  ok('station with no source: no distortion pass', r.dsp === 0, r);
  await b.ev("document.getElementById('stnLeave').click(); 1"); await sleep(500);
  ok('no console errors so far', b.errs.length === errs0, b.errs.slice(errs0, errs0 + 3));

  // ---- reduced motion
  await b.send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
  if (!await loadGame(b, url('desktop'))) throw new Error('no reload');
  await b.ev("document.getElementById('help').hidden=true; 1");
  r = await J("const sc = __sc, D = sc.DIST; D.tick(0.05); const p = { x: sc.camera.position.x + 10, y: 1, z: sc.camera.position.z + 10 }; sc.blast(p.x, p.y, p.z, { R: 24, dmg: 10, crater: 0, depth: 0, owner: null, quiet: true }); D.haze(1, p.x, p.y, p.z, 1, 5, 3); D.tick(0.05); return { enabled: D.enabled(), live: D.live, shocks: D.shocks.length, slots: D.slots.size, label: document.getElementById('mDistort').textContent.trim().slice(0, 60) }");
  ok('prefers-reduced-motion: the engine is off, nothing is kept, the Settings line says why', r.enabled === false && r.live === false && r.shocks === 0 && r.slots === 0 && /Off/.test(r.label), r);
  await b.send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'no-preference' }] });

  // ---- the phone edition: Off by default, but the code runs when it is turned on
  await b.ev("try { localStorage.removeItem('squall-cove-airdistort'); } catch (e) {} 1");
  if (!await loadGame(b, url('phone'))) throw new Error('no phone load');
  await b.ev("document.getElementById('help').hidden=true; 1"); await b.ev(HELP); await b.ev("__sc.enterFP(); 1"); await sleep(1500);
  r = await J("const D = __sc.DIST; D.noMirage = true; return { phone: !!window.__ED.phone, pref: D.pref, label: document.getElementById('mDistort').textContent.trim().slice(0, 40) }");
  ok('phone edition: Air distortion is Off by default', r.phone === true && r.pref === false && /Off/.test(r.label), r);
  r = await J("const sc = __sc, D = sc.DIST, p = __ahead(40); D.tick(0.05); sc.blast(p.x, p.y, p.z, { R: 24, dmg: 10, crater: 0, depth: 0, owner: null, quiet: true }); const off = D.shocks.length; D.setPref(true); D.tick(0.01); sc.blast(p.x, p.y, p.z, { R: 24, dmg: 10, crater: 0, depth: 0, owner: null, quiet: true }); D.ts = 0; D.tick(0.01); D.shocks[0].age = 0.1; const p0 = D.passes; const g = __grab(true); const err = sc.renderer.getContext().getError(); D.ts = 1; return { off, ran: g.ran, dp: D.passes - p0, err }");
  ok('phone edition: nothing while Off; once turned on the ring and the pass run with no GL error', r.off === 0 && r.ran === true && r.dp === 1 && r.err === 0, r);
  ok('no console errors in the whole run', b.errs.length === errs0, b.errs.slice(errs0, errs0 + 3));
} catch (e) { console.log('ERR', e.message); fail.push(e.message); } finally { await b.close(); await srv.close(); }
console.log(fail.length ? 'FAIL: ' + fail.join(' | ') : 'all distortion checks passed'); process.exit(fail.length ? 1 : 0);
