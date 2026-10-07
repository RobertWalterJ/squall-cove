"""supply_truck (6x6 canvas cargo), ambulance (armoured 4x4), fuel_truck (6x4 tanker)."""
from v_lib import *
from v_heavy import frame_panel, side_x


def truck_wheels(M, B, n, axles, R, tw, tx, steer_n=1, lugs=20, seg=22, lug_h=0.04):
    """axles: list of (tag, z). The first `steer_n` axles get steering pivots."""
    for i, (tag, z) in enumerate(axles):
        for sd, s in (('L', 1), ('R', -1)):
            if i < steer_n: steer_wheel(M, tag + sd, (s * tx, R, z), R, tw, s, lugs=lugs, seg=seg, lug_h=lug_h)
            else: add_wheel(M, '%s_wheel_%s%s' % (n, tag, sd), (s * tx, R, z), R, tw, s, lugs=lugs, seg=seg, lug_h=lug_h)
        B.cyl((-tx + 0.1, R, z), (tx - 0.1, R, z), 0.07, 0.07, 8, 'veh_steel_dark', True)
        B.ellipsoid((0, R - 0.05, z), (0.24, 0.18, 0.2), 'veh_steel_dark', seg=8, nl=4)
        for s in (-1, 1):
            bx(B, s * (tx - 0.30) - 0.05, s * (tx - 0.30) + 0.05, R + 0.12, R + 0.20, z - 0.6, z + 0.6, 'veh_steel_dark')
            tube(B, (s * (tx - 0.30), R + 0.20, z), (s * (tx - 0.30), R + 0.34, z), 0.04, 'veh_dark', 6)


def chassis(B, z0, z1, y0=0.88, y1=1.04, hw=0.46):
    bx2(B, hw - 0.12, hw, y0, y1, z0, z1, 'veh_steel_dark')
    for z in [z0 + 0.4 + (z1 - z0 - 0.8) * k / 6 for k in range(7)]: bx(B, -hw, hw, y0 + 0.02, y0 + 0.10, z - 0.05, z + 0.05, 'veh_steel_dark')
    B.cyl((0, y0 - 0.02, z0 + 0.5), (0, y0 - 0.02, z1 - 0.5), 0.035, 0.035, 6, 'veh_dark', False)


