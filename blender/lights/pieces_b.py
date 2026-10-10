"""Generators, cables, junction boxes, searchlights, vehicle light modules."""
from lights_lib import *
from pieces_a import LX, WARM, SODIUM, COOL

def socket_row(r, xs, y, z, depth=.06, rad=.035, mat_=None):
    for x in xs:
        r.add(cyl((x, y, z), (x, y, z + depth), rad, rad, 6), mat_ or CABLE_Y)
        r.add(cyl((x, y, z), (x, y, z + .015), rad + .012, rad + .012, 6), STEEL_D)

def louvres(r, x0, x1, y0, y1, z, k, face=1, depth=.035):
    """k slats between y0..y1 on a face at z (face +1 = +Z, -1 = -Z)"""
    for i in range(k):
        y = y0 + (y1 - y0) * (i + .5) / k
        r.add(box(((x0 + x1) / 2, y, z + face * depth / 2), (x1 - x0, (y1 - y0) / k * .55, depth), rotx(face * D(-18))), BLACK)

# ======================================================================= 6  GENERATORS
def generator_small():
    r = Node('generator_small')
    for sx in (-1, 1):
        for sz in (-1, 1):
            r.add(box((sx * .34, .02, sz * .24), (.07, .04, .07)), RUBBER)
            r.add(box((sx * .34, .33, sz * .24), (.035, .5, .035)), RED)
        r.add(box((sx * .34, .07, 0), (.04, .04, .52)), RED)
        r.add(box((sx * .34, .59, 0), (.04, .04, .52)), RED)
        r.add(box((0, .07, sx * .24), (.72, .04, .04)), RED)
        r.add(box((0, .59, sx * .24), (.72, .04, .04)), RED)
    r.add(box((0, .09, 0), (.64, .03, .44)), STEEL_D)                     # base plate
    r.add(box((-.1, .29, -.02), (.34, .3, .3)), STEEL)                    # engine block
    r.add(cyl((.0, .29, -.02), (.4, .29, -.02), .13, .13, 8), YELLOW)       # alternator
    r.add(box((0, .5, 0), (.5, .16, .36)), RED)                           # fuel tank on top
    r.add(cyl((.12, .58, .05), (.12, .63, .05), .04, .04, 6), BLACK)
    r.add(cyl((-.22, .22, -.42), (-.22, .22, -.1), .06, .06, 8), STEEL_D)  # muffler
    r.add(tube([V(-.22, .22, -.42), V(-.22, .22, -.5), V(-.22, .4, -.52)], .03, 5), STEEL_D)
    r.add(box((0, .3, .25), (.68, .2, .05)), DARK)                         # control panel across the front
    socket_row(r, (-.2, -.05), .3, .275)
    r.add(box((.2, .35, .285), (.07, .05, .03)), IND_OFF)
    r.add(box((.2, .26, .285), (.1, .05, .03)), STEEL)
    r.add(box((-.34, .44, -.14), (.07, .07, .11)), BLACK)                  # pull handle
    r.empty('cable_generator_small_out', V(-.125, .3, .34), V(0, 0, 1), kind='cable_end', note='power socket pair on the front panel')
    r.empty('lightpt_generator_small_status', V(.2, .35, .3), V(0, 0, 1), **{'light': {'type': 'indicator', 'color': [.3, 1, .4], 'I': 0, 'range': 0, 'note': 'status lamp (ind_off -> ind_on); no real light needed'}})
    return r

