"""Gun emplacements with true kinematic chains: yaw > pitch > recoil slide. Game coords (x left, y up, z forward, metres)."""
from e_lib import *


def handwheel(P, c, r, side, mat='emp_steel_dark'):
    """Hand wheel with its axis along x at centre c; `side` = +1/-1 is the outward direction of the crank handle."""
    c = Vector(c)
    P.cyl(c - V(0.03 * side, 0, 0), c + V(0.03 * side, 0, 0), 0.035, 0.035, 8, mat, False)
    loop(P, c, r, 0.012, 'x', mat, n=10, seg=4)
    for k in range(3):
        a = rad(k * 120 + 20); P.sweep([tuple(c), tuple(c + V(0, r * math.cos(a), r * math.sin(a)))], 0.008, 4, mat, False, (False, False))
    h = c + V(0.05 * side, r * 0.95, 0)
    P.cyl(tuple(h), tuple(h + V(0.07 * side, 0, 0)), 0.014, 0.014, 6, 'emp_black', False)


# ================================================================== twin anti-aircraft cannon
def emp_aa():
    M = EM('emp_aa'); rng = random.Random(7)
    YP = (0.0, 0.86, 0.0); TP = (0.0, 1.32, 0.0)
    B = M.node('_base', None, (0, 0, 0))
    # round pad + earth apron
    B.cyl((0, 0, 0), (0, 0.10, 0), 2.6, 2.6, 32, 'emp_concrete', False)
    B.cyl((0, 0, 0), (0, 0.03, 0), 3.1, 3.1, 32, 'emp_earth', False)
    for k in range(4): B.box((0, 0.103, 0), (0.03, 0.006, 5.1), 'emp_concrete_dark', rot=(0, k * 45, 0))   # expansion joints
    # cruciform outrigger base with levelling jacks
    for a in (45, 135, 225, 315):
        sx, cz = math.sin(rad(a)), math.cos(rad(a))
        bar(B, (0, 0.22, 0), (1.5 * sx, 0.20, 1.5 * cz), 0.17, 'emp_steel')
        e = (1.5 * sx, 0, 1.5 * cz)
        B.cyl((e[0], 0.10, e[2]), (e[0], 0.34, e[2]), 0.05, 0.05, 8, 'emp_steel_dark', False)
        B.box((e[0], 0.115, e[2]), (0.32, 0.03, 0.32), 'emp_steel_dark', rot=(0, a, 0))
        B.cyl((e[0], 0.34, e[2]), (e[0], 0.37, e[2]), 0.075, 0.075, 6, 'emp_black', False)
    B.cyl((0, 0.10, 0), (0, 0.28, 0), 0.52, 0.46, 16, 'emp_steel_dark', False)
    B.cyl((0, 0.28, 0), (0, 0.80, 0), 0.22, 0.22, 12, 'emp_steel', False)
    B.cyl((0, 0.80, 0), (0, 0.86, 0), 0.32, 0.32, 14, 'emp_steel_dark', False)
    # sandbag ring open at the rear, plus ammunition crates
    bagarc(B, (0, 0, 0), 2.25, -150, 150, 4, rng, y0=0.10)
    crate(B, (1.15, 0.10, -1.95), (0.75, 0.40, 0.45), 15)
    crate(B, (-1.0, 0.10, -2.0), (0.75, 0.40, 0.45), -10)
    ammo_box(B, (-1.0, 0.60, -2.0), (0.5, 0.22, 0.28), yaw=-10)
    ammo_box(B, (1.15, 0.58, -1.95), (0.5, 0.18, 0.28), yaw=15)
    # ---- yaw: turntable, yoke, hand wheels, rotating gunner platform
    Y = M.node('_yaw', None, YP)
    Y.cyl((0, 0.86, 0), (0, 0.96, 0), 0.48, 0.46, 18, 'emp_steel_dark', False)
    Y.cyl((0, 0.96, 0), (0, 1.00, 0), 0.40, 0.40, 14, 'emp_steel', False)
    for sx in (-1, 1):
        slab(Y, [(-0.36, 0.97), (0.38, 0.97), (0.28, 1.58), (-0.22, 1.58)], (sx * 0.40, 0, 0), (0, 0, 1), (0, 1, 0), 0.06, 'emp_paint')
        Y.cyl((sx * 0.36, 1.32, 0), (sx * 0.54, 1.32, 0), 0.10, 0.10, 10, 'emp_steel_dark', False)
        Y.cyl((sx * 0.54, 1.32, 0), (sx * 0.57, 1.32, 0), 0.06, 0.06, 8, 'emp_black', False)
    bx(Y, -0.40, 0.40, 1.00, 1.12, -0.34, -0.26, 'emp_paint')
    bx(Y, -0.40, 0.40, 1.46, 1.54, -0.20, -0.12, 'emp_paint')
    handwheel(Y, (-0.60, 1.08, -0.16), 0.13, -1)
    handwheel(Y, (0.60, 0.98, -0.20), 0.15, 1)
    # gunner platform (half disc behind the pedestal) carried by two struts
    arc = [(0.95 * math.cos(rad(t)), -0.28 - 0.70 * math.sin(rad(t))) for t in range(0, 181, 30)]
    slab(Y, arc, (0, 0.38, 0), (1, 0, 0), (0, 0, 1), 0.04, 'emp_steel_dark')
    for sx in (-1, 1):
        bar(Y, (sx * 0.34, 1.0, -0.22), (sx * 0.78, 0.40, -0.46), 0.05, 'emp_steel')
        bar(Y, (sx * 0.34, 0.92, -0.20), (sx * 0.30, 0.38, -0.30), 0.04, 'emp_steel')
    for k in range(5): Y.box((0, 0.403, -0.38 - k * 0.12), (1.5 - 0.15 * k, 0.006, 0.02), 'emp_black')   # tread lines
    M.empty('emp_aa_seat', (0.0, 0.40, -0.66), 'emp_aa_yaw', 'ARROWS')
    # ---- pitch (cradle, magazines, shield plates, sights) about the trunnion axis
    P = M.node('_pitch', 'emp_aa_yaw', TP)
    for sx in (-1, 1):
        rod(P, (sx * 0.17, 1.32, -0.20), (sx * 0.17, 1.32, 0.98), 0.075, 'emp_paint', 8)
        bx(P, sx * 0.17 - 0.05, sx * 0.17 + 0.05, 1.25, 1.40, 0.95, 1.03, 'emp_steel_dark')      # front guide bush
    bx(P, -0.26, 0.26, 1.23, 1.41, -0.22, -0.10, 'emp_paint')
    bx(P, -0.10, 0.10, 1.20, 1.44, -0.12, 0.92, 'emp_paint')
    rod(P, (-0.46, 1.32, 0), (0.46, 1.32, 0), 0.05, 'emp_steel_dark', 8)
    for sx in (-1, 1): bx(P, sx * 0.27 - 0.07, sx * 0.27 + 0.07, 1.22, 1.44, -0.12, 0.12, 'emp_steel_dark')
    for sx in (-1, 1):                                       # side magazines on top of the cradle, with feed throats
        ammo_box(P, (sx * 0.27, 1.54, -0.06), (0.15, 0.20, 0.34))
        bx(P, sx * 0.17 - 0.04, sx * 0.17 + 0.04, 1.40, 1.46, -0.16, 0.04, 'emp_steel_dark')
    # gunner shield: two folded wings + upper and lower centre plates (all carried by the cradle)
    for sx in (-1, 1):
        wing(P, sx * 0.28, sx * 0.70, 0.98, 1.86, 0.52, 0.026, 'emp_paint', fold=14, ch=0.12)
        for yy in (1.20, 1.60): bx(P, sx * 0.30 - 0.0, sx * 0.62, yy, yy + 0.04, 0.495, 0.515, 'emp_steel_dark')
        bar(P, (sx * 0.13, 1.22, 0.92), (sx * 0.34, 1.02, 0.52), 0.04, 'emp_steel')
        bar(P, (sx * 0.13, 1.42, 0.92), (sx * 0.34, 1.70, 0.52), 0.04, 'emp_steel')
    bx(P, -0.28, 0.28, 1.52, 1.68, 0.50, 0.526, 'emp_paint')
    bx(P, -0.28, 0.28, 0.98, 1.18, 0.50, 0.526, 'emp_paint')
    # sights: ring sight on a post at the rear, bead foresight at the front
    bx(P, -0.025, 0.025, 1.44, 1.80, -0.14, -0.09, 'emp_steel_dark')
    loop(P, (0, 1.85, -0.115), 0.075, 0.008, 'z', 'emp_black', n=12, seg=4)
    bx(P, -0.012, 0.012, 1.44, 1.74, 0.90, 0.93, 'emp_steel_dark')
    P.cyl((0, 1.74, 0.915), (0, 1.77, 0.915), 0.014, 0.012, 6, 'emp_yellow', False)
    # ---- recoil slide: twin receivers, cooling jackets, barrels and muzzle brakes
    R = M.node('_barrels', 'emp_aa_pitch', (0.0, 1.32, 0.0))
    for sx in (-1, 1):
        x = sx * 0.17
        bx(R, x - 0.065, x + 0.065, 1.255, 1.385, -0.34, 0.22, 'emp_steel_dark')
        rod(R, (x, 1.32, -0.34), (x, 1.32, -0.44), 0.045, 'emp_steel', 8)
        R.cyl((x, 1.32, 0.22), (x, 1.32, 0.94), 0.052, 0.050, 8, 'emp_steel', False)
        for z in (0.34, 0.50, 0.66, 0.82): R.cyl((x, 1.32, z), (x, 1.32, z + 0.035), 0.060, 0.060, 8, 'emp_steel_dark', False)
        R.cyl((x, 1.32, 0.94), (x, 1.32, 1.90), 0.027, 0.021, 8, 'emp_steel_dark', False)
        R.cyl((x, 1.32, 1.86), (x, 1.32, 2.04), 0.042, 0.040, 8, 'emp_steel', False)
        for sy in (-1, 1): R.box((x, 1.32 + sy * 0.042, 1.95), (0.03, 0.012, 0.09), 'emp_black')
        for sz in (-1, 1): R.box((x + sz * 0.042, 1.32, 1.95), (0.012, 0.03, 0.09), 'emp_black')
        rod(R, (x, 1.415, -0.20), (x, 1.415, 0.78), 0.018, 'emp_steel', 6)
        bx(R, x - 0.03, x + 0.03, 1.19, 1.255, -0.10, 0.12, 'emp_black')                         # ejection port housing
    bx(R, -0.11, 0.11, 1.30, 1.36, 0.40, 0.50, 'emp_steel_dark')
    bx(R, -0.11, 0.11, 1.30, 1.36, 0.88, 0.96, 'emp_steel_dark')
    M.empty('emp_aa_muzzle_L', (0.17, 1.32, 2.04), 'emp_aa_barrels', 'ARROWS')
    M.empty('emp_aa_muzzle_R', (-0.17, 1.32, 2.04), 'emp_aa_barrels', 'ARROWS')
    M.empty('emp_aa_casing', (0.0, 1.19, 0.0), 'emp_aa_barrels', 'ARROWS')
    return M


