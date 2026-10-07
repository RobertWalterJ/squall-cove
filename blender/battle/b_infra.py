"""Radio mast, radar station, searchlight tower, wooden watch tower, pumpjack, fuel depot."""
from b_lib import *


def radio_mast():
    M = Model('radio_mast'); B = M.part(); rng = random.Random(11)
    H = 30.0; NS = 12; dh = H / NS
    def Rr(y): return 1.5 - (1.5 - 0.55) * min(1.0, y / 26.0)
    def leg(k, y): a = rad(k * 120); r = Rr(y); return (r * math.sin(a), y, r * math.cos(a))
    # footing: triangular concrete pad + pier
    B.cyl((0, 0, 0), (0, 0.3, 0), 2.7, 2.7, 3, 'battle_concrete', False)
    for k in range(3):
        a = rad(k * 120); p = (1.5 * math.sin(a), 0.3, 1.5 * math.cos(a)); B.cyl(p, (p[0], 0.6, p[2]), 0.28, 0.28, 8, 'battle_concrete_dark', False)
    for i in range(NS):
        y0 = i * dh; y1 = y0 + dh
        for k in range(3):
            tube(B, leg(k, y0 + (0.5 if i == 0 else 0)), leg(k, y1), 0.12, 'battle_galv')
            k2 = (k + 1) % 3
            tube(B, leg(k, y1), leg(k2, y1), 0.06, 'battle_galv', caps=False)
            if (i + k) % 2 == 0: tube(B, leg(k, y0), leg(k2, y1), 0.05, 'battle_galv', caps=False)
            else: tube(B, leg(k2, y0), leg(k, y1), 0.05, 'battle_galv', caps=False)
    # platform at 21 m with dish; side arm antennas
    Rp = Rr(21.0)
    B.cyl((0, 20.6, 0), (0, 20.75, 0), Rp + 0.5, Rp + 0.5, 3, 'battle_steel_dark', False)
    zf = Rp + 0.75
    tube(B, (0, 21.0, Rp), (0, 21.0, zf - 0.1), 0.1, 'battle_steel_dark')
    tube(B, (0, 20.3, Rp), (0, 21.0, zf - 0.1), 0.06, 'battle_steel_dark', caps=False)
    dish(B, (0, 21.2, zf + 0.15), 0.95, 0.95, 0.45, 'battle_white', 'battle_galv', 9, 6, 0.1)
    tube(B, (0, 21.2, zf + 0.15 - 0.2), (0, 21.2, zf + 0.15 + 0.3), 0.04, 'battle_steel_dark')
    B.cyl((0, 21.2, zf + 0.15 + 0.3), (0, 21.2, zf + 0.15 + 0.55), 0.08, 0.05, 6, 'battle_black', False)
    # panel antennas on the upper section, facing each leg outward
    for k, y in ((0, 26.0), (1, 26.0), (2, 26.0), (1, 17.0), (2, 17.0)):
        a = rad(k * 120 + 60); r = Rr(y) + 0.1
        ybox(B, (r * math.sin(a), y, r * math.cos(a)), (0, 0, 0), (0.28, 1.25, 0.08), k * 120 + 60 - 0, 'battle_white')
    # top: whip + beacon
    B.cyl((0, 29.9, 0), (0, 31.5, 0), 0.05, 0.03, 6, 'battle_steel_dark', False)
    B.light((0, 30.0, 0), 0.22, 'battle_light_red')
    # ladder-like cable tray up the +Z leg
    tube(B, (0.0, 0.5, Rr(0) + 0.28), (0.0, 20.8, Rr(20.8) + 0.28), 0.14, 'battle_steel_dark')
    # guy wires
    for (y, ar) in ((10.0, 12.0), (20.0, 15.0), (29.0, 18.0)):
        for k in range(3):
            a = rad(k * 120 + 40)
            top = leg(k, y); bot = (ar * math.sin(a), 0.25, ar * math.cos(a))
            B.sweep([top, bot], 0.018, 3, 'battle_wire', False, (False, False))
    for k in range(3):
        a = rad(k * 120 + 40)
        for ar in (12.0, 15.0, 18.0):
            B.box((ar * math.sin(a), 0.2, ar * math.cos(a)), (0.5, 0.4, 0.5), 'battle_concrete')
    # equipment hut
    hx, hz = -5.0, -2.5
    ybox(B, (hx, 0, hz), (0, 1.2, 0), (3.2, 2.4, 2.6), 15, 'battle_olive')
    ybox(B, (hx, 0, hz), (0, 2.46, 0), (3.5, 0.14, 2.9), 15, 'battle_olive_dark')
    ybox(B, (hx, 0, hz), (0, 0.9, 1.31), (0.9, 1.8, 0.06), 15, 'battle_dark')      # door
    ybox(B, (hx, 0, hz), (1.1, 1.6, 1.31), (0.7, 0.5, 0.06), 15, 'battle_glass')
    ybox(B, (hx, 0, hz), (-1.9, 0.5, 0.2), (0.7, 0.9, 1.0), 15, 'battle_steel')       # AC unit
    ybox(B, (hx, 0, hz), (-1.9, 0.95, 0.2), (0.6, 0.04, 0.6), 15, 'battle_steel_dark')
    ybox(B, (hx, 0, hz), (0, 0.15, 1.75), (1.1, 0.3, 0.8), 15, 'battle_concrete')    # step
    ybox(B, (hx, 0, hz), (1.9, 0.2, -1.7), (0.5, 0.4, 0.5), 15, 'battle_olive_dark')   # generator tank
    tube(B, (hx + 1.0, 0.07, hz + 1.2), (1.0, 0.07, Rr(0) * 0.9), 0.22, 'battle_steel_dark')   # cable run
    # sandbag wall by hut
    bagline(B, (hx - 1.8, hz + 2.0), (hx + 1.0, hz + 2.7), 3, rng, rows=1)
    return M


