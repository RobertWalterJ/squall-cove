"""Squall Cove props, set 2: military, farm, harbour and street props so the maps feel lived in.
  blender -b --python build_props2.py -- [--review] [--only barn,bench]
Writes ../../assets/props2.glb.b64.txt, ../review/props2/props2.json and (with --review) one 3/4 PNG per node.
Every node: one top-level mesh, origin at the centre of the footprint on the ground (Blender z = 0 = three y = 0).
Blender (x, y, z) -> three (x, z, -y). Long axis along +x unless noted. windmill_blades is a second top-level node whose
origin is the rotor hub (axle along x), so spin it about its local X axis.
"""
import sys, os, random
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pg_set2 import *
import pg_set2; pg_set2.CLAMP = True

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
PI = math.pi


def xrods(m, pts, r, k, seg=4):
    for a, b in zip(pts[:-1], pts[1:]): m.rd(a, b, r, k, seg)


def revolve_loop(m, profile, seg, k, loc=(0, 0, 0), rotz=0.0):
    """Closed loop profile [(r, z)...] revolved about z (a tyre, a ring)."""
    n = len(profile); verts = []; faces = []
    for (r, z) in profile:
        for i in range(seg):
            a = 2 * PI * i / seg + rotz
            verts.append((loc[0] + r * math.cos(a), loc[1] + r * math.sin(a), loc[2] + z))
    for j in range(n):
        j2 = (j + 1) % n
        for i in range(seg):
            i2 = (i + 1) % seg
            faces.append((j * seg + i, j * seg + i2, j2 * seg + i2, j2 * seg + i))
    o = mesh('rev', verts, faces, mt(k)); recalc(o); return m.add(o)


def arc_ring(m, R, r, start, arc, k, centre, seg=2, sides=6):
    """Torus arc in the XZ plane (axis along y) about `centre`."""
    o = torus(R, r, seg, sides, (0, 0, 0), (0, 0, 0), mt(k), arc=arc)
    o.data.transform(Matrix.Translation(centre) @ Matrix.Rotation(PI / 2, 4, 'X') @ Matrix.Rotation(start, 4, 'Z'))
    return m.add(o)


# ------------------------------------------------------------------ military
def sandbag_wall():
    m = M('sandbag_wall'); n = 8; h = 1.1 / n
    for i in range(n):
        w = 0.6 - 0.02 * i; z0 = i * h
        if i % 2 == 0:
            spans = [(-1.5 + 0.5 * j, -1.0 + 0.5 * j) for j in range(6)]
        else:
            spans = [(-1.5, -1.25)] + [(-1.25 + 0.5 * j, -0.75 + 0.5 * j) for j in range(5)] + [(1.25, 1.5)]
        for j, (a, b) in enumerate(spans):
            jit = (((i * 7 + j * 3) % 5) - 2) * 0.004
            m.b(a + 0.006, b - 0.006, -w / 2 + jit, w / 2 + jit, z0, z0 + h - 0.004, 'sand1' if (i + j) % 2 == 0 else 'sand2')
    return m


def jersey_barrier():
    m = M('jersey_barrier')
    prof = [(-0.3, 0), (0.3, 0), (0.3, 0.1), (0.15, 0.35), (0.1, 0.8), (-0.1, 0.8), (-0.15, 0.35), (-0.3, 0.1)]
    m.ext_x(prof, -1.5, 1.5, 'concrete')
    m.b(-1.5, 1.5, -0.075, 0.075, 0.8, 0.805, 'concrete2')
    for x in (-1.2, 1.2):   # reflective patches and lifting pockets
        m.b(x - 0.1, x + 0.1, 0.155, 0.165, 0.5, 0.64, 'orange')
        m.b(x - 0.1, x + 0.1, -0.165, -0.155, 0.5, 0.64, 'orange')
    for x in (-1.0, 1.0):
        m.b(x - 0.15, x + 0.15, -0.28, 0.28, 0.0, 0.03, 'concrete2')
    return m


def ammo_crate():
    m = M('ammo_crate')
    m.b(-0.4, 0.4, -0.2, 0.2, 0, 0.32, 'olive')
    m.b(-0.41, 0.41, -0.21, 0.21, 0.32, 0.36, 'olive2')
    for x in (-0.28, 0.28):
        m.b(x - 0.03, x + 0.03, 0.2, 0.215, 0.0, 0.32, 'olive2'); m.b(x - 0.03, x + 0.03, -0.215, -0.2, 0.0, 0.32, 'olive2')
    m.b(0.4, 0.43, -0.07, 0.07, 0.2, 0.23, 'steel'); m.b(-0.43, -0.4, -0.07, 0.07, 0.2, 0.23, 'steel')
    m.b(-0.14, 0.14, 0.2, 0.21, 0.1, 0.2, 'yellow'); m.b(-0.14, 0.14, -0.21, -0.2, 0.1, 0.2, 'yellow')    # stencil
    m.b(-0.03, 0.03, 0.21, 0.225, 0.3, 0.37, 'steel')                                              # latch
    m.b(-0.03, 0.03, -0.225, -0.21, 0.3, 0.37, 'steel')
    return m


