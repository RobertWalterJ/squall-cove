"""Guard towers (wood 8 m, concrete 10 m, steel lattice 12 m) and freestanding ladders. Game coords (x left, y up, z forward).
Every ladder faces +Z: rungs in the plane z = Z_rung, the climber stands at z = Z_rung + 0.40 facing -Z."""
from e_lib import *

CLIMB = 0.40     # distance from rung plane to the climber's standing line


def wall(P, axis, c, a0, a1, y0, y1, th, openings, mat, glass=None, frame='emp_steel_dark'):
    """Wall in a plane. axis 'z': plane z=c spanning x in [a0,a1]; axis 'x': plane x=c spanning z. openings: (b0, b1, ya, yb[, kind])."""
    def B(u0, u1, v0, v1):
        if u1 - u0 < 1e-4 or v1 - v0 < 1e-4: return
        if axis == 'z': bx(P, u0, u1, v0, v1, c - th / 2, c + th / 2, mat)
        else: bx(P, c - th / 2, c + th / 2, v0, v1, u0, u1, mat)
    edges = sorted({a0, a1} | {o[0] for o in openings} | {o[1] for o in openings})
    for u0, u1 in zip(edges, edges[1:]):
        hit = [o for o in openings if o[0] <= u0 + 1e-6 and o[1] >= u1 - 1e-6]
        if not hit: B(u0, u1, y0, y1)
        else:
            o = hit[0]; B(u0, u1, y0, o[2]); B(u0, u1, o[3], y1)
    for o in openings:
        b0, b1, ya, yb = o[:4]; kind = o[4] if len(o) > 4 else 'window'; ft = 0.05
        if kind == 'window':
            # frame + glass + mullion
            if axis == 'z':
                bx(P, b0, b1, ya, ya + ft, c - th / 2 - 0.02, c + th / 2 + 0.02, frame); bx(P, b0, b1, yb - ft, yb, c - th / 2 - 0.02, c + th / 2 + 0.02, frame)
                bx(P, b0, b0 + ft, ya, yb, c - th / 2 - 0.02, c + th / 2 + 0.02, frame); bx(P, b1 - ft, b1, ya, yb, c - th / 2 - 0.02, c + th / 2 + 0.02, frame)
                bx(P, (b0 + b1) / 2 - 0.02, (b0 + b1) / 2 + 0.02, ya, yb, c - 0.02, c + 0.02, frame)
                if glass: bx(P, b0 + ft, b1 - ft, ya + ft, yb - ft, c - 0.008, c + 0.008, glass)
            else:
                bx(P, c - th / 2 - 0.02, c + th / 2 + 0.02, ya, ya + ft, b0, b1, frame); bx(P, c - th / 2 - 0.02, c + th / 2 + 0.02, yb - ft, yb, b0, b1, frame)
                bx(P, c - th / 2 - 0.02, c + th / 2 + 0.02, ya, yb, b0, b0 + ft, frame); bx(P, c - th / 2 - 0.02, c + th / 2 + 0.02, ya, yb, b1 - ft, b1, frame)
                bx(P, c - 0.02, c + 0.02, ya, yb, (b0 + b1) / 2 - 0.02, (b0 + b1) / 2 + 0.02, frame)
                if glass: bx(P, c - 0.008, c + 0.008, ya + ft, yb - ft, b0 + ft, b1 - ft, glass)
        elif kind == 'door':
            if axis == 'z':
                bx(P, b0 + 0.04, b1 - 0.04, ya, yb - 0.04, c - 0.03, c + 0.03, 'emp_steel_dark')
                bx(P, b0, b0 + 0.05, ya, yb, c - th / 2 - 0.02, c + th / 2 + 0.02, frame); bx(P, b1 - 0.05, b1, ya, yb, c - th / 2 - 0.02, c + th / 2 + 0.02, frame)
                bx(P, b0, b1, yb - 0.05, yb, c - th / 2 - 0.02, c + th / 2 + 0.02, frame)
                bx(P, b1 - 0.16, b1 - 0.10, ya + 0.95, ya + 1.0, c + 0.03, c + 0.09, 'emp_galv')
            else:
                bx(P, c - 0.03, c + 0.03, ya, yb - 0.04, b0 + 0.04, b1 - 0.04, 'emp_steel_dark')
                bx(P, c - th / 2 - 0.02, c + th / 2 + 0.02, ya, yb, b0, b0 + 0.05, frame); bx(P, c - th / 2 - 0.02, c + th / 2 + 0.02, ya, yb, b1 - 0.05, b1, frame)
                bx(P, c - th / 2 - 0.02, c + th / 2 + 0.02, yb - 0.05, yb, b0, b1, frame)
                bx(P, c + 0.03, c + 0.09, ya + 0.95, ya + 1.0, b1 - 0.16, b1 - 0.10, 'emp_galv')


