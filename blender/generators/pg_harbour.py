"""Harbour class: pier modules, lighthouses, IALA buoys, mooring bollards, channel-marker piles."""
import math, random
from mathutils import Vector
from pg_core import *

def pier(seed=0, name='pier', length=None):
    """Tileable pier bay: decking across 2.4 m, three stringers, pile bents at 3 m with cross bracing, rails and fittings."""
    r = rng(seed)
    L = length or r.choice([6.0, 9.0])
    Wd, deck_z, bed_z = 2.4, 1.4, -2.5
    tones = ['#9a7650', '#8c6a46', '#a57f57', '#7f6143']
    woods = [mat('deck%d' % i, c, 0.9) for i, c in enumerate(tones)]
    pile = mat('pile', '#4a3a2c', 1.0)
    parts = []
    pw, gap = 0.15, 0.012
    n = int(L / (pw + gap))
    for i in range(n):
        x = -L / 2 + (pw + gap) * (i + 0.5)
        ww = Wd + r.uniform(-0.04, 0.04)
        parts.append(box((pw, ww, 0.05), (x, r.uniform(-0.02, 0.02), deck_z - 0.025), (0, 0, r.uniform(-0.01, 0.01)), material=r.choice(woods), bevel=0.006))
    for y in (-Wd / 2 + 0.2, 0, Wd / 2 - 0.2):
        parts.append(box((L, 0.1, 0.25), (0, y, deck_z - 0.175), material=pile))
    bents = int(L / 3)
    for b in range(bents + 1):
        x = -L / 2 + b * L / bents
        tops = []
        for y in (-Wd / 2 + 0.1, Wd / 2 - 0.1):
            tilt = r.uniform(-0.03, 0.03)
            parts.append(cyl(0.15, 0.14, deck_z + 0.35 - bed_z, 8, loc=(x, y, bed_z), rot=(tilt, 0, 0), material=pile))
            parts.append(cyl(0.16, 0.0, 0.08, 8, loc=(x, y + tilt * (deck_z - bed_z), deck_z + 0.35), material=pile))
            tops.append((x, y))
        parts.append(box((0.15, Wd + 0.2, 0.22), (x, 0, deck_z - 0.38), material=pile))
        brace = mat('brace', '#5a4634', 0.95)
        parts.append(rod((x, -Wd / 2 + 0.1, deck_z - 0.5), (x, Wd / 2 - 0.1, -0.6), 0.05, 6, brace))
        parts.append(rod((x, Wd / 2 - 0.1, deck_z - 0.5), (x, -Wd / 2 + 0.1, -0.6), 0.05, 6, brace))
    # fittings: bollards on one edge, cleats on the other, optional ladder
    iron = mat('iron', '#2c2f33', 0.5, 0.6)
    for b in range(bents):
        x = -L / 2 + (b + 0.5) * L / bents
        parts.append(lathe([(0.0, deck_z), (0.13, deck_z), (0.11, deck_z + 0.05), (0.09, deck_z + 0.28), (0.14, deck_z + 0.34), (0.14, deck_z + 0.38), (0, deck_z + 0.38)], 12, iron))
        parts[-1].data.transform(Matrix.Translation((x, Wd / 2 - 0.25, 0)))
        parts.append(box((0.32, 0.06, 0.04), (x, -Wd / 2 + 0.2, deck_z + 0.09), material=iron))
        parts.append(box((0.08, 0.05, 0.08), (x, -Wd / 2 + 0.2, deck_z + 0.04), material=iron))
    if r.random() < 0.6:
        lx = r.uniform(-L / 4, L / 4)
        for dx in (-0.22, 0.22):
            parts.append(rod((lx + dx, -Wd / 2 - 0.06, -0.8), (lx + dx, -Wd / 2 - 0.06, deck_z + 0.6), 0.025, 6, iron))
        for k in range(7):
            z = -0.6 + k * 0.3
            parts.append(rod((lx - 0.22, -Wd / 2 - 0.06, z), (lx + 0.22, -Wd / 2 - 0.06, z), 0.016, 5, iron))
    if r.random() < 0.5:  # hand rail on one side
        rail = mat('rail_white', '#e9e3d6', 0.6)
        for k in range(int(L / 1.5) + 1):
            x = -L / 2 + k * 1.5
            parts.append(box((0.08, 0.08, 1.0), (x, Wd / 2 - 0.05, deck_z + 0.5), material=rail))
        parts.append(box((L, 0.08, 0.06), (0, Wd / 2 - 0.05, deck_z + 1.0), material=rail))
        parts.append(box((L, 0.05, 0.05), (0, Wd / 2 - 0.05, deck_z + 0.55), material=rail))
    return join(parts, name)

