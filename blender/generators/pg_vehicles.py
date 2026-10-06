"""Squall Cove land vehicles. Blender 4.2, Z up, metres, every vehicle faces +X and rests on z=0.

Node contract (see blender/NOTES-vehicles.md):
  <key>                    root empty (one per vehicle; clone it and ignore its row offset)
  <key>_body               chassis + cab + fittings (one mesh)
  <key>_wheel_<FL|FR|ML|MR|RL|RR>   child of the root, origin = wheel centre, axle = local Y (Blender) = glTF Z
  <key>_seat / _cargo / _hitch      empties
Sub-nodes (mast, forks, bed, trailer, boom, hook, cable) are separate children with pivots documented in the notes.
"""
import math, bmesh, bpy
from mathutils import Vector, Matrix
from pg_core import *

PAL = {
    'white':   dict(color='#f1f1ec', rough=0.5),
    'cream':   dict(color='#e6e2d2', rough=0.6),
    'glass':   dict(color='#25394b', rough=0.12, metal=0.1),
    'tyre':    dict(color='#1b1b1d', rough=0.95),
    'steel':   dict(color='#a4abb2', rough=0.4, metal=0.5),
    'chrome':  dict(color='#c9ced3', rough=0.25, metal=0.7),
    'dark':    dict(color='#2d3034', rough=0.7),
    'black':   dict(color='#131315', rough=0.85),
    'grey':    dict(color='#8a9096', rough=0.6),
    'lgrey':   dict(color='#b6bbc0', rough=0.6),
    'green':   dict(color='#7cc23a', rough=0.45),       # reflective lime-green stripe
    'yellow':  dict(color='#ffd21a', rough=0.45),       # reflective yellow stripe
    'red':     dict(color='#c8242b', rough=0.45),
    'crossred': dict(color='#d71f27', rough=0.5),
    'navy':    dict(color='#1a376b', rough=0.5),
    'blue':    dict(color='#1f5bb0', rough=0.5),
    'orange':  dict(color='#ff7a1c', rough=0.5),
    'forkyel': dict(color='#f5b50a', rough=0.5),
    'tracgrn': dict(color='#3b8c2f', rough=0.5),
    'wheelyel': dict(color='#f1c40f', rough=0.55),
    'quadred': dict(color='#c9281f', rough=0.45),
    'wood':    dict(color='#a97d4c', rough=0.9),
    'wood2':   dict(color='#8f6638', rough=0.9),
    'wood3':   dict(color='#b88d5a', rough=0.9),
    'rubber':  dict(color='#26282a', rough=0.95),
    'hose':    dict(color='#d9a21b', rough=0.8),
    'lamp_w':  dict(color='#fff4cc', rough=0.3, emit='#fff4cc', emit_str=1.5),
    'lamp_r':  dict(color='#ff3a30', rough=0.3, emit='#ff3a30', emit_str=1.5),
    'lamp_b':  dict(color='#2f6bff', rough=0.3, emit='#2f6bff', emit_str=1.5),
    'lamp_a':  dict(color='#ffb21c', rough=0.3, emit='#ffb21c', emit_str=1.5),
}

def m(k):
    if k.startswith('#'):
        return mat('c' + k, k, 0.5)
    return mat(k, **PAL[k])


def prof(pts, y0, y1, mt, name='prof'):
    """Polygon given in the XZ plane, extruded between y0 and y1 (side profile -> solid)."""
    bm = bmesh.new()
    a = [bm.verts.new((x, y0, z)) for x, z in pts]
    b = [bm.verts.new((x, y1, z)) for x, z in pts]
    n = len(pts)
    bm.faces.new(a); bm.faces.new(b)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return obj_from_bm(bm, name, m(mt))


class VB:
    """Vehicle builder: collects parts into the body or into pivoted sub-nodes parented under one root empty."""
    def __init__(s, key, y=0.0):
        s.key = key
        s.root = bpy.data.objects.new(key, None)
        s.root.empty_display_type = 'PLAIN_AXES'; s.root.empty_display_size = 0.5
        link(s.root); s.root.location = (0, y, 0)
        s.stack = [[]]; s.piv = {}; s.nodes = []; s.byname = {}; s.wheels = []; s.empties = []

    @property
    def cur(s): return s.stack[-1]
    def begin(s): s.stack.append([])

    # ---- primitives (all append to the current group) -------------------
    def bx(s, size, loc, mt, rot=(0, 0, 0), bevel=0.0):
        o = box(size, loc, rot, m(mt), bevel); s.cur.append(o); return o
    def pr(s, pts, y0, y1, mt):
        o = prof(pts, y0, y1, mt); s.cur.append(o); return o
    def cz(s, r1, r2, h, loc, mt, seg=10):
        o = cyl(r1, r2, h, seg, loc, (0, 0, 0), m(mt)); s.cur.append(o); return o
    def cyy(s, r, h, x, yc, z, mt, seg=10, r2=None):
        """cylinder along Y, centred on (x, yc, z)"""
        o = cyl(r, r if r2 is None else r2, h, seg, (x, yc + h / 2, z), (math.pi / 2, 0, 0), m(mt)); s.cur.append(o); return o
    def cyx(s, r, h, xc, y, z, mt, seg=10, r2=None):
        """cylinder along X, centred on (xc, y, z); r2 is the +X end radius"""
        o = cyl(r, r if r2 is None else r2, h, seg, (xc - h / 2, y, z), (0, math.pi / 2, 0), m(mt)); s.cur.append(o); return o
    def rd(s, p0, p1, r, mt, seg=5):
        o = rod(p0, p1, r, seg, m(mt)); s.cur.append(o); return o

    # ---- nodes -----------------------------------------------------------
    def end(s, name, pivot=(0, 0, 0), parent=None, rot=(0, 0, 0), local=False):
        objs = s.stack.pop()
        o = join(objs, name)
        pv = Vector(pivot)
        if not local: o.data.transform(Matrix.Translation(-pv))
        par = s.byname[parent] if parent else s.root
        ppv = s.piv[parent] if parent else Vector((0, 0, 0))
        o.parent = par; o.location = pv - ppv; o.rotation_euler = rot
        s.piv[name] = pv; s.byname[name] = o; s.nodes.append(o)
        return o

    def body(s):
        return s.end(s.key + '_body', (0, 0, 0))

    def wheel(s, tag, x, y, z, r, w, hub='steel', tyre='tyre', treads=0, seg=16, parent=None, name=None):
        s.begin()
        s.cyy(r * (0.93 if treads else 1.0), w, 0, 0, 0, tyre, seg)
        s.cyy(r * 0.6, w + 0.04, 0, 0, 0, hub, 10)
        s.cyy(r * 0.22, w + 0.075, 0, 0, 0, 'dark', 6)
        for i in range(treads):
            a = 2 * math.pi * i / treads
            R = r * 0.95
            s.bx((r * 0.1, w * 0.92, r * 2 * math.pi / treads * 0.55), (R * math.cos(a), 0, R * math.sin(a)), tyre, (0, -a, 0))
        nm = name or f'{s.key}_wheel_{tag}'
        o = s.end(nm, (x, y, z), parent, local=True)
        s.wheels.append(dict(name=nm, x=x, y=y, z=z, r=r, w=w, parent=parent))
        return o

    def arch(s, x, zc, R, zb, side, W, mt='dark', thick=0.03):
        """dark wheel-arch patch on the body side: the part of a disc (centre x,zc radius R) above the body's lower edge zb"""
        a0 = math.asin(max(-1, min(1, (zb - zc) / R)))
        pts = [(x + R * math.cos(a0 + (math.pi - 2 * a0) * i / 6), zc + R * math.sin(a0 + (math.pi - 2 * a0) * i / 6)) for i in range(7)]
        y0, y1 = (W, W + thick) if side > 0 else (-W - thick, -W)
        return s.pr(pts, y0, y1, mt)

    def emp(s, suffix, loc, parent=None, size=0.25):
        e = bpy.data.objects.new(f'{s.key}_{suffix}', None)
        e.empty_display_type = 'ARROWS'; e.empty_display_size = size
        link(e)
        pv = s.piv[parent] if parent else Vector((0, 0, 0))
        e.parent = s.byname[parent] if parent else s.root
        e.location = Vector(loc) - pv
        s.empties.append(e); return e

    def rescale_x(s, sx):
        """stretch the body and wheel spacing along X (used by the 'length' parameter)"""
        if abs(sx - 1) < 1e-6: return
        b = s.byname[s.key + '_body']
        b.data.transform(Matrix.Diagonal((sx, 1, 1, 1)))
        for w in s.wheels:
            if w['parent'] is None:
                o = s.byname[w['name']]; o.location.x *= sx; w['x'] *= sx
        for e in s.empties:
            if e.parent is s.root: e.location.x *= sx