def generator_medium():
    r = Node('generator_medium')
    for s in (-1, 1): r.add(box((0, .05, s * .35), (1.7, .1, .1)), STEEL_D)         # skid rails
    r.add(box((0, .2, 0), (1.3, .22, .75)), RED)                                      # belly fuel tank y .09..0.31
    r.add(cyl((-.65, .22, .22), (-.74, .22, .22), .05, .05, 6), BLACK)                # filler neck
    r.add(cyl((-.74, .22, .22), (-.78, .22, .22), .065, .065, 6), YELLOW)
    r.add(box((0, .72, 0), (1.5, .82, .8)), OLIVE)                                     # enclosure y .31..1.13
    r.add(box((0, 1.14, 0), (1.56, .04, .86)), OLIVE_D)                                # roof lid
    for s in (-1, 1):
        louvres(r, -.7, -.15, .5, .95, s * .4, 5, s)
        r.add(box((.35, .72, s * .405), (.015, .78, .015)), BLACK)                     # door seam
    r.add(box((.18, .82, .42), (.62, .5, .04)), DARK)                                  # connector panel (+Z face)
    socket_row(r, (-.02, .13, .28, .43), .72, .44)
    socket_row(r, (.07, .21, .35), .9, .44, .05, .03)
    r.add(box((-.02, .62, .45), (.12, .08, .03)), STEEL); r.add(box((.14, .62, .45), (.12, .08, .03)), STEEL)
    r.add(box((.3, .62, .45), (.07, .07, .03)), IND_OFF)
    r.add(cyl((.46, .8, .44), (.46, .8, .5), .035, .035, 8), RED)                      # e-stop
    r.add(box((.5, 1.22, .0), (.5, .16, .24)), STEEL_D)                                # silencer
    r.add(cyl((.6, 1.2, -.16), (.6, 1.95, -.16), .045, .045, 6), STEEL_D)              # exhaust stack
    r.add(cyl((.6, 1.93, -.16), (.6, 2.02, -.16), .03, .09, 6), STEEL)                 # rain cap
    r.add(tube([V(.6, 1.2, -.16), V(.6, 1.2, -.04)], .045, 6), STEEL_D)
    for x in (-.4, .4): r.add(box((x, 1.2, 0), (.05, .14, .05)), STEEL)                # lifting eye posts
    r.add(box((0, 1.28, 0), (.85, .04, .05)), STEEL)
    r.empty('cable_generator_medium_out_0', V(-.02, .72, .5), V(0, 0, 1), kind='cable_end', note='cam-lock socket 0')
    r.empty('cable_generator_medium_out_1', V(.13, .72, .5), V(0, 0, 1), kind='cable_end', note='cam-lock socket 1')
    r.empty('cable_generator_medium_out_2', V(.28, .72, .5), V(0, 0, 1), kind='cable_end', note='cam-lock socket 2')
    r.empty('cable_generator_medium_out_3', V(.43, .72, .5), V(0, 0, 1), kind='cable_end', note='cam-lock socket 3')
    r.empty('lightpt_generator_medium_status', V(.3, .62, .47), V(0, 0, 1), **{'light': {'type': 'indicator', 'color': [.3, 1, .4], 'I': 0, 'range': 0, 'note': 'status lamp (ind_off -> ind_on)'}})
    r.empty('smoke_generator_medium_exhaust', V(.6, 2.03, -.16), V(0, 1, 0), kind='fx', note='puff / smoke emitter when damaged')
    return r

