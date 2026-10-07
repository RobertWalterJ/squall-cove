"""Builds assets/troops2.glb(.b64.txt): 12 more kinds x 3 variants of low poly characters on the SAME skeleton as troops.glb / facetex_0.
Reuses build_troops.py's skeleton reader, geometry helpers, weights and GLB writer (executed from its source, split at the
'kinds' and 'write the glb' markers), so conventions are identical. Pure python + numpy (no Blender needed).
usage: python build_troops2.py <game dir>"""
import sys, os, json, struct, base64, math, random
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = open(os.path.join(_HERE, '..', 'troops', 'build_troops.py'), encoding='utf-8').read()
_K = '# ------------------------------------------------------------------ kinds'
_W = '# ------------------------------------------------------------------ write the glb'
_HEAD = _SRC[:_SRC.index(_K)]
_TAIL = _SRC[_SRC.index(_W):]
_TAIL = (_TAIL.replace("'troops.glb.b64.txt'", "'troops2.glb.b64.txt'").replace("'troops.glb'", "'troops2.glb'")
         .replace('Squall Cove troops builder (build_troops.py)', 'Squall Cove troops2 builder (build_troops2.py)')
         .replace("C.name.split('_')[1]", "C.name[len('trooper2_'):-2]"))
assert 'troops2.glb' in _TAIL and "len('trooper2_')" in _TAIL
exec(compile(_HEAD, 'build_troops_head', 'exec'), globals())

# ------------------------------------------------------------------ shared kit
SKINS = ['#f1c9a5', '#d9a07a', '#b87a52', '#8d5a3b', '#5f3b27']
HAIRS = ['#1c1714', '#2e2119', '#4a3021', '#8c6a3f', '#b0a89a']
DK = '#0e0f10'


def helmet(C, col, rough=.9, metal=0.0, hc=None, hr=None, skirt=True):
    hc = V(0, 1.522, .010) if hc is None else hc; hr = V(.114, .100, .124) if hr is None else hr
    C.add(col, ell(hc, hr, 12, 6, (0, PI * .46)), ('b', 'head'), rough, metal)
    if skirt:
        C.add(col, ell(hc, hr, 10, 3, (PI * .46, PI * .60), (PI * .55, PI * 1.45), grow=.002), ('b', 'head'), rough, metal)
    return hc, hr


def band(C, col, y0=1.528, y1=1.548, rx=.113, rz=.123, cz=.010, rough=.6):
    C.add(col, loft([ring_y(y0, 0, cz, rx, rz), ring_y(y1, 0, cz, rx - .001, rz - .001)], 12, (False, False), 0), ('b', 'head'), rough)


def chin_strap(C, col):
    for sg in (-1, 1): C.add(col, obox((sg * .1, 1.50, .02), (sg * .05, 1.405, .075), .012, .008), ('b', 'head'), .9)
    C.add(col, box((0, 1.40, .088), (.05, .02, .02)), ('b', 'head'), .9)


def boonie(C, col, strap=None):
    C.add(col, ell(V(0, 1.535, .012), V(.108, .075, .114), 12, 5, (0, PI * .5)), ('b', 'head'), .95)
    C.add(col, loft([ring_y(1.538, 0, .012, .109, .116), ring_y(1.526, 0, .012, .205, .212)], 12, (False, False), 0), ('b', 'head'), .95)
    C.add(strap or '#2a2b22', loft([ring_y(1.538, 0, .012, .110, .117), ring_y(1.555, 0, .012, .109, .116)], 12, (False, False), 0), ('b', 'head'), .8)


def peaked_cap(C, col, visor='#0f0f10', bandc='#0f0f10', plate='#c8a23a'):
    cz = HC[2]
    crown = loft([ring_y(1.523, 0, cz, .100, .111), ring_y(1.57, 0, cz, .103, .114), ring_y(1.604, 0, cz, .118, .126), ring_y(1.622, 0, cz, .114, .121)], 12, (False, True), 0)
    C.add(col, crown, ('b', 'head'), .8)
    C.add(visor, tilted_box((0, 1.545, cz + .165), (.15, .008, .09), -.18), ('b', 'head'), .35, .1)
    C.add(plate, box((0, 1.585, cz + .118), (.034, .04, .008)), ('b', 'head'), .35, .7)
    C.add(bandc, cyl((0, 1.526, cz), (0, 1.552, cz), .105, 12, .116), ('b', 'head'), .5)


def beret(C, col, badge='#9a9a94'):
    C.add(col, ell(V(.012, 1.545, -.002), V(.128, .06, .132), 12, 4, (0, PI * .56)), ('b', 'head'), .95)
    C.add(col, loft([ring_y(1.512, 0, .008, .104, .113), ring_y(1.54, 0, .008, .107, .116)], 12, (False, False), 0), ('b', 'head'), .95)
    C.add(badge, box((-.04, 1.545, .112), (.024, .026, .008)), ('b', 'head'), .4, .6)


def ball_cap(C, col):
    C.add(col, ell(V(0, 1.53, .012), V(.104, .085, .112), 12, 5, (0, PI * .55)), ('b', 'head'), .9)
    C.add(col, tilted_box((0, 1.538, .125), (.12, .008, .085), -.12), ('b', 'head'), .85)


def hard_hat(C, col, brimcol=None):
    C.add(col, ell(V(0, 1.535, .008), V(.112, .088, .122), 12, 5, (0, PI * .5)), ('b', 'head'), .45)
    C.add(brimcol or col, tilted_box((0, 1.538, .125), (.17, .008, .085), -.1), ('b', 'head'), .45)
    C.add(brimcol or col, loft([ring_y(1.532, 0, .008, .113, .123), ring_y(1.526, 0, .008, .125, .135)], 12, (False, False), 0), ('b', 'head'), .45)
    C.add(brimcol or col, box((0, 1.622, .008), (.024, .012, .15)), ('b', 'head'), .45)       # ridge


def goggles_on_eyes(C, strap='#17181a', lens='#2d4254'):
    C.add(strap, loft([ring_y(1.490, 0, HC[2], .093, .105), ring_y(1.518, 0, HC[2], .093, .105)], 12, (False, False), 0), ('b', 'head'), .7)
    for x in (-.038, .038):
        z = hsurf(x, 1.502) + .004
        C.add(strap, cyl((x, 1.502, z), (x, 1.502, z + .024), .033, 8), ('b', 'head'), .6)
        C.add(lens, cyl((x, 1.502, z + .0235), (x, 1.502, z + .028), .026, 8), ('b', 'head'), .15, .2)