def medkit_box():
    m = M('medkit_box')
    m.b(-0.25, 0.25, -0.09, 0.09, 0, 0.34, 'white')
    m.b(-0.252, 0.252, -0.092, 0.092, 0.24, 0.25, 'grey_l')
    for x in (-0.14, 0.14): m.b(x - 0.015, x + 0.015, -0.015, 0.015, 0.34, 0.37, 'grey_l')
    m.b(-0.14, 0.14, -0.015, 0.015, 0.37, 0.39, 'grey_l')
    for s in (-1, 1):
        y0, y1 = (0.09, 0.096) if s > 0 else (-0.096, -0.09)
        m.b(-0.035, 0.035, y0, y1, 0.07, 0.23, 'red'); m.b(-0.075, 0.075, y0, y1, 0.115, 0.185, 'red')
        for x in (-0.19, 0.19): m.b(x - 0.015, x + 0.015, y0, y1, 0.22, 0.28, 'steel')
    return m


def flagpole():
    m = M('flagpole')
    m.b(-0.3, 0.3, -0.3, 0.3, 0, 0.06, 'concrete2')
    m.rd((0, 0, 0.06), (0, 0, 7.92), 0.045, 'steel', 8)
    m.add(ico(0.08, 1, (0, 0, 7.92), mt('yellow')))
    m.rd((0.06, 0, 0.6), (0.06, 0, 7.6), 0.006, 'rope', 3)
    m.b(0.05, 0.09, -0.02, 0.02, 1.4, 1.5, 'steel')
    nu, nv = 8, 4; L, Hh = 1.8, 1.1; zt = 7.85; verts = []; faces = []
    for j in range(nv + 1):
        for i in range(nu + 1):
            u = i / nu; z = zt - Hh * j / nv
            verts.append((0.05 + L * u, 0.14 * math.sin(u * 7.0 - 0.3) * u, z - 0.05 * math.sin(u * 4) * u))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i; faces.append((a, a + 1, a + nu + 2, a + nu + 1))
    m.cloth(verts, faces, 'flag')
    return m


# ------------------------------------------------------------------ street, farm and harbour
def market_stall():
    m = M('market_stall')
    for x in (-1.45, 1.45):
        m.b(x - 0.04, x + 0.04, -0.69, -0.61, 0, 2.62, 'wood2')
        m.b(x - 0.04, x + 0.04, 0.81, 0.89, 0, 2.2, 'wood2')
    m.b(-1.45, 1.45, 0.25, 0.8, 0.0, 0.86, 'wood')                      # counter
    m.b(-1.5, 1.5, 0.22, 0.85, 0.86, 0.9, 'wood2')
    m.b(-1.4, 1.4, -0.7, -0.45, 0.78, 0.82, 'wood2')                    # back shelf
    for x in (-1.4, 1.4): m.b(x - 0.03, x + 0.03, -0.69, -0.46, 0, 0.78, 'wood2')
    produce = ['red', 'yellow', 'orange', 'sign_g', 'red', 'yellow']
    for i, k in enumerate(produce):
        x = -1.2 + i * 0.48
        m.b(x - 0.19, x + 0.19, 0.38, 0.72, 0.9, 1.02, 'wood_end')
        m.b(x - 0.16, x + 0.16, 0.41, 0.69, 1.02, 1.07, k)
    for i in range(6):                                                    # striped awning
        x0 = -1.5 + 0.5 * i; k = 'red' if i % 2 == 0 else 'cream'
        m.slab_yz((-0.9, 2.66), (1.0, 2.26), x0, x0 + 0.5, 0.04, k)
        m.b(x0, x0 + 0.5, 1.0, 1.04, 2.0, 2.3, k)
    m.b(-1.5, 1.5, -0.92, -0.88, 2.2, 2.7, 'cream')                      # back fall
    return m


def bench():
    m = M('bench')
    for i, y in enumerate((-0.2, -0.06, 0.08)):
        m.b(-0.9, 0.9, y, y + 0.125, 0.43, 0.47, 'wood')
    m.b(-0.9, 0.9, -0.275, -0.245, 0.62, 0.74, 'wood', rot=(-0.14, 0, 0))
    m.b(-0.9, 0.9, -0.295, -0.265, 0.78, 0.9, 'wood', rot=(-0.14, 0, 0))
    for x in (-0.78, 0.78):
        m.b(x - 0.035, x + 0.035, 0.12, 0.2, 0, 0.43, 'wood2')
        m.b(x - 0.035, x + 0.035, -0.26, -0.18, 0, 0.43, 'wood2')
        m.b(x - 0.035, x + 0.035, -0.33, -0.27, 0.43, 0.92, 'wood2', rot=(-0.14, 0, 0))
        m.b(x - 0.04, x + 0.04, -0.3, 0.2, 0.62, 0.66, 'wood2')
    m.b(-0.8, 0.8, 0.12, 0.17, 0.2, 0.25, 'wood2')
    return m


def hay_bale():
    m = M('hay_bale')
    m.c(0.75, 1.2, (0, 0.6, 0.75), 'straw', seg=20, rot=(PI / 2, 0, 0))
    for y in (-0.3, 0.3):
        m.c(0.752, 0.03, (0, y + 0.015, 0.75), 'rope', seg=20, rot=(PI / 2, 0, 0))
    for y in (0.6, -0.6):
        s = 1 if y > 0 else -1
        m.c(0.55, 0.01, (0, y + 0.005 * s + (0.005 if s > 0 else 0), 0.75), 'rope', seg=20, rot=(PI / 2, 0, 0))
    return m


