"""Canadian Coast Guard Bay-class 19 m motor lifeboat (Cape / Arun style), rebuilt October 2026.
Metres, Z up, +X is the bow, waterline z = 0. Same envelope and node contract as the old model:
  19.0 m x 6.33 m hull, keel at z = -1.67, deck about z = 1.5, animated parts anim_radar / anim_flag (x2) exported as bay_radar0 / bay_flag0 / bay_flag1.
The hull is a real lofted shell (flared and raked bow, bulwark, sheer, hard chine, deep V); the deckhouse, mast, rails and rescue craft sit on it."""
import math, bpy, bmesh
from mathutils import Vector, Matrix
from pg_core import *

RED, WHITE, BOOT, BOTTOM, DECKC, GLASS = '#d52b1e', '#f1efe9', '#1d1d1f', '#8e2e24', '#6f6863', '#16222b'
ORANGE, STEEL, GREY, DGREY = '#e86a1c', '#9aa1a8', '#8d9399', '#2d3035'
HL = 9.45         # half length (the stern fenders add the last 0.1 m, so the model is 19.0 m long)
WSH = 3.165       # half beam at the top of the bulwark

def sstep(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)

# ------------------------------------------------------------- hull loft (t = 0 stern .. 1 stem)
def xt(t): return -HL + 2 * HL * t
def zs(t):                                           # main deck edge: lowest just aft of amidships, rising to the bow
    if t < 0.4: return 1.45 + 0.14 * (1 - t / 0.4) ** 2
    return 1.45 + 1.35 * ((t - 0.4) / 0.6) ** 1.8
def bh(t): return 0.28 + 0.62 * sstep((t - 0.6) / 0.32)       # bulwark height above the deck edge
def zt(t): return zs(t) + bh(t)
def zk(t):
    if t < 0.3: return -1.67 + 0.45 * (1 - t / 0.3) ** 2
    if t > 0.55: return -1.67 + 1.2 * sstep((t - 0.55) / 0.45) ** 1.4
    return -1.67
def ysh(t):                                          # plan half breadth at the top of the bulwark
    if t < 0.45: return WSH * (0.84 + 0.16 * math.sin(t / 0.45 * math.pi / 2) ** 0.5)
    u = (t - 0.45) / 0.55
    return WSH * max(0.0, math.cos(u * math.pi / 2)) ** 0.85
def flare(t): return 0.07 + 0.43 * sstep((t - 0.5) / 0.5) ** 1.3
def yat(t, z):                                       # half breadth of the topside flare line at height z
    return max(ysh(t) - flare(t) * (zt(t) - z), 0.1 * ysh(t))
def rake(t, z):                                      # stem rake: lower points lie aft of the stem head
    g = sstep((t - 0.6) / 0.4) ** 1.2
    top, bot = zt(t), zk(t)
    return -2.3 * g * (top - z) / max(top - bot, 0.1)

def hull_rows(t):
    zT, zK = zt(t), zk(t)
    zc = zK * 0.5
    zb = zc + 0.6 * (zK - zc)
    zm = 0.34 + (zT - 0.16 - 0.34) * 0.5
    yc = max(yat(t, 0) - 0.12 * (-zc), 0.0)
    return [(yat(t, zT), zT), (yat(t, zT - 0.16), zT - 0.16), (yat(t, zm), zm), (yat(t, 0.34), 0.34), (yat(t, 0.22), 0.22),
            (yat(t, 0.0), 0.0), (yc, zc), (yc * 0.45, zb), (0.0, zK)]

