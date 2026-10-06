"""Canadair CL-415 amphibious water bomber.
Modelled from Wikimedia Commons photographs (side, front three-quarter, belly) and published dimensions: length 19.82 m, span 28.60 m, two PW123AF turboprops with
3.97 m four-blade propellers, a boat hull with a step, high wing on a short pylon, wing-tip floats on struts, a swept fin with a mid-set tailplane carrying end plates.
Livery after the Newfoundland and Labrador aircraft: orange, green band over a grey planing bottom, white bands on the fin.
Z up, nose +X, starboard -Y, keel at z = 0 (the wheels hang below it). Propellers are separate objects whose ORIGIN is the hub, named cl415_prop0 / cl415_prop1.
"""
import math, os
from mathutils import Vector, Matrix
import bmesh
from air_common import *
import air_layout as LY

NAC_X = 5.7                # propeller hub x
NAC_Y = 3.65
HUB_Z = 3.85
WING_Z = 3.3

def materials(tex_dir):
    M = {}
    M['skin'] = tex_mat('cl_skin', os.path.join(tex_dir, 'cl415_livery.jpg'), os.path.join(tex_dir, 'cl415_normal.png'), rough=0.4, nstr=1.0)
    M['glass'] = mat('cl_glass', '#14222f', 0.05, 0.0)
    M['rubber'] = mat('cl_rubber', '#15171a', 0.78, 0.0)
    M['steel'] = mat('cl_steel', '#8b9197', 0.34, 0.85)
    M['dark'] = mat('cl_darkmetal', '#2b2f33', 0.5, 0.55)
    M['silver'] = mat('cl_silver', '#c3c8cc', 0.28, 0.95)
    M['orange'] = mat('cl_orange', '#e2571a', 0.4, 0.0)
    M['white'] = mat('cl_white', '#eceae2', 0.42, 0.0)
    M['green'] = mat('cl_green', '#1f6b49', 0.42, 0.0)
    M['grey'] = mat('cl_grey', '#8d949b', 0.5, 0.15)
    M['tyre'] = mat('cl_tyre', '#0f1113', 0.92, 0.0)
    M['blade'] = mat('cl_blade', '#1b1d20', 0.4, 0.3)
    M['bladetip'] = mat('cl_bladetip', '#ece9de', 0.4, 0.0)
    M['radome'] = mat('cl_radome', '#17191b', 0.3, 0.0)
    M['lens'] = mat('cl_lens', '#c9ced2', 0.12, 0.0)
    M['red'] = mat('cl_red', '#b3232b', 0.35, 0.0)
    M['disc'] = mat('propdisc', '#ffffff', 0.5, alpha=0.04)
    return M

# ------------------------------------------------------------------ hull
def hull_keys():
    K = {}
    K['zt'] = make_interp([(-9.9, 3.45), (-9.5, 3.4), (-7, 3.32), (-4, 3.08), (-2, 2.97), (1, 2.9), (3.5, 2.88), (5.5, 2.84), (6.6, 2.78), (7.6, 2.55), (8.3, 2.22), (8.9, 1.85), (9.3, 1.58), (9.55, 1.38), (9.62, 1.2)])
    K['zb'] = make_interp([(-9.9, 1.7), (-8, 1.32), (-5, 0.8), (-2.5, 0.36), (-1.45, 0.24), (-1.3, 0.05), (-1.0, 0.0), (7.2, 0.0), (8.4, 0.08), (9.0, 0.3), (9.4, 0.62), (9.6, 0.88), (9.62, 1.0)])
    K['w'] = make_interp([(-9.9, 0.3), (-9.5, 0.4), (-8, 0.66), (-6, 1.0), (-3, 1.3), (0, 1.38), (4, 1.36), (6.5, 1.3), (8.0, 1.12), (8.9, 0.86), (9.35, 0.58), (9.55, 0.34), (9.62, 0.06)])
    K['rt'] = make_interp([(-9.9, 0.25), (-6, 0.5), (0, 0.6), (6.5, 0.55), (9.0, 0.35), (9.62, 0.1)])
    K['rb'] = make_interp([(-9.9, 0.2), (-4, 0.3), (0, 0.36), (6, 0.36), (8.5, 0.3), (9.62, 0.1)])
    K['cr'] = make_interp([(-9.9, 0.0), (-4, 0.06), (0, 0.1), (6, 0.08), (9.0, 0.02), (9.62, 0.0)])
    K['vee'] = make_interp([(-9.9, 0.02), (-4, 0.12), (-1.4, 0.18), (-1.2, 0.34), (0, 0.38), (4, 0.34), (7.5, 0.22), (9.0, 0.08), (9.62, 0.0)])
    return K

