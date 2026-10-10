"""
presets.py - the catalogue of fire types (physical size, sim settings, render look, lifecycle kind).

Importing this module registers every extra type into sim.PRESETS.

Most types are SCALED COPIES of the five hand-tuned base presets (campfire, gas, pool, vehicle, building)
defined in sim.py: `scaled(base, r)` multiplies the cell size dx and the vent geometry by r and the vent
speed by sqrt(r) (Froude-like), so the per-cell behaviour that was tuned by eye carries over while the real
size changes. Sizes below are in metres (the domain is grid * dx, see `domain_m`).

kind:  'life'  full lifecycle (ignite, growth, loop variants, decay, extinguished by water)
       'tile'  periodic-in-x front segment (loops only)
       'shot'  one-shot clip(s) (lick)
"""
import sim as S

PRESETS = S.PRESETS


def scaled(base, r, vents=None, **kw):
    p = dict(PRESETS[base])
    p["dx"] = p["dx"] * r
    p["w_src"] = p["w_src"] * (r ** 0.5)
    if vents is None:
        vents = [(v[0] * r, v[1] * r, v[2] * r, v[3] * r, v[4] * r) + tuple(v[5:]) for v in p["vents"]]
    p["vents"] = vents
    p.update(kw)
    return p


# --- hand-tuned look parameters (see bake.py header) ---------------------------------------
LOOK = {
    "campfire": dict(cs=4.5, ka=0.10, cb=0.15, co=1.0, expo=1.5, scroll=3, warp=1.6, noise=0.45, smoke_k=0.9, smoke_albedo=0.40, smoke_pv=0.2),
    "gas": dict(cs=4.5, ka=0.10, cb=0.5, co=0.6, expo=1.7, scroll=4, warp=1.0, noise=0.30, smoke_k=0.5, smoke_albedo=0.35, smoke_pv=0.0),
    "pool": dict(cs=4.5, ka=0.09, cb=0.2, co=0.8, expo=1.8, scroll=1, warp=1.6, noise=0.55, smoke_k=0.7, smoke_albedo=0.06, smoke_pv=0.0),
    "vehicle": dict(cs=4.5, ka=0.09, cb=0.2, co=0.8, expo=1.8, scroll=1, warp=1.8, noise=0.55, smoke_k=0.7, smoke_albedo=0.08, smoke_pv=0.0),
    "building": dict(cs=4.5, ka=0.09, cb=0.2, co=0.8, expo=1.8, scroll=1, warp=1.8, noise=0.55, smoke_k=0.55, smoke_albedo=0.14, smoke_pv=0.0),
}
META = {}   # name -> dict(kind, title, size_note, flame(bool), variants)


def add(name, base, p, look=None, kind="life", title=None, size_note="", flame=True, haze=0.5, haze_shape="default", **meta):
    PRESETS[name] = p
    lk = dict(LOOK[base] if base in LOOK else LOOK["campfire"])
    lk.update(look or {})
    LOOK[name] = lk
    META[name] = dict(kind=kind, title=title or name, size_note=size_note, flame=flame, haze=haze, haze_shape=haze_shape, **meta)


for _n, _t, _s in (("campfire", "Campfire", "flames 0.5 to 0.9 m"), ("gas", "Gas burner flame", "flame 0.5 to 0.7 m"),
                   ("pool", "Fuel pool / burning oil", "pool 2 to 3 m wide, flames 3 m"),
                   ("vehicle", "Vehicle, fully engulfed", "car or truck, 4 to 5 m"),
                   ("building", "Building fire", "9 m wide, flames 8 to 12 m")):
    META[_n] = dict(kind="life", title=_t, size_note=_s, flame=True)
