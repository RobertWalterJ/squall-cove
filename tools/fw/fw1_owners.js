/*FW-START part1c: owners (trees, patches, vehicles, boats, objects), per-frame tick*/
(() => {
  const F = FW, PH = ED.phone;
  const gnd = (x, z) => Math.max(heightAt(x, z), 0);
  /* ---- trees: every tree in the game's `burning` list gets a crown (or trunk, or shrub) fire that follows that tree's burn counter ---- */
  function treeFire(t) {
    const kind = t.kind, gy = gnd(t.x, t.z);
    const name = kind === 'shrub' ? 'shrub' : kind === 'palm' ? 'tree_trunk' : 'tree_crown';
    const sc = kind === 'shrub' ? 0.7 + 0.4 * t.sc : kind === 'palm' ? 1.0 + 0.25 * t.sc : 0.52 + 0.3 * t.sc;
    const f = F.spawn(name, t.x, gy + 0.05, t.z, { sc, F: 1, pri: 2, dur: Infinity, quads: (name === 'tree_crown') ? 2 : 1, state: (t.burn > 11 ? 'ignite' : 'ignite'),
      own: { kind: 'tree', ref: t, endIn: () => t.burn, sync: (f) => { if (f.state === 'burn' || f.state === 'ignite' || f.state === 'grow') { if (t.dead || t.burn <= 0) { if (t.dead) { f.state = 'decay'; f.st = 0; if (!F.types[f.name] || !F.types[f.name].clips || !F.types[f.name].clips.decay) f.state = 'out'; } else F.extinguish(f); } } } } });
    return f;
  }
  /* ---- hot patches (incendiary bombs, fire missions): a few fuel and grass fires over the area, for as long as the patch lasts ---- */
  function patchFire(h) {
    const n = Math.max(1, Math.min(PH ? 3 : 6, Math.round(h.r / 2.2))), fires = [];
    for (let i = 0; i < n; i++) {
      const a = Math.random() * 6.283, d = Math.sqrt(Math.random()) * h.r * 0.85, x = h.x + Math.cos(a) * d, z = h.z + Math.sin(a) * d, fuel = i === 0;
      const f = F.spawn(fuel ? 'oil_slick' : (Math.random() < 0.5 ? 'grass' : 'debris'), x, gnd(x, z) + 0.05, z, { sc: fuel ? Math.max(0.6, h.r / 4) : 1.1, F: 1, pri: 1.5, dur: Math.max(4, h.t), quads: fuel ? 2 : 1,
        own: { kind: 'patch', ref: h, multi: true, sync: (f) => { if (!HEATP.includes(h) && f.state === 'burn') { f.state = 'decay'; f.st = 0; } } } });
      if (f) fires.push(f);
    }
    h._fws = fires;
  }
  /* ---- vehicles: engine fire first, then the whole vehicle; wrecks burn on ---- */
  const SMALLV = new Set(['jeep', 'technical', 'quad_atv', 'ambulance']);
  function vehFire(v, engine) {
    const small = /jeep|technical|quad|ambulance/i.test((v.sp && v.sp.name) || '') || (v.sp && v.sp.hp <= 200 && !v.sp.tracked);
    const name = engine ? 'vehicle_engine' : (small ? 'vehicle_small' : 'vehicle');
    const sc = engine ? 1 : (small ? 1.0 : 1.0);
    const follow = (f) => { f.x = v.x; f.z = v.z; f.y = v.y + (engine ? 0.9 : 0.15); };
    const f = F.spawn(name, v.x, v.y + (engine ? 0.9 : 0.15), v.z, { sc, F: 1, pri: 2.5, quads: (engine || small) ? 1 : 2, follow,
      own: { kind: 'veh', ref: v, multi: true, endIn: () => v.dead ? 50 - (v.wreckT || 0) : 1e9,
        sync: (f) => { if (!BVL.includes(v)) { F.kill(f, true); return; } if (!v.burn && !v.dead && (f.state === 'burn' || f.state === 'grow' || f.state === 'ignite')) F.extinguish(f); else if (engine && v.dead && f.state === 'burn') { f.state = 'decay'; f.st = 0; } } } });
    if (f) { f.black = true; }
    return f;
  }
  function vehSync() {
    for (const v of BVL) {
      if (v.heli && !v.dead && !v.burn) continue; const burning = (v.burn > 0) || (v.dead && v.wreck && (v.wreckT || 0) < 48);
      if (!burning) { if (v._fwe && v._fwe.state === 'burn') F.extinguish(v._fwe); continue; }
      if (!v._fwe || v._fwe.dead) { if (!v._fwe || !v._fwx) { v._fwe = vehFire(v, true); v._fwx = true; } }
      if ((v.burn > 4 || v.dead) && (!v._fwf || v._fwf.dead) && !v._fwNo) { v._fwf = vehFire(v, false); }
    }
  }
  /* ---- boats: deck fires scaled by how badly the boat burns; they die when the crew put it out ---- */
  function boatSync() {
    for (const bt of boats) {
      const want = bt.fire > 0.05 && !(bt.sunk && bt.sinkT > 5);
      if (want) {
        const L = bt.sp.L || 12, nf = Math.max(1, Math.min(PH ? 2 : 4, Math.ceil(bt.fire * L / 14))); bt._fwb = bt._fwb || [];
        bt._fwb = bt._fwb.filter(f => !f.dead);
        while (bt._fwb.length < nf) {
          const k = bt._fwb.length, lx = (k - (nf - 1) / 2) * Math.min(L * 0.3, 7), lz = rnd(-0.2, 0.2) * (bt.sp.B || 4), ly = deckLy(bt, lx, lz) + 0.2;
          const f = F.spawn('boat_deck', 0, 0, 0, { sc: Math.max(0.5, Math.min(1.5, L / 22)), F: 0.6 + bt.fire, pri: 2.5, quads: 2, dur: Infinity, follow: (f) => { const w = worldOfDeck(bt, lx, ly, lz, tv); f.x = w.x; f.y = w.y; f.z = w.z; f.F = 0.55 + Math.min(1, bt.fire) * 0.9; },
            own: { kind: 'boat', ref: bt, multi: true, endIn: () => 1e9, sync: (f) => { if (!(bt.fire > 0.05) && f.state === 'burn') F.extinguish(f); else if (bt.sunk && bt.sinkT > 4 && f.state === 'burn') { f.state = 'decay'; f.st = 0; } } } });
          if (!f) break; f.black = true; bt._fwb.push(f);
        }
      }
    }
  }
  const tv = new THREE.Vector3();
  /* ---- burning objects (wood) ---- */
  let objT = 0;
  function objSync(dt) {
    objT -= dt; if (objT > 0) return; objT = 0.25;
    for (const o of objects) {
      if (o.gone || !(o.burn > 0) || o._fw) continue; if (o._fwTried && simT - o._fwTried < 1) continue; o._fwTried = simT;
      const p = o.body.position, big = Math.max(0.3, Math.min(2.2, Math.cbrt(o.vol || 0.2) * 1.6));
      F.spawn(big > 1.2 ? 'debris' : 'campfire', p.x, p.y, p.z, { sc: big > 1.2 ? big : big * 1.4, F: 1, pri: 1.2, follow: (f) => { const b = o.body.position; f.x = b.x; f.y = b.y - 0.1; f.z = b.z; }, quads: 1,
        own: { kind: 'obj', ref: o, endIn: () => o.burn, sync: (f) => { if (o.gone || !(o.burn > 0)) { if (f.state === 'burn' || f.state === 'grow' || f.state === 'ignite') { f.state = 'decay'; f.st = 0; } } } } });
    }
  }
  F.sync = (dt) => {
    for (const t of burning) if (!t._fw && !t.dead && t.burn > 0) treeFire(t);
    for (const h of HEATP) if (!h._fws && !h.fw) patchFire(h);
    vehSync(); boatSync(); objSync(dt);
    if (F.syncMore) F.syncMore(dt);
  };
  F.tick = (dt) => {
    if (!F.on) return; F.q = F.eff();
    if (F.q !== 'off') { if (!F.ready) F.ensureAtlas(); if (F.ready) { if (F.pre) F.pre(dt); F.sync(dt); } }
    F.frame(dt);
    if (F.q !== 'off' && !F.legacyUntil) F.haze();
  };
  /* the old particle fires step aside only for what FW is really drawing (F.drawn), so a slow atlas load or Fire quality Off keeps the old look */
  F.legacy = () => F.q === 'off' || !!F.legacyUntil || !F.ready;
})();
/*FW-END part1c*/
/*FW-START part1x: test hooks*/
window.__sc.FW = FW;
/*FW-END part1x*/
/*FW-START part1y: qa handles*/
Object.assign(window.__sc, { igniteTree, igniteTreesNear, burning, objects, boats, props, lavaVents, fxS, fxG, puffSmoke, heightAt, camera, scene, renderer, extinguishTree, windAt, wind });
/*FW-END part1y*/
