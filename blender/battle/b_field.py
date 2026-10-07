"""Trenches, wire, sandbag corner, helipad, ruins, rocks, palm."""
from b_lib import *

TD = 1.2     # trench depth (earth wall height); the channel floor is y=0


def trench_revet(B, x, z0, z1, side, along='z'):
    """Plank revetment along a channel wall (a plank sheet plus posts every metre and a top rail)."""
    if along == 'z':
        B.box((x, TD * 0.5, (z0 + z1) / 2), (0.04, TD, abs(z1 - z0)), 'battle_wood_dark')
        n = max(1, int(abs(z1 - z0) / 1.0 + 0.5))
        for k in range(n + 1):
            z = min(z0, z1) + abs(z1 - z0) * k / n
            B.box((x + side * 0.04, TD * 0.5, z), (0.08, TD, 0.1), 'battle_wood')
        B.box((x + side * 0.03, TD + 0.02, (z0 + z1) / 2), (0.1, 0.05, abs(z1 - z0)), 'battle_wood_light')
    else:
        B.box(((z0 + z1) / 2, TD * 0.5, x), (abs(z1 - z0), TD, 0.04), 'battle_wood_dark')
        n = max(1, int(abs(z1 - z0) / 1.0 + 0.5))
        for k in range(n + 1):
            z = min(z0, z1) + abs(z1 - z0) * k / n
            B.box((z, TD * 0.5, x + side * 0.04), (0.1, TD, 0.08), 'battle_wood')
        B.box(((z0 + z1) / 2, TD + 0.02, x + side * 0.03), (abs(z1 - z0), 0.05, 0.1), 'battle_wood_light')


def duck(B, a, b, rng, width=0.8):
    """Duckboard run from a=(x,z) to b=(x,z) at floor level: slats + two rails."""
    ax, az = a; bx, bz = b; L = math.hypot(bx - ax, bz - az); ux, uz = (bx - ax) / L, (bz - az) / L; nx, nz = -uz, ux
    yaw = math.degrees(math.atan2(-uz, ux)); n = max(1, int(L / 0.3))
    for k in range(n):
        t = (k + 0.5) * L / n
        ybox(B, (ax + ux * t, 0.0, az + uz * t), (0, 0.03, 0), (0.2, 0.035, width), yaw, 'battle_wood' if k % 3 else 'battle_wood_light')
    for s in (-1, 1):
        ybox(B, (ax + ux * L / 2, 0.0, az + uz * L / 2), (0, 0.012, s * width * 0.32), (L, 0.025, 0.07), yaw, 'battle_wood_dark')


def lips(B, pts, rng, courses=2):
    for a, b in zip(pts, pts[1:]): bagline(B, a, b, courses, rng, y0=TD)


def trench_straight():
    M = Model('trench_straight'); B = M.part(); rng = random.Random(91)
    B.box((0, 0.012, 0), (1.1, 0.024, 4.0), 'battle_mud')
    blk(B, -1.85, -0.55, -2.0, 2.0, 0.0, TD, 'battle_earth', ins=(0.4, 0, 0, 0))
    blk(B, 0.55, 1.85, -2.0, 2.0, 0.0, TD, 'battle_earth', ins=(0, 0.4, 0, 0))
    trench_revet(B, -0.55, -2.0, 2.0, -1); trench_revet(B, 0.55, -2.0, 2.0, 1)
    duck(B, (0, -2.0), (0, 2.0), rng)
    lips(B, [(-0.78, -2.0), (-0.78, 2.0)], rng); lips(B, [(0.78, -2.0), (0.78, 2.0)], rng)
    return M


