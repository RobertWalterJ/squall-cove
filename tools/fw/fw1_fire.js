/*FW-START part1b: fire types, lifecycle machine, drawing, lights, haze*/
(() => {
  const F = FW, R = F.R, PH = ED.phone;
  const S0 = 1e-6;
  /* ---- types: loaded lazily, one at a time, on the first fire that needs them ---- */
  const resWant = () => (PH || F.q === 'low') ? 'low' : 'full';
  const LAYERS = ['flame', 'smoke', 'heat'];
  const ORDER = { smoke: 6.2, flame: 6.3, heat: 6.4 };
  F.need = (name) => {
    const now = performance.now(); let T = F.types[name]; const res = resWant();
    if (T && T.state === 'ready' && T.res === res) { T.last = now; return T; }
    if (T && (T.state === 'loading' || T.state === 'bad')) return null;
    if (!F.atlas) { F.ensureAtlas(); return null; }
    const info = F.atlas.presets[name]; if (!info) { F.types[name] = { name, state: 'bad' }; return null; }
    if (T && T.state === 'ready') F.unload(name);
    T = F.types[name] = { name, info, state: 'loading', res, last: now, urls: [] };
    const jobs = LAYERS.filter(k => info.layers[k]).map(k => {
      const L = info.layers[k], use = (res === 'low' && L.low) ? L.low : L, url = 'assets/fire/' + use.file; T.urls.push(url);
      return R.loadTex(url).then(tex => ({ k, L, use, tex }));
    });
    Promise.all(jobs).then(got => {
      T.layers = {};
      for (const g of got) {
        const key = 'fire:' + name + ':' + g.k + ':' + res, fwid = g.use.frame_px[0], fhid = g.use.frame_px[1];
        const combo = R.combo({ key, tex: g.tex, cols: g.use.cols, rows: g.use.rows, fw: fwid, fh: fhid, anchor: g.L.anchor, mode: g.k === 'flame' ? 0 : g.k === 'smoke' ? 1 : 2, order: ORDER[g.k], rule: g.k === 'heat' ? 'heat' : 'vis', edge: info.kind === 'tile' ? 0.24 : 0 });
        T.layers[g.k] = { combo, size: g.L.size_m, anchor: g.L.anchor };
      }
      const cl = info.clips, by = (st) => cl.filter(c => c.stage === st);
      T.clips = { ignite: by('ignite')[0], growth: by('growth')[0], decay: by('decay')[0], extinguish: by('extinguish')[0], loop: by('loop'), fireball: by('fireball'), plume: by('plume'), residue: by('residue'), shot: by('shot') };
      T.kind = info.kind; T.state = 'ready'; T.last = performance.now(); F.stats.typesLoaded = (F.stats.typesLoaded || 0) + 1;
    }).catch(e => { T.state = 'bad'; T.err = String(e); });
    return null;
  };
  F.unload = (name) => {
    const T = F.types[name]; if (!T) return; for (const u of T.urls || []) R.dropTex(u);
    for (const k of LAYERS) { const key = 'fire:' + name + ':' + k + ':' + T.res, c = R.combos[key]; if (c) { c.n = 0; c.mesh.visible = false; scene.remove(c.mesh); c.geo.dispose(); c.mat.dispose(); delete R.combos[key]; } }
    delete F.types[name];
  };
  F.sweepTypes = () => {                                              // drop a type's textures when nothing of that type has burned for a while
    const now = performance.now(); const live = new Set(F.fires.map(f => f.name)); for (const nm in F.types) { const T = F.types[nm]; if (T.state === 'ready' && !live.has(nm) && now - T.last > (PH ? 25000 : 90000)) F.unload(nm); }
  };

  /* ---- a fire ---- */
  let idN = 1;
  const KIND_FLAME_ADD = 0.55;
  const BIG = new Set(['pool', 'vehicle', 'building', 'tree_crown', 'oil_slick', 'boat_deck', 'roof', 'vehicle_small']);
  const BLACK = new Set(['pool', 'vehicle', 'oil_slick', 'boat_deck', 'vehicle_small', 'vehicle_engine', 'barrel', 'blast_fuel']);   // heavy black smoke: also get a drifting soot column when big enough
  F.isBlack = (n) => BLACK.has(n);
  /* spawn: type name, world position (base of the flame), options */
  F.spawn = (name, x, y, z, o) => {
    o = o || {}; if (F.q === 'off') return null; const cap = F.cap();
    if (F.fires.length >= cap.fires * 2 + 20) { let w = null; for (const f of F.fires) if (!w || f.pri < w.pri) w = f; if (w && w.pri < (o.pri || 1)) F.kill(w, true); else return null; }
    const f = { id: idN++, name, x, y, z, F: o.F || 1, sc: o.sc || 1, own: o.own || null, dur: o.dur === undefined ? Infinity : o.dur, state: o.state || 'ignite', st: 0, vi: (Math.random() * 3) | 0, flip: Math.random() < 0.5 ? -1 : 1, ph: Math.random() * 3, hit: 0, age: 0, pri: o.pri || 1, yaw: o.yaw !== undefined ? o.yaw : Math.random() * 6.283, quads: o.quads, fade: 1, vis: false, follow: o.follow || null, dead: false, mode: o.mode || null, drift: o.drift, aux: o.aux || null, black: o.black, noLight: !!o.noLight, noSmoke: !!o.noSmoke, ext: false, lean: 0, px: 0, e: 1, sndKey: null };
    if (o.age0) { f.state = o.state || 'grow'; f.st = o.age0; }
    f.start = o.start || null;
    if (f.own && f.own.ref && !f.own.multi) f.own.ref._fw = f;
    F.fires.push(f); F.need(name); F.stats.spawned = (F.stats.spawned || 0) + 1; return f;
  };
  F.kill = (f, now) => {
    if (f.dead) return; if (!now && f.state !== 'out') { f.state = 'out'; f.st = 0; }
    f.dead = true; if (f.own && f.own.ref && !f.own.multi && f.own.ref._fw === f) f.own.ref._fw = null; if (f.onDone) { try { f.onDone(f); } catch (e) { } }
    const i = F.fires.indexOf(f); if (i >= 0) F.fires.splice(i, 1); F.stats.ended = (F.stats.ended || 0) + 1;
  };
  F.extinguish = (f) => {
    if (!f || f.dead || f.state === 'extinguish' || f.state === 'out') return false;
    const T = F.types[f.name]; f.ext = true; f.state = 'extinguish'; f.st = 0; F.stats.extinguished = (F.stats.extinguished || 0) + 1;
    if (T && T.clips && !T.clips.extinguish) { f.state = 'out'; }
    if (F.onExtinguish) F.onExtinguish(f); return true;
  };
  F.drawn = (o) => !!(o && o._fw && o._fw.vis && F.q !== 'off');
  F.drawnFor = (o) => o && o._fw;                                      // exists (even if still loading)
  const clipDur = (c) => c ? c.duration_s : 0;
  const lenOf = (f, T) => { const c = T.clips; return { ig: clipDur(c.ignite), gr: clipDur(c.growth), de: clipDur(c.decay), ex: clipDur(c.extinguish) }; };
  /* advance one fire's state machine. Returns nothing; sets f.clip (the clip being played) and f.clipT (seconds into it) */
  function step(f, dt, T) {
    const C = T.clips; f.age += dt; f.st += dt;
    if (f.follow) f.follow(f);
    if (f.state === 'ignite') { if (!C.ignite) { f.state = C.growth ? 'grow' : 'burn'; f.st = 0; } else if (f.st >= C.ignite.duration_s) { f.st -= C.ignite.duration_s; f.state = C.growth ? 'grow' : 'burn'; if (f.state === 'burn') f.st = Math.random() * 1; } }
    if (f.state === 'grow') { if (!C.growth) { f.state = 'burn'; f.st = 0; } else if (f.st >= C.growth.duration_s) { f.st -= C.growth.duration_s; f.state = 'burn'; } }
    if (f.state === 'burn') {
      if (Number.isFinite(f.dur)) f.dur -= dt;
      const L = C.loop[f.vi] || C.loop[0], ld = L ? L.duration_s / Math.max(0.5, 0.8 + 0.2 * f.F) : 1;
      if (f.st >= ld) { f.st -= ld; if (C.loop.length > 1) f.vi = (f.vi + 1 + ((Math.random() * (C.loop.length - 1)) | 0)) % C.loop.length; f.flip = Math.random() < 0.5 ? -1 : 1; }
      const dl = C.decay ? C.decay.duration_s : 0;
      if (f.dur <= dl && !f.own) { if (C.decay) { f.state = 'decay'; f.st = 0; } else { f.state = 'out'; f.st = 0; } }
      else if (f.own && f.own.endIn && f.own.endIn(f) <= dl) { if (C.decay) { f.state = 'decay'; f.st = 0; } else { f.state = 'out'; f.st = 0; } }
    }
    if (f.state === 'decay') { if (!C.decay || f.st >= C.decay.duration_s) { f.state = 'out'; f.st = 0; } }
    if (f.state === 'extinguish') { if (f.st >= clipDur(C.extinguish) + 0.3) { f.state = 'out'; f.st = 0; } }
    if (f.state === 'fireball') { const L = C.fireball[f.vi % C.fireball.length]; if (f.st >= L.duration_s) { f.state = 'plume'; f.st = 0; } }
    if (f.state === 'plume') { const L = C.plume[f.vi % C.plume.length]; if (f.st >= L.duration_s) { f.state = 'residue'; f.st = 0; } }
    if (f.state === 'residue') { if (Number.isFinite(f.dur)) f.dur -= dt; const L = C.residue[f.vi % C.residue.length]; if (f.st >= L.duration_s) f.st -= L.duration_s; if (f.dur <= 0) { f.state = 'out'; f.st = 0; f.fadeOut = 2.0; } }
    if (f.state === 'shot') { const L = C.shot[f.vi % C.shot.length]; if (f.st >= L.duration_s) { f.state = 'out'; f.st = 0; } }
    if (f.state === 'out') { f.fadeOut = (f.fadeOut === undefined ? 0 : f.fadeOut); f.fade = f.fadeOut > 0 ? Math.max(0, 1 - f.st / f.fadeOut) : 0; if (f.fade <= 0.01) { F.kill(f, true); return false; } }
    return true;
  }
  const clipFor = (f, T) => {
    const C = T.clips;
    switch (f.state) {
      case 'ignite': return C.ignite; case 'grow': return C.growth; case 'burn': return C.loop[f.vi] || C.loop[0];
      case 'decay': return C.decay; case 'extinguish': return C.extinguish;
      case 'fireball': return C.fireball[f.vi % C.fireball.length]; case 'plume': return C.plume[f.vi % C.plume.length];
      case 'residue': case 'out': return f.lastClip || (C.residue[f.vi % (C.residue.length || 1)] || C.loop[f.vi] || C.loop[0]);
      case 'shot': return C.shot[f.vi % C.shot.length];
    } return C.loop[0];
  };
  const _fr = [0, 0, 0];
  function frameOf(c, t, loop, blend) {
    let x = t * c.fps; if (loop) x = ((x % c.count) + c.count) % c.count; else x = Math.min(Math.max(x, 0), c.count - 1);
    const i = Math.floor(x), fr = x - i; let j = i + 1; if (j >= c.count) j = loop ? 0 : c.count - 1;
    _fr[0] = c.first + i; _fr[1] = c.first + j; _fr[2] = (blend || c.fps < 16) ? fr : 0; return _fr;
  }
  F.frameOf = frameOf;
  const isLoopState = (s) => s === 'burn' || s === 'residue' || s === 'out';
  /* ---- per-frame: update, sort, draw ---- */
  const amb = { r: 1, g: 1, b: 1, day: 1 };
  F.amb = amb;
  function updateAmb() {
    const e = tod.e, d = Math.max(0, Math.min(1, (e + 4) / 16)), dk = 1 - d;
    amb.day = d; const wet = Math.min(1, wx.rainAmt * 0.6 + wx.fog * 0.1);
    amb.r = (0.13 + 0.87 * d) * (1 - 0.1 * wet) + 0.02 * dk; amb.g = (0.15 + 0.85 * d) * (1 - 0.08 * wet); amb.b = (0.20 + 0.80 * d) * (1 - 0.05 * wet);
  }
  const _cam = new THREE.Vector3();
  let Kpx = 800;
  /* push the layers of one clip frame as instances. o: { q (quad mode 0..3), rot, stretch, add, noSmoke, cross (2 crossed flame quads with yaw), yaw, loop, blend, lean (0..1 plume lean), warm, tint [r,g,b] for smoke } */
  F.pushClip = (T, clip, t, x, y, z, S, sx, sy, alpha, flip, o) => {
    const wl = F.wind, lk = Math.min(1, F.windMs * 0.09) * (o.lean === undefined ? 1 : o.lean), loop = !!o.loop, blend = !!o.blend, fire = o.fire;
    for (let li = 0; li < 3; li++) {
      const lay = li === 0 ? 'smoke' : li === 1 ? 'flame' : 'heat', LY = T.layers[lay], c = clip[lay]; if (!LY || !c) continue; if (lay === 'smoke' && o.noSmoke) continue;
      const fr = frameOf(c, t, loop, blend), w = LY.size[0] * S * sx, h = LY.size[1] * S * sy;
      const add = lay === 'flame' ? (o.add !== undefined ? o.add : KIND_FLAME_ADD) : 0; let r = 1, g = 1, b = 1;
      if (lay === 'smoke') { r = amb.r; g = amb.g; b = amb.b; if (o.warm) r += o.warm * 0.2; }
      const lx = wl.x * lk * h * (lay === 'smoke' ? 0.55 : 0.18), lz = wl.z * lk * h * (lay === 'smoke' ? 0.55 : 0.18);
      if (lay === 'flame' && o.cross) {
        const fa = fr[0], fb = fr[1], fm = fr[2];
        R.push(LY.combo, x, y, z, w, h, fa, fb, fm, alpha, flip, 2, o.yaw, o.stretch || 1, r, g, b, add, lx, lz);
        const fr2 = frameOf(c, t + 0.37, loop, true); R.push(LY.combo, x, y, z, w, h, fr2[0], fr2[1], fr2[2], alpha * 0.85, -flip, 2, o.yaw + 1.5708, o.stretch || 1, r, g, b, add, lx, lz);
      } else R.push(LY.combo, x, y, z, w, h, fr[0], fr[1], fr[2], alpha, flip, o.q || 0, o.rot || 0, o.stretch || 1, r, g, b, add, lx, lz);
      if (fire && lay === 'flame') { fire.fi = fr[0] - c.first; fire.fc = c.count; }
    }
  };
  const _o = { q: 0, rot: 0, stretch: 1, loop: false, blend: false, cross: false, yaw: 0, noSmoke: false, fire: null, warm: 0 };
  function drawFire(f, T, rank, animated) {
    const clip = clipFor(f, T); if (!clip) return; if (f.state !== 'out') f.lastClip = clip; f.cn = clip.name;
    const S = f.sc * Math.sqrt(f.F), loopish = isLoopState(f.state), spd = (f.state === 'burn' ? 0.8 + 0.2 * f.F : 1);
    const t = animated ? f.st * spd : f.ph, al = f.fade * (f.alphaK === undefined ? 1 : f.alphaK);
    _o.q = 0; _o.rot = 0; _o.stretch = 1; _o.loop = loopish && f.state !== 'out' ? true : false; _o.blend = F.q === 'high'; _o.cross = (f.quads || 1) > 1 && F.q === 'high' && animated; _o.yaw = f.yaw;
    _o.noSmoke = !!f.noSmoke || (!animated && f.px < 10); _o.fire = f; _o.warm = f.warm || 0; _o.add = f.add; _o.lean = f.lean === undefined || f.lean === 0 ? 1 : f.lean;
    F.pushClip(T, clip, t, f.x, f.y, f.z, S, f.sx || 1, f.sy || 1, al, f.flip, _o);
    if (f.black && !f.noSmoke && F.q === 'high' && f.px > 40 && (f.F > 0.7)) F.soot && F.soot(f, al);
  }
  F.wind = { x: 0, z: 0 }; F.windMs = 0;
  const _v = new THREE.Vector3();
  let emaDt = 0.016, slowT = 0, lastSweep = 0;
  /* lights / haze scratch */
  F.energy = (f, T) => {
    const L = T.info.light; if (!L) return 1; const st = f.state; let arr = null, i = f.fi || 0; const cn = f.lastClip && f.lastClip.name;
    if (st === 'burn' || (st === 'residue' && !(L.stage_energy && L.stage_energy[cn]))) arr = L.flicker; else if (L.stage_energy) arr = L.stage_energy[cn] || L.stage_energy[st === 'grow' ? 'growth' : st];
    if (!arr || !arr.length) return st === 'out' ? 0 : 1; const clip = clipFor(f, T); const c = clip && clip.flame; const cnt = c ? c.count : arr.length;
    const fr = c ? Math.min(cnt - 1, Math.floor(f.st * c.fps)) : 0; const j = Math.min(arr.length - 1, Math.floor(fr * arr.length / cnt));
    let e = arr[j]; if (st === 'burn' || st === 'residue') e = e; return e;
  };
  F.frame = (dt) => {
    dt = Math.min(dt, 0.1);
    F.q = F.eff();
    if (F.q === 'off') { if (F.fires.length) for (const f of F.fires.slice()) F.kill(f, true); R.begin(); R.end(); if (F.lightsFx) { try { F.lightsFx(dt); } catch (e) { } } return; }
    // wind (m/s): the game's wind vector
    F.wind.x = wind.v.x; F.wind.z = wind.v.z; F.windMs = Math.hypot(wind.v.x, wind.v.z);
    updateAmb();
    // the smoothness governor: slow frames step the quality down, the old particles take over for a while after that
    if (GOV.perf !== 'best') { emaDt += (dt - emaDt) * 0.06; if (emaDt > 0.05 && F.fires.length > 4) { slowT += dt; if (slowT > 4) { slowT = 0; if (F.q === 'high') { F.govLow = true; F.q = F.eff(); } else if (!F.legacyUntil) { F.legacyUntil = performance.now() + 25000; } } } else slowT = Math.max(0, slowT - dt); }
    if (F.legacyUntil && performance.now() > F.legacyUntil) { F.legacyUntil = 0; emaDt = 0.016; }
    R.begin();
    const cam = camera.position; Kpx = innerHeight * renderer.getPixelRatio() / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
    const cap = F.cap(); const fq = fxPos();
    const alive = [];
    for (const f of F.fires.slice()) {
      const T = F.types[f.name]; if (!T || T.state !== 'ready') { if (!T || T.state === 'bad') { F.need(f.name); if (T && T.state === 'bad') { F.kill(f, true); } } f.vis = false; f.age += dt; if (f.own && f.own.sync) f.own.sync(f); continue; }
      T.last = performance.now();
      if (f.own && f.own.sync) f.own.sync(f);
      if (f.dead) continue;
      if (!step(f, dt, T)) continue;
      const dx = f.x - cam.x, dy = f.y - cam.y, dz = f.z - cam.z, d = Math.hypot(dx, dy, dz); f._d = d;
      const ls = T.layers.flame || T.layers.smoke; const hh = ls ? ls.size[1] * f.sc * Math.sqrt(f.F) : 1; f.px = hh * Kpx / Math.max(d, 1);
      f._T = T; alive.push(f);
    }
    alive.sort((a, b) => b._d - a._d);                                  // far to near
    // who is fully animated: the biggest on screen first
    const rank = alive.slice().sort((a, b) => b.px - a.px); let nAnim = 0; for (const f of rank) { f._anim = (nAnim < cap.fires && f.px >= 14) ? (nAnim++, true) : false; }
    for (const f of alive) {
      if (f.px < 2.5 || F.legacyUntil) { f.vis = false; continue; }                          // too small to matter: culled
      const ang = Math.atan2(f.x - cam.x, f.z - cam.z); if (Math.abs(((ang - cameraYaw() + 9.4248) % 6.2832) - 3.1416) > 2.2 && f._d > 12 && f.px < 60) { f.vis = true; continue; }   // far outside the view: kept alive, not drawn
      f.vis = true; drawFire(f, f._T, 0, f._anim);
    }
    F.sweepNow = (F.sweepNow || 0) + dt; if (F.sweepNow > 5) { F.sweepNow = 0; F.sweepTypes(); }
    for (const fn of F.afters) fn(dt, alive);
    R.end();
    F.alive = alive;
    F.stats.n = F.fires.length; F.stats.anim = nAnim;
  };
  const _fw = new THREE.Vector3();
  function cameraYaw() { camera.getWorldDirection(_fw); return Math.atan2(_fw.x, _fw.z); }
  /* ---- lights: warm flickering point lights through the game's light budget ---- */
  F.lights = (dt) => {
    if (F.q === 'off' || F.legacyUntil) return 0; const dk = LIGHT.dark; if (dk < 0.05) return 0;
    const fc = lightFocus(); const mx = PH ? 4 : 10; let n = 0; const list = [];
    for (const f of F.alive || []) { if (f.noLight || !f.vis || f.fade < 0.05) continue; const T = f._T; const L = T.info.light; if (!L) continue; const dx = f.x - fc.x, dz = f.z - fc.z; const d2 = dx * dx + dz * dz; const rng = Math.min(F.q === 'high' ? 90 : 60, Math.max(7, L.range_m * 1.5)); if (d2 > 160 * 160) continue; f._ls = f.F * Math.pow(Math.max(0.3, L.intensity_vs_campfire || 1), 0.6) / (d2 + 400); list.push(f); }
    list.sort((a, b) => b._ls - a._ls);
    for (const f of list) {
      if (n >= mx) break; const T = f._T, L = T.info.light, e = Math.max(0, F.energy(f, T)); f.e = e; const rng = Math.max(7, Math.min(T.kind === 'blast' ? 110 : 60, L.range_m * 1.5));
      const col = L.color || [1, 0.5, 0.1], I = Math.min(900, 260 * Math.pow(Math.max(0.3, L.intensity_vs_campfire || 1), 0.6) * Math.pow(f.F, 0.8) * (0.25 + 0.75 * Math.min(1.5, e))) * f.fade;
      const cy = f.y + Math.min(6, (T.layers.flame ? T.layers.flame.size[1] : 2) * f.sc * 0.35);
      lightWant('fw' + f.id, 'point', f.x, cy, f.z, col[0], col[1] * (0.85 + 0.15 * Math.min(1, e)), col[2], I, rng, 1.3, { glow: 0, pool: Math.min(rng * 0.25, 9), fl: Math.min(1.3, e), k: dk * f.fade }); n++;
    }
    // far or tiny fires: no animation and no real light, a glow sprite only (the game draws these for lights within about 260 m)
    let g = 0; for (const f of F.alive || []) { if (g >= (PH ? 3 : 8)) break; if (f.noLight || f.fade < 0.1 || !f._T || f.px >= 14 || f._d < 40 || f._d > 600 || f.F < 0.6) continue; const L = f._T.info.light; if (!L) continue; const col = L.color || [1, 0.5, 0.1], S = f.sc * Math.sqrt(f.F), hh = (f._T.layers.flame ? f._T.layers.flame.size[1] : 2) * S;
      lightWant('fwg' + f.id, 'point', f.x, f.y + hh * 0.3, f.z, col[0], col[1], col[2], 0, 1, 0.5, { glow: Math.min(8, Math.max(1.2, hh * 0.45)), glowA: 0.55 * f.fade * Math.min(1, f.F), k: dk }); g++; }
    return n;
  };
  /* ---- heat haze: every fire type's own descriptor feeds the DIST engine ---- */
  F.hazeSources = 0;
  F.haze = () => {
    if (!DIST.live) return; let n = 0; const list = F.alive || [];
    for (const f of list) {
      if (!f.vis || n >= 28) continue; const T = f._T, H = T.info.haze; if (!H) continue; const e = Math.min(1.2, Math.max(0.15, f.e || 1)); const S = f.sc * Math.sqrt(f.F);
      const k = Math.min(1, H.strength * Math.min(1, 0.4 + 0.6 * Math.min(1, f.F)) * (T.kind === 'blast' ? (f.state === 'fireball' ? 1 : f.state === 'plume' ? 0.7 : 0.4) : Math.min(1, e)) * f.fade);
      if (k < 0.04) continue; DIST.haze(DIST.idOf(f), f.x, f.y + 0.4 + ((simT * H.rise_speed_mps) % 1.2), f.z, k, Math.max(0.8, H.height_m * S), Math.max(0.3, H.radius_m * S)); n++;
    }
    F.hazeSources = n;
  };
})();
/*FW-END part1b*/
