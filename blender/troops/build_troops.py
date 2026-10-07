"""Builds assets/troops.glb(.b64.txt): 12 low poly soldiers/guards/SWAT/raiders on the SAME skeleton as facetex_0 in people.glb.
Pure python + numpy (no Blender needed): the skeleton nodes are copied verbatim from facetex_0 (uniformly scaled by S, as the
existing people are scaled by height), the meshes are generated in rest pose and skinned by distance-to-bone weights.
usage: python build_troops.py <game dir>      (reads assets/people.glb.b64.txt, writes assets/troops.glb and .b64.txt)"""
import sys, os, json, struct, base64, math, random
import numpy as np

GAME = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
S = 1.10                                  # uniform size: facetex_0 is 1.57 m, this gives ~1.76 m (existing people range 1.57 to 1.88 the same way)
PI = math.pi

# ------------------------------------------------------------------ read facetex_0
raw = base64.b64decode(open(os.path.join(GAME, 'assets', 'people.glb.b64.txt')).read())
jl = struct.unpack('<I', raw[12:16])[0]
SRC = json.loads(raw[20:20 + jl]); BIN = raw[20 + jl + 8:]
SN = SRC['nodes']
def acc(i):
    a = SRC['accessors'][i]; bv = SRC['bufferViews'][a['bufferView']]
    ct = {5126: '<f4', 5123: '<u2', 5121: 'u1', 5125: '<u4'}[a['componentType']]
    n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
    return np.frombuffer(BIN, dtype=ct, count=a['count'] * n, offset=bv.get('byteOffset', 0) + a.get('byteOffset', 0)).reshape(a['count'], n)
TOP = 19; MESHN = 18
TEMPLATE = [json.loads(json.dumps(SN[i])) for i in range(20)]          # nodes 0..17 bones, 18 mesh node, 19 character node
SKIN0 = SRC['skins'][0]; JOINTS = SKIN0['joints']                       # [17,16,9,...]
JNAMES = [SN[i]['name'] for i in JOINTS]
par = {}
for i in range(20):
    for c in TEMPLATE[i].get('children', []): par[c] = i
def lm(n, sc=1.0):
    t = np.array(n.get('translation', [0, 0, 0]), float) * sc; x, y, z, w = n.get('rotation', [0, 0, 0, 1]); s = n.get('scale', [1, 1, 1])
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    M = np.eye(4); M[:3, :3] = R * np.array(s); M[:3, 3] = t; return M
def glob(i, sc):
    return (glob(par[i], sc) if i in par else np.eye(4)) @ lm(TEMPLATE[i], sc)
JW = {n: glob(i, 1.0)[:3, 3] for n, i in zip(JNAMES, JOINTS)}      # joint positions, unit scale (facetex_0)
IBM = np.stack([np.linalg.inv(glob(i, S)).T for i in JOINTS]).astype('<f4')
# sanity: our IBM at scale 1 must equal facetex_0's own
chk = np.stack([np.linalg.inv(glob(i, 1.0)).T for i in JOINTS]); ref = acc(SKIN0['inverseBindMatrices']).reshape(18, 4, 4)
assert np.abs(chk - ref).max() < 2e-4, np.abs(chk - ref).max()

def V(*a): return np.array(a, float)
J = JW
SEG = {}                                  # bone -> (head, tail) for the weight distances
SEG['hips'] = (J['hips'], J['spine']); SEG['spine'] = (J['spine'], J['chest']); SEG['chest'] = (J['chest'], J['neck'])
SEG['neck'] = (J['neck'], J['head']); SEG['head'] = (J['head'], J['head'] + V(0, .22, 0)); SEG['root'] = (J['root'], J['hips'])
for s in 'LR':
    SEG['upper_arm.' + s] = (J['upper_arm.' + s], J['forearm.' + s]); SEG['forearm.' + s] = (J['forearm.' + s], J['hand.' + s])
    d = J['hand.' + s] - J['forearm.' + s]; d /= np.linalg.norm(d)
    SEG['hand.' + s] = (J['hand.' + s], J['hand.' + s] + d * .1)
    SEG['thigh.' + s] = (J['thigh.' + s], J['shin.' + s]); SEG['shin.' + s] = (J['shin.' + s], J['foot.' + s])
    SEG['foot.' + s] = (J['foot.' + s], J['foot.' + s] + V(0, -.045, .15))
BI = {n: k for k, n in enumerate(JNAMES)}

# ------------------------------------------------------------------ geometry helpers (unit scale, y up, +z front, character's right = -x)
def norm(v): return v / (np.linalg.norm(v) + 1e-12)
def frame(ax):
    ax = norm(ax); ref = V(0, 0, 1) if abs(ax[2]) < .9 else V(1, 0, 0)
    u = norm(np.cross(ax, ref)); v = np.cross(ax, u); return u, v
def orient(Vv, F, cen):
    Vv = np.asarray(Vv); F = np.asarray(F, int).copy()
    a, b, c = Vv[F[:, 0]], Vv[F[:, 1]], Vv[F[:, 2]]
    nrm = np.cross(b - a, c - a); fc = (a + b + c) / 3
    flip = (nrm * (fc - cen)).sum(1) < 0
    F[flip] = F[flip][:, [0, 2, 1]]
    area = np.linalg.norm(nrm, axis=1); return Vv, F[area > 1e-10]
