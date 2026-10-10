"""Light tower, floodlight poles, wall/roof floodlights, lamp posts, string lights."""
from lights_lib import *

# colour extras the game can read from node.extras.light
def LX(col, I, cone, rng, group=None, kind='spot'):
    d = {'light': {'type': kind, 'color': col, 'I': I, 'cone_deg': cone, 'range': rng}}
    if group: d['light']['group'] = group
    return d
WARM = [1, .93, .78]; SODIUM = [1, .8, .5]; COOL = [.9, .95, 1]

# ======================================================================= 1  LIGHT TOWER
def tower_mast(ext):
    """mast assembly in its own frame: hinge at the origin, mast along +Y. Returns Node 'mast' (not a glTF node; parts+empties)."""
    n = Node('mast')
    r1, r2, r3 = .10, .082, .064
    if ext:
        n.add(cyl((0, -.15, 0), (0, 2.6, 0), r1, r1, 8), OLIVE_L)
        n.add(cyl((0, 2.54, 0), (0, 2.66, 0), r1 + .018, r1 + .018, 8), STEEL_D)
        n.add(cyl((0, 2.3, 0), (0, 5.0, 0), r2, r2, 8), GALV)
        n.add(cyl((0, 4.94, 0), (0, 5.06, 0), r2 + .016, r2 + .016, 8), STEEL_D)
        n.add(cyl((0, 4.7, 0), (0, 7.3, 0), r3, r3, 8), STEEL)
        top = 7.3
        cab = [(0, 0, 0), (0, .3, .10), (0, .6, .111), (0, 2.45, .111), (0, 2.9, .094), (0, 4.9, .094), (0, 5.3, .076), (0, 7.2, .076), (0, 7.38, 0)]
        clips = [.9, 1.9, 3.3, 4.4, 5.8, 6.7]
        rad = lambda y: r1 if y < 2.65 else (r2 if y < 5.0 else r3)
    else:
        n.add(cyl((0, -.15, 0), (0, 2.6, 0), r1, r1, 8), OLIVE_L)
        n.add(cyl((0, 2.54, 0), (0, 2.66, 0), r1 + .018, r1 + .018, 8), STEEL_D)
        top = 2.6
        cab = [(0, 0, 0), (0, .3, .10), (0, .6, .111), (0, 2.5, .111), (0, 2.68, 0)]
        clips = [.9, 1.9]
        rad = lambda y: r1
    n.add(tube([V(*p) for p in cab], .021, 5), CABLE)
    for y in clips:
        rr = rad(y); n.add(box((0, y, rr + .012), (.07, .05, .05)), STEEL_D)
        n.add(box((0, y, rr * .5 + .006), (.05, .05, rr + .03)), STEEL_D)     # strap round the tube
    # ---- lamp head (mast frame, axis +Y). junction box on the axis so the head can be turned about the mast
    yb = top + .1
    n.add(box((0, yb, 0), (.3, .22, .3)), STEEL_D)
    n.add(box((0, yb + .14, 0), (2.0, .12, .28)), STEEL)
    heads = []
    yc = yb + .14
    for side, Rs in ((1, np.eye(3)), (-1, roty(PI))):
        for x in (-.62, 0, .62):
            R = Rs @ rotx(D(22))                                  # beam tilted 22 degrees down
            c = Rs @ V(x if side == 1 else -x, 0, 0) + V(0, yc, 0) + Rs @ V(0, 0, .30)
            n.add(box(Rs @ V(x, 0, .20) + V(0, yc, 0), (.12, .12, .22)), STEEL_D)         # bracket from bar to panel
            for g, m in flood_head(.52, .36, .16, False, 0): n.add(xf(g, R, c), m)
            heads.append((c, R, side))
    return n, heads, yb

