"""Watercraft class: one lofted-hull generator, appendage foils, rigs, and six boat types built on them."""
import math, random
from mathutils import Vector
from pg_core import *

PAL = dict(white='#e9e3d6', cream='#efe6cf', red='#d64b2c', brass='#e3a948', navy='#23465c', green='#2f5d46',
           black='#2c2f33', teak='#b48a5a', grey='#8d939a', af_red='#8e2e24', af_black='#2a2a2a', sky='#4f7fa6',
           yellow='#e8b93a', tan_sail='#b3714a', glass='#1d2b33', steel='#b9bec4', rope='#cbbd9b')

# ---------------------------------------------------------------- hull loft
class Hull:
    def __init__(s, L, B, D, fb, transom=0.6, bow_p=0.9, stern_p=0.6, max_at=0.45, sheer_bow=0.12, sheer_stern=0.05,
                 rocker=0.08, forefoot=0.6, chine=0.0, chine_h=0.35, deadrise=0.25, flare=0.08, S=28, K=8):
        s.__dict__.update(locals()); del s.__dict__['s']

    def w(s, t):
        if t >= s.max_at:
            u = (t - s.max_at) / (1 - s.max_at)
            return s.B / 2 * max(0.0, math.cos(u * math.pi / 2)) ** s.bow_p
        u = t / s.max_at
        return s.B / 2 * (s.transom + (1 - s.transom) * math.sin(u * math.pi / 2) ** s.stern_p)

    def x(s, t): return -s.L / 2 + s.L * t
    def zs(s, t): return s.fb + s.sheer_bow * s.D * t * t * 2 + s.sheer_stern * s.D * (1 - t) ** 2 * 2
    def zk(s, t):
        z = s.fb - s.D + s.rocker * s.D * (2 * t - 1) ** 2
        if t > 0.72: z += s.forefoot * s.D * ((t - 0.72) / 0.28) ** 2
        return min(z, s.zs(t) - 0.02)

    def section(s, t):
        """Half-section points k=0 (sheer) .. K (keel centreline), y >= 0."""
        w, zs, zk = s.w(t), s.zs(t), s.zk(t)
        zc = zk + (zs - zk) * s.chine_h
        pts = []
        Ks = max(2, int(s.K * 0.45))
        for k in range(s.K + 1):
            a = k / s.K * math.pi / 2
            rnd = (w * math.cos(a), zs - (zs - zk) * math.sin(a))
            if k <= Ks:  # topsides, flaring out toward the sheer
                f = k / Ks
                hard = (w * (1 - s.flare * f), zs + (zc - zs) * f)
            else:        # bottom with deadrise
                f = (k - Ks) / (s.K - Ks)
                yc = w * (1 - s.flare)
                hard = (yc * (1 - f), zc + (zk - zc) * f * (1 - s.deadrise) + (zk - zc) * s.deadrise * f ** 0.6)
            pts.append((rnd[0] + (hard[0] - rnd[0]) * s.chine, rnd[1] + (hard[1] - rnd[1]) * s.chine))
        pts[-1] = (0.0, zk)
        return pts

    def sheer_pt(s, t, side=1):
        return Vector((s.x(t), side * s.w(t), s.zs(t)))

    def build(s, top='#e9e3d6', bottom='#8e2e24', boot='#2c2f33', stripe=None, name='hull'):
        mats = [mat('topsides_' + top, top, 0.35), mat('antifoul_' + bottom, bottom, 0.8), mat('boot_' + boot, boot, 0.5)]
        if stripe: mats.append(mat('stripe_' + stripe, stripe, 0.4))
        verts, faces, ring_n = [], [], 2 * s.K + 1
        for i in range(s.S + 1):
            t = i / s.S
            sec = s.section(t)
            ring = [(y, z) for (y, z) in sec] + [(-y, z) for (y, z) in reversed(sec[:-1])]
            for (y, z) in ring:
                verts.append((s.x(t), y, z))
        for i in range(s.S):
            for k in range(ring_n - 1):
                a, b = i * ring_n + k, (i + 1) * ring_n + k
                faces.append((a, a + 1, b + 1, b))
        if s.transom > 0.01:
            faces.append(tuple(range(ring_n)))
        o = mesh(name, verts, faces)
        for m in mats: o.data.materials.append(m)
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        for f in bm.faces:
            c = f.calc_center_median()
            t = (c.x + s.L / 2) / s.L
            if c.z < 0.02: f.material_index = 1
            elif c.z < 0.11: f.material_index = 2
            elif stripe and c.z > s.zs(min(max(t, 0), 1)) - 0.12 and abs(f.normal.z) < 0.7: f.material_index = 3
            else: f.material_index = 0
        bm.to_mesh(o.data); bm.free()
        for p in o.data.polygons: p.use_smooth = False
        return solidify(o, 0.025)

    def deck(s, color='#b48a5a', inset=0.0, name='deck', z_off=-0.02):
        verts, faces = [], []
        for i in range(s.S + 1):
            t = i / s.S
            w = max(s.w(t) - inset, 0.0)
            verts += [(s.x(t), w, s.zs(t) + z_off), (s.x(t), -w, s.zs(t) + z_off)]
        for i in range(s.S):
            a = 2 * i
            faces.append((a, a + 2, a + 3, a + 1))
        o = mesh(name, verts, faces, mat('deck_' + color, color, 0.8))
        bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4); bm.to_mesh(o.data); bm.free()
        return o

    def rail(s, h=0.06, color='#b48a5a', name='rail', t0=0.0, t1=1.0):
        verts, faces = [], []
        n = 0
        for side in (1, -1):
            base = len(verts)
            steps = [t0 + (t1 - t0) * i / s.S for i in range(s.S + 1)]
            for t in steps:
                p = s.sheer_pt(t, side)
                verts += [tuple(p), (p.x, p.y, p.z + h)]
            for i in range(len(steps) - 1):
                a = base + 2 * i
                faces.append((a, a + 2, a + 3, a + 1))
        o = mesh(name, verts, faces, mat('rail_' + color, color, 0.6))
        return solidify(o, 0.035, 0)

