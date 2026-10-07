"""AH-1 Cobra style: narrow tandem-cockpit attack helicopter, chin turret, stub wings with rocket pods, two-blade rotor."""
from heli_parts import *

def rocket_pod(P, x, y, z0, z1, r, mat, mat_dark):
    P.sweep([(x, y, z0), (x, y, z0 + 0.12), (x, y, z1 - 0.12), (x, y, z1)], [r * 0.45, r, r, r * 0.97], 10, mat, True)
    P.sweep([(x, y, z1), (x, y, z1 + 0.04)], [r * 0.97, r * 0.97], 10, mat_dark, False, caps=(False, True))
    P.disc((x, y, z1 + 0.045), 0.0001, mat_dark, 3) if False else None
    pts = [(0, 0)] + [(r * 0.62 * math.cos(2 * PI * k / 6), r * 0.62 * math.sin(2 * PI * k / 6)) for k in range(6)]
    for (a, b) in pts:
        P.cyl((x + a, y + b, z1), (x + a, y + b, z1 + 0.07), r * 0.22, r * 0.2, 5, mat_dark, False)
    P.cyl((x, y + r * 0.0, z0 + 0.28), (x, y, z0 + 0.34), r * 1.04, r * 1.04, 10, mat_dark, False)         # band

def build():
    M = Model('cobra')
    od = defmat('cobra_olive', '#4a5232', 0.82, 0.04)
    od2 = defmat('cobra_olive_dark', '#3a4127', 0.85, 0.04)
    g = 'heli_glass'; blk = 'heli_black'; ln = 'heli_panel_line'
    B = M.part('_body')
    keys = [(4.0, .10, 1.00, .78, 2.0), (3.6, .30, 1.20, .64, 2.2), (2.8, .42, 1.50, .58, 2.6), (1.7, .48, 1.62, .55, 2.6),
            (0.6, .50, 1.72, .56, 2.8), (-0.5, .52, 2.10, .58, 3.0), (-1.5, .54, 2.25, .60, 3.0), (-2.6, .50, 2.15, .70, 2.8),
            (-3.4, .38, 1.95, .95, 2.5), (-4.8, .25, 1.82, 1.20, 2.3), (-7.0, .17, 1.78, 1.40, 2.2), (-8.8, .12, 1.85, 1.50, 2.2),
            (-9.1, .10, 1.9, 1.55, 2.2)]
    H = Hull(keys, [], spacing=0.7, nlev=9)
    H.build(B, od.name)
    # engine bays: intake, panel lines, access doors
    H.panel(B, 0, -0.55, 0.15, 0.30, 0.78, 0.012, blk, 2, 2)
    H.frame(B, 0, -1.9, -0.7, -0.45, 0.45, 0.02, 0.012, ln, 3)
    H.frame(B, 0, 0.5, 1.9, -0.6, 0.3, 0.02, 0.012, ln, 3)
    H.frame(B, 0, 2.0, 3.0, -0.4, 0.2, 0.02, 0.012, ln, 3)
    for z in (-4.5, -6.2, -7.8):
        H.band(B, z, z + 0.025, 0.008, ln, 1)
    for k in range(4):
        z = -0.9 - k * 0.18; H.patch(B, H.roofseq(0.86, 2), z, z + 0.06, 0.012, blk, 1)
    B.cyl((0, 2.0, -2.8), (0, 1.95, -3.25), 0.17, 0.11, 8, 'heli_steel_dark')
    B.cyl((0, 1.95, -3.25), (0, 1.94, -3.3), 0.11, 0.07, 8, blk)
    # canopies (glass shells) with framing and cockpit furniture
    fc = [(3.50, .08, 1.30, 1.18, 2.0), (3.2, .30, 1.74, 1.28, 2.2), (2.5, .38, 1.98, 1.42, 2.4), (1.9, .36, 1.98, 1.48, 2.4), (1.6, .30, 1.70, 1.5, 2.2)]
    FC = Hull(fc, [], spacing=0.45, nlev=7); FC.build(B, g, smooth=True)
    rc = [(1.6, .30, 1.8, 1.5, 2.2), (1.3, .38, 2.32, 1.58, 2.4), (0.6, .42, 2.5, 1.65, 2.4), (-0.1, .36, 2.45, 1.75, 2.4), (-0.7, .22, 2.28, 1.85, 2.2), (-1.0, .08, 2.15, 1.9, 2.0)]
    RC = Hull(rc, [], spacing=0.45, nlev=7); RC.build(B, g, smooth=True)
    for z in (2.9, 2.2):
        FC.band(B, z, z + 0.05, 0.012, od.name, 1)
    for z in (1.0, 0.2):
        RC.band(B, z, z + 0.05, 0.012, od.name, 1)
    FC.panel(B, 0, 1.6, 3.4, 0.0, 0.0, 0.0, od.name, 1, 1) if False else None
    B.box((0, 1.58, 3.1), (0.5, 0.2, 0.32), blk, rot=(-20, 0, 0), bevel=0.03)                   # gunner coaming / sight
    B.box((0, 1.52, 1.78), (0.5, 0.3, 0.12), blk, bevel=0.02)                                    # bulkhead between cockpits
    B.box((0, 1.78, 1.52), (0.52, 0.5, 0.12), blk, bevel=0.02)
    seat_bucket(B, (0, 1.58, 2.35), 'heli_seat', 1, 0.42, 0.44, 0.55)
    seat_bucket(B, (0, 1.80, 0.55), 'heli_seat', 1, 0.42, 0.44, 0.55)
    B.ellipsoid((0, 2.12, 2.2), (0.11, 0.13, 0.14), 'heli_seat', 8, 5)                           # gunner helmet
    B.ellipsoid((0, 2.35, 0.45), (0.11, 0.13, 0.14), 'heli_seat', 8, 5)                          # pilot helmet
    # tail
    B.prism([(-7.7, 1.8), (-8.7, 3.55), (-9.35, 3.6), (-9.45, 1.85)], (0, 0, 0), (0, 0, 1), (0, 1, 0), 0.09, od.name, 0.82)
    B.prism([(-8.9, 1.62), (-9.5, 1.62), (-9.5, 1.0), (-9.25, 0.95)], (0, 0, 0), (0, 0, 1), (0, 1, 0), 0.06, od.name, 0.8)
    B.prism([(0.28, -1.15), (-0.28, -1.15), (-0.28, 1.15), (0.28, 1.15)], (0, 1.62, -8.3), (0, 0, 1), (1, 0, 0), 0.045, od.name, 0.8)
    # stub wings, pylons, rocket pods
    B.prism([(0.30, -1.85), (0.42, -0.45), (0.42, 0.45), (0.30, 1.85), (-0.32, 1.85), (-0.45, 0.45), (-0.45, -0.45), (-0.32, -1.85)], (0, 1.02, 0.1), (0, 0, 1), (1, 0, 0), 0.1, od2.name, 0.82)
    for sx in (1, -1):
        for px in (0.85, 1.5):
            B.box((sx * px, 0.88, 0.2), (0.07, 0.3, 0.6), 'heli_steel_dark', bevel=0.012)
            rocket_pod(B, sx * px, 0.66, -0.55, 1.0, 0.19, od2.name, blk)
    # mast area (hub on the hump)
    B.cyl((0, 2.15, -0.9), (0, 2.95, -0.9), 0.14, 0.1, 10, 'heli_steel_dark')
    B.cyl((0, 2.82, -0.9), (0, 2.9, -0.9), 0.26, 0.26, 12, 'heli_metal')
    # skids
    skid_gear(B, 0.95, 1.9, -2.0, 0.9, 0.5, 0.05, 'heli_steel_dark', cross=(0.9, -1.2), belly=lambda z: 0.6, seg=6)
    B.cyl((0, 0.55, 3.3), (0, 0.55, 3.3), 0.001, 0.001, 3, blk) if False else None
    B.cyl((0, 1.2, 3.9), (0, 1.2, 4.25), 0.012, 0.01, 4, 'heli_metal')                         # pitot
    # chin turret: own pivot, barrels along +z
    tp = V(0, 0.62, 3.2)
    TU = M.part('_turret', tp)
    TU.ellipsoid(tp + V(0, -0.02, 0.0), (0.26, 0.2, 0.32), od2.name, 10, 6)
    TU.box(tp + V(0, 0.12, -0.05), (0.3, 0.12, 0.4), 'heli_steel_dark', bevel=0.02)
    TU.cyl(tp + V(0, -0.02, 0.2), tp + V(0, -0.02, 0.5), 0.1, 0.1, 8, 'heli_steel_dark')
    for k in range(3):
        a = 2 * PI * k / 3 + PI / 2
        yo, xo = 0.04 * math.sin(a), 0.04 * math.cos(a)
        TU.cyl(tp + V(xo, -0.02 + yo, 0.45), tp + V(xo, -0.02 + yo, 1.1), 0.014, 0.012, 5, 'heli_metal', True)
    TU.cyl(tp + V(0, -0.02, 1.0), tp + V(0, -0.02, 1.06), 0.07, 0.07, 8, 'heli_steel_dark')
    NL = M.part('_navlights')
    NL.light((0.46, 1.1, 2.9), 0.05, 'heli_light_red'); NL.light((-0.46, 1.1, 2.9), 0.05, 'heli_light_green')
    NL.light((0, 3.66, -9.4), 0.05, 'heli_light_white'); NL.light((0, 1.78, -5.5), 0.05, 'heli_light_red')
    NL.light((1.88, 1.02, 0.1), 0.05, 'heli_light_red'); NL.light((-1.88, 1.02, 0.1), 0.05, 'heli_light_green')
    hub = V(0, 3.05, -0.9)
    R = M.part('_mainrotor', hub)
    mast_head(R, hub, 2, 6.7, 0.69, 0.06, 'heli_steel_dark', 'heli_blade', root=0.7, pitch=5.0, cone=0.3)
    R.cyl(hub + V(0, -0.1, -1.1), hub + V(0, -0.1, 1.1), 0.03, 0.03, 6, 'heli_steel_dark')
    for sz in (1, -1):
        R.box(hub + V(0, -0.1, sz * 1.0), (0.14, 0.04, 0.5), 'heli_steel_dark', bevel=0.01)
    R.cyl(hub + V(0, -0.16, 0), hub + V(0, -0.1, 0), 0.22, 0.22, 12, 'heli_metal')
    BL = M.part('_rotor_blur', hub); BL.disc(hub + V(0, 0.12, 0), 6.7, 'heli_rotor_blur', 44)
    th = V(0.2, 2.75, -9.0)
    T = M.part('_tailrotor', th)
    T.cyl(th + V(-0.05, 0, 0), th + V(0.1, 0, 0), 0.075, 0.06, 8, 'heli_steel_dark')
    for a in (PI / 2, 3 * PI / 2):
        d = V(0, math.cos(a), math.sin(a))
        T.blade(th + V(0.05, 0, 0), d, V(1, 0, 0), 0.08, 1.4, 0.2, 0.18, 0.026, 14.0, 'heli_blade', nst=3, taper_tip=False)
    TB = M.part('_tailrotor_blur', th); TB.disc(th + V(0.05, 0, 0), 1.4, 'heli_rotor_blur', 24, axis='x')
    M.seat((0, 1.65, 2.35)); M.seat((0, 1.87, 0.55))
    return M
