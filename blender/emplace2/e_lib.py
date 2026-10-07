"""Shared helpers for the emplacement / guard-tower models (Blender 4.2 headless).
Game coords: x = model's left, y up, z forward, metres. Geometry is authored in game coords and converted to Blender on object creation
(heli_lib.b_of), so the glTF exporter (Y up) gives game coords back. Reuses Part / VM node tree from blender/bveh/v_lib.py."""
import sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'helis')); sys.path.insert(0, os.path.join(HERE, '..', 'bveh'))
import bpy
from mathutils import Vector, Matrix
import heli_lib as L
from heli_lib import Part, new_empty, part_to_obj, defmat, V, PI, MAT, ear_clip, b_of
import v_lib as VL


def rad(d): return math.radians(d)


def palette():
    D = defmat
    D('emp_paint', '#8f9478', 0.7)                      # THE gun / shield body paint (game may recolour)
    D('emp_steel', '#6d7176', 0.5, 0.8); D('emp_steel_dark', '#3a3d41', 0.55, 0.7); D('emp_galv', '#9aa0a4', 0.45, 0.8)
    D('emp_black', '#1c1c1d', 0.8); D('emp_rubber', '#161616', 0.95); D('emp_brass', '#b08d3a', 0.4, 0.8); D('emp_rust', '#8a4a2a', 0.8, 0.3)
    D('emp_ammo', '#4a5532', 0.75); D('emp_shell', '#6b6e3c', 0.6, 0.3); D('emp_shell_band', '#d6ad1f', 0.7)
    D('emp_wood', '#7a5a3a', 0.85); D('emp_wood_dark', '#4d3824', 0.88); D('emp_wood_light', '#a98457', 0.85); D('emp_crate', '#6d5d3a', 0.85)
    D('emp_sandbag_a', '#a99a6a', 0.97); D('emp_sandbag_b', '#9a8b5c', 0.97); D('emp_sandbag_c', '#b5a574', 0.97)
    D('emp_concrete', '#9b9a93', 0.9); D('emp_concrete_dark', '#6f6e69', 0.9); D('emp_earth', '#6e5b42', 0.97)
    D('emp_glass', '#25303a', 0.1, alpha=0.5, double=True)
    D('emp_lens', '#fff4c8', 0.2, emit='#fff1b8', emit_str=6.0); D('emp_light_red', '#ff2a1a', 0.3, emit='#ff2a1a', emit_str=4.0)
    D('emp_canvas', '#77714f', 0.95, double=True); D('emp_yellow', '#d6ad1f', 0.8); D('emp_white', '#e8e8e2', 0.7)
    D('emp_olive', '#4f5a3a', 0.8); D('emp_roof', '#7d8184', 0.55, 0.6)


BAGM = ['emp_sandbag_a', 'emp_sandbag_b', 'emp_sandbag_c']


# ---------------------------------------------------------------- node tree (VM + scale on empties)
class EM(VL.VM):
    def empty(s, nm, pivot, parent=None, shape='PLAIN_AXES', scale=None):
        s.nodes.append(dict(name=nm, part=None, parent=parent, pivot=Vector(pivot), kind=shape, scale=scale))

    def build(s):
        root = new_empty(s.name, (0, 0, 0), None, size=0.5); objs = {None: root}; piv = {None: Vector((0, 0, 0))}
        for n in s.nodes:
            par = n['parent']
            assert par in objs, (n['name'], par)
            if n['part'] is not None:
                if not n['part'].V: continue
                o = part_to_obj(n['part'], objs[par])
            else:
                o = new_empty(n['name'], (0, 0, 0), objs[par], size=0.12, shape=n['kind'])
                sc = n.get('scale')
                if sc: o.scale = (sc[0], sc[2], sc[1])          # game (x, y, z) -> blender (x, z, y)
            o.location = b_of(n['pivot'] - piv[par])
            objs[n['name']] = o; piv[n['name']] = n['pivot']
        return root


