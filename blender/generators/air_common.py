"""Shared modelling helpers for the detailed aircraft (pg_cormorant.py, pg_cl415.py).
Blender 4.2, Z up, metres, nose toward +X. Starboard is -Y, port is +Y.
Main ideas:
  * hull_loft      a fuselage lofted through many rounded-rectangle sections (separate top and bottom corner radii, roof crown)
  * patch / window surface patches that are projected onto the fuselage with a BVH ray cast, so windows, panels and bezels follow the skin
  * apply_uv       maps a mesh into the livery atlas (air_layout.Region) by face direction
  * tex_mat        a PBR material whose base colour (and normal) come from the painted atlas
"""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from pg_core import *
import air_layout as LY

PI = math.pi

# ---------------------------------------------------------------- interpolation
def make_interp(keys):
    """Monotone cubic (Fritsch-Carlson) through keys [(x, v)]; flat beyond the ends."""
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
                a, b = m[i] / d[i], m[i + 1] / d[i]; s = a * a + b * b
                if s > 9: t = 3 / math.sqrt(s); m[i] = t * a * d[i]; m[i + 1] = t * b * d[i]
    def f(x):
        if x <= xs[0]: return ys[0]
        if x >= xs[-1]: return ys[-1]
        i = 0
        while xs[i + 1] < x: i += 1
        t = (x - xs[i]) / h[i]; t2 = t * t; t3 = t2 * t
        return (2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i] + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1]
    return f

def clamp(v, a, b): return max(a, min(b, v))
def smooth(t): t = clamp(t, 0, 1); return t * t * (3 - 2 * t)

def cluster(x0, x1, n, a=0.5, b=0.5):
    """n+1 samples from x0 to x1, denser toward the ends (a, b: 0 = uniform .. 1 = cosine at that end)."""
    out = []
    for i in range(n + 1):
        t = i / n
        c = (1 - math.cos(PI * t)) / 2
        # blend uniform and cosine per end
        w = a * (1 - t) + b * t
        out.append(x0 + (x1 - x0) * (t * (1 - w) + c * w))
    return out

# ---------------------------------------------------------------- sections
def rr_ring(zt, zb, w, rt, rb, crown=0.0, yoff=0.0, nb=4, ncb=4, ns=5, nct=6, nt=7, vee=0.0):
    """A rounded rectangle section in (y, z): half width w, top zt, bottom zb, corner radii rt (top) and rb (bottom), roof crown.
    Returns 2*N points, bottom centre first, going up the +Y side; the vertex count only depends on the counts."""
    zb0 = zb; zb = zb + vee; h = zt - zb; w = max(w, 0.015)
    rt = max(0.0, min(rt, w * 0.985, h * 0.49)); rb = max(0.0, min(rb, w * 0.985, h * 0.49))
    if rt + rb > h * 0.98:
        s = h * 0.98 / (rt + rb); rt *= s; rb *= s
    half = []
    for i in range(nb): half.append(((w - rb) * i / nb, zb0 + vee * (i / nb)))
    for i in range(ncb): a = -PI / 2 + (PI / 2) * i / ncb; half.append((w - rb + rb * math.cos(a), zb + rb + rb * math.sin(a)))
    for i in range(ns): half.append((w, zb + rb + (h - rb - rt) * i / ns))
    for i in range(nct): a = (PI / 2) * i / nct; half.append((w - rt + rt * math.cos(a), zt - rt + rt * math.sin(a)))
    for i in range(nt): half.append(((w - rt) * (1 - i / nt), zt))
    def crowned(y, z):
        if crown and rt > 0:
            wt = clamp((z - (zt - rt)) / max(rt, 1e-6), 0, 1)
            z -= crown * (y / w) ** 2 * wt
        elif crown:
            z -= crown * (y / w) ** 2 * (1 if z > zt - 1e-6 else 0)
        return z
    half = [(y, crowned(y, z)) for (y, z) in half]
    top_centre = (0.0, zt)
    ring = half + [top_centre] + [(-y, z) for (y, z) in reversed(half[1:])]
    return [(y + yoff, z) for (y, z) in ring]

def ring_ellipse(zt, zb, w, p=2.0, n=48, yoff=0.0):
    zc, hh = (zt + zb) / 2, (zt - zb) / 2; out = []
    for i in range(n):
        a = 2 * PI * i / n - PI / 2; c, s = math.cos(a), math.sin(a)
        out.append((yoff + max(w, 0.015) * math.copysign(abs(c) ** (2 / p), c), zc + max(hh, 0.008) * math.copysign(abs(s) ** (2 / p), s)))
    return out

