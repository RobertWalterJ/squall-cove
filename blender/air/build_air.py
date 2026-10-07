"""Builds assets/air.glb(.b64.txt): griffon, gunship, parachute, emplacement_mg/aa/mortar, shell_heavy, crate_drop.
Pure python + numpy. No skins, flat shaded (un-indexed, face normals), plain colour materials (air_#hex), no textures/UVs/text.
Metres, +Z forward, +Y up, model's left = +X.   usage: python build_air.py [game dir]"""
import sys, os, json, struct, base64, math
import numpy as np

GAME = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PI = math.pi
def V(*a): return np.array(a, float)
UX, UY, UZ = V(1, 0, 0), V(0, 1, 0), V(0, 0, 1)
def norm(v): return v / (np.linalg.norm(v) + 1e-12)
def rotx(a): c, s = math.cos(a), math.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
def roty(a): c, s = math.cos(a), math.sin(a); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
def rotz(a): c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

# ------------------------------------------------------------------ geometry (V, F) helpers
def orient(Vv, F, cen):
    Vv = np.asarray(Vv, float); F = np.asarray(F, int).copy()
    a, b, c = Vv[F[:, 0]], Vv[F[:, 1]], Vv[F[:, 2]]
    flip = (np.cross(b - a, c - a) * ((a + b + c) / 3 - np.asarray(cen, float))).sum(1) < 0
    F[flip] = F[flip][:, [0, 2, 1]]
    return Vv, F
def frame(ax):
    ax = norm(ax); ref = UZ if abs(ax[2]) < .9 else UX
    u = norm(np.cross(ax, ref)); return u, np.cross(ax, u)
def loft(rings, n=8, caps=(True, True), phase=PI / n if False else 0.3927):
    """rings: list of (centre, ru, rv, u, v)"""
    Vs = []; F = []
    for c, ru, rv, u, v in rings:
        for k in range(n):
            a = phase + 2 * PI * k / n
            Vs.append(np.asarray(c, float) + ru * math.cos(a) * np.asarray(u) + rv * math.sin(a) * np.asarray(v))
    Vs = np.array(Vs); R = len(rings); out = []
    for i in range(R - 1):
        cen = (np.asarray(rings[i][0], float) + np.asarray(rings[i + 1][0], float)) / 2
        for k in range(n):
            a = i * n + k; b = i * n + (k + 1) % n; c2 = (i + 1) * n + k; d = (i + 1) * n + (k + 1) % n
            for f in ((a, b, d), (a, d, c2)):
                f = np.array(f); p, q, r = Vs[f[0]], Vs[f[1]], Vs[f[2]]
                if np.dot(np.cross(q - p, r - p), (p + q + r) / 3 - cen) < 0: f = f[[0, 2, 1]]
                out.append(f)
    for side, (i, nb) in enumerate(((0, 1), (R - 1, R - 2))):
        if not caps[side] or R < 2: continue
        ci = len(Vs); Vs = np.vstack([Vs, np.asarray(rings[i][0], float)])
        away = np.asarray(rings[i][0], float) - np.asarray(rings[nb][0], float)
        for k in range(n):
            f = np.array([i * n + k, i * n + (k + 1) % n, ci]); p, q, r = Vs[f[0]], Vs[f[1]], Vs[f[2]]
            if np.dot(np.cross(q - p, r - p), away) < 0: f = f[[0, 2, 1]]
            out.append(f)
    return Vs, np.array(out, int)
def cyl(p0, p1, r0, r1=None, n=8, caps=(True, True)):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float); u, v = frame(p1 - p0)
    r1 = r0 if r1 is None else r1
    return loft([(p0, r0, r0, u, v), (p1, r1, r1, u, v)], n, caps)
def zloft(rings, n=12, caps=(True, True)):
    """rings: (z, cx, cy, rx, ry) along z"""
    return loft([(V(cx, cy, z), rx, ry, UX, UY) for z, cx, cy, rx, ry in rings], n, caps)
def ell(c, r, n=10, nl=6):
    c = np.asarray(c, float); rs = []
    for i in range(nl + 1):
        t = PI * i / nl
        rs.append((c + V(0, r[1] * math.cos(t), 0), max(r[0] * math.sin(t), 1e-4), max(r[2] * math.sin(t), 1e-4), UX, UZ))
    return loft(rs, n, (False, False))