def lighthouse(seed=0, name='lighthouse'):
    r = rng(seed)
    H = r.uniform(10, 16); rb = r.uniform(1.7, 2.3); rt = rb * r.uniform(0.58, 0.72)
    scheme = r.choice([('#f1ece2', '#d64b2c', 'bands'), ('#f1ece2', '#2c2f33', 'bands'), ('#f1ece2', '#d64b2c', 'spiral'),
                       ('#f1ece2', '#f1ece2', 'plain'), ('#e3c14a', '#2c2f33', 'bands')])
    c1, c2, style = scheme
    m1, m2 = mat('lh_' + c1, c1, 0.7), mat('lh_' + c2, c2, 0.7)
    zb = 1.0  # plinth height
    prof = [(rb - (rb - rt) * (k / 24) ** 0.85, zb + H * k / 24) for k in range(25)]
    tower = lathe(prof, 20, m1, cap_bottom=False)
    tower.data.materials.append(m2)
    nb = r.choice([3, 4, 5])
    for p in tower.data.polygons:
        z = (p.center.z - zb) / H
        a = math.atan2(p.center.y, p.center.x)
        if style == 'bands': p.material_index = int(z * nb * 2) % 2
        elif style == 'spiral': p.material_index = int((z * nb * 2 + a / math.pi) % 2)
    parts = [tower]
    stone = mat('plinth', '#8b857a', 0.9)
    parts.append(lathe([(rb + 0.6, 0), (rb + 0.6, zb * 0.8), (rb + 0.3, zb), (0, zb)], 8, stone))
    top = zb + H
    dark = mat('lh_iron', '#2c2f33', 0.5, 0.5)
    parts.append(cyl(rt + 0.7, rt + 0.7, 0.18, 20, loc=(0, 0, top), material=dark))
    posts = 16
    for k in range(posts):
        a = 2 * math.pi * k / posts
        parts.append(rod(((rt + 0.62) * math.cos(a), (rt + 0.62) * math.sin(a), top + 0.18), ((rt + 0.62) * math.cos(a), (rt + 0.62) * math.sin(a), top + 1.05), 0.025, 4, dark))
    parts.append(torus(rt + 0.62, 0.03, 32, 5, loc=(0, 0, top + 1.05), material=dark))
    parts.append(torus(rt + 0.62, 0.02, 32, 5, loc=(0, 0, top + 0.6), material=dark))
    lr = rt * 0.62
    parts.append(cyl(lr + 0.05, lr + 0.05, 0.6, 12, loc=(0, 0, top + 0.18), material=m2 if style != 'plain' else dark))
    lamp = mat('lantern', '#ffe2a0', 0.1, emit='#ffc860', emit_str=4.0)
    parts.append(cyl(lr, lr, 1.5, 12, loc=(0, 0, top + 0.78), material=lamp))
    for k in range(12):
        a = 2 * math.pi * k / 12
        parts.append(rod((lr * 1.01 * math.cos(a), lr * 1.01 * math.sin(a), top + 0.78), (lr * 1.01 * math.cos(a), lr * 1.01 * math.sin(a), top + 2.28), 0.02, 4, dark))
    dome = [(lr + 0.18, top + 2.28)] + [((lr + 0.18) * math.cos(t * math.pi / 2), top + 2.28 + lr * 0.9 * math.sin(t * math.pi / 2)) for t in [k / 6 for k in range(1, 7)]]
    parts.append(lathe(dome, 16, dark, cap_bottom=True, cap_top=False))
    parts.append(ico(0.16, 1, (0, 0, top + 2.28 + lr * 0.9 + 0.12), dark))
    parts.append(rod((0, 0, top + 2.28 + lr * 0.9), (0, 0, top + 2.28 + lr * 0.9 + 0.9), 0.015, 4, dark))
    # door and windows following the taper
    door = mat('lh_door', '#3b4a3a', 0.6)
    parts.append(box((0.2, 0.9, 1.9), (rb - 0.02, 0, zb + 0.95), material=door))
    for k, z in enumerate([0.3, 0.55, 0.8]):
        zz = zb + H * z; rr = rb - (rb - rt) * z ** 0.85
        a = (k * 2.1 + 0.6)
        o = box((0.12, 0.45, 0.65), (rr - 0.02, 0, zz), material=mat('glass', '#1d2b33', 0.1, 0.2))
        o.data.transform(Matrix.Rotation(a, 4, 'Z')); parts.append(o)
    return join(parts, name)