def picnic_table():
    m = M('picnic_table')
    for y in (-0.38, -0.12, 0.14):
        m.b(-0.9, 0.9, y, y + 0.24, 0.72, 0.76, 'wood')
    for s in (-1, 1):
        y0, y1 = (0.45, 0.75) if s > 0 else (-0.75, -0.45)
        m.b(-0.85, 0.85, y0, y1, 0.42, 0.46, 'wood')
    for x in (-0.62, 0.62):
        m.rd((x, -0.62, 0.0), (x, -0.12, 0.72), 0.032, 'wood2', 4)
        m.rd((x, 0.62, 0.0), (x, 0.12, 0.72), 0.032, 'wood2', 4)
        m.b(x - 0.03, x + 0.03, -0.72, 0.72, 0.38, 0.42, 'wood2')
        m.b(x - 0.03, x + 0.03, -0.42, 0.42, 0.68, 0.72, 'wood2')
    return m


def tyre_stack():
    m = M('tyre_stack')
    prof = [(0.19, 0.0), (0.27, 0.0), (0.325, 0.03), (0.34, 0.11), (0.325, 0.19), (0.27, 0.22), (0.19, 0.22), (0.183, 0.11)]
    for i, (dx, dy, rz) in enumerate(((0, 0, 0), (0.03, -0.02, 0.4), (-0.02, 0.03, 0.8))):
        revolve_loop(m, prof, 14, 'rubber', (dx, dy, i * 0.22), rz)
    return m


def log_pile():
    m = M('log_pile'); R = 0.15
    rows = [(4, 0.0), (3, 0.0), (2, 0.0), (1, 0.0)]
    idx = 0
    for ri, (cnt, _) in enumerate(rows):
        z = R + ri * 0.26
        for j in range(cnt):
            y = (j - (cnt - 1) / 2) * 0.3
            ln = 1.9 + 0.05 * ((idx * 5) % 3); x0 = -1.0 + 0.02 * ((idx * 7) % 4) - (ln - 1.9) / 2
            m.c(R, ln, (x0, y, z), 'wood2', seg=8, rot=(0, PI / 2, 0))
            m.c(R - 0.012, 0.01, (x0 + ln, y, z), 'wood_end', seg=8, rot=(0, PI / 2, 0))
            m.c(R - 0.012, 0.01, (x0 - 0.005, y, z), 'wood_end', seg=8, rot=(0, PI / 2, 0))
            idx += 1
    return m


def rowboat_beached():
    m = M('rowboat_beached')
    xs = [-1.75, -1.4, -0.9, -0.3, 0.3, 0.9, 1.4, 1.75]
    beam = dict(zip(xs, [0.5, 0.62, 0.7, 0.72, 0.68, 0.55, 0.33, 0.07]))
    t = 0.03
    zg = lambda x: 0.55 + 0.1 * (x / 1.75) ** 2
    zk = lambda x: 0.07 + 0.2 * max(0.0, (x - 0.5) / 1.25) ** 2
    def ring(x):
        b = beam[x]; g = zg(x); k = zk(x); zc = k + 0.1; c = 0.62 * b; bi = max(b - t, 0.01)
        return [(x, -b, g), (x, -c, zc), (x, 0, k), (x, c, zc), (x, b, g),
                (x, bi, g), (x, max(c - t * 0.8, 0.005), zc + t), (x, 0, k + t), (x, -max(c - t * 0.8, 0.005), zc + t), (x, -bi, g)]
    m.ring_loft(xs, ring, [0, 0, 0, 0, 1, 1, 1, 1, 1, 1], ['boat_hull', 'wood'])
    b0 = beam[-1.75]
    m.ext_x([(-b0, zg(-1.75)), (-0.62 * b0, zk(-1.75) + 0.1), (0, zk(-1.75)), (0.62 * b0, zk(-1.75) + 0.1), (b0, zg(-1.75))], -1.78, -1.75, 'wood2')
    m.b(-1.3, 0.9, -0.035, 0.035, 0.0, 0.075, 'wood2')                         # keel strip
    m.b(-1.2, 0.8, -0.3, 0.3, 0.13, 0.15, 'wood')                              # floorboards
    for x in (-0.9, -0.1, 0.7):
        bb = 0.62 if x > 0.5 else 0.68
        m.b(x - 0.12, x + 0.12, -bb, bb, 0.36, 0.39, 'wood2')
    for s in (-1, 1):
        m.b(-0.5, -0.2, 0.3 * s if s > 0 else -0.5, 0.5 if s > 0 else -0.3, 0.0, 0.18, 'concrete2')   # beach chocks
        m.rd((-0.9, 0.14 * s, 0.41), (1.1, 0.14 * s, 0.41), 0.02, 'wood', 5)    # oars
        m.b(1.1, 1.55, 0.14 * s - 0.07, 0.14 * s + 0.07, 0.4, 0.42, 'wood')
        m.rd((-0.3, 0.64 * s, zg(-0.3)), (-0.3, 0.64 * s, zg(-0.3) + 0.12), 0.015, 'steel', 4)  # rowlocks
    m.rd((1.7, 0, 0.5), (1.78, 0, 0.62), 0.02, 'steel', 4)
    return m


