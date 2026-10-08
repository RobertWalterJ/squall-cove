// Pictures for v9.8: overview symbols, first person compass and corner map, the Quick map (desktop 1400x860); first person on a phone (landscape 844x390 or portrait 390x844).
// usage: node qa/symbols-shots.mjs desktop|landscape|portrait [outDir=qa/shots]      The software renderer is slow: each picture waits for a frame, then forces one.
import fs from 'fs'; import path from 'path';
import { ROOT, sleep, startServer, launch, loadGame, clickText, PROFILES } from './harness.mjs';
const P = PROFILES[process.argv[2] || 'desktop'], out = path.resolve(process.argv[3] || path.join(ROOT, 'qa', 'shots')); fs.mkdirSync(out, { recursive: true });
const T0 = Date.now(), log = (...a) => console.log(`[${((Date.now() - T0) / 1000).toFixed(0)}s]`, ...a); setTimeout(() => { console.log('ERR watchdog'); process.exit(2); }, 900000).unref();
const srv = await startServer(); const b = await launch(P);
const shot = async (name) => { await b.ev("__sc.SA.frame(0.016); __sc.renderer.render(__sc.scene, __sc.camera); 1", true); const f = path.join(out, `sym_${P.name}_${name}.png`); await b.shot(f); log('shot', f); };
try {
  if (!await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=${P.ed}`)) throw new Error('no load');
  await b.ev("document.getElementById('tablet').hidden=true; __sc.openBattleSetup(); 1"); await sleep(500);
  await b.ev(clickText('#bSetup button', 'Begin battle')); await sleep(5000); await b.ev("__sc.CHEAT.god=true;__sc.playBattle('blue');1"); await sleep(4000);
  // a few hostile soldiers close to the player's squad so the strip, the corner map and the overview all have something to show
  await b.ev(`(() => { const S = __sc, mv = (q, x, z) => { q.x = x; q.z = z; if (q.body) q.body.position.set(x, S.standY(x, z) + q.height / 2, z); q.obj.position.set(x, S.standY(x, z) - q.footOff, z); };
    const me = S.fp.p, red = S.people.filter(q => q.bot && !q.ride && q.bot.team === 'red' && q.state !== 'rag'); red.slice(0, 3).forEach((q, i) => mv(q, me.x + Math.sin(S.fp.yaw) * (28 + i * 9) + Math.cos(S.fp.yaw) * (i - 1) * 14, me.z + Math.cos(S.fp.yaw) * (28 + i * 9) - Math.sin(S.fp.yaw) * (i - 1) * 14)); return 1; })()`);
  await sleep(2500); await b.ev("__sc.SA.S.spT = 0; __sc.SA.S.ctT = 0; __sc.SA.contacts(__sc.SA.origin()[0], __sc.SA.origin()[1]); 1");
  // first person: compass, corner map, hint
  await b.ev("document.getElementById('fpHint').textContent = ''; __sc.fp.yaw = __sc.fp.yaw; 1"); await sleep(2500); await shot('fp');
  if (P.name === 'desktop') {
    await b.ev("__sc.SA.qmOpen(); 1"); await sleep(2500); await shot('quickmap');
    await b.ev("__sc.SA.qmClose(); 1");
    await b.ev(`(() => { const S = __sc; S.exitFP(); const ps = S.people.filter(q => q.bot && !q.ride && q.bot.team === 'blue' && q.state !== 'rag'), b0 = ps[0]; S.BATTLE.spec = null; S.god.follow = null; S.god.fly = null; S.god.tgt.x = b0.x + 20; S.god.tgt.z = b0.z + 10; S.god.dist = 420; S.setSel([b0]); return 1; })()`);
    await sleep(5000); await shot('overview');
  }
} catch (e) { console.log('ERR ' + (e && e.stack || e)); } finally { console.log('errors', JSON.stringify(b.errs.slice(0, 4))); await b.close(); await srv.close(); process.exit(0); }