def rail_run(P, a, b, y0, h, mat='emp_galv', mid=True, post_step=1.0, toe=True, wood=False):
    """Handrail from point a to b (x, z) at deck height y0: posts every ~post_step, top rail at h, mid rail, toe board."""
    ax, az = a; bx_, bz = b; Ln = math.hypot(bx_ - ax, bz - az); n = max(1, round(Ln / post_step))
    for i in range(n + 1):
        t = i / n; px = ax + (bx_ - ax) * t; pz = az + (bz - az) * t
        key = (round(px, 2), round(pz, 2), round(y0, 2)); seen = P.__dict__.setdefault('_posts', set())
        if key in seen: continue                       # corner posts are shared by two rail runs (avoid coplanar duplicates)
        seen.add(key)
        bar(P, (px, y0, pz), (px, y0 + h, pz), 0.05, mat)
    bar(P, (ax, y0 + h, az), (bx_, y0 + h, bz), 0.05, mat)
    if mid: bar(P, (ax, y0 + h * 0.52, az), (bx_, y0 + h * 0.52, bz), 0.035, mat)
    if toe:
        d = Vector((bx_ - ax, 0, bz - az)).normalized(); mid_ = Vector(((ax + bx_) / 2, y0 + 0.06, (az + bz) / 2))
        ang = math.degrees(math.atan2(d.x, d.z))
        P.box(tuple(mid_), (0.02, 0.12, Ln), mat, rot=(0, ang, 0))


