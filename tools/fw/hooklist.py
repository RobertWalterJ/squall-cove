HOOKS = [
 ('frame tick', "  lightsTick(dt);\n  DIST.tick(dt);", "  FW.tick(dt); /*FW-HOOK*/\n  lightsTick(dt);\n  DIST.tick(dt);"),
 ('lights n', "  let n = 0; const mx = ED.phone ? 4 : 10;\n  for (const t of burning) { if (n >= mx) break;", "  let n = FW.lights(dt) || 0; const mx = ED.phone ? 4 : 10; /*FW-HOOK*/\n  for (const t of burning) { if (n >= mx) break; if (FW.drawn(t)) continue;"),
 ('lights heatp', "for (const h of HEATP) { if (n >= mx) break; const d = Math.hypot(h.x - fc.x, h.z - fc.z); if (d > 140) continue; const fl = 0.75 + 0.25 * Math.sin(simT * 15 + h.x);", "for (const h of HEATP) { if (n >= mx) break; if (h._fws && h._fws.some(q => q.vis)) continue; const d = Math.hypot(h.x - fc.x, h.z - fc.z); if (d > 140) continue; const fl = 0.75 + 0.25 * Math.sin(simT * 15 + h.x);"),
 ('lights veh', "for (const v of BVL) { if (!v.fire && !(v.burn > 0)) continue; if (n >= mx) break;", "for (const v of BVL) { if (!v.fire && !(v.burn > 0)) continue; if (n >= mx) break; if (v._fwe && v._fwe.vis) continue;"),
 ('tree flames', "if (Math.random() < dt * 14) fxG.emit(t.x + rnd(-0.6, 0.6), gy + rnd(1, 3.5)", "if (!FW.drawn(t) && Math.random() < dt * 14) fxG.emit(t.x + rnd(-0.6, 0.6), gy + rnd(1, 3.5)"),
 ('tree smoke', "if (Math.random() < dt * 6) puffSmoke(t.x, gy + 3, t.z, 1, true, 1);", "if (!FW.drawn(t) && Math.random() < dt * 6) puffSmoke(t.x, gy + 3, t.z, 1, true, 1);"),
 ('obj flames', "for (let q = 0; q < 3; q++) fxG.emit(p.x + rnd(-0.4, 0.4), gy + rnd(0.3, 1.1), p.z + rnd(-0.4, 0.4),", "if (!FW.drawn(o)) for (let q = 0; q < 3; q++) fxG.emit(p.x + rnd(-0.4, 0.4), gy + rnd(0.3, 1.1), p.z + rnd(-0.4, 0.4),"),
 ('obj smoke', "if (Math.random() < 0.5) puffSmoke(p.x, gy + 1, p.z, 1, true, 1);", "if (!FW.drawn(o) && Math.random() < 0.5) puffSmoke(p.x, gy + 1, p.z, 1, true, 1);"),
 ('boat fire', "    if (bt.fire > 0.05) {\n      const n = Math.round(bt.fire * 90 * dt)", "    if (bt.fire > 0.05 && !(bt._fwb && bt._fwb.some(q => q.vis))) {\n      const n = Math.round(bt.fire * 90 * dt)"),
 ('wreck smoke', "if (v.wreckT < 55 && Math.random() < dt * 4) puffSmoke(", "if (!(v._fwf && v._fwf.vis) && v.wreckT < 55 && Math.random() < dt * 4) puffSmoke("),
 ('wreck flames', "if (v.wreckT < 22 && Math.random() < dt * 7) fxG.emit(", "if (!(v._fwf && v._fwf.vis) && v.wreckT < 22 && Math.random() < dt * 7) fxG.emit("),
 ('veh burn smoke', "if (v.burn) { v.burn += dt; if (Math.random() < dt * 6) puffSmoke(v.x + rnd(-0.6, 0.6)", "if (v.burn) { v.burn += dt; if (!(v._fwe && v._fwe.vis) && Math.random() < dt * 6) puffSmoke(v.x + rnd(-0.6, 0.6)"),
 ('veh burn flames', "if (v.hp < v.hpMax * 0.12 && Math.random() < dt * 8) fxG.emit(v.x + rnd(-0.8, 0.8)", "if (!(v._fwe && v._fwe.vis) && v.hp < v.hpMax * 0.12 && Math.random() < dt * 8) fxG.emit(v.x + rnd(-0.8, 0.8)"),
 ('burnArea push', "function burnArea(x, z, r) { HEATP.push({ x, z, r: r * 0.6, p: 18, t: 14 });", "function burnArea(x, z, r) { const hp_ = { x, z, r: r * 0.6, p: 18, t: 14 }; HEATP.push(hp_);"),
 ('burnArea flames', "fxG.emit(fx, fy + 0.6, fz, rnd(-0.5, 0.5), rnd(1.5, 4), rnd(-0.5, 0.5), rnd(0.5, 1.1), rnd(1.6, 3), 0.8, [1, 0.55, 0.18, 0.9]); puffSmoke(fx, fy + 1, fz, 1, true, 1.6);", "if (!(hp_._fws && hp_._fws.some(q => q.vis))) { fxG.emit(fx, fy + 0.6, fz, rnd(-0.5, 0.5), rnd(1.5, 4), rnd(-0.5, 0.5), rnd(0.5, 1.1), rnd(1.6, 3), 0.8, [1, 0.55, 0.18, 0.9]); puffSmoke(fx, fy + 1, fz, 1, true, 1.6); }"),
]