# ================================================================== heavy machine-gun nest
def emp_mg():
    M = EM('emp_mg'); rng = random.Random(11)
    PY = (0.0, 0.98, 0.15); TP = (0.0, 1.12, 0.15)
    B = M.node('_base', None, (0, 0, 0))
    B.box((0, 0.03, -0.1), (3.5, 0.06, 3.0), 'emp_earth')
    for k in range(9): B.box((-0.72 + k * 0.18, 0.075, -0.55), (0.15, 0.03, 1.3), 'emp_wood')
    B.box((-0.8, 0.07, -0.55), (0.06, 0.02, 1.4), 'emp_wood_dark'); B.box((0.8, 0.07, -0.55), (0.06, 0.02, 1.4), 'emp_wood_dark')
    bagline(B, (-1.55, 1.18), (1.55, 1.18), 5, rng, y0=0.06)
    bagline(B, (-1.55, 1.18), (-1.55, -1.15), 4, rng, y0=0.06)
    bagline(B, (1.55, 1.18), (1.55, -1.15), 4, rng, y0=0.06)
    bagline(B, (-1.55, -1.15), (-0.9, -1.15), 3, rng, y0=0.06)
    # tripod (static): three legs to the pintle head
    top = (0.0, 0.93, 0.15)
    for foot in ((0.0, 0.12, 0.82), (0.58, 0.12, -0.40), (-0.58, 0.12, -0.40)):
        bar(B, top, foot, 0.06, 'emp_steel_dark')
        B.box((foot[0], 0.105, foot[2]), (0.20, 0.03, 0.20), 'emp_steel_dark')
    B.cyl((0, 0.86, 0.15), (0, 0.98, 0.15), 0.07, 0.06, 8, 'emp_steel', False)
    for a in (0, 120, 240):
        bar(B, (0, 0.45, 0.15), (0.5 * math.sin(rad(a)) * 0.9, 0.30, 0.15 + 0.5 * math.cos(rad(a)) * 0.9), 0.03, 'emp_steel')
    crate(B, (1.0, 0.06, -0.9), (0.55, 0.30, 0.40), 12)
    ammo_box(B, (1.05, 0.50, -0.9), (0.30, 0.20, 0.16), yaw=12)
    ammo_box(B, (-1.1, 0.16, 0.5), (0.34, 0.20, 0.17), yaw=-20)
    ammo_box(B, (-1.1, 0.16, 0.2), (0.34, 0.20, 0.17), yaw=15)
    B.cyl((-1.15, 0.06, -0.9), (-1.15, 0.38, -0.9), 0.10, 0.10, 8, 'emp_olive', False)       # water can
    B.box((-1.15, 0.40, -0.9), (0.10, 0.04, 0.06), 'emp_black')
    # ---- yaw (pintle head and fork)
    Y = M.node('_yaw', None, PY)
    Y.cyl((0, 0.98, 0.15), (0, 1.02, 0.15), 0.09, 0.09, 10, 'emp_steel', False)
    for sx in (-1, 1):
        slab(Y, [(-0.10, 1.02), (0.12, 1.02), (0.09, 1.20), (-0.07, 1.20)], (sx * 0.095, 0, 0.15), (0, 0, 1), (0, 1, 0), 0.035, 'emp_paint')
        Y.cyl((sx * 0.08, 1.12, 0.15), (sx * 0.15, 1.12, 0.15), 0.035, 0.035, 8, 'emp_steel_dark', False)
    bx(Y, -0.095, 0.095, 1.02, 1.05, 0.04, 0.26, 'emp_paint')
    bx(Y, -0.17, 0.17, 1.00, 1.03, -0.10, -0.04, 'emp_steel_dark')
    # ---- pitch (gun body, shield plate, ammunition box with belt, sights)
    P = M.node('_pitch', 'emp_mg_yaw', TP)
    bx(P, -0.05, 0.05, 1.04, 1.20, -0.34, 0.45, 'emp_steel_dark')                       # receiver
    bx(P, -0.04, 0.04, 1.20, 1.235, -0.28, 0.32, 'emp_steel')                           # top cover
    bx(P, -0.06, 0.06, 1.05, 1.19, -0.40, -0.34, 'emp_black')                           # back plate
    for sx in (-1, 1):
        bar(P, (sx * 0.075, 1.12, -0.38), (sx * 0.085, 1.12, -0.50), 0.025, 'emp_black')  # spade grips
        P.cyl((sx * 0.085, 1.05, -0.50), (sx * 0.085, 1.20, -0.50), 0.014, 0.014, 6, 'emp_black', False)
    bx(P, -0.015, 0.015, 1.03, 1.12, -0.12, -0.08, 'emp_black')                         # trigger bar
    bx(P, -0.03, 0.03, 1.00, 1.05, 0.10, 0.34, 'emp_steel_dark')
    ammo_box(P, (0.17, 1.03, 0.0), (0.17, 0.20, 0.26), handle=False)
    bx(P, 0.08, 0.14, 1.10, 1.16, -0.02, 0.10, 'emp_steel')                             # feed tray
    pa, pc, pb = Vector((0.17, 1.14, 0.0)), Vector((0.20, 1.28, -0.02)), Vector((0.05, 1.215, 0.0))
    for k in range(9):                                      # belt of brass links arching from the box into the feed tray
        t = k / 8; pt = (1 - t) ** 2 * pa + 2 * (1 - t) * t * pc + t * t * pb
        P.box(tuple(pt), (0.05, 0.022, 0.036), 'emp_brass' if k % 2 == 0 else 'emp_steel_dark')
    # shield: slotted plate (left/right/upper/lower pieces) carried by the gun
    for sx in (-1, 1): wing(P, sx * 0.04, sx * 0.28, 0.94, 1.30, 0.50, 0.02, 'emp_paint', fold=10, ch=0.08)
    bx(P, -0.04, 0.04, 1.20, 1.32, 0.485, 0.505, 'emp_paint')
    bx(P, -0.04, 0.04, 0.92, 1.05, 0.485, 0.505, 'emp_paint')
    bar(P, (0.0, 1.00, 0.30), (0.0, 0.96, 0.49), 0.03, 'emp_steel')
    bar(P, (0.0, 1.19, 0.30), (0.0, 1.26, 0.49), 0.03, 'emp_steel')
    # sights: leaf rear sight and blade foresight, over the shield
    bx(P, -0.012, 0.012, 1.235, 1.40, -0.20, -0.17, 'emp_black'); bx(P, -0.04, 0.04, 1.37, 1.40, -0.20, -0.17, 'emp_black')
    bx(P, -0.008, 0.008, 1.235, 1.35, 0.28, 0.30, 'emp_black')
    # ---- barrel recoil node (jacket, barrel, flash hider)
    BR = M.node('_barrel', 'emp_mg_pitch', (0.0, 1.12, 0.45))
    BR.cyl((0, 1.12, 0.45), (0, 1.12, 0.86), 0.034, 0.032, 8, 'emp_steel', False)
    for z in (0.52, 0.62, 0.72, 0.82): BR.cyl((0, 1.12, z), (0, 1.12, z + 0.025), 0.039, 0.039, 8, 'emp_steel_dark', False)
    BR.cyl((0, 1.12, 0.86), (0, 1.12, 1.28), 0.020, 0.018, 8, 'emp_steel_dark', False)
    BR.cyl((0, 1.12, 1.18), (0, 1.12, 1.34), 0.034, 0.030, 8, 'emp_black', False)
    bx(BR, -0.03, 0.03, 1.152, 1.20, 0.55, 0.75, 'emp_steel_dark')                      # carrying handle post
    BR.sweep([(0, 1.19, 0.58), (0, 1.25, 0.60), (0, 1.25, 0.72), (0, 1.19, 0.74)], 0.010, 4, 'emp_black', False, (True, True))
    M.empty('emp_mg_muzzle', (0.0, 1.12, 1.34), 'emp_mg_barrel', 'ARROWS')
    M.empty('emp_mg_casing', (-0.06, 1.10, 0.05), 'emp_mg_pitch', 'ARROWS')
    M.empty('emp_mg_seat', (0.0, 0.09, -0.60))
    return M


