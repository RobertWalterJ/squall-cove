"""Supply depot, artillery battery, mortar pit, bunker, command post, ammo dump, field hospital."""
from b_lib import *


def supply_depot():
    M = Model('supply_depot'); B = M.part(); rng = random.Random(21)
    B.box((0, 0.015, 0), (11.0, 0.03, 8.0), 'battle_sand')
    # tent
    tx, tz = -3.2, -0.6
    tent(B, tx, tz, 5.0, 3.6, 1.55, 2.7, 'battle_canvas', 'battle_wood_light')
    for sx in (-1, 1):
        tube(B, (tx + sx * 1.8, 0.0, tz + 2.5), (tx + sx * 1.8, 1.6, tz + 2.5), 0.07, 'battle_wood')
        B.sweep([(tx + sx * 1.8, 1.6, tz + 2.5), (tx + sx * 3.1, 0.05, tz + 3.6)], 0.012, 3, 'battle_wire', False, (False, False))
        B.sweep([(tx + sx * 1.8, 1.55, tz - 2.5), (tx + sx * 3.1, 0.05, tz - 3.6)], 0.012, 3, 'battle_wire', False, (False, False))
        B.box((tx + sx * 3.1, 0.07, tz + 3.6), (0.1, 0.14, 0.1), 'battle_wood'); B.box((tx + sx * 3.1, 0.07, tz - 3.6), (0.1, 0.14, 0.1), 'battle_wood')
    tube(B, (tx, 0.0, tz + 2.5), (tx, 2.75, tz + 2.5), 0.08, 'battle_wood')
    for (dx, dz, yw) in ((-0.9, -1.2, 0), (-0.9, -0.2, 90), (0.8, -1.5, 0)):
        crate(B, (tx + dx, 0.03, tz + dz), (0.8, 0.5, 0.5), yw, 'battle_crate')
    crate(B, (tx - 0.9, 0.53, tz - 1.2), (0.8, 0.5, 0.5), 8, 'battle_crate_green')
    B.box((tx + 0.5, 0.2, tz + 0.8), (1.3, 0.12, 1.0), 'battle_wood'); B.box((tx + 0.5, 0.31, tz + 0.8), (1.4, 0.1, 1.1), 'battle_olive')
    # crate stacks
    stacks = [(2.6, 1.8, 0), (4.0, 1.2, 8), (3.1, -0.4, -6)]
    for (cx, cz, yw) in stacks:
        for lv in range(3):
            for k in range(3 - lv):
                mat = 'battle_crate' if (lv + k) % 2 == 0 else 'battle_crate_green'
                crate(B, (cx + (k - (2 - lv) / 2) * 0.95 * math.cos(rad(yw)), 0.03 + lv * 0.55, cz - (k - (2 - lv) / 2) * 0.95 * math.sin(rad(yw))), (0.9, 0.55, 0.6), yw + rng.uniform(-3, 3), mat)
    # sack pile on a pallet
    B.box((4.4, 0.08, -2.4), (1.3, 0.14, 1.2), 'battle_wood')
    for lv in range(2):
        for i in range(3):
            for j in range(2):
                bag(B, (4.4 - 0.4 + i * 0.4, 0.14 + lv * 0.17, -2.4 - 0.25 + j * 0.5), (1.0 if lv == 0 else 0.0, 0.0 if lv == 0 else 1.0), rng.choice(BAGM), 0.42, 0.28, 0.17)
    # fuel drums: two groups
    for i in range(6):
        drum(B, (1.0 + (i % 3) * 0.62, 0.0, -3.0 - (i // 3) * 0.62), ['battle_drum_green', 'battle_drum_red', 'battle_drum_blue'][i % 3])
    for i in range(3): drum(B, (-5.0 + i * 0.6, 0.0, 3.0), 'battle_drum_green')
    # flag pole
    fx, fz = 0.2, 3.0
    B.cyl((fx, 0.0, fz), (fx, 0.4, fz), 0.35, 0.28, 8, 'battle_concrete', False)
    B.cyl((fx, 0.4, fz), (fx, 6.0, fz), 0.055, 0.035, 8, 'battle_steel', False)
    B.light((fx, 6.08, fz), 0.07, 'battle_yellow')
    grid = []
    for r in range(4):
        row = []
        for c in range(7):
            t = c / 6; row.append((fx + 0.04 + t * 1.5, 5.85 - 0.4 * r / 3 * 1.0 - 0.0 + 0.08 * math.sin(t * 7), fz + 0.12 * math.sin(t * 7 + 0.5)))
        grid.append(row)
    # tapered pennant: upper edge to a point at the fly
    B.patch(grid, 'battle_flag', (0, 0, 1), False)
    # wooden ramp-like loading dock
    B.box((-0.5, 0.18, 3.3), (2.4, 0.36, 1.4), 'battle_wood'); B.box((-0.5, 0.38, 3.3), (2.5, 0.05, 1.5), 'battle_wood_light')
    bagline(B, (-5.2, -4.0), (-1.0, -4.0), 2, rng)
    bagline(B, (5.0, -3.6), (5.0, 0.4), 2, rng)
    return M


def artillery_battery():
    M = Model('artillery_battery'); B = M.part(); rng = random.Random(31)
    B.cyl((0, 0.0, 0), (0, 0.06, 0), 4.3, 4.3, 24, 'battle_sand', False)
    B.cyl((0, 0.06, 0.3), (0, 0.09, 0.3), 2.1, 2.1, 20, 'battle_concrete_dark', False)
    bagarc(B, (0, 0, 0), 3.7, -150, 150, 4, rng, y0=0.05, rows=1, w=0.4, h=0.18)
    # howitzer: wheels, axle, carriage, shield, trails
    ty = 1.1
    for sx in (-1, 1):
        B.cyl((sx * 1.0, 0.62, 0.0), (sx * 1.2, 0.62, 0.0), 0.62, 0.62, 14, 'battle_rubber', True)
        B.cyl((sx * 1.12, 0.62, 0.0), (sx * 1.25, 0.62, 0.0), 0.28, 0.28, 10, 'battle_steel', False)
    B.cyl((-1.1, 0.62, 0.0), (1.1, 0.62, 0.0), 0.07, 0.07, 6, 'battle_steel_dark', False)
    B.box((0, 0.8, 0.0), (1.2, 0.35, 0.8), 'battle_olive', bevel=0.02)
    for sx in (-1, 1):
        tube(B, (sx * 0.38, 0.8, 0.0), (sx * 0.38, ty, 0.0), 0.2, 'battle_olive')
        tube(B, (sx * 0.33, 0.7, -0.2), (sx * 1.35, 0.2, -3.7), 0.16, 'battle_olive')
        B.box((sx * 1.36, 0.1, -3.78), (0.22, 0.2, 0.5), 'battle_steel_dark')
    B.box((0, 0.7, -1.9), (0.1, 0.04, 0.1), 'battle_black')
    # shield (two slanted plates with a barrel gap)
    for sx in (-1, 1):
        B.box((sx * 0.78, 1.45, 0.62), (1.0, 1.1, 0.05), 'battle_olive_dark', rot=(-12, 0, 0))
    B.box((0, 1.0, 0.55), (0.6, 0.5, 0.05), 'battle_olive_dark', rot=(-12, 0, 0))
    B.box((0, 0.55, 0.0), (0.7, 0.05, 0.7), 'battle_steel_dark')
    # ammo: crates + shell rack + loose shells
    for i in range(2):
        for j in range(2): crate(B, (-2.6, 0.06 + j * 0.42, -1.2 - i * 0.8), (0.9, 0.4, 0.6), 90, 'battle_crate_green')
    crate(B, (2.5, 0.06, -1.2), (0.9, 0.4, 0.6), 90, 'battle_crate_green'); crate(B, (2.5, 0.46, -1.2), (0.9, 0.4, 0.6), 80, 'battle_crate')
    crate(B, (2.4, 0.06, -2.2), (0.9, 0.4, 0.6), 100, 'battle_crate')
    for k in range(6):
        sx, sz = 2.6 + (k % 3) * 0.2, 0.7 + (k // 3) * 0.2
    for k in range(5):
        z = 0.5 + k * 0.2
        B.cyl((-2.8, 0.14, z + 0.0), (-2.2, 0.14, z + 0.0), 0.065, 0.065, 6, 'battle_yellow', False)
        B.cyl((-2.2, 0.14, z), (-1.9, 0.14, z), 0.065, 0.02, 6, 'battle_olive', False)
    B.box((-2.55, 0.1, 1.0), (1.2, 0.08, 1.4), 'battle_wood_dark')
    # camouflage tarp rolled by trail
    B.cyl((0.8, 0.12, -2.8), (-0.8, 0.12, -2.8), 0.12, 0.12, 8, 'battle_camo_a', False)
    # ---- barrel: pivot at the trunnion
    G = M.part('howitzer_barrel', (0, ty, 0))
    G.cyl((-0.45, ty, 0), (0.45, ty, 0), 0.07, 0.07, 6, 'battle_steel', False)
    G.cyl((0, ty, -0.55), (0, ty, 1.1), 0.17, 0.17, 10, 'battle_olive', True)
    G.cyl((0, ty, 1.1), (0, ty, 1.3), 0.12, 0.12, 10, 'battle_steel_dark', False)
    G.cyl((0, ty, 0.2), (0, ty, 3.4), 0.085, 0.07, 10, 'battle_steel_dark', True)
    G.cyl((0, ty, 3.4), (0, ty, 3.78), 0.12, 0.12, 10, 'battle_steel', False)
    for k in range(3): G.box((0, ty, 3.48 + k * 0.1), (0.3, 0.05, 0.04), 'battle_black')
    G.box((0, ty, -0.7), (0.32, 0.36, 0.5), 'battle_steel_dark', bevel=0.02)
    G.box((0.2, ty - 0.05, -0.8), (0.06, 0.4, 0.06), 'battle_steel')
    for sx in (-1, 1): G.cyl((sx * 0.22, ty - 0.2, 0.1), (sx * 0.22, ty - 0.2, 1.5), 0.05, 0.05, 6, 'battle_steel', False)
    return M


def mortar_pit():
    M = Model('mortar_pit'); B = M.part(); rng = random.Random(41)
    B.cyl((0, 0, 0), (0, 0.04, 0), 2.7, 2.7, 20, 'battle_earth', False)
    B.cyl((0, 0.04, 0), (0, 0.06, 0), 1.2, 1.2, 16, 'battle_mud', False)
    bagarc(B, (0, 0, 0), 1.75, -155, 155, 5, rng, y0=0.04, rows=2, w=0.32)
    # duckboards
    for k in range(7): B.box((-0.9 + k * 0.3, 0.075, -0.65), (0.22, 0.03, 0.9), 'battle_wood')
    B.box((0, 0.065, -0.65), (2.0, 0.02, 0.06), 'battle_wood_dark')
    # base plate, bipod, ammo
    B.cyl((0, 0.06, 0.05), (0, 0.13, 0.05), 0.4, 0.4, 12, 'battle_steel_dark', False)
    ang = 72.0; d = Vector((0, math.sin(rad(ang)), math.cos(rad(ang))))
    base = Vector((0, 0.16, 0.05)); mid = base + d * 0.7
    for sx in (-1, 1):
        B.sweep([tuple(mid), (sx * 0.42, 0.08, mid.z + 0.45)], 0.022, 5, 'battle_steel', True)
        B.box((sx * 0.42, 0.065, mid.z + 0.45), (0.16, 0.025, 0.16), 'battle_steel_dark')
    B.cyl((mid.x - 0.1, mid.y, mid.z), (mid.x + 0.1, mid.y, mid.z), 0.035, 0.035, 6, 'battle_steel', False)
    crate(B, (1.0, 0.06, -0.55), (0.8, 0.35, 0.5), 100, 'battle_crate_green'); crate(B, (-1.0, 0.06, -0.35), (0.8, 0.35, 0.5), 80, 'battle_crate_green')
    for k in range(6):
        a = (k % 3) * 0.14; B.cyl((-0.85 + a, 0.11, -0.95 - (k // 3) * 0.15), (-0.45 + a, 0.11, -0.95 - (k // 3) * 0.15), 0.045, 0.045, 6, 'battle_olive', False)
        B.cyl((-0.45 + a, 0.11, -0.95 - (k // 3) * 0.15), (-0.32 + a, 0.11, -0.95 - (k // 3) * 0.15), 0.045, 0.02, 6, 'battle_yellow', False)
    # ---- tube: pivot at the base, rest pose elevated 72 degrees toward +Z
    T = M.part('mortar_tube', (0, 0.16, 0.05)); b0 = Vector((0, 0.16, 0.05))
    T.ellipsoid(tuple(b0), (0.09, 0.09, 0.09), 'battle_steel_dark', 8, 4)
    T.cyl(tuple(b0), tuple(b0 + d * 1.15), 0.055, 0.05, 8, 'battle_steel', True)
    T.cyl(tuple(b0 + d * 1.15), tuple(b0 + d * 1.2), 0.07, 0.07, 8, 'battle_steel_dark', False)
    T.cyl(tuple(b0 + d * 0.6), tuple(b0 + d * 0.72), 0.075, 0.075, 8, 'battle_steel_dark', False)
    T.box(tuple(b0 + d * 0.5 + Vector((0.09, 0.0, -0.02))), (0.07, 0.1, 0.06), 'battle_black')
    return M


def bunker_large():
    M = Model('bunker_large'); B = M.part(); rng = random.Random(51)
    W = 9.0; D = 6.0; Hh = 2.6; t = 0.7; cz = 0.0
    hx = W / 2; zf = D / 2
    # floor and dark interior shell
    B.box((0, 0.05, 0), (W, 0.1, D), 'battle_concrete_dark')
    B.box((0, 1.3, -zf + t + 0.02), (W - 2 * t, 2.4, 0.04), 'battle_dark')
    # front wall with 3 slits
    slits = [-2.7, 0.0, 2.7]; sw = 1.3; y0, y1 = 1.3, 1.75
    B.box((0, y0 / 2, zf - t / 2), (W, y0, t), 'battle_concrete')
    B.box((0, (y1 + Hh) / 2, zf - t / 2), (W, Hh - y1, t), 'battle_concrete')
    edges = [-hx] + sum([[s - sw / 2, s + sw / 2] for s in slits], []) + [hx]
    for i in range(0, len(edges), 2):
        a, b = edges[i], edges[i + 1]
        if b - a > 0.01: B.box(((a + b) / 2, (y0 + y1) / 2, zf - t / 2), (b - a, y1 - y0, t), 'battle_concrete')
    for s in slits:   # splayed slit sill and lintel
        B.box((s, y0 - 0.02, zf - t / 2), (sw + 0.2, 0.04, t + 0.06), 'battle_concrete_dark'); B.box((s, y1 + 0.02, zf - t / 2), (sw + 0.2, 0.04, t + 0.06), 'battle_concrete_dark')
    # side walls (right has a door gap), back wall
    B.box((-hx + t / 2, Hh / 2, 0), (t, Hh, D - 2 * t + 0.001 + 2 * t - 2 * t), 'battle_concrete')
    dz0, dz1 = -0.4, 0.8
    B.box((hx - t / 2, Hh / 2, (-zf + dz0) / 2), (t, Hh, dz0 + zf), 'battle_concrete'); B.box((hx - t / 2, Hh / 2, (dz1 + zf - t) / 2), (t, Hh, zf - t - dz1), 'battle_concrete')
    B.box((hx - t / 2, (1.95 + Hh) / 2, (dz0 + dz1) / 2), (t, Hh - 1.95, dz1 - dz0), 'battle_concrete')
    B.box((hx - 0.2, 0.95, (dz0 + dz1) / 2), (0.08, 1.9, dz1 - dz0 - 0.1), 'battle_steel_dark')
    B.box((0, Hh / 2, -zf + t / 2), (W, Hh, t), 'battle_concrete')
    # roof slab, earth cover, vents
    B.box((0, Hh + 0.25, 0), (W + 0.3, 0.5, D + 0.3), 'battle_concrete_dark')
    blk(B, -hx - 0.6, hx + 0.6, -zf - 0.5, zf - 0.3, Hh + 0.5, Hh + 1.1, 'battle_earth', ins=(0.8, 0.8, 0.7, 0.6))
    blk(B, -hx - 2.0, -hx + 0.0, -zf - 0.4, zf - 0.8, 0.0, Hh + 0.55, 'battle_earth', ins=(1.4, 0.0, 0.3, 0.6))
    blk(B, -hx + 0.0, hx, -zf - 1.4, -zf + 0.1, 0.0, Hh + 0.55, 'battle_earth', ins=(0, 0, 1.0, 0.0))
    blk(B, hx - 0.0, hx + 1.6, -zf - 0.4, 0.2, 0.0, Hh + 0.55, 'battle_earth', ins=(0.0, 1.1, 0.3, 0.0))
    for sx in (-2.5, 2.8): B.cyl((sx, Hh + 1.05, -1.0), (sx, Hh + 1.6, -1.0), 0.12, 0.12, 8, 'battle_steel', True); B.cyl((sx, Hh + 1.6, -1.0), (sx, Hh + 1.75, -1.0), 0.2, 0.2, 8, 'battle_steel_dark', False)
    # blast wall + door step on the right
    B.box((hx + 0.9, 0.9, 0.2), (0.4, 1.8, 2.0), 'battle_concrete')
    B.box((hx + 0.35, 0.05, 0.2), (0.7, 0.1, 1.3), 'battle_concrete_dark')
    # sandbag apron in front and wings
    bagline(B, (-hx - 0.2, zf + 1.4), (-1.1, zf + 1.4), 3, rng, rows=2)
    bagline(B, (1.1, zf + 1.4), (hx + 0.2, zf + 1.4), 3, rng, rows=2)
    bagline(B, (-hx - 0.2, zf + 1.4), (-hx - 0.2, zf - 0.2), 3, rng, rows=2)
    bagline(B, (hx + 0.2, zf + 1.4), (hx + 0.2, zf - 0.2), 3, rng, rows=2)
    return M


def command_post():
    M = Model('command_post'); B = M.part(); rng = random.Random(61)
    B.box((0, 0.015, 0), (9.0, 0.03, 7.0), 'battle_sand')
    # camouflage net draped over poles
    NX, NZ = 10, 8; X0, Z0 = 4.2, 3.2
    def h(x, z):
        r2 = (x / X0) ** 2 + (z / Z0) ** 2
        return 1.55 + 1.15 * max(0.0, 1 - r2) ** 0.8
    pts = []; mats = []; faces = []
    for j in range(NZ + 1):
        for i in range(NX + 1):
            x = -X0 + 2 * X0 * i / NX; z = -Z0 + 2 * Z0 * j / NZ; pts.append((x, h(x, z), z))
    cam = ['battle_camo_a', 'battle_camo_b', 'battle_camo_c', 'battle_camo_d']
    for j in range(NZ):
        for i in range(NX):
            a = j * (NX + 1) + i; faces.append((a, a + NX + 1, a + NX + 2, a + 1))
            v = math.sin(i * 1.3 + j * 0.7) + math.sin(i * 0.5 - j * 1.9) + rng.uniform(-0.5, 0.5)
            mats.append(cam[0 if v < -0.8 else 1 if v < 0.1 else 2 if v < 0.9 else 3])
    # orient upward
    fl = []
    for f in faces:
        a = Vector(pts[f[1]]) - Vector(pts[f[0]]); b = Vector(pts[f[2]]) - Vector(pts[f[0]])
        fl.append(f if a.cross(b).y > 0 else f[::-1])
    B.add(pts, fl, 'battle_camo_a', False, orient=False, mats=mats)
    for (px, pz) in ((-3.4, -2.4), (3.4, -2.4), (-3.4, 2.4), (3.4, 2.4), (0, 0)):
        tube(B, (px, 0.0, pz), (px, h(px, pz) - 0.02, pz), 0.09, 'battle_wood')
    for k in range(10):
        a = rad(k * 36 + 10); px, pz = 4.15 * math.sin(a) * 1.0, 3.15 * math.cos(a)
        B.sweep([(px * 0.98, h(px, pz), pz * 0.98), (px * 1.15, 0.05, pz * 1.15)], 0.012, 3, 'battle_wire', False, (False, False))
    # map table with stools
    tz = 0.2
    B.box((0, 0.76, tz), (2.6, 0.05, 1.2), 'battle_wood_light')
    for sx in (-1, 1):
        for sz in (-1, 1): tube(B, (sx * 1.2, 0.0, tz + sz * 0.5), (sx * 1.2, 0.76, tz + sz * 0.5), 0.06, 'battle_wood_dark')
    flat_rect(B, -1.1, 1.1, tz - 0.5, tz + 0.5, 0.79, 'battle_canvas_light')
    flat_rect(B, -0.9, 0.1, tz - 0.05, tz + 0.02, 0.795, 'battle_black')
    for (mx, mz, m) in ((-0.5, tz + 0.2, 'battle_red'), (0.2, tz - 0.1, 'battle_red'), (0.6, tz + 0.25, 'battle_drum_blue'), (-0.2, tz - 0.3, 'battle_drum_blue')):
        flat_rect(B, mx - 0.07, mx + 0.07, mz - 0.05, mz + 0.05, 0.8, m)
    B.cyl((-0.9, 0.79, tz + 0.35), (-0.9, 0.83, tz + 0.35), 0.06, 0.06, 8, 'battle_steel_dark', False)
    for (sx, sz) in ((-0.7, 1.3), (0.7, 1.3), (0, -0.95)):
        B.box((sx, 0.42, sz), (0.38, 0.04, 0.38), 'battle_olive')
        for a in (-1, 1):
            for b in (-1, 1): tube(B, (sx + a * 0.15, 0.0, sz + b * 0.15), (sx + a * 0.15, 0.4, sz + b * 0.15), 0.035, 'battle_steel_dark', caps=False)
    # radio bench
    rx, rz = 2.9, -0.6
    B.box((rx, 0.72, rz), (0.8, 0.05, 2.0), 'battle_wood')
    for a in (-1, 1):
        for b in (-1, 1): tube(B, (rx + a * 0.35, 0.0, rz + b * 0.9), (rx + a * 0.35, 0.72, rz + b * 0.9), 0.06, 'battle_wood_dark')
    for k, zo in enumerate((-0.7, -0.05, 0.6)):
        B.box((rx, 0.74 + 0.17, rz + zo), (0.5, 0.3, 0.5), 'battle_olive_dark', bevel=0.015)
        B.box((rx - 0.26, 0.74 + 0.2, rz + zo), (0.02, 0.16, 0.22), 'battle_black')
        for kn in range(2): B.cyl((rx - 0.27, 0.74 + 0.12 + kn * 0.1, rz + zo + 0.05), (rx - 0.3, 0.74 + 0.12 + kn * 0.1, rz + zo + 0.05), 0.03, 0.03, 6, 'battle_steel', False)
        B.cyl((rx + 0.15, 0.74 + 0.32, rz + zo), (rx + 0.15, 0.74 + 1.5 - k * 0.2, rz + zo), 0.01, 0.006, 4, 'battle_black', False)
    B.box((rx - 0.1, 0.8, rz + 0.95), (0.12, 0.08, 0.22), 'battle_black'); B.box((rx - 0.1, 0.78, rz + 0.8), (0.18, 0.04, 0.14), 'battle_olive')
    # generator, jerrycans, ammo cans, lantern, crate
    B.box((-3.1, 0.35, -1.7), (1.0, 0.7, 0.7), 'battle_olive', bevel=0.02); B.cyl((-3.4, 0.7, -1.7), (-3.4, 0.85, -1.7), 0.06, 0.06, 6, 'battle_steel', False)
    for k in range(3): B.box((-2.9 + k * 0.28, 0.2, -2.35), (0.22, 0.4, 0.14), 'battle_olive_dark')
    crate(B, (-2.9, 0.03, 1.8), (0.9, 0.5, 0.6), 10, 'battle_crate_green'); crate(B, (-2.8, 0.53, 1.8), (0.8, 0.45, 0.55), -5, 'battle_crate')
    B.cyl((-1.1, 0.8, tz - 0.3), (-1.1, 1.0, tz - 0.3), 0.07, 0.06, 8, 'battle_steel_dark', False); B.cyl((-1.1, 1.0, tz - 0.3), (-1.1, 1.06, tz - 0.3), 0.04, 0.04, 6, 'battle_yellow', False)
    # sandbags at the back, cable runs
    bagline(B, (-3.9, -2.9), (3.9, -2.9), 2, rng)
    B.sweep([(-3.1, 0.06, -1.4), (-1.5, 0.06, -0.6), (rx - 0.5, 0.06, rz)], 0.035, 5, 'battle_black', True)
    return M


def ammo_dump():
    M = Model('ammo_dump'); B = M.part(); rng = random.Random(71)
    B.box((0, 0.015, 0), (11.0, 0.03, 10.0), 'battle_earth_dark')
    zf = 1.2
    # shed shell (concrete block) inside the berm: x +-3.0, z -3.4..zf
    B.box((0, 1.15, (zf - 3.4) / 2), (6.0, 2.3, zf + 3.4), 'battle_concrete')
    B.box((0, 2.35, (zf - 3.4) / 2), (6.3, 0.2, zf + 3.7), 'battle_concrete_dark')
    # earth berm: three sides and roof
    blk(B, -5.6, -2.9, -4.6, zf + 0.5, 0.0, 2.2, 'battle_earth', ins=(2.0, 0.0, 0.6, 0.4))
    blk(B, 2.9, 5.6, -4.6, zf + 0.5, 0.0, 2.2, 'battle_earth', ins=(0.0, 2.0, 0.6, 0.4))
    blk(B, -3.0, 3.0, -4.6, -3.3, 0.0, 2.6, 'battle_earth', ins=(0, 0, 1.0, 0))
    blk(B, -3.0, 3.0, -3.4, zf - 0.1, 2.4, 3.05, 'battle_earth', ins=(0.4, 0.4, 0.3, 0.5))
    # front: door portal with timber doors
    for sx in (-1, 1): B.box((sx * 2.1, 1.1, zf + 0.12), (1.8, 2.2, 0.25), 'battle_concrete_dark')
    B.box((0, 2.0, zf + 0.12), (2.5, 0.5, 0.25), 'battle_concrete_dark')
    for sx in (-1, 1):
        B.box((sx * 0.55, 0.88, zf + 0.06), (1.05, 1.75, 0.1), 'battle_wood_dark')
        for k in range(3): B.box((sx * 0.55, 0.3 + k * 0.6, zf + 0.13), (1.0, 0.1, 0.04), 'battle_steel_dark')
        B.box((sx * 0.1, 0.9, zf + 0.15), (0.05, 0.25, 0.04), 'battle_steel')
    B.box((0, 0.1, zf + 0.5), (3.2, 0.2, 0.8), 'battle_concrete_dark')
    for sx in (-1.8, 1.8): B.cyl((sx, 3.0, -1.5), (sx, 3.6, -1.5), 0.1, 0.1, 8, 'battle_steel', True); B.cyl((sx, 3.6, -1.5), (sx, 3.75, -1.5), 0.18, 0.18, 8, 'battle_steel_dark', False)
    # crates, pallets, shell boxes
    for (cx, cz, yw) in ((-4.0, 2.8, 0), (-2.8, 3.2, 10), (3.6, 2.9, -5)):
        for lv in range(3):
            for k in range(2 if lv < 2 else 1):
                crate(B, (cx + k * 1.05 - (0.5 if lv < 2 else 0.0), 0.03 + lv * 0.5, cz), (1.0, 0.5, 0.6), yw + lv * 3, 'battle_crate_green' if (k + lv) % 2 == 0 else 'battle_crate')
    B.box((1.8, 0.07, 3.2), (1.2, 0.12, 1.2), 'battle_wood')
    for i in range(4): B.cyl((1.4 + (i % 2) * 0.55, 0.13, 3.0 + (i // 2) * 0.55), (1.4 + (i % 2) * 0.55, 0.68, 3.0 + (i // 2) * 0.55), 0.12, 0.12, 8, 'battle_olive', False)
    for i in range(4): B.cyl((1.4 + (i % 2) * 0.55, 0.68, 3.0 + (i // 2) * 0.55), (1.4 + (i % 2) * 0.55, 0.78, 3.0 + (i // 2) * 0.55), 0.12, 0.05, 8, 'battle_yellow', False)
    bagline(B, (-5.0, 4.5), (-1.0, 4.5), 2, rng); bagline(B, (1.0, 4.5), (5.0, 4.5), 2, rng)
    return M


def field_hospital():
    M = Model('field_hospital'); B = M.part(); rng = random.Random(81)
    L_ = 7.0; Wd = 4.6; wh = 1.9; rh = 3.2; cz = -0.5
    B.box((0, 0.02, 0.2), (7.0, 0.04, 10.0), 'battle_sand')
    tent(B, 0, cz, L_, Wd, wh, rh, 'battle_canvas_white', 'battle_wood_light')
    hz = cz + L_ / 2; bz = cz - L_ / 2
    # eave stripe, ground pegs
    for sx in (-1, 1):
        B.box((sx * Wd / 2, 0.06, cz), (0.06, 0.12, L_ + 0.04), 'battle_olive')
        for k in range(5):
            z = bz + (k + 0.5) * L_ / 5
            B.sweep([(sx * (Wd / 2 - 0.04), wh * 0.98, z), (sx * (Wd / 2 + 1.1), 0.05, z)], 0.012, 3, 'battle_wire', False, (False, False))
            B.box((sx * (Wd / 2 + 1.1), 0.1, z), (0.08, 0.2, 0.08), 'battle_wood')
    # front: two door poles, tied-back flaps, porch awning
    for sx in (-1, 1):
        tube(B, (sx * 1.5, 0.0, hz + 1.7), (sx * 1.5, 2.2, hz + 1.7), 0.08, 'battle_wood')
        tube(B, (sx * Wd / 2, wh, hz), (sx * 1.5, 2.2, hz + 1.7), 0.04, 'battle_wood_dark', caps=False)
    B.add([(-1.5, 2.2, hz + 1.7), (1.5, 2.2, hz + 1.7), (Wd / 2, wh, hz), (-Wd / 2, wh, hz)], [(0, 1, 2, 3)], 'battle_canvas_white', False, orient=False)
    # flaps: left and right triangles tied back
    for sx in (-1, 1):
        B.add([(sx * Wd / 2, 0.0, hz), (sx * 0.55, 0.0, hz), (sx * Wd / 2, wh, hz)], [(0, 1, 2)], 'battle_canvas_light', False, orient=False)
    # red crosses on both roof slopes, flat quads laid on the surface
    sl = math.degrees(math.atan2(rh - wh, Wd / 2)); nx, ny = math.sin(rad(sl)), math.cos(rad(sl))
    for sx in (-1, 1):
        cx = sx * Wd / 4; cy = wh + (rh - wh) / 2; ang = -sx * sl
        for (a, b) in ((1.5, 0.45), (0.45, 1.5)):
            B.box((cx + nx * sx * 0.02, cy + ny * 0.02, cz + 0.4), (a, 0.02, b), 'battle_red_cross', rot=(0, 0, ang))
    # sign board with a flat cross, at the entrance
    B.box((2.6, 1.0, hz + 2.4), (0.06, 2.0, 0.06), 'battle_wood'); B.box((2.6, 1.9, hz + 2.4), (1.3, 1.0, 0.05), 'battle_white')
    B.box((2.6, 1.9, hz + 2.43), (0.8, 0.22, 0.02), 'battle_red_cross'); B.box((2.6, 1.9, hz + 2.43), (0.22, 0.8, 0.02), 'battle_red_cross')
    # cots (interior)
    for k, sx in enumerate((-1.2, 1.2)):
        zc = cz - 0.2 + k * 0.6
        for a in (-1, 1):
            for b in (-1, 1): B.box((sx + a * 0.33, 0.2, zc + b * 0.9), (0.05, 0.4, 0.05), 'battle_steel_dark')
            B.box((sx + a * 0.34, 0.4, zc), (0.04, 0.05, 1.9), 'battle_steel_dark')
        B.box((sx, 0.43, zc), (0.66, 0.04, 1.9), 'battle_cot'); B.box((sx, 0.48, zc - 0.2), (0.64, 0.07, 1.25), 'battle_olive'); B.box((sx, 0.48, zc + 0.75), (0.4, 0.08, 0.28), 'battle_white')
    tube(B, (0.0, 0.0, cz + 0.6), (0.0, 1.7, cz + 0.6), 0.03, 'battle_steel', caps=True); B.box((0, 1.7, cz + 0.6), (0.4, 0.02, 0.02), 'battle_steel')
    B.box((0.0, 0.3, cz - 2.4), (1.4, 0.6, 0.7), 'battle_crate_green')
    crate(B, (-1.4, 0.04, cz - 2.5), (0.8, 0.5, 0.5), 5, 'battle_crate'); B.box((0.0, 0.62, cz - 2.4), (0.5, 0.04, 0.4), 'battle_red_cross')
    bagline(B, (-3.1, hz + 1.6), (-1.7, hz + 1.6), 2, rng); bagline(B, (1.7, hz + 1.6), (3.1, hz + 1.6), 2, rng)
    return M
