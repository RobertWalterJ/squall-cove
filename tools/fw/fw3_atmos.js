/*FW-START part3: baked steam, mist and spray, and fog (assets/atmos), driven by the weather and time systems*/
(() => {
  const F = FW, R = F.R, PH = ED.phone;
  const A = F.A = { json: null, types: {}, fx: [], tiles: [], stats: { fx: 0, tiles: 0, steam: 0, splash: 0, bow: 0 }, k: {}, lit: {} };
  const gnd = (x, z) => Math.max(heightAt(x, z), 0);
  const sm = (a, b, x) => { const t = Math.max(0, Math.min(1, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  const clamp01 = (x) => Math.max(0, Math.min(1, x));
  const resWant = () => (PH || F.q === 'low') ? 'low' : 'full';
  A.ensure = () => A.jp || (A.jp = R.loadJson('assets/atmos/atmos_atlas.json?v=fw1').then(j => { A.json = j; return j; }).catch(e => { A.err = String(e); A.jp = null; return null; }));
  A.need = (name) => {
    const now = performance.now(); let T = A.types[name]; const res = resWant();
    if (T && T.state === 'ready' && T.res === res) { T.last = now; return T; }
    if (T && (T.state === 'loading' || T.state === 'bad')) return null;
    if (!A.json) { A.ensure(); return null; }
    const P = A.json.presets[name]; if (!P) { A.types[name] = { name, state: 'bad' }; return null; }
    if (T && T.state === 'ready') A.unload(name);
    T = A.types[name] = { name, P, state: 'loading', res, last: now, urls: [] };
    const jobs = ['main', 'heat'].filter(k => P.layers[k]).map(k => {
      const L = P.layers[k], use = (res === 'low' && L.low) ? L.low : L, url = 'assets/atmos/' + use.file; T.urls.push(url);
      return R.loadTex(url).then(tex => ({ k, L, use, tex }));
    });
    Promise.all(jobs).then(got => {
      T.layers = {}; const strip = P.kind === 'strip' || P.family === 'fog';
      for (const g0 of got) { const g = g0; if (g.k === 'heat') g.L = Object.assign({}, g.L, { size_m: P.layers.main.size_m, anchor: P.layers.main.anchor });
        const key = 'atm:' + name + ':' + g.k + ':' + res, combo = R.combo({ key, tex: g.tex, cols: g.use.cols, rows: g.use.rows, fw: g.use.frame_px[0], fh: g.use.frame_px[1], anchor: g.L.anchor, mode: g.k === 'main' ? 3 : 2, order: g.k === 'heat' ? 6.45 : (P.family === 'fog' ? 5.9 : 6.1), rule: g.k === 'heat' ? 'heat' : 'any', edge: strip ? 0.14 : 0 });
        if (g.k === 'main') combo.mat.uniforms.uCool.value = (P.sensors && P.sensors.thermal && P.sensors.thermal.alpha_gain) || 0.1;
        T.layers[g.k] = { combo, size: g.L.size_m, anchor: g.L.anchor };
      }
      const by = (st) => P.clips.filter(c => c.stage === st);
      T.clips = { start: by('start')[0], loop: by('loop'), fade: by('fade')[0], shot: by('shot'), form: by('form')[0], drift: by('drift'), linger: by('linger')[0], thin: by('thin')[0], fall: by('fall')[0], blob: by('blob') };
      T.state = 'ready'; T.last = performance.now(); A.stats.loaded = (A.stats.loaded || 0) + 1;
    }).catch(e => { T.state = 'bad'; T.err = String(e); });
    return null;
  };
  A.unload = (name) => {
    const T = A.types[name]; if (!T) return; for (const u of T.urls || []) R.dropTex(u);
    for (const k of ['main', 'heat']) { const key = 'atm:' + name + ':' + k + ':' + T.res, c = R.combos[key]; if (c) { c.n = 0; scene.remove(c.mesh); c.geo.dispose(); c.mat.dispose(); delete R.combos[key]; } }
    delete A.types[name];
  };
  A.sweep = () => { const now = performance.now(); const live = new Set([...A.fx.map(f => f.type), ...A.tiles.map(t => t.type)]); for (const nm in A.types) { const T = A.types[nm]; if (T.state === 'ready' && !live.has(nm) && now - T.last > (PH ? 25000 : 90000)) A.unload(nm); } };

  /* ---- lighting: the preset's own day, dusk and night tints, plus the colour of any fire or lamp close by ---- */
  const lightFor = (P) => {
    const k = A.k, L = P.lighting || {}; const d = L.day || { tint: [1, 1, 1], brightness: 1 }, du = L.dusk || d, n = L.night || { tint: [0.5, 0.58, 0.78], brightness: 0.22 };
    const wd = k.day, wn = k.night, wu = Math.max(0, 1 - wd - wn), s = wd + wn + wu || 1; const out = [0, 0, 0];
    for (let i = 0; i < 3; i++) out[i] = (wd * d.tint[i] * d.brightness + wu * du.tint[i] * du.brightness + wn * n.tint[i] * n.brightness) / s * (1 - 0.22 * k.rain);
    return out;
  };
  const addFire = (x, z, y, out) => {                                       // the warm light of the nearest FW fires on a bit of mist or steam
    let n = 0; for (const f of F.alive || []) { if (n >= 5) break; if (f.noLight || !f.vis || f.fade < 0.1 || !f._T) continue; const dx = f.x - x, dz = f.z - z, d2 = dx * dx + dz * dz; const L = f._T.info.light; const rng = Math.max(6, (L && L.range_m || 6) * 1.2); if (d2 > rng * rng) continue; const c = L && L.color || [1, 0.5, 0.1], k = Math.pow(1 - Math.sqrt(d2) / rng, 2) * 1.1 * Math.min(1.2, f.e || 1) * Math.min(1.4, f.F) * f.fade * (0.25 + 0.75 * k_dark()); out[0] += c[0] * k; out[1] += c[1] * k * 0.8; out[2] += c[2] * k * 0.5; n++; }
  };
  const k_dark = () => 1 - A.k.day;

  /* ---- effects: steam jets, bow mist, splashes, hose spray. One list, one frame step. ---- */
  A.capFx = () => PH ? 12 : F.q === 'low' ? 20 : 40;
  A.spawn = (type, x, y, z, o) => {
    o = o || {}; if (F.q === 'off' || !F.ready) return null; A.need(type); if (A.fx.length >= A.capFx()) { let w = null; for (const f of A.fx) if (!w || f.pri < w.pri) w = f; if (w && w.pri < (o.pri || 1)) A.kill(w); else return null; }
    const f = { id: ++A.n, type, x, y, z, sc: o.sc || 1, sx: o.sx || 1, state: o.shot ? 'shot' : 'start', st: 0, vi: (Math.random() * 3) | 0, flip: o.flip || (Math.random() < 0.5 ? -1 : 1), dur: o.dur === undefined ? 3 : o.dur, alpha: o.alpha === undefined ? 1 : o.alpha, q: o.q || 0, yaw: o.yaw || 0, rot: o.rot || 0, follow: o.follow || null, pri: o.pri || 1, own: o.own || null, haze: o.haze !== false, k: 1, kT: 1, dead: false, ph: Math.random() * 3, tint: o.tint || null, hold: false };
    A.fx.push(f); return f;
  }; A.n = 0;
  A.kill = (f) => { f.dead = true; const i = A.fx.indexOf(f); if (i >= 0) A.fx.splice(i, 1); };
  A.stop = (f) => { if (f && !f.dead && f.state !== 'fade' && f.state !== 'shot') { f.state = 'fade'; f.st = 0; f.dur = 0; } };
  F.steam = (type, x, y, z, o) => { const f = A.spawn(type, x, y, z, o); if (f) A.stats.steam++; return f; };
  F.steamAt = (size, x, z, k) => A.spawn(size === 'small' ? 'steam_pipe' : 'steam_burst', x, gnd(x, z) + 0.2, z, { sc: size === 'small' ? (k || 0.6) : (k || 0.4), dur: size === 'small' ? 1.2 : 2.5, pri: 0.5, flip: 1 });
  let burstN = 0;
  const prevExt = F.afterExtinguish;
  F.afterExtinguish = (f) => {
    if (prevExt) prevExt(f); if (F.q === 'off') return; const T = f._T || F.types[f.name], S = f.sc * Math.sqrt(f.F), w = T && T.layers && T.layers.flame ? T.layers.flame.size[0] * S : 2;
    if (A.fx.filter(q => q.type === 'steam_burst' && !q.dead).length >= (PH ? 2 : 4)) return;
    const sc = Math.max(0.12, Math.min(0.9, w / 9)); A.spawn('steam_burst', f.x, f.y + 0.2, f.z, { sc, dur: 1.5 + 2 * sc, pri: 2, flip: 1 }); A.stats.burst = (A.stats.burst || 0) + 1;
  };
  /* lava reaching water: a huge steam column (small at first) */
  F.lavaWet = (x, z) => {
    if (F.q === 'off' || !F.ready) return; A.lavaT = (A.lavaT || 0); if (simT - A.lavaT < 5) return; let water = false, wx0 = 0, wz0 = 0;
    for (let a = 0; a < 8 && !water; a++) { const ang = a * 0.785, px = x + Math.cos(ang) * 3.2, pz = z + Math.sin(ang) * 3.2; if (heightAt(px, pz) < 0.1) { water = true; wx0 = px; wz0 = pz; } }
    if (!water) return; A.lavaT = simT; if (A.fx.filter(q => q.type === 'steam_lava' && !q.dead).length >= 2) return;
    A.spawn('steam_lava', wx0, Math.max(0.05, waveH(wx0, wz0, simT)), wz0, { sc: 0.28, dur: 7, pri: 1.5, flip: 1 });
  };
  F.geyser = (s) => {
    if (F.q === 'off' || !F.ready) return; const f = s._fwg; if (f && !f.dead) { f.dur = Math.max(f.dur, 1.2); return; }
    s._fwg = A.spawn('steam_geyser', s.x, gnd(s.x, s.z) + 0.1, s.z, { sc: 1.8, dur: 2, pri: 1.5, flip: 1 }); if (s._fwg) s._fwg.vis = true;
  };
  /* damaged engines (vehicles, boats) and hot wrecks that have just been put out */
  const engT = { t: 0 };
  A.owners = (dt) => {
    engT.t -= dt; if (engT.t > 0) return; engT.t = 0.5;
    for (const v of BVL) {
      const hot = !v.heli && ((!v.dead && !v.burn && v.hp < v.hpMax * 0.45) || (v.dead && !v.burn && v.wreckT > 14 && v.wreckT < 55 && v._fwNo));
      if (hot && !(v._fwst && !v._fwst.dead)) { if (Math.hypot(v.x - camera.position.x, v.z - camera.position.z) < 120) { const s = Math.sin(v.yaw || 0), c = Math.cos(v.yaw || 0); v._fwst = A.spawn('steam_engine', v.x + s * 1.4, v.y + v.sp.cy * 0.9, v.z + c * 1.4, { sc: 0.9, dur: 9999, pri: 1, follow: (f) => { f.x = v.x + Math.sin(v.yaw || 0) * 1.4; f.y = v.y + v.sp.cy * 0.9; f.z = v.z + Math.cos(v.yaw || 0) * 1.4; if (!BVL.includes(v) || v.burn || !((!v.dead && v.hp < v.hpMax * 0.45) || v.dead)) A.stop(f); } }); } }
    }
    for (const bt of boats) {
      if (bt.sunk || !bt.hpMax) continue; const hot = bt.hp < bt.hpMax * 0.4 && !(bt.fire > 0.05) && bt.sp && bt.sp.kind === 'motor';
      if (hot && !(bt._fwst && !bt._fwst.dead) && Math.hypot(bt.body.position.x - camera.position.x, bt.body.position.z - camera.position.z) < 140) {
        bt._fwst = A.spawn('steam_engine', 0, 0, 0, { sc: Math.max(0.8, (bt.sp.L || 10) / 12), dur: 9999, pri: 1, follow: (f) => { const w = worldOfDeck(bt, -(bt.sp.L || 10) * 0.25, deckLy(bt, 0, 0) + 0.8, 0, _t3); f.x = w.x; f.y = w.y; f.z = w.z; if (bt.sunk || bt.fire > 0.05 || bt.hp >= bt.hpMax * 0.4) A.stop(f); } });
      }
    }
  };
  const _t3 = new THREE.Vector3();
  /* bow mist: a fast boat throws spray at the bow; start, loop while fast, settle when it slows */
  const bowT = { t: 0 };
  A.bows = (dt) => {
    bowT.t -= dt; if (bowT.t > 0) return; bowT.t = 0.25; const cam = camera.position; let n = 0;
    for (const bt of boats) {
      if (bt.sunk || !bt.body) continue; const v = bt.body.velocity, sp = Math.hypot(v.x, v.z), d = Math.hypot(bt.body.position.x - cam.x, bt.body.position.z - cam.z);
      const want = sp > 2.6 && d < (PH ? 70 : 130) && n < (PH ? 2 : 6); const fx = bt._fwbow && !bt._fwbow.dead ? bt._fwbow : null;
      if (want) { n++; if (!fx) { bt._fwbow = A.spawn('mist_bow', 0, 0, 0, { sc: 1, dur: 9999, pri: 1.2, q: 2, haze: false, follow: (f) => bowFollow(bt, f) }); A.stats.bow++; } else { fx.kT = Math.min(1.4, (sp - 2) / 5); } }
      else if (fx && fx.state !== 'fade') A.stop(fx);
    }
  };
  const _q = new THREE.Quaternion(), _fv = new THREE.Vector3();
  function bowFollow(bt, f) {
    const L = bt.sp.L || 10; _fv.set(1, 0, 0).applyQuaternion(bt.group.quaternion); const fxd = _fv.x, fzd = _fv.z, l = Math.hypot(fxd, fzd) || 1; const bx = bt.body.position.x + fxd / l * L * 0.46, bz = bt.body.position.z + fzd / l * L * 0.46;
    f.x = bx; f.z = bz; f.y = waveH(bx, bz, simT) + 0.15; f.yaw = Math.atan2(fzd / l, -fxd / l); f.sc = Math.max(0.45, Math.min(2.6, L / 16)) * Math.min(1.3, f.kT || 1); const sp = Math.hypot(bt.body.velocity.x, bt.body.velocity.z); f.kT = Math.min(1.4, (sp - 2) / 5); if (bt.sunk) A.stop(f);
  }
  /* splashes: baked small, medium and large instead of the old procedural column */
  F.splash = (x, z, y, b) => {
    if (F.q === 'off' || !F.ready || F.legacyUntil) return false; const name = b < 0.8 ? 'splash_small' : b < 2.4 ? 'splash_medium' : 'splash_large', T = A.need(name); if (!T) return false;
    const sc = name === 'splash_small' ? 0.5 + b * 1.1 : name === 'splash_medium' ? Math.max(0.6, b / 1.6) : Math.max(0.4, Math.min(1.4, b / 5)); const f = A.spawn(name, x, y + 0.05, z, { shot: true, sc, pri: 1.5, flip: 1, haze: false });
    if (f) { f.vi = (Math.random() * 3) | 0; A.stats.splash++; } return !!f;
  };
  /* hose and monitor spray: a cone from the nozzle toward the target, held while the jet runs */
  const hoseMap = new WeakMap();
  F.hosePt = (key, fx, fy, fz, tx, ty, tz) => {
    if (F.q === 'off' || !F.ready) return; let f = hoseMap.get(key); const dx = tx - fx, dy = ty - fy, dz = tz - fz, len = Math.hypot(dx, dy, dz) || 1;
    if (!f || f.dead) { f = A.spawn('spray_cone', fx, fy, fz, { sc: 1, dur: 9999, pri: 1.4, q: 1, haze: false }); if (!f) return; hoseMap.set(key, f); f.flip = 1; }
    f.x = fx; f.y = fy; f.z = fz; f.dir = [dx / len, dy / len, dz / len]; f.len = Math.min(len, 38); f.seen = simT; f.sx = Math.max(0.6, Math.min(6, f.len / 5.9));
  };
  F.hose = (bt, tgt) => { if (!bt.ffHead) return; bt.group.updateMatrixWorld(true); const from = bt.ffHead.localToWorld(_t3.set(bt.ffTipX, 0, 0)); const tp = tgt.body.position; F.hosePt(bt, from.x, from.y, from.z, tp.x, tp.y + 1.2, tp.z); };
  /* rain on water */
  let rainS = 0;
  A.rain = (dt) => {
    if (PH || F.q !== 'high' || wx.rainAmt < 0.5) return; rainS -= dt; if (rainS > 0) return; rainS = 0.22 / Math.min(1.5, wx.rainAmt); if (A.fx.length > A.capFx() - 8) return;
    const fc = (typeof lightFocus === 'function') ? lightFocus() : camera.position;
    for (let i = 0; i < 3; i++) { const a = Math.random() * 6.283, r = 4 + Math.random() * 16, x = fc.x + Math.cos(a) * r, z = fc.z + Math.sin(a) * r; if (heightAt(x, z) < 0) { F.splash(x, z, waveH(x, z, simT), 0.12); break; } }
  };

  /* ---- fog: world-anchored tiles of the baked strips, layered with parallax, drifting with the wind; their number follows the Sky Fog control, the time of day and the weather ---- */
  const FOG = {
    mist_dawn: { reach: 110, cap: 22, where: 'water', kind: 'strip' },
    fog_sea: { reach: 200, cap: 12, where: 'water', kind: 'strip' },
    fog_ground: { reach: 90, cap: 22, where: 'low', kind: 'strip' },
    fog_valley: { reach: 260, cap: 8, where: 'valley', kind: 'strip' },
    fog_wisps: { reach: 140, cap: 10, where: 'any', kind: 'strip' },
    fog_forest: { reach: 100, cap: 8, where: 'forest', kind: 'strip' },
    fog_bank: { reach: 380, cap: 3, where: 'bank', kind: 'strip' },
    fog_blobs: { reach: 70, cap: 12, where: 'any', kind: 'blob' },
  };
  A.FOG = FOG;
  const fogScale = () => (PH ? 0.4 : F.q === 'low' ? 0.5 : 1);
  const treeCells = { t: -99, s: new Set() };
  const nearTree = (x, z) => {
    if (simT - treeCells.t > 12) { treeCells.t = simT; treeCells.s.clear(); for (const t of trees) if (!t.dead) treeCells.s.add(Math.round(t.x / 16) * 100000 + Math.round(t.z / 16)); }
    const cx = Math.round(x / 16), cz = Math.round(z / 16); return treeCells.s.has(cx * 100000 + cz);
  };
  const okWhere = (w, x, z) => {
    const h = heightAt(x, z);
    switch (w) { case 'water': return h < -0.1; case 'low': return h > 0.4 && h < 10; case 'valley': return h > 0.4 && h < 7; case 'forest': return h > 1.5 && nearTree(x, z); case 'bank': return h < -0.1; default: return true; }
  };
  /* what fraction of the fog types is wanted now: the Sky control, dawn mist, valley fog, rain, calm air */
  A.climate = () => {
    const e = tod.e, k = A.k, ws = F.windMs; k.rain = clamp01(wx.rainAmt);
    k.day = sm(6, 20, e); k.night = 1 - sm(-8, 2, e); k.fogSky = [0, 0.5, 1][Math.max(0, Math.min(2, wx.fog | 0))];
    const calm = 1 - clamp01((ws - 1) / 6); k.calm = calm;
    k.dawn = tod.am ? sm(-8, -1, e) * (1 - sm(4, 14, e)) : 0;                                         // mist over the water as the sun comes up, burning off by mid morning
    k.valley = Math.max(k.night * 0.5, k.dawn) * calm;                                               // valley fog pools on still nights and early mornings
    k.damp = Math.max(k.rain * 0.7, k.fogSky * 0.6, k.dawn * 0.5);
    A.want = { mist_dawn: clamp01(k.dawn * (0.4 + 0.6 * calm) + k.fogSky * 0.3), fog_sea: clamp01(k.fogSky * (k.fogSky > 0.4 ? 1 : 0) + k.dawn * 0.15), fog_ground: clamp01(k.fogSky * 0.85 + k.valley * 0.45 + k.rain * 0.12), fog_valley: clamp01(k.valley * 0.9 + k.fogSky * 0.35), fog_wisps: clamp01(k.fogSky * 0.7 + k.rain * 0.25 + k.dawn * 0.25), fog_forest: clamp01(k.damp * 0.8), fog_bank: k.fogSky > 0.9 ? 1 : 0, fog_blobs: clamp01(k.fogSky * 0.7 + k.valley * 0.2) };
    if (F.q === 'low') { A.want.fog_forest = 0; A.want.fog_blobs = 0; A.want.fog_wisps *= 0.5; }
  };
  let tileId = 0;
  const poolOf = (type) => A.tiles.filter(t => t.type === type);
  function newTile(type, T, D, fc) {
    const P = T.P, heights = (P.game && P.game.layer_heights_m) || [0], scroll = (P.game && P.game.wind && P.game.wind.scroll_factor) || [1];
    for (let tries = 0; tries < 8; tries++) {
      let x, z; if (D.where === 'bank') { const a = Math.random() * 6.283, r = 220 + Math.random() * 140; x = fc.x + Math.cos(a) * r; z = fc.z + Math.sin(a) * r; } else { const a = Math.random() * 6.283, r = D.reach * Math.sqrt(0.04 + 0.96 * Math.random()); x = fc.x + Math.cos(a) * r; z = fc.z + Math.sin(a) * r; }
      if (!okWhere(D.where, x, z)) continue;
      const k = (Math.random() * heights.length) | 0; return { id: ++tileId, type, x, z, lay: k, hgt: heights[k] || 0, scr: scroll[Math.min(k, scroll.length - 1)], age: 0, ph: Math.random() * 4, vi: (Math.random() * 2) | 0, flip: Math.random() < 0.5 ? -1 : 1, a: 0, aT: 1, th: Math.random(), phase: 'form', dying: false, blob: (Math.random() * 6) | 0, sc: D.kind === 'blob' ? 0.8 + Math.random() * 1.8 : 1, y: 0, d: 0 };
    }
    return null;
  }
  let fogT = 0;
  A.fogStep = (dt) => {
    if (F.q === 'off') { A.tiles.length = 0; return; } A.climate(); const fc = camera.position, ws = F.wind, scale = fogScale();
    fogT -= dt; const doSpawn = fogT <= 0; if (doSpawn) fogT = 0.4;
    for (const type in FOG) {
      const D = FOG[type]; const want = (A.want[type] || 0), tgtN = Math.round(D.cap * scale * want);
      if (want <= 0.02 && !A.tiles.some(t => t.type === type)) continue; const T = A.need(type); if (!T) continue;
      const pool = poolOf(type);
      if (doSpawn) {
        const live = pool.filter(t => !t.dying);
        if (live.length < tgtN) { const t = newTile(type, T, D, fc); if (t) A.tiles.push(t); }
        // thin: as the wanted amount falls, tiles with a high threshold begin to thin and fall (each ends in its own time)
        for (const t of live) if (t.th > want + 0.08 && !t.dying) { t.dying = true; t.phase = T.clips.thin ? 'thin' : 'fall'; t.age2 = 0; }
        if (live.length > tgtN + 2) { const t = live[(Math.random() * live.length) | 0]; if (t && !t.dying) { t.dying = true; t.phase = 'thin'; t.age2 = 0; } }
      }
    }
    const uref = (T) => (T.P.fog && T.P.fog.u_ref_mps) || 0, wl = Math.hypot(ws.x, ws.z) || 1, wux = ws.x / wl, wuz = ws.z / wl;
    for (let i = A.tiles.length - 1; i >= 0; i--) {
      const t = A.tiles[i], T = A.types[t.type], D = FOG[t.type]; if (!T || T.state !== 'ready') { t.age += dt; continue; }
      t.age += dt; const sp = t.scr * F.windMs + uref(T) * 0.5; t.x += wux * sp * dt; t.z += wuz * sp * dt;
      const dx = t.x - fc.x, dz = t.z - fc.z, d = Math.hypot(dx, dz); t.d = d;
      if (d > D.reach * 1.18 && D.where !== 'bank' || (D.where === 'bank' && d > 420)) { A.tiles.splice(i, 1); continue; }
      if (t.dying) { t.age2 += dt; const tc = t.phase === 'thin' ? T.clips.thin : T.clips.fall; const dur = tc ? tc.count / tc.fps : 3; if (t.phase === 'thin' && t.age2 > dur) { t.phase = 'fall'; t.age2 = 0; } else if (t.phase === 'fall' && t.age2 > (T.clips.fall ? T.clips.fall.count / T.clips.fall.fps : 3) + 1.5) { A.tiles.splice(i, 1); continue; } }
      const fadeIn = Math.min(1, t.age / 3.5), edge = 1 - sm(0.78, 1.0, d / D.reach), near = 1;
      const dyingA = t.dying ? Math.max(0, 1 - (t.age2 / ((t.phase === 'thin' ? (T.clips.thin ? T.clips.thin.count / T.clips.thin.fps : 3) : 3) + (T.clips.fall ? T.clips.fall.count / T.clips.fall.fps : 3))) * 1.0) : 1;
      t.a = fadeIn * edge * dyingA * (0.4 + 0.6 * Math.max(A.want[t.type] || 0, 0.3));
      if (!okWhere(D.where, t.x, t.z) && D.where !== 'any') t.a *= 0.0;
      const onW = heightAt(t.x, t.z) < 0; t.y = (onW ? waveH(t.x, t.z, simT) : gnd(t.x, t.z)) + t.hgt;
    }
    A.stats.tiles = A.tiles.length;
  };
  A.drawTiles = () => {
    const cam = camera.position, list = A.tiles.filter(t => t.a > 0.01).sort((a, b) => b.d - a.d), lw = F.windMs; let n = 0;
    for (const t of list) {
      const T = A.types[t.type]; if (!T || T.state !== 'ready') continue; const LY = T.layers.main; if (!LY) continue; const P = T.P, D = FOG[t.type];
      let clip, loop = true, tm = t.age + t.ph;
      if (D.kind === 'blob') clip = T.clips.blob[t.blob % T.clips.blob.length];
      else if (t.dying) { clip = t.phase === 'thin' ? T.clips.thin : T.clips.fall; tm = t.age2; loop = false; if (!clip) clip = T.clips.drift[0]; }
      else if (t.age < (T.clips.form ? T.clips.form.count / T.clips.form.fps : 0)) { clip = T.clips.form; tm = t.age; loop = false; }
      else clip = T.clips.drift[t.vi % T.clips.drift.length] || T.clips.linger;
      if (!clip) continue; const fr = F.frameOf(clip, tm, loop, true), lit = lightFor(P); const col = [lit[0], lit[1], lit[2]]; addFire(t.x, t.z, t.y, col);
      const w = LY.size[0] * t.sc, h = LY.size[1] * t.sc;
      R.push(LY.combo, t.x, t.y - 0.07 * h, t.z, w, h, fr[0], fr[1], fr[2], Math.min(1, t.a) * (D.kind === 'blob' ? 0.8 : 0.9), t.flip, 0, 0, 1, col[0], col[1], col[2], 0, 0, 0);
      const H = T.layers.heat; if (H && false) { }
      n++;
    }
    A.stats.drawn = n;
  };
  /* ---- stepping and drawing the effects ---- */
  const _o = {};
  A.step = (dt) => {
    const cam = camera.position, wl = F.wind, ws = F.windMs;
    for (let i = A.fx.length - 1; i >= 0; i--) {
      const f = A.fx[i]; const T = A.types[f.type]; if (!T || T.state !== 'ready') { if (T && T.state === 'bad') { A.kill(f); } continue; }
      if (f.follow) f.follow(f); if (f.dead) continue; f.st += dt; const C = T.clips;
      if (f.seen !== undefined && simT - f.seen > 0.35 && f.state !== 'fade') A.stop(f);                       // a hose that is no longer refreshed settles
      if (f.state === 'start') { if (!C.start || f.st >= C.start.duration_s) { f.state = 'loop'; f.st = 0; } }
      else if (f.state === 'loop') { if (f.dur < 9000) { f.dur -= dt; if (f.dur <= 0) { f.state = C.fade ? 'fade' : 'dead'; f.st = 0; } } const lc = C.loop[f.vi % C.loop.length]; if (lc && f.st >= lc.duration_s) f.st -= lc.duration_s; }
      else if (f.state === 'fade') { if (!C.fade || f.st >= C.fade.duration_s) { A.kill(f); continue; } }
      else if (f.state === 'shot') { const sc = C.shot[f.vi % C.shot.length]; if (!sc || f.st >= sc.duration_s) { A.kill(f); continue; } }
      else if (f.state === 'dead') { A.kill(f); continue; }
      const d = Math.hypot(f.x - cam.x, f.z - cam.z); if (d > 260) continue;
      let clip, loop = false; const st = f.state;
      clip = st === 'start' ? C.start : st === 'loop' ? C.loop[f.vi % C.loop.length] : st === 'fade' ? C.fade : C.shot[f.vi % C.shot.length]; loop = st === 'loop'; if (!clip) continue;
      const LY = T.layers.main; if (!LY) continue; const P = T.P, S = f.sc, lit = lightFor(P); const col = [lit[0], lit[1], lit[2]]; addFire(f.x, f.z, f.y, col);
      const w = LY.size[0] * S * f.sx, h = LY.size[1] * S; const wg = P.game && P.game.wind || {}; const lean = Math.min(wg.max_lean_deg || 45, (wg.lean_deg_per_mps || 5) * ws) * 0.01745, off = Math.tan(Math.min(1.2, lean)) * h * (wg.drift_top || 0.8) * 0.5;
      const lx = ws > 0.05 ? wl.x / ws * off : 0, lz = ws > 0.05 ? wl.z / ws * off : 0; const fr = F.frameOf(clip, f.st, loop, true);
      let al = f.alpha * (st === 'loop' ? Math.min(1, f.k * 1) : 1) * Math.min(1, Math.max(0.15, f.kT));
      if (f.state === 'fade' && f.type === 'mist_bow') al *= 1;
      let q = f.q, rot = f.rot, yaw = f.yaw;
      if (f.type === 'spray_cone' && f.dir) { camera.getWorldDirection(_cd); _cr.crossVectors(_cd, _up).normalize(); _cu.crossVectors(_cr, _cd).normalize(); const vr = f.dir[0] * _cr.x + f.dir[1] * _cr.y + f.dir[2] * _cr.z, vu = f.dir[0] * _cu.x + f.dir[1] * _cu.y + f.dir[2] * _cu.z; q = 1; rot = Math.atan2(vu, vr); }
      R.push(LY.combo, f.x, f.y, f.z, w, h, fr[0], fr[1], fr[2], Math.min(1, al), f.flip, q, q === 2 ? yaw : rot, 1, col[0], col[1], col[2], 0, f.type === 'spray_cone' || f.type === 'mist_bow' ? 0 : lx, f.type === 'spray_cone' || f.type === 'mist_bow' ? 0 : lz);
      const H = T.layers.heat, hc = clip; if (H) { const fr2 = F.frameOf(hc, f.st, loop, true); R.push(H.combo, f.x, f.y, f.z, H.size[0] * S * f.sx, H.size[1] * S, fr2[0], fr2[1], fr2[2], Math.min(1, al), f.flip, q, q === 2 ? yaw : rot, 1, 1, 1, 1, 0, lx, lz); }
      // the hot gas above a steam source bends the air (descriptor from the preset)
      if (f.haze && P.haze && DIST.live && st !== 'shot') { const H0 = P.haze, k = Math.min(1, H0.strength * Math.min(1, al) * (st === 'start' ? Math.min(1, f.st / (C.start ? C.start.duration_s : 1)) : 1)); if (k > 0.04) DIST.haze(DIST.idOf(f), f.x, f.y + 0.3 + ((simT * (H0.rise_speed_mps || 0.3)) % 1), f.z, k, Math.max(0.6, H0.height_m * S), Math.max(0.3, H0.radius_m * S)); }
    }
  };
  const _cd = new THREE.Vector3(), _cr = new THREE.Vector3(), _cu = new THREE.Vector3(), _up = new THREE.Vector3(0, 1, 0);
  F.afters.push((dt) => {
    if (F.q === 'off' || F.legacyUntil) return; if (!A.json) { A.ensure(); return; }
    try { A.owners(dt); A.bows(dt); A.rain(dt); A.fogStep(dt); A.step(dt); A.drawTiles(); A.sweepT = (A.sweepT || 0) + dt; if (A.sweepT > 6) { A.sweepT = 0; A.sweep(); } } catch (e) { A.err = String(e && e.stack || e); }
  });
/* a world reset (battle stop, calm): every sprite effect goes, the owners start clean */
  F.reset = () => {
    for (const f of F.fires.slice()) F.kill(f, true); if (F.G) { F.G.fronts.length = 0; F.G.spots.length = 0; F.G.bld.length = 0; } if (F.A) { F.A.fx.length = 0; } if (F.P) F.P.list.length = 0; for (const t of burning) t._fw = null; for (const h of HEATP) h._fws = null;
  };
})();
/*FW-END part3*/
