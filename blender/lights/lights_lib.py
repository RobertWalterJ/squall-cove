"""Geometry helpers + scene graph + GLB writer for the lighting pack (pure python + numpy).
Metres, +Z = forward / beam direction, +Y up. Flat shaded: the file carries NO normals (three.js GLTFLoader then flat-shades),
vertices are welded per material and indexed (uint16) to keep the pack small. Plain colour materials are `lights_#hex`; the
named lighting materials (lamp_on, lamp_off, lens_glass, tail_on, tail_off, ind_on, ind_off) are defined in SPECIAL."""
import sys, os, json, struct, base64, math
import numpy as np

PI = math.pi
def V(*a): return np.array(a, float)
UX, UY, UZ = V(1, 0, 0), V(0, 1, 0), V(0, 0, 1)
def norm(v): return v / (np.linalg.norm(v) + 1e-12)
def rotx(a): c, s = math.cos(a), math.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
def roty(a): c, s = math.cos(a), math.sin(a); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
def rotz(a): c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
def D(a): return math.radians(a)

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
def loft(rings, n=8, caps=(True, True), phase=0.3927):
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
def dome(c, r, n=8, nl=3):
    """upper half-ellipsoid, flat open bottom closed by a cap"""
    c = np.asarray(c, float); rs = []
    for i in range(nl + 1):
        t = (PI / 2) * i / nl
        rs.append((c + V(0, r[1] * math.sin(t), 0), max(r[0] * math.cos(t), 1e-4), max(r[2] * math.cos(t), 1e-4), UX, UZ))
    return loft(rs, n, (True, False))
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
    o = {0: (2, 1), 1: (0, 2), 2: (0, 1)}[axis]; n = len(poly); Vs = []
    for av in (a0, a1):
        for p, q in poly:
            v = [0, 0, 0]; v[o[0]] = p; v[o[1]] = q; v[axis] = av; Vs.append(v)
    Vs = np.array(Vs, float); F = []
    for k in range(n):
        k2 = (k + 1) % n; F += [(k, k2, n + k2), (k, n + k2, n + k)]
    for k in range(1, n - 1): F += [(0, k, k + 1), (n, n + k, n + k + 1)]
    return orient(Vs, F, Vs.mean(0))
def tube(pts, r, n=5, caps=(True, True)):
    """tube along a polyline with parallel-transported frames. r may be a float or a list per point."""
    pts = [np.asarray(p, float) for p in pts]; m = len(pts)
    rr = [r] * m if np.isscalar(r) else list(r)
    tans = []
    for i in range(m):
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, m - 1)]; tans.append(norm(b - a))
    u, v = frame(tans[0]); rings = []
    for i in range(m):
        if i > 0:
            t = tans[i]; u = u - t * np.dot(u, t); u = norm(u); v = np.cross(t, u)
        rings.append((pts[i], rr[i], rr[i], u, v))
    return loft(rings, n, caps)
def arc_pts(c, rad, a0, a1, k, y=0.0, plane='xz'):
    out = []
    for i in range(k + 1):
        a = a0 + (a1 - a0) * i / k
        out.append(V(c[0] + rad * math.cos(a), y, c[1] + rad * math.sin(a)))
    return out
def merge(*gs):
    Vs = []; F = []; o = 0
    for v, f in gs:
        Vs.append(np.asarray(v, float)); F.append(np.asarray(f, int) + o); o += len(v)
    return np.vstack(Vs), np.vstack(F)
def xf(g, R=None, t=(0, 0, 0)):
    v, f = g; v = np.asarray(v, float)
    if R is not None: v = v @ np.asarray(R).T
    return v + np.asarray(t, float), f
def look(d, up=UY):
    """rotation matrix taking local +Z to direction d (local +Y kept as upright as possible)"""
    z = norm(np.asarray(d, float)); x = np.cross(up, z)
    if np.linalg.norm(x) < 1e-6: x = UX
    x = norm(x); y = np.cross(z, x)
    return np.stack([x, y, z], 1)
