"""Aircraft for Squall Cove, modelled from reference photographs and three-view drawings (Wikimedia Commons).
  cormorant()  CH-149 Cormorant (AgustaWestland AW101), the Canadian search and rescue helicopter.
               Figures used: length 22.81 m with rotors turning, height 6.65 m, main rotor 18.59 m (five blades), three engines. SAR yellow with red trim, red sponsons.
  cl415()      Canadair CL-415 amphibious water bomber.
               Figures used: length 19.82 m, span 28.60 m, height 8.98 m, two PW123AF turboprops with 3.97 m four-blade propellers, high wing on a pylon, tip floats,
               swept fin with a mid-mounted tailplane and tip winglets. Livery after the Newfoundland and Labrador aircraft: orange, green stripe, grey hull, white fin bands.
Metres, Z up, nose toward +X, origin on the centreline at keel level. Animated parts (rotors, propellers) are separate objects whose ORIGIN IS THE PIVOT, named <key>_<part>N.
"""
import math, bmesh
from mathutils import Vector, Matrix
from pg_core import *

ANIM = []

def place_part(o, p, name):
    """The part was built around its own origin; put that origin at the pivot p."""
    o.location = Vector(p); o.name = name; ANIM.append(o); return o

def lerp_station(st, x, key):
    st = sorted(st, key=lambda s: s['x'])
    if x <= st[0]['x']: return st[0][key]
    if x >= st[-1]['x']: return st[-1][key]
    for a, b in zip(st, st[1:]):
        if a['x'] <= x <= b['x']:
            u = (x - a['x']) / (b['x'] - a['x']); return a[key] + (b[key] - a[key]) * u

def resample(pts, n):
    L = [0.0]
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]; L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    out = []
    for k in range(n):
        d = L[-1] * k / n
        for i in range(len(pts)):
            if L[i] <= d <= L[i + 1] + 1e-9:
                u = (d - L[i]) / max(L[i + 1] - L[i], 1e-9); a, b = pts[i], pts[(i + 1) % len(pts)]; out.append((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)); break
    return out

def refine(st, step=0.25):
    st = sorted(st, key=lambda q: q['x']); out = []
    for a, b in zip(st, st[1:]):
        n = max(1, int(round((b['x'] - a['x']) / step)))
        for i in range(n):
            u = i / n; u2 = u * u * (3 - 2 * u) * 0.5 + u * 0.5
            d = {k: a[k] + (b[k] - a[k]) * u2 for k in ('zt', 'zb', 'w')}; d['x'] = a['x'] + (b['x'] - a['x']) * u; out.append(d)
    out.append(dict(st[-1])); return out

def ring_hull(zt, zb, w):
    h = zt - zb
    r = [(0, zt), (0.62 * w, zt - 0.04 * h), (0.97 * w, zt - 0.28 * h), (w, zt - 0.50 * h), (0.9 * w, zt - 0.72 * h), (0.55 * w, zt - 0.92 * h), (0, zb)]
    return resample(r + [(-y, z) for (y, z) in reversed(r[1:-1])], 44)

def ring_round(zt, zb, w, p=3.6, n=44):
    zc, hh = (zt + zb) / 2, (zt - zb) / 2; out = []
    for i in range(n):
        a = 2 * math.pi * i / n; c, s = math.cos(a), math.sin(a)
        out.append((w * math.copysign(abs(c) ** (2 / p), c), zc + hh * math.copysign(abs(s) ** (2 / p), s)))
    return out

def _close(bm, rings, cap=True):
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n; bm.faces.new((a[i], a[j], b[j], b[i]))
    if cap:
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

def loft(stations, ring_fn, material, name, smooth=True, off=(0.0, 0.0)):
    """Stations (x, zt, zb, w) along X. All rings share a vertex count. off shifts the whole body sideways and up."""
    bm = bmesh.new(); rings = []
    for s in refine(stations):
        pts = ring_fn(s['zt'], s['zb'], max(s['w'], 0.02)); rings.append([bm.verts.new((s['x'], y + off[0], z + off[1])) for (y, z) in pts])
    _close(bm, rings); return obj_from_bm(bm, name, material, smooth)