def loft(rings, n=8, caps=(True, True), phase=PI / 8):
    """rings: list of (centre, ru, rv, u, v)"""
    Vs = []; F = []
    for c, ru, rv, u, v in rings:
        for k in range(n):
            a = phase + 2 * PI * k / n; Vs.append(np.asarray(c, float) + ru * math.cos(a) * np.asarray(u) + rv * math.sin(a) * np.asarray(v))
    R = len(rings)
    for i in range(R - 1):
        for k in range(n):
            a = i * n + k; b = i * n + (k + 1) % n; c2 = (i + 1) * n + k; d = (i + 1) * n + (k + 1) % n
            F += [(a, b, d), (a, d, c2)]
    Vs = np.array(Vs); F = np.array(F, int)
    # orient each quad away from the local ring centres
    out = []
    for idx, f in enumerate(F):
        i = int(f[0]) // n; cen = (np.asarray(rings[i][0], float) + np.asarray(rings[min(i + 1, R - 1)][0], float)) / 2
        a, b, c = Vs[f[0]], Vs[f[1]], Vs[f[2]]
        if np.dot(np.cross(b - a, c - a), (a + b + c) / 3 - cen) < 0: f = f[[0, 2, 1]]
        out.append(f)
    F = out
    for side, (i, nb) in enumerate(((0, 1), (R - 1, R - 2))):
        if not caps[side] or R < 2: continue
        ci = len(Vs); Vs = np.vstack([Vs, np.asarray(rings[i][0], float)])
        away = np.asarray(rings[i][0], float) - np.asarray(rings[nb][0], float)
        for k in range(n):
            f = np.array([i * n + k, i * n + (k + 1) % n, ci])
            a, b, c = Vs[f[0]], Vs[f[1]], Vs[f[2]]
            if np.dot(np.cross(b - a, c - a), away) < 0: f = f[[0, 2, 1]]
            F.append(f)
    return Vs, np.array(F, int)
def ell(c, r, nlon=10, nlat=6, th=(0, PI), ph=(0, 2 * PI), grow=0.0):
    c = np.asarray(c, float); r = np.asarray(r, float) + grow
    full = abs((ph[1] - ph[0]) - 2 * PI) < 1e-6; ncol = nlon if full else nlon + 1
    Vs = []
    for i in range(nlat + 1):
        t = th[0] + (th[1] - th[0]) * i / nlat
        for k in range(ncol):
            p = ph[0] + (ph[1] - ph[0]) * k / nlon
            Vs.append(c + r * V(math.sin(t) * math.sin(p), math.cos(t), math.sin(t) * math.cos(p)))
    F = []
    for i in range(nlat):
        for k in range(nlon):
            k2 = (k + 1) % ncol if full else k + 1
            a = i * ncol + k; b = i * ncol + k2; cc = (i + 1) * ncol + k; d = (i + 1) * ncol + k2
            F += [(a, b, d), (a, d, cc)]
    return orient(np.array(Vs), F, c)
def box(c, size, axes=None):
    c = np.asarray(c, float); sx, sy, sz = [s / 2 for s in size]
    u, v, w = (V(1, 0, 0), V(0, 1, 0), V(0, 0, 1)) if axes is None else axes
    Vs = np.array([c + (a * sx) * u + (b * sy) * v + (d * sz) * w for a in (-1, 1) for b in (-1, 1) for d in (-1, 1)])
    F = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    return orient(Vs, F, c)
def obox(p0, p1, wd, dp, ref=V(0, 0, 1)):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float); ax = norm(p1 - p0)
    u = norm(np.cross(ax, ref if abs(np.dot(ax, ref)) < .95 else V(1, 0, 0))); w = np.cross(u, ax)
    return box((p0 + p1) / 2, (wd, np.linalg.norm(p1 - p0), dp), (u, ax, w))
def tilted_box(c, size, ang_x=0.0, ang_z=0.0):
    ca, sa = math.cos(ang_x), math.sin(ang_x)
    v = V(0, ca, sa); w = V(0, -sa, ca); u = V(1, 0, 0)
    if ang_z: cz, sz = math.cos(ang_z), math.sin(ang_z); u = V(cz, sz, 0); v = np.cross(w, u)
    return box(c, size, (u, v, w))
def cyl(p0, p1, r, n=8, rv=None):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float); u, v = frame(p1 - p0)
    return loft([(p0, r, rv or r, u, v), (p1, r, rv or r, u, v)], n)
def merge(*gs):
    Vs = []; F = []; o = 0
    for v, f in gs:
        Vs.append(v); F.append(np.asarray(f) + o); o += len(v)
    return np.vstack(Vs), np.vstack(F)
UX, UZ = V(1, 0, 0), V(0, 0, 1)
def ring_y(y, cx, cz, rx, rz): return (V(cx, y, cz), rx, rz, UX, UZ)

# torso profile: (y, half width, half depth)
TT = [(.80, .160, .098), (.90, .168, .100), (.99, .152, .092), (1.10, .160, .098), (1.20, .182, .106), (1.27, .190, .100), (1.31, .120, .070), (1.34, .058, .055)]
def tprof(y):
    ys = [t[0] for t in TT]; return (np.interp(y, ys, [t[1] for t in TT]), np.interp(y, ys, [t[2] for t in TT]))
def torso(y0, y1, grow=0.0, growz=None, n=10, caps=(True, True)):
    ys = [y0] + [t[0] for t in TT if y0 < t[0] < y1] + [y1]; growz = grow if growz is None else growz
    rs = []
    for y in ys:
        hx, hz = tprof(y); rs.append(ring_y(y, 0, 0, hx + grow, hz + growz))
    return loft(rs, n, caps)
def tz(y, x, front=True):
    hx, hz = tprof(y); return (1 if front else -1) * hz * math.sqrt(max(0.0, 1 - (x / hx) ** 2))
