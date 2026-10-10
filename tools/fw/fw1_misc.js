/*FW-START part1e: water, rain, soot column, lava, settings*/
(() => {
  const F = FW, R = F.R, PH = ED.phone;
  const gnd = (x, z) => Math.max(heightAt(x, z), 0);
  /* ---- water on fire: how much a fire of each kind needs before it goes out (water-seconds; scaled by its fuel load) ---- */
  const THR = { campfire: 1.5, torch: 1, flare: 2, gas: 99, gas_jet: 99, grass: 1.5, spot_fire: 1, debris: 2.5, barrel: 3, shrub: 3, tree_trunk: 5, tree_crown: 7, vehicle_engine: 3, vehicle_small: 5, vehicle: 8, boat_deck: 8, pool: 10, oil_slick: 12, window: 3, doorway: 3, roof: 12, building: 12, splash_fire: 2, blast_small: 6, blast_medium: 9, blast_large: 14, blast_fuel: 14, blast_ground: 9 };
  const burningState = (f) => f.state === 'burn' || f.state === 'grow' || f.state === 'ignite' || f.state === 'residue' || f.state === 'plume';
  F.water = (x, z, r, amt, y) => {
    if (F.q === 'off') return 0; let n = 0;
    for (const f of F.fires) {
      if (f.dead || !burningState(f)) continue; const t = THR[f.name]; if (!t || t > 50) continue; const reach = r + Math.min(6, 0.5 * f.sc * (f.name === 'building' || f.name === 'roof' ? 4 : 1));
      if (Math.hypot(f.x - x, f.z - z) > reach) continue; if (y !== undefined && y > f.y + 25) continue;
      f.hit += amt; n++; F.stats.waterHits = (F.stats.waterHits || 0) + 1;
      if (f.hit > t * Math.max(0.5, f.F) && f.state !== 'extinguish') F.extinguish(f);
    }
    return n;
  };
  F.onExtinguish = (f) => {                                                    // the fire is out: tell the thing that owned it, make steam and the hiss
    const o = f.own; if (o && o.ref) {
      const r = o.ref;
      if (o.kind === 'tree') { if (r.burn > 0) extinguishTree(r); }
      else if (o.kind === 'veh') { r.burn = 0; r._fwNo = true; if (r._fwf && r._fwf !== f && !r._fwf.dead) F.extinguish(r._fwf); }
      else if (o.kind === 'boat') { if (r.fire > 0.05) { r.fire = 0; r.fireT = 0; } }
      else if (o.kind === 'obj') { r.burn = 0; r.T = Math.min(r.T || 0, 80); }
      else if (o.kind === 'patch') { r.t = Math.min(r.t, 0.5); }
    }
    if (F.afterExtinguish) F.afterExtinguish(f);
  };
  /* rain puts out small fires slowly */
  let rainT = 0;
  const RAINK = { campfire: 6, torch: 3, flare: 6, grass: 5, spot_fire: 3, debris: 8, barrel: 12, shrub: 10, splash_fire: 4 };
  F.rainTick = (dt) => {
    rainT -= dt; if (rainT > 0) return; rainT = 1; const ra = wx.rainAmt; if (ra < 0.55) return;
    for (const f of F.fires) { if (f.dead || !burningState(f)) continue; const k = RAINK[f.name]; if (!k) continue; f.hit += ra * 0.5; if (f.hit > k && f.state !== 'extinguish') F.extinguish(f); }
  };
  const _pre0 = F.pre;
  F.pre = (dt) => { if (_pre0) _pre0(dt); F.rainTick(dt); };
  /* ---- heavy black smoke: a soot column that widens as it rises and leans downwind, in three stacked sprites ---- */
  F.soot = (f, al) => {
    const T = F.need('smoke_column'); if (!T || T.state !== 'ready') return; const LY = T.layers.smoke, clip = T.clips.loop[f.vi % T.clips.loop.length]; if (!LY || !clip.smoke) return;
    const fr = F.frameOf(clip.smoke, f.st * 0.9 + f.ph, true, true), base = f.sc * Math.sqrt(f.F), wl = F.wind, lk = Math.min(1, F.windMs * 0.09), A = F.amb, big = Math.min(1, f.F);
    for (let k = 0; k < 3; k++) {
      const s = base * (0.9 + k * 0.95), hgt = LY.size[1] * base * (0.45 + k * 1.15), dx = wl.x * lk * hgt * 0.5, dz = wl.z * lk * hgt * 0.5;
      R.push(LY.combo, f.x + dx, f.y + hgt, f.z + dz, LY.size[0] * s, LY.size[1] * s, fr[0], fr[1], fr[2], al * (0.55 - k * 0.12) * big, f.flip, 0, 0, 1, A.r * 0.55, A.g * 0.55, A.b * 0.55, 0, wl.x * lk * LY.size[1] * s * 0.5, wl.z * lk * LY.size[1] * s * 0.5);
    }
  };
  /* ---- lava: ground fires where lava meets dry grass ---- */
  let lavaN = 0;
  F.lavaCell = (x, z, k) => {
    if (F.q === 'off' || !F.ready) return; lavaN++; if (lavaN % 5) return;
    for (let a = 0; a < 3; a++) { const ang = Math.random() * 6.283, d = 2.5 + Math.random() * 1.5, px = x + Math.cos(ang) * d, pz = z + Math.sin(ang) * d; if (F.flam(px, pz) > 0.5 && wx.rainAmt < 0.5) { F.igniteGround(px, pz, { convert: true }); break; } }
    if (F.lavaWet) F.lavaWet(x, z);
  };
  const ventT = new WeakMap();
  F.lavaVent = (v, dt) => {
    if (F.q === 'off' || !F.ready) return; let t = (ventT.get(v) || 0) - dt; if (t <= 0) { t = rnd(3, 6); const a = Math.random() * 6.283, d = rnd(3, 7), px = v.x + Math.cos(a) * d, pz = v.z + Math.sin(a) * d; F.igniteGround(px, pz, { convert: true }); igniteTreesNear(px, pz, 2); if (F.lavaWet) F.lavaWet(v.x, v.z); } ventT.set(v, t);
  };
  /* ---- settings: Fire quality ---- */
  const paintFire = () => {
    const b = $('mFireQ'); if (!b) return; const lab = { high: 'High', low: 'Low', off: 'Off' }, eff = F.eff();
    b.firstChild.nodeValue = 'Fire quality: ' + lab[F.pref]; b.setAttribute('aria-pressed', String(F.pref !== 'off'));
    b.querySelector('small').textContent = F.pref === 'off' ? 'Off: the old simple fire is drawn.' : eff !== F.pref ? 'Low for now, because your device asks for less motion or play was slow.' : F.pref === 'low' ? 'Lighter flames and smoke. Saves battery.' : 'Realistic flames, smoke, steam and fog.';
  };
  F.paintFire = paintFire;
  const btn = $('mFireQ');
  if (btn) { btn.addEventListener('click', () => { const nx = { high: 'low', low: 'off', off: 'high' }[F.pref] || 'high'; F.setPref(nx); paintFire(); toast('Fire quality: ' + ({ high: 'High', low: 'Low', off: 'Off' })[nx]); }); paintFire(); }
  F.applyQ(); 
})();
/*FW-END part1e*/