def goggles_up(C, strap='#17181a', lens='#2d4254', tube=False, y=1.585):
    C.add(strap, loft([ring_y(y - .022, 0, .008, .117, .127), ring_y(y - .005, 0, .008, .118, .128)], 12, (False, False), 0), ('b', 'head'), .6)
    for x in (-.038, .038):
        C.add(strap, cyl((x, y, .118), (x, y + .023, .15), .036, 8), ('b', 'head'), .5)
        C.add(lens, cyl((x, y + .0035, .1245), (x, y + .027, .157), .029, 8), ('b', 'head'), .2, .2)


def scarf_neck(C, col, tail=True, y0=1.30, y1=1.37):
    C.add(col, loft([ring_y(y0, 0, -.008, .094, .09), ring_y(y1, 0, -.01, .074, .07)], 10, (False, False)), ('c', NECKCH), .95)
    if tail: C.add(col, box((.04, 1.22, tz(1.22, .04) + .026), (.07, .15, .012)), ('b', 'chest'), .95)


def face_cover(C, col, lo=.52, hi=.86):
    C.add(col, ell(HC, HR, 12, 4, (PI * lo, PI * hi), grow=.008), ('b', 'head'), .9)
    C.add(col, box((0, 1.455, hsurf(0, 1.455, .008) + .004), (.11, .045, .01)), ('b', 'head'), .9)
    C.add(col, box((0, 1.455, -.1), (.04, .06, .03)), ('b', 'head'), .9)


def plate_carrier(C, col, plate, pouch, y0=1.04, y1=1.285, pouch_rows=True):
    C.add(col, torso(y0, y1, .02, .026), ('c', TORSO), .75)
    C.add(plate, box((0, 1.16, tz(1.16, 0) + .03), (.2, .22, .035)), ('b', 'chest'), .6)
    C.add(plate, box((0, 1.16, tz(1.16, 0, False) - .03), (.2, .22, .035)), ('b', 'chest'), .6)
    if pouch_rows:
        for x in (-.075, 0, .075): C.add(pouch, box((x, 1.075, tz(1.075, x) + .034), (.06, .09, .04)), ('b', 'spine'), .75)
    C.add(pouch, box((-.19, 1.12, 0), (.04, .12, .09)), ('b', 'spine'), .75)


def knee_pads(C, col, strap=None):
    for s in 'LR':
        sg = 1 if s == 'L' else -1
        C.add(col, box((sg * .087, .435, .066), (.1, .12, .048)), ('b', 'shin.' + s), .6)
        if strap: C.add(strap, box((sg * .087, .384, .082), (.09, .03, .02)), ('b', 'shin.' + s), .6)


def strap(C, col, pts, w=.036, d=.014, off=.02, both=True):
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        for front in ((True, False) if both else (True,)):
            sgn = 1 if front else -1
            p0 = V(x0, y0, tz(y0, x0, front) + sgn * off); p1 = V(x1, y1, tz(y1, x1, front) + sgn * off)
            C.add(col, obox(p0, p1, w, d, V(0, 0, 1)), ('c', TORSO), .8)


def belt_with(C, col='#17140f', buckle='#9a9a94'): belt(C, col, buckle)


def patches(C, cols, seed, n_torso=10, n_leg=7, n_arm=4):
    rr = random.Random(seed)
    for _ in range(n_torso):
        x = rr.uniform(-.13, .13); y = rr.uniform(1.0, 1.28)
        C.add(rr.choice(cols), box((x, y, tz(y, x) + .006), (rr.uniform(.04, .09), rr.uniform(.035, .07), .012)), ('b', tb(y)), .95)
    for s in 'LR':
        sg = 1 if s == 'L' else -1
        for _ in range(n_leg):
            y = rr.uniform(.45, .85); x = sg * (.09 + rr.uniform(-.04, .04))
            C.add(rr.choice(cols), box((x, y, .094), (rr.uniform(.04, .08), rr.uniform(.04, .08), .012)), ('b', 'thigh.' + s), .95)
        for _ in range(n_arm):
            t = rr.uniform(.1, .9); p = arm_pt(s, t)
            C.add(rr.choice(cols), box(p + V(0, 0, .052), (rr.uniform(.035, .05), rr.uniform(.04, .06), .01)), ('b', 'upper_arm.' + s if t < .5 else 'forearm.' + s), .95)
        for _ in range(3):
            y = rr.uniform(.2, .38)
            C.add(rr.choice(cols), box((sg * .085, y, .068), (.05, .05, .01)), ('b', 'shin.' + s), .95)


def pocket_legs(C, col):
    for s in 'LR':
        sg = 1 if s == 'L' else -1
        C.add(col, box((sg * .163, .70, .01), (.034, .13, .1)), ('b', 'thigh.' + s), .9)


def backpack(C, col, col2, w=.27, h=.3, d=.16, y=1.17):
    C.add(col, box((0, y, -.185), (w, h, d)), ('b', 'chest'), .9)
    C.add(col2, box((0, y + .1, -.185), (w - .01, .1, d + .01)), ('b', 'chest'), .9)
    for sg in (-1, 1):
        C.add(col2, box((sg * (w / 2 + .01), y - .09, -.185), (.04, .14, d - .04)), ('b', 'chest'), .9)
        C.add(col2, obox((sg * .1, 1.31, -.02), (sg * .1, 1.2, -.1), .05, .02), ('b', 'chest'), .9)


def cross(C, c, z, bone, col='#b3262b', size=.05, axis='z', th=.006):
    """flat blank red cross, geometry only, on a surface facing +z (axis z) or +x (axis x)"""
    if axis == 'z':
        C.add(col, box(c + V(0, 0, z), (size, size * .32, th)), ('b', bone), .6)
        C.add(col, box(c + V(0, 0, z), (size * .32, size, th)), ('b', bone), .6)
    else:
        C.add(col, box(c + V(z, 0, 0), (th, size * .32, size)), ('b', bone), .6)
        C.add(col, box(c + V(z, 0, 0), (th, size, size * .32)), ('b', bone), .6)


def holster(C, col='#17140f', grip='#2b2d30', side=-1):
    C.add(col, box((side * .196, .885, 0), (.05, .15, .085)), ('b', 'hips'), .55)
    C.add(grip, box((side * .2, .975, -.012), (.04, .045, .07)), ('b', 'hips'), .4, .5)


def pouches_front(C, col):
    for x in (-.07, .07): C.add(col, box((x, .955, tz(.955, x) + .018), (.05, .09, .035)), ('b', 'spine'), .55)


def collar(C, col): C.add(col, box((0, 1.285, -.02), (.12, .035, .1)), ('c', NECKCH), .9)


