"""Cargo class: crates, barrels, drums, ISO containers, ingot pallets, ice, beach balls, sacks, rope coils."""
import math, random
from mathutils import Vector
from pg_core import *

WOODS = ['#a8743f', '#9c6a38', '#b07c46', '#8f6236', '#b8874f']

def crate(seed=0, name='crate'):
    r = rng(seed)
    kind = r.choice(['cube', 'cube', 'long', 'tall'])
    S = {'cube': [1.0, 1.0, 1.0], 'long': [1.6, 0.8, 0.8], 'tall': [0.9, 0.9, 1.3]}[kind]
    S = [s * r.uniform(0.9, 1.1) for s in S]
    t, gap, bw = 0.022, 0.012, 0.085
    tone = r.randrange(len(WOODS))
    woods = [mat('wood%d' % i, WOODS[(tone + i) % len(WOODS)], 0.85) for i in range(3)]
    batten = mat('batten_wood', '#6e4a26', 0.85)
    parts = [box([s - 2 * t - 0.002 for s in S], material=mat('crate_core', '#2a1d12', 1.0))]
    for n in range(3):
        u, v = [a for a in range(3) if a != n]
        if S[u] < S[v]: u, v = v, u
        cnt = max(2, round(S[v] / 0.16))
        pw = S[v] / cnt
        for sgn in (1, -1):
            for k in range(cnt):
                size = [0, 0, 0]; c = [0, 0, 0]
                size[n] = t; size[u] = S[u] - 0.004; size[v] = pw - gap
                c[n] = sgn * (S[n] / 2 - t / 2); c[v] = -S[v] / 2 + pw * (k + 0.5)
                parts.append(box(size, c, material=r.choice(woods), bevel=0.004))
    # proud battens framing the four vertical faces, plus a diagonal brace
    for n in (0, 1):
        u = 1 - n
        for sgn in (1, -1):
            off = sgn * (S[n] / 2 + t / 2)
            for zz in (-S[2] / 2 + bw / 2, S[2] / 2 - bw / 2):
                size = [0, 0, 0]; c = [0, 0, zz]; size[n] = t; size[u] = S[u]; size[2] = bw; c[n] = off
                parts.append(box(size, c, material=batten, bevel=0.004))
            for uu in (-S[u] / 2 + bw / 2, S[u] / 2 - bw / 2):
                size = [0, 0, 0]; c = [0, 0, 0]; size[n] = t; size[u] = bw; size[2] = S[2] - 2 * bw; c[n] = off; c[u] = uu
                parts.append(box(size, c, material=batten, bevel=0.004))
            if r.random() < 0.75:
                du, dz = S[u] - 2 * bw, S[2] - 2 * bw
                ang = math.atan2(dz, du) * (1 if r.random() < 0.5 else -1)
                size = [0, 0, 0]; size[n] = t; size[u] = math.hypot(du, dz) - bw * 0.6; size[2] = bw * 0.9
                c = [0, 0, 0]; c[n] = off
                rot = (0, -ang, 0) if n == 1 else (ang, 0, 0)
                if n == 1: parts.append(box(size, c, rot, material=batten))
                else:
                    o = box([size[1], size[0], size[2]], (0, 0, 0), (0, -ang, 0), material=batten)
                    o.data.transform(Matrix.Rotation(math.pi / 2, 4, 'Z')); o.data.transform(Matrix.Translation(c))
                    parts.append(o)
    return join(parts, name)