# ================================================================== mortar pit
def emp_mortar():
    M = EM('emp_mortar'); rng = random.Random(23)
    BALL = (0.0, 0.20, 0.0); ELEV = 65.0
    B = M.node('_base', None, (0, 0, 0))
    B.cyl((0, 0, 0), (0, 0.04, 0), 2.3, 2.3, 24, 'emp_earth', False)
    B.cyl((0, 0.04, 0), (0, 0.06, 0), 1.25, 1.25, 16, 'emp_earth', False)
    bagarc(B, (0, 0, 0), 1.55, -150, 150, 3, rng, y0=0.04, rows=1, w=0.34)
    for k in range(7): B.box((-0.9 + k * 0.3, 0.075, -0.75), (0.22, 0.03, 0.9), 'emp_wood')
    B.box((0, 0.065, -0.75), (2.0, 0.02, 0.06), 'emp_wood_dark')
    # fixed base plate with ribs and a ball socket
    B.cyl((0, 0.04, 0), (0, 0.11, 0), 0.42, 0.38, 14, 'emp_steel_dark', False)
    for a in range(0, 180, 45): B.box((0, 0.125, 0), (0.78, 0.03, 0.05), 'emp_steel', rot=(0, a, 0))
    B.cyl((0, 0.11, 0), (0, 0.14, 0), 0.20, 0.17, 10, 'emp_steel', False)
    for sx in (-1, 1): B.box((sx * 0.40, 0.09, 0.0), (0.06, 0.10, 0.10), 'emp_black')          # carrying handles
    # ammunition: a crate with standing bombs, a closed crate and a row of bombs on a pallet
    crate(B, (1.05, 0.06, -0.55), (0.70, 0.32, 0.42), 14, 'emp_crate')
    for (dx, dz) in ((-0.18, -0.09), (0.0, 0.09), (0.18, -0.09)): shell(B, (1.05 + dx, 0.34, -0.55 + dz), (0, 1, 0), 0.40, 0.04)
    crate(B, (1.15, 0.06, -1.15), (0.70, 0.32, 0.42), -8, 'emp_ammo')
    B.box((-1.0, 0.10, -0.55), (0.9, 0.05, 0.9), 'emp_wood')
    for k in range(4): shell(B, (-1.3 + k * 0.17, 0.205, -0.55), (0.0, 0.0, 1.0), 0.40, 0.04)
    for k in range(3): shell(B, (-1.22 + k * 0.17, 0.205, -0.80), (0.0, 0.0, 1.0), 0.40, 0.04)
    # ---- yaw: traverse ring turning on the base plate
    Y = M.node('_yaw', None, BALL)
    Y.cyl((0, 0.14, 0), (0, 0.17, 0), 0.30, 0.30, 14, 'emp_paint', False)
    Y.cyl((0, 0.17, 0), (0, 0.24, 0), 0.11, 0.09, 10, 'emp_steel_dark', False)
    for sx in (-1, 1): Y.box((sx * 0.27, 0.18, 0), (0.10, 0.03, 0.06), 'emp_steel_dark')
    # ---- pitch: tube plus bipod (the bipod follows the tube; its feet reach the ground at 65 degrees elevation)
    T = M.node('_pitch', 'emp_mortar_yaw', BALL)
    T.ellipsoid(BALL, (0.085, 0.085, 0.085), 'emp_steel_dark', 8, 4)
    T.cyl(BALL, (0, 0.20, 1.18), 0.052, 0.048, 10, 'emp_steel', True)
    T.cyl((0, 0.20, 0.0), (0, 0.20, 0.12), 0.075, 0.075, 10, 'emp_paint', False)
    T.cyl((0, 0.20, 1.10), (0, 0.20, 1.20), 0.068, 0.068, 10, 'emp_steel_dark', False)
    T.cyl((0, 0.20, 0.80), (0, 0.20, 0.84), 0.064, 0.064, 8, 'emp_steel_dark', False)
    collar = Vector((0, 0.20, 0.40))
    T.cyl((0, 0.20, 0.35), (0, 0.20, 0.45), 0.072, 0.072, 10, 'emp_steel_dark', False)
    feet = []
    for sx in (-1, 1):
        wf = (sx * 0.44, 0.05, 0.62)                          # wanted foot position at 65 degrees (world)
        f = unpitch(wf, BALL, ELEV); feet.append(f)
        bar(T, tuple(collar + V(sx * 0.04, 0, 0)), tuple(f), 0.045, 'emp_steel')
        pad = f
        T.box(tuple(pad), (0.18, 0.025, 0.18), 'emp_steel_dark', rot=(ELEV, 0, 0))
    # cross-brace with elevating screw and a dial sight
    mid0 = (feet[0] * 0.55 + collar * 0.45); mid1 = (feet[1] * 0.55 + collar * 0.45)
    rod(T, tuple(mid0), tuple(mid1), 0.016, 'emp_steel_dark', 6)
    rod(T, tuple(collar + V(0, -0.02, 0.0)), tuple((mid0 + mid1) / 2), 0.014, 'emp_black', 6)
    T.box((0.075, 0.275, 0.86), (0.05, 0.10, 0.06), 'emp_black')
    T.cyl((0.075, 0.33, 0.86), (0.075, 0.33, 0.96), 0.026, 0.026, 8, 'emp_steel_dark', False)
    T.box((0.075, 0.33, 0.965), (0.034, 0.034, 0.012), 'emp_glass')
    M.empty('emp_mortar_muzzle', (0.0, 0.20, 1.20), 'emp_mortar_pitch', 'ARROWS')
    return M


