"""Shared helpers for the battlefield props (Blender 4.2 headless). Game coords: x left, y up, z forward, metres.
Reuses Part / defmat / new_empty / part_to_obj from blender/helis/heli_lib.py."""
import sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'helis'))
import bpy
from mathutils import Vector, Matrix
import heli_lib as L
from heli_lib import Part, new_empty, part_to_obj, defmat, V, PI, MAT, ear_clip

def rad(d): return math.radians(d)

class Model:
    def __init__(s, name): s.name = name; s.parts = []
    def part(s, nm=None, pivot=(0, 0, 0)):
        p = Part(nm or (s.name + '_body'), pivot); s.parts.append(p); return p
    def total(s): return sum(p.tris() for p in s.parts)
    def build(s):
        root = new_empty(s.name, (0, 0, 0), None, size=0.5)
        for p in s.parts:
            if p.V: part_to_obj(p, root)
        return root

def palette():
    D = defmat
    D('battle_sand', '#b9a678', 0.95); D('battle_sandbag_a', '#a99a6a', 0.97); D('battle_sandbag_b', '#9a8b5c', 0.97); D('battle_sandbag_c', '#b5a574', 0.97)
    D('battle_earth', '#6e5b42', 0.97); D('battle_earth_dark', '#4e4130', 0.97); D('battle_mud', '#3f3426', 0.97)
    D('battle_concrete', '#9b9a93', 0.9); D('battle_concrete_dark', '#6f6e69', 0.9); D('battle_asphalt', '#3c3d3f', 0.92)
    D('battle_olive', '#4f5a3a', 0.8); D('battle_olive_dark', '#394229', 0.8); D('battle_khaki', '#8a7f55', 0.85)
    D('battle_canvas', '#77714f', 0.95, double=True); D('battle_canvas_light', '#a6a285', 0.95, double=True); D('battle_canvas_white', '#cfcdbd', 0.95, double=True)
    D('battle_wood', '#7a5a3a', 0.85); D('battle_wood_dark', '#4d3824', 0.88); D('battle_wood_light', '#a98457', 0.85); D('battle_crate', '#6d5d3a', 0.85); D('battle_crate_green', '#4a5532', 0.82)
    D('battle_steel', '#6d7176', 0.5, 0.8); D('battle_steel_dark', '#3a3d41', 0.55, 0.7); D('battle_galv', '#9aa0a4', 0.45, 0.8); D('battle_rust', '#8a4a2a', 0.8, 0.3)
    D('battle_black', '#1c1c1d', 0.8); D('battle_rubber', '#1a1a1a', 0.95); D('battle_white', '#e8e8e2', 0.7); D('battle_yellow', '#d9b21c', 0.6); D('battle_red', '#b3201f', 0.6)
    D('battle_paint_white', '#e9e9e3', 0.85); D('battle_paint_yellow', '#d6ad1f', 0.85); D('battle_orange', '#d9631c', 0.7)
    D('battle_drum_green', '#4d5b35', 0.6, 0.3); D('battle_drum_blue', '#2f4f7a', 0.6, 0.3); D('battle_drum_red', '#9b2d22', 0.6, 0.3)
    D('battle_camo_a', '#4d5a38', 0.95, double=True); D('battle_camo_b', '#6b6a3f', 0.95, double=True); D('battle_camo_c', '#3a4430', 0.95, double=True); D('battle_camo_d', '#8a7a4a', 0.95, double=True)
    D('battle_wire', '#6a6d70', 0.5, 0.8, double=True); D('battle_dark', '#0e0e0e', 1.0); D('battle_glass', '#25303a', 0.1, alpha=0.5, double=True)
    D('battle_lens', '#fff4c8', 0.2, emit='#fff1b8', emit_str=6.0); D('battle_light_red', '#ff2a1a', 0.3, emit='#ff2a1a', emit_str=5.0)
    D('battle_brick_a', '#9a5a44', 0.95); D('battle_brick_b', '#8a4e3b', 0.95); D('battle_brick_c', '#a8694f', 0.95); D('battle_mortar', '#b8b0a0', 0.95)
    D('battle_plaster', '#c9c0aa', 0.95); D('battle_plaster_dark', '#a69d88', 0.95)
    D('battle_sandstone_a', '#c9a572', 0.95); D('battle_sandstone_b', '#b8905a', 0.95); D('battle_sandstone_c', '#d6b88a', 0.95); D('battle_sandstone_d', '#a47c4a', 0.95)
    D('battle_palm_trunk', '#8a6e4a', 0.95); D('battle_palm_frond', '#3f7a34', 0.85, double=True); D('battle_palm_frond_b', '#4f8a3a', 0.85, double=True); D('battle_coconut', '#5a4228', 0.9)
    D('battle_flag', '#c9b043', 0.9, double=True); D('battle_sock_a', '#d9631c', 0.9, double=True); D('battle_sock_b', '#ecebe4', 0.9, double=True)
    D('battle_red_cross', '#c7201f', 0.8); D('battle_cot', '#5f6a55', 0.9)