def buoy(seed=0, name='buoy'):
    """IALA buoys: port can, starboard cone, cardinal pillar with topmarks, spar, mooring ball."""
    r = rng(seed)
    kind = ['can', 'cone', 'cardinal', 'spar', 'mooring', 'safe'][seed % 6]
    red, green, yel, blk, wht = (mat('b_' + c, c, 0.5) for c in ('#c8372b', '#2f8a5a', '#e3c14a', '#232628', '#f1ece2'))
    steel = mat('b_steel', '#5d6266', 0.5, 0.6)
    parts = []
    if kind in ('can', 'cone', 'safe', 'cardinal'):
        # float body
        parts.append(lathe([(0, 0), (0.9, 0.0), (1.0, 0.25), (1.0, 0.6), (0.9, 0.7), (0, 0.7)], 16, wht if kind == 'safe' else (red if kind == 'can' else green if kind == 'cone' else blk)))
        parts.append(torus(1.0, 0.07, 20, 5, loc=(0, 0, 0.45), material=mat('fender', '#151515', 0.95)))
        if kind == 'can':
            parts.append(cyl(0.45, 0.45, 1.6, 12, loc=(0, 0, 0.7), material=red))
        elif kind == 'cone':
            parts.append(cyl(0.6, 0.05, 1.8, 12, loc=(0, 0, 0.7), material=green))
        else:
            # lattice pillar
            col_a = red if kind == 'safe' else yel
            for k in range(4):
                a = math.pi / 4 + k * math.pi / 2
                parts.append(rod((0.55 * math.cos(a), 0.55 * math.sin(a), 0.7), (0.22 * math.cos(a), 0.22 * math.sin(a), 2.8), 0.04, 5, col_a if kind == 'cardinal' else red))
            for z, rr in ((1.3, 0.42), (2.0, 0.32)):
                parts.append(torus(rr, 0.03, 16, 4, loc=(0, 0, z), material=col_a if kind == 'cardinal' else wht))
            parts.append(cyl(0.3, 0.3, 0.12, 10, loc=(0, 0, 2.8), material=steel))
            parts.append(cyl(0.06, 0.06, 0.8, 6, loc=(0, 0, 2.9), material=steel))
            if kind == 'cardinal':
                q = r.choice(['N', 'S', 'E', 'W'])
                ups = {'N': (1, 1), 'S': (-1, -1), 'E': (1, -1), 'W': (-1, 1)}[q]
                for i, u in enumerate(ups):
                    z0 = 3.25 + i * 0.5
                    if u > 0: parts.append(cyl(0.22, 0.0, 0.36, 10, loc=(0, 0, z0), material=blk))
                    else: parts.append(cyl(0.0, 0.22, 0.36, 10, loc=(0, 0, z0), material=blk))
            else:
                parts.append(ico(0.2, 1, (0, 0, 3.45), red))
            parts.append(cyl(0.1, 0.1, 0.2, 8, loc=(0, 0, 2.92), material=mat('b_light', '#fff3c4', 0.2, emit='#ffd27a', emit_str=3)))
    elif kind == 'spar':
        c = r.choice([red, green, yel])
        parts.append(cyl(0.18, 0.15, 4.0, 10, loc=(0, 0, 0), material=c))
        parts.append(cyl(0.2, 0.2, 0.2, 10, loc=(0, 0, 0.8), material=wht))
    else:
        parts.append(ico(0.55, 2, (0, 0, 0.55), wht))
        parts.append(torus(0.16, 0.035, 12, 5, loc=(0, 0, 1.15), rot=(math.pi / 2, 0, 0), material=steel))
        parts.append(cyl(0.05, 0.05, 0.12, 6, loc=(0, 0, 1.0), material=steel))
        parts.append(box((0.002, 0.3, 0.12), (0, -0.56, 0.62), material=mat('b_num', '#2f6f8f', 0.6)))
    o = join(parts, name)
    for p in o.data.polygons: p.use_smooth = kind == 'mooring'
    return o

