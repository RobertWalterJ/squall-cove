"""Bell 206 JetRanger style (civilian red/white)."""
from heli_parts import *

def build():
    M = Model('bell206')
    white = defmat('bell206_white', '#e8e8e2', 0.38, 0.05)
    red = defmat('bell206_red', '#c3201f', 0.4, 0.05)
    g = 'heli_glass'; blk = 'heli_black'; ln = 'heli_panel_line'
    B = M.part('_body')
    keys = [(2.55, .10, 1.28, 1.00, 2.0), (2.35, .40, 1.55, .80, 2.1), (1.90, .62, 1.80, .62, 2.4), (1.2, .70, 2.05, .56, 2.8),
            (0.3, .72, 2.18, .55, 3.0), (-0.7, .66, 2.32, .62, 2.8), (-1.5, .50, 2.05, .85, 2.4), (-2.2, .30, 1.72, 1.12, 2.2),
            (-3.2, .20, 1.66, 1.20, 2.2), (-5.0, .13, 1.60, 1.27, 2.2), (-6.5, .09, 1.58, 1.30, 2.2)]
    rec = [dict(side='B', z0=0.50, z1=1.45, s0=0.06, s1=0.74, depth=0.26), dict(side='B', z0=-0.85, z1=0.15, s0=0.06, s1=0.74, depth=0.26)]
    H = Hull(keys, rec, spacing=0.75, nlev=9)
    H.build(B, white.name)
    # glass in the window recesses, windscreen, chin glass
    H.panel(B, 0, 0.50, 1.45, 0.06, 0.74, -0.03, g, 2, 2)
    H.panel(B, 0, -0.85, 0.15, 0.06, 0.74, -0.03, g, 2, 2)
    H.panel(B, 0, 1.50, 2.28, 0.02, 0.93, 0.012, g, 3, 3)
    H.panel(B, 0, 1.95, 2.40, -0.62, -0.06, 0.012, g, 2, 2)
    # livery
    H.panel(B, 0, -6.4, 2.3, -0.42, -0.2, 0.013, red.name, 30, 1)
    H.patch(B, H.roofseq(0.84, 3), -1.45, 1.45, 0.009, red.name, 8)
    # door panel lines + handles
    H.frame(B, 0, 0.42, 1.52, -0.58, 0.82, 0.02, 0.012, ln, 3)
    H.frame(B, 0, -0.92, 0.38, -0.58, 0.82, 0.02, 0.012, ln, 3)
    for sd in (1, -1):
        for z in (0.55, -0.80):
            B.box((sd * 0.725, 1.30, z), (0.035, 0.05, 0.14), 'heli_metal', bevel=0.01)
    # intake louvres, cowl lines, exhaust
    for k in range(5):
        z = -0.40 - k * 0.14
        H.patch(B, H.roofseq(0.9, 2), z, z + 0.06, 0.012, blk, 1)
    B.cyl((0.0, 2.28, -1.05), (0.0, 2.38, -1.75), 0.115, 0.085, 8, 'heli_steel_dark')
    B.cyl((0.0, 2.38, -1.75), (0.0, 2.40, -1.86), 0.085, 0.07, 8, blk)
    # tail: fin and stabiliser
    fin = [(-5.45, 1.58), (-6.15, 2.70), (-6.72, 2.68), (-6.74, 1.0), (-6.40, 0.96), (-5.95, 1.30)]
    B.prism(fin, (0, 0, 0), (0, 0, 1), (0, 1, 0), 0.09, red.name, 0.8)
    # (ua = z, ub = y): outline given as (z, y)
    stab = [(0.28, -0.2), (0.2, -0.95), (-0.25, -0.95), (-0.28, -0.2), (-0.28, 0.2), (-0.25, 0.95), (0.2, 0.95), (0.28, 0.2)]
    B.prism(stab, (0, 1.50, -4.95), (0, 0, 1), (1, 0, 0), 0.045, white.name, 0.8)
    for sd in (1, -1):
        B.prism([(0.26, 0), (-0.26, 0), (-0.26, 0.55), (0.12, 0.55)], (sd * 0.96, 1.50, -4.95), (0, 0, 1), (0, 1, 0), 0.035, white.name, 0.8)
    B.box((0, 1.0, -6.62), (0.05, 0.22, 0.26), 'heli_steel_dark', bevel=0.01)        # tail skid
    # mast, fixed swashplate, mast cap
    B.cyl((0, 2.20, 0.05), (0, 2.66, 0.05), 0.11, 0.085, 10, 'heli_steel_dark')
    B.cyl((0, 2.58, 0.05), (0, 2.64, 0.05), 0.24, 0.24, 14, 'heli_metal')
    B.box((0.0, 2.52, 0.05 + 0.2), (0.04, 0.05, 0.26), 'heli_metal')
    # landing skids
    def belly(z): return H.surf(1, z, -1).y + 0.0
    skid_gear(B, 0.97, 2.05, -1.95, 0.62, 0.42, 0.045, 'heli_steel_dark', cross=(0.95, -0.80), belly=lambda z: belly(z) + 0.01)
    B.box((0.0, 0.57, 1.05), (0.9, 0.05, 0.36), 'heli_steel_dark', bevel=0.01) if False else None
    # interior
    for sx in (1, -1):
        seat_bucket(B, (sx * 0.42, 0.98, 0.9), 'heli_seat', 1, 0.46, 0.44, 0.5)
    B.box((0, 0.98, -0.45), (1.3, 0.1, 0.46), 'heli_seat', bevel=0.02)
    B.box((0, 1.33, -0.68), (1.3, 0.7, 0.09), 'heli_seat', rot=(8, 0, 0), bevel=0.02)
    # nav lights as their own node
    NL = M.part('_navlights')
    NL.light((0.63, 1.05, 2.0), 0.05, 'heli_light_red'); NL.light((-0.63, 1.05, 2.0), 0.05, 'heli_light_green')
    NL.light((0, 2.76, -6.76), 0.045, 'heli_light_white'); NL.light((0, 1.72, -3.8), 0.05, 'heli_light_red')
    # main rotor (teetering, two blades)
    hub = V(0, 2.80, 0.05)
    R = M.part('_mainrotor', hub)
    R.cyl(hub + V(0, -0.1, 0), hub + V(0, 0.1, 0), 0.09, 0.09, 8, 'heli_steel_dark')
    R.cyl(hub + V(0, -0.14, 0), hub + V(0, -0.08, 0), 0.20, 0.20, 12, 'heli_metal')           # rotating swashplate ring
    R.box(hub, (0.62, 0.11, 0.2), 'heli_steel_dark', bevel=0.02)                                 # yoke / trunnion
    for a in (0, PI):
        d = V(math.cos(a), 0, math.sin(a)); ch = V(0, 1, 0).cross(d)
        R.box(hub + d * 0.5, (0.34, 0.09, 0.18), 'heli_steel_dark', bevel=0.015)                # blade grip
        R.cyl(hub + d * 0.18 + ch * 0.1 + V(0, -0.1, 0), hub + d * 0.30 + ch * 0.1 + V(0, 0.0, 0), 0.012, 0.012, 4, 'heli_metal')
        R.cyl(hub + d * 0.16 + ch * 0.1 + V(0, -0.14, 0), hub + d * 0.16 + ch * 0.1 + V(0, -0.02, 0), 0.012, 0.012, 4, 'heli_metal')
        R.blade(hub, d, V(0, 1, 0), 0.6, 5.1, 0.34, 0.34, 0.04, 4.0, 'heli_blade', cone=0.2)
    BL = M.part('_rotor_blur', hub); BL.disc(hub + V(0, 0.1, 0), 5.1, 'heli_rotor_blur', 40)
    # tail rotor (two blades) on the left of the fin
    th = V(0.2, 1.85, -6.52)
    T = M.part('_tailrotor', th)
    T.cyl(th + V(-0.06, 0, 0), th + V(0.1, 0, 0), 0.07, 0.06, 8, 'heli_steel_dark')
    for a in (PI / 2, 3 * PI / 2):
        d = V(0, math.cos(a), math.sin(a))
        T.blade(th + V(0.05, 0, 0), d, V(1, 0, 0), 0.07, 0.84, 0.19, 0.17, 0.025, 14.0, 'heli_blade', nst=3, taper_tip=False)
    TB = M.part('_tailrotor_blur', th); TB.disc(th + V(0.05, 0, 0), 0.84, 'heli_rotor_blur', 24, axis='x')
    for loc in ((0.42, 0.98, 0.9), (-0.42, 0.98, 0.9), (0.45, 1.0, -0.45), (0.0, 1.0, -0.45), (-0.45, 1.0, -0.45)):
        M.seat(loc)
    return M