def box(c, size, R=None):
    c = np.asarray(c, float); sx, sy, sz = [s / 2 for s in size]
    P = np.array([V(a * sx, b * sy, d * sz) for a in (-1, 1) for b in (-1, 1) for d in (-1, 1)])
    if R is not None: P = P @ np.asarray(R).T
    Vs = P + c
    F = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    return orient(Vs, F, c)
def hexa(P8):
    """P8 indexed 4*a+2*b+d (like box corners)"""
    P8 = np.array(P8, float); c = P8.mean(0)
    F = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    return orient(P8, F, c)
def prism(poly, axis, a0, a1):
    """convex polygon in the plane perpendicular to `axis` (0=x,1=y,2=z); poly = list of (p,q) with p,q the other two axes in order; extruded a0..a1"""
    o = {0: (2, 1), 1: (0, 2), 2: (0, 1)}[axis]; n = len(poly); Vs = []   # axis 0: poly is (z, y); axis 1: (x, z); axis 2: (x, y)
    for av in (a0, a1):
        for p, q in poly:
            v = [0, 0, 0]; v[o[0]] = p; v[o[1]] = q; v[axis] = av; Vs.append(v)
    Vs = np.array(Vs, float); F = []
    for k in range(n):
        k2 = (k + 1) % n; F += [(k, k2, n + k2), (k, n + k2, n + k)]
    for k in range(1, n - 1): F += [(0, k, k + 1), (n, n + k, n + k + 1)]
    return orient(Vs, F, Vs.mean(0))
def merge(*gs):
    Vs = []; F = []; o = 0
    for v, f in gs:
        Vs.append(np.asarray(v, float)); F.append(np.asarray(f, int) + o); o += len(v)
    return np.vstack(Vs), np.vstack(F)
def xf(g, R=None, t=(0, 0, 0)):
    v, f = g; v = np.asarray(v, float)
    if R is not None: v = v @ np.asarray(R).T
    return v + np.asarray(t, float), f
def mir(g):   # mirror in x
    v, f = g; v = np.asarray(v, float) * V(-1, 1, 1); return v, np.asarray(f)[:, [0, 2, 1]]
def tilt(g, p, ang):   # rotate g around x axis through point p
    return xf(xf(g, None, -np.asarray(p)), rotx(ang), p)

# ------------------------------------------------------------------ scene graph + glb writer
MATS = {}
def mat(hexcol, rough=.8, metal=.0, dbl=False):
    k = (hexcol, rough, metal, dbl); MATS.setdefault(k, len(MATS)); return k
class Node:
    def __init__(self, name, t=(0, 0, 0)):
        self.name = name; self.t = tuple(float(x) for x in t); self.parts = []; self.kids = []
    def add(self, g, m): self.parts.append((g, m)); return self
    def child(self, name, t=(0, 0, 0)):
        n = Node(name, t); self.kids.append(n); return n

