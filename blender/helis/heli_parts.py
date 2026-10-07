"""Reusable helicopter sub-assemblies (game coords: x left, y up, z forward)."""
import math
from mathutils import Vector
from heli_lib import *


class Model:
    """Collects the named nodes of one helicopter."""
    def __init__(self, name):
        self.name = name; self.parts = []; self.empties = []   # parts: (Part); empties: (name, loc)
    def part(self, suffix, pivot=(0, 0, 0)):
        p = Part(self.name + suffix, pivot); self.parts.append(p); return p
    def seat(self, loc):
        self.empties.append(('%s_seat_%d' % (self.name, len([e for e in self.empties if '_seat_' in e[0]])), loc))
    def build(self):
        root = new_empty(self.name, (0, 0, 0), None, size=0.5)
        for p in self.parts:
            if p.V: part_to_obj(p, root)
        for n, loc in self.empties: new_empty(n, loc, root, size=0.12, shape='ARROWS')
        return root


def skid_gear(P, x, zf, zr, hf, hr, r, mat, cross=(), belly=None, seg=6):
    """Pair of skids at +-x with upswept ends and arched cross tubes. belly(z) = underside height at the centreline.
    Skid tube centre height is r (so the bottom touches y=0)."""
    for sx in (x, -x):
        front = []
        for i in range(5):
            a = (i / 4) * PI / 2; front.append((sx, r + (hf - r) * (1 - math.cos(a)), (zf - 0.45) + 0.45 * math.sin(a)))
        rear = []
        for i in range(5):
            a = (i / 4) * PI / 2; rear.append((sx, r + (hr - r) * (1 - math.cos(a)), (zr + 0.4) - 0.4 * math.sin(a)))
        P.sweep(list(reversed(front)) + rear, r, seg, mat, True)
    for z in cross:
        by = belly(z) if belly else 0.6
        h = by - r; pts = []
        for fx, fy in ((1.0, 0.0), (0.995, 0.22), (0.95, 0.5), (0.8, 0.8), (0.55, 0.97), (0.3, 1.0)):
            pts.append((x * fx, r + h * fy, z))
        P.sweep(pts + [(-p[0], p[1], p[2]) for p in reversed(pts[:-1])], r * 0.9, seg, mat, True)


def mast_head(R, hub, nblades, radius, chord, thick, hubmat, blademat, tipmat=None, root=0.5, pitch=5.0, cone=0.2, phase=0.0, twobar=False):
    """Rotating part of a main rotor, built in absolute coords around `hub` (R is the rotor Part)."""
    hub = Vector(hub)
    R.cyl(hub + V(0, -0.12, 0), hub + V(0, 0.12, 0), 0.10, 0.10, 8, hubmat)
    n = nblades
    for i in range(n):
        a = phase + 2 * PI * i / n
        d = V(math.cos(a), 0, math.sin(a))
        ch = V(0, 1, 0).cross(d).normalized()
        # blade grip (root sleeve) and pitch horn
        R.box(hub + d * (root * 0.5 + 0.12), (root * 0.8, 0.1, 0.2), hubmat, rot=(0, -math.degrees(a), 0), bevel=0.02)
        R.cyl(hub + d * (root * 0.2) + V(0, 0.0, 0), hub + d * (root * 0.95), 0.07, 0.055, 6, hubmat)
        R.blade(hub, d, V(0, 1, 0), root * 0.9, radius, chord, chord * 0.92, thick, pitch, blademat, cone=cone)
        # pitch link
        R.cyl(hub + d * 0.18 + ch * 0.12 + V(0, -0.1, 0), hub + d * 0.3 + ch * 0.12 + V(0, 0.0, 0), 0.012, 0.012, 4, hubmat)
        if tipmat:
            pass


def tail_rotor(R, hub, nblades, radius, chord, mat_blade, mat_hub, xoff=0.0, phase=math.pi / 2):
    hub = Vector(hub)
    R.cyl(hub + V(-0.07 + xoff, 0, 0), hub + V(0.07 + xoff, 0, 0), 0.075, 0.06, 8, mat_hub)
    for i in range(nblades):
        a = phase + 2 * PI * i / nblades
        d = V(0, math.cos(a), math.sin(a))
        R.blade(hub, d, V(1, 0, 0), 0.1, radius, chord, chord * 0.85, 0.03, 12.0, mat_blade, nst=3, taper_tip=False)