def _close_rings(bm, rings, cap_a=True, cap_b=True):
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n; bm.faces.new((a[i], a[j], b[j], b[i]))
    if cap_a: bm.faces.new(list(reversed(rings[0])))
    if cap_b: bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

def finish(bm, name, material=None, smooth=True, bvh=False):
    tree = BVHTree.FromBMesh(bm) if bvh else None
    o = obj_from_bm(bm, name, material, smooth)
    return (o, tree) if bvh else o

def hull_loft(xs, section, name, material=None, smooth=True, bvh=True, caps=(True, True)):
    """xs: station positions along X; section(x) -> list of (y, z) with a fixed count."""
    bm = bmesh.new(); rings = []
    for x in xs:
        rings.append([bm.verts.new((x, y, z)) for (y, z) in section(x)])
    _close_rings(bm, rings, *caps)
    return finish(bm, name, material, smooth, bvh)

def sweep(points, section_fn, name, material=None, smooth=True, caps=(True, True)):
    """Generic sweep: points is a list of (centre Vector, right Vector, up Vector, params) and section_fn(params) -> list of (r, u) 2D points."""
    bm = bmesh.new(); rings = []
    for (c, rt, up, prm) in points:
        rings.append([bm.verts.new(c + rt * a + up * b) for (a, b) in section_fn(prm)])
    _close_rings(bm, rings, *caps)
    return finish(bm, name, material, smooth)

# ---------------------------------------------------------------- aerofoils
def foil_xz(chord, t, n=14, camber=0.0, tail_open=0.0):
    """Aerofoil outline (x from the leading edge back, z), top then bottom, n points per surface."""
    xs = [(1 - math.cos(PI * i / n)) / 2 for i in range(n + 1)]
    yt = lambda x: 5 * t * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 - 0.1015 * x ** 4)
    yc = lambda x: camber * 4 * x * (1 - x) if camber else 0.0
    up = [(chord * x, chord * (yc(x) + yt(x))) for x in xs]
    lo = [(chord * x, chord * (yc(x) - yt(x))) for x in reversed(xs[1:-1])]
    return up + lo

def loft_sections(secs, material, name, smooth=True, bvh=False):
    """secs: list of lists of 3D points (all the same length), closed at both ends."""
    bm = bmesh.new(); rings = [[bm.verts.new(p) for p in s] for s in secs]
    _close_rings(bm, rings)
    return finish(bm, name, material, smooth, bvh)

def densify(secs, n=3, keys=None):
    out = []
    for a, b in zip(secs, secs[1:]):
        for i in range(n):
            u = i / n; out.append({k: a[k] + (b[k] - a[k]) * u for k in a})
    out.append(dict(secs[-1])); return out

def wing(secs, material, name, n_foil=14, subdiv=3, smooth=True, bvh=False):
    """secs: dicts with y, xle, chord, t, z (+ optional tw twist in radians about the quarter chord, camber). The leading edge points to +X."""
    ss = []
    for s in densify(secs, subdiv):
        pts = foil_xz(s['chord'], s['t'], n_foil, s.get('camber', 0.0))
        tw = s.get('tw', 0.0); ct, st = math.cos(tw), math.sin(tw); c4 = s['chord'] * 0.25; ss.append([])
        for (x, z) in pts:
            dx, dz = x - c4, z
            ss[-1].append((s['xle'] - (c4 + dx * ct + dz * st), s['y'], s['z'] + dz * ct - dx * st))
    return loft_sections(ss, material, name, smooth, bvh)

def fin(secs, material, name, n_foil=14, subdiv=3, smooth=True):
    """secs: dicts with z, xle, chord, t, (optional y offset). A vertical surface in the XZ plane."""
    ss = []
    for s in densify(secs, subdiv):
        pts = foil_xz(s['chord'], s['t'], n_foil)
        ss.append([(s['xle'] - x, s.get('y', 0.0) + y, s['z']) for (x, y) in pts])
    return loft_sections(ss, material, name, smooth)

# ---------------------------------------------------------------- bodies of revolution and little parts
def revolve(profile, p0, direction, seg=16, material=None, name='rev', smooth=True, cap_a=True, cap_b=True, roll=0.0):
    """profile (r, t) bottom to top along `direction` starting at p0."""
    o = lathe(profile, seg, material, name, cap_top=cap_b, cap_bottom=cap_a, smooth=smooth)
    d = Vector(direction).normalized()
    q = d.to_track_quat('Z', 'Y')
    M = Matrix.Translation(Vector(p0)) @ q.to_matrix().to_4x4() @ Matrix.Rotation(roll, 4, 'Z')
    o.data.transform(M); o.data.update()
    return o