# ================================================================== field gun (howitzer) with shield
def emp_howitzer():
    M = EM('emp_howitzer'); rng = random.Random(31)
    YP = (0.0, 0.95, 0.0); TP = (0.0, 1.32, 0.10)
    B = M.node('_base', None, (0, 0, 0))
    B.cyl((0, 0, 0), (0, 0.025, 0), 3.9, 3.9, 28, 'emp_earth', False)
    # axle, wheels, lower carriage
    WX = 1.0
    rod(B, (-WX, 0.62, 0), (WX, 0.62, 0), 0.08, 'emp_steel_dark', 8)
    for sx in (-1, 1):
        tyre(B, (sx * WX, 0.62, 0), 0.62, 0.24)
        B.box((sx * (WX - 0.28), 0.62, 0), (0.12, 0.16, 0.26), 'emp_steel_dark')
        # mudguard
        slab(B, [(-0.72, 0.98), (-0.40, 1.31), (0.40, 1.31), (0.72, 0.98), (0.68, 0.96), (0.38, 1.27), (-0.38, 1.27), (-0.68, 0.96)], (sx * WX, 0, 0), (0, 0, 1), (0, 1, 0), 0.30, 'emp_paint')
    bx(B, -0.52, 0.52, 0.66, 0.92, -0.42, 0.42, 'emp_paint')
    B.cyl((0, 0.92, 0), (0, 0.95, 0), 0.50, 0.50, 16, 'emp_steel_dark', False)
    # split trails with spades, cross-member, trail jack
    for sx in (-1, 1):
        bar(B, (sx * 0.34, 0.80, -0.30), (sx * 1.12, 0.17, -3.35), 0.16, 'emp_paint')
        bar(B, (sx * 0.34, 0.72, 0.05), (sx * 0.34, 0.80, -0.30), 0.14, 'emp_paint')
        slab(B, [(-0.0, 0.0), (0.38, 0.0), (0.38, 0.40), (0.0, 0.40)], (sx * 1.12 - 0.19, 0, -3.42), (1, 0, 0), (0, 1, 0), 0.05, 'emp_steel_dark')
        B.box((sx * 1.12, 0.12, -3.42), (0.14, 0.24, 0.16), 'emp_steel_dark')
        B.box((sx * 1.12, 0.18, -3.18), (0.20, 0.05, 0.40), 'emp_steel_dark')
        bar(B, (sx * 1.12, 0.40, -3.35), (sx * 1.12, 0.30, -3.55), 0.04, 'emp_black')           # handle
    bar(B, (-0.72, 0.52, -1.52), (0.72, 0.52, -1.52), 0.10, 'emp_paint')
    bar(B, (-0.55, 0.62, -0.95), (0.55, 0.62, -0.95), 0.08, 'emp_steel')
    B.box((0, 0.46, -2.40), (0.10, 0.50, 0.10), 'emp_steel_dark'); B.box((0, 0.20, -2.40), (0.26, 0.04, 0.30), 'emp_steel_dark')
    # sandbag aprons and ammunition at the trails
    crate(B, (-2.0, 0.025, -1.4), (0.8, 0.36, 0.5), 8)
    crate(B, (-2.1, 0.025, -2.2), (0.8, 0.36, 0.5), -6, 'emp_ammo')
    for k in range(3): shell(B, (-1.6 + k * 0.18, 0.12, -2.8), (0.0, 0.0, 1.0), 0.5, 0.05)
    # ---- yaw: top carriage with cheeks, traverse hand wheel, gunner's seat
    Y = M.node('_yaw', None, YP)
    Y.cyl((0, 0.95, 0), (0, 1.04, 0), 0.46, 0.44, 18, 'emp_steel_dark', False)
    for sx in (-1, 1):
        slab(Y, [(-0.58, 1.02), (0.50, 1.02), (0.42, 1.60), (-0.22, 1.64)], (sx * 0.38, 0, 0.05), (0, 0, 1), (0, 1, 0), 0.07, 'emp_paint')
        Y.cyl((sx * 0.33, TP[1], TP[2]), (sx * 0.52, TP[1], TP[2]), 0.12, 0.12, 12, 'emp_steel_dark', False)
    bx(Y, -0.42, 0.42, 1.02, 1.14, -0.62, -0.50, 'emp_paint')
    bx(Y, -0.42, 0.42, 1.52, 1.60, -0.18, -0.06, 'emp_paint')
    handwheel(Y, (0.52, 1.28, -0.34), 0.15, 1)
    handwheel(Y, (-0.52, 1.10, -0.40), 0.17, -1)
    bar(Y, (0.40, 1.12, -0.46), (0.60, 1.00, -0.76), 0.05, 'emp_steel')                 # seat arm
    Y.cyl((0.62, 0.97, -0.78), (0.62, 1.01, -0.78), 0.16, 0.15, 10, 'emp_black', False)
    bar(Y, (0.62, 0.97, -0.78), (0.62, 0.55, -0.70), 0.03, 'emp_steel')
    bx(Y, 0.50, 0.74, 0.50, 0.53, -0.62, -0.40, 'emp_steel_dark')                       # foot rest
    M.empty('emp_howitzer_crew_gunner', (0.62, 1.01, -0.78), 'emp_howitzer_yaw', 'ARROWS')
    # ---- pitch: cradle, recoil cylinders, elevating arc, shield plates, sights
    P = M.node('_pitch', 'emp_howitzer_yaw', TP)
    bx(P, -0.20, 0.20, 1.08, 1.20, -0.55, 1.35, 'emp_paint')
    for sx in (-1, 1):
        bx(P, sx * 0.20 - 0.025 * (1 if sx > 0 else -1) * 0, sx * 0.20 + sx * 0.05, 1.08, 1.46, -0.45, 1.25, 'emp_paint')
        rod(P, (sx * 0.31, 1.24, -0.20), (sx * 0.31, 1.24, 1.18), 0.065, 'emp_steel', 8)
        rod(P, (sx * 0.31, 1.24, 1.18), (sx * 0.31, 1.24, 1.55), 0.030, 'emp_galv', 6)
    rod(P, (-0.54, 1.32, 0.10), (0.54, 1.32, 0.10), 0.06, 'emp_steel_dark', 8)
    loop(P, (0.0, 1.32, 0.10), 0.62, 0.028, 'x', 'emp_steel_dark', n=8, seg=4, a0=195, a1=255)
    for sx in (-1, 1):
        bar(P, (sx * 0.12, 1.12, -0.5), (sx * 0.12, 0.72, -0.1), 0.05, 'emp_paint')            # arc brackets
    # shield: big flat plates with a cut-out for the barrel and a sight window
    SZ = 0.62
    for sx in (-1, 1):
        wing(P, sx * 0.24, sx * 0.92, 0.84, 1.52, SZ, 0.03, 'emp_paint', fold=0, ch=0.0)
        wing(P, sx * 0.24, sx * 0.92, 1.76, 2.04, SZ, 0.03, 'emp_paint', fold=0, ch=0.16)
        wing(P, sx * 0.24, sx * 0.32, 1.52, 1.76, SZ, 0.03, 'emp_paint', fold=0)
        wing(P, sx * 0.62, sx * 0.92, 1.52, 1.76, SZ, 0.03, 'emp_paint', fold=0)
        for yy in (1.0, 1.9): bx(P, sx * 0.26, sx * 0.90, yy, yy + 0.05, SZ - 0.04, SZ - 0.015, 'emp_steel_dark')
        bar(P, (sx * 0.22, 1.20, 1.00), (sx * 0.40, 0.98, SZ), 0.05, 'emp_steel')
        bar(P, (sx * 0.22, 1.44, 1.00), (sx * 0.40, 1.80, SZ), 0.05, 'emp_steel')
        for k in range(4): P.cyl((sx * (0.34 + 0.17 * k), 1.96, SZ + 0.015), (sx * (0.34 + 0.17 * k), 1.96, SZ + 0.035), 0.016, 0.016, 5, 'emp_steel_dark', False)   # bolts
    bx(P, -0.24, 0.24, 1.60, 2.04, SZ - 0.015, SZ + 0.015, 'emp_paint')
    bx(P, -0.24, 0.24, 0.84, 1.06, SZ - 0.015, SZ + 0.015, 'emp_paint')
    # sights: telescope behind the left window, panoramic sight bracket
    bar(P, (0.20, 1.40, 0.15), (0.40, 1.66, 0.15), 0.04, 'emp_steel')
    rod(P, (0.42, 1.68, -0.28), (0.42, 1.68, 0.56), 0.032, 'emp_black', 8)
    P.cyl((0.42, 1.68, 0.56), (0.42, 1.68, 0.60), 0.05, 0.05, 8, 'emp_steel_dark', False)
    P.cyl((0.42, 1.68, -0.28), (0.42, 1.68, -0.36), 0.045, 0.040, 8, 'emp_black', False)
    P.cyl((0.42, 1.70, -0.10), (0.42, 1.82, -0.10), 0.03, 0.03, 8, 'emp_steel_dark', False)     # elevation drum
    P.box((-0.40, 1.62, 0.10), (0.06, 0.20, 0.06), 'emp_steel_dark')
    P.cyl((-0.40, 1.72, 0.10), (-0.40, 1.80, 0.10), 0.035, 0.035, 8, 'emp_black', False)         # dial sight
    # ---- barrel and breech on the recoil slide
    BR = M.node('_barrel', 'emp_howitzer_pitch', (0.0, 1.32, 0.10))
    BR.box((0, 1.32, -0.20), (0.34, 0.34, 0.52), 'emp_steel_dark', bevel=0.02)
    BR.box((0.20, 1.34, -0.30), (0.08, 0.26, 0.20), 'emp_steel')
    BR.box((0.0, 1.32, -0.50), (0.10, 0.10, 0.10), 'emp_black')
    bx(BR, 0.17, 0.30, 1.28, 1.40, -0.38, -0.22, 'emp_black')                                      # breech lever
    BR.sweep([(0, 1.32, 0.0), (0, 1.32, 0.8), (0, 1.32, 1.8), (0, 1.32, 3.0)], [0.150, 0.130, 0.098, 0.075], 12, 'emp_steel', True, (True, True))
    BR.cyl((0, 1.32, 1.55), (0, 1.32, 1.95), 0.118, 0.118, 12, 'emp_steel_dark', False)          # bore evacuator
    BR.cyl((0, 1.32, 2.95), (0, 1.32, 3.25), 0.105, 0.105, 12, 'emp_steel_dark', False)          # muzzle brake
    for k in range(3):
        BR.cyl((0, 1.32, 3.00 + k * 0.08), (0, 1.32, 3.03 + k * 0.08), 0.112, 0.112, 12, 'emp_black', False)
    for sy in (-1, 1): BR.box((0, 1.32 + sy * 0.105, 3.10), (0.07, 0.015, 0.16), 'emp_black')
    BR.cyl((0, 1.32, 0.05), (0, 1.32, 0.12), 0.18, 0.18, 12, 'emp_steel_dark', False)
    M.empty('emp_howitzer_muzzle', (0.0, 1.32, 3.25), 'emp_howitzer_barrel', 'ARROWS')
    M.empty('emp_howitzer_crew_loader', (0.0, 0.0, -1.20))
    M.empty('emp_howitzer_crew_ammo', (-0.30, 0.0, -2.30))
    M.empty('emp_howitzer_crew_commander', (1.75, 0.0, -1.80))
    return M