# ------------------------------------------------------------------ kinds
def desert(n):
    C = Char(f'trooper2_desert_{n}')
    tan = ['#b39c6e', '#a8946a', '#bda77a'][n]; tan2 = ['#8e7b52', '#85734c', '#98835a'][n]
    spec = dict(skin=SKINS[[0, 3, 1][n]], hair=HAIRS[[3, 0, 1][n]], shirt=tan, trouser=tan, boot='#5a4631', glove='#6b5a3c', sleeve='long', face=True, sole='#2a2218')
    body(C, spec); belt(C, '#4f4331', '#8a8a82'); pocket_legs(C, tan2); collar(C, tan)
    if n == 1:
        boonie(C, tan2); hair_cap(C, spec['hair'], .02, PI * .30)
    else:
        helmet(C, tan2, .95); band(C, '#3b3220'); chin_strap(C, '#3b3220')
        rr = random.Random(30 + n)
        for _ in range(8):
            th = rr.uniform(.2, 1.2); ph = rr.uniform(0, 2 * PI); hc = V(0, 1.522, .010); hr = V(.114, .100, .124)
            C.add(rr.choice(['#c2ad80', '#76653f']), box(hc + hr * V(math.sin(th) * math.sin(ph), math.cos(th), math.sin(th) * math.cos(ph)), (.03, .008, .016)), ('b', 'head'), .95)
        if n == 2: goggles_up(C, '#3b3220', '#47552f')
    plate_carrier(C, tan2, '#5d5030', '#6a5a3a')
    scarf_neck(C, ['#d8cfb4', '#9aa07a', '#c9b88a'][n], tail=True)
    for s in 'LR': C.add('#6b5a3c', cyl(arm_pt(s, .93), arm_pt(s, .99), .04, 8), ('c', ARM(s)), .8)
    knee_pads(C, '#4a3f2a', '#3b3220')
    if n != 0: backpack(C, '#8e7b52', '#6a5a3a', .24, .26, .14, 1.15)
    return C


def urban(n):
    C = Char(f'trooper2_urban_{n}')
    base = ['#6c7480', '#5f6b7a', '#747a82'][n]; dk = ['#4c5666', '#3f4b5e', '#555a62'][n]; lt = '#9aa2ac'
    spec = dict(skin=SKINS[[2, 0, 4][n]], hair=HAIRS[[1, 2, 0][n]], shirt=base, trouser=base, boot='#1d1d1f', glove='#202226', sleeve='long', face=True, sole='#0a0a0a')
    body(C, spec); patches(C, [dk, lt, '#38414f'], 11 + n)
    belt(C, '#24262a', '#9a9a94'); collar(C, base)
    helmet(C, ['#59616d', '#4d5765', '#5d6168'][n], .6, .1); band(C, '#17181a'); chin_strap(C, '#17181a')
    for x in (-.108, .108): C.add('#17181a', obox((x, 1.56, .03), (x, 1.56, -.06), .012, .03), ('b', 'head'), .5)
    goggles_on_eyes(C, '#17181a', ['#2d4254', '#4a3b22', '#2d4254'][n])
    plate_carrier(C, '#3a4250', '#252a31', '#2c323b', 1.05, 1.28)
    knee_pads(C, '#17181a', '#2b2e33')
    for s in 'LR':
        sg = 1 if s == 'L' else -1
        C.add('#17181a', cyl(arm_pt(s, .45), arm_pt(s, .56), .05, 8), ('c', ARM(s)), .6)      # elbow pads
        C.add('#202226', cyl(arm_pt(s, .93), arm_pt(s, .99), .04, 8), ('c', ARM(s)), .8)
    pocket_legs(C, dk)
    if n == 2: backpack(C, '#3a4250', '#2c323b', .25, .28, .14, 1.15)
    return C


def sniper(n):
    C = Char(f'trooper2_sniper_{n}')
    base = ['#4d5a35', '#5a5238', '#46503a'][n]
    strips = [['#4d5a35', '#6b6a3f', '#3a4429', '#7a7a4a'], ['#5a5238', '#7a6a42', '#3e3a28', '#8a7a52'], ['#46503a', '#5f6b44', '#2f3a2a', '#6d7a50']][n]
    spec = dict(skin=SKINS[[1, 0, 3][n]], hair=HAIRS[[2, 3, 0][n]], shirt=base, trouser=base, boot='#3b2d20', glove='#3a4429', sleeve='long', face=True)
    body(C, spec); belt(C, '#2c2a1f', '#6a6a60'); collar(C, base)
    if n == 1:      # hood
        C.add(strips[0], ell(HC, HR, 12, 8, th=(0, PI * .78), grow=.016), ('b', 'head'), 1.0)
        C.add(strips[1], ell((0, 1.32, -.05), (.12, .07, .1), 10, 4, (0, PI * .7)), ('c', NECKCH), 1.0)
        hc = V(0, 1.52, 0)
    else:
        boonie(C, strips[0], '#2a2b22'); hair_cap(C, spec['hair'], .02, PI * .30); hc = V(0, 1.54, .01)
    rr = random.Random(50 + n)
    def hang(p, ln, bone, w=.018):
        a = rr.uniform(-.25, .25); b = rr.uniform(-.25, .25)
        C.add(rr.choice(strips), obox(p, p + V(math.sin(a) * ln, -ln, math.sin(b) * ln), w, .007), ('b', bone), 1.0)
    for k in range(14):                      # from hat / hood brim
        ph = rr.uniform(0, 2 * PI); r = .2 if n != 1 else .122
        hang(hc + V(math.sin(ph) * r, -.02, math.cos(ph) * r + .01), rr.uniform(.08, .15), 'head')
    for k in range(18):                      # shoulders and back
        x = rr.uniform(-.17, .17); y = rr.uniform(1.12, 1.3)
        hang(V(x, y, tz(y, x, False) - .01), rr.uniform(.12, .22), 'chest', .022)
    for k in range(8):                       # chest front
        x = rr.uniform(-.12, .12); y = rr.uniform(1.15, 1.28)
        hang(V(x, y, tz(y, x) + .012), rr.uniform(.08, .14), 'chest')
    for s in 'LR':
        for k in range(10):
            t = rr.uniform(.05, .85); p = arm_pt(s, t)
            hang(p + V(rr.choice((-1, 1)) * .045, 0, rr.uniform(-.03, .03)), rr.uniform(.08, .16), 'upper_arm.' + s if t < .5 else 'forearm.' + s)
        for k in range(5):
            y = rr.uniform(.45, .85); hang(V((1 if s == 'L' else -1) * rr.uniform(.06, .16), y, .09), rr.uniform(.1, .18), 'thigh.' + s)
    # rifle sling (rifle itself is a separate weapon node)
    strap(C, '#2b2a1f', [(-.16, 1.29), (-.10, 1.22), (-.03, 1.13), (.04, 1.04), (.10, .97)], .04, .012, .028)
    C.add('#6a6a60', box((-.15, 1.285, tz(1.285, -.15) + .04), (.03, .03, .014)), ('b', 'chest'), .4, .7)
    C.add('#6a6a60', box((.1, .975, tz(.975, .1) + .04), (.03, .03, .014)), ('b', 'spine'), .4, .7)
    for s in 'LR': C.add('#3a4429', cyl(arm_pt(s, .93), arm_pt(s, .99), .04, 8), ('c', ARM(s)), .8)
    return C


