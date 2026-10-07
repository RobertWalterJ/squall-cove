"""UH-60 Black Hawk style: four-blade rotor, stabilator, wheeled gear with tail wheel, two door guns."""
from heli_parts import *

def wheel(P, x, y, z, r, w):
    P.cyl((x - w / 2, y, z), (x + w / 2, y, z), r, r, 14, 'heli_rubber', True)
    P.cyl((x - w / 2 - 0.01, y, z), (x + w / 2 + 0.01, y, z), r * 0.55, r * 0.55, 10, 'heli_metal', False)

def build():
    M = Model('blackhawk')
    od = defmat('blackhawk_olive', '#3f4733', 0.8, 0.05)
    od2 = defmat('blackhawk_olive_dark', '#32392a', 0.85, 0.05)
    g = 'heli_glass'; blk = 'heli_black'; ln = 'heli_panel_line'
    B = M.part('_body')
    keys = [(5.00, .10, 1.75, 1.15, 2.0), (4.55, .55, 2.1, .98, 2.1), (3.6, 1.00, 2.7, .88, 2.5), (2.5, 1.15, 2.95, .85, 3.0),
            (1.0, 1.20, 3.05, .85, 3.4), (-0.5, 1.22, 3.1, .85, 3.6), (-2.5, 1.15, 3.05, .90, 3.2), (-3.6, .95, 2.85, 1.15, 2.8),
            (-4.6, .62, 2.65, 1.50, 2.4), (-6.5, .40, 2.60, 1.60, 2.3), (-8.3, .30, 2.75, 1.75, 2.2), (-9.2, .24, 2.95, 1.85, 2.2)]
    rec = [dict(side='B', z0=-2.0, z1=0.30, s0=-0.50, s1=0.60, depth=0.72),
           dict(side='B', z0=0.95, z1=2.30, s0=0.0, s1=0.62, depth=0.22)]
    H = Hull(keys, rec, spacing=0.85, nlev=9)
    H.build(B, od.name)
    H.panel(B, 0, 0.95, 2.30, 0.0, 0.62, -0.03, g, 2, 2)
    H.panel(B, 0, 2.4, 4.5, 0.02, 0.93, 0.012, g, 4, 3)
    H.panel(B, 0, 3.7, 4.6, -0.6, -0.08, 0.012, g, 2, 2)
    H.panel(B, 0, 2.9, 3.6, 0.9, 1.0, 0.012, g, 2, 1) if False else None
    H.frame(B, 0, 0.88, 2.40, -0.6, 0.72, 0.022, 0.012, ln, 4)
    H.frame(B, 0, -2.05, 0.36, -0.58, 0.68, 0.022, 0.012, ln, 5)
    H.panel(B, 0, -3.15, -2.06, -0.48, 0.58, 0.04, od2.name, 3, 2)
    H.panel(B, 0, -3.0, -2.3, 0.05, 0.50, 0.046, g, 2, 2)
    H.frame(B, 0, -3.15, -2.06, -0.48, 0.58, 0.02, 0.05, ln, 3)
    for sd in (1, -1):
        H.patch(B, H.seq(sd, 0.67, 0.71, 1), -3.4, 0.4, 0.025, 'heli_steel_dark', 12)
        H.patch(B, H.seq(sd, -0.58, -0.54, 1), -3.4, 0.4, 0.025, 'heli_steel_dark', 12)
    for z in (-5.0, -6.6, -8.0):
        H.band(B, z, z + 0.025, 0.008, ln, 1)
    H.panel(B, 0, -3.0, -0.3, -0.95, -0.72, 0.01, od2.name, 6, 1)
    # transmission / engine hump
    dk = [(2.2, .50, 3.12, 2.8, 2.4), (1.2, .85, 3.42, 2.8, 3.0), (-0.5, .98, 3.62, 2.8, 3.2), (-2.2, .92, 3.5, 2.8, 3.0), (-3.4, .55, 3.05, 2.8, 2.4), (-4.0, .25, 2.9, 2.75, 2.2)]
    DK = Hull(dk, [], spacing=0.8, nlev=7); DK.build(B, od.name)
    DK.panel(B, 0, 1.0, 1.5, 0.1, 0.7, 0.012, blk, 2, 2)
    for k in range(4):
        z = -0.4 - k * 0.24; DK.patch(B, DK.roofseq(0.8, 2), z, z + 0.07, 0.012, blk, 1)
    for sd in (1, -1):
        DK.panel(B, sd, -3.0, -1.9, -0.1, 0.3, 0.012, blk, 2, 1)       # exhaust/ IR vents
    B.cyl((0, 3.45, -0.3), (0, 3.98, -0.3), 0.17, 0.12, 10, 'heli_steel_dark')
    B.cyl((0, 3.85, -0.3), (0, 3.93, -0.3), 0.32, 0.32, 14, 'heli_metal')
    # tail pylon, stabilator, tail wheel
    B.prism([(-7.7, 2.65), (-9.3, 4.9), (-10.2, 4.95), (-10.35, 4.1), (-9.95, 2.5)], (0, 0, 0), (0, 0, 1), (0, 1, 0), 0.26, od.name, 0.82)
    B.prism([(0.55, -0.3), (0.5, -2.2), (-0.55, -2.2), (-0.55, -0.3), (-0.55, 0.3), (-0.55, 2.2), (0.5, 2.2), (0.55, 0.3)], (0, 2.45, -9.1), (0, 0, 1), (1, 0, 0), 0.06, od.name, 0.8)
    B.sweep([(0, 1.9, -8.0), (0, 1.15, -8.75), (0, 0.62, -8.95)], 0.07, 6, 'heli_steel_dark')
    wheel(B, 0, 0.27, -8.95, 0.27, 0.16)
    B.prism([(0, 0), (-0.25, 0.0), (-0.3, 0.35), (0.0, 0.5)], (0, 2.62, -9.55), (0, 0, 1), (0, 1, 0), 0.025, 'heli_steel_dark', 0.7) if False else None
    # landing gear: main wheels + oleo struts
    for sx in (1, -1):
        x = sx * 1.38; wz = 0.55
        wheel(B, x, 0.38, wz, 0.38, 0.22)
        B.sweep([(sx * 1.05, 1.05, wz - 0.1), (sx * 1.3, 0.75, wz), (x, 0.4, wz)], 0.07, 6, 'heli_steel_dark')
        B.sweep([(sx * 0.9, 1.1, wz - 0.9), (sx * 1.2, 0.9, wz - 0.5), (x, 0.42, wz)], 0.05, 6, 'heli_steel_dark')
        B.cyl((sx * 1.2, 0.95, wz - 0.05), (sx * 1.3, 0.62, wz), 0.1, 0.075, 8, 'heli_metal')
    # landing light + antennas
    B.box((0, 2.58, 4.45), (0.2, 0.1, 0.1), 'heli_black')
    B.cyl((0, 2.82, -4.2), (0.0, 3.1, -4.35), 0.012, 0.01, 4, 'heli_metal'); B.box((0, 2.64, -6.0), (0.04, 0.3, 0.14), 'heli_steel_dark') if False else None
    B.cyl((0.3, 2.9, -3.5), (0.3, 3.2, -3.6), 0.012, 0.008, 4, 'heli_metal')
    # interior
    B.box((0, 1.08, -0.9), (2.0, 0.06, 3.0), 'heli_interior'); B.box((0, 1.5, -2.5), (2.0, 1.0, 0.08), 'heli_interior')
    for sx in (1, -1):
        for z in (-1.4, -0.45):
            seat_bucket(B, (sx * 0.8, 1.3, z), 'heli_seat_canvas', 2 if sx > 0 else -2, 0.5, 0.42, 0.55)
        seat_bucket(B, (sx * 0.62, 1.3, 1.5), 'heli_seat', 1, 0.5, 0.46, 0.65)
    # door guns
    for name, sd in (('_gun_L', 1), ('_gun_R', -1)):
        mount = V(sd * 1.03, 2.2, 0.12)
        GP = M.part(name, mount); m60(GP, mount, sd, 'heli_metal', 'heli_steel_dark', 'heli_seat')
    NL = M.part('_navlights')
    NL.light((1.05, 1.7, 4.0), 0.06, 'heli_light_red'); NL.light((-1.05, 1.7, 4.0), 0.06, 'heli_light_green')
    NL.light((0, 5.05, -10.3), 0.05, 'heli_light_white'); NL.light((0, 2.55, -5.5), 0.06, 'heli_light_red'); NL.light((0, 3.62, -2.5), 0.05, 'heli_light_red')
    hub = V(0, 4.05, -0.3)
    R = M.part('_mainrotor', hub)
    mast_head(R, hub, 4, 8.18, 0.53, 0.05, 'heli_steel_dark', 'heli_blade', root=0.9, pitch=4.0, cone=0.4)
    R.cyl(hub + V(0, -0.2, 0), hub + V(0, -0.14, 0), 0.3, 0.3, 12, 'heli_metal')
    R.cyl(hub + V(0, -0.06, 0), hub + V(0, 0.08, 0), 0.38, 0.38, 12, 'heli_steel_dark')
    BL = M.part('_rotor_blur', hub); BL.disc(hub + V(0, 0.2, 0), 8.18, 'heli_rotor_blur', 48)
    th = V(0.34, 3.85, -10.0)
    T = M.part('_tailrotor', th)
    T.cyl(th + V(-0.05, 0, 0), th + V(0.14, 0, 0), 0.1, 0.07, 8, 'heli_steel_dark')
    for a in (PI / 4, 3 * PI / 4, 5 * PI / 4, 7 * PI / 4):
        d = V(0, math.cos(a), math.sin(a))
        T.blade(th + V(0.07, 0, 0), d, V(1, 0, 0), 0.1, 1.65, 0.25, 0.23, 0.03, 12.0, 'heli_blade', nst=3, taper_tip=False)
    TB = M.part('_tailrotor_blur', th); TB.disc(th + V(0.07, 0, 0), 1.65, 'heli_rotor_blur', 28, axis='x')
    for loc in ((0.5, 1.25, 1.5), (-0.5, 1.25, 1.5), (1.0, 1.2, 0.0), (-1.0, 1.2, 0.0), (0.8, 1.25, -0.45), (-0.8, 1.25, -0.45), (0.8, 1.25, -1.4), (-0.8, 1.25, -1.4)):
        M.seat(loc)
    return M