def blur_disc(P, hub, radius, mat='heli_rotor_blur'):
    P.disc(hub, radius, mat, seg=32)


def seat_bucket(P, c, mat, facing=1, w=0.48, d=0.46, back_h=0.62):
    """Simple seat: cushion + tilted back; facing = +1 means the occupant faces +z, -1 faces -z, 2 faces +x (left), -2 faces -x."""
    c = Vector(c)
    if abs(facing) == 1:
        P.box(c + V(0, 0.0, 0), (w, 0.1, d), mat, bevel=0.02)
        P.box(c + V(0, back_h / 2 + 0.05, -facing * (d / 2 - 0.04)), (w, back_h, 0.09), mat, rot=(-facing * -8, 0, 0), bevel=0.02)
    else:
        sgn = 1 if facing == 2 else -1
        P.box(c, (d, 0.1, w), mat, bevel=0.02)
        P.box(c + V(-sgn * (d / 2 - 0.04), back_h / 2 + 0.05, 0), (0.09, back_h, w), mat, bevel=0.02)


def m60(P, mount, side, mat_metal, mat_dark, mat_wood=None, belt_mat=None):
    """M60-style pintle gun, pivot at `mount`, barrel along +-x (outward = side). Absolute coords."""
    m = Vector(mount); s = side
    P.cyl(m + V(0, -0.22, 0), m + V(0, 0.0, 0), 0.025, 0.02, 6, mat_dark)                    # pintle post
    P.box(m + V(s * 0.05, 0.03, 0), (0.55, 0.11, 0.075), mat_dark, bevel=0.012)                 # receiver
    P.box(m + V(-s * 0.28, 0.0, 0), (0.12, 0.09, 0.06), mat_wood or mat_dark, bevel=0.015)       # butt
    P.cyl(m + V(s * 0.3, 0.035, 0), m + V(s * 0.92, 0.035, 0), 0.012, 0.01, 6, mat_metal)       # barrel
    P.cyl(m + V(s * 0.3, 0.035, 0), m + V(s * 0.6, 0.035, 0), 0.022, 0.022, 6, mat_dark)         # gas jacket / handguard
    P.box(m + V(s * 0.12, -0.11, 0.02), (0.12, 0.13, 0.1), mat_dark, bevel=0.01)                # ammo box
    P.box(m + V(s * 0.12, -0.04, 0.0), (0.05, 0.03, 0.16), belt_mat or mat_metal)               # feed belt
    P.box(m + V(s * 0.18, 0.09, 0), (0.1, 0.03, 0.02), mat_metal)                               # sight
    P.box(m + V(-s * 0.06, -0.01, 0.0), (0.06, 0.07, 0.04), mat_dark)                           # grip block


def minigun(P, mount, side, mat_metal, mat_dark):
    """Six-barrel minigun on a pintle; pivot at `mount`; barrels along +-x."""
    m = Vector(mount); s = side
    P.cyl(m + V(0, -0.3, 0), m + V(0, 0.0, 0), 0.03, 0.025, 6, mat_dark)
    P.box(m + V(0, 0.0, 0), (0.22, 0.2, 0.2), mat_dark, bevel=0.02)                              # gearbox/motor
    P.cyl(m + V(s * 0.1, 0, 0), m + V(s * 0.45, 0, 0), 0.07, 0.07, 8, mat_dark)                  # barrel housing
    for k in range(6):
        a = 2 * PI * k / 6
        yo, zo = 0.05 * math.cos(a), 0.05 * math.sin(a)
        P.cyl(m + V(s * 0.4, yo, zo), m + V(s * 1.05, yo, zo), 0.011, 0.011, 4, mat_metal, True)
    P.cyl(m + V(s * 1.0, 0, 0), m + V(s * 1.06, 0, 0), 0.07, 0.07, 8, mat_metal)                 # muzzle clamp
    P.box(m + V(-s * 0.05, -0.14, 0), (0.28, 0.2, 0.25), mat_dark, bevel=0.02)                    # ammo drum
    P.box(m + V(-s * 0.18, 0.02, 0), (0.1, 0.12, 0.12), mat_metal, bevel=0.01)                    # electric motor


def nav_lights(M, red, green, white):
    """red = (x,y,z) left pos light etc: pass dict of light positions."""
    pass
