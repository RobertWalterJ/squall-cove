// Part D of the command check (v9.9.16): the player's part. Run through qa/command-check.mjs (node qa/command-check.mjs d [shots]).
// The three settings (all off, independent), take over and hand back, the AI plan running unless overridden, group and phase orders, the advisor (Accept, Edit, Ignore, never blocking), the soldier briefing and the
// objective on the compass, free play, the end-of-round lines, plain labels (no em dashes, no countdowns), 48 px targets on the phone, performance. At most two screenshots here (the overview commander view, the plan and advisor UI).
import fs from 'fs'; import path from 'path';
import { POOL_SRC } from './command-check-lib.mjs';
import { ROOT, sleep, startServer, launch, loadGame, PROFILES } from './harness.mjs';
export async function partD({ b, J, out, ok, num, startBattle, sleep: slp, reload, SHOTS, srvPort }) {
  const withRetry = async (fn) => { try { return await fn(); } catch (e) { if (!/wakeUpAfterNarrowphase/.test(String(e))) throw e; out('  (physics step error in the performance run: fresh page, run again)'); return await fn(); } };          // the physics engine can throw when a body is removed during a step; see QA-LOG, part B
  const WANT = (process.env.SECTIONS || '').split(',').filter(Boolean), on = (n) => !WANT.length || WANT.includes(n);          // SECTIONS=free,end runs only those (defaults, indep, take, override, group, advisor, brief, free, end, labels, shots, perf)
  await b.ev("localStorage.removeItem('squall-cove-cmdopt'); 1", true); await reload();
  await startBattle(20);
  const pool = await J(POOL_SRC); out('  pool: ' + JSON.stringify(pool));

  // ---- 1. defaults: everything off, the AI commands both sides
  if (on('defaults')) {
  const d0 = await J(`const sc = __sc; const out = { cmdSide: sc.CMDM.cmdSide, want: sc.CMDM.want, advisor: sc.CMDM.advisor, freePlay: sc.CMDM.freePlay, human: [sc.CMDR.side.blue.human, sc.CMDR.side.red.human] };
      for (let i = 0; i < 300; i++) sc.qaTick(1/60); out.mayCall = [sc.CMDR.side.blue.mayCall, sc.CMDR.side.red.mayCall]; out.thinks = sc.CMDR.thinks; out.advice = [sc.CMDR.side.blue.advice, sc.CMDR.side.red.advice]; out.chipHidden = document.getElementById('bAdv').hidden; out.err = window.__cmdrerr || null; return out`);
  ok('all three settings are off by default and the AI commands both sides (no human, both may call support)', d0.cmdSide === null && d0.want === null && d0.advisor === false && d0.freePlay === false && d0.human.every(h => h === false) && d0.mayCall.every(m => m === true) && d0.thinks > 5 && !d0.err, d0);
  ok('with the advisor off there is no advice and no HQ chip', d0.advice.every(a => a === null) && d0.chipHidden === true, { advice: d0.advice, chipHidden: d0.chipHidden });

  }
  // ---- 2. independence: each setter changes only its own setting
  if (on('indep')) {
  const ind = await J(`const sc = __sc, M = sc.CMDM; const snap = () => [M.cmdSide || M.want || 'off', M.advisor, M.freePlay]; const log = [snap()];
      sc.cmdmSetAdvisor(true); log.push(snap()); sc.cmdmSetFree(true); log.push(snap()); sc.cmdmSetMode('red'); log.push(snap()); sc.cmdmSetAdvisor(false); log.push(snap()); sc.cmdmSetMode('off'); log.push(snap()); sc.cmdmSetFree(false); log.push(snap());
      const saved = JSON.parse(localStorage.getItem('squall-cove-cmdopt') || '{}'); sc.cmdmSetAdvisor(true); const saved2 = JSON.parse(localStorage.getItem('squall-cove-cmdopt') || '{}'); sc.cmdmSetAdvisor(false); return { log, saved, saved2 }`);
  const want = [['off', false, false], ['off', true, false], ['off', true, true], ['red', true, true], ['red', false, true], ['off', false, true], ['off', false, false]];
  ok('the three settings are independent (each step changes exactly one of commander mode, advisor, free play)', JSON.stringify(ind.log) === JSON.stringify(want), ind.log);
  ok('advisor and free play are remembered between visits, commander mode never is', ind.saved2.advisor === true && !('mode' in ind.saved2) && !('cmdSide' in ind.saved2), ind.saved2);

  }
  // ---- 3. take over and hand back, the battle never pauses
  if (on('take')) {
  const tk = await J(`const sc = __sc, M = sc.CMDM; const B = sc.CMDR.side.blue, R = sc.CMDR.side.red; const t0 = sc.simTime(), bt0 = sc.BATTLE.t, th0 = sc.CMDR.thinks;
      const a = sc.cmdmTake('blue'); for (let i = 0; i < 180; i++) sc.qaTick(1/60); const after = { cmdSide: M.cmdSide, human: [B.human, R.human], mayCall: [B.mayCall, R.mayCall], fire: sc.FIRE.team };
      const b2 = sc.cmdmTake('red'); const swapped = { cmdSide: M.cmdSide, human: [B.human, R.human] };
      sc.cmdmBack('red'); const back = { cmdSide: M.cmdSide, human: [B.human, R.human], over: [B.over, R.over] };
      for (let i = 0; i < 60; i++) sc.qaTick(1/60); return { took: a, after, swapped, back, advanced: +(sc.simTime() - t0).toFixed(2), battleT: +(sc.BATTLE.t - bt0).toFixed(2), thinks: sc.CMDR.thinks - th0, over: sc.BATTLE.over }`);
  ok('Take over: the player commands one side (that side stops spending its own fire support; the other still does)', tk.took && tk.after.cmdSide === 'blue' && tk.after.human[0] === true && tk.after.human[1] === false && tk.after.mayCall[0] === false && tk.after.mayCall[1] === true && tk.after.fire === 'blue', tk.after);
  ok('taking the other side hands the first back (one commanded side at a time), and Hand back to AI returns everything to the AI', tk.swapped.cmdSide === 'red' && tk.swapped.human[0] === false && tk.swapped.human[1] === true && tk.back.cmdSide === null && tk.back.human.every(h => !h), { swapped: tk.swapped, back: tk.back.cmdSide });
  ok('the battle never pauses: the clock, the battle time and the commanders keep running through take over and hand back', tk.advanced >= 3.9 && tk.battleT >= 3.9 && tk.thinks >= 6 && tk.over === false, { simSeconds: tk.advanced, battleSeconds: tk.battleT, thinks: tk.thinks });

  }
  // ---- 4. the AI plan keeps running; the player's orders override pieces of it, and clearing them gives the AI its plan back
  if (on('override')) {
  const ov = await J(`const sc = __sc, S = __S, M = sc.CMDM; const C = S.reset(5); sc.BATTLE.size = 0; sc.BATTLE.t = 100; for (const n of ['Quay East', 'West farm', 'East farm', 'Town centre', 'Lighthouse', 'Mountain lake', 'Landing beach']) S.own(n, null); S.own('Quay West', 'blue'); S.own('Raider camp', 'red'); const Q = sc.cmdrPt('Quay West');
      S.use(S.blue, 16, (q, i) => S.put(q, Q.x + (i % 4) * 3, Q.z + 10 + Math.floor(i / 4) * 3)); S.use(S.red, 0, () => { }); sc.cmdmTake('blue', true); const think = () => { C.reviewT = -99; sc.cmdrThink(C); }; think(); think();
      const base = { plan: C.plan.kind, main: C.plan.main, ai: C.ai.kind, aiMain: C.aiMain, running: C.groups.length };
      S.own('Lighthouse', 'red'); think(); think(); const flipped = { aiMain: C.aiMain, plan: C.plan.kind };            // the AI still re-plans while you command
      S.own('Lighthouse', null); think(); think(); const m0 = C.plan.main; const other = sc.BATTLE.points.map(p => p.name).find(n => n !== m0 && n !== 'Quay West' && n !== 'Raider camp');
      sc.cmdmMain(C, other); think(); think(); const mainOver = { main: C.plan.main, grp: C.groups.find(g => g.role === 'main').obj, aiMain: C.aiMain, wanted: other };
      sc.cmdmPosture(C, 'defend'); think(); think(); const postureOver = { plan: C.plan.kind, ai: C.ai.kind };
      sc.cmdmPosture(C, null); sc.cmdmMain(C, null); think(); think(); const cleared = { plan: C.plan.kind, main: C.plan.main, over: C.over };
      return { base, flipped, m0, mainOver, postureOver, cleared }`);
  ok('while you command, the AI plan keeps running (a changed situation changes its plan and its main effort)', ov.base.running >= 3 && ov.base.plan === 'attack' && ov.base.main && ov.base.ai === 'attack', { base: ov.base, flipped: ov.flipped });
  ok('your main effort replaces the AI main effort at the group level, while the AI still knows what it would have chosen', ov.mainOver.main === ov.mainOver.wanted && ov.mainOver.grp === ov.mainOver.wanted, ov.mainOver);
  ok('your posture order replaces the AI posture (the AI keeps its own call for the advisor)', ov.postureOver.plan === 'defend' && ov.postureOver.ai !== 'defend', ov.postureOver);
  ok('clearing your orders gives the AI its plan back (no overrides, an attack on a point we do not hold)', ov.cleared.plan === 'attack' && !!ov.cleared.main && !ov.cleared.over.posture && !ov.cleared.over.main, ov.cleared);

  }
  // ---- 5. a group order and the phase orders, carried out by the same group leaders
  if (on('group')) {
  const go = await J(`const sc = __sc, S = __S; const C = S.reset(5); sc.BATTLE.size = 0; sc.BATTLE.t = 100; for (const n of ['Quay East', 'West farm', 'East farm', 'Town centre', 'Lighthouse', 'Mountain lake', 'Landing beach']) S.own(n, null); S.own('Quay West', 'blue'); S.own('Raider camp', 'red'); const Q = sc.cmdrPt('Quay West');
      S.use(S.blue, 12, (q, i) => S.put(q, Q.x + (i % 4) * 3, Q.z + 10 + Math.floor(i / 4) * 3)); sc.cmdmTake('blue', true); const think = () => { C.reviewT = -99; sc.cmdrThink(C); }; think(); think();
      const g = C.groups[C.groups.length - 1], id = g.id, name = g.name, before = { role: g.role, obj: g.obj }; sc.cmdmOrder(C, g, 'West farm'); think(); think(); S.tick(180); think();
      const g2 = C.groups.find(x => x.id === id), ordered = { role: g2.role, obj: g2.obj, kind: g2.kind, ph: g2.ph, ovr: !!g2.ovr, withOrders: g2.mem.filter(q => q.bot.gl).length, n: g2.n, name };
      const nBefore = C.groups.reduce((a, x) => a + x.n, 0); sc.cmdmRelease(C, g2); think(); think(); const released = { anyOvr: C.groups.some(x => x.ovr || x.role === 'order'), n: C.groups.reduce((a, x) => a + x.n, 0), nBefore }; return { before, ordered, released, names: C.groups.map(x => x.name) }`);
  ok('a group sent to a point goes there (role on your order, kind attack for ground we do not hold) and its leader gives its soldiers orders', go.ordered.role === 'order' && go.ordered.obj === 'West farm' && go.ordered.kind === 'attack' && go.ordered.ovr && go.ordered.withOrders >= 1 && go.ordered.withOrders === go.ordered.n, go.ordered);
  ok('releasing the group gives its soldiers back to the AI (no order left, nobody lost); groups carry plain names (Alpha, Bravo ...)', go.released && !go.released.anyOvr && go.released.n === go.released.nBefore && go.names.every(n => /^[A-Z][a-z]+( \d)?$/.test(n)) && new Set(go.names).size === go.names.length, { released: go.released, names: go.names });
  const ph = await J(`const sc = __sc, S = __S; const C = S.reset(1); sc.BATTLE.size = 0; sc.BATTLE.t = 100; const T = sc.cmdrPt('Town centre'), Q = sc.cmdrPt('Quay West'); for (const n of ['Quay East', 'West farm', 'East farm', 'Lighthouse', 'Mountain lake', 'Landing beach']) S.own(n, null); S.own('Quay West', 'blue'); S.own('Raider camp', 'red'); S.own('Town centre', 'red');
      const dx = Q.x - T.x, dz = Q.z - T.z, L = Math.hypot(dx, dz), px = -dz / L, pz = dx / L; S.use(S.blue, 8, (q, i) => S.put(q, T.x + dx / L * 85 + px * ((i % 4) * 2 - 3), T.z + dz / L * 85 + pz * ((i % 4) * 2 - 3)));
      S.use(S.red, 4, (q, i) => { S.put(q, T.x + i * 3, T.z + 3); q.bot.obj = T; q.bot.cool = 1e9; q.bot.gT = 1e9; q.bot.reload = 1e9; q.bot.gl = { k: 'hold', x: q.x, z: q.z, t: 1e9, arr: true }; }); C.force = { pt: 'Town centre', until: 1e9 }; C.mainPt = 'Town centre'; sc.cmdmTake('blue', true);
      const think = () => { C.reviewT = -99; sc.cmdrThink(C); }; think(); const g = C.groups[0]; sc.cmdmPhase(C, 'hold'); const seen = []; for (let k = 0; k < 44; k++) { S.tick(60); if (k % 4 === 3) seen.push(g.ph); }
      const heldAt = g.ph; sc.cmdmPhase(C, 'advance'); let assaultAfter = null; const t0 = sc.simTime(); for (let k = 0; k < 20; k++) { S.tick(30); if (g.ph === 'assault') { assaultAfter = +(sc.simTime() - t0).toFixed(1); break; } }
      sc.cmdmFallBack(C); think(); think(); const fb = C.groups.filter(x => x.ovr).map(x => x.ovr.kind + ':' + x.ovr.pt);
      return { heldAt, seen: [...new Set(seen)], assaultAfter, fb, pho: g.pho }`);
  ok('Hold in position keeps a group at its base of fire for 40 simulated seconds (past the normal 28 s limit)', ph.heldAt === 'bof' && ph.seen.join(',') === 'bof', ph);
  ok('Advance now gives the signal at once (the assault starts within 3 seconds)', ph.assaultAfter !== null && ph.assaultAfter <= 3, { assaultAfter: ph.assaultAfter });
  ok('Fall back orders every attacking group to hold the nearest point we hold', ph.fb.length >= 1 && ph.fb.every(f => /^defend:Quay West$/.test(f)), ph.fb);

  }
  // ---- 6. the advisor: suggestions with Accept, Edit and Ignore, never blocking
  if (on('advisor')) {
  const adv = await J(`const sc = __sc, S = __S; const C = S.reset(5); sc.BATTLE.size = 0; sc.BATTLE.t = 100; for (const n of ['Quay East', 'West farm', 'East farm', 'Town centre', 'Lighthouse', 'Mountain lake', 'Landing beach']) S.own(n, null); S.own('Quay West', 'blue'); S.own('Raider camp', 'red'); const Q = sc.cmdrPt('Quay West');
      S.use(S.blue, 12, (q, i) => S.put(q, Q.x + (i % 4) * 3, Q.z + 10 + Math.floor(i / 4) * 3)); S.use(S.red, 0, () => { }); sc.cmdmSetAdvisor(true); sc.cmdmTake('blue', true); const think = () => { C.reviewT = -99; C.advT = -99; sc.cmdrThink(C); }; think(); think();
      const a0 = C.advice && { text: C.advice.text, lines: C.advice.lines.length, differs: C.advice.differs }; const chip0 = document.getElementById('bAdv').hidden;
      sc.cmdmPosture(C, 'defend'); think(); think(); const a1 = C.advice && { differs: C.advice.differs, kind: C.advice.kind }; const chip1 = document.getElementById('bAdv').hidden;
      sc.openCommand('plan'); const tb = document.getElementById('tbBody'); const btns = [...tb.querySelectorAll('button')].map(x => x.textContent.trim()); const modal = document.getElementById('tablet').hidden === false && getComputedStyle(document.getElementById('tablet')).pointerEvents;
      const click = (txt) => { const el = [...document.querySelectorAll('#tbBody button')].find(x => x.textContent.trim().startsWith(txt)); if (el) el.click(); return !!el; };
      const ign = click('Ignore'); think(); const a2 = C.advice && { ignored: C.advice.ignored }; const chip2 = document.getElementById('bAdv').hidden;
      const acc = click('Accept the suggestion'); think(); const a3 = { over: { ...C.over }, advice: C.advice && C.advice.differs }; const chipsAfter = document.getElementById('bAdv').hidden;
      sc.cmdmPosture(C, 'hold'); think(); sc.openCommand('plan'); const tabNow = document.querySelector('#tbTabs [aria-selected="true"]').textContent;
      const edit = click('Edit the plan'); const toggled = document.getElementById('tablet').hidden === false;
      sc.cmdmSetAdvisor(false); think(); const off = C.advice; sc.toggleTablet(false); sc.cmdmBack('blue', true);
      return { a0, chip0, a1, chip1, btns, ign, a2, chip2, acc, a3, chipsAfter, tabNow, edit, toggled, off, modal }`);
  ok('with the advisor on, headquarters gives a suggested plan in plain words (a sentence, three situation lines) and the HQ chip stays hidden while you agree', adv.a0 && /^(Attack|Hold|Defend|Reinforce)/.test(adv.a0.text) && adv.a0.lines === 3 && adv.a0.differs === false && adv.chip0 === true, { a0: adv.a0, chip: adv.chip0 });
  ok('when your orders differ from the AI plan the suggestion says so and an HQ chip appears (no modal, no pause)', adv.a1 && adv.a1.differs === true && adv.chip1 === false, { a1: adv.a1, chipHidden: adv.chip1 });
  ok('the advisor card has Accept the suggestion, Edit the plan and Ignore', ['Accept the suggestion', 'Edit the plan', 'Ignore'].every(t => adv.btns.includes(t)), adv.btns.slice(0, 12));
  ok('Ignore hides the suggestion and the chip without changing anything; Accept drops your overrides and the AI plan is the plan again', adv.ign && adv.a2 && adv.a2.ignored === true && adv.chip2 === true && adv.acc && !adv.a3.over.posture && adv.a3.advice === false, { a2: adv.a2, chip2: adv.chip2, a3: adv.a3 });
  ok('Edit the plan keeps the Plan tab open for your own orders', adv.edit && adv.toggled && adv.tabNow === 'Plan', { tab: adv.tabNow });
  ok('turning the advisor off removes the advice', adv.off === null, adv.off);

  }
  // ---- 7. the soldier briefing: an objective from headquarters on the compass and the HUD line, a voice hook, follow or ignore
  if (on('brief')) {
  const br = await J(`const sc = __sc, S = __S; window.__hq = null; window.__hqVoice = (t) => { window.__hq = t; }; for (const t of ['blue', 'red']) sc.BATTLE.spawnN[t] = sc.BATTLE.spawnN[t] || 0; sc.CMDR.side.red = sc.CMDR.side.red; sc.BATTLE.size = 20; sc.BATTLE.team = 'blue'; sc.cmdmSetFree(true);
      const C = sc.CMDR.side.blue; C.reviewT = -99; sc.cmdrThink(C); sc.playBattle('blue'); for (let i = 0; i < 120; i++) sc.qaTick(1/60); const me = sc.fp.p; const b = sc.BATTLE.brief;
      sc.battleHud(true); const line = document.getElementById('hqLine'); const hint = line && !line.hidden ? line.textContent : null; const o = sc.SA.OBJ_NEAR ? sc.SA.OBJ_NEAR(me.x, me.z) : []; const mark = o.find(x => x.brief); const far = b && b.pt ? sc.cmdrPt(b.pt) : null;
      sc.SA.drawCompass(); const marks = sc.SA.S.cmp.marks.filter(m => m.k === 'obj').length; const out = { fp: sc.fp.on, brief: b && { pt: b.pt, role: b.role, text: b.text }, voice: window.__hq, hintMatches: hint === (b && b.text), briefMark: !!mark, markName: mark && mark.p.name, objMarks: marks, nearest3: o.length, dist: far ? Math.round(Math.hypot(far.x - me.x, far.z - me.z)) : null };
      sc.exitFP2 && sc.exitFP2(); return out`);
  ok('a soldier who deploys gets a short briefing from headquarters (one or two plain sentences naming a point), and the voice hook receives the same words', br.fp && br.brief && br.brief.pt && /^Headquarters: /.test(br.brief.text) && br.brief.text.length < 140 && br.voice === br.brief.text, br);
  ok('the briefing is shown as one line at the top of the view and its objective is on the compass in gold, even when it is not among the nearest three points', br.hintMatches && br.briefMark && br.markName === br.brief.pt && br.objMarks >= 3, { hint: br.hintMatches, mark: br.markName, marks: br.objMarks, nearest: br.nearest3 });

  }
  // ---- 8. free play: jumping in hands the side back unless Free play is on
  if (on('free')) {
  const fpl = await J(`const sc = __sc, M = sc.CMDM; sc.cmdmSetFree(false); sc.cmdmTake('blue', true); sc.cmdmOnEnter(); const off = M.cmdSide; sc.cmdmSetFree(true); sc.cmdmTake('blue', true); sc.cmdmOnEnter(); const on = M.cmdSide; sc.cmdmBack('blue', true); sc.cmdmSetFree(false);
      // and through the real door: entering first person
      sc.cmdmTake('red', true); sc.BATTLE.team = 'blue'; const q = sc.people.find(p => p.bot && p.bot.team === 'blue' && p.state !== 'rag'); let viaEnter = null; if (q) { sc.enterFP(q); viaEnter = M.cmdSide; sc.exitFP(); } return { off, on, viaEnter }`);
  ok('Free play off: jumping into a soldier or the gunship hands the side back to the AI. Free play on: you keep command', fpl.off === null && fpl.on === 'blue', fpl);
  ok('entering first person goes through the same door (command handed back with Free play off)', fpl.viaEnter === null, fpl);

  }
  // ---- 9. end of round lines
  if (on('end')) {
  const er = await J(`const sc = __sc; sc.cmdrReset(); sc.cmdmBack('red', true); sc.BATTLE.team = null; const rows = []; sc.CMDR.side.blue.stats.assaults = 3; sc.CMDR.side.blue.stats.stalls = 1; sc.CMDR.side.blue.stats.drops = 2; sc.CMDR.side.red.stats.commits = 1; sc.cmdmTake('blue', true); sc.CMDR.side.blue.stats.orders = 4; sc.cmdmEndRows(rows); return rows`);
  ok('the end-of-round summary has one plain line per commander (personality, what it did, and your orders if you commanded)', er.length === 2 && /^Port commander$/.test(er[0][0]) && /3 assaults, 1 stall, 2 supply drops, commanded by you \(4 orders\)/.test(er[0][1]) && /reserve committed 1 time/.test(er[1][1]), er);

  }
  // ---- 10. plain labels: no em dashes and no countdowns in anything the player can read, and the controls exist
  if (on('labels')) {
  const lab = await J(`const sc = __sc; sc.cmdmTake('blue', true); sc.cmdmSetAdvisor(true); const C = sc.CMDR.side.blue; C.advT = -99; C.reviewT = -99; sc.cmdrThink(C); sc.openCommand('plan'); const txt = [document.getElementById('tbBody').innerText, document.getElementById('tbTabs').innerText]; sc.toggleTablet(false);
      sc.openBattleSetup(); const sg = [...document.querySelectorAll('#bsBody section.sg')].find(s => s.querySelector('h3') && s.querySelector('h3').textContent === 'Command'); const setup = sg ? sg.innerText : ''; document.getElementById('bSetup').hidden = true; const menu = ['mCmdMode', 'mAdvisor', 'mFreePlay'].map(id => { const e = document.getElementById(id); return e ? e.textContent : null; }); const hud = ['bPlan', 'bAdv'].map(id => { const e = document.getElementById(id); return e ? e.textContent : null; });
      const all = txt.concat([setup], menu, hud, sc.KEYMAP.filter(r => ['Shift + T', 'Plan', 'Menu, Settings, Command'].includes(r[1])).map(r => r[2])).join('\\n'); sc.cmdmBack('blue', true); sc.cmdmSetAdvisor(false);
      return { em: /\\u2014/.test(all), clock: /\\b\\d{1,2}:\\d{2}\\b|countdown|seconds? left|\\b\\d+\\s*s\\b/i.test(all), menu, hud, hasPlanTab: /Plan/.test(txt[1]), setupHas: /Commander mode/.test(setup) && /AI advisor/.test(setup) && /Free play/.test(setup), len: all.length }`);
  ok('every new word the player reads is plain: no em dashes, no clocks or countdowns', lab.em === false && lab.clock === false && lab.len > 500, { em: lab.em, clock: lab.clock });
  ok('the controls exist: Plan tab, Plan and HQ buttons in the HUD, three Menu settings, three Battle setup rows', lab.hasPlanTab && lab.hud[0] === 'Plan' && lab.hud[1] === 'HQ suggests' && lab.menu.every(t => /: (Off|On|Port|Raiders)$/.test(t || '')) && lab.setupHas, lab);

  }
  // ---- screenshots (two): the overview with the commander view, and the plan tab with the advisor
  if (on('shots')) {
  if (SHOTS) {
    await J(`const sc = __sc; sc.cmdmSetAdvisor(true); sc.cmdmTake('blue', true); sc.CMDR.dbg = false; sc.BATTLE.size = 12; sc.BATTLE.tickets.blue = sc.BATTLE.tickets.red = 9999; for (let i = 0; i < 1500; i++) sc.qaTick(1/60); sc.god.tgt.x = 0; sc.god.tgt.z = -20; sc.god.dist = Math.max(sc.god.dist, 230 * sc.CELL); return 1`);
    await b.ev("window.__qaHold = false; 1"); await slp(5000);
    const px = await J(`const cv = document.getElementById('cmdrCv'); if (!cv || !cv.classList.contains('on')) return { on: false }; const d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 0) n++; return { on: true, n }`);
    ok('commander view on the overview: only your side plan is drawn (an overlay canvas with marks)', px.on && px.n > 400, px);
    await b.shot(path.join(ROOT, 'docs', 'cmdr_d_overview.png')); out('  screenshot docs/cmdr_d_overview.png');
    await b.ev("window.__qaHold = true; 1");
    await J(`const sc = __sc; const C = sc.CMDR.side.blue; sc.cmdmPosture(C, 'defend'); C.advT = -99; C.reviewT = -99; sc.cmdrThink(C); sc.openCommand('plan'); return 1`); await slp(1500);
    await b.shot(path.join(ROOT, 'docs', 'cmdr_d_plan_advisor.png')); out('  screenshot docs/cmdr_d_plan_advisor.png');
    await J(`const sc = __sc; sc.toggleTablet(false); sc.cmdmBack('blue', true); sc.cmdmSetAdvisor(false); return 1`);
  }

  }
  // ---- performance with the player commanding
  if (on('perf')) {
  const perf = await withRetry(async () => { await reload(); await startBattle(30); return await J(`const sc = __sc; sc.CMDR.on = true; sc.cmdmSetAdvisor(true); sc.cmdmTake('blue', true); sc.BATTLE.size = 30; sc.BATTLE.tickets.blue = sc.BATTLE.tickets.red = 9999; sc.BATTLE.t = 100; for (let i = 0; i < 600; i++) sc.qaTick(1/60);
      const ms = [], t0 = sc.simTime(); for (let i = 0; i < 1800; i++) { const t = performance.now(); sc.qaTick(1/60); ms.push(performance.now() - t); }
      ms.sort((a, b) => a - b); const mean = ms.reduce((a, c) => a + c, 0) / ms.length; let bots = 0; for (const q of sc.people) if (q.bot && q.state !== 'rag') bots++; sc.cmdmSetAdvisor(false);
      return { bots, mean, p95: ms[Math.floor(ms.length * 0.95)], p99: ms[Math.floor(ms.length * 0.99)], cmdrMs: sc.CMDR.ms, err: window.__cmdrerr || window.__sqerr || null }`); });
  out('  perf with the player commanding and the advisor on (30 a side, 30 s): ' + JSON.stringify({ bots: perf.bots, meanMs: num(perf.mean, 3), p95Ms: num(perf.p95, 3), p99Ms: num(perf.p99, 3), cmdrThinkMs: num(perf.cmdrMs, 3) }));
  ok('performance: 30 a side with the player commanding and the advisor on, a think under 3 ms, no errors', perf.bots >= 40 && perf.cmdrMs < 3 && !perf.err, { mean: num(perf.mean, 2), p99: num(perf.p99, 2), think: num(perf.cmdrMs, 3), err: perf.err });
  }
  return { phone: async () => phoneCheck({ out, ok, num, srvPort }) };
}