def radar_station():
    M = Model('radar_station'); B = M.part(); rng = random.Random(5)
    # concrete apron
    B.box((0, 0.1, 0), (8.0, 0.2, 8.0), 'battle_concrete', bevel=0.03)
    def lg(sx, sz, y):
        t = 1.0 - 0.28 * (y / 9.0); return (sx * 1.7 * t, y, sz * 1.7 * t)
    for sx in (-1, 1):
        for sz in (-1, 1):
            tube(B, lg(sx, sz, 0.2), lg(sx, sz, 9.0), 0.24, 'battle_galv')
            B.box((sx * 1.7, 0.3, sz * 1.7), (0.7, 0.2, 0.7), 'battle_concrete_dark')
    lv = [0.2, 3.0, 6.0, 9.0]
    for a, b in zip(lv, lv[1:]):
        for (s1, z1, s2, z2) in ((1, 1, 1, -1), (1, -1, -1, -1), (-1, -1, -1, 1), (-1, 1, 1, 1)):
            tube(B, lg(s1, z1, a), lg(s2, z2, b), 0.1, 'battle_galv', caps=False)
            tube(B, lg(s2, z2, a), lg(s1, z1, b), 0.1, 'battle_galv', caps=False)
        for (s1, z1, s2, z2) in ((1, 1, 1, -1), (1, -1, -1, -1), (-1, -1, -1, 1), (-1, 1, 1, 1)):
            tube(B, lg(s1, z1, b), lg(s2, z2, b), 0.16, 'battle_steel')
    # platform and rails
    B.box((0, 9.1, 0), (4.4, 0.2, 4.4), 'battle_steel_dark')
    for sx in (-1, 1):
        for sz in (-1, 1): tube(B, (sx * 2.1, 9.2, sz * 2.1), (sx * 2.1, 10.2, sz * 2.1), 0.06, 'battle_steel')
    for (a, b) in (((-2.1, -2.1), (2.1, -2.1)), ((2.1, -2.1), (2.1, 2.1)), ((2.1, 2.1), (-2.1, 2.1)), ((-2.1, 2.1), (-2.1, -2.1))):
        tube(B, (a[0], 10.2, a[1]), (b[0], 10.2, b[1]), 0.05, 'battle_steel', caps=False)
        tube(B, (a[0], 9.7, a[1]), (b[0], 9.7, b[1]), 0.04, 'battle_steel', caps=False)
    # ladder on +Z face
    for sx in (-0.25, 0.25): tube(B, (sx, 0.2, 2.3), (sx, 9.2, 2.05), 0.06, 'battle_steel')
    for i in range(1, 29): y = 0.2 + i * 0.3; tube(B, (-0.25, y, 2.3 - 0.25 * (y / 9.0)), (0.25, y, 2.3 - 0.25 * (y / 9.0)), 0.04, 'battle_steel', caps=False)
    # equipment cabin on platform (left side) and pedestal
    B.box((-1.15, 10.1, -1.15), (1.5, 1.7, 1.5), 'battle_olive', bevel=0.03)
    B.box((-1.15, 11.0, -1.15), (1.65, 0.12, 1.65), 'battle_olive_dark')
    B.box((-1.15, 9.95, -0.37), (0.5, 1.2, 0.05), 'battle_dark')
    B.cyl((0.6, 9.2, 0.6), (0.6, 10.0, 0.6), 0.75, 0.62, 12, 'battle_steel', True)
    B.cyl((0.6, 10.0, 0.6), (0.6, 10.25, 0.6), 0.85, 0.85, 12, 'battle_steel_dark', False)
    # small ground cabin + generator
    B.box((5.2, 0.9, -3.0), (2.6, 1.6, 2.2), 'battle_olive', bevel=0.02)
    B.box((5.2, 1.76, -3.0), (2.9, 0.12, 2.5), 'battle_olive_dark')
    B.box((5.2, 0.8, -1.88), (0.8, 1.5, 0.05), 'battle_dark')
    B.cyl((-5.0, 0.4, -3.0), (-5.0, 1.0, -3.0), 0.5, 0.5, 10, 'battle_steel_dark', True)
    tube(B, (-4.4, 0.08, -3.0), (-1.2, 0.08, -0.3), 0.2, 'battle_black')
    # red beacon on cabin
    B.light((-1.15, 11.3, -1.15), 0.14, 'battle_light_red')
    # ---- rotating dish: pivot at its centre
    cy = 11.6; P = M.part('radar_dish', (0.6, cy, 0.6)); cx, cz = 0.6, 0.6
    P.cyl((cx, 10.25, cz), (cx, cy - 0.9, cz), 0.3, 0.3, 8, 'battle_steel', False)
    P.box((cx, cy - 0.95, cz), (1.0, 0.2, 1.0), 'battle_steel_dark')
    dish(P, (cx, cy, cz + 0.25), 3.0, 1.2, 0.9, 'battle_galv', 'battle_steel', 12, 6, 0.14)
    for sx in (-1, 1):
        tube(P, (cx + sx * 0.6, cy - 0.9, cz), (cx + sx * 0.6, cy + 0.6, cz - 0.15), 0.12, 'battle_steel_dark')
    tube(P, (cx - 2.2, cy, cz - 0.1), (cx + 2.2, cy, cz - 0.1), 0.14, 'battle_steel_dark')
    tube(P, (cx, cy + 1.0, cz - 0.1), (cx, cy - 0.9, cz - 0.1), 0.14, 'battle_steel_dark')
    # feed horn on struts
    fz = cz + 0.25 + 0.9 * 0.5 + 0.5
    for dx, dy in ((-1.6, 0.0), (1.6, 0.0), (0.0, 0.8), (0.0, -0.8)):
        tube(P, (cx + dx, cy + dy, cz + 0.25 + 0.9 * ((dx / 3) ** 2 + (dy / 1.2) ** 2) - 0.45), (cx, cy, fz - 0.1), 0.05, 'battle_steel_dark', caps=False)
    P.box((cx, cy, fz), (0.35, 0.28, 0.4), 'battle_steel')
    P.light((cx, cy + 1.3, cz - 0.1), 0.1, 'battle_light_red')
    return M


