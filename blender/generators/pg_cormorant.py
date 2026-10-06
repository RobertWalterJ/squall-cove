"""CH-149 Cormorant (AgustaWestland AW101 Mk 511), the Canadian search and rescue helicopter.
Modelled from Wikimedia Commons photographs (starboard side, front three-quarter) and published dimensions: fuselage about 19.5 m, five-blade main rotor 18.6 m,
four-blade tail rotor on the port side, three engines (two side inlets, third exhaust at the rear of the doghouse), red sponsons with twin main wheels, twin nose wheels.
SAR yellow with red trim; the paint, panel lines, stripes and lettering come from the UV atlas painted by air_tex.py.
Z up, nose +X, starboard -Y, wheels touch z = 0. Animated parts (rotor, tail rotor, winch point) are separate objects whose ORIGIN is the pivot.
"""
import math, os
from mathutils import Vector, Matrix
import bmesh
from air_common import *
import air_layout as LY

HUB = (1.4, 0.0, 5.7)             # main rotor pivot
TAILHUB = (-9.85, 0.6, 5.3)        # tail rotor pivot (port side of the pylon)
WINCH = (1.6, -2.25, 3.45)         # hoist hook point, starboard side

def materials(tex_dir):
    M = {}
    M['skin'] = tex_mat('cor_skin', os.path.join(tex_dir, 'cormorant_livery.jpg'), os.path.join(tex_dir, 'cormorant_normal.png'), rough=0.42, nstr=1.0)
    M['glass'] = mat('cor_glass', '#14222f', 0.05, 0.0)
    M['rubber'] = mat('cor_rubber', '#15171a', 0.78, 0.0)
    M['steel'] = mat('cor_steel', '#8b9197', 0.34, 0.85)
    M['dark'] = mat('cor_darkmetal', '#2b2f33', 0.5, 0.55)
    M['silver'] = mat('cor_silver', '#c3c8cc', 0.28, 0.95)
    M['red'] = mat('cor_red', '#b3232b', 0.42, 0.0)
    M['yellow'] = mat('cor_yellow', '#f0b412', 0.42, 0.0)
    M['tyre'] = mat('cor_tyre', '#0f1113', 0.92, 0.0)
    M['blade'] = mat('cor_blade', '#34383c', 0.42, 0.4)
    M['bladetip'] = mat('cor_bladetip', '#e8a812', 0.42, 0.0)
    M['white'] = mat('cor_white', '#ecebe4', 0.45, 0.0)
    M['lens'] = mat('cor_lens', '#c9ced2', 0.12, 0.0)
    M['green'] = mat('cor_green', '#1c8a3c', 0.3, 0.0)
    M['disc'] = mat('rotordisc', '#ffffff', 0.5, alpha=0.04)
    return M

def solid_region(px):
    from air_layout import Region
    return Region('solid', (px[0] - 6, px[1] - 6, px[0] + 6, px[1] + 6), (0, 1), (0, 1))

# ------------------------------------------------------------------ fuselage
def fuselage_keys():
    K = {}
    K['zt'] = make_interp([(-10.6, 5.62), (-10.0, 5.6), (-9.0, 5.15), (-8.3, 4.55), (-7.6, 3.95), (-7.0, 3.68), (-5, 3.62), (-2, 3.58), (1, 3.58), (4, 3.52), (6, 3.45), (6.8, 3.38),
                           (7.4, 3.12), (8.0, 2.55), (8.5, 1.9), (8.85, 1.5), (9.0, 1.28), (9.045, 1.1)])
    K['zb'] = make_interp([(-10.6, 5.45), (-10.0, 4.9), (-9.4, 3.9), (-8.9, 2.65), (-8.0, 2.45), (-4.5, 2.4), (-4.0, 2.3), (-3.5, 1.9), (-3.0, 1.45), (-2.4, 0.95), (-1.8, 0.58), (-1.2, 0.5),
                           (8.0, 0.5), (8.5, 0.56), (8.85, 0.72), (9.0, 0.92), (9.045, 1.05)])
    K['w'] = make_interp([(-10.6, 0.08), (-10.3, 0.22), (-9.4, 0.28), (-8.6, 0.4), (-7.5, 0.6), (-6, 0.86), (-4.5, 1.1), (-3.2, 1.3), (-2, 1.4), (0, 1.44), (4, 1.44), (6, 1.4), (7, 1.32),
                          (7.8, 1.26), (8.4, 1.02), (8.75, 0.8), (8.95, 0.55), (9.02, 0.27), (9.045, 0.04)])
    K['rt'] = make_interp([(-10.6, 0.05), (-8, 0.3), (-4, 0.7), (0, 0.85), (6, 0.8), (7.5, 0.6), (9.0, 0.2)])
    K['rb'] = make_interp([(-10.6, 0.05), (-8, 0.3), (-4, 0.5), (0, 0.55), (6, 0.5), (8, 0.35), (9.0, 0.1)])
    K['cr'] = make_interp([(-10.6, 0.0), (-8, 0.02), (-4, 0.1), (0, 0.13), (6, 0.1), (8, 0.04), (9.0, 0.0)])
    return K