def light_tower(extended=True):
    nm = 'light_tower' if extended else 'light_tower_lowered'; sfx = 'light_tower' if extended else 'light_tower_lowered'
    r = Node(nm)
    # ---- trailer
    for s in (-1, 1):
        r.add(box((s * .7, .72, 0), (.08, .16, 3.2)), STEEL_D)          # chassis rails
    r.add(box((0, .82, 0), (1.7, .06, 3.2)), OLIVE_D)                   # deck
    for z in (-1.5, 1.5): r.add(box((0, .72, z), (1.5, .1, .1)), STEEL_D)
    r.add(cyl((-.95, .32, -.1), (.95, .32, -.1), .05, .05, 6), STEEL_D)  # axle
    for s in (-1, 1):
        r.add(box((s * .7, .52, -.1), (.08, .45, .1)), STEEL_D)         # spring hangers
        r.add(cyl((s * .79, .32, -.1), (s * 1.01, .32, -.1), .32, .32, 10), RUBBER)
        r.add(cyl((s * 1.0, .32, -.1), (s * 1.04, .32, -.1), .14, .14, 6), STEEL)
        r.add(box((s * .92, .72, -.1), (.34, .05, .9)), OLIVE)          # mudguard
    for s in (-1, 1):
        r.add(cyl((s * .5, .72, 1.5), (0, .72, 2.7), .04, .04, 6), STEEL_D)   # A-frame drawbar
    r.add(box((0, .72, 2.72), (.16, .14, .22)), STEEL_D); r.add(cyl((0, .72, 2.88), (0, .78, 2.88), .09, .09, 8), STEEL)   # coupler eye
    r.add(cyl((0, .74, 2.2), (0, .14, 2.2), .03, .03, 6), STEEL); r.add(cyl((-.03, .12, 2.2), (.03, .12, 2.2), .12, .12, 8), RUBBER)  # jockey wheel
    r.add(box((0, .74, 2.2), (.1, .06, .1)), STEEL_D); r.add(tube([V(-.215, .72, 2.2), V(.215, .72, 2.2)], .035, 6), STEEL_D)   # cross tube between the A-frame bars
    # ---- outriggers: extended (down on pads) or stowed
    for sx in (-1, 1):
        for z in (-1.15, 1.15):
            if extended:
                xe = sx * 1.5
                r.add(box((sx * 1.1, .66, z), (.8, .1, .08)), OLIVE)
                r.add(cyl((xe, .72, z), (xe, .06, z), .045, .045, 6), STEEL)
                r.add(box((xe, .03, z), (.32, .05, .32)), STEEL_D)
            else:
                xe = sx * .96
                r.add(box((sx * .84, .66, z), (.34, .1, .08)), OLIVE)
                r.add(cyl((xe, .72, z), (xe, .42, z), .045, .045, 6), STEEL)
                r.add(box((xe, .4, z), (.22, .05, .22)), STEEL_D)
    # ---- generator set (enclosure, vents, exhaust, panels), fuel tank, cradle
    r.add(box((0, 1.275, -.2), (1.44, .85, 1.6)), OLIVE)                # enclosure x +-.72, y .85..1.70, z -1.0..0.6
    r.add(box((0, 1.71, -.2), (1.5, .04, 1.66)), OLIVE_D)               # roof lid
    for s in (-1, 1):
        for i in range(3): r.add(box((s * .73, 1.05 + i * .12, -.3), (.03, .06, .55)), BLACK)    # louvres
        r.add(box((s * .725, 1.28, .2), (.02, .75, .02)), BLACK)       # door seam
    r.add(box((0, 1.28, .6), (1.2, .7, .02)), OLIVE_D)                  # front access door
    r.add(box((0, 1.2, -1.03), (.5, .4, .08)), DARK)                    # control panel (rear face)
    r.add(box((-.12, 1.28, -1.075), (.14, .08, .02)), STEEL_D)
    r.add(box((.1, 1.3, -1.075), (.05, .05, .03)), IND_OFF_REF)
    r.add(box((.1, 1.14, -1.075), (.2, .08, .03)), STEEL_D)
    r.add(box((.74, 1.1, .3), (.06, .3, .34)), DARK)                    # side connector plate
    for z in (.2, .4): r.add(cyl((.77, 1.1, z), (.82, 1.1, z), .04, .04, 6), CABLE_Y)
    r.add(cyl((-.5, 1.78, .1), (-.5, 1.78, .5), .1, .1, 8), STEEL_D)   # muffler
    r.add(cyl((-.5, 1.8, .45), (-.5, 2.4, .45), .04, .04, 6), STEEL_D)  # exhaust stack
    r.add(cyl((-.5, 2.38, .45), (-.5, 2.47, .45), .03, .08, 6), STEEL)  # rain cap
    r.add(box((0, 1.06, 1.0), (1.2, .42, .7)), OLIVE_L)                 # fuel tank, y .85..1.27, z .65..1.35
    r.add(cyl((.35, 1.26, .85), (.35, 1.34, .85), .06, .06, 6), STEEL)  # filler cap
    r.add(box((-.4, 1.1, 1.355), (.14, .12, .03)), YELLOW)              # fuel gauge plate
    r.add(box((0, 1.5, .9), (.14, .5, .1)), STEEL_D); r.add(box((0, 1.735, .9), (.3, .06, .16)), STEEL_D)   # mast cradle
    # ---- mast pedestal (two cheek plates + hinge pin) and mast
    hy, hz = 1.85, -1.3
    for s in (-1, 1): r.add(box((s * .14, 1.35, hz), (.06, 1.0, .3)), STEEL_D)
    r.add(box((0, 1.0, hz), (.34, .3, .34)), STEEL_D)
    r.add(cyl((-.17, hy, hz), (.17, hy, hz), .035, .035, 6), STEEL)
    # pigtail from the control panel to the hinge point (buried inside the mast base)
    r.add(tube([V(0, 1.15, -1.07), V(0, 1.3, -1.19), V(0, 1.62, -1.26), V(0, hy, hz)], .021, 5), CABLE)
    mast, heads, yb = tower_mast(extended)
    Rm = np.eye(3) if extended else rotx(D(90))
    for g, m in mast.parts: r.add(xf(g, Rm, (0, hy, hz)), m)
    # lamp-head emitters
    if extended:
        for i, (c, R, side) in enumerate(heads):
            grp = 'front' if side == 1 else 'back'
            r.empty('lightpt_light_tower_%d' % i, V(0, hy, hz) + Rm @ (c + R @ V(0, 0, .12)), R=Rm @ R, **LX(WARM, 370, 62, 58, grp))
    r.empty('cable_%s_genset' % sfx, V(0, 1.2, -1.1), V(0, 0, -1), kind='cable_end', note='generator control panel (rear), internal cable leaves here')
    r.empty('cable_%s_ext' % sfx, V(.83, 1.1, .3), V(1, 0, 0), kind='cable_end', note='external feed socket on the +X side of the enclosure')
    r.empty('cable_%s_head' % sfx, V(0, hy, hz) + Rm @ V(0, yb, 0), V(0, 0, 1), R=Rm, kind='cable_end', note='cable gland on the lamp head junction box')
    r.empty('pivot_%s_mast_hinge' % sfx, (0, hy, hz), V(0, 1, 0), kind='pivot', note='mast hinge axis (X). node pose is fixed in this file; the lowered pose is a separate root')
    return r