// the phone edition: fewer groups, the Plan tab and the new buttons at 48 px or more, nothing wider than the screen
async function phoneCheck({ out, ok, num, srvPort }) {
  const prof = PROFILES.portrait, b = await launch({ ...prof, extraArgs: ['--autoplay-policy=no-user-gesture-required'] }); out('  phone chrome pid ' + b.pid);
  const J = async (expr) => { const r = await b.ev(`JSON.stringify((()=>{ ${expr} })())`); if (!r) throw new Error('the phone page returned nothing: ' + b.errs.slice(-2).join(' / ')); return JSON.parse(r); };
  try {
    if (!await loadGame(b, `http://127.0.0.1:${srvPort}/index.html?map=port&nointro=1&gov=best&edition=phone`, 3)) throw new Error('no load');
    await b.ev("document.getElementById('help').hidden=true; window.__qaHold=true; 1"); await sleep(2500);
    await b.ev("__sc.BATTLE.size = 6; __sc.battleStart(); 1"); await sleep(7000);
    const r = await J(`const sc = __sc; for (let i = 0; i < 300; i++) sc.qaTick(1/60); sc.cmdmSetAdvisor(true); sc.cmdmTake('blue', true); const C = sc.CMDR.side.blue; C.advT = -99; C.reviewT = -99; sc.cmdrThink(C); sc.openCommand('plan');
      const small = [...document.querySelectorAll('#tablet button, #bBtns button')].filter(x => { const r = x.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.height < 47.5; }).map(x => x.textContent.trim() + ':' + Math.round(x.getBoundingClientRect().height));
      const tb = document.getElementById('tablet'), wide = tb.scrollWidth - tb.clientWidth, body = document.getElementById('tbBody'); const total = document.querySelectorAll('#tablet button').length; const hud = ['bPlan'].map(id => { const e = document.getElementById(id), r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; });
      sc.toggleTablet(false); const hb = document.getElementById('bBtns'), hudOver = hb.scrollWidth - hb.clientWidth, page = document.documentElement.scrollWidth - innerWidth, rows = new Set([...hb.querySelectorAll('button')].filter(x => x.offsetParent).map(x => Math.round(x.getBoundingClientRect().top))).size;
      return { maxGroups: sc.CMDR.maxGroups, ed: window.__ED && window.__ED.phone, small, wide, total, hud, groups: C.groups.length, hudOver, page, hudRows: rows }`);
    ok('phone edition: at most three groups a side, and the Plan tab and HUD buttons are 48 px or taller with nothing wider than the screen', r.ed === true && r.maxGroups === 3 && r.groups <= 3 && r.small.length === 0 && r.wide <= 1 && r.total >= 8 && r.hud[0][1] >= 47.5 && r.hudOver <= 1 && r.page <= 1, r);
    const errs = b.errs.filter(e => !/favicon|ERR_FAILED|Failed to load resource|AudioContext|autoplay/i.test(e)); ok('phone edition: no console errors', errs.length === 0, errs.slice(0, 3));
  } finally { await b.close(); }
}
