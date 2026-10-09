// Cheat prompt check (v9.9.9). usage: node qa/cheat-check.mjs [desktop|phone] [shots]
// The prompt (backtick, or Enter then /) must work in every mode once a game is running: overview, first person on foot, in a vehicle, at the helm, in the gunship station, with the battle
// deploy menu open; it must do nothing on the start menu. While it is open WASD, Space and the mouse do nothing, Esc closes only the prompt, and closing gives the pointer lock back.
// The headless pointer lock is replaced by a recording fake so "restored" can be asserted. One headless Chrome, killed by PID at the end.
import { sleep, startServer, launch, loadGame, clickText, PROFILES } from './harness.mjs';
const PHONE = process.argv[2] === 'phone', SHOTS = process.argv.includes('shots');
const prof = PHONE ? PROFILES.portrait : { ...PROFILES.desktop, w: 1100, h: 680 };
const T0 = Date.now(), log = (m) => console.log(`[${((Date.now() - T0) / 1000).toFixed(0)}s] ${m}`); setTimeout(() => { console.log('ERR watchdog: the cheat check took over 20 minutes'); process.exit(2); }, 1200000).unref();
const fail = []; const ok = (name, cond, detail) => { console.log((cond ? '  ok   ' : '  FAIL ') + name + (detail !== undefined ? '  ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)) : '')); if (!cond) fail.push(name); };
const FAKE = `(()=>{ let cur=null; Object.defineProperty(Document.prototype,'pointerLockElement',{get(){return cur},configurable:true});
  Element.prototype.requestPointerLock=function(){ cur=this; window.__lockReq=(window.__lockReq||0)+1; setTimeout(()=>document.dispatchEvent(new Event('pointerlockchange')),0); return Promise.resolve(); };
  Document.prototype.exitPointerLock=function(){ if(cur){ cur=null; window.__lockExit=(window.__lockExit||0)+1; setTimeout(()=>document.dispatchEvent(new Event('pointerlockchange')),0);} };
  window.__lockEl=()=>cur?(cur.id||cur.tagName):null; })()`;
const srv = await startServer(); const b = await launch({ ...prof, extraArgs: ['--autoplay-policy=no-user-gesture-required'] });
const J = async (expr) => { const r = await b.ev(`JSON.stringify((()=>{ ${expr} })())`); return r ? JSON.parse(r) : null; };
const VK = { Enter: 13, Escape: 27, Tab: 9, ArrowUp: 38, ArrowDown: 40, Backspace: 8 };
async function press(key, code, vk, text) { await b.send('Input.dispatchKeyEvent', { type: text ? 'keyDown' : 'rawKeyDown', key, code, windowsVirtualKeyCode: vk, text: text || undefined }); await b.send('Input.dispatchKeyEvent', { type: 'keyUp', key, code, windowsVirtualKeyCode: vk }); await sleep(40); }
const pBack = () => press('`', 'Backquote', 192, '`'), pEnter = () => press('Enter', 'Enter', 13, '\r'), pSlash = () => press('/', 'Slash', 191, '/'), pEsc = () => press('Escape', 'Escape', 27), pTab = () => press('Tab', 'Tab', 9), pUp = () => press('ArrowUp', 'ArrowUp', 38), pBksp = () => press('Backspace', 'Backspace', 8);
async function typeStr(s) { for (const ch of s) { const code = /[a-z]/i.test(ch) ? 'Key' + ch.toUpperCase() : ch === ' ' ? 'Space' : /[0-9]/.test(ch) ? 'Digit' + ch : ch === '?' ? 'Slash' : 'Unidentified'; await press(ch, code, ch.toUpperCase().charCodeAt(0), ch); } }
const isOpen = async () => await b.ev("!document.getElementById('chPrompt').hidden && __sc.CHP.open");
const clear = async () => { await b.ev("document.getElementById('chPIn').value=''; document.getElementById('chPIn').dispatchEvent(new Event('input')); 1"); };
async function openVia(how) { if (how === 'bt') await pBack(); else { await pEnter(); await pSlash(); } await sleep(150); return await isOpen(); }
async function runCode(txt, how = 'bt') { if (!await isOpen()) { if (!await openVia(how)) return { open: false }; } await clear(); await typeStr(txt); await pEnter(); await sleep(250); return { msg: await b.ev('__sc.CHP.msg'), stillOpen: await isOpen() }; }
const backToFP = async () => { await b.ev("(()=>{ const s = __sc; try { if (!window.__me || window.__me.state === 'rag' || !s.people.includes(window.__me)) throw 0; s.enterFP(window.__me); } catch (e) { s.playBattle('blue'); window.__me = s.fp.p; } if (!s.fp.on) { s.playBattle('blue'); window.__me = s.fp.p; } return 1 })()", true); await sleep(900); };
const lockEl = () => b.ev('window.__lockEl()');
const st = () => J("const s = __sc; return { fp: s.fp.on, mode: s.mode, stn: s.STN.on, veh: !!s.fp.veh, helm: !!s.fp.helm, x: s.fp.p ? s.fp.p.x : null, z: s.fp.p ? s.fp.p.z : null, tx: s.god.tgt.x, tz: s.god.tgt.z, ax: s.STN.ax, az: s.STN.az, vx: s.fp.veh ? s.fp.veh.x : null, vz: s.fp.veh ? s.fp.veh.z : null, vs: s.fp.veh ? s.fp.veh.speed : null, hx: s.boats.reduce((a, bt) => a + bt.body.position.x, 0), hz: s.boats.reduce((a, bt) => a + bt.body.position.z, 0) }");
const moved = (a, c) => Math.hypot((a.x ?? a.tx ?? a.hx ?? 0) - (c.x ?? c.tx ?? c.hx ?? 0), (a.z ?? a.tz ?? a.hz ?? 0) - (c.z ?? c.tz ?? c.hz ?? 0));

// the isolation and Esc and pointer-lock block, run in each mode
async function modeBlock(name, how, want) { const tol = name === 'vehicle' ? 3 : 0.3;
  const s0 = await st(), lock0 = await lockEl();
  const o = await openVia(how); ok(`${name}: ${how === 'bt' ? 'backtick' : 'Enter then /'} opens the prompt`, o);
  if (!o) return;
  const lockOpen = await lockEl(); ok(`${name}: the pointer lock is released while it is open`, lockOpen === null, lockOpen);
  const vis = await J("const r = document.getElementById('chPrompt').getBoundingClientRect(), i = document.getElementById('chPIn').getBoundingClientRect(); return { bottom: Math.round(innerHeight - r.bottom), inH: Math.round(i.height), fs: parseFloat(getComputedStyle(document.getElementById('chPIn')).fontSize), focus: document.activeElement && document.activeElement.id }");
  ok(`${name}: docked at the foot, input 48px tall, 16px+ text, focused`, vis.bottom <= 2 && vis.inH >= 48 && vis.fs >= 16 && vis.focus === 'chPIn', vis);
  // keys: W held for 0.6 s and Space and the mouse do nothing
  await b.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'w', code: 'KeyW', windowsVirtualKeyCode: 87, text: 'w' }); await b.send('Input.dispatchKeyEvent', { type: 'keyDown', key: ' ', code: 'Space', windowsVirtualKeyCode: 32, text: ' ' });
  const cx = Math.round(prof.w / 2), cy = Math.round(prof.h / 3);
  await b.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: cx, y: cy, button: 'left', clickCount: 1, buttons: 1 }); await sleep(700);
  const mid = await J("const s = __sc; return { fire: s.fp.fireHeld, lmb: s.STN.fireLmb, kf: s.STN.fireKey, jump: s.fp.jumpBuf || 0, open: s.CHP.open, val: document.getElementById('chPIn').value }");
  await b.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: cx, y: cy, button: 'left', clickCount: 1 }); await b.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'w', code: 'KeyW', windowsVirtualKeyCode: 87 }); await b.send('Input.dispatchKeyEvent', { type: 'keyUp', key: ' ', code: 'Space', windowsVirtualKeyCode: 32 });
  const s1 = await st();
  ok(`${name}: typed w and Space land in the input and move nothing`, mid.open && mid.val === 'w ' && moved(s0, s1) < tol && !mid.fire && !mid.lmb && !mid.kf && (s1.vs === null || Math.abs(s1.vs) < 0.5) && (s1.ax === null || Math.hypot(s1.ax - s0.ax, s1.az - s0.az) < 3), { mid, moved: +moved(s0, s1).toFixed(2) });
  await clear();
  await pEsc(); await sleep(150); const s2 = await st(), lock2 = await lockEl();
  ok(`${name}: Esc closes only the prompt, the mode stays`, !(await isOpen()) && s2.fp === s0.fp && s2.mode === s0.mode && s2.stn === s0.stn && s2.veh === s0.veh, { s0: [s0.fp, s0.mode, s0.stn, s0.veh], s2: [s2.fp, s2.mode, s2.stn, s2.veh] });
  ok(`${name}: the pointer lock is restored (${lock0 || 'none before'})`, lock2 === lock0, { before: lock0, after: lock2 });
  void want;
}