IND_OFF_REF = IND_OFF

# ======================================================================= 2  FLOODLIGHT POLE
def floodlight_pole(nl=2):
    H = 8.0 if nl == 2 else 10.0
    r = Node('floodlight_pole_%d' % nl)
    r.add(cyl((0, 0, 0), (0, .55, 0), .34, .3, 10), CONC)               # concrete pier
    r.add(box((0, .58, 0), (.46, .06, .46)), STEEL_D)                    # base plate
    for sx in (-1, 1):
        for sz in (-1, 1): r.add(cyl((sx * .17, .58, sz * .17), (sx * .17, .68, sz * .17), .018, .018, 4), STEEL)   # anchor bolts
    r0, r1 = .115, .065
    rad = lambda y: r0 + (r1 - r0) * (y - .6) / (H - .6)
    r.add(cyl((0, .6, 0), (0, H, 0), r0, r1, 10), GALV)                  # steel pole
    r.add(cyl((0, .6, 0), (0, 1.0, 0), r0 + .03, r0 + .02, 10), STEEL_D)  # base shroud
    # junction box + conduit
    jy = 1.7
    r.add(box((0, jy, rad(jy) + .06), (.26, .34, .14)), STEEL_D)
    r.add(box((0, jy, rad(jy) - .01), (.2, .26, .1)), STEEL_D)
    r.add(box((0, jy + .06, rad(jy) + .14), (.05, .05, .02)), YELLOW)
    r.add(tube([V(0, jy - .17, rad(jy) + .06), V(0, .62, rad(.62) + .02), V(0, .55, .1)], .022, 5), CABLE)     # conduit down into the pier
    c0, c1 = V(0, jy + .17, rad(jy) + .06), V(0, H - .12, rad(H - .12) + .018)
    r.add(tube([c0, c1], .022, 5), STEEL_D)                              # conduit up
    for y in (3.4, 5.6, 7.3):
        rr = rad(y); r.add(cyl((0, y - .03, 0), (0, y + .03, 0), rr + .025, rr + .025, 8), STEEL_D)
        r.add(box((0, y, rr + .018), (.06, .06, .05)), STEEL_D)
    # collar + cross-arm
    r.add(cyl((0, H - .35, 0), (0, H + .05, 0), r1 + .035, r1 + .03, 8), STEEL_D)
    L = 2.0 if nl == 2 else 3.0
    r.add(box((0, H + .05, 0), (L, .1, .12)), STEEL)
    r.add(box((0, H + .0, rad(H) + .05), (.2, .2, .08)), STEEL_D)
    r.add(box((0, H - .02, rad(H) + .075), (.24, .16, .07)), STEEL_D)    # arm junction box
    xs = [-.7, .7] if nl == 2 else [-1.15, -.4, .4, 1.15]
    for i, x in enumerate(xs):
        yaw = D(-8 if x < 0 else 8) if nl == 4 else 0
        R = roty(yaw) @ rotx(D(28))
        c = V(x, H + .3, .16)
        r.add(box((x, H + .16, .02), (.12, .26, .12)), STEEL_D)          # lamp stem from arm up to the housing
        r.add(box((x, H + .16, .1), (.16, .1, .14)), STEEL_D)
        for g, m in flood_head(.54, .38, .24, True, 1): r.add(xf(g, R, c), m)
        r.empty('lightpt_floodlight_pole_%d_%d' % (nl, i), c + R @ V(0, 0, .18), R=R, **LX(WARM, 700 if nl == 2 else 560, 72, 44 if nl == 2 else 52))
    r.empty('cable_floodlight_pole_%d_feed' % nl, V(0, .2, .45), V(0, 0, 1), kind='cable_end', note='ground feed enters the pier on the +Z side')
    return r

