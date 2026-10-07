"""Shared helpers for the battlefield vehicles (Blender 4.2 headless). Game coords: x = model's left, y up, z forward, metres.
Reuses Part / defmat / new_empty / part_to_obj from blender/helis/heli_lib.py. Adds a node tree (parents, pivots) with relative placement."""
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'helis'))
import bpy
from mathutils import Vector, Matrix
import heli_lib as L
from heli_lib import Part, new_empty, part_to_obj, defmat, V, PI, MAT, ear_clip, b_of

def rad(d): return math.radians(d)


def palette():
    D = defmat
    D('veh_paint', '#8f9478', 0.7)                       # THE body-paint material (game recolours it)
    D('veh_dark', '#26282a', 0.8); D('veh_steel_dark', '#3b3e42', 0.5, 0.8); D('veh_metal', '#7b7f83', 0.4, 0.85)
    D('veh_rubber', '#161616', 0.95); D('veh_seat', '#3a3d34', 0.9); D('veh_canvas', '#77714f', 0.95, double=True)
    D('veh_canvas_dark', '#4f4c36', 0.95, double=True); D('veh_wood', '#7a5a3a', 0.85); D('veh_rust', '#7a4a2e', 0.8, 0.3)
    D('veh_glass', '#25303a', 0.08, alpha=0.5, double=True)
    D('veh_light_white', '#fff4c8', 0.2, emit='#fff1b8', emit_str=5.0); D('veh_light_red', '#ff2a1a', 0.3, emit='#ff2a1a', emit_str=4.0)
    D('veh_light_amber', '#ffb020', 0.3, emit='#ffa010', emit_str=4.0)
    D('veh_white', '#e8e8e2', 0.7); D('veh_red_cross', '#c7201f', 0.7); D('veh_can', '#56603f', 0.6, 0.2)
    D('veh_hose', '#2b2d2c', 0.9)


# ---------------------------------------------------------------- node tree
class VM:
    def __init__(s, name):
        s.name = name; s.nodes = []; s.names = set()
    def node(s, suffix, parent=None, pivot=(0, 0, 0), full=False):
        nm = suffix if full else (s.name + suffix)
        p = Part(nm, pivot); s.nodes.append(dict(name=nm, part=p, parent=parent, pivot=Vector(pivot), kind='mesh')); return p
    def empty(s, nm, pivot, parent=None, shape='PLAIN_AXES'):
        s.nodes.append(dict(name=nm, part=None, parent=parent, pivot=Vector(pivot), kind=shape))
    def body(s):
        return s.node('_body')
    def total(s): return sum(n['part'].tris() for n in s.nodes if n['part'])
    def build(s):
        root = new_empty(s.name, (0, 0, 0), None, size=0.5); objs = {None: root}; piv = {None: Vector((0, 0, 0))}
        for n in s.nodes:
            par = n['parent']
            assert par in objs, (n['name'], par)
            if n['part'] is not None:
                if not n['part'].V: continue
                o = part_to_obj(n['part'], objs[par])
            else:
                o = new_empty(n['name'], (0, 0, 0), objs[par], size=0.12, shape=n['kind'] if n['kind'] != 'PLAIN_AXES' else 'PLAIN_AXES')
            o.location = b_of(n['pivot'] - piv[par])
            objs[n['name']] = o; piv[n['name']] = n['pivot']
        return root


# ---------------------------------------------------------------- primitives
def bx(P, x0, x1, y0, y1, z0, z1, mat, bevel=0.0):
    return P.box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)), mat, bevel=bevel)

def bx2(P, x0, x1, y0, y1, z0, z1, mat, bevel=0.0):
    bx(P, x0, x1, y0, y1, z0, z1, mat, bevel); bx(P, -x1, -x0, y0, y1, z0, z1, mat, bevel)

def blk(P, x0, x1, y0, y1, z0, z1, mat, ins=(0, 0, 0, 0)):
    """Block whose top face is inset (xmin, xmax, zmin, zmax)."""
    b = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
    t = [(x0 + ins[0], z0 + ins[2]), (x1 - ins[1], z0 + ins[2]), (x1 - ins[1], z1 - ins[3]), (x0 + ins[0], z1 - ins[3])]
    pts = [(p[0], y0, p[1]) for p in b] + [(p[0], y1, p[1]) for p in t]
    faces = [(0, 1, 2, 3), (4, 5, 6, 7)] + [(i, (i + 1) % 4, 4 + (i + 1) % 4, 4 + i) for i in range(4)]
    return P.add(pts, faces, mat, False)