def medic(n):
    C = Char(f'trooper2_medic_{n}'); od = ['#566037', '#4d5a35', '#5b6339'][n]; od2 = '#3f4a2b'
    spec = dict(skin=SKINS[[3, 1, 0][n]], hair=HAIRS[[0, 4, 2][n]], shirt=od, trouser=od, boot='#3b2d20', glove='#d9d6c8' if n == 2 else '#2f2a22', sleeve='long', face=True)
    body(C, spec); belt(C, '#2c2f22', '#8a8a82'); collar(C, od); pocket_legs(C, od2)
    if n == 1:
        C.add(od2, ell(V(0, 1.535, .0), V(.106, .07, .118), 12, 5, (0, PI * .5)), ('b', 'head'), .9)                 # soft cap
        C.add(od2, tilted_box((0, 1.535, .12), (.12, .008, .07), -.1), ('b', 'head'), .85)
        C.add('#ece9de', loft([ring_y(1.515, 0, 0, .104, .114), ring_y(1.54, 0, 0, .107, .117)], 12, (False, False), 0), ('b', 'head'), .7)
        hair_cap(C, spec['hair'], .02, PI * .3)
    else:
        helmet(C, od2, .95); band(C, '#ece9de', 1.52, 1.552, .115, .125, .010, .7); chin_strap(C, '#2f3820')
        cross(C, V(.1135, 1.585, .01), .0, 'head', size=.04, axis='x') if False else None
        C.add('#ece9de', box((0, 1.58, .005), (.2, .02, .02)), ('b', 'head'), .7) if False else None
        for sg in (-1, 1): cross(C, V(sg * .1115, 1.532, .01), 0, 'head', size=.04, axis='x', th=.008)
    C.add('#3d4030', torso(1.06, 1.275, .017, .02), ('c', TORSO), .9)
    for x in (-.075, 0, .075): C.add('#d9d6c8' if x == 0 else '#2f3322', box((x, 1.14, tz(1.14, x) + .036), (.062, .1, .045)), ('b', 'spine'), .9)
    cross(C, V(0, 1.14, tz(1.14, 0) + .06), 0, 'spine', size=.05)
    # medic bag
    bagc = ['#4a4630', '#2f3a2a', '#4a4630'][n]
    if n == 0:
        C.add(bagc, box((0, 1.12, -.2), (.3, .26, .14)), ('b', 'chest'), .9)
        C.add('#3a3726', box((0, 1.26, -.2), (.28, .04, .15)), ('b', 'chest'), .9)
        cross(C, V(0, 1.12, -.27), 0, 'chest', size=.12, th=.008)
        for sg in (-1, 1): C.add('#3d4030', obox((sg * .1, 1.31, -.02), (sg * .1, 1.18, -.12), .05, .02), ('b', 'chest'), .9)
    else:
        C.add(bagc, box((.2, .86, .0), (.1, .2, .26)), ('b', 'hips'), .9)
        C.add('#3a3726', box((.2, .965, .0), (.105, .04, .27)), ('b', 'hips'), .9)
        cross(C, V(.2, .86, 0), .054, 'hips', size=.12, axis='x', th=.008)
        strap(C, '#3d4030', [(-.15, 1.28), (-.08, 1.2), (.0, 1.1), (.1, .98), (.17, .93)], .035, .012, .02)
    knee_pads(C, '#26241f', '#1c1b17')
    for s in 'LR': C.add('#2f2a22', cyl(arm_pt(s, .93), arm_pt(s, .99), .04, 8), ('c', ARM(s)), .8)
    # white armband
    for s in 'LR': C.add('#ece9de', cyl(arm_pt(s, .2), arm_pt(s, .3), .06, 8), ('c', ARM(s)), .8) if s == 'L' else None
    return C


def engineer(n):
    C = Char(f'trooper2_engineer_{n}')
    cov = ['#5a6b82', '#8a7a58', '#6b6f52'][n]; cov2 = ['#46566b', '#6f6144', '#565a40'][n]
    spec = dict(skin=SKINS[[4, 2, 0][n]], hair=HAIRS[[0, 1, 4][n]], shirt=cov, trouser=cov, boot='#4a3826', glove='#a8863a', sleeve='long', face=True)
    body(C, spec); belt(C, '#3a2a1a', '#9a9a94'); collar(C, cov); pocket_legs(C, cov2)
    hard_hat(C, ['#e8c32a', '#e8e8e2', '#d9701f'][n])
    if n == 1:      # lamp
        C.add('#2b2d30', cyl((0, 1.585, .125), (0, 1.595, .145), .022, 8), ('b', 'head'), .4, .4)
    hair_cap(C, spec['hair'], .02, PI * .3)
    # tool belt: wide belt, hanging tools
    C.add('#4a3220', torso(.9, .975, .022), ('c', TORSO[:3]), .8)
    C.add('#3a2a1a', box((.2, .83, .02), (.045, .13, .1)), ('b', 'hips'), .85)                      # tool pouch
    C.add('#3a2a1a', box((-.2, .83, .02), (.045, .13, .1)), ('b', 'hips'), .85)
    C.add('#8a8e92', box((.2, .76, .03), (.014, .14, .04)), ('b', 'hips'), .4, .7)                    # wrench
    C.add('#6b4a2a', box((-.205, .76, .02), (.02, .16, .022)), ('b', 'hips'), .8)                    # hammer handle
    C.add('#555b61', box((-.205, .685, .02), (.03, .03, .06)), ('b', 'hips'), .4, .7)
    C.add('#c9852a', box((-.06, .84, tz(.9, -.06) + .02), (.07, .08, .045)), ('b', 'hips'), .85)       # front pouch
    # backpack with coiled wire
    backpack(C, '#4a4630', '#3a3726', .26, .3, .15, 1.16)
    C.add('#d9701f', cyl((0, 1.18, -.285), (0, 1.18, -.2), .115, 12), ('b', 'chest'), .6)           # wire coil (ring of cable)
    C.add('#2b2d30', cyl((0, 1.18, -.288), (0, 1.18, -.29), .05, 10), ('b', 'chest'), .6)
    C.add('#3a3d40', cyl((0, 1.18, -.22), (0, 1.18, -.283), .05, 8), ('b', 'chest'), .6)
    C.add('#e8c32a', obox((-.13, 1.25, -.22), (.14, 1.1, -.22), .012, .012), ('b', 'chest'), .6)     # loose wire lashing
    # safety glasses / kneepads
    knee_pads(C, '#2b2a24')
    for s in 'LR': C.add('#a8863a', cyl(arm_pt(s, .93), arm_pt(s, .99), .04, 8), ('c', ARM(s)), .8)
    return C