def build_hull(S=44):
    bm = bmesh.new(); rows = len(hull_rows(0.0)); ringn = 2 * rows - 1
    vs = []
    for i in range(S + 1):
        t = i / S
        half = [(y, z, xt(t) + rake(t, z)) for (y, z) in hull_rows(t)]
        ring = half + [(-y, z, x) for (y, z, x) in reversed(half[:-1])]
        vs.append([bm.verts.new((x, y, z)) for (y, z, x) in ring])
    for i in range(S):
        for k in range(ringn - 1):
            bm.faces.new((vs[i][k], vs[i + 1][k], vs[i + 1][k + 1], vs[i][k + 1]))
    bm.faces.new(vs[0])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-5)
    bm.normal_update()
    # winding vote: side faces must point away from the centreline
    side = [f for f in bm.faces if f.is_valid and abs(f.normal.y) > 0.5 and abs(f.calc_center_median().y) > 0.05]
    vote = sum(1 for f in side if f.normal.y * f.calc_center_median().y > 0)
    if vote < len(side) / 2: bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.normal_update()
    for f in bm.faces:
        if f.calc_center_median().x < -HL + 1e-3 and abs(f.normal.x) > 0.9 and f.normal.x > 0: f.normal_flip()
    return bm

def cut_planes(o, planes):
    bm = bmesh.new(); bm.from_mesh(o.data)
    for co, no in planes:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
    bm.to_mesh(o.data); bm.free()

def paint_hull(o, sx=4.6, sw=1.0):
    """Topsides red; black boot-top, thin white cove line, white gunwale cap, and the CCG diagonal: one white bar edged by thin dark lines, raked 60 degrees."""
    k = math.tan(math.radians(30)); line = 0.07
    u0, u1 = sx - sw / 2, sx + sw / 2
    no = Vector((1, 0, -k)).normalized()
    cut_planes(o, [((e, 0, 0), tuple(no)) for e in (u0 - line, u0, u1, u1 + line)])
    o.data.materials.clear()
    for m in (mat('ccg_red', RED, 0.45), mat('ccg_bottom', BOTTOM, 0.8), mat('ccg_boot', BOOT, 0.6), mat('ccg_white', WHITE, 0.4), mat('ccg_line', '#2a1d1d', 0.6)):
        o.data.materials.append(m)
    bm = bmesh.new(); bm.from_mesh(o.data)
    for f in bm.faces:
        c = f.calc_center_median(); tc = min(max((c.x + HL) / (2 * HL), 0), 1); u = c.x - c.z * k
        if c.z < 0: f.material_index = 1
        elif c.z < 0.22: f.material_index = 2
        elif c.z < 0.34: f.material_index = 3
        elif c.z > zt(tc) - 0.17: f.material_index = 3
        elif u0 < u < u1: f.material_index = 3
        elif u0 - line < u < u0 or u1 < u < u1 + line: f.material_index = 4
        else: f.material_index = 0
    bm.to_mesh(o.data); bm.free()

def smooth_by_angle(o, deg=38):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(deg))

def deck_mesh(S=44):
    verts, faces = [], []
    for i in range(S + 1):
        t = i / S; z = zs(t) - 0.005; y = max(yat(t, z) - 0.04, 0.0); x = xt(t) + rake(t, z)
        verts += [(x, y, z), (x, -y, z)]
    for i in range(S):
        a = 2 * i; faces.append((a, a + 1, a + 3, a + 2))
    o = mesh('deck', verts, faces, mat('deck_bay', DECKC, 0.85))
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4); bm.to_mesh(o.data); bm.free()
    return o

# ------------------------------------------------------------- small builders
def tube(pts, r, seg=4, material=None, closed=False, smooth=False, name='tube', rot0=0.0):
    pts = [Vector(p) for p in pts]; n = len(pts); verts, faces = [], []
    for i, p in enumerate(pts):
        d = (pts[(i + 1) % n] - pts[i - 1]) if closed else (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)])
        d.normalize(); s = d.cross(Vector((0, 0, 1)))
        if s.length < 1e-4: s = Vector((0, 1, 0))
        s.normalize(); u = s.cross(d).normalized()
        for k in range(seg):
            a = rot0 + 2 * math.pi * k / seg
            verts.append(p + s * (r * math.cos(a)) + u * (r * math.sin(a)))
    for i in range(n if closed else n - 1):
        i2 = (i + 1) % n
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((i * seg + k, i2 * seg + k, i2 * seg + k2, i * seg + k2))
    if not closed:
        faces.append(tuple(reversed(range(seg)))); faces.append(tuple((n - 1) * seg + k for k in range(seg)))
    return mesh(name, verts, faces, material, smooth)

