"""jeep, technical, quad_atv."""
from v_lib import *


def tow_hook(P, x, y, z, d=1):
    P.sweep([(x, y, z), (x, y, z + 0.1 * d), (x, y - 0.06, z + 0.14 * d)], 0.018, 4, 'veh_steel_dark', False)


def jeep():
    M = VM('jeep'); B = M.body(); n = 'jeep'
    R = 0.36; TW = 0.20; TX = 0.75; ZF = 1.05; ZR = -1.05; WY = R
    # ---- running gear
    for tag, z, side in (('FL', ZF, 1), ('FR', ZF, -1)): steer_wheel(M, tag, (side * TX, WY, z), R, TW, side, lugs=18, seg=20)
    for tag, z, side in (('RL', ZR, 1), ('RR', ZR, -1)): add_wheel(M, '%s_wheel_%s' % (n, tag), (side * TX, WY, z), R, TW, side, lugs=18, seg=20)
    for z in (ZF, ZR):
        B.cyl((-0.66, WY, z), (0.66, WY, z), 0.04, 0.04, 8, 'veh_steel_dark', True)
        B.ellipsoid((0, WY - 0.04, z + (0.03 if z > 0 else -0.03)), (0.17, 0.12, 0.12), 'veh_steel_dark', seg=8, nl=4)
        for sx in (-1, 1):
            bx(B, sx * 0.40 - 0.03, sx * 0.40 + 0.03, WY + 0.05, WY + 0.09, z - 0.38, z + 0.38, 'veh_steel_dark')   # leaf spring
            tube(B, (sx * 0.58, WY - 0.05, z), (sx * 0.58, WY + 0.30, z), 0.03, 'veh_dark', 6)                          # shock
    bx2(B, 0.30, 0.40, 0.32, 0.42, -1.55, 1.70, 'veh_steel_dark')                                                       # chassis rails
    bx(B, -0.40, 0.40, 0.34, 0.40, -0.3, 0.3, 'veh_dark')                                                               # transfer case
    B.cyl((0, 0.40, -0.9), (0, 0.40, 0.3), 0.025, 0.025, 6, 'veh_dark', False)                                          # prop shaft
    B.cyl((0.50, 0.30, -1.50), (0.50, 0.30, -0.85), 0.045, 0.04, 8, 'veh_rust', True)                                  # exhaust/muffler
    B.cyl((0.50, 0.30, -1.50), (0.50, 0.30, -1.62), 0.03, 0.03, 8, 'veh_dark', False)
    # ---- tub
    bx(B, -0.62, 0.62, 0.40, 0.46, -1.58, 0.95, 'veh_paint')                                                            # floor
    prof = [(-1.62, 0.40), (0.98, 0.40), (0.98, 0.62), (0.95, 0.80), (0.20, 0.80), (0.0, 0.82), (-0.20, 0.92), (-1.62, 0.92)]
    for sx in (1, -1): extrude_zy(B, prof, sx * 0.62 if sx > 0 else -0.67, 0.67 if sx > 0 else -0.62, 'veh_paint')
    bx(B, -0.62, 0.62, 0.40, 0.92, -1.66, -1.58, 'veh_paint')                                                           # rear panel
    bx(B, -0.45, 0.45, 0.88, 0.94, -1.68, -1.58, 'veh_dark')                                                            # rear top rail
    for sx in (-1, 1): bx(B, sx * 0.68 - 0.012, sx * 0.68 + 0.012, 0.74, 0.77, -1.6, -0.25, 'veh_dark')               # rubbing strake
    # hood, cowl, grille
    blk(B, -0.60, 0.60, 0.60, 0.88, 0.86, 1.62, 'veh_paint', (0.05, 0.05, 0.0, 0.14))
    bx(B, -0.58, 0.58, 0.60, 0.90, 0.80, 0.98, 'veh_paint')                                                             # cowl
    bx(B, -0.56, 0.56, 0.42, 0.74, 1.62, 1.70, 'veh_paint')                                                             # grille panel
    for i in range(7): bx(B, -0.40 + i * 0.133 - 0.02, -0.40 + i * 0.133 + 0.02, 0.50, 0.70, 1.695, 1.715, 'veh_dark')
    bx(B, -0.62, 0.62, 0.60, 0.64, 1.60, 1.72, 'veh_paint')
    for sx in (-1, 1):
        headlight(B, (sx * 0.46, 0.80, 1.70), 0.085, 0.06)
        B.box((sx * 0.30, 0.60, 1.755), (0.14, 0.04, 0.03), 'veh_light_amber')                                           # indicator
        taillight(B, (sx * 0.52, 0.80, -1.675)); B.box((sx * 0.52, 0.70, -1.675), (0.1, 0.05, 0.03), 'veh_light_amber')
    bx(B, -0.78, 0.78, 0.34, 0.44, 1.72, 1.82, 'veh_steel_dark', 0.01)                                                  # front bumper
    bx(B, -0.78, 0.78, 0.34, 0.44, -1.80, -1.68, 'veh_steel_dark', 0.01)                                                # rear bumper
    for sx in (-1, 1): tow_hook(B, sx * 0.30, 0.38, 1.82); tow_hook(B, sx * 0.30, 0.38, -1.80, -1)
    B.cyl((0, 0.50, -1.80), (0, 0.50, -2.0), 0.03, 0.03, 6, 'veh_steel_dark', False)                                    # pintle hook
    B.cyl((0, 0.50, -2.0), (0, 0.50, -2.05), 0.06, 0.06, 8, 'veh_steel_dark', False)
    # fenders
    for z, ln in ((ZF, 0.62), (ZR, 0.55)):
        for sx in (-1, 1):
            xi, xo = (0.60, 0.97) if sx > 0 else (-0.97, -0.60)
            bx(B, xi, xo, 0.76, 0.80, z - ln, z + ln, 'veh_paint', 0.01)
            bx(B, (0.955 if sx > 0 else -0.97), (0.97 if sx > 0 else -0.955), 0.66, 0.80, z - ln, z + ln, 'veh_paint')   # outer lip
            bx(B, xi, xo, 0.66, 0.76, z + ln - 0.03, z + ln, 'veh_paint')
    # windscreen (upright frame, glass), dash
    for sx in (-1, 1):
        tube(B, (sx * 0.60, 0.80, 0.92), (sx * 0.60, 1.38, 0.82), 0.04, 'veh_dark')
        tube(B, (sx * 0.62, 0.80, 0.94), (sx * 0.62, 0.62, 0.86), 0.03, 'veh_dark')
    tube(B, (-0.60, 1.38, 0.82), (0.60, 1.38, 0.82), 0.04, 'veh_dark'); tube(B, (-0.60, 0.84, 0.90), (0.60, 0.84, 0.90), 0.04, 'veh_dark')
    tube(B, (0, 0.84, 0.90), (0, 1.38, 0.82), 0.03, 'veh_dark')
    for sx in (-1, 1):
        B.patch([[(sx * 0.02, 0.86, 0.896), (sx * 0.58, 0.86, 0.896)], [(sx * 0.02, 1.36, 0.826), (sx * 0.58, 1.36, 0.826)]], 'veh_glass', (0, 0, 1), False)
        tube(B, (sx * 0.30, 1.30, 0.835), (sx * 0.12, 1.12, 0.855), 0.012, 'veh_dark')                                   # wiper
    bx(B, -0.60, 0.60, 0.74, 0.90, 0.78, 0.94, 'veh_dark', 0.02)                                                        # dash
    for sx in (-1, 1): B.cyl((sx * 0.64, 1.0, 0.99), (sx * 0.64, 1.1, 0.95), 0.012, 0.012, 4, 'veh_dark', False)       # mirror stalk
    for sx in (-1, 1): B.box((sx * 0.70, 1.12, 0.94), (0.03, 0.14, 0.10), 'veh_dark')                                   # mirror head
    steering_wheel(B, (0.33, 1.00, 0.70), 0.19, -45, col_to=(0.33, 0.82, 0.88))
    for k in range(3): B.box((-0.22 + k * 0.22, 0.88, 0.92), (0.1, 0.08, 0.03), 'veh_metal')                              # gauges
    # seats (driver left = +x)
    for (x, z) in ((0.33, 0.45), (-0.33, 0.45)): seat(B, x, 0.58, z, 0.42, 0.44, back_h=0.5)
    for (x, z) in ((0.31, -0.74), (-0.31, -0.74)): seat(B, x, 0.58, z, 0.52, 0.44, back_h=0.42)
    bx(B, -0.62, 0.62, 0.42, 0.50, -1.15, -0.5, 'veh_steel_dark')                                                       # rear seat base
    bx(B, -0.12, 0.12, 0.46, 0.58, 0.10, 0.80, 'veh_paint')                                                             # tunnel
    # jerry can and spare wheel, shovel, jack
    B.box((0.45, 1.02, -1.35), (0.34, 0.46, 0.17), 'veh_can', bevel=0.015)
    B.box((0.45, 1.27, -1.35), (0.10, 0.04, 0.06), 'veh_dark')
    bx(B, 0.28, 0.62, 0.92, 1.02, -1.35, -1.28, 'veh_dark')
    spare_wheel(B, (-0.12, 0.74, -1.80), 0.34, 0.20)
    bx(B, -0.30, 0.06, 0.40, 0.46, -1.86, -1.68, 'veh_dark')
    tube(B, (-0.66, 0.96, -1.3), (-0.66, 0.96, -0.5), 0.02, 'veh_wood', 6)                                               # shovel handle
    B.box((-0.66, 0.96, -0.40), (0.04, 0.18, 0.22), 'veh_metal')
    # gun pedestal (floor to pivot) with bracing; the gun itself is the node `jeep_gun`
    GP = (0, 1.52, 0.20)
    B.cyl((0, 0.46, 0.20), (0, 1.40, 0.20), 0.035, 0.03, 8, 'veh_steel_dark', True)
    B.cyl((0, 0.46, 0.20), (0, 0.50, 0.20), 0.12, 0.12, 10, 'veh_steel_dark', False)
    for a in (140, -140, 0):
        r = rad(a); tube(B, (0.0, 1.05, 0.20), (0.16 * math.sin(r + PI / 2) * 0 + 0.20 * math.sin(r), 0.48, 0.20 + 0.20 * math.cos(r)), 0.012, 'veh_steel_dark', 4)
    B.cyl((0, 1.40, 0.20), (0, 1.52, 0.20), 0.045, 0.04, 8, 'veh_dark', False)
    G = M.node('_gun', None, GP, full=False)
    G.pivot = Vector(GP)
    gz = machinegun(Loc(G, GP), barrel=1.0)
    M.empty('jeep_muzzle', (GP[0], GP[1], GP[2] + gz), 'jeep_gun', 'ARROWS')
    # markers
    M.empty('jeep_seat_driver', (0.33, 0.66, 0.45)); M.empty('jeep_seat_p0', (-0.33, 0.66, 0.45))
    M.empty('jeep_seat_p1', (0.31, 0.66, -0.74)); M.empty('jeep_seat_p2', (-0.31, 0.66, -0.74))
    M.empty('jeep_seat_gunner', (0.0, 0.62, -0.25))
    M.empty('jeep_exit_L', (1.35, 0.0, 0.1)); M.empty('jeep_exit_R', (-1.35, 0.0, 0.1))
    return M


