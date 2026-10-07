"""Footsteps, run steps, jump/land and foley for the battle layer. Family friendly: breaths only, no voices."""
import math
import numpy as np
import synthlib as S
import gen_util as U
import svp_common as C
from wpn_common import *


# ------------------------------------------------------------------ single foot contacts: f(r, k) k=1 heel, ~0.6 toe
def c_concrete(r, k):
    n = n_of(0.2); j = r.uniform(0.85, 1.2)
    return tickn(r, 0.006, 1400 * j, 5500 * j, 0.9 * k, n) + thump(n, 88 * j, 0.035, 0.75 * k) + fit(S.modal(300 * j, 'stone', 0.12, 0.6, 0.8, r=r), n) * 0.12 * k \
        + bp(noise(n, 'white', r), 3500, 9000, SR, 1) * edec(n, 0.02) * 0.12


def c_asphalt(r, k):
    n = n_of(0.2); j = r.uniform(0.85, 1.2)
    y = lp(tickn(r, 0.007, 900 * j, 4200 * j, 0.85 * k, n), 4500, SR, 2) + thump(n, 80 * j, 0.04, 0.85 * k)
    return y + fit(U.ticks(0.1, lambda t: 300 * math.exp(-t * 18), r, 2000, 6500, 0.002), n) * 0.25 * k


def c_grass(r, k):
    n = n_of(0.3); j = r.uniform(0.85, 1.2)
    sw = bp(noise(n, 'white', r), 500 * j, 3800 * j, SR, 2) * np.minimum(1, np.arange(n) / (0.012 * SR)) * edec(n, 0.06) * 0.9 * k
    return sw + thump(n, 70 * j, 0.05, 0.5 * k) + fit(U.ticks(0.2, lambda t: 150 * math.exp(-t * 10), r, 1800, 7000, 0.003), n) * 0.2 * k


def c_gravel(r, k):
    n = n_of(0.3); j = r.uniform(0.85, 1.2)
    g = U.ticks(0.25, lambda t: 480 * math.exp(-t * 11) + 20, r, 1200 * j, 7500 * j, 0.004, spread=(0.3, 1.0)) * 0.9 * k
    return fit(g, n) + thump(n, 80 * j, 0.04, 0.5 * k) + bp(noise(n, 'white', r), 800, 3500, SR, 1) * edec(n, 0.07) * 0.25 * k


def c_sand(r, k):
    n = n_of(0.25); j = r.uniform(0.85, 1.2)
    y = bp(noise(n, 'white', r), 400 * j, 2800 * j, SR, 2) * np.minimum(1, np.arange(n) / (0.008 * SR)) * edec(n, 0.045) * 0.8 * k
    return y + fit(U.ticks(0.15, lambda t: 260 * math.exp(-t * 8), r, 1200, 4200, 0.005), n) * 0.7 * k + thump(n, 75 * j, 0.04, 0.35 * k)


def c_wood(r, k):
    n = n_of(0.4); j = r.uniform(0.85, 1.2)
    return fit(S.modal(170 * j, 'plank', 0.35, 0.6, 0.9, r=r), n) * 0.7 * k + tickn(r, 0.004, 700, 4200, 0.8 * k, n) + thump(n, 85 * j, 0.05, 0.8 * k)


def c_metal(r, k):
    n = n_of(0.5); j = r.uniform(0.85, 1.2)
    y = fit(S.modal(360 * j, 'iron', 0.4, 0.3, 1.0, r=r), n) * 0.45 * k + fit(S.modal(900 * j, 'steel', 0.3, 0.25, 1.0, r=r), n) * 0.2 * k
    return y + tickn(r, 0.003, 2000, 9000, 0.9 * k, n) + thump(n, 100 * j, 0.03, 0.7 * k)


def c_mud(r, k):
    n = n_of(0.4); j = r.uniform(0.85, 1.2)
    sl = lp(noise(n, 'white', r), 900 * j, SR, 2) * edec(n, 0.04) * 0.9 * k
    bub = fit(U.bubble_cloud(0.3, 90, 520, 90, 0.08, r, 2.0, 2.5), n) * 0.7 * k
    return sl + bub + thump(n, 62 * j, 0.06, 0.8 * k)


def c_water(r, k):
    n = n_of(0.5); j = r.uniform(0.85, 1.2)
    sp = bp(noise(n, 'white', r), 500, 4200 * j, SR, 2) * np.minimum(1, np.arange(n) / (0.006 * SR)) * edec(n, 0.07) * 0.75 * k
    bub = fit(U.bubble_cloud(0.4, 350, 2600, 150, 0.1, r), n) * 0.8 * k
    drips = fit(U.pings(0.4, lambda t: 25 * math.exp(-t * 5), r, 900, 2600, 0.025), n) * 0.2 * k
    return sp + bub + drips + thump(n, 78 * j, 0.05, 0.4 * k)


SURF = dict(concrete=c_concrete, asphalt=c_asphalt, grass=c_grass, gravel=c_gravel, sand=c_sand, wood=c_wood, metal=c_metal, mud=c_mud, water=c_water)
SPAN = dict(water=0.8, metal=0.55, wood=0.45, mud=0.5)