META["campfire"].update(haze=0.45, haze_shape="default")
META["gas"].update(haze=0.4, haze_shape="default")
META["pool"].update(haze=1.0, haze_shape="tall")
META["vehicle"].update(haze=0.9, haze_shape="tall")
META["building"].update(haze=1.0, haze_shape="tall")
# fuel / vehicle fires: heavy black smoke (high soot yield, flare-up puffs, slow cooling so the hot plume rolls and widens)
PRESETS["pool"].update(soot_k=9.0, soot_ox=1.0, mixc=0.8, puff_every=1.6, puff_soot=0.18)
PRESETS["vehicle"].update(soot_k=8.0, soot_ox=1.1, mixc=0.8, puff_every=1.4, puff_soot=0.16)
PRESETS["building"].update(soot_k=6.0, mixc=0.9, puff_every=2.5, puff_soot=0.10)
LOOK["pool"].update(smoke_k=1.1, smoke_albedo=0.045, smoke_glow=0.9, cb=0.05)
LOOK["vehicle"].update(smoke_k=1.1, smoke_albedo=0.05, smoke_glow=0.9, cb=0.05)
LOOK["building"].update(smoke_k=0.8, smoke_albedo=0.10, smoke_glow=0.5, cb=0.04)
LOOK["campfire"].update(smoke_glow=0.35)

# --------------------------------- small flames --------------------------------------------
add("barrel", "campfire", scaled("campfire", 1.15, vents=[(0, 0, 0.20, 0.20, 0.10, 1.0, 0.5), (0.06, 0.04, 0.12, 0.12, 0.15, 0.6, 0.8)],
                                 F_src=0.5, w_src=0.45, soot_k=12.0, warm=3.5),
    look=dict(smoke_albedo=0.14, smoke_k=1.0), title="Barrel fire", size_note="0.6 m drum, flames 1 to 1.4 m")
add("torch", "campfire", scaled("campfire", 0.55, vents=[(0, 0, 0.045, 0.045, 0.05, 1.0, 0.5)], F_src=0.4, w_src=0.35, warm=2.5),
    look=dict(smoke_k=0.4), title="Torch", size_note="flame 0.35 to 0.5 m")
add("flare", "campfire", scaled("campfire", 0.5, vents=[(0, 0, 0.03, 0.03, 0.04, 1.0, 0.4)], F_src=0.5, O_src=0.25, w_src=0.9, soot_k=3.0,
                                theta_ad=0.9, warm=2.2),
    look=dict(tint=(1.0, 0.45, 0.42), cs=5.5, smoke_k=0.5, smoke_albedo=0.7), title="Road flare", size_note="flame 0.25 to 0.4 m")
add("debris", "campfire", scaled("campfire", 1.3, vents=[(-0.35, 0.1, 0.13, 0.12, 0.05, 0.8, 1.0), (0.25, -0.15, 0.15, 0.12, 0.05, 1.0, 1.0),
                                                         (0.0, 0.3, 0.1, 0.1, 0.05, 0.55, 1.0), (0.4, 0.3, 0.1, 0.1, 0.05, 0.5, 1.0)],
                                 F_src=0.24, w_src=0.28, soot_k=11.0, warm=3.5),
    look=dict(smoke_albedo=0.22, smoke_k=1.0), title="Burning debris", size_note="pile 1 m, flames 0.4 to 0.9 m")
add("gas_jet", "gas", scaled("gas", 1.2, grid=(20, 20, 48), vents=[(0, 0, 0.035, 0.035, 0.03, 1.0, 0.15)], F_src=0.3, O_src=0.55, w_src=4.5,
                             src_rate=40.0, soot_k=3.0, warm=2.2),
    look=dict(cb=0.8, expo=1.6, smoke_k=0.25), title="Gas jet / burner", size_note="jet flame 0.9 to 1.2 m")

# --------------------------------- vegetation ----------------------------------------------
add("shrub", "campfire", scaled("campfire", 2.4, vents=[(-0.3, 0, 0.3, 0.3, 0.15, 1.0, 1.0), (0.35, 0.1, 0.28, 0.28, 0.45, 0.8, 1.0),
                                                       (0.0, -0.1, 0.25, 0.25, 0.85, 0.6, 1.0)], F_src=0.36, w_src=0.5, turb=0.9, soot_k=10.0, warm=4.0),
    look=dict(noise=0.55, smoke_albedo=0.3, smoke_k=1.0, warp=2.0), title="Shrub fire", size_note="shrub 2 m, flames 1.5 to 2.5 m")