def build_glb(roots):
    buf = bytearray(); bvs = []; accs = []; meshes = []; nodes = []; mats = []
    mk = {}
    def material(k):
        if k in mk: return mk[k]
        h, ro, me, dbl = k; c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c]
        d = {'name': 'air_' + h, 'pbrMetallicRoughness': {'baseColorFactor': c + [1.0], 'metallicFactor': me, 'roughnessFactor': ro}}
        if dbl: d['doubleSided'] = True
        mats.append(d); mk[k] = len(mats) - 1; return mk[k]
    def addbv(b, target):
        while len(buf) % 4: buf.append(0)
        bvs.append({'buffer': 0, 'byteOffset': len(buf), 'byteLength': len(b), 'target': target}); buf.extend(b); return len(bvs) - 1
    def mesh_for(node):
        bymat = {}
        for (v, f), m in node.parts:
            v = np.asarray(v, float); f = np.asarray(f, int)
            a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]; nr = np.cross(b - a, c - a); ar = np.linalg.norm(nr, axis=1); ok = ar > 1e-9
            a, b, c, nr, ar = a[ok], b[ok], c[ok], nr[ok], ar[ok]
            nn = nr / ar[:, None]
            P = np.stack([a, b, c], 1).reshape(-1, 3); Nn = np.repeat(nn, 3, 0)
            bymat.setdefault(m, []).append((P, Nn))
        prims = []
        for m, lst in bymat.items():
            P = np.vstack([p for p, _ in lst]).astype('<f4'); Nn = np.vstack([n for _, n in lst]).astype('<f4')
            idx = np.arange(len(P), dtype='<u4')
            ap = len(accs); accs.append({'bufferView': addbv(P.tobytes(), 34962), 'componentType': 5126, 'count': len(P), 'type': 'VEC3', 'min': P.min(0).tolist(), 'max': P.max(0).tolist()})
            an = len(accs); accs.append({'bufferView': addbv(Nn.tobytes(), 34962), 'componentType': 5126, 'count': len(P), 'type': 'VEC3'})
            ai = len(accs); accs.append({'bufferView': addbv(idx.tobytes(), 34963), 'componentType': 5125, 'count': len(P), 'type': 'SCALAR'})
            prims.append({'attributes': {'POSITION': ap, 'NORMAL': an}, 'indices': ai, 'material': material(m), 'mode': 4})
        meshes.append({'name': node.name + '_mesh', 'primitives': prims}); return len(meshes) - 1
    def emit(node):
        i = len(nodes); d = {'name': node.name}; nodes.append(d)
        if any(node.t): d['translation'] = list(node.t)
        if node.parts: d['mesh'] = mesh_for(node)
        ks = [emit(k) for k in node.kids]
        if ks: d['children'] = ks
        return i
    top = [emit(r) for r in roots]
    js = {'asset': {'version': '2.0', 'generator': 'build_air.py'}, 'scene': 0, 'scenes': [{'nodes': top}], 'nodes': nodes, 'meshes': meshes,
          'materials': mats, 'accessors': accs, 'bufferViews': bvs, 'buffers': [{'byteLength': len(buf)}]}
    j = json.dumps(js, separators=(',', ':')).encode()
    while len(j) % 4: j += b' '
    while len(buf) % 4: buf.append(0)
    return b'glTF' + struct.pack('<II', 2, 12 + 8 + len(j) + 8 + len(buf)) + struct.pack('<I', len(j)) + b'JSON' + j + struct.pack('<I', len(buf)) + b'BIN\0' + bytes(buf)

# ------------------------------------------------------------------ colours
OLIVE = mat('#4b5232', .85); OLIVE_D = mat('#394029', .85); DGREY = mat('#35383b', .7); BLACK = mat('#151617', .8)
GLASS = mat('#1c2a34', .15, .3); METAL = mat('#5c6165', .5, .6); DARK = mat('#0d0e0f', 1.0); TIP = mat('#d8b73a', .7)
LGREY = mat('#7a8085', .7); GREY = mat('#62676c', .7); GREY_D = mat('#4a4e52', .75)
RED = mat('#c0281f', .8, 0, True); WHITE = mat('#ece8df', .8, 0, True); LINE = mat('#d9d4c4', .9)
WOOD = mat('#8b6b3f', .9); WOOD_D = mat('#4d3a20', .9)
BAG = mat('#8d8160', .95); BAG2 = mat('#7a7050', .95); EARTH = mat('#6e6248', 1.0); CONC = mat('#8e8f8b', .95)
BRASS = mat('#b08a3a', .4, .7); COPPER = mat('#a0623a', .4, .7); SHELL = mat('#4c5040', .6, .3); AMMO = mat('#3f4630', .7)