def build_hull(M):
    K = hull_keys()
    sec = lambda x: rr_ring(K['zt'](x), K['zb'](x), K['w'](x), K['rt'](x), K['rb'](x), K['cr'](x), nb=4, ncb=4, ns=5, nct=6, nt=7, vee=K['vee'](x))
    xs = cluster(-9.9, 9.62, 118, 0.7, 0.9)
    # a pair of stations close together makes the step crisp
    xs = sorted(set(xs + [-1.45, -1.3]))
    o, bvh = hull_loft(xs, sec, 'fus', M['skin'], True, True)
    apply_uv(o, hull_rule(LY.CL))
    return o, bvh

def build_pylon(M):
    zt = 3.38; sec = lambda x: rr_ring(zt, 2.7, 0.95 * min(1, (4.6 - x) / 0.8) * min(1, (x + 0.2) / 0.7) + 0.05, 0.35, 0.05, 0.0, nb=3, ncb=2, ns=3, nct=5, nt=5)
    o, bvh = hull_loft(cluster(-0.2, 4.6, 20, 0.7, 0.7), sec, 'pylon', M['skin'], True, True)
    apply_uv(o, hull_rule(LY.CL)); return o

# ------------------------------------------------------------------ windows and hull details
def hull_details(M, bvh, parts):
    gl, fr, dk, st, rub = M['glass'], M['rubber'], M['dark'], M['steel'], M['rubber']
    # windscreen: two panes with a centre post on the raked nose
    rdv = Vector((-0.55, 0.0, -0.83)).normalized(); ex = Vector((0, 1, 0)); ey = rdv.cross(ex) * -1
    for u in (0.44, -0.44):
        parts.extend(window(bvh, Vector((8.1, 0, 2.5)) + ex * u, ex, ey, rdv, 0.8, 0.7, 0.15, gl, fr, 0.03, 0.01, 0.024, 2, False, 'screen'))
    for s in (-1, 1):
        ex1, ey1, rd1 = Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, -s, 0))
        def wn(x, z, w, h, r=0.1, round_=False, rdv=None, name='win'):
            parts.extend(window(bvh, Vector((x, s * 3.0, z)), ex1, ey1, rdv or rd1, w, h, r, gl, fr, 0.03, 0.01, 0.022, 2, round_, name))
        tilt = Vector((-0.12, -s * 0.9, -0.42)).normalized()
        wn(7.55, 2.35, 0.78, 0.55, 0.14, rdv=tilt); wn(6.55, 2.38, 0.78, 0.55, 0.14, rdv=tilt)          # cockpit side windows
        wn(-0.85, 1.85, 0.42, 0.42, round_=True)                                                       # porthole
        wn(-2.35, 2.0, 0.34, 0.5, 0.08)                                                                # window in the rear door
        wn(3.3, 1.75, 0.22, 0.34, 0.06)                                                                # small cabin window
    # radome on the nose tip
    parts.append(revolve([(0.0, 0.0), (0.34, 0.0), (0.4, 0.1), (0.34, 0.24), (0.18, 0.36), (0.0, 0.4)], (9.56, 0, 1.2), (1, 0, 0), 24, M['radome'], 'radome'))
    parts.append(revolve([(0.0, 0.0), (0.36, 0.0), (0.4, 0.05)], (9.52, 0, 1.2), (1, 0, 0), 24, M['rubber'], 'radomering'))
    # pitot tubes and a nose-mounted light
    for s in (-1, 1): parts.append(tube((8.5, s * 0.78, 1.95), (9.2, s * 0.62, 2.0), 0.014, 5, st, 'pitot'))
    # cockpit wipers
    for u in (0.4, -0.4): parts.append(tube((8.3, u * 0.9, 1.95), (8.0, u * 0.5 + 0.1, 2.5), 0.008, 4, rub, 'wiper'))
    # belly: two scoop doors and the step reinforcement; spray rails along the bow chines
    for s in (-1, 1):
        parts.append(rbox((1.3, 0.34, 0.07), (1.2, s * 0.62, 0.03), M['dark'], 0.02, name='scoopdoor'))
        parts.append(rbox((2.3, 0.1, 0.1), (7.8, s * 0.98, 0.55), M['grey'], 0.03, name='sprayrail'))
    parts.append(rbox((0.14, 1.5, 0.08), (-1.28, 0, 0.1), M['grey'], 0.02, name='stepplate'))
    # dorsal blade aerial, beacon, belly blade aerial
    parts.append(rbox((0.36, 0.035, 0.3), (5.2, 0, 3.0), M['white'], 0.01, name='aerial')); parts.append(rbox((0.3, 0.03, 0.26), (-3.0, 0, 3.1), M['white'], 0.01, name='aerial'))
    parts.append(rbox((0.2, 0.2, 0.1), (2.2, 0, 3.4), M['red'], 0.03, name='beacon'))
    parts.append(rbox((0.3, 0.025, 0.24), (-5.0, 0, 0.7), M['white'], 0.01, name='aerial'))
    # door handles and hatches are in the paint; a retractable boarding step below the front door
    parts.append(rbox((0.4, 0.1, 0.03), (5.8, 1.28, 0.62), M['steel'], 0.01, name='step'))