# ================================================================== wooden guard tower (8 m)
def tower_guard_wood():
    M = EM('tower_guard_wood'); rng = random.Random(52)
    DY = 5.0; H = 1.1; ZR = 0.30                 # deck surface height, leg centre offset, ladder rung plane
    B = M.node('_body', None, (0, 0, 0))
    for sx in (-1, 1):
        for sz in (-1, 1):
            B.box((sx * H, 0.14, sz * H), (0.52, 0.28, 0.52), 'emp_concrete')                       # footings
            bar(B, (sx * H, 0.26, sz * H), (sx * H, 7.18, sz * H), 0.22, 'emp_wood')             # legs / posts
            for yy in (0.9, 3.0): B.box((sx * H, yy, sz * H), (0.27, 0.05, 0.27), 'emp_steel_dark')   # bolt plates
    # girts and X-bracing: sides, back, upper front bay
    levels = [0.32, 2.40, 4.50]
    def face(fixed, axis, y0, y1, girts=(True, True)):
        def pt(u, y, off=0.0): return (fixed + off, y, u) if axis == 'x' else (u, y, fixed + off)
        sg = 1 if fixed > 0 else -1
        for y, on in zip((y0, y1), girts):
            if on: bar(B, pt(-H, y), pt(H, y), 0.14, 'emp_wood_light')
        bar(B, pt(-H, y0), pt(H, y1), 0.11, 'emp_wood_light'); bar(B, pt(H, y0, sg * 0.03), pt(-H, y1, sg * 0.03), 0.11, 'emp_wood_light')
    ox = H + 0.13
    for sx in (-1, 1):
        face(sx * ox, 'x', levels[0], levels[1]); face(sx * ox, 'x', levels[1], levels[2], girts=(False, True))
    face(-ox, 'z', levels[0], levels[1]); face(-ox, 'z', levels[1], levels[2], girts=(False, True))
    face(ox, 'z', levels[1], levels[2], girts=(False, True))
    bar(B, (-H, levels[1], ox), (H, levels[1], ox), 0.14, 'emp_wood_light')
    # deck frame: main beams, joists, hatch headers, planks
    for sz in (-1, 1): bar(B, (-H - 0.12, 4.74, sz * H), (H + 0.12, 4.74, sz * H), 0.24, 'emp_wood_dark')
    for sx in (-1, 1): bar(B, (sx * H, 4.74, -H - 0.12), (sx * H, 4.74, H + 0.12), 0.24, 'emp_wood_dark')
    for x in (-0.9, -0.45, 0.45, 0.9): bar(B, (x, 4.88, -1.1), (x, 4.88, 1.1), 0.10, 'emp_wood_dark')
    for z in (0.0, 1.0): bar(B, (-0.45, 4.88, z), (0.45, 4.88, z), 0.10, 'emp_wood_dark')
    pw = 0.19; z0 = -1.2
    for k in range(12):
        zc = z0 + pw / 2 + k * (pw + 0.0105); y = 4.975
        if 0.02 < zc + pw / 2 and zc - pw / 2 < 0.98 and zc > -0.0:
            for (xa, xb) in ((-1.22, -0.40), (0.40, 1.22)): bx(B, xa, xb, 4.95, 5.0, zc - pw / 2, zc + pw / 2, 'emp_wood' if k % 2 else 'emp_wood_light')
        else:
            bx(B, -1.22, 1.22, 4.95, 5.0, zc - pw / 2, zc + pw / 2, 'emp_wood' if k % 2 else 'emp_wood_light')
    bx(B, -0.40, 0.40, 4.95, 5.07, 0.93, 1.0, 'emp_wood_dark'); bx(B, -0.43, -0.37, 4.95, 5.07, 0.0, 1.0, 'emp_wood_dark'); bx(B, 0.37, 0.43, 4.95, 5.07, 0.0, 1.0, 'emp_wood_dark')   # hatch coaming
    # ladder: rung plane z = ZR, through the hatch, rails 1.1 m above the deck
    ladder(B, 0.0, ZR, 0.0, DY, width=0.46, rung=0.30, rail_w=0.07, rail_d=0.07, rung_r=0.0165, top_ext=1.1, mat_rail='emp_wood', mat_rung='emp_wood_light')
    for by in (1.5, 3.4):
        for sx in (-1, 1): bar(B, (sx * 0.23, by, ZR), (sx * 0.23, by, ox - 0.06), 0.05, 'emp_wood_dark')
    bar(B, (-0.23, 4.62, ZR), (0.23, 4.62, ZR), 0.07, 'emp_wood_dark')
    # handrails (four sides) and kick boards
    top = 1.05
    for (a, b, mid) in (((1.0, -1.0), (1.0, 1.0), False), ((-1.0, -1.0), (-1.0, 1.0), True), ((-1.0, -1.0), (1.0, -1.0), True), ((-1.0, 1.0), (1.0, 1.0), False)):
        rail_run(B, a, b, DY, top, 'emp_wood', mid, post_step=0.7, toe=True)
    # sandbag parapet: +X side and +Z side (right of the hatch and left of it)
    bagline(B, (0.96, -0.98), (0.96, 0.70), 4, rng, y0=DY, rows=1)
    bagline(B, (0.44, 0.98), (0.98, 0.98), 4, rng, y0=DY)
    bagline(B, (-0.98, 0.98), (-0.44, 0.98), 4, rng, y0=DY)
    # roof: top plates, posts already run to 7.18; sloped panels with ribs; gable boards
    for sz in (-1, 1): bar(B, (-H - 0.15, 7.12, sz * H), (H + 0.15, 7.12, sz * H), 0.16, 'emp_wood_dark')
    for sx in (-1, 1): bar(B, (sx * H, 7.12, -H - 0.15), (sx * H, 7.12, H + 0.15), 0.16, 'emp_wood_dark')
    ridge_y = 8.0; eave_y = 7.2; half = 1.55
    L = math.hypot(half, ridge_y - eave_y); ub = (0, (ridge_y - eave_y) / L, -half / L)
    for sgn in (1, -1):
        ub2 = (0, (ridge_y - eave_y) / L, -sgn * half / L)
        slab(B, [(-1.45, 0), (1.45, 0), (1.45, L), (-1.45, L)], (0, eave_y, sgn * half), (1, 0, 0), ub2, 0.06, 'emp_roof')
        nrm = Vector((1, 0, 0)).cross(Vector(ub2)).normalized()
        for i in range(9):
            x = -1.36 + i * 0.34
            p0 = Vector((x, eave_y, sgn * half)) + nrm * 0.045; p1 = Vector((x, ridge_y, 0)) + nrm * 0.045
            bar(B, tuple(p0), tuple(p1), 0.04, 'emp_steel_dark')
    bar(B, (-1.5, ridge_y + 0.03, 0), (1.5, ridge_y + 0.03, 0), 0.16, 'emp_wood_dark')
    for sgn in (-1, 1):
        slab(B, [(-1.2, 7.2), (1.2, 7.2), (0, 7.95)], (sgn * 1.2, 0, 0), (0, 0, 1), (0, 1, 0), 0.05, 'emp_wood_dark')
        bar(B, (sgn * 1.2, 7.18, -1.2), (sgn * 1.2, 7.95, 0), 0.06, 'emp_wood_light'); bar(B, (sgn * 1.2, 7.18, 1.2), (sgn * 1.2, 7.95, 0), 0.06, 'emp_wood_light')
    for sx in (-1, 1): bar(B, (sx * 0.9, 7.12, -1.1), (sx * 0.9, 7.12, 1.1), 0.1, 'emp_wood')
    # searchlight on a bracket (front-left leg), a child node with its own pivot
    LP = (-1.40, 6.45, 1.34)
    bar(B, (-H, 6.45, H), (-1.28, 6.45, 1.28), 0.07, 'emp_steel_dark')
    bar(B, (-H, 6.00, H), (-1.28, 6.38, 1.28), 0.05, 'emp_steel_dark')
    B.box((-1.40, 6.40, 1.28), (0.16, 0.06, 0.16), 'emp_steel_dark')
    Lm = M.node('_lamp', None, LP)
    Lm.cyl((-1.40, 6.45, 1.16), (-1.40, 6.45, 1.62), 0.20, 0.22, 14, 'emp_steel', True)
    Lm.cyl((-1.40, 6.45, 1.62), (-1.40, 6.45, 1.70), 0.25, 0.25, 14, 'emp_steel_dark', False)
    Lm.cyl((-1.40, 6.45, 1.70), (-1.40, 6.45, 1.725), 0.20, 0.20, 14, 'emp_lens', False)
    Lm.cyl((-1.40, 6.45, 1.10), (-1.40, 6.45, 1.16), 0.12, 0.17, 10, 'emp_steel_dark', False)
    for sx in (-1, 1): Lm.box((-1.40 + sx * 0.25, 6.45, 1.34), (0.04, 0.12, 0.12), 'emp_steel_dark')
    # markers
    M.empty('tower_guard_wood_ladder_bottom', (0.0, 0.0, ZR + CLIMB), None, 'ARROWS')
    M.empty('tower_guard_wood_ladder_top', (0.0, DY, -0.35), None, 'ARROWS')
    M.empty('tower_guard_wood_deck', (0.0, DY, 0.0), None, 'CUBE', scale=(0.98, 1.0, 0.98))
    M.empty('tower_guard_wood_seat', (0.62, DY, 0.45), None, 'ARROWS')
    return M


