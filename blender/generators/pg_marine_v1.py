"""Canadian Coast Guard fleet: icebreakers, patrol ships, science vessel, lifeboat, hovercraft.
Metres, Z up, +X is the bow, waterline at z = 0. Paint scheme only: red hull, white superstructure,
white diagonal bow bar raked forward with a narrow red bar beside it, red leaf on the funnel. No wordmarks."""
import math
from mathutils import Vector
from pg_core import *
from pg_boats import Hull, foil

CCG_RED, CCG_WHITE, CCG_BOOT, CCG_BOTTOM, DECK, GLASS = '#d52b1e', '#f1efe9', '#1d1d1f', '#6e2a22', '#6f6863', '#16222b'
ORANGE, STEEL, YELLOW = '#e86a1c', '#9aa1a8', '#e8c13a'

# ---------------------------------------------------------------- paint helpers
def cut(o, planes):
    bm = bmesh.new(); bm.from_mesh(o.data)
    for co, no in planes:
        g = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=g, plane_co=co, plane_no=no)
    bm.to_mesh(o.data); bm.free()

def paint_hull(o, L, boot=0.5, stripe_x=None, stripe_w=None, scale=1.0):
    """Recolour a built hull: bottom, boot top, red topsides, white bow bar raked forward 60 deg, thin red bar aft of it."""
    rake = math.tan(math.radians(30))           # bar at 60 deg from horizontal: x grows with z
    sw = stripe_w or max(0.6, L * 0.03)
    sx = stripe_x if stripe_x is not None else L / 2 - L * 0.2
    gap, red = sw * 0.18, sw * 0.22
    edges = [sx, sx + sw, sx - gap, sx - gap - red]
    no = Vector((1, 0, -rake)).normalized()
    cut(o, [((0, 0, 0), (0, 0, 1)), ((0, 0, boot), (0, 0, 1))] + [((e, 0, 0), tuple(no)) for e in edges])
    ms = [mat('ccg_red', CCG_RED, 0.45), mat('ccg_bottom', CCG_BOTTOM, 0.8), mat('ccg_boot', CCG_BOOT, 0.6), mat('ccg_white', CCG_WHITE, 0.4)]
    o.data.materials.clear()
    for m in ms: o.data.materials.append(m)
    bm = bmesh.new(); bm.from_mesh(o.data)
    for f in bm.faces:
        c = f.calc_center_median(); u = c.x - c.z * rake
        if c.z < 0: f.material_index = 1
        elif c.z < boot: f.material_index = 2
        elif sx < u < sx + sw: f.material_index = 3
        elif sx - gap < u < sx: f.material_index = 3 if False else 0
        elif sx - gap - red < u < sx - gap: f.material_index = 3 if False else 0
        else: f.material_index = 0
    # the narrow bar: white line aft of a red gap reads on a red hull, so paint the thin band white
    for f in bm.faces:
        c = f.calc_center_median(); u = c.x - c.z * rake
        if c.z >= boot and sx - gap - red < u < sx - gap: f.material_index = 3
    bm.to_mesh(o.data); bm.free()
    return o

LEAF = [(0, 1.0), (0.12, 0.72), (0.3, 0.8), (0.24, 0.42), (0.52, 0.6), (0.6, 0.48), (0.48, 0.2), (0.62, 0.2), (0.34, -0.06),
        (0.36, -0.22), (0.06, -0.14), (0.05, -0.5), (-0.05, -0.5), (-0.06, -0.14), (-0.36, -0.22), (-0.34, -0.06), (-0.62, 0.2),
        (-0.48, 0.2), (-0.6, 0.48), (-0.52, 0.6), (-0.24, 0.42), (-0.3, 0.8), (-0.12, 0.72)]

def leaf(size, loc, side=1, color=CCG_RED):
    """Stylised 11-point leaf, flat, facing +Y (side=1) or -Y."""
    v = [(x * size, 0, z * size) for x, z in LEAF]
    o = mesh('leaf', v, [tuple(range(len(v))) if side < 0 else tuple(reversed(range(len(v))))])
    o.data.materials.append(mat('leaf', color, 0.4))
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.to_mesh(o.data); bm.free()
    o.location = loc
    return o

