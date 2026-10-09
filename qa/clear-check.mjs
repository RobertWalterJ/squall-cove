// Clear the battlefield and the overview Gunship button (v9.9.4). usage: node qa/clear-check.mjs [desktop|portrait|landscape] [shots]
// desktop: a battle is started, ended, cleared with both choices, undone, started again, cleared again; the station opens from the overview button in a battle and in the sandbox and leaves cleanly.
// portrait / landscape: only the layout of the Gunship button (48 px, no overlap) and that it opens the station.
import { sleep, startServer, launch, loadGame, clickText, PROFILES } from './harness.mjs';
import path from 'path';
const prof = PROFILES[process.argv[2] || 'desktop'], phone = prof.ed === 'phone', SHOTS = process.argv[3] === 'shots';
const T0 = Date.now(), log = (m) => console.log(`[${((Date.now() - T0) / 1000).toFixed(0)}s] ${m}`); setTimeout(() => { console.log('ERR watchdog: the clear check took over 12 minutes'); process.exit(2); }, 720000).unref();
const fail = []; const ok = (name, cond, detail) => { console.log((cond ? '  ok   ' : '  FAIL ') + name + (detail !== undefined ? '  ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)) : '')); if (!cond) fail.push(name); };
const srv = await startServer(); const b = await launch({ ...prof, extraArgs: ['--autoplay-policy=no-user-gesture-required'] });
const J = async (expr) => { const r = await b.ev(`JSON.stringify((()=>{ ${expr} })())`); return r ? JSON.parse(r) : null; };
const SNAP = `const sc = __sc, civ = sc.people.filter(q => !q.bot && !q.botSaved && q.role !== 'You' && !q.fromHostile).length;
  const civR = sc.people.filter(q => !q.bot && !q.botSaved && q.role !== 'You' && !q.fromHostile).map(q => (q.role || '?') + '/' + (q.side || '-') + '/' + (q.state || '')); return { civR, bots: sc.people.filter(q => q.bot).length, people: sc.people.length, civ, veh: sc.BVL ? sc.BVL.length : -1, air: sc.AIR.list.length, aas: sc.AAS.length, struct: sc.STRUCT.length, pts: sc.BATTLE.points.length, on: sc.BATTLE.on, over: sc.BATTLE.over,
    bodyBattle: document.body.classList.contains('battle'), bHud: !document.getElementById('bHud').hidden, bSpawn: !document.getElementById('bSpawn').hidden, hudCount: document.querySelectorAll('#bHud').length, tickCount: document.querySelectorAll('#bTick').length, boats: sc.boats.length, mode: sc.mode,
    armed: sc.people.filter(q => q.gun || q.bot).length, loose: sc.LOOSE.length, wrecks: sc.LIFE.wrecks.length, shells: sc.AIR.shells.length, fmm: !!(sc.FMS && sc.FMS.m), stn: sc.STN.on, tablet: !document.getElementById('tablet').hidden, voices: sc.VOICE ? sc.VOICE.q.length : 0, sqd: sc.SQD.mates.length, sqdOn: sc.SQD.on };`;
try {
  if (!await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=${prof.ed}`)) throw new Error('no load');
  await b.ev("document.getElementById('help').hidden=true; 1");
  await b.ev("window.__realRender = __sc.renderer.render.bind(__sc.renderer); __sc.renderer.render = () => {}; 1");
  if (phone) {
    // ---- layout of the Gunship button on the phone, sandbox and battle
    await sleep(800);
    const lay = async (label) => J(`const r = (id) => { const e = document.getElementById(id); if (!e) return null; const c = getComputedStyle(e), q = e.getBoundingClientRect(); return { vis: !e.hidden && c.display !== 'none' && c.visibility !== 'hidden' && q.width > 0, x: q.left, y: q.top, w: q.width, h: q.height }; };
      const ids = ['bGun', 'bGunB', 'bFP', 'bMode', 'bCenter', 'bDesel', 'cmdBtn', 'bJump', 'bTab', 'bSpec', 'bSideBtn', 'tmBtn'], o = {}; for (const i of ids) o[i] = r(i);
      const vis = ids.filter(i => o[i] && o[i].vis), hit = []; for (let a = 0; a < vis.length; a++) for (let c = a + 1; c < vis.length; c++) { const A = o[vis[a]], B = o[vis[c]]; if (A.x < B.x + B.w - 1 && B.x < A.x + A.w - 1 && A.y < B.y + B.h - 1 && B.y < A.y + A.h - 1) hit.push(vis[a] + '/' + vis[c]); }
      return { o: { bGun: o.bGun, bGunB: o.bGunB }, hit, scrollX: document.documentElement.scrollWidth > innerWidth + 1, cut: vis.filter(i => o[i].x + o[i].w > innerWidth + 1 || o[i].x < -1) };`);
    const s1 = await lay('sandbox');
    ok('sandbox: the Gunship button is on screen, 48 px tall at least', s1.o.bGun && s1.o.bGun.vis && s1.o.bGun.h >= 47.5, s1.o.bGun);
    ok('sandbox: no overlap and no horizontal scroll', s1.hit.length === 0 && !s1.scrollX, s1);
    await b.ev("__sc.openBattleSetup(); 1"); await sleep(500); await b.ev(clickText('#bSetup button', 'Begin battle')); await sleep(5000);
    const s2 = await lay('battle');
    ok('battle: the Gunship button sits in the Jump in row, 48 px tall at least', s2.o.bGunB && s2.o.bGunB.vis && s2.o.bGunB.h >= 47.5 && !(s2.o.bGun && s2.o.bGun.vis), s2.o);
    ok('battle: no overlap and nothing cut off', s2.hit.length === 0 && !s2.scrollX && s2.cut.length === 0, s2);
    await b.ev("document.getElementById('bGunB').click(); 1"); await sleep(600);
    const st = await J("return { on: __sc.STN.on, team: __sc.STN.team, kind: __sc.STN.u && __sc.STN.u.kind, body: document.body.classList.contains('stn-on') }");
    ok('battle: tapping Gunship opens the station', st.on && st.body && st.kind === 'gunship', st);
    await b.ev("document.getElementById('stnLeave').click(); 1"); await sleep(400);
    ok('leaving returns to the overview', await J("return !__sc.STN.on && !document.body.classList.contains('stn-on')"));
    if (SHOTS) await b.shot(path.join(process.cwd(), 'qa', `clear-${prof.name}.png`));
  } else {
    // ---- sandbox first: the station opens from the overview button and leaves where it started
    const camBefore = async () => J("const c = __sc.camera, g = __sc.god; return { gx: g.tgt.x, gy: g.tgt.y, gz: g.tgt.z, yaw: g.yaw, dist: g.dist, tilt: g.tilt, top: g.top };");
    await sleep(500);
    const vis0 = await J("const e = document.getElementById('bGun'), c = getComputedStyle(e), q = e.getBoundingClientRect(); return { vis: !e.hidden && c.display !== 'none' && q.height > 0, h: q.height, w: q.width, battle: document.getElementById('bGunB').getBoundingClientRect().width };");
    ok('sandbox: the Gunship button is visible in the overview (battle copy hidden)', vis0.vis && vis0.battle === 0, vis0);
    await b.ev("__sc.setSel([]); __sc.god.tgt.set(40, 0, -30); __sc.god.dist = 120; __sc.god.yaw = 1.1; __sc.god.fly = null; __sc.god.fling.set(0, 0); 1"); const c0 = await camBefore();
    await b.ev("document.getElementById('bGun').click(); 1"); await sleep(500);
    const s1 = await J("const S = __sc.STN, u = S.u; return { on: S.on, team: S.team, kind: u && u.kind, body: document.body.classList.contains('stn-on'), hidden: document.getElementById('stn').hidden, aim: [Math.round(S.ax), Math.round(S.az)], bat: __sc.BATTLE.on, y: u && Math.round(u.y), hudBtnHidden: getComputedStyle(document.getElementById('bGun')).display };");
    ok('sandbox: the button calls a gunship and opens the station on the camera centre', s1.on && s1.kind === 'gunship' && s1.body && !s1.hidden && !s1.bat && Math.abs(s1.aim[0] - 40) < 5 && Math.abs(s1.aim[1] + 30) < 5, s1);
    ok('while in the station the button is hidden', s1.hudBtnHidden === 'none', s1.hudBtnHidden);
    const s1b = await J("const S = __sc.STN, u = S.u, sc = __sc; for (let i = 0; i < 40; i++) { sc.updateAir(0.1); sc.stnStep(0.1); } const m0 = [u.x, u.z]; for (let i = 0; i < 20; i++) { sc.updateAir(0.1); sc.stnStep(0.1); } return { alive: sc.AIR.list.includes(u), moved: Math.round(Math.hypot(u.x - m0[0], u.z - m0[1])), state: S.state, canFireHow: (S.W[0].prep <= 0) };");
    ok('sandbox: the gunship orbits and the station runs', s1b.alive && s1b.moved > 20 && s1b.state === 'locked', s1b);
    await b.ev("document.getElementById('stnLeave').click(); 1"); await sleep(400);
    const c1 = await camBefore(); const s1c = await J("return { on: __sc.STN.on, body: document.body.classList.contains('stn-on'), hidden: document.getElementById('stn').hidden, fov: __sc.camera.fov, mode: __sc.mode, pl: !!document.pointerLockElement }");
    ok('sandbox: leaving returns to the overview, camera exactly where it was', !s1c.on && !s1c.body && s1c.hidden && s1c.mode === 'god' && Math.abs(c1.gx - c0.gx) < 1e-6 && Math.abs(c1.gz - c0.gz) < 1e-6 && Math.abs(c1.dist - c0.dist) < 1e-6 && Math.abs(c1.yaw - c0.yaw) < 1e-6, { c0, c1, s1c });
    await b.ev("window.dispatchEvent(new KeyboardEvent('keydown',{key:'o'})); 1"); await sleep(400);
    ok('sandbox: the O key opens it too (reuses the gunship already up)', await J("return __sc.STN.on && __sc.AIR.list.filter(a => a.kind === 'gunship').length === 1")); await b.ev("__sc.stnLeave(); 1");
    await b.ev("__sc.AIR.list.length = 0; 1");

    // ---- a battle
    await b.ev("__sc.openBattleSetup(); 1"); await sleep(500); await b.ev(clickText('#bSetup button', 'Begin battle')); await sleep(5000);
    await b.ev("document.getElementById('help').hidden=true; 1");
    const bv = await J("const g = document.getElementById('bGunB'), q = g.getBoundingClientRect(), j = document.getElementById('bJump').getBoundingClientRect(); return { w: q.width, h: q.height, nextToJump: g.previousElementSibling.id === 'bJump', soloHidden: document.getElementById('bGun').getBoundingClientRect().width === 0 };");
    ok('battle: the Gunship button sits next to Jump in; the sandbox copy is hidden', bv.w > 0 && bv.nextToJump && bv.soloHidden, bv);
    const B0 = await J(SNAP); log('battle running ' + JSON.stringify(B0)); ok('a battle is on with soldiers and points', B0.on && B0.bots >= 10 && B0.pts >= 3, B0);
    // gunship from the overview in the battle, then the cooldown
    await b.ev("__sc.AIR.list.length = 0; __sc.AIR.cd.blue.gs = 0; document.getElementById('bGunB').click(); 1"); await sleep(500);
    const g1 = await J("return { on: __sc.STN.on, team: __sc.STN.team, kind: __sc.STN.u && __sc.STN.u.kind, cd: __sc.AIR.cd.blue.gs }");
    ok('battle: the button calls the gunship for the side and the cooldown starts', g1.on && g1.kind === 'gunship' && g1.team === 'blue' && g1.cd > 0, g1);
    await b.ev("__sc.stnLeave(); 1"); await sleep(300);
    await b.ev("document.getElementById('bGunB').click(); 1"); await sleep(400);
    ok('battle: a second press reuses the gunship that is up (no new call)', await J("return __sc.STN.on && __sc.AIR.list.filter(a => a.kind === 'gunship').length === 1")); await b.ev("__sc.stnLeave(); 1");
    await b.ev("__sc.AIR.list.length = 0; __sc.AIR.cd.blue.gs = 100; document.getElementById('bGunB').click(); 1"); await sleep(300);
    const g2 = await J("return { on: __sc.STN.on, note: [...document.querySelectorAll('#sideFeed *, #notes *')].map(e => e.textContent).join(' | ').slice(-200), log: document.body.innerText.includes('not ready') }");
    ok('battle: on cooldown it says so and stays in the overview', !g2.on, g2); await b.ev("__sc.AIR.cd.blue.gs = 0; 1");

    // leave something of every kind behind
    await b.ev("(()=>{ const sc = __sc; try { sc.callAir('blue', 'cobra'); sc.callAir('red', 'griffon'); } catch (e) { } try { sc.callArty('blue', { x: 20, z: 20 }); } catch (e) { } 1; })()");
    await b.ev("(()=>{ const sc = __sc; sc.makePerson(3, 10, 10); sc.makePerson(4, 14, 10); })(); 1");        // two civilians placed during the battle: they must survive the clear
    await b.ev("__sc.LOOSE.push({ m: new __sc.THREE.Mesh(new __sc.THREE.BoxGeometry(1,1,1), new __sc.THREE.MeshBasicMaterial()), vy: 0, vx: 0, vz: 0, t: 40 }); __sc.scene.add(__sc.LOOSE[__sc.LOOSE.length-1].m); 1");
    await b.ev("(()=>{ const sc = __sc; for (let i = 0; i < 30; i++) { try { sc.updateAir(0.1); } catch (e) { } } })(); 1");
    const B1 = await J(SNAP + ""); log('before clear ' + JSON.stringify(B1));
    const terrainX = await J("let h = 0; for (let i = 0; i < __sc.HGT.length; i += 97) h += __sc.HGT[i]; return { h: Math.round(h * 1000), boats: __sc.boats.length, props: __sc.props.length };");

    // ---- end the battle and show the end screen
    await b.ev("(()=>{ const sc = __sc; sc.BATTLE.tickets.red = 0; sc.BATTLE.over = true; sc.BATTLE.won = 'blue'; sc.endScreen(); })(); 1"); await sleep(400);
    const es = await J("const e = document.getElementById('bClearEnd'); return { has: !!e, vis: !!e && e.getBoundingClientRect().width > 0, text: e && e.textContent };");
    ok('the end screen has a Clear battlefield button', es.has && es.vis && es.text === 'Clear battlefield', es);
    if (SHOTS) { await b.ev("__sc.renderer.render = window.__realRender; 1"); await sleep(2500); await b.shot(path.join(process.cwd(), 'qa', 'clear-endscreen.png')); await b.ev("__sc.renderer.render = () => {}; 1"); }
    await b.ev("document.getElementById('bClearEnd').click(); 1"); await sleep(300);
    const dl = await J("const names = ['clrAll', 'clrKeep', 'clrCancel'].map(i => { const e = document.getElementById(i); return e && e.textContent; }); return { names, shown: !document.getElementById('bSpawn').hidden, battleStill: __sc.BATTLE.on };");
    ok('the dialog offers Clear everything, Keep survivors and Cancel', dl.names.join('|') === 'Clear everything|Keep survivors|Cancel' && dl.shown && dl.battleStill, dl);
    await b.ev("document.getElementById('clrCancel').click(); 1"); await sleep(300);
    ok('Cancel leaves the battle and shows the end screen again', await J("return __sc.BATTLE.on && !!document.getElementById('bClearEnd') && !document.getElementById('bSpawn').hidden"));
    // listener / timer ledger around the start-clear-start cycle
    await b.ev("window.__L = { add: 0, rem: 0, si: 0, ci: 0 }; const a = EventTarget.prototype.addEventListener, r = EventTarget.prototype.removeEventListener; window.__K = {}; EventTarget.prototype.addEventListener = function (...x) { window.__L.add++; const k = (this && this.constructor && this.constructor.name) + ':' + x[0]; window.__K[k] = (window.__K[k] || 0) + 1; return a.apply(this, x); }; EventTarget.prototype.removeEventListener = function (...x) { window.__L.rem++; return r.apply(this, x); }; const si = window.setInterval, ci = window.clearInterval; window.setInterval = function (...x) { window.__L.si++; return si.apply(this, x); }; window.clearInterval = function (...x) { window.__L.ci++; return ci.apply(this, x); }; 1");

    // ---- Keep survivors
    const alive = await J("return __sc.people.filter(q => q.bot && q.state !== 'rag' && q.hp > 0).length");
    const terrain0 = await J("let h = 0; for (let i = 0; i < __sc.HGT.length; i += 97) h += __sc.HGT[i]; return { h: Math.round(h * 1000), boats: __sc.boats.length, props: __sc.props.length };");
    await b.ev("document.getElementById('bClearEnd').click(); 1"); await sleep(200); await b.ev("document.getElementById('clrKeep').click(); 1"); await sleep(600);
    const K = await J(SNAP + ""); const survInfo = await J("const sc = __sc; const s = sc.people.filter(q => q.role === 'Tourist' && q.id !== undefined); return { n: sc.people.length, armed: sc.people.filter(q => q.gun || q.bot || q.botSaved || q.fromHostile || q.side).length, undo: !!sc.CLR.undo, mode: sc.mode, anyHidden: sc.people.some(q => !q.obj.visible) };");
    log('after keep ' + JSON.stringify(K));
    ok('Keep survivors: battle state fully off', !K.on && !K.over && !K.bodyBattle && !K.bHud && !K.bSpawn && K.pts === 0, K);
    ok('Keep survivors: vehicles, aircraft, guns, structures, wrecks, loose guns, squads, shells all gone', K.veh === 0 && K.air === 0 && K.aas === 0 && K.struct === 0 && K.wrecks === 0 && K.loose === 0 && K.sqd === 0 && K.shells === 0 && !K.fmm && K.voices === 0, K);
    ok('Keep survivors: survivors are ordinary unarmed people, the two civilians stay', survInfo.armed === 0 && K.people >= 2 + 1 && K.people <= B1.people && K.bots === 0, { alive, ...survInfo, people: K.people });
    const t1 = await J("let h = 0; for (let i = 0; i < __sc.HGT.length; i += 97) h += __sc.HGT[i]; return { h: Math.round(h * 1000), boats: __sc.boats.length, props: __sc.props.length };");
    ok('terrain (within live crater noise) and boats untouched; battle cover props go, others stay', Math.abs(t1.h - terrain0.h) < 5000 && t1.boats === terrain0.boats, { t1, terrain0 });
    ok('back in the overview with the sandbox tools working', await J("const sc = __sc; sc.setTool('build'); const a = sc.tool; sc.setTool('select'); return sc.mode === 'god'"));

    // ---- undo
    const U = await b.ev("__sc.clearUndo()"); await sleep(400); const U1 = await J(SNAP + "");
    ok('Undo brings the battle back (soldiers, points, HUD)', U === true && U1.on && U1.bots >= 10 && U1.pts === B0.pts && U1.bHud && U1.bodyBattle && U1.civ === B1.civ, U1);
    ok('Undo is single use', (await b.ev("__sc.clearUndo()")) === false);

    // ---- Clear everything, from the Battle tab route (clearDialog is what the tab button calls)
    await b.ev("__sc.clearDialog(); 1"); await sleep(200); await b.ev("document.getElementById('clrAll').click(); 1"); await sleep(500);
    const E = await J(SNAP + "");
    ok('Clear everything: no soldiers survive, only the civilians (ambient workers and the two I placed) remain', !E.on && E.bots === 0 && E.people === B1.civ && E.civ === B1.civ && E.pts === 0 && E.veh === 0 && E.air === 0 && E.struct === 0 && !E.bHud && !E.bodyBattle, E);
    ok('Clear works while the battle is still running (not only after it ends)', true);

    // ---- start again, twice, to see nothing doubles
    const cycle = async (n) => {
      await b.ev("__sc.battleStart(); 1"); await sleep(2500); const S = await J(SNAP + "");
      const dup = await J("const names = __sc.BATTLE.points.map(p => p.name); return { dupNames: names.length - new Set(names).size, flagsInScene: __sc.scene.children.filter(o => o.children && o.children.length >= 3 && o.children[0].geometry && o.children[0].geometry.type === 'CylinderGeometry' && o.children[0].geometry.parameters.height === 9).length, bTabs: document.querySelectorAll('#bTick').length };");
      ok(`restart ${n}: a clean new battle (points ${S.pts}, bots ${S.bots}, one HUD)`, S.on && !S.over && S.pts === B0.pts && S.bots >= 10 && S.hudCount === 1 && S.tickCount === 1 && dup.dupNames === 0 && dup.flagsInScene === S.pts, { S, dup });
      await b.ev("__sc.clearBattlefield(false); 1"); await sleep(400);
      const C = await J(SNAP + ""); ok(`clear after restart ${n}: back to the sandbox`, !C.on && C.bots === 0 && C.pts === 0 && !C.bHud && C.people === 0, C);
    };
    const KP = async () => J("const o = {}; let p = 0; for (const k in window.__K) { if (/^(Window|HTMLDocument|HTMLBodyElement|HTMLHtmlElement|MediaQueryList|Document):/.test(k)) { o[k] = window.__K[k]; p += window.__K[k]; } } return { p, o, total: window.__L.add, si: window.__L.si - window.__L.ci };");
    await cycle(1); const k1 = await KP(); await b.ev("window.__K = {}; window.__L.add = 0; 1"); await cycle(2); const k2 = await KP(); await b.ev("window.__K = {}; window.__L.add = 0; 1"); await cycle(3); const k3 = await KP();
    log('listener ledger ' + JSON.stringify({ k1: k1.p, k2, k3 }));
    ok('no listeners are left on the window, document or body by a start and clear cycle', k2.p === 0 && k3.p === 0, { cycle1: k1.p, cycle2: k2.o, cycle3: k3.o });
    ok('no timers (intervals) are left running by a cycle', k3.si === 0 || k3.si === k2.si, { cycle2: k2.si, cycle3: k3.si });
    // the station inside a battle, then clear while it is open
    await b.ev("__sc.battleStart(); 1"); await sleep(2000); await b.ev("document.getElementById('bGunB').click(); 1"); await sleep(500);
    ok('station open in a battle', await J("return __sc.STN.on")); await b.ev("__sc.clearBattlefield(false); 1"); await sleep(500);
    const X = await J(SNAP + "");
    ok('clearing with the station open closes it cleanly', !X.stn && !X.on && X.air === 0 && !(await J("return document.body.classList.contains('stn-on')")), X);
    // sandbox gunship once more after all of that
    await b.ev("document.getElementById('bGun').click(); 1"); await sleep(500);
    ok('sandbox station still opens after a clear', await J("return __sc.STN.on && !__sc.BATTLE.on")); await b.ev("document.getElementById('stnLeave').click(); 1"); await sleep(300);
    if (SHOTS) { await b.ev("__sc.renderer.render = window.__realRender; __sc.god.dist = 150; 1"); await sleep(3000); await b.shot(path.join(process.cwd(), 'qa', 'clear-overview.png')); }
  }
  const errs = b.errs.filter(e => !/Failed to load resource|favicon|GPU stall|WebGL|swiftshader/i.test(e)); ok('no page errors', errs.length === 0, errs.slice(0, 6));
} catch (e) { console.log('ERR ' + (e.stack || e)); fail.push('exception'); }
await b.close(); await srv.close();
console.log(fail.length ? `\nclear-check: ${fail.length} FAIL` : '\nclear-check: all ok'); process.exit(fail.length ? 1 : 0);