def truck_front(B, hw, zb, zf, zh, fy, by, ry, hood_bot, hood_top, axle_z, R, tx, tw, rake=0.20):
    """Conventional cab + hood + fenders + grille + bumper (front is +z), with seats and a steering wheel inside."""
    bx(B, -hw, hw, fy, by, zb, zf, 'veh_paint', 0.03)
    gh = hw - 0.06; zm = (zb + zf) / 2
    for s in (-1, 1):
        tube(B, (s * gh, by, zf - 0.02), (s * gh, ry, zf - rake), 0.07, 'veh_paint')
        tube(B, (s * gh, by, zb + 0.04), (s * gh, ry, zb + 0.04), 0.07, 'veh_paint')
        tube(B, (s * gh, by, zm - 0.08), (s * gh, ry, zm - 0.08), 0.06, 'veh_paint')
        B.patch([[(s * (gh + 0.01), by + 0.04, zm - 0.14), (s * (gh + 0.01), by + 0.04, zb + 0.10)], [(s * (gh + 0.01), ry - 0.05, zm - 0.14), (s * (gh + 0.01), ry - 0.05, zb + 0.10)]], 'veh_glass', (s, 0, 0), False)
        B.patch([[(s * (gh + 0.01), by + 0.04, zf - 0.06), (s * (gh + 0.01), by + 0.04, zm - 0.02)], [(s * (gh + 0.01), ry - 0.05, zf - rake - 0.06), (s * (gh + 0.01), ry - 0.05, zm - 0.02)]], 'veh_glass', (s, 0, 0), False)
        bx(B, s * (hw - 0.01), s * (hw + 0.03), by - 0.30, by - 0.22, zm + 0.38, zm + 0.62, 'veh_steel_dark')
        frame_panel(B, s, hw, fy + 0.10, by - 0.04, zb + 0.15, zf - 0.20)
        bx(B, s * (hw - 0.02), s * (hw + 0.20), fy - 0.12, fy - 0.07, zb + 0.20, zf - 0.30, 'veh_steel_dark')
        tube(B, (s * (hw + 0.12), fy - 0.07, zb + 0.25), (s * (hw + 0.12), fy - 0.40, zb + 0.25), 0.03, 'veh_steel_dark')
        tube(B, (s * (hw - 0.02), by + 0.45, zf - 0.28), (s * (hw + 0.36), by + 0.55, zf - 0.30), 0.02, 'veh_steel_dark', 6)
        B.box((s * (hw + 0.38), by + 0.62, zf - 0.30), (0.05, 0.38, 0.20), 'veh_dark', bevel=0.01)
    bx(B, -hw - 0.03, hw + 0.03, ry - 0.07, ry, zb - 0.04, zf - rake + 0.06, 'veh_paint', 0.03)
    B.patch([[(-gh + 0.04, by + 0.05, zf - 0.02), (gh - 0.04, by + 0.05, zf - 0.02)], [(-gh + 0.04, ry - 0.07, zf - rake), (gh - 0.04, ry - 0.07, zf - rake)]], 'veh_glass', (0, 0.3, 1), False)
    tube(B, (0, by, zf - 0.02), (0, ry - 0.07, zf - rake), 0.05, 'veh_paint')
    B.patch([[(-gh + 0.04, by + 0.10, zb + 0.01), (gh - 0.04, by + 0.10, zb + 0.01)], [(-gh + 0.04, ry - 0.2, zb + 0.01), (gh - 0.04, ry - 0.2, zb + 0.01)]], 'veh_glass', (0, 0, -1), False)
    bx(B, -0.6, 0.6, ry, ry + 0.07, zb + 0.3, zb + 0.9, 'veh_paint', 0.02)
    bx(B, -hw, hw, fy - 0.35, fy, zb + 0.02, zf, 'veh_steel_dark')
    for x in (0.46, -0.46): seat(B, x, fy + 0.38, zb + 0.55, 0.46, 0.46, back_h=0.7)
    steering_wheel(B, (0.46, fy + 0.95, zf - 0.55), 0.22, -35, col_to=(0.46, fy + 0.6, zf - 0.20))
    bx(B, -hw + 0.06, hw - 0.06, fy + 0.55, fy + 0.80, zf - 0.28, zf - 0.04, 'veh_dark', 0.02)
    ht, hb = hood_top, hood_bot
    blk(B, -hw + 0.14, hw - 0.14, hb, ht, zf, zh - 0.12, 'veh_paint', (0.10, 0.10, 0.0, 0.16))
    bx(B, -hw + 0.02, hw - 0.02, hb - 0.05, ht - 0.05, zh - 0.14, zh - 0.02, 'veh_paint', 0.02)
    for i in range(7): bx(B, -hw * 0.6 + i * hw * 0.2 - 0.025, -hw * 0.6 + i * hw * 0.2 + 0.025, hb + 0.08, ht - 0.14, zh - 0.025, zh, 'veh_dark')
    for s in (-1, 1):
        headlight(B, (s * (hw - 0.22), (hb + ht) / 2 + 0.05, zh - 0.02), 0.11, 0.07)
        B.box((s * (hw - 0.22), hb + 0.05, zh + 0.02), (0.16, 0.06, 0.04), 'veh_light_amber')
        for k in range(4): bx(B, s * (hw - 0.12) - 0.01, s * (hw - 0.12) + 0.01, hb + 0.25 + k * 0.09, hb + 0.29 + k * 0.09, zf + 0.25, zf + 0.8, 'veh_dark')
        tube(B, (s * 0.45, hb - 0.2, zh + 0.22), (s * 0.45, hb - 0.2, zh + 0.34), 0.04, 'veh_steel_dark', 6)
    bx(B, -hw - 0.05, hw + 0.05, hb - 0.30, hb - 0.10, zh - 0.02, zh + 0.22, 'veh_steel_dark', 0.02)
    B.cyl((-0.5, hb - 0.2, zh + 0.12), (0.5, hb - 0.2, zh + 0.12), 0.07, 0.07, 8, 'veh_steel_dark', False)
    ft = R * 2 + 0.10
    for s in (-1, 1):
        xi, xo = s * (hw - 0.30), s * (tx + tw / 2 + 0.10)
        bx(B, xi, xo, ft, ft + 0.05, axle_z - 0.72, axle_z + 0.72, 'veh_paint', 0.02)
        bx(B, s * (tx + tw / 2 + 0.06), xo, ft - 0.45, ft + 0.05, axle_z - 0.72, axle_z + 0.72, 'veh_paint')
        B.patch([[(xi, ft, axle_z + 0.72), (xo, ft, axle_z + 0.72)], [(xi, ft - 0.2, axle_z + 0.84), (xo, ft - 0.2, axle_z + 0.84)], [(xi, ft - 0.45, axle_z + 0.86), (xo, ft - 0.45, axle_z + 0.86)]], 'veh_paint', (0, 1, 1), False)