def pilot(n):
    C = Char(f'trooper2_pilot_{n}')
    suit = ['#6e7560', '#8a7f5f', '#3f4a58'][n]; suit2 = ['#565c48', '#6f6647', '#2f3844'][n]
    spec = dict(skin=SKINS[[1, 2, 0][n]], hair=HAIRS[[0, 2, 3][n]], shirt=suit, trouser=suit, boot='#1e1b18', glove='#3a3228', sleeve='long', face=True, sole='#0a0a0a')
    body(C, spec); belt(C, '#2a2a28', '#9a9a94'); pocket_legs(C, suit2); collar(C, suit2)
    hc = V(0, 1.515, .006); hr = V(.119, .116, .130)
    hcol = ['#e6e6e0', '#9aa1a7', '#d9d6c8'][n]
    C.add(hcol, ell(hc, hr, 12, 7, (0, PI * .66)), ('b', 'head'), .35, .1)
    C.add(hcol, ell(hc, hr, 10, 2, (PI * .66, PI * .78), (PI * .55, PI * 1.45), grow=.002), ('b', 'head'), .35, .1)
    # visor
    vc = ['#2b3944', '#6b6a58', '#2b3944'][n]
    if n == 1:      # raised
        C.add(vc, ell(hc + V(0, .045, .008), hr + V(.012, .004, .014), 10, 3, (PI * .1, PI * .38), (-PI * .38, PI * .38)), ('b', 'head'), .15, .2)
    else:
        C.add(vc, ell(hc + V(0, -.02, .006), hr + V(.012, .004, .014), 10, 4, (PI * .3, PI * .64), (-PI * .38, PI * .38)), ('b', 'head'), .12, .3)
    C.add('#17181a', loft([ring_y(1.488, 0, .006, .12, .131), ring_y(1.502, 0, .006, .121, .132)], 12, (False, False), 0), ('b', 'head'), .6)   # visor seal ring
    for sg in (-1, 1): C.add('#17181a', box((sg * .122, 1.5, .0), (.025, .075, .07)), ('b', 'head'), .55)           # ear cups
    C.add('#17181a', box((0, 1.60, .122), (.05, .03, .03)), ('b', 'head'), .5)
    # life vest
    C.add('#e0742a', torso(1.05, 1.31, .03, .04), ('c', TORSO), .8)
    C.add('#c9631f', torso(1.05, 1.31, .033, .043), ('c', TORSO), .8) if False else None
    C.add('#2b2d30', box((0, 1.0, tz(1.04, 0) + .045), (.34, .02, .02)), ('b', 'spine'), .7)
    for sg in (-1, 1):
        C.add('#e0742a', ell((sg * .105, 1.3, -.01), (.07, .05, .1), 8, 3, (0, PI * .7)), ('c', NECKCH), .8)           # collar cell
        C.add('#d5d9dc', box((sg * .11, 1.18, tz(1.18, sg * .11) + .05), (.05, .1, .01)), ('b', 'chest'), .35, .3)       # reflective patch
        C.add('#17181a', box((sg * .09, 1.09, tz(1.09, sg * .09) + .052), (.07, .09, .035)), ('b', 'spine'), .75)       # pouch
    C.add('#c9c9c2', cyl((.07, 1.09, tz(1.09, .07) + .06), (.07, 1.17, tz(1.17, .07) + .06), .012, 6), ('b', 'chest'), .4, .5)  # whistle/light
    C.add('#d9d6c8', box((0, 1.31, .06), (.04, .02, .06)), ('c', NECKCH), .5)
    for s in 'LR': C.add('#17181a', cyl(arm_pt(s, .93), arm_pt(s, .99), .04, 8), ('c', ARM(s)), .8)
    if n == 2:      # leg g-suit straps
        for s in 'LR':
            sg = 1 if s == 'L' else -1
            C.add('#2b2d30', cyl(V(sg * .091, .72, 0), V(sg * .091, .74, 0), .102, 10), ('b', 'thigh.' + s), .8)
    return C


def officer(n):
    C = Char(f'trooper2_officer_{n}')
    uni = ['#566037', '#6d6a52', '#3a4350'][n]; tr = ['#4a5530', '#5d5a44', '#2e3640'][n]
    spec = dict(skin=SKINS[[0, 3, 2][n]], hair=HAIRS[[4, 0, 1][n]], shirt=uni, trouser=tr, boot='#17130f', glove=None, sleeve='long', face=True, sole='#0a0a0a')
    body(C, spec); belt(C, '#2a1f14', '#c8a23a'); collar(C, '#d9d6c8' if n == 1 else uni)
    cols = ['#3f4a2b', '#4a4632', '#242a33']
    if n == 1: beret(C, '#6a2a2a' if False else '#7a2a2c', '#c8a23a'); hair_cap(C, spec['hair'], .02, PI * .3)
    else: peaked_cap(C, cols[n], '#0f0f10', '#0f0f10'); hair_cap(C, spec['hair'], .01, PI * .46)
    # sidearm holster + cross strap
    holster(C, '#2a1f14', '#2b2d30', -1)
    strap(C, '#2a1f14', [(.17, 1.285), (.09, 1.2), (.0, 1.1), (-.1, 1.0), (-.17, .96)], .035, .012, .02, both=False) if False else None
    C.add('#2a1f14', obox(V(.15, 1.27, tz(1.27, .15) + .012), V(-.11, .975, tz(.975, -.11) + .012), .034, .012, V(0, 0, 1)), ('c', TORSO), .6)
    for s in 'LR':
        sg = 1 if s == 'L' else -1
        C.add(cols[n], tilted_box((sg * .165, 1.292, 0), (.075, .016, .085), 0, -sg * .28), ('b', 'chest'), .8)        # epaulette
        C.add('#c8a23a', box((sg * .165, 1.302, 0), (.03, .006, .03)), ('b', 'chest'), .4, .7)
    C.add('#d9d6c8', box((.06, 1.18, tz(1.18, .06) + .012), (.05, .02, .008)), ('b', 'chest'), .6)                     # blank name tab
    C.add('#3a3d40', box((-.075, 1.18, tz(1.18, -.075) + .012), (.04, .045, .008)), ('b', 'chest'), .6)
    # map case on the left hip with strap
    C.add('#3a2a1a', box((.215, .8, .0), (.03, .21, .27)), ('b', 'hips'), .75)
    C.add('#5a4631', box((.232, .8, .0), (.006, .17, .22)), ('b', 'hips'), .5)
    C.add('#c9c4b0', box((.236, .8, .0), (.004, .14, .19)), ('b', 'hips'), .6)
    C.add('#2a1f14', obox(V(.215, .9, .0), V(.195, .98, .0), .03, .012), ('b', 'hips'), .6)
    if n == 2: C.add('#c8c8c0', cyl(V(.0, 1.285, tz(1.285, 0) + .01), V(.0, 1.285, tz(1.285, 0) + .03), .03, 6), ('b', 'chest'), .5) if False else None
    for s in 'LR': C.add('#17130f', cyl(arm_pt(s, .93), arm_pt(s, .99), .04, 8), ('c', ARM(s)), .7) if n == 0 else None
    return C


