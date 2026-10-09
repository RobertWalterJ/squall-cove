"""Builds assets/fire.glb (+ fire.glb.b64.txt): stylised low-poly fire tongues, clusters, embers, ash, smoke, baked flicker loops.
Pure python + numpy. Metres, +Y up, +Z forward. Vertex colours (COLOR_0, linear), unlit material `fire_vc` (KHR_materials_unlit,
double sided); smoke/ash use `smoke_vc` (lit, vertex colours). Tongue meshes are shared by every cluster child (mesh instancing).
usage: python build_fire.py [game dir]"""
import sys, os, json, struct, base64, math
import numpy as np

GAME = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PI = math.pi
LOOP = 1.2          # seconds
NKEY = 25           # keyframes per loop (last == first)

def lin(c):
    c = np.asarray(c, float)
    return np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)

# ------------------------------------------------------------------ colours (authored in sRGB, stored linear)
FIRE_STOPS = [(0.0, (0.60, 0.04, 0.03)), (0.30, (0.95, 0.30, 0.04)), (0.62, (1.0, 0.62, 0.08)), (1.0, (1.0, 0.82, 0.12))]
CORE_STOPS = [(0.0, (0.95, 0.38, 0.05)), (0.45, (1.0, 0.85, 0.40)), (1.0, (1.0, 0.97, 0.78))]
def ramp(stops, f):
    f = min(max(f, 0.0), 1.0)
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if f <= b:
            u = (f - a) / (b - a); return np.array(ca) * (1 - u) + np.array(cb) * u
    return np.array(stops[-1][1])

# ------------------------------------------------------------------ geometry: (V, F, C)
class Geo:
    def __init__(self, V=None, F=None, C=None):
        self.V = np.zeros((0, 3)) if V is None else np.asarray(V, float)
        self.F = np.zeros((0, 3), int) if F is None else np.asarray(F, int)
        self.C = np.zeros((0, 3)) if C is None else np.asarray(C, float)
    def add(self, g):
        o = len(self.V); self.V = np.vstack([self.V, g.V]); self.F = np.vstack([self.F, g.F + o]); self.C = np.vstack([self.C, g.C]); return self

def orient(V, F, cen):
    F = np.asarray(F, int).copy(); a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    flip = (np.cross(b - a, c - a) * ((a + b + c) / 3 - cen)).sum(1) < 0
    F[flip] = F[flip][:, [0, 2, 1]]; return F

def lobe(h, r, ang, lean, bend, twist, thick, tipflick, base, Htot, stops, rprof=0.75, rings=(0.0, 0.30, 0.60, 0.85), swell=0.35):
    """one tapered, curved, twisted blade. Open bottom (no cap), ends in a point. base=(x,z) of its root. 4 ring x 4 verts + tip = 17 verts, 28 tris."""
    d = np.array([math.cos(ang), math.sin(ang)])        # lean/bend direction in xz
    V = []; C = []
    for t in rings:
        off = d * (lean * h * t + bend * h * t * t)
        c = np.array([base[0] + off[0], h * t * (1 - 0.06 * t), base[1] + off[1]])
        rx = r * (1 - t) ** rprof * (1 + swell * math.sin(PI * min(t * 1.1, 1)))
        rz = rx * thick; tw = twist * t + ang
        cs, sn = math.cos(tw), math.sin(tw)
        for k in range(4):
            a = PI / 4 + k * PI / 2; lx = math.cos(a) * rx; lz = math.sin(a) * rz
            V.append([c[0] + lx * cs - lz * sn, c[1], c[2] + lx * sn + lz * cs])
    off = d * (lean * h + bend * h + tipflick * h)
    V.append([base[0] + off[0], h * 0.95, base[1] + off[1]])
    V = np.array(V); F = []
    nr = len(rings)
    for i in range(nr - 1):
        for k in range(4):
            a = i * 4 + k; b = i * 4 + (k + 1) % 4; c = (i + 1) * 4 + k; e = (i + 1) * 4 + (k + 1) % 4
            F += [(a, b, e), (a, e, c)]
    tip = nr * 4
    for k in range(4): F.append(((nr - 1) * 4 + k, (nr - 1) * 4 + (k + 1) % 4, tip))
    cen = np.array([base[0], h * 0.5, base[1]]) + np.array([d[0], 0, d[1]]) * (lean * h * 0.4)
    F = orient(V, F, cen)
    C = np.array([ramp(stops, v[1] / Htot) for v in V])
    return Geo(V, F, C)