def trench_corner():
    M = Model('trench_corner'); B = M.part(); rng = random.Random(92)
    B.box((0, 0.012, -0.7), (1.1, 0.024, 2.6), 'battle_mud'); B.box((1.0, 0.012, 0), (1.9, 0.024, 1.1), 'battle_mud')
    blk(B, -1.85, -0.55, -2.0, 0.55, 0.0, TD, 'battle_earth', ins=(0.4, 0, 0, 0))                 # west wall of arm A
    blk(B, -1.85, 2.0, 0.55, 1.85, 0.0, TD, 'battle_earth', ins=(0.4, 0, 0, 0.4))                 # south wall of arm B + outer corner
    blk(B, 0.55, 2.0, -1.8, -0.55, 0.0, TD, 'battle_earth', ins=(0, 0, 0.4, 0))                   # north wall of arm B / east wall of A
    blk(B, 0.55, 1.85, -2.0, -1.8, 0.0, TD, 'battle_earth', ins=(0, 0.4, 0, 0))
    trench_revet(B, -0.55, -2.0, 0.55, -1)       # west of A
    trench_revet(B, 0.55, -2.0, -0.55, 1)        # east of A
    trench_revet(B, 0.55, -0.55, 2.0, -1, 'x')   # south of B (z = 0.55): x extends -0.55..2
    trench_revet(B, -0.55, 0.55, 2.0, 1, 'x')
    duck(B, (0, -2.0), (0, 0.3), rng); duck(B, (0.3, 0), (2.0, 0), rng)
    lips(B, [(-0.78, -2.0), (-0.78, 0.78), (2.0, 0.78)], rng)
    lips(B, [(0.78, -2.0), (0.78, -0.78), (2.0, -0.78)], rng)
    return M


def trench_end():
    M = Model('trench_end'); B = M.part(); rng = random.Random(93)
    B.box((0, 0.012, 0), (1.1, 0.024, 4.0), 'battle_mud')
    blk(B, -1.85, -0.55, -2.0, 2.0, 0.0, TD, 'battle_earth', ins=(0.4, 0, 0, 0))
    blk(B, 0.55, 1.85, -2.0, 2.0, 0.0, TD, 'battle_earth', ins=(0, 0.4, 0, 0))
    blk(B, -0.55, 0.55, 1.2, 2.0, 0.0, TD, 'battle_earth', ins=(0, 0, 0, 0.4))
    trench_revet(B, -0.55, -2.0, 1.2, -1); trench_revet(B, 0.55, -2.0, 1.2, 1)
    B.box((0, TD * 0.5, 1.2), (1.1, TD, 0.04), 'battle_wood_dark')
    duck(B, (0, -2.0), (0, 1.1), rng)
    B.box((0, 0.2, 0.8), (0.9, 0.4, 0.5), 'battle_wood')    # firing step at the dead end
    lips(B, [(-0.78, -2.0), (-0.78, 1.45), (0.78, 1.45), (0.78, -2.0)], rng)
    return M


def barbed_wire():
    M = Model('barbed_wire'); B = M.part(); rng = random.Random(95)
    for k in range(5):
        x = -2.0 + k
        for zs in (-0.5, 0.5):
            B.sweep([(x, 0.0, zs), (x, 1.15, zs * 0.55)], 0.022, 4, 'battle_steel_dark', False)
    for (yc, zc, r) in ((0.4, -0.38, 0.4), (0.4, 0.38, 0.4), (0.92, 0.0, 0.38)):
        path = []; n = 8 * 12
        for i in range(n + 1):
            t = i / n; a = 2 * PI * 8 * t + zc
            path.append((-2.0 + 4.0 * t, yc + r * math.sin(a), zc + r * math.cos(a)))
        B.sweep(path, 0.013, 3, 'battle_wire', False, (False, False))
    for yy, zz in ((1.1, 0.0), (0.8, -0.28), (0.8, 0.28)):
        B.sweep([(-2.0, yy, zz * 0.0 + zz), (2.0, yy, zz)], 0.01, 3, 'battle_wire', False, (False, False))
        for k in range(14): B.light((-1.9 + k * 0.29, yy, zz), 0.028, 'battle_wire')
    return M


def sandbag_corner():
    M = Model('sandbag_corner'); B = M.part(); rng = random.Random(96)
    bagline(B, (-1.5, -1.2), (1.5, -1.2), 7, rng, rows=2)
    bagline(B, (-1.2, -0.9), (-1.2, 1.5), 7, rng, rows=2)
    return M