add("grass", "campfire", scaled("campfire", 2.0, grid=(32, 24, 32), vents=[(-0.6, 0, 0.35, 0.3, 0.04, 0.9, 1.0), (0.0, 0.05, 0.38, 0.3, 0.04, 1.0, 1.0),
                                                                          (0.6, -0.05, 0.35, 0.3, 0.04, 0.8, 1.0)],
                                F_src=0.22, w_src=0.3, turb=0.9, soot_k=7.0, delay=(0.03, 0.12), warm=3.0),
    look=dict(smoke_albedo=0.35, smoke_k=0.8, noise=0.6, warp=2.0), title="Grass / brush fire patch", size_note="patch 2 m wide, flames 0.4 to 1.2 m")
add("spot_fire", "campfire", scaled("campfire", 1.0, grid=(24, 20, 32), vents=[(0, 0, 0.14, 0.14, 0.05, 1.0, 1.0), (0.1, 0.05, 0.08, 0.08, 0.05, 0.5, 1.0)],
                                    F_src=0.22, w_src=0.28, soot_k=8.0, warm=2.8),
    look=dict(smoke_albedo=0.35, smoke_k=0.7), title="Spot fire (ember landing)", size_note="small, flames 0.3 to 0.6 m")
add("tree_crown", "building", scaled("building", 1.3, vents=[(-1.5, 0, 1.1, 1.1, 3.2, 0.9, 1.0), (1.4, 0.2, 1.2, 1.0, 3.6, 1.0, 1.0), (0, -0.3, 1.2, 1.2, 5.0, 0.8, 1.0),
                                                            (-0.8, 0.5, 0.9, 0.9, 6.2, 0.6, 1.0), (1.0, -0.5, 0.9, 0.9, 6.8, 0.5, 1.0)], F_src=0.9, soot_k=4.5, warm=10.0),
    look=dict(smoke_albedo=0.2, smoke_k=0.45), title="Crown fire (tree)", size_note="tree 8 to 12 m, flames 6 to 12 m")
add("tree_trunk", "building", scaled("building", 0.5, grid=(24, 24, 48), vents=[(0, 0, 0.28, 0.28, 0.3, 0.9, 1.0), (0, 0, 0.26, 0.26, 1.3, 0.7, 1.0),
                                                                              (0, 0, 0.24, 0.24, 2.3, 0.6, 1.0), (0, 0, 0.22, 0.22, 3.2, 0.5, 1.0)],
                                     F_src=0.7, warm=7.0),
    look=dict(smoke_albedo=0.2, smoke_k=0.6), title="Bare trunk fire", size_note="trunk 4 to 5 m, flames up the trunk")

# --------------------------------- fuel on the ground, boats --------------------------------
add("oil_slick", "pool", scaled("pool", 1.0, grid=(40, 24, 40), vents=[(0, 0, 1.5, 0.8, 0.05, 1.0, 0.7), (1.5, 0.1, 0.6, 0.5, 0.05, 0.6, 0.9),
                                                                      (-1.6, -0.2, 0.7, 0.5, 0.05, 0.7, 0.9)], F_src=0.7, w_src=2.0, warm=6.0),
    look=dict(smoke_k=0.8), title="Oil slick / ground fuel fire", size_note="slick 4 m wide, flames 2 to 3.5 m")
add("boat_deck", "pool", scaled("pool", 1.15, grid=(40, 20, 40), vents=[(-0.8, 0, 2.0, 0.7, 0.1, 1.0, 0.8), (1.9, 0, 0.9, 0.6, 0.8, 0.7, 1.0)],
                                F_src=0.7, w_src=2.1, soot_k=7.0, warm=6.0),
    look=dict(smoke_k=0.75, smoke_albedo=0.05), title="Boat deck fire", size_note="deck fire 5 m, flames 3 to 4 m")
