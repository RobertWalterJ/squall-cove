"""CH-47 Chinook style: tandem three-blade rotors, rear ramp (own node), sponsons, side-window guns."""
from heli_parts import *
from m_blackhawk import wheel

def build():
    M = Model('chinook')
    od = defmat('chinook_olive', '#4c5233', 0.82, 0.04)
    od2 = defmat('chinook_olive_dark', '#3b4129', 0.85, 0.04)
    g = 'heli_glass'; blk = 'heli_black'; ln = 'heli_panel_line'
    B = M.part('_body')
    keys = [(7.3, .30, 2.35, 1.35, 2.0), (6.9, 1.0, 2.9, .95, 2.4), (6.2, 1.55, 3.4, .78, 3.0), (5.3, 1.85, 3.75, .7, 3.8),
            (4.2, 1.92, 3.95, .65, 4.4), (-4.5, 1.92, 4.0, .65, 4.4), (-6.0, 1.9, 4.0, .85, 4.2), (-7.0, 1.82, 3.95, 1.45, 4.0),
            (-8.0, 1.7, 3.9, 2.3, 3.6), (-8.2, 1.68, 3.9, 2.45, 3.6)]
    rec = [dict(side='B', z0=5.75, z1=6.75, s0=0.15, s1=0.70, depth=0.25),
           dict(side='R', z0=2.6, z1=4.4, s0=-0.79, s1=0.36, depth=1.2),
           dict(side='L', z0=3.3, z1=4.05, s0=0.0, s1=0.4, depth=0.4)]
    H = Hull(keys, rec, spacing=1.0, nlev=9)
    H.build(B, od.name)
    H.panel(B, 0, 5.75, 6.75, 0.15, 0.70, -0.03, g, 2, 2)
    H.panel(B, 0, 6.3, 7.15, -0.1, 0.85, 0.012, g, 3, 3)           # windscreen
    H.panel(B, 0, 6.9, 7.25, -0.55, -0.15, 0.012, g, 1, 1)
    H.frame(B, 0, 5.6, 6.9, -0.7, 0.8, 0.022, 0.012, ln, 3)        # cockpit door
    H.frame(B, 1, 2.5, 4.5, -0.85, 0.5, 0.022, 0.012, ln, 3)       # (left) door outline
    H.frame(B, -1, 2.5, 4.5, -0.85, 0.5, 0.022, 0.012, ln, 3)
    for z in (2.0, 0.7, -0.6, -1.9, -3.2, -4.5):
        H.panel(B, 0, z - 0.2, z + 0.2, 0.2, 0.6, 0.012, g, 1, 1)  # cabin windows
        H.frame(B, 0, z - 0.24, z + 0.24, 0.16, 0.64, 0.025, 0.012, ln, 1)
    for z in (1.4, -0.0, -2.6, -3.9, -5.3):
        H.band(B, z, z + 0.03, 0.008, ln, 1)
    H.panel(B, 0, -8.0, 3.0, -0.9, -0.82, 0.01, od2.name, 20, 1)
    # sponsons
    for sx in (1, -1):
        sp = [(5.6, .25, 1.45, .62, 2.2), (4.9, .55, 1.75, .55, 3.0), (2.0, .6, 1.85, .52, 3.4), (-1.0, .58, 1.8, .55, 3.4), (-2.2, .3, 1.5, .62, 2.4)]
        SP = Hull(sp, [], spacing=0.9, nlev=7, xc=sx * 1.62); SP.build(B, od2.name)
        SP.panel(B, sx, 4.6, 5.3, -0.3, 0.3, 0.012, blk, 1, 1)
    # front pylon + rotor-head fairing
    fp = [(5.7, .45, 4.25, 3.6, 2.4), (5.0, .62, 4.62, 3.6, 3.0), (4.3, .5, 4.4, 3.6, 2.4)]
    FP = Hull(fp, [], spacing=0.5, nlev=7); FP.build(B, od.name)
    B.cyl((0, 4.55, 5.0), (0, 4.88, 5.0), 0.2, 0.15, 10, 'heli_steel_dark')
    # rear pylon with engine nacelles
    B.prism([(-4.2, 3.9), (-5.5, 5.6), (-7.4, 5.85), (-8.0, 3.85)], (0, 0, 0), (0, 0, 1), (0, 1, 0), 1.3, od.name, 0.88)
    B.cyl((0, 5.8, -6.9), (0, 6.12, -6.9), 0.22, 0.16, 10, 'heli_steel_dark')
    for sx in (1, -1):
        B.sweep([(sx * 1.0, 4.65, -4.0), (sx * 1.0, 4.7, -5.6), (sx * 1.0, 4.75, -7.2)], [0.5, 0.52, 0.42], 10, od2.name, True)
        B.sweep([(sx * 1.0, 4.65, -3.98), (sx * 1.0, 4.65, -4.02)], 0.38, 10, blk, False, caps=(True, True))
        B.sweep([(sx * 1.0, 4.75, -7.2), (sx * 1.0, 4.76, -7.55)], [0.42, 0.3], 10, 'heli_steel_dark', True)
    # ramp pivot geometry is its own node, hull gets a dark opening behind it
    B.box((0, 3.18, -8.17), (2.7, 1.25, 0.05), 'heli_interior')
    # undercarriage
    for sx in (1, -1):
        for z, hx in ((3.6, 1.75), (-4.9, 1.75)):
            wheel(B, sx * hx, 0.45, z, 0.45, 0.26)
            B.sweep([(sx * 1.55, 0.9, z), (sx * hx, 0.65, z), (sx * hx, 0.45, z)], 0.08, 6, 'heli_steel_dark')
            B.cyl((sx * 1.55, 0.8, z), (sx * 1.7, 0.6, z), 0.11, 0.09, 8, 'heli_metal')
    B.cyl((0, 0.65, 0.5), (0, 0.5, 0.5), 0.12, 0.1, 8, 'heli_steel_dark')                       # cargo hook
    B.cyl((0, 3.95, 6.0), (0.2, 4.2, 6.1), 0.012, 0.01, 4, 'heli_metal')
    B.cyl((0.4, 3.99, -1.0), (0.4, 4.35, -1.0), 0.015, 0.01, 4, 'heli_metal')
    # interior seen through the right door
    B.box((0, 1.0, 1.0), (3.1, 0.07, 11.0), 'heli_interior')
    B.box((0, 2.0, -4.6), (3.0, 2.0, 0.08), 'heli_interior')
    for z in (3.0, 3.7, 4.1):
        seat_bucket(B, (-1.1, 1.45, z), 'heli_seat_canvas', -2, 0.46, 0.4, 0.55)
    seat_bucket(B, (0.55, 2.3, 6.2), 'heli_seat', 1, 0.5, 0.46, 0.62); seat_bucket(B, (-0.55, 2.3, 6.2), 'heli_seat', 1, 0.5, 0.46, 0.62)
    B.box((0, 2.0, 6.7), (1.8, 0.4, 0.2), blk, rot=(-25, 0, 0), bevel=0.03)
    # gun pivots at the left window and right door
    for name, sd, mount in (('_gun_L', 1, V(1.78, 2.3, 3.7)), ('_gun_R', -1, V(-1.85, 2.4, 3.1))):
        GP = M.part(name, mount); m60(GP, mount, sd, 'heli_metal', 'heli_steel_dark', 'heli_seat')
    # ramp
    hinge = V(0, 1.30, -6.78); ua = V(0, 1.1, -1.37).normalized(); L = V(0, 1.1, -1.37).length
    RP = M.part('_ramp', hinge)
    nm = ua.cross(V(1, 0, 0)).normalized()
    RP.prism([(0, -1.45), (L, -1.45), (L, 1.45), (0, 1.45)], hinge + nm * 0.07, ua, V(1, 0, 0), 0.12, od2.name, 0.9)
    for k in range(5):
        RP.prism([(0.1 + k * 0.38, -1.3), (0.16 + k * 0.38, -1.3), (0.16 + k * 0.38, 1.3), (0.1 + k * 0.38, 1.3)], hinge + nm * 0.14, ua, V(1, 0, 0), 0.03, 'heli_steel_dark', 1.0)
    NL = M.part('_navlights')
    NL.light((1.15, 1.45, 6.5), 0.06, 'heli_light_red'); NL.light((-1.15, 1.45, 6.5), 0.06, 'heli_light_green')
    NL.light((0, 5.95, -7.9), 0.05, 'heli_light_white'); NL.light((0, 0.62, 0.0), 0.06, 'heli_light_red'); NL.light((0, 4.0, 4.0), 0.05, 'heli_light_red')
    # rotors (blades only in their node; front lower than the rear)
    for nm_, hub, ph in (('front', V(0, 4.9, 5.0), PI / 2), ('rear', V(0, 6.15, -6.9), PI / 2 + PI / 3)):
        R = M.part('_rotor_' + nm_, hub)
        mast_head(R, hub, 3, 9.15, 0.81, 0.07, 'heli_steel_dark', 'heli_blade', root=1.0, pitch=4.5, cone=0.45, phase=ph)
        R.cyl(hub + V(0, -0.18, 0), hub + V(0, -0.1, 0), 0.34, 0.34, 12, 'heli_metal')
        BL = M.part('_rotor_%s_blur' % nm_, hub); BL.disc(hub + V(0, 0.2, 0), 9.15, 'heli_rotor_blur', 48)
    for z in (3.0, 2.0, 1.0, 0.0, -1.0, -2.0):
        M.seat((1.55, 1.3, z))
    for z in (4.1, 3.6, 3.1):
        M.seat((-1.1, 1.45, z))
    M.seat((0.55, 2.35, 6.2)); M.seat((-0.55, 2.35, 6.2)); M.seat((1.6, 2.2, 3.7)); M.seat((0.0, 1.1, -7.3))
    return M