def tongue(H, nlobe, seed, wide=1.0):
    """H tall; nlobe outer lobes (incl. the main) + 1 hot core lobe."""
    rg = np.random.RandomState(seed)
    R = 0.21 * H * wide
    g = Geo()
    spread = 0.8 * R
    a0 = rg.uniform(0, 2 * PI)
    # main
    g.add(lobe(H, R, a0 + rg.uniform(-.5, .5), rg.uniform(.02, .08), rg.uniform(.10, .22) * rg.choice([-1, 1]), rg.uniform(.5, 1.0) * rg.choice([-1, 1]),
               0.7, rg.uniform(.05, .12), (0, 0), H, FIRE_STOPS))
    hs = [0.72, 0.58, 0.46, 0.38]
    for j in range(nlobe - 1):
        a = a0 + PI * 0.5 + 2 * PI * j / max(nlobe - 1, 1) + rg.uniform(-.35, .35)
        hh = H * hs[j] * rg.uniform(.9, 1.1)
        base = (math.cos(a) * spread, math.sin(a) * spread * 0.8)
        g.add(lobe(hh, R * rg.uniform(.62, .78), a, rg.uniform(.10, .22), rg.uniform(.12, .26) * rg.choice([-1, 1]), rg.uniform(.4, 1.1) * rg.choice([-1, 1]),
                   0.6, rg.uniform(.04, .12), base, H, FIRE_STOPS))
    # hot core: short, fat, pale; sits over the base of the main lobe so it shows through the thin sides
    hc = H * 0.5
    g.add(lobe(hc, R * 1.05, a0 + 1.0, 0.03, 0.06, 0.6, 1.25, 0.04, (0, 0.0), hc, CORE_STOPS, rprof=0.9, swell=0.1))
    g.C = np.array([lin(c) for c in g.C])
    return g

def ico(sub, rad, seed, squash=0.85):
    t = (1 + 5 ** .5) / 2
    V = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
         (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    V = [np.array(v, float) / np.linalg.norm(v) for v in V]
    for _ in range(sub):
        cache = {}; nf = []
        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache: V.append((V[a] + V[b]) / 2 / np.linalg.norm((V[a] + V[b]) / 2)); cache[k] = len(V) - 1
            return cache[k]
        for a, b, c in F:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a); nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        F = nf
    rg = np.random.RandomState(seed)
    V = np.array(V) * (1 + rg.uniform(-.2, .2, (len(V), 1))) * rad * np.array([1, squash, 1])
    F = orient(V, F, np.zeros(3))
    return V, F

def puff(sub, rad, seed):
    V, F = ico(sub, rad, seed)
    f = (V[:, 1] / (rad * 1.2) + 1) / 2          # 0 bottom .. 1 top
    C = np.array([lin(np.array([0.24, 0.24, 0.26]) * (1 - x) + np.array([0.62, 0.62, 0.64]) * x) for x in f.clip(0, 1)])
    return Geo(V, F, C)

def shard(sx, sz, sy, col_lo, col_hi, seed):
    rg = np.random.RandomState(seed)
    V = np.array([[0, sy, 0], [sx * rg.uniform(.7, 1), 0, 0], [-sx * rg.uniform(.5, 1), 0, sz * rg.uniform(.6, 1)], [-sx * rg.uniform(.3, .8), 0, -sz * rg.uniform(.6, 1)], [0, -sy * 0.6, 0]])
    F = orient(V, [(0, 1, 2), (0, 2, 3), (0, 3, 1), (4, 2, 1), (4, 3, 2), (4, 1, 3)], np.zeros(3))
    C = lin(np.array([col_hi, col_lo, col_lo, col_lo, col_lo]))
    return Geo(V, F, C)

# ------------------------------------------------------------------ quaternions (x, y, z, w)
def qaxis(ax, a):
    s = math.sin(a / 2); return np.array([ax[0] * s, ax[1] * s, ax[2] * s, math.cos(a / 2)])
def qmul(a, b):
    x1, y1, z1, w1 = a; x2, y2, z2, w2 = b
    return np.array([w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2])
QI = np.array([0, 0, 0, 1.0])

# ------------------------------------------------------------------ scene
MESHES = {}      # name -> (Geo, material name)
class Node:
    def __init__(self, name, mesh=None, t=(0, 0, 0), yaw=0.0, lean=(0.0, 0.0), s=(1, 1, 1)):
        self.name = name; self.mesh = mesh; self.t = np.array(t, float); self.yaw = yaw; self.lean = lean; self.s = np.array(s, float); self.kids = []
    def child(self, *a, **k): n = Node(*a, **k); self.kids.append(n); return n
    def quat(self, ax=0.0, az=0.0):
        return qmul(qmul(qaxis((0, 1, 0), self.yaw), qaxis((1, 0, 0), self.lean[0] + ax)), qaxis((0, 0, 1), self.lean[1] + az))