# ------------------------------------------------------------------ wing, floats, nacelles
def build_wing(M, parts):
    R = LY.CL
    secs = [dict(y=0.0, xle=4.1, chord=3.55, t=0.15, z=WING_Z), dict(y=3.65, xle=4.05, chord=3.4, t=0.14, z=WING_Z), dict(y=9.0, xle=3.95, chord=2.95, t=0.125, z=WING_Z + 0.05), dict(y=13.9, xle=3.85, chord=2.5, t=0.11, z=WING_Z + 0.15), dict(y=14.3, xle=3.82, chord=2.35, t=0.1, z=WING_Z + 0.16)]
    for s in (-1, 1):
        w = wing([dict(secs_, y=s * secs_['y']) for secs_ in secs], M['skin'], 'wing', 16, 4)
        def rule(c, n):
            return (R['wtop'] if n.z >= 0 else R['wbot']), (lambda co: (co.y, co.x))
        apply_uv(w, rule); parts.append(w)
        # tip floats on a pair of struts
        fy = s * 13.1
        parts.append(revolve([(0.0, 0.0), (0.28, 0.25), (0.4, 0.9), (0.4, 1.9), (0.3, 2.6), (0.12, 3.0), (0.0, 3.1)], (0.55, fy, 2.15), (1, 0, 0), 22, M['orange'], 'float'))
        parts.append(revolve([(0.0, 0.0), (0.2, 0.0), (0.41, 0.06)], (0.55, fy, 2.15), (1, 0, 0), 22, M['red'], 'floatnose'))
        parts.append(tube((1.55, fy, WING_Z - 0.15), (1.5, fy, 2.4), 0.055, 8, M['steel'], 'floatstrut')); parts.append(tube((2.55, fy, WING_Z - 0.12), (2.3, fy, 2.45), 0.055, 8, M['steel'], 'floatstrut2'))
        parts.append(tube((1.55, fy, 2.35), (2.4, fy, 2.35), 0.035, 6, M['steel'], 'floatbrace'))
        parts.append(rbox((1.6, 0.16, 0.14), (1.9, fy, 2.4), M['orange'], 0.04, name='floatfairing'))
        # wing tip cap and nav light
        parts.append(rbox((0.2, 0.12, 0.1), (3.7, s * 14.38, WING_Z + 0.16), M['red'] if s > 0 else M['green'], 0.03, name='navlight'))
        # pitot on the wing leading edge, stall strip
        # flap track fairings under the trailing edge, landing light in the leading edge
        for yy in (2.7, 5.6, 8.0):
            te = (4.1 - 0.0 * yy) - (3.55 - 0.0 * yy) if False else None
            xle_ = 4.1 - 0.0055 * yy * 4; ch_ = 3.55 - 0.1 * yy * 0.47
            parts.append(rbox((1.1, 0.16, 0.15), (xle_ - ch_ + 0.35, s * yy, WING_Z - 0.2), M['orange'], 0.05, name='flaptrack'))
        parts.append(rbox((0.08, 0.5, 0.3), (4.12, s * 6.4, WING_Z - 0.02), M['lens'], 0.02, name='landinglight'))

