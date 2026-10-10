// Six screenshots of the baked fire, steam, fog and lights (FW branch). usage: node qa/fire-shots.mjs [outDir=qa/shots] [only=name,name]
// The software renderer runs at about one frame in several seconds, so effects are advanced by hand (FW.tick with a fixed step) while the game loop is paused (window.__qaHold).
import fs from 'fs'; import path from 'path';
import { boot, log, sleep, ROOT } from './fire-lib.mjs';
const out = path.resolve(process.argv[2] || path.join(ROOT, 'qa', 'shots')), only = process.argv[3] ? process.argv[3].split(',') : null; fs.mkdirSync(out, { recursive: true });
const want = (n) => !only || only.includes(n);
const g = await boot('desktop'); const b = g.b;
const J = async (expr) => { const r = await b.ev(`(async()=>{ ${expr} })()`); return typeof r === 'string' && /^[\[{]/.test(r) ? JSON.parse(r) : r; };
const PRE = `const sc = __sc, F = sc.FW, R = F.R; window.__qaHold = true;`;
const shot = async (name) => { await b.ev("__sc.FW.tick(0.001); __sc.renderer.render(__sc.scene,__sc.camera);1", true); const f = path.join(out, `fire_${name}.png`); await b.shot(f); log('shot', f); };
const pump = (n, dt, ms = 30) => J(`${PRE} for (let i = 0; i < ${n}; i++) { F.tick(${dt}); if (i % 6 === 0) await new Promise(r => setTimeout(r, ${ms})); } return 1`);
const loadAll = (names, atm) => J(`${PRE} for (const n of ${JSON.stringify(names)}) F.need(n); for (const n of ${JSON.stringify(atm || [])}) F.A.need(n); F.needParticles(); for (let i = 0; i < 300; i++) { F.tick(0.01); const ok = ${JSON.stringify(names)}.every(n => F.types[n] && F.types[n].state !== 'loading') && ${JSON.stringify(atm || [])}.every(n => F.A.types[n] && F.A.types[n].state !== 'loading'); if (ok) break; await new Promise(r => setTimeout(r, 250)); } return 1`);
const cam = (x, y, z, tx, ty, tz) => b.ev(`(()=>{ const c = __sc.camera; c.position.set(${x}, ${y}, ${z}); c.lookAt(${tx}, ${ty}, ${tz}); c.updateMatrixWorld(true); return 1 })()`);
const setTime = async (h) => { await b.ev(`window.__qaHold = false; __sc.todSetHour(${h}); 1`); await sleep(14000); await b.ev("window.__qaHold = true; 1"); };
const fireClear = () => J(`${PRE} for (const f of F.fires.slice()) F.kill(f, true); F.G.fronts.length = 0; F.G.spots.length = 0; F.A.fx.length = 0; F.A.tiles.length = 0; F.P.list.length = 0; return 1`);
try {
  const open = JSON.parse(await b.ev("JSON.stringify(__fxFind('grass')||__fxFind('sand'))")); log('open ground', open);
  const gy = (dx, dz) => `Math.max(__sc.heightAt(${open[0]} + ${dx}, ${open[1]} + ${dz}), 0)`;
  // 1 campfire, close, at dusk
  if (want('campfire')) {
    await J(`${PRE} sc.wx.fog = 0; sc.wx.imp.fog = true; sc.wind.v.x = 1; sc.wind.v.z = 0.5; 1`); await setTime(19.4); await fireClear(); await loadAll(['campfire']);
    await J(`${PRE} const y = ${gy(0, 8)}; F.spawn('campfire', ${open[0]}, y + 0.05, ${open[1] + 8}, { sc: 1.5, F: 1.2, state: 'burn', dur: 9999 }); for (let i = 0; i < 60; i++) F.tick(0.05); return 1`);
    await cam(open[0] + 1.6, await b.ev(`${gy(0, 8)} + 1.0`), open[1] + 5.2, open[0], await b.ev(`${gy(0, 8)} + 0.8`), open[1] + 8); await shot('campfire_close');
  }
  // 2 grass fire front spreading
  if (want('grassfront')) {
    await setTime(17.2); await fireClear(); await loadAll(['spot_fire', 'front_lead', 'front_body', 'front_trail', 'lick']);
    await J(`${PRE} sc.wind.v.x = 0; sc.wind.v.z = 4.5; F.tick(0.05); F.igniteGround(${open[0]}, ${open[1] + 1}, { convert: true }); for (let i = 0; i < 140 && !F.G.fronts.length; i++) F.tick(0.1); for (let i = 0; i < 90; i++) F.tick(0.1); return 1`);
    const fr = await J(`${PRE} const fr = F.G.fronts[0]; return JSON.stringify(fr ? { x: fr.x0 + fr.ux * fr.d, z: fr.z0 + fr.uz * fr.d, d: fr.d, hw: fr.hw } : null)`); log('front', JSON.stringify(fr));
    if (fr) { const y = await b.ev(`Math.max(__sc.heightAt(${fr.x}, ${fr.z}), 0)`); await cam(fr.x + 11, y + 1.7, fr.z - 9, fr.x, y + 0.9, fr.z - 1); await shot('grass_front'); }
  }
  // 3 a burning vehicle with black smoke
  if (want('vehicle')) {
    await setTime(16.5); await fireClear(); await loadAll(['vehicle_engine', 'vehicle_small', 'vehicle', 'smoke_column']);
    const v = await J(`${PRE} const vs = sc.BVL.filter(v => !v.dead && !v.heli); let best = null, bs = -1; for (const v of vs) { let s = 0; for (const p of sc.props) { if (!p.item || !/^b-/.test(p.item.id || '')) continue; const d = Math.hypot(p.x - v.x, p.z - v.z); s = Math.max(s, 0); if (d < 18) s -= 18 - d; } if (best === null || s > bs) { best = v; bs = s; } } if (!best) return JSON.stringify(null); best.burn = 7; window.__v = best; for (let i = 0; i < 90; i++) F.tick(0.1); return JSON.stringify({ x: best.x, y: best.y, z: best.z, name: best.sp.name, yaw: best.yaw })`);
    log('vehicle', JSON.stringify(v)); if (v) { await cam(v.x + 8, v.y + 2.0, v.z + 9, v.x, v.y + 3.2, v.z); await shot('vehicle_fire'); }
  }
  // 4 an explosion with flaming debris (the debris is stepped by hand)
  if (want('explosion')) {
    await fireClear(); await loadAll(['blast_fuel', 'blast_medium', 'blast_ground', 'debris_slow', 'debris_med', 'debris_fast', 'smoke_column']);
    await J(`${PRE} sc.wind.v.x = 1.5; sc.wind.v.z = 1; for (const v of [0]) { } const x = ${open[0]}, z = ${open[1] + 30}, y = ${gy(0, 30)}; sc.DEB.p.length = 0; F.dbFrac = 0.9; sc.blast(x, y, z, { R: 13, dmg: 1, crater: 0, depth: 0, owner: null, quiet: true, name: 'Vehicle explosion' }); for (let i = 0; i < 9; i++) { sc.updateDebris(0.05); F.tick(0.05); } return 1`);
    const info = await J(`${PRE} return JSON.stringify({ blast: F.blastStats, fl: sc.DEB.p.filter(d => d.fl).length, deb: sc.DEB.p.length, parts: F.P.list.length })`); log('explosion', JSON.stringify(info));
    await cam(open[0] - 8, await b.ev(`${gy(0, 0)} + 2.2`), open[1] + 4, open[0] + 2, await b.ev(`${gy(0, 30)} + 8`), open[1] + 30); await shot('explosion_debris');
  }
  // 5 a fog bank over water at dawn
  if (want('fogdawn')) {
    await fireClear(); await J(`${PRE} sc.wx.fog = 2; sc.wx.imp.fog = true; sc.wind.v.x = 1.2; sc.wind.v.z = 0.6; return 1`); await setTime(5.9);
    await J(`${PRE} sc.tod.am = true; return 1`); await loadAll([], ['mist_dawn', 'fog_sea', 'fog_bank', 'fog_ground', 'fog_wisps', 'fog_blobs', 'fog_valley']);
    await b.ev("__fxGo(60, 118, 0, 0.02, 3); 1"); await pump(260, 0.5, 20);
    const gy5 = await b.ev("Math.max(__sc.heightAt(60,118),0)"); await cam(60, gy5 + 3.5, 118, 90, 3, 400); await shot('fog_dawn');
  }
  // 6 a lit base at night with light cones in the air (fog level 1 so the cones show)
  if (want('lit_base')) {
    await fireClear(); await J(`${PRE} sc.wx.fog = 1; sc.wx.imp.fog = true; return 1`); await setTime(22.6); await sleep(4000);
    await b.ev("window.__qaHold = false; 1"); await sleep(16000); await b.ev("window.__qaHold = true; 1");
    const tw = await J(`${PRE} let best = null; for (const f of sc.LIGHT.fix) { if (f.kind !== 'tower' || !(f.on > 0.5)) continue; let n = 0; for (const o of sc.LIGHT.fix) if (o !== f && o.on > 0.5 && Math.hypot(o.x - f.x, o.z - f.z) < 40) n++; if (!best || n > best.n) best = { n, f }; } if (!best) return JSON.stringify(null); const f = best.f; return JSON.stringify({ x: f.x, y: f.y, z: f.z, b: f.beam, n: best.n, gy: Math.max(sc.heightAt(f.x, f.z), 0), st: F.L.stats })`);
    log('tower', JSON.stringify(tw));
    if (tw) { const a = Math.atan2(tw.b.dx, tw.b.dz) + 2.6; await cam(tw.x + Math.sin(a) * 30, tw.gy + 2.4, tw.z + Math.cos(a) * 30, tw.x + tw.b.dx * 14, tw.gy + 4, tw.z + tw.b.dz * 14); await shot('lit_base_night'); }
  }
  log('errors', JSON.stringify(b.errs.slice(0, 6)));
} finally { await g.close(); process.exit(0); }
