/*FW-START part2: explosions, flaming debris, embers and sparks, fuel splashes and pools, water extinguishing*/
(() => {
  const F = FW, R = F.R, PH = ED.phone;
  const gnd = (x, z) => Math.max(heightAt(x, z), 0);
  const wet = (x, z) => heightAt(x, z) < 0.3;
  /* ---- the particle sheets: embers, sparks, burning droplets, ash (dots) and ember streaks ---- */
  const P = F.P = { dots: null, streaks: null, list: [], loading: false, cap: PH ? 40 : 140 };
  F.needParticles = () => {
    if (P.dots || P.loading || !F.atlas) return !!P.dots; P.loading = true; const A = F.atlas.particles;
    Promise.all([R.loadTex('assets/fire/' + A.dots.file), R.loadTex('assets/fire/' + A.streaks.file)]).then(([td, ts]) => {
      P.dots = R.combo({ key: 'fire:p_dots', tex: td, cols: A.dots.cols, rows: A.dots.rows, fw: A.dots.frame_px[0], fh: A.dots.frame_px[1], anchor: [0.5, 0.5], mode: 0, order: 7.1, rule: 'vis' });
      P.streaks = R.combo({ key: 'fire:p_streaks', tex: ts, cols: A.streaks.cols, rows: A.streaks.rows, fw: A.streaks.frame_px[0], fh: A.streaks.frame_px[1], anchor: [0.109375, 0.5], mode: 0, order: 7.1, rule: 'vis' });
      P.clips = {}; for (const c of A.dots.clips) P.clips[c.name] = c; for (const c of A.streaks.clips) P.clips[c.name] = c; P.ok = true;
    }).catch(() => { P.loading = false; });
    return false;
  };
  const clipP = (n) => P.clips && P.clips[n];
  /* kind: 'ember' 'spark' 'droplet' 'streak'. v in m/s. */
  F.particle = (kind, x, y, z, vx, vy, vz, o) => {
    if (F.q === 'off') return; F.needParticles(); if (!P.ok) return; if (P.list.length >= P.cap) P.list.shift(); o = o || {};
    const v = 'abcd'[(Math.random() * 4) | 0]; let name = kind === 'ember' ? 'ember_' + v : kind === 'spark' ? 'spark_' + v : kind === 'droplet' ? 'droplet_' + 'abc'[(Math.random() * 3) | 0] : 'ember_streak_' + (o.cls || 'med');
    const c = clipP(name); if (!c) return; P.list.push({ kind, c, x, y, z, vx, vy, vz, age: 0, life: o.life || c.duration_s * (c.loop ? 1.6 : 1), size: o.size || (kind === 'ember' ? rnd(0.14, 0.3) : kind === 'spark' ? rnd(0.35, 0.7) : kind === 'droplet' ? rnd(0.2, 0.4) : 1.4), g: o.g === undefined ? (kind === 'ember' ? 2.5 : 9) : o.g, drag: o.drag === undefined ? 0.4 : o.drag, a: o.a === undefined ? 1 : o.a, wind: kind === 'ember' ? 0.6 : 0.1 });
  };
  const stepParticles = (dt) => {
    if (!P.ok) return; const L = P.list, cam = camera.position, wl = F.wind;
    camera.getWorldDirection(_cd); _cr.crossVectors(_cd, _up).normalize(); _cu.crossVectors(_cr, _cd).normalize();
    for (let i = L.length - 1; i >= 0; i--) {
      const p = L[i]; p.age += dt; if (p.age >= p.life) { L.splice(i, 1); continue; }
      p.vy -= p.g * dt; const dg = Math.max(0, 1 - p.drag * dt); p.vx = p.vx * dg + (wl.x - p.vx) * p.wind * dt * 0.5; p.vz = p.vz * dg + (wl.z - p.vz) * p.wind * dt * 0.5; p.x += p.vx * dt; p.y += p.vy * dt; p.z += p.vz * dt;
      const gy = gnd(p.x, p.z); if (p.y < gy + 0.05 && p.vy < 0) { if (p.kind === 'droplet' || p.kind === 'streak') { L.splice(i, 1); continue; } p.y = gy + 0.05; p.vy = 0; p.vx *= 0.3; p.vz *= 0.3; if (p.kind === 'spark') p.age = Math.max(p.age, p.life * 0.7); }
      const d = Math.hypot(p.x - cam.x, p.z - cam.z); if (d > 260) continue;
      const u = p.age / p.life, fi = Math.min(p.c.count - 1, Math.floor(u * p.c.count)), fa = p.c.first + fi, a = p.a * (p.kind === 'ember' ? Math.min(1, (1 - u) * 3) : 1);
      let rot = 0, stretch = 1;
      if (p.kind === 'streak' || p.kind === 'droplet') { const sp = Math.hypot(p.vx, p.vy, p.vz) + 1e-3; const vr = p.vx * _cr.x + p.vy * _cr.y + p.vz * _cr.z, vu = p.vx * _cu.x + p.vy * _cu.y + p.vz * _cu.z; rot = Math.atan2(-vu, -vr); if (p.kind === 'droplet') rot += 1.5708; stretch = Math.max(0.6, Math.min(1.8, sp / 15)); }
      const cmb = p.kind === 'streak' ? P.streaks : P.dots, sz = p.size; const w = p.kind === 'streak' ? sz : sz, h = p.kind === 'streak' ? sz * 0.25 : sz;
      R.push(cmb, p.x, p.y, p.z, w, h, fa, fa, 0, a, 1, 1, rot, stretch, 1, 1, 1, p.kind === 'ember' ? 0.2 : 0.7, 0, 0);
    }
  };
  const _cd = new THREE.Vector3(), _cr = new THREE.Vector3(), _cu = new THREE.Vector3(), _up = new THREE.Vector3(0, 1, 0);
  /* ---- fireballs ---- */
  const KINDS = { small: ['blast_small', 5], medium: ['blast_medium', 10], large: ['blast_large', 20], fuel: ['blast_fuel', 13], ground: ['blast_ground', 11] };
  F.blastStats = { n: 0, last: null };
  F.blast = (x, gy, z, Rb, o, onWater) => {
    o = o || {}; if (F.q === 'off' || F.legacyUntil || !F.ready) { if (F.q !== 'off') F.ensureAtlas(); return false; }
    if (Rb < 2.2) return false; const fuel = !!(o.fuel || /vehicle|fuel|tank/i.test(o.name || '') || o.heavy && o.skip && o.skip.sp && o.skip.sp.boom);
    let kind = fuel ? 'fuel' : Rb >= 14 ? 'large' : Rb >= 8 ? (!o.air && Rb < 13 && !onWater ? 'ground' : 'medium') : 'small';
    if (o.skip && o.skip.sp && o.skip.sp.boom) kind = 'fuel';
    const [name, rb] = KINDS[kind], T = F.need(name); F.need('smoke_column'); F.needParticles();
    if (!T) return false;                                           // still loading: the old particles play this one
    const sc = Math.max(0.45, Math.min(1.6, Rb / rb)) * (onWater ? 0.85 : 1);
    const f = F.spawn(name, x, gy + 0.05, z, { state: 'fireball', sc, F: 1, pri: 6, dur: (Rb >= 10 ? 26 : 14) * rnd(0.8, 1.2) * (fuel ? 1.6 : 1), quads: Rb >= 8 ? 2 : 1, noLight: false, silent: true });
    if (!f) return false; f.mode = 'blast'; f.vi = (Math.random() * 2) | 0; f.black = fuel || kind === 'large'; F.blastStats.n++; F.blastStats.last = { kind, Rb, x, z };
    // flaming debris: a fraction of the chunks thrown by this blast burn
    F.dbFrac = fuel ? 0.7 : (o.name && /vehicle/i.test(o.name)) ? 0.6 : Rb >= 8 ? 0.2 : 0.12; F.dbT = simT;
    // embers and sparks thrown out, a streak or two
    const ne = Math.min(PH ? 8 : 24, Math.round(6 + Rb * 1.2));
    for (let i = 0; i < ne; i++) { const a = Math.random() * 6.283, e = rnd(0.2, 1.1), sp = Rb * rnd(0.6, 1.5); F.particle(i % 3 ? 'ember' : 'spark', x, gy + 0.8, z, Math.cos(a) * Math.cos(e) * sp, Math.sin(e) * sp * 0.9 + 2, Math.sin(a) * Math.cos(e) * sp, { life: rnd(0.8, 2.2) }); }
    for (let i = 0; i < (PH ? 2 : 6); i++) { const a = Math.random() * 6.283, e = rnd(0.4, 1.3), sp = Rb * rnd(1, 2); F.particle('streak', x, gy + 1, z, Math.cos(a) * Math.cos(e) * sp, Math.sin(e) * sp + 3, Math.sin(a) * Math.cos(e) * sp, { life: rnd(0.4, 0.9), cls: sp > 14 ? 'fast' : sp > 7 ? 'med' : 'slow', size: rnd(1.0, 1.8), g: 7 }); }
    F.burnRadius(x, z, Rb, o, fuel);
    if (fuel) { F.fuelSplash(x, z, Rb, PH ? 2 : 4); F.spill(x, z, { kind: 'fuel', r: Rb * 0.25, dur: rnd(35, 60) }); }
    return true;
  };
  /* what a fireball sets alight: trees, wooden things, dry ground, buildings */
  F.burnRadius = (x, z, Rb, o, fuel) => {
    if (Rb < 5) return; igniteTreesNear(x, z, Rb * 0.9);
    for (const ob of objects) { if (ob.gone || !ob.m || !ob.m.flam || ob.burn > 0) continue; const p = ob.body.position; if (Math.hypot(p.x - x, p.z - z) < Rb * 0.9) ob.T += 220; }
    const n = Math.min(PH ? 2 : 5, Math.round(Rb / 3)); for (let i = 0; i < n; i++) { const a = Math.random() * 6.283, d = Math.sqrt(Math.random()) * Rb * 0.9, px = x + Math.cos(a) * d, pz = z + Math.sin(a) * d; if (Math.random() < 0.6) F.igniteGround(px, pz, { convert: true, sc: 1.1 }); }
    if (Rb >= 6) F.igniteNear(x, z, Rb * 0.9, fuel ? 0.8 : Rb >= 10 ? 0.5 : 0.25);
  };
  /* ---- fuel: thrown splashes that become pool fires, and pools and oil slicks ---- */
  F.fuelSplash = (x, z, Rb, n) => {
    F.need('splash_fire'); F.need('spatter_fan');
    for (let i = 0; i < n; i++) {
      const a = Math.random() * 6.283, d = Rb * rnd(0.3, 1.1), px = x + Math.cos(a) * d, pz = z + Math.sin(a) * d, onW = wet(px, pz);
      const f = F.spawn('splash_fire', px, onW ? Math.max(0.05, waveH(px, pz, simT)) + 0.05 : gnd(px, pz) + 0.05, pz, { sc: rnd(1.0, 1.6), F: rnd(0.9, 1.3), pri: 2, dur: rnd(18, 40), quads: 1, silent: i > 0 });
      if (f) { f.black = true; f.warm = 1; if (onW) f.follow = (ff) => { ff.y = waveH(ff.x, ff.z, simT) + 0.05; }; }
      if (i < 3) { const s = F.spawn('spatter_fan', x + Math.cos(a) * d * 0.4, gnd(x, z) + 0.3, z + Math.sin(a) * d * 0.4, { state: 'shot', sc: 1.6, pri: 1, noLight: true, noSmoke: true, silent: true }); if (s) s.fadeOut = 0; }
    }
  };
  /* a fuel pool or oil slick on the ground or the sea: it burns with heavy black smoke and spreads to what is next to it */
  F.spill = (x, z, o) => {
    o = o || {}; if (F.q === 'off' || !F.ready) return null; const onW = wet(x, z), nm = onW || o.kind === 'oil' ? 'oil_slick' : 'pool'; const gy = onW ? Math.max(0.05, waveH(x, z, simT)) + 0.05 : gnd(x, z) + 0.05;
    for (const f of F.fires) if ((f.name === 'pool' || f.name === 'oil_slick') && Math.hypot(f.x - x, f.z - z) < 2.5 && !f.dead) { f.dur = Math.max(f.dur, o.dur || 40); return f; }
    const sc = Math.max(0.4, Math.min(1.6, (o.r || 2) / 2.2)), f = F.spawn(nm, x, gy, z, { sc, F: o.F || 1, pri: 3, dur: o.dur || rnd(40, 70), quads: 2, silent: o.silent });
    if (f) { f.black = true; if (onW) f.follow = (ff) => { ff.y = waveH(ff.x, ff.z, simT) + 0.05; }; if (!onW) HEATP.push({ x, z, r: Math.max(2, sc * 2.4), p: 12, t: Math.min(30, o.dur || 40), fw: true }); }
    return f;
  };
  /* ---- flaming debris: a flame on a fraction of the chunks in the game's own debris pool ---- */
  F.flDeb = 0;
  F.dFl = (frag) => { if (F.q === 'off' || !F.ready) return 0; const fr = (simT - (F.dbT || -9)) < 0.1 ? F.dbFrac : 0.012; if (Math.random() >= fr) return 0; return F.flDeb < (PH ? 14 : 44) ? 1 : 0; };
  const CLIPS = ['slow', 'med', 'fast'], DESIGN = [4, 12, 30];
  let dbNo = 0;
  F.debrisStep = (dt) => {
    if (typeof DEB === 'undefined' || !DEB.p || !DEB.p.length) { F.flDeb = 0; return; }
    for (const n of ['debris_slow', 'debris_med', 'debris_fast']) F.need(n); const Ts = [F.types.debris_slow, F.types.debris_med, F.types.debris_fast]; if (!Ts[0] || Ts[0].state !== 'ready' || Ts[1].state !== 'ready' || Ts[2].state !== 'ready') return;
    camera.getWorldDirection(_cd); _cr.crossVectors(_cd, _up).normalize(); _cu.crossVectors(_cr, _cd).normalize(); let nfl = 0; const cam = camera.position;
    for (const d of DEB.p) {
      if (!d.fl) continue; nfl++;
      if (d.fl === 1) { d.fl = 2; d.flT = rnd(4, 8) * (PH ? 0.7 : 1); d.age0 = d.age; d.life = Math.max(d.life, d.age + d.flT + 0.5); d.cls = (Math.random() * 3) | 0; d.fph = Math.random() * 3; }
      const u = (d.age - d.age0) / d.flT; if (u >= 1) { d.fl = 0; continue; }
      const sp = Math.hypot(d.vx, d.vy, d.vz), ci = sp < 8 ? 0 : sp < 20 ? 1 : 2, T = Ts[ci], LY = T.layers.flame; if (!LY) continue; const clip = T.clips.loop[d.cls % T.clips.loop.length]; if (!clip || !clip.flame) continue;
      const gnow = gnd(d.x, d.z) + d.s * 0.45, rest = d.y <= gnow + 0.02;
      if (rest && !d._land && d.age > 0.12) { d._land = true; F.debrisLand(d); }
      const dist = Math.hypot(d.x - cam.x, d.z - cam.z); if (dist > 200) continue;
      let rot, stretch;
      if (rest || sp < 1.2) { rot = 1.5708; stretch = 0.7; } else { const vr = d.vx * _cr.x + d.vy * _cr.y + d.vz * _cr.z, vu = d.vx * _cu.x + d.vy * _cu.y + d.vz * _cu.z; rot = Math.atan2(-vu, -vr); stretch = Math.max(0.6, Math.min(1.7, sp / DESIGN[ci])); }
      const S = 0.45 + 2.6 * d.s, al = Math.min(1, (1 - u) * 2.2), fr = F.frameOf(clip.flame, (d.age + d.fph) * 1, true, F.q === 'high'); // the wind of its own motion bends the flame; slow ones lean up
      R.push(LY.combo, d.x, d.y, d.z, LY.size[0] * S, LY.size[1] * S, fr[0], fr[1], fr[2], al, 1, 1, rot, stretch, 1, 1, 1, 0.55, 0, 0);
      const sm = T.layers.smoke; if (sm && !PH && F.q === 'high' && dist < 90 && clip.smoke) { const f2 = F.frameOf(clip.smoke, (d.age + d.fph), true, true); R.push(sm.combo, d.x, d.y, d.z, sm.size[0] * S, sm.size[1] * S, f2[0], f2[1], f2[2], al * 0.7, 1, 1, rot, stretch, F.amb.r, F.amb.g, F.amb.b, 0, 0, 0); }
      if (!rest && Math.random() < dt * 5) F.particle('ember', d.x, d.y, d.z, d.vx * 0.2 + rnd(-1, 1), rnd(0, 1.5), d.vz * 0.2 + rnd(-1, 1), { life: rnd(0.7, 1.4) });
      if (!rest && sp > 8 && Math.random() < dt * 3 && F.q === 'high') F.particle('streak', d.x, d.y, d.z, d.vx * 0.9, d.vy * 0.9, d.vz * 0.9, { life: 0.3, cls: sp > 20 ? 'fast' : 'med', size: 1.2, g: 0 });
    }
    F.flDeb = nfl;
  };
  /* a burning chunk lands: it lights what it touches, makes a spot fire, or fizzles in water */
  F.debrisLand = (d) => {
    F.stats.debrisLand = (F.stats.debrisLand || 0) + 1;
    if (wet(d.x, d.z)) { sparks(d.x, d.y + 0.1, d.z, 3); if (F.steamAt) F.steamAt('small', d.x, d.z, 0.6); F.sndEv && F.sndEv('sizzle', d.x, d.z, { gain: 0.6 }); return; }
    igniteTreesNear(d.x, d.z, 2.2);
    for (const q of objects) { if (q.gone || !q.m || !q.m.flam || q.burn > 0) continue; const p = q.body.position; if (Math.hypot(p.x - d.x, p.z - d.z) < 2) q.T += 120; }
    F.igniteNear(d.x, d.z, 1.5, 0.3);
    if (d.fuelish) F.fuelSplash(d.x, d.z, 1.5, 1); else if (Math.random() < 0.55) F.igniteGround(d.x, d.z, { convert: true, sc: 0.9 });
    HEATP.push({ x: d.x, z: d.z, r: 1.3, p: 9, t: 3, fw: true });
    if (d.s > 0.12) F.sndEv && F.sndEv('clatter', d.x, d.z, { gain: 0.7 });
    for (let i = 0; i < 3; i++) F.particle('spark', d.x, d.y + 0.1, d.z, rnd(-2, 2), rnd(2, 5), rnd(-2, 2), { life: 0.4 });
  };
  F.lfSkip = (lf) => { for (const q of F.fires) if (q.mode === 'blast' && q.vis && Math.abs(q.x - lf.x) < 4 && Math.abs(q.z - lf.z) < 4) return true; return false; };
  F.afters.push((dt) => { F.debrisStep(dt); stepParticles(dt); });
  const _pre = F.pre; let preloaded = false;
  F.pre = (dt) => { if (_pre) _pre(dt); if (!preloaded && typeof BATTLE !== 'undefined' && BATTLE.on) { preloaded = true; for (const n of PH ? ['blast_small', 'debris_med'] : ['blast_small', 'blast_medium', 'blast_ground', 'blast_fuel', 'debris_slow', 'debris_med', 'debris_fast', 'smoke_column']) F.need(n); F.needParticles(); } };
})();
/*FW-END part2*/