add("smoke_column", "pool", scaled("pool", 1.14, grid=(28, 28, 56), vents=[(0, 0, 0.5, 0.5, 0.05, 1.0, 0.6)], F_src=0.5, w_src=2.0, soot_k=14.0, warm=7.0),
    look=dict(smoke_k=0.9, smoke_albedo=0.04), kind="life", flame=False, title="Heavy black smoke column", size_note="column 7 m tall, smoke only")

# --------------------------------- vehicles and buildings -----------------------------------
add("vehicle_engine", "vehicle", scaled("vehicle", 0.5, vents=[(0, 0, 0.3, 0.35, 0.25, 1.0, 1.0)], F_src=0.75, warm=4.5),
    look=dict(smoke_k=0.8), title="Vehicle, engine bay fire", size_note="engine bay, flames 1 to 1.5 m")
add("vehicle_small", "vehicle", scaled("vehicle", 0.7, vents=[(-0.7, 0, 0.35, 0.4, 0.3, 0.9, 1.0), (0.3, 0, 0.35, 0.35, 0.35, 0.5, 1.0)], F_src=0.8, warm=5.5),
    title="Vehicle, hood and cabin fire", size_note="small car, flames 1.5 to 2.5 m")
add("roof", "building", scaled("building", 1.43, grid=(40, 24, 40), vents=[(-5, 0, 0.9, 0.9, 2.6, 0.8, 1.0), (-3, 0, 0.9, 0.9, 3.0, 1.0, 1.0), (-1, 0, 0.9, 0.9, 3.4, 0.9, 1.0),
                                                                          (1, 0, 0.9, 0.9, 3.4, 1.0, 1.0), (3, 0, 0.9, 0.9, 3.0, 0.9, 1.0), (5, 0, 0.9, 0.9, 2.6, 0.7, 1.0)],
                                F_src=0.85, warm=9.0),
    look=dict(smoke_k=0.45), title="Roof fire", size_note="12 m roof, flames 6 to 10 m")
add("window", "building", scaled("building", 0.45, vents=[(0, 0, 0.55, 0.2, 0.7, 1.0, 1.0), (0, 0, 0.5, 0.2, 1.6, 0.5, 1.0)], F_src=0.8, warm=5.0),
    title="Window flames", size_note="window 1.2 m, flames 2.5 to 4 m")
add("doorway", "building", scaled("building", 0.45, vents=[(0, 0, 0.4, 0.25, 0.15, 1.0, 1.0), (0, 0, 0.4, 0.25, 0.8, 0.7, 1.0), (0, 0, 0.4, 0.25, 1.5, 0.5, 1.0)],
                                  F_src=0.8, warm=5.0),
    title="Doorway flames", size_note="door 1 m, flames 3 to 4 m")

# --------------------------------- spreading front tiles (periodic in x) ---------------------
_tile = dict(grid=(32, 16, 32), periodic=True, turb=1.0, delay=(0.03, 0.12), warm=3.0)
add("front_lead", "campfire", scaled("campfire", 1.9, vents=[(0, 0.0, 0.1, 0.35, 0.03, 1.0, 1.0, "line"), (0, 0.22, 0.1, 0.25, 0.03, 0.6, 1.0, "line")],
                                     F_src=0.34, w_src=0.55, soot_k=8.0, **_tile),
    look=dict(smoke_albedo=0.35, smoke_k=0.7, noise=0.6, warp=1.6), kind="tile", title="Fire front, leading edge", size_note="2 m wide tile, flames 0.8 to 1.5 m")
add("front_body", "campfire", scaled("campfire", 1.9, vents=[(0, 0.0, 0.1, 0.35, 0.03, 1.0, 1.0, "line"), (0, 0.22, 0.1, 0.25, 0.03, 0.5, 1.0, "line")],
                                     F_src=0.26, w_src=0.42, soot_k=8.0, **_tile),
    look=dict(smoke_albedo=0.33, smoke_k=0.75, noise=0.6, warp=1.6), kind="tile", title="Fire front, body", size_note="2 m wide tile, flames 0.5 to 1.0 m")
