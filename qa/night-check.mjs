// Night and light check. usage: node qa/night-check.mjs [part1|part2|part3|all] [shots]
// part1 (v9.9.10): the clock maths (24 minutes a day at Normal), pause, save round trip, the sky continuous across dusk, stars and moon, no console errors.
// part2 (v9.9.11): flashlight, light budget caps, headlights, generators blacking out a point.
// part3 (v9.9.12): bot night vision range table.
// One headless Chrome, killed by PID at the end. At most four screenshots in all (with `shots`): dusk sky, night battle point lit, flashlight beam, vehicle headlights.
import fs from 'fs'; import path from 'path';
import { ROOT, sleep, startServer, launch, loadGame, clickText, PROFILES } from './harness.mjs';
const PART = process.argv[2] && !/^shots$/.test(process.argv[2]) ? process.argv[2] : 'all', SHOTS = process.argv.includes('shots');
const prof = { ...PROFILES.desktop, w: 1100, h: 680 };
const PROG = path.join(process.env.TEMP || '.', 'night-progress.log'); try { fs.writeFileSync(PROG, ''); } catch (e) { }
const out = (s) => { console.log(s); try { fs.appendFileSync(PROG, s + String.fromCharCode(10)); } catch (e) { } };
const T0 = Date.now(), log = (m) => out(`[${((Date.now() - T0) / 1000).toFixed(0)}s] ${m}`); setTimeout(() => { console.log('ERR watchdog: the night check took over 40 minutes'); process.exit(2); }, 2400000).unref();
const fail = []; const ok = (name, cond, detail) => { out((cond ? '  ok   ' : '  FAIL ') + name + (detail !== undefined ? '  ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)) : '')); if (!cond) fail.push(name); };
const run = (p) => PART === 'all' || PART === p;
const srv = await startServer(); const b = await launch({ ...prof, extraArgs: ['--autoplay-policy=no-user-gesture-required'] }); console.log('chrome pid ' + b.pid + ' (killed by PID at the end)');
const J = async (expr) => { const r = await b.ev(`JSON.stringify((()=>{ ${expr} })())`); return r ? JSON.parse(r) : null; };
const SHOT = (n) => path.join(ROOT, 'docs', n);
async function tpTo(name, dx, dz) { await b.ev(`(()=>{ const s = __sc, p = s.fp.p, pt = s.BM().points.find(q => q[0] === ${JSON.stringify(name)}); if (!pt) return 0; p.x = pt[1] + ${dx}; p.z = pt[2] + ${dz}; p.y = s.standY(p.x, p.z); s.fp.vx = s.fp.vz = 0; return 1 })()`); await sleep(1200); }
let inBattle = false;
async function press(key, code, vk, text) { await b.send('Input.dispatchKeyEvent', { type: text ? 'keyDown' : 'rawKeyDown', key, code, windowsVirtualKeyCode: vk, text: text || undefined }); await b.send('Input.dispatchKeyEvent', { type: 'keyUp', key, code, windowsVirtualKeyCode: vk }); await sleep(120); }
const waitFor = async (expr, ms = 60000) => { const t0 = Date.now(); while (Date.now() - t0 < ms) { if (await b.ev(expr)) return true; await sleep(400); } return false; };
const frames = (n) => sleep(n * 70);                                  // the page's animation frames do not tick reliably in a hidden headless window, so wait in real time
async function startBattle() {
  if (inBattle) return; inBattle = true;
  await b.ev("__sc.openBattleSetup(); 1"); await sleep(500); await b.ev(clickText('#bSetup button', 'Begin battle')); await sleep(5000);
  await b.ev("__sc.playBattle('blue'); window.__me = __sc.fp.p; __sc.CHEAT.god = true; 1"); await sleep(2500); await b.ev("document.getElementById('help').hidden = true; 1");
  for (let k = 0; k < 6; k++) { const st = await b.ev('__sc.fp.p.state + "|" + Math.round(__sc.fp.p.hp)'); if (!/^rag/.test(st)) break; log('player is ' + st + ', redeploying'); await b.ev("(()=>{ const s = __sc, me = s.fp.p; s.exitFP(); s.removePerson(me); s.playBattle('blue'); window.__me = s.fp.p; s.CHEAT.god = true; return 1 })()"); await sleep(3500); }
}
try {
  if (!await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=${prof.ed}`)) throw new Error('no load');
  await b.ev("document.getElementById('help').hidden = true; 1", true); log('loaded');

  if (run('part1')) {
    log('part 1: the clock and the sky'); await b.ev("__sc.renderer.render0 = __sc.renderer.render.bind(__sc.renderer); __sc.renderer.render = () => {}; 1");   // the maths needs no picture, and it keeps the frame loop quiet
    // ---- clock maths: tick the real stepWeather in 1/10 s steps
    let t0 = 0; const sim = async (secs) => { const r = await J(`const s = __sc, a = s.tod.t; for (let i = 0; i < ${Math.round(secs * 10)}; i++) s.stepWeather(0.1); return [a, s.tod.t]`); t0 = r[0]; return r[1]; };   // one synchronous call, so the live frame loop cannot add time in between
    await b.ev("__sc.todSetHour(6, {}); __sc.todSetMode('off'); 1");
    let t1 = await sim(60);
    ok('Off: the clock stays where it is', Math.abs(t1 - t0) < 1e-9, { t0, t1 });
    await b.ev("__sc.todSetMode('normal'); 1"); t1 = await sim(60);
    ok('Normal: 60 real seconds is exactly one hour', Math.abs(t1 - t0 - 1) < 1e-6, +(t1 - t0).toFixed(6));
    t1 = await sim(1440); ok('Normal: 1440 real seconds (24 minutes) is a full day', Math.abs(t1 - t0 - 24) < 1e-6, +(t1 - t0).toFixed(6));
    await b.ev("__sc.todSetHour(6, {}); __sc.todSetMode('slow'); 1"); t1 = await sim(120); ok('Slow: 48 minutes a day', Math.abs((t1 - t0) - 120 * 30 / 3600) < 1e-6 && Math.abs(86400 / 30 / 60 - 48) < 1e-9, +(t1 - t0).toFixed(5));
    await b.ev("__sc.todSetMode('fast'); 1"); t1 = await sim(60); ok('Fast: 12 minutes a day', Math.abs((t1 - t0) - 2) < 1e-6, +(t1 - t0).toFixed(5));
    await b.ev("__sc.todSetMode('real'); 1"); t1 = await sim(60); ok('Real time: 60 s is one minute', Math.abs((t1 - t0) - 1 / 60) < 1e-6, +(t1 - t0).toFixed(6));
    await b.ev("__sc.todSetMode('normal'); __sc.todPause(true); 1"); t1 = await sim(30); ok('Paused: the clock holds', t1 === t0 && await b.ev('__sc.tod.paused'), { t0, t1 });
    await b.ev("__sc.todPause(false); 1"); t1 = await sim(30); ok('Resumed: the clock runs again', t1 > t0 + 0.4, { t0, t1 });
    const fmt = await J("const s = __sc; s.todSetHour(18.6667, {}); return s.todClock()"); ok('the clock text is plain HH:MM (18:40)', fmt === '18:40', fmt);
    // ---- custom speed and a start hour
    await b.ev("__sc.tod.mul = 240; __sc.tod.preset = 'custom'; __sc.todSetHour(23.9, {}); 1"); t1 = await sim(30);
    ok('custom speed (240x) runs and passes midnight into the next day', Math.abs((t1 - t0) - 2) < 1e-6 && (await b.ev('__sc.todClock()')) === '01:54', await b.ev('__sc.todClock()'));
    // ---- world save round trip
    const rt = await J("const s = __sc; s.todSetMode('fast'); s.todSetHour(21.25, { moon: false }); s.tod.t += 24 * 3; s.todPause(true); const snap = s.snapshotWorld(); window.__snap = snap; const want = { t: s.tod.t, mul: s.tod.mul, run: s.tod.run, paused: s.tod.paused, preset: s.tod.preset }; return { has: !!(snap.wx && snap.wx.tod), want, saved: snap.wx.tod }");
    ok('the world save carries the clock', rt.has, rt.saved);
    await b.ev("(async () => { const s = __sc; s.todSetMode('off'); s.todSetHour(3, {}); await s.loadWorld(window.__snap); window.__done = true })()"); for (let k = 0; k < 40 && !(await b.ev('window.__done === true')); k++) await sleep(1500);
    const back = await J("const s = __sc; return { t: s.tod.t, mul: s.tod.mul, run: s.tod.run, paused: s.tod.paused, preset: s.tod.preset }");
    ok('load restores time, speed, preset and pause', Math.abs(back.t - rt.want.t) < 1e-3 && back.mul === rt.want.mul && back.run === rt.want.run && back.paused === rt.want.paused && back.preset === rt.want.preset, { want: rt.want, back });
    // ---- continuity: step the clock across dusk in 10 Hz steps and compare consecutive sky states
    const cont = await J(`const s = __sc, F = s.SKF, o = s.todOut; s.todSetMode('off'); s.todSetHour(15.0, {}); s.tod.xf = 1; s.stepWeather(0.1); const names = ['dx','dy','dz','keyI','kr','kg','kb','hemi','exp','env','tr','tg','tb','fr','fg','fb','stars','sunVis','moonVis','keep'];
      let prev = Float32Array.from(o), worst = {}, n = 0, minI = 9, maxStar = 0; for (let h = 15.0; h < 24.0; h += 0.02) { s.tod.t = Math.floor(s.tod.t / 24) * 24 + h; s.tod.force = true; s.stepWeather(0.1); for (const k of names) { const d = Math.abs(o[F[k]] - prev[F[k]]); if (!(k in worst) || d > worst[k]) worst[k] = d; } prev = Float32Array.from(o); n++; minI = Math.min(minI, s.sunLight.intensity); maxStar = Math.max(maxStar, o[F.stars]); }
      return { worst, n, minI, maxStar }`);
    // 0.02 h steps are 72 s of game time: at Normal speed that is 1.2 real seconds, so allow a modest per-step change and forbid any jump
    const biggest = Math.max(...Object.values(cont.worst)); ok('sky values are continuous from 15:00 to midnight (no step larger than 0.3 per 72 s of game time, even for the light direction)', biggest < 0.3, { biggest: +biggest.toFixed(4), worst: Object.fromEntries(Object.entries(cont.worst).map(([k, v]) => [k, +v.toFixed(4)])) });
    ok('the stars come out at night and the light never goes out entirely', cont.maxStar > 0.95 && cont.minI > 0.05, { maxStar: cont.maxStar, minI: cont.minI });
    // the same walk at the real frame cadence: Normal speed, 10 Hz, the change between two ticks is tiny
    const cad = await J(`const s = __sc, F = s.SKF, o = s.todOut; s.todSetHour(17.5, {}); s.tod.xf = 1; s.todSetMode('normal'); s.stepWeather(0.1); let prev = Float32Array.from(o), worst = 0; for (let i = 0; i < 4500; i++) { s.stepWeather(0.1); if (i % 1 === 0) { for (const k of ['dx','dy','dz','keyI','kr','kb','tr','tg','tb','fr','hemi','exp','stars','sunVis']) worst = Math.max(worst, Math.abs(o[F[k]] - prev[F[k]])); prev = Float32Array.from(o); } } return { worst, hour: s.todClock() }`);
    ok('at Normal speed no value moves more than 0.03 between two 10 Hz ticks, across dusk', cad.worst < 0.03, cad);
    // the sun and moon geometry
    const geo = await J(`const s = __sc, F = s.SKF, o = s.todRaw; const at = (h) => { s.todSetHour(h, {}); s.stepWeather(0.1); return { sy: +o[F.sy].toFixed(3), my: +o[F.my].toFixed(3), label: s.wx.sky, stars: +o[F.stars].toFixed(2), keyI: +o[F.keyI].toFixed(2) } }; s.todSetMode('off'); return { noon: at(12.5), mid: at(0.5), dawn: at(5.8), dusk: at(18.6) }`);
    ok('noon: the sun is high and the label is day; midnight: the sun is below the horizon, stars on', geo.noon.sy > 0.8 && geo.noon.label === 'day' && geo.mid.sy < -0.3 && geo.mid.stars > 0.95, geo);
    ok('the old five words still read right (dawn, dusk)', geo.dawn.label === 'dawn' && geo.dusk.label === 'dusk', { dawn: geo.dawn.label, dusk: geo.dusk.label });
    const mph = await J(`const s = __sc; const names = new Set(); for (let d = 0; d < 30; d++) { s.tod.t = 24 * d + 22; names.add(s.todMoonName()); } return [...names]`);
    ok('the moon goes through its phases over a month', mph.length >= 7, mph);
    // temperature link and a weather preset that must not break
    await b.ev("__sc.todSetHour(14, {}); __sc.stepWeather(0.1); 1"); const s1 = await b.ev('__sc.todSolar()'); await b.ev("__sc.todSetHour(2, {}); __sc.stepWeather(0.1); 1"); const s2 = await b.ev('__sc.todSolar()');
    ok('the temperature link warms by day and cools by night', s1 > 2 && s2 < -3, { s1, s2 });
    await b.ev("__sc.wx.rain = 2; __sc.wx.imp.rain = true; __sc.todSetHour(1, {}); for (let i = 0; i < 40; i++) __sc.stepWeather(0.1); 1");
    ok('rain still dims the stars and the light at night (weather settings respected)', await b.ev('__sc.starPts.material.uniforms.uA.value < 0.6'), await b.ev('__sc.starPts.material.uniforms.uA.value'));
    await b.ev("__sc.wx.rain = 0; __sc.wx.imp.rain = false; 1");
    // a preset cross-fades rather than jumping
    const xf = await J(`const s = __sc, F = s.SKF, o = s.todOut; s.todSetHour(12.5, {}); s.stepWeather(0.1); const a = o[F.tr]; s.wx.sky = 'night'; let worst = 0, prev = a, k = 0; for (let i = 0; i < 30; i++) { s.stepWeather(0.1); worst = Math.max(worst, Math.abs(o[F.tr] - prev)); prev = o[F.tr]; k++; } return { a, end: o[F.tr], worst: +worst.toFixed(3) }`);
    ok('picking Night from Day fades over about 1.6 s with no single large step', xf.worst < 0.12 && xf.end < xf.a - 0.5, xf);
    await b.ev("__sc.todSetHour(17.0, {}); __sc.stepWeather(0.1); 1");
    await b.ev("if (__sc.renderer.render0) { __sc.renderer.render = __sc.renderer.render0; } 1");
    if (SHOTS) {
      await startBattle();
      await b.ev("(() => { const s = __sc; s.todSetMode('off'); s.todSetHour(18.45, {}); s.tod.xf = 1; s.tod.force = true; s.stepWeather(0.1); return 1 })()"); await tpTo('Mountain lake', 6, 0); await b.ev("(() => { const s = __sc, d = s.todRaw; s.fp.yaw = Math.atan2(d[s.SKF.sx], d[s.SKF.sz]); s.fp.pitch = 0.16; return 1 })()"); await sleep(2500);
      fs.mkdirSync(path.join(ROOT, 'docs'), { recursive: true }); await b.shot(SHOT('night_p1_dusk.png')); log('dusk shot saved');
    }
  }

  if (run('part2')) {
    log('part 2: lights');
    await b.ev("if (!__sc.renderer.render0) { __sc.renderer.render0 = __sc.renderer.render.bind(__sc.renderer); } __sc.renderer.render = () => {}; 1");   // logic needs no picture; it keeps the frame loop quiet on a software renderer
    await startBattle(); await b.ev("document.getElementById('help').hidden = true; 1", true);
    await b.ev("(() => { const s = __sc; s.todSetMode('off'); s.todSetHour(1.0, { moon: true }); s.tod.xf = 1; s.tod.force = true; s.stepWeather(0.1); return 1 })()");
    // ---- the beam texture
    const png = await b.ev("__sc.LIGHT.beamTex.userData.cv.toDataURL('image/png')"); fs.mkdirSync(path.join(ROOT, 'docs'), { recursive: true }); fs.writeFileSync(SHOT('flashlight_beam.png'), Buffer.from(png.split(',')[1], 'base64')); log('beam texture saved');
    const bt = await J("const t = __sc.LIGHT.beamTex, cv = t.userData.cv, c = cv.getContext('2d'); const px = (x, y) => Array.from(c.getImageData(x, y, 1, 1).data).slice(0, 3); return { centre: px(128, 128), spill: px(128 + 58, 128), ring: px(128 + 97, 128), corona: px(128 + 115, 128), edge: px(254, 128), w: cv.width }");
    const lum = (a) => (a[0] + a[1] + a[2]) / 3;
    ok('the beam texture has a bright hot spot, a softer spill, a darker thin ring, a faint corona and a dark edge', lum(bt.centre) > 230 && lum(bt.spill) < lum(bt.centre) - 40 && lum(bt.ring) < lum(bt.spill) && lum(bt.corona) > lum(bt.ring) && lum(bt.corona) < lum(bt.spill) && lum(bt.edge) < 12, bt);
    // ---- budget: the pool is fixed, and a flood of requests never lights more than the cap
    const caps = await J("const L = __sc.LIGHT; return { cap: L.cap, spots: L.spots.length, pts: L.pts.length }");
    ok('desktop: 12 real lights in the pool (4 spot, 8 point)', caps.cap === 12 && caps.spots + caps.pts === 12 && caps.spots === 4, caps);
    const bud = await J(`const s = __sc, L = s.LIGHT, fc = s.mode === 'god' ? s.god.tgt : s.camera.position; let worst = 0, firstSeen = null;
      for (let i = 0; i < 400; i++) { L.nW = 0; for (let k = 0; k < 60; k++) s.lightWant('t' + k, 'point', fc.x + (k % 10) * 6, 3, fc.z + Math.floor(k / 10) * 6, 1, 0.9, 0.7, 500, 30, 1, { glow: 1, pool: 5 }); for (let k = 0; k < 10; k++) s.lightWant('sp' + k, 'spot', fc.x + k * 4, 2, fc.z + 20, 1, 1, 1, 400, 30, 1, { dx: 0, dy: -0.3, dz: 1, glow: 0.5 }); s.lightsSelect(0.016);
        worst = Math.max(worst, s.LIGHT.last.real); const mine = L.pts.filter(p => p.key && /^t[0-9]+$/.test(p.key)).map(p => p.cur); if (firstSeen === null && mine.length && Math.max(...mine) > 0) firstSeen = Math.max(...mine); }
      let nl = 0; s.scene.traverse(o => { if (o.isLight && o.intensity > 0.5 && (o.isPointLight || o.isSpotLight) && (L.pts.some(p => p.L === o) || L.spots.some(p => p.L === o))) nl++; });
      return { worst, nl, firstStep: firstSeen, glow: L.last.glow, poolsShown: L.pools.filter(p => p.visible).length }`);
    ok('desktop: 70 requests never light more than 12 real lights, and the rest are glow sprites and ground pools', bud.worst <= 12 && bud.nl <= 12 && bud.glow > 12 && bud.poolsShown > 0, bud);
    ok('a light that is switched on fades in (its first lit frame is a small fraction of 500)', bud.firstStep !== null && bud.firstStep > 0 && bud.firstStep < 150, bud.firstStep);
    // ---- the torch: the full stop key, the beam, the budget slot
    await b.ev("(() => { const s = __sc; s.todSetHour(1.0, {}); s.LIGHT.torchOn = false; s.fp.veh = null; return 1 })()"); await sleep(300);
    await press('.', 'Period', 190, '.');
    const tr = await J("const s = __sc, L = s.LIGHT, sp = L.spots[0]; for (let i = 0; i < 40; i++) { s.stepWeather(0.1); s.lightsTick(0.1); } return { on: L.torchOn, cur: sp.cur, map: !!sp.L.map, shadow: sp.L.castShadow, dist: sp.L.distance, cone: L.cone.visible }");
    ok('the full stop key switches the torch on: spot slot 0 lights with the beam texture (range under 40 m, soft shadow on desktop)', tr.on && tr.cur > 150 && tr.map && tr.shadow && tr.dist >= 25 && tr.dist <= 40, tr);
    await press('.', 'Period', 190, '.'); const tr2 = await J("const s = __sc, L = s.LIGHT; for (let i = 0; i < 60; i++) { s.stepWeather(0.1); s.lightsTick(0.1); } return { on: L.torchOn, cur: L.spots[0].cur }"); ok('the key again switches it off, and it fades out', !tr2.on && tr2.cur < 5, tr2);
    // flicker only when damaged
    const fk = await J("const s = __sc; const run = (hp) => { let mn = 9, mx = -9; for (let i = 0; i < 400; i++) { const k = s.torchHurtK(hp, i * 0.013); mn = Math.min(mn, k); mx = Math.max(mx, k); } return [+mn.toFixed(2), +mx.toFixed(2)]; }; return { healthy: run(100), hurt: run(20), edge: run(35) }");
    ok('the torch is steady at full health and flickers only when badly hurt', fk.healthy[0] === 1 && fk.healthy[1] === 1 && fk.edge[0] === 1 && fk.hurt[0] < 0.3 && fk.hurt[1] > 0.9, fk);
    await b.ev("(() => { __sc.fp.p.hp = 100; __sc.LIGHT.torchOn = false; return 1 })()");
    // ---- vehicles: headlights auto at night, off by day, toggle
    const veh = await J("const s = __sc, v = s.BVL.find(v => !v.heli && !v.dead); return v ? { id: v.id, key: v.key } : null");
    ok('there is a ground vehicle to test with', !!veh, veh);
    if (veh) {
      const tickJ = (n) => `for (let i = 0; i < ${n}; i++) { s.stepWeather(0.1); s.lightsTick(0.1); }`;
      const at = (hr) => `(() => { const s = __sc, v = s.BVL.find(v => v.id === ${veh.id}), me = s.fp.p; v.x = s.camera.position.x + 8; v.z = s.camera.position.z + 8; v.y = s.standY(v.x, v.z); s.todSetHour(${hr}, {}); s.tod.xf = 1; s.tod.force = true; return 1 })()`;
      await b.ev(at(12.5));
      const day = await J(`const s = __sc, v = s.BVL.find(v => v.id === ${veh.id}); ${tickJ(40)} return { on: s.vehLightsOn(v), k: v.lt ? v.lt.on : null, lamp: s.lampLevel() }`);
      ok('by day the headlights are off by default', day.on === false && day.k < 0.05 && day.lamp < 0.05, day);
      await b.ev(at(0.5));
      const nt = await J(`const s = __sc, v = s.BVL.find(v => v.id === ${veh.id}); ${tickJ(60)} return { on: s.vehLightsOn(v), k: v.lt.on, want: s.LIGHT.W.slice(0, s.LIGHT.nW).some(w => w.key === 'veh' + v.id), lens: v.lt.hl.map(m => m.material.type === 'MeshBasicMaterial') }`);
      ok('at night they come on by themselves (auto-on): lenses lit and a spot light asked for', nt.on === true && nt.k > 0.9 && nt.lens.every(Boolean) && nt.want, nt);
      const tg = await J(`const s = __sc, v = s.BVL.find(v => v.id === ${veh.id}); s.fp.veh = v; s.torchToggle(); const off = { user: v.hlUser, on: s.vehLightsOn(v) }; s.torchToggle(); const on = { user: v.hlUser, on: s.vehLightsOn(v) }; s.torchToggle(); s.fp.veh = null; return { off, on, again: v.hlUser }`);
      if (!tg) log('toggle error: ' + JSON.stringify(b.errs.slice(-3)));
      ok('the key and the Light button toggle the headlights in a vehicle (off, on, off)', tg && tg.off.on === false && tg.on.on === true && tg.again === false, tg);
      await b.ev(`(() => { const s = __sc, v = s.BVL.find(v => v.id === ${veh.id}); v.hlUser = undefined; return 1 })()`);
    }
    // ---- fires cast flickering light through the same budget
    await b.ev("(() => { const s = __sc; s.todSetHour(0.5, {}); s.tod.xf = 1; s.tod.force = true; s.stepWeather(0.1); return 1 })()");
    const fire = await J("const s = __sc; s.HEATP.push({ x: s.fp.p.x + 12, z: s.fp.p.z, r: 5, p: 18, t: 30 }); s.LIGHT.nW = 0; s.lightsTick(0.1); const w = s.LIGHT.W.filter(w => /^hp/.test(w.key)); return { n: w.length, I: w[0] && w[0].I }");
    ok('a burning patch asks for a warm flickering light', fire.n >= 1 && fire.I > 100, fire);
    // ---- bases: light towers and floodlights, powered by a generator
    const base = await J(`const s = __sc, L = s.LIGHT, out = []; for (const p of s.BATTLE.points) { const fx = L.fix.filter(f => f.p === p); out.push({ n: p.name, type: p.type, owner: p.owner, gen: !!(p.lights && p.lights.gen), towers: fx.filter(f => f.kind === 'tower').length, flood: fx.filter(f => f.kind === 'flood').length, lamps: fx.filter(f => f.kind === 'lamp').length, strings: fx.filter(f => f.kind === 'string').length }); } return out`);
    log('point lighting: ' + base.map(x => `${x.n}[${x.type}] ${x.gen ? 'gen ' : ''}T${x.towers} F${x.flood} L${x.lamps} S${x.strings}`).join(' | '));
    const hq = base.find(x => x.type === 'hq' && x.owner), dep = base.find(x => x.type === 'depot' || x.type === 'strongpoint' || x.type === 'airfield' || x.type === 'harbour');
    ok('every point has night lighting suited to its type (light towers on the big ones, lamps on all)', base.every(x => x.lamps + x.towers + x.flood + x.strings > 0) && hq && hq.towers >= 1 && hq.gen && (hq.flood >= 1 || hq.lamps >= 1), base.map(x => [x.n, x.towers, x.flood, x.lamps, x.strings].join('/')));
    if (hq) {
      await b.ev("(() => { const s = __sc; s.todSetHour(0.5, {}); s.tod.xf = 1; s.tod.force = true; return 1 })()");
      const blk = await J(`const s = __sc, L = s.LIGHT, p = s.BATTLE.points.find(q => q.name === ${JSON.stringify(hq.n)}); const run = (n) => { for (let i = 0; i < n; i++) { s.stepWeather(0.1); s.lightsTick(0.1); } };
        p.owner = 'blue'; p._lo = 'blue'; for (const f of L.fix) if (f.p === p) { f.dead = false; f.hp = f.hp0; } if (p.lights.gen) p.lights.gen.dead = false; p.outageT = 0; run(60); const fx = L.fix.filter(f => f.p === p && f.kind !== 'gen'), lit0 = fx.filter(f => f.on > 0.9).length, total = fx.length;
        const flood = fx.find(f => f.kind === 'flood'); if (flood) { s.fixDamage(flood, 999, flood.x, flood.y, flood.z); } run(60); const lit1 = fx.filter(f => f.on > 0.9).length, floodOn = flood ? flood.on : null;
        const gen = p.lights.gen; s.fixDamage(gen, 9999, gen.x, gen.y, gen.z); run(80); const lit2 = fx.filter(f => f.on > 0.05).length;
        return { total, lit0, lit1, floodOn, lit2, gen: { dead: gen.dead } }`);
      ok('a light tower base is lit at night when it is owned and its generator runs', blk.lit0 === blk.total && blk.total >= 3, blk);
      ok('a floodlight can be shot out on its own (the others stay lit)', blk.floodOn !== null && blk.floodOn < 0.5 && blk.lit1 === blk.total - 1, blk);
      ok('destroying the generator blacks the whole point out', blk.gen.dead && blk.lit2 === 0, blk);
      const cap = await J(`const s = __sc, L = s.LIGHT, p = s.BATTLE.points.find(q => q.name === ${JSON.stringify(dep ? dep.n : hq.n)}); const run = (n) => { for (let i = 0; i < n; i++) { s.stepWeather(0.1); s.lightsTick(0.1); } };
        for (const f of L.fix) if (f.p === p) { f.dead = false; f.hp = f.hp0; } if (p.lights.gen) p.lights.gen.dead = false;
        p.owner = 'blue'; p._lo = 'blue'; p.outageT = 0; run(80); const fx = L.fix.filter(f => f.p === p && f.gen && f.kind !== 'gen'); const a = fx.filter(f => f.on > 0.9).length; p.owner = 'red'; run(3); run(60); const b2 = fx.filter(f => f.on > 0.05).length; const out = p.outageT > s.simTime(); p.outageT = 0; run(80); const c = fx.filter(f => f.on > 0.9).length; return { n: fx.length, a, b2, out, c }`);
      ok('capturing a point cuts its power for a while, then the new owner has light', cap.n >= 1 && cap.a === cap.n && cap.b2 === 0 && cap.out && cap.c === cap.n, cap);
      const aim = await J(`const s = __sc, L = s.LIGHT, f = L.fix.find(f => f.kind === 'flood' && !f.dead) || L.fix.find(f => f.kind === 'lamp' && !f.dead); if (!f) return null; const o = { x: f.x - 12, y: f.y, z: f.z }, d = { x: 1, y: 0, z: 0 }; const h = s.lightFixAim(o, d, 60); return { hit: !!h && h.ref === f, t: h && h.t }`);
      ok('a bullet ray finds a lamp head (floodlights are shootable)', aim && aim.hit, aim);
    }
    // ---- lit windows after dusk
    await b.ev("(() => { const s = __sc; s.todSetHour(0.5, {}); s.tod.xf = 1; s.tod.force = true; s.LIGHT.winT = 0; for (let i = 0; i < 25; i++) { s.stepWeather(0.1); s.lightsTick(0.1); } return 1 })()");
    const win = await J("const L = __sc.LIGHT, im = L.win; if (!im) return { built: false }; let lit = 0; const a = im.instanceColor.array; for (let i = 0; i < a.length; i += 3) if (a[i] > 0.1) lit++; return { built: true, n: im.count, lit, visible: im.visible }");
    ok('buildings show lit windows at night', win.built && win.lit > 0 && win.visible, win);
    await b.ev("(() => { const s = __sc; s.todSetHour(12.5, {}); s.tod.xf = 1; s.tod.force = true; s.LIGHT.winT = 0; for (let i = 0; i < 25; i++) { s.stepWeather(0.1); s.lightsTick(0.1); } return 1 })()");
    const win2 = await J("const L = __sc.LIGHT, im = L.win; if (!im) return { built: false }; let lit = 0; const a = im.instanceColor.array; for (let i = 0; i < a.length; i += 3) if (a[i] > 0.02) lit++; return { lit, visible: im.visible }");
    ok('and they are dark by day', win2.lit === 0 || win2.visible === false, win2);
    // ---- the pictures: a lit base, a torch beam on the ground, vehicle headlights
    if (SHOTS) {
      await b.ev("if (__sc.renderer.render0) { __sc.renderer.render = __sc.renderer.render0; } 1");
      // find a standing spot with a clear line to a target (a base from the side, the ground in front of you, a jeep)
      const view = (tx, tz, ty, dists, pitch, extra) => `(() => { const s = __sc, me = s.fp.p; const ty = ${ty === null ? 's.standY(' + tx + ', ' + tz + ') + 4' : ty}; let best = null; for (const d of ${JSON.stringify(dists)}) { for (let k = 0; k < 24 && !best; k++) { const a = k / 24 * 6.283 + 0.4, x = ${tx} + Math.cos(a) * d, z = ${tz} + Math.sin(a) * d, gy = s.standY(x, z); if (gy < 0.9 || s.footBlocked(x, z, 1.4)) continue; if (s.losFull(x, gy + 1.6, z, ${tx}, ty, ${tz})) best = { x, z }; } if (best) break; } if (!best) return 0; me.x = best.x; me.z = best.z; me.y = s.standY(me.x, me.z); s.fp.vx = s.fp.vz = 0; s.fp.stance = 0; me.stanceK = 0; s.fp.yaw = Math.atan2(${tx} - me.x, ${tz} - me.z); s.fp.pitch = ${pitch}; ${extra || ''} return 1 })()`;
      await b.ev("(() => { const s = __sc; s.todSetMode('off'); s.todSetHour(0.5, {}); s.tod.xf = 1; s.tod.force = true; s.LIGHT.torchOn = false; s.fp.p.hp = 100; s.CHEAT.god = true; return 1 })()");
      if (hq) {
        await b.ev(`(() => { const s = __sc, L = s.LIGHT, p = s.BATTLE.points.find(q => q.name === ${JSON.stringify(hq.n)}); p.outageT = 0; for (const f of L.fix) { if (f.p === p) { f.dead = false; f.hp = f.hp0; } } if (p.lights.gen) { p.lights.gen.dead = false; p.lights.gen.hp = p.lights.gen.hp0; } p.owner = 'blue'; p._lo = 'blue'; return 1 })()`);
        const pt = await J(`const s = __sc, p = s.BATTLE.points.find(q => q.name === ${JSON.stringify(hq.n)}); const tw = s.LIGHT.fix.find(f => f.p === p && f.kind === 'tower'); return tw ? { x: tw.x, z: tw.z } : { x: p.x, z: p.z }`);
        log('night point view: ' + await b.ev(view(pt.x, pt.z, null, [30, 26, 34, 22, 38], 0.1)));
        await sleep(6000); await b.shot(SHOT('night_p2_point.png')); log('night point shot saved');
      }
      // the torch on open ground, away from the lamps
      const open = await J(`const s = __sc, L = s.LIGHT; let best = null, bd = -1; for (const q of s.BATTLE.points) { for (const [dx, dz] of [[60, 0], [-60, 0], [0, 60], [0, -60], [90, 40], [-90, -40]]) { const x = q.x + dx, z = q.z + dz; if (s.standY(x, z) < 1 || s.footBlocked(x, z, 2)) continue; { let flat = true; for (const d of [4, 8, 12, 16]) { if (Math.abs(s.standY(x + Math.sin(1.0) * d, z + Math.cos(1.0) * d) - s.standY(x, z)) > 0.35 || s.footBlocked(x + Math.sin(1.0) * d, z + Math.cos(1.0) * d, 1.2)) flat = false; } if (!flat) continue; } let md = 1e9; for (const f of L.fix) md = Math.min(md, Math.hypot(f.x - x, f.z - z)); if (md > bd) { bd = md; best = { x, z }; } } } return best`);
      await b.ev(`(() => { const s = __sc, me = s.fp.p; me.x = ${open.x}; me.z = ${open.z}; me.y = s.standY(me.x, me.z); s.fp.vx = s.fp.vz = 0; s.fp.stance = 0; me.stanceK = 0; s.fp.pitch = -0.28; s.fp.yaw = 1.0; s.LIGHT._init = false; s.LIGHT.torchOn = true; s.LIGHT.kind = 'hand'; for (let i = 0; i < 60; i++) s.lightsTick(0.1); return 1 })()`); await sleep(6000);
      await b.shot(SHOT('flashlight_preview.png')); log('flashlight shot saved');
      // a jeep with its headlights on, seen from the side-front
      const jv = await J("const s = __sc; const v = s.BVL.find(v => !v.heli && !v.dead && !v.sp.tracked) || s.BVL.find(v => !v.heli && !v.dead); return v ? { id: v.id } : null");
      if (jv) {
        const placed = await b.ev(`(() => { const s = __sc, v = s.BVL.find(v => v.id === ${jv.id}), me = s.fp.p; s.LIGHT.torchOn = false; const flat = (x, z) => Math.abs(s.standY(x + 3, z) - s.standY(x - 3, z)) < 0.25 && Math.abs(s.standY(x, z + 3) - s.standY(x, z - 3)) < 0.25 && s.standY(x, z) > 1;
          for (const q of s.BATTLE.points) for (let k = 0; k < 16; k++) { const a = k / 16 * 6.283, jx = q.x + Math.cos(a) * 46, jz = q.z + Math.sin(a) * 46; if (!flat(jx, jz) || s.footBlocked(jx, jz, 4)) continue;
            for (let m = 0; m < 12; m++) { const bb = m / 12 * 6.283, px = jx + Math.cos(bb) * 15, pz = jz + Math.sin(bb) * 15, gy = s.standY(px, pz); if (gy < 1 || s.footBlocked(px, pz, 1.4)) continue; if (!s.losFull(px, gy + 1.6, pz, jx, s.standY(jx, jz) + 1, jz)) continue;
              v.x = jx; v.z = jz; v.y = s.standY(jx, jz); v.yaw = Math.atan2(px - jx, pz - jz) + 1.1; v.speed = 0; try { v.body.position.set(v.x, v.y, v.z); } catch (e) { } v.hlUser = undefined; me.x = px; me.z = pz; me.y = gy; s.fp.vx = s.fp.vz = 0; s.fp.stance = 0; me.stanceK = 0; s.fp.yaw = Math.atan2(jx - px, jz - pz); s.fp.pitch = -0.06; return 1; } } return 0; })()`);
        log('headlights view: ' + placed); await sleep(6000);
        await b.shot(SHOT('night_p2_headlights.png')); log('headlights shot saved');
      }
    }
  }


  if (run('part3')) {
    log('part 3: bots at night');
    await b.ev("if (!__sc.renderer.render0) { __sc.renderer.render0 = __sc.renderer.render.bind(__sc.renderer); } __sc.renderer.render = () => {}; 1");   // logic needs no picture; it keeps the frame loop quiet on a software renderer
    await startBattle(); await b.ev("document.getElementById('help').hidden = true; 1", true);
    // ---- the range table, as a pure function
    const T = await J(`const s = __sc, N = s.NIGHT_VIS, e0 = () => ({ x: 0, z: 0, litK: 0, run: false }); const r = (gear, e, day, dark) => +s.nightSight(gear, e, day, dark).toFixed(2); const lit = e0(); lit.litK = 1; const mv = e0(); mv.run = true; const shot = e0(); shot.lastShot = s.simT;
      return { table: N, day: r('none', e0(), 85, 0), dark: r('none', e0(), 85, 1), lit: r('none', lit, 85, 1), nv: r('nv', e0(), 85, 1), thermal: r('thermal', e0(), 85, 1), moving: r('none', mv, 85, 1), firing: r('none', shot, 85, 1), snipDark: r('none', e0(), 200, 1), snipThermal: r('thermal', e0(), 200, 1), dusk: r('none', e0(), 85, 0.5), half: r('none', { x: 0, z: 0, litK: 0.3 }, 85, 1) }`);
    log('night vision table: ' + JSON.stringify(T.table));
    ok('daylight is unchanged: 85 m', T.day === 85, T.day);
    ok('a bot at night sees a plain dark target only at the short range (about 22 m)', T.dark >= 20 && T.dark <= 25, T.dark);
    ok('a lit target is seen at the long range (the daylight range)', T.lit === 85, T.lit);
    ok('a bot with night vision sees a dark target at the long range', T.nv === 85, T.nv);
    ok('a thermal sight is a little beyond the daylight range, snipers keep 200 m or more', T.thermal > 85 && T.snipThermal >= 200 && T.snipDark < 60, { th: T.thermal, snipThermal: T.snipThermal, snipDark: T.snipDark });
    ok('a fast mover is picked out from farther (38 m), and a muzzle flash gives the shooter away (100 m)', T.moving === 38 && T.firing === 100, { moving: T.moving, firing: T.firing });
    ok('dusk blends between the two, and half-lit lies between dark and lit', T.dusk > T.dark && T.dusk < T.day && T.half > T.dark && T.half < T.lit, { dusk: T.dusk, half: T.half });
    // ---- the real senseEnemy: two soldiers on the quay
    await b.ev("(() => { const s = __sc; s.todSetMode('off'); s.todSetHour(0.5, {}); s.tod.xf = 1; s.tod.force = true; s.stepWeather(0.1); s.setNightAI('none'); s.CHEAT.god = true; for (const q of s.people.slice()) if (q.bot) s.removePerson(q); return 1 })()");
    const sense = await J(`const s = __sc; const bases = [[-60, 80], [-30, 70], [20, 75], [-100, 85], [40, 70]]; let res = null;
      for (const [bx, bz] of bases) { if (s.standY(bx, bz) < 0.5 || s.standY(bx + 70, bz) < 0.5) continue;
        const mk = (team, x, z, cls) => { const q = s.spawnBot(team, true, { x, z, cls }); if (!q) return null; q.x = x; q.z = z; q.y = s.standY(x, z); q.bot.alert = 0; q.bot.scan = 99; q.bot.cls = cls; q.bot.gear = undefined; return q; };
        const a = mk('blue', bx, bz, 'rifle'); if (!a) continue; a.heading = Math.PI / 2; const out = {}; const tgt = mk('red', bx + 15, bz, 'rifle'); if (!tgt) { s.removePerson(a); continue; }
        const at = (d, o) => { o = o || {}; tgt.x = bx + d; tgt.z = bz; tgt.y = s.standY(tgt.x, tgt.z); tgt.litK = o.lit || 0; tgt.run = !!o.run; tgt.lastShot = o.shot ? s.simTime() : -99; tgt.torch = null; return s.senseEnemy(a, a.bot) === tgt; };
        out.near = at(15); if (!out.near) { s.removePerson(a); s.removePerson(tgt); continue; }
        out.far40 = at(40); out.far60 = at(60); a.bot.gear = undefined;
        out.lit60 = at(60, { lit: 1 }); out.moving30 = at(30, { run: true }); out.moving45 = at(45, { run: true }); out.firing60 = at(60, { shot: true });
        s.setNightAI('all'); a.bot.gear = undefined; out.nv60 = at(60); out.gear = a.bot.gear; s.setNightAI('none'); a.bot.gear = undefined;
        s.todSetHour(12.5, {}); s.tod.xf = 1; s.tod.force = true; s.stepWeather(0.1); out.day60 = at(60); s.todSetHour(0.5, {}); s.tod.xf = 1; s.tod.force = true; s.stepWeather(0.1);
        s.removePerson(a); s.removePerson(tgt); res = { base: [bx, bz], ...out }; break; }
      return res`);
    ok('senseEnemy: at night a soldier with no gear sees a dark enemy at 15 m but not at 40 m or 60 m', sense && sense.near && !sense.far40 && !sense.far60, sense);
    ok('senseEnemy: the same enemy is seen at 60 m when lit, at 30 m (not 45 m) when running, and at 60 m just after firing', sense && sense.lit60 && sense.moving30 && !sense.moving45 && sense.firing60, sense);
    ok('senseEnemy: a soldier with night vision (Night vision for AI: all) sees the dark enemy at 60 m, and by day everyone does', sense && sense.nv60 && sense.gear === 'nv' && sense.day60, sense);
    // ---- gear by class and the setting
    const gear = await J(`const s = __sc, g = {}; for (const m of ['none', 'some', 'all']) { s.setNightAI(m); g[m] = {}; for (const c of ['rifle', 'smg', 'sniper', 'medic', 'heavy']) { const b = { cls: c }; g[m][c] = s.botGear({}, b); } } s.setNightAI('some'); return g`);
    ok('Night vision for AI: none gives nobody gear; some gives snipers thermal and assault soldiers night vision; all gives everyone night vision (snipers thermal)', Object.values(gear.none).every(x => x === 'none') && gear.some.sniper === 'thermal' && gear.some.rifle === 'nv' && gear.some.smg === 'nv' && gear.some.medic === 'none' && gear.all.medic === 'nv' && gear.all.sniper === 'thermal', gear);
    const ui = await J("const s = __sc; s.openBattleSetup(); const t = document.getElementById('bsBody').innerText; return { nv: /Night vision for AI/i.test(t), chips: [...document.querySelectorAll('#bsBody button')].map(b => b.textContent).filter(x => /^(None|Some|All)$/.test(x)) }");
    ok('the battle setup has Night vision for AI: none, some, all', ui.nv && ui.chips.length >= 3, ui);
    await b.ev("document.getElementById('bSetup').hidden = true; 1");
    // ---- the player is a target under the same rules
    const pl = await J("const s = __sc, me = s.fp.p; s.LIGHT.torchOn = false; me.litK = 0; const off = s.nightSight('none', me, 85, 1); s.LIGHT.torchOn = true; const on = s.nightSight('none', me, 85, 1); s.LIGHT.torchOn = false; return { off: +off.toFixed(1), on: +on.toFixed(1) }");
    ok('a lit player (torch on) is seen farther than a dark one', pl.on > pl.off + 30 && pl.off < 40, pl);
    // ---- torches: sparing, never with night gear
    const tor = await J(`const s = __sc; s.setNightAI('some'); s.CHEAT.god = true; for (const q of s.people.slice()) if (q.bot) s.removePerson(q); const qs = []; for (let i = 0; i < 24; i++) { const q = s.spawnBot(i % 2 ? 'blue' : 'red', true, { x: -60 + (i % 8) * 6, z: 80 + Math.floor(i / 8) * 6, cls: ['rifle', 'smg', 'sniper', 'medic', 'heavy', 'engineer'][i % 6] }); if (q) { q.bot.alert = 0; q.bot.tgt = null; q.order = { x: 0, z: 0 }; q.bot.hint = null; q.bot.supp = 0; qs.push(q); } }
      for (let i = 0; i < 40; i++) { s.LIGHT.btT = 0; s.LIGHT.nW = 0; s.botLightTick(1.1); for (const q of qs) q.torch && (q.torch.roll = 0); } const on = qs.filter(q => q.torch && q.torch.on); const gearOn = on.filter(q => s.botGear(q, q.bot) !== 'none').length; const dayMax = on.length;
      s.todSetHour(12.5, {}); s.tod.xf = 1; s.tod.force = true; s.stepWeather(0.1); for (let i = 0; i < 5; i++) { s.LIGHT.btT = 0; s.botLightTick(1.1); } const dayOn = qs.filter(q => q.torch && q.torch.on).length; s.todSetHour(0.5, {}); s.tod.xf = 1; s.tod.force = true; s.stepWeather(0.1);
      for (const q of qs) s.removePerson(q); return { n: qs.length, on: dayMax, gearOn, dayOn, cap: Math.max(2, Math.round(s.BATTLE.size * 0.25)) }`);
    ok('bots use torches sparingly (at most a quarter), never with night gear, and not by day', tor.on >= 1 && tor.on <= tor.cap && tor.gearOn === 0 && tor.dayOn === 0, tor);
  }
  const e = b.errs.filter(x => !/favicon|Failed to load resource|net::ERR|WebGL|GPU stall|ReadPixels/.test(x));
  ok('no console errors', e.length === 0, e.slice(0, 5));

  if (run('part2')) {
    // phone edition: the pool is 4 (1 spot, 3 point) and a flood of requests stays under it. One Chrome at a time: the desktop one is closed first.
    await b.close(); const pb = await launch({ ...PROFILES.portrait, extraArgs: ['--autoplay-policy=no-user-gesture-required'] });
    try {
      if (!await loadGame(pb, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=phone`)) throw new Error('phone no load');
      await pb.ev("document.getElementById('help').hidden = true; 1", true);
      const pj = async (expr) => { const r = await pb.ev(`JSON.stringify((()=>{ ${expr} })())`); return r ? JSON.parse(r) : null; };
      const caps = await pj("const L = __sc.LIGHT; return { cap: L.cap, spots: L.spots.length, pts: L.pts.length }");
      ok('phone: 4 real lights in the pool (1 spot, 3 point)', caps.cap === 4 && caps.spots === 1 && caps.pts === 3, caps);
      const bud = await pj(`const s = __sc, L = s.LIGHT, fc = s.camera.position; let worst = 0; for (let i = 0; i < 120; i++) { L.nW = 0; for (let k = 0; k < 40; k++) s.lightWant('t' + k, 'point', fc.x + (k % 8) * 6, 3, fc.z + Math.floor(k / 8) * 6, 1, 0.9, 0.7, 500, 30, 1, { glow: 1, pool: 5 }); for (let k = 0; k < 6; k++) s.lightWant('sp' + k, 'spot', fc.x + k * 4, 2, fc.z + 20, 1, 1, 1, 400, 30, 1, { dx: 0, dy: -0.3, dz: 1, glow: 0.5 }); s.lightsSelect(0.1); worst = Math.max(worst, L.last.real); } return { worst, shadow: L.spots[0].L.castShadow, glowPool: L.glow.length }`);
      ok('phone: 46 requests never light more than 4 real lights, no shadow-casting light, a smaller glow pool', bud.worst <= 4 && bud.shadow === false && bud.glowPool <= 16, bud);
      const btn = await pj("const e = document.getElementById('fpLight'); return { has: !!e }");
      ok('phone: the Light button exists', btn.has, btn);
      const e2 = pb.errs.filter(x => !/favicon|Failed to load resource|net::ERR|WebGL|GPU stall|ReadPixels/.test(x)); ok('phone: no console errors', e2.length === 0, e2.slice(0, 4));
    } finally { await pb.close(); }
  }
} catch (err) { console.log('ERR ' + (err && err.stack || err)); fail.push('exception'); }
finally { await b.close(); await srv.close(); }
console.log(fail.length ? `\n${fail.length} FAILED: ${fail.join('; ')}` : '\nALL OK'); process.exit(fail.length ? 1 : 0);