def bollard(seed=0, name='bollard'):
    r = rng(seed)
    kind = ['post', 'double', 'cleat'][seed % 3]
    iron = mat('iron_' + str(seed % 2), r.choice(['#2c2f33', '#3a4a5a', '#5a3a2c']), 0.5, 0.6)
    if kind == 'post':
        o = lathe([(0, 0), (0.32, 0), (0.3, 0.06), (0.22, 0.12), (0.19, 0.55), (0.24, 0.62), (0.32, 0.7), (0.32, 0.78), (0.28, 0.82), (0, 0.84)], 20, iron, smooth=True)
        return o
    if kind == 'double':
        parts = [box((1.1, 0.5, 0.08), (0, 0, 0.04), material=iron, bevel=0.02)]
        for x in (-0.32, 0.32):
            p = lathe([(0, 0.08), (0.17, 0.08), (0.15, 0.45), (0.21, 0.52), (0.21, 0.58), (0, 0.6)], 16, iron, smooth=True)
            p.data.transform(Matrix.Translation((x, 0, 0))); parts.append(p)
        return join(parts, name)
    parts = [box((0.7, 0.22, 0.06), (0, 0, 0.03), material=iron, bevel=0.02)]
    for x in (-0.14, 0.14):
        parts.append(box((0.1, 0.14, 0.18), (x, 0, 0.15), material=iron, bevel=0.02))
    horn = box((0.95, 0.12, 0.09), (0, 0, 0.27), material=iron, bevel=0.03)
    parts.append(horn)
    return join(parts, name)

def channel_marker(seed=0, name='channel_marker'):
    r = rng(seed)
    pile = mat('pile', '#4a3a2c', 1.0)
    port = seed % 2 == 0
    c = mat('dm_' + ('red' if port else 'green'), '#c8372b' if port else '#2f8a5a', 0.6)
    parts = [cyl(0.2, 0.18, 6.0, 8, loc=(0, 0, 0), material=pile)]
    if port:
        parts.append(box((0.9, 0.04, 0.9), (0, -0.22, 5.2), material=c))
    else:
        parts.append(mesh('tri', [(-0.55, -0.22, 4.7), (0.55, -0.22, 4.7), (0, -0.22, 5.7)], [(0, 1, 2)], c))
        parts[-1] = solidify(parts[-1], 0.04)
    parts.append(box((0.3, 0.005, 0.3), (0, -0.25, 5.2 if port else 4.95), material=mat('dm_num', '#f1ece2', 0.6)))
    parts.append(cyl(0.12, 0.12, 0.25, 8, loc=(0, 0, 6.0), material=mat('b_light', '#fff3c4', 0.2, emit='#ffd27a', emit_str=3)))
    return join(parts, name)

TYPES = [('Pier bay', pier), ('Lighthouse', lighthouse), ('Buoy', buoy), ('Bollard / cleat', bollard), ('Channel marker', channel_marker)]
