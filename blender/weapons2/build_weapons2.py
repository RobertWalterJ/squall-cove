"""Squall Cove weapons set 2 (same conventions as build_weapons.py / weapons.glb).
  blender -b --python build_weapons2.py -- [--review] [--only lmg,rpg]
Writes ../../assets/weapons2.glb, weapons2.glb.b64.txt, ../review/weapons2/weapons2.json, muzzles.json and (with --review) one 3/4 PNG per node.

Blender axes: +x right of the gun, +y = muzzle direction (three -z), +z up (three +y). Every node is a top-level mesh whose origin is
the hold point (grip centre / handle / body centre). `rocket` is a CHILD node of `rpg`.
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'generators'))
import pg_set2
from pg_set2 import *

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
MUZZLE = {}

PAL.update({
    'rpg_green': dict(color='#4d5636', rough=0.7),
    'rpg_tan':   dict(color='#8a7a54', rough=0.8),
    'ammo_olive': dict(color='#4a5234', rough=0.7, metal=0.2),
    'canvas':    dict(color='#7a7456', rough=0.95),
    'canvas2':   dict(color='#665f44', rough=0.95),
    'smoke_grey': dict(color='#6b7176', rough=0.6, metal=0.2),
    'frag_green': dict(color='#3f4a2b', rough=0.55, metal=0.2),
    'flare_orange': dict(color='#d9591f', rough=0.5),
    'lens_red':  dict(color='#7a1d1d', rough=0.1, metal=0.2),
    'wire_red':  dict(color='#a8221f', rough=0.6),
    'wire_blue': dict(color='#1f3f8a', rough=0.6),
    'plast':     dict(color='#a9a58a', rough=0.8),
    'medic_bag': dict(color='#3f4a2b', rough=0.9),
    'rugged':    dict(color='#262a2d', rough=0.8),
    'rugged_o':  dict(color='#d9731f', rough=0.7),
    'weapon_screen': dict(color='#0f2a33', rough=0.2, emit='#5ad0ff', emit_str=1.5),
    'radio_grn': dict(color='#35402e', rough=0.8),
})


def shift(m, v):
    for o in m.parts: o.data.transform(Matrix.Translation(v))


def fin(m, G, muzzle=None):
    shift(m, (-G[0], -G[1], -G[2]))
    if muzzle is not None: MUZZLE[m.key] = tuple(round(muzzle[i] - G[i], 3) for i in range(3))
    return m


def trigger_group(m, y0, zb, lenf=0.07):
    m.b(-0.004, 0.004, y0, y0 + lenf, zb - 0.03, zb - 0.023, 'gun_metal')
    m.b(-0.004, 0.004, y0 + lenf - 0.007, y0 + lenf, zb - 0.03, zb, 'gun_metal')
    m.b(-0.003, 0.003, y0 + 0.02, y0 + 0.027, zb - 0.022, zb, 'gun_dark')


# ---------------------------------------------------------------- lmg
def lmg():
    m = M('lmg')
    m.b(-0.03, 0.03, -0.2, 0.28, 0.02, 0.13, 'gun_metal')                                   # receiver
    m.b(-0.024, 0.024, -0.12, 0.22, 0.13, 0.145, 'gun_steel')                               # feed cover
    m.b(-0.03, 0.03, 0.0, 0.14, 0.118, 0.125, 'gun_dark')
    m.b(-0.09, -0.035, -0.03, 0.1, -0.1, 0.03, 'ammo_olive')                                # ammo box on the left (-x)
    m.b(-0.092, -0.033, -0.03, 0.1, 0.03, 0.036, 'gun_dark')
    for i in range(6):                                                                      # belt rising to the feed port
        f = i / 5; m.b(-0.075 + 0.05 * f - 0.007, -0.075 + 0.05 * f + 0.007, 0.03, 0.05, 0.036 + 0.05 * f, 0.036 + 0.05 * f + 0.014, 'brass' if i % 2 else 'gun_steel')
    m.ext_x([(-0.2, 0.12), (-0.5, 0.105), (-0.52, -0.06), (-0.3, -0.045), (-0.2, 0.0)], -0.024, 0.024, 'gun_poly')   # stock
    m.b(-0.026, 0.026, -0.53, -0.515, -0.065, 0.11, 'rubber')
    m.b(-0.017, 0.017, -0.035, 0.025, -0.12, 0.03, 'gun_poly', rot=(-0.35, 0, 0))             # pistol grip
    m.rd((0, 0.28, 0.09), (0, 0.64, 0.09), 0.027, 'gun_dark', 10)                           # perforated shroud
    for z0 in range(5): m.b(-0.029, 0.029, 0.31 + 0.065 * z0, 0.33 + 0.065 * z0, 0.07, 0.11, 'gun_metal')
    m.rd((0, 0.64, 0.09), (0, 0.82, 0.09), 0.0105, 'gun_steel', 8)                          # barrel
    m.rd((0, 0.79, 0.09), (0, 0.85, 0.09), 0.0175, 'gun_dark', 8)                           # flash hider
    m.rd((0, 0.28, 0.055), (0, 0.6, 0.055), 0.0095, 'gun_steel', 6)                         # gas tube
    m.b(-0.003, 0.003, 0.7, 0.708, 0.098, 0.135, 'gun_dark')                                # front sight
    m.b(-0.008, 0.008, 0.62, 0.72, 0.114, 0.12, 'gun_dark')
    # carry handle on the barrel
    m.b(-0.007, 0.007, 0.36, 0.375, 0.115, 0.17, 'gun_metal'); m.b(-0.007, 0.007, 0.5, 0.515, 0.115, 0.17, 'gun_metal')
    m.b(-0.009, 0.009, 0.36, 0.515, 0.165, 0.178, 'gun_metal')
    m.b(-0.012, 0.012, 0.18, 0.2, 0.145, 0.165, 'gun_dark')                                 # rear sight
    # bipod, deployed
    m.b(-0.014, 0.014, 0.6, 0.63, 0.05, 0.075, 'gun_metal')
    for sg in (-1, 1):
        m.rd((sg * 0.012, 0.615, 0.06), (sg * 0.09, 0.665, -0.1), 0.005, 'gun_steel', 5)
        m.b(sg * 0.09 - 0.008, sg * 0.09 + 0.008, 0.655, 0.685, -0.108, -0.098, 'rubber')
    trigger_group(m, 0.0, 0.02, 0.06)
    return fin(m, (0, 0.0, -0.05), (0, 0.85, 0.09))


# ---------------------------------------------------------------- rpg + rocket (child)
RPG_G = (0, 0.0, -0.02)
def rpg():
    m = M('rpg')
    z0 = 0.1
    m.rd((0, -0.3, z0), (0, 0.5, z0), 0.04, 'rpg_green', 12)                                # tube
    m.add(cyl(0.065, 0.04, 0.1, 12, (0, -0.42, z0), (-math.pi / 2, 0, 0), mt('rpg_green')))  # rear blast flare (cone, wide end at the back)
    m.rd((0, -0.42, z0), (0, -0.425, z0), 0.066, 'gun_dark', 12)
    m.rd((0, 0.46, z0), (0, 0.5, z0), 0.046, 'gun_dark', 12)                                # front collar
    m.rd((0, -0.1, z0), (0, 0.0, z0), 0.0455, 'rpg_tan', 12)                                # bands
    m.rd((0, 0.2, z0), (0, 0.24, z0), 0.0455, 'rpg_tan', 12)
    m.b(-0.045, 0.045, -0.25, -0.02, 0.13, 0.15, 'rubber')                                  # shoulder pad
    m.b(-0.016, 0.016, -0.035, 0.025, -0.1, 0.06, 'gun_poly', rot=(-0.3, 0, 0))              # pistol grip
    m.b(-0.016, 0.016, 0.2, 0.25, 0.0, 0.065, 'gun_poly')                                   # foregrip
    m.b(-0.012, 0.012, 0.18, 0.28, 0.055, 0.065, 'gun_metal')
    m.b(0.04, 0.062, 0.03, 0.22, 0.12, 0.145, 'gun_metal')                                  # sight bracket + optic on the right
    m.b(0.045, 0.062, 0.03, 0.2, 0.145, 0.185, 'gun_dark')
    m.rd((0.0535, 0.2, 0.165), (0.0535, 0.203, 0.165), 0.017, 'lens_g', 8)
    m.b(-0.012, 0.012, -0.02, 0.1, 0.06, 0.07, 'gun_metal')                                 # trigger housing
    trigger_group(m, 0.0, 0.0, 0.05)
    return fin(m, RPG_G, (0, 0.55, z0))


def rocket():
    m = M('rocket')
    z0 = 0.1
    m.rd((0, 0.3, z0), (0, 0.56, z0), 0.028, 'rpg_tan', 10)                                 # motor section (inside the tube)
    m.rd((0, 0.5, z0), (0, 0.66, z0), 0.052, 'frag_green', 12)                              # warhead body
    m.add(cyl(0.052, 0.006, 0.12, 12, (0, 0.66, z0), (-math.pi / 2, 0, 0), mt('frag_green')))   # ogive nose
    m.rd((0, 0.7, z0), (0, 0.775, z0), 0.0, 'gun_dark', 3) if False else None
    m.rd((0, 0.655, z0), (0, 0.665, z0), 0.054, 'gun_dark', 12)                             # seam ring
    for ang in (0, 1.5708, 3.1416, 4.7124):                                                  # fins, folded flat along the motor
        m.b(-0.002, 0.002, 0.3, 0.42, z0 + 0.03 * math.cos(ang) - 0.01 + 0.0, z0 + 0.03 * math.cos(ang) + 0.01, 'gun_steel', rot=(0, 0, 0)) if False else None
    for sx, sz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        m.b(sx * 0.03 - 0.0015 if sx else -0.0015, sx * 0.03 + 0.0015 if sx else 0.0015, 0.3, 0.38, z0 + sz * 0.03 - (0.0015 if sz else 0.0) if sz else z0 - 0.0015 - 0.0, z0 + sz * 0.03 + (0.0015 if sz else 0.0) if sz else z0 + 0.0015, 'gun_steel') if False else None
    fin(m, RPG_G)
    m.origin = (0 - RPG_G[0], 0.45 - RPG_G[1], z0 - RPG_G[2])
    return m


# ---------------------------------------------------------------- grenades
def grenade():
    m = M('grenade')
    m.add(lathe([(0.001, -0.046), (0.024, -0.043), (0.033, -0.026), (0.036, 0.0), (0.033, 0.026), (0.025, 0.04), (0.012, 0.045)], 10, mt('frag_green'), 'g'))
    for z in (-0.022, 0.0, 0.022): m.c(0.0365, 0.004, (0, 0, z - 0.002), 'gun_dark', 10)
    m.c(0.012, 0.022, (0, 0, 0.042), 'gun_steel', 8)                                         # fuze
    m.b(-0.006, 0.006, 0.0, 0.0, 0.0, 0.0, 'gun_steel') if False else None
    m.b(0.012, 0.0185, -0.008, 0.008, -0.036, 0.062, 'gun_steel')                            # safety lever (spoon) along the body
    m.b(0.0, 0.0185, -0.008, 0.008, 0.056, 0.064, 'gun_steel')
    m.add(torus(0.011, 0.0022, 12, 4, (-0.0, -0.012, 0.062), (math.pi / 2, 0, 0), mt('gun_steel')))   # pin ring
    return fin(m, (0, 0, 0))


def smoke_grenade():
    m = M('smoke_grenade')
    m.c(0.029, 0.125, (0, 0, -0.07), 'smoke_grey', 10)
    m.c(0.0295, 0.022, (0, 0, 0.03), 'yellow', 10)                                           # colour band (blank)
    m.c(0.0295, 0.008, (0, 0, -0.07), 'gun_dark', 10)
    m.c(0.027, 0.014, (0, 0, 0.055), 'gun_steel', 8)
    m.c(0.01, 0.02, (0, 0, 0.068), 'gun_steel', 8)                                           # fuze
    m.b(0.018, 0.0275, -0.008, 0.008, -0.04, 0.074, 'gun_steel')                             # lever
    m.add(torus(0.011, 0.0022, 12, 4, (0, -0.012, 0.078), (math.pi / 2, 0, 0), mt('gun_steel')))
    return fin(m, (0, 0, 0))


# ---------------------------------------------------------------- binoculars
def binoculars():
    m = M('binoculars')
    for sg in (-1, 1):
        x = sg * 0.037
        m.rd((x, -0.06, 0), (x, 0.08, 0), 0.026, 'gun_poly', 8)
        m.rd((x, 0.08, 0), (x, 0.115, 0), 0.034, 'gun_dark', 8)                             # objective bell
        m.rd((x, 0.115, 0), (x, 0.117, 0), 0.029, 'lens_g', 8)
        m.rd((x, -0.09, 0), (x, -0.06, 0), 0.023, 'rubber', 8)                              # eyecup
        m.b(x - 0.03, x + 0.03, -0.09, -0.06, -0.03, 0.03, 'gun_poly') if False else None
    m.b(-0.045, 0.045, -0.04, 0.02, -0.014, 0.014, 'gun_poly')                              # hinge bridge
    m.rd((-0.011, -0.01, 0.026), (0.011, -0.01, 0.026), 0.013, 'gun_steel', 8)              # focus wheel
    m.b(-0.075, -0.067, -0.02, 0.0, 0.0, 0.02, 'gun_steel')
    m.b(0.067, 0.075, -0.02, 0.0, 0.0, 0.02, 'gun_steel')
    return fin(m, (0, 0.0, 0), (0, 0.117, 0))


# ---------------------------------------------------------------- flare gun
def flare_gun():
    m = M('flare_gun')
    m.b(-0.016, 0.016, -0.046, 0.012, -0.085, 0.03, 'gun_poly', rot=(-0.2, 0, 0))            # grip
    m.b(-0.015, 0.015, -0.06, 0.07, 0.03, 0.09, 'flare_orange')                              # frame
    m.rd((0, 0.0, 0.075), (0, 0.19, 0.075), 0.021, 'flare_orange', 10)                       # wide barrel
    m.rd((0, 0.185, 0.075), (0, 0.19, 0.075), 0.017, 'gun_dark', 10)                         # muzzle opening
    m.rd((0, 0.19, 0.075), (0, 0.2, 0.075), 0.022, 'gun_dark', 10)
    m.b(-0.004, 0.004, -0.065, -0.045, 0.085, 0.115, 'gun_steel')                            # hammer
    m.b(-0.003, 0.003, 0.17, 0.178, 0.093, 0.108, 'gun_dark')                                # front sight
    trigger_group(m, 0.008, 0.03, 0.05)
    return fin(m, (0, -0.02, 0.0), (0, 0.2, 0.075))


# ---------------------------------------------------------------- marksman rifle
def marksman():
    m = M('marksman')
    m.b(-0.022, 0.022, -0.12, 0.22, 0.03, 0.1, 'gun_dark')                                   # receiver
    m.b(-0.014, 0.014, -0.1, 0.2, 0.1, 0.108, 'gun_steel')                                   # top rail
    m.b(-0.028, 0.028, 0.22, 0.52, 0.035, 0.1, 'gun_poly')                                   # handguard
    m.b(-0.012, 0.012, 0.22, 0.52, 0.1, 0.108, 'gun_steel')
    for y0 in (0.26, 0.32, 0.38, 0.44): m.b(-0.03, 0.03, y0, y0 + 0.02, 0.05, 0.085, 'gun_dark')   # vents
    m.rd((0, 0.52, 0.075), (0, 0.8, 0.075), 0.0105, 'gun_steel', 8)                          # barrel
    m.rd((0, 0.76, 0.075), (0, 0.84, 0.075), 0.0165, 'gun_dark', 8)                          # brake
    m.ext_x([(-0.12, 0.1), (-0.45, 0.092), (-0.465, -0.055), (-0.3, -0.05), (-0.12, 0.01)], -0.021, 0.021, 'gun_poly')   # stock
    m.b(-0.017, 0.017, -0.4, -0.2, 0.09, 0.115, 'gun_poly')                                  # cheek riser
    m.b(-0.022, 0.022, -0.475, -0.46, -0.06, 0.098, 'rubber')
    m.b(-0.017, 0.017, -0.035, 0.025, -0.12, 0.03, 'gun_poly', rot=(-0.3, 0, 0))             # grip
    m.b(-0.015, 0.015, 0.06, 0.12, -0.135, 0.035, 'gun_dark', rot=(0.12, 0, 0))             # 20 round magazine
    m.b(-0.016, 0.016, 0.06, 0.125, -0.145, -0.135, 'gun_metal', rot=(0.12, 0, 0))
    # scope
    m.rd((0, -0.04, 0.158), (0, 0.26, 0.158), 0.02, 'gun_dark', 10)
    m.rd((0, 0.2, 0.158), (0, 0.29, 0.158), 0.029, 'gun_dark', 10)
    m.rd((0, 0.291, 0.158), (0, 0.293, 0.158), 0.025, 'lens_g', 10)
    m.rd((0, -0.085, 0.158), (0, -0.04, 0.158), 0.026, 'gun_dark', 10)
    m.b(-0.011, 0.011, 0.07, 0.09, 0.172, 0.19, 'gun_metal')
    m.b(0.018, 0.034, 0.07, 0.09, 0.148, 0.166, 'gun_metal')
    m.b(-0.014, 0.014, 0.02, 0.045, 0.105, 0.14, 'gun_metal'); m.b(-0.014, 0.014, 0.17, 0.195, 0.105, 0.14, 'gun_metal')
    m.rd((0.02, 0.2, 0.06), (0.022, 0.0, 0.058), 0.004, 'gun_steel', 5) if False else None
    for sg in (-1, 1): m.rd((sg * 0.02, 0.42, 0.035), (sg * 0.026, 0.55, 0.03), 0.005, 'gun_steel', 5)   # folded bipod
    m.b(0.021, 0.027, 0.0, 0.03, 0.07, 0.09, 'gun_steel')                                   # charging handle
    trigger_group(m, 0.01, 0.03, 0.06)
    return fin(m, (0, -0.005, -0.05), (0, 0.84, 0.075))


# ---------------------------------------------------------------- scoped carbine
def carbine_scoped():
    m = M('carbine_scoped')
    m.b(-0.021, 0.021, -0.1, 0.2, 0.03, 0.098, 'gun_metal')
    m.b(-0.013, 0.013, -0.09, 0.19, 0.098, 0.106, 'gun_steel')
    m.b(-0.026, 0.026, 0.2, 0.36, 0.04, 0.1, 'gun_poly')
    m.rd((0, 0.36, 0.075), (0, 0.5, 0.075), 0.0095, 'gun_steel', 8)
    m.rd((0, 0.46, 0.075), (0, 0.53, 0.075), 0.0145, 'gun_dark', 8)
    m.ext_x([(-0.1, 0.095), (-0.1, 0.0), (-0.32, 0.0), (-0.33, 0.085), (-0.32, 0.095)], -0.019, 0.019, 'gun_poly')   # stock
    m.rd((0, -0.1, 0.07), (0, -0.28, 0.07), 0.01, 'gun_steel', 6)                              # collapsible tube
    m.b(-0.02, 0.02, -0.34, -0.325, -0.02, 0.1, 'rubber')
    m.b(-0.017, 0.017, -0.035, 0.025, -0.12, 0.03, 'gun_poly', rot=(-0.35, 0, 0))
    m.b(-0.015, 0.015, 0.075, 0.125, -0.1, 0.035, 'gun_dark', rot=(0.1, 0, 0))                # curved magazine
    m.b(-0.015, 0.015, 0.1, 0.16, -0.19, -0.1, 'gun_dark', rot=(0.3, 0, 0))
    m.b(-0.017, 0.017, 0.21, 0.26, -0.02, 0.04, 'gun_poly')                                   # foregrip
    # compact optic (red dot) on the rail
    m.b(-0.012, 0.012, 0.03, 0.1, 0.106, 0.118, 'gun_dark')
    m.b(-0.016, 0.016, 0.03, 0.1, 0.118, 0.15, 'gun_dark')
    m.b(-0.012, 0.012, 0.1, 0.103, 0.121, 0.146, 'lens_red')                                  # front lens
    m.b(-0.011, 0.011, 0.028, 0.03, 0.123, 0.145, 'lens_g')
    m.b(-0.003, 0.003, 0.17, 0.178, 0.106, 0.13, 'gun_dark')
    trigger_group(m, 0.01, 0.03, 0.06)
    return fin(m, (0, -0.005, -0.05), (0, 0.53, 0.075))


# ---------------------------------------------------------------- revolver
def revolver():
    m = M('revolver')
    m.b(-0.016, 0.016, -0.05, 0.012, -0.085, 0.03, 'gun_wood2', rot=(-0.25, 0, 0))            # wooden grip
    m.b(-0.012, 0.012, -0.045, 0.06, 0.03, 0.098, 'gun_steel')                                # frame
    m.rd((0, 0.0, 0.075), (0, 0.065, 0.075), 0.027, 'gun_steel', 8)                           # cylinder
    for k in range(6):
        a = k * math.pi / 3
        m.rd((0.017 * math.cos(a), 0.0, 0.075 + 0.017 * math.sin(a)), (0.017 * math.cos(a), 0.066, 0.075 + 0.017 * math.sin(a)), 0.0035, 'gun_dark', 4)
    m.rd((0, 0.06, 0.082), (0, 0.19, 0.082), 0.0105, 'gun_steel', 8)                          # barrel
    m.b(-0.007, 0.007, 0.07, 0.185, 0.055, 0.075, 'gun_steel')                                # underlug
    m.b(-0.003, 0.003, 0.18, 0.188, 0.092, 0.108, 'gun_dark')                                 # front sight
    m.b(-0.004, 0.004, -0.06, -0.04, 0.095, 0.12, 'gun_steel', rot=(-0.5, 0, 0))              # hammer
    trigger_group(m, 0.0, 0.03, 0.05)
    return fin(m, (0, -0.02, 0.0), (0, 0.19, 0.082))


# ---------------------------------------------------------------- satchel charge
def satchel_charge():
    m = M('satchel_charge')
    m.b(-0.13, 0.13, -0.05, 0.05, -0.2, -0.02, 'canvas')                                      # bag
    m.b(-0.135, 0.135, -0.055, 0.055, -0.1, -0.015, 'canvas2')                                # flap
    m.b(-0.04, 0.04, 0.05, 0.058, -0.095, -0.05, 'gun_steel')                                 # buckle on the front (+y)
    for x in (-0.075, 0.0, 0.075): m.b(x - 0.03, x + 0.03, -0.035, 0.035, -0.035, -0.02, 'plast')   # blocks at the opening
    m.add(torus(0.07, 0.009, 14, 4, (0, 0, -0.02), (math.pi / 2, 0, 0), mt('rope'), arc=math.pi))   # carry strap arch
    m.b(-0.03, 0.03, 0.058, 0.07, -0.17, -0.12, 'gun_dark')                                   # timer/detonator box on the front
    m.b(-0.02, 0.02, 0.07, 0.074, -0.16, -0.135, 'weapon_screen') if False else None
    m.rd((0.02, 0.07, -0.13), (0.09, 0.075, -0.06), 0.003, 'wire_red', 4)                      # wires
    m.rd((-0.02, 0.07, -0.13), (-0.09, 0.075, -0.07), 0.003, 'wire_blue', 4)
    m.rd((0.0, 0.07, -0.13), (0.0, 0.07, -0.02), 0.003, 'gun_dark', 4)
    return fin(m, (0, 0, 0.05))


# ---------------------------------------------------------------- radio handset
def radio_handset():
    m = M('radio_handset')
    m.b(-0.03, 0.03, -0.018, 0.018, -0.09, 0.06, 'radio_grn')                                 # body
    m.b(-0.034, 0.034, -0.021, 0.021, 0.06, 0.1, 'radio_grn')                                 # head
    m.b(-0.02, 0.02, -0.0215, -0.0185, 0.065, 0.095, 'gun_dark')                              # speaker grille (towards the user, -y)
    for z in (0.07, 0.078, 0.086): m.b(-0.017, 0.017, -0.0235, -0.0215, z, z + 0.004, 'gun_steel')
    m.b(-0.02, 0.02, -0.0195, -0.0185, 0.0, 0.045, 'gun_dark')                                # keypad block
    m.rd((0.02, 0, 0.1), (0.02, 0, 0.27), 0.0055, 'rubber', 5)                                # antenna
    m.rd((-0.015, 0, 0.1), (-0.015, 0, 0.115), 0.009, 'gun_steel', 8)                         # knob
    m.b(0.03, 0.037, -0.01, 0.01, 0.0, 0.045, 'rubber')                                       # push to talk
    m.b(-0.026, 0.026, 0.018, 0.026, -0.08, 0.0, 'gun_dark')                                  # belt clip (back)
    return fin(m, (0, 0, 0))


# ---------------------------------------------------------------- medkit bag
def medkit_bag():
    m = M('medkit_bag')
    m.b(-0.14, 0.14, -0.06, 0.06, -0.19, -0.02, 'medic_bag')
    m.b(-0.145, 0.145, -0.065, 0.065, -0.05, -0.012, 'medic_bag')                             # lid
    m.b(-0.1, 0.1, 0.06, 0.066, -0.15, -0.07, 'white')                                        # panel (blank, flat)
    m.b(-0.1, 0.1, -0.066, -0.06, -0.15, -0.07, 'white')
    for y in (0.0665, -0.0665):                                                               # flat red cross, both sides
        m.b(-0.05, 0.05, y - 0.002, y + 0.002, -0.122, -0.098, 'red'); m.b(-0.012, 0.012, y - 0.002, y + 0.002, -0.15, -0.07, 'red')
    m.b(-0.14, 0.14, -0.002, 0.002, -0.185, -0.185, 'gun_dark') if False else None
    m.rd((-0.13, 0.0, -0.05), (0.13, 0.0, -0.05), 0.003, 'gun_dark', 4)                       # zip line
    m.add(torus(0.07, 0.008, 14, 4, (0, 0, -0.012), (math.pi / 2, 0, 0), mt('rope'), arc=math.pi))
    for sg in (-1, 1): m.b(sg * 0.14, sg * 0.152, -0.04, 0.04, -0.17, -0.12, 'gun_dark')       # end pockets
    return fin(m, (0, 0, 0.06))


# ---------------------------------------------------------------- rugged tablet
def tablet_device():
    m = M('tablet_device')
    # lies in the x-z plane (landscape, 0.25 x 0.17), thin along y; the screen faces -y (toward a viewer behind a muzzle-forward hold)
    m.b(-0.125, 0.125, -0.011, 0.011, -0.085, 0.085, 'rugged')
    m.b(-0.1, 0.1, -0.0118, -0.0105, -0.062, 0.062, 'weapon_screen')                          # emissive screen
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.b(sx * 0.125 - 0.012 + 0.012 * (sx > 0) * 0, sx * 0.125 + 0.012 * 0, -0.014, 0.014, sz * 0.085 - 0.012, sz * 0.085 + 0.012, 'rugged_o') if False else None
            m.b(min(sx * 0.108, sx * 0.13), max(sx * 0.108, sx * 0.13), -0.014, 0.014, min(sz * 0.063, sz * 0.09), max(sz * 0.063, sz * 0.09), 'rugged_o')   # bumper corners
    m.b(-0.04, 0.04, 0.011, 0.018, -0.03, 0.03, 'rugged_o')                                    # back kickstand plate
    m.b(0.03, 0.036, -0.004, 0.004, 0.085, 0.096, 'gun_steel')                                 # power button
    m.rd((0.0, -0.0125, 0.073), (0.0, -0.0128, 0.073), 0.003, 'gun_steel', 6)                  # camera dot
    return fin(m, (0, 0, 0))


# ---------------------------------------------------------------- export hook: parent `rocket` to `rpg`
_orig_export = pg_set2.export_glb
def _export(objs, path):
    byname = {o.name: o for o in objs}
    if 'rocket' in byname and 'rpg' in byname:
        c, p = byname['rocket'], byname['rpg']
        c.parent = p; c.matrix_parent_inverse = p.matrix_world.inverted()
    _orig_export(objs, path)
pg_set2.export_glb = _export

MODELS = [lmg, rpg, rocket, grenade, smoke_grenade, binoculars, flare_gun, marksman, carbine_scoped, revolver, satchel_charge, radio_handset, medkit_bag, tablet_device]
objs, man = run(MODELS, 'weapons2', 'weapons2', (0.9, 0.55, 0.35), argv)
json.dump(MUZZLE, open(os.path.join(ROOT, 'blender', 'review', 'weapons2', 'muzzles.json'), 'w'), indent=1)
if '--only' not in argv:
    import shutil
    shutil.copyfile(os.path.join(__import__('tempfile').gettempdir(), 'sc_weapons2.glb'), os.path.join(ROOT, 'assets', 'weapons2.glb'))
print('MUZZLES', json.dumps(MUZZLE))