BAGM = ['battle_sandbag_a', 'battle_sandbag_b', 'battle_sandbag_c']

# ---------------------------------------------------------------- primitives
def R3(deg): return Matrix.Rotation(rad(deg), 3, 'Y')

def ybox(P, c0, off, size, yaw, mat, bevel=0.0, tilt=(0, 0)):
    """Box at c0 + R(yaw) * off, rotated by yaw about Y (plus optional x/z tilt in degrees)."""
    c = Vector(c0) + R3(yaw) @ Vector(off)
    return P.box(tuple(c), size, mat, rot=(tilt[0], yaw, tilt[1]), bevel=bevel)

def tube(P, a, b, w, mat, seg=4, caps=True, smooth=False):
    """Square beam (seg=4, w = full width) or round tube (w = radius)."""
    if seg == 4: return P.sweep([a, b], w * 0.7071, 4, mat, False, (caps, caps), phase=PI / 4)
    return P.sweep([a, b], w, seg, mat, smooth, (caps, caps))

def extrude_xy(P, prof, z0, z1, mat, smooth=False):
    n = len(prof); pts = [(x, y, z0) for x, y in prof] + [(x, y, z1) for x, y in prof]
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    for t in ear_clip(prof): faces.append(tuple(t)); faces.append(tuple(n + i for i in reversed(t)))
    return P.add(pts, faces, mat, smooth)

def blk(P, x0, x1, z0, z1, y0, y1, mat, ins=(0, 0, 0, 0)):
    """Block whose top is inset at (xmin, xmax, zmin, zmax)."""
    b = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
    t = [(x0 + ins[0], z0 + ins[2]), (x1 - ins[1], z0 + ins[2]), (x1 - ins[1], z1 - ins[3]), (x0 + ins[0], z1 - ins[3])]
    pts = [(p[0], y0, p[1]) for p in b] + [(p[0], y1, p[1]) for p in t]
    faces = [(0, 1, 2, 3), (4, 5, 6, 7)] + [(i, (i + 1) % 4, 4 + (i + 1) % 4, 4 + i) for i in range(4)]
    return P.add(pts, faces, mat, False)

def bag(P, c, d, mat, l=0.5, w=0.3, h=0.16):
    """Single sandbag; c = centre of its base, d = unit (x,z) direction of its long axis."""
    dx, dz = d; nx, nz = -dz, dx; rings = []
    for (y, sx, sz) in ((0.0, 0.86, 0.84), (0.5, 1.0, 1.0), (1.0, 0.8, 0.72)):
        ring = []
        for (a, b) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            lx = a * l / 2 * sx; lz = b * w / 2 * sz
            ring.append((c[0] + lx * dx + lz * nx, c[1] + h * y, c[2] + lx * dz + lz * nz))
        rings.append(ring)
    return P.loft(rings, mat, False, (True, True))

def bagline(P, a, b, courses, rng, y0=0.0, rows=1, l=0.5, w=0.3, h=0.16, step=0.92, jit=0.05):
    """Sandbags along the (x,z) line a->b, `courses` high, `rows` bags thick, running bond."""
    ax, az = a; bx, bz = b; Ln = math.hypot(bx - ax, bz - az); ux, uz = (bx - ax) / Ln, (bz - az) / Ln; nx, nz = -uz, ux
    n = max(1, round(Ln / l)); sp = Ln / n; cnt = 0
    for j in range(courses):
        if j % 2 == 0: items = [((i + 0.5) * sp, sp) for i in range(n)]
        else: items = [(sp * 0.25, sp * 0.5)] + [(i * sp, sp) for i in range(1, n)] + [(Ln - sp * 0.25, sp * 0.5)]
        for (t, ln) in items:
            for r in range(rows):
                ro = (r - (rows - 1) / 2) * w * 0.98
                ang = rng.uniform(-jit, jit); cs, sn = math.cos(ang), math.sin(ang)
                d = (ux * cs - uz * sn, ux * sn + uz * cs)
                c = (ax + ux * t + nx * ro, y0 + j * h * step, az + uz * t + nz * ro)
                bag(P, c, d, rng.choice(BAGM), ln * 1.02, w, h); cnt += 1
    return cnt

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