# ---------------------------------------------------------------- primitives
def bx(P, x0, x1, y0, y1, z0, z1, mat, bevel=0.0): return VL.bx(P, x0, x1, y0, y1, z0, z1, mat, bevel)
def bx2(P, x0, x1, y0, y1, z0, z1, mat, bevel=0.0): return VL.bx2(P, x0, x1, y0, y1, z0, z1, mat, bevel)
def tube(P, a, b, w, mat, seg=4, caps=True): return VL.tube(P, a, b, w, mat, seg, caps)
def cyl(P, a, b, r0, r1, seg, mat, smooth=False, caps=(True, True)): return P.cyl(a, b, r0, r1, seg, mat, smooth, caps)


def slab(P, outline, origin, ua, ub, thick, mat):
    """Flat plate: polygon (a, b) in the plane of unit vectors ua, ub through `origin`, thickness along ua x ub (centred)."""
    o = Vector(origin); ua = Vector(ua).normalized(); ub = Vector(ub).normalized(); nm = ua.cross(ub).normalized()
    outline = list(outline); n = len(outline)
    area = sum(outline[i][0] * outline[(i + 1) % n][1] - outline[(i + 1) % n][0] * outline[i][1] for i in range(n))
    if area < 0: outline.reverse()
    pts = []
    for h in (-thick / 2, thick / 2): pts += [tuple(o + ua * a + ub * b + nm * h) for a, b in outline]
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    for t in ear_clip(outline):
        faces.append(tuple(n + i for i in t)); faces.append(tuple(reversed(t)))
    return P.add(pts, faces, mat, False)


def wing(P, xi, xo, y0, y1, z, thick, mat, fold=0.0, ch=0.0):
    """Upright plate from inner edge x=xi to outer edge x=xo at depth z; folds back (toward -Z) by `fold` degrees; top outer corner chamfered by ch."""
    s = 1 if xo > xi else -1; w = abs(xo - xi)
    outline = [(0, y0), (w, y0), (w, y1 - ch), (w - ch, y1), (0, y1)]
    ua = (s * math.cos(rad(fold)), 0, -math.sin(rad(fold)))
    return slab(P, outline, (xi, 0, z), ua, (0, 1, 0), thick, mat)


def bar(P, a, b, w, mat):
    return tube(P, a, b, w, mat, 4)


def rod(P, a, b, r, mat, seg=6):
    return P.sweep([a, b], r, seg, mat, False, (True, True))


def circle_pts(c, r, axis='y', n=12, a0=0.0, a1=360.0, closed=True):
    """Points on a circle around `c` in the plane normal to `axis` ('x','y','z')."""
    c = Vector(c); out = []
    m = n if (closed and abs(a1 - a0) >= 360) else n + 1
    for k in range(m):
        a = rad(a0 + (a1 - a0) * k / n)
        if axis == 'y': out.append(c + V(r * math.sin(a), 0, r * math.cos(a)))
        elif axis == 'z': out.append(c + V(r * math.cos(a), r * math.sin(a), 0))
        else: out.append(c + V(0, r * math.cos(a), r * math.sin(a)))
    return out


def loop(P, c, r, tr, axis, mat, n=12, seg=4, a0=0.0, a1=360.0):
    """Thin ring / arc (tube of radius tr along a circle)."""
    pts = circle_pts(c, r, axis, n, a0, a1)
    if abs(a1 - a0) >= 360: pts = pts + [pts[0]]
    return P.sweep(pts, tr, seg, mat, False, (False, False) if abs(a1 - a0) >= 360 else (True, True))


def tyre(P, c, r, w, mat_t='emp_rubber', mat_r='emp_steel', seg=18, side=1):
    """Pneumatic wheel, axis along x, centre c."""
    c = Vector(c)
    path = [c + V(x * w, 0, 0) for x in (-0.5, -0.42, -0.25, 0.25, 0.42, 0.5)]
    rb = r
    P.sweep(path, [rb * 0.80, rb * 0.96, rb, rb, rb * 0.96, rb * 0.80], seg, mat_t, True, (True, True))
    for sgn in (-1, 1):
        P.cyl(c + V(sgn * w * 0.5, 0, 0), c + V(sgn * (w * 0.5 + 0.03), 0, 0), r * 0.58, r * 0.55, 12, mat_r, False)
    P.cyl(c + V(-w * 0.5 - 0.03, 0, 0), c + V(w * 0.5 + 0.08, 0, 0), r * 0.16, r * 0.16, 8, 'emp_steel_dark', False)
    for k in range(6):
        a = 2 * PI * k / 6
        P.cyl(c + V(w * 0.5 + 0.03, r * 0.38 * math.cos(a), r * 0.38 * math.sin(a)), c + V(w * 0.5 + 0.06, r * 0.38 * math.cos(a), r * 0.38 * math.sin(a)), r * 0.04, r * 0.035, 5, 'emp_steel_dark', False)


