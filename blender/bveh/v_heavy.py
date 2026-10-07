"""apc (8x8 wheeled) and light_tank (tracked)."""
from v_lib import *


def ring_xz(y, cx, cz, rx, rz, n=12, a0=PI / 12):
    return [(cx + rx * math.cos(a0 + 2 * PI * k / n), y, cz + rz * math.sin(a0 + 2 * PI * k / n)) for k in range(n)]


def side_x(y, y0, ym, y1, wb, wm, wt):
    """half width of the 6-point hull ring at height y"""
    if y <= ym: return wb + (wm - wb) * (y - y0) / (ym - y0)
    return wm + (wt - wm) * (y - ym) / (y1 - ym)


def frame_panel(P, s, x, y0, y1, z0, z1, mat='veh_dark'):
    """Flat outline (4 thin bars) of a panel on a side face; x = magnitude of the face position, s = +1 left / -1 right."""
    t = 0.04; a, b = s * (x - 0.02), s * (x + 0.02)
    bx(P, a, b, y0, y1, z0, z0 + t, mat); bx(P, a, b, y0, y1, z1 - t, z1, mat)
    bx(P, a, b, y0, y0 + t, z0, z1, mat); bx(P, a, b, y1 - t, y1, z0, z1, mat)


def apc():
    M = VM('apc'); B = M.body(); n = 'apc'
    R = 0.54; TW = 0.36; TX = 1.30
    AX = (('F1', 2.55), ('F2', 1.30), ('R1', -1.30), ('R2', -2.55))
    for tag, z in AX:
        for sd, s in (('L', 1), ('R', -1)):
            if tag[0] == 'F': steer_wheel(M, tag + sd, (s * TX, R, z), R, TW, s, lugs=18, seg=18, lug_h=0.035)
            else: add_wheel(M, '%s_wheel_%s%s' % (n, tag, sd), (s * TX, R, z), R, TW, s, lugs=18, seg=18, lug_h=0.035)
        B.cyl((-1.10, R, z), (1.10, R, z), 0.07, 0.07, 8, 'veh_steel_dark', True)
        B.ellipsoid((0, R - 0.05, z), (0.22, 0.17, 0.2), 'veh_steel_dark', seg=8, nl=4)
        for sd in (-1, 1): tube(B, (sd * 0.92, R + 0.04, z), (sd * 0.98, R + 0.44, z), 0.04, 'veh_steel_dark', 6)
    B.cyl((0.0, 0.58, -2.55), (0.0, 0.58, 2.55), 0.04, 0.04, 6, 'veh_dark', False)
    # ---- hull
    secs = [(3.88, 0.78, 0.92, 0.74, 0.74, 1.05, 1.34), (3.55, 0.88, 1.08, 0.92, 0.66, 1.15, 1.62), (3.05, 0.90, 1.20, 1.10, 0.62, 1.22, 1.94),
            (2.5, 0.90, 1.22, 1.16, 0.62, 1.25, 2.02), (-2.8, 0.90, 1.22, 1.16, 0.62, 1.25, 2.02), (-3.80, 0.88, 1.18, 1.10, 0.66, 1.22, 1.94)]
    B.loft(hull_rings(secs), 'veh_paint', False, (True, True))
    bx(B, -0.72, 0.72, 0.52, 0.64, -3.6, 3.4, 'veh_steel_dark')
    for tag, z in AX:
        for s in (-1, 1):
            bx(B, s * 1.04, s * 1.60, 1.15, 1.20, z - 0.62, z + 0.62, 'veh_paint', 0.02)
            bx(B, s * 1.56, s * 1.60, 1.02, 1.20, z - 0.62, z + 0.62, 'veh_paint')
    # front
    bx(B, -0.55, 0.55, 0.78, 1.00, 3.90, 4.10, 'veh_paint', 0.03)
    for s in (-1, 1):
        bx(B, s * 0.70, s * 0.90, 0.92, 1.06, 3.60, 3.78, 'veh_dark', 0.02)
        headlight(B, (s * 0.80, 0.99, 3.78), 0.09, 0.07)
        tube(B, (s * 0.50, 0.80, 3.88), (s * 0.50, 0.80, 4.05), 0.04, 'veh_steel_dark', 6)
    for xx in (-0.55, 0.0, 0.55):
        bx(B, xx - 0.20, xx + 0.20, 1.68, 1.82, 3.40, 3.48, 'veh_dark')
        B.patch([[(xx - 0.17, 1.70, 3.465), (xx + 0.17, 1.70, 3.465)], [(xx - 0.17, 1.80, 3.445), (xx + 0.17, 1.80, 3.445)]], 'veh_glass', (0, 0.6, 1), False)
    # sides
    for s in (-1, 1):
        xs = side_x(1.7, 0.62, 1.25, 2.02, 0.90, 1.22, 1.16)
        frame_panel(B, s, xs, 1.38, 1.98, -0.55, 0.55)
        bx(B, s * (xs - 0.01), s * (xs + 0.04), 1.62, 1.70, 0.38, 0.52, 'veh_steel_dark')
        for z in (2.0, 1.1, -1.9, -2.6): bx(B, s * (xs - 0.01), s * (xs + 0.025), 1.62, 1.78, z - 0.09, z + 0.09, 'veh_dark')
    for k in range(2): B.box((1.19, 1.58, -1.62 - k * 0.22), (0.07, 0.42, 0.18), 'veh_can', bevel=0.01)
    tube(B, (-1.19, 1.48, -0.9), (-1.19, 1.48, -2.1), 0.02, 'veh_wood', 6); B.box((-1.19, 1.48, -2.2), (0.03, 0.2, 0.2), 'veh_metal')
    tube(B, (1.20, 1.2, 2.0), (1.20, 1.2, 3.2), 0.022, 'veh_steel_dark', 6)
    # roof
    for (x, z) in ((0.55, -0.2), (-0.55, -0.2), (0.55, -1.5), (-0.55, -1.5)):
        B.cyl((x, 2.0, z), (x, 2.08, z), 0.36, 0.36, 12, 'veh_paint', False)
        B.cyl((x, 2.08, z), (x, 2.12, z), 0.30, 0.30, 12, 'veh_steel_dark', False)
        B.box((x + 0.15, 2.15, z - 0.12), (0.10, 0.04, 0.06), 'veh_dark')
    bx(B, -0.85, 0.85, 1.98, 2.03, -3.62, -2.38, 'veh_steel_dark')
    for k in range(7): bx(B, -0.75, 0.75, 2.03, 2.07, -3.55 + k * 0.17, -3.55 + k * 0.17 + 0.08, 'veh_dark')
    bx(B, -0.2, 0.2, 1.98, 2.10, 2.55, 3.05, 'veh_paint')
    B.cyl((-0.90, 2.0, -2.2), (-0.90, 2.12, -2.2), 0.10, 0.08, 8, 'veh_dark', False)
    B.sweep([(-0.9, 2.12, -2.2), (-0.92, 3.0, -2.35), (-0.95, 3.8, -2.45)], [0.014, 0.01, 0.006], 5, 'veh_dark', False, (True, True))
    B.cyl((1.0, 1.9, -3.2), (1.0, 2.1, -3.2), 0.08, 0.08, 8, 'veh_rust', True)
    for s in (-1, 1): taillight(B, (s * 0.95, 1.05, -3.84), 0.14, 0.10)
    # ---- ramp node (closed = vertical; open it by rotating about X by about -90 deg)
    RP = (0, 0.72, -3.83)
    RM = M.node('_ramp', None, RP)
    bx(RM, -0.82, 0.82, 0.74, 1.98, -3.93, -3.80, 'veh_paint')
    for k in range(3): bx(RM, -0.74, 0.74, 0.92 + k * 0.34, 0.97 + k * 0.34, -3.955, -3.93, 'veh_dark')
    bx(RM, -0.12, 0.12, 1.30, 1.38, -4.0, -3.93, 'veh_steel_dark')
    for s in (-1, 1): bx(RM, s * 0.67, s * 0.77, 0.80, 0.90, -3.98, -3.93, 'veh_steel_dark')
    # ---- turret (pivot about Y at the ring)
    TP = (0.0, 2.02, 1.35)
    T = M.node('_turret', None, TP)
    T.loft([ring_xz(2.02, 0, 1.35, 0.85, 1.00), ring_xz(2.22, 0.0, 1.33, 0.78, 0.92), ring_xz(2.50, 0.0, 1.40, 0.55, 0.62)], 'veh_paint', False, (True, True))
    T.cyl((0, 2.02, 1.35), (0, 2.08, 1.35), 0.96, 0.96, 16, 'veh_steel_dark', False)
    bx(T, -0.34, 0.34, 2.14, 2.50, 2.17, 2.38, 'veh_paint')
    T.cyl((-0.30, 2.50, 1.20), (-0.30, 2.58, 1.20), 0.20, 0.20, 10, 'veh_paint', False)
    T.cyl((-0.30, 2.58, 1.20), (-0.30, 2.62, 1.20), 0.16, 0.16, 10, 'veh_steel_dark', False)
    for s in (-1, 1):
        bx(T, s * 0.56, s * 0.60, 2.10, 2.30, 1.8, 2.0, 'veh_dark')
        T.box((s * 0.78, 2.22, 1.28), (0.08, 0.22, 0.3), 'veh_steel_dark')
    bx(T, 0.30, 0.52, 2.50, 2.60, 0.95, 1.20, 'veh_steel_dark')
    T.box((0.42, 2.62, 1.12), (0.12, 0.06, 0.12), 'veh_dark')
    # ---- gun at the trunnion (pivot about X)
    GP = (0.0, 2.32, 1.35 + 0.82)
    G = M.node('_gun', 'apc_turret', GP); Lg = Loc(G, GP)
    Lg.cyl((0, 0, 0.30), (0, 0, 2.30), 0.042, 0.038, 10, 'veh_steel_dark', True)
    Lg.cyl((0, 0, 0.30), (0, 0, 1.25), 0.075, 0.07, 10, 'veh_metal', True)
    Lg.cyl((0, 0, 1.25), (0, 0, 1.31), 0.085, 0.06, 10, 'veh_steel_dark', False)
    Lg.cyl((0, 0, 2.10), (0, 0, 2.38), 0.062, 0.062, 8, 'veh_dark', True)
    Lg.cyl((-0.24, 0.0, 0.28), (-0.24, 0.0, 0.95), 0.02, 0.02, 6, 'veh_steel_dark', False)
    Lg.box((-0.24, 0.0, 0.40), (0.07, 0.07, 0.2), 'veh_steel_dark')
    Lg.box((0.26, -0.02, 0.12), (0.1, 0.16, 0.2), 'veh_can', bevel=0.01)
    M.empty('apc_muzzle', (GP[0], GP[1], GP[2] + 2.40), 'apc_gun', 'ARROWS')
    # mantlet + cheek plates: a child of the gun (pitch) node, so it elevates with the barrel
    S = M.node('_gun_mantlet', 'apc_gun', GP); Ls = Loc(S, GP)
    Ls.loft([[(-0.32, -0.20, 0.04), (0.32, -0.20, 0.04), (0.32, 0.20, 0.04), (-0.32, 0.20, 0.04)],
             [(-0.27, -0.16, 0.42), (0.27, -0.16, 0.42), (0.27, 0.16, 0.42), (-0.27, 0.16, 0.42)]], 'veh_paint', False, (True, True))
    for sx in (-1, 1): wing(S, sx * 0.30, sx * 0.52, GP[1] - 0.20, GP[1] + 0.20, GP[2] + 0.06, 0.03, 'veh_paint', fold=28, ch=0.08)
    M.empty('apc_seat_driver', (0.45, 1.20, 2.75)); M.empty('apc_seat_gunner', (0.0, 1.95, 1.2), 'apc_turret')
    k = 0
    for s in (1, -1):
        for z in (0.9, 0.1, -0.7, -1.5):
            M.empty('apc_seat_p%d' % k, (s * 0.72, 1.12, z)); k += 1
    M.empty('apc_exit_L', (1.95, 0.0, 0.0)); M.empty('apc_exit_R', (-1.95, 0.0, 0.0)); M.empty('apc_exit_rear', (0.0, 0.0, -4.6))
    return M


