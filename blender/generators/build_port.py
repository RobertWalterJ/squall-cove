"""Squall Cove port: static buildings and props.
  blender -b --python build_port.py -- [--review] [--only warehouse,office]
Writes ../../assets/port.glb.b64.txt (one-line base64 GLB), ../review/port/port.json (manifest: sizes, tris, doors)
and, with --review, a flat-lit Workbench 3/4 render per model into ../review/port/.

Every model is ONE top-level mesh node (several materials) named by its key, origin at the centre of its footprint on
the ground (Blender z = 0), long axis along +X, y up in three (Blender Z). Blender (x, y, z) -> three (x, z, -y).
Doors are listed in the manifest as (side, along-wall offset m, width m, height m), side in +x -x +y -y (Blender axes;
three z = -Blender y, so Blender +y is three -z).
"""
import bpy, bmesh, sys, os, json, base64, math, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from mathutils import Vector, Matrix
from pg_core import *

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
REVIEW = os.path.join(ROOT, 'blender', 'review', 'port')
ASSET = os.path.join(ROOT, 'assets', 'port.glb.b64.txt')
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
os.makedirs(REVIEW, exist_ok=True)

PAL = {
    'concrete':  dict(color='#a3a39e', rough=0.9),
    'concrete2': dict(color='#7b7c79', rough=0.9),
    'brick':     dict(color='#9c4a3b', rough=0.9),
    'brick2':    dict(color='#7f3b30', rough=0.9),
    'metal_b':   dict(color='#8fa3ad', rough=0.55, metal=0.3),   # corrugated blue-grey
    'metal_g':   dict(color='#aeb3b5', rough=0.55, metal=0.3),
    'metal_d':   dict(color='#4a5157', rough=0.6, metal=0.4),
    'roof_red':  dict(color='#8a3a30', rough=0.7, metal=0.2),
    'roof_grey': dict(color='#5d6166', rough=0.7, metal=0.2),
    'roof_dark': dict(color='#3b3f44', rough=0.8),
    'glass':     dict(color='#27394a', rough=0.15, metal=0.1),
    'door_g':    dict(color='#3d6b4f', rough=0.6, metal=0.2),
    'door_b':    dict(color='#2f5f8f', rough=0.6, metal=0.2),
    'door_r':    dict(color='#a3302b', rough=0.6, metal=0.2),
    'door_k':    dict(color='#2a2d31', rough=0.7),
    'white':     dict(color='#e6e6e0', rough=0.7),
    'cream':     dict(color='#d9ceb0', rough=0.85),
    'yellow':    dict(color='#d9a62b', rough=0.6),
    'siding_w':  dict(color='#dcdad2', rough=0.85),
    'siding_y':  dict(color='#d6bf6e', rough=0.85),
    'siding_g':  dict(color='#7f8c86', rough=0.85),
    'stucco':    dict(color='#c2b59b', rough=0.95),
    'wood':      dict(color='#8f6638', rough=0.9),
    'wood2':     dict(color='#6b4a2a', rough=0.9),
    'olive':     dict(color='#58623b', rough=0.85),
    'olive2':    dict(color='#464e2e', rough=0.9),
    'sand1':     dict(color='#a99668', rough=0.95),
    'sand2':     dict(color='#93825a', rough=0.95),
    'c_red':     dict(color='#a3302b', rough=0.55, metal=0.3),
    'c_blue':    dict(color='#2c5d93', rough=0.55, metal=0.3),
    'c_green':   dict(color='#3b7a4d', rough=0.55, metal=0.3),
    'c_orange':  dict(color='#d27a22', rough=0.55, metal=0.3),
    'frame':     dict(color='#2a2d31', rough=0.6, metal=0.4),
    'rust':      dict(color='#7a4a30', rough=0.9, metal=0.2),
    'steel':     dict(color='#a4abb2', rough=0.4, metal=0.5),
    'black':     dict(color='#1b1c1e', rough=0.8),
    'tank':      dict(color='#d9dbd6', rough=0.6, metal=0.2),
    'red':       dict(color='#b3262b', rough=0.55),
    'lens':      dict(color='#f0e6b0', rough=0.3),
    'grass':     dict(color='#5d6b3a', rough=1.0),
    'wrap':      dict(color='#bfd0d8', rough=0.35),
    'cardboard': dict(color='#a98756', rough=0.9),
    'crane':     dict(color='#c4c8cc', rough=0.5, metal=0.3),
}
MATS_BY = {}
def mt(k):
    if k == 'mesh':
        return mat('mesh', '#8a9298', 0.5, 0.4, alpha=0.3)
    return mat(k, **PAL[k])