add("front_trail", "campfire", scaled("campfire", 1.9, vents=[(0, 0.0, 0.1, 0.35, 0.03, 0.8, 1.0, "line")],
                                      F_src=0.12, w_src=0.25, soot_k=12.0, **_tile),
    look=dict(smoke_albedo=0.28, smoke_k=1.0, noise=0.6, warp=1.6, cs=3.5), kind="tile", title="Fire front, trailing edge", size_note="2 m wide tile, low flames, smoke")
add("lick", "campfire", scaled("campfire", 1.5, grid=(20, 16, 28), vents=[(0, 0, 0.1, 0.1, 0.03, 1.0, 0.0)], F_src=0.3, w_src=0.4, soot_k=8.0, warm=0.5),
    look=dict(smoke_k=0.3), kind="shot", title="Flame lick (leading-edge pop-up)", size_note="0.5 to 0.9 m, about 0.8 s")


# --------------------------------- explosions (kind 'blast') -----------------------------------
def _blast(name, title, note, dxm, grid, blast, resid_vents, look=None, **kw):
    r = dxm / PRESETS["pool"]["dx"]
    opts = dict(F_src=0.5, w_src=1.5, soot_k=11.0, mixc=0.7, warm=0.0)
    opts.update(kw)
    p = scaled("pool", r, grid=grid, vents=resid_vents, blast=blast, **opts)
    lk = dict(smoke_k=1.0, smoke_albedo=0.05, smoke_glow=1.0, expo=1.5, noise=0.5)
    lk.update(look or {})
    add(name, "pool", p, look=lk, kind="blast", title=title, size_note=note, haze=1.0, haze_shape="tall")


_blast("blast_small", "Explosion, small fireball", "fireball about 3 m", 0.2, (32, 32, 48),
       dict(R0=0.25, R1=1.5, tx=0.25, dur=0.5, z=0.9, F=0.9, th=1.1, S=0.45, zs=1.0, kick=0.5),
       [(0, 0, 0.5, 0.5, 0.05, 1.0, 1.0)])
_blast("blast_medium", "Explosion, medium fireball", "fireball about 8 m", 0.5, (32, 32, 48),
       dict(R0=0.5, R1=4.0, tx=0.45, dur=0.8, z=2.2, F=0.9, th=1.1, S=0.45, zs=1.0, kick=0.5),
       [(0, 0, 1.2, 1.2, 0.1, 1.0, 1.0)])
_blast("blast_large", "Explosion, large fireball", "fireball about 20 m", 1.25, (32, 32, 48),
       dict(R0=1.0, R1=10.0, tx=0.9, dur=1.5, z=5.5, F=0.9, th=1.1, S=0.45, zs=1.0, kick=0.5),
       [(0, 0, 3.0, 3.0, 0.2, 1.0, 1.0)])
_blast("blast_fuel", "Explosion, rolling fuel fireball", "rolling fireball about 12 m, heavy black smoke", 0.6, (32, 32, 48),
       dict(R0=0.8, R1=6.0, tx=1.0, dur=1.8, z=3.5, F=1.0, th=0.95, S=0.7, zs=1.0, kick=0.4),
       [(0, 0, 2.0, 2.0, 0.1, 1.0, 1.0)], soot_k=16.0, look=dict(smoke_albedo=0.035))
_blast("blast_ground", "Explosion, ground-hugging burst", "burst 12 m wide, 4 m tall", 0.5, (40, 32, 32),
       dict(R0=0.6, R1=6.0, tx=0.5, dur=1.0, z=1.0, F=0.9, th=1.05, S=0.5, zs=0.35, kick=0.6),
       [(0, 0, 1.5, 1.5, 0.1, 1.0, 1.0)])