# ---------------------------------------------------------------- superstructure kit
def tier(x, z, l, w, h, color=CCG_WHITE, bevel=0.08):
    return box((l, w, h), (x, 0, z + h / 2), material=mat('ss_' + color, color, 0.45), bevel=bevel)

def window_row(x, z, l, w, h, n, pitch=None, both=True, front=False):
    g = mat('glass', GLASS, 0.1, 0.2); out = []
    pitch = pitch or l / n
    for i in range(n):
        xi = x - l / 2 + pitch * (i + 0.5)
        for s in ((1, -1) if both else (1,)):
            out.append(box((pitch * 0.62, 0.04, h), (xi, s * w / 2, z), material=g))
    if front: out.append(box((0.04, w * 0.9, h), (x + l / 2, 0, z), material=g))
    return out

def bridge(x, z, l, w, h=2.6, wings=True):
    """Wheelhouse with a continuous raked window band and bridge wings."""
    out = [tier(x, z, l, w, h)]
    g = mat('glass', GLASS, 0.1, 0.2)
    out.append(box((l * 0.96, w + 0.04, h * 0.36), (x, 0, z + h * 0.62), material=g))
    out.append(box((0.3, w * 0.94, h * 0.4), (x + l / 2 + 0.05, 0, z + h * 0.62), (0, -0.25, 0), material=g))
    out.append(box((l + 0.6, w + 0.5, 0.18), (x, 0, z + h + 0.09), material=mat('ss_' + CCG_WHITE, CCG_WHITE, 0.45)))
    if wings:
        out.append(box((l * 0.45, w + 3.0, 0.25), (x + l * 0.2, 0, z + h * 0.3), material=mat('ss_' + CCG_WHITE, CCG_WHITE, 0.45)))
    return out

def funnel(x, z, l, w, h, leaf_size=None):
    out = [box((l, w, h), (x, 0, z + h / 2), material=mat('funnel_white', CCG_WHITE, 0.4), bevel=min(l, w) * 0.2)]
    out.append(box((l * 1.02, w * 1.02, h * 0.12), (x, 0, z + h * 0.94), material=mat('funnel_top', '#262626', 0.6), bevel=min(l, w) * 0.2))
    ls = leaf_size or min(l, h) * 0.32
    for s in (1, -1): out.append(leaf(ls, (x, s * (w / 2 + 0.02), z + h * 0.52), s))
    return out

def mast(x, z, h, yard=3.0, radar=True):
    m = mat('mast', CCG_WHITE, 0.45); out = [cyl(0.32, 0.18, h, 8, loc=(x, 0, z), material=m)]
    out.append(rod((x, -yard / 2, z + h * 0.72), (x, yard / 2, z + h * 0.72), 0.07, 6, m))
    if radar:
        out.append(box((0.3, yard * 0.7, 0.18), (x + 0.3, 0, z + h * 0.55), material=mat('radar', '#2b2b2b', 0.5)))
        out.append(cyl(0.45, 0.45, 0.5, 12, loc=(x, 0, z + h), material=mat('dome', '#ecebe6', 0.4)))
    return out

def crane(x, y, z, reach, ang=0.6):
    """Knuckle deck crane, slewed outboard and stowed low."""
    m = mat('crane', ORANGE, 0.45)
    out = [cyl(0.55, 0.65, 2.4, 10, loc=(x, y, z), material=m)]
    top = (x, y, z + 2.4); tip = (x - reach * 0.75, y, z + 2.4 + reach * 0.35)
    out.append(rod(top, tip, 0.28, 6, m))
    out.append(rod(tip, (tip[0], y, tip[2] - 1.6), 0.04, 4, mat('wire', '#222222', 0.6)))
    return out

def lifeboat_pair(x, z, w, l=7.0):
    m = mat('lifeboat', ORANGE, 0.5); out = []
    for s in (1, -1):
        b = box((l, 2.4, 1.6), (x, s * (w / 2 + 0.8), z + 0.9), material=m, bevel=0.6); out.append(b)
        out.append(box((l * 0.5, 2.0, 0.6), (x, s * (w / 2 + 0.8), z + 1.9), material=mat('ss_' + CCG_WHITE, CCG_WHITE, 0.45), bevel=0.25))
    return out