# ======================================================================= 3  WALL / ROOF FLOODLIGHTS
def floodlight_wall():
    r = Node('floodlight_wall')
    r.add(box((0, 0, .015), (.2, .34, .03)), STEEL_D)                    # wall plate (back at z=0)
    for sx in (-1, 1):
        for sy in (-1, 1): r.add(cyl((sx * .07, sy * .13, .03), (sx * .07, sy * .13, .05), .018, .018, 5), STEEL)
    r.add(box((0, .04, .26), (.07, .07, .5)), STEEL)                     # arm
    r.add(tube([V(0, -.14, .03), V(0, .0, .3)], .022, 5), STEEL_D)       # diagonal brace
    R = rotx(D(20)); c = V(0, -.1, .56)
    r.add(box((0, -.0, .56), (.1, .16, .1)), STEEL_D)                    # knuckle block
    for g, m in flood_head(.46, .32, .2, True, 1): r.add(xf(g, R, c), m)
    r.add(tube([V(0, .02, .1), V(0, .05, .0)], .016, 4), CABLE)
    r.empty('lightpt_floodlight_wall', c + R @ V(0, 0, .16), R=R, **LX(WARM, 560, 80, 36))
    r.empty('cable_floodlight_wall', V(0, .17, .02), V(0, 1, 0), kind='cable_end', note='conduit entry at the top of the wall plate')
    return r