def lamp(v, mt, size, loc): return v.bx(size, loc, mt)


# ===================================================================== 1 AMBULANCE
def ambulance(length=6.0, paint='white', y=0.0):
    v = VB('ambulance', y); W = 1.05
    v.begin() if False else None
    v.pr([(-3.0, 0.45), (3.0, 0.45), (3.0, 1.05), (2.55, 1.3), (1.9, 1.4), (1.15, 2.3), (0.95, 2.6), (-3.0, 2.6)], -W, W, paint)
    # glass
    v.bx((0.05, 1.7, 0.98), (1.548, 0, 1.869), 'glass', (0, -0.695, 0))
    for sd in (1, -1):
        v.pr([(0.88, 1.6), (1.66, 1.6), (1.17, 2.2), (0.88, 2.2)], sd * (W - 0.01) - 0.015, sd * (W + 0.025) + 0.015, 'glass')
        # stripes (yellow under green), cab to tail
        v.bx((4.7, 0.03, 0.17), (-0.62, sd * (W + 0.008), 1.07), 'yellow')
        v.bx((4.7, 0.03, 0.2), (-0.62, sd * (W + 0.008), 1.26), 'green')
        # red cross, door seam, rear window strip
        v.bx((0.62, 0.03, 0.19), (-1.35, sd * (W + 0.012), 1.95), 'crossred')
        v.bx((0.19, 0.03, 0.62), (-1.35, sd * (W + 0.012), 1.95), 'crossred')
        v.bx((0.03, 0.03, 1.55), (0.8, sd * (W + 0.006), 1.55), 'grey')
        v.bx((0.12, 0.03, 0.05), (1.0, sd * (W + 0.012), 1.65), 'dark')
        v.bx((1.0, 0.03, 0.34), (-2.2, sd * (W + 0.01), 2.1), 'glass')      # frosted patient window
        # mirrors
        v.bx((0.05, 0.16, 0.05), (1.62, sd * (W + 0.08), 1.9), 'dark')
        v.bx((0.1, 0.07, 0.28), (1.62, sd * (W + 0.17), 1.9), 'dark')
        # lamps + arch trim
        v.bx((0.04, 0.34, 0.2), (3.0, sd * 0.68, 0.92), 'lamp_w')
        v.bx((0.04, 0.2, 0.34), (-3.0, sd * 0.93, 0.98), 'lamp_r')
        v.bx((0.04, 0.12, 0.12), (2.99, sd * 0.97, 0.6), 'lamp_a')
        for ax in (1.75, -1.75):
            v.arch(ax, 0.4, 0.52, 0.45, sd, W)
    # grille, bumpers, doors
    v.bx((0.04, 0.8, 0.3), (3.01, 0, 0.78), 'dark')
    v.bx((0.22, 2.12, 0.22), (3.06, 0, 0.58), 'dark')
    v.bx((0.22, 2.12, 0.22), (-3.06, 0, 0.58), 'dark')
    v.bx((0.03, 0.03, 1.75), (-3.005, 0, 1.55), 'grey')
    for sd in (1, -1):
        v.bx((0.03, 0.62, 0.7), (-3.008, sd * 0.45, 2.05), 'glass')
        v.bx((0.04, 0.05, 0.2), (-3.015, sd * 0.1, 1.45), 'dark')
    v.bx((0.03, 2.0, 0.17), (-3.004, 0, 1.0), 'yellow'); v.bx((0.03, 2.0, 0.2), (-3.004, 0, 0.85), 'green')
    # roof: light bar, aircon, siren
    v.bx((0.4, 1.5, 0.06), (0.55, 0, 2.63), 'dark')
    v.bx((0.34, 0.7, 0.14), (0.55, 0.38, 2.73), 'lamp_r'); v.bx((0.34, 0.7, 0.14), (0.55, -0.38, 2.73), 'lamp_b')
    v.bx((0.5, 0.6, 0.12), (-1.9, 0, 2.66), 'lgrey')
    v.bx((0.12, 1.0, 0.1), (-3.0, 0, 2.62), 'lamp_a')
    # step
    v.bx((0.18, 1.2, 0.05), (-3.12, 0, 0.38), 'steel')
    v.body()
    for tag, x, yy in (('FL', 1.75, 1), ('FR', 1.75, -1), ('RL', -1.75, 1), ('RR', -1.75, -1)):
        v.wheel(tag, x, yy * 0.98, 0.40, 0.40, 0.28)
    v.emp('seat', (1.3, 0.45, 1.25)); v.emp('cargo', (-1.2, 0, 0.95)); v.emp('hitch', (-3.2, 0, 0.5))
    v.rescale_x(length / 6.38)
    return v