def quat(R):
    R = np.asarray(R, float); t = np.trace(R)
    if t > 0:
        s = math.sqrt(t + 1) * 2; q = [(R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s, s / 4]
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = math.sqrt(1 + R[0, 0] - R[1, 1] - R[2, 2]) * 2; q = [s / 4, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s, (R[2, 1] - R[1, 2]) / s]
    elif R[1, 1] > R[2, 2]:
        s = math.sqrt(1 + R[1, 1] - R[0, 0] - R[2, 2]) * 2; q = [(R[0, 1] + R[1, 0]) / s, s / 4, (R[1, 2] + R[2, 1]) / s, (R[0, 2] - R[2, 0]) / s]
    else:
        s = math.sqrt(1 + R[2, 2] - R[0, 0] - R[1, 1]) * 2; q = [(R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, s / 4, (R[1, 0] - R[0, 1]) / s]
    q = np.array(q); q /= np.linalg.norm(q); return [float(x) for x in q]

# ------------------------------------------------------------------ materials
MATS = {}
def mat(hexcol, rough=.8, metal=.0, dbl=False):
    k = (hexcol, rough, metal, dbl); MATS.setdefault(k, len(MATS)); return k
# named lighting materials: the game toggles by swapping lamp_off <-> lamp_on (or driving emissiveIntensity on lamp_on)
SPECIAL = {
    'lamp_off':   {'baseColorFactor': [.62, .62, .56, 1], 'metallicFactor': .1, 'roughnessFactor': .25},
    'lamp_on':    {'baseColorFactor': [1, .93, .72, 1], 'metallicFactor': 0, 'roughnessFactor': .4, 'emissive': [1, .88, .58]},
    'lens_glass': {'baseColorFactor': [.55, .66, .7, .38], 'metallicFactor': .2, 'roughnessFactor': .08, 'blend': True},
    'tail_off':   {'baseColorFactor': [.42, .04, .03, 1], 'metallicFactor': .05, 'roughnessFactor': .3},
    'tail_on':    {'baseColorFactor': [1, .08, .05, 1], 'metallicFactor': 0, 'roughnessFactor': .4, 'emissive': [1, .1, .06]},
    'ind_off':    {'baseColorFactor': [.05, .22, .08, 1], 'metallicFactor': 0, 'roughnessFactor': .4},
    'ind_on':     {'baseColorFactor': [.2, 1, .35, 1], 'metallicFactor': 0, 'roughnessFactor': .4, 'emissive': [.25, 1, .4]},
}
def lin(c): return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
LAMP_ON, LAMP_OFF, GLASS_L = 'lamp_on', 'lamp_off', 'lens_glass'
TAIL_ON, TAIL_OFF, IND_ON, IND_OFF = 'tail_on', 'tail_off', 'ind_on', 'ind_off'

# ------------------------------------------------------------------ scene graph
class Node:
    def __init__(self, name, t=(0, 0, 0), R=None, extras=None):
        self.name = name; self.t = tuple(float(x) for x in t); self.R = None if R is None else np.asarray(R, float)
        self.parts = []; self.kids = []; self.extras = extras; self.moving = False
    def add(self, g, m): self.parts.append((g, m)); return self
    def addp(self, parts, R=None, t=(0, 0, 0)):
        for g, m in parts: self.parts.append((xf(g, R, t), m))
        return self
    def child(self, name, t=(0, 0, 0), R=None, extras=None):
        n = Node(name, t, R, extras); self.kids.append(n); return n
    def empty(self, name, t, direction=None, R=None, **extras):
        """a pivot empty; local +Z = `direction` (beam / cable exit). extras go to node.extras"""
        if R is None and direction is not None: R = look(direction)
        n = Node(name, t, R, extras or None); self.kids.append(n); return n

def tri_count(node):
    n = 0
    for (v, f), m in node.parts: n += len(f)
    for k in node.kids: n += tri_count(k)
    return n

def build_glb(roots, generator='build_lights.py'):
    buf = bytearray(); bvs = []; accs = []; meshes = []; nodes = []; mats = []
    mk = {}
    def material(k):
        if k in mk: return mk[k]
        if isinstance(k, str):
            s = SPECIAL[k]; d = {'name': k, 'pbrMetallicRoughness': {'baseColorFactor': s['baseColorFactor'], 'metallicFactor': s['metallicFactor'], 'roughnessFactor': s['roughnessFactor']}}
            if 'emissive' in s: d['emissiveFactor'] = s['emissive']
            if s.get('blend'): d['alphaMode'] = 'BLEND'; d['doubleSided'] = True
        else:
            h, ro, me, dbl = k; c = [lin(int(h[i:i + 2], 16) / 255) for i in (1, 3, 5)]
            d = {'name': 'lights_' + h, 'pbrMetallicRoughness': {'baseColorFactor': c + [1.0], 'metallicFactor': me, 'roughnessFactor': ro}}
            if dbl: d['doubleSided'] = True
        mats.append(d); mk[k] = len(mats) - 1; return mk[k]
    def addbv(b, target):
        while len(buf) % 4: buf.append(0)
        bvs.append({'buffer': 0, 'byteOffset': len(buf), 'byteLength': len(b), 'target': target}); buf.extend(b); return len(bvs) - 1
    def mesh_for(node):
        bymat = {}
        for (v, f), m in node.parts:
            v = np.asarray(v, float); f = np.asarray(f, int)
            a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]; ar = np.linalg.norm(np.cross(b - a, c - a), axis=1); ok = ar > 1e-9
            bymat.setdefault(m, []).append(np.stack([a[ok], b[ok], c[ok]], 1).reshape(-1, 3))
        prims = []
        for m, lst in bymat.items():
            P = np.vstack(lst)
            q = np.round(P / 1e-5).astype(np.int64)
            uq, inv = np.unique(q, axis=0, return_inverse=True)
            inv = np.asarray(inv).reshape(-1)
            first = np.zeros(len(uq), int); first[inv[::-1]] = np.arange(len(inv))[::-1]
            Pu = P[first].astype('<f4'); idx = inv.astype('<u2' if len(uq) < 65535 else '<u4')
            ap = len(accs); accs.append({'bufferView': addbv(Pu.tobytes(), 34962), 'componentType': 5126, 'count': len(Pu), 'type': 'VEC3', 'min': Pu.min(0).tolist(), 'max': Pu.max(0).tolist()})
            ai = len(accs); accs.append({'bufferView': addbv(idx.tobytes(), 34963), 'componentType': 5123 if len(uq) < 65535 else 5125, 'count': len(idx), 'type': 'SCALAR'})
            prims.append({'attributes': {'POSITION': ap}, 'indices': ai, 'material': material(m), 'mode': 4})
        meshes.append({'name': node.name + '_mesh', 'primitives': prims}); return len(meshes) - 1
    def emit(node):
        i = len(nodes); d = {'name': node.name}; nodes.append(d)
        if any(node.t): d['translation'] = [round(x, 5) for x in node.t]
        if node.R is not None: d['rotation'] = [round(x, 6) for x in quat(node.R)]
        if node.extras: d['extras'] = node.extras
        if node.parts: d['mesh'] = mesh_for(node)
        ks = [emit(k) for k in node.kids]
        if ks: d['children'] = ks
        return i
    top = [emit(r) for r in roots]
    js = {'asset': {'version': '2.0', 'generator': generator}, 'scene': 0, 'scenes': [{'nodes': top}], 'nodes': nodes, 'meshes': meshes,
          'materials': mats, 'accessors': accs, 'bufferViews': bvs, 'buffers': [{'byteLength': len(buf)}]}
    j = json.dumps(js, separators=(',', ':')).encode()
    while len(j) % 4: j += b' '
    while len(buf) % 4: buf.append(0)
    return b'glTF' + struct.pack('<II', 2, 12 + 8 + len(j) + 8 + len(buf)) + struct.pack('<I', len(j)) + b'JSON' + j + struct.pack('<I', len(buf)) + b'BIN\0' + bytes(buf)

# ------------------------------------------------------------------ shared colours
OLIVE = mat('#4b5232', .8); OLIVE_D = mat('#394029', .85); OLIVE_L = mat('#5d6641', .8)
STEEL = mat('#6b7076', .45, .6); STEEL_D = mat('#44484d', .5, .6); GALV = mat('#8a9096', .5, .6)
DARK = mat('#1c1e20', .6, .3); BLACK = mat('#121314', .8); RUBBER = mat('#18191a', .95)
CONC = mat('#8a8b86', .95); CONC_D = mat('#6f706c', .95)
YELLOW = mat('#c9a227', .6); RED = mat('#9c2a20', .6); ORANGE = mat('#c4601e', .6)
WOOD = mat('#7a5c36', .9); BRASS = mat('#a8843a', .4, .7); CABLE = mat('#15161a', .7); CABLE_Y = mat('#c7a21e', .7)
GREEN_P = mat('#2f4a3a', .6, .3)   # painted harbour-lamp green
CREAM = mat('#d9d2bd', .7)

# ------------------------------------------------------------------ shared sub-assemblies
def flood_head(w=.5, h=.34, d=.22, hood=True, detail=0):
    """a floodlight head, housing centred on the origin, lens facing +Z. Returns [(geo, mat)] and lens-front z.
    detail 0 = housing + lens + hood; 1 = + bezel, rear fins, trunnion pins."""
    P = [(box((0, 0, 0), (w, h, d)), DARK_LAMP_BODY)]
    if detail:
        P.append((box((0, 0, d / 2 - .004), (w * .97, h * .93, .03)), STEEL_D))
        for i in range(4): P.append((box((-w * .33 + i * w * .22, 0, -d / 2 - .02), (.02, h * .8, .06)), STEEL_D))
        for s in (-1, 1): P.append((cyl((s * (w / 2 - .02), 0, 0), (s * (w / 2 + .05), 0, 0), .022, .022, 6), STEEL))
    P.append((box((0, 0, d / 2 + .004), (w * .86, h * .8, .025)), LAMP_OFF))
    if hood: P.append((box((0, h / 2 + .012, d / 2 + .04), (w * 1.02, .02, .2)), DARK_LAMP_BODY))
    return P
DARK_LAMP_BODY = mat('#2a2d30', .5, .45)

def catenary(a, b, sag, k):
    """k+1 points from a to b hanging with `sag` metres below the chord at mid-span (parabola approx of a catenary)"""
    a = np.asarray(a, float); b = np.asarray(b, float); out = []
    for i in range(k + 1):
        u = i / k; p = a + (b - a) * u; p[1] -= sag * 4 * u * (1 - u); out.append(p)
    return out

def string_span(a, b, nb=13, sag=.45, cable_r=.011, bulb_r=.05, hang=.07, bulb_mat=None, nside=4):
    """PARAMETRIC STRING LIGHTS: returns (parts, bulb_positions, cable_points). Catenary cable a->b with `nb` evenly spaced bulbs
    (by arc length of the parabola approx.), each bulb hanging `hang` below the cable on a little socket."""
    bulb_mat = bulb_mat or LAMP_OFF
    k = 24; pts = catenary(a, b, sag, k)
    seg = [np.linalg.norm(pts[i + 1] - pts[i]) for i in range(k)]; cum = np.concatenate([[0], np.cumsum(seg)]); L = cum[-1]
    kk = max(6, nb)                     # cable polyline: coarse but follows the curve
    cpts = catenary(a, b, sag, kk)
    parts = [(tube(cpts, cable_r, nside), CABLE)]
    bulbs = []
    for i in range(nb):
        s = L * (i + .5) / nb
        j = int(np.searchsorted(cum, s)); j = min(max(j, 1), k)
        u = (s - cum[j - 1]) / (seg[j - 1] + 1e-9); p = pts[j - 1] + (pts[j] - pts[j - 1]) * u
        # the cable polyline is coarser than `pts`: snap the socket top onto the coarse polyline so everything stays connected
        t = (j - 1 + u) / k; q = catenary(a, b, sag, 1)[0] * 0   # (unused)
        jj = min(int(t * kk), kk - 1); uu = t * kk - jj; top = cpts[jj] + (cpts[jj + 1] - cpts[jj]) * uu
        parts.append((cyl(top + V(0, .01, 0), top + V(0, -hang, 0), .02, .015, 5, (False, False)), BLACK))
        c = top + V(0, -hang - bulb_r * .8, 0)
        parts.append((ell(c, (bulb_r, bulb_r * 1.15, bulb_r), 6, 3), bulb_mat)); bulbs.append(c)
    return parts, bulbs, cpts