# ================================================================== concrete guard tower (10 m)
def tower_guard_concrete():
    M = EM('tower_guard_concrete'); rng = random.Random(61)
    SH = 1.1; DY = 6.6; ZR = 1.45; WALL_Z = SH
    B = M.node('_body', None, (0, 0, 0))
    # shaft with plinth, formwork bands, capital
    B.box((0, 0.15, 0), (2.7, 0.30, 2.7), 'emp_concrete_dark')
    bx(B, -SH, SH, 0.30, 5.90, -SH, SH, 'emp_concrete')
    for yy in (1.4, 2.7, 4.0, 5.2): bx(B, -SH - 0.02, SH + 0.02, yy, yy + 0.07, -SH - 0.02, SH + 0.02, 'emp_concrete_dark')
    for yy in (0.7, 2.0, 3.3, 4.6):                                    # shuttering tie-hole rows
        for xx in (-0.7, 0.0, 0.7):
            for (nx, nz) in ((0, -1), (-1, 0), (1, 0)): B.box((nx * (SH + 0.005) + (xx if nx == 0 else 0), yy, nz * (SH + 0.005) + (xx if nz == 0 else 0)), (0.05 if nx == 0 else 0.012, 0.05, 0.05 if nz == 0 else 0.012), 'emp_black')
    bx(B, -1.22, 1.22, 5.90, 6.40, -1.22, 1.22, 'emp_concrete_dark')                   # capital band
    # haunches under the cantilevered floor slab (sides and back; none on the ladder side)
    for sx in (-1, 1):
        for zc in (-0.9, 0.5):
            hs = 0.78
            pts = [(0, 0), (hs, 0), (0, 0.52)]
            slab(B, pts, (sx * 1.22, 5.88, zc), (sx, 0, 0), (0, 1, 0), 0.20, 'emp_concrete')
    for xc in (-0.8, 0.8):
        slab(B, [(0, 0), (0.78, 0), (0, 0.52)], (xc, 5.88, -1.22), (0, 0, -1), (0, 1, 0), 0.20, 'emp_concrete')
    # base door on +X, with canopy and step
    bx(B, SH, SH + 0.14, 0.30, 0.42, -0.62, 0.38, 'emp_concrete_dark')                 # step
    wall(B, 'x', SH + 0.01, -0.50, 0.30, 0.42, 2.45, 0.04, [(-0.45, 0.25, 0.42, 2.20, 'door')], 'emp_concrete_dark')
    bx(B, SH, SH + 0.45, 2.50, 2.62, -0.65, 0.45, 'emp_concrete')                      # canopy
    # ladder on +Z with safety hoops (cage), standoff brackets to the shaft wall
    ladder(B, 0.0, ZR, 0.0, DY, width=0.46, rung=0.30, rail_w=0.06, rail_d=0.08, rung_r=0.0165, top_ext=1.0, z_wall=WALL_Z, bracket_ys=(0.5, 1.7, 2.9, 4.1, 5.3))
    cage_hoops(B, 0.0, ZR, [2.4 + 0.9 * k for k in range(5)], r=0.42, z_wall=WALL_Z)
    # floor slab with a notch at the ladder (hatch zone), cabin walls with windows, roof
    bx(B, -2.0, 2.0, 6.40, DY, -2.0, 1.2, 'emp_concrete')
    bx(B, -2.0, -0.46, 6.40, DY, 1.2, 2.0, 'emp_concrete'); bx(B, 0.46, 2.0, 6.40, DY, 1.2, 2.0, 'emp_concrete')
    for sx in (-1, 1): bx(B, sx * 0.46, sx * 0.52, 6.40, DY + 0.06, 1.2, 2.0, 'emp_yellow')   # painted notch edges
    CW = 1.85; CF = 0.40; CT = 8.90
    wall(B, 'z', CF, -CW, CW, DY, CT, 0.16, [(-0.45, 0.45, DY, DY + 2.05, 'door'), (0.75, 1.65, 7.45, 8.45), (-1.65, -0.75, 7.45, 8.45)], 'emp_concrete', 'emp_glass')
    wall(B, 'z', -CW, -CW, CW, DY, CT, 0.16, [(-1.3, -0.15, 7.45, 8.45), (0.15, 1.3, 7.45, 8.45)], 'emp_concrete', 'emp_glass')
    for sx in (-1, 1):
        wall(B, 'x', sx * CW, -CW, CF, DY, CT, 0.16, [(-1.5, -0.15, 7.45, 8.45)], 'emp_concrete', 'emp_glass')
    bx(B, -CW, CW, DY, DY + 0.01, -CW, CF, 'emp_wood_dark')                              # cabin floor boards
    bx(B, -2.10, 2.10, CT, CT + 0.25, -2.10, 0.62, 'emp_concrete')                         # roof slab
    bx(B, -2.14, 2.14, CT + 0.25, CT + 0.29, -2.14, 0.66, 'emp_concrete_dark')
    # interior fittings: counter below the front windows, a locker
    bx(B, 0.5, 1.8, DY, DY + 0.8, 0.14, 0.34, 'emp_wood'); bx(B, 0.5, 1.8, DY + 0.8, DY + 0.84, 0.12, 0.36, 'emp_wood_light')
    bx(B, -1.8, -1.3, DY, DY + 1.6, -1.8, -1.3, 'emp_steel_dark')
    # balcony railing (front and sides) and the roof railing with a radio mast stub
    top = 1.05
    rail_run(B, (-1.95, 1.95), (-0.52, 1.95), DY, top, 'emp_galv', True, 0.9); rail_run(B, (0.52, 1.95), (1.95, 1.95), DY, top, 'emp_galv', True, 0.9)
    rail_run(B, (-1.95, 1.95), (-1.95, 0.55), DY, top, 'emp_galv', True, 0.9); rail_run(B, (1.95, 1.95), (1.95, 0.55), DY, top, 'emp_galv', True, 0.9)
    RY = CT + 0.29
    rail_run(B, (-2.05, -2.05), (2.05, -2.05), RY, top, 'emp_galv', True, 1.0)
    rail_run(B, (-2.05, 0.55), (2.05, 0.55), RY, top, 'emp_galv', True, 1.0)
    rail_run(B, (-2.05, -2.05), (-2.05, 0.55), RY, top, 'emp_galv', True, 1.0); rail_run(B, (2.05, -2.05), (2.05, 0.55), RY, top, 'emp_galv', True, 1.0)
    B.box((1.5, RY + 0.06, -1.5), (0.4, 0.12, 0.4), 'emp_steel_dark')
    B.cyl((1.5, RY + 0.12, -1.5), (1.5, RY + 1.55, -1.5), 0.045, 0.035, 8, 'emp_galv', False)
    B.cyl((1.5, RY + 1.55, -1.5), (1.5, RY + 2.05, -1.5), 0.012, 0.008, 5, 'emp_black', False)
    bar(B, (1.2, RY + 1.35, -1.5), (1.8, RY + 1.35, -1.5), 0.03, 'emp_galv'); bar(B, (1.5, RY + 1.15, -1.8), (1.5, RY + 1.15, -1.2), 0.03, 'emp_galv')
    for sx in (-1, 1): bar(B, (1.5, RY + 1.3, -1.5), (1.5 + sx * 0.45, RY + 0.12, -1.5 + sx * 0.45), 0.012, 'emp_black')
    B.box((-1.2, RY + 0.2, -1.6), (0.7, 0.4, 0.5), 'emp_concrete_dark')                    # roof hatch housing
    # markers
    M.empty('tower_guard_concrete_ladder_bottom', (0.0, 0.0, ZR + CLIMB), None, 'ARROWS')
    M.empty('tower_guard_concrete_ladder_top', (0.0, DY, 0.85), None, 'ARROWS')
    M.empty('tower_guard_concrete_deck', (0.0, DY, -0.72), None, 'CUBE', scale=(1.70, 1.0, 1.10))
    M.empty('tower_guard_concrete_seat', (1.20, DY, -0.15), None, 'ARROWS')
    M.empty('tower_guard_concrete_roof', (0.0, RY, -0.72), None, 'CUBE', scale=(1.85, 1.0, 1.12))
    return M