def tb(y): return 'hips' if y < .944 else 'spine' if y < 1.117 else 'chest'
# arms: rings along shoulder -> elbow -> wrist
ARM_T = [0, .12, .25, .5, .75, 1.0]; ARM_R = [.060, .058, .054, .047, .043, .034]
def arm_pt(s, t):
    S0 = J['upper_arm.' + s]; E = J['forearm.' + s]; W = J['hand.' + s]
    return S0 + (E - S0) * (t / .5) if t <= .5 else E + (W - E) * ((t - .5) / .5)
def arm(s, t0, t1, grow=0.0, n=8, caps=(True, True)):
    ts = [t0] + [t for t in ARM_T if t0 < t < t1] + [t1]
    return loft([(arm_pt(s, t), np.interp(t, ARM_T, ARM_R) + grow, np.interp(t, ARM_T, ARM_R) + grow, UX, UZ) for t in ts], n, caps)
def hand(s, grow=0.0, fist=True):
    W = J['hand.' + s]; d = norm(W - J['forearm.' + s]); L = .105
    rs = [(W, .026 + grow, .040 + grow, UX, UZ), (W + d * L * .45, .030 + grow, .046 + grow, UX, UZ), (W + d * L, .026 + grow, .040 + grow, UX, UZ)]
    g = loft(rs, 8)
    th = box(W + d * L * .35 + V(-(1 if s == 'R' else -1) * 0 + (.028 if s == 'L' else -.028) * -1, 0, .035), (.018 + grow, .05, .02 + grow))   # thumb, inside and forward
    return merge(g, th)
# legs
LEG_Y = [.88, .65, .449, .30, .13, .09]; LEG_RX = [.093, .086, .064, .060, .049, .046]; LEG_RZ = [.098, .090, .066, .064, .052, .048]
def leg(s, y0, y1, grow=0.0, n=8, caps=(True, True)):
    sg = 1 if s == 'L' else -1
    ys = [y1] + [y for y in LEG_Y if y1 > y > y0] + [y0]
    rs = []
    for y in ys:
        x = sg * (.091 - .007 * (min(y, .818) - .818) / (.449 - .818) * 1.0) if y < .818 else sg * .091
        x = sg * np.interp(y, [.087, .449, .818, .9], [.084, .087, .091, .091])
        rs.append(ring_y(y, x, np.interp(y, [.087, .449, .818], [-.008, 0, 0]), np.interp(y, LEG_Y[::-1], LEG_RX[::-1]) + grow, np.interp(y, LEG_Y[::-1], LEG_RZ[::-1]) + grow))
    return loft(rs, n, caps)
def foot(s, grow=0.0, h=.045):
    sg = 1 if s == 'L' else -1; x = sg * .084
    spec = [(-.075, .044, .040), (.0, .052, .042), (.10, .052, .036), (.15, .042, .028), (.178, .024, .016)]
    return loft([(V(x, h, z), rx + grow, ry + grow * .5, UX, V(0, 1, 0)) for z, rx, ry in spec], 8)
def boot(s, top=.24, grow=0.0):
    sg = 1 if s == 'L' else -1; x = sg * .085
    shaft = loft([ring_y(.03, x, -.008, .060 + grow, .064 + grow), ring_y(top, x, -.008, .057 + grow, .062 + grow)], 8)
    return shaft, foot(s, grow)

# ------------------------------------------------------------------ weights
def dseg(P, a, b):
    ab = b - a; t = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1); return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)
def weights(P, spec):
    n = len(P)
    if spec[0] == 'b':
        Jn = np.zeros((n, 4), np.uint8); Jn[:, 0] = BI[spec[1]]; W = np.zeros((n, 4), np.float32); W[:, 0] = 1; return Jn, W
    names = spec[1]; D = np.stack([dseg(P, *SEG[b]) for b in names], 1); Wt = 1.0 / (D + .012) ** 2.6
    Wt /= Wt.sum(1, keepdims=True); order = np.argsort(-Wt, 1)[:, :4]
    Jn = np.zeros((n, 4), np.uint8); W = np.zeros((n, 4), np.float32)
    for r in range(n):
        for k in range(min(4, len(names))):
            j = order[r, k]
            if Wt[r, j] >= .02 or k == 0: Jn[r, k] = BI[names[j]]; W[r, k] = Wt[r, j]
        W[r] /= W[r].sum()
    return Jn, W
TORSO = ['hips', 'spine', 'chest', 'neck']
def ARM(s): return ['chest', 'upper_arm.' + s, 'forearm.' + s, 'hand.' + s]
def LEG(s): return ['hips', 'thigh.' + s, 'shin.' + s, 'foot.' + s]
NECKCH = ['chest', 'neck', 'head']

# ------------------------------------------------------------------ a character
def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4) for x in c]
class Char:
    def __init__(s, name): s.name = name; s.parts = []        # (matkey, V, F, spec)
    def add(s, hexcol, g, spec, rough=.82, metal=0.0):
        v, f = g; s.parts.append(((hexcol, rough, metal), v, f, spec))
    def mirror(s, hexcol, fn, specfn, **kw):
        for sd in 'LR': s.add(hexcol, fn(sd), specfn(sd), **kw)

HC = V(0, 1.485, .015); HR = V(.088, .110, .100)         # head centre / radii
def hsurf(x, y, grow=0.0):
    k = 1 - (x / (HR[0] + grow)) ** 2 - ((y - HC[1]) / (HR[1] + grow)) ** 2
    return HC[2] + (HR[2] + grow) * math.sqrt(max(k, 0))

