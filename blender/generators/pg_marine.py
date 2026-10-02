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
    """Recolour a built hull: bottom, boot top, red topsides, and the Coast Guard diagonal: ONE wide white bar edged by thin dark lines,
    raked 60 degrees (top toward the bow). stripe_x is the bar's centre at the waterline, stripe_w its width along the hull.
    Measured from photographs: the bar is 6 to 12 percent of the hull length wide and sits between 28 and 70 percent back from the bow."""
    rake = math.tan(math.radians(30))           # bar at 60 deg from horizontal: x grows with z
    sw = stripe_w or L * 0.08
    sx = stripe_x if stripe_x is not None else L / 2 - L * 0.4
    line = max(0.12, L * 0.0032)
    u0, u1 = sx - sw / 2, sx + sw / 2
    edges = [u0 - line, u0, u1, u1 + line]
    no = Vector((1, 0, -rake)).normalized()
    cut(o, [((0, 0, 0), (0, 0, 1)), ((0, 0, boot), (0, 0, 1))] + [((e, 0, 0), tuple(no)) for e in edges])
    ms = [mat('ccg_red', CCG_RED, 0.45), mat('ccg_bottom', CCG_BOTTOM, 0.8), mat('ccg_boot', CCG_BOOT, 0.6), mat('ccg_white', CCG_WHITE, 0.4), mat('ccg_line', '#2a1d1d', 0.6)]
    o.data.materials.clear()
    for m in ms: o.data.materials.append(m)
    bm = bmesh.new(); bm.from_mesh(o.data)
    for f in bm.faces:
        c = f.calc_center_median(); u = c.x - c.z * rake
        if c.z < 0: f.material_index = 1
        elif c.z < boot: f.material_index = 2
        elif u0 < u < u1: f.material_index = 3
        elif u0 - line < u < u0 or u1 < u < u1 + line: f.material_index = 4
        else: f.material_index = 0
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

def funnel(x, z, l, w, h, leaf_size=None, y=0.0, black=False):
    body = mat('funnel_black', '#222222', 0.6) if black else mat('funnel_white', CCG_WHITE, 0.4)
    out = [box((l, w, h), (x, y, z + h / 2), material=body, bevel=min(l, w) * 0.2)]
    out.append(box((l * 1.02, w * 1.02, h * 0.12), (x, y, z + h * 0.94), material=mat('funnel_top', '#262626', 0.6), bevel=min(l, w) * 0.2))
    if not black:
        ls = leaf_size or min(l, h) * 0.32
        for s in (1, -1): out.append(leaf(ls, (x, y + s * (w / 2 + 0.02), z + h * 0.52), s))
    return out

def mast(x, z, h, yard=3.0, radar=True, color=None):
    m = mat('mast_' + (color or CCG_WHITE), color or CCG_WHITE, 0.45); r = max(0.32, h * 0.03)
    out = [cyl(r, r * 0.55, h, 8, loc=(x, 0, z), material=m)]
    out.append(rod((x, -yard / 2, z + h * 0.72), (x, yard / 2, z + h * 0.72), 0.09, 6, m))
    if radar:
        out.append(box((0.3, yard * 0.7, 0.18), (x + 0.3, 0, z + h * 0.55), material=mat('radar', '#2b2b2b', 0.5)))
        out.append(cyl(0.5, 0.5, 0.55, 12, loc=(x, 0, z + h), material=mat('dome', '#ecebe6', 0.4)))
    return out

def crane(x, y, z, reach, d=-1):
    """Knuckle deck crane, slewed fore (d=+1) or aft (d=-1) and stowed low."""
    m = mat('crane', ORANGE, 0.45)
    out = [cyl(0.55, 0.65, 2.4, 10, loc=(x, y, z), material=m)]
    top = (x, y, z + 2.4); tip = (x + d * reach * 0.75, y, z + 2.4 + reach * 0.35)
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

# ---------------------------------------------------------------- the ship builder (v2)
# Layouts are MEASURED from side-on photographs of the real ships. Every position is a fraction of hull length counted from the BOW
# (b = 0 at the stem, 1 at the transom), so a spec reads like a general arrangement drawing. Heights and sizes are metres.
def X(L, b): return L / 2 - L * b

def tier_box(L, B, z, h, b0, b1, wf, bevel=0.3):
    return tier((X(L, b0) + X(L, b1)) / 2, z, (b1 - b0) * L, B * wf, h, bevel=bevel)