def helipad():
    M = Model('helipad'); B = M.part(); rng = random.Random(97)
    S = 12.0; H = 0.18
    blk(B, -S / 2, S / 2, -S / 2, S / 2, 0.0, H, 'battle_concrete', ins=(0.1, 0.1, 0.1, 0.1))
    y = H + 0.004
    for (a, b, c, d) in ((-5.5, 5.5, -5.5, -5.25), (-5.5, 5.5, 5.25, 5.5), (-5.5, -5.25, -5.5, 5.5), (5.25, 5.5, -5.5, 5.5)):
        flat_rect(B, a, b, c, d, y, 'battle_paint_yellow')
    ring_flat(B, (0, 0, 0), 4.2, 4.55, y, 'battle_paint_white', 48)
    for sx in (-1, 1): flat_rect(B, sx * 1.1 - 0.22, sx * 1.1 + 0.22, -1.8, 1.8, y, 'battle_paint_white')
    flat_rect(B, -1.1, 1.1, -0.22, 0.22, y, 'battle_paint_white')
    for sx in (-5.2, -2.6, 0, 2.6, 5.2):
        for sz in (-5.2, 5.2):
            B.cyl((sx, H, sz), (sx, H + 0.06, sz), 0.1, 0.1, 6, 'battle_yellow', False); B.cyl((sz, H, sx), (sz, H + 0.06, sx), 0.1, 0.1, 6, 'battle_yellow', False)
    for (a, b, c, d) in ((-0.3, 0.3, -5.95, -5.5),):
        pass
    # tie-down rings and an arrow marking north-facing approach (flat triangle)
    flat_pts = [(-0.5, y, 3.0), (0.5, y, 3.0), (0.0, y, 3.9)]
    B.add(flat_pts, [(0, 2, 1)], 'battle_paint_white', False, orient=False)
    # pole + base
    px, pz = 5.2, -5.2
    B.cyl((px, H, pz), (px, H + 0.12, pz), 0.28, 0.28, 8, 'battle_steel_dark', False)
    B.cyl((px, H + 0.12, pz), (px, 4.2, pz), 0.06, 0.04, 8, 'battle_steel', False)
    B.cyl((px, 4.1, pz), (px, 4.22, pz), 0.1, 0.1, 8, 'battle_steel_dark', False)
    # windsock: pivot at the pole top, rotates about Y, sock points +Z at rest
    W = M.part('windsock', (px, 4.15, pz))
    cy = 4.15; cx = px; cz = pz
    W.cyl((cx, cy, cz), (cx, cy + 0.02, cz + 0.3), 0.04, 0.04, 6, 'battle_steel', False)
    rings = []
    segs = 5; z0 = cz + 0.3
    for i in range(segs + 1):
        t = i / segs; r = 0.3 - 0.17 * t; zz = z0 + t * 1.7; yy = cy - 0.02 - 0.12 * t * t
        rings.append([(cx + r * math.cos(PI * 2 * k / 8), yy + r * math.sin(PI * 2 * k / 8), zz) for k in range(8)])
    for i in range(segs):
        mt = 'battle_sock_a' if i % 2 == 0 else 'battle_sock_b'
        W.add(rings[i] + rings[i + 1], [(k, (k + 1) % 8, 8 + (k + 1) % 8, 8 + k) for k in range(8)], mt, False, orient=False)
    ring_pts = [(cx + 0.3 * math.cos(PI * 2 * k / 12), cy - 0.02 + 0.3 * math.sin(PI * 2 * k / 12), z0) for k in range(13)]
    W.sweep(ring_pts, 0.02, 4, 'battle_steel', False, (False, False))
    return M


def brickwall(P, p0, p1, thick, colh, openings, rng, bl=0.6, bh=0.25, mats=('battle_brick_a', 'battle_brick_b', 'battle_brick_c'), maxh=3.0):
    """Brick wall from p0 to p1. colh(u) = surviving height at distance u along the wall, openings = [(u0,u1,y0,y1)]."""
    dx, dz = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dx, dz); yaw = math.degrees(math.atan2(-dz / L, dx / L))
    nj = int(maxh / bh); cnt = 0
    for j in range(nj):
        y0 = j * bh; off = bl / 2 if j % 2 else 0.0
        u = -off
        while u < L - 1e-6:
            a = max(0.0, u); b = min(L, u + bl); u += bl
            if b - a < 0.12: continue
            uc = (a + b) / 2
            if y0 + bh * 0.9 > colh(uc): continue
            if any(o[0] < uc < o[1] and y0 + bh * 0.5 > o[2] and y0 + bh * 0.5 < o[3] for o in openings): continue
            ybox(P, (p0[0], 0, p0[1]), (uc, y0 + bh / 2, 0), (b - a - 0.012, bh - 0.012, thick), yaw, mats[rng.randrange(len(mats))]); cnt += 1
    return cnt