def militia(n):
    C = Char(f'trooper2_militia_{n}')
    jk = ['#6b5a45', '#4b6a4e', '#8a8d90'][n]; sl = ['#3f4f6b', '#8a6a4a', '#5a3f2d'][n]
    trou = ['#3b4a63', '#5a5a42', '#2e3033'][n]
    spec = dict(skin=SKINS[[2, 4, 1][n]], hair=HAIRS[[0, 1, 2][n]], shirt=jk, sleeve_col=sl, trouser=trou, boot=['#5a4228', '#2a2b2d', '#6b5a40'][n],
                glove=None, sleeve='long', face=n != 0, sole='#cdbb8f')
    body(C, spec)
    for s in 'LR': C.add(sl, cyl(arm_pt(s, .94), arm_pt(s, 1.0), .037, 8), ('c', ARM(s)), .9)
    C.add('#2a2b2d', torso(.95, .99, .012), ('c', TORSO[:3]), .7)
    C.add(['#7a5a3a', '#6b6a3f', '#4a4d52'][n], box((0, 1.03, tz(1.03, 0) + .016), (.21, .1, .02)), ('b', 'spine'), .9)
    C.add(jk, ell((0, 1.335, -.045), (.095, .055, .085), 10, 4, (0, PI * .75)), ('c', NECKCH), .9)
    # mismatched patch on one knee
    C.add(['#6b6a3f', '#3b4a63', '#8a6a4a'][n], box((.087, .45, .094), (.1, .12, .01)), ('b', 'thigh.L'), .95)
    C.add(['#4a4d52', '#8a8d90', '#4b6a4e'][n], box((-.087, .6, .094), (.09, .08, .01)), ('b', 'thigh.R'), .95)
    # headwear
    if n == 0: hair_cap(C, HAIRS[0], .01, PI * .42)
    if n == 1: ball_cap(C, '#5a3f2d'); hair_cap(C, HAIRS[1], .02, PI * .3)
    if n == 2:      # head wrap
        C.add('#7a2a2c' if False else '#6b3f3a', ell(HC + V(0, .01, 0), HR, 12, 5, (0, PI * .46), grow=.012), ('b', 'head'), .95)
        C.add('#6b3f3a', box((.07, 1.53, -.1), (.04, .05, .04)), ('b', 'head'), .9)
    # scarf over the face (not n=2: neck scarf only)
    face_cover(C, ['#8a8d90', '#a23f33' if False else '#7a5a3a', '#2f3033'][n]) if n != 2 else face_cover(C, '#b0a89a')
    # bandolier
    brown = '#4a3220'
    pts = [(-.16, 1.29), (-.10, 1.23), (-.03, 1.14), (.04, 1.05), (.11, .98), (.15, .945)]
    strap(C, brown, pts, .036, .014, .02)
    for (x0, y0), (x1, y1) in zip(pts[1:-1], pts[2:]):
        for f in (.25, .75):
            x = x0 + (x1 - x0) * f; y = y0 + (y1 - y0) * f
            C.add('#b08a3a', box((x, y, tz(y, x) + .035), (.018, .028, .014)), ('b', tb(y)), .4, .7)
    if n == 1:      # vest over the top
        C.add('#3d4030', torso(1.05, 1.27, .014, .018), ('c', TORSO), .9)
    if n == 2:      # plastic bag / satchel on a cord
        C.add('#5a4a30', box((.2, .95, -.03), (.06, .2, .22)), ('b', 'hips'), .9)
        C.add('#4a3220', obox(V(.15, 1.28, -.02), V(.2, 1.05, -.03), .02, .01), ('b', 'chest'), .8)
    return C


def riot(n):
    C = Char(f'trooper2_riot_{n}')
    blk = ['#1c2229', '#1b1d1f', '#22282d'][n]; arm_c = '#2c3238'
    spec = dict(skin=SKINS[[1, 4, 2][n]], hair=HAIRS[[0, 0, 2][n]], shirt=blk, trouser=blk, boot='#0e0f10', glove='#17181a', sleeve='long', face=True, sole='#050505')
    body(C, spec); belt(C, '#0e0f10', '#4a4d52'); collar(C, blk)
    hc, hr = V(0, 1.522, .008), V(.118, .104, .128)
    hcol = ['#2c3238', '#232a30', '#3a4148'][n]
    C.add(hcol, ell(hc, hr, 12, 6, (0, PI * .5)), ('b', 'head'), .35, .2)
    C.add(hcol, ell(hc, hr, 10, 3, (PI * .5, PI * .66), (PI * .52, PI * 1.48), grow=.002), ('b', 'head'), .35, .2)
    C.add(hcol, ell(hc, hr, 10, 2, (PI * .5, PI * .62), (-PI * .52, PI * .52), grow=-.004), ('b', 'head'), .35, .2) if False else None
    # neck guard for n=2
    if n == 2: C.add(hcol, loft([ring_y(1.40, 0, -.01, .085, .09), ring_y(1.33, 0, -.012, .1, .105)], 10, (False, False)), ('c', NECKCH), .5)
    vis = '#9bb6c6'
    if n == 1:     # visor down
        C.add(vis, ell(hc + V(0, -.02, .004), hr + V(.012, .008, .014), 10, 4, (PI * .3, PI * .72), (-PI * .4, PI * .4)), ('b', 'head'), .1, .1)
        C.add('#0e0f10', ell(hc + V(0, -.02, .004), hr + V(.014, .01, .016), 10, 1, (PI * .295, PI * .31), (-PI * .4, PI * .4)), ('b', 'head'), .5)
    else:          # visor raised
        C.add(vis, ell(hc + V(0, .04, .008), hr + V(.012, .004, .016), 10, 3, (PI * .16, PI * .42), (-PI * .38, PI * .38)), ('b', 'head'), .1, .1)
        C.add('#0e0f10', ell(hc + V(0, .04, .008), hr + V(.014, .006, .018), 10, 1, (PI * .415, PI * .435), (-PI * .38, PI * .38)), ('b', 'head'), .5)
    for sg in (-1, 1): C.add('#0e0f10', box((sg * .116, 1.55, .01), (.016, .05, .05)), ('b', 'head'), .5)       # visor pivots
    # chest protector and shoulder / arm guards
    C.add(arm_c, torso(1.03, 1.30, .026, .034), ('c', TORSO), .45, .2)
    C.add('#17181a', box((0, 1.2, tz(1.2, 0) + .045), (.2, .08, .02)), ('b', 'chest'), .5)
    C.add('#17181a', box((0, 1.1, tz(1.1, 0) + .045), (.17, .09, .02)), ('b', 'spine'), .5)
    C.add('#17181a', box((0, 1.2, tz(1.2, 0, False) - .045), (.2, .08, .02)), ('b', 'chest'), .5)
    for s in 'LR':
        sg = 1 if s == 'L' else -1
        C.add(arm_c, cyl(arm_pt(s, .02), arm_pt(s, .4), .068, 8), ('c', ARM(s)), .45, .2)                         # upper arm guard
        C.add(arm_c, cyl(arm_pt(s, .56), arm_pt(s, .92), .06, 8), ('c', ARM(s)), .45, .2)                         # forearm guard
        C.add('#17181a', cyl(arm_pt(s, .47), arm_pt(s, .55), .066, 8), ('c', ARM(s)), .5)
        C.add(arm_c, box((sg * .18, 1.29, 0), (.08, .04, .12)), ('b', 'chest'), .45, .2)                           # shoulder cap
        C.add(arm_c, box((sg * .09, .95, tz(.95, sg * .09) + .03), (.1, .13, .03)), ('b', 'hips'), .45, .2)      # hip/groin plate
        C.add(arm_c, box((sg * .091, .66, .098), (.11, .24, .028)), ('b', 'thigh.' + s), .45, .2)                   # thigh guard
        C.add(arm_c, box((sg * .087, .435, .075), (.11, .13, .04)), ('b', 'shin.' + s), .4, .2)                     # knee
        C.add(arm_c, box((sg * .087, .27, .07), (.1, .2, .03)), ('b', 'shin.' + s), .4, .2)                         # shin
        C.add('#17181a', box((sg * .087, .12, .095), (.09, .08, .035)), ('b', 'foot.' + s), .5)
    C.add('#17181a', cyl(V(.205, .93, .0), V(.205, .72, .0), .014, 6), ('b', 'hips'), .4)                          # baton
    C.add('#17181a', cyl(V(.205, .96, .0), V(.205, .93, .0), .02, 6), ('b', 'hips'), .5)
    return C