# ===================================================================== 2 FIRETRUCK
def firetruck(length=8.5, paint='red', y=0.0):
    v = VB('firetruck', y); r = 0.52
    v.bx((8.3, 1.1, 0.4), (0, 0, 0.85), 'dark')                         # chassis frame
    for ax in (2.8, -1.4, -2.8):
        v.cyy(0.12, 2.0, ax, 0, 0.52, 'steel', 8)
    v.pr([(4.25, 1.05), (4.25, 2.5), (3.95, 3.25), (1.3, 3.25), (1.3, 1.05)], -1.2, 1.2, paint)   # cab
    v.bx((5.5, 2.5, 1.9), (-1.5, 0, 2.0), paint)                         # equipment body
    v.bx((0.04, 2.0, 0.66), (4.12, 0, 2.89), 'glass', (0, -0.38, 0))
    for sd in (1, -1):
        v.pr([(2.0, 2.25), (3.85, 2.25), (3.75, 3.05), (2.0, 3.05)], sd * 1.18, sd * 1.23, 'glass')
        v.bx((0.04, 0.03, 0.5), (2.0, sd * 1.22, 1.85), 'dark')
        v.bx((2.85, 0.03, 0.2), (2.8, sd * 1.215, 2.0), 'white')          # white stripe, cab
        v.bx((5.52, 0.03, 0.2), (-1.5, sd * 1.255, 2.55), 'white')        # white stripe, body
        v.bx((5.52, 0.03, 0.1), (-1.5, sd * 1.255, 2.38), 'yellow')
        for cx in (-3.4, -2.0, -0.6):
            v.bx((1.3, 0.04, 1.05), (cx, sd * 1.26, 1.75), 'lgrey')         # roller shutters
            for k in range(3):
                v.bx((1.3, 0.05, 0.03), (cx, sd * 1.265, 1.4 + k * 0.3), 'grey')
        v.bx((0.2, 0.05, 0.5), (0.8, sd * 1.265, 1.8), 'dark')              # pump panel
        v.cyy(0.07, 0.12, 0.8, sd * 1.3, 1.9, 'chrome', 6)
        # lamps, mirrors, steps
        v.bx((0.05, 0.4, 0.25), (4.25, sd * 0.8, 1.55), 'lamp_w')
        v.bx((0.05, 0.12, 0.25), (-4.26, sd * 1.05, 1.5), 'lamp_r')
        v.bx((0.05, 0.14, 0.05), (3.75, sd * 1.3, 2.6), 'dark'); v.bx((0.1, 0.07, 0.4), (3.75, sd * 1.4, 2.5), 'dark')
        v.bx((0.5, 0.2, 0.06), (3.0, sd * 1.25, 0.95), 'steel')           # cab step
        v.cz(0.07, 0.07, 1.4, (-4.28, sd * 0.95, 1.1), 'chrome', 6)          # rear handrails
        v.bx((0.4, 0.04, 0.3), (-4.0, sd * 0.85, 0.65), 'rubber')            # mud flaps
        v.cz(0.08, 0.08, 2.4, (-4.2, sd * 1.0, 1.4), 'chrome', 6) if False else None
        # beacons
        v.cz(0.1, 0.08, 0.14, (3.9, sd * 1.05, 3.25), 'lamp_a', 8)
    # front bumper, grille
    v.bx((0.3, 2.45, 0.3), (4.35, 0, 0.85), 'chrome')
    v.bx((0.03, 1.4, 0.55), (4.26, 0, 1.6), 'dark')
    v.bx((0.5, 2.5, 0.07), (-4.5, 0, 0.78), 'steel')                       # rear step
    v.bx((0.03, 2.2, 0.3), (-4.26, 0, 1.2), 'yellow'); v.bx((0.03, 2.2, 0.1), (-4.26, 0, 1.4), 'white')
    # roof lights
    v.bx((0.4, 1.8, 0.07), (2.4, 0, 3.28), 'dark')
    v.bx((0.34, 0.85, 0.15), (2.4, 0.45, 3.37), 'lamp_r'); v.bx((0.34, 0.85, 0.15), (2.4, -0.45, 3.37), 'lamp_r')
    v.bx((0.9, 0.5, 0.05), (1.2, 0, 3.0), 'dark') if False else None
    # ladder on the body roof (left half), hose reel (right half)
    for yy in (-0.83, -0.27):
        v.bx((5.0, 0.05, 0.07), (-1.5, yy, 3.12), 'steel')
    for i in range(13):
        v.bx((0.04, 0.6, 0.04), (-3.9 + i * 0.4, -0.55, 3.12), 'steel')
    for cx in (-3.5, -0.2):
        v.bx((0.12, 0.12, 0.12), (cx, -0.55, 3.0), 'dark'); v.bx((0.12, 0.5, 0.06), (cx, -0.55, 3.04), 'dark')
    v.cyy(0.45, 0.05, -3.3, 0.22, 3.5, 'steel', 12); v.cyy(0.45, 0.05, -3.3, 0.98, 3.5, 'steel', 12)
    v.cyy(0.42, 0.7, -3.3, 0.6, 3.5, 'hose', 12); v.cyy(0.14, 0.78, -3.3, 0.6, 3.5, 'chrome', 6)
    v.bx((0.1, 0.1, 0.5), (-3.3, 0.22, 3.2), 'dark'); v.bx((0.1, 0.1, 0.5), (-3.3, 0.98, 3.2), 'dark')
    v.bx((0.08, 0.76, 0.08), (-2.75, 0.6, 3.48), 'hose')
    v.body()
    for tag, x, yy in (('FL', 2.8, 1), ('FR', 2.8, -1), ('ML', -1.4, 1), ('MR', -1.4, -1), ('RL', -2.8, 1), ('RR', -2.8, -1)):
        v.wheel(tag, x, yy * 0.97, r, r, 0.38, hub='steel', treads=0, seg=16)
    v.emp('seat', (3.0, 0.55, 1.65)); v.emp('cargo', (-1.5, 0, 3.0)); v.emp('hitch', (-4.7, 0, 0.8))
    v.rescale_x(length / 9.25)
    return v