def build_fuselage(M):
    K = fuselage_keys()
    sec = lambda x: rr_ring(K['zt'](x), K['zb'](x), K['w'](x), K['rt'](x), K['rb'](x), K['cr'](x), nb=4, ncb=4, ns=5, nct=6, nt=7)
    xs = cluster(-10.6, 9.045, 124, 0.75, 0.9)
    o, bvh = hull_loft(xs, sec, 'fus', M['skin'], True, True)
    apply_uv(o, hull_rule(LY.COR))
    return o, bvh

def build_doghouse(M):
    zt = make_interp([(3.35, 3.55), (3.2, 3.95), (2.8, 4.5), (2.2, 4.8), (1.2, 4.93), (-0.5, 4.95), (-1.6, 4.85), (-2.6, 4.55), (-3.6, 4.1), (-4.5, 3.62)])
    w = make_interp([(3.35, 0.4), (3.2, 0.7), (2.8, 0.98), (2.2, 1.1), (1.0, 1.14), (-0.5, 1.12), (-1.6, 1.02), (-2.6, 0.85), (-3.6, 0.62), (-4.5, 0.38)])
    rt = make_interp([(3.35, 0.3), (2.8, 0.5), (1.0, 0.55), (-3.0, 0.5), (-4.5, 0.3)])
    sec = lambda x: rr_ring(zt(x), 3.3, w(x), rt(x), 0.12, 0.06, nb=3, ncb=2, ns=5, nct=6, nt=6)
    o, bvh = hull_loft(cluster(-4.5, 3.35, 56, 0.6, 0.6), sec, 'dog', M['skin'], True, True)
    apply_uv(o, hull_rule(LY.COR))
    return o, bvh

# ------------------------------------------------------------------ windows
def add_windows(M, fus_bvh, parts):
    gl, fr = M['glass'], M['rubber']
    for s in (-1, 1):
        rd, ex, ey = Vector((0, -s, 0)), Vector((1, 0, 0)), Vector((0, 0, 1))
        def wn(x, z, w, h, r=0.12, round_=False, rdv=None, name='win'):
            parts.extend(window(fus_bvh, Vector((x, s * 3.0, z)), ex, ey, rdv or rd, w, h, r, gl, fr, 0.03, 0.01, 0.024, 2, round_, name))
        for x in (-0.45, 1.1, 4.25): wn(x, 2.2, 0.52, 0.64, 0.14)
        wn(-1.8, 2.2, 0.48, 0.48, round_=True)                                  # aft round cabin window
        if s < 0: wn(2.55, 2.45, 0.46, 0.5, 0.12)                               # sliding-door window
        else: wn(2.55, 2.2, 0.52, 0.64, 0.14)
        wn(5.2, 2.3, 0.42, 0.42, round_=True)                                   # porthole in the forward crew door
        wn(6.5, 2.62, 0.84, 0.68, 0.2, rdv=Vector((-0.1, -s * 0.9, -0.42)))    # cockpit door window (tilted ray: the shoulder leans over here)
        wn(7.6, 1.95, 0.4, 0.32, 0.1, rdv=Vector((-0.28, -s * 0.96, 0)))        # small lower nose windows
        wn(8.25, 1.72, 0.32, 0.26, 0.09, rdv=Vector((-0.6, -s * 0.8, 0)))
    # windscreen: two big panes with a centre post, following the raked nose
    rdv = Vector((-0.72, 0.0, -0.69)).normalized(); ex = Vector((0, 1, 0)); ey = (rdv.cross(ex)) * -1
    for u in (0.5, -0.5):
        parts.extend(window(fus_bvh, Vector((8.0, 0, 2.62)) + ex * u, ex, ey, rdv, 0.84, 0.86, 0.17, gl, fr, 0.03, 0.01, 0.024, 2, False, 'screen'))