def track_loop(P, x0, x1, zf, zr, cy, ro, ri, mat, step=15):
    """Closed track band (outer radius ro, inner ri), centres at (zf, cy), (zr, cy)."""
    def loop(r):
        pts = []
        for a in range(-90, 91, step): pts.append((zf + r * math.cos(rad(a)), cy + r * math.sin(rad(a))))
        for a in range(90, 271, step): pts.append((zr + r * math.cos(rad(a)), cy + r * math.sin(rad(a))))
        return pts
    o = loop(ro); i = loop(ri); n = len(o); verts = []
    for (z, y) in o: verts.append((x0, y, z))
    for (z, y) in o: verts.append((x1, y, z))
    for (z, y) in i: verts.append((x1, y, z))
    for (z, y) in i: verts.append((x0, y, z))
    faces = []
    for q in range(4):
        for k in range(n): faces.append((q * n + k, q * n + (k + 1) % n, ((q + 1) % 4) * n + (k + 1) % n, ((q + 1) % 4) * n + k))
    P.add(verts, faces, mat, False)
    return o


def road_wheel(P, c, r, s):
    c = Vector(c)
    for dx in (-0.115, 0.055): P.cyl(c + V(dx, 0, 0), c + V(dx + 0.06, 0, 0), r, r, 14, 'veh_rubber', False)
    P.cyl(c + V(-0.07, 0, 0), c + V(0.07, 0, 0), r * 0.72, r * 0.72, 12, 'veh_metal', False)
    P.cyl(c + V(s * 0.07, 0, 0), c + V(s * 0.115, 0, 0), r * 0.30, r * 0.26, 8, 'veh_steel_dark', False)
    for k in range(5):
        a = 2 * PI * k / 5
        P.box(c + V(s * 0.075, r * 0.5 * math.cos(a), r * 0.5 * math.sin(a)), (0.02, 0.035, 0.035), 'veh_dark')