# ================================================================== single quick-firing 37 mm flak gun on a tripod
def emp_flak():
    M = EM('emp_flak'); rng = random.Random(41)
    YP = (0.0, 0.88, 0.0); TP = (0.0, 1.24, 0.0)
    B = M.node('_base', None, (0, 0, 0))
    B.cyl((0, 0, 0), (0, 0.08, 0), 2.1, 2.1, 24, 'emp_concrete', False)
    B.cyl((0, 0, 0), (0, 0.025, 0), 2.7, 2.7, 24, 'emp_earth', False)
    top = (0.0, 0.84, 0.0)
    for a in (0, 120, 240):
        sx, cz = math.sin(rad(a)), math.cos(rad(a)); f = (1.45 * sx, 0.10, 1.45 * cz)
        bar(B, top, f, 0.10, 'emp_steel')
        B.cyl((f[0], 0.08, f[2]), (f[0], 0.14, f[2]), 0.12, 0.10, 8, 'emp_steel_dark', False)
        B.box((f[0], 0.095, f[2]), (0.26, 0.03, 0.26), 'emp_steel_dark', rot=(0, a, 0))
    for a in (0, 120, 240):                       # ring tie between the legs
        a2 = a + 120
        p1 = (0.7 * math.sin(rad(a)), 0.45, 0.7 * math.cos(rad(a))); p2 = (0.7 * math.sin(rad(a2)), 0.45, 0.7 * math.cos(rad(a2)))
        bar(B, p1, p2, 0.05, 'emp_steel_dark')
    B.cyl((0, 0.78, 0), (0, 0.88, 0), 0.20, 0.17, 12, 'emp_steel_dark', False)
    bagarc(B, (0, 0, 0), 1.85, -115, 115, 3, rng, y0=0.08)
    crate(B, (-0.9, 0.08, -1.45), (0.7, 0.34, 0.45), 14)
    ammo_box(B, (-0.9, 0.55, -1.45), (0.45, 0.2, 0.28), yaw=14)
    crate(B, (0.95, 0.08, -1.40), (0.7, 0.34, 0.45), -10, 'emp_ammo')
    for k in range(5): B.cyl((0.4 + k * 0.07, 0.12, -1.0), (0.4 + k * 0.07, 0.12, -0.65), 0.025, 0.025, 6, 'emp_brass', False)
    # ---- yaw: turntable, yoke, seat bracket, hand wheels
    Y = M.node('_yaw', None, YP)
    Y.cyl((0, 0.88, 0), (0, 0.96, 0), 0.34, 0.32, 14, 'emp_steel_dark', False)
    for sx in (-1, 1):
        slab(Y, [(-0.26, 0.94), (0.30, 0.94), (0.20, 1.38), (-0.14, 1.38)], (sx * 0.28, 0, 0), (0, 0, 1), (0, 1, 0), 0.05, 'emp_paint')
        Y.cyl((sx * 0.25, TP[1], 0), (sx * 0.40, TP[1], 0), 0.08, 0.08, 10, 'emp_steel_dark', False)
    bx(Y, -0.28, 0.28, 0.98, 1.06, -0.30, -0.22, 'emp_paint')
    handwheel(Y, (-0.44, 1.02, -0.14), 0.11, -1)
    bar(Y, (0.28, 1.02, -0.20), (0.62, 0.98, -0.56), 0.045, 'emp_steel')
    Y.cyl((0.64, 0.96, -0.58), (0.64, 1.00, -0.58), 0.15, 0.14, 10, 'emp_black', False)
    bar(Y, (0.64, 0.96, -0.58), (0.64, 0.40, -0.40), 0.03, 'emp_steel')
    M.empty('emp_flak_seat', (0.64, 1.00, -0.58), 'emp_flak_yaw', 'ARROWS')
    # ---- pitch: cradle sleeve, clip guide, shield plates, sights
    P = M.node('_pitch', 'emp_flak_yaw', TP)
    rod(P, (0, 1.24, -0.26), (0, 1.24, 0.82), 0.085, 'emp_paint', 8)
    rod(P, (-0.40, 1.24, 0), (0.40, 1.24, 0), 0.04, 'emp_steel_dark', 8)
    bx(P, -0.20, 0.20, 1.16, 1.32, -0.12, 0.12, 'emp_steel_dark')
    bx(P, -0.09, 0.09, 1.20, 1.44, -0.26, -0.10, 'emp_paint')
    bx(P, -0.07, 0.07, 1.34, 1.46, -0.14, 0.24, 'emp_steel_dark')
    P.box((0, 1.52, 0.04), (0.10, 0.06, 0.26), 'emp_ammo')
    for k in range(5): P.cyl((-0.04 + k * 0.02, 1.55, -0.07 + k * 0.0), (-0.04 + k * 0.02, 1.62, -0.07), 0.009, 0.009, 5, 'emp_brass', False)
    # shield plates (two wings fold back, centre plates above/below the barrel)
    for sx in (-1, 1):
        wing(P, sx * 0.12, sx * 0.56, 0.86, 1.62, 0.44, 0.022, 'emp_paint', fold=18, ch=0.10)
        bar(P, (sx * 0.08, 1.20, 0.76), (sx * 0.22, 1.02, 0.44), 0.035, 'emp_steel')
        bar(P, (sx * 0.08, 1.28, 0.76), (sx * 0.22, 1.50, 0.44), 0.035, 'emp_steel')
    bx(P, -0.12, 0.12, 1.34, 1.62, 0.43, 0.457, 'emp_paint')
    bx(P, -0.12, 0.12, 0.86, 1.14, 0.43, 0.457, 'emp_paint')
    # sights: ring on the left, bead on a post
    bar(P, (0.14, 1.36, -0.02), (0.30, 1.56, -0.02), 0.03, 'emp_steel_dark')
    loop(P, (0.30, 1.64, -0.02), 0.07, 0.007, 'z', 'emp_black', n=12, seg=4)
    bar(P, (0.14, 1.36, 0.60), (0.30, 1.56, 0.60), 0.025, 'emp_steel_dark')
    P.cyl((0.30, 1.56, 0.60), (0.30, 1.61, 0.60), 0.012, 0.010, 6, 'emp_yellow', False)
    # ---- recoil slide: receiver, jacket, barrel, muzzle brake, spring tube
    R = M.node('_barrel', 'emp_flak_pitch', (0.0, 1.24, 0.0))
    bx(R, -0.065, 0.065, 1.16, 1.31, -0.38, 0.26, 'emp_steel_dark')
    rod(R, (0, 1.24, -0.38), (0, 1.24, -0.50), 0.04, 'emp_steel', 8)
    R.cyl((0, 1.24, 0.26), (0, 1.24, 0.96), 0.050, 0.046, 8, 'emp_steel', False)
    for z in (0.36, 0.52, 0.68, 0.84): R.cyl((0, 1.24, z), (0, 1.24, z + 0.03), 0.057, 0.057, 8, 'emp_steel_dark', False)
    R.cyl((0, 1.24, 0.96), (0, 1.24, 1.70), 0.030, 0.024, 8, 'emp_steel_dark', False)
    R.cyl((0, 1.24, 1.64), (0, 1.24, 1.82), 0.046, 0.044, 8, 'emp_steel', False)
    for sy in (-1, 1): R.box((0, 1.24 + sy * 0.046, 1.74), (0.03, 0.012, 0.09), 'emp_black')
    rod(R, (0.075, 1.30, -0.20), (0.075, 1.30, 0.70), 0.018, 'emp_steel', 6)
    M.empty('emp_flak_muzzle', (0.0, 1.24, 1.82), 'emp_flak_barrel', 'ARROWS')
    M.empty('emp_flak_casing', (0.0, 1.14, 0.0), 'emp_flak_barrel', 'ARROWS')
    return M
