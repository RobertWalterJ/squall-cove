// Shared staging for the command check parts C and D: a pool of soldiers made once and moved between scenarios (see the note at the top of command-check-b.mjs for why they are never removed and re-made),
// plus helpers to own points, step the game and read the groups. The text is evaluated in the page (J), the page gets window.__S.
export const POOL_SRC = `const sc = __sc; sc.CHEAT.free = false; sc.CHEAT.budget = false; sc.CHEAT.ammo = false; sc.BATTLE.tickets.blue = 9999; sc.BATTLE.tickets.red = 5000; sc.BATTLE.t = 100; sc.BATTLE.size = 0;
  for (const q of sc.people.slice()) if (q.bot) sc.removePerson(q);
  for (const t of ['blue', 'red']) sc.BATTLE.spawnN[t] = 0;
  const S = window.__S = { n: 0, T: sc.cmdrPt('Town centre'), blue: [], red: [], park: null,
    mk(team, cls) { const q = sc.makePerson(2 + ((this.n++) % 4), this.park.x, this.park.z); q.y = sc.standY(q.x, q.z); q.side = team; q.role = team === 'blue' ? 'Guard' : 'Raider'; sc.makeBotOf(q, team, cls || 'rifle'); q.hp = 1e6; q.bot.follow = true; return q; },
    put(q, x, z) { q.x = x; q.z = z; q.y = sc.standY(x, z); q.order = null; q.route = null; q.obj.position.set(q.x, q.y - q.footOff, q.z); if (q.body) q.body.position.set(q.x, q.y + q.height / 2, q.z); const bb = q.bot; bb.gl = null; bb.grp = null; bb.stage = null; bb.tgt = null; bb.memE = null; bb.mags = 6; bb.supp = 0; bb.retreat = 0; bb.morale = 1; bb.dead = false; bb.cls = bb.cls0 || bb.cls; bb.el = null; q.hp = 1e6; },
    park1(q) { this.put(q, this.park.x + (this.n++ % 10) * 2, this.park.z + Math.floor(this.n / 10) % 6 * 2); q.bot.follow = true; },
    tick(k) { for (let i = 0; i < k; i++) sc.qaTick(1/60); },
    own(n, o) { const p = sc.cmdrPt(n); p.owner = o; p.prog = o === 'blue' ? 1 : o === 'red' ? -1 : 0; },
    use(list, n, f) { for (let i = 0; i < list.length; i++) { let q = list[i]; if (!sc.people.includes(q) || q.state === 'rag' || q.bot.dead) { const team = q.bot.team; if (sc.people.includes(q)) sc.removePerson(q); q = list[i] = this.mk(team); } if (i < n) { q.bot.follow = false; f(q, i); } else this.park1(q); } },
    reset(maxGroups) { sc.CMDR.maxGroups = maxGroups || 5; sc.CMDR.side.red = null; sc.BATTLE.size = 0; sc.BATTLE.team = null; sc.CHEAT.free = false; sc.CHEAT.budget = false; sc.CHEAT.ammo = false;
      const C = sc.CMDR.side.blue; C.plan = null; C.groups = []; C.know.clear(); C.obs.clear(); C.pers = 'balanced'; C.force = null; C.mainPt = null; C.reviewT = -99; C.commit = null; C.bad.clear(); C.forceDef = 0; C.inbox.length = 0; C.reports.length = 0; C.rep = {}; C.log.length = 0; C.budget = 120; C.ownPrev.clear(); C.need = {}; C.supT = -99; C.advT = -99; this.C = C; return C; },
    teamAt(n, x, z, spread) { this.use(this.blue, n, (q, i) => this.put(q, x + (i % 4) * (spread || 2), z + Math.floor(i / 4) * (spread || 2))); },
    G() { return this.C.groups.find(g => g.role === 'main') || this.C.groups[0]; } };
  { const bad = (x, z) => sc.standY(x, z) < 2 || sc.BATTLE.points.some(p => Math.hypot(p.x - x, p.z - z) < 120) || sc.footBlocked(x, z, 4); let best = null; for (let x = -300; x <= 300 && !best; x += 20) for (let z = -300; z <= 300; z += 20) if (!bad(x, z) && !bad(x + 24, z + 24) && !bad(x + 24, z)) { best = { x, z }; break; } S.park = best || { x: -300, z: 300 }; }
  for (let i = 0; i < 20; i++) S.blue.push(S.mk('blue')); for (let i = 0; i < 12; i++) S.red.push(S.mk('red')); S.n = 0;
  for (const v of sc.BVL) if (v.ai) { v.ai.st = 'park'; v.ai.t = 1e9; }          // vehicles stay parked: their AI would spawn crew soldiers into the staged groups
  return { blue: S.blue.length, red: S.red.length, squads: new Set(S.blue.map(q => q.bot.sq)).size, park: S.park }`;