def generator_large():
    r = Node('generator_large')
    for s in (-1, 1): r.add(box((0, .08, s * .5), (3.0, .16, .14)), STEEL_D)           # skid rails
    for x in (-.9, .9): r.add(box((x, .09, 0), (.3, .12, 1.3)), STEEL_D)               # cross beams (fork pockets)
    r.add(box((0, .28, 0), (2.5, .36, 1.1)), RED)                                      # belly fuel tank .10..0.46
    r.add(cyl((-1.0, .3, .56), (-1.0, .36, .56), .06, .06, 6), BLACK)
    r.add(box((.25, 1.12, 0), (2.5, 1.32, 1.2)), OLIVE)                                # enclosure y .46..1.78
    r.add(box((.25, 1.8, 0), (2.56, .05, 1.26)), OLIVE_D)                              # roof lid
    r.add(box((-1.35, 1.1, 0), (.5, 1.24, 1.1)), OLIVE_L)                              # radiator housing at -X
    for i in range(6): r.add(box((-1.62, .65 + i * .17, 0), (.04, .1, 1.0)), BLACK)    # radiator grille slats
    for s in (-1, 1):
        louvres(r, -.5, .45, .7, 1.5, s * .6, 6, s)
        louvres(r, .55, 1.05, .7, 1.5, s * .6, 5, s)
        r.add(box((.15, 1.1, s * .605), (.015, 1.26, .015)), BLACK)
    r.add(box((.15, 1.0, .64), (1.1, .9, .06)), DARK)                                  # connector bay (+Z side)
    socket_row(r, (-.3, -.1, .1, .3, .5), .72, .67, .06, .04)
    socket_row(r, (-.3, -.1, .1, .3, .5), 1.0, .67, .06, .04)
    for i, x in enumerate((-.3, .0, .3)): r.add(box((x, 1.3, .67), (.14, .1, .04)), STEEL)
    r.add(box((.6, 1.3, .67), (.07, .07, .04)), IND_OFF)
    r.add(cyl((.78, 1.28, .67), (.78, 1.28, .74), .045, .045, 8), RED)
    r.add(box((.9, 1.95, 0), (.9, .3, .5)), STEEL_D)                                   # silencer
    r.add(cyl((1.1, 1.9, .1), (1.1, 2.9, .1), .08, .08, 8), STEEL_D)                   # exhaust stack
    r.add(cyl((1.1, 2.88, .1), (1.1, 3.0, .1), .05, .15, 8), STEEL)
    for x in (-.7, 1.1): r.add(cyl((x, 1.8, .0), (x, 1.98, 0), .06, .06, 6), STEEL)    # lifting eyes
    for x in (-.7, 1.1): r.add(box((x, 2.0, 0), (.04, .16, .22)), STEEL)
    for i in range(5):
        r.empty('cable_generator_large_out_%d' % i, V(-.3 + .2 * i, .72, .75), V(0, 0, 1), kind='cable_end', note='cam-lock socket (bottom row) %d' % i)
    r.empty('lightpt_generator_large_status', V(.6, 1.3, .7), V(0, 0, 1), **{'light': {'type': 'indicator', 'color': [.3, 1, .4], 'I': 0, 'range': 0, 'note': 'status lamp (ind_off -> ind_on)'}})
    r.empty('smoke_generator_large_exhaust', V(1.1, 3.01, .1), V(0, 1, 0), kind='fx', note='puff / smoke emitter when damaged')
    return r

# ======================================================================= 6b  CABLES + JUNCTION BOXES
def plug(p, d, ln=.15, rad=.04):
    p = np.asarray(p, float); d = norm(np.asarray(d, float))
    return [(cyl(p, p + d * ln, rad, rad, 6), CABLE_Y), (cyl(p + d * ln * .6, p + d * ln * .75, rad + .012, rad + .012, 6), STEEL_D)]
CR = .026; GY = .042      # cable centre height when lying on the ground
def cable_straight_4m():
    r = Node('cableseg_straight_4m'); y = GY
    r.add(tube([V(0, y, .12), V(0, y, 3.88)], CR, 6), CABLE)
    r.addp(plug((0, y, 0), (0, 0, 1))); r.addp(plug((0, y, 4), (0, 0, -1)))
    r.empty('cable_straight_4m_a', (0, y, 0), V(0, 0, -1), kind='cable_end', length=4.0)
    r.empty('cable_straight_4m_b', (0, y, 4), V(0, 0, 1), kind='cable_end', length=4.0)
    return r
def cable_90():
    r = Node('cableseg_90'); y = GY; R_ = 1.2; z0 = .14
    pts = [V(0, y, .12)] + [V(R_ * (1 - math.cos(p)), y, z0 + R_ * math.sin(p)) for p in [i * PI / 2 / 7 for i in range(8)]] + [V(R_ + .02, y, z0 + R_)]
    r.add(tube(pts, CR, 6), CABLE)
    r.addp(plug((0, y, 0), (0, 0, 1))); r.addp(plug((R_ + .14, y, z0 + R_), (-1, 0, 0)))
    r.empty('cable_90_a', (0, y, 0), V(0, 0, -1), kind='cable_end')
    r.empty('cable_90_b', (R_ + .14, y, z0 + R_), V(1, 0, 0), kind='cable_end')
    return r