# ---------------------------------------------------------------- sandbags (own materials)
def bag(P, c, d, mat, l=0.5, w=0.3, h=0.16):
    dx, dz = d; nx, nz = -dz, dx; rings = []
    for (y, sx, sz) in ((0.0, 0.86, 0.84), (0.5, 1.0, 1.0), (1.0, 0.8, 0.72)):
        ring = []
        for (a, b) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            lx = a * l / 2 * sx; lz = b * w / 2 * sz
            ring.append((c[0] + lx * dx + lz * nx, c[1] + h * y, c[2] + lx * dz + lz * nz))
        rings.append(ring)
    return P.loft(rings, mat, False, (True, True))


def bagline(P, a, b, courses, rng, y0=0.0, rows=1, l=0.5, w=0.3, h=0.16, step=0.92, jit=0.05):
    ax, az = a; bx_, bz = b; Ln = math.hypot(bx_ - ax, bz - az); ux, uz = (bx_ - ax) / Ln, (bz - az) / Ln; nx, nz = -uz, ux
    n = max(1, round(Ln / l)); sp = Ln / n
    for j in range(courses):
        if j % 2 == 0: items = [((i + 0.5) * sp, sp) for i in range(n)]
        else: items = [(sp * 0.25, sp * 0.5)] + [(i * sp, sp) for i in range(1, n)] + [(Ln - sp * 0.25, sp * 0.5)]
        for (t, ln) in items:
            for r in range(rows):
                ro = (r - (rows - 1) / 2) * w * 0.98
                ang = rng.uniform(-jit, jit); cs, sn = math.cos(ang), math.sin(ang)
                d = (ux * cs - uz * sn, ux * sn + uz * cs)
                c = (ax + ux * t + nx * ro, y0 + j * h * step, az + uz * t + nz * ro)
                bag(P, c, d, rng.choice(BAGM), ln * 1.02, w, h)


def bagarc(P, c, r, a0, a1, courses, rng, y0=0.0, l=0.5, w=0.3, h=0.16, step=0.92, rows=1):
    """Sandbags along an arc (degrees; 0 = +Z, 90 = +X)."""
    Ln = abs(rad(a1 - a0)) * r; n = max(3, round(Ln / l))
    for j in range(courses):
        for i in range(n + 1):
            f = (i + (0.5 if j % 2 else 0.0)) / n
            if f > 1.0: continue
            ang = rad(a0 + (a1 - a0) * f)
            for rr in range(rows):
                rrr = r + (rr - (rows - 1) / 2) * w
                p = (c[0] + rrr * math.sin(ang), y0 + j * h * step, c[2] + rrr * math.cos(ang))
                bag(P, p, (math.cos(ang), -math.sin(ang)), rng.choice(BAGM), l * 1.02, w, h)


def crate(P, c, size, yaw, mat='emp_crate', bat='emp_wood_dark'):
    """Wooden crate, c = centre of its BASE."""
    sx, sy, sz = size; cc = (c[0], c[1] + sy / 2, c[2]); cy = Matrix.Rotation(rad(yaw), 3, 'Y')
    def at(o): return tuple(Vector(cc) + cy @ Vector(o))
    P.box(at((0, 0, 0)), size, mat, rot=(0, yaw, 0))
    for s in (-1, 1): P.box(at((s * (sx / 2 - 0.03), 0, 0)), (0.06, sy + 0.02, sz + 0.03), bat, rot=(0, yaw, 0))
    P.box(at((0, 0, 0)), (sx + 0.03, sy + 0.02, sz * 0.14), bat, rot=(0, yaw, 0))