# ---------------------------------------------------------------- foils, spars, sails
def foil(chord_root, chord_tip, span, x_le, z_top, tr=0.12, sweep=0.0, material=None, name='foil', y=0.0, down=True, n=10):
    def prof(c):
        pts = []
        for i in range(n + 1):
            xx = (1 - math.cos(math.pi * i / n)) / 2
            yt = 5 * tr * c * (0.2969 * math.sqrt(xx) - 0.1260 * xx - 0.3516 * xx ** 2 + 0.2843 * xx ** 3 - 0.1015 * xx ** 4)
            pts.append((xx * c, yt))
        return [(x, yy) for x, yy in pts] + [(x, -yy) for x, yy in reversed(pts[1:-1])]
    root, tip = prof(chord_root), prof(chord_tip)
    m = len(root); sgn = -1 if down else 1
    verts = [(x_le - x, y + yy, z_top) for x, yy in root] + [(x_le - sweep - x, y + yy, z_top + sgn * span) for x, yy in tip]
    faces = [(i, (i + 1) % m, m + (i + 1) % m, m + i) for i in range(m)]
    faces += [tuple(reversed(range(m))), tuple(range(m, 2 * m))]
    return mesh(name, verts, faces, material)

def ellipsoid(c, r, seg=12, material=None, name='bulb'):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2 + 1, radius=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.LocRotScale(Vector(c), None, Vector(r)), verts=bm.verts)
    return obj_from_bm(bm, name, material, smooth=True)

def sail(corners, camber=0.08, side=1, color='#f3eee3', U=8, V=10, name='sail'):
    """corners: tack, clew, head (triangle) or tack, clew, peak, throat (gaff/quad)."""
    tack, clew = Vector(corners[0]), Vector(corners[1])
    quad = len(corners) == 4
    peak = Vector(corners[2]); throat = Vector(corners[3]) if quad else Vector(corners[2])
    luff = (throat - tack).normalized()
    nrm = (clew - tack).cross(luff).normalized() * side
    verts, faces = [], []
    for j in range(V + 1):
        v = j / V
        a = tack.lerp(throat, v)
        b = clew.lerp(peak, v) if quad else clew.lerp(peak, v)
        if not quad:
            b = clew + (peak - clew) * v
        chord = (b - a).length
        for i in range(U + 1):
            u = i / U
            p = a.lerp(b, u) + nrm * camber * chord * math.sin(math.pi * u) * (1 - 0.35 * v) * (u ** 0.15)
            verts.append(tuple(p))
    for j in range(V):
        for i in range(U):
            a = j * (U + 1) + i
            faces.append((a, a + 1, a + U + 2, a + U + 1))
    o = mesh(name, verts, faces, mat('sail_' + color, color, 0.85))
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4); bm.to_mesh(o.data); bm.free()
    return solidify(o, 0.012, 0)