def special(n):
    C = Char(f'trooper2_special_{n}')
    blk = ['#15171a', '#2a3a2a', '#101214'][n]; gry = ['#262a2e', '#1f2c1f', '#2a2e33'][n]
    spec = dict(skin=SKINS[[3, 0, 4][n]], hair=HAIRS[0], shirt=blk, trouser=blk, boot='#0e0f10', glove='#0e0f10', sleeve='long', face=n == 1, sole='#050505')
    body(C, spec); belt(C, '#0e0f10', '#3a3d40')
    if n != 1:
        C.add(blk, ell(HC, HR, 12, 8, grow=.008), ('b', 'head'), .95)       # balaclava
        C.add(blk, loft([ring_y(1.40, 0, -.01, .066, .066), ring_y(1.34, 0, -.012, .082, .082)], 10, (False, False)), ('c', NECKCH), .95)
        eye_strip(C, spec)
    else:
        C.add('#2a3a2a', loft([ring_y(1.34, 0, -.01, .07, .07), ring_y(1.40, 0, -.01, .066, .066)], 10, (False, False)), ('c', NECKCH), .95)
        face_cover(C, '#1f2c1f', .55, .88)
    hc = V(0, 1.52, .008); hr = V(.112, .096, .122)
    helmet(C, gry, .5, .3, hc, hr)
    C.add('#0e0f10', box((0, 1.585, .128), (.06, .05, .035)), ('b', 'head'), .5, .4)                       # NVG mount shroud
    for x in (-.108, .108): C.add('#0e0f10', obox((x, 1.55, .03), (x, 1.55, -.06), .012, .03), ('b', 'head'), .5)
    # NVG goggles flipped up: a bridge plus two tubes pointing forward-up
    C.add('#0e0f10', box((0, 1.612, .15), (.1, .028, .05)), ('b', 'head'), .5, .4)
    for x in (-.034, .034):
        C.add('#17181a', cyl((x, 1.615, .14), (x, 1.66, .2), .026, 8), ('b', 'head'), .45, .4)
        C.add('#3b8a4a' if False else '#1f4a2a', cyl((x, 1.662, .202), (x, 1.667, .207), .02, 8), ('b', 'head'), .2, .2)
    if n == 2:
        for sg in (-1, 1): C.add('#0e0f10', box((sg * .108, 1.49, .0), (.03, .07, .06)), ('b', 'head'), .5)
        C.add('#0e0f10', obox((.108, 1.49, .0), (.07, 1.44, .08), .008, .008), ('b', 'head'), .5)
    plate_carrier(C, gry, '#1a1c1f', '#202327', 1.04, 1.285)
    for sg in (-1, 1): C.add(gry, box((sg * .182, 1.288, 0), (.07, .05, .1)), ('b', 'chest'), .75)
    knee_pads(C, '#202327', '#0e0f10')
    for s in 'LR':
        sg = 1 if s == 'L' else -1
        C.add('#202327', box((sg * .163, .74, .0), (.04, .17, .1)), ('b', 'thigh.' + s), .7)
    C.add('#0e0f10', box((-.205, .855, .01), (.04, .14, .08)), ('b', 'thigh.R'), .6)                       # drop-leg holster
    # sling and suppressor
    strap(C, '#0e0f10', [(-.16, 1.29), (-.09, 1.22), (-.02, 1.13), (.05, 1.04), (.11, .97)], .04, .014, .034)
    C.add('#2b2d30', cyl(V(.205, .78, .02), V(.205, 1.0, .02), .028, 8), ('b', 'hips'), .4, .6)           # suppressor in a side pouch
    C.add('#0e0f10', cyl(V(.205, .96, .02), V(.205, 1.0, .02), .034, 8), ('b', 'hips'), .6)
    C.add('#0e0f10', box((.205, .86, .02), (.07, .035, .07)), ('b', 'hips'), .6)
    if n == 0: C.add('#262a2e', box((0, 1.17, -.18), (.26, .22, .1)), ('b', 'chest'), .8)               # assault pack
    return C