# --------------------------------- carried flames (kind 'carried'): the fire as seen from the moving object -----
def _carried(name, title, note, wind, vents, delay, **kw):
    # soot needs a residence time; in a fast wind the fuel travels metres in that time, so the delay shrinks with speed
    p = scaled("campfire", 1.0, grid=(48, 16, 24), vents=vents, wind=wind, F_src=1.0, w_src=1.6, soot_k=9.0, turb=1.1, src_rate=60.0,
               delay=delay, warm=1.8, **kw)
    p["dx"] = 0.06
    add(name, "campfire", p, look=dict(noise=0.55, warp=1.2, smoke_k=0.5, smoke_albedo=0.15, smoke_glow=0.3, expo=1.6), kind="carried", title=title, size_note=note,
        haze=0.3, haze_shape="default")


_HEAD = [(-1.0, 0.0, 0.12, 0.12, 0.55, 1.0, 1.0), (-1.0, 0.0, 0.07, 0.07, 0.55, 0.7, 0.6)]
_carried("debris_slow", "Flaming debris, slow tumbling", "object speed about 4 m/s", 4.0, _HEAD, (0.02, 0.08))
_carried("debris_med", "Flaming debris, medium speed", "object speed about 12 m/s", 12.0, _HEAD, (0.008, 0.03))
_carried("debris_fast", "Flaming debris, fast", "object speed about 30 m/s", 30.0, _HEAD, (0.004, 0.012))
add("trail_tile", "campfire", dict(scaled("campfire", 1.9, grid=(32, 12, 16), vents=[(0, 0, 0.1, 0.25, 0.3, 1.0, 1.0, "line")], periodic=True, wind=20.0,
                                          F_src=0.3, w_src=0.25, soot_k=8.0, turb=1.0, warm=2.0)),
    look=dict(smoke_albedo=0.2, smoke_k=0.6, noise=0.6, warp=1.2), kind="tile", title="Flame trail segment (tileable)", size_note="2 m long streaming ribbon, repeat or stretch along the path",
    haze=0.2, haze_shape="wide")

# --------------------------------- burning spatter and splash --------------------------------------
import math as _m
_sp = [(0.0, 0.0, 0.12, 0.12, 0.04, 1.0, 1.0, "disc", 0.0)]
for _i in range(1, 8):
    _a = _i * 2.4
    _r = 0.10 + 0.085 * _i
    _sp.append((_r * _m.cos(_a), _r * _m.sin(_a) * 0.8, 0.13, 0.12, 0.04, 0.8, 1.0, "disc", 0.15 * _i))
add("splash_fire", "pool", scaled("pool", 0.4, grid=(32, 24, 32), vents=_sp, F_src=0.5, w_src=1.2, soot_k=8.0, warm=3.5),
    look=dict(smoke_k=0.9, smoke_albedo=0.06, smoke_glow=0.8), title="Burning fuel splash (spreads into a ground fire)",
    size_note="splash 1 m, spreads over about 1.2 s, flames 0.8 to 1.2 m", haze=0.5, haze_shape="wide")
add("spatter_fan", "campfire", scaled("campfire", 1.5, grid=(32, 20, 28), vents=[(-0.25, 0, 0.1, 0.1, 0.03, 1.0, 0.0, "disc", 0.0), (0.0, 0, 0.1, 0.1, 0.03, 1.0, 0.0, "disc", 0.12),
                                                                              (0.25, 0, 0.1, 0.1, 0.03, 1.0, 0.0, "disc", 0.24)], F_src=0.3, w_src=0.4, soot_k=8.0, warm=0.5),
    look=dict(smoke_k=0.3), kind="shot", title="Short-lived fan of flame (spatter)", size_note="0.5 to 0.9 m, about 0.8 s", haze=0.15, haze_shape="wide")


# ---- per-type overrides applied after all types exist: heavy black smoke on fuel fires, haze metadata ----
_FUEL = dict(soot_k=10.0, soot_ox=1.0, mixc=0.8, puff_every=1.6, puff_soot=0.18)
for _n in ("oil_slick", "boat_deck", "smoke_column", "vehicle_engine", "vehicle_small"):
    PRESETS[_n].update(_FUEL)
    LOOK[_n].update(smoke_k=1.1, smoke_albedo=0.045, smoke_glow=0.9)