def technical():
    M = VM('technical'); B = M.body(); n = 'technical'
    R = 0.40; TW = 0.26; TX = 0.84; ZF = 1.62; ZR = -1.38
    for tag, z, side in (('FL', ZF, 1), ('FR', ZF, -1)): steer_wheel(M, tag, (side * TX, R, z), R, TW, side, lugs=18, seg=22)
    for tag, z, side in (('RL', ZR, 1), ('RR', ZR, -1)): add_wheel(M, '%s_wheel_%s' % (n, tag), (side * TX, R, z), R, TW, side, lugs=18, seg=22)
    for z in (ZF, ZR):
        B.cyl((-0.72, R, z), (0.72, R, z), 0.05, 0.05, 8, 'veh_steel_dark', True)
        B.ellipsoid((0, R - 0.04, z), (0.2, 0.14, 0.14), 'veh_steel_dark', seg=8, nl=4)
    for sx in (-1, 1):
        for z in (ZR,): bx(B, sx * 0.55 - 0.04, sx * 0.55 + 0.04, R + 0.06, R + 0.12, z - 0.55, z + 0.55, 'veh_steel_dark')
    bx2(B, 0.36, 0.48, 0.38, 0.50, -2.45, 2.50, 'veh_steel_dark')
    B.cyl((0, 0.42, -1.3), (0, 0.42, 1.5), 0.03, 0.03, 6, 'veh_dark', False)
    B.cyl((0.60, 0.34, -2.10), (0.60, 0.34, -1.0), 0.06, 0.05, 8, 'veh_rust', True)
    B.cyl((-0.55, 0.30, 0.2), (-0.55, 0.30, 1.0), 0.09, 0.09, 8, 'veh_steel_dark', True)                                 # fuel tank hint
    # ---- body: side profile (z, y). cab roof 1.72, bed side 1.30
    side = [(-2.55, 0.50), (2.40, 0.50), (2.52, 0.62), (2.52, 0.95), (2.38, 1.08), (1.30, 1.10), (1.05, 1.74), (-0.55, 1.74), (-0.62, 1.30), (-2.55, 1.30)]
    for sx in (1, -1): extrude_zy(B, side, (0.73 if sx > 0 else -0.80), (0.80 if sx > 0 else -0.73), 'veh_paint')
    bx(B, -0.74, 0.74, 0.50, 0.58, -2.55, 2.45, 'veh_paint')                                                            # floor pan / sills
    bx(B, -0.78, 0.78, 0.50, 0.96, 1.30, 2.50, 'veh_paint')                                                             # engine bay block (under hood)
    blk(B, -0.80, 0.80, 0.96, 1.12, 1.25, 2.48, 'veh_paint', (0.04, 0.04, 0.0, 0.20))                                    # hood
    bx(B, -0.80, 0.80, 0.62, 1.04, 2.48, 2.58, 'veh_paint', 0.02)                                                       # front grille panel
    for i in range(6): bx(B, -0.55 + i * 0.22 - 0.04, -0.55 + i * 0.22 + 0.04, 0.74, 0.96, 2.575, 2.595, 'veh_dark')
    bx(B, -0.84, 0.84, 0.40, 0.56, 2.52, 2.68, 'veh_steel_dark', 0.02)                                                  # bumper
    bx(B, -0.84, 0.84, 0.40, 0.54, -2.62, -2.52, 'veh_steel_dark', 0.02)
    bx(B, -0.84, 0.84, 1.12, 1.16, 2.50, 2.58, 'veh_steel_dark')
    for sx in (-1, 1):
        headlight(B, (sx * 0.62, 0.92, 2.58), 0.10, 0.06); taillight(B, (sx * 0.64, 1.18, -2.58), 0.14, 0.2)
        B.box((sx * 0.64, 0.84, 2.60), (0.14, 0.05, 0.03), 'veh_light_amber')
    # fender flares + wheel arches (dark liners)
    for z in (ZF, ZR):
        for sx in (-1, 1):
            xi, xo = (0.74, 0.98) if sx > 0 else (-0.98, -0.74)
            bx(B, xi, xo, 0.84 if z == ZF else 0.90, (0.88 if z == ZF else 0.94), z - 0.55, z + 0.55, 'veh_paint', 0.02)
            bx(B, (0.96 if sx > 0 else -0.98), (0.98 if sx > 0 else -0.96), 0.70, 0.88 if z == ZF else 0.94, z - 0.55, z + 0.55, 'veh_paint')
    # windows: windscreen, side glass, rear glass
    B.patch([[(-0.70, 1.18, 1.27), (0.70, 1.18, 1.27)], [(-0.70, 1.68, 1.07), (0.70, 1.68, 1.07)]], 'veh_glass', (0, 0, 1), False)
    for sx in (-1, 1):
        xs = sx * 0.805
        B.patch([[(xs, 1.20, 0.90), (xs, 1.20, 0.10), (xs, 1.20, -0.50)], [(xs, 1.68, 0.90), (xs, 1.68, 0.10), (xs, 1.68, -0.50)]], 'veh_glass', (sx, 0, 0), False)
        bx(B, sx * 0.795 - 0.012, sx * 0.795 + 0.012, 1.18, 1.70, 0.10 - 0.02, 0.10 + 0.02, 'veh_dark')               # B pillar
        for z in (0.55, -0.30): bx(B, sx * 0.805 - 0.015, sx * 0.805 + 0.015, 1.04, 1.10, z - 0.10, z + 0.10, 'veh_dark')  # handles
        B.box((sx * 0.92, 1.28, 1.12), (0.05, 0.16, 0.10), 'veh_dark')                                                  # mirror
    B.patch([[(-0.66, 1.30, -0.558), (0.66, 1.30, -0.558)], [(-0.66, 1.66, -0.558), (0.66, 1.66, -0.558)]], 'veh_glass', (0, 0, -1), False)
    bx(B, -0.80, 0.80, 1.72, 1.78, -0.58, 1.08, 'veh_paint', 0.02)
    # bed: floor, inner walls, tailgate, wheel boxes
    bx(B, -0.72, 0.72, 0.92, 0.98, -2.50, -0.62, 'veh_dark')
    for sx in (-1, 1):
        bx(B, sx * 0.68 - 0.03, sx * 0.68 + 0.03, 0.98, 1.30, -2.50, -0.62, 'veh_paint')
        bx(B, sx * 0.55 - 0.15, sx * 0.55 + 0.15, 0.98, 1.16, ZR - 0.45, ZR + 0.45, 'veh_paint', 0.03)                  # wheel box
        B.cyl((sx * 0.80, 1.30, -2.5), (sx * 0.80, 1.30, -0.62), 0.03, 0.03, 6, 'veh_steel_dark', False)               # rail
    bx(B, -0.78, 0.78, 0.60, 1.30, -2.62, -2.52, 'veh_paint')                                                           # tailgate
    for sx in (-1, 1): bx(B, sx * 0.68 - 0.03, sx * 0.68 + 0.03, 0.98, 1.30, -2.56, -2.50, 'veh_steel_dark')
    bx(B, -0.15, 0.15, 1.12, 1.16, -2.64, -2.60, 'veh_steel_dark')                                                      # latch
    # cab interior seats (front + rear bench)
    for x in (0.34, -0.34): seat(B, x, 0.86, 0.45, 0.46, 0.46, back_h=0.62)
    seat(B, 0.0, 0.86, -0.18, 1.25, 0.44, back_h=0.5)
    steering_wheel(B, (0.34, 1.34, 0.90), 0.20, -40, col_to=(0.34, 1.12, 1.15))
    bx(B, -0.74, 0.74, 1.10, 1.26, 1.05, 1.32, 'veh_dark', 0.02)                                                        # dash
    # ---- ring mount in the bed
    RZ = -1.55; RY = 1.62
    for k in range(4):
        a = rad(45 + 90 * k); tube(B, (0.55 * math.sin(a), 0.98, RZ + 0.55 * math.cos(a)), (0.55 * math.sin(a), RY, RZ + 0.55 * math.cos(a)), 0.02, 'veh_steel_dark', 6)
    pts = [(0.62 * math.sin(2 * PI * k / 20), RY, RZ + 0.62 * math.cos(2 * PI * k / 20)) for k in range(21)]
    B.sweep(pts, 0.022, 6, 'veh_steel_dark', True, (False, False))
    B.cyl((0, 0.98, RZ), (0, 1.88, RZ), 0.045, 0.04, 8, 'veh_steel_dark', True)                                         # pedestal
    B.cyl((0, 0.98, RZ), (0, 1.02, RZ), 0.20, 0.20, 10, 'veh_steel_dark', False)
    for a in (0, 120, 240): tube(B, (0, 1.20, RZ), (0.40 * math.sin(rad(a)), 1.0, RZ + 0.40 * math.cos(rad(a))), 0.014, 'veh_steel_dark', 4)
    B.cyl((0, 1.88, RZ), (0, 1.98, RZ), 0.07, 0.06, 8, 'veh_dark', False)
    # ammo crates in bed + spare tyre
    for (x, z) in ((0.45, -2.2), (-0.45, -2.2)): B.box((x, 1.08, z), (0.4, 0.2, 0.3), 'veh_can', bevel=0.01)
    spare_wheel(B, (0.0, 1.34, -0.76), 0.36, 0.22)
    # ---- gun node
    GP = (0, 1.98, RZ)
    G = M.node('_gun', None, GP)
    Lg = Loc(G, GP)
    # DShK-style heavy MG
    Lg.box((0, 0, 0.0), (0.12, 0.17, 0.62), 'veh_steel_dark', bevel=0.012)
    Lg.box((0, 0.10, 0.02), (0.07, 0.03, 0.5), 'veh_metal')
    Lg.cyl((0, 0.0, 0.30), (0, 0.0, 1.55), 0.024, 0.022, 8, 'veh_steel_dark', True)
    Lg.cyl((0, 0.0, 0.30), (0, 0.0, 0.85), 0.048, 0.046, 8, 'veh_metal', True)
    Lg.box((0, 0.0, 1.57), (0.12, 0.09, 0.14), 'veh_dark', bevel=0.01)
    for sx in (-1, 1): Lg.box((sx * 0.075, 0.0, 1.57), (0.02, 0.07, 0.10), 'veh_dark')
    Lg.box((0, -0.04, -0.42), (0.1, 0.13, 0.22), 'veh_dark')
    for sx in (-1, 1): Lg.cyl((sx * 0.10, 0.0, -0.46), (sx * 0.10, 0.0, -0.56), 0.02, 0.02, 6, 'veh_dark', False); Lg.box((sx * 0.10, 0.0, -0.58), (0.03, 0.16, 0.03), 'veh_dark')
    Lg.box((0.22, -0.04, 0.05), (0.2, 0.26, 0.3), 'veh_can', bevel=0.01)                                                 # ammo box
    Lg.box((0.12, 0.02, 0.05), (0.06, 0.06, 0.14), 'veh_metal')
    for sx in (-1, 1): Lg.box((sx * 0.30, 0.08, 0.40), (0.02, 0.4, 0.46) if False else (0.02, 0.32, 0.28), 'veh_paint')    # shield wings
    Lg.box((0, 0.16, 0.40), (0.62, 0.34, 0.025), 'veh_paint')                                                            # gun shield
    Lg.box((0, 0.0, 0.40), (0.14, 0.14, 0.04), 'veh_dark')
    Lg.box((0, 0.05, 0.42), (0.04, 0.08, 0.02), 'veh_dark')
    M.empty('technical_muzzle', (0, GP[1], GP[2] + 1.66), 'technical_gun', 'ARROWS')
    # markers
    M.empty('technical_seat_driver', (0.34, 0.98, 0.45)); M.empty('technical_seat_p0', (-0.34, 0.98, 0.45))
    M.empty('technical_seat_p1', (0.34, 0.98, -0.20)); M.empty('technical_seat_p2', (-0.34, 0.98, -0.20))
    M.empty('technical_seat_p3', (0.58, 1.10, -2.15)); M.empty('technical_seat_p4', (-0.58, 1.10, -2.15))
    M.empty('technical_seat_gunner', (0.0, 1.32, RZ - 0.35))
    M.empty('technical_exit_L', (1.45, 0.0, 0.3)); M.empty('technical_exit_R', (-1.45, 0.0, 0.3))
    return M