def crate(P, c, size, yaw, mat, bat='battle_wood_dark'):
    """Wooden crate with end battens + lid strap; c = centre of its BASE."""
    sx, sy, sz = size; cc = (c[0], c[1] + sy / 2, c[2])
    ybox(P, cc, (0, 0, 0), size, yaw, mat)
    for s in (-1, 1): ybox(P, cc, (s * (sx / 2 - 0.03), 0, 0), (0.06, sy + 0.02, sz + 0.03), yaw, bat)
    ybox(P, cc, (0, 0, 0), (sx + 0.03, sy + 0.02, sz * 0.14), yaw, bat)

def drum(P, c, mat, h=0.88, r=0.29, seg=10):
    P.cyl((c[0], c[1], c[2]), (c[0], c[1] + h, c[2]), r, r, seg, mat, False)
    P.cyl((c[0], c[1] + h * 0.45, c[2]), (c[0], c[1] + h * 0.52, c[2]), r + 0.012, r + 0.012, seg, 'battle_steel_dark', False)

def ring_flat(P, c, r0, r1, y, mat, seg=32, a0=0, a1=360):
    """Flat annulus (or arc) at height y, facing +Y."""
    pts = []; faces = []; n = seg
    for i in range(n + 1):
        a = rad(a0 + (a1 - a0) * i / n)
        pts.append((c[0] + r0 * math.sin(a), y, c[2] + r0 * math.cos(a))); pts.append((c[0] + r1 * math.sin(a), y, c[2] + r1 * math.cos(a)))
    for i in range(n): faces.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
    fl = []
    for f in faces:
        a = Vector(pts[f[1]]) - Vector(pts[f[0]]); b = Vector(pts[f[2]]) - Vector(pts[f[0]])
        fl.append(f if a.cross(b).y > 0 else f[::-1])
    return P.add(pts, fl, mat, False, orient=False)

def flat_rect(P, x0, x1, z0, z1, y, mat):
    """Flat quad at height y facing +Y."""
    pts = [(x0, y, z0), (x0, y, z1), (x1, y, z1), (x1, y, z0)]
    a = Vector(pts[1]) - Vector(pts[0]); b = Vector(pts[2]) - Vector(pts[0])
    f = (0, 1, 2, 3) if a.cross(b).y > 0 else (3, 2, 1, 0)
    return P.add(pts, [f], mat, False, orient=False)

def dish(P, c, rw, rh, depth, mat_front, mat_back, nu=8, nv=6, thick=0.1):
    """Elliptical parabolic dish centred at c, opening toward +Z. rw/rh half width/height, depth = rim set-back."""
    c = Vector(c); front = []; back = []
    for j in range(nv + 1):
        rf = []; rb = []; v = -1 + 2 * j / nv
        for i in range(nu + 1):
            u = -1 + 2 * i / nu
            x = u * math.sqrt(max(0.0, 1 - v * v / 2)); y = v * math.sqrt(max(0.0, 1 - u * u / 2))
            zf = depth * (x * x + y * y) - depth * 0.5
            rf.append((c.x + x * rw, c.y + y * rh, c.z + zf)); rb.append((c.x + x * rw, c.y + y * rh, c.z + zf - thick))
        front.append(rf); back.append(rb)
    P.patch(front, mat_front, (0, 0, 1), True); P.patch(back, mat_back, (0, 0, -1), True)
    for A, B, out in ((front[0], back[0], (0, -1, 0)), (front[-1], back[-1], (0, 1, 0)),
                      ([r[0] for r in front], [r[0] for r in back], (-1, 0, 0)), ([r[-1] for r in front], [r[-1] for r in back], (1, 0, 0))):
        P.patch([A, B], mat_back, out, False)

def tent(P, cx, cz, length, width, wall_h, ridge_h, mat, floor_mat=None, closed_back=True, y0=0.0):
    """Ridge tent along Z (open at +Z). Double-sided canvas."""
    hw = width / 2; z0 = cz - length / 2; z1 = cz + length / 2
    prof = [(-hw, y0), (-hw, y0 + wall_h), (0, y0 + ridge_h), (hw, y0 + wall_h), (hw, y0 + wall_h * 0 + y0)]
    prof = [(cx + x, y) for x, y in prof]; n = len(prof)
    pts = [(x, y, z0) for x, y in prof] + [(x, y, z1) for x, y in prof]
    faces = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
    if closed_back: faces.append((0, 1, 2, 3, 4)[::-1])
    P.add(pts, faces, mat, False, orient=False)
    if floor_mat: flat_rect(P, cx - hw, cx + hw, z0, z1, y0 + 0.02, floor_mat)