def helideck(x0, x1, z, w):
    out = [box((x1 - x0, w, 0.3), ((x0 + x1) / 2, 0, z + 0.15), material=mat('helideck', '#4a5257', 0.85))]
    c = ((x0 + x1) / 2, 0, z + 0.32); r = min(x1 - x0, w) * 0.36
    out.append(torus(r, 0.14, 32, 4, loc=c, material=mat('heli_mark', YELLOW, 0.5)))
    out.append(box((r * 0.9, 0.35, 0.02), c, material=mat('heli_mark', YELLOW, 0.5)))
    rm = mat('net', '#2e3236', 0.8)
    for s in (1, -1): out.append(box((x1 - x0, 0.06, 0.6), ((x0 + x1) / 2, s * w / 2, z + 0.5), material=rm))
    return out

# ---------------------------------------------------------------- the ship builder
def ccg_ship(sp, name):
    L, B, T, fb = sp['L'], sp['B'], sp['T'], sp['fb']
    h = Hull(L, B, T + fb, fb, transom=sp.get('transom', 0.72), bow_p=sp.get('bow_p', 0.75), stern_p=0.4, max_at=0.48,
             sheer_bow=sp.get('sheer_bow', 0.12), sheer_stern=0.02, rocker=0.0, forefoot=sp.get('forefoot', 0.85),
             chine=sp.get('chine', 0.35), chine_h=0.25, deadrise=0.1, flare=sp.get('flare', 0.1), S=sp.get('S', 72), K=14)
    hull = h.build(CCG_RED, CCG_BOTTOM, CCG_BOOT, None, name + '_hull')
    paint_hull(hull, L, boot=max(0.35, T * 0.12), stripe_x=L / 2 - L * sp.get('stripe_at', 0.2), stripe_w=sp.get('stripe_w', L * 0.035))
    parts = [hull, h.deck(DECK)]
    parts.append(h.rail(1.0, CCG_RED))
    dz = fb
    x = lambda t: -L / 2 + L * t
    # superstructure tiers: (t_centre, length frac, width frac, height)
    z = dz
    tiers = list(sp['tiers'])
    if L > 60: tiers = [(tiers[0][0] - 0.01, tiers[0][1] * 1.08, tiers[0][2], tiers[0][3])] + tiers   # icebreakers stand tall: one more deck
    for i, (tc, lf, wf, ht) in enumerate(tiers):
        wf = min(0.94, wf * 1.08)
        parts.append(tier(x(tc), z, L * lf, B * wf, ht))
        parts += window_row(x(tc), z + ht * 0.55, L * lf * 0.9, B * wf + 0.02, ht * 0.34, max(3, int(L * lf / 3.2)))
        z += ht
    bt, blf, bwf = sp['bridge']
    parts += bridge(x(bt), z, L * blf, B * bwf, sp.get('bridge_h', 2.8))
    ztop = z + sp.get('bridge_h', 2.8) + 0.18
    if sp.get('mast'):
        mt, mh = sp['mast']; parts += mast(x(mt), ztop, mh, yard=B * 0.35)
    for ft, fl, fw, fh, fz in sp.get('funnels', []):
        parts += funnel(x(ft), dz + fz, L * fl, B * fw, fh)
    if sp.get('heli'):
        h0, h1, hz, hw = sp['heli']; parts += helideck(x(h0), x(h1), dz + hz, B * hw)
        if sp.get('hangar'):
            ht0, ht1, hh = sp['hangar']; parts.append(tier((x(ht0) + x(ht1)) / 2, dz, x(ht1) - x(ht0), B * hw * 0.7, hh))
    for ct, cy in sp.get('cranes', []):
        parts += crane(x(ct), cy * B / 2, dz, sp.get('crane_reach', B * 0.8))
    if sp.get('lifeboats'):
        lt, lz = sp['lifeboats']; parts += lifeboat_pair(x(lt), dz + lz, B * 0.62)
    # bow and stern fittings
    bm = mat('fit', '#2b2b2b', 0.6, 0.3)
    for s in (1, -1):
        parts.append(cyl(0.5, 0.5, 0.6, 8, loc=(x(0.9), s * B * 0.15, dz), material=bm))
    parts.append(foil(T * 0.6, T * 0.5, T * 0.7, -L / 2 + L * 0.03, -T * 0.55, 0.15, 0.0, mat('rud', CCG_BOTTOM, 0.6), 'rudder'))
    for extra in sp.get('extras', []): parts += extra(L, B, T, fb, x)
    o = join(parts, name)
    return o