def cable_sag_6m(L=6.0, h=.9, sag=.866):
    """PARAMETRIC: a cable hanging between two raised sockets (height h) and lying on the ground at mid-span"""
    r = Node('cableseg_sag_6m'); y = GY
    pts = catenary(V(0, h, .15), V(0, h, L - .15), sag, 14)
    pts = [V(0, h, .12)] + pts + [V(0, h, L - .12)]
    pts = [V(p[0], max(p[1], y), p[2]) for p in pts]
    r.add(tube(pts, CR, 6), CABLE)
    r.addp(plug((0, h, 0), (0, 0, 1))); r.addp(plug((0, h, L), (0, 0, -1)))
    r.empty('cable_sag_6m_a', (0, h, 0), V(0, 0, -1), kind='cable_end', socket_height=h)
    r.empty('cable_sag_6m_b', (0, h, L), V(0, 0, 1), kind='cable_end', socket_height=h)
    return r
def cable_reel():
    r = Node('cablereel'); ay = .5
    for s in (-1, 1):
        r.add(box((s * .36, .03, 0), (.05, .05, .9)), STEEL_D)                          # ground rails
        for sz in (-1, 1): r.add(tube([V(s * .36, .03, sz * .42), V(s * .36, ay, 0)], .025, 5), STEEL_D)   # A-frame legs
        r.add(cyl((s * .27, ay, 0), (s * .3, ay, 0), .42, .42, 12), ORANGE)             # flanges
    r.add(cyl((-.3, ay, 0), (.3, ay, 0), .16, .16, 8), STEEL_D)                         # core
    r.add(cyl((-.27, ay, 0), (.27, ay, 0), .34, .34, 12), CABLE)                        # wound cable
    r.add(cyl((-.4, ay, 0), (.4, ay, 0), .03, .03, 6), STEEL)                           # axle
    r.add(box((.33, ay + .1, .22), (.04, .04, .24)), STEEL); r.add(box((.36, ay + .1, .34), (.07, .05, .05)), BLACK)   # crank
    tail = [V(0, ay, .3), V(0, .4, .5), V(0, .17, .66), V(0, GY, .9), V(0, GY, 2.2)]
    r.add(tube(tail, CR, 6), CABLE); r.addp(plug((0, GY, 2.2), (0, 0, 1)))
    r.empty('cable_reel_end', (0, GY, 2.35), V(0, 0, 1), kind='cable_end', note='free end of the reel (plug)')
    r.empty('pivot_cablereel_hub', (0, ay, 0), V(1, 0, 0), kind='pivot', note='reel spin axis (X)')
    return r

def junction_box():
    r = Node('junction_box')
    for sx in (-1, 1):
        for sz in (-1, 1): r.add(box((sx * .2, .05, sz * .11), (.08, .1, .08)), RUBBER)
    r.add(box((0, .27, 0), (.52, .34, .32)), YELLOW)
    r.add(box((0, .45, 0), (.54, .04, .34)), STEEL_D)                                   # lid
    r.add(box((0, .52, 0), (.3, .04, .04)), STEEL);
    for s in (-1, 1): r.add(box((s * .13, .49, 0), (.04, .06, .04)), STEEL)
    r.add(box((0, .24, .165), (.44, .22, .02)), DARK)
    socket_row(r, (-.14, 0, .14), .22, .17, .06, .035)
    r.add(box((.17, .33, .175), (.06, .05, .02)), IND_OFF)
    r.add(cyl((0, .2, -.16), (0, .2, -.23), .04, .04, 6), CABLE)                         # input gland
    for i in range(3): r.empty('cable_junction_box_out_%d' % i, V(-.14 + .14 * i, .22, .23), V(0, 0, 1), kind='cable_end', note='output socket %d' % i)
    r.empty('cable_junction_box_in', V(0, .2, -.23), V(0, 0, -1), kind='cable_end', note='fixed input gland')
    return r