def ruined_wall():
    M = Model('ruined_wall'); B = M.part(); rng = random.Random(101)
    hs = [2.5, 2.5, 2.4, 2.0, 1.7, 2.0, 1.1, 0.7, 1.3, 1.9, 1.8, 2.3, 1.4]
    def colh(u): return hs[min(len(hs) - 1, int(u / 0.5))] + (0.2 if u > 5.0 else 0)
    brickwall(B, (-3.0, 0.0), (3.0, 0.0), 0.34, colh, [(2.0, 3.0, 0.9, 1.9)], rng, bl=0.55, bh=0.25, maxh=2.8)
    B.box((0.0, 0.04, 0.0), (6.1, 0.08, 0.6), 'battle_concrete_dark')
    # plaster patches on the face and a lintel stub over the window
    B.box((-0.5, 1.2, 0.18), (0.9, 0.7, 0.03), 'battle_plaster_dark')
    B.box((-2.3, 1.5, -0.18), (0.8, 0.6, 0.03), 'battle_plaster')
    for k in range(18):
        x = rng.uniform(-3.4, 3.4); z = rng.choice((-1, 1)) * rng.uniform(0.35, 0.9); s = rng.uniform(0.12, 0.35)
        B.box((x, s * 0.4, z), (s * 1.6, s * 0.8, s), rng.choice(['battle_brick_a', 'battle_brick_b', 'battle_brick_c', 'battle_mortar']), rot=(rng.uniform(-20, 20), rng.uniform(0, 180), rng.uniform(-20, 20)))
    return M