# ---------------------------------------------------------------- the fleet (principal dimensions from published data, layouts stylised)
def deck_cargo(L, B, T, fb, x):
    m = mat('container', '#2f5d46', 0.6)
    return [box((6.1, 2.44, 2.6), (x(0.78), s * 1.5, fb + 1.3), material=m, bevel=0.03) for s in (1, -1)]

def sci_aframe(L, B, T, fb, x):
    m = mat('crane', ORANGE, 0.45)
    out = [rod((x(0.02), s * B * 0.35, fb), (x(0.0), s * B * 0.3, fb + 6), 0.3, 6, m) for s in (1, -1)]
    out.append(rod((x(0.0), -B * 0.3, fb + 6), (x(0.0), B * 0.3, fb + 6), 0.3, 6, m))
    return out

FLEET = {
    'louis_st_laurent': dict(L=119.8, B=24.4, T=9.9, fb=6.5, sheer_bow=0.18, forefoot=1.1, bow_p=0.7, stripe_at=0.17,
        tiers=[(0.6, 0.34, 0.8, 3.0), (0.62, 0.28, 0.75, 2.8), (0.64, 0.22, 0.7, 2.8)], bridge=(0.66, 0.15, 0.78), mast=(0.66, 9),
        funnels=[(0.42, 0.07, 0.16, 9.5, 2.0)], heli=(0.08, 0.3, 3.2, 0.8), hangar=(0.3, 0.42, 6.0), cranes=[(0.84, 0.6), (0.84, -0.6)],
        lifeboats=(0.48, 3.0), crane_reach=14),
    'arpatuuq': dict(L=138.5, B=29.4, T=10.5, fb=7.5, sheer_bow=0.18, forefoot=1.1, bow_p=0.62, stripe_at=0.16,
        tiers=[(0.62, 0.4, 0.86, 3.2), (0.64, 0.34, 0.8, 3.0), (0.66, 0.28, 0.74, 3.0), (0.67, 0.2, 0.68, 3.0)], bridge=(0.69, 0.12, 0.84),
        mast=(0.67, 11), funnels=[(0.44, 0.06, 0.12, 8.0, 12.0)], heli=(0.06, 0.28, 3.4, 0.8), hangar=(0.28, 0.4, 6.4),
        cranes=[(0.88, 0.55), (0.12, -0.6)], lifeboats=(0.52, 3.2), crane_reach=16),
    'terry_fox': dict(L=88.0, B=17.8, T=8.3, fb=5.5, sheer_bow=0.16, forefoot=1.0, bow_p=0.72, stripe_at=0.2,
        tiers=[(0.7, 0.3, 0.82, 2.8), (0.72, 0.22, 0.76, 2.8)], bridge=(0.74, 0.14, 0.82), mast=(0.72, 7),
        funnels=[(0.52, 0.07, 0.14, 7.0, 4.0), (0.52, 0.07, 0.14, 7.0, 4.0)], cranes=[(0.3, 0.55)], lifeboats=(0.58, 2.8), crane_reach=10,
        extras=[lambda L, B, T, fb, x: [box((L * 0.2, B * 0.5, 0.6), (x(0.12), 0, fb + 0.3), material=mat('tow', '#3a3a3a', 0.6))]]),
    'pierre_radisson': dict(L=98.3, B=19.5, T=7.2, fb=5.8, sheer_bow=0.15, forefoot=1.0, bow_p=0.72, stripe_at=0.19,
        tiers=[(0.6, 0.36, 0.84, 2.9), (0.62, 0.28, 0.78, 2.8), (0.64, 0.2, 0.72, 2.8)], bridge=(0.66, 0.14, 0.82), mast=(0.65, 8),
        funnels=[(0.45, 0.08, 0.14, 8.0, 5.7)], heli=(0.06, 0.32, 2.8, 0.82), cranes=[(0.86, 0.5)], lifeboats=(0.5, 2.9), crane_reach=12),
    'capt_molly_kool': dict(L=83.7, B=18.0, T=7.2, fb=5.2, sheer_bow=0.14, forefoot=0.95, bow_p=0.8, stripe_at=0.22,
        tiers=[(0.76, 0.24, 0.86, 2.8), (0.78, 0.18, 0.8, 2.8)], bridge=(0.79, 0.14, 0.86), mast=(0.79, 7),
        funnels=[(0.66, 0.04, 0.1, 6.0, 5.6), (0.66, 0.04, 0.1, 6.0, 5.6)], cranes=[(0.4, 0.6)], crane_reach=12,
        extras=[lambda L, B, T, fb, x: [box((L * 0.34, B * 0.86, 0.3), (x(0.3), 0, fb + 0.15), material=mat('workdeck', '#5d5751', 0.9))]]),
    'martha_l_black': dict(L=83.0, B=16.2, T=6.1, fb=5.0, sheer_bow=0.14, forefoot=0.85, bow_p=0.75, stripe_at=0.2,
        tiers=[(0.62, 0.3, 0.84, 2.8), (0.64, 0.22, 0.78, 2.8)], bridge=(0.66, 0.14, 0.82), mast=(0.65, 7),
        funnels=[(0.44, 0.07, 0.14, 6.0, 5.6)], heli=(0.06, 0.28, 2.8, 0.82), hangar=(0.28, 0.38, 5.6), cranes=[(0.86, 0.5)],
        lifeboats=(0.5, 2.8), crane_reach=10),
    'donjek_aops': dict(L=103.6, B=19.0, T=5.7, fb=6.0, sheer_bow=0.1, forefoot=0.7, bow_p=0.85, flare=0.14, stripe_at=0.2,
        tiers=[(0.63, 0.36, 0.86, 3.0), (0.66, 0.26, 0.8, 2.9)], bridge=(0.7, 0.13, 0.84), mast=(0.62, 12),
        funnels=[(0.46, 0.05, 0.1, 5.5, 5.9), (0.46, 0.05, 0.1, 5.5, 5.9)], heli=(0.06, 0.3, 3.0, 0.8), hangar=(0.3, 0.44, 5.9),
        lifeboats=(0.55, 3.0), extras=[deck_cargo]),
    'sir_john_franklin': dict(L=63.4, B=16.0, T=5.8, fb=4.2, sheer_bow=0.16, forefoot=0.6, bow_p=0.9, chine=0.2, stripe_at=0.2,
        tiers=[(0.7, 0.4, 0.86, 2.8), (0.73, 0.3, 0.8, 2.7)], bridge=(0.78, 0.16, 0.84), mast=(0.75, 8),
        funnels=[(0.5, 0.06, 0.12, 4.5, 5.5)], cranes=[(0.4, -0.6)], lifeboats=(0.6, 2.8), crane_reach=9, extras=[sci_aframe]),
    'hero_class': dict(L=42.8, B=7.0, T=2.8, fb=2.4, transom=0.85, sheer_bow=0.18, forefoot=0.5, bow_p=1.1, chine=1.0, flare=0.08, S=56,
        stripe_at=0.26, stripe_w=1.6, tiers=[(0.62, 0.32, 0.84, 2.4)], bridge=(0.66, 0.2, 0.8), bridge_h=2.2, mast=(0.6, 6),
        lifeboats=None),
}