# ===================================================================== 3 FORKLIFT
def forklift(length=3.2, paint='forkyel', y=0.0):
    v = VB('forklift', y)
    v.bx((1.2, 0.76, 0.5), (0.25, 0, 0.55), paint, bevel=0.03)                       # mid body
    v.bx((0.75, 1.1, 0.7), (-0.65, 0, 0.88), paint, bevel=0.05)                      # counterweight
    v.bx((0.3, 0.8, 0.55), (0.6, 0, 0.98), paint, bevel=0.02)                        # dash housing
    v.bx((0.6, 1.0, 0.12), (-0.25, 0, 0.82), 'dark')                                 # floor plate
    v.bx((0.5, 0.5, 0.1), (-0.05, 0, 0.97), 'black', bevel=0.02)                     # seat
    v.bx((0.08, 0.5, 0.5), (-0.3, 0, 1.25), 'black', (0, 0.15, 0), bevel=0.02)
    v.cz(0.015, 0.015, 0.4, (0.5, 0, 1.3), 'dark', 6)
    v.cyx(0.12, 0.03, 0.46, 0, 1.78 - 0.18, 'black', 10) if False else None
    # steering wheel (tilted disc) + column
    v.rd((0.62, 0, 1.2), (0.45, 0, 1.5), 0.025, 'dark')
    v.cyx(0.13, 0.03, 0.44, 0, 1.52, 'black', 10)
    for sd in (1, -1):
        v.bx((0.65, 0.3, 0.05), (0.72, sd * 0.52, 0.7), paint)                       # front mudguards
        v.bx((0.2, 0.3, 0.05), (1.1, sd * 0.52, 0.66), paint, (0, -0.35, 0)) if False else None
        # overhead guard posts and roof
        v.bx((0.06, 0.06, 1.25), (0.6, sd * 0.46, 1.5), 'dark')
        v.bx((0.06, 0.06, 1.2), (-0.35, sd * 0.46, 1.5), 'dark')
        v.bx((0.04, 0.04, 0.2), (0.3, sd * 0.46, 1.9), 'dark', (0, 0.0, 0)) if False else None
        v.bx((0.1, 0.12, 0.08), (-0.99, sd * 0.4, 0.95), 'lamp_r')                   # tail lamps
        v.bx((0.06, 0.1, 0.1), (0.78, sd * 0.3, 1.05), 'lamp_w')                      # work lamps
        v.bx((0.1, 0.14, 0.12), (1.0, sd * 0.3, 0.55), 'dark')                       # lift cylinder support
    v.bx((1.1, 1.05, 0.05), (0.12, 0, 2.15), 'dark')
    for k in range(5):
        v.bx((0.06, 1.05, 0.03), (-0.28 + k * 0.2, 0, 2.19), 'dark')
    v.cz(0.07, 0.07, 0.1, (-0.2, 0.35, 2.17), 'lamp_a', 8)                           # beacon
    v.bx((0.04, 0.5, 0.3), (-1.03, 0, 0.9), 'dark')                                  # counterweight plate
    v.bx((0.1, 0.1, 0.25), (-0.1, -0.5, 0.45), 'dark')                               # step
    v.bx((0.3, 0.2, 0.04), (0.1, -0.55, 0.52), 'steel')
    v.body()
    for tag, x, yy, r, w in (('FL', 0.7, 1, 0.34, 0.26), ('FR', 0.7, -1, 0.34, 0.26), ('RL', -0.7, 1, 0.24, 0.2), ('RR', -0.7, -1, 0.24, 0.2)):
        v.wheel(tag, x, yy * (0.53 if x > 0 else 0.4), r, r, w, hub='dark', seg=12)
    # mast: two channel uprights + cross bars; pivot at the base for tilt
    v.begin()
    for sd in (1, -1):
        v.bx((0.1, 0.1, 2.1), (1.05, sd * 0.32, 1.4), 'dark')
        v.bx((0.06, 0.14, 1.9), (1.13, sd * 0.32, 1.5), 'steel')
    v.bx((0.1, 0.84, 0.1), (1.05, 0, 2.38), 'dark'); v.bx((0.1, 0.84, 0.1), (1.05, 0, 0.5), 'dark')
    v.bx((0.1, 0.84, 0.08), (1.05, 0, 1.4), 'dark')
    v.cz(0.05, 0.05, 1.7, (0.98, 0.0, 0.5), 'chrome', 6)
    v.end('forklift_mast', (1.05, 0, 0.5))
    # forks + carriage + backrest: pivot at the fork heel on the floor, child of the mast
    v.begin()
    v.bx((0.05, 0.9, 0.5), (1.19, 0, 0.35), 'dark')
    for sd in (1, -1):
        v.bx((1.0, 0.11, 0.05), (1.7, sd * 0.3, 0.075), 'steel')
        v.bx((0.06, 0.11, 0.7), (1.2, sd * 0.3, 0.4), 'steel')
        v.bx((0.04, 0.05, 0.9), (1.17, sd * 0.38, 0.95), 'dark')
        v.bx((0.04, 0.05, 0.9), (1.17, sd * 0.1, 0.95), 'dark')
    for zz in (0.55, 1.0, 1.4):
        v.bx((0.04, 0.9, 0.05), (1.17, 0, zz), 'dark')
    v.end('forklift_forks', (1.2, 0, 0.05), 'forklift_mast')
    v.emp('seat', (-0.05, 0, 1.05)); v.emp('cargo', (1.7, 0, 0.1), 'forklift_forks')
    v.rescale_x(1.0)
    return v


