"""Bell UH-1H Iroquois style: long cabin, open sliding doors, door guns, two-blade rotor with stabiliser bar."""
from heli_parts import *

def build():
    M = Model('huey')
    od = defmat('huey_olive', '#4a4f33', 0.82, 0.04)
    od2 = defmat('huey_olive_dark', '#3d4229', 0.85, 0.04)
    g = 'heli_glass'; blk = 'heli_black'; ln = 'heli_panel_line'
    B = M.part('_body')
    keys = [(3.40, .15, 1.55, .98, 2.0), (3.05, .55, 1.95, .78, 2.2), (2.40, 1.00, 2.35, .62, 2.5), (1.50, 1.17, 2.42, .55, 3.0),
            (0.50, 1.22, 2.45, .55, 3.5), (-1.0, 1.22, 2.45, .52, 3.6), (-2.4, 1.20, 2.40, .55, 3.5), (-3.0, .85, 2.30, .90, 2.8),
            (-3.8, .55, 2.20, 1.25, 2.4), (-5.0, .34, 2.14, 1.48, 2.3), (-7.0, .24, 2.14, 1.62, 2.2), (-9.0, .16, 2.25, 1.75, 2.2),
            (-9.5, .12, 2.38, 1.80, 2.2)]
    rec = [dict(side='B', z0=-1.30, z1=0.55, s0=-0.55, s1=0.64, depth=0.72),
           dict(side='B', z0=0.78, z1=1.62, s0=0.05, s1=0.68, depth=0.22)]
    H = Hull(keys, rec, spacing=0.8, nlev=9)
    H.build(B, od.name)
    H.panel(B, 0, 0.78, 1.62, 0.05, 0.68, -0.03, g, 2, 2)                  # cockpit door windows
    H.panel(B, 0, 1.68, 3.0, 0.02, 0.92, 0.012, g, 3, 3)                    # windscreen / side glass
    H.panel(B, 0, 2.55, 3.15, -0.62, -0.05, 0.012, g, 2, 2)                 # chin glass
    # doors, panel lines
    H.frame(B, 0, 0.70, 1.70, -0.60, 0.78, 0.022, 0.012, ln, 3)             # cockpit door
    H.frame(B, 0, -1.34, 0.60, -0.60, 0.70, 0.022, 0.012, ln, 5)             # cabin opening frame
    # sliding door slid aft along its rail
    H.panel(B, 0, -2.35, -1.36, -0.50, 0.62, 0.04, od2.name, 3, 2)
    H.panel(B, 0, -2.15, -1.55, 0.05, 0.50, 0.046, g, 2, 2)
    H.frame(B, 0, -2.35, -1.36, -0.50, 0.62, 0.02, 0.05, ln, 3)
    for sd in (1, -1):
        H.patch(B, H.seq(sd, 0.74, 0.78, 1), -2.6, 0.75, 0.025, 'heli_steel_dark', 12)     # upper rail
        H.patch(B, H.seq(sd, -0.62, -0.58, 1), -2.6, 0.75, 0.025, 'heli_steel_dark', 12)  # lower rail
    for z in (-4.2, -6.0, -7.8):
        H.band(B, z, z + 0.025, 0.008, ln, 1)
    H.panel(B, 0, -2.2, -0.4, -0.95, -0.7, 0.01, od2.name, 6, 1)                        # belly strip panel
    # doghouse / transmission cowl and engine deck
    dk = [(1.2, .50, 2.72, 2.30, 2.6), (0.7, .80, 3.0, 2.25, 3.0), (-0.6, .92, 3.12, 2.25, 3.2), (-1.8, .86, 3.08, 2.25, 3.0), (-2.6, .62, 2.78, 2.3, 2.6), (-3.1, .30, 2.5, 2.3, 2.2)]
    DK = Hull(dk, [], spacing=0.7, nlev=7)
    DK.build(B, od.name, smooth=True)
    DK.panel(B, 0, 0.55, 1.0, 0.1, 0.8, 0.012, blk, 2, 2)                                # intake grille
    for k in range(4):
        z = -0.4 - k * 0.22
        DK.patch(B, DK.roofseq(0.78, 2), z, z + 0.07, 0.012, blk, 1)
    B.cyl((0, 3.0, -2.2), (0, 2.9, -3.1), 0.27, 0.2, 10, 'heli_steel_dark')              # exhaust
    B.cyl((0, 2.9, -3.1), (0, 2.88, -3.2), 0.2, 0.13, 10, blk)
    # mast and fixed swashplate
    B.cyl((0, 3.0, -0.35), (0, 3.55, -0.35), 0.15, 0.11, 10, 'heli_steel_dark')
    B.cyl((0, 3.45, -0.35), (0, 3.53, -0.35), 0.3, 0.3, 14, 'heli_metal')
    # tail: fin, tail skid, elevator
    fin = [(-7.9, 2.14), (-8.9, 3.95), (-9.55, 4.05), (-9.7, 2.1)]
    B.prism(fin, (0, 0, 0), (0, 0, 1), (0, 1, 0), 0.11, od.name, 0.82)
    B.prism([(0.3, -1.1), (-0.3, -1.1), (-0.3, 1.1), (0.3, 1.1)], (0, 2.05, -8.1), (0, 0, 1), (1, 0, 0), 0.05, od.name, 0.8)
    B.sweep([(0, 1.92, -8.6), (0, 1.55, -9.0), (0, 1.5, -9.4)], 0.04, 6, 'heli_steel_dark')   # tail skid
    B.box((0, 0.58, 3.30), (0.2, 0.05, 0.2), 'heli_steel_dark') if False else None
    B.cyl((0.35, 1.5, 3.15), (0.35, 1.5, 3.2), 0.1, 0.1, 8, 'heli_light_white') if False else None
    B.cyl((0.0, 1.62, 3.22), (0.0, 1.62, 3.55), 0.015, 0.01, 4, 'heli_metal')          # pitot
    # landing skids
    skid_gear(B, 1.30, 2.1, -2.0, 0.78, 0.55, 0.06, 'heli_steel_dark', cross=(1.2, -0.95), belly=lambda z: 0.58, seg=6)
    B.box((0, 0.58, 1.2), (1.1, 0.04, 0.3), 'heli_steel_dark') if False else None
    # cabin interior
    B.box((0, 0.84, -0.4), (1.9, 0.06, 2.4), 'heli_interior')
    B.box((0, 1.05, -1.62), (1.9, 0.9, 0.08), 'heli_interior')
    for sx in (1, -1):
        for z in (-0.95, -0.15):
            seat_bucket(B, (sx * 0.78, 1.0, z), 'heli_seat_canvas', 2 if sx > 0 else -2, 0.5, 0.42, 0.55)
        seat_bucket(B, (sx * 0.6, 1.08, 1.2), 'heli_seat', 1, 0.5, 0.46, 0.6)
    # door gun pivots
    for name, sd in (('_gun_L', 1), ('_gun_R', -1)):
        mount = V(sd * 0.98, 1.62, 0.36)
        GP = M.part(name, mount); m60(GP, mount, sd, 'heli_metal', 'heli_steel_dark', 'heli_seat')
    # nav lights
    NL = M.part('_navlights')
    NL.light((1.03, 1.40, 2.75), 0.06, 'heli_light_red'); NL.light((-1.03, 1.40, 2.75), 0.06, 'heli_light_green')
    NL.light((0, 4.12, -9.65), 0.05, 'heli_light_white'); NL.light((0, 1.62, -6.5), 0.06, 'heli_light_red')
    NL.light((0, 0.82, 2.78), 0.07, 'heli_light_white')
    # main rotor + stabiliser bar
    hub = V(0, 3.62, -0.35)
    R = M.part('_mainrotor', hub)
    mast_head(R, hub, 2, 7.3, 0.53, 0.05, 'heli_steel_dark', 'heli_blade', root=0.8, pitch=4.0, cone=0.3)
    R.cyl(hub + V(0, -0.1, -1.25), hub + V(0, -0.1, 1.25), 0.03, 0.03, 6, 'heli_steel_dark')       # stabiliser bar
    for sz in (1, -1):
        R.box(hub + V(0, -0.1, sz * 1.1), (0.14, 0.04, 0.55), 'heli_steel_dark', bevel=0.01)       # paddles
        R.cyl(hub + V(0, -0.1, sz * 0.1), hub + V(0.0, -0.45, sz * 0.12), 0.012, 0.012, 4, 'heli_metal')
    R.cyl(hub + V(0, -0.22, 0), hub + V(0, -0.16, 0), 0.26, 0.26, 12, 'heli_metal')
    BL = M.part('_rotor_blur', hub); BL.disc(hub + V(0, 0.15, 0), 7.3, 'heli_rotor_blur', 44)
    th = V(0.24, 3.38, -9.4)
    T = M.part('_tailrotor', th)
    T.cyl(th + V(-0.05, 0, 0), th + V(0.12, 0, 0), 0.08, 0.06, 8, 'heli_steel_dark')
    for a in (PI / 2, 3 * PI / 2):
        d = V(0, math.cos(a), math.sin(a))
        T.blade(th + V(0.06, 0, 0), d, V(1, 0, 0), 0.08, 1.3, 0.21, 0.19, 0.028, 14.0, 'heli_blade', nst=3, taper_tip=False)
    TB = M.part('_tailrotor_blur', th); TB.disc(th + V(0.06, 0, 0), 1.3, 'heli_rotor_blur', 24, axis='x')
    for loc in ((0.5, 1.1, 1.2), (-0.5, 1.1, 1.2), (0.9, 1.0, 0.0), (-0.9, 1.0, 0.0), (0.78, 1.05, -0.95), (-0.78, 1.05, -0.95), (0.78, 1.05, -0.15), (-0.78, 1.05, -0.15)):
        M.seat(loc)
    return M