def junction_box_dist():
    r = Node('junction_box_dist')
    for sx in (-1, 1): r.add(box((sx * .35, .04, 0), (.1, .08, .34)), RUBBER)
    r.add(box((0, .38, 0), (.9, .6, .34)), OLIVE)
    r.add(box((0, .7, 0), (.94, .05, .38)), OLIVE_D)
    r.add(box((0, .74, 0), (.4, .04, .04)), STEEL);
    r.add(box((0, .38, .175), (.8, .5, .02)), DARK)
    socket_row(r, (-.3, -.1, .1, .3), .2, .18, .06, .04)
    socket_row(r, (-.3, -.1, .1, .3), .38, .18, .06, .04)
    for i in range(4): r.add(box((-.3 + .2 * i, .56, .19), (.1, .08, .03)), STEEL)
    r.add(box((.4, .56, .19), (.05, .05, .03)), IND_OFF)
    r.add(cyl((-.2, .3, -.17), (-.2, .3, -.25), .05, .05, 6), CABLE)
    for i in range(4):
        r.empty('cable_junction_box_dist_out_%d' % i, V(-.3 + .2 * i, .2, .25), V(0, 0, 1), kind='cable_end', note='lower row socket %d' % i)
        r.empty('cable_junction_box_dist_out_%d' % (i + 4), V(-.3 + .2 * i, .38, .25), V(0, 0, 1), kind='cable_end', note='upper row socket %d' % (i + 4))
    r.empty('cable_junction_box_dist_in', V(-.2, .3, -.25), V(0, 0, -1), kind='cable_end', note='fixed input gland')
    return r

# ======================================================================= 7  SEARCHLIGHTS
def searchlight_ground():
    r = Node('searchlight_ground')
    r.add(box((0, .1, 0), (2.0, .2, 2.0)), CONC)                                        # pad y 0..0.2
    r.add(cyl((0, .2, 0), (0, .75, 0), .6, .55, 12), OLIVE_D)                          # fixed base drum
    r.add(cyl((0, .7, 0), (0, .78, 0), .62, .62, 12), STEEL_D)                          # bearing ring (static)
    for k in range(4):
        a = k * PI / 2 + PI / 4; r.add(box((.5 * math.cos(a), .3, .5 * math.sin(a)), (.05, .2, .05), roty(-a)), STEEL)   # bolts/lugs
    # power box + cable
    r.add(box((1.55, .35, 0), (.7, .7, .55)), OLIVE)
    r.add(box((1.55, .72, 0), (.74, .05, .6)), OLIVE_D)
    r.add(box((1.18, .38, 0), (.04, .4, .4)), DARK)
    socket_row_x = [(1.15, .3, z) for z in (-.1, .1)]
    for (x, y, z) in socket_row_x: r.add(cyl((x, y, z), (x - .06, y, z), .035, .035, 6), CABLE_Y)
    r.add(box((1.18, .52, .0), (.04, .06, .12)), IND_OFF)
    for sz in (-1, 1): r.add(box((1.55, .08, sz * .2), (.6, .16, .08)), STEEL_D)         # box feet rails
    r.add(tube([V(1.12, .3, .1), V(1.02, .25, .1), V(.9, .23, .1), V(.62, .23, .1), V(.55, .3, .1)], .03, 5), CABLE)
    # yoke (rotating): pivot on top of the bearing ring
    y = r.child('searchlight_yoke', (0, .78, 0)); y.moving = True
    y.add(cyl((0, 0, 0), (0, .12, 0), .56, .56, 12), STEEL)                              # turntable
    y.add(box((0, .15, 0), (1.5, .1, .42)), STEEL_D)
    for s in (-1, 1):
        y.add(box((s * .74, .78, 0), (.12, 1.2, .42)), OLIVE)                          # yoke arms up to the elevation axis
        y.add(cyl((s * .66, 1.12, 0), (s * .88, 1.12, 0), .1, .1, 8), STEEL)            # bearing boss
    y.add(box((0, .24, -.35), (.5, .3, .22)), DARK)                                      # slip-ring box
    h = y.child('searchlight_head', (0, 1.12, 0)); h.moving = True                      # pitch about X
    h.add(cyl((0, 0, -.5), (0, 0, .62), .55, .55, 14), OLIVE_L)                          # drum
    h.add(cyl((0, 0, -.82), (0, 0, -.5), .3, .55, 14), OLIVE)                            # tapered back
    h.add(cyl((0, 0, .58), (0, 0, .74), .6, .6, 14), STEEL_D)                            # front bezel
    h.add(cyl((0, 0, .7), (0, 0, .75), .5, .5, 14), LAMP_OFF)                            # lens disc
    h.add(cyl((0, 0, .66), (0, 0, .69), .53, .53, 14), BLACK)
    for s in (-1, 1): h.add(cyl((s * .5, 0, 0), (s * .8, 0, 0), .085, .085, 8), STEEL)    # trunnions into the yoke bosses
    h.add(cyl((0, .53, -.35), (0, .66, -.35), .1, .1, 8), STEEL_D)                       # cooling vent
    h.add(cyl((0, .65, -.35), (0, .7, -.35), .14, .14, 8), BLACK)
    h.add(tube([V(-.28, .5, .0), V(-.28, .75, .05), V(.28, .75, .05), V(.28, .5, 0)], .025, 5), STEEL)   # carry handle
    h.add(box((0, -.2, -.88), (.16, .16, .1)), DARK)                                       # cable gland
    h.empty('lightpt_searchlight_ground', V(0, 0, .8), R=np.eye(3), **LX([1, .96, .88], 2400, 14, 190, kind='spot'))
    r.empty('cable_searchlight_power', V(1.15, .3, 0), V(-1, 0, 0), kind='cable_end', note='power box socket pair (socket face looks -X toward the base)')
    r.empty('searchlight_yaw_axis', (0, .78, 0), V(0, 1, 0), kind='pivot', note='yoke yaw axis (Y); node searchlight_yoke carries it')
    return r