# ------------------------------------------------------------------ 1 griffon (CH-146 / Bell 412 style), ~11 m
def griffon():
    r = Node('griffon')
    hull = zloft([(3.75, 0, 1.2, .30, .32), (3.45, 0, 1.35, .62, .62), (2.9, 0, 1.5, .92, .85), (2.0, 0, 1.6, 1.0, .95),
                  (-1.7, 0, 1.6, 1.0, .95), (-2.3, 0, 1.8, .7, .7), (-2.8, 0, 2.0, .4, .42)], 12)
    r.add(hull, OLIVE)
    r.add(cyl(V(0, 2.02, -2.5), V(0, 2.1, -5.55), .38, .15, 8), OLIVE)                         # tail boom
    r.add(prism([(-4.5, 2.05), (-5.8, 2.12), (-5.72, 3.7), (-5.25, 3.7)], 0, -.07, .07), OLIVE)  # fin
    r.add(prism([(-4.9, 2.0), (-5.8, 2.0), (-5.55, 1.45)], 0, -.06, .06), OLIVE_D)               # lower fin
    r.add(box((0, 2.08, -4.75), (3.2, .06, .65)), OLIVE_D)                                       # stabiliser
    r.add(ell((0, 2.62, -.55), (.78, .5, 1.5), 10, 5), OLIVE)                                    # engine deck
    r.add(box((.42, 2.85, .85), (.28, .3, .5)), DGREY); r.add(box((-.42, 2.85, .85), (.28, .3, .5)), DGREY)   # intakes
    r.add(cyl(V(0, 2.8, -1.7), V(0, 2.95, -2.35), .15, .13, 8), BLACK)                           # exhaust
    r.add(cyl(V(0, 2.5, .3), V(0, 3.32, .3), .13, .1, 8), METAL)                                 # mast
    r.add(ell((0, 1.98, 2.62), (.86, .56, .78), 10, 5), GLASS)                                   # windscreen bubble
    r.add(box((.975, 1.9, 1.35), (.05, .55, .95)), GLASS); r.add(box((.975, 1.9, -.15), (.05, .55, .8)), GLASS)   # left windows
    r.add(box((.975, 1.35, 1.0), (.04, .25, .35)), DGREY)
    # right side: open sliding door
    r.add(box((-.985, 1.62, .6), (.05, 1.15, 1.5)), DARK)                                         # opening
    r.add(box((-1.04, 1.64, -1.0), (.06, 1.2, 1.5)), OLIVE); r.add(box((-1.075, 1.95, -1.0), (.03, .42, .8)), GLASS)   # door slid back
    r.add(box((-1.0, 2.26, -.55), (.12, .06, 3.4)), DGREY); r.add(box((-1.0, 1.02, -.55), (.12, .06, 3.4)), DGREY)   # door rails
    r.add(box((-.45, 1.1, .95), (.4, .5, .45)), DGREY); r.add(box((.0, 1.1, .35), (.3, .5, .3)), DGREY)             # seats inside
    r.add(cyl(V(-.7, 1.0, .75), V(-.7, 1.22, .75), .045, .04, 6), METAL)                          # pintle post
    # skids
    for s in (1, -1):
        r.add(cyl(V(s * 1.15, .07, -2.3), V(s * 1.15, .07, 2.5), .06, .06, 8), DGREY)
        r.add(cyl(V(s * 1.15, .07, 2.5), V(s * 1.15, .38, 3.0), .06, .05, 8), DGREY)
        for z in (1.4, -1.1):
            r.add(cyl(V(s * 1.15, .07, z), V(s * .82, .95, z), .045, .045, 6), DGREY)
    r.add(cyl(V(-1.15, .7, 1.4), V(1.15, .7, 1.4), .04, .04, 6), DGREY); r.add(cyl(V(-1.15, .7, -1.1), V(1.15, .7, -1.1), .04, .04, 6), DGREY)
    r.add(cyl(V(.0, 1.0, 3.5), V(.0, 1.25, 3.62), .015, .015, 4), METAL)
    r.add(cyl(V(.25, 2.95, -1.9), V(.25, 3.55, -2.05), .014, .01, 4), METAL)
    # main rotor
    mr = r.child('griffon_mainrotor', (0, 3.45, .3))
    mr.add(cyl(V(0, -.18, 0), V(0, .12, 0), .24, .2, 8), METAL)
    for s in (1, -1):
        mr.add(box((s * 3.85, 0, 0), (6.9, .045, .36)), DGREY); mr.add(box((s * 3.4, 0, 0), (.9, .05, .38)), DARK)
        mr.add(box((s * 7.25, 0, 0), (.55, .05, .36)), TIP); mr.add(box((s * .6, -.04, 0), (.5, .1, .22)), METAL)
    # tail rotor
    tr = r.child('griffon_tailrotor', (.2, 3.0, -5.55))
    tr.add(cyl(V(-.05, 0, 0), V(.22, 0, 0), .09, .07, 8), METAL)
    for s in (1, -1):
        tr.add(box((.12, s * .56, 0), (.03, 1.0, .2)), DGREY); tr.add(box((.12, s * 1.0, 0), (.03, .16, .2)), TIP)
    # door gun
    g = r.child('griffon_gun', (-.7, 1.22, .75))
    g.add(box((-.02, 0, 0), (.16, .14, .34)), BLACK)
    g.add(cyl(V(-.12, 0, 0), V(-1.15, 0, .0), .03, .03, 8), BLACK); g.add(cyl(V(-.12, 0, 0), V(-.55, 0, 0), .05, .05, 8), DGREY)
    g.add(cyl(V(-1.15, 0, 0), V(-1.27, 0, 0), .045, .045, 8), DGREY)
    g.add(box((.06, .02, -.2), (.1, .1, .2)), BLACK); g.add(box((.12, -.02, .0), (.12, .18, .22)), AMMO)
    g.add(cyl(V(.05, .0, -.28), V(.05, .1, -.34), .02, .02, 6), METAL)
    return r