def searchlight_tower():
    M = Model('searchlight_tower'); B = M.part(); rng = random.Random(3)
    B.box((0, 0.12, 0), (3.2, 0.24, 3.2), 'battle_concrete', bevel=0.02)
    def lg(sx, sz, y):
        t = 1.0 - 0.3 * (y / 5.6); return (sx * 1.0 * t, y, sz * 1.0 * t)
    for sx in (-1, 1):
        for sz in (-1, 1): tube(B, lg(sx, sz, 0.2), lg(sx, sz, 5.6), 0.14, 'battle_steel')
    lv = [0.2, 1.9, 3.7, 5.6]
    for a, b in zip(lv, lv[1:]):
        for (s1, z1, s2, z2) in ((1, 1, 1, -1), (1, -1, -1, -1), (-1, -1, -1, 1), (-1, 1, 1, 1)):
            tube(B, lg(s1, z1, a), lg(s2, z2, b), 0.06, 'battle_steel', caps=False)
            tube(B, lg(s2, z2, a), lg(s1, z1, b), 0.06, 'battle_steel', caps=False)
            tube(B, lg(s1, z1, b), lg(s2, z2, b), 0.09, 'battle_steel')
    B.box((0, 5.7, 0), (2.0, 0.14, 2.0), 'battle_wood_dark')
    for sx in (-1, 1):
        for sz in (-1, 1): tube(B, (sx * 0.95, 5.77, sz * 0.95), (sx * 0.95, 6.5, sz * 0.95), 0.05, 'battle_steel')
    for (a, b) in (((-0.95, -0.95), (0.95, -0.95)), ((0.95, -0.95), (0.95, 0.95)), ((0.95, 0.95), (-0.95, 0.95)), ((-0.95, 0.95), (-0.95, -0.95))):
        tube(B, (a[0], 6.5, a[1]), (b[0], 6.5, b[1]), 0.05, 'battle_steel', caps=False)
    for sx in (-0.2, 0.2): tube(B, (sx, 0.2, 1.1), (sx, 5.7, 0.8), 0.05, 'battle_steel')
    for i in range(1, 18): y = 0.2 + i * 0.3; z = 1.1 - 0.3 * (y - 0.2) / 5.5; tube(B, (-0.2, y, z), (0.2, y, z), 0.035, 'battle_steel', caps=False)
    # yoke
    B.cyl((0, 5.78, 0), (0, 6.15, 0), 0.4, 0.34, 10, 'battle_steel_dark', True)
    for sx in (-1, 1): B.box((sx * 0.72, 6.55, 0.0), (0.12, 0.9, 0.34), 'battle_steel_dark')
    B.box((0, 6.2, 0), (1.6, 0.14, 0.34), 'battle_steel_dark')
    # generator & cable
    B.box((2.0, 0.45, -1.2), (1.2, 0.8, 0.8), 'battle_olive', bevel=0.02); B.box((2.0, 0.9, -1.2), (1.0, 0.05, 0.6), 'battle_steel_dark')
    tube(B, (1.6, 0.07, -0.8), (0.8, 0.07, -0.7), 0.1, 'battle_black', caps=False)
    bagline(B, (-1.6, 1.9), (1.6, 1.9), 2, rng)
    # lamp: pivot at the lamp centre, beam along +Z
    cy = 6.55; L_ = M.part('searchlight_lamp', (0, cy, 0))
    L_.cyl((0, cy, -0.62), (0, cy, 0.42), 0.46, 0.5, 12, 'battle_olive', True, (True, False))
    L_.cyl((0, cy, 0.42), (0, cy, 0.56), 0.54, 0.54, 12, 'battle_steel_dark', False, (True, True))
    L_.cyl((0, cy, 0.56), (0, cy, 0.585), 0.44, 0.44, 12, 'battle_lens', False, (True, True))
    L_.cyl((0, cy, -0.62), (0, cy, -0.9), 0.46, 0.2, 12, 'battle_steel_dark', True)
    L_.cyl((-0.66, cy, 0), (0.66, cy, 0), 0.07, 0.07, 6, 'battle_steel', False)
    for k in range(4): L_.box((0, cy + 0.52, -0.3 + k * 0.18), (0.26, 0.06, 0.07), 'battle_steel_dark')
    L_.box((0, cy + 0.55, 0.0), (0.06, 0.1, 0.5), 'battle_steel_dark')
    return M