def ammo_box(P, c, size, mat='emp_ammo', yaw=0.0, handle=True):
    """Metal ammunition box (c = centre) with a lid ridge and a carry handle on top."""
    cy = Matrix.Rotation(rad(yaw), 3, 'Y')
    P.box(c, size, mat, rot=(0, yaw, 0), bevel=0.01)
    P.box(tuple(Vector(c) + cy @ Vector((0, size[1] / 2 + 0.006, 0))), (size[0] * 0.92, 0.014, size[2] * 0.9), 'emp_steel_dark', rot=(0, yaw, 0))
    if handle: P.box(tuple(Vector(c) + cy @ Vector((0, size[1] / 2 + 0.03, 0))), (size[0] * 0.38, 0.03, 0.02), 'emp_black', rot=(0, yaw, 0))


def shell(P, base, d, length, r, mat='emp_shell'):
    """Artillery / mortar shell standing along unit vector d from `base`: body, driving band, ogive nose, fins optional."""
    base = Vector(base); d = Vector(d).normalized()
    P.sweep([base, base + d * length * 0.62], r, 8, mat, True, (True, True))
    P.sweep([base + d * length * 0.62, base + d * length * 0.85, base + d * length], [r, r * 0.72, r * 0.18], 8, mat, True, (False, True))
    P.sweep([base + d * length * 0.12, base + d * length * 0.17], r * 1.04, 8, 'emp_brass', False, (True, True))
    P.sweep([base + d * length * 0.80, base + d * length * 0.84], r * 0.97, 8, 'emp_shell_band', False, (True, True))


def ladder(P, x, z, y0, y1, width=0.44, rung=0.30, rail_w=0.05, rail_d=0.09, rung_r=0.0145, top_ext=0.0, mat_rail='emp_galv', mat_rung='emp_galv', z_wall=None, bracket_ys=()):
    """Vertical ladder centred at (x, z): rails at x +- width/2, rungs every `rung` metres. Climber stands at +Z. Rails run y0..y1+top_ext."""
    hw = width / 2
    for sx in (-1, 1): bar(P, (x + sx * hw, y0, z), (x + sx * hw, y1 + top_ext, z), rail_w, mat_rail)
    n = int((y1 - y0 - 0.1) / rung)
    for k in range(n + 1):
        y = y0 + 0.28 + k * rung
        if y > y1 + 0.001: break
        P.sweep([(x - hw, y, z), (x + hw, y, z)], rung_r, 6, mat_rung, False, (True, True))
    if z_wall is not None:
        for by in bracket_ys:
            for sx in (-1, 1):
                bar(P, (x + sx * hw, by, z - 0.02), (x + sx * hw, by, z_wall), 0.04, 'emp_steel_dark')
                P.box((x + sx * hw, by, z_wall - 0.01), (0.10, 0.12, 0.02), 'emp_steel_dark')


def cage_hoops(P, x, z, ys, r=0.42, z_wall=None, mat='emp_galv', straps=True):
    """Safety hoops around a ladder at (x, z): semicircles opening toward the wall (-Z), centred a little proud of the rungs."""
    cz = z + 0.12
    for y in ys:
        pts = circle_pts((x, y, cz), r, 'y', 10, -105, 105, closed=False)
        # ends reach back to the wall bracket line
        if z_wall is not None:
            pts = [Vector((pts[0].x, y, z_wall))] + pts + [Vector((pts[-1].x, y, z_wall))]
        P.sweep(pts, 0.013, 4, mat, False, (True, True), phase=PI / 4)
    if straps and len(ys) > 1:
        for a in (-60, 0, 60):
            px = x + r * math.sin(rad(a)); pz = cz + r * math.cos(rad(a))
            bar(P, (px, ys[0], pz), (px, ys[-1], pz), 0.025, mat)


def unpitch(p, pivot, elev_deg):
    """Position p (world, wanted at elevation `elev_deg` degrees) expressed in the pitch frame (barrel horizontal along +Z)."""
    q = Vector(p) - Vector(pivot); e = rad(elev_deg)
    # world = Rot(rotation.x = -e) * local ; local = Rot(+e) * world offset
    y = q.y * math.cos(e) - q.z * math.sin(e)
    z = q.y * math.sin(e) + q.z * math.cos(e)
    return Vector(pivot) + V(q.x, y, z)