# ===================================================================== 4 CARGO TRUCK
def cargotruck(length=7.0, paint='navy', y=0.0):
    v = VB('cargotruck', y)
    v.bx((6.9, 1.0, 0.35), (0, 0, 0.92), 'dark')                                      # chassis rails
    for ax in (2.1, -2.1):
        v.cyy(0.11, 2.0, ax, 0, 0.5, 'steel', 8)
    v.pr([(3.5, 1.08), (3.5, 2.35), (3.15, 3.05), (1.5, 3.05), (1.5, 1.08)], -1.2, 1.2, paint)
    v.bx((0.04, 2.0, 0.72), (3.35, 0, 2.7), 'glass', (0, -0.42, 0))
    for sd in (1, -1):
        v.pr([(1.8, 2.15), (3.1, 2.15), (3.0, 2.95), (1.8, 2.95)], sd * 1.18, sd * 1.225, 'glass')
        v.bx((0.04, 0.03, 0.5), (1.65, sd * 1.22, 1.6), 'dark')
        v.bx((0.5, 0.03, 0.55), (2.2, sd * 1.21, 1.55), 'dark', (0, 0, 0)) if False else None
        v.bx((1.9, 0.03, 0.14), (2.5, sd * 1.215, 1.5), 'white')                      # cab stripe
        v.bx((0.04, 0.4, 0.28), (3.5, sd * 0.78, 1.6), 'lamp_w')
        v.bx((0.5, 0.45, 0.1), (2.1, sd * 1.05, 1.15), paint)                         # fender over front wheel
        v.bx((0.05, 0.14, 0.05), (3.0, sd * 1.3, 2.6), 'dark'); v.bx((0.1, 0.07, 0.42), (3.0, sd * 1.4, 2.45), 'dark')
        v.cz(0.07, 0.07, 2.4, (1.35, sd * 1.0, 1.0), 'chrome', 8)                    # exhaust stacks
        v.cyx(0.3, 1.1, 0.0, sd * 0.95, 0.8, 'steel', 10)                             # fuel tanks
        v.bx((0.35, 0.04, 0.4), (-2.6, sd * 0.85, 0.75), 'rubber')                    # mud flaps
        v.bx((0.04, 0.3, 0.14), (-3.5, sd * 0.9, 1.0), 'lamp_r')
        v.bx((0.4, 0.5, 0.06), (3.0, sd * 1.05, 0.95), 'steel')                       # cab steps
    v.bx((0.3, 2.45, 0.3), (3.62, 0, 0.9), 'chrome')
    v.bx((0.03, 1.5, 0.6), (3.51, 0, 1.75), 'dark')
    v.bx((0.5, 2.0, 0.1), (3.75, 0, 0.5), 'dark') if False else None
    v.cz(0.1, 0.08, 0.14, (2.5, 0, 3.05), 'lamp_a', 8)
    v.bx((0.5, 2.2, 0.15), (-3.6, 0, 0.8), 'dark')                                    # rear bumper
    v.body()
    for tag, x, yy in (('FL', 2.1, 1), ('FR', 2.1, -1), ('RL', -2.1, 1), ('RR', -2.1, -1)):
        v.wheel(tag, x, yy * 0.98, 0.5, 0.5, 0.36 if x > 0 else 0.42, hub='steel', treads=0)
    # flatbed: deck, side boards, stakes; pivot = centre of the deck surface
    v.begin()
    v.bx((4.6, 2.5, 0.2), (-1.1, 0, 1.2), 'grey')
    v.bx((4.6, 2.3, 0.06), (-1.1, 0, 1.33), 'lgrey')
    for sd in (1, -1):
        v.bx((4.6, 0.06, 0.45), (-1.1, sd * 1.22, 1.55), 'wood')
        v.bx((4.6, 0.07, 0.1), (-1.1, sd * 1.22, 1.88), 'steel')
        v.bx((4.6, 0.04, 0.12), (-1.1, sd * 1.25, 1.15), 'red') if False else None
        for k in range(7):
            v.bx((0.1, 0.09, 0.66), (-3.3 + k * 0.7333, sd * 1.24, 1.6), 'steel')
    v.bx((0.1, 2.5, 1.0), (1.1, 0, 1.78), 'steel')
    for k in range(3):
        v.bx((0.12, 2.3, 0.1), (1.1, 0, 1.5 + k * 0.28), 'dark')
    v.bx((0.06, 2.4, 0.45), (-3.4, 0, 1.55), 'wood')
    v.bx((0.1, 2.5, 0.07), (-3.4, 0, 1.82), 'steel')
    v.bx((0.1, 2.4, 0.12), (-3.45, 0, 1.0), 'red')
    v.end('cargotruck_bed', (-1.1, 0, 1.3))
    v.emp('cargo', (0, 0, 0), 'cargotruck_bed')
    v.emp('seat', (2.3, 0.5, 1.75)); v.emp('hitch', (-3.7, 0, 0.9))
    v.rescale_x(1.0)
    return v


# ===================================================================== 5 PATROL CAR
def patrolcar(length=4.8, paint='white', y=0.0):
    v = VB('patrolcar', y); W = 0.95
    v.pr([(-2.4, 0.4), (2.4, 0.4), (2.4, 0.9), (2.2, 1.05), (1.25, 1.12), (-2.15, 1.12), (-2.4, 1.0)], -W, W, paint)
    v.pr([(1.25, 1.1), (0.7, 1.76), (-2.15, 1.76), (-2.4, 1.1)], -0.86, 0.86, 'glass')                    # greenhouse
    v.bx((2.9, 1.9, 0.07), (-0.72, 0, 1.8), paint, bevel=0.02)                                           # roof
    v.bx((0.14, 1.78, 0.7), (-0.5, 0, 1.43), paint)                                                      # B pillar
    v.bx((0.2, 1.78, 0.7), (-2.3, 0, 1.43), paint)                                                       # D pillar
    for sd in (1, -1):
        v.rd((1.25, sd * 0.86, 1.08), (0.7, sd * 0.86, 1.78), 0.05, paint)
        v.bx((4.7, 0.03, 0.26), (0.0, sd * (W + 0.008), 0.72), 'blue')                                   # blue band
        v.bx((0.04, 0.34, 0.16), (2.4, sd * 0.62, 0.78), 'lamp_w')
        v.bx((0.04, 0.2, 0.14), (-2.4, sd * 0.78, 0.85), 'lamp_r')
        v.bx((0.1, 0.07, 0.22), (1.0, sd * (W + 0.15), 1.3), 'dark'); v.bx((0.05, 0.12, 0.05), (1.0, sd * (W + 0.07), 1.25), 'dark')
        v.bx((0.03, 0.03, 0.55), (0.35, sd * (W + 0.006), 0.8), 'grey')
        v.bx((0.03, 0.03, 0.55), (-1.2, sd * (W + 0.006), 0.8), 'grey')
        v.cyy(0.1, 0.03, 1.05, sd * (W + 0.012), 0.72, 'yellow', 10)                                      # crest on the front doors
        v.cyy(0.065, 0.035, 1.05, sd * (W + 0.014), 0.72, 'navy', 8)
        for ax in (1.4, -1.4):
            v.arch(ax, 0.37, 0.48, 0.4, sd, W)
        v.bx((0.1, 0.1, 0.3), (-1.0, sd * 0.4, 1.9), 'steel') if False else None
    v.bx((0.03, 1.0, 0.25), (2.401, 0, 0.78), 'dark')
    v.bx((0.2, 1.8, 0.2), (2.45, 0, 0.5), 'dark'); v.bx((0.2, 1.8, 0.2), (-2.45, 0, 0.5), 'dark')
    v.cyy(0.18, 0.03, 2.402, 0.0, 0.98, 'yellow', 10) if False else None
    v.cyx(0.12, 0.03, 2.39, 0, 0.92, 'yellow', 10)
    v.cyx(0.08, 0.034, 2.39, 0, 0.92, 'navy', 8)
    v.bx((0.4, 0.07, 0.7), (-2.43, 0, 0.9), 'dark', (0, 0, 0)) if False else None
    # roof light bar and spotlight
    v.bx((0.4, 1.35, 0.05), (0.0, 0, 1.87), 'dark')
    v.bx((0.34, 0.7, 0.13), (0.0, 0.35, 1.95), 'lamp_b'); v.bx((0.34, 0.7, 0.13), (0.0, -0.35, 1.95), 'lamp_w')
    v.bx((0.1, 0.8, 0.05), (-2.0, 0, 1.87), 'dark'); v.bx((0.08, 0.5, 0.06), (-2.0, 0, 1.9), 'lamp_b')   # rear deck bar
    v.bx((0.6, 0.3, 0.06), (-2.15, 0, 1.0), 'dark')
    v.body()
    for tag, x, yy in (('FL', 1.4, 1), ('FR', 1.4, -1), ('RL', -1.4, 1), ('RR', -1.4, -1)):
        v.wheel(tag, x, yy * 0.86, 0.37, 0.37, 0.25, hub='lgrey')
    v.emp('seat', (0.85, 0.4, 1.0)); v.emp('cargo', (-1.5, 0, 1.1)); v.emp('hitch', (-2.6, 0, 0.5))
    v.rescale_x(length / 4.8)
    return v


