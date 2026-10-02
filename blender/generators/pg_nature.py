"""Nature class: pines, broadleaf trees, palms, shrubs, grass tufts, and rocks (boulder, slab, sea stack, pebbles).
Foliage and rock colour is baked into vertex colours ('Col') so it survives glTF export."""
import math, random
from mathutils import Vector, Color
from pg_core import *

def hsv(h, s, v):
    c = Color(); c.hsv = (h % 1.0, max(0, min(1, s)), max(0, min(1, v)))
    return (lin(c.r), lin(c.g), lin(c.b))

def displace(o, amp, freq, seed, octaves=3, axis_scale=(1, 1, 1)):
    off = Vector((seed * 7.1, seed * 3.3, seed * 5.7))
    for v in o.data.vertices:
        n = fbm3(v.co * freq + off, octaves)
        nrm = v.co.normalized() if v.co.length > 1e-6 else Vector((0, 0, 1))
        v.co += Vector((nrm.x * axis_scale[0], nrm.y * axis_scale[1], nrm.z * axis_scale[2])) * n * amp

def trunk(h, r0, r1, bend=0.0, seg=7, rings=6, color='#5a3f2a', seed=0):
    r = rng(seed)
    prof = []
    verts, faces = [], []
    lean = Vector((r.uniform(-1, 1), r.uniform(-1, 1), 0)).normalized() * bend
    for k in range(rings + 1):
        t = k / rings
        rr = r0 + (r1 - r0) * t
        c = lean * (t * t) * h
        for i in range(seg):
            a = 2 * math.pi * i / seg
            verts.append((c.x + rr * math.cos(a), c.y + rr * math.sin(a), h * t))
    for k in range(rings):
        for i in range(seg):
            i2 = (i + 1) % seg
            faces.append((k * seg + i, k * seg + i2, (k + 1) * seg + i2, (k + 1) * seg + i))
    o = mesh('trunk', verts, faces, mat('bark_' + color, color, 0.95))
    return o, lean * h

def pine(seed=0, name='pine'):
    r = rng(seed)
    H = r.uniform(5, 11); tiers = r.randint(4, 7)
    t, top = trunk(H * 0.35, H * 0.035, H * 0.02, 0.04, seed=seed)
    parts = [t]
    hue = r.uniform(0.27, 0.36)
    for i in range(tiers):
        f = i / max(1, tiers - 1)
        z0 = H * (0.18 + 0.68 * f)
        rad = H * (0.28 - 0.2 * f) * r.uniform(0.85, 1.1)
        hh = H * (0.34 - 0.12 * f)
        bm = bmesh.new()
        seg = r.choice([7, 8, 9])
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=seg, radius1=rad, radius2=0.0, depth=hh, matrix=Matrix.Translation((0, 0, hh / 2)))
        for v in bm.verts:
            if v.co.z < hh * 0.05 and v.co.xy.length > rad * 0.5:  # droop the skirt tips unevenly
                v.co.z -= r.uniform(0.05, 0.25) * hh
                v.co.xy *= r.uniform(0.88, 1.08)
        bmesh.ops.transform(bm, matrix=Matrix.Translation((top.x * f, top.y * f, z0)) @ Matrix.Rotation(r.uniform(0, 6.28), 4, 'Z') @ Matrix.Rotation(r.uniform(-0.06, 0.06), 4, 'X'), verts=bm.verts)
        o = obj_from_bm(bm, 'tier')
        o.data.materials.append(mat('foliage', '#ffffff', 0.85, vcol=True))
        sat, val = r.uniform(0.45, 0.6), r.uniform(0.22, 0.32)
        set_vcol(o, lambda co, n, z0=z0: hsv(hue + 0.01 * n.z, sat, val * (0.75 + 0.45 * max(0, n.z)) * (0.85 + 0.25 * (co.z - z0) / max(hh, 1e-3))))
        parts.append(o)
    t.data.materials.clear(); t.data.materials.append(mat('foliage', '#ffffff', 0.85, vcol=True))
    set_vcol(t, lambda co, n: hsv(0.07, 0.45, 0.22))
    return join(parts, name)

