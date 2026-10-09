// Getting up with Space after a knock-down (v9.9.5). usage: node qa/getup-check.mjs
// A knocked-down player with hp > 0 must always get up with Space (and with the touch Jump button), in the sandbox and in a battle,
// while the ragdoll is still moving, while crouched or prone, and in water. A real knock-out (hp <= 0 / BATTLE.down) keeps the deploy menu.
import { sleep, startServer, launch, loadGame, PROFILES } from './harness.mjs';
const srv = await startServer(), b = await launch(PROFILES.desktop), fail = [];
const ok = (name, cond, d) => { console.log((cond ? '  ok   ' : '  FAIL ') + name + (d !== undefined ? '  ' + JSON.stringify(d) : '')); if (!cond) fail.push(name); };
const J = async (expr) => { const r = await b.ev(`JSON.stringify((()=>{ ${expr} })())`); return r ? JSON.parse(r) : null; };
const space = "window.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', code: 'Space', bubbles: true })); window.dispatchEvent(new KeyboardEvent('keyup', { key: ' ', code: 'Space', bubbles: true }));";
try {
  if (!await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=desktop`)) throw new Error('no load');
  await b.ev("document.getElementById('help').hidden=true; 1");
  // ---- sandbox
  await b.ev("__sc.enterFP(); 1"); await sleep(1500);
  const pre = await J("return { mode: __sc.mode, p: !!__sc.fp.p }"); ok('sandbox: in first person', pre.mode === 'fp' && pre.p, pre);
  await J("__sc.topple(__sc.fp.p, { x: 2, y: 3, z: 1 }); return 1"); await sleep(120);
  let r = await J("return { st: __sc.fp.p.state, frozen: !!(__sc.fp.p.rag && __sc.fp.p.rag.frozen) }"); ok('sandbox: toppled', r.st === 'rag', r);
  await b.ev(space); await sleep(250);
  r = await J("return { st: __sc.fp.p.state }"); ok('sandbox: Space while the ragdoll is still moving gets up', r.st !== 'rag', r);
  // settled (frozen) ragdoll
  await J("__sc.topple(__sc.fp.p, { x: 1, y: 1, z: 1 }); return 1"); await sleep(5000);
  r = await J("return { st: __sc.fp.p.state, frozen: !!(__sc.fp.p.rag && __sc.fp.p.rag.frozen) }"); ok('sandbox: settled ragdoll', r.st === 'rag', r);
  await b.ev(space); await sleep(250);
  r = await J("return { st: __sc.fp.p.state }"); ok('sandbox: Space on a settled ragdoll gets up', r.st !== 'rag', r);
  // crouched / prone before the knock-down: the first Space must stand the player up, not just change stance
  for (const stance of [1, 2]) {
    await J(`__sc.fp.stance = ${stance}; __sc.topple(__sc.fp.p, { x: 1, y: 2, z: 0 }); return 1`); await sleep(400);
    await b.ev(space); await sleep(250);
    r = await J("return { st: __sc.fp.p.state, stance: __sc.fp.stance }"); ok('sandbox: knocked down while stance ' + stance + ', one Space gets up', r.st !== 'rag', r);
  }
  // touch Jump button
  await J("__sc.topple(__sc.fp.p, { x: 1, y: 2, z: 0 }); return 1"); await sleep(400);
  await b.ev("document.getElementById('fpJump').click(); 1"); await sleep(250);
  r = await J("return { st: __sc.fp.p.state }"); ok('sandbox: the Jump button gets up', r.st !== 'rag', r);
  // shallow and deep water: put the pelvis over water
  for (const [label, wantMax, wantMin] of [['shallow water', 0.15, -0.9], ['deep water', -1.0, -30]]) {
    const spot = await J(`const sc = __sc; let best = null; for (let x = -118; x <= 118 && !best; x += 2) for (let z = -118; z <= 118; z += 2) { const h = sc.standY(x, z); if (h < ${wantMax} && h > ${wantMin}) { best = { x, z, h }; break; } } return best;`);
    if (!spot) { ok('sandbox: ' + label + ' spot found', false); continue; }
    await J(`const p = __sc.fp.p; p.x = ${spot.x}; p.z = ${spot.z}; __sc.topple(p, { x: 0, y: 1, z: 0 }); const pb = p.rag.bodies.pelvis; pb.position.set(${spot.x}, ${Math.max(spot.h, -1) + 0.3}, ${spot.z}); return 1`); await sleep(500);
    await b.ev(space); await sleep(300);
    r = await J("return { st: __sc.fp.p.state, swim: !!__sc.fp.p.swim }"); ok('sandbox: ' + label + ': Space gets up (stands or swims)', r.st !== 'rag', { spot, ...r });
    await J("const p = __sc.fp.p; p.swim = false; return 1");
    await J("const p = __sc.fp.p; if (p.state === 'rag') __sc.standUp(p); return 1");
    // back to dry land for the next case
    await J("const sc = __sc, p = sc.fp.p; for (let r = 0; r < 200; r += 3) { for (let k = 0; k < 16; k++) { const a = k / 16 * 6.283, x = Math.cos(a) * r, z = Math.sin(a) * r; if (sc.standY(x, z) > 0.8) { p.x = x; p.z = z; p.y = sc.standY(x, z); if (p.body) { p.body.position.set(x, p.y + 0.9, z); } return 1; } } } return 0"); await sleep(300);
  }
  // ---- battle: knocked down but alive
  await b.ev("__sc.exitFP(); 1"); await sleep(400);
  await b.ev("__sc.CHEAT.god = true; __sc.playBattle('blue'); 1"); await sleep(4000);
  await b.ev("document.getElementById('help').hidden=true; 1");
  r = await J("return { on: __sc.BATTLE.on, fp: __sc.fp.on, hp: __sc.fp.p && __sc.fp.p.hp, down: __sc.BATTLE.down }"); ok('battle: in first person, alive', r.on && r.fp && !r.down, r);
  await J("const p = __sc.fp.p; p.hp = 100; __sc.topple(p, { x: 2, y: 3, z: 1 }); return 1"); await sleep(300);
  r = await J("return { st: __sc.fp.p.state, down: __sc.BATTLE.down, hp: __sc.fp.p.hp }"); ok('battle: knocked down with hp > 0, not a knock-out', r.st === 'rag' && !r.down && r.hp > 0, r);
  await b.ev(space); await sleep(300);
  r = await J("return { st: __sc.fp.p.state, down: __sc.BATTLE.down, hp: __sc.fp.p.hp, mode: __sc.mode, fpon: __sc.fp.on, veh: !!__sc.fp.veh, stance: __sc.fp.stance, wheel: !!__sc.SQD, keyroute: 1 }"); ok('battle: Space gets up', r.st !== 'rag', r);
  await J("const p = __sc.fp.p; __sc.fp.stance = 2; __sc.topple(p, { x: 2, y: 3, z: 1 }); return 1"); await sleep(300);
  await b.ev(space); await sleep(300);
  r = await J("return { st: __sc.fp.p.state }"); ok('battle: knocked down prone, one Space gets up', r.st !== 'rag', r);
  await J("const p = __sc.fp.p; __sc.topple(p, { x: 2, y: 3, z: 1 }); return 1"); await sleep(300);
  await b.ev("document.getElementById('fpJump').click(); 1"); await sleep(300);
  r = await J("return { st: __sc.fp.p.state }"); ok('battle: the Jump button gets up', r.st !== 'rag', r);
  await b.ev("__sc.CHEAT.god = false; 1");
  // a real knock-out still shows the deploy menu and Space does not stand the body up
  await J("const sc = __sc, p = sc.fp.p; sc.hurt(p, 500, null, false, 'Test'); return 1"); await sleep(600);
  r = await J("return { st: __sc.fp.p && __sc.fp.p.state, down: __sc.BATTLE.down, menu: !document.getElementById('bSpawn').hidden }"); ok('battle: a real knock-out keeps the deploy menu', r.down && r.menu && r.st === 'rag', r);
  await b.ev(space); await sleep(300);
  r = await J("return { st: __sc.fp.p && __sc.fp.p.state, down: __sc.BATTLE.down }"); ok('battle: Space does not get a knocked-out player up', r.st === 'rag' && r.down, r);
  // ---- the gunship station is never blocked by a cooldown (Part 1a)
  await b.ev("__sc.exitFP(); 1"); await sleep(600);
  r = await J("const sc = __sc; sc.AIR.list.length = 0; sc.AIR.cd.blue.gs = 180; sc.AIR.cd.red.gs = 180; return { team: sc.BATTLE.team, mode: sc.mode, on: sc.BATTLE.on }"); ok('battle: overview, gunship cooldown set to 180 s', r.on && r.mode === 'god', r);
  r = await J("const sc = __sc; const res = sc.gunshipFromOverview(); return { res, on: sc.STN.on, kind: sc.STN.u && sc.STN.u.kind, pstn: !!(sc.STN.u && sc.STN.u.pstn), cd: sc.AIR.cd.blue.gs, team: sc.STN.team }"); ok('battle: the Gunship button opens the station during the cooldown with a free gunship, cooldown untouched', r.res && r.on && r.kind === 'gunship' && r.pstn && r.cd > 170, r);
  await b.ev("document.getElementById('stnLeave').click(); 1"); await sleep(600);
  r = await J("const sc = __sc; sc.STN.on = sc.STN.on; return { on: sc.STN.on, up: sc.gunshipUp('blue'), cd: sc.AIR.cd.blue.gs }"); ok('leaving the station works', !r.on, r);
  r = await J("const sc = __sc; sc.AIR.list.length = 0; sc.AIR.cd.blue.gs = 0; sc.callAir('blue', 'gunship'); const up = sc.gunshipUp('blue'); const u = sc.AIR.list.find(a => a.kind === 'gunship' && a.team === 'blue'); const res = sc.gunshipFromOverview(); return { up, res, on: sc.STN.on, same: sc.STN.u === u, n: sc.AIR.list.filter(a => a.kind === 'gunship' && a.team === 'blue').length }"); ok('battle: a gunship already called is taken over, not duplicated', r.up && r.res && r.on && r.same && r.n === 1, r);
  await b.ev("document.getElementById('stnLeave').click(); 1"); await sleep(600);
  const errs = b.errs.filter(e => !/favicon|WebGL|GPU/i.test(e)); ok('no console errors', errs.length === 0, errs.slice(0, 3));
} catch (e) { console.log('ERR', e.message); fail.push(e.message); } finally { await b.close(); await srv.close(); }
console.log(fail.length ? 'FAIL: ' + fail.join(' | ') : 'all getup checks passed'); process.exit(fail.length ? 1 : 0);
