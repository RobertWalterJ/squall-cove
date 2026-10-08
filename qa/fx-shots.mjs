// Visual check of tracers, flashes, impacts, blasts, horizon flashes in first person on the Port battle map.
// usage: node qa/fx-shots.mjs desktop|landscape [outDir=qa/shots] [only=name,name]
// The software renderer runs at ~1 frame a second, so effects that live 0.1 s would be gone before a frame draws them.
// The test therefore slows the particle update (window.__fxScale) and keeps trail tracers alive; it changes nothing in the game files.
import fs from 'fs'; import path from 'path';
import { ROOT, sleep, startServer, launch, loadGame, clickText, PROFILES } from './harness.mjs';
const P = PROFILES[process.argv[2] || 'desktop'], out = path.resolve(process.argv[3] || path.join(ROOT, 'qa', 'shots'));
const only = process.argv[4] ? process.argv[4].split(',') : null;
fs.mkdirSync(out, { recursive: true });
const srv = await startServer(); const b = await launch(P);
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);
const want = (n) => !only || only.includes(n);
try {
  const ok = await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=${P.ed}`);
  log('loaded', ok); if (!ok) throw new Error('no load');
  await b.ev("(document.getElementById('help')||{}).hidden=true;1", true);
  await b.ev("__sc.openCommand();1"); await sleep(500);
  await b.ev("document.getElementById('tablet').hidden=true; __sc.openBattleSetup(); 1"); await sleep(700);
  log(await b.ev(clickText('#bSetup button', 'Begin battle'))); await sleep(6000);
  await b.ev("__sc.CHEAT.god=true; 1", true);
  await b.ev("__sc.playBattle('blue');1"); await sleep(3000);
  await b.ev(`(()=>{ const sc=__sc; try{ document.getElementById('fpHint').style.display='none'; }catch(e){}
    window.__fxScale = 1; window.__fxUpd = [sc.fxG.update, sc.fxS.update]; for (const f of [sc.fxG, sc.fxS]) { const u = f.update; f.update = (dt) => u(dt * window.__fxScale); }
    if (sc.fp.p && sc.fp.p.state === 'rag') sc.fpJumpOrGetUp(); return 1 })()`);
  const st = () => b.ev("JSON.stringify({on:__sc.fp.on,rag:__sc.fp.p&&__sc.fp.p.state,x:+__sc.camera.position.x.toFixed(1),y:+__sc.camera.position.y.toFixed(1),z:+__sc.camera.position.z.toFixed(1),yaw:+__sc.fp.yaw.toFixed(2),t:+__sc.simTime().toFixed(2)})");
  log('fp', await st()); await sleep(4000); log('fp+4s', await st());
  await b.ev(`window.__fxT = { kinds: ['rifle','smg','mg','vulcan','hmg','aa','cannon','naval'], on: false, dist: 38,
    start(rows, dist){ this.on = true; this.rows = rows; this.dist = dist || 38; }, stop(){ this.on = false; },
    tick(){ if(!this.on) return; const sc = __sc, T = sc.tracers; const cp = sc.camera.position, y = sc.fp.yaw, f = [Math.sin(y), Math.cos(y)], r = [Math.cos(y), -Math.sin(y)], K = this.kinds, n = K.length, D = this.dist;
      this.rows.forEach((team, ri) => K.forEach((k, ki) => { const sd = ri === 0 ? -1 : 1, lat = sd * D * 0.08, dy = ((n - 1) / 2 - ki) * D * 0.055 + 1.0;
        const x1 = cp.x + f[0] * D + r[0] * lat, z1 = cp.z + f[1] * D + r[1] * lat, L = 60 * sd;
        sc.addTracer(x1 + r[0] * L, cp.y + dy, z1 + r[1] * L, x1, cp.y + dy, z1, { k, team, trail: true }); })); T.age.fill(0); T.life.fill(5); } };
    setInterval(() => __fxT.tick(), 100); 1`);
  await b.ev(`window.__fxFind = (surf) => { const sc = __sc; for (let r = 0; r < 4000; r++) { const x = (Math.random() * 2 - 1) * 330, z = (Math.random() * 2 - 1) * 330; const h0 = sc.heightAt(x, z); if (h0 < 0.5) continue; let ok = true; for (let i = 0; i <= 3 && ok; i++) for (let j = -2; j <= 2; j++) { const qx = x + j * 3, qz = z - 9 - i * 4; if (sc.surfaceAt(qx, qz) !== surf || Math.abs(sc.heightAt(qx, qz) - h0) > 1.2) { ok = false; break; } } if (ok) return [x, z, h0]; } return null; };
    window.__fxGo = (x, z, yaw, pitch, h) => { const sc = __sc, p = sc.fp.p; p.x = x; p.z = z; p.y = Math.max(sc.heightAt(x, z), 0) + h; sc.fp.yaw = yaw; sc.fp.pitch = pitch; sc.fp.vx = sc.fp.vz = 0; sc.CHEAT.fly = true; return 1; }; 1`);
  const go = (x, z, yaw, pitch, h) => b.ev(`__fxGo(${x},${z},${yaw},${pitch},${h})`);
  const shot = async (name, wait = 350, age = 0) => { await sleep(wait); if (age) await b.ev(`(()=>{ for (const u of __fxUpd) u(${age}); return 1 })()`); await b.ev("__sc.renderer.render(__sc.scene,__sc.camera);1", true); const f = path.join(out, `fx_${P.name}_${name}.png`); await b.shot(f); log('shot', name); };
  const SCALE = (s) => b.ev(`window.__fxScale=${s};1`);
  const SEA = [60, 118];                                           // open sea south of the quay: clean sky and water behind the effects

  // 1 tracers: blue top row, red bottom row, over the sea
  if (want('tracers_near') || want('tracers_far')) {
    await go(SEA[0], SEA[1], 0, 0.02, 3); await sleep(1500);
    await b.ev("__fxT.start(['blue','red'], 38);1"); await shot('tracers_near', 1800);
    await b.ev("__fxT.start(['blue','red'], 90);1"); await shot('tracers_far', 1800);
    await b.ev("__fxT.stop();1");
  }
  // 2 muzzle flashes: particles run at 6% speed so the first frames after the shot are drawn
  await SCALE(0.01);
  const mf = (kind, team) => `(()=>{const cp=__sc.camera.position,y=__sc.fp.yaw,fx=Math.sin(y),fz=Math.cos(y); for(let i=0;i<3;i++){ const ox=(i-1)*7; const x=cp.x+fx*16+fz*ox, z=cp.z+fz*16-fx*ox; __sc.addTracer(x,cp.y-0.4,z,x+fx*80,cp.y-0.3,z+fz*80,{k:'${kind}',team:'${team}'}); } return 1})()`;
  await go(SEA[0], SEA[1], 0, 0.02, 3);
  for (const k of ['rifle', 'mg', 'hmg', 'cannon', 'naval']) { if (!want('flash_' + k)) continue; await b.ev("__sc.MZF.n=0;1"); await b.ev(mf(k, 'blue')); await shot('flash_' + k, 0, 0.03); }
  // 3 impacts, 4 per shot, on the surface named: found by scanning the map
  const imp = (kind, ref, off) => `(()=>{const cp=__sc.camera.position,y=__sc.fp.yaw,fx=Math.sin(y),fz=Math.cos(y),x=cp.x+fx*9+fz*${off},z=cp.z+fz*9-fx*${off},gy=Math.max(__sc.heightAt(x,z),0); __sc.impactFx('${kind}',${ref},{x,y:gy+0.05,z},{x:0,y:1,z:0}); return 1})()`;
  for (const [nm, surf, kind, ref] of [['sand', 'sand', 'land', 'null'], ['grass', 'grass', 'land', 'null'], ['concrete', 'concrete', 'land', 'null'], ['dirt', 'dirt', 'land', 'null'], ['metal', 'sand', 'veh', 'null'], ['wood', 'sand', 'obj', '{m:{name:"wood"}}']]) {
    if (!want('impact_' + nm)) continue; const pt = await b.ev(`JSON.stringify(__fxFind('${surf}'))`); log('spot', nm, pt); const q = JSON.parse(pt || 'null'); if (!q) continue;
    await go(q[0], q[1], Math.PI, -0.12, 1.7); await sleep(1200); for (let k = 0; k < 4; k++) await b.ev(imp(kind, ref, (k - 1.5) * 2.5)); await shot('impact_' + nm, 0, 0.18); }
  if (want('impact_water')) { await go(SEA[0], SEA[1], 0, -0.1, 2); for (let k = 0; k < 4; k++) await b.ev(imp('water', 'null', (k - 1.5) * 2.5)); await shot('impact_water', 0, 0.3); }
  // 4 blast: 40 m ahead of a spot on open ground
  if (want('blast_t0')) {
    const q = JSON.parse(await b.ev("JSON.stringify(__fxFind('sand')||__fxFind('grass'))") || 'null'); log('blast spot', JSON.stringify(q));
    if (q) {
      await go(q[0], q[1] + 12, Math.PI, 0.05, 2.5);
      await b.ev(`(()=>{const cp=__sc.camera.position,y=__sc.fp.yaw,fx=Math.sin(y),fz=Math.cos(y),x=cp.x+fx*40,z=cp.z+fz*40,gy=Math.max(__sc.heightAt(x,z),0); __sc.blast(x,gy,z,{R:12,dmg:1,crater:0,depth:0}); return 1})()`);
      await shot('blast_t0', 0, 0.08);
      await b.ev("(()=>{for(const o of __sc.SHK.list) if(o.m.visible) o.t=Math.max(o.t,o.life*0.3); return 1})()"); await shot('blast_t1', 0, 0.45);
      await SCALE(1); await b.send('Emulation.setDeviceMetricsOverride', { width: 320, height: 200, deviceScaleFactor: 1, mobile: false }); const t0 = await b.ev('__sc.simTime()'); await sleep(26000); log('sim seconds in the fire wait', ((await b.ev('__sc.simTime()')) - t0).toFixed(2)); await b.send('Emulation.setDeviceMetricsOverride', { width: P.w, height: P.h, deviceScaleFactor: 1, mobile: !!P.mobile }); await shot('blast_fire', 3000);
    }
  }
  // 5 night: horizon flashes and tracers
  if (want('horizon')) {
    await SCALE(0.01); await go(SEA[0], SEA[1], 0, 0.03, 3);
    await b.ev("(()=>{__sc.wx.sky='night'; Object.assign(__sc.wx.cur, __sc.SKIES.night); return 1})()"); await sleep(3000);
    // the same flash the battle makes on the horizon (see hzUpdate): a big one and a small one, placed in front so they are in view
    const hz = (dx, dist, big) => b.ev(`(()=>{const sc=__sc,cp=sc.camera.position,a=sc.fp.yaw+${dx},x=cp.x+Math.sin(a)*${dist},z=cp.z+Math.cos(a)*${dist},gy=Math.max(sc.heightAt(x,z),0)+3; sc.fxG.emit(x,gy,z,0,0,0,${big?0.5:0.22},${dist}*${big?0.08:0.045},0.5,[1,0.72,0.38,0.85]); return 1})()`);
    await hz(-0.35, 520, true); await hz(0.3, 700, false); await hz(0.05, 420, false); await shot('horizon_a', 0, 0.1);
    await hz(-0.2, 800, true); await hz(0.4, 450, false); await shot('horizon_b', 0, 0.2);
    await SCALE(1); await go(SEA[0], SEA[1], 0, 0.02, 3); await b.ev("__fxT.start(['blue','red'], 50);1"); log('night sim', await b.ev('__sc.simTime()')); await shot('tracers_night', 1800); log('act', await b.ev('Array.from(__sc.tracers.act).reduce((a,c)=>a+c,0)')); await b.ev("__fxT.stop();1");
  }
  log('errors', JSON.stringify(b.errs.slice(0, 8)));
} catch (e) { log('ERR', e.message); } finally { await b.close(); await srv.close(); log('done'); }