def build_nacelles(M, parts):
    R = LY.CL
    rr = make_interp([(-1.4, 0.16), (-1.0, 0.32), (-0.2, 0.5), (1.0, 0.64), (3.0, 0.66), (4.4, 0.54), (5.0, 0.44), (5.55, 0.37)])
    for s in (-1, 1):
        sec = lambda x, s=s: ring_ellipse(HUB_Z + rr(x) * 0.95, HUB_Z - rr(x) * 0.9, rr(x), 2.5, 36, yoff=s * NAC_Y)
        o = hull_loft(cluster(-1.4, 5.55, 36, 0.7, 0.5), sec, 'nacelle', M['skin'], True, False)
        reg = R['nac_sb'] if s < 0 else R['nac_pt']; orange = solid_region(LY.CL_SOLID['orange'])
        def rule(c, n, s=s, reg=reg):
            if abs(n.y) > 0.45 and (n.y * s > 0): return reg, (lambda co: (co.x, co.z))
            return orange, (lambda co: (0.5, 0.5))
        apply_uv(o, rule); parts.append(o)
        # intake chin under the front of the nacelle, exhaust stacks on the rear flanks
        parts.append(rbox((0.9, 0.55, 0.3), (4.55, s * NAC_Y, HUB_Z - 0.62), M['orange'], 0.08, name='chin'))
        parts.append(rbox((0.5, 0.42, 0.06), (4.9, s * NAC_Y, HUB_Z - 0.78), M['dark'], 0.02, name='intakemouth'))
        for k, off in enumerate((-1, 1)):
            a = Vector((0.3 - 0.0 * k, s * NAC_Y + off * 0.22, HUB_Z + 0.5)); d = Vector((-0.55, off * 0.5, 0.2)).normalized()
            parts.append(revolve([(0.12, 0.0), (0.135, 0.3), (0.13, 0.6), (0.0, 0.58)], a, d, 14, M['silver'], 'exhaust'))
        # oil cooler scoop and cowling latches
        parts.append(rbox((0.5, 0.3, 0.14), (1.2, s * NAC_Y, HUB_Z + 0.58), M['orange'], 0.05, name='scoop'))
        # prop shaft housing behind the spinner
        parts.append(revolve([(0.34, 0.0), (0.36, 0.1)], (5.5, s * NAC_Y, HUB_Z), (1, 0, 0), 20, M['dark'], 'shaftring'))

def build_props(M):
    props = []
    for k, s in enumerate((-1, 1)):
        bl = []
        for i in range(4):
            a = i * PI / 2 + 0.3
            secs = [dict(y=0.34, xle=0.12, chord=0.3, t=0.2, z=0.0, tw=0.55), dict(y=0.8, xle=0.14, chord=0.38, t=0.12, z=0.0, tw=0.42), dict(y=1.4, xle=0.13, chord=0.36, t=0.085, z=0.0, tw=0.28), dict(y=1.9, xle=0.1, chord=0.28, t=0.07, z=0.0, tw=0.2), dict(y=1.98, xle=0.08, chord=0.2, t=0.06, z=0.0, tw=0.2)]
            b = wing(secs, M['blade'], 'pb', 10, 3)
            b.data.materials.append(M['bladetip']); idx = len(b.data.materials) - 1
            for p in b.data.polygons:
                if p.center.y > 1.7: p.material_index = idx
            b.data.transform(Matrix.Rotation(PI / 2, 4, 'X')); b.data.transform(Matrix.Rotation(a, 4, 'X')); bl.append(b)
            cuff = rbox((0.22, 0.18, 0.32), (0.0, 0.0, 0.34), M['dark'], 0.05, name='cuff'); cuff.data.transform(Matrix.Rotation(a, 4, 'X')); bl.append(cuff)
        bl.append(revolve([(0.0, 0.0), (0.3, 0.0), (0.33, 0.12), (0.3, 0.4), (0.18, 0.62), (0.0, 0.76)], (-0.02, 0, 0), (1, 0, 0), 24, M['white'], 'spinner'))
        bl.append(cyl(1.98, 1.98, 0.01, 40, loc=(0.2, 0, 0), rot=(0, PI / 2, 0), material=M['disc'], name='disc'))
        o = join(bl, 'prop'); o.location = Vector((NAC_X, s * NAC_Y, HUB_Z)); o.name = f'cl415_prop{k}'; props.append(o)
    return props

