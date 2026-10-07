"""CH-146 Griffon (Bell 412EP): four-blade rotor, open right door with pintle minigun, wire-strike cutters, FLIR ball."""
from heli_parts import *

def build():
    M = Model('griffon')
    gr = defmat('griffon_grey', '#43473f', 0.78, 0.06)
    gr2 = defmat('griffon_grey_dark', '#34372f', 0.8, 0.06)
    g = 'heli_glass'; blk = 'heli_black'; ln = 'heli_panel_line'
    B = M.part('_body')
    keys = [(3.35, .14, 1.50, 1.00, 2.0), (3.0, .52, 1.92, .80, 2.2), (2.3, .98, 2.32, .62, 2.5), (1.4, 1.13, 2.40, .56, 3.0),
            (0.4, 1.17, 2.42, .55, 3.4), (-1.0, 1.17, 2.42, .54, 3.6), (-2.2, 1.14, 2.38, .56, 3.4), (-3.0, .85, 2.28, .92, 2.8),
            (-3.9, .56, 2.2, 1.28, 2.4), (-5.2, .36, 2.16, 1.50, 2.3), (-7.5, .25, 2.16, 1.65, 2.2), (-9.5, .17, 2.30, 1.76, 2.2),
            (-10.0, .13, 2.40, 1.80, 2.2)]
    rec = [dict(side='R', z0=-1.45, z1=0.50, s0=-0.55, s1=0.65, depth=0.72),
           dict(side='B', z0=0.72, z1=1.58, s0=0.05, s1=0.68, depth=0.22)]
    H = Hull(keys, rec, spacing=0.8, nlev=9)
    H.build(B, gr.name)
    H.panel(B, 0, 0.72, 1.58, 0.05, 0.68, -0.03, g, 2, 2)
    H.panel(B, 0, 1.65, 2.95, 0.02, 0.92, 0.012, g, 3, 3)
    H.panel(B, 0, 2.5, 3.1, -0.62, -0.05, 0.012, g, 2, 2)
    H.frame(B, 0, 0.64, 1.66, -0.60, 0.78, 0.022, 0.012, ln, 3)
    # closed left cabin door with window; right side: the door slid back on its rail
    H.frame(B, 1, -1.50, 0.56, -0.60, 0.70, 0.022, 0.012, ln, 5)
    H.panel(B, 1, -1.15, 0.2, 0.05, 0.52, 0.012, g, 3, 2)
    H.frame(B, -1, -1.50, 0.56, -0.60, 0.70, 0.022, 0.012, ln, 5)
    H.panel(B, -1, -2.4, -1.5, -0.50, 0.62, 0.04, gr2.name, 2, 2)
    H.panel(B, -1, -2.25, -1.7, 0.05, 0.50, 0.046, g, 2, 2)
    H.frame(B, -1, -2.4, -1.5, -0.50, 0.62, 0.02, 0.05, ln, 2)
    for sd in (1, -1):
        H.patch(B, H.seq(sd, 0.74, 0.78, 1), -2.6, 0.75, 0.025, 'heli_steel_dark', 12)
        H.patch(B, H.seq(sd, -0.62, -0.58, 1), -2.6, 0.75, 0.025, 'heli_steel_dark', 12)
    for z in (-4.2, -6.0, -7.8, -9.0):
        H.band(B, z, z + 0.025, 0.008, ln, 1)
    H.panel(B, 0, -2.2, -0.4, -0.95, -0.7, 0.01, gr2.name, 6, 1)
    # cowling
    dk = [(1.3, .52, 2.7, 2.30, 2.6), (0.8, .84, 3.0, 2.25, 3.0), (-0.6, .95, 3.15, 2.25, 3.2), (-2.0, .90, 3.1, 2.25, 3.0), (-2.8, .66, 2.8, 2.3, 2.6), (-3.4, .30, 2.5, 2.3, 2.2)]
    DK = Hull(dk, [], spacing=0.7, nlev=7); DK.build(B, gr.name)
    DK.panel(B, 0, 0.6, 1.05, 0.1, 0.8, 0.012, blk, 2, 2)
    for k in range(4):
        z = -0.5 - k * 0.22; DK.patch(B, DK.roofseq(0.78, 2), z, z + 0.07, 0.012, blk, 1)
    B.cyl((0, 3.02, -2.4), (0, 2.92, -3.3), 0.26, 0.19, 10, 'heli_steel_dark')
    B.cyl((0, 2.92, -3.3), (0, 2.9, -3.4), 0.19, 0.12, 10, blk)
    B.cyl((0, 3.0, -0.3), (0, 3.5, -0.3), 0.16, 0.12, 10, 'heli_steel_dark')
    B.cyl((0, 3.38, -0.3), (0, 3.47, -0.3), 0.3, 0.3, 14, 'heli_metal')
    # wire-strike cutters (above and below), FLIR ball, antennas
    B.prism([(0.0, 0.0), (-0.07, 0.0), (-0.1, 0.55), (0.0, 0.62), (0.08, 0.45)], (0, 2.36, 1.95), (0, 0, 1), (0, 1, 0), 0.035, 'heli_steel_dark', 0.7)
    B.prism([(0.0, 0.0), (-0.1, 0.0), (-0.2, -0.38), (-0.02, -0.46), (0.08, -0.25)], (0, 0.64, 2.72), (0, 0, 1), (0, 1, 0), 0.035, 'heli_steel_dark', 0.7)
    B.ellipsoid((0, 0.66, 3.0), (0.2, 0.2, 0.22), 'heli_black', 10, 6)
    B.cyl((0, 0.66, 3.0), (0, 0.8, 3.0), 0.12, 0.12, 8, 'heli_steel_dark')
    B.prism([(0.2, 0), (-0.2, 0), (-0.3, -0.38), (0.1, -0.2)], (0, 0.56, -1.2), (0, 0, 1), (0, 1, 0), 0.025, 'heli_steel_dark', 0.7)    # belly antenna blade
    B.box((0, 0.5, -0.3), (0.5, 0.1, 0.8), gr2.name, bevel=0.03)                                                                          # belly cargo hook fairing
    B.cyl((0.0, 2.4, 0.2), (0.0, 2.4, 0.2), 0.001, 0.001, 3, blk) if False else None
    # tail: fin, ventral fin, stabiliser with end plates
    B.prism([(-8.4, 2.16), (-9.35, 3.95), (-10.05, 3.95), (-10.1, 2.2)], (0, 0, 0), (0, 0, 1), (0, 1, 0), 0.11, gr.name, 0.82)
    B.prism([(-9.3, 1.78), (-10.0, 1.78), (-10.0, 1.1), (-9.75, 1.0)], (0, 0, 0), (0, 0, 1), (0, 1, 0), 0.07, gr.name, 0.8)
    B.prism([(0.32, -1.25), (-0.3, -1.25), (-0.3, 1.25), (0.32, 1.25)], (0, 2.06, -8.7), (0, 0, 1), (1, 0, 0), 0.05, gr.name, 0.8)
    for sd in (1, -1):
        B.prism([(0.3, 0), (-0.3, 0), (-0.3, 0.7), (0.12, 0.7)], (sd * 1.27, 2.0, -8.7), (0, 0, 1), (0, 1, 0), 0.04, gr.name, 0.8)
    # skids
    skid_gear(B, 1.28, 2.1, -2.1, 0.8, 0.55, 0.06, 'heli_steel_dark', cross=(1.2, -1.0), belly=lambda z: 0.56, seg=6)
    # interior
    B.box((0, 0.84, -0.5), (1.9, 0.06, 2.5), 'heli_interior'); B.box((0, 1.05, -1.72), (1.9, 0.9, 0.08), 'heli_interior')
    for z in (-1.1, -0.4):
        seat_bucket(B, (-0.78, 1.0, z), 'heli_seat_canvas', -2, 0.5, 0.42, 0.55)
    for sx in (1, -1):
        seat_bucket(B, (sx * 0.6, 1.08, 1.2), 'heli_seat', 1, 0.5, 0.46, 0.6)
    B.box((-0.7, 1.02, 0.3), (0.5, 0.1, 0.45), 'heli_seat_canvas', bevel=0.02)          # gunner perch near the door
    # gun on its own pivot (right door, barrel toward -x)
    mount = V(-0.98, 1.62, 0.25)
    GP = M.part('_gun', mount); minigun(GP, mount, -1, 'heli_metal', 'heli_steel_dark')
    NL = M.part('_navlights')
    NL.light((1.0, 1.40, 2.7), 0.06, 'heli_light_red'); NL.light((-1.0, 1.40, 2.7), 0.06, 'heli_light_green')
    NL.light((0, 4.03, -10.05), 0.05, 'heli_light_white'); NL.light((0, 1.74, -6.5), 0.06, 'heli_light_red')
    NL.light((0, 0.78, 2.6), 0.07, 'heli_light_white'); NL.light((0, 3.12, -2.0), 0.05, 'heli_light_red')
    hub = V(0, 3.56, -0.3)
    R = M.part('_mainrotor', hub)
    mast_head(R, hub, 4, 7.0, 0.5, 0.05, 'heli_steel_dark', 'heli_blade', root=0.7, pitch=4.0, cone=0.25, phase=PI / 4)
    R.cyl(hub + V(0, -0.2, 0), hub + V(0, -0.14, 0), 0.26, 0.26, 12, 'heli_metal')
    BL = M.part('_rotor_blur', hub); BL.disc(hub + V(0, 0.15, 0), 7.0, 'heli_rotor_blur', 44)
    th = V(0.24, 3.3, -9.9)
    T = M.part('_tailrotor', th)
    T.cyl(th + V(-0.05, 0, 0), th + V(0.12, 0, 0), 0.08, 0.06, 8, 'heli_steel_dark')
    for a in (PI / 2, 3 * PI / 2):
        d = V(0, math.cos(a), math.sin(a))
        T.blade(th + V(0.06, 0, 0), d, V(1, 0, 0), 0.08, 1.3, 0.23, 0.21, 0.028, 14.0, 'heli_blade', nst=3, taper_tip=False)
    TB = M.part('_tailrotor_blur', th); TB.disc(th + V(0.06, 0, 0), 1.3, 'heli_rotor_blur', 24, axis='x')
    for loc in ((0.5, 1.1, 1.2), (-0.5, 1.1, 1.2), (-0.9, 1.0, 0.0), (-0.78, 1.05, -0.4), (-0.78, 1.05, -1.1), (0.5, 1.05, -0.4), (0.5, 1.05, -1.1), (0.0, 1.05, -1.3)):
        M.seat(loc)
    return M