def broadleaf(seed=0, name='broadleaf'):
    r = rng(seed)
    H = r.uniform(5, 9)
    autumn = r.random() < 0.3
    t, top = trunk(H * 0.5, H * 0.05, H * 0.03, 0.08, seed=seed)
    parts = [t]
    vm = mat('foliage', '#ffffff', 0.85, vcol=True)
    t.data.materials.clear(); t.data.materials.append(vm)
    set_vcol(t, lambda co, n: hsv(0.07, 0.4, 0.2))
    base = Vector((top.x, top.y, H * 0.5))
    blobs = []
    for b in range(r.randint(3, 5)):
        a = r.uniform(0, 6.28); el = r.uniform(0.5, 1.1)
        L = H * r.uniform(0.22, 0.32)
        tip = base + Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el))) * L
        br = rod(base, tip, H * 0.018, 5, vm); set_vcol(br, lambda co, n: hsv(0.07, 0.4, 0.2)); parts.append(br)
        blobs.append((tip, H * r.uniform(0.18, 0.26)))
    blobs.append((base + Vector((0, 0, H * 0.32)), H * 0.28))
    hue = r.uniform(0.06, 0.12) if autumn else r.uniform(0.22, 0.3)
    for c, rad in blobs:
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=rad, matrix=Matrix.Translation(c))
        o = obj_from_bm(bm, 'canopy', vm)
        displace(o, rad * 0.35, 1.6 / rad, seed + len(parts))
        for v in o.data.vertices:
            if v.co.z < c.z - rad * 0.3: v.co.z = c.z - rad * 0.3 + (v.co.z - (c.z - rad * 0.3)) * 0.3  # flatter undersides
        val = r.uniform(0.3, 0.4)
        set_vcol(o, lambda co, n: hsv(hue + 0.02 * fbm3(co * 0.8, 2), 0.6 if not autumn else 0.75, val * (0.6 + 0.5 * max(0, n.z))))
        parts.append(o)
    return join(parts, name)

def palm(seed=0, name='palm'):
    r = rng(seed)
    H = r.uniform(6, 10)
    vm = mat('foliage', '#ffffff', 0.85, vcol=True)
    lean = Vector((r.uniform(-1, 1), r.uniform(-1, 1), 0)).normalized() * H * r.uniform(0.15, 0.35)
    parts = []
    N = 12
    pts = [Vector((lean.x * (k / N) ** 2, lean.y * (k / N) ** 2, H * k / N)) for k in range(N + 1)]
    for k in range(N):
        seg = rod(pts[k], pts[k + 1] + (pts[k + 1] - pts[k]) * 0.05, H * (0.03 - 0.008 * k / N) * (1.15 if k % 2 else 1.0), 7, vm)
        set_vcol(seg, lambda co, n, k=k: hsv(0.08, 0.35, 0.32 + 0.05 * (k % 2)))
        parts.append(seg)
    crown = pts[-1]
    nf = r.randint(7, 11)
    for i in range(nf):
        a = 2 * math.pi * i / nf + r.uniform(-0.2, 0.2)
        L = H * r.uniform(0.38, 0.5); droop = r.uniform(0.5, 0.9)
        verts, faces = [], []
        M = 10
        for k in range(M + 1):
            t = k / M
            d = Vector((math.cos(a), math.sin(a), 0)) * L * t
            z = L * (0.35 * t - droop * t * t)
            w = L * 0.13 * math.sin(math.pi * min(1, t * 1.1)) * (1 - 0.3 * t)
            side = Vector((-math.sin(a), math.cos(a), 0)) * w
            c = crown + d + Vector((0, 0, z))
            verts += [tuple(c - side + Vector((0, 0, -w * 0.25))), tuple(c), tuple(c + side + Vector((0, 0, -w * 0.25)))]
        for k in range(M):
            p = 3 * k
            faces += [(p, p + 3, p + 4, p + 1), (p + 1, p + 4, p + 5, p + 2)]
        o = mesh('frond', verts, faces, vm)
        hue = r.uniform(0.24, 0.31)
        set_vcol(o, lambda co, n: hsv(hue, 0.6, 0.3 + 0.12 * abs(n.z)))
        parts.append(o)
    for i in range(r.randint(2, 5)):
        a = r.uniform(0, 6.28)
        c = ico(H * 0.025, 1, tuple(crown + Vector((math.cos(a) * H * 0.04, math.sin(a) * H * 0.04, -H * 0.03))), vm)
        set_vcol(c, lambda co, n: hsv(0.09, 0.6, 0.2)); parts.append(c)
    return join(parts, name)