def ruined_house():
    M = Model('ruined_house'); B = M.part(); rng = random.Random(111)
    hw, hd = 3.5, 2.75; t = 0.35
    B.box((0, 0.06, 0), (2 * hw + 0.2, 0.12, 2 * hd + 0.2), 'battle_concrete_dark')
    def prof(seed, base=2.8, lo=1.0):
        r = random.Random(seed); v = [r.choice([base, base, base - 0.3, lo + 0.5, lo + 1.0, lo, base - 0.8]) for _ in range(12)]
        for i in range(1, len(v)):
            v[i] = 0.6 * v[i] + 0.4 * v[i - 1]
        return lambda u: v[min(len(v) - 1, int(u / 0.75))]
    def hf(seed, base=2.8): return prof(seed, base)
    # walls (front +Z, back -Z, left +X, right -X); heights taller at corners
    cwall = lambda f: (lambda u, L=1: f(u))
    brickwall(B, (-hw, hd), (hw, hd), t, hf(1), [(2.9, 3.9, 0.0, 2.1), (0.8, 1.7, 0.9, 2.0), (5.3, 6.2, 0.9, 2.0)], rng, bl=0.78, bh=0.34, maxh=3.0)
    brickwall(B, (hw, hd), (hw, -hd), t, hf(2), [(1.9, 2.9, 0.9, 2.0)], rng, bl=0.78, bh=0.34, maxh=3.0)
    brickwall(B, (hw, -hd), (-hw, -hd), t, hf(3, 3.0), [(2.4, 3.4, 0.9, 2.0)], rng, bl=0.78, bh=0.34, maxh=3.0)
    brickwall(B, (-hw, -hd), (-hw, hd), t, hf(4, 2.2), [(1.0, 2.0, 0.9, 2.0), (3.6, 4.6, 0.9, 2.0)], rng, bl=0.78, bh=0.34, maxh=3.0)
    # interior partition stub
    brickwall(B, (-1.0, -hd), (-1.0, 0.8), 0.25, lambda u: 2.4 - 0.6 * (u / 3.5) ** 2 * 1.2, [(2.0, 2.9, 0.0, 2.0)], rng, bl=0.78, bh=0.34, maxh=2.6)
    # chimney stack on the back wall
    brickwall(B, (2.2, -hd + 0.5), (3.0, -hd + 0.5), 0.8, lambda u: 4.2, [], rng, bl=0.4, bh=0.3, maxh=4.4)
    # broken roof: rafters, ridge and one surviving plank panel
    ry = 2.85; rh = 4.3
    for k in range(5):
        z = -hd + 0.5 + k * 1.1 if False else -hd + 0.4 + k * 1.2
        zz = -hd + 0.4 + k * 1.2
    for k, x in enumerate((-3.2, -2.1, -1.0, 0.1, 1.2, 2.3, 3.2)):
        full = (k in (0, 1, 2, 5))
        # rafter pair: front slope (+Z side) and back slope
        tube(B, (x, ry, hd + 0.35), (x, rh, 0.0), 0.12, 'battle_wood_dark')
        if full or k in (3,): tube(B, (x, ry, -hd - 0.35), (x, rh, 0.0), 0.12, 'battle_wood_dark')
        else: tube(B, (x, ry, -hd - 0.35), (x, ry + 0.85 + 0.4 * (k % 2), -hd * 0.55), 0.12, 'battle_wood_dark')
    tube(B, (-3.4, rh, 0.0), (0.4, rh, 0.0), 0.16, 'battle_wood')
    tube(B, (0.4, rh, 0.0), (1.4, rh - 0.5, 0.2), 0.16, 'battle_wood', caps=True)
    # surviving roof boarding over the left-front and back, tilted slabs
    sl = math.degrees(math.atan2(rh - ry, hd + 0.35))
    B.box((-2.15, (ry + rh) / 2 + 0.08, (hd + 0.35) / 2), (2.3, 0.07, 3.3), 'battle_wood_light', rot=(sl, 0, 0))
    B.box((-2.6, (ry + rh) / 2 + 0.08, -(hd + 0.35) / 2), (1.5, 0.07, 3.3), 'battle_wood_light', rot=(-sl, 0, 0))
    # rubble inside and out
    for k in range(34):
        x = rng.uniform(-hw - 0.6, hw + 0.6); z = rng.uniform(-hd - 0.6, hd + 0.6)
        if abs(x) < hw - 0.3 and abs(z) < hd - 0.3 and rng.random() < 0.3: continue
        s = rng.uniform(0.15, 0.5)
        B.box((x, s * 0.35 + 0.12, z), (s * 1.5, s * 0.7, s), rng.choice(['battle_brick_a', 'battle_brick_b', 'battle_mortar', 'battle_plaster_dark', 'battle_wood_dark']), rot=(rng.uniform(-25, 25), rng.uniform(0, 180), rng.uniform(-25, 25)))
    # fallen beam and a door-frame stub
    B.box((1.5, 0.3, 0.9), (2.4, 0.16, 0.16), 'battle_wood_dark', rot=(0, 25, 8))
    return M