def watch_tower_wood():
    M = Model('watch_tower_wood'); B = M.part(); rng = random.Random(8)
    HY = 6.4
    def lg(sx, sz, y): t = 1.0 - 0.3 * (y / HY); return (sx * 1.35 * t, y, sz * 1.35 * t)
    for sx in (-1, 1):
        for sz in (-1, 1):
            tube(B, lg(sx, sz, 0.0), lg(sx, sz, HY + 0.1), 0.22, 'battle_wood')
            B.box((sx * 1.35, 0.06, sz * 1.35), (0.5, 0.12, 0.5), 'battle_earth_dark')
    lv = [0.0, 2.1, 4.2, HY]
    for a, b in zip(lv, lv[1:]):
        sides = ((1, 1, 1, -1), (1, -1, -1, -1), (-1, -1, -1, 1), (-1, 1, 1, 1))
        for (s1, z1, s2, z2) in sides:
            tube(B, lg(s1, z1, a + 0.1), lg(s2, z2, b - 0.1), 0.1, 'battle_wood_light')
            tube(B, lg(s2, z2, a + 0.1), lg(s1, z1, b - 0.1), 0.1, 'battle_wood_light')
            tube(B, lg(s1, z1, b), lg(s2, z2, b), 0.14, 'battle_wood_dark')
    # platform deck + walkway
    B.box((0, HY + 0.1, 0), (3.0, 0.16, 3.0), 'battle_wood_light')
    for k in range(-5, 6): B.box((k * 0.27, HY + 0.185, 0), (0.02, 0.01, 3.0), 'battle_wood_dark')
    # cabin: corner posts, half walls with open slots, roof
    cb = HY + 0.18; c = 1.0
    for sx in (-1, 1):
        for sz in (-1, 1): tube(B, (sx * c, cb, sz * c), (sx * c, cb + 1.4, sz * c), 0.14, 'battle_wood')
    for (x0, z0, x1, z1) in ((-c, -c, c, -c), (-c, c, c, c)):
        B.box(((x0 + x1) / 2, cb + 0.4, z0), (2.0, 0.8, 0.1), 'battle_wood_light')
        B.box(((x0 + x1) / 2, cb + 1.3, z0), (2.0, 0.14, 0.12), 'battle_wood_dark')
    for sx in (-1, 1):
        B.box((sx * c, cb + 0.4, 0), (0.1, 0.8, 2.0), 'battle_wood_light')
        B.box((sx * c, cb + 1.3, 0), (0.12, 0.14, 2.0), 'battle_wood_dark')
    for k in (-0.5, 0.5): B.box((k * 1.6 * 0.6, cb + 0.82, -c), (0.04, 0.5, 0.12), 'battle_wood_dark')
    blk(B, -1.8, 1.8, -1.9, 1.9, cb + 1.4, cb + 1.95, 'battle_wood_dark', ins=(0.8, 0.8, 1.7, 1.7))
    blk(B, -1.65, 1.65, -1.75, 1.75, cb + 1.37, cb + 1.45, 'battle_galv', ins=(0, 0, 0, 0))
    # walkway rail
    HR = HY + 0.18 + 0.95
    for sx in (-1, 1):
        for sz in (-1, 1): tube(B, (sx * 1.45, HY + 0.18, sz * 1.45), (sx * 1.45, HR, sz * 1.45), 0.07, 'battle_wood')
    for (a, b) in (((-1.45, -1.45), (1.45, -1.45)), ((1.45, -1.45), (1.45, 1.45)), ((-1.45, 1.45), (-1.45, -1.45))):
        tube(B, (a[0], HR, a[1]), (b[0], HR, b[1]), 0.06, 'battle_wood', caps=False)
        tube(B, (a[0], HR - 0.4, a[1]), (b[0], HR - 0.4, b[1]), 0.05, 'battle_wood', caps=False)
    tube(B, (-1.45, HR, 1.45), (-0.4, HR, 1.45), 0.06, 'battle_wood', caps=False); tube(B, (0.4, HR, 1.45), (1.45, HR, 1.45), 0.06, 'battle_wood', caps=False)
    # ladder (+Z), from ground out front to the deck opening
    z0, z1 = 2.2, 1.3
    for sx in (-0.28, 0.28): tube(B, (sx, 0.0, z0), (sx, HY + 0.2, z1), 0.09, 'battle_wood')
    n = 21
    for i in range(1, n):
        t = i / n; tube(B, (-0.28, t * (HY + 0.2), z0 + (z1 - z0) * t), (0.28, t * (HY + 0.2), z0 + (z1 - z0) * t), 0.055, 'battle_wood_light', caps=False)
    # sandbags at the base
    bagline(B, (-1.5, 2.0 + 0.9), (-0.7, 2.9), 2, rng)
    return M