HOOKS += [
 ('settings button', '<button id="mDistort" type="button">Air distortion: On<small>Bends the air over big blasts and fires. Off saves battery.</small></button>', '<button id="mDistort" type="button">Air distortion: On<small>Bends the air over big blasts and fires. Off saves battery.</small></button>\n    <button id="mFireQ" type="button">Fire quality: High<small>Realistic flames, smoke, steam and fog.</small></button>'),
 ('keymap fire', "  ['over', 'Menu, Settings, Air distortion',", "  ['over', 'Menu, Settings, Fire quality', 'Realistic baked fire: High draws flames, smoke, steam and fog from sprite sheets. Low is lighter (and the default on the phone). Off uses the old simple particle fire. Reduced motion lowers High to Low. Remembered (squall-cove-firequality)'],\n  ['over', 'Menu, Settings, Air distortion',"),
 ('lava cell', "if (LV[k] > 0.05 && LT[k] > 0.35) fxG.emit(G2W(j), HGT[k] + LV[k] + 0.3,", "if (LV[k] > 0.05 && LT[k] > 0.35) FW.lavaCell(G2W(j), G2W(i), k); if (LV[k] > 0.05 && LT[k] > 0.35) fxG.emit(G2W(j), HGT[k] + LV[k] + 0.3,"),
 ('lava vent', "for (const v of lavaVents) { DIST.haze(DIST.idOf(v), v.x, Math.max(standY(v.x, v.z), 0) + 0.8, v.z, 0.9, 7, 6);", "for (const v of lavaVents) { FW.lavaVent(v, dt); DIST.haze(DIST.idOf(v), v.x, Math.max(standY(v.x, v.z), 0) + 0.8, v.z, 0.9, 7, 6);"),
 ('bomber water', "      if (Math.random() < 0.15) { const wet = heightAt(x, z) < 0; if (wet) splash(x, z, 0.8); else puffSmoke(x, y + 0.5, z, 1, false, 0.9); }", "      FW.water(x, z, 8, 1.4, y); if (Math.random() < 0.15) { const wet = heightAt(x, z) < 0; if (wet) splash(x, z, 0.8); else puffSmoke(x, y + 0.5, z, 1, false, 0.9); }"),
 ('truck water', "if (v.sprayT > 1.2) { v.sprayT = 0; for (const b of burning.slice())", "if (v.sprayT > 1.2) { v.sprayT = 0; FW.water(t.x, t.z, 9, 2.5); for (const b of burning.slice())"),
]