def tube(P, a, b, w, mat, seg=4, caps=True):
    """Square beam (seg 4, w = full width) or round tube (w = radius)."""
    if seg == 4: return P.sweep([a, b], w * 0.7071, 4, mat, False, (caps, caps), phase=PI / 4)
    return P.sweep([a, b], w, seg, mat, True if seg > 6 else False, (caps, caps))

def extrude_zy(P, prof, x0, x1, mat):
    """Polygon given as (z, y) extruded along x from x0 to x1 (concave allowed)."""
    n = len(prof); pts = [(x0, y, z) for z, y in prof] + [(x1, y, z) for z, y in prof]
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    for t in ear_clip(prof): faces.append(tuple(t)); faces.append(tuple(n + i for i in reversed(t)))
    return P.add(pts, faces, mat, False)

def extrude_xy(P, prof, z0, z1, mat):
    n = len(prof); pts = [(x, y, z0) for x, y in prof] + [(x, y, z1) for x, y in prof]
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    for t in ear_clip(prof): faces.append(tuple(t)); faces.append(tuple(n + i for i in reversed(t)))
    return P.add(pts, faces, mat, False)

def hull_rings(secs):
    """secs: (z, wb, wm, wt, y0, ym, y1) -> ring of 6 points: bottom, shoulder, top corners."""
    rings = []
    for (z, wb, wm, wt, y0, ym, y1) in secs:
        rings.append([(-wb, y0, z), (wb, y0, z), (wm, ym, z), (wt, y1, z), (-wt, y1, z), (-wm, ym, z)])
    return rings

def loop_ring(cx, cy, cz, rx, ry, n=12, a0=0.0):
    """Circle/ellipse ring in the x-y plane at z."""
    return [(cx + rx * math.cos(a0 + 2 * PI * k / n), cy + ry * math.sin(a0 + 2 * PI * k / n), cz) for k in range(n)]

def ellipse_hull(P, stations, mat, n=14, smooth=True, caps=(True, True)):
    """stations: (z, rx, ry, cy[, cx]) elliptical rings along z."""
    rings = []
    for st in stations:
        z, rx, ry, cy = st[:4]; cx = st[4] if len(st) > 4 else 0.0
        rings.append(loop_ring(cx, cy, z, rx, ry, n))
    return P.loft(rings, mat, smooth, caps)


def append_xf(P, S, fn):
    """Copy scratch Part S into P with point transform fn."""
    base = len(P.V); P.V += [tuple(fn(Vector(p))) for p in S.V]
    for (idx, m, sm) in S.F: P.F.append(([i + base for i in idx], m, sm))


# ---------------------------------------------------------------- wheels
def tyre(P, c, r, w, side, lugs=16, lug_h=0.03, seg=20, rim='veh_metal', nuts=5, spokes=False, mud=False):
    """Wheel with its axis along x, centre c (world game coords), outer hub face on `side` (+1/-1)."""
    c = Vector(c); hw = w / 2
    path = [c + V(x * w, 0, 0) for x in (-0.5, -0.43, -0.3, 0.3, 0.43, 0.5)]
    P.sweep(path, [r * 0.80, r * 0.95, r, r, r * 0.95, r * 0.80], seg, 'veh_rubber', True, (True, True))
    # tread lugs
    nl = lugs
    for i in range(nl):
        a = 2 * PI * i / nl + (PI / nl if i % 2 else 0.0)
        for sgn in ((-1, 1) if mud else (0,)):
            wx = (w * 0.30 if mud else w * 0.62)
            P.box(c + V(sgn * w * 0.2, (r + lug_h * 0.4) * math.cos(a), (r + lug_h * 0.4) * math.sin(a)), (wx, lug_h * 1.4, r * (0.16 if not mud else 0.11)),
                  'veh_rubber', rot=(math.degrees(a), 0, 0))
    # rim plate (outer face) + hub cap + nuts; thin inner hub
    xo = side * hw
    P.cyl(c + V(xo - side * 0.04, 0, 0), c + V(xo + side * 0.012, 0, 0), r * 0.60, r * 0.60, 12, rim, False)
    P.cyl(c + V(xo + side * 0.012, 0, 0), c + V(xo + side * 0.05, 0, 0), r * 0.22, r * 0.18, 8, 'veh_steel_dark', False)
    for k in range(nuts):
        a = 2 * PI * k / nuts
        P.cyl(c + V(xo + side * 0.012, r * 0.38 * math.cos(a), r * 0.38 * math.sin(a)), c + V(xo + side * 0.04, r * 0.38 * math.cos(a), r * 0.38 * math.sin(a)), r * 0.035, r * 0.03, 5, 'veh_dark', False)
    P.cyl(c + V(-xo + side * 0.04, 0, 0), c + V(-xo - side * 0.012, 0, 0), r * 0.40, r * 0.40, 10, 'veh_steel_dark', False)