class M:
    """Collects the parts of one model, then joins them into a single node."""
    def __init__(s, key):
        s.key = key; s.parts = []; s.doors = []; s.notes = ''
    def add(s, o): s.parts.append(o); return o
    def b(s, x0, x1, y0, y1, z0, z1, k, rot=(0, 0, 0), bevel=0.0):
        return s.add(box((x1 - x0, y1 - y0, z1 - z0), ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), rot, mt(k), bevel))
    def c(s, r, h, loc, k, seg=12, r2=None, rot=(0, 0, 0)):
        return s.add(cyl(r, r if r2 is None else r2, h, seg, loc, rot, mt(k)))
    def rd(s, p0, p1, r, k, seg=6):
        return s.add(rod(p0, p1, r, seg, mt(k)))
    def ext(s, pts, a0, a1, fn, k):
        """Polygon pts (u, v) extruded between a0 and a1; fn(u, v, a) -> (x, y, z)."""
        bm = bmesh.new()
        A = [bm.verts.new(fn(u, v, a0)) for u, v in pts]; B = [bm.verts.new(fn(u, v, a1)) for u, v in pts]
        n = len(pts); bm.faces.new(A); bm.faces.new(B[::-1])
        for i in range(n):
            j = (i + 1) % n; bm.faces.new((A[i], A[j], B[j], B[i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        return s.add(obj_from_bm(bm, 'p', mt(k)))
    def ext_x(s, pts_yz, x0, x1, k): return s.ext(pts_yz, x0, x1, lambda u, v, a: (a, u, v), k)
    def ext_y(s, pts_xz, y0, y1, k): return s.ext(pts_xz, y0, y1, lambda u, v, a: (u, a, v), k)
    def poly(s, verts, faces, k):
        return s.add(mesh('p', verts, faces, mt(k)))
    def door(s, side, off, w, h):
        s.doors.append(dict(side=side, offset=round(off, 2), width=w, height=h))
    def finish(s):
        o = join(s.parts, s.key)
        o.location = (0, 0, 0)
        return o


def side_map(side):
    """(u, w, v) -> (x, y, z) for a wall on `side`; u along the wall, w outward, v up."""
    return {'+y': lambda u, w, v: (u, w, v), '-y': lambda u, w, v: (u, -w, v),
            '+x': lambda u, w, v: (w, u, v), '-x': lambda u, w, v: (-w, u, v)}[side]


def corr(m, side, u0, u1, v0, v1, w0, amp, pitch, k):
    """Corrugated cladding with vertical ribs: zigzag between w0 and w0 + amp, extruded from v0 to v1."""
    n = max(2, int(round((u1 - u0) / (pitch / 2))))
    n += n % 2
    front = [(u0 + (u1 - u0) * i / n, w0 + (amp if i % 2 else 0)) for i in range(n + 1)]
    back = [(u1, w0 - 0.03), (u0, w0 - 0.03)]
    fn = side_map(side)
    return m.ext(front + back, v0, v1, lambda u, w, a: fn(u, w, a), k)


def rect_on(m, side, u, v, w, h, k, depth=0.06, wall=0.0):
    """Flat patch (window, door leaf, sign) proud of the wall by `depth`, centred at (u, v)."""
    x0, y0, z0 = side_map(side)(u - w / 2, wall, v - h / 2); x1, y1, z1 = side_map(side)(u + w / 2, wall + depth, v + h / 2)
    return m.b(min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), min(z0, z1), max(z0, z1), k)


def window(m, side, u, v, w, h, wall, k='glass', frame='white'):
    rect_on(m, side, u, v, w + 0.2, h + 0.2, frame, 0.03, wall)
    rect_on(m, side, u, v, w, h, k, 0.07, wall)


def gable(m, x0, x1, y0, y1, zeave, zridge, k, ov=0.35, t=0.14, axis='x', cap=None):
    """Two sloped roof slabs. axis 'x': ridge along X. zridge is the roof top at the ridge, zeave the wall-top height."""
    if axis == 'x':
        hw = (y1 - y0) / 2; yc = (y0 + y1) / 2; L = x1 - x0 + 2 * ov; xc = (x0 + x1) / 2
    else:
        hw = (x1 - x0) / 2; yc = (x0 + x1) / 2; L = y1 - y0 + 2 * ov; xc = (y0 + y1) / 2
    s = (zridge - zeave) / hw; th = math.atan(s)
    half = (hw + ov) / math.cos(th); mid = (hw + ov) / 2
    for sg in (1, -1):
        zc = zridge - s * mid - 0.5 * t / math.cos(th)
        if axis == 'x':
            m.add(box((L, half, t), (xc, yc + sg * mid, zc), (-sg * th, 0, 0), mt(k)))
        else:
            m.add(box((half, L, t), (yc + sg * mid, xc, zc), (0, sg * th, 0), mt(k)))
    if cap:
        if axis == 'x': m.b(xc - L / 2, xc + L / 2, yc - 0.15, yc + 0.15, zridge - 0.1, zridge + 0.06, cap)
        else: m.b(yc - 0.15, yc + 0.15, xc - L / 2, xc + L / 2, zridge - 0.1, zridge + 0.06, cap)


def hip(m, x0, x1, y0, y1, z0, h, k, ov=0.4):
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hx, hy = (x1 - x0) / 2 + ov, (y1 - y0) / 2 + ov
    r = max(0.0, hx - hy) if hx >= hy else 0.0
    zs = z0 - 0.15
    V = [(cx - hx, cy - hy, zs), (cx + hx, cy - hy, zs), (cx + hx, cy + hy, zs), (cx - hx, cy + hy, zs),
         (cx - r, cy, z0 + h), (cx + r, cy, z0 + h)]
    F = [(3, 2, 1, 0), (0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4)]
    m.poly(V, F, k)


def body(m, x0, x1, y0, y1, z0, z1, k):
    return m.b(x0, x1, y0, y1, z0, z1, k)


# ====================================================================== models
def warehouse():
    m = M('warehouse'); L, W = 29.6, 13.6; ze, zr = 6.5, 8.9
    m.b(-L / 2, L / 2, -W / 2, W / 2, 0, 0.2, 'concrete2')                              # slab apron
    m.ext_x([(-W / 2, 0.2), (W / 2, 0.2), (W / 2, ze), (0, zr - 0.2), (-W / 2, ze)], -L / 2 + 0.1, L / 2 - 0.1, 'metal_b')
    m.b(-L / 2, L / 2, -W / 2 - 0.05, W / 2 + 0.05, 0.2, 1.1, 'concrete')              # plinth
    for sd in ('+y', '-y'):
        corr(m, sd, -L / 2 + 0.1, L / 2 - 0.1, 1.1, ze, W / 2, 0.06, 0.6, 'metal_b')
    gable(m, -L / 2, L / 2, -W / 2, W / 2, ze, zr, 'metal_g', ov=0.2, cap='metal_d')
    # three roller doors on the +y side, one personnel door and high windows on the -y side
    for u in (-9.0, 0.0, 9.0):
        rect_on(m, '+y', u, 2.5, 5.6, 5.0, 'metal_d', 0.1, W / 2 + 0.06)
        rect_on(m, '+y', u, 2.4, 4.8, 4.5, 'door_g', 0.16, W / 2 + 0.06)
        for r in range(1, 7): rect_on(m, '+y', u, 0.15 + r * 0.7, 4.8, 0.06, 'metal_d', 0.2, W / 2 + 0.06)
        m.door('+y', u, 4.8, 4.5)
    rect_on(m, '-y', -11.0, 1.1, 1.1, 2.2, 'door_b', 0.1, W / 2 + 0.06); m.door('-y', -11.0, 1.1, 2.2)
    for u in range(-12, 13, 4):
        window(m, '-y', u + 1.0, 4.6, 1.6, 0.9, W / 2 + 0.06)
    # end walls: loading bay door on +x end, small vents
    rect_on(m, '+x', 0, 2.0, 3.6, 4.0, 'door_b', 0.12, L / 2 - 0.02); m.door('+x', 0.0, 3.6, 4.0)
    rect_on(m, '+x', 0, 7.0, 1.6, 0.8, 'metal_d', 0.08, L / 2 - 0.02)
    rect_on(m, '-x', 0, 7.0, 1.6, 0.8, 'metal_d', 0.08, L / 2 - 0.02)
    return m


def office():
    m = M('office'); L, W = 13.7, 9.6; zt = 10.2
    m.b(-L / 2, L / 2, -W / 2, W / 2, 0, 0.5, 'concrete')                              # plinth
    body(m, -L / 2 + 0.05, L / 2 - 0.05, -W / 2 + 0.05, W / 2 - 0.05, 0.5, zt, 'brick')
    for zb in (3.5, 6.9):                                                              # floor bands
        m.b(-L / 2 - 0.05, L / 2 + 0.05, -W / 2 - 0.05, W / 2 + 0.05, zb - 0.1, zb + 0.15, 'concrete')
    m.b(-L / 2 - 0.15, L / 2 + 0.15, -W / 2 - 0.15, W / 2 + 0.15, zt, zt + 0.25, 'concrete')  # parapet cap slab (flat roof edge)
    m.b(-L / 2 + 0.4, L / 2 - 0.4, -W / 2 + 0.4, W / 2 - 0.4, zt, zt + 0.12, 'roof_dark')
    for fl in range(3):
        zc = 0.5 + fl * 3.23 + 1.7
        for u in (-5.0, -1.7, 1.7, 5.0):
            if fl == 0 and u in (-1.7, 1.7):
                continue
            window(m, '-y', u, zc, 1.6, 1.4, W / 2 - 0.05)
            window(m, '+y', u, zc, 1.6, 1.4, W / 2 - 0.05)
        for u in (-2.2, 2.2):
            window(m, '+x', u, zc, 1.5, 1.4, L / 2 - 0.05); window(m, '-x', u, zc, 1.5, 1.4, L / 2 - 0.05)
    # entrance on the +y long side (front), centred
    rect_on(m, '+y', 0, 1.75, 2.8, 2.5, 'metal_d', 0.1, W / 2 - 0.05)
    rect_on(m, '+y', 0, 1.7, 2.4, 2.3, 'glass', 0.16, W / 2 - 0.05)
    m.door('+y', 0.0, 2.4, 2.3)
    m.b(-1.9, 1.9, W / 2 - 0.05, W / 2 + 1.3, 2.9, 3.1, 'concrete2')                  # canopy
    m.b(-1.9, -1.75, W / 2 + 1.15, W / 2 + 1.3, 0.5, 2.9, 'concrete2'); m.b(1.75, 1.9, W / 2 + 1.15, W / 2 + 1.3, 0.5, 2.9, 'concrete2')
    m.b(-2.2, 2.2, W / 2, W / 2 + 1.5, 0, 0.5, 'concrete')                            # steps
    # roof plant
    m.b(3.0, 5.5, -2.0, 0.5, zt + 0.12, zt + 0.8, 'metal_g')                           # stair head
    m.b(-4.5, -1.5, 0.5, 3.0, zt + 0.12, zt + 0.5, 'metal_d'); m.c(0.5, 0.25, (-3.0, 1.75, zt + 0.5), 'steel', 10)
    return m


def hangar():
    m = M('hangar'); L, W = 23.7, 19.6; zs, zt = 5.0, 9.9
    hw = W / 2
    arch = [(-hw, 0.0), (hw, 0.0), (hw, zs)]
    N = 9
    for i in range(1, N):
        a = math.pi * i / N
        arch.append((hw * math.cos(a), zs + (zt - zs) * math.sin(a)))
    arch.append((-hw, zs))
    m.ext_x(arch, -L / 2, L / 2, 'metal_g')
    # arch ribs standing proud
    big = [(y * 1.0, z) for (y, z) in arch]
    for x in (-L / 2 + 0.2, -9, -6, -3, 0, 3, 6, 9, L / 2 - 0.2):
        arch_r = [(y * 1.02, zs + (z - zs) * 1.02 if z > zs else z) for (y, z) in arch]
        m.ext_x(arch_r, x - 0.12, x + 0.12, 'metal_b')
    m.b(-L / 2, L / 2, -hw - 0.1, hw + 0.1, 0, 0.5, 'concrete')                        # plinth
    # big door on the +x end: two sliding leaves + track
    for sgn in (-1, 1):
        rect_on(m, '+x', sgn * 3.6, 3.6, 7.0, 7.2, 'metal_d', 0.15, L / 2 + 0.02)
        rect_on(m, '+x', sgn * 3.6, 3.6, 6.7, 6.9, 'door_b', 0.22, L / 2 + 0.02)
        for r in range(1, 6): rect_on(m, '+x', sgn * 3.6, r * 1.1, 6.7, 0.07, 'metal_d', 0.26, L / 2 + 0.02)
    m.b(L / 2 + 0.02, L / 2 + 0.3, -7.5, 7.5, 7.5, 7.9, 'metal_d')                     # door hood
    m.door('+x', 0.0, 14.0, 7.2)
    rect_on(m, '-y', 6.0, 1.1, 1.1, 2.2, 'door_b', 0.1, hw); m.door('-y', 6.0, 1.1, 2.2)
    for u in (-8, -4, 0, 4, 8):
        window(m, '+y', u, 3.2, 1.8, 1.0, hw + 0.0)
    return m


def workshop():
    m = M('workshop'); L, W = 11.4, 7.4; zw = 3.9
    m.b(-L / 2, L / 2, -W / 2, W / 2, 0, 0.3, 'concrete2')
    body(m, -L / 2 + 0.1, L / 2 - 0.1, -W / 2 + 0.1, W / 2 - 0.1, 0.3, zw, 'concrete')
    for zz in (1.3, 2.3, 3.3): m.b(-L / 2 + 0.05, L / 2 - 0.05, -W / 2 + 0.05, W / 2 - 0.05, zz, zz + 0.05, 'concrete2')   # block courses
    # mono-pitch metal roof, high side at -y
    th = math.atan(0.8 / W)                                                            # mono-pitch roof, high side at -y
    m.add(box((L + 0.6, W / math.cos(th) + 0.5, 0.14), (0, 0, zw + 0.3), (-th, 0, 0), mt('roof_grey')))
    m.add(box((L, 0.2, 0.7), (0, -W / 2 + 0.1, zw + 0.3), (0, 0, 0), mt('concrete')))
    rect_on(m, '+y', -2.5, 1.5, 3.4, 2.9, 'metal_d', 0.1, W / 2 - 0.1)
    rect_on(m, '+y', -2.5, 1.45, 3.0, 2.7, 'door_r', 0.16, W / 2 - 0.1)
    for r in range(1, 5): rect_on(m, '+y', -2.5, 0.2 + r * 0.5, 3.0, 0.05, 'metal_d', 0.2, W / 2 - 0.1)
    m.door('+y', -2.5, 3.0, 2.7)
    rect_on(m, '+y', 2.5, 1.1, 1.0, 2.1, 'door_k', 0.1, W / 2 - 0.1); m.door('+y', 2.5, 1.0, 2.1)
    window(m, '+y', 4.5, 1.9, 1.0, 1.0, W / 2 - 0.1)
    window(m, '-y', -3, 2.2, 1.6, 1.0, W / 2 - 0.1); window(m, '-y', 3, 2.2, 1.6, 1.0, W / 2 - 0.1)
    window(m, '+x', 0, 2.2, 1.4, 1.0, L / 2 - 0.1)
    m.c(0.18, 0.7, (-4.5, -2.0, zw + 0.5), 'metal_d', 8)                             # flue
    m.b(-L / 2 - 0.6, -L / 2, -1.0, 1.0, 0, 0.9, 'wood2')                              # wood stack against the back
    return m


def house_a():
    m = M('house_a'); L, W = 7.4, 6.2; ze = 3.0
    m.b(-L / 2, L / 2, -W / 2, W / 2, 0, 0.4, 'concrete')
    m.ext_x([(-W / 2 + 0.05, 0.4), (W / 2 - 0.05, 0.4), (W / 2 - 0.05, ze), (0, 5.1), (-W / 2 + 0.05, ze)], -L / 2 + 0.05, L / 2 - 0.05, 'siding_w')
    gable(m, -L / 2, L / 2, -W / 2, W / 2, ze, 5.5, 'roof_red', ov=0.35, cap='roof_dark')
    m.b(2.3, 2.9, 0.6, 1.2, 5.0, 6.0, 'brick')                                         # chimney (ridge top 5.5 .. 6.0)
    rect_on(m, '+y', -1.5, 1.7, 1.0, 2.1, 'door_g', 0.1, W / 2 - 0.05); m.door('+y', -1.5, 1.0, 2.1)
    m.b(-2.4, -0.6, W / 2, W / 2 + 0.6, 0.4, 0.55, 'wood')                              # porch deck (boards)
    window(m, '+y', 1.8, 1.7, 1.3, 1.2, W / 2 - 0.05); window(m, '+y', 3.1, 1.7, 0.9, 1.2, W / 2 - 0.05)
    window(m, '-y', -2, 1.7, 1.3, 1.2, W / 2 - 0.05); window(m, '-y', 2, 1.7, 1.3, 1.2, W / 2 - 0.05)
    window(m, '+x', 0, 1.7, 1.3, 1.2, L / 2 - 0.05); window(m, '+x', 0, 3.6, 0.8, 0.8, L / 2 - 0.05)
    window(m, '-x', 0, 1.7, 1.3, 1.2, L / 2 - 0.05)
    return m


def house_b():
    m = M('house_b'); L, W = 6.8, 6.4
    m.b(-L / 2, L / 2, -W / 2, W / 2, 0, 0.45, 'concrete2')
    body(m, -L / 2 + 0.05, L / 2 - 0.05, -W / 2 + 0.05, W / 2 - 0.05, 0.45, 3.2, 'siding_y')
    hip(m, -L / 2, L / 2, -W / 2, W / 2, 3.2, 2.6, 'roof_grey', ov=0.45)
    m.b(-1.2, 0.0, 0.0, 1.0, 5.0, 5.9, 'brick2')                                      # chimney
    # front porch with columns on +x end
    m.b(L / 2 - 0.05, L / 2 + 1.0, -2.0, 2.0, 0.0, 0.4, 'concrete')
    m.b(L / 2 - 0.05, L / 2 + 1.1, -2.2, 2.2, 2.7, 2.9, 'roof_grey')
    for yy in (-1.9, 1.9): m.b(L / 2 + 0.8, L / 2 + 0.95, yy - 0.08, yy + 0.08, 0.4, 2.7, 'white')
    rect_on(m, '+x', 0.0, 1.5, 1.0, 2.1, 'door_r', 0.1, L / 2 - 0.05); m.door('+x', 0.0, 1.0, 2.1)
    window(m, '+x', -2.5, 1.6, 1.2, 1.2, L / 2 - 0.05); window(m, '+x', 2.5, 1.6, 1.2, 1.2, L / 2 - 0.05)
    for u in (-2.5, 0.0, 2.5):
        window(m, '+y', u, 1.7, 1.3, 1.2, W / 2 - 0.05); window(m, '-y', u, 1.7, 1.3, 1.2, W / 2 - 0.05)
    window(m, '-x', 0, 1.7, 1.4, 1.2, L / 2 - 0.05)
    return m


def house_c():
    m = M('house_c'); L, W = 7.0, 6.6; ze = 4.4
    m.b(-L / 2, L / 2, -W / 2, W / 2, 0, 0.4, 'concrete')
    # two storeys, stucco; gable ridge across Y so the gable faces +x
    m.ext_y([(-L / 2 + 0.05, 0.4), (L / 2 - 0.05, 0.4), (L / 2 - 0.05, ze), (0, 6.0), (-L / 2 + 0.05, ze)], -W / 2 + 0.05, W / 2 - 0.05, 'stucco')
    gable(m, -L / 2, L / 2, -W / 2, W / 2, ze, 6.3, 'roof_dark', ov=0.35, axis='y', cap='roof_grey')
    m.b(L / 2 - 0.05, L / 2 + 0.7, -W / 2 + 0.2, W / 2 - 0.2, 2.6, 2.75, 'wood')       # balcony slab on +x
    m.b(L / 2 + 0.55, L / 2 + 0.65, -W / 2 + 0.2, W / 2 - 0.2, 2.75, 3.6, 'wood2')      # balcony rail (solid)
    m.b(L / 2 - 0.05, L / 2 + 0.65, -W / 2 + 0.2, -W / 2 + 0.3, 2.75, 3.6, 'wood2'); m.b(L / 2 - 0.05, L / 2 + 0.65, W / 2 - 0.3, W / 2 - 0.2, 2.75, 3.6, 'wood2')
    rect_on(m, '+x', -1.5, 1.45, 1.0, 2.1, 'door_g', 0.1, L / 2 - 0.05); m.door('+x', -1.5, 1.0, 2.1)
    window(m, '+x', 1.6, 1.6, 1.3, 1.2, L / 2 - 0.05)
    rect_on(m, '+x', 0.0, 3.7, 2.0, 1.9, 'glass', 0.1, L / 2 - 0.05)
    for u in (-2.0, 2.0):
        window(m, '+y', u, 1.6, 1.2, 1.2, W / 2 - 0.05); window(m, '-y', u, 1.6, 1.2, 1.2, W / 2 - 0.05)
        window(m, '+y', u, 3.7, 1.2, 1.2, W / 2 - 0.05); window(m, '-y', u, 3.7, 1.2, 1.2, W / 2 - 0.05)
    window(m, '-x', 0, 3.7, 1.0, 1.0, L / 2 - 0.05)
    return m


def guardhouse():
    m = M('guardhouse'); L = 4.0
    m.b(-L / 2, L / 2, -L / 2, L / 2, 0, 0.25, 'concrete')
    body(m, -1.85, 1.85, -1.85, 1.85, 0.25, 2.75, 'cream')
    m.b(-L / 2, L / 2, -L / 2, L / 2, 2.75, 3.0, 'roof_dark')
    m.b(-1.85, 1.85, -1.86, 1.86, 1.0, 1.1, 'red')                                       # red sill stripe
    rect_on(m, '+x', 0.0, 1.35, 1.0, 2.1, 'door_b', 0.1, 1.85); m.door('+x', 0.0, 1.0, 2.1)
    rect_on(m, '+x', 1.15, 1.6, 0.4, 0.4, 'glass', 0.08, 1.85)
    for sd in ('+y', '-y'): window(m, sd, 0, 1.7, 2.2, 1.0, 1.85)
    window(m, '-x', 0, 1.7, 2.2, 1.0, 1.85)
    return m


def watchtower():
    m = M('watchtower'); zp = 8.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.rd((sx * 1.4, sy * 1.4, 0.07), (sx * 1.1, sy * 1.1, zp), 0.09, 'wood2', 5)
    for z0, z1, a, b_ in ((0.0, 3.2, 1.4, 1.27), (3.2, 5.6, 1.27, 1.17), (5.6, zp, 1.17, 1.1)):          # cross braces
        for sx, sy, tx, ty in ((1, 1, 1, -1), (-1, 1, 1, 1), (-1, -1, -1, 1), (1, -1, -1, -1)):
            pass
    for (za, zb, ra, rb) in ((0.0, 3.2, 1.4, 1.27), (3.2, 5.6, 1.27, 1.17), (5.6, zp, 1.17, 1.1)):
        for sx in (-1, 1): m.rd((sx * ra, -ra, max(za, 0.07)), (sx * rb, rb, zb), 0.04, 'wood', 4); m.rd((sx * ra, ra, max(za, 0.07)), (sx * rb, -rb, zb), 0.04, 'wood', 4)
        for sy in (-1, 1): m.rd((-ra, sy * ra, max(za, 0.07)), (rb, sy * rb, zb), 0.04, 'wood', 4)
        for z in (za, zb):
            r = ra if z == za else rb
            zz_ = max(z, 0.05); m.b(-r, r, -r - 0.03, -r + 0.03, zz_ - 0.04, zz_ + 0.04, 'wood'); m.b(-r, r, r - 0.03, r + 0.03, zz_ - 0.04, zz_ + 0.04, 'wood')
    m.b(-1.5, 1.5, -1.5, 1.5, zp, zp + 0.2, 'wood2')                                   # platform
    cab0, cab1 = zp + 0.2, zp + 1.6
    m.b(-1.3, 1.3, -1.3, 1.3, cab0, cab1, 'olive')
    for sd in ('+x', '-x', '+y', '-y'):
        rect_on(m, sd, 0, zp + 1.05, 2.0, 0.6, 'glass', 0.06, 1.3)
    m.b(-1.5, 1.5, -1.5, 1.5, cab1, cab1 + 0.2, 'roof_dark'); m.b(-0.9, 0.9, -0.9, 0.9, cab1 + 0.2, cab1 + 0.28, 'roof_dark')
    m.c(0.12, 0.12, (0.8, 0.0, cab1 + 0.28), 'steel', 8)                                  # searchlight
    # ladder on the +x face, door on the cab +x
    for yy in (-0.3, 0.3): m.rd((1.18, yy, 0), (1.18, yy, zp), 0.03, 'steel', 4)
    for z in [0.4 + i * 0.5 for i in range(15)]: m.rd((1.18, -0.3, z), (1.18, 0.3, z), 0.02, 'steel', 4)
    rect_on(m, '+x', 0.0, zp + 0.95, 0.7, 1.4, 'door_k', 0.05, 1.3); m.door('+x', 0.0, 0.7, 1.4)
    for yy in (-1.45, 1.45): m.b(-1.5, 1.5, yy - 0.02, yy + 0.02, zp + 0.2, zp + 0.9, 'wood')
    return m


def fuel_tank():
    m = M('fuel_tank'); R = 5.0
    m.c(R + 0.1, 0.2, (0, 0, 0), 'concrete2', 24)
    m.c(R, 7.7, (0, 0, 0.2), 'tank', 24)
    m.c(R, 0.3, (0, 0, 7.9), 'tank', 24, r2=1.3)                                        # shallow cone roof
    for z in (2.7, 5.3): m.c(R + 0.04, 0.16, (0, 0, z), 'steel', 24)
    m.c(R + 0.03, 0.8, (0, 0, 6.3), 'red', 24)                                          # red band
    Rr = R - 0.1
    for i in range(12):                                                                # roof-edge handrail: posts + two rings
        a = 2 * math.pi * i / 12
        m.rd((Rr * math.cos(a), Rr * math.sin(a), 7.9), (Rr * math.cos(a), Rr * math.sin(a), 8.9), 0.03, 'steel', 4)
    m.add(torus(Rr, 0.035, 24, 4, (0, 0, 8.9), (0, 0, 0), mt('steel')))
    m.add(torus(Rr, 0.03, 24, 4, (0, 0, 8.4), (0, 0, 0), mt('steel')))
    for yy in (-0.28, 0.28): m.rd((R + 0.12, yy, 0.2), (R + 0.12, yy, 8.9), 0.03, 'black', 4)  # ladder on +x
    for z in [0.6 + i * 0.4 for i in range(21)]: m.rd((R + 0.12, -0.28, z), (R + 0.12, 0.28, z), 0.02, 'black', 4)
    for z in (0.2, 4.0, 7.9): m.b(R - 0.02, R + 0.12, -0.35, 0.35, z, z + 0.05, 'black')    # ladder brackets
    m.c(0.5, 0.25, (1.8, 2.5, 7.95), 'steel', 8, r2=0.4)                                 # roof hatch
    m.rd((-R, 0, 0.8), (-R - 1.2, 0, 0.8), 0.15, 'steel', 8); m.rd((-R - 1.2, 0, 0.8), (-R - 1.2, 0, 0.0), 0.15, 'steel', 8)   # draw-off pipe
    return m


def silo():
    m = M('silo'); R = 2.5
    m.c(R + 0.25, 0.4, (0, 0, 0), 'concrete2', 20)
    m.c(R, 13.2, (0, 0, 0.4), 'concrete', 20)
    for z in (2.0, 4.5, 7.0, 9.5, 12.0): m.c(R + 0.05, 0.14, (0, 0, z), 'concrete2', 20)
    m.c(R, 2.0, (0, 0, 13.6), 'metal_g', 20, r2=0.6)                                    # conical top
    m.c(0.6, 0.4, (0, 0, 15.6), 'metal_d', 12)
    for yy in (-0.28, 0.28): m.rd((R + 0.15, yy, 0.4), (R + 0.15, yy, 15.0), 0.03, 'steel', 4)
    for z in [0.8 + i * 0.4 for i in range(35)]: m.rd((R + 0.15, -0.28, z), (R + 0.15, 0.28, z), 0.02, 'steel', 4)
    m.b(-R - 1.0, -R + 0.3, -0.3, 0.3, 0.4, 1.4, 'metal_d')                              # discharge chute box
    m.b(-R - 1.0, -R - 0.6, -0.5, 0.5, 0.0, 0.4, 'concrete')
    return m


def quay_crane():
    m = M('quay_crane'); G = 10.0; D = 6.0                                              # rail gauge 20 m along x, legs at y = +-6
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.b(sx * G - 0.55, sx * G + 0.55, sy * D - 0.55, sy * D + 0.55, 1.0, 18.0, 'red' if False else 'crane')
            m.b(sx * G - 0.7, sx * G + 0.7, sy * D - 1.4, sy * D + 1.4, 0.0, 1.0, 'metal_d')   # wheel truck
        m.b(sx * G - 0.5, sx * G + 0.5, -D, D, 17.2, 18.0, 'crane')                    # portal cross beam at each rail line
    for sy in (-1, 1):
        m.b(-G, G, sy * D - 0.5, sy * D + 0.5, 17.2, 18.0, 'crane')                    # portal sill beams along x
        for sx in (-1, 1):                                                           # knee braces
            m.rd((sx * G, sy * D, 12.0), (sx * G * 0.6, sy * D, 17.2), 0.2, 'crane', 5)
            m.rd((sx * G, sy * D, 3.0), (sx * G, -sy * D, 14.0), 0.18, 'crane', 5)
    # machinery house, A-frame and boom
    m.b(-6.0, 3.0, -4.5, 4.5, 18.0, 23.0, 'crane')
    m.b(-6.0, -4.5, -4.5, 4.5, 18.0, 18.6, 'red')
    m.b(-6.0, 3.0, -4.6, 4.6, 22.6, 23.0, 'red')
    rect_on(m, '+y', -1.5, 20.5, 6.0, 1.4, 'glass', 0.08, 4.5); rect_on(m, '-y', -1.5, 20.5, 6.0, 1.4, 'glass', 0.08, 4.5)
    for sy in (-1, 1):
        m.b(-5.0, 30.0, sy * 1.6 - 0.5, sy * 1.6 + 0.5, 21.6, 23.2, 'crane')    # boom girders (x -6.5 .. 30)
        m.b(-5.0, -3.0, sy * 1.6 - 0.5, sy * 1.6 + 0.5, 21.6, 23.2, 'red')
    m.b(8.0, 30.0, -2.0, 2.0, 22.6, 22.9, 'crane')                                      # boom cross deck
    for xx in range(-4, 28, 4): m.rd((xx, -1.6, 21.7), (xx + 4, 1.6, 23.1), 0.1, 'crane', 4); m.rd((xx, 1.6, 21.7), (xx + 4, -1.6, 23.1), 0.1, 'crane', 4)
    m.b(28.5, 30.0, -2.2, 2.2, 21.4, 23.4, 'red')                                       # boom tip head
    m.b(-11.0, -6.0, -2.5, 2.5, 22.4, 23.0, 'crane')                                 # backreach girder
    m.b(-12.5, -9.5, -3.5, 3.5, 18.0, 22.4, 'metal_d')                                  # counterweight
    # A-frame apex (z 30)
    for sy in (-1, 1):
        m.rd((-3.5, sy * 2.0, 23.0), (-1.0, sy * 0.8, 30.0), 0.35, 'crane', 6)
        m.rd((1.5, sy * 2.0, 23.0), (-1.0, sy * 0.8, 30.0), 0.35, 'crane', 6)
    m.b(-1.6, -0.4, -1.4, 1.4, 29.4, 30.0, 'red')
    for sy in (-1, 1):                                                                  # stays to the boom tip and the backreach
        m.rd((-1.0, sy * 0.8, 29.9), (29.2, sy * 1.6, 23.2), 0.12, 'steel', 4)
        m.rd((-1.0, sy * 0.8, 29.9), (-11.0, sy * 1.2, 22.9), 0.12, 'steel', 4)
    # trolley + hoist + spreader (container hung under the boom, empty spreader)
    m.b(18.0, 22.0, -2.2, 2.2, 20.0, 21.6, 'metal_d')
    for sx_ in (18.6, 21.4):
        for sy_ in (-0.8, 0.8): m.rd((sx_, sy_, 20.0), (sx_, sy_ * 1.3, 8.4), 0.04, 'black', 3)
    m.b(18.0, 22.0, -1.3, 1.3, 7.9, 8.4, 'metal_d')
    # operator cabin under the trolley
    m.b(19.0, 21.0, -1.8, -0.8, 18.4, 20.0, 'yellow')
    # ladder on a land-side leg
    for yy in (-0.2, 0.2): m.rd((-G - 0.62, -D + yy, 1.0), (-G - 0.62, -D + yy, 17.5), 0.03, 'steel', 4)
    return m


def bunker():
    m = M('bunker'); L, W = 8.0, 6.0
    m.b(-L / 2, L / 2, -W / 2, W / 2, 0, 0.15, 'concrete2')
    m.b(-L / 2 + 0.6, L / 2 - 0.6, -W / 2 + 0.6, W / 2 - 0.6, 0.15, 0.2, 'door_k')
    for i in range(7):                                                                 # sandbag courses, upper ones stepped in
        z0 = 0.15 + i * 0.3; z1 = z0 + 0.3; k = 'sand1' if i % 2 == 0 else 'sand2'; ins = 0.0 if i < 4 else 0.12 * (i - 3)
        m.b(-L / 2 + ins, -L / 2 + 0.7 + ins, -W / 2 + ins, W / 2 - ins, z0, z1, k)            # back wall (-x)
        m.b(-L / 2 + ins, L / 2 - ins, -W / 2 + ins, -W / 2 + 0.7 + ins, z0, z1, k)           # side walls
        m.b(-L / 2 + ins, L / 2 - ins, W / 2 - 0.7 - ins, W / 2 - ins, z0, z1, k)
        m.b(L / 2 - 0.7 - ins, L / 2 - ins, -W / 2 + ins, -1.2, z0, z1, k)                    # front wall, 2.4 m entrance
        m.b(L / 2 - 0.7 - ins, L / 2 - ins, 1.2, W / 2 - ins, z0, z1, k)
    for sy in (-1, 1): m.b(L / 2 - 0.68, L / 2 + 0.02, sy * 2.3 - 0.6, sy * 2.3 + 0.6, 1.2, 1.5, 'door_k')   # firing slits
    m.b(-L / 2 + 0.3, L / 2 - 0.3, -W / 2 + 0.3, W / 2 - 0.3, 2.25, 2.37, 'metal_g')                    # corrugated roof deck
    for i in range(14):
        x = -L / 2 + 0.5 + i * (L - 1.0) / 13
        m.b(x - 0.05, x + 0.05, -W / 2 + 0.3, W / 2 - 0.3, 2.37, 2.45, 'metal_d')                         # roof corrugation ribs
    for i in range(3):
        m.b(-L / 2 + 0.9, L / 2 - 0.9, -W / 2 + 0.7 + i * 2.2, -W / 2 + 1.5 + i * 2.2, 2.45, 2.75, 'sand1' if i % 2 == 0 else 'sand2')
    m.c(0.03, 0.6, (-L / 2 + 0.6, 0, 2.75), 'black', 4)                                  # aerial
    m.door('+x', 0.0, 2.4, 2.1)
    return m


def tent():
    m = M('tent'); L, W = 6.0, 4.0; zw, zr = 1.3, 2.85
    pts = [(-W / 2, 0.0), (W / 2, 0.0), (W / 2, zw), (0, zr), (-W / 2, zw)]
    m.ext_x(pts, -L / 2, L / 2, 'olive')
    m.b(-L / 2 - 0.1, L / 2 + 0.1, -0.08, 0.08, zr - 0.08, zr + 0.0, 'olive2')         # ridge seam
    for i in range(1, 6):                                                              # roof seam stripes
        x = -L / 2 + i * L / 6
        m.b(x - 0.03, x + 0.03, -W / 2 - 0.02, 0.0, zw - 0.0, zw + 0.0, 'olive2') if False else None
    m.ext_x([(-W / 2 - 0.06, 0.0), (-W / 2 + 0.2, 0.0), (-W / 2 + 0.2, zw), (-W / 2 - 0.06, zw)], -L / 2, L / 2, 'olive2')
    m.ext_x([(W / 2 - 0.2, 0.0), (W / 2 + 0.06, 0.0), (W / 2 + 0.06, zw), (W / 2 - 0.2, zw)], -L / 2, L / 2, 'olive2')
    # door flap on +x end
    m.ext_x([(-0.7, 0.0), (0.7, 0.0), (0.7, 1.9), (0, 2.4), (-0.7, 1.9)], L / 2 - 0.02, L / 2 + 0.06, 'door_k')
    m.ext_x([(-0.7, 0.0), (-0.05, 0.0), (-0.05, 2.3), (-0.7, 1.9)], L / 2 + 0.04, L / 2 + 0.1, 'olive2')
    m.door('+x', 0.0, 1.4, 1.9)
    for x in (-L / 2 - 0.0, L / 2):
        m.rd((x, 0, 0), (x, 0, zr + 0.1), 0.04, 'wood2', 5)
    for x in (-2.0, 0.0, 2.0):
        for sy in (-1, 1):
            m.rd((x, sy * (W / 2 + 0.0), zw), (x, sy * (W / 2 + 0.0), 0.0), 0.03, 'wood2', 4)
    return m


def container(name, paint):
    m = M(name); L, W, H = 5.97, 2.42, 2.59
    m.b(-L / 2, L / 2 - 0.05, -W / 2 + 0.03, W / 2 - 0.03, 0.12, H - 0.08, paint)
    for sd in ('+y', '-y'):
        corr(m, sd, -L / 2 + 0.2, L / 2 - 0.25, 0.25, H - 0.2, W / 2 - 0.04, 0.045, 0.25, paint)
    corr(m, '-x', -W / 2 + 0.15, W / 2 - 0.15, 0.25, H - 0.2, L / 2 - 0.04, 0.03, 0.25, paint)
    # steel frame: corner posts, top and bottom rails
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.b(sx * (L / 2 - 0.08) - 0.08, sx * (L / 2 - 0.08) + 0.08, sy * (W / 2 - 0.08) - 0.08, sy * (W / 2 - 0.08) + 0.08, 0.0, H, 'frame')
    for sy in (-1, 1):
        m.b(-L / 2, L / 2, sy * (W / 2 - 0.08) - 0.08, sy * (W / 2 - 0.08) + 0.08, 0.0, 0.14, 'frame')
        m.b(-L / 2, L / 2, sy * (W / 2 - 0.08) - 0.08, sy * (W / 2 - 0.08) + 0.08, H - 0.14, H, 'frame')
    for sx in (-1, 1):
        m.b(sx * (L / 2 - 0.08) - 0.08, sx * (L / 2 - 0.08) + 0.08, -W / 2, W / 2, 0.0, 0.14, 'frame')
        m.b(sx * (L / 2 - 0.08) - 0.08, sx * (L / 2 - 0.08) + 0.08, -W / 2, W / 2, H - 0.14, H, 'frame')
    m.b(-L / 2 + 0.16, L / 2 - 0.16, -W / 2 + 0.16, W / 2 - 0.16, H - 0.1, H - 0.02, paint)  # roof
    for yy in (-0.8, 0.0, 0.8): m.b(-L / 2 + 0.2, L / 2 - 0.2, yy - 0.05, yy + 0.05, H - 0.1, H - 0.0, 'frame')    # roof ribs
    # door end on +x: two leaves, four locking bars, a seam
    m.b(L / 2 - 0.06, L / 2 + 0.03, -W / 2 + 0.16, W / 2 - 0.16, 0.14, H - 0.14, paint)
    for yy in (-0.55, 0.55):
        for k in (-0.17, 0.17): m.rd((L / 2 + 0.05, yy + k, 0.2), (L / 2 + 0.05, yy + k, H - 0.2), 0.022, 'steel', 4)
        m.b(L / 2 + 0.03, L / 2 + 0.08, yy - 0.2, yy + 0.2, H * 0.5 - 0.1, H * 0.5 + 0.1, 'steel')   # cam handle plate
    m.b(L / 2 + 0.03, L / 2 + 0.07, -0.015, 0.015, 0.14, H - 0.14, 'frame')
    m.door('+x', 0.0, 2.34, 2.3)
    return m


def lamp_post():
    m = M('lamp_post')
    m.c(0.22, 0.15, (0, 0, 0), 'concrete2', 8)
    m.c(0.11, 6.85, (0, 0, 0.15), 'metal_d', 8, r2=0.06)
    m.rd((0, 0, 6.75), (0.6, 0, 7.0), 0.045, 'metal_d', 6); m.rd((0.6, 0, 7.0), (1.7, 0, 7.0), 0.045, 'metal_d', 6)
    m.b(1.3, 2.1, -0.18, 0.18, 6.86, 7.0, 'metal_g')                                  # lamp head
    m.b(1.35, 2.05, -0.14, 0.14, 6.82, 6.88, 'lens')
    m.b(-0.1, 0.1, -0.08, 0.08, 0.8, 1.3, 'metal_g')                                    # access hatch
    return m


def quay_bollard():
    m = M('quay_bollard')
    prof = [(0.34, 0.0), (0.34, 0.06), (0.27, 0.1), (0.19, 0.12), (0.18, 0.55), (0.24, 0.62), (0.25, 0.75), (0.2, 0.9), (0.0, 0.9)]
    m.add(lathe(prof, 12, mt('black'), 'b'))
    m.c(0.3, 0.05, (0, 0, 0.0), 'concrete2', 12)
    m.b(-0.09, 0.09, -0.3, 0.3, 0.1, 0.17, 'rust')
    return m


def fence_section():
    m = M('fence_section'); L, H = 4.0, 2.0
    for sx in (-1, 1): m.c(0.045, H, (sx * (L / 2 - 0.05), 0, 0), 'steel', 8)
    m.c(0.04, H, (0, 0, 0), 'steel', 8)
    m.rd((-L / 2 + 0.05, 0, H - 0.04), (L / 2 - 0.05, 0, H - 0.04), 0.03, 'steel', 6)
    m.rd((-L / 2 + 0.05, 0, 0.1), (L / 2 - 0.05, 0, 0.1), 0.03, 'steel', 6)
    m.b(-L / 2 + 0.05, L / 2 - 0.05, -0.006, 0.006, 0.1, H - 0.04, 'mesh')           # translucent mesh body
    x0, x1, z0, z1 = -L / 2 + 0.07, L / 2 - 0.07, 0.12, H - 0.06
    step = 0.4
    nlines = int(((x1 - x0) + (z1 - z0)) / step) + 1
    for sgn in (1, -1):                                                                # diamond wire pattern, both diagonals
        for d in range(nlines):
            c0 = d * step
            if sgn > 0: fz = lambda x: z0 - (x1 - x0) + c0 + (x - x0)
            else: fz = lambda x: z1 + (x1 - x0) - c0 - (x - x0)
            ax, bx = x0, x1; az, bz = fz(ax), fz(bx)
            ta, tb = (z0 - az) / (bz - az), (z1 - az) / (bz - az)
            lo = max(0.0, min(ta, tb)); hi = min(1.0, max(ta, tb))
            if hi - lo > 0.03:
                m.rd((ax + (bx - ax) * lo, 0, az + (bz - az) * lo), (ax + (bx - ax) * hi, 0, az + (bz - az) * hi), 0.007, 'steel', 3)
    for sx in (-1, 1): m.c(0.06, 0.04, (sx * (L / 2 - 0.05), 0, H), 'steel', 6)
    return m


def road_barrier():
    m = M('road_barrier'); L = 3.0; n = 6
    for sx in (-1, 1):                                                                  # A-frame feet
        m.b(sx * 1.2 - 0.05, sx * 1.2 + 0.05, -0.5, 0.5, 0.0, 0.08, 'metal_d')
        m.rd((sx * 1.2, -0.45, 0.04), (sx * 1.2, 0.0, 1.0), 0.03, 'metal_d', 5); m.rd((sx * 1.2, 0.45, 0.04), (sx * 1.2, 0.0, 1.0), 0.03, 'metal_d', 5)
    for row, (z0, z1) in enumerate(((0.72, 0.97), (0.4, 0.65))):
        for i in range(n):
            k = 'red' if (i + row) % 2 == 0 else 'white'
            x0 = -L / 2 + i * L / n
            m.b(x0, x0 + L / n, -0.03, 0.03, z0, z1, k)
    m.b(-L / 2, L / 2, -0.04, 0.04, 0.97, 1.0, 'metal_d')
    return m


def pallets():
    m = M('pallets'); L, W = 1.2, 1.0
    for i in range(4):
        z0 = i * 0.375
        for yy in (-0.4, 0.0, 0.4): m.b(-L / 2, L / 2, yy - 0.05, yy + 0.05, z0, z0 + 0.09, 'wood2')    # bearers
        for xx in (-0.55, 0.0, 0.55): m.b(xx - 0.06, xx + 0.06, -W / 2, W / 2, z0 + 0.09, z0 + 0.14, 'wood')
        k = 'wrap' if i % 2 == 0 else 'cardboard'
        m.b(-L / 2 + 0.03, L / 2 - 0.03, -W / 2 + 0.03, W / 2 - 0.03, z0 + 0.14, z0 + 0.36, k, bevel=0.02)
        m.b(-L / 2 + 0.02, L / 2 - 0.02, -W / 2 + 0.02, W / 2 - 0.02, z0 + 0.2, z0 + 0.24, 'white' if i % 2 == 0 else 'door_r')
    return m


def road_sign():
    m = M('road_sign')
    m.c(0.12, 0.05, (0, 0, 0), 'concrete2', 8)
    m.c(0.04, 2.95, (0, 0, 0.05), 'steel', 8)
    m.c(0.31, 0.03, (0.05, 0, 2.55), 'white', 20, rot=(0, math.pi / 2, 0))
    m.c(0.28, 0.03, (0.07, 0, 2.55), 'red', 20, rot=(0, math.pi / 2, 0))
    m.c(0.2, 0.03, (0.09, 0, 2.55), 'white', 20, rot=(0, math.pi / 2, 0))
    m.b(0.09, 0.12, -0.15, 0.15, 2.51, 2.59, 'red')                                    # no-entry bar
    return m


ALL = [warehouse, office, hangar, workshop, house_a, house_b, house_c, guardhouse, watchtower, fuel_tank, silo,
       quay_crane, bunker, tent, lambda: container('container_red', 'c_red'), lambda: container('container_blue', 'c_blue'),
       lambda: container('container_green', 'c_green'), lambda: container('container_orange', 'c_orange'),
       lamp_post, quay_bollard, fence_section, road_barrier, pallets, road_sign]
ALL[14].__name__ = 'container_red'; ALL[15].__name__ = 'container_blue'; ALL[16].__name__ = 'container_green'; ALL[17].__name__ = 'container_orange'


def key_of(f):
    return f.__name__


reset()
only = argv[argv.index('--only') + 1].split(',') if '--only' in argv else None
objs = {}; doors = {}
for f in ALL:
    if only and key_of(f) not in only:
        continue
    mdl = f()
    o = mdl.finish(); objs[mdl.key] = o; doors[mdl.key] = mdl.doors
bpy.context.view_layer.update()


def r3(x): return round(float(x), 3)

manifest = {}; total = 0
for k, o in objs.items():
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    t = tri_count(o); total += t
    manifest[k] = dict(length_x=r3(mx.x - mn.x), width_y=r3(mx.y - mn.y), height=r3(mx.z - mn.z), tris=t, min=[r3(c) for c in mn], max=[r3(c) for c in mx], doors=doors[k])
    print('MODEL', k, manifest[k]['length_x'], 'x', manifest[k]['width_y'], 'x', manifest[k]['height'], 'tris', t, 'minz', r3(mn.z))
manifest['_total_tris'] = total
json.dump(manifest, open(os.path.join(REVIEW, 'port.json'), 'w'), indent=1)

tmp = os.path.join(tempfile.gettempdir(), 'sc_port.glb')
export_glb(list(bpy.context.scene.objects), tmp)
data = open(tmp, 'rb').read()
print('GLB bytes', len(data), 'total tris', total)
if not only:
    open(ASSET, 'w', newline='').write(base64.b64encode(data).decode('ascii'))
    print('WROTE', ASSET)

if '--review' in argv:
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light = 'FLAT'; sh.color_type = 'MATERIAL'; sh.show_object_outline = False; sh.show_cavity = False
    w = bpy.data.worlds.new('rw'); w.color = (0.74, 0.80, 0.86); sc.world = w
    sc.render.image_settings.file_format = 'PNG'
    for mtl in bpy.data.materials:
        b = mtl.node_tree.nodes['Principled BSDF']
        c = b.inputs['Base Color'].default_value
        mtl.diffuse_color = (c[0], c[1], c[2], 1)
    sh.light = 'STUDIO'
    gm = mat('ground', '#9aa18c', 1.0); gm.diffuse_color = (0.38, 0.42, 0.34, 1)
    ground = box((300, 300, 0.04), (0, 0, -0.02), (0, 0, 0), gm)
    for k, o in objs.items():
        for q in bpy.data.objects: q.hide_render = True
        o.hide_render = False; ground.hide_render = False
        mn = Vector(manifest[k]['min']); mx = Vector(manifest[k]['max']); c = (mn + mx) / 2; sz = max(mx.x - mn.x, mx.y - mn.y, mx.z - mn.z)
        cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); link(cam); sc.camera = cam
        cam.data.clip_end = 1000; cam.data.lens = 40
        sc.render.resolution_x, sc.render.resolution_y = 800, 560
        cam.location = c + Vector((0.8, -0.62, 0.42)).normalized() * sz * 2.4
        cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(REVIEW, f'{k}_3q.png')
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam)
    print('REVIEW DONE')
print('BUILD DONE')