def light_tank():
    M = VM('light_tank'); B = M.body(); n = 'light_tank'
    TXc = 1.03; TWd = 0.38; CY = 0.382; ZF = 1.85; ZR = -1.85; RO = 0.34; RI = 0.31; WY = CY - RI + 0.29
    for sd, s in (('L', 1), ('R', -1)):
        x = s * TXc
        T = M.node('_track_%s' % sd, None, (x, CY, 0))
        outer = track_loop(T, x - TWd / 2, x + TWd / 2, ZF, ZR, CY, RO, RI, 'veh_steel_dark', 15)
        m = len(outer); pts = list(outer)
        seg = [math.hypot(pts[(k + 1) % m][0] - pts[k][0], pts[(k + 1) % m][1] - pts[k][1]) for k in range(m)]
        per = sum(seg); nl = int(per / 0.20); acc = [0.0]
        for k in range(m): acc.append(acc[-1] + seg[k])
        for j in range(nl):
            d = per * j / nl; k = 0
            while acc[k + 1] < d: k += 1
            f = (d - acc[k]) / max(seg[k], 1e-6); a = pts[k]; b = pts[(k + 1) % m]
            z = a[0] + (b[0] - a[0]) * f; y = a[1] + (b[1] - a[1]) * f
            tz, ty = b[0] - a[0], b[1] - a[1]; th = math.degrees(math.atan2(-ty, tz))
            nzv, nyv = -ty, tz; ln = math.hypot(nzv, nyv); nzv /= ln; nyv /= ln
            if z * nzv + (y - CY) * nyv < 0: nzv, nyv = -nzv, -nyv
            T.box((x, y + nyv * 0.012, z + nzv * 0.012), (TWd * 0.96, 0.03, 0.10), 'veh_steel_dark', rot=(th, 0, 0))
            T.box((x, y + nyv * 0.032, z + nzv * 0.032), (TWd * 0.5, 0.015, 0.06), 'veh_metal', rot=(th, 0, 0))
        for z in (-0.9, 0.0, 0.9): B.cyl((x - 0.07, 0.62, z), (x + 0.07, 0.62, z), 0.07, 0.07, 8, 'veh_rubber', False)
        for i in range(5):
            z = -1.2 + 0.6 * i
            Wd = M.node('_wheel_%s%d' % (sd, i + 1), None, (x, WY, z)); road_wheel(Wd, (x, WY, z), 0.29, s)
        Sp = M.node('_sprocket_%s' % sd, None, (x, CY, ZF)); c = Vector((x, CY, ZF))
        Sp.cyl(c + V(-0.08, 0, 0), c + V(0.08, 0, 0), 0.26, 0.26, 12, 'veh_metal', False)
        Sp.cyl(c + V(s * 0.08, 0, 0), c + V(s * 0.12, 0, 0), 0.10, 0.08, 8, 'veh_steel_dark', False)
        for k in range(12):
            a = 2 * PI * k / 12
            Sp.box(c + V(0, 0.285 * math.cos(a), 0.285 * math.sin(a)), (0.10, 0.07, 0.05), 'veh_steel_dark', rot=(math.degrees(a), 0, 0))
        Id = M.node('_idler_%s' % sd, None, (x, CY, ZR)); road_wheel(Id, Vector((x, CY, ZR)), 0.30, s)
    # ---- hull
    secs = [(2.55, 0.50, 0.66, 0.60, 0.52, 0.80, 1.05), (2.10, 0.66, 0.84, 0.82, 0.36, 0.78, 1.22), (1.45, 0.80, 0.88, 0.88, 0.32, 0.85, 1.27),
            (-1.85, 0.80, 0.88, 0.88, 0.32, 0.85, 1.27), (-2.40, 0.74, 0.84, 0.80, 0.40, 0.85, 1.14)]
    B.loft(hull_rings(secs), 'veh_paint', False, (True, True))
    for s in (-1, 1):
        xi, xo = s * 0.80, s * 1.28
        bx(B, xi, xo, 0.88, 0.93, -2.30, 1.95, 'veh_paint', 0.015)
        B.patch([[(xi, 0.93, 1.95), (xo, 0.93, 1.95)], [(xi, 0.85, 2.18), (xo, 0.85, 2.18)], [(xi, 0.67, 2.28), (xo, 0.67, 2.28)]], 'veh_paint', (0, 1, 1), False)
        B.patch([[(xi, 0.88, 1.95), (xo, 0.88, 1.95)], [(xi, 0.80, 2.18), (xo, 0.80, 2.18)], [(xi, 0.62, 2.28), (xo, 0.62, 2.28)]], 'veh_paint', (0, -1, -1), False)
        bx(B, s * 1.24, s * 1.28, 0.75, 0.93, -2.3, 1.95, 'veh_paint')
        B.box((s * 1.02, 1.03, -1.5), (0.34, 0.20, 0.7), 'veh_paint', bevel=0.02)
        B.box((s * 1.02, 1.02, 0.7), (0.34, 0.14, 0.5), 'veh_can', bevel=0.01)
        tube(B, (s * 1.20, 0.97, 1.5), (s * 1.20, 0.97, 0.7), 0.02, 'veh_steel_dark', 6)
        B.cyl((s * 0.62, 1.00, 2.40), (s * 0.62, 1.00, 2.48), 0.07, 0.07, 8, 'veh_dark', False)
        B.cyl((s * 0.62, 1.00, 2.48), (s * 0.62, 1.00, 2.52), 0.055, 0.055, 8, 'veh_light_white', False)
        tube(B, (s * 0.28, 0.58, 2.50), (s * 0.28, 0.58, 2.68), 0.04, 'veh_steel_dark', 6)
        taillight(B, (s * 0.7, 0.9, -2.41), 0.12, 0.08)
        B.cyl((s * 0.5, 1.1, -2.40), (s * 0.5, 1.1, -2.62), 0.07, 0.06, 8, 'veh_rust', True)
    bx(B, 0.30, 0.78, 1.22, 1.36, 1.62, 1.95, 'veh_paint', 0.02)
    bx(B, 0.34, 0.74, 1.34, 1.38, 1.66, 1.84, 'veh_steel_dark')
    B.patch([[(0.40, 1.29, 1.62), (0.68, 1.29, 1.62)], [(0.40, 1.34, 1.58), (0.68, 1.34, 1.58)]], 'veh_glass', (0, 0, 1), False)
    B.box((-0.45, 1.14, 2.26), (0.14, 0.14, 0.12), 'veh_dark'); B.cyl((-0.45, 1.14, 2.26), (-0.45, 1.14, 2.62), 0.016, 0.016, 6, 'veh_steel_dark', False)
    for k in range(6): bx(B, -0.55, 0.55, 1.27, 1.30, -2.2 + k * 0.17, -2.2 + k * 0.17 + 0.09, 'veh_dark')
    bx(B, -0.62, 0.62, 1.26, 1.28, -2.30, -1.20, 'veh_steel_dark')
    # ---- turret (about Y at the ring)
    TP = (0.0, 1.27, 0.12)
    T = M.node('_turret', None, TP)
    T.loft([ring_xz(1.27, 0, 0.12, 0.92, 1.05), ring_xz(1.50, 0, 0.10, 0.86, 1.00), ring_xz(1.78, 0, 0.04, 0.64, 0.78)], 'veh_paint', False, (True, True))
    T.cyl((0, 1.25, 0.12), (0, 1.32, 0.12), 1.0, 1.0, 16, 'veh_steel_dark', False)
    bx(T, -0.40, 0.40, 1.42, 1.80, 1.02, 1.22, 'veh_paint')
    bx(T, -0.14, 0.14, 1.52, 1.68, 1.22, 1.27, 'veh_dark')
    T.cyl((0.30, 1.78, -0.12), (0.30, 1.88, -0.12), 0.22, 0.22, 12, 'veh_paint', False)
    T.cyl((0.30, 1.88, -0.12), (0.30, 1.94, -0.12), 0.17, 0.17, 12, 'veh_steel_dark', False)
    T.box((0.30, 1.97, -0.22), (0.12, 0.04, 0.08), 'veh_dark')
    T.cyl((-0.34, 1.78, 0.32), (-0.34, 1.82, 0.32), 0.17, 0.17, 10, 'veh_paint', False)
    T.cyl((-0.34, 1.82, 0.32), (-0.34, 1.86, 0.32), 0.14, 0.14, 10, 'veh_steel_dark', False)
    for k in range(6):
        a = rad(k * 60 + 15); T.box((0.30 + 0.20 * math.cos(a), 1.90, -0.12 + 0.20 * math.sin(a)), (0.04, 0.05, 0.04), 'veh_glass')
    bx(T, 0.36, 0.60, 1.74, 1.86, 0.30, 0.52, 'veh_steel_dark')
    T.box((0.0, 1.62, -1.0), (1.1, 0.45, 0.34), 'veh_paint', bevel=0.03)
    for s in (-1, 1):
        for k in range(3):                                                  # smoke launchers (3 per side)
            zz = 0.40 - 0.14 * k
            T.sweep([(s * 0.86, 1.52, zz), (s * 0.97, 1.65, zz)], 0.035, 8, 'veh_steel_dark', True, (True, True))
            T.sweep([(s * 0.96, 1.64, zz), (s * 0.99, 1.67, zz)], 0.022, 8, 'veh_dark', False, (True, True))
        bx(T, s * 0.78, s * 0.82, 1.38, 1.60, 0.20, 0.64, 'veh_steel_dark')
    T.sweep([(-0.55, 1.75, -0.6), (-0.58, 2.3, -0.62), (-0.6, 2.9, -0.64)], [0.012, 0.009, 0.005], 5, 'veh_dark', False)
    # ---- barrel (about X at the trunnion)
    GP = (0.0, 1.62, 0.12 + 0.98)
    G = M.node('_barrel', 'light_tank_turret', GP); Lg = Loc(G, GP)
    Lg.cyl((0, 0, 0.2), (0, 0, 2.55), 0.052, 0.045, 10, 'veh_steel_dark', True)
    Lg.cyl((0, 0, 0.2), (0, 0, 0.55), 0.09, 0.08, 10, 'veh_metal', True)
    Lg.cyl((0, 0, 1.45), (0, 0, 1.75), 0.07, 0.07, 10, 'veh_metal', True)
    Lg.cyl((0, 0, 2.38), (0, 0, 2.62), 0.068, 0.068, 8, 'veh_dark', True)
    Lg.cyl((0.22, 0.0, 0.2), (0.22, 0.0, 0.85), 0.022, 0.022, 6, 'veh_steel_dark', False)
    Lg.box((0.22, 0.0, 0.35), (0.07, 0.07, 0.2), 'veh_steel_dark')
    M.empty('light_tank_muzzle', (GP[0], GP[1], GP[2] + 2.64), 'light_tank_barrel', 'ARROWS')
    # mantlet + gun shield cheeks: a child of the barrel (pitch) node, so it elevates with the barrel
    S = M.node('_barrel_mantlet', 'light_tank_barrel', GP); Ls = Loc(S, GP)
    Ls.loft([[(-0.34, -0.23, -0.06), (0.34, -0.23, -0.06), (0.34, 0.23, -0.06), (-0.34, 0.23, -0.06)],
             [(-0.29, -0.19, 0.30), (0.29, -0.19, 0.30), (0.29, 0.19, 0.30), (-0.29, 0.19, 0.30)]], 'veh_paint', False, (True, True))
    for sx in (-1, 1): wing(S, sx * 0.33, sx * 0.54, GP[1] - 0.23, GP[1] + 0.23, GP[2] + 0.03, 0.03, 'veh_paint', fold=30, ch=0.08)
    M.empty('light_tank_seat_driver', (0.5, 0.9, 1.55)); M.empty('light_tank_seat_gunner', (-0.34, 1.45, 0.32), 'light_tank_turret')
    M.empty('light_tank_seat_p0', (0.30, 1.50, -0.12), 'light_tank_turret'); M.empty('light_tank_seat_p1', (-0.5, 0.9, 1.55))
    M.empty('light_tank_exit_L', (1.8, 0.0, -0.2)); M.empty('light_tank_exit_R', (-1.8, 0.0, -0.2))
    return M