def floodlight_roof():
    r = Node('floodlight_roof')
    r.add(box((0, .025, 0), (.6, .05, .6)), STEEL_D)
    for sx in (-1, 1):
        for sz in (-1, 1): r.add(cyl((sx * .24, .05, sz * .24), (sx * .24, .1, sz * .24), .022, .022, 5), STEEL)
    r.add(cyl((0, .0, 0), (0, 1.0, 0), .05, .05, 8), GALV)               # stand pole
    for sz in (-1, 1): r.add(tube([V(0, .6, 0), V(0, .05, sz * .24)], .02, 5), STEEL_D)   # two legs bracing the pole
    r.add(box((0, .96, 0), (.14, .1, .14)), STEEL_D)
    R = rotx(D(24)); c = V(0, 1.2, .14)
    r.add(box((0, 1.08, .06), (.12, .26, .12)), STEEL_D)
    for g, m in flood_head(.5, .34, .22, True, 1): r.add(xf(g, R, c), m)
    r.empty('lightpt_floodlight_roof', c + R @ V(0, 0, .17), R=R, **LX(WARM, 620, 75, 40))
    r.empty('cable_floodlight_roof', V(0, .06, -.2), V(0, 0, -1), kind='cable_end', note='cable enters at the base plate edge (-Z)')
    return r

# ======================================================================= 4  LAMP POSTS
def lamp_cobra():
    r = Node('lamp_cobra')
    r.add(cyl((0, 0, 0), (0, .06, 0), .22, .22, 8), CONC)
    r.add(cyl((0, .0, 0), (0, .95, 0), .17, .13, 8), GALV)                # base shaft
    r.add(box((0, .45, .13), (.2, .45, .05)), STEEL_D)                    # service door
    r.add(cyl((0, .9, 0), (0, 6.7, 0), .095, .058, 8), GALV)              # pole
    arm = [V(0, 6.2, 0), V(.05, 6.75, 0), V(.45, 7.1, 0), V(1.0, 7.2, 0), V(1.5, 7.2, 0)]
    r.add(tube(arm, .04, 6), GALV)
    r.add(cyl((0, 6.15, 0), (0, 6.35, 0), .105, .105, 8), STEEL_D)        # arm collar
    # cobra-head: tapered luminaire 1.3..2.0 m out
    P = []
    for a, (xx, ww, hh) in enumerate(((1.3, .32, .2), (2.0, .2, .13))):
        for b in (-1, 1):
            for d in (-1, 1): P.append((xx, 7.15 + b * hh / 2, d * ww / 2))
    r.add(hexa(P), DARK_LAMP_BODY)
    r.add(box((1.66, 7.15 - .105, 0), (.52, .03, .2)), LAMP_OFF)         # lens underneath
    r.add(box((1.66, 7.22, 0), (.5, .04, .1)), STEEL_D)
    r.empty('lightpt_lamp_cobra', V(1.66, 7.02, 0), R=rotx(D(90)), **LX(SODIUM, 190, 110, 27, kind='spot'))
    r.empty('cable_lamp_cobra', V(0, .35, .16), V(0, 0, 1), kind='cable_end', note='ground feed enters the service door of the base')
    return r