def fishing_hut():
    m = M('fishing_hut')
    for x in (-1.8, 0, 1.8):
        for y in (-1.4, 1.4): m.c(0.1, 1.2, (x, y, 0), 'wood2', seg=8)
    for y in (-1.4, 1.4): m.b(-1.9, 1.9, y - 0.04, y + 0.04, 0.35, 0.43, 'wood2')
    for x in (-1.8, 1.8): m.b(x - 0.04, x + 0.04, -1.45, 1.45, 0.65, 0.73, 'wood2')
    m.b(-2.1, 2.1, -1.6, 1.6, 1.2, 1.3, 'wood2')                                  # deck
    m.b(-2.0, 2.0, -1.5, 1.5, 1.3, 3.5, 'wood_g')                                   # walls
    for x in (-1.5, -0.9, -0.3, 0.3, 0.9, 1.5):                                     # plank lines
        m.b(x - 0.01, x + 0.01, 1.5, 1.52, 1.3, 3.5, 'wood2'); m.b(x - 0.01, x + 0.01, -1.52, -1.5, 1.3, 3.5, 'wood2')
    m.b(-0.55, 0.45, 1.5, 1.57, 1.3, 3.15, 'wood2')                                 # door
    m.b(-0.1, 0.0, 1.57, 1.6, 2.2, 2.4, 'steel')
    m.b(0.95, 1.75, 1.5, 1.56, 2.2, 3.0, 'glass')                                   # front window
    for y in (-0.5, 0.5):
        m.b(2.0, 2.06, y - 0.4, y + 0.4, 2.2, 3.0, 'glass'); m.b(-2.06, -2.0, y - 0.4, y + 0.4, 2.2, 3.0, 'glass')
    m.ext_x([(-1.5, 3.5), (1.5, 3.5), (0, 4.25)], -2.0, 2.0, 'wood_g')
    m.slab_yz((-1.8, 3.4), (0.0, 4.3), -2.3, 2.3, 0.08, 'roof_grey')
    m.slab_yz((1.8, 3.4), (0.0, 4.3), -2.3, 2.3, 0.08, 'roof_grey')
    for x in (1.1, 1.5):                                                            # ladder
        m.rd((x, 2.1, 0.0), (x, 1.7, 1.25), 0.03, 'wood2', 4)
    for i in range(1, 6):
        t = i / 6; m.b(1.08, 1.52, 2.1 - 0.4 * t - 0.02, 2.1 - 0.4 * t + 0.02, 1.25 * t - 0.02, 1.25 * t + 0.02, 'wood')
    m.add(ico(0.13, 1, (-1.95, 1.8, 1.55), mt('orange')))
    m.b(-1.95, -1.9, 1.5, 1.8, 3.0, 3.03, 'rope')
    return m


def jetty_section():
    m = M('jetty_section')
    xsp = [-3.6, -1.8, 0.0, 1.8, 3.6]
    for x in xsp:
        for y in (-1.2, 1.2): m.c(0.15, 1.0, (x, y, 0), 'wood2', seg=8)
        m.b(x - 0.11, x + 0.11, -1.45, 1.45, 0.96, 1.08, 'wood2')
    for y in (-1.2, 0.0, 1.2): m.b(-4.0, 4.0, y - 0.08, y + 0.08, 1.08, 1.15, 'wood2')
    for i in range(40):
        x0 = -3.9 + 0.2 * i
        m.b(x0 - 0.09, x0 + 0.09, -1.5, 1.5, 1.15, 1.2, 'wood' if i % 3 else 'wood_g')
    for s in (-1, 1):
        m.b(-4.0, 4.0, 1.5 * s - 0.04 if s > 0 else -1.54, 1.54 if s > 0 else -1.46, 1.2, 1.28, 'wood2')
    for x in (-3.3, 3.3):
        for y in (-1.3, 1.3): m.c(0.07, 0.26, (x, y, 1.2), 'black', seg=8)
    for x0, x1 in ((-3.6, -1.8), (1.8, 3.6)):
        m.rd((x0, -1.2, 0.2), (x1, -1.2, 0.95), 0.03, 'wood', 4); m.rd((x0, 1.2, 0.2), (x1, 1.2, 0.95), 0.03, 'wood', 4)
    return m


def life_ring_post():
    m = M('life_ring_post')
    m.b(-0.05, 0.05, -0.05, 0.05, 0, 1.6, 'wood')
    m.b(-0.065, 0.065, -0.065, 0.065, 1.6, 1.65, 'wood2')
    m.b(-0.03, 0.03, 0.05, 0.17, 1.28, 1.34, 'steel'); m.b(-0.03, 0.03, 0.05, 0.17, 1.52, 1.58, 'steel')
    c = Vector((0, 0.2, 1.36))
    o = torus(0.21, 0.05, 14, 6, (0, 0, 0), (0, 0, 0), mt('ring_red'))
    o.data.transform(Matrix.Translation(c) @ Matrix.Rotation(PI / 2, 4, 'X')); m.add(o)
    for i in range(4):
        arc_ring(m, 0.21, 0.054, i * PI / 2 - 0.2, 0.4, 'white', c, seg=2)
    return m


def signboard():
    m = M('signboard')
    m.b(-0.06, 0.06, -0.1, -0.04, 0, 2.3, 'wood2')
    m.b(-0.75, 0.75, -0.03, 0.03, 1.55, 2.25, 'wood2')
    m.b(-0.71, 0.71, 0.03, 0.036, 1.59, 2.21, 'cream')
    m.b(-0.71, 0.71, -0.036, -0.03, 1.59, 2.21, 'cream')
    for z, w in ((2.08, 0.5), (1.92, 0.62), (1.76, 0.4)):
        m.b(-w, w, 0.036, 0.042, z - 0.04, z + 0.04, 'black'); m.b(-w, w, -0.042, -0.036, z - 0.04, z + 0.04, 'black')
    return m


