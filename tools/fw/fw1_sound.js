/*FW-START part1f: fire sound (FIRE-SOUND-SPEC.md): loops by size and fuel, near/far crossfade, interior twin in the station, one-shots with voice limits*/
(() => {
  const F = FW, PH = ED.phone, S = F.snd = { loops: new Map(), keys: new Set(), duck: 1, duckT: 0, last: {}, acc: 0, tickT: 0, n: { loops: 0, shots: 0 }, played: {} };
  const CLS = { campfire: 'camp', barrel: 'camp', torch: 'camp', flare: 'camp', spot_fire: 'camp', debris: 'camp', lick: null, gas: 'gas', gas_jet: 'gas', shrub: 'medium', tree_trunk: 'tree', tree_crown: 'tree', vehicle_engine: 'medium', window: 'medium', doorway: 'medium', splash_fire: 'medium', vehicle: 'vehicle', vehicle_small: 'vehicle', boat_deck: 'vehicle', pool: 'pool', oil_slick: 'pool', grass: 'grass', building: 'large', roof: 'large', blast_small: 'medium', blast_medium: 'large', blast_large: 'large', blast_fuel: 'pool', blast_ground: 'large', debris_slow: null, debris_med: null, debris_fast: null, front_lead: 'grass' };
  const REF = { camp: 3, medium: 5, large: 12, vehicle: 6, pool: 9, grass: 8, tree: 6, gas: 2 };
  const XF = { camp: [12, 40], medium: [20, 64], large: [45, 144], vehicle: [22, 72], pool: [32, 104], grass: [25, 80], tree: [22, 72] };
  const NEARMAX = { camp: 40, medium: 64, large: 144, vehicle: 72, pool: 104, grass: 80, tree: 72, gas: 30 }, FARMAX = { camp: 40, medium: 75, large: 220, vehicle: 110, pool: 160, grass: 130, tree: 100 };
  const WOOD = new Set(['building', 'roof', 'window', 'doorway', 'tree_trunk', 'tree_crown', 'shrub', 'debris', 'campfire']);
  const SMALLN = new Set(['campfire', 'barrel', 'torch', 'flare', 'spot_fire', 'gas', 'gas_jet', 'grass', 'debris', 'shrub', 'vehicle_engine', 'window', 'doorway', 'lick', 'splash_fire', 'tree_trunk']);
  const sm = (a, b, x) => { const t = Math.max(0, Math.min(1, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  const Lis = () => { const L = Snd.L; return L ? L : { x: camera.position.x, z: camera.position.z, rx: 1, rz: 0, y: camera.position.y }; };
  const ready = () => Snd.ready && Snd.on && Snd.ctx && Snd.ctx.state === 'running';
  /* ---- one-shots: stem families, minimum gap and a voice class cap ---- */
  const SH = {
    pop: ['fire_pop_ember', 0.11, 'fwpop', 3], spark: ['fire_spark', 0.09, 'fwspark', 3], log_crack: ['fire_log_crack', 0.35, 'fwcrack', 2], beam_creak: ['fire_beam_creak', 3.5, 'fwcreak', 1], glass: ['fire_glass', 0.7, 'fwglass', 2],
    flare_small: ['fire_flare_small', 0.9, 'fwflare', 2], flare_medium: ['fire_flare_medium', 1.5, 'fwflare', 2], flare_large: ['fire_flare_large', 3, 'fwflareL', 1], ignite_soft: ['fire_ignite_soft', 0.6, 'fwign', 2], ignite_large: ['fire_ignite_large', 2.5, 'fwignL', 1],
    tank_burst: ['fire_tank_burst', 1.5, 'fwtank', 2], lick: ['fire_lick', 0.45, 'fwlick', 3], collapse: ['fire_collapse', 6, 'fwcol', 1], clatter: ['fire_clatter', 0.9, 'fwclat', 2], water_short: ['fire_water_hiss_short', 0.25, 'fwhiss', 3], water_long: ['fire_water_hiss_long', 1.2, 'fwhissL', 2],
    out_fade: ['fire_out_fade', 0.8, 'fwout', 2], sizzle: ['fire_sizzle', 1.2, 'fwsizz', 2],
  };
  const FARSTEM = { flare_large: 'fire_flare_large_far', tank_burst: 'fire_tank_burst_far', collapse: 'fire_collapse_far' };
  const MAXD = { pop: 40, spark: 35, log_crack: 70, beam_creak: 80, glass: 90, flare_small: 60, flare_medium: 110, flare_large: 220, ignite_soft: 60, ignite_large: 220, tank_burst: 260, lick: 45, collapse: 300, clatter: 60, water_short: 80, water_long: 100, out_fade: 70, sizzle: 30 };
  let capsSet = false;
  F.sndEv = (kind, x, z, o) => {
    if (!ready()) return null; o = o || {}; const d = SH[kind]; if (!d) return null;
    if (!capsSet) { capsSet = true; for (const k in SH) { const e = SH[k]; if (Snd.caps && Snd.caps[e[2]] === undefined) Snd.caps[e[2]] = e[3]; } }
    const L = Lis(), dist = Math.hypot(x - L.x, z - L.z); if (dist > (MAXD[kind] || 100) * (FARSTEM[kind] ? 2.6 : 1)) return null;
    let stem = d[0]; if (FARSTEM[kind] && dist > 150) stem = FARSTEM[kind];
    S.n.shots++; S.played[kind] = (S.played[kind] || 0) + 1;
    return Snd.fx(stem, x, z, { gain: o.gain === undefined ? 1 : o.gain, gap: d[1], cls: d[2], y: o.y, delay: o.delay, q: true });
  };
  F.sndEvAt = (kind, f, o) => F.sndEv(kind, f.x, f.z, Object.assign({ y: f.y + 1 }, o));
  /* ---- lifecycle events ---- */
  const _spawn = F.spawn;
  F.afterExtinguish = ((prev) => (f) => {
    if (prev) prev(f); const big = ['building', 'roof', 'vehicle', 'pool', 'oil_slick', 'boat_deck', 'tree_crown', 'blast_large', 'blast_fuel', 'blast_medium'].includes(f.name);
    if (f.hit > 0) F.sndEvAt(big ? 'water_long' : 'water_short', f, { gain: 0.9 });
    F.sndEvAt('out_fade', f, { delay: 0.4, gain: big ? 1 : 0.8 }); F.sndEvAt('sizzle', f, { delay: 1.6, gain: 0.8 });
  })(F.afterExtinguish);
  F.onIgnite = (f) => {
    if (/^tree/.test(f.name) || f.name === 'shrub' || f.name === 'lick' || /^debris_/.test(f.name)) return;
    const big = ['pool', 'oil_slick', 'blast_fuel', 'vehicle', 'boat_deck', 'building', 'roof'].includes(f.name);
    if (big) { F.sndEvAt('ignite_large', f, { gain: 0.9 }); S.duck = 0.45; S.duckT = 1.2; } else if (f.name !== 'spot_fire' || Math.random() < 0.5) F.sndEvAt('ignite_soft', f, { gain: 0.8 });
  };
  /* ---- loops: cluster the fires, pick the nearest few classes, crossfade near and far ---- */
  const cl = new Map();
  function clusters() {
    cl.clear(); const L = Lis();
    const add = (cls, x, z, str, n) => {
      if (!cls) return; const cx = Math.round(x / 15), cz = Math.round(z / 15), key = cls + ':' + cx + ':' + cz; let c = cl.get(key);
      if (!c) { c = { key, cls, x: 0, z: 0, w: 0, n: 0, str: 0 }; cl.set(key, c); } c.x += x * (str + 0.05); c.z += z * (str + 0.05); c.w += str + 0.05; c.n += n; c.str = Math.max(c.str, str);
    };
    for (const f of F.alive || []) {
      if (f.dead || !(f.state === 'burn' || f.state === 'grow' || f.state === 'decay' || f.state === 'residue' || f.state === 'plume' || f.state === 'fireball' || f.state === 'ignite')) continue;
      let cls = CLS[f.name]; if (!cls) continue; const T = f._T; const e = Math.max(0.2, Math.min(1.1, f.e || 1)); const ph = f.state === 'ignite' ? 0.25 : f.state === 'grow' ? 0.65 : f.state === 'decay' ? 0.5 : 1;
      add(cls, f.x, f.z, Math.min(1, Math.sqrt(f.F)) * ph * (0.6 + 0.4 * e) * f.fade, 1);
    }
    if (F.G) for (const fr of F.G.fronts) { let n = 0; for (const c of fr.cols) if (!c.dead) n++; if (n) add('grass', fr.x0 + fr.ux * fr.d, fr.z0 + fr.uz * fr.d, Math.min(1, 0.4 + n * 0.12), Math.max(1, n >> 1)); }
    for (const c of cl.values()) { c.x /= c.w; c.z /= c.w; c.d = Math.hypot(c.x - L.x, c.z - L.z); if (c.cls === 'medium' && c.n > 12) c.cls = 'large'; c.pr = c.str * (REF[c.cls] + 4) / (c.d + REF[c.cls]); }
    return [...cl.values()].sort((a, b) => b.pr - a.pr);
  }
  F.soundTick = (dt) => {
    S.tickT -= dt; S.duckT -= dt; if (S.duckT <= 0) S.duck += (1 - S.duck) * Math.min(1, dt * 1.5); if (S.tickT > 0) return; const step = 0.25; S.tickT = step;
    if (!ready() || F.q === 'off') { if (S.keys.size) { for (const k of S.keys) Snd.set(k, 'fire_camp_loop', 0, {}); S.keys.clear(); } return; }
    const L = Lis(), maxL = PH ? 3 : 6, list = clusters(), live = new Set(); let used = 0;
    const station = Snd.stnOn;
    for (const c of list) {
      if (used >= maxL) break; const cls = c.cls, d = c.d; if (d > (FARMAX[cls] || NEARMAX[cls] || 60) * 1.02) continue; used++;
      const boost = Math.min(2, Math.pow(10, Math.min(6, 3 * Math.log2(Math.max(1, c.n))) / 20)), g = Math.min(1, REF[cls] / Math.max(d, 0.5)), lv = c.str * boost * S.duck * 0.9, dx = c.x - L.x, dz = c.z - L.z, len = Math.hypot(dx, dz) || 1, pan = Math.max(-0.9, Math.min(0.9, (dx * L.rx + dz * L.rz) / len * Math.min(1, len / 10)));
      const xf = XF[cls]; let nearL = 0, farL = 0;
      if (xf) { const w = sm(0, 1, (Math.log(Math.max(d, 1)) - Math.log(xf[0])) / (Math.log(xf[1]) - Math.log(xf[0]))); nearL = Math.cos(w * Math.PI / 2) * g * lv; farL = Math.sin(w * Math.PI / 2) * g * lv; if (d > NEARMAX[cls]) nearL = 0; farL *= 1 - sm(0.85, 1, d / (FARMAX[cls] || 100)); }
      else { nearL = g * lv * (1 - sm(0.85, 1, d / NEARMAX[cls])); }
      const ns = station && (cls === 'medium' || cls === 'large') ? 'fire_' + cls + '_loop_int' : 'fire_' + cls + '_loop', fs = 'fire_' + cls + '_loop_far';
      const cut = station ? 2400 : 20000;
      if (nearL > 0.004) { Snd.set('fw:' + c.key + ':n', ns, nearL, { pan, tc: 0.3, cut }); live.add('fw:' + c.key + ':n'); }
      if (xf && farL > 0.004) { Snd.set('fw:' + c.key + ':f', station ? 'fire_' + cls + '_loop_far' : fs, farL, { pan, tc: 0.3, cut }); live.add('fw:' + c.key + ':f'); }
    }
    for (const k of S.keys) if (!live.has(k)) Snd.set(k, 'fire_camp_loop', 0, { tc: 0.4 });
    S.keys = live; S.n.loops = live.size;
    // the faraway bed
    let far = 0; for (const c of list) if (c.d > 60) far += c.str * c.n * Math.min(1, 150 / c.d) * 0.12; Snd.set('fw:distant', 'fire_distant_loop', Math.min(0.5, far) * S.duck, { tc: 0.8 });
    // one-shots: pops and cracks from the nearest burning things, flare-ups, licks
    S.acc += step; const burn = (F.alive || []).filter(f => !f.dead && f.state === 'burn' && f._d < 70).sort((a, b) => a._d - b._d).slice(0, 3);
    let pops = 0;
    for (const f of burn) {
      const e = Math.max(0.3, Math.min(1.2, f.e || 1)), nm = f.name;
      if (f._d < 40 && pops < 2 && Math.random() < (0.4 + 2.2 * e * Math.min(1, f.F)) * step * (SMALLN.has(nm) ? 0.6 : 1)) { F.sndEvAt('pop', f, { gain: 0.5 + 0.3 * Math.random() }); pops++; }
      if (WOOD.has(nm) && Math.random() < (0.05 + 0.3 * e) * step) F.sndEvAt('log_crack', f, { gain: 0.8 });
      if ((nm === 'building' || nm === 'roof') && Math.random() < step / 11) F.sndEvAt('beam_creak', f, { gain: 0.8 });
      if (!SMALLN.has(nm) || nm === 'vehicle_engine') { if (Math.random() < 0.3 * step) F.sndEvAt('lick', f, { gain: 0.7 }); }
      if ((nm === 'vehicle' || nm === 'pool' || nm === 'oil_slick' || nm === 'boat_deck') && Math.random() < 0.15 * step) F.sndEvAt('spark', f, { gain: 0.6 });
      const T = f._T; const eNow = T ? F.energy(f, T) : 1; if (f._ePrev !== undefined && eNow > f._ePrev * 1.4 + 0.3 && f._ePrev > 0.15) { F.sndEvAt(f.F > 1.2 || nm === 'building' || nm === 'pool' ? 'flare_large' : f.F > 0.8 ? 'flare_medium' : 'flare_small', f, { gain: 0.8 }); } f._ePrev = eNow;
    }
  };
  const _frame = F.frame;
  F.frame = (dt) => { _frame(dt); try { F.soundTick(dt); } catch (e) { S.err = String(e); } };
  const _spawn2 = F.spawn;
  F.spawn = (name, x, y, z, o) => { const f = _spawn2(name, x, y, z, o); if (f && !(o && o.silent)) { try { F.onIgnite(f); } catch (e) { } } return f; };
})();
/*FW-END part1f*/
