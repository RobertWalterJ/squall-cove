// Real screenshots of the gunship sensor station. usage: node qa/station-shots.mjs desktop|portrait|landscape [outDir=qa/shots] [modes=thermal,night,colour; each may be mode[:phos][:sky][:fx], e.g. night:white:night:fx]
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
  for (const spec of modes) {
    const [m, phos = 'green', sky = '', fx = ''] = spec.split(':');
    await b.ev(`(() => { const sc = __sc, S = sc.STN; ${sky ? `sc.wx.sky = '${sky}';` : ''} sc.stnSetPhos('${phos}', true); sc.stnSetMode('${m}', true); sc.stnStep(0.05); return 1; })()`);
    if (sky) await sleep(9000);
    if (fx) await b.ev(`(() => { const sc = __sc, S = sc.STN, h = (x, z) => Math.max(sc.heightAt(x, z), 0); const R = (a, c) => a + Math.random() * (c - a);
      for (let k = 0; k < 14; k++) { const x0 = S.ax + R(-30, 30), z0 = S.az + R(-30, 30), x1 = S.ax + R(-6, 6), z1 = S.az + R(-6, 6); sc.addTracer(x0, h(x0, z0) + 1.5, z0, x1, h(x1, z1) + 1, z1, { k: k % 3 ? 'rifle' : 'mg' }); }
      for (let k = 0; k < 5; k++) { const x = S.ax + R(-14, 14), z = S.az + R(-14, 14); sc.muzzleFlash(x, h(x, z) + 1.5, z, 1, 0, 0, k % 2 ? 'cannon' : 'rifle', 'blue'); }
      sc.blast(S.ax + 12, h(S.ax + 12, S.az), S.az - 6, { R: 7, dmg: 0, crater: 0, depth: 0, owner: null }); sc.burnArea(S.ax - 9, S.az + 8, 7);
      if (${m === 'night' ? 'true' : 'false'}) sc.flareStart(S.ax - 25, h(S.ax - 25, S.az) + 60, S.az + 10);
      for (let i = 0; i < 2; i++) { sc.updateTracers(0.015); sc.stnStep(0.015); } return 1; })()`);
    await b.ev(`(() => { const sc = __sc; sc.renderer.render = window.__realRender; sc.stnRender(); const cv = sc.renderer.domElement, c2 = document.createElement('canvas'); c2.width = 160; c2.height = 90; const g = c2.getContext('2d'); g.drawImage(cv, 0, 0, 160, 90); const d = g.getImageData(0, 0, 160, 90).data; let sum = 0, hi = 0; for (let i = 0; i < d.length; i += 4) { const l = (d[i] + d[i + 1] + d[i + 2]) / 3; sum += l; if (l > 235) hi++; } let sl = -1; try { const R = sc.stnR, w = R.rw, h = R.rh, buf = R.half ? new Uint16Array(w * h * 4) : new Uint8Array(w * h * 4); sc.renderer.readRenderTargetPixels(R.rt, 0, 0, w, h, buf); let ls = 0, n = 0; for (let i = 0; i < buf.length; i += 4 * 37) { const f = (k) => R.half ? sc.THREE.DataUtils.fromHalfFloat(buf[i + k]) : buf[i + k] / 255; ls += 0.2126 * f(0) + 0.7152 * f(1) + 0.0722 * f(2); n++; } sl = +(ls / n).toFixed(4); } catch (e) { sl = 'err ' + e.message; }
      window.__probe = { sceneLum: sl, mean: +(sum / 14400).toFixed(1), brightFrac: +(hi / 14400).toFixed(3), tracersActive: sc.tracers.act.reduce((a, b) => a + b, 0) }; return 1; })()`);
    log('probe ' + JSON.stringify(await b.ev('window.__probe')));
    await sleep(1200); const f = path.join(out, `station_${P.name}_${spec.replace(/:/g, '-')}.png`); if (!process.env.NOSHOT) { await b.shot(f); log('shot ' + f); }
    await b.ev("__sc.renderer.render = () => {}; 1");
  }
  log('errors ' + JSON.stringify(b.errs.slice(0, 5)));
} catch (e) { log('ERR ' + e.message); } finally { await b.close(); await srv.close(); log('done'); }