def add_wheel(M, name, c, r, w, side, parent=None, **kw):
    """Wheel node (origin at the wheel centre; spin about X)."""
    P = M.node(name, parent, c, full=True); tyre(P, c, r, w, side, **kw); return P

def steer_wheel(M, tag, c, r, w, side, **kw):
    """Steering pivot `<model>_steer_<tag>` at the kingpin (wheel centre) containing the wheel node `<model>_wheel_<tag>`."""
    nm = '%s_steer_%s' % (M.name, tag); M.empty(nm, c, None, 'ARROWS')
    add_wheel(M, '%s_wheel_%s' % (M.name, tag), c, r, w, side, nm, **kw)

def spare_wheel(P, c, r, w, axis_z=True, lugs=14):
    """Static spare wheel with its axis along z, outer face toward +z... built via scratch rotation."""
    S = Part('s', c); tyre(S, c, r, w, 1, lugs=lugs, nuts=5)
    cc = Vector(c)
    def fn(p):
        d = p - cc  # rotate x-axis -> z-axis (about y by -90 deg): (x,y,z) -> (z,y,-x)... pick x->-z so the outer face (+x) turns toward -z
        return cc + V(d.z, d.y, -d.x)
    append_xf(P, S, fn)


# ---------------------------------------------------------------- common parts
def seat(P, x, hip_y, z, w=0.46, d=0.46, mat='veh_seat', back_h=0.5, back=True, tilt=-10):
    P.box((x, hip_y - 0.10, z), (w, 0.14, d), mat, bevel=0.02)
    if back: P.box((x, hip_y + 0.12 + back_h / 2 - 0.1, z - d / 2 + 0.03), (w, back_h, 0.08), mat, rot=(tilt, 0, 0), bevel=0.02)

def bench(P, x0, x1, hip_y, z0, z1, mat='veh_wood', rest=True):
    P.box(((x0 + x1) / 2, hip_y - 0.04, (z0 + z1) / 2), (abs(x1 - x0), 0.05, abs(z1 - z0)), mat)

def steering_wheel(P, c, r=0.18, tilt=-55, col_to=None):
    c = Vector(c); pts = []; n = 12
    t = rad(tilt); ax = Vector((0, math.sin(t), math.cos(t)))  # wheel normal
    u = Vector((1, 0, 0)); v = ax.cross(u).normalized()
    for k in range(n + 1):
        a = 2 * PI * (k % n) / n; pts.append(c + u * (r * math.cos(a)) + v * (r * math.sin(a)))
    P.sweep(pts, 0.016, 5, 'veh_dark', True, (False, False))
    P.cyl(c - ax * 0.02, c + ax * 0.03, 0.035, 0.03, 8, 'veh_dark', False)
    for a in (0.0, 2.1, 4.2): P.sweep([c, c + u * (r * math.cos(a)) + v * (r * math.sin(a))], 0.01, 4, 'veh_dark', False, (False, False))
    if col_to is not None: P.cyl(c, Vector(col_to), 0.022, 0.022, 6, 'veh_dark', False)