HOOKS += [
 ('manifest bump', "fetch('audio/manifest.json?v=99')", "fetch('audio/manifest.json?v=1010')"),
 ('old veh fire loop', "(v.burn || (v.dead && v.wreckT < 40)) && d < 140 ? 0.45 : 0", "(v.burn || (v.dead && v.wreckT < 40)) && d < 140 && !(v._fwe && v._fwe.vis) ? 0.45 : 0"),
]

HOOKS += [
 ('blast fireball', "  fxG.emit(x, gy + 1.5, z, 0, 3, 0, 0.35, R * 0.9, 1.6, [1, 0.8, 0.4, 1]); fxG.emit(x, gy + 3, z, 0, 5, 0, 0.5, R * 1.3, 1.2, [1, 0.55, 0.2, 0.8]); puffSmoke(x, gy + 1.5, z, Math.round(R * 0.9), true, R * 0.14);", "  const fwOK = FW.blast(x, gy, z, R, o, wet); /*FW-HOOK*/ if (!fwOK) { fxG.emit(x, gy + 1.5, z, 0, 3, 0, 0.35, R * 0.9, 1.6, [1, 0.8, 0.4, 1]); fxG.emit(x, gy + 3, z, 0, 5, 0, 0.5, R * 1.3, 1.2, [1, 0.55, 0.2, 0.8]); puffSmoke(x, gy + 1.5, z, Math.round(R * 0.9), true, R * 0.14); }"),
 ('debris flame flag', "DEB.p.push({ x, y, z, vx: Math.cos(a) * Math.cos(e) * sp,", "DEB.p.push({ fl: FW.dFl(frag), x, y, z, vx: Math.cos(a) * Math.cos(e) * sp,"),
 ('LF residue acc', "f.acc += dt * FXK * fade * up * (6 + f.R);", "if (!FW.lfSkip(f)) f.acc += dt * FXK * fade * up * (6 + f.R);"),
 ('LF residue haze', "    DIST.haze(DIST.idOf(f), f.x, f.y + 0.5, f.z, 0.7 * Math.min(1, (f.life - f.age) / (f.life * 0.35)), 4 + f.R * 0.4, 2.5 + f.R * 0.45);", "    if (!FW.lfSkip(f)) DIST.haze(DIST.idOf(f), f.x, f.y + 0.5, f.z, 0.7 * Math.min(1, (f.life - f.age) / (f.life * 0.35)), 4 + f.R * 0.4, 2.5 + f.R * 0.45);"),
]

HOOKS += [
 ('splash baked', "const y = waveH(x, z, simT), b = Math.max(0.25, Math.min(big, 7));", "const y = waveH(x, z, simT), b = Math.max(0.25, Math.min(big, 7)); const fwS = FW.splash(x, z, y, b); /*FW-HOOK*/"),
 ('splash col off', "r: 0.35 + 0.28 * b, col: true });", "r: 0.35 + 0.28 * b, col: true }); if (fwS) { scene.remove(col); WSP.pop(); col.material.dispose(); }"),
 ('splash droplets', "const n = Math.round(14 + 10 * b);", "const n = fwS ? Math.round(2 + b) : Math.round(14 + 10 * b);"),
 ('splash foam', "  fxS.emit(x, y + 0.15, z, 0, 0.4, 0, 1.6, 0.9 + 0.8 * b, 2.4, [0.95, 0.99, 1, 0.5], 0, 1);", "  if (!fwS) fxS.emit(x, y + 0.15, z, 0, 0.4, 0, 1.6, 0.9 + 0.8 * b, 2.4, [0.95, 0.99, 1, 0.5], 0, 1);"),
 ('monitor hose', "if (n) ffSpray(bt, tgt, n);", "if (n) ffSpray(bt, tgt, n); FW.hose(bt, tgt);"),
 ('truck hose', "v.hold = true; v.spraying = true; v.sprayT = (v.sprayT || 0) + dt;", "v.hold = true; v.spraying = true; v.sprayT = (v.sprayT || 0) + dt; FW.hosePt(v, v.x + Math.cos(v.yaw) * 3, v.y + 3, v.z + Math.sin(v.yaw) * 3, t.x, Math.max(heightAt(t.x, t.z), 0) + 2, t.z);"),
]