def _rock(P, c, R, Hh, layers, rng, mats, n=10, spin=0.35, shape=None):
    rings = []; rmat = []
    ys = [Hh * (i / layers) ** 0.95 for i in range(layers + 1)]
    shape = shape or [1.0, 0.92, 0.80, 0.9, 0.72, 0.84, 0.6, 0.5, 0.36, 0.3]
    base = [rng.uniform(0.8, 1.15) for _ in range(n)]
    for i in range(layers):
        s0 = shape[i % len(shape)]; s1 = s0 * rng.uniform(0.93, 0.99); tw = rng.uniform(-spin, spin)
        for (y, s) in ((ys[i], s0), (ys[i + 1], s1)):
            ring = []
            for k in range(n):
                a = 2 * PI * k / n + tw * (y / Hh)
                r = R * s * base[k] * (1 + 0.05 * math.sin(3 * a + i))
                ring.append((c[0] + r * math.sin(a), y, c[2] + r * math.cos(a)))
            rings.append(ring)
        rmat.append(mats[i % len(mats)] if rng.random() < 0.7 else rng.choice(mats))
    pts = [p for r in rings for p in r]; faces = []; fm = []
    nr = len(rings)
    for a in range(nr - 1):
        for k in range(n):
            faces.append((a * n + k, a * n + (k + 1) % n, (a + 1) * n + (k + 1) % n, (a + 1) * n + k)); fm.append(rmat[a // 2])
    faces.append(tuple(reversed(range(n)))); fm.append(rmat[0])
    faces.append(tuple((nr - 1) * n + k for k in range(n))); fm.append(mats[2 % len(mats)])
    P.add(pts, faces, mats[0], False, mats=fm)


def dune_rock_cluster():
    M = Model('dune_rock_cluster'); B = M.part(); rng = random.Random(121)
    mats = ['battle_sandstone_a', 'battle_sandstone_b', 'battle_sandstone_c', 'battle_sandstone_d']
    _rock(B, (-1.3, 0, -0.8), 3.0, 8.0, 7, rng, mats, n=11)
    _rock(B, (3.6, 0, 1.4), 2.6, 6.0, 6, rng, mats, n=10)
    _rock(B, (-3.4, 0, 3.4), 2.1, 4.0, 5, rng, mats, n=9)
    for (x, z, r, h) in ((1.3, 2.6, 0.9, 1.1), (-0.8, 3.4, 0.7, 0.8), (4.4, -1.6, 1.0, 1.2), (-4.4, -1.0, 0.8, 0.9), (1.0, -2.6, 0.7, 0.7)):
        _rock(B, (x, 0, z), r, h, 2, rng, mats, n=7, shape=[1.0, 0.8, 0.6])
    B.cyl((0.0, 0.0, 0.8), (0.0, 0.05, 0.8), 6.8, 6.8, 18, 'battle_sand', False)
    return M


def palm_tree():
    M = Model('palm_tree'); B = M.part(); rng = random.Random(131)
    path = []; rad_ = []; n = 12
    for i in range(n + 1):
        t = i / n; path.append((0.55 * t * t + 0.1 * math.sin(t * 3), 6.8 * t, 0.35 * t * t))
        rad_.append(0.2 * (1 - t) + 0.12 * t + 0.14 * max(0.0, 1 - t * 6) ** 2 + 0.012 * (i % 2))
    B.sweep(path, rad_, 8, 'battle_palm_trunk', True)
    T = Vector(path[-1]); B.ellipsoid(tuple(T + Vector((0, 0.1, 0))), (0.25, 0.22, 0.25), 'battle_palm_trunk', 8, 4)
    for k in range(5):
        a = rad(k * 72 + 20); B.ellipsoid((T.x + 0.2 * math.sin(a), T.y - 0.12, T.z + 0.2 * math.cos(a)), (0.13, 0.15, 0.13), 'battle_coconut', 6, 3)
    nf = 18
    for k in range(nf):
        phi = rad(k * 360 / nf + rng.uniform(-8, 8)); el = rad(rng.uniform(25, 60) if k % 2 == 0 else rng.uniform(55, 78)); L = rng.uniform(3.6, 4.6)
        dirh = Vector((math.sin(phi), 0, math.cos(phi))); perp = Vector((dirh.z, 0, -dirh.x)); grid = []
        for i in range(8):
            t = i / 7; w = 0.7 * math.sin(PI * min(1.0, t * 1.1) ** 0.9) + 0.03
            pos = T + Vector((0, 0.15, 0)) + dirh * (L * t * math.cos(el)) + Vector((0, L * t * math.sin(el) - 1.9 * L * 0.25 * t * t * 1.0, 0))
            grid.append([tuple(pos + perp * w + Vector((0, -0.12 * w, 0))), tuple(pos + Vector((0, 0.05 * w + 0.03, 0))), tuple(pos - perp * w + Vector((0, -0.12 * w, 0)))])
        B.patch(grid, 'battle_palm_frond' if k % 2 else 'battle_palm_frond_b', (0, 1, 0), False)
    B.cyl((0, 0.0, 0), (0, 0.06, 0), 0.7, 0.7, 10, 'battle_sand', False)
    return M