def bridge_deck(L, B, z, h, b0, b1, wf, wing=0.9):
    """Top tier: wheelhouse with a raked front window band, side windows, a roof overhang and bridge wings."""
    xc = (X(L, b0) + X(L, b1)) / 2; l = (b1 - b0) * L; w = B * wf
    g = mat('glass', GLASS, 0.1, 0.2); wh = mat('ss_' + CCG_WHITE, CCG_WHITE, 0.45)
    out = [tier(xc, z, l, w, h, bevel=0.3)]
    out.append(box((l * 0.97, w + 0.05, h * 0.38), (xc, 0, z + h * 0.6), material=g))
    out.append(box((0.3, w * 0.94, h * 0.4), (X(L, b0) + 0.06, 0, z + h * 0.6), (0, -0.28, 0), material=g))
    out.append(box((l + 0.3, w + 0.3, 0.16), (xc, 0, z + h + 0.08), material=wh))
    wl = max(w + 0.4, min(B * wing, w + 3.0)); wlen = min(l * 0.5, 4.5)
    out.append(box((wlen, wl, 0.22), (X(L, b0) - wlen * 0.4, 0, z + h * 0.3), material=wh))
    return out

def roof_at(L, z0, tiers, x):
    z = z0
    for (h, b0, b1, wf) in tiers:
        if X(L, b1) - 0.01 <= x <= X(L, b0) + 0.01: z += h
        else: break
    return z

def ccg_ship(sp, name):
    L, B, T, fb = sp['L'], sp['B'], sp['T'], sp['fb']
    h = Hull(L, B, T + fb, fb, transom=sp.get('transom', 0.72), bow_p=sp.get('bow_p', 0.75), stern_p=0.4, max_at=0.48,
             sheer_bow=(sp['bow_rise'] / (2 * (T + fb)) if 'bow_rise' in sp else sp.get('sheer_bow', 0.12)), sheer_stern=0.02, rocker=0.0, forefoot=sp.get('forefoot', 0.85),
             chine=sp.get('chine', 0.35), chine_h=0.25, deadrise=0.1, flare=sp.get('flare', 0.14), S=sp.get('S', 72), K=14)
    hull = h.build(CCG_RED, CCG_BOTTOM, CCG_BOOT, None, name + '_hull')
    paint_hull(hull, L, boot=max(0.35, T * 0.12), stripe_x=X(L, sp['stripe']), stripe_w=L * sp.get('stripe_w', 0.08))
    parts = [hull, h.deck(DECK), h.rail(1.0, CCG_RED)]
    zdeck = lambda b: h.zs(1 - min(max(b, 0.0), 1.0)) - 0.1          # main deck height at fraction b from the bow
    tiers = sp['tiers']
    z0 = zdeck((tiers[0][1] + tiers[0][2]) / 2)
    z = z0
    for i, (ht, b0, b1, wf) in enumerate(tiers):
        if i < len(tiers) - 1:
            parts.append(tier_box(L, B, z, ht, b0, b1, wf))
            xc = (X(L, b0) + X(L, b1)) / 2
            parts += window_row(xc, z + ht * 0.55, (b1 - b0) * L * 0.9, B * wf + 0.02, ht * 0.34, max(3, int((b1 - b0) * L / 3.2)))
        else:
            parts += bridge_deck(L, B, z, ht, b0, b1, wf, sp.get('wing', 0.9))
        z += ht
    ztop = z
    for (b0, b1, wf, ht) in sp.get('blocks', []):                         # separate deckhouses: hangars, deck boxes
        zb = zdeck((b0 + b1) / 2)
        parts.append(tier_box(L, B, zb, ht, b0, b1, wf))
        parts += window_row((X(L, b0) + X(L, b1)) / 2, zb + ht * 0.55, (b1 - b0) * L * 0.8, B * wf + 0.02, ht * 0.22, max(2, int((b1 - b0) * L / 5)))
    for (b, mh) in sp.get('masts', []):
        x = X(L, b); parts += mast(x, roof_at(L, z0, tiers, x) + 0.18, mh, yard=B * 0.3, color=sp.get('mast_color'))
    for fn in sp.get('funnels', []):
        b, fl, fw, fh = fn[:4]; fy = fn[4] if len(fn) > 4 else 0.0; black = len(fn) > 5 and fn[5]
        x = X(L, b); zf = roof_at(L, z0, tiers, x) if b >= tiers[0][1] and b <= tiers[0][2] else zdeck(b)
        parts += funnel(x, zf, fl, fw, fh, y=fy, black=black)
    if sp.get('heli'):
        b0, b1, hz, hw = sp['heli']
        parts += helideck(X(L, b1), X(L, b0), zdeck((b0 + b1) / 2) + hz, B * hw)
    for (b, yf, reach, d) in sp.get('cranes', []):
        parts += crane(X(L, b), yf * B / 2, zdeck(b), reach, d)
    if sp.get('boats'):
        b, ti = sp['boats']; zr = z0 + sum(t[0] for t in tiers[:ti + 1])
        parts += lifeboat_pair(X(L, b), zr, B * tiers[ti][3] * 0.78)
    bm = mat('fit', '#2b2b2b', 0.6, 0.3)
    for s in (1, -1):
        parts.append(cyl(0.5, 0.5, 0.6, 8, loc=(X(L, 0.07), s * B * 0.15, zdeck(0.07)), material=bm))
    parts.append(foil(T * 0.6, T * 0.5, T * 0.7, -L / 2 + L * 0.03, -T * 0.55, 0.15, 0.0, mat('rud', CCG_BOTTOM, 0.6), 'rudder'))
    for extra in sp.get('extras', []): parts += extra(L, B, T, fb, zdeck)
    return join(parts, name)