# ===================================================================== 6 TRACTOR
def tractor(length=4.0, paint='tracgrn', y=0.0):
    v = VB('tractor', y)
    v.pr([(0.3, 0.7), (2.0, 0.7), (2.0, 1.4), (1.65, 1.6), (0.3, 1.6)], -0.38, 0.38, paint)         # hood
    v.bx((0.5, 0.5, 0.45), (-0.0, 0, 0.95), 'dark')                                                 # engine / gearbox
    v.bx((0.3, 0.75, 0.4), (2.0, 0, 0.7), 'dark')                                                   # front weight
    v.bx((0.03, 0.55, 0.55), (2.01, 0, 1.2), 'dark')                                                # grille
    v.bx((0.1, 1.2, 0.18), (2.03, 0, 0.62), 'steel') if False else None
    v.cyy(0.1, 1.5, 0.95, 0, 0.45, 'steel', 8); v.cyy(0.12, 2.0, -0.95, 0, 0.75, 'steel', 8)        # axle housings
    v.bx((1.7, 1.2, 0.12), (-0.55, 0, 0.98), paint)                                                  # cab floor
    v.bx((0.5, 0.9, 0.4), (-1.0, 0, 1.2), paint)                                                     # rear housing
    # cab: posts, roof, glazing
    for px in (0.3, -1.35):
        for sd in (1, -1):
            v.bx((0.07, 0.07, 1.85), (px, sd * 0.68, 1.95), paint)
    v.bx((1.9, 1.5, 0.1), (-0.52, 0, 2.95), paint, bevel=0.02)
    for sd in (1, -1):
        v.bx((1.5, 0.03, 1.6), (-0.52, sd * 0.69, 1.93), 'glass')
        v.bx((0.07, 0.07, 1.6), (-0.52, sd * 0.69, 1.93), paint)
    v.bx((0.03, 1.3, 1.6), (0.31, 0, 1.93), 'glass'); v.bx((0.03, 1.3, 1.6), (-1.36, 0, 1.93), 'glass')
    v.bx((0.5, 0.45, 0.15), (-0.8, 0, 1.17), 'black'); v.bx((0.1, 0.45, 0.5), (-1.05, 0, 1.45), 'black')   # seat
    v.rd((0.1, 0, 1.2), (0.0, 0, 1.55), 0.03, 'dark'); v.cyx(0.14, 0.03, -0.05, 0, 1.55, 'black', 10)
    v.bx((0.12, 0.12, 0.12), (-0.52, 0, 3.06), 'lamp_a')
    for sd in (1, -1):
        # rear fenders (flat + angled ends)
        v.bx((0.7, 0.55, 0.07), (-0.95, sd * 1.0, 1.6), paint)
        v.bx((0.45, 0.55, 0.07), (-0.4, sd * 1.0, 1.52), paint, (0, 0.5, 0))
        v.bx((0.45, 0.55, 0.07), (-1.5, sd * 1.0, 1.52), paint, (0, -0.5, 0))
        v.bx((0.05, 0.05, 0.14), (-0.95, sd * 1.22, 1.55), paint) if False else None
        v.bx((0.05, 0.28, 0.1), (2.05, sd * 0.45, 1.2), 'lamp_w')
        v.cz(0.05, 0.05, 0.9, (1.1, sd * 0.2 if sd > 0 else 0.0, 1.6), 'dark', 6) if sd > 0 else None   # exhaust
    v.cz(0.08, 0.08, 0.07, (1.1, 0.2, 2.5), 'dark', 6)
    v.bx((0.5, 0.14, 0.1), (-1.7, 0, 0.55), 'dark'); v.bx((0.1, 0.18, 0.2), (-1.92, 0, 0.58), 'steel')   # drawbar + hitch
    v.body()
    for tag, x, yy, r, w, tr, hub in (('FL', 0.95, 1, 0.45, 0.26, 12, 'wheelyel'), ('FR', 0.95, -1, 0.45, 0.26, 12, 'wheelyel'),
                                     ('RL', -0.95, 1, 0.75, 0.46, 14, 'wheelyel'), ('RR', -0.95, -1, 0.75, 0.46, 14, 'wheelyel')):
        v.wheel(tag, x, yy * (0.7 if x > 0 else 1.0), r, r, w, hub=hub, treads=tr)
    # trailer: hitch pivot, A-frame tongue, deck, boards; wheels are its children
    HP = (-1.95, 0, 0.58)
    v.begin()
    v.rd((-1.95, 0, 0.62), (-2.8, 0.55, 0.78), 0.04, 'dark'); v.rd((-1.95, 0, 0.62), (-2.8, -0.55, 0.78), 0.04, 'dark')
    v.cz(0.06, 0.06, 0.12, (-1.95, 0, 0.52), 'steel', 8)
    v.bx((2.5, 1.7, 0.1), (-3.75, 0, 0.82), 'wood2')
    v.bx((2.5, 0.1, 0.12), (-3.75, 0.5, 0.74), 'dark'); v.bx((2.5, 0.1, 0.12), (-3.75, -0.5, 0.74), 'dark')
    for sd in (1, -1):
        v.bx((2.5, 0.05, 0.4), (-3.75, sd * 0.85, 1.07), 'wood')
        v.bx((2.5, 0.06, 0.07), (-3.75, sd * 0.85, 1.3), 'wood2')
        for k in range(4):
            v.bx((0.08, 0.08, 0.52), (-2.6 - k * 0.8333, sd * 0.87, 1.1), 'wood2')
        v.bx((0.04, 0.12, 0.14), (-5.0, sd * 0.7, 0.9), 'lamp_r')
    v.bx((0.05, 1.7, 0.4), (-2.52, 0, 1.07), 'wood'); v.bx((0.05, 1.7, 0.4), (-5.0, 0, 1.07), 'wood')
    v.cyy(0.07, 1.7, -3.9, 0, 0.5, 'steel', 8)
    v.end('tractor_trailer', HP)
    for tag, yy in (('ML', 1), ('MR', -1)):
        v.wheel(tag, -3.9, yy * 0.98, 0.5, 0.5, 0.26, hub='wheelyel', treads=0, seg=14, parent='tractor_trailer', name=f'tractor_trailer_wheel_{tag}')
    v.emp('cargo', (-3.75, 0, 0.87), 'tractor_trailer')
    v.emp('seat', (-0.8, 0, 1.3)); v.emp('hitch', HP)
    v.rescale_x(1.0)
    return v