def head_and_face(C, spec):
    sk = spec['skin']; face = spec.get('face', True)
    C.add(sk, ell(HC, HR, 12, 8), ('b', 'head'), .7)
    C.add(sk, merge(*[box((x, 1.48, .012), (.012, .04, .026)) for x in (-HR[0] - .002, HR[0] + .002)]), ('b', 'head'), .7)   # ears
    C.add(sk, cyl((0, 1.29, -.008), (0, 1.42, -.012), .048, 8), ('c', NECKCH), .7)
    if face:
        C.add(sk, box((0, 1.468, hsurf(0, 1.468) + .006), (.022, .036, .03)), ('b', 'head'), .7)                  # nose
        for x in (-.036, .036):
            C.add('#17130f', box((x, 1.502, hsurf(x, 1.502) - .001), (.022, .012, .012)), ('b', 'head'), .5)
            C.add(spec['hair'], box((x, 1.524, hsurf(x, 1.524) + .002), (.034, .007, .012)), ('b', 'head'))
        C.add('#6b3a30', box((0, 1.425, hsurf(0, 1.425) + .001), (.042, .007, .012)), ('b', 'head'), .6)
def eye_strip(C, spec):        # a balaclava or mask: skin strip with the eyes only
    sk = spec['skin']
    C.add(sk, box((0, 1.505, hsurf(0, 1.505, .008) + .002), (.125, .03, .014)), ('b', 'head'), .7)
    for x in (-.036, .036): C.add('#17130f', box((x, 1.504, hsurf(x, 1.504, .008) + .010), (.02, .012, .006)), ('b', 'head'), .5)
def hair_cap(C, col, back=.02, th1=PI * .40, grow=.006):
    C.add(col, ell(HC + V(0, .004, -back), HR, 12, 4, (0, th1), grow=grow), ('b', 'head'), .9)

def body(C, spec):
    """spec: skin hair shirt trouser boot glove sleeve(long/short) belt"""
    head_and_face(C, spec)
    sh, tr = spec['shirt'], spec['trouser']
    C.add(tr, torso(.80, .99, .004), ('c', TORSO[:3]))
    C.add(sh, torso(.99, 1.325, .004), ('c', TORSO))
    for s in 'LR':
        t1 = 1.0 if spec.get('sleeve', 'long') == 'long' else .36
        C.add(spec.get('sleeve_col', sh), arm(s, 0, t1, .004), ('c', ARM(s)))
        if t1 < 1: C.add(spec['skin'], arm(s, t1 - .01, 1.0, 0), ('c', ARM(s)), .7)
        C.add(spec['glove'] or spec['skin'], hand(s, .004 if spec['glove'] else 0), ('c', ARM(s)), .6 if spec['glove'] is None else .8)
        C.add(tr, leg(s, .115, .88, .004), ('c', LEG(s)))
        b1, b2 = boot(s, grow=.004)
        C.add(spec['boot'], b1, ('c', ['shin.' + s, 'foot.' + s])); C.add(spec['boot'], b2, ('b', 'foot.' + s))
        C.add(spec.get('sole', '#17140f'), box(((.084 if s == 'L' else -.084), .008, .045), (.098, .016, .26)), ('b', 'foot.' + s), .9)

def belt(C, col='#17140f', buckle='#9a9a94'):
    C.add(col, torso(.955, 1.0, .014), ('c', TORSO[:3]), .55)
    C.add(buckle, box((0, .977, tz(.977, 0) + .016), (.04, .036, .008)), ('b', 'spine'), .4, .7)

# ------------------------------------------------------------------ kinds
SKINS = ['#f1c9a5', '#d9a07a', '#b87a52', '#8d5a3b', '#5f3b27']
HAIRS = ['#1c1714', '#2e2119', '#4a3021', '#8c6a3f', '#b0a89a']
def guard(n):
    C = Char(f'trooper_guard_{n}'); navy = '#1b2a4a'
    spec = dict(skin=SKINS[[0, 2, 4][n]], hair=HAIRS[[1, 0, 0][n]], shirt='#27406e' if n != 1 else '#3a5a8e', trouser='#16213a', boot='#14110e', glove=None,
                sleeve='long' if n != 1 else 'short')
    body(C, spec); hair_cap(C, spec['hair'], .01, PI * .46)
    belt(C)
    C.add('#17140f', box((-.196, .885, 0), (.05, .15, .085)), ('b', 'hips'), .55)                      # holster, right hip
    C.add('#2b2d30', box((-.2, .975, -.012), (.04, .045, .07)), ('b', 'hips'), .4, .5)                  # pistol grip
    for x in (-.07, .07): C.add('#17140f', box((x, .955, tz(.955, x) + .018), (.05, .09, .035)), ('b', 'spine'), .55)   # pouches
    C.add('#17140f', box((.20, .94, .02), (.03, .1, .06)), ('b', 'hips'), .55)                          # baton ring
    for s in 'LR':
        sg = 1 if s == 'L' else -1
        C.add(navy, tilted_box((sg * .165, 1.292, 0), (.075, .016, .085), 0, -sg * .28), ('b', 'chest'), .8)   # epaulette
    C.add('#c9c9c2', box((.075, 1.19, tz(1.19, .075) + .006), (.04, .045, .008)), ('b', 'chest'), .4, .8)   # badge
    C.add('#f1f1ea', box((-.07, 1.19, tz(1.19, -.07) + .004), (.06, .02, .006)), ('b', 'chest'), .6)     # blank name tab
    C.add('#242a33', box((.0, 1.292, -.005), (.1, .026, .09)), ('c', NECKCH), .85)                           # collar
    C.add('#1a2a4c', box((.095, 1.245, tz(1.245, .095) + .02), (.035, .06, .025)), ('b', 'chest'), .5, .3)   # radio on the chest
    if n == 2:
        C.add('#d6e22a', torso(1.03, 1.30, .02), ('c', TORSO), .7)                                        # hi-vis vest
        for y0 in (1.085, 1.17): C.add('#d5d9dc', torso(y0, y0 + .028, .026), ('c', TORSO), .35, .3)       # reflective bands
        C.add('#d6e22a', box((0, 1.13, tz(1.13, 0, False) - .026), (.28, .24, .01)), ('b', 'chest'), .7)
    # peaked cap
    cz = HC[2]; cc = V(0, 0, cz)
    crown = loft([ring_y(1.523, 0, cz, .100, .111), ring_y(1.57, 0, cz, .103, .114), ring_y(1.604, 0, cz, .118, .126), ring_y(1.622, 0, cz, .114, .121)], 12, (False, True), 0)
    C.add(navy, crown, ('b', 'head'), .8)
    C.add('#0f0f10', tilted_box((0, 1.545, cz + .165), (.15, .008, .09), -.18), ('b', 'head'), .35, .1)    # visor
    C.add('#c8a23a', box((0, 1.585, cz + .118), (.034, .04, .008)), ('b', 'head'), .35, .7)               # blank badge plate
    C.add('#0f0f10', cyl((0, 1.526, cz), (0, 1.552, cz), .105, 12, .116), ('b', 'head'), .5)               # band
    return C