# ---------------------------------------------------------------- the fleet (principal dimensions from published data; layout fractions from photographs)
def deck_boxes(bs, color='#2f5d46'):
    def f(L, B, T, fb, zdeck):
        m = mat('container', color, 0.6)
        return [box((6.1, 2.44, 2.6), (X(L, b), s * 1.4, zdeck(b) + 1.3), material=m, bevel=0.03) for b in bs for s in (1, -1)]
    return f

def a_frame(b, hgt=8.0):
    def f(L, B, T, fb, zdeck):
        wh = mat('ss_' + CCG_WHITE, CCG_WHITE, 0.45); dk = mat('aframe_dark', '#2c2f33', 0.6)
        z = zdeck(b); x = X(L, b)
        return [box((2.4, B * 0.3, hgt * 0.78), (x, 0, z + hgt * 0.39), material=wh, bevel=0.25), box((2.7, B * 0.33, hgt * 0.22), (x, 0, z + hgt * 0.89), material=dk, bevel=0.2)]
    return f

def workdeck(b0, b1, wf):
    def f(L, B, T, fb, zdeck):
        return [box(((b1 - b0) * L, B * wf, 0.3), ((X(L, b0) + X(L, b1)) / 2, 0, zdeck((b0 + b1) / 2) + 0.15), material=mat('workdeck', '#5d5751', 0.9))]
    return f