def tube(p0, p1, r, seg=8, material=None, name='tube', r1=None):
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    return revolve([(r, 0.0), (r if r1 is None else r1, d.length)], p0, d, seg, material, name, smooth=True)

def rbox(size, loc, material=None, bevel=0.02, rot=(0, 0, 0), name='rbox', seg=2):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.Diagonal(Vector((size[0], size[1], size[2], 1))), verts=bm.verts)
    if bevel > 0: bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=bevel, segments=seg, affect='EDGES')
    bmesh.ops.transform(bm, matrix=xf(loc, rot), verts=bm.verts)
    o = obj_from_bm(bm, name, material, True)
    return o

def tyre(x, y, z, r, w, material_tyre, material_hub, name='wheel', axis='Y', seg=22):
    """A wheel with a rounded tyre, rim and hub. Axle along Y (default)."""
    prof_t = [(r * 0.62, -w / 2), (r * 0.9, -w / 2 * 0.98), (r * 0.99, -w / 2 * 0.6), (r, -w * 0.18), (r, w * 0.18), (r * 0.99, w / 2 * 0.6), (r * 0.9, w / 2 * 0.98), (r * 0.62, w / 2)]
    t = lathe(prof_t, seg, material_tyre, name, cap_top=False, cap_bottom=False, smooth=True)
    prof_h = [(0.0, -w * 0.42), (r * 0.55, -w * 0.42), (r * 0.6, -w * 0.3), (r * 0.6, w * 0.3), (r * 0.55, w * 0.42), (0.0, w * 0.42)]
    h = lathe(prof_h, seg, material_hub, name + 'hub', smooth=True)
    hc = lathe([(0.0, w * 0.46), (r * 0.18, w * 0.46), (r * 0.18, w * 0.52)], 10, material_hub, name + 'cap', smooth=True)
    for o in (t, h, hc):
        o.data.transform(Matrix.Rotation(-PI / 2, 4, 'X')); o.data.transform(Matrix.Translation((x, y, z)))
    return join([t, h, hc], name)

# ---------------------------------------------------------------- surface patches (windows, panels, bezels)
def rrect(w, h, r, nc=4):
    """Rounded rectangle outline (u, v), CCW, w x h, corner radius r."""
    r = min(r, w / 2 - 1e-4, h / 2 - 1e-4); pts = []
    for (cx, cy, a0) in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, PI / 2), (-w / 2 + r, -h / 2 + r, PI), (w / 2 - r, -h / 2 + r, 3 * PI / 2)):
        for i in range(nc + 1):
            a = a0 + (PI / 2) * i / nc; pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def circle_pts(r, n=20):
    return [(r * math.cos(2 * PI * i / n), r * math.sin(2 * PI * i / n)) for i in range(n)]

def offset_outline(pts, d):
    """Grow (d > 0) or shrink a star-shaped outline about its centroid by a distance (approximate: scales radially)."""
    cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts); out = []
    for (x, y) in pts:
        dx, dy = x - cx, y - cy; L = math.hypot(dx, dy) or 1e-9
        out.append((cx + dx * (L + d) / L, cy + dy * (L + d) / L))
    return out

def hit(bvh, origin, direction):
    loc, nor, idx, dist = bvh.ray_cast(origin, direction)
    return (loc, nor) if loc is not None else (None, None)

def _project(bvh, c, ex, ey, rd, u, v, off, back=8.0):
    o = c + ex * u + ey * v - rd * back
    loc, nor = hit(bvh, o, rd)
    if loc is None: return None
    return loc + nor * off

def patch(bvh, c, ex, ey, rd, outline, off, K=2, material=None, name='patch', smooth=True):
    """A surface patch following the skin. outline is a list of (u, v) in the plane (c, ex, ey); the patch is projected along rd onto the BVH
    and lifted by `off` along the surface normal. K concentric rings plus a centre point."""
    c, ex, ey, rd = Vector(c), Vector(ex).normalized(), Vector(ey).normalized(), Vector(rd).normalized()
    cx = sum(p[0] for p in outline) / len(outline); cy = sum(p[1] for p in outline) / len(outline)
    bm = bmesh.new(); rings = []
    for k in range(K):
        s = 1 - k / K; ring = []
        for (u, v) in outline:
            p = _project(bvh, c, ex, ey, rd, cx + (u - cx) * s, cy + (v - cy) * s, off)
            ring.append(bm.verts.new(p if p is not None else c))
        rings.append(ring)
    centre = bm.verts.new(_project(bvh, c, ex, ey, rd, cx, cy, off) or c)
    n = len(outline)
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n; bm.faces.new((a[i], a[j], b[j], b[i]))
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((rings[-1][i], rings[-1][j], centre))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return obj_from_bm(bm, name, material, smooth)