# ===================================================================== 7 QUAD BIKE
def quadbike(length=2.0, paint='quadred', y=0.0):
    v = VB('quadbike', y)
    v.bx((0.9, 0.36, 0.3), (0.0, 0, 0.45), 'dark')                                                   # engine + frame
    v.bx((0.75, 0.5, 0.3), (0.25, 0, 0.8), paint, bevel=0.04)                                         # tank cowl
    v.pr([(0.55, 0.55), (1.0, 0.55), (1.0, 0.72), (0.7, 0.82), (0.55, 0.82)], -0.3, 0.3, paint)   # nose
    v.bx((0.8, 1.3, 0.06), (0.62, 0, 0.64), paint) if False else None
    v.bx((0.5, 0.5, 0.15), (-0.2, 0, 0.9), 'black', bevel=0.04)                                       # seat
    v.bx((0.65, 0.5, 0.2), (-0.55, 0, 0.7), paint, bevel=0.03)                                        # rear body
    v.bx((0.62, 1.3, 0.07), (0.62, 0, 0.64), paint); v.bx((0.72, 1.3, 0.07), (-0.62, 0, 0.64), paint)   # fenders joined across
    v.bx((0.5, 0.5, 0.03), (-0.75, 0, 0.86), 'dark')                                                # rear rack plate
    v.bx((0.4, 0.5, 0.03), (0.88, 0, 0.8), 'dark')                                                  # front rack
    for sd in (1, -1):
        v.bx((0.75, 0.3, 0.06), (0.62, sd * 0.47, 0.63), paint) if False else None
        v.bx((0.12, 0.3, 0.06), (1.0, sd * 0.5, 0.6), paint, (0, 0.5, 0))
        v.bx((0.45, 0.3, 0.06), (0.1, sd * 0.5, 0.3), 'dark') if False else None
        v.bx((0.12, 0.3, 0.06), (-1.0, sd * 0.5, 0.6), paint, (0, -0.5, 0))
        v.bx((0.5, 0.22, 0.05), (0.0, sd * 0.4, 0.32), 'steel')                                      # footboards
        v.bx((0.4, 0.03, 0.06), (0.88, sd * 0.25, 0.86), 'dark'); v.bx((0.5, 0.03, 0.06), (-0.75, sd * 0.25, 0.9), 'dark')   # rack rails
        v.rd((0.9, sd * 0.2, 0.84), (0.9, sd * 0.2, 0.9), 0.02, 'dark') if False else None
        v.bx((0.1, 0.2, 0.15), (0.97, sd * 0.2, 0.7), 'lamp_w') if False else None
        v.bx((0.05, 0.14, 0.12), (0.97, sd * 0.22, 0.68), 'lamp_w')
        v.bx((0.04, 0.14, 0.1), (-1.0, sd * 0.2, 0.7), 'lamp_r') if False else None
    v.bx((0.04, 0.12, 0.1), (-0.99, 0.2, 0.7), 'lamp_r'); v.bx((0.04, 0.12, 0.1), (-0.99, -0.2, 0.7), 'lamp_r')
    # handlebar
    v.rd((0.5, 0, 0.9), (0.45, 0, 1.12), 0.03, 'dark')
    v.bx((0.05, 0.8, 0.05), (0.45, 0, 1.14), 'dark')
    for sd in (1, -1):
        v.cyy(0.035, 0.12, 0.45, sd * 0.4, 1.14, 'black', 6)
        v.bx((0.08, 0.04, 0.06), (0.4, sd * 0.28, 1.19), 'dark')
    v.bx((0.1, 0.22, 0.12), (0.48, 0, 1.17), 'dark')
    v.bx((0.4, 0.04, 0.04), (-0.9, 0.0, 0.5), 'steel') if False else None
    v.cyx(0.05, 0.4, -0.85, 0.15, 0.45, 'steel', 6)                                                  # exhaust
    v.cyy(0.06, 1.1, 0.62, 0, 0.28, 'steel', 6); v.cyy(0.06, 1.1, -0.62, 0, 0.28, 'steel', 6)
    v.body()
    for tag, x, yy in (('FL', 0.62, 1), ('FR', 0.62, -1), ('RL', -0.62, 1), ('RR', -0.62, -1)):
        v.wheel(tag, x, yy * 0.54, 0.28, 0.28, 0.24, hub='lgrey', treads=10, seg=12)
    v.emp('seat', (-0.2, 0, 1.0)); v.emp('cargo', (-0.75, 0, 0.9)); v.emp('hitch', (-1.05, 0, 0.45))
    v.rescale_x(length / 2.0)
    return v


# ===================================================================== 8 HAND CART
def handcart(length=1.6, paint='wood', y=0.0):
    v = VB('handcart', y)
    # tray: slatted floor, sloped sides, front and back boards
    for i in range(6):
        v.bx((0.23, 0.74, 0.04), (-0.45 + i * 0.255, 0, 0.5), ['wood', 'wood3'][i % 2])
    for sd in (1, -1):
        v.bx((1.4, 0.04, 0.3), (0.1, sd * 0.38, 0.65), 'wood2', (sd * 0.15, 0, 0))
        v.bx((1.4, 0.05, 0.05), (0.1, sd * 0.43, 0.8), 'wood3', (sd * 0.15, 0, 0))
        v.rd((-0.6, sd * 0.3, 0.9), (0.8, sd * 0.3, 0.52), 0.035, 'wood3', 6)                      # handle / long member
        v.bx((0.12, 0.08, 0.12), (-0.82, sd * 0.3, 0.92), 'rubber') if False else None
        v.cyx(0.04, 0.2, -0.78, sd * 0.3, 0.93, 'rubber', 6)                                       # grips
        v.rd((-0.6, sd * 0.3, 0.88), (-0.55, sd * 0.3, 0.0), 0.03, 'dark', 6)                       # stand legs
        v.bx((0.1, 0.1, 0.03), (-0.55, sd * 0.3, 0.015), 'dark')
    v.bx((0.05, 0.8, 0.3), (0.8, 0, 0.66), 'wood2')
    v.bx((0.05, 0.8, 0.26), (-0.62, 0, 0.64), 'wood2')
    v.cyy(0.025, 0.95, 0.0, 0, 0.3, 'steel', 6)                                                      # axle
    v.bx((0.6, 0.05, 0.05), (0.25, 0, 0.44), 'dark') if False else None
    v.bx((0.08, 0.8, 0.06), (0.0, 0, 0.43), 'dark')
    v.body()
    for tag, yy in (('ML', 1), ('MR', -1)):
        v.wheel(tag, 0.0, yy * 0.5, 0.3, 0.3, 0.07, hub='steel', treads=0, seg=12)
    v.emp('seat', (-0.8, 0, 0.95)); v.emp('cargo', (0.1, 0, 0.55)); v.emp('hitch', (-0.85, 0, 0.9))
    v.rescale_x(length / 1.6)
    return v