def soldier(n):
    C = Char(f'trooper_soldier_{n}'); od = ['#566037', '#4d5a35', '#5b6339'][n]; od2 = '#3f4a2b'
    spec = dict(skin=SKINS[[1, 3, 0][n]], hair=HAIRS[[2, 0, 3][n]], shirt=od, trouser=od, boot='#3b2d20', glove='#2f2a22', sleeve='long', face=True)
    body(C, spec)
    # helmet with net cover
    hc = V(0, 1.522, .010); hr = V(.114, .100, .124)
    C.add(od2, ell(hc, hr, 12, 6, (0, PI * .46)), ('b', 'head'), .95)
    C.add(od2, ell(hc, hr, 10, 3, (PI * .46, PI * .60), (PI * .55, PI * 1.45), grow=.002), ('b', 'head'), .95)       # nape skirt
    C.add('#1a1a16', loft([ring_y(1.528, 0, .010, .113, .123), ring_y(1.548, 0, .010, .112, .122)], 12, (False, False), 0), ('b', 'head'), .6)   # elastic band
    rr = random.Random(7 + n)
    for k in range(16):                       # scrim loops over the net
        th = rr.uniform(.15, 1.3); ph = rr.uniform(0, 2 * PI)
        p = hc + hr * V(math.sin(th) * math.sin(ph), math.cos(th), math.sin(th) * math.cos(ph))
        C.add(rr.choice(['#6e7545', '#2f3820', '#8a7a52']), box(p, (.03, .008, .016)), ('b', 'head'), .95)
    for sg in (-1, 1): C.add('#2f3820', obox((sg * .1, 1.50, .02), (sg * .05, 1.405, .075), .012, .008), ('b', 'head'), .9)   # chin strap
    C.add('#2f3820', box((0, 1.40, .088), (.05, .02, .02)), ('b', 'head'), .9)
    # chest rig
    C.add('#3d4030', torso(1.06, 1.275, .017, .02), ('c', TORSO), .9)
    for i, x in enumerate((-.075, 0, .075)): C.add('#2f3322', box((x, 1.14, tz(1.14, x) + .036), (.062, .1, .045)), ('b', 'spine'), .9)
    for x in (-.055, .055): C.add('#363a2a', box((x, 1.235, tz(1.235, x) + .034), (.07, .06, .04)), ('b', 'chest'), .9)
    C.add('#2a2d20', box((-.172, 1.16, 0), (.04, .1, .08)), ('b', 'spine'), .9)
    for sg in (-1, 1): C.add('#3d4030', obox((sg * .11, 1.325, 0), (sg * .105, 1.2, .0), .05, .13), ('b', 'chest'), .9)    # shoulder straps
    C.add('#2c2f22', torso(.95, 1.0, .013), ('c', TORSO[:3]), .8)                                       # belt
    # cargo pockets and knee pads
    for s in 'LR':
        sg = 1 if s == 'L' else -1
        C.add(od2, box((sg * .163, .70, .01), (.034, .13, .1)), ('b', 'thigh.' + s), .9)
        C.add('#26241f', box((sg * .087, .435, .066), (.1, .12, .045)), ('b', 'shin.' + s), .7)
        C.add('#1c1b17', box((sg * .087, .384, .082), (.09, .03, .02)), ('b', 'shin.' + s), .7)
        C.add('#2f2a22', cyl(arm_pt(s, .93), arm_pt(s, .99), .04, 8), ('c', ARM(s)), .8)                 # glove cuff
    C.add(od, box((0, 1.285, -.02), (.12, .035, .1)), ('c', NECKCH), .9)                                  # collar
    if n >= 1:
        C.add('#4a4630', box((0, 1.17, -.185), (.27, .3, .16)), ('b', 'chest'), .9)
        C.add('#3a3726', box((0, 1.27, -.185), (.26, .1, .17)), ('b', 'chest'), .9)
        for sg in (-1, 1): C.add('#3a3726', box((sg * .145, 1.08, -.185), (.04, .14, .12)), ('b', 'chest'), .9)
        for sg in (-1, 1): C.add('#3d4030', obox((sg * .1, 1.31, -.02), (sg * .1, 1.2, -.1), .05, .02), ('b', 'chest'), .9)
    if n == 2: C.add('#8a7f5a', cyl((-.15, 1.335, -.19), (.15, 1.335, -.19), .046, 8), ('b', 'chest'), .9)    # bedroll
    return C

