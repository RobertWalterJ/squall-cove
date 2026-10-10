/*FW-START part1d: ground fires (spot fires, spreading fronts), buildings, spread rules*/
(() => {
  const F = FW, R = F.R, PH = ED.phone, G = F.G = { fronts: [], spots: [], bld: [], bldT: 0, stats: { fronts: 0, spots: 0, builds: 0 } };
  const gnd = (x, z) => Math.max(heightAt(x, z), 0);
  const smAt = (x, z) => { try { const k = Math.round(W2G(z)) * TN + Math.round(W2G(x)); return Math.min(1, SM[k] || 0); } catch (e) { return 0; } };
  const flam = (x, z) => { const h = heightAt(x, z); if (h < 0.5) return 0; const s = surfaceAt(x, z); return s === 'grass' ? 1 : s === 'dirt' ? 0.45 : 0; };
  F.flam = flam;
  const dry = (x, z) => 1 - 0.85 * smAt(x, z);
  const CAPF = () => F.cap().front;
  /* ---- spot fires: a small fire on flammable ground. It grows, and in dry ground with some wind it turns into a spreading front ---- */
  F.igniteGround = (x, z, o) => {
    o = o || {}; if (F.q === 'off' || !F.ready) return null; const fl = flam(x, z); if (!fl && !o.force) return null; if (wx.rainAmt > 0.55 && !o.force) return null;
    for (const s of G.spots) if (!s.fire.dead && Math.hypot(s.x - x, s.z - z) < 2.0) return s.fire;
    for (const fr of G.fronts) { const lx = x - fr.x0 - fr.ux * fr.d, lz = z - fr.z0 - fr.uz * fr.d, lon = lx * fr.ux + lz * fr.uz, lat = lx * fr.nx + lz * fr.nz; if (lon < 1 && lon > -9 && Math.abs(lat) < fr.hw + 1.5) return null; }
    if (G.spots.length >= CAPF() * 3) return null;
    const fire = F.spawn('spot_fire', x, gnd(x, z) + 0.05, z, { sc: o.sc || 1.5, F: 1, pri: 1.2, dur: o.dur || rnd(14, 22), own: { kind: 'spot', multi: true, endIn: () => 1e9 } });
    if (!fire) return null; G.stats.spots++; G.spots.push({ x, z, fire, t: 0, convert: o.convert !== false, ahead: !!o.ahead, dry: dry(x, z) * fl }); return fire;
  };
  /* ---- fronts ---- */
  const COLW = 1.5;
  function makeFront(x, z, o) {
    if (G.fronts.length >= CAPF()) return null;
    let ux = F.wind.x, uz = F.wind.z; const ms = Math.hypot(ux, uz); if (ms < 0.5) { const a = Math.random() * 6.283; ux = Math.cos(a); uz = Math.sin(a); } else { ux /= ms; uz /= ms; }
    const fr = { x0: x, z0: z, ux, uz, nx: -uz, nz: ux, d: 0, age: 0, hw: 0.9, cols: [], dry: o.dry === undefined ? 1 : o.dry, spotT: rnd(2, 4), burnT: 0, lickT: 0, hpT: 0, ashT: 0, speed: 0.2, calm: ms < 0.5, maxHW: PH ? 5 : 10, lastAlive: 0 };
    fr.fuelBase = (28 + Math.random() * 40) * (0.6 + 0.4 * fr.dry);
    for (const lat of [-0.75, 0.75]) fr.cols.push(newCol(fr, lat));
    G.fronts.push(fr); G.stats.fronts++; F.need('front_lead'); F.need('front_body'); F.need('front_trail'); F.need('lick'); F.needStrip();
    return fr;
  }
  const newCol = (fr, lat) => ({ lat, fuel: fr.fuelBase * (0.7 + Math.random() * 0.6), dead: false, td: 0, ph: Math.random() * 3, vi: (Math.random() * 3) | 0, lx: 0, lz: 0, ly: 0, a: 1 });
  F.makeFront = makeFront;
  /* a front's spread speed in m/s: wind, dry ground, slope; rain slows it */
  function frontSpeed(fr) {
    const px = fr.x0 + fr.ux * fr.d, pz = fr.z0 + fr.uz * fr.d, h0 = heightAt(px, pz), h1 = heightAt(px + fr.ux * 4, pz + fr.uz * 4), sl = (h1 - h0) / 4;
    let v = 0.1 + 0.17 * F.windMs; v *= 0.5 + 0.5 * dry(px, pz); v *= Math.max(0.5, Math.min(2, 1 + 2.5 * sl)); if (wx.rainAmt > 0.3) v *= 0.25; if (fr.calm) v = Math.min(v, 0.22);
    return Math.max(0.08, Math.min(2.5, v));
  }
  /* strip decal texture (burnt ground with breathing embers) */
  F.needStrip = () => {
    if (G.strip || G.stripP) return; G.stripP = R.loadTex('assets/fire/fire_burnt_strip.webp').then(tex => { G.strip = R.combo({ key: 'fire:strip', tex, cols: 4, rows: 4, fw: 128, fh: 64, anchor: [0.5, 0.5], mode: 0, order: 5.6, rule: 'vis' }); }).catch(() => { });
  };
  const tileT = (name) => { const T = F.need(name); return T && T.state === 'ready' ? T : null; };
  const _od = { q: 0, rot: 0, stretch: 1, loop: true, blend: false, cross: false, yaw: 0, noSmoke: false, fire: null, add: 0.5 };
  const hardFire = () => G.fronts.length + G.spots.length;
  F.syncMore = (dt) => {
    for (let i = G.spots.length - 1; i >= 0; i--) {                              // spot fires: merge into a passing front, or grow into one
      const s = G.spots[i], f = s.fire; s.t += dt; if (f.dead) { G.spots.splice(i, 1); continue; }
      let merged = false; for (const fr of G.fronts) { const lx = s.x - fr.x0 - fr.ux * fr.d, lz = s.z - fr.z0 - fr.uz * fr.d, lon = lx * fr.ux + lz * fr.uz, lat = lx * fr.nx + lz * fr.nz; if (lon < 1.2 && lon > -6 && Math.abs(lat) < fr.hw + 1) merged = true; }
      if (merged && f.state === 'burn') { f.state = 'decay'; f.st = 0; continue; }
      if (s.convert && s.t > 5 && f.state === 'burn' && s.dry > 0.2 && G.fronts.length < CAPF() && (F.windMs > 1.2 || Math.random() < dt * 0.05)) { s.convert = false; makeFront(s.x, s.z, { dry: s.dry }); }
    }
    for (let i = G.fronts.length - 1; i >= 0; i--) { const fr = G.fronts[i]; if (!stepFront(fr, dt)) { G.fronts.splice(i, 1); } }
    // burning trees light the grass under them (downwind), and fires heat nearby buildings
    if (F.q !== 'off') { G.treeT = (G.treeT || 0) - dt; if (G.treeT <= 0) { G.treeT = 0.7; treeToGround(); } }
    G.bldT -= dt; if (G.bldT <= 0) { G.bldT = 1.0; buildingSpread(); }
    for (let i = G.bld.length - 1; i >= 0; i--) { const b = G.bld[i]; b.t += dt; if (!b.col && b.t > b.life) { b.col = true; if (F.sndEv) { F.sndEv('collapse', b.p.x, b.p.z, { y: 3 }); F.sndEv('clatter', b.p.x, b.p.z, { delay: 0.9 }); F.sndEv('clatter', b.p.x + 2, b.p.z, { delay: 1.8, gain: 0.7 }); } } if (b.t > b.life + 6) G.bld.splice(i, 1); }
  };
  function treeToGround() {
    for (const t of burning) {
      if (t.dead || !t._fw || t._fw.state !== 'burn' || t._fwg) continue; if (t._fw.age < 3.5) continue; t._fwg = true;
      if (Math.random() < 0.55 && F.windMs > 0.8) { const a = Math.atan2(F.wind.z, F.wind.x) + rnd(-0.6, 0.6), d = rnd(2, 4.5); F.igniteGround(t.x + Math.cos(a) * d, t.z + Math.sin(a) * d, { convert: true }); }
    }
  }
  function stepFront(fr, dt) {
    fr.age += dt; fr.speed = frontSpeed(fr); fr.d += fr.speed * dt; fr.hw = Math.min(fr.maxHW, fr.hw + dt * (0.12 + 0.28 * fr.speed));
    while (fr.cols.length * COLW * 0.5 < fr.hw) { const k = fr.cols.length; fr.cols.push(newCol(fr, k % 2 ? 0.75 + COLW * (k >> 1) : -0.75 - COLW * (k >> 1))); }
    let alive = 0; const trees = fr.cols;
    for (const c of fr.cols) {
      const px = fr.x0 + fr.ux * fr.d + fr.nx * c.lat, pz = fr.z0 + fr.uz * fr.d + fr.nz * c.lat; c.lx = px; c.lz = pz; c.ly = gnd(px, pz);
      if (!c.dead) { c.fuel -= fr.speed * dt; if (c.fuel <= 0 || !flam(px, pz) || wx.rainAmt > 0.7 && Math.random() < dt * 0.4) { c.dead = true; c.td = fr.age; } else alive++; }
      c.a = c.dead ? Math.max(0, 1 - (fr.age - c.td) / 4.5) : Math.min(1, fr.age / 1.2);
    }
    if (alive) fr.lastAlive = fr.age; if (!alive && fr.age - fr.lastAlive > 5) return false; if (fr.age > 400) return false;
    // effects: heat on the ground (people and AI avoid it), flammables in the lead zone, trees, buildings
    fr.burnT -= dt; if (fr.burnT <= 0) {
      fr.burnT = 0.6; let k = 0;
      for (const c of fr.cols) { if (c.dead) continue; if ((k++ & 1) === 0) { try { heatGT(c.lx, c.lz, 1.7, 330); } catch (e) { } } }
      const lead = fr.d; const hw = fr.hw + 1.4;
      for (const t of trees === 0 ? [] : window.__sc.trees) { if (t.dead || t.burn > 0) continue; const dx = t.x - fr.x0 - fr.ux * lead, dz = t.z - fr.z0 - fr.uz * lead; if (Math.abs(dx) > 14 || Math.abs(dz) > 14) continue; const lon = dx * fr.ux + dz * fr.uz, lat = dx * fr.nx + dz * fr.nz; if (Math.abs(lat) < hw && lon > -2 && lon < 2.4 && Math.random() < 0.55) igniteTree(t); }
      for (const o of objects) { if (o.gone || !o.m || !o.m.flam || o.burn > 0) continue; const p = o.body.position, dx = p.x - fr.x0 - fr.ux * lead, dz = p.z - fr.z0 - fr.uz * lead; if (Math.abs(dx) > 12 || Math.abs(dz) > 12) continue; const lon = dx * fr.ux + dz * fr.uz, lat = dx * fr.nx + dz * fr.nz; if (Math.abs(lat) < hw && lon > -2 && lon < 3) o.T += 140; }
      F.igniteNear(fr.x0 + fr.ux * lead, fr.z0 + fr.uz * lead, fr.hw + 2.5, 0.5);
    }
    fr.hpT -= dt; if (fr.hpT <= 0) { fr.hpT = 1.2; HEATP.push({ x: fr.x0 + fr.ux * (fr.d - 1), z: fr.z0 + fr.uz * (fr.d - 1), r: fr.hw + 1.2, p: 7, t: 1.4, fw: true }); }
    fr.ashT -= dt; if (fr.ashT <= 0) { fr.ashT = 0.7; paintAsh(fr); }
    fr.lickT -= dt; if (fr.lickT <= 0 && F.q === 'high') { fr.lickT = rnd(0.5, 1.8); const lat = rnd(-fr.hw, fr.hw), x = fr.x0 + fr.ux * (fr.d + 0.6) + fr.nx * lat, z = fr.z0 + fr.uz * (fr.d + 0.6) + fr.nz * lat; if (flam(x, z) && F.fires.length < F.cap().fires) { const l = F.spawn('lick', x, gnd(x, z) + 0.05, z, { state: 'shot', sc: rnd(0.9, 1.5), pri: 0.5, noLight: true, noSmoke: true }); if (l) l.fadeOut = 0; } }
    fr.spotT -= dt; if (fr.spotT <= 0) { fr.spotT = F.windMs > 4 ? rnd(2, 5) : rnd(6, 14); if (F.windMs > 3 && alive) { const lat = rnd(-fr.hw, fr.hw), ahead = rnd(2.5, 2.5 + Math.min(8, F.windMs * 1.1)), x = fr.x0 + fr.ux * (fr.d + ahead) + fr.nx * lat, z = fr.z0 + fr.uz * (fr.d + ahead) + fr.nz * lat; F.igniteGround(x, z, { ahead: true, convert: false, dur: 12, sc: 1.2 }); } }
    return true;
  }
  function paintAsh(fr) {
    try { for (const c of fr.cols) { if (c.dead && fr.age - c.td > 4) continue; const x = fr.x0 + fr.ux * (fr.d - 3) + fr.nx * c.lat, z = fr.z0 + fr.uz * (fr.d - 3) + fr.nz * c.lat; const gx = Math.round(W2G(x)), gz = Math.round(W2G(z)); for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) { const k = (gz + a) * TN + gx + b; if (k > 0 && k < TN * TN) ashData[k] = Math.max(ashData[k], 150); } } ashTex.needsUpdate = true; } catch (e) { }
  }
  /* ---- drawing the fronts: three rows of tiles per column (lead, body, trail) and a smouldering strip behind ---- */
  F.afterDraw = (dt, alive) => {
    if (!G.fronts.length) return; const L = tileT('front_lead'), B = tileT('front_body'), T = tileT('front_trail'); if (!L || !B || !T) return;
    const cam = camera.position, high = F.q === 'high', Kp = innerHeight * renderer.getPixelRatio() / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
    G.drawn = 0;
    for (const fr of G.fronts) {
      const mx = fr.x0 + fr.ux * fr.d, mz = fr.z0 + fr.uz * fr.d, dc = Math.hypot(mx - cam.x, mz - cam.z); if (dc > 520 + fr.hw * 6) continue;
      const fuelK = 0.9 + 0.35 * Math.min(1, fr.dry) + 0.3 * Math.min(1, F.windMs / 8), anim = dc < 160;
      for (const c of fr.cols) {
        const cd = Math.hypot(c.lx - cam.x, c.lz - cam.z); if (cd > 520) continue; const sc = fuelK * (0.9 + 0.2 * Math.sin(c.ph * 3 + fr.age * 0.7)), t = anim ? fr.age + c.ph : c.ph;
        const rows = [[L, 0, 1.0], [B, 1.7, 1.0], [T, 4.4, 1.0]];
        for (const [TT, off, kk] of rows) {
          if (c.dead && TT === L) continue; if (c.dead && TT === B && fr.age - c.td > 2.5) continue;
          if (fr.d - off < -0.8) continue; const x = c.lx - fr.ux * off, z = c.lz - fr.uz * off; const h = heightAt(x, z); if (h < 0.4) continue;
          const a = c.a * kk * (TT === T ? (c.dead ? c.a : 1) : 1) * Math.min(1, Math.max(0, (fr.d - off + 0.8) / 1.2));
          if (a < 0.02) continue; const clip = TT.clips.loop[(c.vi + (TT === L ? 0 : TT === B ? 1 : 2)) % TT.clips.loop.length];
          _od.loop = true; _od.blend = high; _od.noSmoke = !high && TT !== T; _od.q = 0; _od.lean = 1; F.pushClip(TT, clip, t + (TT === B ? 0.31 : TT === T ? 0.62 : 0), x, h + 0.04, z, sc, 1, 1, a, (c.vi & 1) ? -1 : 1, _od); G.drawn++;
        }
        if (G.strip && !c.dead) { const off = 7.5, x = c.lx - fr.ux * off, z = c.lz - fr.uz * off; if (fr.d - off > -1 && heightAt(x, z) > 0.4) { const fi = ((fr.age * 6 + c.ph * 5) | 0) % 16, edge = Math.abs(c.lat) > fr.hw - 1.2 ? 0.45 : 1; R.push(G.strip, x, heightAt(x, z) + 0.06, z, 2.1, 1.1, fi, fi, 0, 0.5 * edge * c.a, 1, 3, Math.atan2(fr.nx, fr.nz) + 1.5708, 1, 1, 1, 1, 0, 0, 0); } }
      }
    }
  };
  /* ---- buildings: windows, a doorway and the roof catch fire and burn for a minute or two ---- */
  const bldList = () => { const out = []; for (const p of props) { if (p.gone || !p.item || !p.mesh) continue; const id = p.item.id || ''; if (/^b-/.test(id) && p.item.box && !/tank|silo|tower/.test(id)) out.push(p); } return out; };
  F.igniteBuilding = (p, o) => {
    o = o || {}; if (F.q === 'off' || !F.ready || !p || p._fwBurn && simT - p._fwBurn < 150) return false; if (G.bld.length >= (PH ? 2 : 5)) return false;
    p._fwBurn = simT; const [hx, hh, hz] = p.item.box, yaw = p.mesh.rotation.y, c = Math.cos(yaw), s = Math.sin(yaw), gy = gnd(p.x, p.z), big = Math.max(hx, hz);
    const rec = { p, t: 0, life: 70 + Math.random() * 50 + big * 3, fires: [] }; G.bld.push(rec); G.stats.builds++;
    const place = (lx, lz) => ({ x: p.x + lx * c + lz * s, z: p.z - lx * s + lz * c });
    const nWin = Math.max(2, Math.min(PH ? 3 : 6, Math.round(big / 2.2)));
    const mk = (name, lx, lz, y, sc, delay, dur, extra) => { const q = place(lx, lz); const f = F.spawn(name, q.x, y, q.z, Object.assign({ sc, F: 1, pri: 2, dur: dur, quads: name === 'roof' ? 2 : 1 }, extra || {})); if (f) { f.warm = 0.5; rec.fires.push(f); if (delay > 0) { f.alphaK = 0; f.hold = delay; } } return f; };
    for (let i = 0; i < nWin; i++) { const side = Math.random() < 0.5 ? 1 : -1, alongX = Math.random() < 0.5; const lx = alongX ? rnd(-hx * 0.8, hx * 0.8) : side * (hx + 0.35), lz = alongX ? side * (hz + 0.35) : rnd(-hz * 0.8, hz * 0.8); mk('window', lx, lz, gy + Math.min(hh * 0.35, 1.2), 0.75 * Math.min(1.3, 0.6 + big / 10), i * 2.5, rec.life - i * 3); }
    mk('doorway', 0, hz + 0.4, gy + 0.05, 0.8, 1.5, rec.life);
    mk('roof', 0, 0, gy + hh * 0.85, Math.max(0.35, big * 2 / 12), 7 + Math.random() * 6, rec.life - 8);
    rec.fires.forEach(f => { f.own = null; });
    F.onBuilding && F.onBuilding(rec); return true;
  };
  /* delayed fires of a building start after their delay: handled in the per-frame pre step */
  F.pre = (dt) => { for (const b of G.bld) for (const f of b.fires) if (f.hold > 0) { f.hold -= dt; if (f.hold <= 0) { f.alphaK = undefined; f.st = 0; f.state = 'ignite'; if (f.name === 'window' && F.sndEv) F.sndEv('glass', f.x, f.z, { y: f.y }); } else { f.alphaK = 0; f.st = 0; } } };
  /* fires close to a building may set it alight: the front, burning vehicles, fuel pools, flaming debris, burning trees */
  F.igniteNear = (x, z, r, p) => {
    if (F.q === 'off') return false; G.bldC = G.bldC || { t: -9, l: [] }; if (simT - G.bldC.t > 4) { G.bldC.t = simT; G.bldC.l = bldList(); }
    for (const b of G.bldC.l) { const [hx, , hz] = b.item.box; const d = Math.hypot(b.x - x, b.z - z) - Math.max(hx, hz); if (d < r && Math.random() < p) { if (F.igniteBuilding(b)) return true; } } return false;
  };
  function buildingSpread() {
    for (const f of F.fires) { if (f.dead || f.state !== 'burn' || !f.vis) continue; if (f.name === 'vehicle' || f.name === 'pool' || f.name === 'oil_slick' || f.name === 'boat_deck') F.igniteNear(f.x, f.z, 4 + 2 * f.sc, 0.12 * f.F); else if (f.name === 'tree_crown' && f.age > 5) F.igniteNear(f.x, f.z, 3.5, 0.06); }
  }
  F.G.cap = CAPF;
  F.afters.push((dt, alive) => F.afterDraw(dt, alive));
})();
/*FW-END part1d*/