# ------------------------------------------------------------------ 2 gunship (AC-130 style), ~30 m long, 40 m span
def gunship():
    r = Node('gunship')
    fus = zloft([(15.2, 0, -.2, .12, .12), (14.6, 0, -.2, .5, .5), (13.0, 0, -.05, 1.3, 1.3), (10.0, 0, 0, 1.8, 1.9), (5.0, 0, 0, 1.95, 2.0),
                 (-5.0, 0, 0, 1.95, 2.0), (-9.0, 0, .3, 1.7, 1.75), (-12.5, 0, 1.0, 1.15, 1.15), (-14.8, 0, 1.7, .55, .55)], 14)
    r.add(fus, GREY)
    r.add(cyl(V(0, -.2, 15.1), V(0, -.2, 16.0), .02, .02, 4), METAL)                                    # pitot
    r.add(ell((0, 1.05, 12.2), (1.05, .6, 1.2), 10, 5), GLASS)                                          # cockpit glass
    r.add(box((0, -.9, 14.3), (.7, .35, .9)), GREY_D)                                                    # chin
    r.add(ell((-.8, -1.95, 10.0), (.35, .35, .35), 8, 4), DARK)                                          # sensor ball
    for z in (3.0, -6.5):
        r.add(box((0, 2.2, z), (.06, .8, 1.1)), GREY_D)                                                  # dorsal antennas
    r.add(box((0, 2.55, -1.0), (.5, .3, 1.8)), GREY_D)
    # wings
    for s in (1, -1):
        P = []
        for a in (0, 1):
            for b in (0, 1):
                for d in (0, 1):
                    x = 1.2 + a * 18.8; zt = (-3.8 + a * 1.6, 2.8 - a * 2.2)[d]; y0, y1 = (1.7 + a * .35, 2.7 - a * .25)[b], 0
                    yy = y0 if b == 0 else 2.7 - a * .25
                    P.append((s * x, yy, zt))
        r.add(hexa(P), GREY)
        for x, i in ((5.5, 1 if s > 0 else 2), (12.0, 0 if s > 0 else 3)):
            xx = s * x
            r.add(zloft([(4.6, xx, 1.7, .4, .42), (4.0, xx, 1.7, .62, .62), (0.0, xx, 1.7, .68, .66), (-2.0, xx, 1.7, .5, .5), (-3.2, xx, 1.7, .22, .22)], 10), GREY_D)
            r.add(zloft([(5.15, xx, 1.7, .01, .01), (4.9, xx, 1.7, .16, .16), (4.55, xx, 1.7, .36, .36)], 10), DGREY)
            r.add(box((xx, .98, 1.5), (.9, .12, 1.4)), GREY_D)
            p = r.child('gunship_prop_%d' % i, (xx, 1.7, 5.0))
            for k in range(4):
                R = rotz(k * PI / 2)
                p.add(xf(box((0, 1.2, 0), (.24, 1.8, .05), roty(.45)), R), DGREY)
                p.add(xf(box((0, 1.98, 0), (.25, .25, .06), roty(.45)), R), TIP)
            p.add(cyl(V(0, 0, -.35), V(0, 0, .1), .3, .3, 10), DGREY)
    # tail
    r.add(prism([(-7.5, 1.7), (-14.8, 2.0), (-14.4, 6.8), (-11.6, 6.8)], 0, -.18, .18), GREY)
    r.add(box((0, 6.95, -13.2), (14.0, .3, 2.6)), GREY)
    r.add(box((0, 2.4, -5.0), (.2, 1.0, 1.6)), GREY_D)
    # sponsons + landing gear
    for s in (1, -1):
        r.add(ell((s * 1.95, -1.3, -1.5), (.55, .95, 3.6), 10, 6), GREY)
        for z in (-.2, -2.8):
            r.add(xf(cyl(V(-.25, 0, 0), V(.25, 0, 0), .62, .62, 10), None, (s * 2.1, -1.95, z)), BLACK)
            r.add(xf(cyl(V(-.1, 0, 0), V(.3, 0, 0), .28, .28, 8), None, (s * 2.1, -1.95, z)), METAL)
    # guns on the left side (+x); barrels along +x from the muzzle base
    for z, name in ((8.0, 'gunship_minigun'), (4.3, 'gunship_cannon'), (-2.0, 'gunship_howitzer')):
        r.add(box((1.83, -.35, z), (.3, .85, 1.1)), GREY_D); r.add(box((1.95, -.35, z), (.1, .6, .8)), DARK)
    mg = r.child('gunship_minigun', (1.92, -.35, 8.0))
    mg.add(box((.2, 0, 0), (.4, .34, .34)), BLACK)
    for k in range(6):
        a = k * PI / 3; mg.add(cyl(V(.4, .1 * math.cos(a), .1 * math.sin(a)), V(1.9, .1 * math.cos(a), .1 * math.sin(a)), .028, .028, 6), DGREY)
    for x in (.7, 1.25, 1.9): mg.add(cyl(V(x, 0, 0), V(x + .07, 0, 0), .15, .15, 8), METAL)
    cn = r.child('gunship_cannon', (1.92, -.35, 4.3))
    cn.add(box((.25, 0, 0), (.5, .4, .4)), BLACK)
    cn.add(cyl(V(.4, 0, 0), V(1.1, 0, 0), .13, .13, 8), DGREY); cn.add(cyl(V(1.0, 0, 0), V(2.5, 0, 0), .075, .075, 8), BLACK)
    cn.add(cyl(V(2.5, 0, 0), V(2.65, 0, 0), .11, .11, 8), DGREY)
    hw = r.child('gunship_howitzer', (1.92, -.35, -2.0))
    hw.add(box((.25, 0, 0), (.5, .7, .7)), BLACK)
    hw.add(cyl(V(.45, 0, 0), V(1.5, 0, 0), .27, .24, 10), DGREY); hw.add(cyl(V(1.5, 0, 0), V(2.7, 0, 0), .2, .17, 10), DGREY)
    hw.add(cyl(V(2.7, 0, 0), V(3.05, 0, 0), .26, .26, 10), METAL)
    return r