def add_noseteam(M, parts):
    st, dk, rub, sil = M['steel'], M['dark'], M['rubber'], M['silver']
    # electro-optical turret under the chin
    parts.append(revolve([(0.0, 0.0), (0.12, 0.0), (0.2, 0.05), (0.2, 0.12)], (8.25, 0, 0.5), (0, 0, -1), 20, dk, 'eoneck'))
    parts.append(revolve([(0.0, 0.0), (0.14, 0.0), (0.27, 0.06), (0.32, 0.18), (0.3, 0.34), (0.2, 0.45), (0.0, 0.5)], (8.25, 0, 0.33), (0, 0, -1), 24, M['white'], 'eoball'))
    parts.append(revolve([(0.0, 0.0), (0.13, 0.0), (0.14, 0.04), (0.0, 0.05)], (8.5, 0, 0.14), (1, 0, 0), 16, M['glass'], 'eolens'))
    parts.append(revolve([(0.0, 0.0), (0.06, 0.0), (0.06, 0.04), (0.0, 0.05)], (8.5, 0.15, 0.2), (1, 0, 0), 12, M['glass'], 'eolens2'))
    parts.append(rbox((0.46, 0.36, 0.08), (8.25, 0, 0.5), dk, 0.03, name='eomount'))
    # landing light, wire cutter, pitot tubes, wipers
    parts.append(rbox((0.22, 0.34, 0.2), (8.72, 0, 0.78), M['lens'], 0.05, name='landlight'))
    for s in (-1, 1):
        parts.append(tube((8.35, s * 0.55, 1.05), (9.15, s * 0.6, 1.0), 0.018, 6, st, 'pitot'))
    for u in (0.5, -0.5):
        parts.append(tube((8.18, u * 0.9, 2.2), (7.78, u * 0.55 + 0.32 * (1 if u > 0 else -1) * 0.0 + 0.1 * u, 2.95), 0.01, 4, rub, 'wiper'))
    parts.append(tube((6.65, 0, 3.4), (6.65, 0, 3.78), 0.02, 5, dk, 'wirecutter')); parts.append(tube((6.65, 0, 3.8), (6.95, 0, 3.55), 0.015, 5, dk, 'wirecutter2'))

def build_doghouse_details(M, dog_bvh, parts):
    gl, fr, dk, st, sil = M['glass'], M['rubber'], M['dark'], M['steel'], M['silver']
    for s in (-1, 1):
        # square engine inlets on each forward flank
        inner = rrect(0.5, 0.68, 0.09); outer = rrect(0.5 + 0.09, 0.68 + 0.09, 0.13)
        c = Vector((2.35, s * 3.0, 3.98)); ex = Vector((1, 0, 0)); ey = Vector((0, 0, 1)); rd = Vector((-0.25, -s * 0.97, 0))
        parts.append(patch(dog_bvh, c, ex, ey, rd, inner, 0.015, 3, M['glass'], 'inlet'))
        parts.append(bezel(dog_bvh, c, ex, ey, rd, inner, outer, 0.05, 0.003, st, 'inletlip'))
        # exhausts: short silver stubs angled out and aft
        a = Vector((0.95, s * 1.0, 4.12)); d = Vector((-0.8, s * 0.45, 0.05)).normalized()
        parts.append(revolve([(0.2, 0.0), (0.22, 0.2), (0.215, 0.7), (0.19, 0.74), (0.19, 0.6), (0.0, 0.58)], a, d, 20, sil, 'exhaust', cap_a=True))
        parts.append(revolve([(0.14, 0.0), (0.23, 0.12)], a + d * -0.04, d, 20, dk, 'exhbase'))
    # third engine exhaust at the rear of the doghouse (silver, on the centreline)
    parts.append(revolve([(0.22, 0.0), (0.235, 0.25), (0.23, 0.9), (0.2, 0.94), (0.2, 0.8), (0.0, 0.78)], Vector((-1.5, 0, 4.4)), Vector((-1, 0, -0.08)), 22, sil, 'exh3'))
    parts.append(rbox((1.2, 0.5, 0.12), (-0.6, 0, 4.95), dk, 0.04, name='roofvent'))