def oil_pumpjack():
    M = Model('oil_pumpjack'); B = M.part(); rng = random.Random(2)
    # skid base
    for sx in (-0.55, 0.55): B.box((sx, 0.15, -0.3), (0.28, 0.3, 8.8), 'battle_steel_dark')
    for z in (-4.2, -2.4, 0.0, 2.4, 3.9): B.box((0, 0.15, z), (1.4, 0.2, 0.25), 'battle_steel_dark')
    B.box((0, 0.1, -0.3), (2.4, 0.1, 9.4), 'battle_concrete')    # pad under
    # samson post
    py = 4.5
    for sx in (-0.45, 0.45):
        tube(B, (sx, 0.3, -1.5), (sx, py - 0.05, -0.12), 0.18, 'battle_rust')
        tube(B, (sx, 0.3, 1.4), (sx, py - 0.05, 0.12), 0.18, 'battle_rust')
    tube(B, (-0.5, 2.2, -0.9), (0.5, 2.2, -0.9), 0.1, 'battle_rust', caps=False); tube(B, (-0.5, 2.2, 0.9), (0.5, 2.2, 0.9), 0.1, 'battle_rust', caps=False)
    B.box((0, py - 0.15, 0), (1.2, 0.3, 0.5), 'battle_steel_dark')        # saddle bearing
    B.cyl((-0.65, py, 0), (0.65, py, 0), 0.14, 0.14, 8, 'battle_steel', False)
    # gearbox, crank and counterweights, motor
    B.box((0, 0.95, -2.6), (1.0, 1.2, 1.3), 'battle_olive', bevel=0.03)
    for sx in (-1, 1):
        B.cyl((sx * 0.62, 1.3, -2.6), (sx * 0.68, 1.3, -2.6), 0.9, 0.9, 12, 'battle_rust', False)
        B.box((sx * 0.7, 1.9, -2.6), (0.12, 0.6, 0.9), 'battle_steel_dark')
    B.cyl((-0.75, 1.3, -2.6), (0.75, 1.3, -2.6), 0.1, 0.1, 6, 'battle_steel', False)
    B.box((0, 0.65, -4.1), (0.7, 0.7, 1.1), 'battle_olive_dark', bevel=0.03)
    tube(B, (0.45, 0.7, -3.7), (0.45, 1.1, -2.75), 0.06, 'battle_black', caps=False); tube(B, (-0.45, 0.7, -3.7), (-0.45, 1.1, -2.75), 0.06, 'battle_black', caps=False)
    B.box((0, 1.0, -3.3), (1.0, 0.7, 0.1), 'battle_steel_dark')
    # wellhead
    wz = 3.3
    B.cyl((0, 0.0, wz), (0, 0.9, wz), 0.14, 0.14, 8, 'battle_steel', True)
    B.cyl((0, 0.35, wz), (0, 0.42, wz), 0.28, 0.28, 8, 'battle_steel_dark', False)
    B.cyl((-0.4, 0.7, wz), (0.4, 0.7, wz), 0.07, 0.07, 6, 'battle_steel', False)
    B.cyl((0.4, 0.7, wz), (0.4, 1.0, wz), 0.07, 0.07, 6, 'battle_rust', False)
    for k in (-1, 1): B.cyl((k * 0.4, 0.82, wz), (k * 0.4, 0.88, wz), 0.14, 0.14, 8, 'battle_red', False)
    B.sweep([(0.45, 0.3, wz + 0.02), (0.45, 0.2, wz + 2.0)], 0.07, 6, 'battle_rust', True)
    B.cyl((0, 0.9, wz), (0, 2.5, wz), 0.035, 0.035, 6, 'battle_steel', False)
    B.cyl((0, 0.9, wz), (0, 1.3, wz), 0.1, 0.1, 8, 'battle_steel', True)
    # tank and pipe by the pad
    B.cyl((1.9, 0.0, 1.0), (1.9, 1.5, 1.0), 0.8, 0.8, 12, 'battle_rust', True); B.cyl((1.9, 1.5, 1.0), (1.9, 1.7, 1.0), 0.5, 0.2, 12, 'battle_steel_dark', False)
    B.sweep([(0.5, 0.2, wz + 2.0), (1.9, 0.2, 2.2), (1.9, 0.3, 1.5)], 0.07, 6, 'battle_rust', True)
    # ---- walking beam + horsehead (pivot at the samson saddle)
    H = M.part('pump_head', (0, py, 0))
    H.box((0, py + 0.02, -0.15), (0.3, 0.5, 6.1), 'battle_olive')
    for sx in (-1, 1): H.box((sx * 0.17, py + 0.02, -0.15), (0.05, 0.36, 6.0), 'battle_olive_dark')
    H.box((0, py - 0.1, 0.0), (0.9, 0.4, 0.5), 'battle_steel_dark')
    R = 3.25; path = []
    for k in range(8):
        a = rad(42 + k * 7.2); path.append((0, py + R * math.cos(a) - 0.0, R * math.sin(a)))
    H.sweep(path, 0.17, 4, 'battle_olive', False, (True, True), phase=PI / 4)
    H.box((0, py + 0.25, 2.4), (0.34, 0.1, 1.0), 'battle_olive_dark')
    # carrier bar + cables at rest
    for sx in (-0.18, 0.18): H.sweep([(sx, py + R * math.cos(rad(92)) + 0.0, R * math.sin(rad(92))), (sx, 2.55, 3.3)], 0.018, 3, 'battle_wire', False, (False, False))
    H.box((0, 2.5, 3.3), (0.6, 0.08, 0.14), 'battle_steel_dark')
    H.box((0, py + 0.05, -3.25), (0.55, 0.9, 0.5), 'battle_rust')     # counterweight block at the rear tip
    return M