# ================================================================== steel lattice guard tower (12 m)
def tower_guard_steel():
    M = EM('tower_guard_steel'); rng = random.Random(71)
    DY = 9.6; H0 = 1.9; H1 = 1.2; ZR = 2.05
    def h(y): return H0 + (H1 - H0) * y / DY
    B = M.node('_body', None, (0, 0, 0))
    for sx in (-1, 1):
        for sz in (-1, 1):
            B.box((sx * H0, 0.15, sz * H0), (0.55, 0.30, 0.55), 'emp_concrete')
            bar(B, (sx * H0, 0.3, sz * H0), (sx * H1, DY - 0.05, sz * H1), 0.17, 'emp_galv')
            B.box((sx * H0, 0.34, sz * H0), (0.34, 0.05, 0.34), 'emp_steel_dark')
    ys = [0.5, 2.5, 4.4, 6.2, 7.9, 9.3]
    def pt(face, u, y, o=0.0):
        return {'+z': (u, y, h(y) + o), '-z': (u, y, -h(y) - o), '+x': (h(y) + o, y, u), '-x': (-h(y) - o, y, u)}[face]
    for face in ('+z', '-z', '+x', '-x'):
        for y in ys: bar(B, pt(face, -h(y), y), pt(face, h(y), y), 0.09, 'emp_steel')
        for ya, yb in zip(ys, ys[1:]):
            bar(B, pt(face, -h(ya), ya), pt(face, h(yb), yb), 0.07, 'emp_steel_dark')
            bar(B, pt(face, h(ya), ya, 0.04), pt(face, -h(yb), yb, 0.04), 0.07, 'emp_steel_dark')
    # deck: under-frame, grating, landing with a notch around the ladder
    for sx in (-1, 1): bar(B, (sx * 1.35, DY - 0.18, -1.5), (sx * 1.35, DY - 0.18, 2.5), 0.16, 'emp_steel')
    for z in (-1.4, -0.4, 0.6, 1.5): bar(B, (-1.5, DY - 0.18, z), (1.5, DY - 0.18, z), 0.12, 'emp_steel')
    bar(B, (-1.5, DY - 0.18, 2.5), (-0.46, DY - 0.18, 2.5), 0.12, 'emp_steel'); bar(B, (0.46, DY - 0.18, 2.5), (1.5, DY - 0.18, 2.5), 0.12, 'emp_steel')
    bx(B, -1.5, 1.5, DY - 0.06, DY, -1.5, 1.7, 'emp_steel_dark')
    bx(B, -1.5, -0.46, DY - 0.06, DY, 1.7, 2.5, 'emp_steel_dark'); bx(B, 0.46, 1.5, DY - 0.06, DY, 1.7, 2.5, 'emp_steel_dark')
    for k in range(12): bx(B, -1.5, 1.5, DY, DY + 0.012, -1.4 + k * 0.26, -1.4 + k * 0.26 + 0.05, 'emp_black')
    # ladder with hoops, brackets from the lattice face
    ladder(B, 0.0, ZR, 0.0, DY, width=0.46, rung=0.30, rail_w=0.06, rail_d=0.08, rung_r=0.0165, top_ext=1.1)
    for by in ys[1:-1]:
        for sx in (-1, 1):
            bar(B, (sx * 0.23, by, ZR), (sx * 0.23, by, h(by)), 0.05, 'emp_steel_dark')
    cage_hoops(B, 0.0, ZR, [2.5 + 0.9 * k for k in range(7)], r=0.42, z_wall=ZR)
    # railings around deck + landing (front opening for the ladder)
    top = 1.05
    rail_run(B, (-1.5, -1.5), (1.5, -1.5), DY, top, 'emp_galv', True, 1.0)
    rail_run(B, (-1.5, -1.5), (-1.5, 2.5), DY, top, 'emp_galv', True, 1.0); rail_run(B, (1.5, -1.5), (1.5, 2.5), DY, top, 'emp_galv', True, 1.0)
    rail_run(B, (-1.5, 2.5), (-0.52, 2.5), DY, top, 'emp_galv', True, 1.0); rail_run(B, (0.52, 2.5), (1.5, 2.5), DY, top, 'emp_galv', True, 1.0)
    # small roofed cabin on the back half
    CT = DY + 1.95
    wall(B, 'z', -0.10, -1.2, 1.2, DY, CT, 0.10, [(-0.40, 0.40, DY, DY + 1.85, 'door'), (0.65, 1.1, DY + 0.95, DY + 1.65), (-1.1, -0.65, DY + 0.95, DY + 1.65)], 'emp_olive', 'emp_glass')
    wall(B, 'z', -1.40, -1.2, 1.2, DY, CT, 0.10, [(-0.5, 0.5, DY + 0.95, DY + 1.65)], 'emp_olive', 'emp_glass')
    for sx in (-1, 1): wall(B, 'x', sx * 1.2, -1.4, -0.10, DY, CT, 0.10, [(-1.0, -0.5, DY + 0.95, DY + 1.65)], 'emp_olive', 'emp_glass')
    rise = 0.55; eave = CT
    for sgn in (1, -1):
        L = math.hypot(0.85, rise)
        slab(B, [(-1.4, 0), (1.4, 0), (1.4, L), (-1.4, L)], (0, eave, -0.75 + sgn * 0.85), (1, 0, 0), (0, rise / L, -sgn * 0.85 / L), 0.06, 'emp_roof')
    for sx in (-1, 1): slab(B, [(-0.80, 0), (0.80, 0), (0.0, rise)], (sx * 1.21, eave, -0.75), (0, 0, 1), (0, 1, 0), 0.06, 'emp_olive')
    bar(B, (-1.45, eave + rise, -0.75), (1.45, eave + rise, -0.75), 0.12, 'emp_steel_dark')
    # floodlight on a bracket at the cabin front corner (child node)
    FP = (0.95, CT - 0.35, 0.26)
    bar(B, (0.95, CT - 0.60, -0.10), (0.95, CT - 0.45, 0.18), 0.06, 'emp_steel_dark')
    B.box((0.95, CT - 0.50, 0.04), (0.12, 0.10, 0.20), 'emp_steel_dark')
    Fm = M.node('_lamp', None, FP)
    Fm.box((0.95, CT - 0.35, 0.28), (0.46, 0.34, 0.30), 'emp_steel_dark', bevel=0.02)
    Fm.box((0.95, CT - 0.35, 0.445), (0.40, 0.28, 0.03), 'emp_lens')
    Fm.box((0.95, CT - 0.15, 0.38), (0.50, 0.03, 0.30), 'emp_steel')
    for sx in (-1, 1): Fm.box((0.95 + sx * 0.26, CT - 0.35, 0.26), (0.03, 0.10, 0.12), 'emp_steel')
    M.empty('tower_guard_steel_ladder_bottom', (0.0, 0.0, ZR + CLIMB), None, 'ARROWS')
    M.empty('tower_guard_steel_ladder_top', (0.0, DY, 1.35), None, 'ARROWS')
    M.empty('tower_guard_steel_deck', (0.0, DY, 1.2), None, 'CUBE', scale=(1.40, 1.0, 1.20))
    M.empty('tower_guard_steel_seat', (-0.90, DY, 1.15), None, 'ARROWS')
    return M