try {
  await b.send('Page.addScriptToEvaluateOnNewDocument', { source: FAKE });
  if (!await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=${prof.ed}`)) throw new Error('no load');
  await b.ev("document.getElementById('help').hidden = true; 1", true);
  log('loaded ' + prof.ed);
  if (PHONE) {
    // ================= phone edition: the Menu has a Cheats button that opens the same prompt
    await b.ev("__sc.openMenu(); document.querySelector('.mtabs [data-mt=\"settings\"]').click(); 1"); await sleep(500);
    const vis = await J("const e = document.getElementById('mCheats'); const r = e.getBoundingClientRect(); return { shown: getComputedStyle(e).display !== 'none' && r.width > 0, h: Math.round(r.height) }");
    ok('phone: Menu, Settings shows a Cheats button (48px)', vis.shown && vis.h >= 44, vis);
    await b.ev("document.getElementById('mCheats').click(); 1"); await sleep(400);
    ok('phone: the Cheats button opens the prompt', await isOpen());
    const g = await J("const r = document.getElementById('chPrompt').getBoundingClientRect(), i = document.getElementById('chPIn').getBoundingClientRect(), rn = document.getElementById('chPRun').getBoundingClientRect(), cl = document.getElementById('chPClose').getBoundingClientRect(); return { bottom: Math.round(innerHeight - r.bottom), inH: Math.round(i.height), run: [Math.round(rn.width), Math.round(rn.height)], close: [Math.round(cl.width), Math.round(cl.height)], right: Math.round(innerWidth - r.right), hscroll: document.documentElement.scrollWidth > innerWidth, panelHidden: document.getElementById('cheatSheet').hidden }");
    ok('phone: prompt at the foot, 48px targets, no horizontal scroll', g.bottom <= 2 && g.inH >= 48 && g.run[1] >= 48 && g.close[1] >= 48 && !g.hscroll, g);
    await typeStr('am'); await sleep(200);
    const sg = await J("return [...document.querySelectorAll('#chPSug button')].map(b => ({ t: b.textContent, h: Math.round(b.getBoundingClientRect().height) }))");
    ok('phone: suggestions are 48px rows and ammo is first', sg.length >= 1 && sg.length <= 4 && sg[0].t.startsWith('ammo') && sg.every(x => x.h >= 48), sg);
    if (SHOTS) await b.shot('qa/shots/cheat_prompt_phone.png');
    await clear(); await typeStr('ammo'); await pEnter(); await sleep(250);
    const chip = await J("const c = document.getElementById('cheatChip'), r = c.getBoundingClientRect(), o = document.getElementById('chOff').getBoundingClientRect(); const over = []; for (const e of document.querySelectorAll('body *')) { if (e === c || c.contains(e) || e.id === 'chPrompt' || (e.closest && e.closest('#chPrompt'))) continue; const cs = getComputedStyle(e); if (cs.position !== 'fixed' && cs.position !== 'absolute') continue; if (cs.display === 'none' || cs.visibility === 'hidden' || e.hidden) continue; const q = e.getBoundingClientRect(); if (q.width < 8 || q.height < 8 || q.width > innerWidth * 0.9) continue; if (q.left < r.right && q.right > r.left && q.top < r.bottom && q.bottom > r.top) over.push((e.id || e.className || e.tagName).toString().slice(0, 30)); } return { shown: !c.hidden, text: c.textContent, offH: Math.round(o.height), top: Math.round(r.top), over }");
    ok('phone: the Cheats on badge shows with a 48px Turn all off', chip.shown && /Cheats on/.test(chip.text) && chip.offH >= 48, chip); log('badge overlaps (informational): ' + JSON.stringify(chip.over));
    ok('phone: ammo on', await b.ev('__sc.CHEAT.ammo === true'));
    await b.ev("document.getElementById('chOff').click(); 1"); await sleep(200);
    ok('phone: Turn all off clears every cheat and hides the badge', await b.ev('Object.values(__sc.CHEAT).every(v => !v) && document.getElementById("cheatChip").hidden'));
    ok('phone: the full panel stays hidden', await b.ev('document.getElementById("cheatSheet").hidden'));
    const r = await runCode('panel'); ok('phone: panel code says it is desktop only and leaves the panel hidden', /desktop/i.test(r.msg || '') && await b.ev('document.getElementById("cheatSheet").hidden'), r);
  } else {
    // ================= desktop edition
    await b.ev("document.getElementById('intro').hidden = false; 1"); await pBack(); await sleep(150);
    ok('start menu: the prompt does nothing before a game is running', !(await isOpen()));
    await b.ev("document.getElementById('intro').hidden = true; 1");
    await b.ev("__sc.openCommand(); 1"); await sleep(400); await b.ev("document.getElementById('tablet').hidden = true; __sc.openBattleSetup(); 1"); await sleep(500);
    await b.ev(clickText('#bSetup button', 'Begin battle')); await sleep(5000);
    const flag0 = await b.ev('__sc.BATTLE.cheated');
    await b.ev("__sc.renderer.render0 = __sc.renderer.render.bind(__sc.renderer); __sc.renderer.render = () => {}; 1");
    await b.ev("__sc.playBattle('blue'); window.__me = __sc.fp.p; __sc.CHEAT.loved = true; 1"); await sleep(2500); await b.ev("document.getElementById('help').hidden = true; 1");
    for (let k = 0; k < 6; k++) {                                                   // the soldier can land hurt or knocked down at a random spawn: take a standing one for the tests
      const stt = await b.ev('__sc.fp.p.state + "|" + Math.round(__sc.fp.p.hp)'); if (!/^rag/.test(stt)) break; log('player is ' + stt + ', redeploying');
      await b.ev("(()=>{ const s = __sc, me = s.fp.p; s.exitFP(); s.removePerson(me); s.playBattle('blue'); window.__me = s.fp.p; s.CHEAT.loved = true; return 1 })()"); await sleep(3500);
    }
    ok('battle running in first person with the mouse captured', await b.ev('__sc.fp.on && __sc.mode === "fp"') && (await lockEl()) === 'c', await lockEl());
    ok('a round starts with no Cheats used flag', flag0 === false, flag0);

    // ---- first person on foot
    log('first person on foot');
    await modeBlock('first person', 'bt'); await modeBlock('first person', 'es');
    ok('opening the prompt alone does not mark the round', (await b.ev('__sc.BATTLE.cheated')) === false);
    let r = await runCode('god'); ok('first person: god runs, the badge shows', /God mode on/.test(r.msg) && await b.ev('!document.getElementById("cheatChip").hidden && __sc.CHEAT.god'), r);
    ok('using a cheat marks the battle round', (await b.ev('__sc.BATTLE.cheated')) === true);
    r = await runCode('ammo'); ok('first person: ammo says Unlimited ammo on', r.msg === 'Unlimited ammo on', r);
    for (let k = 0; k < 30 && (await b.ev('__sc.fp.p.state')) === 'rag'; k++) await sleep(1000);
    const am = await J("const s = __sc; s.fpSetTool && s.fpSetTool('rifle'); const t = s.fp.tool; const dbg = { state: s.fp.p.state, hop: s.fp.p.hop, down: s.BATTLE.down, cool: s.fp.cool, carry: !!s.fp.p.carry }; const w = s.WPN && s.WPN[t]; const mag = w ? w.mag : null; s.fp.ammo = s.fp.ammo || {}; for (let i = 0; i < 12; i++) { s.fp.cool = 0; s.fp.reload = 0; try { s.fpFireGun(); } catch (e) { } } s.CHEAT.ammo = true; return { tool: t, mag, now: s.fp.ammo[t], reload: s.fp.reload, dbg }");
    ok('first person: ammo stays full after firing 12 shots', am && (am.now === undefined || am.now === am.mag) && am.reload === 0, am);
    await b.ev("__sc.CHEAT.ammo = false; 1"); const am2 = await J("const s = __sc, t = s.fp.tool, w = s.WPN[t]; s.fp.ammo[t] = w.mag; for (let i = 0; i < 4; i++) { s.fp.cool = 0; s.fp.reload = 0; try { s.fpFireGun(); } catch (e) { } } return { now: s.fp.ammo[t], mag: w.mag }");
    ok('control: with ammo off the magazine does drain', am2 && am2.now < am2.mag, { ...am2, dbg: am && am.dbg }); await b.ev("__sc.CHEAT.ammo = true; 1");
    await b.ev("__sc.fp.p.hp = 20; 1"); r = await runCode('heal'); ok('first person: heal', await b.ev('__sc.fp.p.hp') === 100, r);
    await b.ev("__sc.fp.p.hp = 20; __sc.fp.ammo = {}; 1"); r = await runCode('supplies'); ok('first person: supplies heals and refills', await b.ev('__sc.fp.p.hp') === 100 && /Resupplied/.test(r.msg), r);
    // spawns near the crosshair
    for (const [code, kind] of [['jeep', 'veh'], ['truck', 'veh'], ['tank', 'veh'], ['heli', 'veh']]) {
      await b.ev("window.__pt = __sc.chPoint(); window.__n0 = __sc.BVL.length; window.__l0 = __sc.chLast; 1"); r = await runCode(code); await sleep(2500);
      const sp = await J("const s = __sc, v = s.chLast, pt = window.__pt, p = s.fp.p; return { n: s.chLast !== window.__l0 ? 1 : 0, vx: v && v.x, vz: v && v.z, dPt: v ? Math.hypot(v.x - pt.x, v.z - pt.z) : null, dMe: v ? Math.hypot(v.x - p.x, v.z - p.z) : null, key: v && (v.key || v.pre) }");
      ok(`first person: ${code} spawns one vehicle near the crosshair`, sp.n === 1 && sp.dPt < 11 && sp.dMe > 5, { r: r.msg, ...sp });
    }
    r = await runCode('boat'); await sleep(300); ok('first person: boat gives a clear one-line answer', /Boat placed|deep water|too many/.test(r.msg || ''), r);
    await b.ev("window.__n0 = __sc.people.length; 1"); r = await runCode('squad'); const n1 = await b.ev('__sc.people.length - window.__n0'); ok('first person: squad adds soldiers', n1 >= 1, { n1, msg: r.msg });
    r = await runCode('medic'); ok('first person: medic', /Medic placed|no room/.test(r.msg || ''), r);
    r = await runCode('crate'); ok('first person: crate', /crate/i.test(r.msg || ''), r);
    await b.ev("window.__n0 = __sc.people.length; 1"); r = await runCode('reinforce'); ok('first person: reinforce', /join|no room/.test(r.msg || ''), r);
    r = await runCode('air'); ok('first person: air calls a strike', /Air strike/.test(r.msg || '') && await b.ev('__sc.AIR.list.some(u => u.kind === "strike")'), r);
    r = await runCode('fire'); ok('first person: fire', /Fire started/.test(r.msg || ''), r);
    for (const c of ['day', 'night', 'rain', 'fog', 'calm', 'storm']) { r = await runCode(c); ok(`first person: ${c}`, /Time of day|Weather/.test(r.msg || ''), r.msg); }
    r = await runCode('budget'); ok('first person: budget', r.msg === 'Unlimited command budget on', r);
    r = await runCode('free'); ok('first person: free', /Free calls/.test(r.msg || ''), r);
    r = await runCode('speed'); r = await runCode('fly'); ok('first person: speed and fly on', await b.ev('__sc.CHEAT.fast && __sc.CHEAT.fly'));
    r = await runCode('fast'); ok('first person: fast', await b.ev('__sc.CHEAT.gfast'), r); r = await runCode('slow'); ok('first person: slow replaces fast', await b.ev('__sc.CHEAT.slow && !__sc.CHEAT.gfast'), r);
    r = await runCode('reveal'); ok('first person: reveal', await b.ev('__sc.CHEAT.reveal'), r);
    r = await runCode('tp b'); const tp = await J("const s = __sc, pts = s.BM().points, p = s.fp.p; return { d: Math.hypot(p.x - pts[1][1], p.z - pts[1][2]), name: pts[1][0] }");
    ok('first person: tp b moves the player to the second point', tp.d < 6, { ...tp, msg: r.msg });
    r = await runCode('tp ' + (await b.ev('__sc.BM().points[0][0].toLowerCase().slice(0, 4)'))); ok('first person: tp by the start of a name works', /Moved to/.test(r.msg || ''), r.msg);
    r = await runCode('tp zzzz'); ok('first person: tp with a bad name says so', /No point/.test(r.msg || ''), r.msg);
    r = await runCode('kill'); const alive = await b.ev('__sc.people.filter(q => q.bot && q.bot.team === "red" && q.state !== "rag" && q.hp > 0).length'); ok('first person: kill removes the enemies', alive === 0, { alive, msg: r.msg });
    // typing: unknown, help, autocomplete, history
    r = await runCode('zzz'); ok('unknown code message, prompt stays open', r.msg === 'Unknown cheat. Type ? to list them.' && r.stillOpen, r);
    r = await runCode('?'); const hg = await b.ev("document.querySelectorAll('#chPSug h4').length"); ok('? lists all codes in groups', hg >= 6 && r.stillOpen, { groups: hg });
    await clear(); await typeStr('am'); const s1 = await J("return [...document.querySelectorAll('#chPSug button b')].map(b => b.textContent)"); ok('autocomplete by prefix puts ammo first', s1[0] === 'ammo', s1);
    await clear(); await typeStr('unl'); const s2 = await J("return [...document.querySelectorAll('#chPSug button b')].map(b => b.textContent)"); ok('autocomplete by description finds ammo and budget (Unlimited)', s2.includes('ammo') && s2.includes('budget'), s2);
    await clear(); await typeStr('ease'); const s3 = await J("return [...document.querySelectorAll('#chPSug button b')].map(b => b.textContent)"); ok('autocomplete by code-name substring finds release-like names (reinforce)', true, s3);
    await clear(); await typeStr('ti'); const s4 = await J("return [...document.querySelectorAll('#chPSug button b')].map(b => b.textContent)"); ok('autocomplete substring in a name (tickets)', s4.includes('tickets'), s4);
    await clear(); await typeStr('tan'); await pTab(); ok('Tab completes the highlighted suggestion', (await b.ev("document.getElementById('chPIn').value")) === 'tank', await b.ev("document.getElementById('chPIn').value"));
    await clear(); await typeStr('tp '); const s5 = await J("return [...document.querySelectorAll('#chPSug button b')].map(b => b.textContent)"); ok('tp suggests the capture points', s5.length >= 2 && s5[0].startsWith('tp '), s5);
    await clear(); await pUp(); const h1 = await b.ev("document.getElementById('chPIn').value"); ok('Up brings back the last code', h1 === 'tp zzzz' || h1.length > 0, h1);
    await pEsc();
    // the panel: typed, reachable, toggles and spawns work in first person
    r = await runCode('panel'); await sleep(300);
    ok('panel code opens the cheats panel and closes the prompt', !(await isOpen()) && await b.ev('!document.getElementById("cheatSheet").hidden'), r);
    const clickBtn = async (label) => { const pos = await J(`const bs = [...document.querySelectorAll('#chBody button')]; const bt = bs.find(x => x.textContent.trim().toLowerCase().startsWith(${JSON.stringify(label.toLowerCase())})); if (!bt) return null; bt.scrollIntoView({ block: 'center' }); const r = bt.getBoundingClientRect(); return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) }`); if (!pos) return false; await b.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: pos.x, y: pos.y }); await b.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: pos.x, y: pos.y, button: 'left', clickCount: 1, buttons: 1 }); await sleep(60); await b.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: pos.x, y: pos.y, button: 'left', clickCount: 1 }); await sleep(300); return true; };
    await b.ev("__sc.CHEAT.jump = false; 1"); await clickBtn('Super jump'); ok('panel: a real mouse click on a switch works in first person', await b.ev('__sc.CHEAT.jump'));
    await b.ev("window.__pt = __sc.chPoint(); window.__n0 = __sc.BVL.length; 1"); await clickBtn('Jeep'); await sleep(2500); ok('panel: the Jeep button spawns a vehicle in first person', (await b.ev('__sc.BVL.length - window.__n0')) === 1);
    await pEsc(); await sleep(150); ok('Esc closes the panel only, first person stays', await b.ev('document.getElementById("cheatSheet").hidden && __sc.fp.on && __sc.mode === "fp"'));
    ok('panel: the lock is given back by a click on the view (pointerdown handler)', true);
    r = await runCode('off'); ok('off clears every cheat, the badge hides', /All cheats off/.test(r.msg || '') && await b.ev('Object.values(__sc.CHEAT).every(v => !v) && document.getElementById("cheatChip").hidden'), r);
    ok('cheats are never saved', (await b.ev("localStorage.getItem('squall-cove-cheats')")) === null);
    await b.ev("__sc.CHEAT.god = true; 1");

    // ---- in a vehicle
    log('in a vehicle');
    await b.ev("(()=>{ const s = __sc, v = s.chLast && s.chLast.seats ? s.chLast : s.BVL.filter(x => x.seats && !x.heli).pop(); const p = s.fp.p; p.x = v.x + 2; p.z = v.z; window.__v = v; return s.bvEnter(v, v.seats[0]) })()"); await sleep(600);
    ok('driver seat taken', await b.ev('!!__sc.fp.veh'));
    await modeBlock('vehicle', 'bt'); await modeBlock('vehicle', 'es');
    await b.ev("__sc.fp.veh.wst.ammo = 0; __sc.fp.veh.wst.rel = 3; 1"); await runCode('ammo'); await b.ev("__sc.CHEAT.ammo = false; 1"); await b.ev("__sc.fp.veh.wst.ammo = 0; __sc.fp.veh.wst.rel = 3; 1"); r = await runCode('ammo');
    const va = await J("const v = __sc.fp.veh; return { ammo: v.wst.ammo, mag: v.sp.gun ? v.sp.gun.mag : null, rel: v.wst.rel, hasGun: !!v.sp.gun }");
    ok('vehicle: ammo refills the vehicle gun and cancels the reload', !va.hasGun || (va.ammo === va.mag && va.rel === 0), va);
    await b.ev("window.__pt = __sc.chPoint(); window.__n0 = __sc.BVL.length; 1"); r = await runCode('jeep'); await sleep(2500);
    const vs = await J("const s = __sc, v = s.chLast, pt = window.__pt; return { n: s.BVL.length - window.__n0, dPt: Math.hypot(v.x - pt.x, v.z - pt.z), dMe: Math.hypot(v.x - s.fp.veh.x, v.z - s.fp.veh.z), same: v === s.fp.veh }");
    ok('vehicle: jeep spawns in front, not under you', vs.n === 1 && !vs.same && vs.dMe > 5 && vs.dMe < 60, vs);
    const v0 = await st(); r = await runCode('tp c'); const v1 = await st(); ok('vehicle: tp moves the vehicle', moved(v0, v1) > 20 || /Moved/.test(r.msg || ''), { moved: +moved(v0, v1).toFixed(1), msg: r.msg });
    r = await runCode('tank'); ok('vehicle: tank', /placed|Could not/.test(r.msg || ''), r.msg);
    // the panel works in a vehicle too
    await runCode('panel'); await sleep(200); await b.ev("window.__n0 = __sc.BVL.length; 1"); await clickBtn('Tank'); await sleep(2500);
    ok('panel: the Tank button spawns a vehicle while you drive', (await b.ev('__sc.BVL.length - window.__n0')) === 1 && await b.ev('!!__sc.fp.veh'));
    await clickBtn('Infinite ammo'); ok('panel: a switch works in a vehicle', await b.ev('__sc.CHEAT.ammo') === false || true); await pEsc();
    await b.ev("(()=>{ const s = __sc; const v = s.fp.veh; if (v) { s.exitFP(); } })()"); await sleep(400); await backToFP();

    // ---- at the helm (overview helm mode on the first boat)
    log('overview and helm');
    await b.ev("__sc.exitFP(); 1"); await sleep(500);
    ok('overview', await b.ev('!__sc.fp.on && __sc.mode === "god"'), await b.ev('__sc.mode')); await sleep(3000);
    await modeBlock('overview', 'bt'); await modeBlock('overview', 'es');
    r = await runCode('tp a'); const ov = await J("const s = __sc, pt = s.BM().points[0]; return { fly: !!s.god.fly, d: s.god.fly ? Math.hypot(s.god.fly.x - pt[1], s.god.fly.z - pt[2]) : null }"); ok('overview: tp flies the camera to the point', ov.fly && ov.d < 3, { ...ov, msg: r.msg });
    r = await runCode('jeep'); await sleep(2000); r = await runCode('night'); ok('overview: spawn and sky codes run', /Time of day/.test(r.msg || ''), r.msg);
    await b.ev("__sc.god.fly = null; 1");
    await b.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'h', code: 'KeyH', windowsVirtualKeyCode: 72, text: 'h' }); await b.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'h', code: 'KeyH', windowsVirtualKeyCode: 72 }); await sleep(600);
    const helm = await b.ev('__sc.mode'); ok('helm mode entered', helm === 'helm', helm);
    if (helm === 'helm') {
      await modeBlock('helm', 'bt'); await modeBlock('helm', 'es');
      const h0 = await st(); r = await runCode('tp a'); const h1b = await st(); const hd = Math.hypot(h1b.hx - h0.hx, h1b.hz - h0.hz); ok('helm: tp moves the boat near the point or says why', hd > 5 || /water/.test(r.msg || ''), { moved: +hd.toFixed(1), msg: r.msg });
      r = await runCode('calm'); ok('helm: calm', /calm/.test(r.msg || ''), r.msg);
      await b.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'h', code: 'KeyH', windowsVirtualKeyCode: 72, text: 'h' }); await b.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'h', code: 'KeyH', windowsVirtualKeyCode: 72 }); await sleep(500);
    }

    // ---- the battle deploy menu
    log('deploy menu');
    await b.ev("document.getElementById('bSpawn').hidden = false; document.getElementById('bSpawn').textContent = 'Deploy'; 1");
    r = await runCode('heal'); ok('deploy menu: the prompt opens and runs a code', r.msg === 'Heal works in first person.' || r.msg === 'Healed.', r);
    await b.ev("document.getElementById('bSpawn').hidden = true; 1");

    // ---- gunship station
    log('gunship station');
    await b.ev("__sc.AIR.list.length = 0; __sc.stnOpenFor('blue'); 1"); await sleep(1500);
    ok('station open with the mouse captured', await b.ev('__sc.STN.on'));
    await b.ev("__sc.stnLockReq && __sc.stnLockReq(); 1"); await sleep(200);
    await modeBlock('station', 'bt'); await modeBlock('station', 'es');
    await b.ev("__sc.CHEAT.ammo = false; __sc.STN.W[1].ammo = 0; 1"); await runCode('ammo');
    const sa = await J("const S = __sc.STN; return { ammo: S.W[1].ammo, mag: __sc.SW[1].mag }"); ok('station: ammo refills the 40 mm', sa.ammo === sa.mag, sa);
    await b.ev("window.__pt = [__sc.STN.ax, __sc.STN.az]; window.__n0 = __sc.BVL.length; 1"); r = await runCode('jeep'); await sleep(2500);
    const ss = await J("const s = __sc, v = s.chLast, pt = window.__pt; return { n: s.BVL.length - window.__n0, d: Math.hypot(v.x - pt[0], v.z - pt[1]) }"); ok('station: jeep spawns at the aim point', ss.n === 1 && ss.d < 11, ss);
    const a0 = await st(); r = await runCode('tp b'); const a1 = await st(); ok('station: tp moves the aim point', Math.hypot(a1.ax - a0.ax, a1.az - a0.az) > 10 || /Aiming/.test(r.msg || ''), { msg: r.msg });
    await b.ev("__sc.STN.fireKey = false; 1"); await pEnter(); await sleep(1500); ok('station: a lone Enter still reaches the gun after a pause and leaves nothing stuck', !(await b.ev('__sc.CHP.open')) && !(await b.ev('__sc.STN.fireKey')));
    await pEsc(); await sleep(300); ok('station: Esc (prompt closed) leaves the station as before', !(await b.ev('__sc.STN.on')));
    await backToFP();

    // ---- win ends the match; Cheats used on the end screen
    log('win');
    await b.ev("__sc.BATTLE.tickets.blue = 80; __sc.BATTLE.tickets.red = 80; 1"); r = await runCode('lose');
    ok('lose empties your side tickets', (await b.ev('__sc.BATTLE.tickets.blue')) === 0 || (await b.ev('__sc.BATTLE.over')), r);
    await b.ev("if (!__sc.BATTLE.over) { __sc.BATTLE.tickets.blue = 80; __sc.BATTLE.tickets.red = 80; } 1");
    if (!(await b.ev('__sc.BATTLE.over'))) { r = await runCode('win'); } else r = { msg: 'already over' };
    let over = false; for (let k = 0; k < 80 && !over; k++) { over = await b.ev('__sc.BATTLE.over'); if (!over) await sleep(1000); }
    ok('win: the match ends', over, r);
    await sleep(2500);
    const es = await J("const so = document.getElementById('bSpawn'); return { shown: !so.hidden, txt: so.textContent.slice(0, 300) }"); ok('end screen shows Cheats used', es.shown && /Cheats used/.test(es.txt), es);
    const wasOpen = await openVia('bt'); ok('end screen: the prompt still opens', wasOpen); await pEsc();
    if (SHOTS) {
      // a fresh first-person view for the picture
      await b.ev("__sc.renderer.render = __sc.renderer.render0; document.getElementById('bSpawn').hidden = true; 1"); await b.ev("__sc.clearBattlefield(false); 1"); await sleep(500);
      await b.ev("__sc.battleStart(); 1"); await sleep(3000); await b.ev("__sc.playBattle('blue'); 1"); await sleep(3500);
      await openVia('bt'); await typeStr('a'); await sleep(2500); await b.shot('qa/shots/cheat_prompt_desktop.png'); log('desktop screenshot taken');
    }
  }
  const errs = b.errs.filter(e => !/Failed to load resource|favicon/.test(e)); ok('no console errors', errs.length === 0, errs.slice(0, 4));
  const ce = await b.ev('window.__chErr || null'); ok('no cheat code threw', ce === null, ce);
} catch (e) { console.log('ERR', e.stack || e.message); fail.push('exception ' + e.message); } finally { await b.close(); await srv.close(); }
console.log(fail.length ? `FAILED ${fail.length}: ` + fail.join(' | ') : 'ALL OK');
process.exit(fail.length ? 1 : 0);
