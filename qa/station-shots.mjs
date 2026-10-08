// Real screenshots of the gunship sensor station. usage: node qa/station-shots.mjs desktop|portrait|landscape [outDir=qa/shots] [modes=thermal,night,colour]
// The software renderer needs many seconds a frame, so the game's own draw is off while the scene is set up; each shot is one manual render then a capture (the qa/fx-shots.mjs approach).
import fs from 'fs'; import path from 'path';
import { ROOT, sleep, startServer, launch, loadGame, clickText, PROFILES } from './harness.mjs';
const P = PROFILES[process.argv[2] || 'desktop'], out = path.resolve(process.argv[3] || path.join(ROOT, 'qa', 'shots')), modes = (process.argv[4] || 'thermal,night,colour').split(',');
fs.mkdirSync(out, { recursive: true }); const T0 = Date.now(), log = (m) => console.log(`[${((Date.now() - T0) / 1000).toFixed(0)}s] ${m}`); setTimeout(() => { console.log('ERR watchdog'); process.exit(2); }, 1200000).unref();
const srv = await startServer(); const b = await launch({ ...P, extraArgs: ['--autoplay-policy=no-user-gesture-required'] });
try {
  if (!await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=${P.ed}`)) throw new Error('no load');
  await b.ev("document.getElementById('tablet').hidden=true; __sc.openBattleSetup(); 1"); await sleep(500); await b.ev(clickText('#bSetup button', 'Begin battle')); await sleep(5000);
  await b.ev("__sc.CHEAT.god=true; __sc.playBattle('blue'); 1"); await sleep(2500); await b.ev("document.getElementById('help').hidden=true; __sc.exitFP(); 1"); await sleep(500);
  await b.ev("window.__realRender = __sc.renderer.render.bind(__sc.renderer); __sc.renderer.render = () => {}; 1");
  log(await b.ev(`(() => { const sc = __sc; sc.AIR.list.length = 0; sc.stnOpenFor('blue'); const S = sc.STN, hs = sc.hotSpot('blue'); sc.stnSetAim(hs.x, hs.z); S.zoom = S.zoomT = 4.5; for (let i = 0; i < 30; i++) { sc.updateAir(0.1); sc.stnStep(0.1); } return 'open ' + S.on + ' ' + S.state + ' contacts ' + S.contacts.length + ' range ' + Math.round(S.range); })()`));
  await sleep(1500);
  for (const m of modes) {
    await b.ev(`(() => { const sc = __sc, S = sc.STN; sc.stnSetMode('${m}', true); ${m === 'colour' ? "sc.stnSelect(2); for (let i = 0; i < 6; i++) sc.stnStep(0.05); S.fireKey = true; for (let i = 0; i < 12; i++) { sc.updateAir(0.05); sc.updateTracers(0.05); sc.stnStep(0.05); } S.fireKey = false;" : "sc.stnStep(0.05);"} sc.renderer.render = window.__realRender; sc.stnRender(); return 1; })()`);
    await sleep(1200); const f = path.join(out, `station_${P.name}_${m}.png`); await b.shot(f); log('shot ' + f);
    await b.ev("__sc.renderer.render = () => {}; 1");
  }
  log('errors ' + JSON.stringify(b.errs.slice(0, 5)));
} catch (e) { log('ERR ' + e.message); } finally { await b.close(); await srv.close(); log('done'); }