def heavy(n):
    C = Char(f'trooper2_heavy_{n}')
    od = ['#4d5a35', '#4a4a44', '#3a4a52'][n]; arm_c = ['#3a3d30', '#2f3033', '#2b3338'][n]
    spec = dict(skin=SKINS[[2, 4, 0][n]], hair=HAIRS[[0, 1, 3][n]], shirt=od, trouser=od, boot='#17140f', glove='#17181a', sleeve='long', face=True, sole='#0a0a0a')
    body(C, spec); belt(C, '#17140f', '#6a6a60'); collar(C, od)
    hc, hr = V(0, 1.524, .008), V(.120, .104, .130)
    helmet(C, ['#3f4a2b', '#3a3a38', '#2b3338'][n], .8, 0.1, hc, hr)
    band(C, '#17181a', 1.53, 1.552, .119, .129, .008)
    C.add('#17181a', box((0, 1.40, .108), (.1, .04, .03)), ('b', 'head'), .6)                              # chin bar / mouth guard
    C.add('#17181a', obox((.1, 1.48, .06), (0, 1.395, .105), .015, .01), ('b', 'head'), .6) if False else None
    chin_strap(C, '#17181a')
    # bulky armour
    C.add(arm_c, torso(1.0, 1.31, .045, .06), ('c', TORSO), .6, .2)
    C.add('#17181a', box((0, 1.17, tz(1.17, 0) + .075), (.26, .27, .035)), ('b', 'chest'), .5)
    C.add('#17181a', box((0, 1.17, tz(1.17, 0, False) - .075), (.26, .27, .035)), ('b', 'chest'), .5)
    for x in (-.1, 0, .1): C.add('#202327', box((x, 1.04, tz(1.04, x) + .06), (.075, .1, .05)), ('b', 'spine'), .7)
    for s in 'LR':
        sg = 1 if s == 'L' else -1
        C.add(arm_c, box((sg * .205, 1.275, 0), (.11, .09, .17)), ('b', 'chest'), .55, .2)                  # big shoulder pauldrons
        C.add(arm_c, cyl(arm_pt(s, .1), arm_pt(s, .42), .074, 8), ('c', ARM(s)), .6, .2)
        C.add(arm_c, box((sg * .163, .72, .0), (.05, .22, .12)), ('b', 'thigh.' + s), .6)
        C.add(arm_c, box((sg * .09, .66, .108), (.13, .22, .035)), ('b', 'thigh.' + s), .6)
        C.add('#17181a', box((sg * .087, .435, .075), (.12, .13, .055)), ('b', 'shin.' + s), .6)
        C.add(arm_c, box((sg * .088, .27, .07), (.1, .17, .03)), ('b', 'shin.' + s), .6)
    C.add(arm_c, box((0, .9, tz(.95, 0) + .06), (.17, .12, .035)), ('b', 'hips'), .6)                       # groin plate
    # ammo belt: brass rounds in a link belt crossing the chest and dropping to a box
    pts = [(-.17, 1.30), (-.11, 1.22), (-.03, 1.12), (.05, 1.02), (.12, .93), (.19, .86)]
    strap(C, '#3a3d40', pts, .034, .02, .06, both=False)
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        for f in (.2, .5, .8):
            x = x0 + (x1 - x0) * f; y = y0 + (y1 - y0) * f
            C.add('#b08a3a', box((x, y, tz(y, x) + .076), (.022, .03, .02)), ('b', tb(y)), .35, .7)
    C.add('#4a4d40', box((.215, .8, .02), (.09, .16, .15)), ('b', 'hips'), .8)                              # ammo box on the hip
    C.add('#6a6a60', box((.215, .885, .02), (.09, .012, .15)), ('b', 'hips'), .5, .3)
    backpack(C, arm_c, '#202327', .3, .32, .16, 1.15)
    C.add('#17181a', cyl(V(.19, 1.0, -.17), V(.19, 1.3, -.17), .018, 6), ('b', 'chest'), .5)                # spare barrel tube
    return C


def port_worker(n):
    C = Char(f'trooper2_port_worker_{n}')
    ov = ['#2c3e5e', '#6b6f73', '#8a7a58'][n]; ov2 = ['#223048', '#55595d', '#6f6144'][n]
    hv = ['#d6e22a', '#f06a1a', '#d6e22a'][n]
    spec = dict(skin=SKINS[[3, 1, 2][n]], hair=HAIRS[[0, 4, 1][n]], shirt=ov, trouser=ov, boot='#3a2a1a', glove=['#c8a23a', '#d9d6c8', '#2f6a4a'][n], sleeve='long', face=True, sole='#17140f')
    body(C, spec); belt(C, '#2a2420', '#9a9a94'); collar(C, ov2); pocket_legs(C, ov2)
    for s in 'LR': C.add(['#c8a23a', '#d9d6c8', '#2f6a4a'][n], cyl(arm_pt(s, .93), arm_pt(s, .99), .04, 8), ('c', ARM(s)), .8)
    hard_hat(C, ['#e8e8e2', '#e8c32a', '#2f5f9a'][n])
    hair_cap(C, spec['hair'], .02, PI * .3)
    # hi-vis vest
    C.add(hv, torso(1.03, 1.30, .02), ('c', TORSO), .7)
    for y0 in (1.085, 1.17): C.add('#d5d9dc', torso(y0, y0 + .028, .026), ('c', TORSO), .35, .3)
    C.add(hv, box((0, 1.13, tz(1.13, 0, False) - .026), (.28, .24, .01)), ('b', 'chest'), .7)
    for sg in (-1, 1):
        C.add('#d5d9dc', box((sg * .06, 1.2, tz(1.2, sg * .06) + .022), (.025, .22, .008)), ('b', 'chest'), .35, .3) if False else None
    C.add('#2a2b2d', box((.095, 1.245, tz(1.245, .095) + .035), (.035, .06, .025)), ('b', 'chest'), .5, .3)     # radio
    C.add('#2a2b2d', box((-.07, 1.2, tz(1.2, -.07) + .03), (.07, .06, .02)), ('b', 'chest'), .6)                # ID badge holder (blank)
    C.add('#d9d6c8', box((-.07, 1.2, tz(1.2, -.07) + .042), (.05, .04, .004)), ('b', 'chest'), .6)
    if n == 1:      # ear defenders
        for sg in (-1, 1): C.add('#d9701f', box((sg * .118, 1.49, .0), (.03, .08, .075)), ('b', 'head'), .6)
        C.add('#d9701f', obox((.118, 1.53, 0), (-.118, 1.53, 0), .014, .012), ('b', 'head'), .6)
    if n == 2:      # safety glasses
        C.add('#a8c0c8', box((0, 1.502, hsurf(0, 1.502) + .014), (.12, .028, .008)), ('b', 'head'), .1, .1)
    C.add('#c8a23a', box((-.2, .88, 0), (.04, .1, .1)), ('b', 'hips'), .85) if n == 0 else None             # tool pouch
    return C


KINDS = [('desert', desert), ('urban', urban), ('sniper', sniper), ('medic', medic), ('engineer', engineer), ('pilot', pilot),
         ('officer', officer), ('militia', militia), ('riot', riot), ('special', special), ('heavy', heavy), ('port_worker', port_worker)]
CHARS = [fn(n) for _, fn in KINDS for n in range(3)]

exec(compile(_TAIL, 'build_troops_tail', 'exec'), globals())
