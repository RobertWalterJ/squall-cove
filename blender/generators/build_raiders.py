"""Squall Cove raider / smuggler / SWAT boats.
  blender -b --python build_raiders.py -- [--review]
Writes ../../assets/raiders.glb.b64.txt (one-line base64 of the GLB), ../review/raiders/raiders.json (manifest)
and, with --review, flat-lit Workbench 3/4 renders of each boat into ../review/raiders/.

Nodes (all top-level, all at the model origin; the game clones by name like the other boat nodes):
  runner_hull  gunboat_hull (+ children gunboat_mount0, gunboat_mount1)  landing_hull  landing_ramp  swatrib_hull
Blender is Z up and the bow faces +X; the glTF export maps (x, y, z) -> three (x, z, -y). Origin = waterline (z = 0),
y-up in three. Left (port) = Blender +Y = three -Z.
"""
import bpy, bmesh, sys, os, json, base64, math, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from mathutils import Vector, Matrix
from pg_core import *

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
REVIEW = os.path.join(ROOT, 'blender', 'review', 'raiders')
ASSET = os.path.join(ROOT, 'assets', 'raiders.glb.b64.txt')
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
os.makedirs(REVIEW, exist_ok=True)

PAL = {
    'charcoal': dict(color='#2b2e33', rough=0.55),
    'charcoal2': dict(color='#3b3f45', rough=0.7),
    'black':    dict(color='#131315', rough=0.85),
    'engine':   dict(color='#1b1c1f', rough=0.5, metal=0.2),
    'engine2':  dict(color='#2c2f33', rough=0.45, metal=0.3),
    'steel':    dict(color='#a4abb2', rough=0.4, metal=0.5),
    'dark':     dict(color='#2d3034', rough=0.7),
    'glass':    dict(color='#25394b', rough=0.12, metal=0.1),
    'tarp':     dict(color='#454d47', rough=0.9),
    'strap':    dict(color='#1c1c1e', rough=0.9),
    'seat':     dict(color='#26282b', rough=0.9),
    'red':      dict(color='#a81f25', rough=0.5),
    'armour':   dict(color='#232427', rough=0.65, metal=0.2),
    'ammo':     dict(color='#58603f', rough=0.8),
    'tyre':     dict(color='#1b1b1d', rough=0.95),
    'olive':    dict(color='#58623b', rough=0.75),
    'olive2':   dict(color='#4a5330', rough=0.8),
    'olive3':   dict(color='#6a7448', rough=0.8),
    'tube':     dict(color='#8d9399', rough=0.7),
    'tube2':    dict(color='#6f757b', rough=0.75),
    'wood':     dict(color='#8f6638', rough=0.9),
    'lamp_b':   dict(color='#2f6bff', rough=0.3, emit='#2f6bff', emit_str=1.5),
    'lamp_r':   dict(color='#ff3a30', rough=0.3, emit='#ff3a30', emit_str=1.5),
}
def m(k): return mat(k, **PAL[k])


def prof(pts, y0, y1, mt, name='prof'):
    """Polygon in the XZ plane extruded between y0 and y1."""
    bm = bmesh.new()
    a = [bm.verts.new((x, y0, z)) for x, z in pts]; b = [bm.verts.new((x, y1, z)) for x, z in pts]
    n = len(pts); bm.faces.new(a); bm.faces.new(b)
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return obj_from_bm(bm, name, m(mt))


def plan(pts, z0, z1, mt, name='plan', rake=None):
    """Polygon in the XY plane extruded between z0 and z1. rake(x)->dz lifts the bottom ring."""
    bm = bmesh.new()
    a = [bm.verts.new((x, y, z0 + (rake(x) if rake else 0))) for x, y in pts]; b = [bm.verts.new((x, y, z1)) for x, y in pts]
    n = len(pts); bm.faces.new(a); bm.faces.new(b)
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return obj_from_bm(bm, name, m(mt))


def interp(tbl, t):
    if t <= tbl[0][0]: return tbl[0][1]
    for (t0, v0), (t1, v1) in zip(tbl, tbl[1:]):
        if t <= t1: return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return tbl[-1][1]