def build_gear(M, parts):
    tyre_m, hub_m, st, dk = M['tyre'], M['steel'], M['steel'], M['dark']
    nx = 7.05
    parts.append(tube((nx, 0, 0.62), (nx, 0, 0.42), 0.09, 10, st, 'noseleg'))
    parts.append(tube((nx, 0, 0.5), (nx + 0.0, 0, 0.36), 0.05, 8, dk, 'nosefork'))
    parts.append(tube((nx, -0.25, 0.36), (nx, 0.25, 0.36), 0.035, 8, st, 'noseaxle'))
    for dy in (-0.2, 0.2): parts.append(tyre(nx, dy, 0.36, 0.36, 0.2, tyre_m, hub_m, 'nosewheel'))
    parts.append(rbox((0.7, 0.55, 0.16), (nx, 0, 0.62), dk, 0.03, name='nosegearbay'))
    parts.append(tube((nx + 0.35, 0, 0.55), (nx + 0.1, 0, 0.4), 0.025, 6, st, 'noselink'))
    for s in (-1, 1):
        mx, my = -1.95, s * 1.7
        parts.append(tube((mx, my, 0.75), (mx, my, 0.4), 0.11, 10, st, 'mainleg'))
        parts.append(tube((mx, my - 0.3, 0.42), (mx, my + 0.3, 0.42), 0.04, 8, st, 'mainaxle'))
        for dy in (-0.17, 0.17): parts.append(tyre(mx, my + dy, 0.42, 0.42, 0.26, tyre_m, hub_m, 'mainwheel'))
        parts.append(tube((mx + 0.45, my, 0.85), (mx + 0.05, my, 0.5), 0.03, 6, dk, 'torquelink'))
        parts.append(tube((mx - 0.4, my, 0.9), (mx - 0.05, my, 0.5), 0.025, 6, dk, 'brace'))
    for s in (-1, 1):
        parts.append(rbox((0.5, 0.18, 0.12), (3.5, s * 1.05, 0.5), dk, 0.03, name='jackpad'))

def build_sponsons(M, parts):
    R = LY.COR
    key_w = make_interp([(-3.0, 0.04), (-2.7, 0.3), (-2.0, 0.52), (-0.8, 0.6), (0.5, 0.54), (1.0, 0.34), (1.2, 0.04)])
    key_h = make_interp([(-3.0, 0.03), (-2.7, 0.26), (-2.0, 0.4), (-0.8, 0.44), (0.5, 0.38), (1.0, 0.22), (1.2, 0.03)])
    for s in (-1, 1):
        sec = lambda x, s=s: ring_ellipse(1.02 + key_h(x), 1.02 - key_h(x), key_w(x), 2.4, 32, yoff=s * 1.72)
        o = hull_loft(cluster(-3.0, 1.2, 28, 0.8, 0.8), sec, 'sponson', M['skin'], True, False)
        reg = R['sp_sb'] if s < 0 else R['sp_pt']; red_solid = solid_region(LY.COR_SOLID['red'])
        xz = lambda co: (co.x, co.z)
        def rule(c, n, s=s, reg=reg):
            if n.y * s > 0.35: return reg, xz
            return red_solid, (lambda co: (0.5, 0.5))
        apply_uv(o, rule); parts.append(o)
        parts.append(rbox((0.12, 0.1, 0.1), (1.15, s * 1.72, 1.02), M['red'] if s > 0 else M['green'], 0.03, name='navlight'))

def build_rails(M, parts):
    st = M['steel']
    for s in (-1, 1):
        parts.append(tube((1.75, s * 1.47, 3.02), (3.65, s * 1.47, 3.02), 0.022, 6, st, 'handrail'))
        for x in (1.75, 3.65): parts.append(tube((x, s * 1.4, 3.02), (x, s * 1.47, 3.02), 0.02, 6, st, 'handrailpost'))
    # cabin step under the door
    parts.append(rbox((0.5, 0.22, 0.04), (2.65, -1.42, 0.62), st, 0.01, name='cabinstep'))

