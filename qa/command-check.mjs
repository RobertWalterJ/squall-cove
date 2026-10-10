// Command check (v9.9.13 onward): the theatre commander and everything under it. usage: node qa/command-check.mjs [a|b|c|d|all] [--baseline] [shots]
// Everything runs on simulated time: the frame loop is paused (window.__qaHold) and the test steps the game itself with __sc.qaTick(1/60), the way qa/stance-check.mjs and qa/night-check.mjs do,
// so results do not depend on the speed of the software renderer. Random numbers are not seeded, so the AI sections assert ranges and rules, not exact frames.
//   d (v9.9.16): see qa/command-check-d.mjs (settings, take over and hand back, overrides, advisor, briefing, free play, end lines, plain labels, phone 48 px, performance).
//   c (v9.9.15): see qa/command-check-c.mjs (supply budget, ammunition state, resupply, air drop, convoy, medevac, reinforcement choice, cheats, supply bar).
//   b (v9.9.14): see qa/command-check-b.mjs (group leaders, fire and manoeuvre, reports, stall, reserve, fallback, mechanised, performance).
//   a (v9.9.13): the commander thinks about once a second, picks objectives and a posture, fog of war, groups and reserve, orders reach the soldiers, support sequencing and budget accounting, performance, no console errors.
// With --baseline the perf section runs on the previous release (git HEAD, it carries the qaTick hook already) so the cost of the commander is reported against it.
// One headless Chrome, killed by PID at the end. At most three screenshots in all (with `shots`): the commander overlay on the tactical map, the commander view in overview, the briefing / advisor UI.
import fs from 'fs'; import path from 'path'; import { execSync } from 'child_process';
import { ROOT, sleep, startServer, launch, loadGame } from './harness.mjs';
const WHICH = process.argv.find(a => ['a', 'b', 'c', 'd', 'all'].includes(a)) || 'all', BASE = process.argv.includes('--baseline'), SHOTS = process.argv.includes('shots');
const run = (p) => WHICH === 'all' || WHICH === p;
const PROG = path.join(process.env.TEMP || '.', 'command-progress.log'); try { fs.writeFileSync(PROG, ''); } catch (e) { }
const out = (s) => { console.log(s); try { fs.appendFileSync(PROG, s + String.fromCharCode(10)); } catch (e) { } };
const T0 = Date.now(), log = (m) => out(`[${((Date.now() - T0) / 1000).toFixed(0)}s] ${m}`);
setTimeout(() => { out('ERR watchdog: the command check took over 90 minutes'); process.exit(2); }, 5400000).unref();
const fail = [], ok = (name, cond, detail) => { out((cond ? '  ok   ' : '  FAIL ') + name + (detail !== undefined ? '  ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)) : '')); if (!cond) fail.push(name); };
const num = (v, d = 2) => +(+v).toFixed(d);
const overrides = {};
if (BASE) {                                                          // the previous release with the test hook patched in, served as /index.html
  let html = execSync('git show ' + (process.env.BASEREF || 'HEAD') + ':index.html', { cwd: ROOT, maxBuffer: 1 << 28 }).toString('utf8');
  if (!html.includes('function qaTick(') || !html.includes('window.__qaHold')) throw new Error('the previous release has no qaTick hook');      // v9.9.12 and later carry the hook themselves
  overrides['/index.html'] = html;
}
const srv = await startServer(ROOT, 0, overrides), b = await launch({ name: 'check', ed: 'desktop', w: 900, h: 600, mobile: false, dpr: 1 });
out('chrome pid ' + b.pid + ' (killed by PID at the end)');
const J = async (expr) => { const n0 = b.errs.length, r = await b.ev(`JSON.stringify((()=>{ ${expr} })())`); if (!r) throw new Error('the page returned nothing: ' + b.errs.slice(n0).join(' / ').slice(0, 600) + ' :: ' + expr.slice(0, 160).replace(/\s+/g, ' ')); return JSON.parse(r); };
const URL0 = `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=desktop`;
const reload = async () => { if (!await loadGame(b, URL0, 3)) throw new Error('no load'); await b.ev("document.getElementById('help').hidden=true; window.__qaHold=true; __sc.ensureWeapons && __sc.ensureWeapons(); 1"); await sleep(3000); };      // a clean page for the performance runs: staged scenarios can leave the physics engine in a state where a step throws
const startBattle = async (size) => { await b.ev(`document.getElementById('help').hidden=true; __sc.BATTLE.size=${size}; __sc.battleStart(); 1`); await sleep(7000); };
const tick = (n) => J(`for (let i=0;i<${n};i++) __sc.qaTick(1/60); return __sc.simTime()`);
try {
  if (!await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=desktop`, 3)) throw new Error('no load');
  await b.ev("document.getElementById('help').hidden=true; window.__qaHold=true; __sc.ensureWeapons && __sc.ensureWeapons(); 1"); await sleep(3000);
  log('loaded' + (BASE ? ' (baseline: previous release)' : ''));

  if (run('a') && !BASE) {
    // ================================================================ PART A
    await startBattle(20);
    await J(`const sc = __sc; for (const q of sc.people.slice()) if (!q.bot && q.side !== 'blue' && q.side !== 'red') sc.removePerson(q); sc.CHEAT.free = false; sc.CHEAT.budget = false; sc.BATTLE.tickets.blue = sc.BATTLE.tickets.red = 9999;
      for (const t of ['blue', 'red']) for (let n = 0; sc.cmdrSquads(t).length < 5 && n < 40; n++) sc.spawnBot(t, true); return 1`);          // the opening is a real firefight, so top both sides up to five squads and the checks have an army to command
    const s0 = await J(`const sc = __sc; return { on: sc.CMDR.on, blue: !!sc.CMDR.side.blue, red: !!sc.CMDR.side.red, pers: [sc.CMDR.side.blue.pers, sc.CMDR.side.red.pers], bots: sc.people.filter(q => q.bot).length }`);
    ok('a battle starts with one commander per side, each with a personality', s0.on && s0.blue && s0.red && s0.pers.every(p => ['aggressive', 'balanced', 'cautious'].includes(p)), s0);

    // ---- the thinking loop: about once a second per side
    await J(`const sc = __sc; sc.CMDR.thinks = 0; sc.CMDR.side.blue.plan = null; sc.CMDR.side.red.plan = null; return 1`);
    const t1 = await J(`const sc = __sc; for (let i = 0; i < 600; i++) sc.qaTick(1/60); return { thinks: sc.CMDR.thinks, ms: sc.CMDR.ms, err: window.__cmdrerr || null, bt: sc.BATTLE.t, tix: sc.BATTLE.tickets }`);
    ok('the commanders think about once a second each (two sides, 10 simulated seconds: 16 to 24 turns)', t1.thinks >= 16 && t1.thinks <= 24 && !t1.err, t1);
    const g1 = await J(`const sc = __sc, out = {}; for (const t of ['blue', 'red']) { const C = sc.CMDR.side[t], sq = sc.cmdrSquads(t), seen = new Map(); let dup = 0, orphan = 0; for (const g of C.groups) for (const id of g.sq) { if (seen.has(id)) dup++; seen.set(id, g.id); } for (const s of sq) if (!seen.has(s.id)) orphan++;
      const res = C.groups.filter(g => g.role === 'reserve').reduce((a, g) => a + g.sq.length, 0); out[t] = { squads: sq.length, groups: C.groups.length, roles: C.groups.map(g => g.role + ':' + g.sq.length + '>' + g.obj), dup, orphan, reserve: res, plan: C.plan && C.plan.kind, pers: C.pers, max: sc.CMDR.maxGroups }; } return out`);
    ok('every directed squad belongs to exactly one group, none left over', ['blue', 'red'].every(t => g1[t].dup === 0 && g1[t].orphan === 0 && g1[t].squads >= 3), g1);
    ok('no side has more groups than the cap (5 on the desktop, 3 on the phone)', ['blue', 'red'].every(t => g1[t].groups >= 1 && g1[t].groups <= g1[t].max), { blue: g1.blue.groups, red: g1.red.groups });
    ok('the opening is an attack on the points (the race for neutral ground)', ['blue', 'red'].every(t => g1[t].plan === 'attack'), { blue: g1.blue.plan, red: g1.red.plan });
    // reserve: out of the opening and with nothing threatened, a fifth to a sixth of the squads wait in reserve (rounded; none below four squads)
    const rs = await J(`const sc = __sc; sc.BATTLE.t = 100; for (const t of ['blue', 'red']) { const C = sc.CMDR.side[t]; C.know.clear(); C.reviewT = -99; C.plan = null; sc.cmdrThink(C); } const out = {}; for (const t of ['blue', 'red']) { const C = sc.CMDR.side[t], N = sc.cmdrSquads(t).length, res = C.groups.filter(g => g.role === 'reserve').reduce((a, g) => a + g.sq.length, 0), P = sc.CPERS[C.pers]; out[t] = { N, res, pers: C.pers, want: N >= 4 ? Math.max(1, Math.round(N * P.reserve)) : 0, plan: C.plan.kind }; } return out`);
    ok('the reserve is the fraction the personality asks for (cautious more than aggressive), and only when there are four squads or more', ['blue', 'red'].every(t => rs[t].plan === 'reinforce' ? rs[t].res === 0 : rs[t].res === rs[t].want), rs);

    // ---- orders reach the soldiers: a soldier's objective is its group's point, and group members carry the group id
    const ord = await J(`const sc = __sc; const bad = []; let n = 0; for (const t of ['blue', 'red']) { const C = sc.CMDR.side[t]; for (const q of sc.people) { const bb = q.bot; if (!bb || bb.team !== t || bb.dead || bb.crew || bb.follow || bb.psq) continue; n++; const g = C.groups.find(x => x.id === bb.grp); const p = g && sc.cmdrPt(g.obj); if (!g || !p || bb.obj !== p || !g.sq.includes(bb.sq)) bad.push([t, bb.sq, bb.grp, bb.obj && bb.obj.name]); } } return { n, bad: bad.slice(0, 5), nbad: bad.length }`);
    ok('every soldier takes the objective of the group its squad is in', ord.n > 10 && ord.nbad === 0, ord);

    // ---- fog of war. Blue's soldiers are gathered at their quay; six red soldiers are put on a red-held point they cannot see.
    const fog = await J(`const sc = __sc, C = sc.CMDR.side.blue, E = sc.cmdrPt('Landing beach'), Q = sc.cmdrPt('Quay West');
      const blues = sc.people.filter(q => q.bot && q.bot.team === 'blue' && !q.bot.crew), reds = sc.people.filter(q => q.bot && q.bot.team === 'red' && !q.bot.crew);
      blues.forEach((q, i) => { q.x = Q.x + (i % 6) * 2; q.z = Q.z + Math.floor(i / 6) * 2 + 4; q.y = sc.standY(q.x, q.z); q.order = null; q.bot.tgt = null; q.bot.memE = null; });
      sc.BATTLE.points.forEach(p => { if (p.name === 'Lighthouse' && p.owner === 'blue') p.owner = null; });
      const est = () => { C.know.clear(); C.obs.clear(); C.lastN.clear(); const sq = sc.cmdrSquads('blue'), fr = sc.cmdrKnow(C), X = sc.cmdrContext(C, sq, fr), a = X.att.find(x => x.p === E); return { str: +sc.cmdrStr(C, E, X).toFixed(3), score: +a.score.toFixed(4), radio: X.radio }; };
      const away = []; reds.slice(0, 6).forEach((q, i) => { q.x = -150 + i; q.z = -250; q.y = sc.standY(q.x, q.z); });
      const a = est();
      reds.slice(0, 6).forEach((q, i) => { q.x = E.x + (i % 3) * 3; q.z = E.z + Math.floor(i / 3) * 3; q.y = sc.standY(q.x, q.z); q.bot.tgt = null; });
      const hidden = est();
      const lh = sc.cmdrPt('Lighthouse'); const own0 = lh.owner; lh.owner = 'blue';
      const radio = est(); lh.owner = own0;
      return { away: a, hidden, radio, redOnBeach: reds.slice(0, 6).filter(q => Math.hypot(q.x - E.x, q.z - E.z) < 50).length }`);
    ok('fog of war: six unseen enemies on a point change neither the estimate nor the score the commander gives it', fog.redOnBeach === 6 && fog.hidden.str === fog.away.str && fog.hidden.score === fog.away.score, { away: fog.away, hidden: fog.hidden });
    ok('with a radio mast the commander sees them (estimate rises to the real number)', fog.radio.radio && fog.radio.str >= 6, fog.radio);

    // ---- staged scenarios: what the commander picks. Fake contacts stand in for what the soldiers have reported.
    const stage = `const sc = __sc, C = sc.CMDR.side.blue, now = sc.simTime(), own = (n, o) => { const p = sc.cmdrPt(n); p.owner = o; p.prog = o === 'blue' ? 1 : o === 'red' ? -1 : 0; };
      const fake = (n, x, z) => { for (let i = 0; i < n; i++) C.know.set({ state: 'idle', hp: 50, x, z }, { x: x + (i % 4) * 2, z: z + Math.floor(i / 4) * 2, t: sc.simTime() }); };
      const reset = () => { C.know.clear(); C.obs.clear(); C.lastN.clear(); C.plan = null; C.mainPt = null; C.reviewT = -99; C.groups = []; C.force = null; C.commit = null; C.bad.clear(); C.forceDef = 0; C.ownPrev.clear(); sc.BATTLE.t = 100; sc.BATTLE.tickets.blue = sc.BATTLE.tickets.red = 80; C.pers = 'balanced'; sc.CMDR.diff = 'normal'; };
      const seeAll = () => { for (const p of sc.BATTLE.points) C.obs.set(p.name, sc.simTime()); };
      const gather = () => { const Q = sc.cmdrPt('Quay West'); sc.people.filter(q => q.bot && q.bot.team === 'blue' && !q.bot.crew && !q.bot.psq).forEach((q, i) => { q.x = Q.x + (i % 6) * 2; q.z = Q.z + 6 + Math.floor(i / 6) * 2; q.y = sc.standY(q.x, q.z); q.order = null; q.bot.tgt = null; q.bot.memE = null; }); };
      const think = () => { gather(); seeAll(); C.reviewT = -99; sc.cmdrThink(C); const m = C.groups.find(g => g.role === 'main'); return { plan: C.plan.kind, main: m && m.obj, kind: m && m.kind, roles: C.groups.map(g => g.role + ':' + g.kind + ':' + g.obj + ':' + g.sq.length) }; };`;
    const weak = await J(stage + `reset(); own('Quay West','blue'); own('Quay East','blue'); own('West farm','blue'); own('Raider camp','red'); own('Landing beach','red'); own('Town centre','red'); own('Lighthouse',null); own('East farm',null); own('Mountain lake',null);
      gather(); seeAll(); fake(10, sc.cmdrPt('Town centre').x, sc.cmdrPt('Town centre').z); return think()`);
    ok('a point the enemy holds weakly is attacked in preference to a strongly held one', weak.plan === 'attack' && weak.kind === 'attack' && weak.main !== 'Town centre' && weak.main !== 'Raider camp', weak);
    const strongHeld = await J(stage + `reset(); own('Quay West','blue'); own('Quay East','blue'); own('Town centre','blue'); own('Raider camp','red'); own('Landing beach','red'); own('Lighthouse',null); own('West farm',null); own('East farm',null); own('Mountain lake',null);
      fake(8, sc.cmdrPt('Town centre').x + 10, sc.cmdrPt('Town centre').z); return think()`);
    ok('a strategic point of ours under heavy attack gets a defence (posture reinforce, main effort defending that point)', strongHeld.plan === 'reinforce' && strongHeld.kind === 'defend' && strongHeld.main === 'Town centre', strongHeld);
    const quiet = await J(stage + `reset(); own('Quay West','blue'); own('Quay East','blue'); own('Town centre','blue'); own('Raider camp','red'); own('Landing beach','red'); own('Lighthouse',null); own('West farm',null); own('East farm',null); own('Mountain lake',null); return think()`);
    ok('an even battle with nothing threatened is an attack, aimed at a point we do not hold', quiet.plan === 'attack' && quiet.kind === 'attack' && !['Quay West', 'Quay East', 'Town centre'].includes(quiet.main), quiet);
    const hq = await J(stage + `reset(); own('Quay West','blue'); own('Quay East','blue'); own('Raider camp','red'); own('Landing beach','red'); own('Lighthouse',null); own('Town centre',null); own('West farm',null); own('East farm',null); own('Mountain lake',null); const r = think(); const X = C.ctx; return { ...r, hqScore: +X.att.find(a => a.p.name === 'Raider camp').score.toFixed(3), best: +X.att[0].score.toFixed(3) }`);
    ok('the enemy headquarters is never the main effort while its side holds another point', hq.main !== 'Raider camp' && hq.hqScore < hq.best * 0.2, hq);
    const posts = await J(stage + `reset(); own('Quay West','blue'); own('Quay East','blue'); own('Raider camp','red'); own('Landing beach','red'); gather(); seeAll(); const sq = sc.cmdrSquads('blue'); const X = sc.cmdrContext(C, sq, sc.cmdrKnow(C)); const out = {};
      for (const k of ['aggressive', 'balanced', 'cautious']) { X.P = sc.CPERS[k]; X.conf = 0.9; X.dk = 1; out[k + '_0.9'] = sc.cmdrPosture(C, X).kind; X.conf = 1.1; out[k + '_1.1'] = sc.cmdrPosture(C, X).kind; X.conf = 0.45; out[k + '_0.45'] = sc.cmdrPosture(C, X).kind; }
      X.P = sc.CPERS.balanced; X.dk = 1.25; X.conf = 1.1; out.easy_1_1 = sc.cmdrPosture(C, X).kind; return out`);
    ok('personality moves the commit threshold: at an edge of 0.9 an aggressive commander attacks, a balanced one holds, a cautious one holds', posts['aggressive_0.9'] === 'attack' && posts['balanced_0.9'] === 'hold' && posts['cautious_0.9'] === 'hold', posts);
    ok('a clear edge (1.1) is an attack for balanced and aggressive; a cautious commander still holds', posts['balanced_1.1'] === 'attack' && posts['aggressive_1.1'] === 'attack' && posts['cautious_1.1'] === 'hold', posts);
    ok('losing badly (0.45) every personality defends; an easy difficulty needs more edge than normal', ['aggressive', 'balanced', 'cautious'].every(k => posts[k + '_0.45'] === 'defend') && posts.easy_1_1 === 'hold', posts);

    // ---- group continuity: the same groups keep their squads over time (no thrash), and a captured objective moves the group on
    const cont = await J(stage + `reset(); own('Quay West','blue'); own('Quay East','blue'); own('Raider camp','red'); own('Landing beach','red'); own('Lighthouse',null); own('Town centre',null); own('West farm',null); own('East farm',null); own('Mountain lake',null);
      gather(); seeAll(); C.reviewT = -99; sc.cmdrThink(C); const ids0 = C.groups.map(g => g.id + ':' + g.sq.join('+')).join('|'), mp0 = C.mainPt; let changes = 0; let prev = ids0;
      for (let k = 0; k < 8; k++) { for (let i = 0; i < 90; i++) sc.qaTick(1/60); seeAll(); C.reviewT = -99; sc.cmdrThink(C); const cur = C.groups.map(g => g.id + ':' + g.sq.join('+')).join('|'); if (cur !== prev) changes++; prev = cur; }
      return { ids0, prev, changes, mp0, mp1: C.mainPt }`);
    ok('groups are stable over eight reviews in a quiet stretch (at most two membership changes while soldiers die and spawn)', cont.changes <= 2, cont);
    const flip = await J(stage + `reset(); own('Quay West','blue'); own('Quay East','blue'); own('Raider camp','red'); own('Landing beach','red'); own('Lighthouse',null); own('Town centre',null); own('West farm',null); own('East farm',null); own('Mountain lake',null);
      think(); const first = C.mainPt, g = C.groups.find(x => x.role === 'main'), id = g.id; own(first, 'blue'); const r = think(); const g2 = C.groups.find(x => x.role === 'main'); return { first, now: r.main, sameGroup: g2 && g2.id === id, kind: r.kind }`);
    ok('when the main objective is taken the same group is given the next one', flip.now && flip.now !== flip.first && flip.sameGroup, flip);

    // ---- support: budget accounting and sequencing
    const bud = await J(stage + `reset(); C.budget = 100; const a = sc.cmdrSpend(C, 'arty'), after = C.budget; C.budget = 5; const b2 = sc.cmdrSpend(C, 'gunship'), after2 = C.budget; sc.CHEAT.free = true; C.budget = 5; const c3 = sc.cmdrSpend(C, 'gunship'), after3 = C.budget; sc.CHEAT.free = false; return { a, after, b2, after2, c3, after3, team: sc.BATTLE.team }`);
    ok('budget accounting: a call costs its price, a call you cannot afford is refused and costs nothing, the free cheat bypasses it', bud.a && bud.after === 88 && !bud.b2 && bud.after2 === 5 && bud.c3 && bud.after3 === 5, bud);
    const sup = await J(stage + `reset(); own('Quay West','blue'); own('Quay East','blue'); own('Raider camp','red'); own('Landing beach','red'); own('Lighthouse',null); own('Town centre',null); own('West farm',null); own('East farm',null); own('Mountain lake',null);
      sc.BATTLE.team = null; sc.AIR.cd.blue.ar = 0; sc.AIR.cd.blue.gr = 99; sc.AIR.cd.blue.gs = 99; sc.AIR.cd.blue.st = 99; C.budget = 100; sc.AIR.shells.length = 0; gather(); seeAll(); const tp = sc.cmdrPt('Landing beach'); fake(6, tp.x, tp.z); think();
      let m = null, P = null; for (let k = 0; k < 6; k++) { gather(); m = C.groups.find(g => g.role === 'main'); P = sc.cmdrPt(m.obj); fake(6, P.x, P.z);
        for (const id of m.sq) for (const q of sc.people) if (q.bot && q.bot.sq === id) { const a = Math.random() * 6.28; q.x = P.x - 100; q.z = P.z + Math.sin(a) * 6; q.y = sc.standY(q.x, q.z); }
        C.supT = -99; C.reviewT = -99; C.mayCall = true; sc.cmdrThink(C); if (sc.AIR.shells.length) break; }
      const spent = 100 - C.budget, ar = sc.AIR.cd.blue.ar, shells = sc.AIR.shells.length; return { main: m.obj, spent: +spent.toFixed(2), arCd: ar, shells, log: C.log.slice(-3).map(l => l.msg) }`);
    ok('before an assault arrives the commander puts artillery on a defended objective, once, and pays for it', sup.shells > 0 && sup.arCd > 0 && sup.spent >= 11.5 && sup.log.some(m => /Artillery/.test(m)), sup);
    await J(`const sc = __sc; sc.BATTLE.team = null; sc.AIR.shells.length = 0; return 1`);

    // ---- removals inside the physics step are deferred (the cannon-es hazard): a shattering impact is queued, the prop is still there during the step and is fractured right after it
    const fq = await J(`const sc = __sc; const o = sc.objects.find(x => x.body && !x.gone && x.m); if (!o) return { none: true }; const f0 = sc.frags.length, n0 = sc.world.bodies.length; o.m = Object.assign({}, o.m, { str: 0.0001 });
      o.body.dispatchEvent({ type: 'collide', body: { mass: 2000, velocity: { x: 0, y: -10, z: 0 }, sco: null }, contact: { getImpactVelocityAlongNormal: () => -12 } }); const queued = !o.gone, bodiesDuring = sc.world.bodies.length; sc.qaTick(1/60); return { queued, bodiesDuring: bodiesDuring - n0, gone: !!o.gone, frags: sc.frags.length - f0 }`);
    ok('a prop that shatters on impact is queued while the physics step runs and fractured just after it (nothing removed inside the step)', !fq.none && fq.queued === true && fq.bodiesDuring === 0 && fq.gone === true && fq.frags >= 3, fq);

    // ---- performance: 30 a side in a staged firefight, 30 simulated seconds. Commander on versus off in the same build.
    await startBattle(30);
    const perf = async (on) => J(`const sc = __sc; sc.CMDR.on = ${on}; sc.BATTLE.size = 30; sc.BATTLE.tickets.blue = sc.BATTLE.tickets.red = 9999; const pt = sc.BATTLE.points.find(p => p.name === 'Town centre') || sc.BATTLE.points[0]; let nb = 0, nr = 0;
      for (const q of sc.people) { if (!q.bot || q.bot.crew) continue; const blue = q.bot.team === 'blue', k = blue ? nb++ : nr++; const a = (k % 15) * 0.4 - 2.8, d = blue ? -30 : 30; q.x = pt.x + Math.sin(a) * 18; q.z = pt.z + d + Math.cos(a) * 3 * (blue ? -1 : 1); q.y = sc.standY(q.x, q.z); q.order = null; q.route = null; }
      for (let i = 0; i < 60; i++) sc.qaTick(1/60); const ms = [], t0 = sc.simTime(); for (let i = 0; i < 1800; i++) { const t = performance.now(); sc.qaTick(1/60); ms.push(performance.now() - t); }
      ms.sort((a, b) => a - b); const mean = ms.reduce((a, c) => a + c, 0) / ms.length; return { bots: sc.people.filter(q => q.bot && q.state !== 'rag').length, mean, p95: ms[Math.floor(ms.length * 0.95)], p99: ms[Math.floor(ms.length * 0.99)], max: ms[ms.length - 1], sim: sc.simTime() - t0, cmdrMs: sc.CMDR.ms, thinks: sc.CMDR.thinks }`);
    let pOff, pOn; try { pOff = await perf(false); pOn = await perf(true); } catch (e) { if (!/wakeUpAfterNarrowphase/.test(String(e))) throw e; out('  (physics step error in the performance run: fresh page, run again)'); await reload(); await startBattle(30); pOff = await perf(false); pOn = await perf(true); }
    out('  perf commander OFF (legacy planBattle): ' + JSON.stringify({ bots: pOff.bots, meanMs: num(pOff.mean, 3), p95Ms: num(pOff.p95, 3), p99Ms: num(pOff.p99, 3) }));
    out('  perf commander ON  (this release):      ' + JSON.stringify({ bots: pOn.bots, meanMs: num(pOn.mean, 3), p95Ms: num(pOn.p95, 3), p99Ms: num(pOn.p99, 3), cmdrThinkMs: num(pOn.cmdrMs, 3), thinks: pOn.thinks }));
    ok('performance: 30 a side for 30 simulated seconds, the commander adds under 1 ms to the mean step and one think takes under 3 ms', pOn.bots >= 40 && pOn.mean - pOff.mean < 1.0 && pOn.cmdrMs < 3, { on: num(pOn.mean, 2), off: num(pOff.mean, 2), think: num(pOn.cmdrMs, 3) });
    const errs = await b.ev('window.__cmdrerr || window.__sqerr || null', true); ok('no commander errors were recorded', !errs, errs);
  }

  if (run('a') && !BASE && SHOTS) {
    // ---- the debug overlay: pixels on the overview canvas, then a picture of the tactical map with the plans drawn on it
    await startBattle(14);
    await J(`const sc = __sc; sc.BATTLE.tickets.blue = sc.BATTLE.tickets.red = 9999; for (let i = 0; i < 1800; i++) sc.qaTick(1/60); sc.CMDR.dbg = true; return 1`);
    await b.ev("window.__qaHold = false; 1"); await sleep(4000);
    const px = await J(`const cv = document.getElementById('cmdrCv'); if (!cv || !cv.classList.contains('on')) return { on: false }; const d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 0) n++; return { on: true, n, w: cv.width, h: cv.height }`);
    ok('the cmdr debug overlay draws on the overview (a canvas above the scene with marks on it)', px.on && px.n > 400, px);
    await b.ev("window.__qaHold = true; 1");
    await b.send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'l', code: 'KeyL', windowsVirtualKeyCode: 76 }); await b.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'l', code: 'KeyL', windowsVirtualKeyCode: 76 }); await sleep(2500);
    const open = await b.ev("!!(document.getElementById('tmap') && !document.getElementById('tmap').hidden) || (typeof __sc.TMAP !== 'undefined')", true);
    await b.shot(path.join(ROOT, 'docs', 'cmdr_a_tactical_map.png')); log('screenshot docs/cmdr_a_tactical_map.png (tactical map open: ' + open + ')');
  }

  if (run('b') && !BASE) { const { partB } = await import('./command-check-b.mjs'); await partB({ b, J, out, ok, num, startBattle, sleep, reload }); }

  if (run('c') && !BASE) { const { partC } = await import('./command-check-c.mjs'); await partC({ b, J, out, ok, num, startBattle, sleep, reload }); }

  let D_PHONE = null;
  if (run('d') && !BASE) { const { partD } = await import('./command-check-d.mjs'); const r = await partD({ b, J, out, ok, num, startBattle, sleep, reload, SHOTS, srvPort: srv.port }); D_PHONE = r && r.phone; }

  if (run('a') && BASE) {
    await startBattle(30);
    const pBase = await J(`const sc = __sc; sc.BATTLE.size = 30; sc.BATTLE.tickets.blue = sc.BATTLE.tickets.red = 9999; const pt = sc.BATTLE.points.find(p => p.name === 'Town centre') || sc.BATTLE.points[0]; let nb = 0, nr = 0;
      for (const q of sc.people) { if (!q.bot || q.bot.crew) continue; const blue = q.bot.team === 'blue', k = blue ? nb++ : nr++; const a = (k % 15) * 0.4 - 2.8, d = blue ? -30 : 30; q.x = pt.x + Math.sin(a) * 18; q.z = pt.z + d + Math.cos(a) * 3 * (blue ? -1 : 1); q.y = sc.standY(q.x, q.z); q.order = null; q.route = null; }
      for (let i = 0; i < 60; i++) sc.qaTick(1/60); const ms = []; for (let i = 0; i < 1800; i++) { const t = performance.now(); sc.qaTick(1/60); ms.push(performance.now() - t); }
      ms.sort((a, b) => a - b); const mean = ms.reduce((a, c) => a + c, 0) / ms.length; return { bots: sc.people.filter(q => q.bot && q.state !== 'rag').length, mean, p95: ms[Math.floor(ms.length * 0.95)], p99: ms[Math.floor(ms.length * 0.99)] }`);
    out('  perf BASELINE (the previous build, BASEREF, default HEAD): ' + JSON.stringify({ bots: pBase.bots, meanMs: num(pBase.mean, 3), p95Ms: num(pBase.p95, 3), p99Ms: num(pBase.p99, 3) }));
  }

  const errs = b.errs.filter(e => !/favicon|ERR_FAILED|Failed to load resource|AudioContext|autoplay/i.test(e));
  const phys = errs.filter(e => /wakeUpAfterNarrowphase/.test(e)), other = errs.filter(e => !/wakeUpAfterNarrowphase/.test(e) && !/^\s+at /.test(e));
  out('  physics-step errors recorded (cannon-es wakeUpAfterNarrowphase, a body removed inside a step; the performance runs are retried on a fresh page when one hits): ' + phys.length);
  ok('no console errors other than that physics-step one', other.length === 0, other.slice(0, 5));
  if (D_PHONE) { await b.close(); await D_PHONE(); }          // the phone edition is a second Chrome, started only after the first one is gone
} catch (e) { out('ERR ' + (e && e.stack || e)); fail.push('crash'); }
finally { await b.close(); await srv.close(); }
out(fail.length ? `\nFAILED (${fail.length}): ${fail.join(' | ')}` : '\nALL OK'); process.exit(fail.length ? 1 : 0);