def walk_step(r, surface):
    """Heel strike then a softer toe slap a beat later."""
    fn = SURF[surface]; dur = SPAN.get(surface, 0.38); td = r.uniform(0.075, 0.11) * (1.9 if surface in ('water', 'mud') else 1.0)
    w = r.uniform(0.85, 1.15)
    return fade_out(mix(dur, [(fn(r, 1.0 * w), 0.0, 1.0), (fn(r, 0.55 * w), td, 0.6)]), 0.15)


def run_step(r, surface):
    fn = SURF[surface]; w = r.uniform(0.9, 1.2)
    return fade_out(mix(0.28, [(fn(r, 1.25 * w), 0.0, 1.0), (fn(r, 0.45), r.uniform(0.045, 0.06), 0.45)]), 0.2)


# ------------------------------------------------------------------ jump / land
def cloth_burst(r, dur, level=0.5, lo=500, hi=3500, rate=14):
    n = n_of(dur); t = np.linspace(0, 1, n)
    mod = 0.4 + 0.6 * S.smooth_random(n, rate, r, 1.0)
    return bp(noise(n, 'white', r), lo, hi, SR, 2) * mod * np.sin(np.pi * t) ** 0.8 * level


def breath_in(r, dur, level=0.3, hi=5000):
    n = n_of(dur); t = np.linspace(0, 1, n)
    return bp(noise(n, 'white', r), 500, hi, SR, 2) * np.sin(np.pi * t) ** 1.6 * level


def jump(r, i):
    surface = ('concrete', 'grass', 'gravel')[i % 3]
    return fade_out(mix(0.4, [(cloth_burst(r, 0.3, 0.55), 0.0, 1.0), (SURF[surface](r, 0.8)[:n_of(0.2)], 0.0, 0.8), (breath_in(r, 0.2, 0.3), 0.0, 1.0),
                              (S.tv_bandpass(noise(n_of(0.3), 'white', r), np.linspace(600, 2200, n_of(0.3)), 1.5, 2) * 0.2, 0.05, 0.5)]), 0.2)


def land(r, kind, i):
    hard = kind == 'hard'
    surf = ('concrete', 'gravel', 'wood')[i % 3] if hard else ('grass', 'sand', 'mud')[i % 3]
    body = SURF[surf](r, 1.6 if hard else 1.0)
    gear = steel_rattle(r, 0.4, 0.5) if hard else cloth_burst(r, 0.3, 0.5)
    return fade_out(mix(0.6, [(body, 0.0, 1.0), (SURF[surf](r, 0.9), 0.012, 0.6), (gear, 0.02, 0.8), (thump(n_of(0.3), 62 if hard else 75, 0.09, 0.9 if hard else 0.5), 0.0, 1.0),
                              (breath_in(r, 0.18, 0.3 if hard else 0.12), 0.05, 1.0)]), 0.2)


# ------------------------------------------------------------------ foley
def steel_rattle(r, dur, level=1.0):
    out = np.zeros(n_of(dur)); t = 0.0
    while t < dur - 0.08:
        put(out, sumv(pingn(r.uniform(1800, 4600), r.uniform(0.01, 0.03), 0.12, ((1, 1, 1), (2.76, .5, .6), (5.4, .25, .3)), r=r) * 0.6, tickn(r, 0.002, 2000, 8000, 0.5)),
            t, r.uniform(0.3, 1.0) * level)
        t += r.exponential(0.06) + 0.012
    return out


def foley_cloth(r, i):
    dur = r.uniform(0.5, 0.8)
    return fade_out(cloth_burst(r, dur, 0.8, r.uniform(400, 900), r.uniform(2500, 5000), r.uniform(10, 22)) + lp(noise(n_of(dur), 'white', r), 400, SR, 1) * 0.05, 0.25)


def foley_gear(r, i):
    dur = 0.8; n = n_of(dur); t = np.linspace(0, 1, n)
    out = steel_rattle(r, dur, 0.7) * np.sin(np.pi * np.clip(t * 1.1, 0, 1)) ** 0.4
    sling = lp(noise(n, 'white', r), 1200, SR, 2) * S.smooth_random(n, 11, r, 1.0) * np.sin(np.pi * t) * 0.35      # leather strap
    knock = fit(S.modal(r.uniform(180, 260), 'wood', 0.3, 0.5, 0.8, r=r), n) * 0.2
    put(out, knock, r.uniform(0.0, 0.3), 1.0)
    return fade_out(out + sling, 0.2)


def foley_pickup(r, i):
    return mix(0.35, [(cloth_burst(r, 0.2, 0.6, 600, 3500), 0.0, 1.0), (tickn(r, 0.004, 900, 4500, 0.6), 0.14, 1.0), (thump(n_of(0.1), 130, 0.03, 0.35), 0.15, 1.0),
                      (pingn(r.uniform(1800, 2300), 0.04, 0.2, ((1, .3, 1), (2.0, .15, .6))), 0.15, 0.7)])