# ================================================================== freestanding ladders
def _free_ladder(name, L, hoops=False, tall_brackets=None):
    M = EM(name); B = M.node('_body', None, (0, 0, 0)); ZW = -0.25
    ext = 0.9
    brk = tall_brackets or [0.4 + k * 1.8 for k in range(int(L / 1.8) + 1) if 0.4 + k * 1.8 < L - 0.2]
    brk = sorted(set(brk + [L - 0.3]))
    ladder(B, 0.0, 0.0, 0.0, L, width=0.46, rung=0.30, rail_w=0.06, rail_d=0.09, rung_r=0.0165, top_ext=ext, z_wall=ZW, bracket_ys=brk)
    for sx in (-1, 1): B.box((sx * 0.23, 0.02, 0.0), (0.12, 0.04, 0.12), 'emp_steel_dark')
    if hoops:
        n = int((L - 2.3) / 0.9) + 1
        cage_hoops(B, 0.0, 0.0, [2.3 + 0.9 * k for k in range(n)], r=0.42, z_wall=ZW)
    M.empty(name + '_ladder_bottom', (0.0, 0.0, CLIMB), None, 'ARROWS')
    M.empty(name + '_ladder_top', (0.0, L, ZW - 0.30), None, 'ARROWS')
    return M


def ladder_4m(): return _free_ladder('ladder_4m', 4.0)
def ladder_8m(): return _free_ladder('ladder_8m', 8.0)
def ladder_hoops_6m(): return _free_ladder('ladder_hoops_6m', 6.0, hoops=True)