def spotlight_tripod():
    r = Node('spotlight_tripod')
    feet = [V(0, 0, .66), V(-.57, 0, -.33), V(.57, 0, -.33)]; head = V(0, 1.3, 0)
    for f in feet:
        r.add(tube([f + V(0, .02, 0), head + (f * 0 + V(f[0] * .06, 0, f[2] * .06))], .022, 5), STEEL_D)
        r.add(box(f + V(0, .015, 0), (.1, .03, .1)), RUBBER)
    pts = [f * .62 + head * .38 for f in feet]
    for i in range(3): r.add(tube([pts[i], pts[(i + 1) % 3]], .012, 4), STEEL_D)
    r.add(box((0, 1.32, 0), (.18, .1, .18)), STEEL_D)
    r.add(cyl((0, 1.3, 0), (0, 1.72, 0), .035, .035, 6), GALV)                           # centre column
    r.add(cyl((0, 1.62, 0), (0, 1.66, 0), .05, .05, 6), BLACK)
    r.add(box((0, 1.74, 0), (.4, .04, .14)), STEEL_D)                                    # yoke base
    for s in (-1, 1): r.add(box((s * .19, 1.9, 0), (.03, .34, .14)), STEEL_D)           # yoke arms
    r.add(tube([V(0, 1.74, -.06), V(0, 1.62, -.25), V(0, .9, -.55), V(0, GY, -1.1), V(0, GY, -3.0)], .02, 5), CABLE)
    r.addp(plug((0, GY, -3.0), (0, 0, -1), .13, .04))
    h = r.child('spotlight_head', (0, 1.98, 0)); h.moving = True
    h.add(cyl((0, 0, -.2), (0, 0, .2), .15, .15, 10), OLIVE)
    h.add(cyl((0, 0, -.32), (0, 0, -.2), .09, .15, 10), OLIVE_D)
    h.add(cyl((0, 0, .18), (0, 0, .24), .17, .17, 10), STEEL_D)
    h.add(cyl((0, 0, .235), (0, 0, .255), .13, .13, 10), LAMP_OFF)
    for s in (-1, 1): h.add(cyl((s * .14, 0, 0), (s * .2, 0, 0), .025, .025, 6), STEEL)
    h.add(tube([V(0, .14, .1), V(0, .22, 0), V(0, .14, -.12)], .018, 4), STEEL)
    h.add(box((0, -.04, -.35), (.06, .06, .06)), DARK)
    h.empty('lightpt_spotlight_tripod', V(0, 0, .27), R=np.eye(3), **LX([1, .96, .88], 800, 16, 90, kind='spot'))
    r.empty('cable_spotlight_tripod', V(0, GY, -3.13), V(0, 0, -1), kind='cable_end', note='plug end of the supply cable (lying on the ground)')
    return r