def ship(key, name=None):
    return ccg_ship(FLEET[key], name or key)

# ---------------------------------------------------------------- small craft
def bay_lifeboat(name='bay_class'):
    """19 m self-righting lifeboat: deep-vee hull, tall enclosed wheelhouse, roll-over mast."""
    L, B, T, fb = 19.0, 6.3, 1.67, 1.5
    h = Hull(L, B, T + fb, fb, transom=0.85, bow_p=1.0, stern_p=0.3, max_at=0.45, sheer_bow=0.22, sheer_stern=0.02, rocker=0.0,
             forefoot=0.45, chine=1.0, chine_h=0.3, deadrise=0.45, flare=0.1, S=48, K=12)
    hull = paint_hull(h.build(CCG_RED, CCG_BOTTOM, CCG_BOOT, None, name + '_hull'), L, boot=0.25, stripe_x=L / 2 - 4.6, stripe_w=1.0)
    parts = [hull, h.deck(DECK), h.rail(0.9, CCG_WHITE)]
    parts.append(tier(0.4, fb, 9.0, B * 0.84, 2.0, bevel=0.3))
    parts.append(tier(0.9, fb + 2.0, 5.5, B * 0.74, 1.8, bevel=0.25))
    parts += window_row(0.9, fb + 2.9, 5.0, B * 0.74 + 0.02, 0.8, 4, front=True)
    parts.append(box((0.6, B * 0.62, 0.9), (3.6, 0, fb + 2.9), (0, -0.5, 0), material=mat('glass', GLASS, 0.1, 0.2)))
    parts += window_row(0.4, fb + 1.1, 8.0, B * 0.84 + 0.02, 0.5, 6)
    m = mat('mast', CCG_WHITE, 0.45)
    for s in (1, -1): parts.append(rod((-1.8, s * 1.8, fb + 3.8), (-0.6, s * 1.2, fb + 6.4), 0.12, 6, m))
    parts.append(rod((-0.6, -1.2, fb + 6.4), (-0.6, 1.2, fb + 6.4), 0.12, 6, m))
    parts.append(cyl(0.3, 0.3, 0.3, 10, loc=(-0.6, 0, fb + 6.45), material=mat('dome', '#ecebe6', 0.4)))
    parts.append(box((1.2, 3.0, 0.5), (-L / 2 + 2.0, 0, fb + 0.25), material=mat('davit', ORANGE, 0.5)))      # recovery cradle
    return join(parts, name)