FLEET = {
    # fb is the freeboard at the waterline; the hull sheers up toward the bow from there. Houses are 12 to 15 m tall (photographs: about twice the hull side).
    'louis_st_laurent': dict(L=119.8, B=24.4, T=5.5, fb=7.0, bow_rise=3.4, forefoot=1.1, bow_p=0.7, flare=0.16, stripe=0.40, stripe_w=0.065, mast_color=ORANGE,
        tiers=[(3.2, .29, .54, .68), (3.1, .29, .51, .64), (3.0, .30, .48, .60), (2.9, .30, .45, .56), (2.6, .31, .41, .50)], masts=[(.37, 12)],
        funnels=[(.46, 8.0, 6.0, 8.0)], blocks=[(.70, .80, .62, 5.0)], heli=(.84, .97, 1.4, .80),
        cranes=[(.18, .55, 12, 1), (.60, .62, 12, -1)], boats=(.40, 0)),
    'arpatuuq': dict(L=138.5, B=29.4, T=5.5, fb=8.0, bow_rise=3.8, forefoot=1.1, bow_p=0.62, flare=0.16, stripe=0.38, stripe_w=0.07, mast_color=ORANGE,
        tiers=[(3.5, .25, .50, .70), (3.4, .25, .47, .66), (3.3, .26, .44, .62), (3.2, .27, .41, .56), (3.0, .28, .38, .50)], masts=[(.34, 14)],
        funnels=[(.45, 9.0, 7.0, 7.5)], blocks=[(.62, .78, .66, 7.0)], heli=(.80, .97, 2.0, .78),
        cranes=[(.15, .5, 14, 1), (.55, .6, 16, -1)], boats=(.36, 0)),
    'terry_fox': dict(L=88.0, B=17.8, T=5.5, fb=4.6, bow_rise=2.6, forefoot=1.0, bow_p=0.72, flare=0.16, stripe=0.275, stripe_w=0.095, mast_color='#2b2b2b',
        tiers=[(3.1, .20, .47, .72), (3.0, .21, .45, .68), (3.0, .22, .41, .64), (2.7, .23, .37, .56)], masts=[(.31, 8)],
        funnels=[(.40, 1.5, 1.5, 3.5, 1.7, True), (.40, 1.5, 1.5, 3.5, -1.7, True)], cranes=[(.52, .5, 15, -1)], boats=(.37, 0),
        extras=[workdeck(.60, .95, .80)]),
    'pierre_radisson': dict(L=98.3, B=19.5, T=5.5, fb=5.4, bow_rise=3.0, forefoot=1.0, bow_p=0.72, flare=0.15, stripe=0.51, stripe_w=0.085, mast_color=ORANGE,
        tiers=[(3.1, .25, .64, .72), (3.0, .26, .62, .68), (2.9, .27, .55, .64), (2.9, .27, .50, .58), (2.7, .28, .48, .54)], masts=[(.42, 9), (.66, 7)],
        funnels=[(.57, 5.5, 3.2, 6.0)], blocks=[(.66, .86, .62, 4.2)], heli=(.86, 1.0, 1.8, .78),
        cranes=[(.22, .42, 10, 1), (.22, -.42, 10, 1), (.82, .5, 12, -1)], boats=(.50, 0)),
    'capt_molly_kool': dict(L=83.7, B=18.0, T=5.5, fb=4.4, bow_rise=2.5, forefoot=0.95, bow_p=0.8, flare=0.15, stripe=0.56, stripe_w=0.12, mast_color='#2b2b2b',
        tiers=[(3.3, .35, .75, .80), (3.1, .37, .70, .72), (3.0, .41, .64, .62), (2.9, .46, .60, .54), (2.5, .48, .58, .46)], masts=[(.52, 8)],
        funnels=[(.62, 1.6, 1.3, 3.0, 0.9, True), (.62, 1.6, 1.3, 3.0, -0.9, True)], cranes=[(.90, .45, 14, 1)],
        extras=[deck_boxes([.80, .84]), workdeck(.76, 1.0, .86)]),
    'martha_l_black': dict(L=83.0, B=16.2, T=5.0, fb=4.2, bow_rise=2.6, forefoot=0.85, bow_p=0.75, flare=0.14, stripe=0.70, stripe_w=0.085, mast_color=ORANGE,
        tiers=[(3.1, .43, .76, .80), (3.0, .43, .74, .74), (2.9, .43, .70, .68), (2.8, .43, .66, .60), (2.4, .44, .62, .54)], masts=[(.58, 8)],
        funnels=[(.62, 5.0, 3.0, 5.5)], blocks=[(.78, .90, .66, 4.8)], heli=(.90, 1.0, 0.8, .74),
        cranes=[(.40, .35, 16, 1)], boats=(.72, 0)),
    'donjek_aops': dict(L=103.6, B=19.0, T=5.0, fb=5.5, bow_rise=2.2, forefoot=0.7, bow_p=0.85, flare=0.16, stripe=0.45, stripe_w=0.07, mast_color=STEEL,
        tiers=[(3.4, .24, .54, .84), (3.2, .25, .52, .72), (3.0, .26, .48, .62), (2.8, .27, .44, .52)], masts=[(.34, 13)],
        funnels=[(.50, 2.0, 1.6, 3.5, 1.4, True), (.50, 2.0, 1.6, 3.5, -1.4, True)], blocks=[(.55, .77, .70, 7.5)], heli=(.80, .99, 2.2, .76),
        cranes=[(.62, -.62, 10, -1)], boats=(.40, 0)),
    'sir_john_franklin': dict(L=63.4, B=16.0, T=5.0, fb=4.5, bow_rise=2.5, forefoot=0.6, bow_p=0.9, chine=0.2, flare=0.14, stripe=0.44, stripe_w=0.075, mast_color=ORANGE,
        tiers=[(3.2, .13, .62, .86), (3.0, .20, .60, .76), (3.0, .30, .58, .68)], masts=[(.46, 8)],
        funnels=[(.67, 1.1, 1.1, 4.0, 1.5, True), (.67, 1.1, 1.1, 4.0, 0.0, True), (.67, 1.1, 1.1, 4.0, -1.5, True)],
        cranes=[(.72, -.6, 8, -1)], extras=[a_frame(.86, 9.0), workdeck(.64, 1.0, .88)]),
    'hero_class': dict(L=42.8, B=7.0, T=2.8, fb=1.9, transom=0.85, bow_rise=1.6, forefoot=0.5, bow_p=1.1, chine=1.0, flare=0.1, S=56, stripe=0.30, stripe_w=0.10,
        tiers=[(2.6, .30, .64, .86), (2.5, .36, .58, .76), (2.2, .38, .54, .62)], masts=[(.46, 7)], cranes=[(.84, .0, 5, -1)],
        extras=[workdeck(.66, .98, .80)]),
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
    parts = [hull, h.deck(DECK), h.rail(0.55, CCG_RED)]
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
    parts.append(box((L, B, 1.6), (0, 0, 0.8), material=sk, bevel=1.0))
    parts.append(box((L - 1.0, B - 1.0, 0.6), (0, 0, 1.85), material=mat('ccg_red', CCG_RED, 0.45), bevel=0.7))
    parts.append(box((L - 3.2, B - 3.2, 0.15), (0, 0, 2.2), material=mat('deck', DECK, 0.85), bevel=0.05))
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