# ======================================================================= 8  VEHICLE LIGHTS
def vehicle_headlights():
    r = Node('vehicle_headlights')
    r.add(box((0, 0, -.06), (1.3, .05, .06)), STEEL_D)
    r.add(box((0, 0, -.1), (.12, .1, .06)), STEEL_D)                                      # centre mount block
    for i, s in enumerate((1, -1)):
        x = s * .55
        r.add(box((x, 0, -.06), (.1, .1, .06)), STEEL_D)
        r.add(cyl((x, 0, -.04), (x, 0, .06), .085, .085, 10), DARK_LAMP_BODY)
        r.add(cyl((x, 0, .06), (x, 0, .09), .1, .1, 10), STEEL)
        r.add(cyl((x, 0, .085), (x, 0, .105), .08, .08, 10), LAMP_OFF)
        r.empty('lightpt_vehicle_headlight_%s' % ('l' if s == 1 else 'r'), V(x, 0, .12), R=np.eye(3), **LX([1, .95, .82], 160, 40, 45, 'headlights'))
    r.empty('cable_vehicle_headlights', V(0, 0, -.14), V(0, 0, -1), kind='cable_end', note='harness entry at the centre mount')
    return r
def vehicle_taillights():
    r = Node('vehicle_taillights')
    r.add(box((0, 0, -.04), (1.3, .05, .06)), STEEL_D)
    r.add(box((0, 0, -.06), (.12, .1, .06)), STEEL_D)
    for s in (1, -1):
        x = s * .55
        r.add(box((x, 0, 0), (.2, .12, .08)), DARK_LAMP_BODY)
        r.add(box((x, .018, .042), (.17, .07, .016)), TAIL_OFF)                          # brake / tail lens
        r.add(box((x, -.04, .042), (.08, .03, .016)), LAMP_OFF)                          # reverse lamp
        n = 'l' if s == 1 else 'r'
        r.empty('lightpt_vehicle_tail_%s' % n, V(x, .018, .06), R=np.eye(3), **LX([1, .08, .05], 12, 100, 7, 'tail', kind='point'))
        r.empty('lightpt_vehicle_reverse_%s' % n, V(x, -.04, .06), R=np.eye(3), **LX([1, .97, .9], 20, 90, 9, 'reverse', kind='point'))
    r.empty('cable_vehicle_taillights', V(0, 0, -.1), V(0, 0, -1), kind='cable_end', note='harness entry at the centre mount')
    return r
def vehicle_lightbar():
    r = Node('vehicle_lightbar')
    for s in (-1, 1):
        r.add(box((s * .42, .03, 0), (.12, .06, .14)), RUBBER)
        r.add(box((s * .42, .08, 0), (.05, .06, .1)), STEEL_D)
    r.add(box((0, .12, 0), (1.12, .06, .08)), STEEL_D)                                    # rail
    r.add(box((0, .19, .0), (1.06, .09, .12)), DARK_LAMP_BODY)                              # bar body
    for i in range(6):
        x = -.45 + .18 * i
        r.add(box((x, .19, .068), (.15, .065, .018)), LAMP_OFF)
        r.empty('lightpt_vehicle_lightbar_%d' % i, V(x, .19, .082), R=np.eye(3), **LX([.95, .97, 1], 120, 24, 55, 'lightbar'))
    r.add(tube([V(.53, .17, -.04), V(.6, .1, -.1), V(.55, .05, -.3)], .012, 4), CABLE)
    r.empty('cable_vehicle_lightbar', V(.55, .05, -.3), V(0, 0, -1), kind='cable_end', note='pigtail end (12 V plug)')
    return r

def materials_ref():
    r = Node('lights_materials_ref')
    for i, m in enumerate((LAMP_ON, LAMP_OFF, GLASS_L, TAIL_ON, TAIL_OFF, IND_ON, IND_OFF)):
        r.add(box((i * .15, .04, 0), (.08, .08, .08)), m)
    return r