def hovercraft(name='hovercraft'):
    """Griffon 8000TD class: black skirt, red/white body, cabin forward, twin ducted propellers aft."""
    L, B = 28.5, 12.0
    parts = []
    sk = mat('skirt', '#1b1b1c', 0.95)
    # skirt as a squashed rounded box ring
    parts.append(box((L, B, 1.6), (0, 0, 0.8), material=sk, bevel=0.3))
    parts.append(box((L - 1.0, B - 1.0, 0.6), (0, 0, 1.85), material=mat('ccg_red', CCG_RED, 0.45), bevel=0.25))
    parts.append(box((L - 2.0, B - 2.0, 0.15), (0, 0, 2.2), material=mat('deck', DECK, 0.85)))
    parts.append(tier(4.5, 2.2, 13.0, 7.4, 2.4, bevel=0.35))
    parts += window_row(4.5, 3.6, 12.0, 7.42, 0.8, 8)
    parts.append(box((0.6, 6.6, 0.9), (11.0, 0, 3.6), (0, -0.4, 0), material=mat('glass', GLASS, 0.1, 0.2)))
    parts += bridge(7.6, 4.6, 4.0, 4.0, 1.8, wings=False)
    for s in (1, -1):
        y = s * 3.1
        parts.append(torus(1.9, 0.28, 24, 6, loc=(-11.0, y, 4.6), rot=(0, math.pi / 2, 0), material=mat('duct', CCG_WHITE, 0.4)))
        pm = mat('prop', '#3a3a3a', 0.5)
        parts.append(box((0.2, 0.18, 3.5), (-10.9, y, 4.6), (0.4, 0, 0), material=pm)); parts.append(box((0.2, 0.18, 3.5), (-10.9, y, 4.6), (-1.17, 0, 0), material=pm))
        parts.append(box((0.6, 0.5, 0.5), (-10.9, y, 4.6), material=pm))
        parts.append(box((1.0, 0.1, 3.4), (-12.4, y, 4.6), material=mat('ccg_red', CCG_RED, 0.45)))                  # rudder vanes
        parts.append(box((1.4, 0.6, 2.2), (-11.0, y, 3.1), material=mat('ss_' + CCG_WHITE, CCG_WHITE, 0.45)))
    for s in (1, -1): parts.append(leaf(0.7, (-6.0, s * (B / 2 - 0.48), 1.85), s, CCG_WHITE))
    return join(parts, name)

ALL = list(FLEET) + ['bay_class', 'hovercraft']

def build(key):
    if key == 'bay_class': return bay_lifeboat()
    if key == 'hovercraft': return hovercraft()
    return ship(key)
