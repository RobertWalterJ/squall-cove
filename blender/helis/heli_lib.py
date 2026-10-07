"""Shared helpers for the helicopter generators (Blender 4.2, headless).
All geometry is authored in GAME coordinates: x = model's LEFT, y = up, z = forward (metres), origin on the ground.
It is converted to Blender (x, -z, y) when the objects are created, so the glTF exporter (Y up) gives game coords back.
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix

PI = math.pi
def V(*a): return Vector(a)
def b_of(p): return (p[0], -p[2], p[1])
def clamp(v, a, b): return max(a, min(b, v))

# ------------------------------------------------------------------ materials
MAT = {}
def _lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def hexrgb(h):
    h = h.lstrip('#'); return tuple(_lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))

def defmat(name, color, rough=0.6, metal=0.0, emit=None, emit_str=4.0, alpha=1.0, double=False):
    if name in MAT: return MAT[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*hexrgb(color), 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = (*hexrgb(emit), 1)
        b.inputs['Emission Strength'].default_value = emit_str
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
        m.blend_method = 'BLEND'
    m.use_backface_culling = not double
    MAT[name] = m
    return m

def std_palette():
    defmat('heli_glass', '#25303a', 0.08, 0.0, alpha=0.5)
    defmat('heli_interior', '#3a3d36', 0.9)
    defmat('heli_seat', '#3a3d34', 0.85)
    defmat('heli_seat_canvas', '#6e6c4e', 0.95)
    defmat('heli_black', '#1c1d1e', 0.75)
    defmat('heli_panel_line', '#232526', 0.8)
    defmat('heli_metal', '#7b7f83', 0.4, 0.85)
    defmat('heli_steel_dark', '#3b3e42', 0.45, 0.8)
    defmat('heli_rubber', '#1a1a1a', 0.95)
    defmat('heli_blade', '#26282a', 0.55, 0.2)
    defmat('heli_blade_tip', '#c9a227', 0.6)
    defmat('heli_light_red', '#ff2a1a', 0.3, emit='#ff2a1a', emit_str=5.0)
    defmat('heli_light_green', '#22ff55', 0.3, emit='#22ff55', emit_str=5.0)
    defmat('heli_light_white', '#f4f4ff', 0.3, emit='#ffffff', emit_str=5.0)
    defmat('heli_rotor_blur', '#9aa0a6', 0.9, alpha=0.12, double=True)

# ------------------------------------------------------------------ interpolation
def make_interp(keys):
    keys = sorted(keys); xs = [k[0] for k in keys]; ys = [k[1] for k in keys]; n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]; d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    if n > 1:
        m[0] = d[0]; m[-1] = d[-1]
        for i in range(1, n - 1):
            m[i] = 0.0 if d[i - 1] * d[i] <= 0 else 2 * d[i - 1] * d[i] / (d[i - 1] + d[i])
        for i in range(n - 1):
            if d[i] == 0: m[i] = m[i + 1] = 0.0
            else:
                a, bb = m[i] / d[i], m[i + 1] / d[i]; s = a * a + bb * bb
                if s > 9: t = 3 / math.sqrt(s); m[i] = t * a * d[i]; m[i + 1] = t * bb * d[i]
    def f(x):
        if x <= xs[0]: return ys[0]
        if x >= xs[-1]: return ys[-1]
        i = 0
        while xs[i + 1] < x: i += 1
        t = (x - xs[i]) / h[i]; t2 = t * t; t3 = t2 * t
        return (2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i] + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1]
    return f

# ------------------------------------------------------------------ mesh container
def _vol(pts, faces):
    s = 0.0
    for f in faces:
        a = Vector(pts[f[0]])
        for k in range(1, len(f) - 1):
            s += a.dot(Vector(pts[f[k]]).cross(Vector(pts[f[k + 1]])))
    return s

def weld(pts, faces, eps=2e-4):
    key = {}; newp = []; remap = []
    for p in pts:
        k = (round(p[0] / eps), round(p[1] / eps), round(p[2] / eps))
        if k not in key: key[k] = len(newp); newp.append(tuple(p))
        remap.append(key[k])
    nf = []; keep = []
    for fi, f in enumerate(faces):
        g = []
        for i in f:
            j = remap[i]
            if not g or g[-1] != j: g.append(j)
        if len(g) > 1 and g[0] == g[-1]: g.pop()
        g = list(dict.fromkeys(g))
        if len(g) < 3: continue
        nf.append(tuple(g)); keep.append(fi)
    return newp, nf, remap, keep

def ear_clip(poly):
    """poly: list of (a, b); returns list of index triples."""
    n = len(poly); idx = list(range(n))
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    if area < 0: idx.reverse()
    def cross(o, a, b): return (poly[a][0] - poly[o][0]) * (poly[b][1] - poly[o][1]) - (poly[a][1] - poly[o][1]) * (poly[b][0] - poly[o][0])
    tris = []; guard = 0
    while len(idx) > 3 and guard < 1000:
        guard += 1; found = False
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            if cross(i0, i1, i2) <= 1e-12: continue
            ok = True
            for j in idx:
                if j in (i0, i1, i2): continue
                if cross(i0, i1, j) >= 0 and cross(i1, i2, j) >= 0 and cross(i2, i0, j) >= 0: ok = False; break
            if ok:
                tris.append((i0, i1, i2)); idx.pop(k); found = True; break
        if not found: break
    if len(idx) == 3: tris.append(tuple(idx))
    return tris

class Part:
    def __init__(self, name, pivot=(0, 0, 0)):
        self.name = name; self.pivot = Vector(pivot); self.V = []; self.F = []   # F: (idx list, mat name, smooth)

    def tris(self): return sum(len(f[0]) - 2 for f in self.F)

    def add(self, pts, faces, mat, smooth=False, orient=True, mats=None, flats=None, do_weld=False, tagged=None, mat_tag=None):
        pts = [tuple(p) for p in pts]; faces = [tuple(f) for f in faces]
        if do_weld:
            pts, nf, remap, keep = weld(pts, faces)
            if mats: mats = [mats[k] for k in keep]
            if flats: flats = [flats[k] for k in keep]
            if tagged is not None:
                tg = {remap[i] for i in tagged}
                mats = [mat_tag if any(i in tg for i in f) else (mats[k] if mats else mat) for k, f in enumerate(nf)]
                flats = [True if mats[k] == mat_tag else (flats[k] if flats else not smooth) for k, f in enumerate(nf)]
                flats = [bool(x) for x in flats]
            faces = nf
        if orient and _vol(pts, faces) < 0: faces = [f[::-1] for f in faces]
        base = len(self.V); self.V += pts
        for k, f in enumerate(faces):
            m = mats[k] if mats else mat
            fl = flats[k] if flats else (not smooth)
            self.F.append(([i + base for i in f], m, not fl))
        return self

    # ---- primitives
    def box(self, c, size, mat, rot=(0, 0, 0), bevel=0.0, smooth=False):
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
        if bevel > 0: bmesh.ops.bevel(bm, geom=bm.verts[:] + bm.edges[:], offset=bevel, segments=1, affect='EDGES')
        M = Matrix.Translation(Vector(c)) @ (Matrix.Rotation(math.radians(rot[2]), 4, 'Z') @ Matrix.Rotation(math.radians(rot[1]), 4, 'Y') @ Matrix.Rotation(math.radians(rot[0]), 4, 'X'))
        pts = [tuple(M @ v.co) for v in bm.verts]
        bm.verts.ensure_lookup_table()
        faces = [tuple(v.index for v in f.verts) for f in bm.faces]
        bm.free()
        return self.add(pts, faces, mat, smooth)

    def loft(self, rings, mat, smooth=True, caps=(True, True), tagrings=None, mat_tag=None, do_weld=False):
        pts = []; n = len(rings[0]); tagged = set()
        for ri, r in enumerate(rings):
            for ci, p in enumerate(r):
                if tagrings and tagrings[ri][ci]: tagged.add(len(pts))
                pts.append(p)
        faces = []
        for a in range(len(rings) - 1):
            for i in range(n):
                j = (i + 1) % n
                faces.append((a * n + i, a * n + j, (a + 1) * n + j, (a + 1) * n + i))
        flats = [not smooth] * len(faces)
        if caps[0]: faces.append(tuple(reversed(range(n)))); flats.append(True)
        if caps[1]: faces.append(tuple((len(rings) - 1) * n + i for i in range(n))); flats.append(True)
        return self.add(pts, faces, mat, smooth, flats=flats, mats=[mat] * len(faces), do_weld=do_weld,
                        tagged=tagged if tagrings else None, mat_tag=mat_tag)

    def sweep(self, path, radii, seg, mat, smooth=True, caps=(True, True), up=(0, 1, 0), phase=0.0):
        """Tube along a polyline. radii: float, list of floats or list of (ra, rb) ellipse radii."""
        P = [Vector(p) for p in path]; n = len(P)
        if not isinstance(radii, (list, tuple)): radii = [radii] * n
        tans = []
        for i in range(n):
            a = P[max(i - 1, 0)]; b = P[min(i + 1, n - 1)]
            tans.append((b - a).normalized())
        ref = Vector(up)
        if abs(tans[0].dot(ref)) > 0.95: ref = Vector((1, 0, 0))
        nrm = tans[0].cross(ref).normalized(); rings = []
        for i in range(n):
            t = tans[i]
            nrm = (nrm - t * nrm.dot(t))
            if nrm.length < 1e-6: nrm = t.cross(Vector((0, 1, 0)) if abs(t.y) < .9 else Vector((1, 0, 0)))
            nrm.normalize(); bn = t.cross(nrm)
            r = radii[i]; ra, rb = (r, r) if not isinstance(r, (tuple, list)) else r
            ring = []
            for k in range(seg):
                a = phase + 2 * PI * k / seg
                ring.append(P[i] + nrm * (ra * math.cos(a)) + bn * (rb * math.sin(a)))
            rings.append(ring)
        return self.loft(rings, mat, smooth, caps)

    def cyl(self, p0, p1, r0, r1=None, seg=8, mat=None, smooth=True, caps=(True, True)):
        return self.sweep([p0, p1], [r0, r0 if r1 is None else r1], seg, mat, smooth, caps)

    def ellipsoid(self, c, r, mat, seg=10, nl=6, smooth=True, axis='z'):
        c = Vector(c); rings = []
        for i in range(nl + 1):
            t = PI * i / nl; s = max(math.sin(t), 1e-3)
            ring = []
            for k in range(seg):
                a = 2 * PI * k / seg
                if axis == 'z': ring.append(c + Vector((r[0] * s * math.cos(a), r[1] * s * math.sin(a), r[2] * math.cos(t))))
                elif axis == 'x': ring.append(c + Vector((r[0] * math.cos(t), r[1] * s * math.cos(a), r[2] * s * math.sin(a))))
                else: ring.append(c + Vector((r[0] * s * math.cos(a), r[1] * math.cos(t), r[2] * s * math.sin(a))))
            rings.append(ring)
        return self.loft(rings, mat, smooth, (False, False), do_weld=True)

    def prism(self, outline, origin, ua, ub, thick, mat, k=0.86, smooth=False):
        """Extruded polygon (a, b) in the plane spanned by unit vectors ua, ub; thickness along ua x ub; edges chamfered by k."""
        o = Vector(origin); ua = Vector(ua).normalized(); ub = Vector(ub).normalized(); nm = ua.cross(ub).normalized()
        cen = (sum(p[0] for p in outline) / len(outline), sum(p[1] for p in outline) / len(outline))
        rings = []
        for h, s in ((-thick / 2, k), (0.0, 1.0), (thick / 2, k)):
            rings.append([o + ua * (cen[0] + (p[0] - cen[0]) * s) + ub * (cen[1] + (p[1] - cen[1]) * s) + nm * h for p in outline])
        n = len(outline); pts = []; faces = []
        for r in rings: pts += r
        for a in range(2):
            for i in range(n):
                j = (i + 1) % n; faces.append((a * n + i, a * n + j, (a + 1) * n + j, (a + 1) * n + i))
        for ti in ear_clip(outline):
            faces.append(tuple(ti)); faces.append(tuple(2 * n + i for i in reversed(ti)))
        return self.add(pts, faces, mat, smooth)

    def patch(self, grid, mat, outward, smooth=True):
        """grid: rows x cols of points. Oriented so the first quad faces `outward`."""
        R = len(grid); C = len(grid[0]); pts = []; faces = []
        for r in grid: pts += [tuple(p) for p in r]
        for i in range(R - 1):
            for j in range(C - 1):
                faces.append((i * C + j, i * C + j + 1, (i + 1) * C + j + 1, (i + 1) * C + j))
        a, b, c = Vector(pts[faces[0][0]]), Vector(pts[faces[0][1]]), Vector(pts[faces[0][2]])
        if (b - a).cross(c - a).dot(Vector(outward)) < 0: faces = [f[::-1] for f in faces]
        return self.add(pts, faces, mat, smooth, orient=False)

    def light(self, c, r, mat):
        c = Vector(c)
        pts = [c + Vector(d) * r for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
        faces = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
        return self.add(pts, faces, mat, False)

    def disc(self, c, radius, mat, seg=28, axis='y'):
        c = Vector(c); pts = [tuple(c)]
        for k in range(seg):
            a = 2 * PI * k / seg
            off = Vector((radius * math.cos(a), 0, radius * math.sin(a))) if axis == 'y' else Vector((0, radius * math.cos(a), radius * math.sin(a)))
            pts.append(tuple(c + off))
        faces = [(0, 1 + k, 1 + (k + 1) % seg) for k in range(seg)]
        return self.add(pts, faces, mat, False, orient=False)

    def blade(self, hub, d, up, r0, r1, chord0, chord1, thick, pitch_deg, mat, cone=0.0, nst=5, taper_tip=True):
        """Rotor blade from radius r0 to r1 along unit vector d from `hub`; `up` = thickness direction. cone = tip lift along up."""
        hub = Vector(hub); d = Vector(d).normalized(); up = Vector(up).normalized(); ch = up.cross(d).normalized()
        rings = []
        for i in range(nst):
            u = i / (nst - 1); r = r0 + (r1 - r0) * u
            chord = chord0 + (chord1 - chord0) * u
            pit = math.radians(pitch_deg * (1 - 0.6 * u))
            c = hub + d * r + up * (cone * u * u)
            t = thick * (0.6 if (i == nst - 1 and taper_tip) else 1.0)
            prof = [(0.25, 0), (0.12, 0.5), (-0.3, 0.38), (-0.75, 0.0), (-0.3, -0.34), (0.12, -0.5)]
            ring = []
            for (px, py) in prof:
                cc = px * chord; tt = py * t
                cp, sp = math.cos(pit), math.sin(pit)
                ring.append(c + ch * (cc * cp - tt * sp) + up * (cc * sp + tt * cp))
            rings.append(ring)
        return self.loft(rings, mat, True, (True, True))

# ------------------------------------------------------------------ hull: lofted superellipse sections with recessed openings
class Hull:
    """keys: (z, w, top, bot, p). Ring points are laid out by normalised height s (-1 bottom .. +1 top)
    so recess (door/window) edges land exactly on ring lines. recesses: dicts side 'L'/'R'/'B', z0, z1, s0, s1, depth."""
    def __init__(self, keys, recesses=(), spacing=0.7, nlev=11, xc=0.0, zmarks=(), minw=0.015):
        ks = sorted(keys)
        self.fw = make_interp([(k[0], k[1]) for k in ks]); self.ft = make_interp([(k[0], k[2]) for k in ks])
        self.fb = make_interp([(k[0], k[3]) for k in ks]); self.fp = make_interp([(k[0], k[4]) for k in ks])
        self.z_min = ks[0][0]; self.z_max = ks[-1][0]; self.xc = xc; self.minw = minw
        self.rec = list(recesses)
        zs = set()
        for a, b in zip(ks, ks[1:]):
            n = max(1, int(round((b[0] - a[0]) / spacing)))
            for i in range(n): zs.add(round(a[0] + (b[0] - a[0]) * i / n, 5))
        zs.add(ks[-1][0])
        for z in zmarks: zs.add(round(z, 5))
        edges = set()
        for r in self.rec: edges.add(round(r['z0'], 5)); edges.add(round(r['z1'], 5))
        zs = [z for z in zs if all(abs(z - e) > 0.03 for e in edges)]
        st = []
        for z in zs:
            act = frozenset(i for i, r in enumerate(self.rec) if r['z0'] < z < r['z1'])
            st.append((z, 0, act))
        for i, r in enumerate(self.rec):
            for z, flag in ((r['z0'], 'in'), (r['z1'], 'out')):
                base = frozenset(j for j, q in enumerate(self.rec) if q['z0'] < z < q['z1'])
                if flag == 'in': st += [(round(z, 5), -1, base), (round(z, 5), 1, base | {i})]
                else: st += [(round(z, 5), -1, base | {i}), (round(z, 5), 1, base)]
        st.sort(key=lambda t: (t[0], t[1]))
        self.stations = [(z, act) for z, _, act in st]
        base_levels = [math.sin(-PI / 2 + PI * k / (nlev + 1)) for k in range(1, nlev + 1)]
        ed = set()
        for r in self.rec: ed.add(round(r['s0'], 5)); ed.add(round(r['s1'], 5))
        self.levels = sorted(set([round(s, 5) for s in base_levels]) | ed)
        # remove base levels that are too close to an edge
        keep = []
        for s in self.levels:
            if s in ed or all(abs(s - e) > 0.045 for e in ed): keep.append(s)
        self.levels = keep

    def params(self, z):
        return max(self.fw(z), self.minw), self.ft(z), self.fb(z), max(self.fp(z), 1.2)

    def surf(self, side, z, s, off=0.0, depth=0.0):
        w, top, bot, p = self.params(z); yc = (top + bot) / 2; hh = max((top - bot) / 2, 0.01)
        s = clamp(s, -1, 1)
        x = w * max(1 - abs(s) ** p, 0.0) ** (1 / p)
        y = yc + hh * s
        P = Vector((side * (max(x - depth, 0.0)) + self.xc, y, z))
        if off:
            n = self.normal(side, z, s); P += n * off
        return P

    def normal(self, side, z, s):
        w, top, bot, p = self.params(z); yc = (top + bot) / 2; hh = max((top - bot) / 2, 0.01)
        s = clamp(s, -1, 1); x = w * max(1 - abs(s) ** p, 0.0) ** (1 / p)
        gx = p * (x / w) ** (p - 1) / w; gy = p * math.copysign(abs(s) ** (p - 1), s) / hh
        n = Vector((side * gx, gy, 0))
        if n.length < 1e-9: n = Vector((0, 1, 0))
        return n.normalized()

    def s_of(self, y, z):
        w, top, bot, p = self.params(z); return clamp((y - (top + bot) / 2) / ((top - bot) / 2), -1, 1)

    def _entries(self, side):
        """ring entries for one side ascending s: (s, tag)"""
        out = []
        for s in self.levels:
            ents = []
            for i, r in enumerate(self.rec):
                ok = r['side'] == 'B' or (r['side'] == 'L' and side > 0) or (r['side'] == 'R' and side < 0)
                if not ok: continue
                if abs(s - r['s0']) < 1e-6: ents = [(s, None), (s, i)]
                elif abs(s - r['s1']) < 1e-6: ents = [(s, i), (s, None)]
                elif r['s0'] < s < r['s1']: ents = [(s, i)]
            out += ents if ents else [(s, None)]
        return out

    def rings(self):
        ep = self._entries(1); em = self._entries(-1)
        rings = []; tags = []
        for z, act in self.stations:
            ring = [self.surf(1, z, -1)]; tg = [False]
            for s, t in ep:
                d = self.rec[t]['depth'] if (t is not None and t in act) else 0.0
                ring.append(self.surf(1, z, s, 0, d)); tg.append(d > 0)
            ring.append(self.surf(1, z, 1)); tg.append(False)
            for s, t in reversed(em):
                d = self.rec[t]['depth'] if (t is not None and t in act) else 0.0
                ring.append(self.surf(-1, z, s, 0, d)); tg.append(d > 0)
            rings.append(ring); tags.append(tg)
        return rings, tags

    def build(self, P, mat, mat_in='heli_interior', smooth=True, caps=(True, True)):
        rings, tags = self.rings()
        return P.loft(rings, mat, smooth, caps, tagrings=tags, mat_tag=mat_in, do_weld=True)

    # ---- surface patches
    def seq(self, side, s0, s1, n=1):
        return [(side, s0 + (s1 - s0) * i / n) for i in range(n + 1)]
    def roofseq(self, s0, n=3):
        a = [(1, s0 + (1 - s0) * i / n) for i in range(n + 1)]
        b = [(-1, 1 - (1 - s0) * i / n) for i in range(1, n + 1)]
        return a + b
    def ringseq(self):
        a = [(1, s) for s in [-1] + self.levels + [1]]
        b = [(-1, s) for s in reversed(self.levels)]
        return a + b

    def patch(self, P, seq, z0, z1, off, mat, nz=2, smooth=True):
        zs = [z0 + (z1 - z0) * i / nz for i in range(nz + 1)]
        grid = [[self.surf(sd, z, s, off) for (sd, s) in seq] for z in zs]
        zc = (z0 + z1) / 2; mid = seq[len(seq) // 2]
        out = self.normal(mid[0], zc, mid[1])
        return P.patch(grid, mat, out, smooth)

    def panel(self, P, side, z0, z1, s0, s1, off, mat, nz=2, ns=1, smooth=True):
        for sd in ((1, -1) if side == 0 else (side,)):
            self.patch(P, self.seq(sd, s0, s1, ns), z0, z1, off, mat, nz, smooth)

    def frame(self, P, side, z0, z1, s0, s1, th, off, mat, nz=2):
        """Thin outline strips (door / hatch panel lines) around a rectangle in (z, s). th in metres of z; s width derived."""
        ds = th / max(self.params((z0 + z1) / 2)[1] - self.params((z0 + z1) / 2)[2], 0.3) * 2
        for sd in ((1, -1) if side == 0 else (side,)):
            self.patch(P, self.seq(sd, s0, s0 + ds, 1), z0, z1, off, mat, nz)
            self.patch(P, self.seq(sd, s1 - ds, s1, 1), z0, z1, off, mat, nz)
            self.patch(P, self.seq(sd, s0, s1, 2), z0, z0 + th, off, mat, 1)
            self.patch(P, self.seq(sd, s0, s1, 2), z1 - th, z1, off, mat, 1)

    def band(self, P, z0, z1, off, mat, nz=1):
        self.patch(P, self.ringseq(), z0, z1, off, mat, nz)

# ------------------------------------------------------------------ scene objects
def new_empty(name, loc, parent=None, size=0.15, shape='PLAIN_AXES'):
    o = bpy.data.objects.new(name, None); o.empty_display_type = shape; o.empty_display_size = size
    bpy.context.scene.collection.objects.link(o)
    o.location = b_of(loc)
    if parent is not None: o.parent = parent
    return o

def part_to_obj(part, parent):
    verts = [b_of(Vector(p) - part.pivot) for p in part.V]
    me = bpy.data.meshes.new(part.name)
    me.from_pydata(verts, [], [f[0] for f in part.F])
    me.update()
    order = []
    for f in part.F:
        if f[1] not in order: order.append(f[1])
    for mn in order: me.materials.append(MAT[mn])
    assert len(me.polygons) == len(part.F), (part.name, len(me.polygons), len(part.F))
    for poly, f in zip(me.polygons, part.F):
        poly.material_index = order.index(f[1]); poly.use_smooth = f[2]
    o = bpy.data.objects.new(part.name, me)
    bpy.context.scene.collection.objects.link(o)
    o.location = b_of(part.pivot)
    if parent is not None: o.parent = parent
    return o

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MAT.clear()
    std_palette()