HEXF = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
def hexa(v, material, name='hexa'):
    """8 corners: 0..3 the bottom quad counter-clockwise from above (aft-right, fwd-right, fwd-left, aft-left; right = -Y), 4..7 the top above them."""
    return mesh(name, v, HEXF, material)

def patch(c, u, v):
    a, b, cc, d = [Vector(p) for p in c]
    return a * (1 - u) * (1 - v) + b * u * (1 - v) + cc * u * v + d * (1 - u) * v

def slab(c, centre, u0, u1, v0, v1, d0, d1, material):
    """A thin raised panel on a bilinear wall patch c = (u0v0, u1v0, u1v1, u0v1); pushed outward, away from `centre`."""
    q = [patch(c, u0, v0), patch(c, u1, v0), patch(c, u1, v1), patch(c, u0, v1)]
    n = (q[1] - q[0]).cross(q[3] - q[0]).normalized(); mid = sum(q, Vector()) / 4
    if n.dot(mid - Vector(centre)) < 0:
        n = -n; q = [q[0], q[3], q[2], q[1]]
    v = [p + n * d0 for p in q] + [p + n * d1 for p in q]
    return mesh('slab', v, HEXF, material)

def windows(parts, c, centre, spans, v0, v1, glass, frame, m=0.016):
    for (a, b) in spans:
        parts.append(slab(c, centre, a - m, b + m, v0 - m * 1.6, v1 + m * 1.6, -0.02, 0.022, frame))
        parts.append(slab(c, centre, a, b, v0, v1, -0.02, 0.04, glass))

def bollard(x, y, z, m):
    return [cyl(0.09, 0.09, 0.24, 8, loc=(x, y, z), material=m), cyl(0.15, 0.13, 0.07, 8, loc=(x, y, z + 0.24), material=m)]

def lifering(x, y, z, axis, mo, mw):
    """A life ring (orange, white quarters) hung on a vertical surface; axis 'x' faces fore-aft, 'y' faces athwartships."""
    rot = (0, math.pi / 2, 0) if axis == 'x' else (math.pi / 2, 0, 0)
    out = [torus(0.27, 0.075, 16, 5, loc=(x, y, z), rot=rot, material=mo)]
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        if axis == 'y': off, sz = (0.27 * math.cos(a), 0.0, 0.27 * math.sin(a)), (0.15, 0.17, 0.15)
        else: off, sz = (0.0, 0.27 * math.cos(a), 0.27 * math.sin(a)), (0.17, 0.15, 0.15)
        out.append(box(sz, (x + off[0], y + off[1], z + off[2]), material=mw))
    return out

def navlight(x, y, z, color):
    return box((0.14, 0.12, 0.12), (x, y, z), material=mat('nav' + color, color, 0.4, emit=color, emit_str=1.6))

