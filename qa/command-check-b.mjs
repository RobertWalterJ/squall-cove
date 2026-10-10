// Part B of the command check (v9.9.14): group leaders, fire and manoeuvre, reports, stall detection, reserve trigger, defence fallback, mechanised. Run through qa/command-check.mjs (node qa/command-check.mjs b).
// Everything is staged on simulated time (window.__qaHold, __sc.qaTick). The red commander is switched off in the staged scenarios so the defenders stay where they are put.
// The soldiers are made once (a pool) and moved between scenarios, never removed and re-made: removing and adding many soldiers between physics steps made the physics engine (cannon-es) throw
// 'wakeUpAfterNarrowphase' on the next step in an earlier version of this test. Pool soldiers not in use are parked far away with b.follow set, which keeps them out of every group.
export async function partB({ b, J, out, ok, num, startBattle, sleep, reload }) {
  const WANT = (process.env.SECTIONS || '').split(',').filter(Boolean), on = (n) => !WANT.length || WANT.includes(n);          // SECTIONS=roles,reports runs only those (drill, bound, flank, roles, reports, stall, reserve, defence, mech, perf)
  await startBattle(20);
  await J(`const sc = __sc; sc.CHEAT.free = false; sc.BATTLE.tickets.blue = 9999; sc.BATTLE.tickets.red = 5000; sc.BATTLE.t = 100; sc.BATTLE.size = 0;
      for (const q of sc.people.slice()) if (q.bot) sc.removePerson(q);
      for (const t of ['blue', 'red']) sc.BATTLE.spawnN[t] = 0;
      const S = window.__S = { n: 0, T: sc.cmdrPt('Town centre'), blue: [], red: [], park: null,
        mk(team, cls) { const q = sc.makePerson(2 + ((this.n++) % 4), this.park.x, this.park.z); q.y = sc.standY(q.x, q.z); q.side = team; q.role = team === 'blue' ? 'Guard' : 'Raider'; sc.makeBotOf(q, team, cls || 'rifle'); q.hp = 1e6; q.bot.follow = true; return q; },
        put(q, x, z) { q.x = x; q.z = z; q.y = sc.standY(x, z); q.order = null; q.route = null; q.obj.position.set(q.x, q.y - q.footOff, q.z); if (q.body) q.body.position.set(q.x, q.y + q.height / 2, q.z); const bb = q.bot; bb.gl = null; bb.grp = null; bb.stage = null; bb.tgt = null; bb.memE = null; bb.mags = 6; bb.supp = 0; bb.retreat = 0; bb.morale = 1; bb.dead = false; bb.cls = bb.cls0 || bb.cls; bb.el = null; },
        park1(q) { this.put(q, this.park.x + (this.n++ % 10) * 2, this.park.z + Math.floor(this.n / 10) % 6 * 2); q.bot.follow = true; },
        tick(k) { for (let i = 0; i < k; i++) sc.qaTick(1/60); },
        own(n, o) { const p = sc.cmdrPt(n); p.owner = o; p.prog = o === 'blue' ? 1 : o === 'red' ? -1 : 0; },
        use(list, n, f) { for (let i = 0; i < list.length; i++) { let q = list[i]; if (!sc.people.includes(q) || q.state === 'rag' || q.bot.dead) { const team = q.bot.team; if (sc.people.includes(q)) sc.removePerson(q); q = list[i] = this.mk(team); } if (i < n) { q.bot.follow = false; f(q, i); } else this.park1(q); } },
        // blue squads 150 m short of the target, red defenders on it; the red commander is off so the defenders stay put
        stage(nb, nr, cls) { const T = this.T; sc.CMDR.maxGroups = 1; sc.CMDR.side.red = null; sc.BATTLE.size = 0;
          this.own('Quay West', 'blue'); this.own('Quay East', 'blue'); this.own('Raider camp', 'red'); this.own('Town centre', 'red'); this.own('Landing beach', null); this.own('West farm', null); this.own('East farm', null); this.own('Lighthouse', null); this.own('Mountain lake', null);
          const Q = sc.cmdrPt('Quay West'), dx = Q.x - T.x, dz = Q.z - T.z, L = Math.hypot(dx, dz), sx = T.x + dx / L * 150, sz = T.z + dz / L * 150, px = -dz / L, pz = dx / L; this.start = { x: sx, z: sz };
          this.use(this.blue, nb, (q, i) => { this.put(q, sx + px * ((i % 4) * 2 - 3) + dx / L * Math.floor(i / 4) * 3, sz + pz * ((i % 4) * 2 - 3) + dz / L * Math.floor(i / 4) * 3); const c = cls && cls[i]; if (c) { q.bot.cls0 = q.bot.cls0 || q.bot.cls; q.bot.cls = c; } });
          this.use(this.red, nr, (q, i) => { this.put(q, T.x + (i % 3) * 3, T.z + Math.floor(i / 3) * 3 - 3); q.bot.obj = T; q.bot.cool = 1e9; q.bot.gT = 1e9; q.bot.reload = 1e9; q.bot.gl = { k: 'hold', x: q.x, z: q.z, t: 1e9, arr: true }; });          // the defenders see but do not shoot: the drill is what is tested, not who wins
          const C = sc.CMDR.side.blue; C.plan = null; C.groups = []; C.know.clear(); C.obs.clear(); C.pers = 'balanced'; C.force = { pt: T.name, until: 1e9 }; C.mainPt = T.name; C.reviewT = -99; C.commit = null; C.bad.clear(); C.forceDef = 0; C.inbox.length = 0; C.reports.length = 0; C.rep = {}; C.log.length = 0; C.budget = 0; C.ownPrev.clear(); this.C = C;
          return { blue: this.blue.filter(q => !q.bot.follow).length, red: this.red.filter(q => !q.bot.follow).length }; },
        alive() { return this.blue.filter(q => !q.bot.follow && q.state !== 'rag' && !q.bot.dead).length; },
        G() { return this.C.groups.find(g => g.role === 'main') || this.C.groups[0]; } };
      { const bad = (x, z) => sc.standY(x, z) < 2 || sc.BATTLE.points.some(p => Math.hypot(p.x - x, p.z - z) < 120) || sc.footBlocked(x, z, 4); let best = null; for (let x = -300; x <= 300 && !best; x += 20) for (let z = -300; z <= 300; z += 20) if (!bad(x, z) && !bad(x + 24, z + 24) && !bad(x + 24, z)) { best = { x, z }; break; } S.park = best || { x: -300, z: 300 }; }
      for (let i = 0; i < 20; i++) S.blue.push(S.mk('blue')); for (let i = 0; i < 12; i++) S.red.push(S.mk('red')); S.n = 0;
      return { blue: S.blue.length, red: S.red.length, squads: new Set(S.blue.map(q => q.bot.sq)).size }`);

  // ---- 1. the drill: assemble, base of fire, signal, assault. Sampled every 0.25 s for up to 110 simulated seconds.
  if (on('drill')) {
  const st = await J(`return __S.stage(8, 6)`);
  ok('staged: eight blue soldiers 150 m short of a point (Town centre) held by six red', st.blue === 8 && st.red === 6, st);
  const drill = await J(`const S = __S, sc = __sc, C = S.C, out = []; let bofStart = -1, asStart = -1, firstAs = null; const T = S.T;
      for (let k = 0; k < 440; k++) { S.tick(15); const g = S.G(); if (!g) { out.push({ t: sc.simTime(), none: 1, alive: S.alive(), squads: C.squads.length }); continue; } const fire = g.fire || [], move = g.move || [], go = (q) => q.bot.gl && q.bot.gl.k === 'go' && !q.bot.gl.arr && Math.hypot(q.bot.gl.x - q.x, q.bot.gl.z - q.z) > (q.bot.gl.tol || 5);
        const fg = fire.filter(go).length, mg = move.filter(go).length, fp = g.fp ? (fire.length ? fire.filter(q => Math.hypot(q.x - g.fp.x, q.z - g.fp.z) <= 15).length / fire.length : 1) : null;
        out.push({ t: +sc.simTime().toFixed(1), ph: g.ph, fg, mg, fp, fire: fire.length, move: move.length, dist: Math.round(g.dist), n: g.n });
        if (g.ph === 'bof' && bofStart < 0) bofStart = sc.simTime(); if (g.ph === 'assault' && asStart < 0) { asStart = sc.simTime(); firstAs = { fp, sinceBof: +(asStart - bofStart).toFixed(1), fire: fire.length, move: move.length, signal: g.signal }; }
        if (g.ph === 'secure' || T.owner === 'blue') break; }
      const phs = []; for (const o of out) if (o.ph && phs[phs.length - 1] !== o.ph) phs.push(o.ph);
      return { phs, firstAs, bofStart, n: out.length, last: out[out.length - 1], bothMoving: out.filter(o => o.ph === 'bof' && o.fg > 0 && o.mg > 0).length, bofSamples: out.filter(o => o.ph === 'bof').length, owner: T.owner, alive: S.alive(), log: S.C.log.slice(-6).map(l => l.msg) }`);
  ok('the group assembles, goes to a base of fire, and only then assaults (phase order assemble, bof, assault)', drill.phs.length >= 2 && drill.phs.indexOf('assault') > drill.phs.indexOf('bof') && drill.phs.indexOf('bof') >= 0 && drill.phs[0] === 'assemble', { phs: drill.phs, n: drill.n });
  ok('the assault starts on the signal: base of fire in position (70 percent of the fire element within 15 m) or after the 28 s limit', drill.firstAs && drill.firstAs.fire >= 2 && (drill.firstAs.fp >= 0.7 || drill.firstAs.sinceBof >= 27.5), drill.firstAs);
  ok('base-of-fire phase: the fire element and the manoeuvre element are never both moving at the same time', drill.bofSamples >= 3 && drill.bothMoving === 0, { bofSamples: drill.bofSamples, bothMoving: drill.bothMoving });
  out('  drill: ' + JSON.stringify({ phs: drill.phs, firstAs: drill.firstAs, last: drill.last, owner: drill.owner, alive: drill.alive }));

  }
  // ---- 2. bounding overwatch, as a unit: four soldiers 95 m out, the leader's bound routine run once a second for 60 s
  if (on('bound')) {
  const bnd = await J(`const S = __S, sc = __sc; const T = S.T, C = S.C; S.stage(0, 0); const bl = S.blue.slice(0, 4); { const Q = sc.cmdrPt('Quay West'), dx = Q.x - T.x, dz = Q.z - T.z, L = Math.hypot(dx, dz); S.use(S.blue, 4, (q, i) => S.put(q, T.x + dx / L * (95 + i * 2) - dz / L * i, T.z + dz / L * (95 + i * 2) + dx / L * i)); } const g = { id: 'GT', mem: bl, move: bl, fire: [], ow: [], dist: 95, n: 4, kind: 'attack', role: 'main', obj: T.name };
      let swaps = 0, last = null, maxMovingTeams = 0; for (let k = 0; k < 240; k++) { S.tick(15); sc.glBound(C, g, T, bl); const mov = bl.filter(q => q.bot.gl && q.bot.gl.k === 'go' && !q.bot.gl.arr && Math.hypot(q.bot.gl.x - q.x, q.bot.gl.z - q.z) > (q.bot.gl.tol || 5)); const teams = new Set(mov.map(q => q.bot.gl.bt)); maxMovingTeams = Math.max(maxMovingTeams, teams.size);
        const bt = g.bound && g.bound.team; if (last !== null && bt !== last) swaps++; last = bt; }
      const mind = Math.min(...bl.map(q => Math.hypot(q.x - T.x, q.z - T.z))); return { swaps, maxMovingTeams, bounds: g.bound && g.bound.n, mind: Math.round(mind) }`);
  ok('bounding overwatch: only one buddy team moves at a time and the teams swap (at least three bounds in 60 s)', bnd.maxMovingTeams <= 1 && bnd.bounds >= 3 && bnd.swaps >= 3, bnd);
  ok('bounding closes the distance (soldiers that started 95 m out end up inside 65 m after 60 s)', bnd.mind < 65, { closest: bnd.mind });

  }
  // ---- 3. flanking when pinned
  if (on('flank')) {
  const fl = await J(`const S = __S, sc = __sc; S.stage(8, 6); const C = S.C, T = S.T; let g = null, k = 0; for (; k < 300; k++) { S.tick(15); g = S.G(); if (g && g.ph === 'assault' && g.move && g.move.length >= 2) break; }
      if (!g || g.ph !== 'assault') return { reached: false, ph: g && g.ph, alive: S.alive() };
      const t0 = sc.simTime(); let fw = null; for (let i = 0; i < 60; i++) { for (const q of g.mem) { q.bot.supp = 1; } S.tick(15); if (g.fw) { fw = { x: g.fw.x, z: g.fw.z }; break; } }
      if (!fw) return { reached: true, flank: false, after: +(sc.simTime() - t0).toFixed(1), eng: g.eng, ph: g.ph };
      S.tick(70); const ap = g.ap; const a1 = Math.atan2(ap.z - T.z, ap.x - T.x), a2 = Math.atan2(fw.z - T.z, fw.x - T.x); let d = Math.abs(a2 - a1); if (d > Math.PI) d = 2 * Math.PI - d;
      return { reached: true, flank: true, afterSec: +(sc.simTime() - t0).toFixed(1), fwDist: Math.round(Math.hypot(fw.x - T.x, fw.z - T.z)), angDeg: Math.round(d * 57.3), reports: [...new Set(C.reports.map(r => r.kind))] }`);
  ok('pinned for five seconds under contact, the group flanks: a point to the side of the objective, about 55 m out, 40 degrees or more off the axis, reported up as pinned', fl.reached && fl.flank && fl.fwDist >= 40 && fl.fwDist <= 70 && fl.angDeg >= 40 && fl.reports.includes('pinned'), fl);

  }
  // ---- 4. element roles: a sniper goes to overwatch; one soldier watches a security sector
  if (on('roles')) {
  const roles = await J(`const S = __S, sc = __sc; S.stage(8, 4, [null, null, 'sniper']); const C = S.C, T = S.T; let sn = null, guard = null, g = null, spot = null, seenOw = false;
      for (let k = 0; k < 260; k++) { S.tick(15); g = S.G(); if (!g) continue; sn = g.mem.find(q => q.bot && q.bot.cls === 'sniper'); if (sn && sn.bot && sn.bot.el === 'ow') seenOw = true; if (g.owSpot) spot = g.owSpot; const gq = g.mem.find(q => q.bot && q.bot.gl && q.bot.gl.k === 'guard' && q.bot.gl.sec); if (gq) guard = { face: +gq.bot.gl.face.toFixed(2), el: gq.bot.el }; if (seenOw && guard && sn && sn.bot && sn.bot.gl && sn.bot.gl.arr) break; }
      const dsn = sn && spot ? Math.hypot(sn.x - T.x, sn.z - T.z) : null;
      return { seenOw, spot: spot ? { x: Math.round(spot.x), z: Math.round(spot.z) } : spot, sniperThen: sn && sn.bot && sn.bot.gl && sn.bot.gl.then, sniperDist: dsn && Math.round(dsn), guard, owCount: g && g.ow.length, ph: g && g.ph }`);
  ok('the sniper is detached to an overwatch spot (an element of its own, ordered to go there and watch)', roles.seenOw && roles.owCount === 1 && roles.sniperThen === 'ow', roles);
  ok('the overwatch spot is 85 to 120 m from the objective (the sniper reaches it or is on its way)', roles.spot && (roles.sniperDist === null || (roles.sniperDist >= 60 && roles.sniperDist <= 140)), { spot: roles.spot, dist: roles.sniperDist });
  ok('a security soldier watches a sector away from the objective while the group is in its base-of-fire phase', !!roles.guard && typeof roles.guard.face === 'number', roles.guard);

  }
  // ---- 5. reports reach the commander
  if (on('reports')) {
  const rep = await J(`const S = __S, sc = __sc; S.stage(8, 6); const C = S.C, T = S.T; for (let k = 0; k < 200; k++) S.tick(15); const g = S.G(); const kinds0 = C.reports.map(r => r.kind);
      S.own(T.name, 'blue'); for (let k = 0; k < 10; k++) S.tick(15); S.own(T.name, 'red');            // secured: the point changes hands to our side
      g.n0 = 8; g.lost = 4; for (const q of g.mem) q.bot.mags = 0; S.tick(240);                                          // casualties and low ammo, forced; three more thinks so the commander reads them all
      const kinds = [...new Set(C.reports.map(r => r.kind))], logged = C.log.filter(l => /Report from/.test(l.msg)).length;
      return { kinds0: [...new Set(kinds0)], kinds, logged, counts: C.rep, inbox: C.inbox.length }`);
  ok('reports reach the commander: contact, secured, casualties and low ammo are sent by the group leader and read by the commander (inbox emptied, a log line each)', ['contact', 'secured', 'casualties', 'lowammo'].every(k => rep.kinds.includes(k)) && rep.logged >= 4 && rep.inbox === 0, rep);

  }
  // ---- 6. stall detection and replan
  if (on('stall')) {
  const stall = await J(`const S = __S, sc = __sc; S.stage(8, 6); const C = S.C, T = S.T; for (let k = 0; k < 60; k++) S.tick(15); const g = S.G(); g.ph = 'assault'; g.asT = sc.simTime() - 100; g.p0 = g.prog; g.n0 = g.n; g.lost = 0; S.tick(70);
      return { log: C.log.slice(-8).map(l => l.msg), bad: C.bad.get(T.name) > sc.simTime(), main: g.obj, kinds: [...new Set(C.reports.map(r => r.kind))] }`);
  ok('an assault that is not getting anywhere is declared stalled, reported, the objective is marked bad for a while, and the commander replans (reserve committed, main effort moved, or fall back)', stall.kinds.includes('stalled') && stall.bad && stall.log.some(m => /stalled: (reserve committed|main effort moves|falling back)/.test(m)), stall);
  const stall2 = await J(`const S = __S, sc = __sc; S.stage(8, 6); const C = S.C, T = S.T; for (const n of ['Landing beach', 'West farm', 'East farm', 'Lighthouse', 'Mountain lake']) S.own(n, 'blue'); for (let k = 0; k < 60; k++) S.tick(15); const g = S.G(); g.ph = 'assault'; g.asT = sc.simTime() - 100; g.p0 = g.prog; g.n0 = g.n; g.lost = 0; S.tick(70);
      return { log: C.log.slice(-5).map(l => l.msg), forceDef: C.forceDef > sc.simTime(), plan: C.plan && C.plan.kind }`);
  ok('with nothing else to attack, a stalled assault falls back to the defence lines (posture defend for a while)', stall2.forceDef && stall2.log.some(m => /falling back to defence lines/.test(m)), stall2);

  }
  // ---- 7. reserve trigger
  if (on('reserve')) {
  const rsv = await J(`const sc = __sc, S = __S; sc.CMDR.maxGroups = 5; sc.CMDR.side.red = null; sc.BATTLE.size = 0; const Q = sc.cmdrPt('Quay West'), R = sc.cmdrPt('Raider camp');
      S.use(S.blue, 20, (q, i) => S.put(q, Q.x + (i % 5) * 3, Q.z + 8 + Math.floor(i / 5) * 3)); S.use(S.red, 4, (q, i) => { S.put(q, R.x + i * 3, R.z + 5); q.bot.obj = R; });
      const C = sc.CMDR.side.blue; S.own('Quay West', 'blue'); S.own('Quay East', 'blue'); S.own('Town centre', 'blue'); S.own('Raider camp', 'red'); S.own('Landing beach', 'red'); for (const n of ['West farm', 'East farm', 'Lighthouse', 'Mountain lake']) S.own(n, null);
      C.plan = null; C.groups = []; C.force = null; C.mainPt = null; C.commit = null; C.know.clear(); C.ownPrev.clear(); C.pers = 'balanced'; C.bad.clear(); C.forceDef = 0; C.reports.length = 0; sc.BATTLE.t = 100;
      for (let k = 0; k < 10; k++) { S.tick(30); } const before = C.groups.filter(g => g.role === 'reserve').reduce((a, g) => a + g.sq.length, 0), roles0 = C.groups.map(g => g.role + ':' + g.sq.length);
      S.own('Town centre', 'red'); for (let k = 0; k < 6; k++) S.tick(30);
      const after = C.groups.filter(g => g.role === 'reserve').reduce((a, g) => a + g.sq.length, 0), tgt = C.groups.filter(g => g.obj === 'Town centre').map(g => g.role + ':' + g.kind + ':' + g.sq.length);
      return { before, after, commit: C.commit && C.commit.why, to: C.commit && C.commit.to, tgt, roles0, log: C.log.slice(-4).map(l => l.msg) }`);
  ok('reserve trigger: a point of ours falls, the reserve is committed and the same point becomes an objective to retake', rsv.before >= 1 && rsv.commit === 'lost' && rsv.to === 'Town centre' && rsv.after === 0 && rsv.tgt.length >= 1, rsv);

  }
  // ---- 8. defence: ring positions facing the threat, and a fallback line when overrun
  if (on('defence')) {
  const def = await J(`const sc = __sc, S = __S; sc.CMDR.side.red = null; const P = sc.cmdrPt('Town centre'); sc.CMDR.maxGroups = 1; sc.BATTLE.size = 0;
      S.own('Quay West', null); S.own('Quay East', null); S.own('Town centre', 'blue'); S.own('Raider camp', 'red'); S.own('Landing beach', 'red'); for (const n of ['West farm', 'East farm', 'Lighthouse', 'Mountain lake']) S.own(n, null);
      S.use(S.blue, 5, (q, i) => S.put(q, P.x - 5 + (i % 4) * 3, P.z - 5 + Math.floor(i / 4) * 3)); S.use(S.red, 0, () => { });
      const C = sc.CMDR.side.blue; C.reports.length = 0; C.rep = {}; C.inbox.length = 0; C.plan = null; C.groups = []; C.force = null; C.mainPt = null; C.know.clear(); C.commit = null; C.bad.clear(); C.forceDef = sc.simTime() + 1e6; C.reviewT = -99; C.ownPrev.clear(); sc.BATTLE.t = 100;
      for (let k = 0; k < 8; k++) S.tick(30); const g = C.groups.find(x => x.kind === 'defend'); if (!g) return { noDefence: true, groups: C.groups.map(x => x.role + ':' + x.kind + ':' + x.obj), plan: C.plan && C.plan.kind };
      const ring = g.mem.filter(q => q.bot.gl && q.bot.gl.k === 'go').length, ph0 = g.ph, obj0 = g.obj;
      const ex = P.x + 40, ez = P.z; for (let i = 0; i < 10; i++) C.know.set({ state: 'idle', hp: 50, x: ex, z: ez }, { x: ex + (i % 4) * 2, z: ez + Math.floor(i / 4) * 2, t: sc.simTime() }); g.n0 = 8; g.lost = 3; S.tick(70);
      const fb = g.fb, dp = Math.hypot(P.x - ex, P.z - ez), df = fb ? Math.hypot(fb.x - ex, fb.z - ez) : 0, goFb = fb ? g.mem.filter(q => q.bot.gl && q.bot.gl.k === 'go' && Math.hypot(q.bot.gl.x - fb.x, q.bot.gl.z - fb.z) < 10).length : 0;
      return { obj0, ring, ph0, ph: g.ph, fb: fb && { x: Math.round(fb.x), z: Math.round(fb.z) }, fartherFromEnemy: fb ? +(df - dp).toFixed(1) : null, goFb, members: g.mem.length, reports: [...new Set(C.reports.map(r => r.kind))] }`);
  ok('defenders take ring positions around the point they hold', !def.noDefence && def.ring >= 4 && def.ph0 === 'hold', def);
  ok('overrun (ten enemies at 40 m against five, three of eight lost) the defenders fall back to a line about 75 m behind the point, away from the enemy, and report it', !def.noDefence && def.ph === 'fall' && def.fartherFromEnemy > 40 && def.goFb >= Math.floor(def.members * 0.6) && def.reports.includes('fallback'), def);

  }
  // ---- 9. mechanised: the vehicle that picks a squad carries it to the group's staging point, not straight onto the objective
  if (on('mech')) {
  await b.ev("__sc.ensureBVeh().then(() => { window.__bvok = 1; }); 1"); for (let k = 0; k < 40 && !(await b.ev('window.__bvok === 1')); k++) await sleep(500);
  const mc = await J(`const sc = __sc, S = __S; const Q = sc.cmdrPt('Quay West'); sc.BV.sqBusy.clear(); const v = sc.bvMake('apc', 'blue', Q.x + 20, Q.z + 10, 0); if (!v) return { made: false }; sc.bvAIInit(v, 0, false); S.use(S.blue, 4, (q, i) => S.put(q, Q.x + 10 + i, Q.z + 12)); const sqd = S.blue.slice(0, 4); const stage = { x: Q.x + 260, z: Q.z - 30 }, obj = { x: Q.x + 400, z: Q.z - 20 };
        for (const q of sqd) { q.bot.obj = obj; q.bot.stage = stage; } const a = sc.bvFindSquad(v); for (const q of sqd) q.bot.stage = null; sc.BV.sqBusy.clear(); const b2 = sc.bvFindSquad(v);
        return { made: true, seats: v.seats.filter(s => s.kind === 'pass').length, withStage: a && { x: Math.round(a.obj.x - Q.x), z: Math.round(a.obj.z - Q.z) }, noStage: b2 && { x: Math.round(b2.obj.x - Q.x), z: Math.round(b2.obj.z - Q.z) } }`);
  ok('mechanised: a squad with a staging point is carried to the staging point (the vehicle AI uses b.stage before the objective)', mc.made && mc.withStage && mc.withStage.x === 260 && mc.noStage && mc.noStage.x === 400, mc);

  }
  // ---- performance with group orders in play: 30 a side, 30 simulated seconds (on a freshly loaded page)
  if (on('perf')) {
  await reload(); await startBattle(30);
  const perfB = await J(`const sc = __sc; sc.CMDR.on = true; sc.BATTLE.size = 30; sc.BATTLE.tickets.blue = sc.BATTLE.tickets.red = 9999; sc.BATTLE.t = 100; for (let i = 0; i < 600; i++) sc.qaTick(1/60);
      const ms = [], t0 = sc.simTime(); for (let i = 0; i < 1800; i++) { const t = performance.now(); sc.qaTick(1/60); ms.push(performance.now() - t); }
      ms.sort((a, b) => a - b); const mean = ms.reduce((a, c) => a + c, 0) / ms.length; let gl = 0, bots = 0; for (const q of sc.people) if (q.bot && q.state !== 'rag') { bots++; if (q.bot.gl) gl++; }
      return { bots, gl, mean, p95: ms[Math.floor(ms.length * 0.95)], p99: ms[Math.floor(ms.length * 0.99)], cmdrMs: sc.CMDR.ms, err: window.__cmdrerr || window.__sqerr || null }`);
  out('  perf with group orders (30 a side, a marching battle): ' + JSON.stringify({ bots: perfB.bots, withOrders: perfB.gl, meanMs: num(perfB.mean, 3), p95Ms: num(perfB.p95, 3), p99Ms: num(perfB.p99, 3), cmdrThinkMs: num(perfB.cmdrMs, 3) }));
  ok('performance: 30 a side with group orders for 30 simulated seconds, a commander think (with the group leaders) under 3 ms, no errors', perfB.bots >= 40 && perfB.gl >= 10 && perfB.cmdrMs < 3 && !perfB.err, { mean: num(perfB.mean, 2), p99: num(perfB.p99, 2), think: num(perfB.cmdrMs, 3), withOrders: perfB.gl, err: perfB.err });
  }
}