PRESETS["vehicle_engine"].update(puff_every=1.8, soot_k=9.0)
PRESETS["tree_crown"].update(puff_every=2.0, puff_soot=0.12, mixc=0.9)
PRESETS["barrel"].update(puff_every=2.0, puff_soot=0.14)
PRESETS["debris"].update(puff_every=3.0, puff_soot=0.08)
for _n, _h, _s in (("barrel", 0.6, "default"), ("torch", 0.25, "default"), ("flare", 0.2, "default"), ("debris", 0.4, "default"),
                   ("gas_jet", 0.6, "default"), ("shrub", 0.55, "default"), ("grass", 0.4, "wide"), ("spot_fire", 0.25, "wide"),
                   ("tree_crown", 0.9, "tall"), ("tree_trunk", 0.6, "tall"), ("oil_slick", 1.0, "tall"), ("boat_deck", 0.9, "tall"),
                   ("smoke_column", 0.7, "tall"), ("vehicle_engine", 0.6, "tall"), ("vehicle_small", 0.75, "tall"), ("roof", 1.0, "tall"),
                   ("window", 0.6, "default"), ("doorway", 0.6, "default"), ("front_lead", 0.4, "wide"), ("front_body", 0.4, "wide"),
                   ("front_trail", 0.25, "wide"), ("lick", 0.15, "wide")):
    META[_n].update(haze=_h, haze_shape=_s)


# ---- tuning pass from the look-dev contact sheets: sizes, fuel flux, smoke density ----
PRESETS["grass"].update(F_src=0.4, w_src=0.5)
PRESETS["debris"].update(F_src=0.34)
PRESETS["gas_jet"].update(F_src=0.55, w_src=7.0)
for _n, _dx in (("oil_slick", 0.18), ("boat_deck", 0.20), ("tree_crown", 0.48), ("roof", 0.50), ("building", 0.36), ("vehicle", 0.17), ("pool", 0.16),
                ("vehicle_small", 0.12), ("vehicle_engine", 0.085)):
    PRESETS[_n]["dx"] = _dx     # bigger domain around the same fire so it never fills the cell
PRESETS["smoke_column"]["vents"] = [(0, 0, 0.9, 0.9, 0.05, 1.0, 0.6)]
PRESETS["smoke_column"].update(F_src=0.7)
PRESETS["front_lead"].update(F_src=0.6, w_src=0.9)
PRESETS["front_body"].update(F_src=0.42, w_src=0.7)
PRESETS["front_trail"].update(F_src=0.22, w_src=0.4)
LOOK["front_lead"].update(smoke_k=0.35)
LOOK["front_body"].update(smoke_k=0.4)
LOOK["front_trail"].update(smoke_k=0.6)
for _n in ("pool", "vehicle", "oil_slick", "boat_deck", "smoke_column", "vehicle_small", "vehicle_engine"):
    LOOK[_n].update(smoke_k=1.6, smoke_albedo=0.04)
PRESETS["grass"].update(F_src=0.6, w_src=0.7, dx=0.085)
# fast carried flames fragment into separate pockets: shed fuel along the tail and mix more so the streak stays continuous
for _n, _amps in (("debris_med", (0.5, 0.3)), ("debris_fast", (0.8, 0.6))):
    _v = PRESETS[_n]["vents"]
    PRESETS[_n]["vents"] = _v + [(-0.72, 0.0, 0.1, 0.1, 0.55, _amps[0], 1.0), (-0.42, 0.0, 0.09, 0.09, 0.55, _amps[1], 1.0)]
    PRESETS[_n].update(diff=0.22, vc=0.25)
PRESETS["lick"].update(F_src=0.6, w_src=0.8)
PRESETS["spatter_fan"].update(F_src=0.6, w_src=0.8)


def domain_m(name):
    p = PRESETS[name]
    g = p.get("grid", S.GRID)
    return [round(g[0] * p["dx"], 2), round(g[1] * p["dx"], 2), round(g[2] * p["dx"], 2)]


TYPES = [n for n in META]