def mesh(name, geo, mat): MESHES[name] = (geo, mat)

def make_world():
    roots = []
    sizes = {'s': (0.4, 2), 'm': (1.0, 3), 'l': (2.5, 4)}
    seeds = {'s': 10, 'm': 20, 'l': 30}
    for k, (H, nl) in sizes.items():
        for i in range(1, 4):
            nm = 'flame_%s_%02d' % (k, i)
            mesh(nm, tongue(H, nl, seeds[k] + i * 7), 'fire_vc'); roots.append(Node(nm, nm))
    # cluster children: (mesh, x, z, yaw, lean(x,z), scale(x,y,z))
    R = np.random.RandomState(5)
    def tn(root, prefix, specs):
        for i, (m, x, z, yaw, ln, sc) in enumerate(specs):
            root.child('%s_t%d' % (prefix, i), m, (x, 0, z), yaw, ln, sc)
    camp = Node('fire_camp'); sp = []
    for i in range(5):
        a = 2 * PI * i / 5 + 0.3; sp.append(('flame_m_0%d' % (1 + i % 3), math.cos(a) * 0.32, math.sin(a) * 0.32, a, (math.sin(a) * 0.12, -math.cos(a) * 0.12), (0.62, 0.72 + 0.12 * (i % 2), 0.62)))
    tn(camp, 'fire_camp', sp); roots.append(camp)
    bld = Node('fire_building'); sp = []
    sp = [('flame_l_01', -1.95, 0.1, 0.4, (0.0, 0.05), (1.6, 1.15, 1.1)), ('flame_l_02', 0.0, -0.1, 1.5, (0, 0), (1.8, 1.65, 1.2)), ('flame_l_03', 2.0, 0.1, 2.6, (0.0, -0.05), (1.6, 1.3, 1.1)),
          ('flame_m_02', -1.05, -0.35, 3.1, (0, 0.04), (1.6, 2.8, 1.2)), ('flame_m_03', 1.1, -0.35, 4.2, (0, -0.04), (1.6, 2.4, 1.2))]
    tn(bld, 'fire_building', sp); roots.append(bld)
    veh = Node('fire_vehicle'); sp = []
    zs = [-1.3, -0.6, 0.0, 0.65, 1.3]; hs = [0.85, 1.15, 1.35, 1.0, 0.8]; xo = [0.18, -0.2, 0.12, -0.15, 0.1]
    for i in range(5):
        sp.append(('flame_m_0%d' % (1 + (i + 1) % 3), xo[i], zs[i], 1.3 * i, (0.0, 0.0), (1.05, hs[i], 1.05)))
    sp.append(('flame_s_02', 0.55, -0.4, 0.4, (0, -0.15), (1.5, 1.5, 1.5)))
    tn(veh, 'fire_vehicle', sp); roots.append(veh)
    tree = Node('fire_tree'); sp = [('flame_l_02', 0.0, 0.0, 0.2, (0, 0), (0.62, 2.1, 0.62)), ('flame_l_03', 0.2, 0.15, 2.0, (0.05, -0.05), (0.5, 1.4, 0.5)),
                                   ('flame_m_02', -0.25, -0.15, 3.5, (-0.04, 0.06), (0.8, 2.6, 0.8)), ('flame_m_01', 0.05, -0.3, 4.9, (0.05, 0), (0.7, 1.9, 0.7))]
    tn(tree, 'fire_tree', sp); roots.append(tree)
    gr = Node('fire_ground'); sp = []
    for i in range(8):
        a = 2 * PI * i / 8 + 0.2; r = 1.15 + 0.12 * (i % 2)
        sp.append(('flame_s_0%d' % (1 + i % 3), math.cos(a) * r, math.sin(a) * r, a, (math.sin(a) * 0.35, -math.cos(a) * 0.35), (1.15, 1.0 + 0.35 * (i % 3) / 2, 1.15)))
    tn(gr, 'fire_ground', sp); roots.append(gr)
    # embers / ash
    for i, (sx, sy) in enumerate([(0.035, 0.07), (0.045, 0.09), (0.03, 0.12)], 1):
        nm = 'ember_%02d' % i; mesh(nm, shard(sx, sx * 0.8, sy, (1.0, 0.45, 0.06), (1.0, 0.9, 0.4), 40 + i), 'fire_vc'); roots.append(Node(nm, nm))
    for i, (sx, sy) in enumerate([(0.05, 0.012), (0.07, 0.01)], 1):
        nm = 'ash_flake_%02d' % i; mesh(nm, shard(sx, sx * 0.7, sy, (0.12, 0.12, 0.13), (0.30, 0.29, 0.29), 50 + i), 'smoke_vc'); roots.append(Node(nm, nm))
    # smoke
    mesh('smoke_puff_01', puff(0, 0.5, 61), 'smoke_vc'); mesh('smoke_puff_02', puff(1, 0.5, 62), 'smoke_vc'); mesh('smoke_puff_03', puff(1, 0.5, 63), 'smoke_vc')
    for i in (1, 2, 3): roots.append(Node('smoke_puff_%02d' % i, 'smoke_puff_%02d' % i))
    col = Node('smoke_column')
    for i, (y, s, x) in enumerate([(0.55, 0.9, 0.0), (1.6, 1.15, 0.1), (2.9, 1.5, -0.2), (4.4, 1.95, 0.25), (6.2, 2.5, 0.0)]):
        col.child('smoke_column_p%d' % i, 'smoke_puff_0%d' % (1 + i % 3), (x, y, 0.1 * (-1) ** i), 1.1 * i, (0, 0), (s, s * 0.95, s))
    roots.append(col)
    return roots