def barrel(seed=0, name='barrel'):
    r = rng(seed)
    h, r0, bulge, n = r.uniform(0.85, 1.0), r.uniform(0.28, 0.33), r.uniform(0.14, 0.2), r.choice([14, 16, 18])
    gap = 0.012
    woods = [mat('stave%d' % i, c, 0.85) for i, c in enumerate(WOODS)]
    parts = []
    Z = 10
    prof = lambda z: r0 * (1 + bulge * math.sin(math.pi * z / h))
    for i in range(n):
        a0 = 2 * math.pi * i / n + gap / r0 / 2
        a1 = 2 * math.pi * (i + 1) / n - gap / r0 / 2
        verts, faces = [], []
        for k in range(Z + 1):
            z = h * k / Z; rr = prof(z)
            for a in (a0, (a0 + a1) / 2, a1):
                verts.append((rr * math.cos(a), rr * math.sin(a), z))
        for k in range(Z):
            for j in range(2):
                p = k * 3 + j
                faces.append((p, p + 1, p + 4, p + 3))
        o = mesh('stave', verts, faces, r.choice(woods))
        parts.append(solidify(o, 0.022))
    hm = mat('hoop', '#3b3633', 0.5, 0.7)
    for zf in (0.06, 0.2, 0.8, 0.94):
        z = h * zf; rr = prof(z) + 0.004
        parts.append(lathe([(rr, z - 0.025), (rr + 0.006, z), (rr, z + 0.025)], 28, hm, cap_top=False, cap_bottom=False))
    head = mat('head', '#8f6236', 0.85)
    for z in (0.035, h - 0.035 - 0.02):
        parts.append(cyl(prof(z) - 0.02, prof(z) - 0.02, 0.02, 24, loc=(0, 0, z), material=head))
    if r.random() < 0.5:
        parts.append(cyl(0.025, 0.025, 0.03, 8, loc=(prof(h / 2) - 0.005, 0, h / 2), rot=(0, math.pi / 2, 0), material=mat('bung', '#4a3424', 0.9)))
    o = join(parts, name)
    for p in o.data.polygons: p.use_smooth = True
    return o

def drum(seed=0, name='drum'):
    r = rng(seed)
    col = r.choice(['#2f6f8f', '#b8402a', '#e3b13a', '#3c6e47', '#2c2f33', '#7d8792'])
    R, H = 0.29, 0.88
    m = mat('drum_' + col, col, 0.45, 0.4)
    prof = [(0.0, 0.0), (R - 0.02, 0.0), (R, 0.012), (R + 0.008, 0.025), (R, 0.04)]
    for zc in (H * 0.33, H * 0.67):
        prof += [(R, zc - 0.03), (R + 0.012, zc - 0.012), (R + 0.012, zc + 0.012), (R, zc + 0.03)]
    prof += [(R, H - 0.04), (R + 0.008, H - 0.025), (R, H - 0.012), (R - 0.02, H), (R - 0.022, H - 0.012), (0, H - 0.012)]
    parts = [lathe(prof, 28, m, cap_top=False, cap_bottom=False, smooth=True)]
    cm = mat('bung_steel', '#9aa0a6', 0.35, 0.8)
    parts.append(cyl(0.035, 0.035, 0.02, 10, loc=(R * 0.6, 0, H - 0.012), material=cm))
    parts.append(cyl(0.02, 0.02, 0.02, 8, loc=(-R * 0.6, 0, H - 0.012), material=cm))
    if r.random() < 0.6:
        lab = mat('drum_label', r.choice(['#f1ece2', '#e3a948', '#151515']), 0.6)
        a = r.uniform(0, 6.28)
        o = box((0.004, 0.2, 0.16), (R + 0.002, 0, H * 0.5), material=lab)
        o.data.transform(Matrix.Rotation(a, 4, 'Z')); parts.append(o)
    return join(parts, name)

CONTAINER_LEN = {10: 2.991, 20: 6.058, 40: 12.192}
LINE_COLOURS = ['#b8402a', '#2f6f8f', '#3c6e47', '#d0822f', '#7d8792', '#e3c14a', '#5a3f72', '#1f4e79']