# ------------------------------------------------------------- the boat
def build(name='bay_class'):
    import pg_marine as M
    parts = []
    mred, mwhite, mglass = mat('ccg_red', RED, 0.45), mat('ccg_white', WHITE, 0.4), mat('glass', GLASS, 0.1, 0.2)
    mfr, mdk, mor = mat('frame', STEEL, 0.5, 0.3), mat('fit', '#2b2b2b', 0.6, 0.3), mat('lifering', ORANGE, 0.5)
    mrail, mblack, mgrey = mat('rail_white', '#e9e7e1', 0.4), mat('fender', '#161618', 0.85), mat('inflatable', GREY, 0.75)
    mss = mat('ss_' + WHITE, WHITE, 0.45)

    # --- hull
    hull = obj_from_bm(build_hull(), 'hull')
    paint_hull(hull)
    solidify(hull, 0.035)
    smooth_by_angle(hull, 38)
    parts += [hull, deck_mesh()]
    tz = lambda x: (x + HL) / (2 * HL)

    # --- wheelhouse and cabin (hexahedra: trapezoid plan, raked windscreen)
    xa, xf, wa, wf, zr = -2.4, 3.2, 1.95, 1.55, 3.80
    zA = zF = zs(tz(xa)) - 0.04                     # one flat sill so every wall is planar (the front sinks into the rising foredeck)
    rk = 0.85
    wt = wf - (wa + (wf - wa) / (xf - xa) * (xf - rk - xa))        # keeps the side walls flat
    cab = [(xa, -wa, zA), (xf, -wf, zF), (xf, wf, zF), (xa, wa, zA), (xa, -wa, zr), (xf - rk, -(wf - wt), zr), (xf - rk, wf - wt, zr), (xa, wa, zr)]
    parts.append(hexa(cab, mss, 'cabin'))
    cc = (0.5, 0, 2.6)
    front = (cab[1], cab[2], cab[6], cab[5]); port = (cab[3], cab[2], cab[6], cab[7]); stbd = (cab[0], cab[1], cab[5], cab[4]); aft = (cab[0], cab[3], cab[7], cab[4])
    windows(parts, front, cc, [(0.05, 0.245), (0.265, 0.49), (0.51, 0.735), (0.755, 0.95)], 0.30, 0.88, mglass, mfr)
    for sd in (port, stbd): windows(parts, sd, cc, [(0.10, 0.29), (0.34, 0.53), (0.58, 0.77)], 0.36, 0.84, mglass, mfr)
    parts.append(slab(aft, cc, 0.40, 0.60, 0.04, 0.82, -0.02, 0.05, mfr))                      # aft door
    parts.append(slab(aft, cc, 0.43, 0.57, 0.50, 0.76, -0.02, 0.07, mglass))
    ov = 0.14
    roof = [(xa - ov, -wa - ov, zr), (xf - rk + 0.22, -(wf - wt) - ov, zr), (xf - rk + 0.22, wf - wt + ov, zr), (xa - ov, wa + ov, zr),
            (xa - ov, -wa - ov, zr + 0.12), (xf - rk + 0.22, -(wf - wt) - ov, zr + 0.12), (xf - rk + 0.22, wf - wt + ov, zr + 0.12), (xa - ov, wa + ov, zr + 0.12)]
    parts.append(hexa(roof, mss, 'roof'))
    zrt = zr + 0.12

    # --- flying bridge (upper steering station)
    bxa, bxf, bwa, bwf, bz1 = 0.0, 2.2, 1.35, 1.12, zrt + 0.92
    bwt = bwa + (bwf - bwa) / (bxf - bxa) * (bxf - 0.5 - bxa)
    fb = [(bxa, -bwa, zrt - 0.02), (bxf, -bwf, zrt - 0.02), (bxf, bwf, zrt - 0.02), (bxa, bwa, zrt - 0.02),
          (bxa, -bwa, bz1), (bxf - 0.5, -bwt, bz1), (bxf - 0.5, bwt, bz1), (bxa, bwa, bz1)]
    parts.append(hexa(fb, mss, 'bridge'))
    fc = (1.1, 0, zrt + 0.5)
    windows(parts, (fb[1], fb[2], fb[6], fb[5]), fc, [(0.06, 0.32), (0.36, 0.64), (0.68, 0.94)], 0.28, 0.84, mglass, mfr)
    for sd in ((fb[3], fb[2], fb[6], fb[7]), (fb[0], fb[1], fb[5], fb[4])): windows(parts, sd, fc, [(0.12, 0.45), (0.55, 0.88)], 0.28, 0.84, mglass, mfr)
    ex, y1, y2 = bxf - 0.5 + 0.28, bwt + 0.12, bwa + 0.12
    bro = [(bxa - 0.1, -y2, bz1), (ex, -y1, bz1), (ex, y1, bz1), (bxa - 0.1, y2, bz1), (bxa - 0.1, -y2, bz1 + 0.11), (ex, -y1, bz1 + 0.11), (ex, y1, bz1 + 0.11), (bxa - 0.1, y2, bz1 + 0.11)]
    parts.append(hexa(bro, mss, 'bridge_roof'))
    ztop = bz1 + 0.11
    parts.append(cyl(0.07, 0.07, 0.22, 8, loc=(1.3, 0, ztop), material=mdk))                                                          # searchlight
    parts.append(cyl(0.2, 0.2, 0.34, 10, loc=(1.3, 0, ztop + 0.3), rot=(0, math.pi / 2, 0), material=mat('search', '#c9ccd0', 0.35, 0.4)))
    parts.append(cyl(0.17, 0.17, 0.02, 10, loc=(1.64, 0, ztop + 0.3), rot=(0, math.pi / 2, 0), material=mat('lens', '#fff3b0', 0.2, emit='#fff3b0', emit_str=1.5)))
    parts.append(cyl(0.12, 0.2, 0.28, 8, loc=(0.35, 0.55, ztop), rot=(0, 0.5, 0), material=mat('horn', '#c9ccd0', 0.4, 0.4)))
    parts.append(navlight(1.45, bwf + 0.02, bz1 - 0.22, '#ff2020'))      # port (left looking forward, +Y)
    parts.append(navlight(1.45, -(bwf + 0.02), bz1 - 0.22, '#18d85a'))   # starboard

    # --- roof handrail
    rz = zrt
    corners = [(xa + 0.02, -(wa - 0.1)), (xf - rk - 0.1, -(wf - wt - 0.1)), (xf - rk - 0.1, wf - wt - 0.1), (xa + 0.02, wa - 0.1)]
    loop = corners + [corners[0]]
    for a, b in zip(loop[:-1], loop[1:]):
        parts.append(rod((a[0], a[1], rz + 0.62), (b[0], b[1], rz + 0.62), 0.028, 4, mrail))
        parts.append(rod((a[0], a[1], rz + 0.3), (b[0], b[1], rz + 0.3), 0.022, 4, mrail))
    for (px, py) in corners + [(-0.2, -(wa - 0.1)), (-0.2, wa - 0.1), (xa + 0.02, 0.0)]:
        parts.append(rod((px, py, rz), (px, py, rz + 0.62), 0.03, 4, mrail))

    # --- exhaust funnel (red, black top)
    parts.append(box((0.95, 1.1, 1.8), (-1.75, 0, zrt + 0.9), (0, -0.09, 0), material=mred, bevel=0.09))
    parts.append(box((0.99, 1.14, 0.14), (-1.87, 0, zrt + 1.8), (0, -0.09, 0), material=mat('funnel_top', '#262626', 0.6), bevel=0.05))
    parts.append(cyl(0.13, 0.13, 0.35, 8, loc=(-1.98, 0.0, zrt + 1.85), material=mdk))

    # --- lattice mast with radar scanner (animated), antennas, lights, ensign staff
    mx = -0.62; z0 = zrt; levels = [(z0, 0.40), (z0 + 1.25, 0.31), (z0 + 2.0, 0.23), (z0 + 2.7, 0.16)]
    corner = lambda lv, sx, sy: (mx + sx * lv[1], sy * lv[1], lv[0])
    for sx in (1, -1):
        for sy in (1, -1):
            for a, b in zip(levels[:-1], levels[1:]): parts.append(rod(corner(a, sx, sy), corner(b, sx, sy), 0.035, 4, mrail))
    for lv in levels:
        cs = [corner(lv, 1, 1), corner(lv, 1, -1), corner(lv, -1, -1), corner(lv, -1, 1)]
        for p, q in zip(cs, cs[1:] + cs[:1]): parts.append(rod(p, q, 0.022, 4, mrail))
    for a, b in zip(levels[:-1], levels[1:]):
        for (s1, s2) in (((1, 1), (1, -1)), ((1, -1), (-1, -1)), ((-1, -1), (-1, 1)), ((-1, 1), (1, 1))):
            parts.append(rod(corner(a, *s1), corner(b, *s2), 0.018, 4, mrail))
    zp = levels[-1][0]
    parts.append(box((0.62, 0.62, 0.08), (mx, 0, zp + 0.04), material=mss))
    parts.append(cyl(0.06, 0.06, 0.3, 6, loc=(mx, 0, zp + 0.08), material=mdk))
    mrad = mat('radar', '#2b2b2b', 0.5)
    sc = join([box((0.14, 1.5, 0.2), (mx, 0, zp + 0.5), material=mrad), box((0.2, 1.5, 0.06), (mx - 0.06, 0, zp + 0.5), material=mrad)], 'radar_bar')
    M.pivoted(sc, (mx, 0, zp + 0.5), 'anim_radar')
    parts.append(rod((mx, -0.55, zp + 0.95), (mx, 0.55, zp + 0.95), 0.03, 4, mrail))                       # yardarm with nav lights
    parts.append(navlight(mx, 0.55, zp + 0.95, '#ff2020')); parts.append(navlight(mx, -0.55, zp + 0.95, '#18d85a'))
    parts.append(rod((mx, 0, zp + 0.08), (mx, 0, zp + 1.5), 0.04, 6, mrail))                                # topmast
    parts.append(ico(0.13, 1, loc=(mx + 0.2, 0.18, zp + 0.3), material=mat('dome', '#ecebe6', 0.4)))        # GPS dome
    parts.append(box((0.1, 0.1, 0.1), (mx, 0, zp + 1.5), material=mat('masthead', '#fffbe8', 0.3, emit='#fffbe8', emit_str=2.0)))
    parts.append(rod((mx + 0.12, 0.2, zp + 0.08), (mx + 0.14, 0.22, 9.0), 0.012, 3, mdk))                  # VHF whip: the model tops out at 9.0 m
    parts.append(rod((mx - 0.18, -0.2, zp + 0.08), (mx - 0.2, -0.22, zp + 1.1), 0.012, 3, mdk))
    parts.append(rod((mx + 0.16, -0.2, zp + 0.08), (mx + 0.16, -0.2, zp + 0.85), 0.012, 3, mdk))
    M.flag_on(mx, zp + 1.5, 0.45, parts)                                                                     # pennant at the masthead (bay_flag0)
    M.flag_on(-9.2, zs(0.02) + 0.02, 0.45, parts)                                                          # ensign at the stern (bay_flag1)

    # --- foredeck
    zf = lambda x: zs(tz(x))
    parts.append(box((0.9, 0.8, 0.22), (5.6, 0, zf(5.6) + 0.1), material=mss, bevel=0.06))                 # forward hatch
    parts.append(cyl(0.2, 0.22, 0.42, 8, loc=(7.15, 0, zf(7.15)), material=mdk))                           # windlass
    parts.append(cyl(0.16, 0.16, 0.7, 8, loc=(8.0, 0, zf(8.0)), material=mss))                             # samson post
    parts.append(cyl(0.2, 0.2, 0.06, 8, loc=(8.0, 0, zf(8.0) + 0.7), material=mdk))
    for s in (1, -1): parts += bollard(6.5, s * 0.6, zf(6.5), mdk)

    # --- deck edge rails, stanchions and rubbing strake (both sides)
    N = 14; ts = [0.012 + (0.6 - 0.012) * i / N for i in range(N + 1)]
    for s in (1, -1):
        base = [(xt(t), s * (yat(t, zt(t)) - 0.1), zt(t)) for t in ts]
        parts.append(tube([(p[0], p[1], p[2] + 0.74) for p in base], 0.03, 4, mrail, name='toprail'))
        parts.append(tube([(p[0], p[1], p[2] + 0.38) for p in base], 0.022, 4, mrail, name='midrail'))
        for p in base[::2]: parts.append(rod(p, (p[0], p[1], p[2] + 0.74), 0.03, 4, mrail))
        parts.append(rod(base[-1], (base[-1][0], base[-1][1], base[-1][2] + 0.74), 0.035, 4, mrail))
        sp = [(xt(t) + rake(t, zs(t) - 0.7), s * (yat(t, zs(t) - 0.7) + 0.03), zs(t) - 0.7) for t in [0.02 + 0.66 * i / 18 for i in range(19)]]
        parts.append(tube(sp, 0.05, 4, mblack, name='strake', rot0=math.pi / 4))
    sx0 = -9.34; wsd = yat(0.0, zt(0.0)) - 0.1; zst = zt(0.0)
    for (ya, yb) in ((0.75, wsd), (-0.75, -wsd)):                                   # stern rail, open in the middle for the rescue craft
        parts.append(rod((sx0, ya, zst + 0.74), (sx0, yb, zst + 0.74), 0.03, 4, mrail)); parts.append(rod((sx0, ya, zst + 0.38), (sx0, yb, zst + 0.38), 0.022, 4, mrail))
        parts.append(rod((sx0, ya, zst), (sx0, ya, zst + 0.74), 0.035, 4, mrail))

    stem = [(xt(1.0) + rake(1.0, z), 0.0, z) for z in (0.3, 0.9, 1.6, 2.4, 3.1, zt(1.0) - 0.04)]
    parts.append(tube(stem, 0.07, 4, mblack, name='stembar', rot0=math.pi / 4))                              # black stem fender
    # --- stern: fenders, towing post, bollards
    for y in (-1.9, -0.95, 0.0, 0.95, 1.9):
        parts.append(cyl(0.1, 0.1, 0.85, 8, loc=(-HL, y, zs(0.0) - 0.95), material=mblack))
    mtow = mat('towpost', '#38342f', 0.6, 0.3)
    parts.append(cyl(0.2, 0.22, 0.85, 8, loc=(-8.35, 0, zs(0.02)), material=mtow))
    parts.append(cyl(0.3, 0.3, 0.08, 8, loc=(-8.35, 0, zs(0.02) + 0.85), material=mtow))
    for s in (1, -1):
        parts += bollard(-8.1, s * (yat(0.03, zs(0.03)) - 0.4), zs(0.03), mdk)
        parts += bollard(-3.4, s * (yat(0.32, zs(0.32)) - 0.35), zs(0.32), mdk)

    # --- stern gantry (davit) over the rescue craft
    gx = -8.85; gz0 = zs(0.01); gz1 = gz0 + 2.9; gy = 2.15
    for s in (1, -1):
        parts.append(rod((gx, s * gy, gz0), (gx + 0.12, s * gy, gz1), 0.08, 6, mrail))
        parts.append(rod((gx + 0.12, s * gy, gz1 - 1.9), (gx + 1.3, s * gy, gz0), 0.045, 4, mrail))
    parts.append(rod((gx + 0.12, -gy, gz1), (gx + 0.12, gy, gz1), 0.09, 6, mrail))
    parts.append(box((0.3, 0.3, 0.26), (gx + 0.12, 0, gz1 - 0.2), material=mor, bevel=0.05))

    # --- rescue craft: grey inflatable on a cradle
    cx, wcl, ch = -5.4, 0.62, zs(0.2) + 0.3
    path = []
    for i in range(20):
        a = 2 * math.pi * i / 20; c, s_ = math.cos(a), math.sin(a)
        x = cx + 1.95 * math.copysign(abs(c) ** 0.7, c); y = wcl * math.copysign(abs(s_) ** 0.7, s_) * (1 - 0.55 * max(0.0, c) ** 2)
        path.append((x, y, ch + 0.29))
    parts.append(tube(path, 0.28, 8, mgrey, closed=True, smooth=True, name='rhib_tube'))
    fl = [(cx + (p[0] - cx) * 0.9, p[1] * 0.86, ch + 0.13) for p in path]
    parts.append(mesh('rhib_floor', fl, [tuple(range(len(fl)))], mat('rhib_floor', '#34383d', 0.8)))
    parts.append(box((0.55, 0.7, 0.5), (cx + 0.35, 0, ch + 0.4), material=mdk, bevel=0.05))
    parts.append(box((0.08, 0.6, 0.3), (cx + 0.66, 0, ch + 0.78), (0, -0.5, 0), material=mglass))
    parts.append(box((0.36, 0.34, 0.62), (cx - 2.0, 0, ch + 0.42), material=mat('outboard', '#25282c', 0.55)))
    for s in (1, -1): parts.append(box((4.4, 0.16, 0.12), (cx, s * 0.5, ch - 0.18), material=mrail))
    for dx in (-1.5, 0.0, 1.4): parts.append(box((0.14, 1.3, 0.12), (cx + dx, 0, ch - 0.25), material=mrail))

    # --- life rings
    for s in (1, -1):
        parts += lifering(xa - 0.04, s * 1.35, 2.75, 'x', mor, mwhite)
        parts += lifering(-6.7, s * (yat(0.17, zt(0.17)) - 0.12), zt(0.17) + 0.58, 'y', mor, mwhite)
    return join(parts, name)