# ------------------------------------------------------------------ animation
def flicker_keys(node, rg):
    """returns (times, scale keys (N,3), rotation keys (N,4)) -- integer harmonics of the 1.2 s loop, so it is seamless."""
    ph = rg.uniform(0, 2 * PI, 4)
    amp = rg.uniform(0.16, 0.26); amp2 = rg.uniform(0.06, 0.12); sway = rg.uniform(0.05, 0.11)
    T = np.linspace(0, LOOP, NKEY); S = []; Q = []
    for t in T:
        w = 2 * PI * t / LOOP
        sy = 1 + amp * math.sin(w + ph[0]) + amp2 * math.sin(2 * w + ph[1])
        sxz = 1 - 0.35 * (sy - 1)
        S.append(node.s * np.array([sxz, sy, sxz]))
        Q.append(node.quat(sway * math.sin(w + ph[2]) + 0.4 * sway * math.sin(2 * w + ph[3]), sway * math.cos(w + ph[2] * 0.7) + 0.3 * sway * math.sin(2 * w + ph[0])))
    S[-1] = S[0].copy(); Q[-1] = Q[0].copy()
    return T, np.array(S), np.array(Q)

# ------------------------------------------------------------------ glb writer
def build_glb(roots):
    buf = bytearray(); bvs = []; accs = []; meshes = []; nodes = []
    mats = [{'name': 'fire_vc', 'doubleSided': True, 'pbrMetallicRoughness': {'baseColorFactor': [1, 1, 1, 1], 'metallicFactor': 0.0, 'roughnessFactor': 1.0},
             'emissiveFactor': [0, 0, 0], 'extensions': {'KHR_materials_unlit': {}}},
            {'name': 'smoke_vc', 'pbrMetallicRoughness': {'baseColorFactor': [1, 1, 1, 1], 'metallicFactor': 0.0, 'roughnessFactor': 1.0}}]
    mi = {'fire_vc': 0, 'smoke_vc': 1}
    def addbv(b, target=None):
        while len(buf) % 4: buf.append(0)
        d = {'buffer': 0, 'byteOffset': len(buf), 'byteLength': len(b)}
        if target: d['target'] = target
        bvs.append(d); buf.extend(b); return len(bvs) - 1
    def acc(arr, ctype, typ, target=None, minmax=False):
        a = np.ascontiguousarray(arr, dtype='<f4' if ctype == 5126 else '<u4')
        d = {'bufferView': addbv(a.tobytes(), target), 'componentType': ctype, 'count': len(a), 'type': typ}
        if minmax: d['min'] = a.min(0).reshape(-1).tolist() if a.ndim > 1 else [float(a.min())]; d['max'] = a.max(0).reshape(-1).tolist() if a.ndim > 1 else [float(a.max())]
        accs.append(d); return len(accs) - 1
    def acc16(ix):
        a = np.asarray(ix, dtype='<u2'); accs.append({'bufferView': addbv(a.tobytes(), 34963), 'componentType': 5123, 'count': len(a), 'type': 'SCALAR'}); return len(accs) - 1
    mesh_idx = {}
    for name, (g, mt) in MESHES.items():
        if mt == 'fire_vc':      # unlit: indexed, shared vertices, no normals (smallest)
            a, b, c = g.V[g.F[:, 0]], g.V[g.F[:, 1]], g.V[g.F[:, 2]]
            ok = np.linalg.norm(np.cross(b - a, c - a), axis=1) > 1e-10
            pr = {'attributes': {'POSITION': acc(g.V, 5126, 'VEC3', 34962, True), 'COLOR_0': acc(g.C, 5126, 'VEC3', 34962)},
                  'indices': acc16(g.F[ok].reshape(-1)), 'material': mi[mt], 'mode': 4}
            meshes.append({'name': name, 'primitives': [pr]}); mesh_idx[name] = len(meshes) - 1; continue
        a, b, c = g.V[g.F[:, 0]], g.V[g.F[:, 1]], g.V[g.F[:, 2]]
        nr = np.cross(b - a, c - a); ln = np.linalg.norm(nr, axis=1); ok = ln > 1e-10
        P = np.stack([a, b, c], 1)[ok].reshape(-1, 3); Nn = np.repeat(nr[ok] / ln[ok][:, None], 3, 0)
        Cc = np.stack([g.C[g.F[:, 0]], g.C[g.F[:, 1]], g.C[g.F[:, 2]]], 1)[ok].reshape(-1, 3)
        idx = np.arange(len(P), dtype='<u4')
        pr = {'attributes': {'POSITION': acc(P, 5126, 'VEC3', 34962, True), 'NORMAL': acc(Nn, 5126, 'VEC3', 34962), 'COLOR_0': acc(Cc, 5126, 'VEC3', 34962)},
              'indices': acc(idx, 5125, 'SCALAR', 34963), 'material': mi[mt], 'mode': 4}
        meshes.append({'name': name, 'primitives': [pr]}); mesh_idx[name] = len(meshes) - 1
    node_of = {}
    def emit(n):
        i = len(nodes); d = {'name': n.name}; nodes.append(d); node_of[n.name] = i
        if n.mesh: d['mesh'] = mesh_idx[n.mesh]
        if np.any(n.t): d['translation'] = [round(float(x), 5) for x in n.t]
        q = n.quat()
        if np.abs(q - QI).max() > 1e-9: d['rotation'] = [round(float(x), 6) for x in q]
        if np.abs(n.s - 1).max() > 1e-9: d['scale'] = [round(float(x), 5) for x in n.s]
        ks = [emit(k) for k in n.kids]
        if ks: d['children'] = ks
        return i
    top = [emit(r) for r in roots]
    # animations
    byname = {}
    def walk(n): byname[n.name] = n; [walk(k) for k in n.kids]
    for r in roots: walk(r)
    T = np.linspace(0, LOOP, NKEY); tacc = acc(T, 5126, 'SCALAR', None, True)
    groups = {'flicker_s': ['flame_s_0%d' % i for i in (1, 2, 3)], 'flicker_m': ['flame_m_0%d' % i for i in (1, 2, 3)], 'flicker_l': ['flame_l_0%d' % i for i in (1, 2, 3)],
              'flicker_cluster': [k.name for r in roots if r.name.startswith('fire_') for k in r.kids]}
    anims = []
    rg = np.random.RandomState(99)
    for an, names in groups.items():
        chans = []; samps = []
        for nm in names:
            n = byname[nm]; _, S, Q = flicker_keys(n, rg)
            sa = acc(S, 5126, 'VEC3'); ra = acc(Q, 5126, 'VEC4')
            for path, a in (('scale', sa), ('rotation', ra)):
                samps.append({'input': tacc, 'output': a, 'interpolation': 'LINEAR'}); chans.append({'sampler': len(samps) - 1, 'target': {'node': node_of[nm], 'path': path}})
        anims.append({'name': an, 'samplers': samps, 'channels': chans})
    js = {'asset': {'version': '2.0', 'generator': 'build_fire.py'}, 'extensionsUsed': ['KHR_materials_unlit'], 'scene': 0, 'scenes': [{'nodes': top}], 'nodes': nodes,
          'meshes': meshes, 'materials': mats, 'accessors': accs, 'bufferViews': bvs, 'buffers': [{'byteLength': len(buf)}], 'animations': anims}
    j = json.dumps(js, separators=(',', ':')).encode()
    while len(j) % 4: j += b' '
    while len(buf) % 4: buf.append(0)
    return b'glTF' + struct.pack('<II', 2, 12 + 8 + len(j) + 8 + len(buf)) + struct.pack('<I', len(j)) + b'JSON' + j + struct.pack('<I', len(buf)) + b'BIN\0' + bytes(buf)

if __name__ == '__main__':
    glb = build_glb(make_world())
    out = os.path.join(GAME, 'assets'); os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'fire.glb'), 'wb').write(glb)
    open(os.path.join(out, 'fire.glb.b64.txt'), 'w').write(base64.b64encode(glb).decode())
    print('fire.glb %d bytes' % len(glb))
