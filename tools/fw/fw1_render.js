/*FW-START part1a: baked sprite renderer (fire, later steam / mist / fog share it)*/
/* ================================================================ FW: realistic baked fire (v9.9.12-fw)
   Source: tools/fw/*.js (injected by tools/fw/inject.py). Atlas format: MODEL-NOTES-FIRE-BAKED.md. Everything here is one self-contained block:
   the sprite renderer (instanced camera-facing quads, a few draw calls), the lazy atlas loader, the fire lifecycle machine, the owner sync that
   replaces the old particle fires, spread, lights, haze, sound, explosions, flaming debris, steam, mist, fog.
   The old particle code stays as the Fire quality "Off" fallback and while an atlas is still loading (FW.drawn(owner) says whether FW draws that thing). */
const FW = (() => {
  const F = { v: 'fw-1', afters: [], q: 'high', ready: false, failed: false, fires: [], types: {}, stats: {}, on: true };
  const PH = ED.phone;
  /* ---- quality: High / Low / Off. Desktop default High, phone default Low. Reduced motion lowers one step. */
  const QKEY = 'squall-cove-firequality';
  const QORD = ['off', 'low', 'high'];
  function readQ() { let q = PH ? 'low' : 'high'; try { const v = localStorage.getItem(QKEY); if (QORD.includes(v)) q = v; } catch (e) { } return q; }
  F.pref = readQ();
  F.eff = () => { let i = QORD.indexOf(F.pref); if ((REDUCE_MOTION || F.govLow) && i > 1) i = 1; return QORD[i]; };
  F.setPref = (q) => { if (!QORD.includes(q)) return; F.pref = q; try { localStorage.setItem(QKEY, q); } catch (e) { } F.govLow = false; F.applyQ(); };
  F.CAP = { high: PH ? { fires: 14, inst: 160, front: 3 } : { fires: 40, inst: 420, front: 8 }, low: PH ? { fires: 8, inst: 80, front: 2 } : { fires: 18, inst: 200, front: 4 } };
  F.cap = () => F.CAP[F.q] || F.CAP.low;
  F.applyQ = () => { F.q = F.eff(); if (F.q === 'off') { if (F.reset) F.reset(); else for (const f of F.fires.slice()) F.kill(f, true); } };

  /* ---- the sprite renderer ---- */
  const R = { combos: {}, tex: {}, loadN: 0, drawn: 0, inst: 0, dropped: 0 };
  F.R = R;
  const STRIDE = 20;
  const VS = [
    'attribute vec4 aP; attribute vec4 aS; attribute vec4 aF; attribute vec4 aT; attribute vec4 aL;',
    'uniform vec2 uAnchor; varying vec2 vUv; varying vec4 vF; varying vec4 vT; varying float vFade; varying float vH;',
    'void main(){',
    '  vec2 loc = position.xy - uAnchor; vec2 q = vec2(loc.x * aP.w * aL.z, loc.y) * aS.xy;',
    '  vec3 toCam = cameraPosition - aP.xyz; float dist = length(toCam); vec3 right; vec3 up = vec3(0.0, 1.0, 0.0); float fade = 1.0; float mq = aS.z;',
    '  if (mq < 0.5) { vec3 h = vec3(toCam.x, 0.0, toCam.z); float hl = length(h); h = hl > 1e-4 ? h / hl : vec3(0.0, 0.0, 1.0); right = vec3(h.z, 0.0, -h.x); }',
    '  else if (mq < 1.5) { vec3 f = toCam / max(dist, 1e-4); right = normalize(cross(up, f) + vec3(1e-5, 0.0, 0.0)); vec3 u2 = cross(f, right); float c = cos(aS.w), s = sin(aS.w); q = vec2(c * q.x - s * q.y, s * q.x + c * q.y); up = u2; }',
    '  else if (mq < 2.5) { right = vec3(cos(aS.w), 0.0, -sin(aS.w)); vec3 n = vec3(sin(aS.w), 0.0, cos(aS.w)); vec3 hh = vec3(toCam.x, 0.0, toCam.z); float d2 = max(length(hh), 1e-4); fade = smoothstep(0.05, 0.8, abs(dot(n, hh / d2))); }',
    '  else { right = vec3(cos(aS.w), 0.0, -sin(aS.w)); up = vec3(sin(aS.w), 0.0, cos(aS.w)); }',
    '  vec3 wp = aP.xyz + right * q.x + up * q.y;',
    '  float t = clamp(loc.y / max(1.0 - uAnchor.y, 0.001), 0.0, 1.0); wp.x += aL.x * t * t; wp.z += aL.y * t * t;',
    '  float sz = max(aS.x, aS.y); float nr = 0.25 * sz + 0.6; fade *= smoothstep(nr * 0.5, nr, dist);',
    '  vUv = position.xy; vF = aF; vT = aT; vFade = fade; vH = t;',
    '  gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0);',
    '}'].join('\n');
  const FS = [
    'precision highp float; uniform sampler2D tAtlas; uniform vec2 uGrid; uniform vec2 uInset; uniform float uSensor; uniform float uMode; uniform vec3 uLit; uniform float uCool; uniform float uEdge;',
    'varying vec2 vUv; varying vec4 vF; varying vec4 vT; varying float vFade; varying float vH;',
    'vec4 frame(float fi, vec2 uv){ float c = mod(fi, uGrid.x); float r = floor(fi / uGrid.x); vec2 u = clamp(uv, uInset, 1.0 - uInset); return texture2D(tAtlas, vec2((c + u.x) / uGrid.x, (r + 1.0 - u.y) / uGrid.y)); }',
    'vec3 hotRamp(float v){ vec3 a = vec3(0.016, 0.016, 0.055); vec3 b = vec3(0.157, 0.04, 0.35); vec3 c = vec3(0.59, 0.08, 0.27); vec3 d = vec3(0.92, 0.27, 0.08); vec3 e = vec3(1.0, 0.75, 0.16); vec3 f = vec3(1.0, 0.96, 0.67);',
    '  return v < 0.18 ? mix(a, b, v / 0.18) : v < 0.38 ? mix(b, c, (v - 0.18) / 0.2) : v < 0.58 ? mix(c, d, (v - 0.38) / 0.2) : v < 0.78 ? mix(d, e, (v - 0.58) / 0.2) : mix(e, f, clamp((v - 0.78) / 0.14, 0.0, 1.0)); }',
    'void main(){',
    '  vec4 a = frame(vF.x, vUv); vec4 o = vec4(a.rgb * a.a, a.a);',
    '  if (vF.z > 0.002) { vec4 b = frame(vF.y, vUv); o = mix(o, vec4(b.rgb * b.a, b.a), vF.z); }',
    '  float g = vF.w * vFade; if (uEdge > 0.0) g *= smoothstep(0.0, uEdge, vUv.x) * smoothstep(0.0, uEdge, 1.0 - vUv.x); vec3 rgb = o.rgb * vT.rgb; float al = o.a;',
    '  if (uMode < 0.5) {',                                                                              // flame
    '    if (uSensor > 1.5) { float l = dot(o.rgb, vec3(0.3, 0.59, 0.11)); rgb = mix(vec3(l), vec3(1.0), 0.45) * al * 4.5; }',
    '    al *= (1.0 - vT.a);',
    '  } else if (uMode < 1.5) {',                                                                       // smoke: lit by the sun/sky, and a warm underlight near the base from the baked colour
    '    rgb = o.rgb * vT.rgb; if (uSensor > 1.5) { float l = dot(o.rgb, vec3(0.3, 0.59, 0.11)); rgb = vec3(l) * 1.6; }',
    '    al *= (1.0 - vT.a);',
    '  } else if (uMode < 2.5) {',                                                                       // heat map (thermal): the game keys hot things in magenta
    '    float v = a.r; al = clamp(v * 3.0, 0.0, 1.0); if (v < 0.02) al = 0.0; rgb = vec3(1.0, 0.0, 1.0) * al * (0.35 + 0.65 * v);',
    '  } else {',                                                                                        // grey mist / steam / fog: lit by uLit, cool and faint in thermal, a bright veil in night vision
    '    rgb = o.rgb * vT.rgb * uLit; if (uSensor > 1.5) { float l = dot(rgb, vec3(0.3, 0.59, 0.11)); rgb = vec3(l) * 1.9; al *= 0.9; } if (uSensor > 0.5 && uSensor < 1.5) { rgb = vec3(0.1) * al; al *= uCool; }',
    '  }',
    '  float n = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453) - 0.5;',                // a little dither hides 8-bit banding in soft gradients
    '  vec4 outc = vec4(rgb * g, al * g); if (outc.a > 0.002) { outc.a += n * (1.6 / 255.0); outc.rgb += n * (1.3 / 255.0) * outc.a; } if (outc.a < 0.003 && uMode < 2.5) discard;',
    '  gl_FragColor = outc;',
    '}'].join('\n');
  const QUAD = new Float32Array([0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0]), QIDX = [0, 1, 2, 0, 2, 3];
  /* a combo = one atlas texture + one instanced mesh = one draw call. def: { key, tex, cols, rows, fw, fh (frame px), anchor [x from left, y from top], mode 0 flame 1 smoke 2 heat 3 mist, order, rule }
     rule: 'vis' (hidden in Thermal), 'heat' (only in Thermal), 'any' (always; mist/fog fade themselves) */
  function mkCombo(def, cap) {
    const geo = new THREE.InstancedBufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(QUAD, 3)); geo.setIndex(QIDX);
    const buf = new Float32Array(cap * STRIDE), ib = new THREE.InstancedInterleavedBuffer(buf, STRIDE, 1); ib.setUsage(THREE.DynamicDrawUsage);
    ['aP', 'aS', 'aF', 'aT', 'aL'].forEach((nm, i) => geo.setAttribute(nm, new THREE.InterleavedBufferAttribute(ib, 4, i * 4)));
    geo.instanceCount = 0;
    const mat = new THREE.ShaderMaterial({
      uniforms: { tAtlas: { value: def.tex }, uAnchor: { value: new THREE.Vector2(def.anchor[0], 1 - def.anchor[1]) }, uGrid: { value: new THREE.Vector2(def.cols, def.rows) }, uInset: { value: new THREE.Vector2(0.6 / def.fw, 0.6 / def.fh) }, uSensor: SENSOR, uMode: { value: def.mode }, uLit: { value: new THREE.Vector3(1, 1, 1) }, uCool: { value: 0.1 }, uEdge: { value: def.edge || 0 } },
      vertexShader: VS, fragmentShader: FS, transparent: true, depthWrite: false, depthTest: true, side: THREE.DoubleSide, fog: false, toneMapped: false,
      blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor, blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneMinusSrcAlphaFactor,
    });
    const mesh = new THREE.Mesh(geo, mat); mesh.frustumCulled = false; mesh.renderOrder = def.order; mesh.matrixAutoUpdate = false;
    const c = { def, cap, buf, ib, geo, mat, mesh, n: 0, last: 0 };
    mesh.onBeforeRender = () => { const s = SENSOR.value; geo.instanceCount = def.rule === 'heat' ? (s === 1 ? c.n : 0) : def.rule === 'vis' ? (s === 1 ? 0 : c.n) : c.n; };
    scene.add(mesh); return c;
  }
  R.combo = (def, cap) => { let c = R.combos[def.key]; if (!c) c = R.combos[def.key] = mkCombo(def, cap || F.cap().inst); return c; };
  R.begin = () => { for (const k in R.combos) R.combos[k].n = 0; R.drawn = 0; };
  R.end = () => { let inst = 0, calls = 0; for (const k in R.combos) { const c = R.combos[k]; c.geo.instanceCount = c.n; c.ib.needsUpdate = c.n > 0 || c.lastN > 0; c.lastN = c.n; c.mesh.visible = c.n > 0; if (c.n > 0) { calls++; inst += c.n; } } R.inst = inst; R.calls = calls; };
  /* push one instance. q: 0 cylindrical billboard, 1 spherical with rotation rot, 2 fixed yaw (crossed quads), 3 flat on the ground (yaw rot) */
  R.push = (c, x, y, z, w, h, fa, fb, mix, alpha, flip, q, rot, stretch, r, g, b, add, lx, lz) => {
    if (c.n >= c.cap) { R.dropped++; return; } const o = c.n++ * STRIDE, B = c.buf;
    B[o] = x; B[o + 1] = y; B[o + 2] = z; B[o + 3] = flip; B[o + 4] = w; B[o + 5] = h; B[o + 6] = q; B[o + 7] = rot; B[o + 8] = fa; B[o + 9] = fb; B[o + 10] = mix; B[o + 11] = alpha;
    B[o + 12] = r; B[o + 13] = g; B[o + 14] = b; B[o + 15] = add; B[o + 16] = lx; B[o + 17] = lz; B[o + 18] = stretch; B[o + 19] = 0;
  };
  /* ---- textures: fetched on demand, decoded with straight alpha (no premultiply: lossy WebP bleeds colour into the clear pixels), no mipmaps (they would mix neighbouring frames) */
  R.loadTex = (url) => {
    let t = R.tex[url]; if (t) { t.last = performance.now(); return t.p; } t = R.tex[url] = { url, last: performance.now(), tex: null, bytes: 0 };
    t.p = fetch(url).then(r => { if (!r.ok) throw new Error('http ' + r.status); return r.blob(); }).then(b => createImageBitmap(b, { premultiplyAlpha: 'none', colorSpaceConversion: 'none' })).then(bm => {
      const tx = new THREE.Texture(bm); tx.flipY = false; tx.premultiplyAlpha = false; tx.generateMipmaps = false; tx.minFilter = THREE.LinearFilter; tx.magFilter = THREE.LinearFilter; tx.wrapS = tx.wrapT = THREE.ClampToEdgeWrapping; tx.colorSpace = THREE.NoColorSpace; tx.needsUpdate = true;
      t.tex = tx; t.bytes = bm.width * bm.height * 4; R.loadN++; return tx;
    }).catch(e => { delete R.tex[url]; throw e; });
    return t.p;
  };
  R.dropTex = (url) => { const t = R.tex[url]; if (!t) return; delete R.tex[url]; try { if (t.tex) { if (t.tex.image && t.tex.image.close) t.tex.image.close(); t.tex.dispose(); } } catch (e) { } };
  R.texBytes = () => { let n = 0; for (const k in R.tex) n += R.tex[k].bytes || 0; return n; };
  R.json = {};
  R.loadJson = (url) => R.json[url] || (R.json[url] = fetch(url).then(r => { if (!r.ok) throw new Error('http ' + r.status); return r.json(); }));
  F.ensureAtlas = () => {
    if (F.atlasP) return F.atlasP;
    F.atlasP = R.loadJson('assets/fire/fire_atlas.json?v=fw1').then(j => { F.atlas = j; F.ready = true; return j; }).catch(e => { F.failed = true; F.err = String(e); return null; });
    return F.atlasP;
  };
  return F;
})();
/*FW-END part1a*/