def shrub(seed=0, name='shrub'):
    r = rng(seed)
    vm = mat('foliage', '#ffffff', 0.85, vcol=True)
    parts = []
    hue = r.uniform(0.2, 0.32)
    flowers = r.random() < 0.35
    for i in range(r.randint(3, 6)):
        rad = r.uniform(0.35, 0.7)
        c = Vector((r.uniform(-0.5, 0.5), r.uniform(-0.5, 0.5), rad * 0.7))
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=rad, matrix=Matrix.Translation(c))
        o = obj_from_bm(bm, 'blob', vm)
        displace(o, rad * 0.3, 2.0 / rad, seed * 13 + i)
        fh = r.choice([0.95, 0.0, 0.12])
        set_vcol(o, lambda co, n: hsv(fh, 0.55, 0.75) if flowers and fbm3(co * 3.0, 2) > 0.18 and n.z > 0.2 else hsv(hue, 0.55, 0.28 * (0.7 + 0.5 * max(0, n.z))))
        parts.append(o)
    return join(parts, name)

def grass(seed=0, name='grass'):
    r = rng(seed)
    vm = mat('foliage', '#ffffff', 0.85, vcol=True)
    verts, faces = [], []
    hue = r.uniform(0.18, 0.3)
    for i in range(r.randint(25, 45)):
        a = r.uniform(0, 6.28); d = r.uniform(0, 0.25)
        base = Vector((math.cos(a) * d, math.sin(a) * d, 0))
        h = r.uniform(0.3, 0.7); lean = Vector((math.cos(a), math.sin(a), 0)) * r.uniform(0.05, 0.25)
        side = Vector((-math.sin(a + 1.2), math.cos(a + 1.2), 0)) * 0.025
        n = len(verts)
        verts += [tuple(base - side), tuple(base + side), tuple(base + lean * 0.5 + Vector((0, 0, h * 0.55)) + side * 0.6),
                  tuple(base + lean * 0.5 + Vector((0, 0, h * 0.55)) - side * 0.6), tuple(base + lean + Vector((0, 0, h)))]
        faces += [(n, n + 1, n + 2, n + 3), (n + 3, n + 2, n + 4)]
    o = mesh(name, verts, faces, vm)
    set_vcol(o, lambda co, n: hsv(hue - 0.06 * co.z, 0.55, 0.22 + 0.35 * co.z))
    return o

# ---------------------------------------------------------------- rocks
ROCKS = {'granite': (0.08, 0.07, 0.66), 'basalt': (0.6, 0.06, 0.42), 'sandstone': (0.07, 0.38, 0.78), 'limestone': (0.12, 0.08, 0.84)}

def _rock_colour(o, seed, kind, base_val=None):
    r = rng(seed)
    h, s, v = ROCKS[kind]
    v = base_val or v
    off = Vector((seed * 1.7, seed * 2.9, 0.3))
    def col(co, n):
        k = fbm3(co * 1.3 + off, 3)
        strata = 0.5 + 0.5 * math.sin(co.z * 9.0 + k * 3) if kind == 'sandstone' else 0.5
        val = v * (0.78 + 0.35 * k + 0.12 * strata) * (0.75 + 0.3 * max(0, n.z))
        if n.z > 0.6 and fbm3(co * 2.5 + off * 2, 2) > 0.22:  # sparse lichen on upward faces
            return hsv(0.17, 0.3, val * 0.92)
        return hsv(h, s, val)
    o.data.materials.clear(); o.data.materials.append(mat('rock', '#ffffff', 0.9, vcol=True))
    set_vcol(o, col)