def swat(n):
    C = Char(f'trooper_swat_{n}'); blk = ['#16181b', '#1d2024', '#14171a'][n]; gry = '#2d3136'
    spec = dict(skin=SKINS[[2, 0, 3][n]], hair=HAIRS[0], shirt=blk, trouser=blk, boot='#0e0f10', glove='#121315', sleeve='long', face=False, sole='#050505')
    body(C, spec)
    # balaclava
    C.add(blk, ell(HC, HR, 12, 8, grow=.008), ('b', 'head'), .95)
    C.add(blk, loft([ring_y(1.40, 0, -.01, .066, .066), ring_y(1.34, 0, -.012, .082, .082)], 10, (False, False)), ('c', NECKCH), .95)
    eye_strip(C, spec)
    # ballistic helmet
    hc = V(0, 1.52, .008); hr = V(.112, .094, .122)
    C.add(gry, ell(hc, hr, 12, 6, (0, PI * .46)), ('b', 'head'), .55, .3)
    C.add(gry, ell(hc, hr, 10, 3, (PI * .46, PI * .64), (PI * .52, PI * 1.48), grow=.002), ('b', 'head'), .55, .3)
    C.add('#0e0f10', box((0, 1.585, .128), (.05, .04, .03)), ('b', 'head'), .5, .4)                       # shroud
    C.add('#0e0f10', obox((-.108, 1.55, .03), (-.108, 1.55, -.06), .012, .03), ('b', 'head'), .5)          # side rail L
    C.add('#0e0f10', obox((.108, 1.55, .03), (.108, 1.55, -.06), .012, .03), ('b', 'head'), .5)
    if n == 1:                                 # raised visor
        C.add('#7fa3b8', ell(hc + V(0, .03, .01), hr + V(.012, .0, .024), 10, 3, (PI * .17, PI * .42), (-PI * .36, PI * .36)), ('b', 'head'), .25, .1)
        C.add('#0e0f10', ell(hc + V(0, .03, .01), hr + V(.012, .0, .024), 10, 1, (PI * .41, PI * .43), (-PI * .36, PI * .36), .003), ('b', 'head'), .5)
    else:                                      # goggles pushed up
        C.add('#0e0f10', loft([ring_y(1.563, 0, .008, .117, .127), ring_y(1.58, 0, .008, .118, .128)], 12, (False, False), 0), ('b', 'head'), .6)
        for x in (-.038, .038):
            C.add('#0e0f10', cyl((x, 1.585, .118), (x, 1.608, .15), .036, 8), ('b', 'head'), .5)
            C.add('#33465a', cyl((x, 1.5885, .1245), (x, 1.612, .157), .029, 8), ('b', 'head'), .2, .2)
    if n == 2:
        for sg in (-1, 1): C.add('#0e0f10', box((sg * .108, 1.49, .0), (.03, .07, .06)), ('b', 'head'), .5)  # headset cups
        C.add('#0e0f10', obox((.108, 1.49, .0), (.07, 1.44, .08), .008, .008), ('b', 'head'), .5)
    # plate carrier and pouches
    C.add(gry, torso(1.04, 1.285, .02, .026), ('c', TORSO), .75)
    C.add('#1a1c1f', box((0, 1.16, tz(1.16, 0) + .03), (.2, .22, .035)), ('b', 'chest'), .6)                 # front plate
    C.add('#1a1c1f', box((0, 1.16, tz(1.16, 0, False) - .03), (.2, .22, .035)), ('b', 'chest'), .6)          # back plate
    C.add('#c9ccce', box((.07, 1.235, tz(1.235, .07) + .056), (.06, .035, .006)), ('b', 'chest'), .7)         # blank patch panel, chest
    C.add('#c9ccce', box((0, 1.2, tz(1.2, 0, False) - .052), (.17, .06, .006)), ('b', 'chest'), .7)           # blank patch panel, back
    for x in (-.075, 0, .075): C.add('#202327', box((x, 1.075, tz(1.075, x) + .034), (.06, .09, .04)), ('b', 'spine'), .75)
    for x in (-.08, .08): C.add('#202327', box((x, 1.215, tz(1.215, x) + .045), (.06, .06, .035)), ('b', 'chest'), .75)
    C.add('#202327', box((-.19, 1.12, 0), (.04, .12, .09)), ('b', 'spine'), .75)
    for sg in (-1, 1): C.add(gry, box((sg * .182, 1.288, 0), (.07, .05, .1)), ('b', 'chest'), .75)           # shoulder pads
    C.add('#0e0f10', torso(.95, 1.0, .015), ('c', TORSO[:3]), .55)
    for s in 'LR':
        sg = 1 if s == 'L' else -1
        C.add('#202327', box((sg * .163, .74, .0), (.04, .17, .1)), ('b', 'thigh.' + s), .7)
        C.add('#202327', box((sg * .087, .435, .066), (.1, .12, .048)), ('b', 'shin.' + s), .5)
        C.add('#0e0f10', box((sg * .087, .38, .08), (.09, .03, .02)), ('b', 'shin.' + s), .5)
        C.add('#202327', box((sg * .205, 1.06, 0), (.03, .1, .08)), ('b', 'upper_arm.' + s), .7) if False else None
    C.add('#0e0f10', box((-.205, .855, .01), (.04, .14, .08)), ('b', 'thigh.R'), .6)                         # drop-leg holster
    return C