# ------------------------------------------------------------------ tail
def build_tail(M, parts):
    R = LY.CL
    secs = [dict(z=2.75, xle=-4.75, chord=5.3, t=0.12), dict(z=4.4, xle=-5.9, chord=4.1, t=0.115), dict(z=6.4, xle=-7.35, chord=2.7, t=0.1), dict(z=8.3, xle=-8.5, chord=1.55, t=0.085), dict(z=8.42, xle=-8.55, chord=1.4, t=0.07)]
    f = fin(secs, M['skin'], 'fin', 16, 4)
    def rule(c, n): return (R['fin'] if c.y < 0 else R['fin2']), (lambda co: (co.x, co.z))
    apply_uv(f, rule); parts.append(f)
    # tailplane: mid-set and swept, with end plates
    for s in (-1, 1):
        tp = wing([dict(y=0.0, xle=-6.55, chord=3.0, t=0.11, z=4.95), dict(y=s * 2.4, xle=-6.95, chord=2.4, t=0.1, z=4.95), dict(y=s * 4.55, xle=-7.5, chord=1.75, t=0.09, z=4.95)], M['skin'], 'tailplane', 14, 3)
        apply_uv(tp, lambda c, n: (R['tail'], lambda co: (co.y, co.x))); parts.append(tp)
        ep = fin([dict(z=4.55, xle=-7.7, chord=1.45, t=0.07, y=s * 4.6), dict(z=5.0, xle=-7.6, chord=1.55, t=0.08, y=s * 4.6), dict(z=5.75, xle=-7.95, chord=1.1, t=0.06, y=s * 4.6)], M['skin'], 'endplate', 12, 2)
        apply_uv(ep, lambda c, n: (solid_region(LY.CL_SOLID['orange']), lambda co: (0.5, 0.5))); parts.append(ep)
    parts.append(rbox((0.2, 0.2, 0.12), (-9.95, 0, 8.45), M['white'], 0.03, name='strobe'))
    parts.append(rbox((0.14, 0.1, 0.1), (-10.12, 0, 3.4), M['lens'], 0.02, name='taillight'))
    # dorsal fin fillet and fin root fairing
    fil = rbox((3.2, 0.7, 0.35), (-6.0, 0, 3.15), M['orange'], 0.14, name='finfillet'); parts.append(fil)

# ------------------------------------------------------------------ gear
def build_gear(M, parts):
    tyr, hub, st, dk = M['tyre'], M['steel'], M['steel'], M['dark']
    nx = 7.6
    parts.append(rbox((0.9, 0.55, 0.25), (nx, 0, 0.12), M['dark'], 0.06, name='nosegearbay'))
    parts.append(tube((nx, 0, 0.1), (nx, 0, -0.55), 0.09, 10, st, 'noseleg'))
    parts.append(tube((nx, 0, -0.05), (nx + 0.35, 0, -0.45), 0.045, 6, dk, 'noselink'))
    parts.append(tube((nx, -0.3, -0.62), (nx, 0.3, -0.62), 0.04, 8, st, 'noseaxle'))
    for dy in (-0.14, 0.14): parts.append(tyre(nx, dy, -0.62, 0.38, 0.17, tyr, hub, 'nosewheel'))
    for s in (-1, 1):
        mx, my = 0.85, s * 1.62
        parts.append(rbox((1.9, 0.5, 0.6), (mx - 0.2, s * 1.22, 0.42), M['orange'], 0.2, name='gearfairing'))
        parts.append(tube((mx, my, 0.5), (mx, my, -0.45), 0.12, 10, st, 'mainleg'))
        parts.append(tube((mx + 0.5, s * 1.45, 0.45), (mx, my, -0.2), 0.05, 6, dk, 'maindrag'))
        parts.append(tube((mx - 0.5, s * 1.35, 0.5), (mx, my, -0.25), 0.05, 6, dk, 'maindrag2'))
        parts.append(tube((mx, my - 0.2, -0.52), (mx, my + 0.28, -0.52), 0.05, 8, st, 'mainaxle'))
        parts.append(tyre(mx, my + 0.1, -0.52, 0.56, 0.3, tyr, hub, 'mainwheel'))
        parts.append(rbox((0.5, 0.1, 0.1), (mx, my + 0.3, -0.12), dk, 0.02, name='brakeline'))

# ------------------------------------------------------------------ assemble
def build(tex_dir):
    M = materials(tex_dir)
    parts = []
    hull, bvh = build_hull(M); parts.append(hull)
    parts.append(build_pylon(M))
    hull_details(M, bvh, parts)
    build_wing(M, parts); build_nacelles(M, parts); build_tail(M, parts); build_gear(M, parts)
    props = build_props(M)
    return hull, parts, props, M