HOOKS += [
 ('geyser steam', "if (s.geyser && geyserBurst(s) && Math.random() < dt * 20) puffSmoke(s.x + rnd(-0.5, 0.5),", "if (s.geyser && geyserBurst(s)) FW.geyser(s); if (s.geyser && geyserBurst(s) && !(s._fwg && !s._fwg.dead) && Math.random() < dt * 20) puffSmoke(s.x + rnd(-0.5, 0.5),"),
]

HOOKS += [
 ('fix model', "const g = kind === 'tower' ? buildTower() : kind === 'flood' ? buildFlood() : kind === 'lamp' ? buildLamp() : kind === 'gen' ? buildGen() : buildStrings(6); g.position.set(sp.x, sp.y - 0.02, sp.z);", "const g = FW.fixModel(kind, p) || (kind === 'tower' ? buildTower() : kind === 'flood' ? buildFlood() : kind === 'lamp' ? buildLamp() : kind === 'gen' ? buildGen() : buildStrings(6)); g.position.set(sp.x, sp.y - 0.02, sp.z); /*FW-HOOK*/"),
 ('fix search', "f.kind = 'gen'; out.push(f); gen = f; }", "f.kind = 'gen'; out.push(f); gen = f; }\n  else if (kind === 'search') out.push(mk('search', 0, 1.1, 0, 0, 2400, 190, 1.2, 0, [1, 0.96, 0.88], 60));"),
 ('fix fit', "for (const f of out) { f.model = g; LIGHT.fix.push(f); }", "for (const f of out) { f.model = g; FW.fixFit(f, g, kind, sp, yaw); LIGHT.fix.push(f); }"),
 ('fix want', "lightWant('fx' + f.id, 'point', f.x, f.y, f.z, f.col[0], f.col[1], f.col[2], f.I * f.on, f.range, f.kind === 'tower' ? 3 : f.kind === 'flood' ? 2.5 : 1.5, { glow: f.glow, glowA: 0.85, pool: f.pool, k: f.on });", "if (!(f.glb && FW.fixWant(f, lk))) lightWant('fx' + f.id, 'point', f.x, f.y, f.z, f.col[0], f.col[1], f.col[2], f.I * f.on, f.range, f.kind === 'tower' ? 3 : f.kind === 'flood' ? 2.5 : 1.5, { glow: f.glow, glowA: 0.85, pool: f.pool, k: f.on });"),
 ('lay wait', "lightsInit(); for (const p of BATTLE.points) { try { layPointFix(p); } catch (e) { window.__lterr = String(e && e.stack || e); } }", "lightsInit(); if (FW.packWait(layPointLights)) return; for (const p of BATTLE.points) { try { layPointFix(p); FW.fixCables(p); } catch (e) { window.__lterr = String(e && e.stack || e); } } /*FW-HOOK*/"),
 ('lights clear', "function lightsClear() {", "function lightsClear() { FW.fixClear();"),
]

HOOKS += [
 ('reset lf', "function lfClear() { LF.list.length = 0;", "function lfClear() { FW.reset(); LF.list.length = 0;"),
 ('reset calm', "function calm0() { clearLavaVents(); burning.length = 0;", "function calm0() { FW.reset(); clearLavaVents(); burning.length = 0;"),
]