# ------------------------------------------------------------------ parachute canopy
def canopy(radius, height, centre_y, ng, rimdrop=.12):
    """dome of ng gores alternating red/white. returns (red, white, rim points)"""
    cen = V(0, centre_y, 0); tmax = PI * .56; NL = 6; reds = []; whites = []; rim = []
    for g in range(ng):
        p0 = 2 * PI * g / ng; p1 = 2 * PI * (g + 1) / ng; pm = (p0 + p1) / 2
        cols = [(p0, 1.0), (pm, 1.05), (p1, 1.0)]
        Vs = []
        for i in range(NL + 1):
            t = tmax * i / NL
            for ph, bulge in cols:
                Vs.append(cen + V(radius * math.sin(t) * math.sin(ph) * bulge, height * math.cos(t), radius * math.sin(t) * math.cos(ph) * bulge))
        F = []
        for i in range(NL):
            for k in range(2):
                a = i * 3 + k; b = a + 1; c = a + 3; d = a + 4; F += [(a, b, d), (a, d, c)]
        g_ = orient(np.array(Vs), F, cen - V(0, .4 * height, 0))
        (reds if g % 2 == 0 else whites).append(g_)
        rim.append(np.array(Vs[NL * 3]))
    return merge(*reds), merge(*whites), rim
def lines_to(rim, pt, r=.012):
    return merge(*[cyl(p, pt, r, r, 3) for p in rim])

def parachute():
    r = Node('parachute')
    red, wh, rim = canopy(3.0, 2.3, 6.1, 12)
    r.add(red, RED); r.add(wh, WHITE)
    r.add(lines_to(rim, V(0, 0, 0)), LINE)
    r.add(box((0, -.04, 0), (.28, .22, .18)), DGREY)               # harness block at the join point
    return r

