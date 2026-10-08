// AC-130 gunship sound and weapons check. usage: node qa/ac130-check.mjs [desktop|portrait] [simSeconds=20]
// Calls a gunship for each side in a running battle, puts many enemies under them, runs the game for N seconds of game time and reads back the Snd counters:
// plays and culls, which stems played, the peak of each voice-budget class, memory held by AC-130 buffers. One headless Chrome at a time (qa/harness.mjs).
import { sleep, startServer, launch, loadGame, clickText, PROFILES } from './harness.mjs';
const prof0 = PROFILES[process.argv[2] || 'desktop'], prof = process.argv[2] === 'portrait' ? prof0 : { ...prof0, w: 480, h: 300 }, SIM = +(process.argv[3] || 20);
const T0 = Date.now(), log = (m) => console.log(`[${((Date.now() - T0) / 1000).toFixed(0)}s] ${m}`); setTimeout(() => { console.log('ERR watchdog: test took over 25 minutes'); process.exit(2); }, 1500000).unref();
const srv = await startServer(); const b = await launch({ ...prof, extraArgs: ['--autoplay-policy=no-user-gesture-required'] }); const fail = [], info = {};
try {
  if (!await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=${prof.ed}`)) throw new Error('no load');
  await b.ev("document.getElementById('tablet').hidden=true; __sc.openBattleSetup(); 1"); await sleep(500);
  await b.ev(clickText('#bSetup button', 'Begin battle')); await sleep(5000); await b.ev("__sc.CHEAT.god=true;__sc.playBattle('blue');1"); await sleep(3000);
  await b.ev("window.dispatchEvent(new KeyboardEvent('keydown',{key:'Shift'}));1"); await sleep(1500);
  for (let k = 0; k < 40; k++) { const s = await b.ev('JSON.stringify(__sc.Snd.stats2())'); const o = JSON.parse(s); if (o.ready && o.ctx === 'running') break; await sleep(500); }
  log('audio ready'); info.audio = JSON.parse(await b.ev('JSON.stringify(__sc.Snd.stats2())'));
  const before = JSON.parse(await b.ev(`JSON.stringify({ by: Object.assign({}, __sc.Snd.by), st: Object.assign({}, __sc.AC.st), loaded: __sc.Snd.stats2().loaded })`));
  // two gunships, one per side, set into their orbit over the hot spot; every soldier of both sides is moved into a ring under them so each has many targets
  const setup = await b.ev(`(async () => { await __sc.ensureAir(); const S = __sc, hs = S.hotSpot('blue'), out = {};
    const ub = S.airSpawn('blue', 'gunship'), ur = S.airSpawn('red', 'gunship'); if (!ub || !ur) return 'nogunship';
    for (const [u, a] of [[ub, 0], [ur, Math.PI]]) { u.oa = a; u.x = hs.x + Math.cos(a) * u.orbit; u.z = hs.z + Math.sin(a) * u.orbit; u.y = 165; u.life = 400; u.hd = a + Math.PI / 2 + Math.PI / 2; }
    S.god.tgt.x = hs.x; S.god.tgt.z = hs.z;
    let n = 0; for (const q of S.people) { if (q.state === 'rag' || q.ride) continue; const a = n * 2.399, r = 25 + (n % 9) * 9; const x = hs.x + Math.cos(a) * r, z = hs.z + Math.sin(a) * r; q.x = x; q.z = z; if (q.body) q.body.position.set(x, S.standY(x, z) + q.height / 2, z); q.obj.position.set(x, S.standY(x, z) - q.footOff, z); n++; }
    return JSON.stringify({ moved: n, team: S.people.filter(q => q.bot).length, people: S.people.length, hs: [hs.x | 0, hs.z | 0] }); })()`);
  log('setup ' + setup); info.setup = setup; if (!/moved/.test(setup)) fail.push('setup: ' + setup);
  await b.ev("__sc.Snd.cnPeak={};__sc.Snd.vPeak=0;1");
  const wall0 = Date.now(); let simDone = 0;
  // the headless renderer is far slower than real time, so the game's own loop barely advances; drive the air and sound update by hand at real-time pace (audio durations are real)
  simDone = await b.ev(`new Promise(res => { const S = __sc; let sim = 0, last = performance.now(); const iv = setInterval(() => { const n = performance.now(), dt = Math.min(0.1, (n - last) / 1000); last = n; sim += dt; S.updateAir(dt); S.Snd.frame(dt); S.updateTracers(dt); if (sim >= ${SIM}) { clearInterval(iv); res(sim); } }, 25); })`);
  log('run finished'); const wall = (Date.now() - wall0) / 1000;
  const after = JSON.parse(await b.ev(`JSON.stringify({ by: Object.assign({}, __sc.Snd.by), st: Object.assign({}, __sc.AC.st), stats: __sc.Snd.stats2(), peak: __sc.Snd.cnPeak || {}, vPeak: __sc.Snd.vPeak, caps: __sc.Snd.caps, max: __sc.Snd.max,
     mb: Object.entries(__sc.Snd.bufs).filter(([k]) => k.startsWith('ac130_')).reduce((a, [k, v]) => a + v.length * 4, 0) / 1048576, nbuf: Object.keys(__sc.Snd.bufs).filter(k => k.startsWith('ac130_')).length,
     air: __sc.AIR.list.filter(u => u.kind === 'gunship').map(u => ({ team: u.team, hp: u.hp, down: u.down, shots: !!u.ac })), err: window.__acerr || null, lite: __sc.AC.lite })`));
  const played = {}; for (const k in after.by) { if (!/^ac130_/.test(k)) continue; const d = after.by[k] - (before.by[k] || 0); if (d > 0) played[k] = d; }
  const st = {}; for (const k in after.st) st[k] = after.st[k] - (before.st[k] || 0);
  console.log(`profile ${prof.name}: ${simDone.toFixed(1)} s of game time in ${wall.toFixed(0)} s wall; ${setup}`);
  console.log('engine: played', after.stats.played, 'culled', after.stats.culled, 'loaded', after.stats.loaded, 'voices now', after.stats.voices, 'peak voices', after.vPeak, 'of limit', after.max, '(ceiling', Math.floor(after.max * 1.4) + ')');
  console.log('AC-130 counters over the run:', JSON.stringify(st));
  console.log('AC-130 stems played:', JSON.stringify(played, null, 0));
  console.log('class peaks vs caps:', JSON.stringify(after.peak), 'caps', JSON.stringify(after.caps));
  console.log(`AC-130 buffers held: ${after.nbuf} stems, ${after.mb.toFixed(1)} MB decoded (lite=${after.lite})`);
  console.log('gunships:', JSON.stringify(after.air), 'errors:', after.err, 'page errors:', JSON.stringify(b.errs.slice(0, 5)));
  // ---- assertions
  const has = (re) => Object.keys(played).some(k => re.test(k));
  if (simDone < SIM * 0.6) fail.push(`only ${simDone.toFixed(1)} s of game time ran`);
  for (const c of Object.keys(after.caps)) if ((after.peak[c] || 0) > after.caps[c]) fail.push(`class ${c} peaked at ${after.peak[c]} over its cap ${after.caps[c]}`);
  if (after.vPeak > after.max * 1.4 + 1) fail.push(`voices peaked at ${after.vPeak}, over the ceiling ${Math.floor(after.max * 1.4)}`);
  if (!has(/^ac130_vulcan_start/)) fail.push('no Vulcan spin-up played'); if (!has(/^ac130_vulcan_loop/)) fail.push('no Vulcan loop played'); if (!has(/^ac130_vulcan_end/)) fail.push('no Vulcan spin-down played');
  if (!has(/^ac130_bofors_shot/)) fail.push('no Bofors shot'); if (!has(/^ac130_bofors_hit_/)) fail.push('no Bofors hit'); if (!has(/^ac130_howitzer_fire/)) fail.push('no howitzer fire'); if (!has(/^ac130_howitzer_hit/)) fail.push('no howitzer hit');
  if (!has(/^ac130_vulcan_(hit_|stitch)/)) fail.push('no Vulcan impact or stitch');
  if (SIM >= 15 && after.st.vstart < 1) fail.push('no Vulcan burst');
  const vh = ((st.vhit || 0)) / Math.max(1, simDone); if (vh > 14) fail.push(`Vulcan hits ${vh.toFixed(1)} per second, over the aggregate cap`);
  if (after.err) fail.push('AC-130 code error: ' + after.err.slice(0, 200)); if (b.errs.length) fail.push('page errors: ' + b.errs[0]);
  console.log(fail.length ? 'FAIL: ' + fail.join(' | ') : 'ok: budgets held, all families played');
} catch (e) { console.log('ERR', e.message); fail.push(e.message); } finally { await b.close(); await srv.close(); }
process.exit(fail.length ? 1 : 0);
