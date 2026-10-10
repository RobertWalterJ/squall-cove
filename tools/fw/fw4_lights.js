/*FW-START part4: lights pack (modelled towers, floodlights, lamps, generators, strings, searchlights, cables) and strong-light effects (cones, beam glow, flares, ground pools, wet smears)*/
(() => {
  const F = FW, R = F.R, PH = ED.phone;
  const L4 = F.L = { pack: null, loading: null, failed: false, pk: null, fx: null, cables: [], beams: [], search: [], stats: { models: 0, cables: 0, cones: 0, flares: 0, glows: 0, pools: 0, wets: 0 } };
  const gnd = (x, z) => Math.max(heightAt(x, z), 0);
  const sm = (a, b, x) => { const t = Math.max(0, Math.min(1, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  const clamp01 = (x) => Math.max(0, Math.min(1, x));
  /* ---- the pack: loaded once, on the first battle (fixtures wait for it), 0.4 MB ---- */
  F.pack = () => {
    if (L4.pack) return Promise.resolve(L4.pack); if (L4.loading) return L4.loading;
    L4.loading = loadGLB('lights_pack').then(g => {
      L4.pack = g;
      const off = new THREE.MeshStandardMaterial({ color: 0xd8cfbf, roughness: 0.4, metalness: 0.1 }), on = new THREE.MeshBasicMaterial({ color: 0xfff0c0, toneMapped: false }), indOff = new THREE.MeshStandardMaterial({ color: 0x1d3a22, roughness: 0.4 }), indOn = new THREE.MeshBasicMaterial({ color: 0x66ff88, toneMapped: false });
      g.scene.traverse(o => { if (o.isMesh && o.material) { const n = o.material.name; if (n === 'lamp_off') { off.copy(o.material); off.name = 'lamp_off'; } else if (n === 'ind_off') { indOff.copy(o.material); } } });
      L4.pk = { off, on, indOff, indOn };
      L4.meta = {}; g.scene.traverse(o => { if (o.name && /^(lightpt_|cable_|smoke_|pivot_|searchlight_)/.test(o.name)) L4.meta[o.name] = true; });
      return g;
    }).catch(e => { L4.failed = true; L4.err = String(e); return null; });
    return L4.loading;
  };
  /* a fixture builder asks to wait for the pack once; if it cannot load, the procedural models are used */
  F.packWait = (fn) => { if (F.q === 'off' || L4.pack || L4.failed) return false; if (L4.waiting) return true; L4.waiting = true; F.pack().then(() => { L4.waiting = false; fn(); }, () => { L4.waiting = false; fn(); }); return true; };
  const NAMES = { tower: 'light_tower', flood: 'floodlight_pole_2', gen: 'generator_medium', string: 'string_lights_8m', search: 'searchlight_ground' };
  const FEED = { tower: 'cable_light_tower_ext', flood: 'cable_floodlight_pole_2_feed', lamp_cobra: 'cable_lamp_cobra', lamp_harbour: 'cable_lamp_harbour', string: 'cable_string_lights_8m_a', search: 'cable_searchlight_power' };
  const lensProxy = (meshes, ind) => ({ meshes, set material(m) { const pk = L4.pk; const mm = m === LENSON ? pk.on : m === GENON ? pk.indOn : (ind ? pk.indOff : pk.off); for (const x of this.meshes) x.material = mm; }, get material() { return this.meshes[0] ? this.meshes[0].material : null; } });

  /* the pack's pieces are many small meshes; merge the static ones by material (and each lens group into one mesh) so a base costs a few draw calls, not a few hundred */
  function mergeGeos(geos, colors) {
    let nv = 0, ni = 0; for (const g of geos) { nv += g.attributes.position.count; ni += g.index ? g.index.count : g.attributes.position.count; }
    const pos = new Float32Array(nv * 3), idx = new Uint32Array(ni), col = colors ? new Float32Array(nv * 3) : null; let vo = 0, io = 0, gi = 0;
    for (const g of geos) { pos.set(g.attributes.position.array, vo * 3); const n = g.attributes.position.count; if (col) { const c = colors[gi++]; for (let i = 0; i < n; i++) { col[(vo + i) * 3] = c.r; col[(vo + i) * 3 + 1] = c.g; col[(vo + i) * 3 + 2] = c.b; } } if (g.index) { for (let i = 0; i < g.index.count; i++) idx[io + i] = g.index.array[i] + vo; io += g.index.count; } else { for (let i = 0; i < n; i++) idx[io + i] = vo + i; io += n; } vo += n; }
    const out = new THREE.BufferGeometry(); out.setAttribute('position', new THREE.BufferAttribute(pos, 3)); if (col) out.setAttribute('color', new THREE.BufferAttribute(col, 3)); out.setIndex(new THREE.BufferAttribute(idx, 1)); out.computeBoundingSphere(); return out;
  }
  const _m4 = new THREE.Matrix4(), _inv = new THREE.Matrix4();
  let PKMAT = null;
  const pkMat = () => PKMAT || (PKMAT = new THREE.MeshStandardMaterial({ vertexColors: true, flatShading: true, roughness: 0.55, metalness: 0.35 }));
  /* meshes -> one mesh. byColour: the colours of their materials go into a vertex colour attribute and one shared material draws them all (the pack's materials are plain colours) */
  function mergeMeshes(root, meshes, byColour) {
    _inv.copy(root.matrixWorld).invert(); const geos = [], cols = [];
    for (const o of meshes) { const g = o.geometry.clone(); g.applyMatrix4(_m4.multiplyMatrices(_inv, o.matrixWorld)); geos.push(g); if (byColour) cols.push(o.material && o.material.color ? o.material.color : { r: 0.5, g: 0.5, b: 0.5 }); }
    const m = new THREE.Mesh(mergeGeos(geos, byColour ? cols : null), byColour ? pkMat() : meshes[0].material); m.castShadow = false; m.receiveShadow = false; m.matrixAutoUpdate = false; m.frustumCulled = true; for (const g of geos) g.dispose(); return m;
  }
  function mergeModel(g, lensSets) {
    g.updateMatrixWorld(true); const lensAll = new Set(); for (const set of lensSets) for (const m of set) lensAll.add(m);
    const stat = []; g.traverse(o => { if (o.isMesh && !lensAll.has(o) && o.geometry && o.material) stat.push(o); });
    const out = stat.length ? mergeMeshes(g, stat, true) : null;
    const lensOut = lensSets.map(set => set.length ? [mergeMeshes(g, set, false)] : []);
    for (const o of stat) o.parent && o.parent.remove(o); for (const set of lensSets) for (const o of set) o.parent && o.parent.remove(o);
    if (out) g.add(out); for (const arr of lensOut) for (const m of arr) g.add(m);
    return lensOut;
  }
  F.fixModel = (kind, p) => {
    if (F.q === 'off' || !L4.pack) return null; const nm = kind === 'lamp' ? ((p && (p.type === 'harbour' || p.type === 'radio' || p.type === 'depot')) ? 'lamp_harbour' : 'lamp_cobra') : NAMES[kind]; if (!nm) return null;
    const src = nodeByName(L4.pack, nm); if (!src) return null; const g = new THREE.Group(), c = src.clone(true); g.add(c); g.userData.pkName = nm; g.userData.pkKind = kind;
    const lens = [], ind = []; g.updateMatrixWorld(true);
    const lpts = []; c.traverse(o => { if (o.name && o.name.startsWith('lightpt_') && o.userData && o.userData.light) lpts.push(o); });
    c.traverse(o => { if (o.isMesh) { o.castShadow = false; o.receiveShadow = false; const n = o.material && o.material.name; if (n === 'lamp_off') lens.push(o); else if (n === 'ind_off') ind.push(o); } });
    if (kind === 'tower') {                                                  // two groups, front and back, like the two bars before
      const groups = { front: [], back: [] }; const pf = lpts.filter(o => o.userData.light.group === 'front'), pb = lpts.filter(o => o.userData.light.group === 'back'); const mid = (arr) => { const v = new THREE.Vector3(); for (const o of arr) { const w = new THREE.Vector3(); o.getWorldPosition(w); v.add(w); } return v.multiplyScalar(1 / Math.max(1, arr.length)); }, zf = mid(pf).z, zb = mid(pb).z;
      for (const m of lens) { const w = new THREE.Vector3(); m.getWorldPosition(w); (Math.abs(w.z - zf) < Math.abs(w.z - zb) ? groups.front : groups.back).push(m); }
      g.userData.lens = [[lensProxy(groups.front)], [lensProxy(groups.back)]];
    } else if (kind === 'gen') g.userData.lens = [[lensProxy(ind, true)]];
    else g.userData.lens = [[lensProxy(lens)]];
    if (kind !== 'search') {                                                  // static pieces merged; each lens group becomes one mesh the proxy can swap
      const sets = kind === 'tower' ? [g.userData.lens[0][0].meshes, g.userData.lens[1][0].meshes] : kind === 'gen' ? [ind] : [lens], merged = mergeModel(g, sets);
      if (kind === 'tower') { g.userData.lens = [[lensProxy(merged[0])], [lensProxy(merged[1])]]; } else if (kind === 'gen') g.userData.lens = [[lensProxy(merged[0], true)]]; else g.userData.lens = [[lensProxy(merged[0])]];
    }
    g.userData.lpts = lpts; L4.stats.models++; return g;
  };
  /* what each fixture record learns from its model: lamp position, beam direction, cone and range from the pack's own empties */
  const _p = new THREE.Vector3(), _q = new THREE.Quaternion(), _d = new THREE.Vector3();
  F.fixFit = (f, g, kind, sp, yaw) => {
    if (!g.userData.pkName) return; g.updateMatrixWorld(true); const lp = g.userData.lpts || [];
    f.glb = true; f.pkName = g.userData.pkName; f.glow = (f.glow || 1) * 0.35; f.pool = 0;
    let mine = lp.filter(o => o.userData.light.type !== 'indicator'); if (kind === 'tower') { const gi = g.userData.lens.indexOf(f.lens); const grp = gi === 0 ? 'front' : 'back'; mine = mine.filter(o => o.userData.light.group === grp); }
    if (kind === 'gen' || !mine.length) { return; }
    let cx = 0, cy = 0, cz = 0, dx = 0, dy = 0, dz = 0, cone = 0, range = 0; for (const o of mine) { o.getWorldPosition(_p); o.getWorldQuaternion(_q); _d.set(0, 0, 1).applyQuaternion(_q); cx += _p.x; cy += _p.y; cz += _p.z; dx += _d.x; dy += _d.y; dz += _d.z; cone = Math.max(cone, o.userData.light.cone_deg || 60); range = Math.max(range, o.userData.light.range || 30); }
    const n = mine.length, dl = Math.hypot(dx, dy, dz) || 1; f.x = cx / n; f.y = cy / n; f.z = cz / n; f.beam = { dx: dx / dl, dy: dy / dl, dz: dz / dl, cone, range, lens: kind === 'tower' ? 0.6 : kind === 'search' ? 0.7 : kind === 'flood' ? 0.4 : 0.28 };
    if (kind === 'search') { const y = nodeByName({ scene: g }, 'searchlight_yoke'), h = nodeByName({ scene: g }, 'searchlight_head'); f.yoke = y; f.head = h; f.swA = Math.random() * 6; f.swYaw = yaw; f.beamPt = lp.find(o => o.userData.light.type === 'spot'); L4.search.push(f); }
  };
  /* ---- cables: from a generator socket to each light it feeds, lying on the ground (a sagged tube through sampled terrain heights) ---- */
  const cableMat = new THREE.MeshStandardMaterial({ color: 0x1b1d1f, roughness: 0.9, metalness: 0.05 });
  function merge(list) {
    let nv = 0, ni = 0; for (const g of list) { nv += g.attributes.position.count; ni += g.index.count; } const pos = new Float32Array(nv * 3), nor = new Float32Array(nv * 3), idx = new Uint32Array(ni); let vo = 0, io = 0;
    for (const g of list) { pos.set(g.attributes.position.array, vo * 3); nor.set(g.attributes.normal.array, vo * 3); for (let i = 0; i < g.index.count; i++) idx[io + i] = g.index.array[i] + vo; vo += g.attributes.position.count; io += g.index.count; g.dispose(); }
    const out = new THREE.BufferGeometry(); out.setAttribute('position', new THREE.BufferAttribute(pos, 3)); out.setAttribute('normal', new THREE.BufferAttribute(nor, 3)); out.setIndex(new THREE.BufferAttribute(idx, 1)); return out;
  }
  const emptyW = (g, name) => { let e = null; g.traverse(o => { if (!e && o.name === name) e = o; }); if (!e) return null; e.updateWorldMatrix(true, false); return e.getWorldPosition(new THREE.Vector3()); };
  function tube(a, b) {
    const pts = [a.clone()], dx = b.x - a.x, dz = b.z - a.z, len = Math.hypot(dx, dz), n = Math.max(2, Math.round(len / 1.6)), ux = dx / (len || 1), uz = dz / (len || 1);
    pts.push(new THREE.Vector3(a.x + ux * 0.5, gnd(a.x + ux * 0.5, a.z + uz * 0.5) + 0.05, a.z + uz * 0.5));
    for (let i = 1; i < n; i++) { const t = i / n, x = a.x + dx * t, z = a.z + dz * t; pts.push(new THREE.Vector3(x, gnd(x, z) + 0.045 + 0.02 * Math.sin(t * 9), z)); }
    pts.push(new THREE.Vector3(b.x - ux * 0.5, gnd(b.x - ux * 0.5, b.z - uz * 0.5) + 0.05, b.z - uz * 0.5)); pts.push(b.clone());
    const curve = new THREE.CatmullRomCurve3(pts, false, 'centripetal'); return new THREE.TubeGeometry(curve, pts.length * 3, 0.026, 5, false);
  }
  F.fixCables = (p) => {
    if (F.q === 'off' || !L4.pack || !p.lights) return; const gen = p.lights.gen; if (!gen || !gen.model || !gen.model.userData.pkName) return;
    const geos = []; let gi = 0;
    for (const f of LIGHT.fix) {
      if (f.p !== p || f.gen !== gen || !f.glb || f === gen) continue; const feed = f.pkName === 'lamp_cobra' ? FEED.lamp_cobra : f.pkName === 'lamp_harbour' ? FEED.lamp_harbour : FEED[f.model.userData.pkKind];
      const A = emptyW(gen.model, 'cable_generator_medium_out_' + (gi++ % 4)), B = feed && emptyW(f.model, feed); if (!A || !B) continue; geos.push(tube(A, B));
    }
    if (geos.length) { const m = new THREE.Mesh(merge(geos), cableMat); m.frustumCulled = false; m.castShadow = false; scene.add(m); L4.cables.push(m); p._fwCable = m; L4.stats.cables += geos.length; }
    // a searchlight sweeping over the base, fed from the same generator, at the bigger points
    if (['hq', 'airfield', 'harbour'].includes(p.type) && !p._fwSearch) { p._fwSearch = true; const a0 = p.x * 0.011 + p.z * 0.009 + 2.3; try { const s = fixPlace(p, 'search', a0 + 2.4, 20, gen, 'out'); if (s) { fixCablesOne(p, gen, s); } } catch (e) { L4.err = String(e); } }
  };
  function fixCablesOne(p, gen, f) { if (!f.glb) return; const A = emptyW(gen.model, 'cable_generator_medium_out_3'), B = emptyW(f.model, FEED.search); if (!A || !B) return; const m = new THREE.Mesh(merge([tube(A, B)]), cableMat); m.frustumCulled = false; scene.add(m); L4.cables.push(m); L4.stats.cables++; }
  F.fixClear = () => { for (const m of L4.cables) { scene.remove(m); m.geometry.dispose(); } L4.cables.length = 0; L4.search.length = 0; };
  /* a searchlight sweeps: yaw back and forth, a little pitch; its beam feeds a spot light and the strong-light effects */
  const _sw = new THREE.Vector3(), _sq = new THREE.Quaternion();
  F.fixWant = (f, lk) => {
    if (!f.glb || f.kind !== 'search') return false; if (f.on < 0.02) return true;
    const dt = F.lastDt || 0.016; f.swA += dt * 0.3; if (f.yoke) f.yoke.rotation.y = f.swYaw + Math.sin(f.swA) * 1.15 + f.swA * 0.0; if (f.head) f.head.rotation.x = -0.14 - 0.06 * Math.sin(f.swA * 1.7);
    f.model.updateMatrixWorld(true); const o = f.beamPt; if (!o) return true; o.getWorldPosition(_sw); o.getWorldQuaternion(_sq); _d.set(0, 0, 1).applyQuaternion(_sq);
    f.x = _sw.x; f.y = _sw.y; f.z = _sw.z; f.beam.dx = _d.x; f.beam.dy = _d.y; f.beam.dz = _d.z;
    lightWant('fx' + f.id, 'spot', f.x, f.y, f.z, 1, 0.96, 0.88, f.I * f.on, 190, 2.2, { dx: _d.x, dy: _d.y, dz: _d.z, ang: 0.13, glow: 0.4, glowA: 0.9, k: f.on }); return true;
  };

  /* ---- the strong-light effects ---- */
  const TEX = {};
  const loadFxTex = (name) => R.loadTex('assets/' + name);
  F.fxLoad = () => {
    if (L4.fx || L4.fxLoading) return; L4.fxLoading = true;
    Promise.all(['lights_fx_cone.png', 'lights_fx_beam_glow.png', 'lights_fx_flare.png', 'lights_fx_pool.png', 'lights_fx_wet.png'].map(loadFxTex)).then(([cone, glow, flare, pool, wet]) => { L4.fx = { cone, glow, flare, pool, wet }; initFx(); }).catch(e => { L4.fxErr = String(e); L4.fxLoading = false; });
  };
  const CAPS = () => ({ cone: PH ? 0 : 6, flare: PH ? 6 : 12, glow: PH ? 4 : 16, pool: PH ? 6 : 14, wet: PH ? 0 : 8 });
  let fxMesh = null, coneGeo = null; const cones = [];
  const instMat = (tex, vs, fs, order, extra) => new THREE.ShaderMaterial({ uniforms: Object.assign({ tMap: { value: tex }, uPx: { value: 800 } }, extra || {}), vertexShader: vs, fragmentShader: fs, transparent: true, depthWrite: false, depthTest: true, side: THREE.DoubleSide, fog: false, toneMapped: false, blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor, blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneFactor });
  function mkInst(cap, attrs, mat, order) {
    const g = new THREE.InstancedBufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(new Float32Array([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, 1, 0]), 3)); g.setIndex([0, 1, 2, 0, 2, 3]); const bufs = {};
    for (const [nm, n] of attrs) { const a = new Float32Array(cap * n); const at = new THREE.InstancedBufferAttribute(a, n); at.setUsage(THREE.DynamicDrawUsage); g.setAttribute(nm, at); bufs[nm] = at; } g.instanceCount = 0;
    const m = new THREE.Mesh(g, mat); m.frustumCulled = false; m.renderOrder = order; scene.add(m); return { g, m, bufs, n: 0, cap };
  }
  let FL = null, GL = null, PL = null, WT = null;
  function initFx() {
    const caps = CAPS();
    // flares: spherical billboards, size set in world metres from a pixel size
    FL = mkInst(caps.flare, [['aP', 4], ['aC', 4]], instMat(L4.fx.flare, 'attribute vec4 aP; attribute vec4 aC; varying vec2 vUv; varying vec4 vC; void main(){ vUv = position.xy * 0.5 + 0.5; vC = aC; vec3 toC = cameraPosition - aP.xyz; vec3 f = normalize(toC); vec3 r = normalize(cross(vec3(0.0, 1.0, 0.0), f) + vec3(1e-5, 0.0, 0.0)); vec3 u = cross(f, r); vec3 wp = aP.xyz + f * 0.25 + (r * position.x + u * position.y) * aP.w; gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0); }', 'precision highp float; uniform sampler2D tMap; varying vec2 vUv; varying vec4 vC; void main(){ vec4 t = texture2D(tMap, vUv); float a = t.a * vC.a; float l = max(t.r, max(t.g, t.b)); vec3 c = (t.a > 0.01 ? t.rgb : vec3(l)) * vC.rgb; gl_FragColor = vec4(c * a, a * 0.0); }', 0, {}), 8.4);
    // beam glow strips
    GL = mkInst(caps.glow, [['aP', 4], ['aD', 4], ['aC', 4]], instMat(L4.fx.glow, 'attribute vec4 aP; attribute vec4 aD; attribute vec4 aC; varying vec2 vUv; varying vec4 vC; void main(){ float s = position.x * 0.5 + 0.5; vUv = vec2(s, position.y * 0.5 + 0.5); vC = aC; vec3 mid = aP.xyz + aD.xyz * aD.w * 0.5; vec3 toC = normalize(cameraPosition - mid); vec3 side = cross(aD.xyz, toC); float sl = length(side); side = sl > 1e-4 ? side / sl : vec3(0.0, 1.0, 0.0); float w = aP.w * (0.25 + 0.75 * s); vec3 wp = aP.xyz + aD.xyz * aD.w * s + side * position.y * w; gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0); }', 'precision highp float; uniform sampler2D tMap; varying vec2 vUv; varying vec4 vC; void main(){ vec4 t = texture2D(tMap, vUv); float a = t.a * vC.a; gl_FragColor = vec4(vC.rgb * a, 0.0); }', 0, {}), 8.3);
    // ground pools and wet smears: flat quads on the ground
    const flatVS = 'attribute vec4 aP; attribute vec4 aD; attribute vec4 aC; varying vec2 vUv; varying vec4 vC; void main(){ vUv = position.xy * 0.5 + 0.5; vC = aC; float c = cos(aD.x), s = sin(aD.x); vec2 l = vec2(position.x * aD.y, position.y * aD.z); vec3 wp = vec3(aP.x + l.x * c - l.y * s, aP.y, aP.z + l.x * s + l.y * c); gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0); }', flatFS = 'precision highp float; uniform sampler2D tMap; varying vec2 vUv; varying vec4 vC; void main(){ vec4 t = texture2D(tMap, vUv); float a = t.a * vC.a; gl_FragColor = vec4(vC.rgb * a, 0.0); }';
    const pm = instMat(L4.fx.pool, flatVS, flatFS, 0, {}); pm.polygonOffset = true; pm.polygonOffsetFactor = -3; pm.polygonOffsetUnits = -3; PL = mkInst(caps.pool, [['aP', 4], ['aD', 4], ['aC', 4]], pm, 2.1);
    const wm = instMat(L4.fx.wet, flatVS, flatFS, 0, {}); wm.polygonOffset = true; wm.polygonOffsetFactor = -4; wm.polygonOffsetUnits = -4; WT = mkInst(caps.wet || 1, [['aP', 4], ['aD', 4], ['aC', 4]], wm, 2.2);
    // cones: the open cone with the baked gradient, one mesh each (at most six), plus a thin hot core
    const seg = 24, pos = [], uv = [], idx = []; for (let i = 0; i <= seg; i++) { const a = i / seg * Math.PI * 2, c = Math.cos(a) * 0.5, s = Math.sin(a) * 0.5; pos.push(0, 0, 0, c, s, 1); uv.push(0, i / seg, 1, i / seg); } for (let i = 0; i < seg; i++) { const b = i * 2; idx.push(b, b + 1, b + 3, b, b + 3, b + 2); }
    coneGeo = new THREE.BufferGeometry(); coneGeo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); coneGeo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); coneGeo.setIndex(idx);
    for (let i = 0; i < caps.cone * 2; i++) {
      const mat = new THREE.ShaderMaterial({ uniforms: { tMap: { value: L4.fx.cone }, uA: { value: 0 }, uCol: { value: new THREE.Color(1, 0.93, 0.78) }, uT: { value: 0 } }, vertexShader: 'varying vec2 vUv; varying vec3 vN; varying vec3 vV; void main(){ vUv = uv; vec4 mv = modelViewMatrix * vec4(position, 1.0); float th = uv.y * 6.2831853; vN = normalize(normalMatrix * vec3(cos(th), sin(th), -0.5)); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }', fragmentShader: 'precision highp float; uniform sampler2D tMap; uniform float uA; uniform vec3 uCol; uniform float uT; varying vec2 vUv; varying vec3 vN; varying vec3 vV; void main(){ vec4 t = texture2D(tMap, vec2(vUv.x, fract(vUv.y + uT))); float a = t.a; float e = pow(abs(dot(normalize(vN), normalize(vV))), 1.5); float al = a * e * uA; gl_FragColor = vec4(uCol * al, 0.0); }', transparent: true, depthWrite: false, depthTest: true, side: THREE.DoubleSide, fog: false, toneMapped: false, blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor, blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneFactor });
      const m = new THREE.Mesh(coneGeo, mat); m.frustumCulled = false; m.visible = false; m.renderOrder = 8.1; m.matrixAutoUpdate = true; scene.add(m); cones.push(m);
    }
    L4.fxReady = true;
  }
  const haze = () => {
    const A = F.A ? F.A.k : {}; let smoke = 0; for (const f of F.alive || []) { if (f.black && f.vis && f.px > 30) smoke += 0.3; } smoke = Math.min(1, smoke);
    const fog = (A.fogSky || 0), mist = Math.max(A.dawn || 0, A.valley || 0) * 0.7, rain = wx.rainAmt;
    return Math.max(0.1, Math.min(1, 0.15 + 1.0 * fog + 0.8 * mist + 1.2 * smoke * 0.5 + 0.5 * rain));
  };
  L4.haze = haze;
  const _cam = new THREE.Vector3(), _cq = new THREE.Quaternion();
  const put = (S, nm, i, a, b, c, d) => { const o = S.bufs[nm]; const v = o.array, k = i * o.itemSize; v[k] = a; v[k + 1] = b; v[k + 2] = c; v[k + 3] = d; };
  F.lightsFx = (dt) => {
    F.lastDt = dt;
    if (F.q === 'off') { if (fxMesh !== 'off' && L4.fxReady) { for (const m of cones) m.visible = false; for (const S of [FL, GL, PL, WT]) if (S) { S.g.instanceCount = 0; } fxMesh = 'off'; } return; } fxMesh = null;
    if (!LIGHT.fix.some(f => f.glb)) return; if (!L4.fxReady) { F.fxLoad(); return; }
    const lk = LIGHT.lampK, H = haze(), cam = camera.position, caps = CAPS(); const Kpx = innerHeight * renderer.getPixelRatio() / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
    camera.getWorldDirection(_d); const wet = Math.min(1, wx.rainAmt * 1.3);
    const cand = []; for (const f of LIGHT.fix) { if (!f.glb || f.kind === 'gen' || f.dead || f.on < 0.04) continue; const d = Math.hypot(f.x - cam.x, f.y - cam.y, f.z - cam.z); if (d > 700) continue; f._fd = d; cand.push(f); }
    cand.sort((a, b) => a._fd - b._fd); let nF = 0, nG = 0, nP = 0, nW = 0, nC = 0;
    for (const m of cones) m.visible = false;
    for (const f of cand) {
      const b = f.beam; if (!b) continue; const d = f._fd, on = f.on * lk, col = f.col || [1, 0.93, 0.78], toCx = (cam.x - f.x) / (d || 1), toCy = (cam.y - f.y) / (d || 1), toCz = (cam.z - f.z) / (d || 1);
      const facing = Math.max(0, b.dx * toCx + b.dy * toCy + b.dz * toCz), omni = b.cone > 100;
      // flare: bigger in haze, none from behind a spot lamp
      if (nF < caps.flare) { const px = Math.max(12, Math.min(220, 900 * b.lens / Math.max(d, 1))) * (d > 400 ? Math.max(0.4, 1 - (d - 400) / 300) : 1) * (1 + 0.8 * H); const a = on * (omni ? 0.8 : Math.pow(facing, 2) * 0.9 + 0.08) * (0.6 + 0.4 * H); if (a > 0.01) { put(FL, 'aP', nF, f.x, f.y, f.z, px * d / Kpx * 0.5); put(FL, 'aC', nF, col[0], col[1], col[2], Math.min(1, a)); nF++; } }
      if (!omni) {
        // cone near, beam strip beyond about 150 m, only the flare beyond about 400 m
        if (d < 150 && nC < caps.cone && !PH) { const len = Math.min(b.range * 0.85, 60), r = 2 * Math.tan(b.cone * 0.5 * Math.PI / 180) * len; const rx = cam.x - f.x, ry = cam.y - f.y, rz = cam.z - f.z, tt = rx * b.dx + ry * b.dy + rz * b.dz; let inside = 1; if (tt > 0 && tt < len) { const ex = rx - b.dx * tt, ey = ry - b.dy * tt, ez = rz - b.dz * tt, rad = Math.tan(b.cone * 0.5 * Math.PI / 180) * tt; if (Math.hypot(ex, ey, ez) < rad * 1.05) inside = 0.12; } const m0 = cones[nC * 2], m1 = cones[nC * 2 + 1]; if (m0) { for (const [mm, sc, k] of [[m0, 1, 0.5], [m1, 0.35, 0.35]]) { mm.visible = true; mm.position.set(f.x, f.y, f.z); _sw.set(f.x + b.dx, f.y + b.dy, f.z + b.dz); mm.lookAt(_sw); mm.scale.set(r * sc, r * sc, len); mm.material.uniforms.uA.value = on * k * (0.02 + 0.98 * H * H) * (1 - sm(110, 150, d)) * inside; mm.material.uniforms.uCol.value.setRGB(col[0], col[1], col[2]); mm.material.uniforms.uT.value = (simT * 0.01) % 1; } nC++; } }
        else if (d >= 100 && nG < caps.glow) { const len = Math.min(b.range, 120); put(GL, 'aP', nG, f.x, f.y, f.z, len * Math.tan(b.cone * 0.5 * Math.PI / 180) * 0.9 + 0.5); put(GL, 'aD', nG, b.dx, b.dy, b.dz, len); put(GL, 'aC', nG, col[0], col[1], col[2], on * (0.2 + 0.8 * H) * 0.7 * sm(100, 160, d) * (1 - sm(500, 700, d))); nG++; }
      }
      // ground pool: where the beam lands, long axis along the beam's ground projection; round for a lamp
      if (d < 130 && nP < caps.pool) {
        const gy = gnd(f.x, f.z); let cx = f.x, cz = f.z, ang = 0, a = b.range * 0.55, bb = b.range * 0.5;
        if (!omni) { const t = b.dy < -0.05 ? Math.min(b.range, (f.y - gy) / -b.dy) : b.range * 0.6; cx = f.x + b.dx * t; cz = f.z + b.dz * t; const tilt = Math.max(0.3, Math.cos(Math.asin(Math.min(0.95, Math.abs(b.dy))))); ang = Math.atan2(b.dz, b.dx); a = Math.min(b.range * 0.7, b.range * Math.tan(b.cone * 0.5 * Math.PI / 180) * 0.5 / tilt) ; bb = a * 0.6; } else { cx = f.x; cz = f.z; a = bb = b.range * 0.55; }
        put(PL, 'aP', nP, cx, gnd(cx, cz) + 0.06, cz, 1); put(PL, 'aD', nP, -ang, a, bb, 1); put(PL, 'aC', nP, col[0], col[1], col[2], on * 0.3 * (1 - 0.3 * H)); nP++;
      }
      // wet ground: a reflection smear under the lamp, pointing away from the camera
      if (wet > 0.05 && d < 70 && nW < caps.wet) { const gy = gnd(f.x, f.z), len = Math.max(2, 1.5 * (f.y - gy)), ax = f.x - cam.x, az = f.z - cam.z, al = Math.hypot(ax, az) || 1; put(WT, 'aP', nW, f.x + ax / al * len * 0.5, gy + 0.07, f.z + az / al * len * 0.5, 1); put(WT, 'aD', nW, -Math.atan2(az, ax), len * 0.5, 0.9, 1); put(WT, 'aC', nW, col[0], col[1], col[2], on * wet * 0.7); nW++; }
    }
    const fin = (S, n) => { S.g.instanceCount = n; for (const k in S.bufs) S.bufs[k].needsUpdate = true; S.n = n; };
    fin(FL, nF); fin(GL, nG); fin(PL, nP); fin(WT, nW); L4.stats.flares = nF; L4.stats.glows = nG; L4.stats.pools = nP; L4.stats.wets = nW; L4.stats.cones = nC;
  };
  F.afters.push((dt) => { try { F.lightsFx(dt); } catch (e) { L4.err = String(e && e.stack || e); } });
  F.pre0 = F.pre; F.pre = (dt) => { if (F.pre0) F.pre0(dt); if (!L4.pack && !L4.failed && !L4.loading && typeof BATTLE !== 'undefined' && (BATTLE.on || (typeof LP !== 'undefined'))) F.pack(); };
})();
/*FW-END part4*/