def crate_drop():
    r = Node('crate_drop')
    r.add(box((0, .3, 0), (.8, .6, .8)), WOOD)
    for x in (-.3, .3): r.add(box((x, .3, 0), (.06, .62, .82)), WOOD_D)
    for z in (-.3, .3): r.add(box((0, .3, z), (.82, .62, .06)), WOOD_D)
    r.add(box((0, .62, 0), (.84, .04, .84)), WOOD_D)
    r.add(box((.25, .2, .41), (.2, .22, .03)), AMMO)
    ch = r.child('crate_drop_chute', (0, 0, 0))
    red, wh, rim = canopy(1.3, 1.0, 3.6, 8)
    ch.add(red, RED); ch.add(wh, WHITE)
    hp = V(0, 1.6, 0); ch.add(lines_to(rim, hp, .01), LINE)
    for x in (-.4, .4):
        for z in (-.4, .4): ch.add(cyl(hp, V(x, .62, z), .01, .01, 3), LINE)
    return r

# ------------------------------------------------------------------ shell
def shell_geo(L=.5, R=.052):
    s = L / .5; Rb = R
    parts = []
    z = lambda a: a * s
    parts.append((cyl(V(0, 0, z(-.25)), V(0, 0, z(-.06)), Rb, Rb, 10), BRASS))
    parts.append((cyl(V(0, 0, z(-.265)), V(0, 0, z(-.25)), Rb * 1.12, Rb * 1.12, 10), BRASS))
    parts.append((cyl(V(0, 0, z(-.06)), V(0, 0, z(.07)), Rb, Rb, 10), SHELL))
    parts.append((cyl(V(0, 0, z(-.01)), V(0, 0, z(.03)), Rb * 1.05, Rb * 1.05, 10), COPPER))
    og = [(.07, 1.0), (.115, .93), (.16, .76), (.2, .52), (.232, .26), (.25, .08)]
    parts.append((loft([(V(0, 0, z(a)), Rb * f, Rb * f, UX, UY) for a, f in og], 10, (False, True)), SHELL))
    parts.append((cyl(V(0, 0, z(.085)), V(0, 0, z(.1)), Rb * 1.02, Rb * 1.02, 10), TIP))
    return parts
def shell_heavy():
    r = Node('shell_heavy')
    for g, m in shell_geo(): r.add(g, m)
    return r

# ------------------------------------------------------------------ emplacements
def emplacement_mg():
    r = Node('emplacement_mg')
    r.add(cyl(V(0, 0, 0), V(0, .05, 0), 2.0, 2.0, 16), EARTH)
    rng = np.random.RandomState(7); NB = 14; Rr = 1.4
    for c in range(4):
        for k in range(NB):
            a = 2 * PI * (k + .5 * (c % 2)) / NB
            if abs(((a - PI + PI) % (2 * PI)) - PI) < .5: continue          # open at the rear (-z)
            a += rng.uniform(-.03, .03)
            u = V(math.cos(a), 0, -math.sin(a)); w = V(math.sin(a), 0, math.cos(a))
            R = np.stack([u, UY, w], 1)
            r.add(box((Rr * math.sin(a), .05 + .1 + c * .2, Rr * math.cos(a)), (.6, .2, .32), R), BAG if (k + c) % 2 else BAG2)
    for x, z in ((-.9, -1.2), (.9, -1.0)): r.add(box((x, .2, z), (.5, .3, .26)), AMMO)
    head = V(0, .98, 0)
    for lx, lz in ((.0, .8), (.55, -.5), (-.55, -.5)):
        r.add(cyl(head, V(lx, .05, lz), .028, .02, 6), DGREY)
    r.add(cyl(head + V(0, -.06, 0), head + V(0, .02, 0), .06, .05, 8), METAL)
    g = r.child('emplacement_mg_gun', tuple(head + V(0, .1, 0)))
    g.add(box((0, 0, .02), (.13, .17, .72)), DGREY)
    g.add(cyl(V(0, .02, .38), V(0, .02, 1.35), .026, .026, 8), BLACK); g.add(cyl(V(0, .02, .38), V(0, .02, .95), .05, .05, 8), DGREY)
    g.add(cyl(V(0, .02, 1.35), V(0, .02, 1.42), .04, .04, 8), DGREY)
    g.add(box((.17, -.02, .0), (.16, .22, .26)), AMMO); g.add(box((0, -.12, 0), (.06, .12, .2)), METAL)
    g.add(box((0, 0, -.4), (.15, .2, .06)), BLACK)
    for x in (-.07, .07): g.add(cyl(V(x, 0, -.34), V(x, .12, -.46), .018, .018, 6), BLACK)
    g.add(box((0, .12, .2), (.03, .06, .05)), METAL)
    return r