# ===================================================================== 9 CRANE TRUCK
def cranetruck(length=9.0, paint='orange', y=0.0):
    v = VB('cranetruck', y)
    v.bx((8.8, 1.1, 0.4), (0, 0, 1.0), 'dark')
    for ax in (3.0, -1.6, -3.0):
        v.cyy(0.12, 2.0, ax, 0, 0.6, 'steel', 8)
    v.pr([(4.5, 1.25), (4.5, 2.65), (4.1, 3.45), (2.3, 3.45), (2.3, 1.25)], -1.25, 1.25, paint)
    v.bx((0.04, 2.1, 0.82), (4.34, 0, 3.05), 'glass', (0, -0.42, 0))
    v.bx((6.5, 2.5, 0.38), (-1.35, 0, 1.45), 'yellow')                                              # deck
    v.bx((6.5, 2.46, 0.1), (-1.35, 0, 1.68), 'dark')
    for sd in (1, -1):
        v.pr([(2.5, 2.45), (4.0, 2.45), (3.9, 3.3), (2.5, 3.3)], sd * 1.23, sd * 1.28, 'glass')
        v.bx((0.04, 0.03, 0.5), (2.5, sd * 1.27, 1.9), 'dark')
        v.bx((2.0, 0.03, 0.16), (3.4, sd * 1.265, 1.8), 'yellow')
        v.bx((0.5, 0.45, 0.1), (3.0, sd * 1.05, 1.28), paint)
        v.bx((0.05, 0.4, 0.28), (4.5, sd * 0.8, 1.8), 'lamp_w')
        v.bx((0.05, 0.16, 0.05), (4.05, sd * 1.3, 2.9), 'dark'); v.bx((0.1, 0.07, 0.45), (4.05, sd * 1.4, 2.75), 'dark')
        v.bx((0.5, 0.5, 0.06), (3.4, sd * 1.25, 1.1), 'steel')
        v.cz(0.08, 0.08, 2.8, (2.15, sd * 1.05, 1.25), 'chrome', 8)
        v.bx((0.3, 0.04, 0.35), (-4.1, sd * 0.85, 0.85), 'rubber')
        # outrigger boxes (stowed): beam + folded leg and pad, front and rear
        for ox in (0.6, -4.0):
            v.bx((0.35, 0.8, 0.3), (ox, sd * 1.5, 1.35), 'yellow')
            v.cz(0.08, 0.08, 0.5, (ox, sd * 1.8, 0.85), 'dark', 6)
            v.bx((0.5, 0.45, 0.1), (ox, sd * 1.8, 0.75), 'steel')
        v.bx((0.04, 0.3, 0.14), (-4.5, sd * 0.9, 1.35), 'lamp_r')
        v.cz(0.1, 0.08, 0.14, (3.9, sd * 1.0, 3.45), 'lamp_a', 8)
    v.bx((0.3, 2.5, 0.3), (4.62, 0, 1.0), 'chrome')
    v.bx((0.03, 1.5, 0.65), (4.51, 0, 2.0), 'dark')
    for k in range(6):
        v.bx((0.04, 0.3, 0.28), (-4.52, -1.0 + k * 0.4, 1.4), ['black', 'yellow'][k % 2])
    v.bx((0.4, 2.0, 0.2), (-4.7, 0, 1.0), 'dark')
    # turret: slewing ring, housing, operator cab, boom bracket
    v.cz(0.9, 0.9, 0.3, (-1.1, 0, 1.73), 'dark', 12)
    v.bx((2.0, 1.8, 1.0), (-1.3, 0, 2.5), paint, bevel=0.05)
    v.bx((1.0, 0.55, 0.95), (-0.55, 0.78, 2.6), 'white')
    v.bx((0.04, 0.5, 0.65), (-0.03, 0.8, 2.7), 'glass'); v.bx((0.7, 0.04, 0.65), (-0.55, 1.07, 2.7), 'glass')
    v.bx((0.5, 0.1, 0.95), (-0.9, 0.46, 3.0), paint); v.bx((0.5, 0.1, 0.95), (-0.9, -0.46, 3.0), paint)
    v.bx((0.4, 1.0, 0.3), (-2.0, 0, 3.0), 'dark')                                                    # counterweight
    v.cyy(0.12, 1.2, -0.9, 0, 2.8, 'chrome', 8)
    v.body()
    for tag, x, yy in (('FL', 3.0, 1), ('FR', 3.0, -1), ('ML', -1.6, 1), ('MR', -1.6, -1), ('RL', -3.0, 1), ('RR', -3.0, -1)):
        v.wheel(tag, x, yy * 0.98, 0.6, 0.6, 0.4, hub='steel', treads=0)
    # boom: outer + inner telescoping box sections along local +X from the pivot; sheave at the tip
    PV = (-0.9, 0, 2.8); BL = 7.2; ang = math.radians(25)
    v.begin()
    x0 = PV[0]
    v.bx((5.0, 0.7, 0.7), (x0 + 2.2, 0, PV[2]), paint)
    v.bx((0.1, 0.8, 0.8), (x0 + 4.75, 0, PV[2]), 'dark')
    v.bx((4.6, 0.5, 0.5), (x0 + 4.9, 0, PV[2]), 'yellow')
    v.bx((0.2, 0.62, 0.62), (x0 + BL - 0.1, 0, PV[2]), 'dark')
    v.cyy(0.2, 0.35, x0 + BL, 0, PV[2], 'steel', 10)
    v.cyy(0.12, 0.5, x0 + 0.0, 0, PV[2], 'dark', 8)
    for k in range(5):
        v.bx((0.08, 0.72, 0.15), (x0 + 0.5 + k * 0.9, 0, PV[2] + 0.38), 'dark') if False else None
    v.end('cranetruck_boom', PV, rot=(0, -ang, 0))
    tip = (PV[0] + BL * math.cos(ang), 0, PV[2] + BL * math.sin(ang))
    # cable (1 m, hangs down from the sheave; scale its local Z to the rope length) and hook block
    v.begin(); v.cz(0.03, 0.03, 1.0, (tip[0], 0, tip[2] - 1.0), 'dark', 5)
    v.end('cranetruck_cable', tip)
    hz = tip[2] - 2.2
    v.begin()
    v.bx((0.42, 0.3, 0.4), (tip[0], 0, hz - 0.2), 'yellow')
    v.cyy(0.09, 0.34, tip[0], 0, hz - 0.12, 'dark', 8)
    v.cz(0.05, 0.05, 0.14, (tip[0], 0, hz - 0.5), 'steel', 6)
    v.torus(0.12, 0.04, 10, 5, (tip[0], 0, hz - 0.68), (math.pi / 2, 0, 0), 'steel', 1.6 * math.pi) if False else None
    t = torus(0.13, 0.04, 10, 5, (tip[0], 0, hz - 0.68), (math.pi / 2, 0, 0.6), m('steel'), 1.65 * math.pi); v.cur.append(t)
    v.end('cranetruck_hook', (tip[0], 0, hz))
    v.emp('seat', (3.2, 0.55, 2.1)); v.emp('cargo', (-1.35, 0, 1.73)); v.emp('hitch', (-4.8, 0, 1.0))
    v.rescale_x(1.0)
    return v


ALL = [ambulance, firetruck, forklift, cargotruck, patrolcar, tractor, quadbike, handcart, cranetruck]