def boulder(seed=0, name='boulder'):
    r = rng(seed)
    kind = r.choice(list(ROCKS))
    R = r.uniform(0.6, 1.6)
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=R)
    o = obj_from_bm(bm, name)
    sx, sy, sz = r.uniform(0.9, 1.4), r.uniform(0.75, 1.1), r.uniform(0.55, 0.85)
    for v in o.data.vertices: v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
    displace(o, R * 0.35, 0.9 / R, seed, 4)
    # fracture facets: flatten against a few random planes
    for _ in range(r.randint(2, 5)):
        nrm = Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-0.2, 1))).normalized()
        d = R * r.uniform(0.55, 0.8)
        for v in o.data.vertices:
            k = v.co.dot(nrm)
            if k > d: v.co -= nrm * (k - d)
    zmin = min(v.co.z for v in o.data.vertices)
    for v in o.data.vertices:
        if v.co.z < zmin + R * 0.2: v.co.z = zmin + R * 0.2 - (zmin + R * 0.2 - v.co.z) * 0.2
    _rock_colour(o, seed, kind)
    return o

def slab(seed=0, name='slab'):
    r = rng(seed)
    kind = r.choice(['sandstone', 'limestone', 'basalt'])
    W = r.uniform(2.0, 3.5)
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    o = obj_from_bm(bm, name)
    steps = r.randint(3, 5)
    for v in o.data.vertices:
        p = Vector((v.co.x * W, v.co.y * W * 0.7, v.co.z * 0.9))
        v.co = p
    displace(o, 0.5, 0.6, seed, 3, (1, 1, 0.3))
    for v in o.data.vertices:  # terrace into strata
        if v.co.z > -0.3:
            z = v.co.z
            q = math.floor(z * steps / 0.9) * 0.9 / steps
            v.co.z = q + (z - q) * 0.25
            v.co.xy *= 1 - 0.12 * (z / 0.9)
    _rock_colour(o, seed, kind)
    return o

def sea_stack(seed=0, name='sea_stack'):
    r = rng(seed)
    kind = r.choice(['basalt', 'sandstone', 'granite'])
    H = r.uniform(5, 10); R = H * r.uniform(0.18, 0.26)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=12, radius1=R, radius2=R * 0.7, depth=H, matrix=Matrix.Translation((0, 0, H / 2)))
    bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 0.1], cuts=10, use_grid_fill=True)
    o = obj_from_bm(bm, name)
    off = Vector((seed, seed * 2, 0))
    for v in o.data.vertices:
        if v.co.z < H - 0.05:
            rr = Vector((v.co.x, v.co.y, 0))
            n = fbm3(Vector((v.co.x, v.co.y, v.co.z * 0.6)) * 0.5 + off, 4)
            notch = 1 - 0.28 * math.exp(-((v.co.z - 0.8) ** 2) / 0.3)  # wave-cut notch at the waterline
            ledge = 1 + 0.1 * (1 if math.sin(v.co.z * 2.2 + seed) > 0.6 else 0)  # bedding ledges
            v.co.xy = rr.xy * (1 + 0.6 * n) * notch * ledge
        if v.co.z >= H - 0.05:
            v.co.z += fbm3(v.co * 0.8 + off, 2) * 0.8
    _rock_colour(o, seed, kind)
    # a cap of turf
    cap = [p for p in o.data.polygons if p.normal.z > 0.8 and p.center.z > H * 0.9]
    gm = mat('turf', '#5f7f3a', 0.9)
    o.data.materials.append(gm)
    for p in cap: p.material_index = 1
    return o

def pebbles(seed=0, name='pebbles'):
    r = rng(seed)
    parts = []
    for i in range(r.randint(8, 16)):
        R = r.uniform(0.08, 0.3)
        a, d = r.uniform(0, 6.28), r.uniform(0, 0.9)
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=R)
        o = obj_from_bm(bm, 'pebble')
        for v in o.data.vertices: v.co = Vector((v.co.x * 1.3, v.co.y, v.co.z * 0.6 + R * 0.6)) + Vector((math.cos(a) * d, math.sin(a) * d, 0))
        displace(o, R * 0.15, 2 / R, seed * 31 + i)
        _rock_colour(o, seed * 31 + i, r.choice(list(ROCKS)))
        parts.append(o)
    o = join(parts, name)
    for p in o.data.polygons: p.use_smooth = True
    return o

VEG_TYPES = [('Pine', pine), ('Broadleaf', broadleaf), ('Palm', palm)]
GROUND_TYPES = [('Shrub', shrub), ('Grass tuft', grass)]
ROCK_TYPES = [('Boulder', boulder), ('Strata slab', slab), ('Sea stack', sea_stack), ('Pebble cluster', pebbles)]