def loft(L, T, mats, n=13, name='hull'):
    """Closed lofted hull. T has tables hd, hc, zk, zc, zd over t = 0 (transom) .. 1 (stem).
    ring = keel, chine(-y), deck(-y), deck(+y), chine(+y). mats = (bottom, side, deck)."""
    bm = bmesh.new(); rings = []
    for i in range(n):
        t = i / (n - 1); x = -L / 2 + t * L
        hd = max(interp(T['hd'], t), 0.03); hc = max(interp(T['hc'], t), 0.02)
        zk, zc, zd = interp(T['zk'], t), interp(T['zc'], t), interp(T['zd'], t)
        rings.append([bm.verts.new(p) for p in ((x, 0, zk), (x, -hc, zc), (x, -hd, zd), (x, hd, zd), (x, hc, zc))])
    mi = (0, 1, 2, 1, 0)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(5):
            try:
                f = bm.faces.new((r0[k], r0[(k + 1) % 5], r1[(k + 1) % 5], r1[k])); f.material_index = mi[k]
            except ValueError: pass
    for r in (rings[0], rings[-1]):
        f = bm.faces.new(r); f.material_index = 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    o = obj_from_bm(bm, name, None)
    for k in mats: o.data.materials.append(m(k))
    return o


def sweep(path, radii, mt, sides=8, name='tube', z=0.0):
    """Tube swept along a polyline of (x, y) with centre height z; radii per point."""
    bm = bmesh.new(); rings = []
    up = Vector((0, 0, 1))
    for i, (x, y) in enumerate(path):
        p0 = Vector(path[max(i - 1, 0)] + (0,)); p1 = Vector(path[min(i + 1, len(path) - 1)] + (0,))
        T = (p1 - p0).normalized(); S = T.cross(up).normalized()
        c = Vector((x, y, z)); r = radii[i]
        rings.append([bm.verts.new(c + r * (math.cos(2 * math.pi * k / sides) * S + math.sin(2 * math.pi * k / sides) * up)) for k in range(sides)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides): bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
    bm.faces.new(rings[0]); bm.faces.new(rings[-1][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return obj_from_bm(bm, name, m(mt))


class P:
    """Collects parts, then joins them into a named node."""
    def __init__(s): s.o = []
    def add(s, o): s.o.append(o); return o
    def bx(s, size, loc, mt, rot=(0, 0, 0), bevel=0.0): return s.add(box(size, loc, rot, m(mt), bevel))
    def cz(s, r1, r2, h, loc, mt, seg=8): return s.add(cyl(r1, r2, h, seg, loc, (0, 0, 0), m(mt)))
    def cyx(s, r, h, xc, y, z, mt, seg=8, r2=None): return s.add(cyl(r, r if r2 is None else r2, h, seg, (xc - h / 2, y, z), (0, math.pi / 2, 0), m(mt)))
    def cyy(s, r, h, x, yc, z, mt, seg=8): return s.add(cyl(r, r, h, seg, (x, yc + h / 2, z), (math.pi / 2, 0, 0), m(mt)))
    def rd(s, p0, p1, r, mt, seg=5): return s.add(rod(p0, p1, r, seg, m(mt)))
    def pr(s, pts, y0, y1, mt): return s.add(prof(pts, y0, y1, mt))
    def join(s, name): return join(s.o, name)


def outboard(p, x, y, zt, cow='engine', leg='engine2', scale=1.0, tilt=0.0):
    """Outboard motor with its transom clamp at (x, y, zt): cowl, leg, torpedo and a prop disc. Hangs aft (-x)."""
    s = scale
    p.bx((0.12 * s, 0.34 * s, 0.34 * s), (x + 0.04, y, zt - 0.05), 'steel')                 # clamp bracket on the transom
    p.bx((0.5 * s, 0.38 * s, 0.5 * s), (x - 0.22 * s, y, zt + 0.1 * s), cow, bevel=0.06)     # cowl
    p.bx((0.24 * s, 0.24 * s, 0.95 * s), (x - 0.2 * s, y, zt - 0.5 * s), leg)               # leg
    p.cyx(0.1 * s, 0.55 * s, x - 0.28 * s, y, zt - 0.95 * s, leg, 6)                         # torpedo
    p.cyx(0.2 * s, 0.03, x - 0.58 * s, y, zt - 0.95 * s, 'steel', 8)                         # prop disc


# ====================================================================== 1 RUNNER
def build_runner():
    L = 9.4
    T = dict(hd=[(0, 1.25), (0.15, 1.3), (0.5, 1.3), (0.7, 1.1), (0.88, 0.6), (1, 0.03)],
             hc=[(0, 1.0), (0.15, 1.05), (0.5, 1.0), (0.7, 0.75), (0.88, 0.3), (1, 0.02)],
             zk=[(0, -0.38), (0.4, -0.40), (0.7, -0.25), (0.88, 0.2), (1, 0.75)],
             zc=[(0, -0.2), (0.4, -0.18), (0.7, 0.0), (0.88, 0.3), (1, 0.8)],
             zd=[(0, 0.58), (0.5, 0.62), (0.8, 0.78), (1, 0.95)])
    zd = lambda x: interp(T['zd'], (x + L / 2) / L)
    p = P(); p.add(loft(L, T, ('black', 'charcoal', 'charcoal2'), name='runner_h'))
    # console + windscreen
    p.bx((1.0, 0.85, 0.5), (0.3, 0, zd(0.3) + 0.25), 'charcoal', bevel=0.05)
    p.bx((0.7, 0.7, 0.04), (0.3, 0, zd(0.3) + 0.52), 'dark')
    p.bx((0.04, 0.95, 0.36), (0.78, 0, zd(0.3) + 0.7), 'glass', rot=(0, math.radians(-20), 0))
    p.bx((0.05, 1.0, 0.04), (0.84, 0, zd(0.3) + 0.9), 'black')
    p.cyx(0.12, 0.03, 0.1, 0, zd(0.3) + 0.6, 'black', 8, r2=0.12)
    p.bx((0.06, 0.06, 0.4), (0.78, 0.5, zd(0.3) + 0.7), 'black'); p.bx((0.06, 0.06, 0.4), (0.78, -0.5, zd(0.3) + 0.7), 'black')
    # two seats behind the console
    for yy in (0.4, -0.4): p.bx((0.45, 0.6, 0.42), (-0.55, yy, zd(-0.55) + 0.21), 'seat', bevel=0.05)
    # tarp-covered cargo bay
    p.bx((2.0, 1.75, 0.5), (-2.55, 0, zd(-2.55) + 0.2), 'tarp', bevel=0.12)
    for xs in (-3.25, -2.55, -1.85): p.bx((0.07, 1.82, 0.52), (xs, 0, zd(xs) + 0.2), 'strap', bevel=0.02)
    # bow cleat and fender rail, transom board
    p.bx((0.2, 0.08, 0.06), (3.7, 0, zd(3.7) + 0.05), 'steel')
    p.bx((0.12, 2.5, 0.5), (-4.66, 0, 0.35), 'charcoal2')
    for yy in (0.62, -0.62): outboard(p, -4.72, yy, 0.62, scale=1.1)
    o = p.join('runner_hull')
    return o


# ====================================================================== 2 GUNBOAT
def build_gunboat():
    L = 9.4
    T = dict(hd=[(0, 1.35), (0.2, 1.4), (0.55, 1.4), (0.75, 1.15), (0.9, 0.6), (1, 0.03)],
             hc=[(0, 1.1), (0.2, 1.15), (0.55, 1.1), (0.75, 0.8), (0.9, 0.3), (1, 0.02)],
             zk=[(0, -0.4), (0.5, -0.42), (0.75, -0.2), (0.9, 0.3), (1, 0.9)],
             zc=[(0, -0.15), (0.5, -0.12), (0.75, 0.1), (0.9, 0.4), (1, 0.95)],
             zd=[(0, 0.72), (0.5, 0.75), (0.85, 0.92), (1, 1.1)])
    zd = lambda x: interp(T['zd'], (x + L / 2) / L)
    p = P(); p.add(loft(L, T, ('black', 'red', 'black'), name='gunboat_h'))
    # armoured wheelhouse (sloped slabs, slit windows)
    z0 = zd(-0.3)
    p.pr([(-1.35, z0), (1.05, z0), (0.75, z0 + 1.15), (-1.05, z0 + 1.15)], -0.82, 0.82, 'armour')
    p.bx((2.1, 1.9, 0.1), (-0.15, 0, z0 + 1.2), 'armour')
    p.bx((0.05, 1.3, 0.2), (0.88, 0, z0 + 0.7), 'glass', rot=(0, math.radians(-14), 0))     # forward slit
    for sd in (1, -1):
        p.bx((1.3, 0.05, 0.16), (-0.1, sd * 0.84, z0 + 0.72), 'glass')
        p.bx((1.9, 0.04, 0.16), (-0.15, sd * 0.93, z0 + 0.42), 'red')                       # red stripe on the armour
    p.rd((-0.9, 0.5, z0 + 1.25), (-0.9, 0.5, z0 + 2.3), 0.025, 'black')                      # whip aerial
    # fore gun position: pedestal + shield (gun is added by the game at gunboat_mount0)
    xf_, xa = 2.9, -2.5
    p.cz(0.14, 0.14, 0.6, (xf_, 0, zd(xf_)), 'black')
    p.bx((0.05, 0.85, 0.6), (xf_ + 0.38, 0, zd(xf_) + 0.9), 'armour')
    for sd in (1, -1): p.bx((0.55, 0.05, 0.6), (xf_ + 0.12, sd * 0.42, zd(xf_) + 0.9), 'armour', rot=(0, 0, sd * math.radians(-18)))
    p.cz(0.4, 0.4, 0.1, (xf_, 0, zd(xf_) - 0.0), 'red', 10)
    # aft gun position: a low round tub with a shield
    p.cz(0.55, 0.5, 0.42, (xa, 0, zd(xa)), 'red', 10)
    p.cz(0.14, 0.14, 0.5, (xa, 0, zd(xa) + 0.42), 'black')
    p.bx((0.05, 0.95, 0.6), (xa - 0.5, 0, zd(xa) + 0.95), 'armour')
    for sd in (1, -1): p.bx((0.55, 0.05, 0.6), (xa - 0.22, sd * 0.47, zd(xa) + 0.95), 'armour', rot=(0, 0, sd * math.radians(18)))
    # exhaust stubs, rudders, trim tabs at the transom
    for sd in (1, -1):
        p.cyx(0.075, 0.45, -4.9, sd * 0.6, 0.28, 'engine', 6)
        p.bx((0.25, 0.04, 0.7), (-4.9, sd * 0.95, -0.2), 'engine2')
        p.bx((0.3, 0.35, 0.03), (-4.8, sd * 0.35, -0.38), 'steel')
    p.bx((0.12, 2.65, 0.5), (-4.66, 0, 0.4), 'black')
    # tyre fenders on the sides, ammo boxes aft
    for xs in (1.0, -0.2, -1.4, -3.0):
        for sd in (1, -1): p.cyy(0.19, 0.2, xs, sd * 1.47 if sd > 0 else -1.67, zd(xs) - 0.2, 'tyre', 8)
    for (xs, yy, zz) in ((-3.7, 0.6, 0), (-3.7, -0.5, 0), (-3.7, 0.6, 0.3)):
        p.bx((0.55, 0.35, 0.3), (xs, yy, zd(xs) + 0.15 + zz), 'ammo')
    p.bx((0.2, 0.08, 0.06), (4.15, 0, zd(4.15) + 0.04), 'steel')
    o = p.join('gunboat_hull')
    mounts = []
    for i, (x, z) in enumerate(((xf_, zd(xf_) + 0.65), (xa, zd(xa) + 1.0))):
        e = bpy.data.objects.new(f'gunboat_mount{i}', None); e.empty_display_type = 'ARROWS'; e.empty_display_size = 0.3
        link(e); e.parent = o; e.location = (x, 0, z); mounts.append(e)
    return o, mounts


# ====================================================================== 3 LANDING CRAFT
HINGE = (8.0, 0.0, 0.6)       # model coords, Blender (x forward, y left, z up) == three (x, -z, y)
RAMP_LEN, RAMP_W, RAMP_T = 2.0, 3.5, 0.14

def build_landing():
    L, FLOOR, TOP, BOT = 16.0, 0.6, 1.7, -0.6
    outline = [(-8, -2.3), (4.4, -2.3), (8, -1.85), (8, 1.85), (4.4, 2.3), (-8, 2.3)]
    p = P()
    p.add(plan(outline, BOT, FLOOR, 'olive2', rake=lambda x: 0.5 if x > 7 else 0.0, name='lc_slab'))
    wz, wh = FLOOR + (TOP - FLOOR) / 2, TOP - FLOOR
    p.bx((0.16, 4.6, wh), (-7.92, 0, wz), 'olive')                                          # transom
    for sd in (1, -1):
        p.bx((12.4, 0.16, wh), (-1.8, sd * 2.22, wz), 'olive')                              # straight sides
        a = math.atan2(-0.45, 3.6) * sd
        p.bx((3.63, 0.16, wh), (6.2, sd * 2.0, wz), 'olive', rot=(0, 0, a))                 # bow quarters
        p.bx((12.4, 0.2, 0.08), (-1.8, sd * 2.22, TOP + 0.03), 'olive3')                    # coaming
        p.bx((3.7, 0.2, 0.08), (6.2, sd * 2.0, TOP + 0.03), 'olive3', rot=(0, 0, a))
        # bench with a rail above it, along the troop well
        p.bx((8.0, 0.4, 0.45), (-0.2, sd * 1.93, FLOOR + 0.22), 'wood')
        p.rd((-4.2, sd * 2.1, 1.38), (3.8, sd * 2.1, 1.38), 0.03, 'steel', 5)
        for xs in (-4.2, -1.5, 1.2, 3.8): p.rd((xs, sd * 2.1, FLOOR + 0.4), (xs, sd * 2.1, 1.38), 0.03, 'steel', 5)
        # ramp hinge brackets and stops at the bow
        p.bx((0.3, 0.2, 0.3), (8.0, sd * 1.82, FLOOR + 0.1), 'steel')
        p.bx((0.25, 0.16, 1.3), (7.7, sd * 1.82, FLOOR + 0.8 + 0.1), 'olive3')
        # bollards and a rear fender
        p.cz(0.1, 0.1, 0.25, (-7.2, sd * 1.9, TOP), 'steel', 6)
    # aft cab
    p.bx((2.6, 2.6, 2.3), (-5.9, 0, FLOOR + 1.15), 'olive', bevel=0.06)
    p.bx((2.9, 2.9, 0.1), (-5.9, 0, FLOOR + 2.35), 'olive3')
    p.bx((0.06, 2.0, 0.6), (-4.58, 0, FLOOR + 1.5), 'glass')
    for sd in (1, -1): p.bx((1.6, 0.06, 0.55), (-5.9, sd * 1.32, FLOOR + 1.5), 'glass')
    p.bx((0.06, 0.9, 1.6), (-7.22, 0, FLOOR + 0.9), 'olive2')                              # aft door
    p.cz(0.14, 0.14, 0.7, (-6.6, 0.7, FLOOR + 2.4), 'black', 8)                              # exhaust stack
    p.rd((-6.4, -0.9, FLOOR + 2.4), (-6.4, -0.9, FLOOR + 3.4), 0.025, 'black')
    # loose stores in the well: two fuel drums, a crate
    for yy in (-0.4, 0.4): p.cz(0.22, 0.22, 0.55, (-3.7, yy, FLOOR), 'red', 8)
    p.bx((0.6, 0.5, 0.4), (-3.7, 1.2, FLOOR + 0.2), 'ammo')
    # twin exhaust stubs, skegs and rudders under the transom
    for sd in (1, -1):
        p.cyx(0.09, 0.4, -8.2, sd * 1.2, 0.2, 'engine', 6)
        p.bx((0.3, 0.05, 0.8), (-8.2, sd * 1.4, -0.5), 'engine2')
    hull = p.join('landing_hull')

    # ramp: local origin at the hinge, plate rises along +Z (raised = closed)
    r = P()
    r.bx((RAMP_T, RAMP_W, RAMP_LEN), (HINGE[0] + RAMP_T / 2, 0, HINGE[2] + RAMP_LEN / 2), 'olive', bevel=0.02)
    for yy in (-1.2, 0, 1.2): r.bx((0.06, 0.08, RAMP_LEN - 0.1), (HINGE[0] + RAMP_T + 0.03, yy, HINGE[2] + RAMP_LEN / 2), 'olive3')
    for zz in (0.5, 1.0, 1.5): r.bx((0.04, RAMP_W - 0.1, 0.07), (HINGE[0] + RAMP_T + 0.02, 0, HINGE[2] + zz), 'olive2')
    for sd in (1, -1): r.bx((0.2, 0.08, RAMP_LEN), (HINGE[0] + RAMP_T / 2 + 0.03, sd * (RAMP_W / 2 - 0.04), HINGE[2] + RAMP_LEN / 2), 'olive3')   # side flanges
    r.bx((0.22, 0.5, 0.18), (HINGE[0] + 0.1, 0, HINGE[2] + RAMP_LEN - 0.1), 'steel')       # lifting eye plate
    ramp = r.join('landing_ramp')
    ramp.data.transform(Matrix.Translation(-Vector(HINGE)))
    ramp.location = HINGE
    return hull, ramp


# ====================================================================== 4 RESPONSE RIB
def build_rib():
    L = 8.0
    T = dict(hd=[(0, 0.95), (0.2, 1.0), (0.6, 0.95), (0.85, 0.5), (1, 0.03)],
             hc=[(0, 0.8), (0.5, 0.85), (0.85, 0.45), (1, 0.02)],
             zk=[(0, -0.28), (0.5, -0.3), (0.8, -0.1), (1, 0.3)],
             zc=[(0, -0.1), (0.5, -0.08), (0.8, 0.1), (1, 0.35)],
             zd=[(0, 0.18), (0.8, 0.2), (1, 0.35)])
    p = P(); p.add(loft(L, T, ('black', 'black', 'charcoal2'), name='rib_h'))
    half = [(-3.75, 1.0), (-1.5, 1.03), (0.8, 1.0), (2.4, 0.78), (3.25, 0.46), (3.62, 0.18)]
    path = half + [(3.72, 0.0)] + [(x, -y) for x, y in reversed(half)]
    rad = [0.3, 0.35, 0.36, 0.33, 0.29, 0.27] + [0.26] + [0.27, 0.29, 0.33, 0.36, 0.35, 0.3][::-1][::-1]
    rad = [0.3, 0.35, 0.36, 0.33, 0.29, 0.27, 0.26, 0.27, 0.29, 0.33, 0.36, 0.35, 0.3]
    p.add(sweep(path, rad, 'tube', 8, 'tube', z=0.3))
    for sd in (1, -1):
        p.bx((0.14, 0.1, 0.3), (-3.82, sd * 1.0, 0.3), 'tube2')                              # stern tube end caps
    p.bx((0.12, 1.9, 0.65), (-3.93, 0, 0.42), 'charcoal2')                                   # transom
    # console, windscreen, blue light bar, grab rails, seats
    p.bx((0.8, 0.7, 0.75), (-0.4, 0, 0.18 + 0.375), 'black', bevel=0.05)
    p.bx((0.7, 0.62, 0.05), (-0.4, 0, 0.18 + 0.78), 'tube2')
    p.bx((0.04, 0.6, 0.3), (-0.02, 0, 1.2), 'glass', rot=(0, math.radians(-22), 0))
    p.bx((0.06, 0.5, 0.06), (-0.55, 0, 1.0), 'lamp_b')
    p.rd((-0.8, 0.4, 0.95), (-0.8, 0.4, 1.35), 0.025, 'steel'); p.rd((-0.8, -0.4, 0.95), (-0.8, -0.4, 1.35), 0.025, 'steel')
    p.rd((-0.8, 0.4, 1.35), (-0.8, -0.4, 1.35), 0.025, 'steel')
    for xs in (-1.5, -2.3): p.bx((0.55, 1.2, 0.34), (xs, 0, 0.18 + 0.17), 'seat', bevel=0.05)
    p.bx((0.5, 0.8, 0.3), (1.2, 0, 0.18 + 0.15), 'seat', bevel=0.05)
    p.rd((3.1, 0.35, 0.65), (3.1, -0.35, 0.65), 0.03, 'steel')
    p.bx((0.3, 0.1, 0.1), (3.5, 0, 0.62), 'steel')                                           # bow handle
    outboard(p, -3.99, 0.0, 0.5, cow='engine', leg='engine', scale=1.15)
    return p.join('swatrib_hull')


# ====================================================================== assemble
reset()
runner = build_runner()
gun, mounts = build_gunboat()
landing, ramp = build_landing()
rib = build_rib()
bpy.context.view_layer.update()

def wbounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type == 'MESH' for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx

def r3(x): return round(float(x), 3)
groups = {'runner': [runner], 'gunboat': [gun], 'landing': [landing, ramp], 'swatrib': [rib]}
manifest = {}; total = 0
for k, objs in groups.items():
    mn, mx = wbounds(objs); tris = sum(tri_count(o) for o in objs); total += tris
    manifest[k] = dict(nodes=[o.name for o in objs], length=r3(mx.x - mn.x), beam=r3(mx.y - mn.y), height=r3(mx.z - mn.z),
                       min=[r3(c) for c in mn], max=[r3(c) for c in mx], tris=tris)
    print('BOAT', k, manifest[k])
manifest['landing_ramp'] = dict(hinge_blender=list(HINGE), hinge_three=[HINGE[0], HINGE[2], -HINGE[1]], length=RAMP_LEN, width=RAMP_W,
                                open_rotation_z_deg=-100, closed_rotation_z=0)
manifest['gunboat_mounts'] = {e.name: [r3(c) for c in e.location] for e in mounts}
json.dump(manifest, open(os.path.join(REVIEW, 'raiders.json'), 'w'), indent=1)

tmp = os.path.join(tempfile.gettempdir(), 'sc_raiders.glb')
export_glb(list(bpy.context.scene.objects), tmp)
data = open(tmp, 'rb').read()
print('GLB bytes', len(data), 'total tris', total)
open(ASSET, 'w', newline='').write(base64.b64encode(data).decode('ascii'))
print('WROTE', ASSET)

if '--review' in argv:
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_object_outline = False; sh.show_cavity = False
    w = bpy.data.worlds.new('rw'); w.color = (0.74, 0.80, 0.86); sc.world = w
    sc.render.image_settings.file_format = 'PNG'
    for mt in bpy.data.materials:
        b = mt.node_tree.nodes['Principled BSDF']
        c = b.inputs['Emission Color'].default_value if b.inputs['Emission Strength'].default_value > 0 else b.inputs['Base Color'].default_value
        mt.diffuse_color = (c[0], c[1], c[2], 1)
    sea = mat('sea', '#3d6d8a', 1.0); sea.diffuse_color = (0.12, 0.3, 0.42, 1)
    water = box((200, 200, 0.04), (0, 0, -0.02), (0, 0, 0), sea)

    def shoot(name, objs, path, d, res=(900, 560)):
        for o in bpy.data.objects: o.hide_render = True
        vis = list(objs)
        for o in objs: vis += list(o.children_recursive)
        for o in vis: o.hide_render = False
        water.hide_render = False
        bpy.context.view_layer.update()
        mn, mx = wbounds(vis); c = (mn + mx) / 2; sz = max(mx.x - mn.x, mx.y - mn.y, mx.z - mn.z)
        cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); link(cam); sc.camera = cam
        cam.data.clip_end = 500; cam.data.lens = 40
        sc.render.resolution_x, sc.render.resolution_y = res
        cam.location = c + Vector(d).normalized() * sz * 1.7
        cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam)

    for k, objs in groups.items():
        shoot(k, objs, os.path.join(REVIEW, f'{k}_3q_front.png'), (0.8, -0.62, 0.42))
        shoot(k, objs, os.path.join(REVIEW, f'{k}_3q_rear.png'), (-0.8, -0.62, 0.42))
    ramp.rotation_euler = (0, math.radians(100), 0)
    shoot('landing', groups['landing'], os.path.join(REVIEW, 'landing_ramp_open_3q.png'), (0.9, -0.55, 0.3))
    ramp.rotation_euler = (0, 0, 0)
    print('REVIEW DONE')
print('BUILD DONE')
