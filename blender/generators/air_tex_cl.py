"""Livery painter for the Canadair CL-415 (see air_tex.py for the shared Atlas class)."""
import os, math
import numpy as np
from air_tex import *
import air_layout as LY

def lin(pts, x):
    if x <= pts[0][0]: return pts[0][1]
    for (a, b) in zip(pts, pts[1:]):
        if x <= b[0]: return a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])
    return pts[-1][1]

ORG = '#e2571a'; GRN = '#1f6b49'; GRY = '#8d949b'

def paint(out):
    R = LY.CL; A = Atlas(ORG)
    SB, PT, TOP, BOT = R['sb'], R['pt'], R['top'], R['bot']
    org, grn, gry, wht, blk = hexc(ORG), hexc(GRN), hexc(GRY), hexc('#f1efe6'), hexc('#16181a')
    keel = [(-9.9, 1.7), (-8, 1.32), (-5, 0.8), (-2.5, 0.36), (-1.45, 0.24), (-1.3, 0.05), (-1.0, 0.0), (7.2, 0.0), (8.4, 0.08), (9.0, 0.3), (9.4, 0.62), (9.62, 0.95)]
    xs_ = [x / 4.0 for x in range(-39, 39)] + [9.6]
    lower = [(x, lin(keel, x) + 0.36) for x in xs_]
    upper = [(x, lin([(-9.9, 3.0), (-6, 2.2), (-2.5, 1.55), (0, 1.4), (6, 1.4), (8.6, 1.46), (9.6, 1.5)], x)) for x in xs_]
    for reg, sd in ((SB, -1), (PT, 1)):
        A.poly(reg, [(lower[0][0], 0.0)] + lower + [(lower[-1][0], 0.0)], gry)                     # grey planing bottom
        A.poly(reg, lower + upper[::-1], grn)                                                       # green band
        A.thick_poly(reg, [(x, z + 0.06) for (x, z) in upper], 0.035, wht)                          # white pinstripe
        A.thick_poly(reg, [(x, z - 0.03) for (x, z) in lower], 0.02, hexc('#d8dadc'))
        A.poly(reg, [(6.3, 2.12), (8.0, 1.98), (9.55, 1.62), (9.55, 1.5), (8.0, 1.75), (6.3, 1.9)], blk)   # glare shield under the cockpit windows
        for xs in (-9.0, -7.5, -6.0, -4.5, -3.0, -0.2, 1.4, 3.0, 4.4, 7.0): A.seam(reg, [(xs, lin(keel, xs) + 0.4), (xs, 3.2)], 0.010)
        for zs in (2.15, 2.6): A.seam(reg, [(-9.0, zs), (6.5, zs)], 0.007)
        A.seam(reg, [(-9.4, 3.18), (6.4, 3.18)], 0.009)
        fd = [(5.2, 2.35), (6.5, 2.35), (6.5, 0.7), (5.2, 0.7)]
        A.seam(reg, fd, 0.016, closed=True, dark=(20, 20, 20, 190))
        A.seam(reg, [(5.3, 2.25), (6.4, 2.25), (6.4, 0.8), (5.3, 0.8)], 0.008, closed=True)
        A.thick_poly(reg, [(5.35, 1.55), (5.35, 1.8)], 0.04, hexc('#2a2a2a'))
        rd = [(-2.9, 2.5), (-1.7, 2.5), (-1.7, 1.1), (-2.9, 1.1)]
        A.seam(reg, rd, 0.016, closed=True, dark=(20, 20, 20, 190)); A.thick_poly(reg, [(-1.85, 1.6), (-1.85, 1.85)], 0.04, hexc('#2a2a2a'))
        A.seam(reg, [(3.6, 2.7), (4.1, 2.7), (4.1, 2.3), (3.6, 2.3)], 0.008, closed=True)
        A.seam(reg, [(-5.6, 2.2), (-4.7, 2.2), (-4.7, 1.8), (-5.6, 1.8)], 0.008, closed=True)
        A.text(reg, (7.5, 0.95), '284', 0.42, wht, 'arialbd.ttf')
        A.text(reg, (3.0, 1.1), 'Newfoundland', 0.16, wht, 'arialbd.ttf'); A.text(reg, (3.0, 0.82), 'Labrador', 0.16, wht, 'arialbd.ttf')
        A.circle(reg, (1.35, 0.97), 0.19, wht); A.circle(reg, (1.35, 0.97), 0.13, grn)
        for zs in (1.95, 2.75):
            for k in range(0, 150):
                xx = -9.0 + k * 0.1
                if xx > 6.4: break
                p = np.array(A.P(reg, xx, zs)); A.d.ellipse((*(p - 0.9), *(p + 0.9)), fill=(80, 36, 6, 120))
        A.weather(reg, 0.14, 71 + sd)
    # ---- top view
    A.fill(TOP, org)
    A.poly(TOP, [(8.7, 1.9), (9.9, 1.9), (9.9, -1.9), (8.7, -1.9)], blk)
    for xs in (-9.0, -7.0, -5.0, -3.0, -1.0, 0.8, 2.6, 4.4, 6.0): A.seam(TOP, [(xs, -1.4), (xs, 1.4)], 0.010)
    A.seam(TOP, [(-9.5, 0.0), (6.5, 0.0)], 0.008)
    A.weather(TOP, 0.16, 81)
    # ---- belly: grey hull bottom, tank doors, scoop doors, step
    A.fill(BOT, gry)
    for (x0, x1) in ((6.2, 3.7), (3.55, 1.6), (-0.9, -3.2), (-3.4, -5.6)): A.seam(BOT, [(x0, -0.55), (x1, -0.55), (x1, 0.55), (x0, 0.55)], 0.013, closed=True, dark=(40, 42, 46, 170))
    A.seam(BOT, [(1.4, -0.82), (0.0, -0.82), (0.0, -0.4), (1.4, -0.4)], 0.013, closed=True, dark=(30, 32, 36, 190)); A.seam(BOT, [(1.4, 0.82), (0.0, 0.82), (0.0, 0.4), (1.4, 0.4)], 0.013, closed=True, dark=(30, 32, 36, 190))
    A.seam(BOT, [(-9.5, 0.0), (9.0, 0.0)], 0.01, dark=(40, 42, 46, 150)); A.seam(BOT, [(-1.3, -1.4), (-1.3, 1.4)], 0.02, dark=(30, 32, 36, 200))
    for xs in (-8.0, -6.5, -4.5, 7.0, 8.0): A.seam(BOT, [(xs, -1.4), (xs, 1.4)], 0.01, dark=(40, 42, 46, 150))
    A.weather(BOT, 0.30, 91)
    # ---- fin sides: orange with white bands, registration letters
    for reg, sd in ((R['fin'], -1), (R['fin2'], 1)):
        A.fill(reg, org)
        for (z0, z1) in ((2.9, 3.6), (4.2, 4.8), (5.4, 6.0), (6.6, 7.2), (7.8, 8.4)):
            A.poly(reg, [(-10.2, z0), (-4.5, z0), (-4.5, z1), (-10.2, z1)], wht)
        A.text(reg, (-9.05, 6.9), 'C-FYWK', 0.25, blk, 'arialbd.ttf')
        for xs in (-9.0, -8.0): A.seam(reg, [(xs, 3.0), (xs, 8.3)], 0.01)
        A.seam(reg, [(-9.6, 3.0), (-9.6, 8.3)], 0.012)
        A.weather(reg, 0.12, 101 + sd)
    # ---- tailplane: orange, white tips
    A.fill(R['tail'], org); A.fill(R['tail'], wht, (-4.9, -3.9)); A.fill(R['tail'], wht, (3.9, 4.9))
    for yy in (-3.0, -1.5, 1.5, 3.0): A.seam(R['tail'], [(yy, -6.5), (yy, -9.7)], 0.01)
    A.seam(R['tail'], [(-4.5, -8.4), (4.5, -8.7)], 0.01)
    A.weather(R['tail'], 0.12, 111)
    # ---- nacelles: orange with a green lower stripe and cowl seams
    for reg in (R['nac_sb'], R['nac_pt']):
        A.fill(reg, org); A.fill(reg, grn, None, (3.5, 3.0)); A.fill(reg, wht, None, (3.55, 3.5))
        for xs in (-0.4, 1.4, 3.0, 4.4): A.seam(reg, [(xs, 4.7), (xs, 3.0)], 0.012)
        A.seam(reg, [(-1.5, 4.0), (5.5, 4.0)], 0.008)
        A.weather(reg, 0.12, 121)
    # ---- wing top and bottom (a = y, b = x)
    for reg, top in ((R['wtop'], True), (R['wbot'], False)):
        A.fill(reg, org); A.fill(reg, wht, (-14.6, -14.05)); A.fill(reg, wht, (14.05, 14.6)); A.fill(reg, hexc('#3b3e42'), None, (4.2, 3.78)) if True else None
        for yy in (-12.9, -8.7, -1.6, 1.6, 8.7, 12.9): A.seam(reg, [(yy, 3.9), (yy, -0.1)], 0.011)
        for sd in (-1, 1):
            A.seam(reg, [(sd * 1.6, 0.9), (sd * 8.6, 1.0), (sd * 8.6, -0.1)], 0.011)
            A.seam(reg, [(sd * 8.7, 0.8), (sd * 12.9, 0.8)], 0.011)
            for k in range(1, 6): A.seam(reg, [(sd * (1.6 + k * 1.4), 3.8), (sd * (1.6 + k * 1.4), 0.9)], 0.007)
        A.seam(reg, [(-14.4, 2.2), (14.4, 2.2)], 0.007); A.seam(reg, [(-14.4, 3.6), (14.4, 3.6)], 0.008)
        if top:
            A.text(reg, (6.5, 2.2), 'NO STEP', 0.14, hexc('#b8420c'), 'arialbd.ttf'); A.text(reg, (-6.5, 2.2), 'NO STEP', 0.14, hexc('#b8420c'), 'arialbd.ttf')
        A.weather(reg, 0.14, 131)
    for nm, col in (('orange', ORG), ('white', '#f1efe6'), ('green', GRN), ('dark', '#26282a'), ('grey', GRY), ('hull', GRY)):
        x, y = LY.CL_SOLID[nm]; A.d.rectangle(((x - 14) * SS, (y - 14) * SS, (x + 14) * SS, (y + 14) * SS), fill=hexc(col))
    A.save(os.path.join(out, 'cl415_livery.jpg'), os.path.join(out, 'cl415_normal.png'))