def headlight(P, c, r=0.10, depth=0.08, mat='veh_light_white', bezel=True):
    c = Vector(c)
    if bezel: P.cyl(c - V(0, 0, depth * 0.5), c + V(0, 0, depth * 0.1), r * 1.2, r * 1.2, 10, 'veh_dark', False)
    P.cyl(c, c + V(0, 0, depth), r, r * 0.9, 10, mat, False)

def taillight(P, c, w=0.14, h=0.08, back=-1):
    c = Vector(c); P.box(c, (w, h, 0.05), 'veh_light_red')

def machinegun(L, light=True, scale=1.0, barrel=0.95):
    """Light machine gun (M60-style) at the local origin of Loc L; barrel points +Z, grips behind. Returns muzzle z."""
    s = scale
    L.box((0, 0, 0.08 * s), (0.075 * s, 0.13 * s, 0.50 * s), 'veh_steel_dark', bevel=0.008)           # receiver
    L.box((0, 0.075 * s, 0.06 * s), (0.05 * s, 0.025 * s, 0.4 * s), 'veh_metal')                        # feed cover
    L.cyl((0, 0.0, 0.33 * s), (0, 0.0, barrel * s), 0.017 * s, 0.017 * s, 8, 'veh_steel_dark', True)    # barrel
    L.cyl((0, 0.0, 0.33 * s), (0, 0.0, 0.62 * s), 0.032 * s, 0.032 * s, 8, 'veh_metal', True)           # perforated jacket
    L.cyl((0, 0.0, 0.62 * s), (0, 0.0, 0.67 * s), 0.036 * s, 0.026 * s, 8, 'veh_steel_dark', False)
    L.cyl((0, 0.0, (barrel - 0.07) * s), (0, 0.0, (barrel + 0.04) * s), 0.027 * s, 0.027 * s, 8, 'veh_dark', False)  # flash hider
    L.box((0, -0.01, -0.28 * s), (0.05 * s, 0.09 * s, 0.14 * s), 'veh_dark')                            # rear
    for sx in (-1, 1): L.box((sx * 0.055 * s, 0.0, -0.33 * s), (0.025 * s, 0.14 * s, 0.03 * s), 'veh_dark')  # spade grips
    L.box((0, -0.12 * s, -0.04 * s), (0.03 * s, 0.14 * s, 0.04 * s), 'veh_dark')                        # pistol grip
    L.box((0.12 * s, -0.04 * s, 0.05 * s), (0.11 * s, 0.17 * s, 0.26 * s), 'veh_can')                   # ammo box
    L.box((0.07 * s, 0.02 * s, 0.06 * s), (0.04 * s, 0.03 * s, 0.14 * s), 'veh_metal')                  # belt feed
    L.box((0, 0.1 * s, 0.22 * s), (0.02 * s, 0.04 * s, 0.03 * s), 'veh_dark')                           # sight
    L.box((0, -0.1 * s, 0.16 * s), (0.04 * s, 0.07 * s, 0.05 * s), 'veh_dark')                          # pintle block
    return (barrel + 0.04) * s


class Loc:
    """Draws into Part P with an offset (so a gun can be authored at its own origin)."""
    def __init__(s, P, off): s.P = P; s.o = Vector(off)
    def _p(s, p): return tuple(s.o + Vector(p))
    def box(s, c, size, mat, **kw): return s.P.box(s._p(c), size, mat, **kw)
    def cyl(s, a, b, r0, r1, seg, mat, smooth=True, caps=(True, True)): return s.P.cyl(s._p(a), s._p(b), r0, r1, seg, mat, smooth, caps)
    def sweep(s, path, radii, seg, mat, smooth=True, caps=(True, True), **kw): return s.P.sweep([s._p(p) for p in path], radii, seg, mat, smooth, caps, **kw)
    def ellipsoid(s, c, r, mat, **kw): return s.P.ellipsoid(s._p(c), r, mat, **kw)
    def loft(s, rings, mat, smooth=True, caps=(True, True)): return s.P.loft([[s._p(p) for p in r] for r in rings], mat, smooth, caps)
    def add(s, pts, faces, mat, smooth=False, **kw): return s.P.add([s._p(p) for p in pts], faces, mat, smooth, **kw)


def mirror_x(P, fn_build):
    pass