def build_hoist(M, parts):
    dk, rd, st = M['dark'], M['red'], M['steel']
    x = 1.7
    parts.append(rbox((0.62, 0.5, 0.6), (x, -1.6, 3.88), dk, 0.07, name='hoistbox'))
    parts.append(revolve([(0.0, 0.0), (0.27, 0.0), (0.27, 0.32), (0.0, 0.32)], (x - 0.16, -1.95, 3.88), (1, 0, 0), 18, rd, 'hoistdrum'))
    parts.append(rbox((0.42, 0.1, 0.46), (x, -1.4, 3.55), dk, 0.03, name='hoistbracket'))
    parts.append(tube((x, -1.6, 3.6), (x, -2.1, 3.5), 0.05, 8, st, 'hoistarm'))
    parts.append(tube((x, -2.1, 3.5), (x, -2.25, 3.42), 0.03, 6, dk, 'hoistcable'))
    parts.append(revolve([(0.0, 0.0), (0.16, 0.08), (0.22, 0.3), (0.22, 0.9), (0.16, 1.12), (0.0, 1.2)], (1.35, -1.52, 3.28), (1, 0, 0), 18, rd, 'hoistpod'))
    for k in (1.55, 2.25): parts.append(tube((k, -1.55, 3.36), (k, -1.42, 3.5), 0.03, 5, dk, 'podbrace'))

def build_tail(M, parts):
    R = LY.COR; sk = M['skin']
    stab = wing([dict(y=-1.75, xle=-9.85, chord=0.62, t=0.07, z=2.72), dict(y=-0.9, xle=-9.15, chord=0.95, t=0.1, z=2.7), dict(y=0.9, xle=-9.15, chord=0.95, t=0.1, z=2.7), dict(y=1.75, xle=-9.85, chord=0.62, t=0.07, z=2.72)], sk, 'stab', 12, 2)
    apply_uv(stab, lambda c, n: (R['stab'], lambda co: (co.y, co.x))); parts.append(stab)
    parts.append(revolve([(0.0, 0.0), (0.22, 0.02), (0.28, 0.2), (0.24, 0.5), (0.17, 0.62), (0.0, 0.66)], (TAILHUB[0], 0.05, TAILHUB[2]), (0, 1, 0), 18, M['yellow'], 'tgb'))
    parts.append(rbox((0.5, 0.36, 0.24), (-10.2, 0.0, 5.7), M['yellow'], 0.06, name='tgbtop'))
    parts.append(rbox((0.1, 0.1, 0.12), (-10.45, 0, 5.82), M['red'], 0.03, name='beacon'))
    parts.append(rbox((0.14, 0.06, 0.1), (-10.58, 0, 5.4), M['white'], 0.02, name='taillight'))
    for (x, z, hgt) in ((-3.0, 3.6, 0.3), (-1.8, 3.62, 0.22), (5.2, 3.46, 0.25)):
        parts.append(rbox((0.32, 0.03, hgt), (x, 0, z + hgt / 2), M['dark'], 0.01, name='bladeant'))
    parts.append(tube((-5.5, 0, 3.62), (-6.6, 0, 3.55), 0.008, 4, M['dark'], 'wireant'))
    parts.append(tube((0.0, 0, 0.5), (0.0, 0, 0.35), 0.014, 5, M['dark'], 'bellyant'))

def build_mast(M, parts):
    h = HUB
    parts.append(revolve([(0.52, 0.0), (0.42, 0.14), (0.3, 0.38), (0.26, 0.6)], (h[0], h[1], 4.82), (0, 0, 1), 24, M['yellow'], 'mastfair'))
    parts.append(revolve([(0.0, 0.0), (0.2, 0.0), (0.2, 0.4)], (h[0], h[1], h[2] - 0.45), (0, 0, 1), 18, M['steel'], 'mast'))