def emplacement_aa():
    r = Node('emplacement_aa')
    r.add(cyl(V(0, 0, 0), V(0, .12, 0), 2.2, 2.2, 20), CONC)
    r.add(cyl(V(0, .12, 0), V(0, .3, 0), 1.0, .9, 16), GREY_D)
    r.add(cyl(V(0, .3, 0), V(0, 1.15, 0), .38, .3, 12), GREY)
    r.add(cyl(V(0, 1.15, 0), V(0, 1.28, 0), .62, .62, 12), DGREY)
    for x in (-.5, .5): r.add(box((x, 1.55, -.05), (.1, .6, .9)), GREY_D)
    r.add(box((0, 1.38, -.6), (.5, .08, .5)), BLACK); r.add(box((0, 1.65, -.78), (.4, .35, .06)), BLACK)
    for x, z in ((-1.6, -1.0), (1.6, -.8), (-1.5, 1.2)): r.add(box((x, .3, z), (.55, .36, .4)), AMMO)
    g = r.child('emplacement_aa_barrels', (0, 1.55, 0))
    for x in (-.22, .22):
        g.add(cyl(V(x, 0, .1), V(x, 0, 3.1), .045, .04, 8), BLACK); g.add(cyl(V(x, 0, .3), V(x, 0, 1.4), .085, .085, 8), DGREY)
        g.add(cyl(V(x, 0, 3.1), V(x, 0, 3.28), .075, .075, 8), DGREY)
        g.add(box((x, 0, -.2), (.2, .24, .6)), BLACK); g.add(xf(cyl(V(-.1, 0, 0), V(.1, 0, 0), .26, .26, 10), None, (x * 2.2, -.05, -.2)), AMMO)
    g.add(box((0, 0, -.1), (.55, .12, .5)), DGREY); g.add(box((0, .1, -.7), (.3, .2, .25)), METAL)
    g.add(box((0, .0, -.55), (.12, .42, .5), rotx(-.4)), DGREY)
    return r

def emplacement_mortar():
    r = Node('emplacement_mortar')
    r.add(cyl(V(0, 0, 0), V(0, .06, 0), .42, .42, 14), METAL)
    d = V(0, math.sin(math.radians(72)), math.cos(math.radians(72)))
    r.add(cyl(V(0, .06, 0), d * 1.25 + V(0, .06, 0), .055, .052, 10), DGREY)
    r.add(cyl(d * 1.18 + V(0, .06, 0), d * 1.28 + V(0, .06, 0), .065, .065, 10), BLACK)
    r.add(cyl(V(0, .06, 0), V(0, .06, 0) + d * .1, .08, .08, 10), METAL)
    top = d * .85 + V(0, .06, 0)
    for s in (-1, 1): r.add(cyl(top, V(s * .5, .03, .85), .018, .015, 6), DGREY)
    r.add(box(top, (.12, .05, .08)), METAL)
    # shells lying beside, crate
    r.add(box((-.95, .12, .1), (.4, .24, .75)), AMMO)
    for k, (x, z) in enumerate(((-.62, .55), (-.55, .75), (.7, -.4))):
        for g, m in shell_geo(.38, .04):
            gg = xf(xf(g, roty(.5 + k)), None, (x, .045, z)); r.add(gg, m)
    for g, m in shell_geo(.38, .04): r.add(xf(xf(g, rotx(-PI / 2 + .1)), None, (-.95, .38, .1)), m)
    return r

# ------------------------------------------------------------------ assemble
roots = [griffon(), gunship(), parachute(), emplacement_mg(), emplacement_aa(), emplacement_mortar(), shell_heavy(), crate_drop()]
out = build_glb(roots)
open(os.path.join(GAME, 'assets', 'air.glb'), 'wb').write(out)
open(os.path.join(GAME, 'assets', 'air.glb.b64.txt'), 'w').write(base64.b64encode(out).decode())
print('glb bytes', len(out), 'b64', len(base64.b64encode(out)))