def fuel_depot():
    M = Model('fuel_depot'); B = M.part(); rng = random.Random(4)
    X = 10.0; Z = 5.0; T = 0.5; HW = 0.95
    B.box((0, 0.04, 0), (2 * X, 0.08, 2 * Z), 'battle_earth_dark')
    # bund wall (concrete) with two step crossings
    for (cx, cz, sx, sz) in ((0, -Z + T / 2, 2 * X, T), (0, Z - T / 2, 2 * X, T), (-X + T / 2, 0, T, 2 * Z - 2 * T), (X - T / 2, 0, T, 2 * Z - 2 * T)):
        B.box((cx, HW / 2, cz), (sx, HW, sz), 'battle_concrete')
        B.box((cx, HW + 0.05, cz), (sx + 0.1 if sx > sz else sx + 0.14, 0.1, sz + 0.14 if sx > sz else sz), 'battle_concrete_dark')
    for k in range(4):
        B.box((7.5, 0.1 + k * 0.22, Z + 0.3 + (3 - k) * 0.28 - 0.0), (1.2, 0.2, 0.28), 'battle_concrete_dark')
        B.box((7.5, 0.1 + k * 0.22, Z - 0.4 - 0.28 * k - 0.35 + 0.0), (1.2, 0.2, 0.28), 'battle_concrete_dark')
    # tanks
    tz = -0.6
    for i, tx in enumerate((-5.6, 0.0, 5.6)):
        r = 2.0; h = 4.6
        B.cyl((tx, 0.0, tz), (tx, 0.25, tz), r + 0.2, r + 0.2, 16, 'battle_concrete', False)
        B.cyl((tx, 0.25, tz), (tx, h, tz), r, r, 16, 'battle_galv' if i != 1 else 'battle_olive', True, (False, False))
        B.cyl((tx, h * 0.5 - 0.1, tz), (tx, h * 0.5 + 0.1, tz), r + 0.025, r + 0.025, 16, 'battle_red', False, (False, False))
        B.cyl((tx, h, tz), (tx, h + 0.5, tz), r, 0.45, 16, 'battle_steel', True, (False, True))
        B.cyl((tx, h + 0.5, tz), (tx, h + 0.7, tz), 0.28, 0.28, 8, 'battle_steel_dark', False)
        # ladder up the front
        for sx in (-0.2, 0.2): tube(B, (tx + sx, 0.25, tz + r + 0.12), (tx + sx, h - 0.1, tz + r + 0.12), 0.05, 'battle_steel_dark')
        for j in range(1, 14): y = 0.25 + j * 0.32; tube(B, (tx - 0.2, y, tz + r + 0.12), (tx + 0.2, y, tz + r + 0.12), 0.035, 'battle_steel_dark', caps=False)
        # outlet riser, valve and manifold stub
        B.sweep([(tx, 0.55, tz + r - 0.05), (tx, 0.55, tz + r + 0.5), (tx, 0.4, tz + 1.6 + r - 0.0 - 1.0 + 0.0)], 0.12, 8, 'battle_steel', True)
        B.cyl((tx - 0.0, 0.55, tz + r + 0.55), (tx, 0.55 + 0.35, tz + r + 0.55), 0.04, 0.04, 6, 'battle_steel_dark', False)
        B.cyl((tx - 0.2, 0.9, tz + r + 0.55), (tx + 0.2, 0.9, tz + r + 0.55), 0.14, 0.14, 8, 'battle_red', False)
    # ground manifold along x, with cross pipes
    mz = tz + 2.0 + 1.25
    B.cyl((-6.0, 0.3, mz), (7.0, 0.3, mz), 0.14, 0.14, 8, 'battle_steel', True)
    for tx in (-5.6, 0.0, 5.6): B.cyl((tx, 0.3, mz), (tx, 0.3, tz + 2.55), 0.12, 0.12, 8, 'battle_steel', True)
    for x in (-3.0, 3.0): B.box((x, 0.12, mz), (0.2, 0.24, 0.5), 'battle_concrete_dark')
    # pump kiosk + hose reel
    B.box((8.1, 1.0, -2.3), (2.2, 2.0, 2.0), 'battle_olive', bevel=0.03); B.box((8.1, 2.05, -2.3), (2.5, 0.12, 2.3), 'battle_olive_dark')
    B.box((8.1, 0.9, -1.28), (0.8, 1.7, 0.05), 'battle_dark')
    B.cyl((7.2, 0.85, 0.5), (7.2, 0.85, 0.75), 0.4, 0.4, 12, 'battle_red', False)
    B.sweep([(6.4, 0.3, mz), (7.4, 0.35, 1.3), (8.0, 0.4, -1.0)], 0.1, 6, 'battle_steel', True)
    # drums by the kiosk, sandbags at the gap
    for i, (dx, dz) in enumerate(((-8.6, 2.6), (-8.0, 2.9), (-8.0, 2.2), (-8.6, 2.0))):
        drum(B, (dx, 0, dz), ['battle_drum_green', 'battle_drum_red', 'battle_drum_blue', 'battle_drum_green'][i])
    return M