def container(seed=0, name='container', length=None):
    """ISO container: 2.438 m wide, 2.591 m high, trapezoidal side corrugation, corner castings, cargo doors with lock rods."""
    r = rng(seed)
    ft = length or r.choice([10, 20, 20, 40])
    L, W, H = CONTAINER_LEN[ft], 2.438, 2.591
    col = r.choice(LINE_COLOURS)
    body = mat('ctr_' + col, col, 0.55, 0.25)
    frame = mat('ctr_frame_' + col, col, 0.5, 0.3)
    dark = mat('ctr_dark', '#2b2b2b', 0.7, 0.3)
    parts = []
    post, rail = 0.16, 0.16
    # corrugated long walls
    pitch, depth = 0.278, 0.036
    def corrugated(length, height, axis_len_x=True):
        verts, faces = [], []
        xs = []
        n = int(length / pitch)
        for i in range(n):
            x0 = -length / 2 + i * pitch
            for f, d in ((0.0, 0), (0.18, depth), (0.5, depth), (0.68, 0)):
                xs.append((x0 + f * pitch, d))
        xs.append((length / 2, 0))
        for x, d in xs:
            verts += [(x, d, 0), (x, d, height)]
        for i in range(len(xs) - 1):
            a = 2 * i
            faces.append((a, a + 2, a + 3, a + 1))
        return verts, faces
    for side in (1, -1):
        v, f = corrugated(L - 2 * post, H - 2 * rail)
        o = mesh('wall', [(x, side * (W / 2 - 0.04 + d * (1 if side > 0 else -1) * 0 + (d if side > 0 else -d)), z + rail) for x, y0, z in v for d in [y0]], f, body)
        parts.append(o)
    # front (blind) end corrugated across Y, roof panels, floor
    v, f = corrugated(W - 2 * post, H - 2 * rail)
    parts.append(mesh('front', [(L / 2 - 0.04 + d, x, z + rail) for x, d, z in v], f, body))
    parts.append(box((L - 0.1, W - 0.12, 0.03), (0, 0, H - 0.05), material=body))
    for i in range(int(L / 0.6)):
        parts.append(box((0.22, W - 0.2, 0.02), (-L / 2 + 0.4 + i * 0.6, 0, H - 0.025), material=body))
    parts.append(box((L - 0.1, W - 0.12, 0.05), (0, 0, 0.1), material=dark))
    # frame: corner posts, top and bottom rails, end headers
    for sx in (1, -1):
        for sy in (1, -1):
            parts.append(box((post, post, H), (sx * (L / 2 - post / 2), sy * (W / 2 - post / 2), H / 2), material=frame))
            for sz in (0, 1):
                parts.append(box((0.178, 0.162, 0.118), (sx * (L / 2 - 0.089), sy * (W / 2 - 0.081), 0.059 + sz * (H - 0.118)), material=dark))
        for sz in (0, 1):
            parts.append(box((post, W, rail), (sx * (L / 2 - post / 2), 0, rail / 2 + sz * (H - rail)), material=frame))
    for sy in (1, -1):
        for sz in (0, 1):
            parts.append(box((L, post * 0.8, rail), (0, sy * (W / 2 - post * 0.4), rail / 2 + sz * (H - rail)), material=frame))
    # cargo doors at -X: two leaves, four lock rods with cams and handles, hinges
    dx = -L / 2 + 0.03
    for sy in (1, -1):
        leaf = box((0.03, W / 2 - post - 0.01, H - 2 * rail), (dx, sy * (W / 4 - post / 2 + 0.005), H / 2), material=body)
        parts.append(leaf)
        for k in range(5):
            parts.append(box((0.02, W / 2 - post - 0.05, 0.05), (dx - 0.02, sy * (W / 4 - post / 2), rail + 0.25 + k * (H - 2 * rail - 0.5) / 4), material=body))
    rm = mat('lockrod', '#9aa0a6', 0.35, 0.8)
    for yy in (-0.85, -0.3, 0.3, 0.85):
        parts.append(rod((dx - 0.05, yy, 0.12), (dx - 0.05, yy, H - 0.12), 0.018, 6, rm))
        parts.append(box((0.03, 0.06, 0.08), (dx - 0.05, yy, 0.18), material=rm))
        parts.append(box((0.03, 0.06, 0.08), (dx - 0.05, yy, H - 0.18), material=rm))
        parts.append(box((0.025, 0.28, 0.035), (dx - 0.08, yy + (0.14 if yy < 0 else -0.14), 1.1), material=rm))
    for sy in (1, -1):
        for z in (0.5, 1.3, 2.1):
            parts.append(cyl(0.025, 0.025, 0.12, 8, loc=(dx - 0.03, sy * (W / 2 - 0.02), z - 0.06), material=dark))
    # placard band
    parts.append(box((0.01, 0.6, 0.18), (L / 2 + 0.001, 0, H - 0.45), material=mat('placard', '#f1ece2', 0.6)))
    o = join(parts, name)
    return o