# ------------------------------------------------------------------ rotors
def build_rotor(M):
    bl = []
    for i in range(5):
        a = i * 2 * PI / 5
        secs = [dict(y=-0.95, xle=0.34, chord=0.62, t=0.15, z=0.0), dict(y=-1.8, xle=0.33, chord=0.58, t=0.11, z=-0.01), dict(y=-5.0, xle=0.32, chord=0.54, t=0.085, z=-0.07),
                dict(y=-8.0, xle=0.30, chord=0.52, t=0.075, z=-0.2), dict(y=-8.7, xle=0.22, chord=0.56, t=0.065, z=-0.26), dict(y=-9.1, xle=0.04, chord=0.48, t=0.06, z=-0.3), dict(y=-9.35, xle=-0.2, chord=0.3, t=0.05, z=-0.32)]
        b = wing(secs, M['blade'], 'blade', 12, 3)
        b.data.materials.append(M['bladetip']); idx = len(b.data.materials) - 1
        for p in b.data.polygons:
            if p.center.y < -8.55: p.material_index = idx
        b.data.transform(Matrix.Rotation(PI / 2, 4, 'Z')); b.data.transform(Matrix.Rotation(a, 4, 'Z')); bl.append(b)
        sl = rbox((0.75, 0.3, 0.22), (0.62, 0.0, -0.02), M['dark'], 0.05, name='sleeve'); sl.data.transform(Matrix.Rotation(a, 4, 'Z')); bl.append(sl)
        hn = tube((0.45, 0.0, -0.05), (0.9, 0.0, 0.12), 0.03, 5, M['steel'], 'pitchlink'); hn.data.transform(Matrix.Rotation(a + 0.3, 4, 'Z')); bl.append(hn)
    bl.append(revolve([(0.0, -0.2), (0.62, -0.2), (0.66, -0.06), (0.62, 0.1), (0.4, 0.14), (0.0, 0.14)], (0, 0, 0), (0, 0, 1), 28, M['dark'], 'hubplate'))
    bl.append(revolve([(0.0, 0.14), (0.4, 0.14), (0.38, 0.26), (0.28, 0.36), (0.0, 0.38)], (0, 0, 0), (0, 0, 1), 28, M['red'], 'hubcap'))
    bl.append(cyl(9.35, 9.35, 0.01, 56, loc=(0, 0, -0.1), material=M['disc'], name='disc'))
    o = join(bl, 'rotor'); o.location = Vector(HUB); return o

def build_tail_rotor(M):
    bl = []
    for i in range(4):
        a = i * PI / 2 + 0.4
        secs = [dict(y=0.25, xle=0.16, chord=0.3, t=0.14, z=0.0), dict(y=1.0, xle=0.15, chord=0.3, t=0.1, z=0.0), dict(y=1.9, xle=0.13, chord=0.26, t=0.08, z=0.0), dict(y=2.0, xle=0.1, chord=0.2, t=0.07, z=0.0)]
        b = wing(secs, M['blade'], 'tb', 10, 2)
        b.data.materials.append(M['red']); idx = len(b.data.materials) - 1
        for p in b.data.polygons:
            if p.center.y > 1.75: p.material_index = idx
        b.data.transform(Matrix.Rotation(PI / 2, 4, 'X'))
        b.data.transform(Matrix.Rotation(a, 4, 'Y')); bl.append(b)
    bl.append(revolve([(0.0, -0.16), (0.2, -0.16), (0.24, -0.04), (0.24, 0.08), (0.0, 0.12)], (0, 0, 0), (0, 1, 0), 18, M['dark'], 'tailhub'))
    bl.append(cyl(2.0, 2.0, 0.008, 36, loc=(0, 0.0, 0), rot=(-PI / 2, 0, 0), material=M['disc'], name='tdisc'))
    o = join(bl, 'tailrotor'); o.location = Vector(TAILHUB); return o

# ------------------------------------------------------------------ assemble
def build(tex_dir):
    M = materials(tex_dir)
    parts = []
    fus, fbvh = build_fuselage(M); parts.append(fus)
    dog, _ = build_doghouse(M)
    cowls = []
    for s_ in (-1, 1):
        c = rbox((1.2, 0.38, 1.1), (2.3, s_ * 1.0, 3.98), M['skin'], 0.16, name='cowl'); apply_uv(c, hull_rule(LY.COR)); cowls.append(c)
    dog = join([dog] + cowls, 'dog')
    dbvh = BVHTree.FromObject(dog, bpy.context.evaluated_depsgraph_get()); parts.append(dog)
    add_windows(M, fbvh, parts)
    add_noseteam(M, parts)
    build_doghouse_details(M, dbvh, parts)
    build_gear(M, parts); build_sponsons(M, parts); build_hoist(M, parts); build_rails(M, parts); build_tail(M, parts); build_mast(M, parts)
    rotor = build_rotor(M); rotor.name = 'cormorant_rotor0'
    tail = build_tail_rotor(M); tail.name = 'cormorant_tail0'
    winch = rbox((0.14, 0.14, 0.14), (0, 0, 0), M['dark'], 0.02, name='winch'); winch.location = Vector(WINCH); winch.name = 'cormorant_winch0'
    return fus, parts, [rotor, tail, winch], M
