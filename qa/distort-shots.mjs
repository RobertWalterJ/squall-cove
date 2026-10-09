// Four screenshots of the air distortion engine (v9.9.6). usage: node qa/distort-shots.mjs [outDir=qa/shots]
// The effect clock is frozen (DIST.ts = 0) and the ring age is set by hand, because the software renderer shows about one frame a second and a ring lives 0.3 s.
import fs from 'fs'; import path from 'path';
import { ROOT, sleep, startServer, launch, loadGame, PROFILES } from './harness.mjs';
const out = path.resolve(process.argv[2] || path.join(ROOT, 'qa', 'shots')); fs.mkdirSync(out, { recursive: true });
const prof = { ...PROFILES.desktop, w: 960, h: 560 };
const srv = await startServer(); const b = await launch({ ...prof, extraArgs: ['--autoplay-policy=no-user-gesture-required'] });
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);
const shot = async (name) => { await sleep(3500); log(await b.ev('JSON.stringify(__sc.DIST.status())'), b.errs.slice(-2)); const f = path.join(out, `distort_${name}.png`); await b.shot(f); log('shot', name); };
try {
  if (!await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=desktop`)) throw new Error('no load');
  await b.ev("document.getElementById('help').hidden=true; document.getElementById('fpHint') && (document.getElementById('fpHint').style.display='none'); __sc.enterFP(); __sc.DIST.noMirage = true; 1"); await sleep(2000);
  await b.ev(`window.__ahead = (d) => { const sc = __sc, c = sc.camera, v = new sc.THREE.Vector3(); c.getWorldDirection(v); const l = Math.hypot(v.x, v.z) || 1; const x = c.position.x + v.x / l * d, z = c.position.z + v.z / l * d; return { x, z, y: Math.max(sc.heightAt(x, z), 0) }; }; 1`);
  // the open water south of the quay: a clear horizon, a ship and the palms behind the effects
  await b.ev("(()=>{ const sc = __sc, p = sc.fp.p; sc.CHEAT.fly = true; p.x = 60; p.z = 118; p.y = Math.max(sc.heightAt(60, 118), 0) + 3; sc.fp.vx = sc.fp.vz = 0; sc.fp.yaw = 1.57; sc.fp.pitch = 0.02; return 1 })()"); await sleep(1500);
  // 1: shockwave mid-flight, 70 m ahead
  await b.ev("(()=>{ const sc = __sc, D = sc.DIST; D.reset(); D.ts = 1; D.tick(0.01); const p = __ahead(70); sc.blast(p.x, p.y, p.z, { R: 24, dmg: 10, crater: 0, depth: 0, owner: null, quiet: true }); D.ts = 0; D.shocks[0].age = 0.1; return 1 })()");
  await shot('1_shockwave');
  // 2: a close ring, 32 m ahead, earlier in its life
  await b.ev("(()=>{ const sc = __sc, D = sc.DIST; D.reset(); D.ts = 1; D.tick(0.01); const p = __ahead(32); sc.blast(p.x, p.y, p.z, { R: 24, dmg: 10, crater: 0, depth: 0, owner: null, quiet: true }); D.ts = 0; D.shocks[0].age = 0.05; return 1 })()");
  await shot('2_close_ring');
  // 3: burning palms with their haze, looking north at the shore against the sunset
  await b.ev("(()=>{ const sc = __sc, D = sc.DIST; D.reset(); sc.fp.yaw = 3.14; sc.fp.pitch = 0.03; const p = sc.fp.p; const L = sc.trees.filter(t => !t.dead && Math.hypot(t.x - p.x, t.z - p.z) > 25 && Math.hypot(t.x - p.x, t.z - p.z) < 130 && Math.abs(t.x - p.x) < 40 && t.z < p.z).sort((a, b) => Math.hypot(a.x - p.x, a.z - p.z) - Math.hypot(b.x - p.x, b.z - p.z)).slice(0, 7); for (const t of L) sc.igniteTree(t, 60); window.__burn = L.length; D.ts = 20; return L.length })()"); await sleep(6000);
  await b.ev("(()=>{ const D = __sc.DIST; D.ts = 0; for (const t of __sc.trees) if (t.burn > 0) t.burn = 40; return D.status() })()").then(r => log('haze', r));
  await shot('3_fire_haze');
  // 4: the gunship station, thermal, with a ring
  await b.ev("clearInterval(window.__keep); __sc.exitFP(); 1"); await sleep(800);
  await b.ev("(()=>{ const sc = __sc, D = sc.DIST; D.reset(); D.ts = 1; sc.stnOpenFor('blue'); sc.stnSetMode('thermal', true); sc.stnStep(0.05); const S = sc.STN; for (let i = 0; i < 6; i++) sc.blast(S.ax + i * 6 - 15, S.ay, S.az + 10, { R: 5, dmg: 1, crater: 0, depth: 0, owner: null, quiet: true }); D.ts = 20; return 1 })()"); await sleep(6000);
  await b.ev("(()=>{ const sc = __sc, D = sc.DIST, S = sc.STN; D.ts = 0; D.shock(S.ax, S.ay + 1, S.az, 26); D.shocks[0].age = 0.09; return 1 })()");
  await shot('4_station_thermal');
} catch (e) { console.log('ERR', e.message); } finally { await b.close(); await srv.close(); }