def foil_pts(chord, t, n=12):
    """A symmetric aerofoil outline (NACA four-digit thickness), leading edge at x = 0. Returns (x, z) going over the top and back underneath."""
    xs = [(1 - math.cos(math.pi * i / n)) / 2 for i in range(n + 1)]
    yt = lambda x: 5 * t * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 - 0.1036 * x ** 4)
    up = [(chord * x, chord * yt(x)) for x in xs]; lo = [(chord * x, -chord * yt(x)) for x in reversed(xs[1:-1])]
    return up + lo

def densify(secs, n=3):
    out = []
    for a, b in zip(secs, secs[1:]):
        for i in range(n):
            u = i / n; out.append({k: a[k] + (b[k] - a[k]) * u for k in a})
    out.append(dict(secs[-1])); return out

def wing_loft(secs, material, name, smooth=True):
    """secs: dicts with y, xle, chord, t (thickness ratio), z. A wing from root to tip."""
    bm = bmesh.new(); rings = []
    for s in densify(secs):
        rings.append([bm.verts.new((s['xle'] - x, s['y'], s['z'] + z)) for (x, z) in foil_pts(s['chord'], s['t'])])
    _close(bm, rings); return obj_from_bm(bm, name, material, smooth)

def fin_loft(secs, material, name, smooth=True):
    """secs: dicts with z, xle, chord, t. A vertical surface on the centreline."""
    bm = bmesh.new(); rings = []
    for s in densify(secs):
        rings.append([bm.verts.new((s['xle'] - x, y, s['z'])) for (x, y) in foil_pts(s['chord'], s['t'])])
    _close(bm, rings); return obj_from_bm(bm, name, material, smooth)

def prism(poly_xy, z0, z1, material, name, bevel=0.0):
    bm = bmesh.new(); a = [bm.verts.new((x, y, z0)) for (x, y) in poly_xy]; b = [bm.verts.new((x, y, z1)) for (x, y) in poly_xy]; n = len(a)
    bm.faces.new(list(reversed(a))); bm.faces.new(b)
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if bevel > 0: bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=bevel, segments=2, affect='EDGES')
    return obj_from_bm(bm, name, material)

def fine(o, cuts=2):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    bm.to_mesh(o.data); bm.free(); o.data.update()

def fine_nose(o, xmin, cuts=3):
    bm = bmesh.new(); bm.from_mesh(o.data)
    ed = [e for e in bm.edges if all(v.co.x > xmin for v in e.verts)]
    bmesh.ops.subdivide_edges(bm, edges=ed, cuts=cuts, use_grid_fill=True)
    bm.to_mesh(o.data); bm.free(); o.data.update()