def bezel(bvh, c, ex, ey, rd, inner, outer, off_in, off_out, material, name='bezel'):
    """A raised frame between two outlines with the same point count: the lip at off_in, the foot at off_out."""
    c, ex, ey, rd = Vector(c), Vector(ex).normalized(), Vector(ey).normalized(), Vector(rd).normalized()
    bm = bmesh.new(); a = []; b = []
    for (u, v) in inner:
        p = _project(bvh, c, ex, ey, rd, u, v, off_in); a.append(bm.verts.new(p if p is not None else c))
    for (u, v) in outer:
        p = _project(bvh, c, ex, ey, rd, u, v, off_out); b.append(bm.verts.new(p if p is not None else c))
    n = len(a)
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return obj_from_bm(bm, name, material, True)

def window(bvh, c, ex, ey, rd, w, h, r, glass, frame, fw=0.035, sink=0.012, lip=0.03, K=2, round_=False, name='win'):
    """A recessed-looking window: a glass patch under a raised rubber bezel."""
    if round_:
        inner = circle_pts(w / 2, 24); outer = circle_pts(w / 2 + fw, 24)
    else:
        inner = rrect(w, h, r); outer = rrect(w + 2 * fw, h + 2 * fw, r + fw)
    K = max(K, 4 if max(w, h) > 0.6 else 3 if max(w, h) > 0.38 else 2)
    g = patch(bvh, c, ex, ey, rd, inner, sink, K, glass, name + 'g')
    f = bezel(bvh, c, ex, ey, rd, inner, outer, lip, 0.002, frame, name + 'f')
    return [g, f]

def side_frame(side):
    """(ray direction, in-plane x axis, in-plane up axis) for the starboard (-1) or port (+1) side."""
    return (Vector((0, -side, 0)), Vector((1, 0, 0)), Vector((0, 0, 1)))

# ---------------------------------------------------------------- UVs
def apply_uv(obj, rule):
    """rule(centre, normal) -> (Region, fn(co) -> (a, b)) for each polygon; sets the active UV layer per loop."""
    me = obj.data
    uvl = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        reg, ab = rule(p.center, p.normal)
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            a, b = ab(co)
            uvl.data[li].uv = reg.uv(a, b)
    return obj

def solid_uv(obj, px):
    uvl = obj.data.uv_layers.get('UVMap') or obj.data.uv_layers.new(name='UVMap')
    u, v = px[0] / LY.ATLAS, 1 - px[1] / LY.ATLAS
    for d in uvl.data: d.uv = (u, v)
    return obj

def hull_rule(R, ext_dir_x=0.7):
    """Rule for a fuselage-like shell: top, belly or a side by face direction; the nose/tail ends fall onto the nearest side."""
    xz = lambda co: (co.x, co.z); xy = lambda co: (co.x, co.y)
    def rule(c, n):
        if n.z > 0.62 and abs(n.z) > abs(n.y): return R['top'], xy
        if n.z < -0.62 and abs(n.z) > abs(n.y): return R['bot'], xy
        return (R['pt'] if c.y > 0 else R['sb']), xz
    return rule

# ---------------------------------------------------------------- materials
def tex_mat(name, img_path, normal_path=None, rough=0.5, metal=0.0, nstr=1.0, mr_path=None):
    key = ('tex', name, img_path, normal_path, rough, metal)
    if key in MATS: return MATS[key]
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    it = nt.nodes.new('ShaderNodeTexImage'); it.image = bpy.data.images.load(img_path); it.image.colorspace_settings.name = 'sRGB'; it.interpolation = 'Linear'
    nt.links.new(it.outputs['Color'], b.inputs['Base Color'])
    if normal_path and os.path.exists(normal_path):
        nm = nt.nodes.new('ShaderNodeTexImage'); nm.image = bpy.data.images.load(normal_path); nm.image.colorspace_settings.name = 'Non-Color'
        nn = nt.nodes.new('ShaderNodeNormalMap'); nn.inputs['Strength'].default_value = nstr
        nt.links.new(nm.outputs['Color'], nn.inputs['Color']); nt.links.new(nn.outputs['Normal'], b.inputs['Normal'])
    MATS[key] = m
    return m

def flat_mat(name, color, rough=0.5, metal=0.0, spec=0.5, alpha=1.0, coat=0.0):
    m = mat(name, color, rough, metal, alpha=alpha)
    return m

def solid_region(px):
    return LY.Region('solid', (px[0] - 6, px[1] - 6, px[0] + 6, px[1] + 6), (0, 1), (0, 1))
