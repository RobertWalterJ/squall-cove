// Part C of the command check (v9.9.15): supply and logistics. Run through qa/command-check.mjs (node qa/command-check.mjs c).
// Budget and income, ammunition state and its effect on fire and boldness, group ammo and wounded, resupply, the air drop (cargo aircraft, wind drift, smoke marker, anti-air), the supply truck convoy and its ambush,
// medevac, the choice of reinforcement, the budget and ammo cheats, the supply bar, performance.
import { POOL_SRC } from './command-check-lib.mjs';
export async function partC({ b, J, out, ok, num, startBattle, sleep, reload }) {
  const WANT = (process.env.SECTIONS || '').split(',').filter(Boolean), on = (n) => !WANT.length || WANT.includes(n);          // SECTIONS=drop,aa runs only those (budget, ammo, group, resupply, drop, aa, convoy, medevac, reinforce, cheats, bar, perf)
  await startBattle(20);
  const pool = await J(POOL_SRC); out('  pool: ' + JSON.stringify(pool));

  // ---- 1. budget: generous start, income from held points (a depot earns most), plain words
  if (on('budget')) {
  const bud = await J(`const sc = __sc, S = __S; const C = S.reset(); const start = C.budget; const base = {}; for (const n of ['Quay West', 'Quay East', 'West farm', 'East farm', 'Town centre', 'Lighthouse', 'Mountain lake', 'Landing beach', 'Raider camp']) S.own(n, null);
      S.own('Quay West', 'blue'); const hqOnly = sc.supIncome('blue'); S.own('West farm', 'blue'); const withDepot = sc.supIncome('blue');            // Quay West is a headquarters, West farm a supply depot
      S.use(S.blue, 4, (q, i) => S.put(q, sc.cmdrPt('Quay West').x + i * 2, sc.cmdrPt('Quay West').z + 8)); S.use(S.red, 0, () => { }); C.budget = 0; C.lastT = sc.simTime(); const t0 = sc.simTime(); S.tick(1200); const gain = C.budget, dt = sc.simTime() - t0;
      return { start, hqOnly: +hqOnly.toFixed(3), withDepot: +withDepot.toFixed(3), gain: +gain.toFixed(2), expect: +(withDepot * dt).toFixed(2), dt: +dt.toFixed(1), words: [160, 100, 60, 20, 3].map(v => { C.budget = v; return sc.supWord(C); }), cap: sc.SUPMAX }`);
  ok('a side starts with a generous supply (at least 100 of a 160 cap)', bud.start >= 100 && bud.cap === 160, { start: bud.start, cap: bud.cap });
  ok('income comes from held points and a depot earns the most (headquarters alone 0.60 a second, with a depot 1.20)', bud.hqOnly === 0.6 && bud.withDepot === 1.2, { hqOnly: bud.hqOnly, withDepot: bud.withDepot });
  ok('supply accrues at the income rate (20 simulated seconds, within 15 percent of income times time)', Math.abs(bud.gain - bud.expect) <= bud.expect * 0.15, { gain: bud.gain, expect: bud.expect, dt: bud.dt });
  ok('the supply level is a plain word, never a number (plenty, enough, low, empty)', bud.words.join(',') === 'plenty,plenty,enough,low,empty', bud.words);

  }
  // ---- 2. ammunition: reserve magazines, slower and less bold when low, never a hard stop
  if (on('ammo')) {
  const am = await J(`const sc = __sc, S = __S; S.reset(); const Q = sc.cmdrPt('Quay West'); S.use(S.blue, 2, (q, i) => S.put(q, Q.x + i * 3, Q.z + 20)); S.use(S.red, 1, (q) => S.put(q, Q.x + 25, Q.z + 20)); const q = S.blue[0], e = S.red[0], bb = q.bot; e.bot.follow = true;
      const k = (m) => { bb.mags = m; return +sc.ammoK(bb).toFixed(2); }; const ks = [6, 2, 1, 0].map(k);
      bb.mags = 3; bb.ammo = 1; bb.reload = 0; bb.cool = 0; q.heading = Math.atan2(e.x - q.x, e.z - q.z); sc.botFire(q, bb, e, 25); const afterReload = { mags: bb.mags, ammo: bb.ammo, reload: +bb.reload.toFixed(2) };
      bb.mags = 0; bb.ammo = 1; bb.reload = 0; bb.cool = 0; const t1 = sc.simTime(); let shots = 0; for (let i = 0; i < 6; i++) { bb.reload = 0; bb.cool = 0; const a0 = bb.ammo; q.lastShot = -1; sc.botFire(q, bb, e, 25); if (q.lastShot >= 0 || bb.ammo !== a0) shots++; } const dry = { mags: bb.mags, shots, cool0: +bb.cool.toFixed(2) };
      bb.mags = 0; bb.tac = 'push'; q.hp = 100; e.hp = 100; S.tick(5); const tac = bb.tac; sc.CHEAT.ammo = true; const cheat = +sc.ammoK(bb).toFixed(2); sc.CHEAT.ammo = false;
      return { ks, afterReload, dry, tac, cheat }`);
  ok('low ammunition slows the rate of fire: full or two magazines 1.00, one 1.25, none 1.70 (times the weapon cool-down)', am.ks.join(',') === '1,1,1.25,1.7', am.ks);
  ok('a reload costs one reserve magazine (3 becomes 2) and refills the magazine', am.afterReload.mags === 2 && am.afterReload.ammo > 1, am.afterReload);
  ok('never a hard stop: with no reserve magazines a soldier still reloads and keeps firing (six shots in six tries)', am.dry.mags === 0 && am.dry.shots === 6, am.dry);
  ok('a soldier out of magazines is less bold: a pushing soldier holds instead', am.tac === 'hold', { tac: am.tac });
  ok('the ammo cheat removes the penalty for the cheating side', am.cheat === 1, { cheat: am.cheat });

  }
  // ---- 3. group ammunition and wounded
  if (on('group')) {
  const gs = await J(`const sc = __sc, S = __S; const C = S.reset(1); const Q = sc.cmdrPt('Quay West'); S.own('Quay West', 'blue'); S.own('Raider camp', 'red'); S.use(S.blue, 8, (q, i) => S.put(q, Q.x + (i % 4) * 2, Q.z + 12 + Math.floor(i / 4) * 2)); S.use(S.red, 0, () => { });
      S.blue.slice(0, 4).forEach(q => { q.bot.mags = 0; }); S.blue.slice(4, 7).forEach(q => { q.hp = 20; }); sc.CMDR.thinks = 0; C.reviewT = -99; sc.cmdrThink(C); const g = C.groups[0]; return { n: g.n, ammo: +g.ammo.toFixed(3), wounded: g.wounded, hurt: +g.hurt.toFixed(3) }`);
  ok('a group knows its ammunition (half the people have none: 0.50) and how many are hurt (3 of 8)', gs.n === 8 && gs.ammo === 0.5 && gs.wounded === 3 && Math.abs(gs.hurt - 0.375) < 0.01, gs);

  }
  // ---- 4. resupply: a low group goes to the nearest supply, and a depot or headquarters refills people standing in it
  if (on('resupply')) {
  const rs = await J(`const sc = __sc, S = __S; const C = S.reset(1); const Q = sc.cmdrPt('Quay West'); for (const n of ['Quay East', 'West farm', 'East farm', 'Town centre', 'Lighthouse', 'Mountain lake', 'Landing beach']) S.own(n, null); S.own('Quay West', 'blue'); S.own('Raider camp', 'red');
      S.use(S.blue, 4, (q, i) => S.put(q, Q.x + 110 + i * 2, Q.z + 20)); S.use(S.red, 0, () => { }); for (const q of S.blue.slice(0, 4)) q.bot.mags = 0; C.reviewT = -99; sc.cmdrThink(C); S.tick(60); sc.cmdrThink(C); const g = C.groups[0];
      const heading = S.blue.slice(0, 4).filter(q => q.bot.gl && q.bot.gl.rs && Math.hypot(q.bot.gl.x - Q.x, q.bot.gl.z - Q.z) < 14).length, src = g.resup;
      // standing in the headquarters refills magazines (+1 every 2 s)
      for (const q of S.blue.slice(0, 4)) { S.put(q, Q.x + 5, Q.z + 5); q.bot.mags = 0; } S.tick(60 * 5); const refilled = S.blue.slice(0, 4).map(q => q.bot.mags);
      return { src, heading, refilled, ammo: +g.ammo.toFixed(2) }`);
  ok('a group short of ammunition with a headquarters 110 m away is sent there (its orders point at it), and says where in plain words', rs.heading >= 3 && /Quay West/.test(rs.src || ''), rs);
  ok('people standing in a headquarters or depot get a magazine back every two seconds (5 s: at least 2 each)', rs.refilled.every(m => m >= 2), { mags: rs.refilled });

  }
  // ---- 5. the air drop: a cargo aircraft, pallets released upwind, wind drift, smoke marker, within tolerance
  if (on('drop')) {
  const ad = await J(`const sc = __sc, S = __S; const C = S.reset(1); for (const n of ['Quay East', 'West farm', 'East farm', 'Town centre', 'Lighthouse', 'Mountain lake', 'Landing beach']) S.own(n, null); S.own('Quay West', 'blue'); S.own('Raider camp', 'red');
      const E = sc.cmdrPt('Mountain lake'); S.use(S.blue, 4, (q, i) => S.put(q, E.x - 60 + i * 2, E.z + 30)); S.use(S.red, 0, () => { }); for (const q of S.blue.slice(0, 4)) q.bot.mags = 0; sc.AIR.cd.blue.dr = 0; sc.SUP.pal.length = 0; sc.SUP.marks.length = 0; C.budget = 120; C.need = {};
      C.reviewT = -99; sc.cmdrThink(C); const g = C.groups[0], cargo = sc.AIR.list.find(u => u.kind === 'cargo'), mk = sc.SUP.marks[0];
      if (!cargo || !mk) return { called: false, log: C.log.slice(-4).map(l => l.msg), budget: C.budget, cd: sc.AIR.cd.blue.dr, convoy: !!sc.SUP.convoy.blue };
      const dz = { x: mk.x, z: mk.z }, dGroup = Math.hypot(dz.x - g.cx, dz.z - g.cz), alt = cargo.y, wind0 = { x: sc.wind.v.x, z: sc.wind.v.z }, spent = 120 - C.budget;
      let released = 0, landed = [], tmax = 0; for (let k = 0; k < 220 && landed.length < 3; k++) { S.tick(15); released = Math.max(released, cargo.rel); landed = sc.SUP.pal.filter(p => p.state === 'land'); tmax = sc.simTime(); if (k % 8 === 0) for (const q of S.blue.slice(0, 4)) { q.bot.mags = 0; } }
      const err = landed.map(p => +Math.hypot(p.x - dz.x, p.z - dz.z).toFixed(1)), cx = landed.reduce((a, p) => a + p.x, 0) / Math.max(1, landed.length), cz = landed.reduce((a, p) => a + p.z, 0) / Math.max(1, landed.length);
      return { called: true, dz: { x: Math.round(dz.x), z: Math.round(dz.z) }, dGroup: Math.round(dGroup), alt: Math.round(alt), wind: { x: +wind0.x.toFixed(1), z: +wind0.z.toFixed(1) }, spent, cd: sc.AIR.cd.blue.dr, released, landed: landed.length, err, centreErr: +Math.hypot(cx - dz.x, cz - dz.z).toFixed(1), markerAge: +mk.age.toFixed(1), markers: sc.SUP.marks.length, log: C.log.slice(-4).map(l => l.msg), clear: Math.round(cargo.clear || 0) }`);
  ok('a group out of ammunition and far from any supply gets an air drop: a cargo aircraft is called, the zone is 45 to 110 m from the group, the price (14) is paid', ad.called && ad.dGroup >= 40 && ad.dGroup <= 115 && Math.abs(ad.spent - 14) < 1.5 && ad.cd > 0, { dGroup: ad.dGroup, spent: ad.spent, cd: ad.cd, log: ad.log, convoy: ad.convoy });
  ok('the cargo aircraft flies high (about 175 m above ground) and releases three pallets', ad.called && ad.alt >= 160 && ad.released === 3, { alt: ad.alt, released: ad.released });
  ok('a smoke marker burns on the drop zone from the moment of the call', ad.called && ad.markers >= 1 && ad.markerAge > 5, { markers: ad.markers, markerAge: ad.markerAge });
  ok('all three pallets land on the drop zone: the aircraft released upwind so the wind carries them down (each within 45 m, their centre within 30 m)', ad.called && ad.landed === 3 && ad.err.every(e => e <= 45) && ad.centreErr <= 30, { wind: ad.wind, err: ad.err, centre: ad.centreErr, landed: ad.landed });
  out('  air drop: ' + JSON.stringify({ dz: ad.dz, wind: ad.wind, err: ad.err, centreErr: ad.centreErr, track_clearance_to_enemy_points_m: ad.clear }));
  const pal = await J(`const sc = __sc, S = __S; const C = S.C; const p = sc.SUP.pal.find(x => x.state === 'land'); if (!p) return { none: true }; S.use(S.blue, 3, (q, i) => { S.put(q, p.x + i * 3, p.z + 4); q.bot.mags = 0; }); const n0 = p.n; S.tick(60 * 5); return { mags: S.blue.slice(0, 3).map(q => q.bot.mags), used: n0 - p.n, left: p.n }`);
  ok('people at a landed pallet get magazines back and the pallet is used up gradually', !pal.none && pal.mags.every(m => m >= 2) && pal.used >= 3, pal);

  }
  // ---- 6. the aircraft is vulnerable to anti-air, and is never sent where anti-air would reach it
  if (on('aa')) {
  for (let k = 0; k < 90 && !(await b.ev('__sc.AAS.length > 0')); k++) await sleep(1000);          // the battle kit (guns at the points) loads after the battle starts
  out('  anti-air guns laid: ' + await b.ev('__sc.AAS.length'));
  const aa = await J(`const sc = __sc, S = __S; const C = S.C; const R = sc.cmdrPt('Raider camp'); S.own('Raider camp', 'red'); for (const e of sc.AAS) e.needCrew = false; sc.AIR.cd.blue.dr = 0; const refused = sc.cmdrAirDrop('blue', { x: R.x - 60, z: R.z + 40 });
      // an aircraft that does fly over an enemy point is shot at by its anti-air gun
      const g = new sc.THREE.Group(); sc.scene.add(g); const u = { kind: 'cargo', team: 'blue', g, mesh: g, x: R.x + 80, z: R.z, y: 175, hd: Math.PI, spd: 0, hp: 150, hpMax: 150, rad: 14, life: 99, props: [], rel: 3, trav: 0, L0: 1e9, R: { x: 0, z: 0 }, dz: { x: 0, z: 0 } }; sc.AIR.list.push(u);
      let t = 0, aimed = 0; for (let k = 0; k < 40; k++) { S.tick(15); t = sc.simTime(); for (const e of sc.AAS) if (e.p && e.p.owner === 'red' && e.aimAt && sc.simTime() - (e.aimT || -9) < 1 && Math.hypot(e.aimAt.x - u.x, e.aimAt.z - u.z) < 1) aimed++; if (u.hp < 150) break; } const hit = { hp: Math.round(u.hp), down: !!u.down, aimed }; sc.damageAir(u, 15, 'red'); hit.after = Math.round(u.hp); if (!u.down) { sc.damageAir(u, 9999, 'red'); } S.tick(240); const gone = !sc.AIR.list.includes(u) || u.down;
      // a shot-down aircraft drops nothing
      sc.AIR.cd.blue.dr = 0; sc.SUP.pal.length = 0; let dzp = null; { const foes = sc.BATTLE.points.filter(p => p.owner === 'red'); for (let x = -300; x <= 300 && !dzp; x += 20) for (let z = -300; z <= 300 && !dzp; z += 20) if (sc.standY(x, z) > 2 && !sc.footBlocked(x, z, 6) && foes.every(p => Math.hypot(p.x - x, p.z - z) > 420)) dzp = { x, z }; } const ok2 = dzp ? sc.cmdrAirDrop('blue', dzp) : false; const c2 = sc.AIR.list.find(w => w.kind === 'cargo' && w !== u); if (c2) sc.damageAir(c2, 9999, 'red'); S.tick(60 * 20); const pallets = sc.SUP.pal.length, cd = sc.AIR.cd.blue.dr, off = sc.AIR.off.blue.dr;
      return { refused: refused === false, hit, gone, called2: ok2, pallets, cd, off }`);
  ok('an air drop is not flown along a track that passes within reach of an enemy anti-air gun (a drop zone beside the enemy headquarters is refused)', aa.refused, aa);
  ok('the cargo aircraft is a target: enemy anti-air guns within range aim at it (and a hit hurts it)', (aa.hit.aimed > 0 || aa.hit.hp < 150 || aa.hit.down) && aa.hit.after < 150, aa.hit);
  ok('a shot-down cargo aircraft drops nothing, and the next drop is delayed (a cooldown of 110 s from the loss, which is still above 80 twenty seconds later, and the aircraft marked offline)', aa.called2 && aa.pallets === 0 && aa.cd >= 80 && aa.off === true, { called: aa.called2, pallets: aa.pallets, cd: aa.cd, off: aa.off });

  }
  // ---- 7. the convoy: a spare supply truck drives to the nearest held point and unloads; it can be ambushed
  if (on('convoy')) {
  await b.ev("__sc.ensureBVeh().then(() => { window.__bvok = 1; }); 1"); for (let k = 0; k < 40 && !(await b.ev('window.__bvok === 1')); k++) await sleep(500);
  const cv = await J(`const sc = __sc, S = __S; const C = S.reset(1); for (const n of ['Quay East', 'West farm', 'East farm', 'Town centre', 'Lighthouse', 'Mountain lake', 'Landing beach']) S.own(n, null); S.own('Quay West', 'blue'); S.own('Raider camp', 'red'); const Q = sc.cmdrPt('Quay West');
      for (const w of sc.BVL.slice()) if (w.team === 'blue' && w.key === 'supply_truck') sc.removeVehicle && sc.removeVehicle(w);
      const v = sc.bvMake('supply_truck', 'blue', Q.x + 30, Q.z + 20, 0); if (!v) return { made: false }; sc.bvAIInit(v, 0, false); v.ai.st = 'idle'; v.ai.t = 99;
      S.use(S.blue, 4, (q, i) => S.put(q, Q.x + 160 + i * 2, Q.z + 30)); S.use(S.red, 0, () => { }); for (const q of S.blue.slice(0, 4)) q.bot.mags = 0; sc.AIR.cd.blue.dr = 99; C.budget = 120; C.need = {}; C.reviewT = -99; sc.cmdrThink(C); const g = C.groups[0]; const b0 = C.budget;
      const sent = sc.cmdrConvoy(C, g), A = v.ai; const r = { made: true, sent, kind: A.kind, st: A.st, spent: +(b0 - C.budget).toFixed(1), convoy: !!sc.SUP.convoy.blue, dest: sc.SUP.convoy.blue && sc.SUP.convoy.blue.dest, driver: !!(v.seats[0] && v.seats[0].q) };
      // arrival: the truck is put at its stop and told it has arrived; people standing there get magazines
      const goal = A.goal; if (goal) { v.x = goal.x; v.z = goal.z; v.y = sc.standY(goal.x, goal.z); if (v.body) { v.body.position.x = goal.x; v.body.position.z = goal.z; v.body.position.y = v.y + 1; } A.path = null; A.req = null; A.arrived = true; sc.bvAIThink(v); } r.holdKind = A.kind; r.holdSt = A.st;
      for (const q of S.blue.slice(0, 4)) { S.put(q, v.x + 4, v.z + 6); q.bot.mags = 0; } S.tick(60 * 6); r.refilled = S.blue.slice(0, 4).map(q => q.bot.mags);
      // the ambush: the truck is destroyed on the road
      sc.damageVehicle(v, 9999, null); S.tick(60 * 5); r.afterAmbush = { convoy: !!sc.SUP.convoy.blue, log: C.log.slice(-3).map(l => l.msg) }; return r`);
  ok('a spare supply truck is sent to the held point nearest a low group (driver aboard, mission convoy, price 8)', cv.made && cv.sent && cv.kind === 'convoy' && cv.st === 'go' && cv.convoy && cv.driver && Math.abs(cv.spent - 8) < 1, cv);
  ok('on arrival the truck stops and unloads: people within 26 m get magazines back', cv.holdKind === 'convoy' && cv.holdSt === 'hold' && (cv.refilled || []).every(m => m >= 2), { st: cv.holdSt, mags: cv.refilled });
  ok('a destroyed truck is an ambushed convoy: the commander drops it from its plans and logs it', cv.afterAmbush && cv.afterAmbush.convoy === false && cv.afterAmbush.log.some(m => /convoy was destroyed/.test(m)), cv.afterAmbush);

  }
  // ---- 8. medevac: a hurt group is answered with the medevac helicopter
  if (on('medevac')) {
  const md = await J(`const sc = __sc, S = __S; const C = S.reset(1); for (const n of ['Quay East', 'West farm', 'East farm', 'Town centre', 'Lighthouse', 'Mountain lake', 'Landing beach']) S.own(n, null); S.own('Quay West', 'blue'); S.own('Raider camp', 'red'); const Q = sc.cmdrPt('Quay West');
      S.use(S.blue, 8, (q, i) => S.put(q, Q.x + (i % 4) * 2, Q.z + 15 + Math.floor(i / 4) * 2)); S.use(S.red, 0, () => { }); S.blue.slice(0, 4).forEach(q => { q.hp = 20; }); sc.AIR.cd.blue.md = 0; for (const u of sc.AIR.list.slice()) if (u.kind === 'medevac') { sc.scene.remove(u.g); sc.AIR.list.splice(sc.AIR.list.indexOf(u), 1); } C.budget = 120; C.need = {}; C.reviewT = -99; sc.cmdrThink(C);
      const g = C.groups[0], u = sc.AIR.list.find(w => w.kind === 'medevac'); return { wounded: g.wounded, called: !!u, tgtDist: u ? Math.round(Math.hypot(u.tgt.x - g.cx, u.tgt.z - g.cz)) : null, spent: +(120 - C.budget).toFixed(1), cd: sc.AIR.cd.blue.md, log: C.log.slice(-2).map(l => l.msg) }`);
  ok('four or more wounded in a group of eight: the medevac helicopter is sent to the group (price 10)', md.wounded >= 4 && md.called && md.tgtDist <= 10 && Math.abs(md.spent - 10) < 1 && md.cd > 0, md);

  }
  // ---- 9. the choice of reinforcement: by boat when the point nearest the fight is on the coast, otherwise by transport helicopter to that point
  if (on('reinforce')) {
  const rf = await J(`const sc = __sc, S = __S; const out = {}; const mk = (obj, ownMap) => { const C = S.reset(1); sc.BATTLE.size = 20; sc.BATTLE.tickets.blue = 9999; sc.BATTLE.t = 100; for (const n of ['Quay West', 'Quay East', 'West farm', 'East farm', 'Town centre', 'Lighthouse', 'Mountain lake', 'Landing beach', 'Raider camp']) S.own(n, null); for (const n of ownMap) S.own(n, 'blue'); S.own('Raider camp', 'red');
        const P = sc.cmdrPt(ownMap[0]); S.use(S.blue, 6, (q, i) => S.put(q, P.x + (i % 3) * 2, P.z + 14 + Math.floor(i / 3) * 2)); S.use(S.red, 0, () => { }); C.force = { pt: obj, until: 1e9 }; C.mainPt = obj; for (const k in sc.AIR.cd.blue) sc.AIR.cd.blue[k] = 0; C.budget = 150; C.need = {}; C.reviewT = -99; C.supT = -99; sc.CMDR.maxGroups = 1; sc.cmdrThink(C); return C; };
      let C = mk('Landing beach', ['Quay East']); out.coast = { bt: sc.AIR.cd.blue.bt, pa: sc.AIR.cd.blue.pa, log: C.log.filter(l => /Reinforce/.test(l.msg)).map(l => l.msg), harbour: sc.cmdrPt('Quay East').type };
      C = mk('Mountain lake', ['Town centre']); out.inland = { bt: sc.AIR.cd.blue.bt, pa: sc.AIR.cd.blue.pa, log: C.log.filter(l => /Reinforce/.test(l.msg)).map(l => l.msg), type: sc.cmdrPt('Town centre').type };
      sc.BATTLE.size = 0; return out`);
  ok('thin side, point nearest the fight is a harbour: reinforcements come by boat', rf.coast.bt > 0 && rf.coast.pa === 0 && rf.coast.log.some(m => /by boat/.test(m)), rf.coast);
  ok('thin side, point nearest the fight is inland: reinforcements come by transport helicopter to that point', rf.inland.pa > 0 && rf.inland.bt === 0 && rf.inland.log.some(m => /transport helicopter to Town centre/.test(m)), rf.inland);

  }
  // ---- 10. cheats: budget fills the supply and bypasses every price, ammo keeps every soldier of the side at full magazines
  if (on('cheats')) {
  const ch = await J(`const sc = __sc, S = __S; const C = S.reset(1); const Q = sc.cmdrPt('Quay West'); S.own('Quay West', 'blue'); S.use(S.blue, 4, (q, i) => S.put(q, Q.x + i * 2, Q.z + 15)); S.use(S.red, 0, () => { });
      C.budget = 5; sc.CHEAT.budget = true; C.reviewT = -99; sc.cmdrThink(C); const filled = C.budget; const afford = sc.cmdrSpend(C, 'gunship'), keeps = C.budget === filled; sc.CHEAT.budget = false;
      for (const q of S.blue.slice(0, 4)) q.bot.mags = 0; sc.CHEAT.ammo = true; C.reviewT = -99; sc.cmdrThink(C); const mags = S.blue.slice(0, 4).map(q => q.bot.mags); sc.CHEAT.ammo = false;
      return { filled, afford, keeps, mags, cap: sc.SUPMAX }`);
  ok('the budget cheat fills the supply (to the cap) and spending is free', ch.filled === ch.cap && ch.afford && ch.keeps, ch);
  ok('the ammo cheat puts every soldier of the side back to full magazines', ch.mags.every(m => m === 6), ch.mags);

  }
  // ---- 11. the supply bar: a thin bar and a word for the player's side only, no numbers
  if (on('bar')) {
  const hud = await J(`const sc = __sc, S = __S; const C = S.reset(1); sc.BATTLE.team = null; const none = sc.supBarHtml ? sc.supBarHtml() : 'missing'; sc.BATTLE.team = 'blue'; C.budget = 140; const full = sc.supBarHtml(); C.budget = 20; const low = sc.supBarHtml(); sc.BATTLE.team = null; return { none, full, low }`);
  ok('the supply bar is shown for the side you play, empty for a spectator, with a plain word as its label', hud.none === '' && /Supply: plenty/.test(hud.full) && /Supply: low/.test(hud.low) && !/>\s*\d/.test(hud.full), hud);

  }
  // ---- performance with logistics running (on a freshly loaded page)
  if (on('perf')) {
  await reload(); await startBattle(30);
  const perf = await J(`const sc = __sc; sc.CMDR.on = true; sc.BATTLE.size = 30; sc.BATTLE.tickets.blue = sc.BATTLE.tickets.red = 9999; sc.BATTLE.t = 100; for (let i = 0; i < 600; i++) sc.qaTick(1/60);
      const ms = [], t0 = sc.simTime(); for (let i = 0; i < 1800; i++) { const t = performance.now(); sc.qaTick(1/60); ms.push(performance.now() - t); }
      ms.sort((a, b) => a - b); const mean = ms.reduce((a, c) => a + c, 0) / ms.length; let low = 0, bots = 0; for (const q of sc.people) if (q.bot && q.state !== 'rag') { bots++; if (q.bot.mags !== undefined && q.bot.mags <= 1) low++; }
      return { bots, low, mean, p95: ms[Math.floor(ms.length * 0.95)], p99: ms[Math.floor(ms.length * 0.99)], cmdrMs: sc.CMDR.ms, err: window.__cmdrerr || window.__sqerr || null, budget: [sc.CMDR.side.blue.budget, sc.CMDR.side.red.budget].map(v => Math.round(v)), drops: sc.SUP.drops || 0 }`);
  out('  perf with logistics (30 a side, 30 s): ' + JSON.stringify({ bots: perf.bots, lowAmmo: perf.low, meanMs: num(perf.mean, 3), p95Ms: num(perf.p95, 3), p99Ms: num(perf.p99, 3), cmdrThinkMs: num(perf.cmdrMs, 3), budgets: perf.budget, drops: perf.drops }));
  ok('performance: 30 a side with logistics for 30 simulated seconds, a think under 3 ms, no errors', perf.bots >= 40 && perf.cmdrMs < 3 && !perf.err, { mean: num(perf.mean, 2), p99: num(perf.p99, 2), think: num(perf.cmdrMs, 3), err: perf.err });
  }
}
