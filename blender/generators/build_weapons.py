"""Squall Cove hand weapons and first-person arms.
  blender -b --python build_weapons.py -- [--review] [--only pistol,rifle]
Writes ../../assets/weapons.glb.b64.txt, ../review/weapons/weapons.json and (with --review) one 3/4 PNG per node.

Blender axes: +x right of the gun, +y = muzzle direction (three -z), +z up (three +y). Every weapon is a top-level mesh
node whose origin is the centre of the grip (where the hand holds it), so parenting to a camera or hand bone needs no
rotation. Design positions below are written in a convenient frame and shifted by -G so the grip centre is (0, 0, 0).
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pg_set2 import *

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
MUZZLE = {}   # key -> muzzle position in node space (Blender axes)


def shift(m, v):
    for o in m.parts: o.data.transform(Matrix.Translation(v))


def fin(m, G, muzzle):
    shift(m, (-G[0], -G[1], -G[2]))
    MUZZLE[m.key] = tuple(round(muzzle[i] - G[i], 3) for i in range(3))
    return m


def snap_z(m):
    lo = min(v.co.z for o in m.parts for v in o.data.vertices)
    shift(m, (0, 0, -lo))


def trigger_group(m, y0, zb, lenf=0.07):
    """Trigger guard and trigger under a receiver whose bottom is at zb."""
    m.b(-0.004, 0.004, y0, y0 + lenf, zb - 0.03, zb - 0.023, 'gun_metal')
    m.b(-0.004, 0.004, y0 + lenf - 0.007, y0 + lenf, zb - 0.03, zb, 'gun_metal')
    m.b(-0.003, 0.003, y0 + 0.02, y0 + 0.027, zb - 0.022, zb, 'gun_dark')


# ---------------------------------------------------------------- pistol
def pistol():
    m = M('pistol')
    m.b(-0.016, 0.016, -0.046, 0.012, -0.075, 0.03, 'gun_poly', rot=(-0.2, 0, 0))      # grip
    m.b(-0.014, 0.014, -0.05, 0.14, 0.03, 0.052, 'gun_dark')                               # frame
    m.b(-0.015, 0.015, -0.055, 0.14, 0.052, 0.088, 'gun_metal')                            # slide
    m.b(-0.016, 0.016, 0.0, 0.016, 0.052, 0.088, 'gun_steel')                              # slide serrations block
    m.rd((0, 0.14, 0.07), (0, 0.158, 0.07), 0.0065, 'gun_steel', 8)                        # barrel tip
    m.b(-0.003, 0.003, 0.128, 0.136, 0.088, 0.096, 'gun_dark')                             # front sight
    m.b(-0.011, 0.011, -0.05, -0.04, 0.088, 0.096, 'gun_dark')                             # rear sight
    trigger_group(m, 0.008, 0.03, 0.05)
    m.b(-0.015, 0.015, -0.062, -0.028, -0.082, -0.07, 'gun_dark', rot=(-0.2, 0, 0))       # mag base
    return fin(m, (0, -0.02, 0.0), (0, 0.158, 0.07))


# ---------------------------------------------------------------- smg
def smg():
    m = M('smg')
    m.b(-0.02, 0.02, -0.11, 0.2, 0.02, 0.09, 'gun_metal')                                  # receiver
    m.b(-0.012, 0.012, -0.1, 0.19, 0.09, 0.097, 'gun_steel')
    m.rd((0, 0.2, 0.062), (0, 0.31, 0.062), 0.0165, 'gun_dark', 8)                         # barrel shroud
    m.rd((0, 0.31, 0.062), (0, 0.365, 0.062), 0.0085, 'gun_steel', 8)
    m.b(-0.017, 0.017, 0.14, 0.2, -0.05, 0.02, 'gun_poly')                                 # foregrip
    m.b(-0.017, 0.017, -0.035, 0.025, -0.1, 0.03, 'gun_poly', rot=(-0.3, 0, 0))            # pistol grip
    m.b(-0.014, 0.014, 0.065, 0.095, -0.19, 0.02, 'gun_dark')                              # magazine
    m.b(-0.015, 0.015, 0.062, 0.098, -0.2, -0.19, 'gun_metal')
    m.rd((0.012, -0.11, 0.075), (0.012, -0.28, 0.075), 0.0045, 'gun_steel', 5)              # folded wire stock
    m.rd((-0.012, -0.11, 0.075), (-0.012, -0.28, 0.075), 0.0045, 'gun_steel', 5)
    m.b(-0.014, 0.014, -0.295, -0.28, 0.025, 0.095, 'gun_poly')
    m.b(-0.003, 0.003, 0.2, 0.208, 0.097, 0.125, 'gun_dark')                               # front sight
    m.b(-0.014, 0.014, -0.085, -0.075, 0.097, 0.118, 'gun_dark')                           # rear sight
    trigger_group(m, 0.02, 0.02, 0.06)
    return fin(m, (0, -0.005, -0.04), (0, 0.365, 0.062))


# ---------------------------------------------------------------- rifle (shifted frame used again for the arms)
RG = (0, -0.005, -0.05)
def rifle_parts(m):
    m.b(-0.022, 0.022, -0.10, 0.20, 0.03, 0.098, 'gun_metal')                              # receiver
    m.b(-0.018, 0.018, -0.09, 0.19, 0.098, 0.108, 'gun_steel')                             # dust cover
    m.b(-0.028, 0.028, 0.20, 0.46, 0.04, 0.105, 'gun_wood')                                # handguard
    m.b(-0.022, 0.022, 0.28, 0.46, 0.105, 0.12, 'gun_wood2')                               # upper handguard
    m.rd((0, 0.46, 0.075), (0, 0.745, 0.075), 0.0095, 'gun_dark', 8)                       # barrel
    m.rd((0, 0.2, 0.128), (0, 0.5, 0.128), 0.0085, 'gun_steel', 6)                         # gas tube
    m.rd((0, 0.70, 0.075), (0, 0.775, 0.075), 0.0145, 'gun_dark', 8)                       # flash hider
    m.b(-0.004, 0.004, 0.62, 0.628, 0.082, 0.13, 'gun_dark')                               # front sight post
    m.b(-0.011, 0.011, 0.6, 0.64, 0.07, 0.085, 'gun_dark')
    m.b(-0.012, 0.012, 0.15, 0.17, 0.108, 0.128, 'gun_dark')                               # rear sight
    m.b(-0.02, 0.02, -0.40, -0.10, -0.035, 0.09, 'gun_wood')                               # stock
    m.b(-0.022, 0.022, -0.412, -0.40, -0.05, 0.095, 'gun_dark')                            # butt plate
    m.b(-0.017, 0.017, -0.035, 0.025, -0.12, 0.03, 'gun_poly', rot=(-0.35, 0, 0))          # pistol grip
    m.b(-0.016, 0.016, 0.075, 0.125, -0.10, 0.035, 'gun_dark', rot=(0.1, 0, 0))            # magazine upper
    m.b(-0.016, 0.016, 0.1, 0.16, -0.205, -0.10, 'gun_dark', rot=(0.3, 0, 0))              # magazine lower (curve)
    trigger_group(m, 0.01, 0.03, 0.06)

def rifle():
    m = M('rifle'); rifle_parts(m)
    return fin(m, RG, (0, 0.775, 0.075))


# ---------------------------------------------------------------- shotgun (pump)
def shotgun():
    m = M('shotgun')
    m.b(-0.022, 0.022, -0.09, 0.17, 0.035, 0.105, 'gun_metal')                              # receiver
    m.b(0.0215, 0.0235, -0.01, 0.09, 0.06, 0.092, 'gun_dark')                               # ejection port
    m.ext_x([(-0.09, 0.105), (-0.45, 0.095), (-0.46, -0.075), (-0.2, -0.02), (-0.09, 0.02)], -0.02, 0.02, 'gun_wood')  # stock
    m.b(-0.022, 0.022, -0.465, -0.455, -0.08, 0.1, 'gun_dark')
    m.rd((0, 0.17, 0.092), (0, 0.78, 0.092), 0.0145, 'gun_dark', 8)                          # barrel
    m.rd((0, 0.17, 0.062), (0, 0.6, 0.062), 0.0125, 'gun_metal', 8)                          # magazine tube
    m.rd((0, 0.6, 0.062), (0, 0.615, 0.062), 0.016, 'gun_dark', 8)
    m.b(-0.033, 0.033, 0.26, 0.43, 0.036, 0.086, 'gun_wood2')                               # pump forend
    m.b(-0.003, 0.003, 0.765, 0.775, 0.104, 0.116, 'gun_steel')                              # bead sight
    m.b(-0.006, 0.006, 0.18, 0.64, 0.103, 0.108, 'gun_dark')                                  # rib
    trigger_group(m, 0.0, 0.035, 0.06)
    return fin(m, (0, -0.11, 0.04), (0, 0.78, 0.092))


# ---------------------------------------------------------------- sniper
def sniper():
    m = M('sniper')
    m.b(-0.02, 0.02, -0.08, 0.25, 0.03, 0.095, 'gun_metal')                                  # receiver
    m.ext_x([(-0.08, 0.095), (-0.2, 0.105), (-0.52, 0.105), (-0.54, -0.07), (-0.27, -0.03), (-0.2, 0.0), (-0.1, 0.03)],
            -0.021, 0.021, 'gun_wood2')                                                       # stock
    m.b(-0.022, 0.022, -0.55, -0.54, -0.075, 0.108, 'gun_dark')
    m.b(-0.017, 0.017, -0.04, 0.025, -0.11, 0.03, 'gun_wood2', rot=(-0.35, 0, 0))            # grip
    m.b(-0.025, 0.025, 0.1, 0.42, 0.025, 0.07, 'gun_wood2')                                  # forend
    m.rd((0, 0.25, 0.072), (0, 0.9, 0.072), 0.0125, 'gun_dark', 8)                           # heavy barrel
    m.rd((0, 0.88, 0.072), (0, 0.95, 0.072), 0.0175, 'gun_dark', 8)                          # muzzle brake
    m.rd((0, -0.05, 0.158), (0, 0.27, 0.158), 0.022, 'gun_dark', 10)                         # scope tube
    m.rd((0, 0.2, 0.158), (0, 0.31, 0.158), 0.032, 'gun_dark', 10)                           # objective bell
    m.rd((0, 0.311, 0.158), (0, 0.313, 0.158), 0.028, 'lens_g', 10)                          # lens
    m.rd((0, -0.09, 0.158), (0, -0.04, 0.158), 0.028, 'gun_dark', 10)                        # eyepiece
    m.b(-0.011, 0.011, 0.08, 0.1, 0.178, 0.198, 'gun_metal')                                 # elevation turret
    m.b(0.02, 0.04, 0.08, 0.1, 0.148, 0.168, 'gun_metal')                                    # windage turret
    m.b(-0.013, 0.013, 0.1, 0.12, 0.095, 0.138, 'gun_metal')                                 # rear scope ring
    m.b(-0.013, 0.013, 0.2, 0.22, 0.095, 0.138, 'gun_metal')                                 # front scope ring
    m.rd((0.02, -0.02, 0.078), (0.075, -0.02, 0.058), 0.005, 'gun_steel', 5)                 # bolt handle
    m.add(ico(0.012, 1, (0.08, -0.02, 0.054), mt('gun_dark')))
    m.b(-0.015, 0.015, 0.02, 0.1, -0.045, 0.03, 'gun_metal')                                 # magazine
    m.rd((0.02, 0.4, 0.03), (0.026, 0.58, 0.024), 0.005, 'gun_steel', 5)                     # folded bipod legs
    m.rd((-0.02, 0.4, 0.03), (-0.026, 0.58, 0.024), 0.005, 'gun_steel', 5)
    trigger_group(m, 0.0, 0.03, 0.055)
    return fin(m, (0, -0.01, -0.04), (0, 0.95, 0.072))


# ---------------------------------------------------------------- knife
def knife():
    m = M('knife')
    m.b(-0.014, 0.014, -0.06, 0.06, -0.018, 0.018, 'gun_wood2')                              # handle
    m.b(-0.0165, 0.0165, -0.072, -0.06, -0.02, 0.02, 'gun_steel')                            # pommel
    m.b(-0.022, 0.022, 0.06, 0.07, -0.03, 0.024, 'gun_steel')                                # guard
    m.ext_x([(0.07, 0.015), (0.21, 0.015), (0.285, -0.008), (0.21, -0.022), (0.07, -0.022)], -0.0025, 0.0025, 'blade')
    m.b(-0.0035, 0.0035, 0.07, 0.21, 0.011, 0.015, 'gun_steel')                              # spine
    m.b(-0.0148, 0.0148, -0.045, -0.035, -0.0185, 0.0185, 'gun_dark')                        # grip ring
    m.b(-0.0148, 0.0148, 0.0, 0.01, -0.0185, 0.0185, 'gun_dark')
    return fin(m, (0, 0, 0), (0, 0.285, -0.008))


# ---------------------------------------------------------------- loose magazine
def magazine():
    m = M('magazine')
    m.b(-0.016, 0.016, -0.03, 0.02, 0.1, 0.2, 'gun_dark', rot=(0.1, 0, 0))
    m.b(-0.016, 0.016, 0.0, 0.05, 0.0, 0.11, 'gun_dark', rot=(0.3, 0, 0))
    m.b(-0.0165, 0.0165, -0.04, 0.0, 0.2, 0.208, 'gun_metal')                                # feed lips
    m.b(-0.012, 0.012, -0.03, -0.005, 0.205, 0.215, 'brass')                                 # top round
    m.b(-0.018, 0.018, -0.02, 0.07, -0.004, 0.006, 'gun_metal')                              # floor plate
    snap_z(m)
    return m


# ---------------------------------------------------------------- muzzle flash (placed at the rifle muzzle)
def muzzle_flash():
    pos = (0.0, 0.775 + 0.02 - RG[1], 0.075 - RG[2])
    m = M('muzzle_flash', origin=pos)
    vs = [pos]; fs = []
    n = 16
    for i in range(n):
        a = 2 * math.pi * i / n + 0.12
        r = [0.13, 0.04, 0.085, 0.04][i % 4] if i % 2 == 0 else 0.032
        r = {0: 0.14, 2: 0.07, 4: 0.12, 6: 0.065, 8: 0.14, 10: 0.07, 12: 0.12, 14: 0.065}.get(i, 0.035)
        vs.append((pos[0] + r * math.cos(a), pos[1], pos[2] + r * math.sin(a)))
    for i in range(n):
        fs.append((0, 1 + i, 1 + (i + 1) % n))
    # winding: viewed from -y (the camera looks along +y in Blender = -z in three), counter-clockwise needs reversal
    m.cloth(vs, [tuple(reversed(f)) for f in fs], 'flash')
    return m


# ---------------------------------------------------------------- arms (same frame as the rifle: grip centre = origin)
def arms_idle():
    m = M('arms_idle')
    S = Vector((0, 0, 0))
    def forearm(wrist, elbow, far):
        w = Vector(wrist); e = Vector(elbow); f = Vector(far)
        m.rd(w, w + (e - w) * 0.34, 0.03, 'skin', 8)                                         # bare forearm
        m.rd(w + (e - w) * 0.30, w + (e - w) * 0.38, 0.05, 'cuff', 8)                        # cuff
        m.rd(w + (e - w) * 0.38, f, 0.047, 'olive_cloth', 8)                                 # sleeve
    # right hand on the pistol grip
    m.b(-0.03, 0.03, -0.062, -0.026, -0.055, 0.075, 'skin')
    m.b(0.017, 0.031, -0.06, 0.05, -0.055, 0.012, 'skin')
    m.b(-0.031, -0.017, -0.06, 0.05, -0.055, 0.012, 'skin')
    for z0 in (-0.058, -0.035, -0.012):
        m.b(-0.03, 0.03, 0.022, 0.05, z0, z0 + 0.021, 'skin')                                # three curled fingers
    m.b(-0.008, 0.008, 0.0, 0.07, 0.062, 0.084, 'skin')                                      # trigger finger
    m.b(-0.047, -0.03, -0.05, 0.025, 0.02, 0.07, 'skin')                                     # thumb
    forearm((0.012, -0.075, 0.008), (0.1, -0.31, -0.095), (0.2, -0.62, -0.20))
    # left hand cupping the handguard
    m.b(-0.03, 0.03, 0.25, 0.35, 0.05, 0.09, 'skin')
    for i in range(4):
        y0 = 0.25 + 0.025 * i + 0.003 * i
        m.b(0.028, 0.052, y0, y0 + 0.024, 0.06, 0.15, 'skin')
    m.b(-0.052, -0.03, 0.26, 0.32, 0.09, 0.15, 'skin')
    forearm((-0.005, 0.25, 0.062), (-0.12, -0.02, -0.04), (-0.27, -0.40, -0.17))
    return m


MODELS = [pistol, smg, rifle, shotgun, sniper, knife, muzzle_flash, magazine, arms_idle]
objs, man = run(MODELS, 'weapons', 'weapons', (0.9, 0.55, 0.35), argv,
                extra_review=[('arms_with_rifle', ['arms_idle', 'rifle'])])
print('MUZZLES', json.dumps(MUZZLE))
json.dump(MUZZLE, open(os.path.join(ROOT, 'blender', 'review', 'weapons', 'muzzles.json'), 'w'), indent=1)