def cut(o, planes):
    """Slice the mesh along axis planes [(axis, value)] so painted regions get clean straight edges."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    for ax, v in planes:
        no = [0, 0, 0]; no[ax] = 1; co = [0, 0, 0]; co[ax] = v
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
    bm.to_mesh(o.data); bm.free(); o.data.update()

def paint(o, material, pred):
    me = o.data; me.materials.append(material); idx = len(me.materials) - 1
    for p in me.polygons:
        c = p.center; n = p.normal
        if pred(c.x, c.y, c.z, n.x, n.y, n.z): p.material_index = idx

def along_x(profile, x0, y, z, seg, material, name):
    """A body of revolution lying along X: profile is (radius, distance from x0), nose toward +X."""
    o = lathe(profile, seg, material, name, smooth=True); o.data.transform(Matrix.Rotation(math.pi / 2, 4, 'Y')); o.data.transform(Matrix.Translation((x0, y, z))); return o

def wheel(x, y, z, r, w, material, name='wheel'):
    return cyl(r, r, w, 18, loc=(x, y - w / 2, z), rot=(-math.pi / 2, 0, 0), material=material, name=name)

# ---------------------------------------------------------------- CH-149 Cormorant
def lofted_sponson(s, material):
    return loft([dict(x=-1.4, zt=0.42, zb=-0.38, w=0.3), dict(x=-0.4, zt=0.55, zb=-0.5, w=0.72), dict(x=2.0, zt=0.58, zb=-0.55, w=0.8), dict(x=3.4, zt=0.52, zb=-0.46, w=0.68), dict(x=4.1, zt=0.3, zb=-0.28, w=0.3)],
                lambda zt, zb, w: ring_round(zt, zb, w, 3.0, 24), material, 'sponson', off=(s * 1.68, 1.55))

def cormorant(name='cormorant_hull'):
    ANIM.clear()
    Y, RED, DARK, GREY, WHITE = '#efb81c', '#c8262b', '#11171f', '#6d747b', '#f1efe9'
    my, mr, md, mg, mw = mat('sar_yellow', Y, 0.38), mat('sar_red', RED, 0.42), mat('sar_dark', DARK, 0.18, 0.2), mat('sar_grey', GREY, 0.5, 0.3), mat('sar_white', WHITE, 0.45)
    st = [dict(x=8.9, zt=2.7, zb=1.9, w=0.5), dict(x=8.4, zt=3.25, zb=1.55, w=1.0), dict(x=7.5, zt=3.58, zb=1.28, w=1.34), dict(x=6.0, zt=3.78, zb=1.05, w=1.47), dict(x=4.2, zt=3.88, zb=0.97, w=1.56),
          dict(x=0.0, zt=3.92, zb=0.95, w=1.6), dict(x=-4.0, zt=3.86, zb=1.0, w=1.52), dict(x=-6.2, zt=3.7, zb=1.3, w=1.28), dict(x=-8.0, zt=3.78, zb=2.1, w=0.85), dict(x=-9.6, zt=4.2, zb=3.2, w=0.45), dict(x=-10.3, zt=4.7, zb=3.8, w=0.3)]
    parts = []
    fus = loft(st, lambda zt, zb, w: ring_round(zt, zb, w, 4.4, 34), my, 'fus')
    fine_nose(fus, 6.0); cut(fus, [(2, 2.0), (2, 2.45), (2, 2.85), (2, 3.5), (0, 5.7), (0, 7.4), (0, 8.1)])
    paint(fus, mr, lambda x, y, z, nx, ny, nz: 3.6 < x < 7.4 and nz > 0.5 and z > 3.3)                          # red cockpit roof
    paint(fus, mr, lambda x, y, z, nx, ny, nz: -9.3 < x < -8.0)                                                  # red band round the tail pylon
    paint(fus, mr, lambda x, y, z, nx, ny, nz: 2.38 < z < 2.56 and abs(ny) > 0.55 and -4.4 < x < 5.2)           # the thin red stripe along the cabin
    parts.append(fus)
    W = lambda x: lerp_station(st, x, 'w')
    paint(fus, md, lambda x, y, z, nx, ny, nz: x > 7.4 and 2.85 < z < 3.5 and nx > 0.3)                       # windscreen, painted onto the nose so it follows the curve
    paint(fus, md, lambda x, y, z, nx, ny, nz: 5.7 < x < 7.4 and 2.85 < z < 3.5 and abs(ny) > 0.45)           # cockpit side windows
    paint(fus, md, lambda x, y, z, nx, ny, nz: x > 8.1 and 2.0 < z < 2.45 and nx > 0.5)                         # chin windows
    for s in (1, -1):                                                                                            # cabin windows and the forward sliding door
        for xx in (2.9, 1.8, 0.7, -0.4, -1.5, -2.6):
            parts.append(box((0.5, 0.06, 0.45), (xx, s * (W(xx) + 0.012), 3.0), material=md, bevel=0.03, name='win'))
        dx, dz, dw, dh = 3.9, 2.15, 1.25, 1.75
        for (cx, cz, sx, sz) in ((dx, dz + dh / 2, dw, 0.05), (dx, dz - dh / 2, dw, 0.05), (dx - dw / 2, dz, 0.05, dh), (dx + dw / 2, dz, 0.05, dh)):
            parts.append(box((sx, 0.05, sz), (cx, s * (W(dx) + 0.01), cz), material=mg, name='doorframe'))
        parts.append(box((0.5, 0.06, 0.55), (dx, s * (W(dx) + 0.02), 2.75), material=md, bevel=0.07, name='doorwin'))
    for s in (1, -1):                                                                                            # red sponsons with the main gear
        parts.append(lofted_sponson(s, mr))
        parts.append(cyl(0.12, 0.12, 0.65, 8, loc=(0.9, s * 1.8, 0.7), material=mg, name='strut'))
        parts.append(wheel(0.9, s * 1.8, 0.62, 0.62, 0.36, md, 'mainwheel')); parts.append(wheel(0.9, s * 1.8, 0.62, 0.3, 0.42, mg, 'hub'))
        parts.append(cyl(0.5, 0.5, 0.04, 20, loc=(1.2, s * 2.3, 1.7), rot=(-math.pi / 2, 0, 0), material=mw, name='roundel'))
    parts.append(cyl(0.1, 0.1, 0.9, 8, loc=(7.0, 0, 0.55), material=mg, name='nosestrut')); parts.append(wheel(7.0, 0, 0.45, 0.43, 0.3, md, 'nosewheel')); parts.append(wheel(7.0, 0, 0.45, 0.2, 0.34, mg, 'nosehub'))
    parts.append(ico(0.34, 2, (8.15, 0, 1.45), md, 'sensor'))                                                   # electro-optical turret
    parts.append(box((0.9, 0.03, 0.03), (8.0, 0, 3.45), material=mg, name='wirecutter'))
    parts.append(box((5.4, 1.5, 0.5), (-1.2, 0, 4.1), material=my, bevel=0.2, name='doghouse'))                   # gearbox fairing and two engines with intakes
    for s in (1, -1):
        parts.append(loft([dict(x=-3.6, zt=0.26, zb=-0.28, w=0.24), dict(x=-2.5, zt=0.38, zb=-0.34, w=0.42), dict(x=-0.4, zt=0.42, zb=-0.36, w=0.5), dict(x=0.9, zt=0.38, zb=-0.36, w=0.48), dict(x=1.4, zt=0.32, zb=-0.3, w=0.42)],
                          lambda zt, zb, w: ring_round(zt, zb, w, 3.0, 24), my, 'engine', off=(s * 0.82, 4.2)))
        parts.append(box((0.08, 0.46, 0.4), (1.4, s * 0.82, 4.2), material=md, name='intake'))
        parts.append(cyl(0.15, 0.15, 0.7, 10, loc=(-4.0, s * 0.62, 4.24), rot=(0, math.pi / 2, 0), material=mg, name='exhaust'))
    parts.append(cyl(0.16, 0.16, 0.9, 10, loc=(-3.7, 0, 3.98), rot=(0, math.pi / 2, 0), material=mg, name='exhaust'))
    parts.append(box((0.55, 0.6, 0.5), (1.4, -1.5, 3.95), material=mg, bevel=0.1, name='hoistbox')); parts.append(rod((1.4, -1.55, 3.7), (1.4, -2.3, 3.7), 0.09, 8, mg, 'hoistarm'))     # the rescue hoist
    parts.append(fin_loft([dict(z=3.8, xle=-8.4, chord=2.2, t=0.1), dict(z=4.6, xle=-9.4, chord=1.95, t=0.1), dict(z=5.4, xle=-10.3, chord=1.5, t=0.09), dict(z=6.05, xle=-10.9, chord=1.05, t=0.08)], my, 'fin'))
    parts.append(cyl(0.22, 0.22, 0.5, 10, loc=(-10.4, -0.12, 5.45), rot=(-math.pi / 2, 0, 0), material=mg, name='tgb'))
    parts.append(wing_loft([dict(y=-1.7, xle=-9.0, chord=1.0, t=0.1, z=3.75), dict(y=1.7, xle=-9.0, chord=1.0, t=0.1, z=3.75)], my, 'tailplane'))
    parts.append(box((0.04, 2.2, 0.04), (-6.4, 0, 1.25), material=mg, name='rampline'))
    for (ax, az, bx, bz) in ((2.6, 3.9, 2.25, 4.45), (-2.0, 3.85, -2.5, 4.35), (6.6, 3.6, 6.35, 3.95)): parts.append(rod((ax, 0, az), (bx, 0, bz), 0.03, 4, md, 'aerial'))
    parts.append(cyl(0.27, 0.34, 1.55, 12, loc=(-0.8, 0, 4.35), material=mg, name='mast')); parts.append(cyl(0.5, 0.5, 0.26, 16, loc=(-0.8, 0, 5.8), material=md, name='hub'))
    for i in range(5):                                                                                          # the five blade sleeves on the hub
        a = i * 2 * math.pi / 5; parts.append(rod((-0.8, 0, 5.93), (-0.8 + math.cos(a) * 0.9, math.sin(a) * 0.9, 5.93), 0.1, 6, md, 'sleeve'))
    hull = join(parts, name)
    blades = []                                                                                                  # five blades with the swept, broadened tip, red tips
    for i in range(5):
        a = i * 2 * math.pi / 5
        bl = prism([(0.9, -0.2), (7.9, -0.28), (8.6, -0.33), (9.2, -0.44), (9.35, 0.0), (9.0, 0.36), (8.6, 0.33), (7.9, 0.28), (0.9, 0.2)], -0.025, 0.025, md, 'blade')
        paint(bl, mr, lambda x, y, z, nx, ny, nz: x > 8.5)
        bl.data.transform(Matrix.Rotation(a, 4, 'Z')); blades.append(bl)
    blades.append(cyl(9.35, 9.35, 0.01, 48, loc=(0, 0, -0.005), material=mat('rotordisc', '#ffffff', 0.5, alpha=0.1), name='disc'))
    place_part(join(blades, 'rotor'), (-0.8, 0, 6.05), 'cormorant_rotor0')
    tb = []                                                                                                      # tail rotor: four blades, 4.0 m across, turning about the lateral axis
    for i in range(4):
        a = i * math.pi / 2; b = box((0.05, 0.28, 1.95), (0, 0, 0), material=md, bevel=0.01, name='tb'); b.data.transform(Matrix.Translation((0, 0, 1.05))); b.data.transform(Matrix.Rotation(a, 4, 'Y')); tb.append(b)
    ht = cyl(0.2, 0.2, 0.3, 10, loc=(0, -0.15, 0), rot=(-math.pi / 2, 0, 0), material=mg, name='tht'); tb.append(ht)
    place_part(join(tb, 'tailrotor'), (-10.4, -0.5, 5.45), 'cormorant_tail0')
    place_part(box((0.2, 0.2, 0.2), (0, 0, 0), material=md, name='winch'), (1.4, -2.3, 3.5), 'cormorant_winch0')
    return hull

# ---------------------------------------------------------------- Canadair CL-415
def cl415(name='cl415_hull'):
    ANIM.clear()
    OR, WH, GR, GH, DK, GY = '#e2571a', '#f1efe9', '#1f6b49', '#8d949b', '#11171f', '#6d747b'
    mo, mw, mgreen, mh, md, mg = mat('cl_orange', OR, 0.38), mat('cl_white', WH, 0.45), mat('cl_green', GR, 0.45), mat('cl_hull', GH, 0.5, 0.2), mat('cl_dark', DK, 0.18, 0.2), mat('cl_grey', GY, 0.5, 0.3)
    st = [dict(x=9.9, zt=2.2, zb=1.3, w=0.4), dict(x=9.3, zt=2.9, zb=0.9, w=0.85), dict(x=8.4, zt=3.45, zb=0.5, w=1.28), dict(x=7.0, zt=3.78, zb=0.12, w=1.52), dict(x=4.5, zt=3.82, zb=0.0, w=1.62),
          dict(x=0.0, zt=3.85, zb=0.0, w=1.64), dict(x=-3.5, zt=3.8, zb=0.0, w=1.6), dict(x=-6.0, zt=3.72, zb=0.1, w=1.48), dict(x=-8.0, zt=3.72, zb=0.7, w=1.15), dict(x=-9.3, zt=3.85, zb=1.4, w=0.7), dict(x=-9.9, zt=3.95, zb=1.8, w=0.4)]
    parts = []
    fus = loft(st, ring_hull, mo, 'fus')
    fine_nose(fus, 6.8); cut(fus, [(2, 2.75), (2, 3.6), (2, 2.8), (2, 3.55), (0, 6.6), (0, 8.0), (0, 8.4)])
    paint(fus, mh, lambda x, y, z, nx, ny, nz: z < 0.62)                                              # grey planing bottom with the chine
    paint(fus, mgreen, lambda x, y, z, nx, ny, nz: 0.62 <= z < 1.55 and abs(ny) > 0.3)                 # green lower side stripe
    parts.append(fus)
    W = lambda x: lerp_station(st, x, 'w')
    paint(fus, md, lambda x, y, z, nx, ny, nz: x > 8.0 and 2.75 < z < 3.6 and nx > 0.15 and nz < 0.85)       # windscreen, painted onto the nose so it follows the curve
    paint(fus, md, lambda x, y, z, nx, ny, nz: 6.6 < x < 8.4 and 2.8 < z < 3.55 and abs(ny) > 0.4)         # cockpit side windows
    for s in (1, -1):
        dx, dz = -1.4, 2.1
        for (cx, cz, sx, sz) in ((dx, dz + 1.0, 1.1, 0.05), (dx, dz - 1.0, 1.1, 0.05), (dx - 0.55, dz, 0.05, 2.0), (dx + 0.55, dz, 0.05, 2.0)): parts.append(box((sx, 0.05, sz), (cx, s * (W(dx) + 0.01), cz), material=mg, name='doorframe'))
        parts.append(box((0.5, 0.06, 0.5), (dx, s * (W(dx) + 0.02), 2.6), material=md, bevel=0.08, name='doorwin'))
        parts.append(cyl(0.2, 0.2, 0.05, 12, loc=(2.2, s * W(2.2), 2.65), rot=(-math.pi / 2, 0, 0), material=md, name='porthole'))
        parts.append(cyl(0.2, 0.2, 0.05, 12, loc=(-5.0, s * W(-5.0), 2.65), rot=(-math.pi / 2, 0, 0), material=md, name='porthole'))
    parts.append(box((4.8, 2.0, 1.7), (0.7, 0, 4.25), material=mo, bevel=0.4, name='pylon'))
    secs = [dict(y=0.0, xle=3.2, chord=3.65, t=0.15, z=5.1), dict(y=3.6, xle=3.2, chord=3.5, t=0.14, z=5.1), dict(y=9.0, xle=3.2, chord=3.2, t=0.13, z=5.1), dict(y=14.3, xle=3.2, chord=2.9, t=0.12, z=5.1)]
    for s in (1, -1):                                                                                  # the wing: real aerofoil sections, 3.65 m chord at the root to 2.9 m at the tip
        w = wing_loft([dict(y=s * q['y'], xle=q['xle'], chord=q['chord'], t=q['t'], z=q['z']) for q in secs], mo, 'wing')
        paint(w, mw, lambda x, y, z, nx, ny, nz: abs(y) > 13.4)
        parts.append(w)
    for s in (1, -1):
        eng = loft([dict(x=-1.3, zt=0.3, zb=-0.28, w=0.28), dict(x=-0.3, zt=0.62, zb=-0.56, w=0.52), dict(x=1.4, zt=0.78, zb=-0.8, w=0.64), dict(x=3.2, zt=0.78, zb=-0.8, w=0.62), dict(x=4.2, zt=0.66, zb=-0.66, w=0.52), dict(x=4.75, zt=0.5, zb=-0.5, w=0.42)],
                   lambda zt, zb, w: ring_round(zt, zb, w, 2.8, 28), mo, 'nacelle', off=(s * 3.6, 5.15))
        paint(eng, mg, lambda x, y, z, nx, ny, nz: x > 4.3)                                              # the intake lip
        parts.append(eng)
        parts.append(box((1.0, 0.36, 0.3), (-0.2, s * 3.6, 6.0), material=mg, bevel=0.1, name='exhaust'))      # exhaust stack on top
        parts.append(box((3.6, 0.9, 0.6), (1.2, s * 3.6, 4.35), material=mo, bevel=0.28, name='underpod'))   # the fairing under the wing
        parts.append(rod((1.1, s * 14.3, 4.95), (1.1, s * 14.3, 3.05), 0.1, 8, mg, 'floatstrut'))
        parts.append(rod((0.5, s * 14.3, 4.95), (0.9, s * 14.3, 3.05), 0.06, 6, mg, 'floatbrace'))
        parts.append(along_x([(0.0, 0.0), (0.34, 0.3), (0.44, 1.1), (0.34, 2.1), (0.0, 2.6)], 0.0, s * 14.3, 2.7, 14, mw, 'tipfloat'))
        parts.append(box((0.55, 0.45, 1.1), (-0.5, s * 1.95, 0.75), material=mg, bevel=0.15, name='gearleg')); parts.append(wheel(-0.5, s * 1.95, 0.05, 0.62, 0.4, md, 'mainwheel')); parts.append(wheel(-0.5, s * 1.95, 0.05, 0.3, 0.46, mg, 'hub'))
    parts.append(box((0.3, 0.3, 1.0), (7.6, 0, 0.7), material=mg, name='nosegear')); parts.append(wheel(7.6, 0, 0.25, 0.42, 0.3, md, 'nosewheel'))
    fin = fin_loft([dict(z=3.8, xle=-7.4, chord=2.6, t=0.1), dict(z=5.5, xle=-8.0, chord=2.2, t=0.1), dict(z=7.2, xle=-8.3, chord=1.8, t=0.09), dict(z=8.98, xle=-8.7, chord=1.55, t=0.08)], mo, 'fin')
    paint(fin, mw, lambda x, y, z, nx, ny, nz: 5.0 < z < 5.9 or 7.0 < z < 7.9)                          # the white bands on the fin
    parts.append(fin)
    for s in (1, -1):                                                                                  # tailplane with tip winglets
        parts.append(wing_loft([dict(y=0.0, xle=-7.5, chord=2.5, t=0.11, z=5.7), dict(y=s * 3.0, xle=-7.7, chord=2.2, t=0.1, z=5.7), dict(y=s * 5.6, xle=-8.3, chord=1.9, t=0.09, z=5.7)], mo, 'tailplane'))
        parts.append(box((1.3, 0.12, 1.4), (-9.2, s * 5.6, 6.35), material=mw, bevel=0.05, name='winglet'))
    hull = join(parts, name)
    for k, s in enumerate((-1, 1)):                                                                       # four-blade propellers, 3.97 m across, with a spinner
        bl = []
        for i in range(4):
            a = i * math.pi / 2; b = prism([(-0.1, 0.17), (0.1, 0.24), (0.1, -0.1), (-0.1, -0.16)], 0.34, 1.97, md, 'pb'); b.data.transform(Matrix.Rotation(a, 4, 'X')); bl.append(b)
        sp = lathe([(0.0, 0.0), (0.32, 0.05), (0.34, 0.4), (0.14, 0.82), (0.0, 0.95)], 16, mw, 'spinner', smooth=True); sp.data.transform(Matrix.Rotation(math.pi / 2, 4, 'Y')); bl.append(sp); bl.append(cyl(1.98, 1.98, 0.01, 32, loc=(0.0, 0, 0), rot=(0, math.pi / 2, 0), material=mat('propdisc', '#ffffff', 0.5, alpha=0.1), name='disc'))
        place_part(join(bl, 'prop'), (4.75, s * 3.6, 5.15), f'cl415_prop{k}')
    return hull