def mud_flaps(B, x, y, z, w=0.55):
    for s in (-1, 1): B.box((s * x, y, z), (w, 0.5, 0.025), 'veh_rubber')


# =========================================================================== supply truck
def supply_truck():
    M = VM('supply_truck'); B = M.body(); n = 'supply_truck'
    R = 0.55; TW = 0.32; TX = 0.98; HW = 1.0
    AX = [('F1', 3.0), ('R1', -1.2), ('R2', -2.6)]
    truck_wheels(M, B, n, AX, R, TW, TX, 1)
    chassis(B, -4.2, 4.0)
    truck_front(B, HW, 0.60, 2.25, 3.95, 1.05, 1.80, 2.70, 1.02, 1.82, 3.0, R, TX, TW)
    B.cyl((1.08, 0.78, 0.9), (1.08, 0.78, -0.2), 0.26, 0.26, 12, 'veh_steel_dark', True)
    B.cyl((-1.08, 0.8, 1.0), (-1.08, 0.8, 0.3), 0.14, 0.14, 8, 'veh_dark', True)
    B.cyl((-1.12, 0.85, 0.5), (-1.12, 2.9, 0.5), 0.07, 0.07, 8, 'veh_rust', True)
    B.cyl((-1.12, 2.9, 0.5), (-1.12, 2.98, 0.5), 0.10, 0.07, 8, 'veh_dark', False)
    FL = 1.30; SZ0, SZ1 = 0.38, -4.30
    bx(B, -1.15, 1.15, FL - 0.12, FL, SZ1, SZ0, 'veh_paint')
    bx(B, -1.12, 1.12, FL, FL + 0.04, SZ1 + 0.04, SZ0 - 0.02, 'veh_wood')
    for s in (-1, 1):
        bx(B, s * 1.12, s * 1.17, FL - 0.12, FL + 0.62, SZ1, SZ0, 'veh_paint')
        for z in [SZ0 - 0.2 - k * 0.78 for k in range(6)]: bx(B, s * 1.12, s * 1.20, FL - 0.12, FL + 0.62, z - 0.03, z + 0.03, 'veh_paint')
        bx(B, s * 1.10, s * 1.22, FL + 0.58, FL + 0.66, SZ1, SZ0, 'veh_steel_dark')
        bx(B, s * 1.16, s * 1.20, FL - 0.40, FL - 0.12, SZ1 + 0.4, SZ0 - 0.2, 'veh_paint')
        bx(B, s * 1.12, s * 1.20, FL - 0.12, FL + 0.66, SZ1 - 0.10, SZ1 - 0.04, 'veh_steel_dark')
        B.box((s * 1.0, FL + 0.50, SZ1 - 0.13), (0.1, 0.12, 0.04), 'veh_steel_dark')
        taillight(B, (s * 0.9, FL + 0.14, SZ1 - 0.13), 0.22, 0.12)
        bx(B, s * 0.68, s * 1.08, FL + 0.38, FL + 0.43, SZ1 + 0.1, SZ0 - 0.18, 'veh_wood')
        for z in [SZ0 - 0.4 - k * 1.0 for k in range(5)]: bx(B, s * 0.72, s * 0.76, FL + 0.04, FL + 0.38, z - 0.03, z + 0.03, 'veh_steel_dark')
    bx(B, -1.17, 1.17, FL - 0.12, FL + 1.05, SZ0 - 0.04, SZ0 + 0.04, 'veh_paint')
    bx(B, -1.15, 1.15, FL - 0.12, FL + 0.66, SZ1 - 0.07, SZ1, 'veh_paint')
    bx(B, -1.2, 1.2, 0.98, 1.08, -4.45, -4.28, 'veh_steel_dark', 0.02)
    B.cyl((0, 1.0, -4.45), (0, 1.0, -4.62), 0.04, 0.04, 6, 'veh_steel_dark', False)
    mud_flaps(B, 0.98, 0.82, -3.35)
    # canvas tunnel
    ARC = 1.12; YB = FL + 0.66; YH = 1.15
    def arc(sc, z): return [(ARC * sc * math.cos(PI * t / 10), YB + YH * sc * math.sin(PI * t / 10) - (0.0 if sc == 1 else 0.05), z) for t in range(11)]
    zs = [SZ0, -0.4, -1.4, -2.4, -3.4, SZ1 - 0.05]
    B.patch([arc(1.0 + (0.02 if 0 < i < len(zs) - 1 else 0), z) for i, z in enumerate(zs)], 'veh_canvas', (0, 1, 0), False)
    B.add([(ARC * math.cos(PI * t / 10), YB + YH * math.sin(PI * t / 10), SZ0) for t in range(11)], [tuple(range(11))], 'veh_canvas', False, orient=False)
    for z in (-0.4, -1.4, -2.4, -3.4, SZ1 + 0.05):
        B.sweep([(ARC * 0.97 * math.cos(PI * t / 10), YB + (YH - 0.03) * math.sin(PI * t / 10), z) for t in range(11)], 0.022, 4, 'veh_steel_dark', False, (True, True))
    B.sweep([(ARC * math.cos(PI * t / 10), YB + YH * math.sin(PI * t / 10), SZ1 - 0.05) for t in range(11)], 0.03, 5, 'veh_canvas_dark', False, (True, True))
    for z in (-0.4, -1.4, -2.4, -3.4):
        for s in (-1, 1): B.sweep([(s * 1.12, YB - 0.2, z), (s * 1.125, YB + 0.02, z)], 0.015, 4, 'veh_canvas_dark', False)
    B.box((1.14, 0.62, -0.95), (0.12, 0.46, 0.34), 'veh_can', bevel=0.01)
    M.empty('supply_truck_seat_driver', (0.46, 1.43, 1.15)); M.empty('supply_truck_seat_p0', (-0.46, 1.43, 1.15))
    k = 1
    for s in (1, -1):
        for z in (-0.5, -1.5, -2.5, -3.5):
            M.empty('supply_truck_seat_p%d' % k, (s * 0.88, FL + 0.50, z)); k += 1
    M.empty('supply_truck_exit_L', (1.8, 0.0, 1.4)); M.empty('supply_truck_exit_R', (-1.8, 0.0, 1.4)); M.empty('supply_truck_exit_rear', (0.0, 0.0, -5.0))
    return M


