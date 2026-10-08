// AC-130 sensor station check (GUNSHIP-STATION-SPEC.md). usage: node qa/station-check.mjs [desktop|portrait]
// Opens the station for a side in a running battle and asserts, in atomic page evaluations (the software renderer runs about one frame in many seconds, so the test steps the
// simulation by hand with __sc.updateAir and __sc.stnStep and keeps the game's own draw switched off except where a real render is the thing being tested):
//   altitude, camera ground point fixed while the aircraft moves, gimbal limit and lock loss, weapon ready-up states, fire at the aim point, danger close, immunity, crew callouts,
//   Thermal / Night / Colour render without errors, exit restores the normal view, the interior/exterior mix crossfade, the operator role at deploy, and (portrait) the phone layout.
import { sleep, startServer, launch, loadGame, clickText, PROFILES } from './harness.mjs';
const LAYOUT_ONLY = process.argv[3] === 'layout', prof0 = PROFILES[process.argv[2] || 'desktop'], phone = prof0.ed === 'phone', prof = phone ? prof0 : { ...prof0, w: 560, h: 360 };
const T0 = Date.now(), log = (m) => console.log(`[${((Date.now() - T0) / 1000).toFixed(0)}s] ${m}`); setTimeout(() => { console.log('ERR watchdog: the station check took over 25 minutes'); process.exit(2); }, 1500000).unref();
const fail = [], num = {}; const ok = (name, cond, detail) => { console.log((cond ? '  ok   ' : '  FAIL ') + name + (detail !== undefined ? '  ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)) : '')); if (!cond) fail.push(name); };
const srv = await startServer(); const b = await launch({ ...prof, extraArgs: ['--autoplay-policy=no-user-gesture-required'] });
const J = async (expr) => { const r = await b.ev(`JSON.stringify((()=>{ ${expr} })())`); return r ? JSON.parse(r) : null; };
try {
  if (!await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=${prof.ed}`)) throw new Error('no load');
  await b.ev("document.getElementById('tablet').hidden=true; __sc.openBattleSetup(); 1"); await sleep(500); await b.ev(clickText('#bSetup button', 'Begin battle')); await sleep(5000);
  await b.ev("__sc.CHEAT.god=true; __sc.playBattle('blue'); 1"); await sleep(2500); await b.ev("document.getElementById('help').hidden=true; __sc.exitFP(); 1"); await sleep(500);
  await b.ev("window.__realRender = __sc.renderer.render.bind(__sc.renderer); __sc.renderer.render = () => {}; 1");                                   // the game's own draw is off until a render is the thing under test
  for (let k = 0; k < 60; k++) { const s = await b.ev('JSON.stringify(__sc.Snd.stats2())'); const o = JSON.parse(s); if (o.ready && o.ctx === 'running') break; if (k === 3) await b.ev("window.dispatchEvent(new KeyboardEvent('keydown',{key:'Shift'}));1"); await sleep(500); }
  log('battle running, audio ' + (await b.ev('JSON.stringify(__sc.Snd.stats2())')));
  const base = await J("const c = __sc.camera; return { fov: c.fov, near: c.near, far: c.far, mode: __sc.getMode ? 0 : 0, fog: __sc.scene.fog.density, body: document.body.className, tablet: document.getElementById('tablet').hidden }");

  if (!LAYOUT_ONLY) {
  // ---- 1 open: a gunship is summoned for the side, high, with the station on it
  const o1 = await J("__sc.AIR.list.length = 0; const r = __sc.stnOpenFor('blue'); const u = __sc.STN.u; return { r, on: __sc.STN.on, kind: u && u.kind, y: u && u.y, team: u && u.team, hidden: document.getElementById('stn').hidden, body: document.body.classList.contains('stn-on') }");
  ok('opens for the side and summons a gunship', o1.r && o1.on && o1.kind === 'gunship' && o1.team === 'blue' && !o1.hidden && o1.body, o1);
  ok('flies high (450 to 600 m)', o1.y >= 450 && o1.y <= 600, 'y=' + Math.round(o1.y)); num.altitude = Math.round(o1.y);

  // ---- 2 the camera's ground point stays fixed while the aircraft moves
  const o2 = await J(`const S = __sc.STN, u = S.u, A0 = [S.ax, S.az], P0 = [u.x, u.z], cam = __sc.camera; let maxAim = 0, maxPx = 0, minRange = 1e9, maxRange = 0, states = new Set(), n = 0; const THREE = __sc.THREE; for (let i = 0; i < 25; i++) { __sc.updateAir(0.1); __sc.stnStep(0.1); }
    for (let i = 0; i < 90; i++) { __sc.updateAir(0.1); __sc.stnStep(0.1); maxAim = Math.max(maxAim, Math.hypot(S.ax - A0[0], S.az - A0[1])); states.add(S.state);
      if (i % 10 === 9) { const v = new THREE.Vector3(S.ax, S.ay, S.az).project(cam); maxPx = Math.max(maxPx, Math.hypot(v.x, v.y)); n++; } minRange = Math.min(minRange, S.range); maxRange = Math.max(maxRange, S.range); }
    return { moved: Math.round(Math.hypot(u.x - P0[0], u.z - P0[1])), maxAim, ndcOffCentre: +maxPx.toFixed(4), states: [...states], range: [Math.round(minRange), Math.round(maxRange)], y: Math.round(u.y), off: +(S.off * 57.3).toFixed(1) }`);
  ok('aim point does not move while the aircraft flies', o2.maxAim < 0.001 && o2.moved > 150, o2); ok('the point stays at the centre of the view', o2.ndcOffCentre < 0.02, 'max offset ' + o2.ndcOffCentre + ' (normalised)'); ok('stays locked in a steady orbit', o2.states.length === 1 && o2.states[0] === 'locked', o2.states);
  num.aircraftMoved = o2.moved; num.centreOffset = o2.ndcOffCentre; num.range = o2.range;

  // ---- 3 gimbal limit: beyond about 65 degrees the camera eases to the limit, says so, refuses to fire, drifts, then breaks lock; regaining the angle restores control
  const o3 = await J(`const S = __sc.STN, u = S.u, LIM = __sc.STN_LIM; const bear = () => Math.atan2(S.ax - u.x, S.az - u.z); const set = (rel) => { u.hd = bear() - Math.PI / 2 - rel; };
    const out = {}; const A0 = [S.ax, S.az]; set(1.75); __sc.stnStep(0.1); out.state1 = S.state; for (let i = 0; i < 25; i++) { set(1.75); __sc.stnStep(0.1); }
    const Lb = u.hd + Math.PI / 2, cb = Math.atan2(S.cd.x, S.cd.z); out.camOff = +(Math.abs(Math.atan2(Math.sin(cb - Lb), Math.cos(cb - Lb))) * 57.3).toFixed(1); out.limit = +(LIM * 57.3).toFixed(1);
    out.canFire = [0, 1, 2].map(i => S.canFire(i)); S.weapon = 0; S.W[0].prep = 0; S.W[0].rel = 0; out.fired = __sc.stnTryFire(); out.why = __sc.STN.msg || ''; out.stateAt2_5s = S.state; out.movedAt2_5s = Math.hypot(S.ax - A0[0], S.az - A0[1]);
    for (let i = 0; i < 20; i++) { set(1.75); __sc.stnStep(0.1); } out.movedAt4_5s = +Math.hypot(S.ax - A0[0], S.az - A0[1]).toFixed(2); out.stateAt4_5s = S.state;
    for (let i = 0; i < 50; i++) { set(1.75); __sc.stnStep(0.1); } out.stateAt9_5s = S.state; out.broken = S.state; out.msgBroken = (document.getElementById('stnMsg').textContent || '') ; return out;`);
  ok('past the limit it says Losing target and eases to the limit', o3.state1 === 'losing' && Math.abs(o3.camOff - o3.limit) < 3, o3); ok('weapons refuse to fire outside the limit and say why', o3.canFire.every(x => !x) && o3.fired === false && /gimbal limit/.test(o3.why), o3.why);
  ok('after a few seconds the point starts to drift', o3.movedAt4_5s > 0.5, 'drift ' + o3.movedAt4_5s + ' m'); ok('and finally the lock breaks', o3.stateAt9_5s === 'broken', o3.stateAt9_5s); num.limitDeg = o3.limit; num.camAtLimitDeg = o3.camOff;
  const o3b = await J(`const S = __sc.STN, u = S.u; __sc.stnSetAim(S.ax, S.az); const bearing = Math.atan2(S.ax - u.x, S.az - u.z); u.hd = bearing - Math.PI / 2; for (let i = 0; i < 3; i++) __sc.stnStep(0.1); const a = S.state;
    const A1 = [S.ax, S.az]; u.hd = bearing - Math.PI / 2 - 1.75; for (let i = 0; i < 20; i++) { u.hd = Math.atan2(A1[0] - u.x, A1[1] - u.z) - Math.PI / 2 - 1.75; __sc.stnStep(0.1); } const lost = S.state; u.hd = Math.atan2(S.ax - u.x, S.az - u.z) - Math.PI / 2 - 0.2; for (let i = 0; i < 6; i++) __sc.stnStep(0.1); return { retaken: a, lost, regained: S.state };`);
  ok('slewing or tapping after a break locks again; regaining the angle restores control', o3b.retaken === 'locked' && o3b.lost === 'losing' && o3b.regained === 'locked', o3b);

  // ---- 4 weapons: one at a time, ready-up after a switch
  const o4 = await J(`const S = __sc.STN, u = S.u; u.hd = Math.atan2(S.ax - u.x, S.az - u.z) - Math.PI / 2; for (let i = 0; i < 50; i++) __sc.stnStep(0.1); const lab = (i) => document.getElementById('stnC' + (i + 1)).querySelector('.stnLab').textContent; const out = {};
    const adv = (t) => { for (let k = 0; k < Math.round(t / 0.02); k++) __sc.stnStep(0.02); };
    for (const [i, name, ready] of [[1, 'cannon', 1.0], [0, 'howitzer', 2.0], [2, 'vulcan', 0.12]]) { __sc.stnSelect(i); adv(0.02); const r = { sel: S.weapon, justAfter: lab(i), fireOk0: S.canFire(i) }; adv(ready * 0.5); r.half = lab(i); adv(ready * 0.5 + 0.1); r.after = lab(i); r.fireOk1 = S.canFire(i); out[name] = r; }
    out.others = [0, 1, 2].filter(i => i !== S.weapon).map(i => S.canFire(i)); return out;`);
  ok('switching shows Getting ready then Ready (howitzer about 2 s, 40 mm about 1 s, Vulcan almost none)', o4.cannon.justAfter === 'Getting ready' && o4.cannon.half === 'Getting ready' && o4.cannon.after === 'Ready' && o4.howitzer.justAfter === 'Getting ready' && o4.howitzer.half === 'Getting ready' && o4.howitzer.after === 'Ready' && o4.vulcan.after === 'Ready' && !o4.howitzer.fireOk0 && o4.howitzer.fireOk1, o4);
  ok('only the chosen weapon can fire', o4.others.every(x => !x), o4.others);
  num.ready = { howitzer: 2.0, cannon: 1.0, vulcan: 0.12 };

  // ---- 5 fire: the shells and rounds land on the aim point; danger close; immunity
  const o5 = await J(`const S = __sc.STN, u = S.u, sc = __sc; const out = {}; const set = () => { u.hd = Math.atan2(S.ax - u.x, S.az - u.z) - Math.PI / 2; };
    // a quiet spot: no people near
    const free = (x, z) => sc.people.every(q => Math.hypot(q.x - x, q.z - z) > 120); let found = null; for (let r = 0; r < 800 && !found; r++) { const x = (Math.random() * 2 - 1) * 300, z = (Math.random() * 2 - 1) * 300; if (sc.heightAt(x, z) > 1 && free(x, z)) found = [x, z]; }
    if (!found) { return { err: 'no quiet ground' }; } sc.stnSetAim(found[0], found[1]); set(); for (let i = 0; i < 40; i++) { set(); sc.stnStep(0.1); } out.state = S.state; out.aim = [Math.round(S.ax), Math.round(S.az)]; out.danger0 = S.danger;
    // howitzer
    sc.stnSelect(0); for (let i = 0; i < 25; i++) { set(); sc.stnStep(0.1); } const n0 = sc.AIR.shells.length; out.howFired = sc.stnTryFire(); const sh = sc.AIR.shells[sc.AIR.shells.length - 1]; out.shellErr = sh && sh.stn ? +Math.hypot(sh.x - S.ax, sh.z - S.az).toFixed(2) : null; out.shells = sc.AIR.shells.length - n0; out.how2 = sc.stnTryFire(); sc.stnStep(0.02); out.howLab = document.getElementById('stnC1').querySelector('.stnLab').textContent;
    const h0 = sc.AC.st.howHit; for (let i = 0; i < 40; i++) { sc.updateAir(0.1); set(); sc.stnStep(0.1); } out.howHits = sc.AC.st.howHit - h0;
    // 40 mm: three rounds, each a tracer that ends within a few metres of the point
    sc.stnSelect(1); for (let i = 0; i < 25; i++) { set(); sc.stnStep(0.1); } const T = sc.tracers; const endErr = () => { let best = []; for (let k = 0; k < T.N; k++) if (T.act[k]) { const ex = T.sx[k] + T.ux[k] * T.D[k], ez = T.sz[k] + T.uz[k] * T.D[k], ey = T.sy[k] + T.uy[k] * T.D[k]; if (ey < 80) best.push(Math.hypot(ex - S.ax, ez - S.az)); } return best; };
    let ce = []; for (let tries = 0; tries < 4 && !ce.length; tries++) { if (tries) { S.W[1].rel = 0; } T.act.fill(0); out.canFired = sc.stnTryFire(); for (let i = 0; i < 18; i++) { sc.updateAir(0.1); set(); sc.stnStep(0.1); if (i % 3 === 2) for (const e of endErr()) ce.push(e); } out.tries = tries + 1; }   /* the phone drops three tracers in ten on purpose */
    out.cannonTracers = ce.length; out.cannonMax = ce.length ? +Math.max(...ce).toFixed(2) : null;
    // Vulcan: hold the trigger for two seconds
    sc.stnSelect(2); for (let i = 0; i < 10; i++) { set(); sc.stnStep(0.1); } T.act.fill(0); const v0 = S.shots.vul; S.fireKey = true; const ve = []; for (let i = 0; i < 30; i++) { sc.updateAir(0.05); set(); sc.stnStep(0.05); for (const e of endErr()) ve.push(e); T.act.fill(0); } S.fireKey = false; set(); sc.stnStep(0.05); sc.updateAir(0.05); out.vulRounds = S.shots.vul - v0; out.vulMax = ve.length ? +Math.max(...ve).toFixed(2) : null; out.vulWithin6 = ve.length ? +(ve.filter(e => e < 6).length / ve.length).toFixed(2) : null; out.vulFill = +S.W[2].fill.toFixed(2); out.vulEnded = !sc.AC.stn.SS.vOn;
    return out;`);
  if (o5.err) ok('found a quiet spot', false, o5); else {
    ok('howitzer fires and the shell lands within 5 m of the aim point', o5.howFired && o5.shells === 1 && o5.shellErr !== null && o5.shellErr <= 5, { err: o5.shellErr }); ok('the howitzer then reloads (no second shot at once)', o5.how2 === false && o5.howLab === 'Reloading', o5.howLab); ok('the shell lands (impact sound and blast code ran)', o5.howHits >= 1, o5.howHits);
    ok('40 mm rounds end within 6 m of the aim point', o5.canFired && o5.cannonTracers >= 1 && o5.cannonMax <= 6, { tracers: o5.cannonTracers, max: o5.cannonMax }); ok('Vulcan fires while held and lands on the point', o5.vulRounds > 10 && o5.vulWithin6 >= 0.8, { rounds: o5.vulRounds, within6: o5.vulWithin6, max: o5.vulMax }); ok('Vulcan stops when released', o5.vulEnded, o5.vulFill);
    num.fire = { howitzerErr: o5.shellErr, cannonMax: o5.cannonMax, vulcanRounds: o5.vulRounds, vulcanWithin6: o5.vulWithin6 }; }
  const o5b = await J(`const S = __sc.STN, sc = __sc; const out = {}; const q = sc.people.find(p => sc.STN && p.side === S.team && p.state !== 'rag' && !p.ride); if (!q) return { err: 'no friend' }; const save = [q.x, q.z]; sc.stnSetAim(q.x + 60, q.z); S.contacts = []; sc.stnStep(0.02); out.near = S.danger; sc.stnSetAim(q.x + 200, q.z); sc.stnStep(0.02);
    out.far = Math.max(0, S.danger - 0); out.dcText = document.getElementById('stnMsg').textContent; return out;`);
  ok('danger close warns when friendlies are within about 90 m of the aim point', o5b.near >= 1, o5b);
  const o5c = await J(`const sc = __sc, u = sc.STN.u; const hp = u.hp; sc.damageAir(u, 500, 'mg'); sc.damageAir(u, 9999, 'crash'); sc.damageAir(u, 80, 'you'); const small = u.hp; sc.damageAir(u, 170, 'you', 'missile'); const one = hp - u.hp; return { hp, small, oneMissile: one, pct: +(one / u.hpMax * 100).toFixed(1), down: u.down };`);
  ok('small arms, machine guns, light AA and crashes cannot hurt it', o5c.small === o5c.hp, o5c); ok('a missile hurts it slowly and never kills it in one hit', o5c.oneMissile > 0 && o5c.pct < 10 && !o5c.down, o5c.pct + ' percent of its health'); num.missilePct = o5c.pct;

  // ---- 6 crew callouts
  const o6 = await J(`const S = __sc.STN; S.crew.say.length = 0; S.crew.last = ''; S.crewForce = true; for (let i = 0; i < 40; i++) __sc.stnCrew('how'); S.crewForce = false; const said = S.crew.say.slice(); let rep = 0; for (let i = 1; i < said.length; i++) if (said[i] === said[i - 1]) rep++;
    S.crew.n = 0; S.crew.say.length = 0; S.crew.last = ''; for (let i = 0; i < 600; i++) __sc.stnCrew('how'); const rate = S.crew.n / 600; return { phrases: [...new Set(said)], repeats: rep, rate: +rate.toFixed(2), n: said.length };`);
  ok('crew calls vary and never repeat the same words twice in a row', o6.repeats === 0 && o6.phrases.length >= 3, o6); ok('about two reloads in three get a call', o6.rate > 0.55 && o6.rate < 0.78, o6.rate); num.crewRate = o6.rate;

  // ---- 7 the sound mix: interior bed in, exterior out, impacts muffled (needs the audio engine running)
  await b.ev("__sc.AC.stn.preInt(); 1"); let haveInt = false; for (let k = 0; k < 40; k++) { haveInt = await b.ev("__sc.Snd.have('ac130_int_cabin_loop') && __sc.Snd.have('ac130_int_headset_loop') && __sc.Snd.have('ac130_int_whine_loop')"); if (haveInt) break; await b.ev("__sc.AC.stn.preInt(); 1"); await sleep(1500); }
  await b.ev("for (let i = 0; i < 20; i++) __sc.Snd.tick && 0; 1"); await sleep(6000);
  const mix = await J("return __sc.Snd.stnState()");
  ok('interior stems are loaded when the station opens', !!haveInt);
  if (haveInt && mix && mix.ctx === 'running') { ok('outdoor beds fall (ambience, weather, water, people at or under 15 percent)', ['amb', 'wx', 'water', 'ppl'].every(k => mix.buses[k] <= mix.vol[k] * 0.15 + 0.002), mix.buses); ok('cabin bed about 0.7 and the headset about 0.6 are in', mix.cabin !== null && mix.cabin > 0.55 && mix.head !== null && mix.head > 0.45, { cabin: mix.cabin, head: mix.head, whine: mix.whine }); ok('own aircraft exterior drone is faded out', mix.prop.every(g => g < 0.05), mix.prop); ok('the mat bus closes to 2.5 kHz at about -6 dB', mix.matCut >= 2400 && mix.matCut <= 2600 && Math.abs(mix.buses.mat - mix.vol.mat * 0.5) < 0.03, { cut: mix.matCut, gain: mix.buses.mat }); num.mixOpen = mix; }
  else ok('audio engine running for the mix check', false, mix);

  // ---- 8 the three sensor modes render without errors (a real draw each)
  await b.ev("__sc.renderer.render = window.__realRender; 1"); const errs0 = b.errs.length; const rt = {};
  for (const m of ['thermal', 'night', 'colour']) { const t = Date.now(); const r = await J(`const S = __sc.STN; __sc.stnSetMode('${m}'); __sc.stnStep(0.05); __sc.stnRender(); const gl = __sc.renderer.getContext(); return { mode: S.mode, err: gl.getError(), rt: [__sc.renderer.getRenderTarget() === null] };`); rt[m] = { ms: Date.now() - t, err: r.err, mode: r.mode }; }
  ok('Thermal, Night vision and Colour all render with no GL or console errors', Object.values(rt).every(x => x.err === 0) && b.errs.length === errs0, { rt, errors: b.errs.slice(errs0, errs0 + 3) });
  const hot = await J("let n = 0, all = 0; for (const q of __sc.people) q.obj.traverse(o => { if (o.isMesh) { all++; if (o.material.type === 'MeshBasicMaterial' && o.material.color.getHex() === 0xff00ff) n++; } }); const R = __sc.stnR; return { magenta: n, meshes: all, rt: [R.rw, R.rh], view: [Math.round(__sc.STN.view.w), Math.round(__sc.STN.view.h)], pr: __sc.renderer.getPixelRatio() };");
  ok('thermal puts every person mesh back after drawing', hot && hot.magenta === 0 && hot.meshes > 0, hot);
  if (phone) ok('phone: the sensor view is drawn smaller than the screen', hot.rt[0] <= 760 && hot.rt[0] < hot.view[0] * hot.pr * 0.75, hot);
  await b.ev("__sc.renderer.render = () => {}; 1");

  // ---- 9 leaving restores the normal view and the normal mix
  const o9 = await J(`const sc = __sc, S = sc.STN; const u = S.u; const wasManual = u.wasManual; sc.stnClose(); return { on: S.on, hidden: document.getElementById('stn').hidden, body: document.body.classList.contains('stn-on'), fov: sc.camera.fov, near: sc.camera.near, far: sc.camera.far, rt: sc.renderer.getRenderTarget() === null, scissor: sc.renderer.getContext().isEnabled(sc.renderer.getContext().SCISSOR_TEST), fog: sc.scene.fog.density, manual: u.manual, wasManual, alive: sc.AIR.list.includes(u), life: Math.round(u.life), up: [sc.camera.up.x, sc.camera.up.y, sc.camera.up.z] };`);
  await sleep(2500);
  const o9b = await J("const c = __sc.camera; return { fov: c.fov, aspect: +c.aspect.toFixed(3), win: +(innerWidth / innerHeight).toFixed(3), far: c.far, near: c.near, tablet: document.getElementById('tablet').hidden }");
  ok('exit: station closed, page back, draw target and scissor reset', !o9.on && o9.hidden && !o9.body && o9.rt && !o9.scissor, o9); ok('exit: camera fov, aspect and clipping are the normal ones', Math.abs(o9b.fov - base.fov) < 0.01 && Math.abs(o9b.aspect - o9b.win) < 0.01 && o9b.far === base.far && o9b.near === base.near, { before: base, after: o9b }); ok('exit: fog restored and the aircraft stays on station', Math.abs(o9.fog - base.fog) < 0.0001 && o9.alive && o9.manual === !!o9.wasManual, { fog: o9.fog, base: base.fog, life: o9.life });
  await sleep(6000); const mix2 = await J("return __sc.Snd.stnState()");
  if (mix && mix.ctx === 'running' && mix2) { ok('exit: outdoor beds come back and the interior bed fades out', mix2.on === false && mix2.buses.amb >= mix2.vol.amb * 0.9 && Math.abs(mix2.buses.mat - mix2.vol.mat) < 0.03 && mix2.matCut > 15000 && (mix2.cabin === null || mix2.cabin < 0.05), mix2); }

  // ---- 10 the operator role at deploy: spawns the player at the station
  await b.ev("__sc.AIR.list.length = 0; __sc.BATTLE.kit = 'gunship'; __sc.playBattle('blue'); 1"); await sleep(4000);
  let o10 = await J("return { on: __sc.STN.on, op: __sc.STN.op, fp: __sc.fp.on, kit: __sc.BATTLE.kit, gunships: __sc.AIR.list.filter(u => u.kind === 'gunship' && u.team === 'blue').length, hp: __sc.fp.p && __sc.fp.p.hp }");
  for (let k = 0; k < 20 && !(o10 && o10.on); k++) { await sleep(1500); o10 = await J("return { on: __sc.STN.on, op: __sc.STN.op, fp: __sc.fp.on, kit: __sc.BATTLE.kit, gunships: __sc.AIR.list.filter(u => u.kind === 'gunship' && u.team === 'blue').length, hp: __sc.fp.p && __sc.fp.p.hp }"); }
  ok('Gunship operator: deploying opens the station, with the side\'s gunship summoned and the player in first person', o10 && o10.on && o10.op && o10.fp && o10.gunships === 1, o10);
  const lk0 = await J("const p = __sc.fp.p; window.__lk = [p.x, p.z, __sc.fp.yaw]; window.dispatchEvent(new KeyboardEvent('keydown', { key: 'w' })); window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Shift' })); return { x: p.x, z: p.z }"); await sleep(2500);
  const lk1 = await J("const p = __sc.fp.p; window.dispatchEvent(new KeyboardEvent('keyup', { key: 'w' })); window.dispatchEvent(new KeyboardEvent('keyup', { key: 'Shift' })); return { moved: +Math.hypot(p.x - window.__lk[0], p.z - window.__lk[1]).toFixed(2), yaw: Math.abs(__sc.fp.yaw - window.__lk[2]) }");
  ok('keys at the station never reach the soldier underneath', lk1 && lk1.moved < 0.6 && lk1.yaw < 0.01, lk1);
  const o10b = await J("const sc = __sc; window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); return { on: sc.STN.on, fp: sc.fp.on }");
  ok('Esc leaves the station and the player is back as a soldier', o10b && !o10b.on && o10b.fp, o10b);
  await b.ev("__sc.STN.on && __sc.stnClose(); __sc.BATTLE.kit = 'assault'; 1");
  const o10c = await J("const sc = __sc; sc.exitFP(); const out = {}; sc.BATTLE.kit = 'assault'; const p = sc.stnOpenFor('red'); out.opened = p; out.team = sc.STN.u && sc.STN.u.team; sc.stnClose(); return out;");
  ok('the god-mode command panel and the red side open the same station', o10c && o10c.opened && o10c.team === 'red', o10c);
  const o12 = await J("const sc = __sc; sc.AIR.list.length = 0; sc.BATTLE.on = false; let out; try { const r = sc.stnOpenFor('blue'); const u = sc.STN.u, p0 = [u.x, u.z]; for (let i = 0; i < 40; i++) sc.stnStep(0.1); out = { r, on: sc.STN.on, moved: Math.round(Math.hypot(u.x - p0[0], u.z - p0[1])), state: sc.STN.state, y: Math.round(u.y) }; sc.stnClose(); } catch (e) { out = { err: String(e) }; } sc.BATTLE.on = true; return out;");
  ok('sandbox (no battle running): the station flies the gunship itself', o12 && o12.r && o12.moved > 100 && o12.state === 'locked', o12);
  ok('no page errors during the run', b.errs.filter(e => !/Failed to load resource|favicon/.test(e)).length === 0, b.errs.slice(0, 3));

  }
  // ---- 11 layout: no overlaps between the readouts, message, map and thumb pad; targets; no sideways scroll
  {
    if (!phone) { await b.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 760, deviceScaleFactor: 1, mobile: false }); await sleep(800); }
    await b.ev("__sc.renderer.render = () => {}; __sc.stnOpenFor('blue'); 1"); await sleep(2500);
    const O = await J(`const sc = __sc; sc.stnMsg && 0; sc.STN.msg = 'DANGER CLOSE: friendly forces within 90 m of the aim point.'; sc.STN.msgT = sc.STN.t; sc.STN.danger = 1; sc.STN.hudT = 0; sc.stnStep(0.05); document.getElementById('stnMsg').hidden = false;
      const ids = ['stnTL', 'stnTR', 'stnMsg', 'stnSt', 'stnMini', 'stnPad', 'stnCards', 'stnBar'], R = {}; for (const id of ids) { const e = document.getElementById(id), q = e.getBoundingClientRect(), vis = !e.hidden && getComputedStyle(e).display !== 'none' && q.width > 0; R[id] = vis ? [q.left, q.top, q.right, q.bottom] : null; }
      const hit = []; const a = (x, y) => R[x] && R[y] && R[x][0] < R[y][2] - 1 && R[y][0] < R[x][2] - 1 && R[x][1] < R[y][3] - 1 && R[y][1] < R[x][3] - 1; const view = ['stnTL', 'stnTR', 'stnMsg', 'stnSt', 'stnMini', 'stnPad'];
      for (let i = 0; i < view.length; i++) for (let j = i + 1; j < view.length; j++) if (a(view[i], view[j])) hit.push(view[i] + '+' + view[j]); const vr = document.getElementById('stnView').getBoundingClientRect(); const outside = view.filter(id => R[id] && (R[id][0] < vr.left - 1 || R[id][2] > vr.right + 1 || R[id][1] < vr.top - 1 || R[id][3] > vr.bottom + 1));
      const small = []; for (const e of document.querySelectorAll('#stn button')) { const q = e.getBoundingClientRect(); if (q.width && q.height && Math.min(q.width, q.height) < 47.5) small.push(e.id + ':' + Math.round(q.width) + 'x' + Math.round(q.height)); }
      const lv = R.stnBar; const leave = document.getElementById('stnLeave').getBoundingClientRect();
      return { hit, outside, small, scrollW: document.documentElement.scrollWidth, win: [innerWidth, innerHeight], leave: [Math.round(leave.left), Math.round(leave.top), Math.round(leave.right), Math.round(leave.bottom)], viewH: Math.round(vr.height), viewW: Math.round(vr.width), pad: getComputedStyle(document.getElementById('stnPad')).display };`);
    ok('layout: readouts, message, map and thumb pad do not overlap one another or leave the view', O.hit.length === 0 && O.outside.length === 0, O);
    ok('layout: no sideways scroll and Leave station is on screen', O.scrollW <= O.win[0] + 1 && O.leave[2] <= O.win[0] + 1 && O.leave[3] <= O.win[1] + 1 && O.leave[0] >= 0, O);
    if (phone) ok('phone: every button in the station is at least 48 px and the thumb pad is shown', O.small.length === 0 && O.pad !== 'none', O.small);
    await b.ev("__sc.stnClose(); 1");
    if (!phone) await b.send('Emulation.setDeviceMetricsOverride', { width: prof.w, height: prof.h, deviceScaleFactor: 1, mobile: false });
  }
  if (false) {
    await b.ev("__sc.renderer.render = () => {}; __sc.stnOpenFor('blue'); 1"); await sleep(3000);
    const L = await J(`const r = (id) => { const e = document.getElementById(id); const q = e.getBoundingClientRect(); return { x: Math.round(q.left), y: Math.round(q.top), w: Math.round(q.width), h: Math.round(q.height) }; }; const small = []; for (const e of document.querySelectorAll('#stn button')) { const q = e.getBoundingClientRect(); if (q.width && q.height && Math.min(q.width, q.height) < 47.5) small.push(e.id + ':' + Math.round(q.width) + 'x' + Math.round(q.height)); }
      return { view: r('stnView'), cards: r('stnCards'), bar: r('stnBar'), leave: r('stnLeave'), pad: r('stnPad'), win: [innerWidth, innerHeight], scrollW: document.documentElement.scrollWidth, small, rt: [__sc.renderer.getPixelRatio()], padShown: getComputedStyle(document.getElementById('stnPad')).display };`);
    ok('phone: no sideways scroll, Leave station always on screen, thumb pad shown', L.scrollW <= L.win[0] + 1 && L.leave.y + L.leave.h <= L.win[1] + 1 && L.leave.x >= 0 && L.leave.x + L.leave.w <= L.win[0] + 1 && L.padShown !== 'none', L);
    ok('phone: every button in the station is at least 48 px', L.small.length === 0, L.small); await b.ev("__sc.stnClose(); 1");
  }
} catch (e) { console.log('ERR', e.stack || e.message); fail.push(e.message); } finally { await b.close(); await srv.close(); }
console.log('numbers', JSON.stringify(num)); console.log(fail.length ? 'FAIL: ' + fail.join(' | ') : 'station check: all ok'); process.exit(fail.length ? 1 : 0);
