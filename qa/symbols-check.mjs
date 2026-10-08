// Situational awareness check (v9.8): overview symbols, compass strip, corner map, Quick map on M, mount on J.
// usage: node qa/symbols-check.mjs [desktop|portrait|landscape] [--reload]
// One headless Chrome (qa/harness.mjs). The software renderer is slow, so the test waits for frames instead of timing anything.
import { sleep, startServer, launch, loadGame, clickText, PROFILES } from './harness.mjs';
const arg = process.argv[2] && !process.argv[2].startsWith('--') ? process.argv[2] : 'desktop', RELOAD = process.argv.includes('--reload');
const P0 = PROFILES[arg], P = arg === 'desktop' ? { ...P0, w: 1100, h: 700 } : P0;
const T0 = Date.now(), log = (m) => console.log(`[${((Date.now() - T0) / 1000).toFixed(0)}s] ${m}`); setTimeout(() => { console.log('ERR watchdog: test took over 20 minutes'); process.exit(2); }, 1200000).unref();
const srv = await startServer(); const b = await launch({ ...P, extraArgs: ['--autoplay-policy=no-user-gesture-required'] }); const fail = [], info = {};
const ok = (c, m) => { if (!c) fail.push(m); log((c ? 'ok   ' : 'FAIL ') + m); };
const J = async (e) => { const r = await b.ev(`JSON.stringify(${e})`); return r === null || r === undefined ? null : JSON.parse(r); };
try {
  if (!await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=${P.ed}`)) throw new Error('no load');
  await b.ev("localStorage.removeItem('squall-cove-symbols');localStorage.removeItem('squall-cove-minimap');1", true);
  await b.ev("document.getElementById('tablet').hidden=true; __sc.openBattleSetup(); 1"); await sleep(500);
  await b.ev(clickText('#bSetup button', 'Begin battle')); await sleep(5000); await b.ev("__sc.CHEAT.god=true;__sc.playBattle('blue');1"); await sleep(3500);
  log('in battle: ' + await J("{fp:__sc.fp.on, ed:window.__ED&&window.__ED.phone, sa:!!__sc.SA, people:__sc.people.length}"));
  ok(await b.ev('!!__sc.SA'), 'SA module present');
  // ---- first person: compass heading matches the real facing
  await b.ev("__sc.fp.yaw = 1.1; __sc.fp.pitch = 0; 1"); await sleep(3500);
  const comp = await J(`(() => { const S = __sc.SA.S; __sc.SA.drawCompass(); const d = new __sc.THREE.Vector3(); __sc.camera.getWorldDirection(d); const camB = (Math.atan2(d.x, -d.z) * 180 / Math.PI + 360) % 360; return { heading: S.cmp.heading, camB, marks: S.cmp.marks.map(m => m.k), w: S.cmp.w, yaw: __sc.fp.yaw }; })()`);
  info.compass = comp; const dB = Math.abs(((comp.heading - comp.camB + 540) % 360) - 180);
  ok(dB < 1.0, `compass heading ${comp.heading.toFixed(1)} matches camera facing ${comp.camB.toFixed(1)} (diff ${dB.toFixed(2)} deg, fp.yaw ${comp.yaw})`);
  const exp = ((Math.atan2(Math.sin(1.1), -Math.cos(1.1)) * 180 / Math.PI) + 360) % 360; ok(Math.abs(comp.heading - exp) < 0.5, `compass heading follows fp.yaw (${comp.heading.toFixed(1)} vs ${exp.toFixed(1)})`);
  ok(comp.marks.includes('obj'), 'compass shows at least one point letter: ' + comp.marks.join(','));
  // a point straight ahead reads as the centre of the strip
  const ahead = await J(`(() => { const S = __sc.SA.S, p = __sc.BATTLE.points[0], o = __sc.SA.origin(); __sc.fp.yaw = Math.atan2(p.x - o[0], p.z - o[1]); __sc.SA.drawCompass(); const m = S.cmp.marks.find(x => x.k === 'obj'); return { hd: S.cmp.heading, brg: __sc.SA.brg(p.x - o[0], p.z - o[1]), mark: m && m.brg }; })()`);
  ok(Math.abs(ahead.hd - ahead.brg) < 0.5, `facing point A: heading ${ahead.hd.toFixed(1)} = bearing to it ${ahead.brg.toFixed(1)}`);
  // ---- hint text and the controls list
  const hint = await b.ev("document.getElementById('fpHint').textContent"); info.hint = hint;
  const keys = await J("__sc.KEYMAP.filter(r => r[0] === 'fp' && /^(M|J|Shift \\+ M)$/.test(r[1])).map(r => [r[1], r[2].slice(0, 60)])");
  ok(keys.length === 3, 'controls list has J (mount), M (quick map) and Shift + M rows: ' + JSON.stringify(keys.map(k => k[0])));
  ok(!(await J("__sc.KEYMAP.some(r => r[0] === 'fp' && r[1] === 'M' && /mount/i.test(r[2]))")), 'M no longer means mount in the controls list');
  const src = await (await fetch(`http://127.0.0.1:${srv.port}/index.html`)).text();
  ok(/M opens the map and L the full map\. The compass runs along the top, and Shift \+ M hides the corner map/.test(src) && /The Map button opens the map/.test(src), 'the first person hints (desktop and phone) mention map, full map, compass and the minimap toggle');
  ok(!/M[^.]*mount/i.test(src.replace(/\/\*[\s\S]*?\*\//g, '')), 'no text still says M mounts');
  // ---- corner map is drawn and visible
  await b.ev("__sc.SA.build(); 1"); await sleep(1500);
  const mini = await J("(() => { const m = document.getElementById('miniMap'), r = m.getBoundingClientRect(); return { hidden: m.hidden, w: Math.round(r.width), h: Math.round(r.height), pref: localStorage.getItem('squall-cove-minimap') }; })()");
  info.mini = mini; ok(!mini.hidden && mini.w > 60, `corner map shown (${mini.w}x${mini.h})`);
  // ---- the corner map's terrain lines up with the chips and the heading: a stand-in picture with a dot 50 m ahead and a dot 40 m to the right must land straight above and straight right of the arrow
  const al = await J(`(() => { const A = __sc.SA, T = A.TMAP, EXT = 128 * __sc.CELL, N = 512, cv = document.createElement('canvas'); cv.width = cv.height = N; const c = cv.getContext('2d'); c.fillStyle = '#336644'; c.fillRect(0, 0, N, N);
    const o = A.origin(), yaw = __sc.fp.yaw, fx = Math.sin(yaw), fz = Math.cos(yaw), rx = -Math.cos(yaw), rz = Math.sin(yaw), dot = (x, z, col) => { c.fillStyle = col; c.beginPath(); c.arc((x + EXT) / (2 * EXT) * N, (z + EXT) / (2 * EXT) * N, 5, 0, 6.283); c.fill(); };
    dot(o[0] + fx * 50, o[1] + fz * 50, '#ff00ff'); dot(o[0] + rx * 40, o[1] + rz * 40, '#00ffff');
    const keep = [T.base, T.key, T.building, __sc.BATTLE.on]; T.base = cv; T.key = A.tmKey(); T.building = true; __sc.BATTLE.on = false;
    const q = document.createElement('canvas'); q.style.cssText = 'position:fixed;left:0;top:0;width:200px;height:200px'; document.body.appendChild(q); A.drawMap(q, 100, false); const x = q.getContext('2d'), sc = 100 / 100, px = (X, Y) => Array.from(x.getImageData(Math.round(X * q.width / 200), Math.round(Y * q.height / 200), 1, 1).data);
    const up = px(100, 100 - 50 * sc), rt = px(100 + 40 * sc, 100), bad = px(100 - 50 * sc, 100); q.remove(); T.base = keep[0]; T.key = keep[1]; T.building = keep[2]; __sc.BATTLE.on = keep[3]; return { up, rt, bad }; })()`);
  const closeTo = (p, r, g, bl) => p && Math.abs(p[0] - r) < 90 && Math.abs(p[1] - g) < 90 && Math.abs(p[2] - bl) < 90;
  ok(closeTo(al.up, 255, 0, 255), 'corner map: a dot 50 m ahead is drawn straight above the arrow ' + JSON.stringify(al.up)); ok(closeTo(al.rt, 0, 255, 255), 'corner map: a dot 40 m to the right is drawn straight right of the arrow ' + JSON.stringify(al.rt)); ok(!closeTo(al.bad, 255, 0, 255) && !closeTo(al.bad, 0, 255, 255), 'and nothing on the left');
  // ---- Quick map on M: pointer lock released, then taken back; Esc and M close it; it never eats other keys
  await b.ev(`window.__pl = { exit: 0, req: 0 }; window.__fakeLock = true; const cvs = __sc.renderer.domElement;
    Object.defineProperty(document, 'pointerLockElement', { configurable: true, get: () => window.__fakeLock ? cvs : null });
    document.exitPointerLock = () => { __pl.exit++; window.__fakeLock = false; }; cvs.requestPointerLock = () => { __pl.req++; window.__fakeLock = true; }; 1`);
  const key = (k, extra = '') => b.ev(`window.dispatchEvent(new KeyboardEvent('keydown', { key: '${k}', ${extra} bubbles: true })); 1`);
  await key('m'); await sleep(900);
  const qm = await J("({ open: __sc.SA.S.qm, shown: !document.getElementById('qmap').hidden, exit: __pl.exit, lock: !!document.pointerLockElement, canvas: document.getElementById('qmCv').getBoundingClientRect().width | 0 })");
  info.qm = qm; ok(qm.open && qm.shown, 'M opens the Quick map'); ok(qm.exit >= 1 && !qm.lock, `pointer lock released on open (exit calls ${qm.exit})`); ok(qm.canvas > 150, `Quick map canvas is ${qm.canvas}px wide`);
  const drawn = await J("(() => { const c = document.getElementById('qmCv'), x = c.getContext('2d'); const d = x.getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 0; i < d.length; i += 4 * 37) if (d[i] + d[i + 1] + d[i + 2] > 30) n++; return n; })()");
  ok(drawn > 50, `Quick map has pixels drawn (${drawn} sampled)`);
  await key('m'); await sleep(500);
  const qm2 = await J("({ open: __sc.SA.S.qm, shown: !document.getElementById('qmap').hidden, req: __pl.req })");
  ok(!qm2.open && !qm2.shown, 'M again closes the Quick map'); if (arg === 'desktop') ok(qm2.req >= 1, `pointer lock taken back on close (request calls ${qm2.req})`); else ok(qm2.req === 0, 'a touch phone never asks for pointer lock');
  await key('m'); await sleep(400); await key('Escape'); await sleep(400);
  ok(!(await b.ev('__sc.SA.S.qm')), 'Esc closes the Quick map');
  await key('m'); await sleep(400); await b.ev("document.getElementById('qmap').dispatchEvent(new PointerEvent('pointerdown', { bubbles: true })); 1"); await sleep(300);
  ok(!(await b.ev('__sc.SA.S.qm')), 'a tap outside the map closes it');
  // ---- J is mount now (it must report on a vehicle or the squad, not open a map); M must not mount
  const logRows = async () => { await b.ev('__sc.openLog(); 1'); const r = await J("[...document.querySelectorAll('.logrow b')].map(e => e.textContent)"); await b.ev("document.getElementById('menuSheet').hidden = true; 1", true); return r || []; };
  const before = (await logRows()).length; await key('j'); await sleep(600); const after = await logRows();
  const mountMsg = after.slice(0, Math.max(0, after.length - before + 1)).find(t => /vehicle|squad|dismount|mounting|driver/i.test(t));
  ok(!!mountMsg, 'J gives the mount reply: ' + JSON.stringify(mountMsg)); ok(!(await b.ev('__sc.SA.S.qm')), 'J does not open the map');
  // ---- the corner map toggle persists
  await key('M', 'shiftKey: true,'); await sleep(500);
  const t1 = await J("({ hidden: document.getElementById('miniMap').hidden, pref: localStorage.getItem('squall-cove-minimap'), on: __sc.SA.miniOn() })");
  ok(t1.hidden && t1.pref === '0' && !t1.on, 'Shift + M hides the corner map and saves it: ' + JSON.stringify(t1));
  await key('M', 'shiftKey: true,'); await sleep(400); const t2 = await J("({ hidden: document.getElementById('miniMap').hidden, pref: localStorage.getItem('squall-cove-minimap') })");
  ok(!t2.hidden && t2.pref === '1', 'Shift + M shows it again and saves it');
  // ---- layout: nothing overlaps the compass, corner map or Map button (phones: the 390x844 and 844x390 postures)
  const lay = await J(`(() => { const ids = ['#compass', '#miniMap', '#fpMapBtn'], others = ['#bHud', '#bTick', '#bStat', '.fpTop', '.fpHint', '#sqHud', '#feedCol', '#fpStick', '#fpFire', '#fpUse', '#fpJump', '#fpStance', '#fpTools', '#fpSquad', '#fpReload', '#fpZoom', '#fpHelm', '#fpDrop', '#fpPrompt'];
    const vis = (e) => { if (!e) return null; const r = e.getBoundingClientRect(), cs = getComputedStyle(e); if (r.width < 2 || r.height < 2 || cs.display === 'none' || cs.visibility === 'hidden' || e.hidden) return null; return r; };
    const rows = []; const all = [...ids, ...others].map(s => [s, document.querySelector(s)]).filter(([s, e]) => e); const found = {};
    for (const [s, e] of all) { const r = vis(e); if (r) found[s] = r; }
    const names = Object.keys(found), hits = [];
    for (const a of ids) { if (!found[a]) continue; for (const o of names) { if (o === a || ids.includes(o) && o < a) continue; const A = found[a], B = found[o]; const ix = Math.min(A.right, B.right) - Math.max(A.left, B.left), iy = Math.min(A.bottom, B.bottom) - Math.max(A.top, B.top); if (ix > 1 && iy > 1) hits.push(a + ' x ' + o + ' (' + Math.round(ix) + 'x' + Math.round(iy) + ')'); } }
    const rect = (s) => found[s] ? [Math.round(found[s].left), Math.round(found[s].top), Math.round(found[s].width), Math.round(found[s].height)] : null;
    const out = { hits, compass: rect('#compass'), mini: rect('#miniMap'), mapBtn: rect('#fpMapBtn'), vw: innerWidth, vh: innerHeight, shown: names };
    return out; })()`);
  info.layout = lay; log('layout ' + JSON.stringify(lay));
  ok(lay.hits.length === 0, 'no overlaps with the compass, corner map or Map button: ' + JSON.stringify(lay.hits));
  if (arg !== 'desktop') { const btn = lay.mapBtn; ok(!!btn && btn[2] >= 48 && btn[3] >= 48, 'Map button is at least 48 px: ' + JSON.stringify(btn)); }
  const inside = (r) => !r || (r[0] >= 0 && r[1] >= 0 && r[0] + r[2] <= lay.vw && r[1] + r[3] <= lay.vh); ok(inside(lay.compass) && inside(lay.mini) && inside(lay.mapBtn), 'compass, corner map and Map button are inside the screen');
  // ---- overview symbols
  await b.ev("__sc.exitFP(); 1"); await sleep(4000);
  await b.ev(`(() => { const S = __sc; S.BATTLE.spec = null; const mv = (q, x, z) => { q.x = x; q.z = z; if (q.body) q.body.position.set(x, S.standY(x, z) + q.height / 2, z); q.obj.position.set(x, S.standY(x, z) - q.footOff, z); };
    const blue = S.people.filter(q => q.bot && !q.ride && q.bot.team === 'blue' && q.state !== 'rag'), red = S.people.filter(q => q.bot && !q.ride && q.bot.team === 'red' && q.state !== 'rag'), b0 = blue[0];
    red.slice(0, 4).forEach((q, i) => mv(q, b0.x + 40 + i * 14, b0.z + 25 - i * 9)); S.god.follow = null; S.god.fly = null; S.god.tgt.x = b0.x + 20; S.god.tgt.z = b0.z + 10; S.god.dist = ${arg === 'desktop' ? 300 : 420}; return 1; })()`); await sleep(4500);
  const sy = await J(`(() => { const S = __sc.SA.S; __sc.SA.frame(0.016); const f = S.syms.filter(s => s.side === 'friendly'), h = S.syms.filter(s => s.side === 'hostile'); const kinds = (a) => [...new Set(a.map(s => s.kind))]; return { mode: __sc.getHover ? 'ok' : '', fade: S.fade, on: __sc.SA.symOn(), cls: document.getElementById('symCv').className, f: f.length, h: h.length, fShapes: [...new Set(f.map(s => s.shape))], hShapes: [...new Set(h.map(s => s.shape))], fKinds: kinds(f), hKinds: kinds(h), pts: S.pts.map(p => p.letter + (p.owner || '-')), labels: S.syms.filter(s => s.label).map(s => s.label).slice(0, 6), total: S.total, drawn: S.drawn, err: __sc.SA.err || null }; })()`);
  info.sym = sy; log('symbols ' + JSON.stringify(sy));
  ok(sy.on && /on/.test(sy.cls), 'symbols default ON in a battle and the overlay is showing'); ok(sy.f > 0 && sy.h > 0, `both sides have symbols (friendly ${sy.f}, hostile ${sy.h})`);
  ok(sy.fShapes.join() === 'rect' && sy.hShapes.join() === 'diamond', `friendly = rectangle, hostile = diamond (${sy.fShapes}, ${sy.hShapes})`);
  ok(sy.pts.length >= 1 && /^[A-Z]/.test(sy.pts[0]), 'points have letter markers: ' + sy.pts.join(' '));
  ok(sy.labels.length > 0, 'squads show a name when zoomed in: ' + sy.labels.join(', '));
  // a selected unit gets the yellow dashed outline; a wounded unit is dim
  const sel = await J(`(() => { const S = __sc.SA.S, q = __sc.people.find(p => p.bot && !p.ride && p.state !== 'rag' && p.bot.team === 'blue'); if (!q) return null; __sc.setSel([q]); __sc.SA.frame(0.016); return { sel: S.syms.some(s => s.sel) }; })()`);
  ok(sel && sel.sel, 'a selected unit is marked (yellow dashed outline)');
  // ---- 70 a side: cluster cap holds and nobody is lost from the counts
  const mass = await J(`(() => { const S = __sc.SA.S, sc = __sc; const cap = S.cap; let n = 0;
    for (const [team, role] of [['blue', 'Guard'], ['red', 'Raider']]) for (let i = 0; i < 70; i++) { const a = i * 2.399 + (team === 'red' ? 1.1 : 0), r = 40 + (i % 14) * 18 + (team === 'red' ? 7 : 0); const x = Math.cos(a) * r, z = Math.sin(a) * r; const q = sc.makePerson(0, x, z); q.side = team; q.role = role; q.y = sc.standY(x, z); n++; }
    sc.god.dist = 480; return { made: n, cap }; })()`);
  await sleep(4500);
  const cl = await J(`(() => { const S = __sc.SA.S; __sc.SA.frame(0.016); const cnt = (side) => S.syms.filter(s => s.side === side).reduce((a, s) => a + s.n, 0); return { cap: S.cap, drawnB: S.drawn.blue, drawnR: S.drawn.red, nB: cnt('friendly'), nR: cnt('hostile'), totB: S.total.blue, totR: S.total.red, osB: S.onScreen.blue, osR: S.onScreen.red, merged: S.syms.filter(s => s.merged).length, syms: S.syms.length }; })()`);
  info.cluster = cl; log('cluster ' + JSON.stringify(cl));
  ok(cl.drawnB <= cl.cap && cl.drawnR <= cl.cap, `cluster cap holds: drawn ${cl.drawnB} / ${cl.drawnR} per side, cap ${cl.cap}`);
  ok(cl.totB >= 70 && cl.totR >= 70, `70 or more units on each side counted (${cl.totB} / ${cl.totR})`); ok(cl.nB === cl.osB && cl.nR === cl.osR, `cluster counts add up: ${cl.nB} drawn = ${cl.osB} on screen of ${cl.totB} friendly, ${cl.nR} = ${cl.osR} of ${cl.totR} hostile`);
  ok(cl.merged > 0, `crowded marks were merged (${cl.merged} merged marks)`);
  // ---- zoomed in: nothing extra; zoomed out: symbols
  const zs = []; for (const d of [60, 120, 400]) { await b.ev(`__sc.god.fly = null; __sc.god.dist = ${d}; 1`); await sleep(2500); zs.push(await J(`(() => { __sc.SA.frame(0.016); const S = __sc.SA.S; return { d: ${d}, spx: +S.spx.toFixed(1), fade: +S.fade.toFixed(2), n: S.syms.length, on: /on/.test(document.getElementById('symCv').className) }; })()`)); }
  log('zoom ' + JSON.stringify(zs)); ok(zs[0].n === 0 && !zs[0].on && zs[1].n === 0 && !zs[1].on, 'symbols hidden when zoomed in (soldier ' + zs[0].spx + ' and ' + zs[1].spx + ' px tall)'); ok(zs[2].n > 0 && zs[2].fade === 1 && zs[2].spx < 7, 'symbols visible when zoomed out (soldier ' + zs[2].spx + ' px tall)');
  // ---- close up the symbols fade out; the Symbols toggle works and is remembered
  await b.ev('__sc.god.fly = null; __sc.god.dist = 40; 1'); log('dist set ' + await b.ev('__sc.god.dist') + ' spec ' + await b.ev('!!__sc.BATTLE.spec')); await sleep(3500); log('dist after ' + await b.ev('__sc.god.dist')); const near = await J("(() => { __sc.SA.frame(0.016); return { fade: __sc.SA.S.fade, cls: document.getElementById('symCv').className, n: __sc.SA.S.syms.length }; })()");
  ok(near.fade < 0.05 && !/on/.test(near.cls), `symbols fade away when the camera is close (fade ${near.fade.toFixed(2)})`);
  await b.ev('__sc.god.dist = 300; document.getElementById("bSym").click(); 1'); await sleep(800);
  const tg = await J("({ pref: localStorage.getItem('squall-cove-symbols'), on: __sc.SA.symOn(), label: document.getElementById('bSym').textContent })");
  ok(tg.pref === '0' && !tg.on && /off/i.test(tg.label), 'the Symbols button turns them off and remembers it: ' + JSON.stringify(tg));
  await b.ev('document.getElementById("bSym").click(); 1'); const tg2 = await J("({ pref: localStorage.getItem('squall-cove-symbols'), on: __sc.SA.symOn() })"); ok(tg2.pref === '1' && tg2.on, 'and back on');
  // ---- persistence across a reload (minimap off stays off), then the sandbox default for symbols
  if (RELOAD) {
    await b.ev("localStorage.setItem('squall-cove-minimap','0'); localStorage.removeItem('squall-cove-symbols'); 1");
    if (!await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=${P.ed}`)) throw new Error('no reload');
    const rl = await J("({ mini: __sc.SA.miniOn(), sym: __sc.SA.symOn(), battle: __sc.BATTLE.on })"); log('after reload ' + JSON.stringify(rl));
    ok(rl.mini === false, 'corner map stays off after a reload'); ok(rl.sym === false && !rl.battle, 'symbols are off by default in the sandbox when no hostile unit exists');
  }
  ok(b.errs.length === 0, 'no console errors: ' + JSON.stringify(b.errs.slice(0, 4)));
  console.log('\n=== ' + (fail.length ? 'FAILED ' + fail.length : 'PASSED') + ' ===\n' + fail.join('\n'));
  console.log(JSON.stringify(info));
} catch (e) { console.log('ERR ' + (e && e.stack || e)); fail.push('crash'); }
finally { await b.close(); await srv.close(); process.exit(fail.length ? 1 : 0); }