def battens(corners, n=3, color='#d9d2c4', name='battens'):
    tack, clew, head = (Vector(c) for c in corners[:3])
    out = []
    for i in range(1, n + 1):
        v = i / (n + 1)
        a = tack.lerp(head, v); b = clew + (head - clew) * v
        out.append(rod(b + (a - b) * 0.0, b + (a - b) * 0.3, 0.012, 4, mat('batten', color, 0.6)))
    return out

def spar(p0, p1, r0, r1=None, color='#cfcac0', metal=0.6, seg=8):
    r1 = r0 if r1 is None else r1
    p0, p1 = Vector(p0), Vector(p1)
    o = cyl(r0, r1, (p1 - p0).length, seg, material=mat('spar_' + color, color, 0.35, metal))
    q = (p1 - p0).to_track_quat('Z', 'Y')
    o.data.transform(Matrix.Translation(p0) @ q.to_matrix().to_4x4())
    return o

def wire(p0, p1):
    return rod(p0, p1, 0.006, 4, mat('wire', '#9aa0a6', 0.3, 0.8))

def cabin(x0, x1, w0, w1, z0, h, rake=0.15, tumble=0.12, color='#e9e3d6', window='#1d2b33', name='cabin', windows=True):
    """Trapezoid trunk: footprint from x0 (aft) to x1 (fwd), half-widths w0 (aft) w1 (fwd)."""
    zt = z0 + h
    ti = 1 - tumble
    verts = [(x0, -w0, z0), (x1, -w1, z0), (x1, w1, z0), (x0, w0, z0),
             (x0, -w0 * ti, zt), (x1 - rake * h, -w1 * ti, zt), (x1 - rake * h, w1 * ti, zt), (x0, w0 * ti, zt)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    parts = [mesh(name, verts, faces, mat('cabin_' + color, color, 0.45))]
    if windows:
        wm = mat('glass', window, 0.1, 0.2)
        for side in (1, -1):
            zz = z0 + h * 0.62
            for xs in [x0 + (x1 - x0) * f for f in (0.18, 0.45, 0.72)]:
                f = (xs - x0) / (x1 - x0)
                ww = (w0 + (w1 - w0) * f) * (1 - tumble * 0.62) + 0.006
                parts.append(box((min(0.45, (x1 - x0) * 0.2), 0.01, h * 0.28), (xs, side * ww, zz), material=wm))
    return parts

def cleat(p, ang=0.0, color='#b9bec4'):
    m = mat('fitting_' + color, color, 0.3, 0.8)
    return [box((0.18, 0.04, 0.03), (p[0], p[1], p[2] + 0.05), (0, 0, ang), material=m),
            box((0.05, 0.035, 0.05), (p[0], p[1], p[2] + 0.02), (0, 0, ang), material=m)]

def winch(p, r=0.06, color='#b9bec4'):
    m = mat('fitting_' + color, color, 0.3, 0.8)
    return [cyl(r, r * 0.8, r * 1.4, 10, loc=p, material=m), cyl(r * 0.5, r * 0.5, r * 0.4, 8, loc=(p[0], p[1], p[2] + r * 1.4), material=m)]

# ---------------------------------------------------------------- boat types
def jit(rng, v, f=0.06): return v * (1 + rng.uniform(-f, f))

GAME = dict(split=False)   # split=True: boom + mainsail and jib come back as separate objects, centred, pivot at mast / stem

def _finish(parts, rig, jib, name, pivot, jib_pivot=None):
    if not GAME['split']:
        return join(parts + rig + jib, name)
    hull = join(parts, name + '_hull')
    out = [hull]
    for objs, nm, pv in ((rig, name + '_rig', pivot), (jib, name + '_jib', jib_pivot)):
        if objs:
            o = join(objs, nm)
            o.data.transform(Matrix.Translation(-Vector(pv))); o.location = pv
            out.append(o)
    return out

def dinghy(seed=0, name='dinghy'):
    """Cat-rigged sailing dinghy (Squall Cove 'Petrel'): round bilge, wide transom, daggerboard."""
    r = rng(seed)
    L, B = jit(r, 4.2), jit(r, 1.6)
    h = Hull(L, B, 0.62, 0.36, transom=0.78, bow_p=0.85, stern_p=0.5, max_at=0.42, sheer_bow=0.18, sheer_stern=0.0,
             rocker=0.1, forefoot=0.45, chine=0.15, flare=0.1)
    top, stripe = r.choice([(PAL['white'], PAL['red']), (PAL['yellow'], PAL['navy']), (PAL['sky'], PAL['white']), (PAL['white'], PAL['green'])])
    parts = [h.build(top, PAL['white'], PAL['grey'], stripe, name + '_hull'), h.deck(PAL['white'] if r.random() < .5 else PAL['teak'], 0.0),
             h.rail(0.04, PAL['teak'])]
    # cockpit well and thwart
    parts.append(box((L * 0.45, B * 0.62, 0.05), (-L * 0.08, 0, h.zs(0.4) - 0.05), material=mat('floor', '#d8d2c4', 0.8)))
    parts.append(box((0.25, B * 0.86, 0.04), (0.15, 0, h.zs(0.55) - 0.12), material=mat('thwart', PAL['teak'], 0.8)))
    # daggerboard + transom-hung rudder + tiller
    fm = mat('foil_' + PAL['black'], PAL['black'], 0.4)
    parts.append(foil(0.32, 0.26, 0.85, 0.35, h.zk(0.55) + 0.05, 0.1, 0.06, fm))
    parts.append(foil(0.30, 0.22, 0.75, -L / 2 + 0.05, h.zs(0) - 0.05, 0.1, 0.05, fm, 'rudder'))
    parts.append(spar((-L / 2 + 0.02, 0, h.zs(0) + 0.02), (-L / 2 + 1.15, 0, h.zs(0) + 0.16), 0.02, 0.016, PAL['teak'], 0))
    # cat rig
    mx, mz = L / 2 - 1.1, h.zs(0.75)
    mh = jit(r, 5.4)
    parts.append(spar((mx, 0, mz - 0.25), (mx, 0, mz + mh), 0.045, 0.028))
    boom_z = mz + 0.8; blen = L * 0.6
    bang = math.radians(r.uniform(12, 22))
    if GAME['split']: bang = 0.0
    clew = (mx - blen * math.cos(bang), blen * math.sin(bang), boom_z)
    rig = [spar((mx, 0, boom_z), clew, 0.03, 0.025)]
    sc = r.choice(['#f3eee3', '#f3eee3', '#efe2c7'])
    corners = [(mx - 0.03, 0, boom_z + 0.04), clew, (mx - 0.03, 0, mz + mh - 0.08)]
    rig.append(sail(corners, 0.09, -1, sc))
    rig += battens(corners, 3)
    for t in (0.25, 0.8):
        for side in (1, -1): parts += cleat(h.sheer_pt(t, side) + Vector((0, -side * 0.06, 0)))
    GAME['meta'] = dict(L=L, B=B, D=h.D, fb=h.fb, mast_x=mx, deck_z=mz, boom_z=boom_z, boom_len=blen, mast_h=mh, keel_z=h.zk(0.55) - 0.85)
    return _finish(parts, rig, [], name, (mx, 0, boom_z))

def keelboat(seed=0, name='keelboat'):
    """Bermuda sloop (Squall Cove 'Kestrel'): fin keel and bulb, spade rudder, trunk cabin, lifelines."""
    r = rng(seed)
    L, B = jit(r, 7.5), jit(r, 2.6)
    h = Hull(L, B, 1.05, 0.62, transom=0.62, bow_p=0.9, stern_p=0.45, max_at=0.48, sheer_bow=0.14, sheer_stern=0.02,
             rocker=0.05, forefoot=0.55, chine=0.1, flare=0.06)
    top, stripe, af = r.choice([(PAL['navy'], PAL['brass'], PAL['af_black']), (PAL['white'], PAL['navy'], PAL['af_red']),
                                (PAL['green'], PAL['cream'], PAL['af_red']), (PAL['white'], PAL['red'], PAL['af_black'])])
    parts = [h.build(top, af, PAL['white'] if top != PAL['white'] else PAL['black'], stripe, name + '_hull'),
             h.deck('#d9d2c4'), h.rail(0.05, PAL['teak'])]
    fm = mat('keel', '#3a3a3a', 0.5, 0.3)
    kz = h.zk(0.5) + 0.05
    parts.append(foil(1.0, 0.7, 1.15, 0.45, kz, 0.12, 0.25, fm, 'keel'))
    parts.append(ellipsoid((0.45 - 0.25 - 0.45, 0, kz - 1.15), (0.85, 0.16, 0.14), 12, mat('lead', '#555a5e', 0.4, 0.6)))
    parts.append(foil(0.42, 0.3, 1.0, -L / 2 + 1.0, h.zk(0.12) + 0.1, 0.12, 0.1, fm, 'rudder'))
    # cabin trunk, cockpit coaming, hatch
    cz = h.zs(0.5) - 0.02
    parts += cabin(-0.5, L * 0.18, B * 0.33, B * 0.26, cz, 0.42, 0.25, 0.14, PAL['cream'])
    parts.append(box((0.6, 0.55, 0.06), (L * 0.05, 0, cz + 0.44), material=mat('hatch', PAL['teak'], 0.6)))
    cm = mat('coaming', PAL['teak'], 0.7)
    for side in (1, -1):
        parts.append(box((1.9, 0.04, 0.2), (-1.55, side * B * 0.32, cz + 0.08), material=cm))
        parts += winch((-1.0, side * B * 0.36, cz + 0.18))
    # rig
    mx = L * 0.12; mh = jit(r, 9.5)
    mz = cz
    parts.append(spar((mx, 0, mz), (mx, 0, mz + mh), 0.07, 0.045))
    boom_z = mz + 1.0; blen = 3.4
    bang = math.radians(r.uniform(8, 18))
    if GAME['split']: bang = 0.0
    clew = (mx - blen * math.cos(bang), blen * math.sin(bang), boom_z)
    rig = [spar((mx, 0, boom_z), clew, 0.05, 0.04)]
    sc = r.choice(['#f3eee3', '#f3eee3', '#e9dcc0'])
    main = [(mx - 0.05, 0, boom_z + 0.05), clew, (mx - 0.05, 0, mz + mh - 0.15)]
    rig.append(sail(main, 0.08, -1, sc, name='main')); rig += battens(main, 4)
    stem = (L / 2 - 0.05, 0, h.zs(1) + 0.05)
    jhead = (mx + 0.05, 0, mz + mh * 0.82)
    jclew = (mx - 0.9, 1.15 * math.sin(bang) + (0.0 if GAME['split'] else 0.5), h.zs(0.5) + 0.35)
    jib = [sail([stem, jclew, jhead], 0.07, -1, sc, name='jib')]
    top_m = (mx, 0, mz + mh)
    parts += [wire(stem, top_m), wire((-L / 2 + 0.1, 0, h.zs(0) + 0.05), top_m)]
    for side in (1, -1):
        cp = h.sheer_pt(0.52, side)
        parts.append(wire(cp, (mx, 0, mz + mh * 0.95)))
        parts.append(spar((mx, 0, mz + mh * 0.55), (mx, side * 0.75, mz + mh * 0.55), 0.015, 0.012))
    # stanchions + lifelines
    pm = mat('fitting_#b9bec4', PAL['steel'], 0.3, 0.8)
    ts = [0.1, 0.28, 0.46, 0.64, 0.8]
    for side in (1, -1):
        tops = []
        for t in ts:
            p = h.sheer_pt(t, side) + Vector((0, -side * 0.06, 0))
            parts.append(rod(p, p + Vector((0, 0, 0.6)), 0.012, 5, pm)); tops.append(p + Vector((0, 0, 0.6)))
        for a, b in zip(tops, tops[1:]): parts.append(wire(a, b))
    parts.append(spar(h.sheer_pt(0.97, 1) * 0 + Vector((L / 2 - 0.3, 0, h.zs(1) + 0.05)), (L / 2 + 0.25, 0, h.zs(1) + 0.08), 0.02))
    GAME['meta'] = dict(L=L, B=B, D=h.D, fb=h.fb, mast_x=mx, deck_z=mz, boom_z=boom_z, boom_len=blen, mast_h=mh, keel_z=kz - 1.15, stem=list(stem))
    return _finish(parts, rig, jib, name, (mx, 0, boom_z), stem)

def gaff_cutter(seed=0, name='gaff_cutter'):
    """Traditional gaff cutter: long keel, bowsprit, gaff main, staysail and jib, tan-bark sails."""
    r = rng(seed)
    L, B = jit(r, 8.5), jit(r, 2.7)
    h = Hull(L, B, 1.45, 0.75, transom=0.5, bow_p=0.75, stern_p=0.55, max_at=0.45, sheer_bow=0.2, sheer_stern=0.08,
             rocker=0.02, forefoot=0.3, chine=0.0, flare=0.05)
    top, stripe = r.choice([(PAL['green'], PAL['brass']), (PAL['black'], PAL['brass']), (PAL['navy'], PAL['cream']), ('#7a2b22', PAL['cream'])])
    parts = [h.build(top, PAL['af_red'], PAL['cream'], stripe, name + '_hull'), h.deck(PAL['teak']), h.rail(0.12, PAL['teak'])]
    fm = mat('keel_' + top, top, 0.5)
    parts.append(foil(L * 0.55, L * 0.5, 0.6, L * 0.25, h.zk(0.5) + 0.05, 0.08, 0.15, fm, 'longkeel'))
    parts.append(foil(0.6, 0.5, 1.2, -L / 2 + 0.2, h.zs(0) - 0.05, 0.08, 0.1, fm, 'rudder'))
    cz = h.zs(0.5) - 0.02
    parts += cabin(-1.0, 0.9, B * 0.3, B * 0.26, cz, 0.38, 0.05, 0.08, PAL['teak'], name='doghouse')
    mx = L * 0.08; mh = jit(r, 8.0)
    parts.append(spar((mx, 0, cz), (mx, 0, cz + mh), 0.09, 0.06, '#c49a62', 0))
    boom_z = cz + 0.9; blen = L * 0.62
    bang = math.radians(r.uniform(10, 20))
    clew = (mx - blen * math.cos(bang), blen * math.sin(bang), boom_z)
    parts.append(spar((mx, 0, boom_z), clew, 0.06, 0.05, '#c49a62', 0))
    throat = Vector((mx - 0.08, 0, cz + mh * 0.72))
    peak = throat + Vector((-blen * 0.62 * math.cos(bang), blen * 0.62 * math.sin(bang), 2.0))
    parts.append(spar(throat, peak, 0.05, 0.04, '#c49a62', 0))
    sc = r.choice([PAL['tan_sail'], PAL['tan_sail'], '#efe2c7'])
    parts.append(sail([(mx - 0.08, 0, boom_z + 0.06), clew, peak, throat], 0.07, -1, sc, U=8, V=8, name='gaffmain'))
    # bowsprit, staysail, jib
    sp_end = (L / 2 + 2.6, 0, h.zs(1) + 0.15)
    parts.append(spar((L / 2 - 0.8, 0, h.zs(1) + 0.08), sp_end, 0.06, 0.045, '#c49a62', 0))
    stem = (L / 2 - 0.05, 0, h.zs(1) + 0.12)
    parts.append(sail([stem, (mx + 0.4, 1.0, cz + 0.5), (mx + 0.05, 0, cz + mh * 0.68)], 0.06, -1, sc, name='staysail'))
    parts.append(sail([sp_end, (mx + 1.2, 1.6, cz + 0.9), (mx + 0.05, 0, cz + mh * 0.92)], 0.06, -1, sc, name='jib'))
    for p in (stem, sp_end): parts.append(wire(p, (mx, 0, cz + mh * 0.95)))
    for side in (1, -1):
        for t in (0.48, 0.55): parts.append(wire(h.sheer_pt(t, side), (mx, 0, cz + mh * 0.75)))
    return join(parts, name)

def tug(seed=0, name='tug'):
    """Harbour tug (Squall Cove 'Bollard'): bluff bow, round stern, two-tier house, funnel, tyre fenders, bow pudding."""
    r = rng(seed)
    L, B = jit(r, 9.0), jit(r, 3.4)
    h = Hull(L, B, 1.9, 1.15, transom=0.0, bow_p=0.38, stern_p=0.35, max_at=0.45, sheer_bow=0.22, sheer_stern=0.03,
             rocker=0.04, forefoot=0.4, chine=0.0, flare=0.12, S=32)
    top, house, funnel = r.choice([(PAL['black'], PAL['white'], PAL['red']), (PAL['red'], PAL['white'], PAL['black']),
                                   (PAL['navy'], PAL['cream'], PAL['brass']), (PAL['green'], PAL['white'], PAL['red'])])
    parts = [h.build(top, PAL['af_red'], PAL['white'], None, name + '_hull'), h.deck('#6b6258'), h.rail(0.45, top)]
    parts.append(foil(1.0, 0.8, 0.7, -L / 2 + 1.8, h.zk(0.25) + 0.1, 0.12, 0.0, mat('skeg', top, 0.5), 'skeg'))
    parts.append(foil(0.8, 0.7, 1.1, -L / 2 + 0.75, h.zk(0.08) + 0.6, 0.12, 0.0, mat('rud', '#3a3a3a', 0.5), 'rudder'))
    dz = h.zs(0.5) - 0.02
    hm = mat('house_' + house, house, 0.45)
    parts.append(box((3.4, B * 0.62, 1.3), (0.2, 0, dz + 0.65), material=hm, bevel=0.04))
    parts.append(box((2.0, B * 0.55, 1.15), (0.55, 0, dz + 1.3 + 0.575), material=hm, bevel=0.04))
    gm = mat('glass', PAL['glass'], 0.1, 0.2)
    parts.append(box((2.04, B * 0.56, 0.42), (0.55, 0, dz + 2.05), material=gm))
    parts.append(box((2.4, B * 0.68, 0.1), (0.55, 0, dz + 2.5), material=mat('roof_' + funnel, funnel, 0.5)))
    for x in (-0.8, 0.0, 0.8):
        for side in (1, -1): parts.append(box((0.45, 0.02, 0.35), (0.2 + x, side * B * 0.31, dz + 0.85), material=gm))
    fm = mat('funnel_' + funnel, funnel, 0.5)
    parts.append(cyl(0.42, 0.36, 1.6, 12, loc=(-1.75, 0, dz + 1.2), material=fm))
    parts.append(cyl(0.38, 0.36, 0.25, 12, loc=(-1.75, 0, dz + 2.81), material=mat('black', PAL['black'], 0.6)))
    parts.append(cyl(0.425, 0.41, 0.3, 12, loc=(-1.75, 0, dz + 2.15), material=mat('band', PAL['brass'], 0.4)))
    parts.append(spar((0.9, 0, dz + 2.55), (0.9, 0, dz + 4.2), 0.05, 0.035, PAL['white'], 0))
    parts.append(spar((0.9, -0.6, dz + 3.7), (0.9, 0.6, dz + 3.7), 0.03, 0.03, PAL['white'], 0))
    # towing bitts and hook
    bm_ = mat('bitt', PAL['black'], 0.5, 0.3)
    for side in (1, -1): parts.append(cyl(0.14, 0.14, 0.55, 10, loc=(-2.9, side * 0.4, dz), material=bm_))
    parts.append(spar((-2.9, -0.5, dz + 0.42), (-2.9, 0.5, dz + 0.42), 0.05))
    parts.append(spar((-3.3, 0, dz), (-3.3, 0, dz + 1.0), 0.07, 0.05, PAL['black'], 0.3))
    # tyre fenders following the sheer, bow pudding
    tm = mat('rubber', '#151515', 0.95)
    for i in range(7):
        t = 0.12 + i * 0.11
        for side in (1, -1):
            p = h.sheer_pt(t, side)
            nrm = Vector((0, side, 0))
            parts.append(torus(0.32, 0.12, 12, 6, loc=(p.x, p.y + side * 0.14, p.z - 0.45), rot=(math.pi / 2, 0, 0), material=tm))
    bp = h.sheer_pt(1.0)
    parts.append(torus(0.55, 0.22, 10, 7, loc=(bp.x - 0.35, 0, bp.z - 0.35), rot=(math.pi / 2, 0, math.pi / 2), material=tm, arc=math.pi))
    sp = h.sheer_pt(0.0)
    parts.append(torus(0.75, 0.2, 10, 7, loc=(sp.x + 0.25, 0, sp.z - 0.3), rot=(math.pi / 2, 0, -math.pi / 2), material=tm, arc=math.pi))
    GAME['meta'] = dict(L=L, B=B, D=h.D, fb=h.fb, deck_z=dz)
    return _finish(parts, [], [], name, (0, 0, 0))

def dory(seed=0, name='dory'):
    """Banks dory: flat bottom, flared hard-chine sides, tombstone transom, thwarts and oars."""
    r = rng(seed)
    L, B = jit(r, 5.2), jit(r, 1.55)
    h = Hull(L, B, 0.62, 0.42, transom=0.3, bow_p=1.0, stern_p=0.9, max_at=0.5, sheer_bow=0.35, sheer_stern=0.25,
             rocker=0.12, forefoot=0.2, chine=1.0, chine_h=0.05, deadrise=0.0, flare=0.32)
    top, inside = r.choice([(PAL['yellow'], '#d8cfb8'), (PAL['sky'], '#d8cfb8'), ('#c8b48a', '#e6dcc4'), (PAL['red'], '#d8cfb8')])
    parts = [h.build(top, '#6a5a44', PAL['black'], PAL['black'], name + '_hull'), h.rail(0.05, '#7d5a3a')]
    parts.append(h.deck(inside, 0.05, 'floor', z_off=-(h.zs(0.5) - h.zk(0.5)) + 0.05))
    tm = mat('thwart', '#9a7650', 0.8)
    for t in (0.3, 0.55, 0.75):
        w = h.w(t) * (1 - h.flare * 0.4)
        parts.append(box((0.22, w * 1.9, 0.04), (h.x(t), 0, h.zs(t) - 0.2), material=tm))
    om = mat('oar', '#c49a62', 0.7)
    for side in (1, -1):
        p = h.sheer_pt(0.5, side)
        a = Vector((p.x + 0.5, -side * 0.6, p.z + 0.05)); b = Vector((p.x - 0.9, side * 2.0, p.z - 0.25))
        parts.append(rod(a, b, 0.025, 6, om))
        d = (b - a).normalized()
        parts.append(box((0.55, 0.14, 0.02), tuple(b + d * 0.2), (0, 0, math.atan2(d.y, d.x)), material=om))
    return join(parts, name)

def workboat(seed=0, name='workboat'):
    """Downeast-style launch: fine entry, hard-ish chine, wide transom, forward wheelhouse, hauler davit, trap stack."""
    r = rng(seed)
    L, B = jit(r, 9.5), jit(r, 3.2)
    h = Hull(L, B, 1.35, 0.95, transom=0.85, bow_p=0.95, stern_p=0.25, max_at=0.4, sheer_bow=0.28, sheer_stern=0.0,
             rocker=0.03, forefoot=0.5, chine=0.55, chine_h=0.32, deadrise=0.35, flare=0.12)
    top = r.choice([PAL['white'], PAL['sky'], PAL['green'], PAL['yellow']])
    parts = [h.build(top, PAL['af_red'], PAL['black'], PAL['black'] if top != PAL['white'] else PAL['navy'], name + '_hull'),
             h.deck('#bdb7a8'), h.rail(0.35, top)]
    parts.append(foil(2.2, 1.8, 0.45, -L / 2 + 3.2, h.zk(0.3) + 0.1, 0.1, 0.0, mat('skeg', '#3a3a3a', 0.5), 'skeg'))
    dz = h.zs(0.55)
    hm = mat('house', PAL['white'], 0.45)
    hx = L * 0.12
    parts += cabin(hx - 1.6, hx + 1.2, B * 0.38, B * 0.3, dz, 1.0, 0.1, 0.06, PAL['white'], windows=False, name='cuddy')
    parts.append(box((1.2, B * 0.74, 0.08), (hx - 1.2, 0, dz + 1.95), material=hm))
    parts.append(box((2.6, B * 0.8, 0.08), (hx - 2.3, 0, dz + 2.0), material=mat('roof', top, 0.5)))
    gm = mat('glass', PAL['glass'], 0.1, 0.2)
    parts.append(box((0.05, B * 0.66, 0.7), (hx - 0.62, 0, dz + 1.5), (0, -0.35, 0), material=gm))
    for side in (1, -1):
        parts.append(box((0.9, 0.04, 0.9), (hx - 1.15, side * B * 0.37, dz + 1.5), material=hm))
        parts.append(rod((hx - 3.5, side * B * 0.37, dz), (hx - 3.5, side * B * 0.37, dz + 2.0), 0.03, 6, hm))
    # hauler davit and a stack of traps (crates)
    parts.append(spar((hx - 0.4, B * 0.42, dz), (hx - 0.4, B * 0.42, dz + 1.6), 0.05, 0.04, PAL['steel']))
    parts.append(spar((hx - 0.4, B * 0.42, dz + 1.6), (hx - 0.4, B * 0.62, dz + 1.45), 0.04))
    trap = mat('trap', '#7a8c5a', 0.8)
    for i in range(r.randint(3, 6)):
        parts.append(box((1.0, 0.55, 0.45), (-L / 2 + 1.0 + (i % 3) * 0.05, -0.5 + (i % 2) * 1.0, dz + 0.22 + (i // 2) * 0.46), material=trap, bevel=0.02))
    parts.append(spar((-L / 2 + 0.6, 0, dz + 2.0), (-L / 2 + 0.6, 0, dz + 3.2), 0.04))
    return join(parts, name)

TYPES = [('Dinghy (cat rig)', dinghy), ('Keelboat (sloop)', keelboat), ('Gaff cutter', gaff_cutter),
         ('Harbour tug', tug), ('Banks dory', dory), ('Downeast workboat', workboat)]