def drop_crate(r, i):
    n = n_of(0.8); j = r.uniform(0.9, 1.15)
    y = fit(S.modal(125 * j, 'plank', 0.6, 0.9, 0.9, r=r), n) * 0.8 + thump(n, 58 * j, 0.1, 1.2) + tickn(r, 0.006, 500, 3500, 0.8, n)
    y += fit(U.ticks(0.3, lambda t: 40 * math.exp(-t * 6), r, 700, 3500, 0.004), n) * 0.5       # rattling contents
    put(y, fit(S.modal(210 * j, 'plank', 0.3, 0.5, 0.8, r=r), n_of(0.4)), 0.11, 0.35)
    return y


def swim_stroke(r, i):
    dur = 0.75; n = n_of(dur); t = np.linspace(0, 1, n)
    wsh = S.tv_bandpass(noise(n, 'white', r), 700 + 1800 * np.sin(np.pi * t), 1.8, 2) * np.sin(np.pi * np.clip(t * 1.3, 0, 1)) ** 1.4 * 0.7
    slap = lp(noise(n_of(0.15), 'white', r), 2500, SR, 2) * edec(n_of(0.15), 0.025) * 0.8
    out = wsh.copy(); put(out, slap, 0.0, 1.0); put(out, fit(U.bubble_cloud(0.3, 300, 2000, 80, 0.12, r), n_of(0.3)), 0.12, 0.5)
    return fade_out(out, 0.2)


def breath_hurt(r, i):
    """Mild, short pained breath for taking a hit: an 'hnh' grunt/exhale. No scream, no gore."""
    dur = 0.32; n = n_of(dur); f0 = np.linspace(r.uniform(150, 185), r.uniform(110, 135), n)
    vow = (r.uniform(480, 640), r.uniform(1050, 1350), r.uniform(2300, 2600))
    env = np.minimum(1, np.arange(n) / (0.012 * SR)) * np.exp(-np.arange(n) / (0.16 * SR))
    v = C.vocal(f0, dur, [np.full(n, x) for x in vow], r, breath=1.1, env=env)
    v = v / (np.max(np.abs(v)) + 1e-9) * 0.7
    hiss = bp(noise(n, 'white', r), 2500, 7000, SR, 1) * env * 0.12
    return fade_out(v + hiss, 0.2)


def heal(r=None):
    r = rng(601); notes = [76, 79, 83, 88]
    parts = [(pingn(C.hz(m), 0.35, 1.2, ((1, 1, 1), (2.0, .25, .5), (3.0, .1, .3))), 0.09 * k, 0.8 - 0.06 * k) for k, m in enumerate(notes)]
    parts.append((pingn(C.hz(100), 0.5, 1.2, ((1, .2, 1),)), 0.3, 0.4))
    return fade_out(mix(1.3, parts), 0.15)


def render():
    kw = dict(bus='ppl', group='people', max_dist=28, weight=1.0, rate=(0.94, 1.06))
    for s in SURF:
        fam('step_' + s, 6, lambda r, i, s=s: walk_step(r, s), peak=-6, tags=['step', s], meta={'surface': s}, **kw)
    fam('step_run_hard', 3, lambda r, i: run_step(r, ('concrete', 'asphalt', 'wood')[i % 3]), peak=-5, tags=['step', 'run', 'hard'], meta={'surface': 'hard'}, **kw)
    fam('step_run_soft', 3, lambda r, i: run_step(r, ('grass', 'sand', 'mud')[i % 3]), peak=-6, tags=['step', 'run', 'soft'], meta={'surface': 'soft'}, **kw)
    fam('foley_jump', 3, jump, peak=-7, tags=['foley', 'jump'], **kw)
    fam('foley_land_hard', 3, lambda r, i: land(r, 'hard', i), peak=-5, tags=['foley', 'land'], **kw)
    fam('foley_land_soft', 3, lambda r, i: land(r, 'soft', i), peak=-7, tags=['foley', 'land'], **kw)
    kw['max_dist'] = 22
    fam('foley_cloth', 3, foley_cloth, peak=-10, tags=['foley', 'cloth'], **kw)
    fam('foley_gear', 3, foley_gear, peak=-9, tags=['foley', 'gear'], **kw)
    fam('foley_pickup', 1, foley_pickup, peak=-8, tags=['foley', 'pickup'], **kw)
    fam('foley_drop_crate', 1, drop_crate, peak=-5, tags=['foley', 'crate'], **dict(kw, max_dist=60))
    fam('foley_swim_stroke', 3, swim_stroke, peak=-9, tags=['foley', 'swim'], **kw)
    fam('foley_breath_hurt', 3, breath_hurt, peak=-7, tags=['foley', 'breath', 'hurt'], **dict(kw, max_dist=35))
    fam('foley_heal', 1, lambda r, i: heal(), peak=-8, tags=['foley', 'heal'], **dict(kw, bus='ui', max_dist=1000, rate=(1.0, 1.0)))