def lamp_harbour():
    r = Node('lamp_harbour')
    r.add(cyl((0, 0, 0), (0, .12, 0), .26, .24, 8), CONC)
    r.add(cyl((0, .12, 0), (0, .55, 0), .2, .12, 8), GREEN_P)              # fluted foot
    r.add(cyl((0, .5, 0), (0, .66, 0), .15, .15, 8), BRASS)
    r.add(cyl((0, .6, 0), (0, 3.5, 0), .07, .052, 8), GREEN_P)              # post
    r.add(cyl((0, 1.5, 0), (0, 1.6, 0), .09, .09, 8), BRASS)
    r.add(cyl((0, 3.1, 0), (0, 3.2, 0), .085, .085, 8), BRASS)
    # scroll arm with a banner hook
    r.add(tube([V(0, 2.55, 0), V(.2, 2.8, 0), V(.55, 2.88, 0), V(.62, 2.7, 0)], .022, 5), GREEN_P)
    r.add(box((0, 2.52, 0), (.12, .08, .12)), BRASS)
    # lantern
    r.add(cyl((0, 3.46, 0), (0, 3.6, 0), .13, .2, 6), GREEN_P)             # bottom cap
    r.add(cyl((0, 3.58, 0), (0, 3.98, 0), .19, .19, 6), LAMP_OFF)           # glass body (emissive when on)
    for k in range(6):
        a = PI / 6 + k * PI / 3 + PI / 6
        r.add(box((.2 * math.cos(a), 3.78, .2 * math.sin(a)), (.03, .44, .03), roty(-a)), GREEN_P)   # ribs
    r.add(cyl((0, 3.96, 0), (0, 4.02, 0), .23, .23, 6), GREEN_P)           # roof rim
    r.add(cyl((0, 4.0, 0), (0, 4.24, 0), .23, .03, 6), GREEN_P)            # roof
    r.add(ell((0, 4.3, 0), (.05, .06, .05), 6, 3), BRASS)                  # finial
    r.empty('lightpt_lamp_harbour', V(0, 3.78, 0), R=rotx(D(90)), **LX([1, .82, .52], 150, 160, 22, kind='point'))
    r.empty('cable_lamp_harbour', V(0, .3, -.2), V(0, 0, -1), kind='cable_end', note='ground feed enters the foot on the -Z side')
    return r

def lamp_bollard():
    r = Node('lamp_bollard')
    r.add(box((0, .02, 0), (.36, .04, .36)), CONC)
    r.add(cyl((0, .0, 0), (0, .62, 0), .1, .1, 8), GALV)
    r.add(cyl((0, .55, 0), (0, .74, 0), .105, .105, 8), LAMP_OFF)           # light band
    for k in range(4):
        a = k * PI / 2 + PI / 4; r.add(box((.1 * math.cos(a), .645, .1 * math.sin(a)), (.025, .2, .025), roty(-a)), STEEL_D)
    r.add(cyl((0, .73, 0), (0, .8, 0), .118, .118, 8), STEEL_D)
    r.add(dome((0, .8, 0), (.118, .06, .118), 8, 2), STEEL)
    r.empty('lightpt_lamp_bollard', V(0, .62, 0), R=rotx(D(90)), **LX(SODIUM, 60, 150, 9, kind='point'))
    r.empty('cable_lamp_bollard', V(0, .04, -.18), V(0, 0, -1), kind='cable_end', note='ground feed under the base plate edge')
    return r

# ======================================================================= 5  STRING LIGHTS
def string_lights_span(L=8.0, nb=13, sag=.5, y=2.6, name='string_lights_span_8m'):
    r = Node(name)
    a, b = V(-L / 2, y, 0), V(L / 2, y, 0)
    parts, bulbs, cp = string_span(a, b, nb, sag)
    for g, m in parts: r.add(g, m)
    for s, p in ((-1, a), (1, b)):
        r.add(cyl(p + V(s * .05, .0, 0), p + V(s * .05, .06, 0), .035, .035, 6), STEEL_D)     # eye hook
        r.add(box(p + V(s * .06, 0, 0), (.06, .06, .06)), STEEL_D)
    for i, p in enumerate(bulbs):
        r.empty('lightpt_%s_%02d' % (name, i), p, V(0, -1, 0), **LX([1, .82, .5], 6, 160, 5, kind='point'))
    r.empty('cable_%s_a' % name, a + V(-.06, 0, 0), V(-1, 0, 0), kind='cable_end', note='attachment end A (x = -L/2)')
    r.empty('cable_%s_b' % name, b + V(.06, 0, 0), V(1, 0, 0), kind='cable_end', note='attachment end B (x = +L/2)')
    return r
def string_lights_8m():
    r = string_lights_span(8.0, 13, .5, 2.6, 'string_lights_8m')
    for s in (-1, 1):
        x = s * 4.0 + s * .06 + s * .0
        r.add(cyl((x, 0, 0), (x, 2.68, 0), .06, .045, 8), WOOD)
        r.add(cyl((x, 0, 0), (x, .06, 0), .16, .16, 8), CONC_D)
        r.add(tube([V(x, 1.9, 0), V(x - s * .2, 2.1, 0)], .014, 4), STEEL_D)
    return r