def raider(n):
    C = Char(f'trooper_raider_{n}')
    red, redd, gr, grd = '#7b2227', '#5a1a1e', '#6b6d70', '#4b4d50'
    top = [red, grd, gr][n]; sl = [red, red, gr][n]; pocket = [gr, red, red][n]
    trou = ['#5d5a47', '#4a4a3f', '#3f4440'][n]
    spec = dict(skin=SKINS[[4, 1, 2][n]], hair=HAIRS[[0, 2, 1][n]], shirt=top, sleeve_col=sl, trouser=trou, boot='#5a4228', glove=None if n != 1 else '#2b2b2b', sleeve='long', face=n in (0, 2),
                sole='#cdbb8f')
    body(C, spec)
    C.add(top, ell((0, 1.335, -.045), (.095, .055, .085), 10, 4, (0, PI * .75)), ('c', NECKCH), .9)         # hood, down
    C.add(pocket, box((0, 1.03, tz(1.03, 0) + .016), (.21, .1, .02)), ('b', 'spine'), .9)                 # front pocket
    C.add(redd if n != 1 else grd, torso(.97, 1.03, .012), ('c', TORSO[:3]), .9)                           # hem band
    C.add(top, cyl((-.0, 1.31, .05), (0, 1.25, .085), .012, 6), ('b', 'chest'), .9) if False else None
    for s in 'LR':
        sg = 1 if s == 'L' else -1
        C.add(trou, box((sg * .162, .70, .01), (.036, .14, .105)), ('b', 'thigh.' + s), .9)               # cargo pocket
        C.add(redd if n == 0 else '#2a2b2d', cyl(arm_pt(s, .95), arm_pt(s, 1.0), .037, 8), ('c', ARM(s)), .9)   # cuffs
    C.add('#2a2b2d', torso(.95, .99, .012), ('c', TORSO[:3]), .7)
    # headwear
    if n == 0: hair_cap(C, HAIRS[0], .01, PI * .42)
    if n == 2: hair_cap(C, HAIRS[1], .01, PI * .46)
    if n == 1:                                                                                             # balaclava + beanie
        C.add(grd, ell(HC, HR, 12, 8, grow=.008), ('b', 'head'), .95)
        eye_strip(C, spec)
        C.add(redd, ell(HC + V(0, .02, 0), HR + V(.01, .002, .01), 12, 6, (0, PI * .56), grow=.012), ('b', 'head'), .95)
        C.add('#3a1215', loft([ring_y(1.496, 0, HC[2], .106, .116), ring_y(1.532, 0, HC[2], .108, .118)], 12, (False, False), 0), ('b', 'head'), .95)
    else:                                                                                                  # bandana over nose and mouth
        bc = [None, None, redd][n] or ['#7b2227', None, '#7b2227'][n]
        bcol = '#8a2a2e' if n == 0 else '#2f3033'
        C.add(bcol, ell(HC, HR, 12, 4, (PI * .52, PI * .84), grow=.008), ('b', 'head'), .9)
        C.add(bcol, box((0, 1.455, hsurf(0, 1.455, .008) + .004), (.1, .04, .01)), ('b', 'head'), .9)
        C.add(bcol, box((0, 1.455, -.1), (.04, .06, .03)), ('b', 'head'), .9)                              # knot
        for sg in (-1, 1): C.add(bcol, box((sg * .02, 1.41, -.115), (.02, .06, .015)), ('b', 'head'), .9)
    if n == 2:                                                                                             # bandolier
        brown = '#4a3220'
        pts = [(-.16, 1.29), (-.10, 1.23), (-.03, 1.14), (.04, 1.05), (.11, .98), (.15, .945)]
        for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
            for front in (True, False):
                p0 = V(x0, y0, tz(y0, x0, front) + (.02 if front else -.02)); p1 = V(x1, y1, tz(y1, x1, front) + (.02 if front else -.02))
                C.add(brown, obox(p0, p1, .036, .014, V(0, 0, 1)), ('c', TORSO), .8)
        for (x0, y0), (x1, y1) in zip(pts[1:-1], pts[2:]):
            for f in (0.25, 0.75):
                x = x0 + (x1 - x0) * f; y = y0 + (y1 - y0) * f
                C.add('#b08a3a', box((x, y, tz(y, x) + .035), (.018, .028, .014)), ('b', tb(y)), .4, .7)
        C.add(brown, obox(V(-.16, 1.29, 0), V(-.10, 1.23, tz(1.23, -.10) + .02), .04, .02), ('b', 'chest'), .8)
        C.add(brown, obox(V(-.17, 1.29, -.0), V(-.12, 1.22, tz(1.22, -.12, False) - .02), .04, .02), ('b', 'chest'), .8)
    if n == 1:
        C.add('#2b2d2f', box((-.19, .88, .0), (.04, .12, .08)), ('b', 'hips'), .6)                         # work pouch
    return C

KINDS = [('guard', guard), ('soldier', soldier), ('swat', swat), ('raider', raider)]
CHARS = [fn(n) for _, fn in KINDS for n in range(3)]

# ------------------------------------------------------------------ write the glb
buf = bytearray(); BV = []; AC = []
def add_bv(data, target=None):
    while len(buf) % 4: buf.append(0)
    o = len(buf); buf.extend(data); bv = {'buffer': 0, 'byteOffset': o, 'byteLength': len(data)}
    if target: bv['target'] = target
    BV.append(bv); return len(BV) - 1
def add_ac(arr, ctype, typ, target=None, minmax=False):
    bvi = add_bv(arr.tobytes(), target); a = {'bufferView': bvi, 'componentType': ctype, 'count': int(len(arr)), 'type': typ}
    if minmax: a['min'] = [float(x) for x in arr.min(0)]; a['max'] = [float(x) for x in arr.max(0)]
    AC.append(a); return len(AC) - 1