def ingot_pallet(seed=0, name='ingots'):
    r = rng(seed)
    metal, col, rough = r.choice([('steel', '#8d959e', 0.35), ('aluminium', '#c9ccd1', 0.3), ('copper', '#b87333', 0.3), ('lead', '#5d6266', 0.5), ('gold', '#d4af37', 0.2)])
    pm = mat('pallet', '#b8956a', 0.9)
    parts = []
    PL, PW = 1.2, 1.0
    for y in (-PW / 2 + 0.05, 0, PW / 2 - 0.05):
        parts.append(box((PL, 0.1, 0.1), (0, y, 0.07), material=pm, bevel=0.005))
    for i in range(7):
        parts.append(box((0.14, PW, 0.022), (-PL / 2 + 0.07 + i * (PL - 0.14) / 6, 0, 0.131), material=pm, bevel=0.003))
    for i in range(3):
        parts.append(box((0.14, PW, 0.02), (-PL / 2 + 0.07 + i * (PL - 0.14) / 2, 0, 0.01), material=pm))
    im = mat('ingot_' + metal, col, rough, 1.0)
    il, iw, ih = 0.5, 0.16, 0.09
    def ingot(c, rotz):
        b0, t0 = (il / 2, iw / 2), (il / 2 - 0.03, iw / 2 - 0.02)
        v = [(-b0[0], -b0[1], 0), (b0[0], -b0[1], 0), (b0[0], b0[1], 0), (-b0[0], b0[1], 0),
             (-t0[0], -t0[1], ih), (t0[0], -t0[1], ih), (t0[0], t0[1], ih), (-t0[0], t0[1], ih)]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        M = Matrix.Translation(c) @ Matrix.Rotation(rotz, 4, 'Z')
        return mesh('ingot', [M @ Vector(p) for p in v], f, im)
    layers = r.randint(3, 6)
    z = 0.142
    for L_ in range(layers):
        if L_ % 2 == 0:
            for i in range(2):
                for j in range(5):
                    parts.append(ingot((-0.27 + i * 0.54, -0.36 + j * 0.18, z), 0))
        else:
            for i in range(6):
                for j in range(2):
                    parts.append(ingot((-0.45 + i * 0.18, -0.25 + j * 0.5, z), math.pi / 2))
        z += ih + 0.002
    sm = mat('strap', '#2f6f8f', 0.6)
    for x in (-0.3, 0.3):
        parts.append(box((0.03, PW + 0.01, 0.005), (x, 0, z + 0.002), material=sm))
    return join(parts, name)

def ice(seed=0, name='ice'):
    r = rng(seed)
    kind = ['block', 'floe', 'shard'][seed % 3]
    sx, sy, sz = {'block': (1.3, 1.1, 0.9), 'floe': (2.6, 2.0, 0.45), 'shard': (0.9, 0.8, 1.4)}[kind]
    bm = bmesh.new()
    for _ in range(40):
        u, v, w = r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1)
        if kind == 'block':
            u, v, w = [max(-1, min(1, x * 1.6)) for x in (u, v, w)]
        bm.verts.new((u * sx / 2, v * sy / 2, w * sz / 2))
    bmesh.ops.convex_hull(bm, input=bm.verts)
    o = obj_from_bm(bm, name, mat('ice', '#a9d6e5', 0.12, 0.0, transmission=0.35))
    m2 = mat('snowcap', '#f4f8fa', 0.9)
    o.data.materials.append(m2)
    for p in o.data.polygons:
        if p.normal.z > 0.75: p.material_index = 1
    return o