# =========================================================================== ambulance
def ambulance():
    M = VM('ambulance'); B = M.body(); n = 'ambulance'
    R = 0.50; TW = 0.34; TX = 1.0
    for tag, z in (('F', 2.15), ('R', -1.65)):
        for sd, s in (('L', 1), ('R', -1)):
            nm = tag + sd
            if tag == 'F': steer_wheel(M, nm, (s * TX, R, z), R, TW, s, lugs=18, seg=22, lug_h=0.035)
            else: add_wheel(M, '%s_wheel_%s' % (n, nm), (s * TX, R, z), R, TW, s, lugs=18, seg=22, lug_h=0.035)
        B.cyl((-0.90, R, z), (0.90, R, z), 0.07, 0.07, 8, 'veh_steel_dark', True)
        B.ellipsoid((0, R - 0.05, z), (0.22, 0.16, 0.2), 'veh_steel_dark', seg=8, nl=4)
        for s in (-1, 1): bx(B, s * 0.72 - 0.05, s * 0.72 + 0.05, R + 0.10, R + 0.18, z - 0.55, z + 0.55, 'veh_steel_dark')
    B.cyl((0, 0.55, -1.65), (0, 0.55, 2.15), 0.04, 0.04, 6, 'veh_dark', False)
    hood = [(3.55, 0.80, 0.92, 0.76, 0.66, 1.05, 1.28), (3.15, 0.95, 1.05, 0.92, 0.62, 1.15, 1.52), (2.50, 1.02, 1.10, 1.00, 0.60, 1.2, 1.62), (2.05, 1.02, 1.10, 1.00, 0.60, 1.2, 1.62)]
    B.loft(hull_rings(hood), 'veh_paint', False, (True, True))
    body = [(2.05, 1.02, 1.10, 1.0, 0.60, 1.2, 1.64), (1.78, 1.02, 1.10, 0.98, 0.60, 1.2, 2.34), (0.52, 1.02, 1.10, 0.98, 0.60, 1.2, 2.34), (0.46, 1.04, 1.12, 1.0, 0.60, 1.2, 2.66),
            (-3.30, 1.04, 1.12, 1.0, 0.62, 1.2, 2.66), (-3.50, 1.0, 1.08, 0.96, 0.66, 1.18, 2.50)]
    B.loft(hull_rings(body), 'veh_paint', False, (True, True))
    bx(B, -0.7, 0.7, 0.50, 0.62, -3.3, 3.3, 'veh_steel_dark')
    for z in (2.15, -1.65):
        for s in (-1, 1):
            bx(B, s * 1.00, s * 1.58, 1.08, 1.14, z - 0.62, z + 0.62, 'veh_paint', 0.02)
            bx(B, s * 1.52, s * 1.56, 0.92, 1.14, z - 0.62, z + 0.62, 'veh_paint')
    bx(B, -0.95, 0.95, 0.50, 0.70, 3.50, 3.72, 'veh_steel_dark', 0.02)
    for s in (-1, 1):
        headlight(B, (s * 0.65, 0.98, 3.54), 0.10, 0.07)
        tube(B, (s * 0.42, 0.55, 3.72), (s * 0.42, 0.55, 3.88), 0.04, 'veh_steel_dark', 6)
        tube(B, (s * 0.9, 0.75, 3.62), (s * 0.9, 1.35, 3.30), 0.03, 'veh_steel_dark', 6)
    B.patch([[(-0.88, 1.66, 1.77), (-0.04, 1.66, 1.77)], [(-0.82, 2.18, 1.52), (-0.06, 2.18, 1.52)]], 'veh_glass', (0, 0.3, 1), False)
    B.patch([[(0.04, 1.66, 1.77), (0.88, 1.66, 1.77)], [(0.06, 2.18, 1.52), (0.82, 2.18, 1.52)]], 'veh_glass', (0, 0.3, 1), False)
    for s in (-1, 1):
        xs = side_x(1.9, 0.6, 1.2, 2.34, 1.02, 1.10, 0.98)
        frame_panel(B, s, side_x(1.45, 0.6, 1.2, 2.34, 1.02, 1.10, 0.98), 1.18, 2.22, 0.55, 1.75)
        B.patch([[(s * (xs + 0.015), 1.86, 1.58), (s * (xs + 0.015), 1.86, 0.78)], [(s * (xs + 0.015), 2.14, 1.58), (s * (xs + 0.015), 2.14, 0.78)]], 'veh_glass', (s, 0, 0), False)
        bx(B, s * (xs - 0.02), s * (xs + 0.045), 1.56, 1.62, 0.72, 0.92, 'veh_steel_dark')
        tube(B, (s * 1.12, 1.9, 1.72), (s * 1.38, 2.05, 1.72), 0.02, 'veh_steel_dark', 6); B.box((s * 1.40, 2.15, 1.72), (0.06, 0.4, 0.2), 'veh_dark')
        bx(B, s * 1.02, s * 1.22, 0.58, 0.66, 0.45, 1.8, 'veh_steel_dark')
        xs2 = side_x(1.97, 0.62, 1.2, 2.66, 1.04, 1.12, 1.0)
        for z in (-0.2, -2.6): B.patch([[(s * (xs2 + 0.012), 1.84, z + 0.3), (s * (xs2 + 0.012), 1.84, z - 0.3)], [(s * (xs2 + 0.012), 2.14, z + 0.3), (s * (xs2 + 0.012), 2.14, z - 0.3)]], 'veh_glass', (s, 0, 0), False)
        xw = side_x(1.55, 0.62, 1.2, 2.66, 1.04, 1.12, 1.0) + 0.012
        zc, yc = -1.4, 1.55
        bx(B, s * xw, s * (xw + 0.02), yc - 0.45, yc + 0.45, zc - 0.45, zc + 0.45, 'veh_white')
        bx(B, s * xw, s * (xw + 0.04), yc - 0.35, yc + 0.35, zc - 0.11, zc + 0.11, 'veh_red_cross')
        bx(B, s * xw, s * (xw + 0.045), yc - 0.11, yc + 0.11, zc - 0.35, zc + 0.35, 'veh_red_cross')
        bx(B, s * xw, s * (xw + 0.03), 0.62, 0.70, -3.1, 0.3, 'veh_steel_dark')
        B.box((s * 1.14, 1.0, 0.12), (0.1, 0.46, 0.34), 'veh_can', bevel=0.01)
    bx(B, -0.62, 0.62, 2.66, 2.68, -2.8, -0.2, 'veh_white')
    bx(B, -0.10, 0.10, 2.68, 2.70, -2.4, -0.6, 'veh_red_cross'); bx(B, -0.55, 0.55, 2.68, 2.705, -1.60, -1.40, 'veh_red_cross')
    bx(B, -0.55, 0.55, 2.30, 2.40, 1.0, 1.25, 'veh_dark', 0.02)
    bx(B, -0.5, 0.0, 2.40, 2.48, 1.0, 1.25, 'veh_light_red'); bx(B, 0.0, 0.5, 2.40, 2.48, 1.0, 1.25, 'veh_light_amber')
    bx(B, -0.45, 0.45, 2.66, 2.80, 0.1, 0.6, 'veh_steel_dark', 0.02)
    B.sweep([(-0.9, 2.66, -3.1), (-0.95, 3.5, -3.2), (-0.98, 4.2, -3.25)], [0.014, 0.01, 0.006], 5, 'veh_dark', False, (True, True))
    zr = -3.50
    for s in (-1, 1):
        bx(B, 0.0, s * 0.96, 0.78, 2.46, zr - 0.04, zr + 0.02, 'veh_paint')
        bx(B, s * 0.02, s * 0.04, 0.78, 2.46, zr - 0.07, zr - 0.04, 'veh_dark')
        bx(B, s * 0.86, s * 0.94, 1.1, 1.5, zr - 0.10, zr - 0.06, 'veh_steel_dark')
        taillight(B, (s * 0.88, 0.92, zr - 0.06), 0.14, 0.2)
    bx(B, -0.62, 0.62, 1.12, 2.12, zr - 0.07, zr - 0.05, 'veh_white')
    bx(B, -0.10, 0.10, 1.22, 2.02, zr - 0.09, zr - 0.07, 'veh_red_cross'); bx(B, -0.40, 0.40, 1.52, 1.72, zr - 0.095, zr - 0.07, 'veh_red_cross')
    bx(B, -1.05, 1.05, 0.55, 0.72, -3.58, -3.42, 'veh_steel_dark', 0.02)
    B.cyl((0, 0.62, -3.58), (0, 0.62, -3.8), 0.04, 0.04, 6, 'veh_steel_dark', False)
    M.empty('ambulance_seat_driver', (0.46, 1.35, 1.35)); M.empty('ambulance_seat_p0', (-0.46, 1.35, 1.35))
    M.empty('ambulance_seat_p1', (0.75, 1.30, -0.4)); M.empty('ambulance_seat_p2', (0.75, 1.30, -1.3)); M.empty('ambulance_seat_p3', (-0.2, 1.0, -1.8))
    M.empty('ambulance_exit_L', (1.8, 0.0, 1.2)); M.empty('ambulance_exit_R', (-1.8, 0.0, 1.2)); M.empty('ambulance_exit_rear', (0.0, 0.0, -4.4))
    return M