def quad_atv():
    M = VM('quad_atv'); B = M.body(); n = 'quad_atv'
    R = 0.31; TW = 0.24; TX = 0.52; ZF = 0.68; ZR = -0.70
    for tag, z, side in (('FL', ZF, 1), ('FR', ZF, -1)): steer_wheel(M, tag, (side * TX, R, z), R, TW, side, lugs=12, seg=18, mud=True, lug_h=0.045)
    for tag, z, side in (('RL', ZR, 1), ('RR', ZR, -1)): add_wheel(M, '%s_wheel_%s' % (n, tag), (side * TX, R, z), R, TW, side, lugs=12, seg=18, mud=True, lug_h=0.045)
    for z in (ZF, ZR):
        B.cyl((-0.40, R, z), (0.40, R, z), 0.035, 0.035, 8, 'veh_steel_dark', True)
        for sx in (-1, 1):
            tube(B, (sx * 0.30, R + 0.35, z + (0.05 if z > 0 else -0.05)), (sx * 0.40, R + 0.04, z), 0.016, 'veh_steel_dark', 4)   # shock
    B.cyl((0, R, ZR), (0, R, ZF), 0.025, 0.025, 6, 'veh_dark', False)
    # frame + engine
    bx(B, -0.22, 0.22, 0.30, 0.40, -0.85, 0.90, 'veh_steel_dark')
    bx(B, -0.2, 0.2, 0.40, 0.66, -0.32, 0.30, 'veh_steel_dark', 0.03)
    B.cyl((0.0, 0.58, -0.05), (0.0, 0.58, 0.17), 0.16, 0.16, 10, 'veh_metal', True)
    B.cyl((0.30, 0.34, -0.9), (0.30, 0.34, -0.45), 0.045, 0.04, 8, 'veh_rust', True)
    bx(B, 0.20, 0.34, 0.28, 0.40, -1.0, -0.55, 'veh_steel_dark')
    # body panels: fenders, nose, fuel tank, seat
    blk(B, -0.26, 0.26, 0.46, 0.74, 0.40, 1.08, 'veh_paint', (0.04, 0.04, 0.0, 0.20))                                    # nose
    bx(B, -0.28, 0.28, 0.78, 0.82, 0.60, 0.95, 'veh_dark')
    for sx in (-1, 1):
        xi, xo = (0.30, 0.66) if sx > 0 else (-0.66, -0.30)
        bx(B, xi, xo, 0.64, 0.69, ZF - 0.40, ZF + 0.36, 'veh_paint', 0.02)
        bx(B, xi, xo, 0.64, 0.69, ZR - 0.42, ZR + 0.42, 'veh_paint', 0.02)
        bx(B, sx * 0.30 - 0.02, sx * 0.30 + 0.02, 0.40, 0.60, 0.0, 0.40, 'veh_paint')
    blk(B, -0.26, 0.26, 0.70, 0.96, 0.05, 0.50, 'veh_paint', (0.04, 0.04, 0.06, 0.04))                                   # fuel tank
    B.cyl((0, 0.97, 0.30), (0, 1.00, 0.30), 0.04, 0.04, 8, 'veh_dark', False)
    # long seat for two (rider + passenger)
    B.box((0, 0.78, -0.36), (0.38, 0.12, 0.95), 'veh_seat', bevel=0.03)
    B.box((0, 0.88, -0.72), (0.38, 0.14, 0.2), 'veh_seat', bevel=0.03)                                                   # passenger back-rest
    B.box((0, 0.84, -0.50), (0.34, 0.03, 0.04), 'veh_dark')
    for sx in (-1, 1): B.box((sx * 0.30, 0.54, -0.35), (0.12, 0.03, 0.9), 'veh_dark')                                     # foot boards
    # handlebars and headlight
    tube(B, (0, 0.72, 0.38), (0, 1.12, 0.32), 0.024, 'veh_steel_dark', 6)
    tube(B, (-0.42, 1.14, 0.30), (0.42, 1.14, 0.30), 0.02, 'veh_steel_dark', 6)
    for sx in (-1, 1):
        B.cyl((sx * 0.30, 1.14, 0.30), (sx * 0.46, 1.14, 0.30), 0.028, 0.028, 6, 'veh_rubber', False)
        B.box((sx * 0.20, 1.18, 0.34), (0.05, 0.03, 0.08), 'veh_dark')
        headlight(B, (sx * 0.20, 0.70, 1.08), 0.07, 0.05)
    B.box((0, 1.20, 0.30), (0.12, 0.06, 0.05), 'veh_dark')
    # racks: front and rear with rifle rack
    bx(B, -0.28, 0.28, 0.80, 0.83, 0.46, 0.92, 'veh_steel_dark')
    for sx in (-1, 1): tube(B, (sx * 0.27, 0.80, 0.46), (sx * 0.27, 0.92, 0.92), 0.012, 'veh_steel_dark', 4)
    for z in (0.5, 0.7, 0.9): tube(B, (-0.27, 0.83, z), (0.27, 0.83, z), 0.012, 'veh_steel_dark', 4)
    bx(B, -0.34, 0.34, 0.74, 0.78, -1.05, -0.82, 'veh_steel_dark')
    for sx in (-1, 1): tube(B, (sx * 0.33, 0.78, -1.05), (sx * 0.33, 0.96, -1.05), 0.012, 'veh_steel_dark', 4); tube(B, (sx * 0.33, 0.78, -0.82), (sx * 0.33, 0.96, -0.82), 0.012, 'veh_steel_dark', 4)
    tube(B, (-0.33, 0.96, -1.05), (0.33, 0.96, -1.05), 0.012, 'veh_steel_dark', 4)
    for z in (-0.88, -0.96): tube(B, (-0.33, 0.86, z), (0.33, 0.86, z), 0.012, 'veh_steel_dark', 4)
    B.box((0, 0.84, -1.0), (0.5, 0.20, 0.14), 'veh_can', bevel=0.012)                                                    # cargo box
    # rifle rack on left rear (+x): two rifles in a cradle, upright slanted barrels
    xr = 0.45
    for k, off in enumerate((-0.06, 0.06)):
        a = (xr + off * 0, 0.60, -0.88 - off * 3.0)
        tube(B, (xr + off, 0.62, -0.62 + off * 0.0), (xr + off, 1.18, -0.58), 0.012, 'veh_dark', 6)                    # rifle barrel
        B.box((xr + off, 0.70, -0.64), (0.03, 0.22, 0.05), 'veh_wood')                                                      # stock
        B.box((xr + off, 0.92, -0.60), (0.035, 0.28, 0.04), 'veh_dark')                                                     # body
    B.box((xr, 0.60, -0.66), (0.20, 0.07, 0.10), 'veh_steel_dark', bevel=0.01)                                           # cradle lower
    B.box((xr, 0.98, -0.58), (0.20, 0.04, 0.05), 'veh_steel_dark')                                                       # strap
    # tail light + number plate (blank)
    taillight(B, (0.0, 0.74, -1.07), 0.16, 0.06); B.box((0.0, 0.60, -1.05), (0.20, 0.10, 0.015), 'veh_white')
    # markers
    M.empty('quad_atv_seat_driver', (0.0, 0.88, -0.20)); M.empty('quad_atv_seat_p0', (0.0, 0.92, -0.62))
    M.empty('quad_atv_exit_L', (1.0, 0.0, -0.3)); M.empty('quad_atv_exit_R', (-1.0, 0.0, -0.3))
    return M