def beach_ball(seed=0, name='beach_ball'):
    r = rng(seed)
    sets = [['#f1ece2', '#d64b2c', '#f1ece2', '#e3a948', '#f1ece2', '#2f6f8f'],
            ['#d64b2c', '#e3a948', '#3c6e47', '#2f6f8f', '#f1ece2', '#5a3f72']]
    cols = r.choice(sets)
    R = r.uniform(0.45, 0.6)
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=R, matrix=Matrix.Translation((0, 0, R)))
    o = obj_from_bm(bm, name, None, smooth=True)
    for c in cols: o.data.materials.append(mat('gore_' + c, c, 0.35))
    o.data.materials.append(mat('cap', '#f1ece2', 0.35))
    for p in o.data.polygons:
        c = p.center
        if abs(c.z - R) > R * 0.86: p.material_index = len(cols)
        else: p.material_index = int(((math.atan2(c.y, c.x) + math.pi) / (2 * math.pi)) * 6) % 6
    return o

def sack(seed=0, name='sack'):
    r = rng(seed)
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    sx, sy, sz = r.uniform(0.38, 0.45), r.uniform(0.28, 0.32), r.uniform(0.32, 0.4)
    off = Vector((r.random() * 9, r.random() * 9, 0))
    for v in bm.verts:
        p = v.co.copy()
        # pillow-like: squarish in plan, flattened, sagging lumps
        q = Vector((math.copysign(abs(p.x) ** 0.6, p.x), math.copysign(abs(p.y) ** 0.6, p.y), p.z))
        n = noise.noise(p * 2.2 + off) * 0.08
        z = q.z * (1 if q.z > 0 else 0.55)
        v.co = Vector((q.x * sx * (1 + n), q.y * sy * (1 + n), (z + 0.55) * sz * (1 + n * 0.5)))
    bmat = mat('burlap', r.choice(['#b59a6b', '#a68c5e', '#c2ab7d']), 0.95)
    o = obj_from_bm(bm, name, bmat, smooth=True)
    ear = cyl(0.07, 0.02, 0.16, 8, loc=(sx * 0.95, 0, sz * 0.62), rot=(0, math.pi / 2, 0), material=bmat)
    tie = torus(0.055, 0.015, 10, 5, loc=(sx * 1.0, 0, sz * 0.62), rot=(0, math.pi / 2, 0), material=mat('twine', '#6e5a3a', 0.9))
    stencil = box((0.18, 0.003, 0.12), (0, -sy * 0.93, sz * 0.6), material=mat('stencil', '#3b4a6b', 0.9))
    return join([o, ear, tie, stencil], name)

def rope_coil(seed=0, name='rope_coil'):
    r = rng(seed)
    turns, rr, R0 = r.randint(4, 7), 0.025, r.uniform(0.22, 0.3)
    col = r.choice(['#cbbd9b', '#e3a948', '#2f6f8f', '#d64b2c'])
    verts, faces = [], []
    N, sides = turns * 24, 6
    for i in range(N + 1):
        a = 2 * math.pi * i / 24
        layer = i / N
        R = R0 + rr * 2.1 * (i / 24) * 0.35
        z = rr + (i // 24 % 2) * rr * 1.5
        for j in range(sides):
            b = 2 * math.pi * j / sides
            verts.append(((R + rr * math.cos(b)) * math.cos(a), (R + rr * math.cos(b)) * math.sin(a), z + rr * math.sin(b)))
    for i in range(N):
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append((i * sides + j, (i + 1) * sides + j, (i + 1) * sides + j2, i * sides + j2))
    return mesh(name, verts, faces, mat('rope_' + col, col, 0.9), smooth=True)

TYPES = [('Crate', crate), ('Barrel', barrel), ('Steel drum', drum), ('Ingot pallet', ingot_pallet),
         ('Ice', ice), ('Beach ball', beach_ball), ('Sack', sack), ('Rope coil', rope_coil)]

def container10(seed=0, name='container10'): return container(seed, name, 10)
def container20(seed=0, name='container20'): return container(seed, name, 20)
def container40(seed=0, name='container40'): return container(seed, name, 40)
CONTAINER_TYPES = [('ISO 10 ft', container10), ('ISO 20 ft', container20), ('ISO 40 ft', container40)]