# =========================================================================== fuel truck
def fuel_truck():
    M = VM('fuel_truck'); B = M.body(); n = 'fuel_truck'
    R = 0.52; TW = 0.32; TX = 0.98; HW = 1.0
    AX = [('F1', 2.85), ('R1', -1.55), ('R2', -2.90)]
    truck_wheels(M, B, n, AX, R, TW, TX, 1)
    chassis(B, -4.4, 4.1)
    truck_front(B, HW, 0.55, 2.15, 3.75, 1.02, 1.74, 2.62, 1.0, 1.78, 2.85, R, TX, TW)
    TY = 2.12; RX = 1.05; RY = 0.78
    st = [(0.12, 0.55, 0.40, TY), (0.20, 0.88, 0.64, TY), (0.37, 1.02, 0.76, TY), (0.60, RX, RY, TY), (-3.5, RX, RY, TY), (-3.75, 1.02, 0.76, TY), (-3.88, 0.82, 0.60, TY), (-3.94, 0.55, 0.40, TY)]
    ellipse_hull(B, st, 'veh_paint', 18, True)
    for z in (-0.1, -1.2, -2.3, -3.2): ellipse_hull(B, [(z + 0.06, RX + 0.018, RY + 0.018, TY), (z - 0.06, RX + 0.018, RY + 0.018, TY)], 'veh_metal', 18, False, (False, False))
    for s in (-1, 1): bx(B, s * 0.88, s * 1.12, 1.18, 1.34, -3.6, 0.3, 'veh_steel_dark')
    for z in (0.1, -1.9, -3.6): bx(B, -0.8, 0.8, 1.20, 1.38, z - 0.15, z + 0.15, 'veh_steel_dark')
    for z in (-0.2, -1.4, -2.7):
        B.cyl((0, TY + RY - 0.03, z), (0, TY + RY + 0.14, z), 0.30, 0.30, 12, 'veh_metal', False)
        B.cyl((0, TY + RY + 0.14, z), (0, TY + RY + 0.20, z), 0.26, 0.26, 12, 'veh_steel_dark', False)
        B.box((0.0, TY + RY + 0.23, z), (0.34, 0.05, 0.05), 'veh_dark')
        tube(B, (0.22, TY + RY + 0.14, z - 0.3), (0.22, TY + RY + 0.28, z - 0.3), 0.03, 'veh_steel_dark', 6)
    bx(B, -0.28, 0.28, TY + RY - 0.02, TY + RY + 0.03, -3.5, 0.3, 'veh_metal')
    for s in (-1, 1):
        for z in (0.2, -0.8, -2.2, -3.5): tube(B, (s * 0.30, TY + RY, z), (s * 0.30, TY + RY + 0.5, z), 0.016, 'veh_steel_dark', 6)
        tube(B, (s * 0.30, TY + RY + 0.5, 0.2), (s * 0.30, TY + RY + 0.5, -3.5), 0.016, 'veh_steel_dark', 6)
    zc = -3.94
    bx(B, -0.85, 0.85, 1.0, 1.9, zc - 0.25, zc + 0.10, 'veh_paint', 0.02)
    bx(B, -0.78, 0.78, 1.06, 1.84, zc - 0.28, zc - 0.25, 'veh_dark')
    for i in range(3): bx(B, -0.65 + i * 0.5, -0.55 + i * 0.5, 1.16, 1.74, zc - 0.30, zc - 0.27, 'veh_steel_dark')
    for s in (-1, 1):
        B.cyl((s * 0.5, 1.4, zc - 0.28), (s * 0.5, 1.4, zc - 0.55), 0.06, 0.06, 8, 'veh_metal', False)
        B.cyl((s * 0.5, 1.4, zc - 0.55), (s * 0.5, 1.4, zc - 0.62), 0.09, 0.09, 8, 'veh_steel_dark', False)
        taillight(B, (s * 0.92, 1.1, zc - 0.28), 0.14, 0.2)
    for k in range(3):
        r = 0.20 + k * 0.045
        B.sweep([(-1.17, 1.55 + r * math.sin(2 * PI * j / 12), -3.4 + r * math.cos(2 * PI * j / 12)) for j in range(13)], 0.032, 5, 'veh_hose', True, (False, False))
    B.cyl((-1.1, 1.55, -3.4), (-1.19, 1.55, -3.4), 0.12, 0.12, 8, 'veh_steel_dark', False)
    tube(B, (-0.65, 1.0, zc - 0.4), (-0.65, 3.0, zc - 0.4), 0.02, 'veh_steel_dark', 6); tube(B, (-0.9, 1.0, zc - 0.4), (-0.9, 3.0, zc - 0.4), 0.02, 'veh_steel_dark', 6)
    for k in range(9): tube(B, (-0.9, 1.15 + k * 0.22, zc - 0.4), (-0.65, 1.15 + k * 0.22, zc - 0.4), 0.014, 'veh_steel_dark', 6)
    bx(B, -1.1, 1.1, 0.88, 1.0, -4.5, -4.3, 'veh_steel_dark', 0.02)
    mud_flaps(B, 0.98, 0.75, -3.45)
    B.cyl((-1.12, 0.85, 0.4), (-1.12, 2.55, 0.4), 0.07, 0.07, 8, 'veh_rust', True)
    B.cyl((1.1, 0.78, 0.9), (1.1, 0.78, 0.0), 0.24, 0.24, 12, 'veh_steel_dark', True)
    M.empty('fuel_truck_seat_driver', (0.46, 1.40, 1.10)); M.empty('fuel_truck_seat_p0', (-0.46, 1.40, 1.10))
    M.empty('fuel_truck_exit_L', (1.8, 0.0, 1.3)); M.empty('fuel_truck_exit_R', (-1.8, 0.0, 1.3))
    return M
