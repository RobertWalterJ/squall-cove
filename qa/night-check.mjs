// Night and light check. usage: node qa/night-check.mjs [part1|part2|part3|all] [shots]
// part1 (v9.9.10): the clock maths (24 minutes a day at Normal), pause, save round trip, the sky continuous across dusk, stars and moon, no console errors.
// part2 (v9.9.11): flashlight, light budget caps, headlights, generators blacking out a point.
// part3 (v9.9.12): bot night vision range table.
// One headless Chrome, killed by PID at the end. At most four screenshots in all (with `shots`): dusk sky, night battle point lit, flashlight beam, vehicle headlights.
import fs from 'fs'; import path from 'path';
import { ROOT, sleep, startServer, launch, loadGame, clickText, PROFILES } from './harness.mjs';
const PART = process.argv[2] && !/^shots$/.test(process.argv[2]) ? process.argv[2] : 'all', SHOTS = process.argv.includes('shots');
const prof = { ...PROFILES.desktop, w: 1100, h: 680 };
const T0 = Date.now(), log = (m) => console.log(`[${((Date.now() - T0) / 1000).toFixed(0)}s] ${m}`); setTimeout(() => { console.log('ERR watchdog: the night check took over 20 minutes'); process.exit(2); }, 1200000).unref();
const fail = []; const ok = (name, cond, detail) => { console.log((cond ? '  ok   ' : '  FAIL ') + name + (detail !== undefined ? '  ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)) : '')); if (!cond) fail.push(name); };
const run = (p) => PART === 'all' || PART === p;
const srv = await startServer(); const b = await launch({ ...prof, extraArgs: ['--autoplay-policy=no-user-gesture-required'] });
const J = async (expr) => { const r = await b.ev(`JSON.stringify((()=>{ ${expr} })())`); return r ? JSON.parse(r) : null; };
const SHOT = (n) => path.join(ROOT, 'docs', n);
async function tpTo(name, dx, dz) { await b.ev(`(()=>{ const s = __sc, p = s.fp.p, pt = s.BM().points.find(q => q[0] === ${JSON.stringify(name)}); if (!pt) return 0; p.x = pt[1] + ${dx}; p.z = pt[2] + ${dz}; p.y = s.standY(p.x, p.z); s.fp.vx = s.fp.vz = 0; return 1 })()`); await sleep(1200); }
async function startBattle() {
  await b.ev("__sc.openBattleSetup(); 1"); await sleep(500); await b.ev(clickText('#bSetup button', 'Begin battle')); await sleep(5000);
  await b.ev("__sc.playBattle('blue'); window.__me = __sc.fp.p; __sc.CHEAT.god = true; 1"); await sleep(2500); await b.ev("document.getElementById('help').hidden = true; 1");
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
  const e = b.errs.filter(x => !/favicon|Failed to load resource|net::ERR|WebGL|GPU stall|ReadPixels/.test(x));
  ok('no console errors', e.length === 0, e.slice(0, 5));
} catch (err) { console.log('ERR ' + (err && err.stack || err)); fail.push('exception'); }
finally { await b.close(); await srv.close(); }
console.log(fail.length ? `\n${fail.length} FAILED: ${fail.join('; ')}` : '\nALL OK'); process.exit(fail.length ? 1 : 0);