nodes = []; meshes = []; materials = []; skins = []; anims = []; scene_nodes = []
ibm_acc = add_ac(IBM.reshape(18, 16), 5126, 'MAT4')
AC[ibm_acc]['count'] = 18
# idle clip, copied from facetex_0 and sharing its samplers' data across all twelve (translation scaled by S)
a0 = SRC['animations'][0]; samp_acc = {}
def clipacc(i, scale_t=False):
    key = (i, scale_t)
    if key in samp_acc: return samp_acc[key]
    d = acc(i).astype('<f4')
    if scale_t: d = d * np.float32(S)
    r = SRC['accessors'][i]; typ = r['type']; d2 = d.reshape(r['count'], -1)
    idx = add_ac(d2.reshape(-1) if typ == 'SCALAR' else d2, 5126, typ)
    if typ == 'SCALAR': AC[idx]['min'] = [float(d2.min())]; AC[idx]['max'] = [float(d2.max())]
    samp_acc[key] = idx; return idx
matcache = {}
def qw(W):
    q = np.round(W.astype(np.float64) * 65535).astype(np.int64); d = 65535 - q.sum(1); q[np.arange(len(q)), q.argmax(1)] += d; return q.astype('<u2')
tri_counts = {}
for ci, C in enumerate(CHARS):
    base = len(nodes)
    for i in range(18):
        nd = json.loads(json.dumps(TEMPLATE[i]))
        if 'translation' in nd: nd['translation'] = [x * S for x in nd['translation']]
        if 'children' in nd: nd['children'] = [c + base for c in nd['children']]
        nodes.append(nd)
    # group parts by material
    prims = {}
    for mk, v, f, spec in C.parts:
        prims.setdefault(mk, []).append((v, f, spec))
    plist = []; tris = 0
    for mk, items in prims.items():
        PV = []; PN = []; PJ = []; PW = []; PI_ = []
        for v, f, spec in items:
            Jn, W = weights(v, spec)
            a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]; nrm = np.cross(b - a, c - a); nrm /= (np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12)
            idx = f.reshape(-1); PV.append(v[idx]); PN.append(np.repeat(nrm, 3, 0)); PJ.append(Jn[idx]); PW.append(W[idx])
        PV = np.vstack(PV) * S; PN = np.vstack(PN); PJ = np.vstack(PJ); PW = np.vstack(PW)
        n = len(PV); tris += n // 3
        ind = np.arange(n, dtype='<u2' if n < 65535 else '<u4')
        hexcol, rough, metal = mk
        if (ci, mk) not in matcache:
            materials.append({'name': f'tp_{hexcol}', 'doubleSided': True, 'pbrMetallicRoughness': {'baseColorFactor': srgb(hexcol) + [1], 'metallicFactor': metal, 'roughnessFactor': rough}})
            matcache[(ci, mk)] = len(materials) - 1
        wacc = add_ac(qw(PW), 5123, 'VEC4', 34962); AC[wacc]['normalized'] = True
        plist.append({'attributes': {'POSITION': add_ac(PV.astype('<f4'), 5126, 'VEC3', 34962, True), 'NORMAL': add_ac(PN.astype('<f4'), 5126, 'VEC3', 34962),
                                     'JOINTS_0': add_ac(PJ.astype('u1'), 5121, 'VEC4', 34962), 'WEIGHTS_0': wacc},
                      'indices': add_ac(ind, 5123 if n < 65535 else 5125, 'SCALAR', 34963), 'material': matcache[(ci, mk)]})
    tri_counts[C.name] = tris
    meshes.append({'name': C.name + '_mesh', 'primitives': plist})
    mn = {'mesh': len(meshes) - 1, 'name': C.name + '_mesh', 'skin': len(skins)}
    nodes.append(mn)
    top = json.loads(json.dumps(TEMPLATE[19])); top['name'] = C.name; top['children'] = [base + 18, base + 17]
    top['extras'] = {'height': round(1.5738529526366623 * S, 3), 'hip_height': round(0.8184035353710644 * S, 3), 'kind': C.name.split('_')[1], 'variant': int(C.name[-1])}
    nodes.append(top); scene_nodes.append(len(nodes) - 1)
    skins.append({'inverseBindMatrices': ibm_acc, 'joints': [j + base for j in JOINTS], 'name': C.name})
    chans = []; sams = []
    for ch in a0['channels']:
        sm = a0['samplers'][ch['sampler']]; path = ch['target']['path']
        sams.append({'input': clipacc(sm['input']), 'output': clipacc(sm['output'], path == 'translation'), 'interpolation': sm.get('interpolation', 'LINEAR')})
        chans.append({'sampler': len(sams) - 1, 'target': {'node': ch['target']['node'] + base, 'path': path}})
    anims.append({'name': 'idle', 'channels': chans, 'samplers': sams})
while len(buf) % 4: buf.append(0)
gl = {'asset': {'version': '2.0', 'generator': 'Squall Cove troops builder (build_troops.py)'}, 'scene': 0, 'scenes': [{'name': 'Scene', 'nodes': scene_nodes}],
      'nodes': nodes, 'meshes': meshes, 'materials': materials, 'skins': skins, 'animations': anims, 'accessors': AC, 'bufferViews': BV, 'buffers': [{'byteLength': len(buf)}]}
js = json.dumps(gl, separators=(',', ':')).encode()
while len(js) % 4: js += b' '
out = b'glTF' + struct.pack('<II', 2, 12 + 8 + len(js) + 8 + len(buf)) + struct.pack('<I', len(js)) + b'JSON' + js + struct.pack('<I', len(buf)) + b'BIN\0' + bytes(buf)
open(os.path.join(GAME, 'assets', 'troops.glb'), 'wb').write(out)
open(os.path.join(GAME, 'assets', 'troops.glb.b64.txt'), 'w').write(base64.b64encode(out).decode())
print('glb bytes', len(out), 'b64', len(base64.b64encode(out)))
for k, v in tri_counts.items(): print(k, v)