# ------------------------------------------------------------------ tall structures
def lattice4(m, h_top, w0, w1, bays, leg_r, k_leg, k_br, br_r=0.03, seg=4):
    """Square tapered lattice tower: legs at +-w, horizontals each level, one alternating diagonal per face per bay."""
    def w(z): return w0 + (w1 - w0) * z / h_top
    zs = [h_top * i / bays for i in range(bays + 1)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.rd((sx * w0, sy * w0, 0), (sx * w1, sy * w1, h_top), leg_r, k_leg, 6)
    for i, z in enumerate(zs):
        if i == 0: continue
        a = w(z)
        for p, q in (((-a, -a), (a, -a)), ((a, -a), (a, a)), ((a, a), (-a, a)), ((-a, a), (-a, -a))):
            m.rd((p[0], p[1], z), (q[0], q[1], z), br_r, k_br, seg)
    for i in range(bays):
        za, zb = zs[i], zs[i + 1]; a, b = w(za), w(zb)
        flip = 1 if i % 2 == 0 else -1
        faces = [((-a, -a), (a, -a), (-b, -b), (b, -b)), ((a, -a), (a, a), (b, -b), (b, b)),
                 ((a, a), (-a, a), (b, b), (-b, b)), ((-a, a), (-a, -a), (-b, b), (-b, -b))]
        for (p0, p1, q0, q1) in faces:
            s, e = ((p0, q1) if flip > 0 else (p1, q0))
            m.rd((s[0], s[1], za), (e[0], e[1], zb), br_r, k_br, seg)


def windmill():
    m = M('windmill'); hub = Vector((-0.55, 0, 11.5))
    lattice4(m, 10.8, 1.6, 0.5, 4, 0.07, 'galv', 'galv', 0.035, 4)
    m.b(-0.75, 0.75, -0.75, 0.75, 10.8, 10.9, 'wood2')
    m.b(-0.4, 0.4, -0.27, 0.27, 10.9, 11.75, 'metal_d')
    m.rd((-0.7, 0, 11.5), (0.2, 0, 11.5), 0.07, 'steel', 6)
    m.rd((0.3, 0, 11.5), (3.3, 0, 11.5), 0.05, 'galv', 4)
    m.ext([(2.8, 11.1), (4.7, 11.0), (4.7, 12.4), (3.0, 11.9)], -0.015, 0.015, lambda u, v, a: (u, a, v), 'galv')
    m.b(4.0, 4.7, -0.017, 0.017, 11.5, 12.4, 'red')
    m.rd((0, 0, 0.4), (0, 0, 10.9), 0.035, 'rust', 4)                                  # pump rod
    m.b(-0.35, 0.35, -0.35, 0.35, 0, 0.5, 'wood_g')                                    # pump housing
    return m


def windmill_blades():
    hub = Vector((-0.55, 0, 11.5)); m = M('windmill_blades', origin=hub)
    N = 18
    for i in range(N):
        th = 2 * PI * i / N
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        S = Matrix.Diagonal((0.02, 0.28, 1.9, 1.0))
        T = Matrix.Translation(hub) @ Matrix.Rotation(th, 4, 'X') @ Matrix.Rotation(math.radians(25), 4, 'Z') @ Matrix.Translation((0, 0, 1.5)) @ S
        bmesh.ops.transform(bm, matrix=T, verts=bm.verts)
        m.add(obj_from_bm(bm, 'blade', mt('galv')))
    for R in (2.45, 1.25):
        m.add(torus(R, 0.03, 18, 4, tuple(hub), (0, PI / 2, 0), mt('steel')))
    for i in range(6):
        th = 2 * PI * i / 6
        m.rd(hub, hub + Vector((0, 2.4 * math.cos(th), 2.4 * math.sin(th))), 0.025, 'steel', 4)
    m.add(cyl(0.2, 0.2, 0.4, 8, tuple(hub + Vector((-0.2, 0, 0))), (0, PI / 2, 0), mt('metal_d')))
    return m


def water_tower():
    m = M('water_tower')
    zs = [0, 3.3, 6.6, 10.0]
    def w(z): return 2.6 - 0.7 * z / 10.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.rd((sx * 2.6, sy * 2.6, 0), (sx * 1.9, sy * 1.9, 10.0), 0.12, 'galv', 6)
    for z in zs[1:]:
        a = w(z)
        for p, q in (((-a, -a), (a, -a)), ((a, -a), (a, a)), ((a, a), (-a, a)), ((-a, a), (-a, -a))):
            m.rd((p[0], p[1], z), (q[0], q[1], z), 0.05, 'galv', 4)
    for i in range(3):
        za, zb = zs[i], zs[i + 1]; a, b = w(za), w(zb)
        for (p0, p1, q0, q1) in [((-a, -a), (a, -a), (-b, -b), (b, -b)), ((a, -a), (a, a), (b, -b), (b, b)),
                                 ((a, a), (-a, a), (b, b), (-b, b)), ((-a, a), (-a, -a), (-b, b), (-b, -b))]:
            m.rd((p0[0], p0[1], za), (q1[0], q1[1], zb), 0.03, 'rust', 3); m.rd((p1[0], p1[1], za), (q0[0], q0[1], zb), 0.03, 'rust', 3)
    m.b(-2.2, 2.2, -2.2, 2.2, 9.9, 10.0, 'frame')
    prof = [(0.001, 10.0), (1.8, 10.05), (2.3, 10.5), (2.4, 10.9), (2.4, 12.9), (2.3, 13.0), (1.0, 13.55), (0.0, 13.75)]
    m.add(lathe(prof, 16, mt('tank'), 'tank', cap_top=False, cap_bottom=False))
    m.c(2.42, 0.12, (0, 0, 11.2), 'steel', seg=12); m.c(2.42, 0.12, (0, 0, 12.4), 'steel', seg=12)
    m.c(0.15, 0.25, (0, 0, 13.75), 'steel', seg=6)
    for sx in (-0.25, 0.25): m.rd((sx, 2.75, 0.2), (sx, 2.75, 10.4), 0.03, 'steel', 4)
    for i in range(1, 9):
        z = 0.2 + 10.2 * i / 9; m.b(-0.25, 0.25, 2.73, 2.77, z - 0.015, z + 0.015, 'steel')
    return m


def barn():
    m = M('barn')
    hw = 4.3
    prof = [(-hw, 0), (hw, 0), (hw, 3.8), (3.3, 5.9), (0, 7.55), (-3.3, 5.9), (-hw, 3.8)]
    m.ext_x(prof, -6.85, 6.85, 'barn_red')
    m.b(-6.9, 6.9, -hw - 0.05, hw + 0.05, 0, 0.35, 'concrete2')
    for p0, p1 in (((hw, 3.75), (3.3, 5.9)), ((3.3, 5.9), (0, 7.62)), ((-3.3, 5.9), (-hw, 3.75)), ((0, 7.62), (-3.3, 5.9))):
        m.slab_yz(p0, p1, -7.0, 7.0, 0.18, 'roof_dark')
    for s in (-1, 1):
        for x in (-6.9, 6.9):
            m.b(x - 0.06, x + 0.06, s * hw - 0.06, s * hw + 0.06, 0, 3.9, 'white')
        for x in (-4.5, 0.0, 4.5):
            m.b(x - 0.5, x + 0.5, s * (hw + 0.02) - 0.03, s * (hw + 0.02) + 0.03, 1.5, 2.7, 'white')
            m.b(x - 0.4, x + 0.4, s * (hw + 0.02) - 0.04, s * (hw + 0.02) + 0.04, 1.6, 2.6, 'glass')
    m.b(6.85, 6.93, -1.75, 1.75, 0.35, 3.75, 'white')                                # doors on +x end
    m.b(6.93, 6.97, -1.65, -0.03, 0.35, 3.65, 'red_d'); m.b(6.93, 6.97, 0.03, 1.65, 0.35, 3.65, 'red_d')
    for y0, y1 in ((-1.65, -0.03), (0.03, 1.65)):
        m.rd((6.975, y0, 0.37), (6.975, y1, 3.63), 0.04, 'white', 4); m.rd((6.975, y1, 0.37), (6.975, y0, 3.63), 0.04, 'white', 4)
    m.b(6.85, 6.93, -0.65, 0.65, 4.55, 5.65, 'white'); m.b(6.93, 6.96, -0.55, 0.55, 4.65, 5.55, 'red_d')   # hay loft door
    m.b(-7.0, -6.85, -0.5, 0.5, 6.2, 6.8, 'roof_dark')                                # vent at -x gable
    m.b(-0.3, 0.3, -0.3, 0.3, 7.55, 8.0, 'roof_dark')                                 # ridge vent
    return m


def hay_rack():
    m = M('hay_rack')
    for x in (-1.4, 1.4):
        for y in (-0.42, 0.42): m.b(x - 0.04, x + 0.04, y - 0.04, y + 0.04, 0, 1.0, 'wood2')
        m.b(x - 0.04, x + 0.04, -0.66, 0.66, 1.1, 1.18, 'wood2')
    m.b(-1.5, 1.5, -0.32, 0.32, 0.45, 0.5, 'wood')
    for s in (-1, 1):
        m.b(-1.5, 1.5, 0.58 * s - 0.04, 0.58 * s + 0.04, 1.12, 1.18, 'wood2')
        m.b(-1.5, 1.5, 0.3 * s - 0.03, 0.3 * s + 0.03, 0.5, 0.56, 'wood2')
        for i in range(14):
            x = -1.4 + 2.8 * i / 13
            m.rd((x, 0.3 * s, 0.52), (x, 0.6 * s, 1.14), 0.017, 'wood', 4)
    m.b(-1.3, 1.3, -0.3, 0.3, 0.5, 0.95, 'straw')
    return m


def fuel_pump():
    m = M('fuel_pump')
    m.b(-0.7, 0.7, -0.45, 0.45, 0, 0.15, 'concrete')
    m.b(-0.3, 0.3, -0.22, 0.22, 0.15, 1.6, 'pump_red'); m.b(-0.32, 0.32, -0.24, 0.24, 0.15, 0.3, 'frame')
    m.b(-0.34, 0.34, -0.26, 0.26, 1.6, 2.1, 'white'); m.b(-0.36, 0.36, -0.28, 0.28, 2.1, 2.2, 'pump_red')
    for s in (-1, 1):
        y0, y1 = (0.22, 0.235) if s > 0 else (-0.235, -0.22)
        m.b(-0.2, 0.2, y0, y1, 1.1, 1.42, 'glass'); m.b(-0.2, 0.2, y0, y1, 0.8, 1.0, 'white')
        m.b(-0.28, 0.28, y0 if s > 0 else -0.24, 0.24 if s > 0 else y1, 1.0, 1.1, 'frame')
        y2, y3 = (0.26, 0.275) if s > 0 else (-0.275, -0.26)
        m.b(-0.22, 0.22, y2, y3, 1.7, 2.05, 'pump_red')
    m.b(0.3, 0.4, -0.1, 0.1, 0.78, 1.05, 'frame')                                        # holster
    m.rd((0.4, 0, 1.0), (0.46, 0, 0.9), 0.025, 'black', 5)
    xrods(m, [(0.34, 0, 0.9), (0.52, 0, 0.6), (0.5, 0, 0.3), (0.36, 0.1, 0.2), (0.3, 0.22, 1.2)], 0.018, 'black', 5)
    for x in (-0.55, 0.55): m.c(0.07, 0.9, (x, 0.0, 0.15), 'yellow', seg=8)
    return m


def phone_box():
    m = M('phone_box')
    for sx in (-1, 1):
        for sy in (-1, 1): m.b(sx * 0.46 - 0.04, sx * 0.46 + 0.04, sy * 0.46 - 0.04, sy * 0.46 + 0.04, 0, 2.0, 'phone_red')
    m.b(-0.5, 0.5, -0.5, 0.5, 0, 0.3, 'phone_red')
    for s in (-1, 1):
        for horiz in (0, 1):
            def bx(u0, u1, d0, d1, z0, z1, k):
                if horiz: m.b(d0 * s if s > 0 else -d1, d1 if s > 0 else -d0, u0, u1, z0, z1, k)
                else: m.b(u0, u1, d0 if s > 0 else -d1, d1 if s > 0 else -d0, z0, z1, k)
            bx(-0.42, 0.42, 0.47, 0.485, 0.3, 2.0, 'glass')
            for u in (-0.14, 0.14): bx(u - 0.015, u + 0.015, 0.465, 0.495, 0.3, 2.0, 'phone_red')
            for z in (0.62, 0.94, 1.26, 1.58): bx(-0.42, 0.42, 0.465, 0.495, z - 0.015, z + 0.015, 'phone_red')
    m.b(-0.5, 0.5, -0.5, 0.5, 2.0, 2.2, 'phone_red'); m.b(-0.42, 0.42, -0.42, 0.42, 2.2, 2.3, 'phone_red')
    m.b(-0.3, 0.3, -0.3, 0.3, 2.3, 2.36, 'phone_red'); m.b(-0.14, 0.14, -0.14, 0.14, 2.36, 2.4, 'phone_red')
    for s in (-1, 1):
        y0, y1 = (0.5, 0.51) if s > 0 else (-0.51, -0.5)
        m.b(-0.38, 0.38, y0, y1, 2.04, 2.17, 'white')
    m.b(0.17, 0.22, 0.5, 0.54, 1.0, 1.25, 'brass')
    m.b(-0.1, 0.1, -0.45, -0.37, 1.2, 1.55, 'black')
    return m


def bus_stop():
    m = M('bus_stop')
    for x in (-1.4, 1.4):
        m.b(x - 0.04, x + 0.04, -0.64, -0.56, 0, 2.4, 'frame'); m.b(x - 0.04, x + 0.04, 0.56, 0.64, 0, 2.35, 'frame')
    m.b(-1.5, 1.5, -0.75, 0.75, 2.38, 2.48, 'roof_grey', rot=(0.04, 0, 0))
    m.b(-1.4, 1.4, -0.62, -0.58, 0.35, 2.3, 'glass'); m.b(-1.4, -1.36, -0.58, 0.58, 0.35, 2.3, 'glass')
    m.b(-1.4, 1.4, -0.64, -0.56, 0.3, 0.38, 'frame'); m.b(-1.4, 1.4, -0.64, -0.56, 2.3, 2.38, 'frame')
    m.b(-1.0, 1.0, -0.5, -0.1, 0.45, 0.5, 'wood')
    for x in (-0.9, 0.9): m.b(x - 0.03, x + 0.03, -0.5, -0.1, 0.0, 0.45, 'frame')
    m.b(0.2, 1.1, -0.57, -0.54, 1.0, 1.9, 'white'); m.b(0.25, 1.05, -0.575, -0.57, 1.05, 1.85, 'sign_g')
    m.b(1.37, 1.43, 0.57, 0.63, 2.35, 3.2, 'frame')
    m.c(0.26, 0.03, (1.4, 0.66, 3.0), 'yellow', seg=14, rot=(PI / 2, 0, 0))
    m.b(1.3, 1.5, 0.66, 0.672, 2.93, 3.07, 'black')
    return m


def tent_large():
    m = M('tent_large')
    m.ext_x([(-2.45, 0), (2.45, 0), (2.45, 2.0), (0, 3.95), (-2.45, 2.0)], -4.0, 4.0, 'tent')
    m.slab_yz((2.45, 2.0), (0, 3.95), -4.0, 4.0, 0.05, 'tent2'); m.slab_yz((0, 3.95), (-2.45, 2.0), -4.0, 4.0, 0.05, 'tent2')
    m.b(-4.0, 4.0, -2.5, 2.5, 0, 0.3, 'tent2')
    m.rd((-4.02, 0, 4.0), (4.02, 0, 4.0), 0.05, 'wood2', 5)
    for s in (-1, 1):
        for x in (-2.5, 0.0, 2.5):
            m.b(x - 0.5, x + 0.5, 2.46 if s > 0 else -2.55, 2.55 if s > 0 else -2.46, 0.9, 1.7, 'roof_dark')
    m.b(4.0, 4.04, -0.95, 0.95, 0.0, 2.5, 'roof_dark')
    m.b(4.04, 4.08, -1.0, -0.95, 0.0, 2.55, 'tent2'); m.b(4.04, 4.08, 0.95, 1.0, 0.0, 2.55, 'tent2')
    m.b(-4.04, -4.0, -0.95, 0.95, 0.0, 2.3, 'roof_dark')
    for x in (-4.0, 4.0): m.rd((x * 1.0, 0, 0), (x * 1.0, 0, 4.0), 0.06, 'wood2', 5)
    return m


def camo_net():
    m = M('camo_net'); nu, nv = 12, 10; rnd = random.Random(11)
    verts = []; fcol = []
    for j in range(nv + 1):
        for i in range(nu + 1):
            u = -3 + 6 * i / nu; v = -2.5 + 5 * j / nv
            z = 0.3 + 2.7 * (1 - abs(v) / 2.5) ** 1.4
            z *= 1 - 0.08 * max(0.0, math.cos(PI * u / 5.0))
            z += 0.04 * math.sin(u * 3 + v * 2) * (z / 3)
            verts.append((u, v, min(z, 3.0)))
    faces = []
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i; faces.append((a, a + 1, a + nu + 2, a + nu + 1)); fcol.append((i // 2 * 5 + j // 2 * 3 + rnd.randint(0, 1)) % 3)
    n = len(verts)
    allf = faces + [tuple(k + n for k in reversed(f)) for f in faces]
    me = bpy.data.meshes.new('net'); me.from_pydata(verts + verts, [], allf); me.validate(); me.update()
    for k in ('camo1', 'camo2', 'camo3'): me.materials.append(mt(k))
    for p, c in zip(me.polygons, fcol + fcol): p.material_index = c
    m.add(link(bpy.data.objects.new('net', me)))
    for x in (-2.5, 2.5): m.rd((x, 0, 0), (x, 0, 3.0), 0.05, 'wood2', 6)
    for x, y in ((-3, -2.5), (3, -2.5), (-3, 2.5), (3, 2.5)):
        m.rd((x, y, 0.0), (x, y, 0.32), 0.02, 'rope', 4)
    return m


def radio_mast():
    m = M('radio_mast'); bays = 8; z0 = 0.2; bh = 2.3
    ang = [PI / 2, PI / 2 + 2 * PI / 3, PI / 2 + 4 * PI / 3]
    def R(i): return 0.6 - 0.3 * i / bays
    def pt(i, a): return (R(i) * math.cos(ang[a]), R(i) * math.sin(ang[a]), z0 + bh * i)
    m.b(-0.9, 0.9, -0.8, 0.8, 0, z0, 'concrete')
    for i in range(bays):
        k = 'red' if i % 2 == 0 else 'white'
        for a in range(3): m.rd(pt(i, a), pt(i + 1, a), 0.045, k, 4)
        for a in range(3):
            b = (a + 1) % 3
            if i % 2 == 0: m.rd(pt(i, a), pt(i + 1, b), 0.022, 'galv', 3)
            else: m.rd(pt(i, b), pt(i + 1, a), 0.022, 'galv', 3)
    for i in range(bays + 1):
        for a in range(3): m.rd(pt(i, a), pt(i, (a + 1) % 3), 0.022, 'galv', 3)
    top = z0 + bh * bays
    m.b(-0.45, 0.45, -0.45, 0.45, top, top + 0.06, 'frame')
    m.rd((0, 0, top), (0, 0, 20.0), 0.015, 'steel', 3)
    m.add(ico(0.1, 1, (0, 0, top + 0.16), mt('red')))
    for z, y in ((15.0, 0.0), (12.0, 0.0)):
        m.add(cyl(0.3, 0.04, 0.22, 10, (0.5, 0, z), (0, PI / 2, 0), mt('grey_l')))
    m.b(0.0, 0.1, 0.38, 0.52, 14.0, 15.0, 'white')
    return m


def sand_dune_grass():
    m = M('sand_dune_grass'); rnd = random.Random(7)
    verts = []; faces = []
    for bi in range(46):
        r = rnd.random() ** 0.7 * 0.28; th = rnd.random() * 2 * PI
        bx, by = r * math.cos(th), r * math.sin(th)
        h = 0.45 + 0.55 * (1 - r / 0.35) * rnd.random() ** 0.5
        h = min(h, 1.0)
        la = th + rnd.uniform(-0.5, 0.5)
        lean = rnd.uniform(0.08, 0.3) * h
        wd = (-math.sin(la), math.cos(la)); ld = (math.cos(la), math.sin(la))
        base = len(verts)
        for lv, w in ((0, 0.016), (1, 0.014), (2, 0.009)):
            t = lv / 2.4
            off = lean * t * t * 1.8
            cx, cy = bx + ld[0] * off, by + ld[1] * off
            cz = h * t * (1 - 0.12 * t)
            verts.append((cx + wd[0] * w, cy + wd[1] * w, cz)); verts.append((cx - wd[0] * w, cy - wd[1] * w, cz))
        off = lean * 1.8; verts.append((bx + ld[0] * off, by + ld[1] * off, h))
        faces += [(base, base + 1, base + 3, base + 2), (base + 2, base + 3, base + 5, base + 4), (base + 4, base + 5, base + 6)]
    n = len(verts)
    allf = faces + [tuple(k + n for k in reversed(f)) for f in faces]
    m.add(mesh('grass', verts + verts, allf, mt('dune')))
    return m


MODELS = [sandbag_wall, jersey_barrier, ammo_crate, medkit_box, flagpole, market_stall, bench, hay_bale, picnic_table,
          tyre_stack, log_pile, rowboat_beached, fishing_hut, jetty_section, life_ring_post, signboard, windmill,
          windmill_blades, water_tower, barn, hay_rack, fuel_pump, phone_box, bus_stop, tent_large, camo_net, radio_mast,
          sand_dune_grass]
run(MODELS, 'props2', 'props2', (0.8, -0.62, 0.42), argv)
