"""Material impacts, terrain granular loops, lava/glass (bus 'mat')."""
import math
import numpy as np
import synthlib as S
from synthlib import SR, rng, n_of, noise, lp, hp, bp, resonator, impact, modal
from gen_util import *


def V(name, count, maker, peak=-6, weight=2, max_dist=90, group=None, lazy=False, meta=None, **kw):
    S.variants(maker, name, count, bus='mat', peak=peak, weight=weight, max_dist=max_dist, group=group or ('core' if not lazy else 'mat'), lazy=lazy, meta=meta, **kw)


def L(name, x, lufs=-26, peak=-6, weight=2, max_dist=70, meta=None, stereo=False):
    S.save(name, x, bus='mat', loop=True, target_lufs=lufs, peak=peak, weight=weight, max_dist=max_dist, lazy=True, group='mat', meta=meta)


def mat_meta(material, size, speed=(1, 12), extra=None):
    d = dict(material=material, sizeClass=size, impactSpeed=list(speed))
    if extra: d.update(extra)
    return d


# ---------------------------------------------------------------- wood
def wood(render):
    def knock(i):
        r = rng(seed_of('wk', i)); return impact('wood', jit(r, 380, .3), size=jit(r, .7, .2), hardness=r.uniform(.4, .6), dur=0.4, seed=i + 100)
    V('mat_wood_knock', 6, knock, peak=-8, weight=2, meta=mat_meta('wood', 's', (0.5, 5), dict(pickBy='speed -> gain; mass -> pitch down')))

    def thump(i):
        r = rng(seed_of('wt', i)); return impact('wood', jit(r, 150, .3), size=jit(r, 1.0, .2), hardness=.15, dur=0.6, seed=i + 200, thump=1.0)
    V('mat_wood_thump', 6, thump, peak=-5, weight=4, meta=mat_meta('wood', 'l', (1, 10)))

    def creak(i):
        r = rng(seed_of('wc', i)); d = r.uniform(1.0, 1.6); n = n_of(d); t = np.arange(n) / SR
        fc = jit(r, 520, .2) * (1 + 0.35 * np.sin(np.pi * t / d) * r.choice([-1, 1]))
        src = noise(n, 'white', r) * (0.5 + 0.5 * (np.sin(2 * np.pi * (28 + 20 * t / d) * t + r.uniform(0, 6)) > 0.2))   # stick-slip
        y = S.tv_bandpass(src, fc, 0.35, 2) + 0.6 * S.tv_bandpass(src, fc * 2.1, 0.3, 2)
        return y * np.sin(np.pi * t / d) ** 0.7
    V('mat_wood_creak', 6, creak, peak=-14, weight=1, lazy=True, max_dist=60, meta=mat_meta('wood', 'm', (0, 2), dict(note='stress groan for loaded pier/hull/beam')))

    def crack(i):
        r = rng(seed_of('wcr', i)); n = n_of(0.7); out = np.zeros(n)
        put(out, burst(r, 0.02, 1500, 9000, 0.004), 0, 1)
        put(out, sweep(jit(r, 1800), 600, 0.12, tau=0.03) * .5, 0.002)
        put(out, impact('wood', jit(r, 260, .2), 1.0, .6, 0.6, i + 300), 0.01, 0.6)
        put(out, ticks(0.25, lambda t: 80 * math.exp(-t / .08), r, 1500, 6000), 0.02, 0.5)
        return out
    V('mat_wood_crack', 6, crack, peak=-4, weight=4, meta=mat_meta('wood', 'm', (3, 20), dict(note='fracture under load')))

    def splinter(i):
        r = rng(seed_of('wsp', i)); d = 1.0; out = Z(d)
        put(out, burst(r, 0.03, 1200, 8000, 0.006), 0, 1)
        put(out, ticks(d, lambda t: 110 * math.exp(-t / .3) + 8, r, 1200, 7000, 0.005, spread=(.2, 1)), 0.01, 0.8)
        put(out, ticks(d, lambda t: 25 * math.exp(-t / .4), r, 400, 1800, 0.012), 0.02, 0.4)
        return out
    V('mat_wood_splinter', 6, splinter, peak=-7, weight=3, meta=mat_meta('wood', 'm', (3, 20)))

    def snap(i):
        r = rng(seed_of('wsn', i)); n = n_of(0.45); out = np.zeros(n)
        put(out, burst(r, 0.012, 2000, 10000, 0.003), 0, 1)
        put(out, resonator(noise(n, 'white', r), jit(r, 1200, .15), 25) * edec(n, 0.05) * 0.5, 0)
        put(out, impact('wood', jit(r, 320, .2), .5, .7, .3, i + 400), 0.005, 0.5)
        return out
    V('mat_wood_snap', 6, snap, peak=-5, weight=3, meta=mat_meta('wood', 's', (2, 15), dict(note='branch / mast / rigging member snaps')))

    def plank_drop(i):
        r = rng(seed_of('wpd', i)); d = 1.1; out = Z(d); t = 0.0; g = 1.0; f0 = jit(r, 200, .25)
        gaps = [0.0, r.uniform(.12, .2)]; gaps.append(gaps[-1] + r.uniform(.06, .1)); gaps.append(gaps[-1] + r.uniform(.03, .05))
        for k, tt_ in enumerate(gaps):
            put(out, impact('plank', f0 * (1 + .03 * k), 1.0, .4, 0.5, i * 7 + k + 500), tt_, g); g *= 0.45
        return out
    V('mat_wood_plank_drop', 6, plank_drop, peak=-6, weight=3, meta=mat_meta('wood', 'm', (1, 8), dict(note='plank lands and bounces')))

    def barrel(i):
        r = rng(seed_of('wb', i)); n = n_of(0.9); out = np.zeros(n)
        f0 = jit(r, 170, .2)
        put(out, impact('barrel', f0, 1.0, .35, 0.9, i + 600, thump=0.8), 0)
        put(out, resonator(noise(n, 'white', r), f0 * 1.9, 9) * edec(n, 0.12) * 0.35, 0)
        return out
    V('mat_wood_barrel_knock', 6, barrel, peak=-7, weight=3, meta=mat_meta('wood-barrel', 'm', (0.5, 6), dict(note='hollow; empty barrels, resonant')))

    def crate(i):
        r = rng(seed_of('wcs', i)); d = 0.9; out = Z(d)
        put(out, impact('plank', jit(r, 130, .2), 1.3, .35, 0.7, i + 700, thump=1.1), 0)
        put(out, impact('wood', jit(r, 330, .2), .8, .5, 0.4, i + 710), 0.0, 0.5)
        put(out, ticks(0.35, lambda t: 40 * math.exp(-t / .12), r, 300, 1800, 0.012), 0.02, 0.6)   # rattle of boards
        return out
    V('mat_wood_crate_slam', 6, crate, peak=-4, weight=5, meta=mat_meta('wood-crate', 'l', (2, 12)))

    def collapse(i):
        r = rng(seed_of('wcol', i)); d = 3.2; out = Z(d)
        put(out, burst(r, 0.03, 800, 8000, 0.006), 0, 1)
        put(out, resonator(noise(n_of(1.5), 'brown', r), jit(r, 110, .2), 3) * edec(n_of(1.5), .5) * .9, 0.0, 0.7)
        t = 0.02; j = 0
        while t < 2.6:
            kind = r.integers(0, 4); a = math.exp(-t / 1.1) * r.uniform(.4, 1)
            if kind == 0: x = impact('plank', r.uniform(120, 400), 1.0, .4, .5, int(r.integers(1e6)), thump=.5)
            elif kind == 1: x = impact('wood', r.uniform(250, 700), .6, .6, .35, int(r.integers(1e6)))
            elif kind == 2: x = burst(r, 0.02, 1200, 7000, 0.004)
            else: x = ticks(0.2, lambda tt_: 90, r, 1000, 6000)
            put(out, x, t, a); t += r.exponential(0.07 + 0.25 * t / 2.6)
        put(out, lp(noise(n_of(d), 'pink', r), 500) * S.env_attack(n_of(d), .3) * edec(n_of(d), 1.2) * 0.25, 0)   # dust/rumble bed
        return out
    V('mat_wood_collapse', 4, collapse, peak=-3, weight=8, max_dist=200, meta=mat_meta('wood', 'xl', (3, 30), dict(note='whole structure/pier/house falling')))


# ---------------------------------------------------------------- stone
def stone():
    def tock(i):
        r = rng(seed_of('st', i)); n = n_of(0.28); f0 = jit(r, 780, .25)
        out = impact('stone', f0, 0.8, .55, 0.28, i + 800)
        out = out + 0.3 * lp(noise(n, 'white', r), 3500) * edec(n, 0.02)       # gritty
        put(out, sine(jit(r, 95, .1), 0.15, 0.04), 0, 0.5)
        return out
    V('mat_stone_tock', 6, tock, peak=-5, weight=3, meta=mat_meta('stone', 'm', (0.3, 6), dict(note='block placed on stone; the Place tool')))

    def scrape(i):
        r = rng(seed_of('ss', i)); d = r.uniform(.9, 1.3); n = n_of(d); t = np.arange(n) / SR
        src = noise(n, 'white', r) * (0.4 + 0.6 * smooth(n, 40, r))
        y = S.tv_filter(src, 1800 + 1200 * np.sin(2 * np.pi * 3 * t), 'lp', 2)
        y = hp(y, 250) + 0.5 * S.tv_bandpass(src, 500 + 400 * t / d, 0.5, 2)
        return y * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 0.5
    V('mat_stone_scrape', 4, scrape, peak=-10, weight=2, lazy=True, meta=mat_meta('stone', 'm', (0.2, 2), dict(note='stone dragging; loop-able by retriggering')))

    def crumble(i):
        r = rng(seed_of('sc', i)); d = 1.8; out = Z(d)
        put(out, ticks(d, lambda t: 140 * math.exp(-t / .7) + 10, r, 600, 4500, 0.006, spread=(.2, 1)), 0, 1)
        put(out, ticks(d, lambda t: 25 * math.exp(-t / .6), r, 250, 1200, 0.014), 0, .8)
        put(out, lp(noise(n_of(d), 'brown', r), 320) * edec(n_of(d), .5) * .6, 0, 0.5)
        return out
    V('mat_stone_crumble', 4, crumble, peak=-6, weight=4, meta=mat_meta('stone', 'm', (1, 10), dict(note='block breaks down / weathers')))

    def shatter(i):
        r = rng(seed_of('ssh', i)); d = 2.0; out = Z(d)
        put(out, burst(r, 0.03, 600, 9000, 0.006), 0, 1)
        put(out, impact('stone', jit(r, 420, .2), 1.5, .8, .4, i + 900, thump=1.0), 0, 0.9)
        put(out, ticks(d, lambda t: 160 * math.exp(-t / .5) + 6, r, 700, 6000, 0.005), 0.01, 0.9)
        for k in range(5):
            put(out, impact('stone', r.uniform(500, 1600), .5, .6, .2, int(r.integers(1e6))), r.uniform(0.05, .6), 0.35)
        return out
    V('mat_stone_shatter', 4, shatter, peak=-3, weight=6, max_dist=150, meta=mat_meta('stone', 'l', (4, 30)))

    def roll(d, r):
        n = n_of(d); t = np.arange(n) / SR
        y = lp(noise(n, 'brown', r), 420) * (0.6 + 0.4 * np.sin(2 * np.pi * 1.2 * t + 1)) * 0.6
        y += ticks(d, lambda t: 22, r, 500, 3000, 0.008) * 0.8
        for k in range(int(d * 5)):
            put(y, impact('stone', r.uniform(500, 1400), .5, .5, .12, int(r.integers(1e6))), r.uniform(0, d - .2), r.uniform(.1, .35))
        return y + hp(noise(n, 'pink', r), 1500) * 0.03
    L('mat_stone_rock_roll', loop_of(lambda d: roll(d, rng(seed_of('roll')))), meta=dict(drive='boulder speed -> gain and rate 0.8..1.4'))

    def rubble(i):
        r = rng(seed_of('sr', i)); d = 1.4; out = Z(d)
        for k in range(r.integers(8, 14)):
            tk = r.uniform(0, 1.1) ** 1.6 * 1.1; put(out, impact('stone', r.uniform(450, 1500), .6, .55, .2, int(r.integers(1e6))), tk, r.uniform(.2, .8) * math.exp(-tk / .8))
        put(out, ticks(d, lambda t: 40 * math.exp(-t / .5), r, 800, 5000, 0.005), 0, 0.5)
        return out
    V('mat_stone_rubble_settle', 4, rubble, peak=-9, weight=2, meta=mat_meta('stone', 's', (0, 3), dict(note='aftershock of collapse')))

    def chink(i):
        r = rng(seed_of('sq', i)); n = n_of(0.35); f = jit(r, 2800, .2); out = np.zeros(n)
        put(out, sine(f, 0.3, 0.05) * 0.5 + sine(f * 2.76, 0.2, 0.03) * 0.3, 0)
        put(out, burst(r, 0.01, 2500, 10000, 0.002), 0, 0.8)
        put(out, impact('stone', jit(r, 900, .2), .4, .8, .12, i + 1000), 0, 0.5)
        return out
    V('mat_stone_quarry_chink', 4, chink, peak=-9, weight=2, lazy=True, meta=mat_meta('stone+steel', 's', (2, 8), dict(note='quarry work, pick on rock')))


# ---------------------------------------------------------------- metal
def metal():
    def clang_s(i):
        r = rng(seed_of('cs', i)); return impact('steel', jit(r, 1050, .3), 1.0, .85, 1.3, i + 1100)
    V('mat_metal_clang_s', 6, clang_s, peak=-6, weight=3, meta=mat_meta('steel', 's', (1, 10)))

    def clang_l(i):
        r = rng(seed_of('cl', i)); return impact('steel', jit(r, 240, .3), 1.8, .75, 3.0, i + 1200, thump=0.7)
    V('mat_metal_clang_l', 6, clang_l, peak=-3, weight=6, max_dist=160, meta=mat_meta('steel', 'l', (1, 15)))

    def scrape(i):
        r = rng(seed_of('ms', i)); d = r.uniform(1.0, 1.4); n = n_of(d); t = np.arange(n) / SR
        src = noise(n, 'white', r) * (0.5 + 0.5 * smooth(n, 60, r))
        y = S.tv_bandpass(src, 1400 + 900 * np.sin(2 * np.pi * 1.7 * t), 0.4, 2)
        sq = sum(np.sin(2 * np.pi * f * t * (1 + 0.05 * np.sin(2 * np.pi * 3 * t))) * a for f, a in [(jit(r, 2300, .1), .3), (jit(r, 3700, .1), .2)])
        return (y + sq * (0.5 + 0.5 * smooth(n, 8, r))) * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 0.6
    V('mat_metal_scrape', 4, scrape, peak=-10, weight=2, lazy=True, meta=mat_meta('steel', 'm', (0.2, 3)))

    def bend(i):
        r = rng(seed_of('mb', i)); d = r.uniform(1.8, 2.4); n = n_of(d); t = np.arange(n) / SR
        src = noise(n, 'white', r)
        f = jit(r, 160, .2) * (1 - 0.35 * t / d)
        y = S.tv_bandpass(src, f, 0.12, 2) * 2 + S.tv_bandpass(src, f * 2.76, 0.12, 2) + 0.6 * S.tv_bandpass(src, f * 5.4, 0.15, 2)
        y *= (0.6 + 0.4 * (np.sin(2 * np.pi * 7 * t) > 0)) * S.env_attack(n, 0.2) * np.exp(-np.maximum(0, t - d * .6) * 2)
        return y
    V('mat_metal_bend_groan', 4, bend, peak=-8, weight=3, lazy=True, meta=mat_meta('steel', 'l', (0, 3), dict(note='hull/girder yielding under load')))

    def clatter(i):
        r = rng(seed_of('mc', i)); d = 1.6; out = Z(d); t = 0.0
        while t < d - .3:
            put(out, impact('iron', r.uniform(500, 2800), r.uniform(.3, .8), .8, .35, int(r.integers(1e6))), t, r.uniform(.3, 1) * math.exp(-t / .9)); t += r.exponential(.045 + .1 * t)
        return out
    V('mat_metal_scrap_clatter', 4, clatter, peak=-6, weight=3, meta=mat_meta('scrap', 'm', (1, 8)))

    def ingot(i):
        r = rng(seed_of('mi', i)); return impact('iron', jit(r, 420, .2), 1.0, .4, .6, i + 1300, thump=1.2)
    V('mat_metal_ingot_clunk', 4, ingot, peak=-5, weight=3, meta=mat_meta('iron', 'm', (0.5, 5)))

    def boom(i):
        r = rng(seed_of('mx', i)); d = 3.4; out = Z(d)
        put(out, impact('steel', jit(r, 75, .15), 2.5, .45, 3.2, i + 1400, thump=1.3), 0)
        put(out, impact('steel', jit(r, 160, .2), 2.0, .5, 2.2, i + 1410), 0.0, 0.6)
        put(out, resonator(noise(n_of(1.2), 'white', r), jit(r, 190, .1), 6) * edec(n_of(1.2), .4) * .4, 0)
        return out
    V('mat_metal_container_boom', 4, boom, peak=-3, weight=8, max_dist=200, meta=mat_meta('steel-container', 'xl', (1, 12)))

    def chain(d, r):
        n = n_of(d); y = np.zeros(n)
        def g(rr, i):
            return impact('steel', rr.uniform(1200, 3200), .25, .9, .12, int(rr.integers(1e9))) * rr.uniform(.2, 1)
        y = grains(d, lambda t: 26 + 10 * math.sin(t * 2), g, r)
        y += ticks(d, lambda t: 50, r, 3000, 9000, 0.002) * 0.3
        return y
    L('mat_metal_chain_rattle', loop_of(lambda d: chain(d, rng(seed_of('chain')))), meta=dict(drive='chain speed (links/s) -> rate 0.7..1.6 and gain'))

    def anchor(i):
        r = rng(seed_of('ma', i)); d = 2.8; out = Z(d)
        t = 0.0
        while t < 1.2:
            put(out, impact('steel', r.uniform(1200, 3000), .25, .9, .12, int(r.integers(1e9))), t, r.uniform(.2, .6) * (0.4 + t)); t += r.exponential(.03)
        put(out, impact('iron', jit(r, 160, .15), 1.5, .5, 1.0, i + 1500, thump=1.2), 1.2, 1.0)
        put(out, burst(r, 0.4, 100, 3000, 0.1), 1.2, 0.3)
        return out
    V('mat_metal_anchor_drop', 4, anchor, peak=-4, weight=6, max_dist=140, meta=mat_meta('steel', 'l', (2, 12), dict(note='chain pays out then anchor hits; play water_splash_m at +1.2 s if over water')))

    def sizzle(i):
        r = rng(seed_of('mz', i)); d = 1.6; n = n_of(d); t = np.arange(n) / SR
        y = hp(noise(n, 'white', r), 3500) * 0.25 * (0.7 + 0.3 * smooth(n, 30, r)) * np.exp(-t / 0.9)
        y += ticks(d, lambda tt_: 60 * math.exp(-tt_ / 1.0) + 10, r, 2500, 9000, 0.003) * 0.9
        y += bubble_cloud(d, 300, 1100, 25, 0.8, r, 1.2) * 0.4
        return y * S.env_attack(n, 0.01)
    V('mat_metal_sizzle_melt', 4, sizzle, peak=-9, weight=2, lazy=True, meta=mat_meta('metal-hot', 's', (0, 1), dict(note='metal heating / melting')))


# ---------------------------------------------------------------- glass
def glass():
    def ping(i):
        r = rng(seed_of('gp', i)); return impact('glass', jit(r, 2600, .3), .9, .85, 1.5, i + 1600)
    V('mat_glass_ping', 6, ping, peak=-8, weight=2, meta=mat_meta('glass', 's', (0.3, 4)))

    def crack(i):
        r = rng(seed_of('gc', i)); n = n_of(0.5); out = np.zeros(n)
        put(out, burst(r, 0.01, 3000, 14000, 0.002), 0, 1)
        put(out, sweep(jit(r, 2800, .15), jit(r, 7500, .15), 0.06, tau=0.02) * .5, 0.0)
        put(out, impact('glass', jit(r, 3400, .2), .4, .9, .4, i + 1700), 0.003, 0.5)
        return out
    V('mat_glass_crack', 6, crack, peak=-6, weight=3, meta=mat_meta('glass', 's', (1, 10)))

    def shards(d, r, rate, f_lo, f_hi, tau):
        return pings(d, lambda t: rate * math.exp(-t / tau) + 1, r, f_lo, f_hi, 0.03, mat=2.32) + ticks(d, lambda t: rate * .6 * math.exp(-t / tau), r, 3000, 12000, 0.002) * 0.5

    def big(i):
        r = rng(seed_of('gbl', i)); d = 3.0; out = Z(d)
        put(out, burst(r, 0.02, 2000, 14000, 0.005), 0, 1)
        for k in range(14):
            put(out, impact('glass', r.uniform(1800, 6500), .5, .9, .5, int(r.integers(1e9))), r.uniform(0, .02), r.uniform(.15, .5))
        put(out, shards(d, r, 220, 1500, 9000, 0.6), 0.015, 0.7)
        put(out, impact('glass', jit(r, 700, .2), 1.0, .5, 1.2, i + 1800, thump=.3), 0, 0.5)
        return out
    V('mat_glass_shatter_large', 4, big, peak=-3, weight=5, max_dist=150, meta=mat_meta('glass', 'l', (2, 20)))

    def small(i):
        r = rng(seed_of('gsm', i)); d = 1.5; out = Z(d)
        put(out, burst(r, 0.015, 3000, 14000, 0.004), 0, 1)
        for k in range(8):
            put(out, impact('glass', r.uniform(3000, 8500), .35, .9, .3, int(r.integers(1e9))), r.uniform(0, .015), r.uniform(.15, .5))
        put(out, shards(d, r, 120, 2500, 10000, 0.35), 0.01, 0.6)
        return out
    V('mat_glass_shatter_small', 4, small, peak=-5, weight=3, meta=mat_meta('glass', 's', (1, 12)))

    def settle(i):
        r = rng(seed_of('gst', i)); d = 1.8; out = Z(d)
        out += pings(d, lambda t: 22 * math.exp(-t / .8) + 1, r, 1800, 8000, 0.025, mat=2.32)
        out += ticks(d, lambda t: 25 * math.exp(-t / .8), r, 3500, 11000, 0.002) * 0.4
        return out
    V('mat_glass_shards_settle', 4, settle, peak=-11, weight=1, meta=mat_meta('glass', 's', (0, 1)))


# ---------------------------------------------------------------- ice
def ice():
    def crack(i):
        r = rng(seed_of('ic', i)); n = n_of(0.6); out = np.zeros(n)
        put(out, burst(r, 0.015, 1500, 11000, 0.004), 0, 1)
        put(out, sweep(jit(r, 500, .2), jit(r, 3200, .2), 0.09, tau=0.04) * .6, 0)    # rising pitch sweep
        put(out, impact('ice', jit(r, 1400, .25), .6, .8, .5, i + 1900), 0.004, 0.5)
        return out
    V('mat_ice_crack', 6, crack, peak=-5, weight=3, meta=mat_meta('ice', 'm', (1, 12)))

    def crunch(i):
        r = rng(seed_of('icr', i)); d = 0.9; out = Z(d)
        put(out, ticks(d, lambda t: 220 * math.exp(-t / .22) + 10, r, 1200, 7000, 0.006, spread=(.3, 1)), 0, 1)
        put(out, ticks(d, lambda t: 60 * math.exp(-t / .2), r, 500, 2200, 0.012), 0, .6)
        return out
    V('mat_ice_crunch', 6, crunch, peak=-7, weight=2, meta=mat_meta('ice', 's', (0.5, 6), dict(note='walking/stepping on ice, hull in brash')))

    def tinkle(i):
        r = rng(seed_of('it', i)); d = 1.2
        out = pings(d, lambda t: 28 * math.exp(-t / .5) + 2, r, 2500, 9000, 0.03, mat=3.45) + ticks(d, lambda t: 20 * math.exp(-t / .4), r, 4000, 11000, 0.002) * .3
        return out
    V('mat_ice_tinkle', 4, tinkle, peak=-11, weight=1, meta=mat_meta('ice', 's', (0, 1)))

    def groan(i):
        r = rng(seed_of('ig', i)); d = r.uniform(2.0, 2.8); n = n_of(d); t = np.arange(n) / SR
        src = noise(n, 'white', r); f = jit(r, 230, .3) * (1 + 0.5 * np.sin(np.pi * t / d) * r.choice([-1, 1]) + 0.1 * np.sin(2 * np.pi * 5 * t))
        y = S.tv_bandpass(src, f, .1, 2) * 2 + S.tv_bandpass(src, f * 1.52, .12, 2) + 0.5 * S.tv_bandpass(src, f * 2.9, .15, 2)
        return y * np.sin(np.pi * t / d) ** 0.8
    V('mat_ice_groan', 4, groan, peak=-8, weight=3, lazy=True, meta=mat_meta('ice', 'l', (0, 2)))

    def creak(i):
        r = rng(seed_of('icrk', i)); d = r.uniform(3.2, 5.5); n = n_of(d); t = np.arange(n) / SR
        src = noise(n, 'white', r)
        f0 = jit(r, 520, .25); f = f0 * (1 + 0.8 * smooth(n, 0.6, r, 1.0) - 0.4)
        y = S.tv_bandpass(src, f, .05, 2) * 3 + S.tv_bandpass(src, f * 1.7, .06, 2) * 1.5
        y += S.tv_bandpass(src, f * 3.1, .08, 2) * 0.6 * (0.5 + 0.5 * smooth(n, 7, r))
        return y * (0.3 + 0.7 * smooth(n, 1.2, r)) * np.sin(np.pi * t / d) ** 0.5
    V('mat_ice_creak', 4, creak, peak=-12, weight=2, lazy=True, max_dist=140, meta=mat_meta('sea-ice', 'xl', (0, 1), dict(note='long glide; trigger for sea ice under load or temperature change; 3 to 6 s')))

    def brk(i):
        r = rng(seed_of('ib', i)); d = 2.6; out = Z(d)
        put(out, burst(r, 0.02, 1000, 11000, 0.006), 0, 1)
        put(out, sweep(300, 2500, 0.15, tau=0.06) * .5, 0)
        put(out, impact('ice', jit(r, 180, .2), 2.0, .6, 1.0, i + 2000, thump=1.2), 0.0, 0.9)
        put(out, ticks(d, lambda t: 130 * math.exp(-t / .45) + 4, r, 900, 6500, 0.006), 0.05, 0.8)
        put(out, burst(r, 1.0, 100, 2500, 0.3) * S.env_attack(n_of(1.0), .1), 0.25, 0.3)     # water churn
        out += pings(d, lambda t: 14 * math.exp(-t / .6), r, 2500, 7000, 0.03, mat=3.45) * 0.4
        return out
    V('mat_ice_break_large', 4, brk, peak=-3, weight=7, max_dist=180, meta=mat_meta('ice', 'xl', (2, 15), dict(note='floe fractures; pair with water_splash_l')))

    def melt(i):
        r = rng(seed_of('im', i)); n = n_of(0.3); f = r.uniform(1800, 3200); out = np.zeros(n)
        b = bubble(r, f, f, .8, rise=2.5); put(out, b / np.max(np.abs(b)), 0); put(out, sine(f * 1.5, .08, .015) * .15, 0)
        return out
    V('mat_ice_melt_drip', 4, melt, peak=-17, weight=0.5, lazy=True, max_dist=35, meta=mat_meta('ice', 's', (0, 0), dict(note='rate by temperature above 0 C')))


# ---------------------------------------------------------------- terrain granular, slumps
def terrain():
    def sand(d, r):
        n = n_of(d); y = ticks(d, lambda t: 1500, r, 3500, 11000, 0.0015, spread=(.2, .8)) + hp(noise(n, 'white', r), 3000) * 0.05
        y = y * (0.8 + 0.2 * smooth(n, 12, r))
        return y + lp(noise(n, 'pink', r), 700) * 0.04 * smooth(n, 3, r)
    L('grain_sand_pour', loop_of(lambda d: sand(d, rng(seed_of('sandp')))), meta=dict(drive='flow rate -> gain; lowpass opens with fall height; rate 0.9..1.1'), lufs=-28)

    def earth(d, r):
        n = n_of(d)
        def g(rr, i):
            k = int(rr.uniform(.01, .03) * SR); x = rr.standard_normal(k) * np.exp(-np.arange(k) / (k * .25)); return lp(x, rr.uniform(200, 1400)) * rr.uniform(.3, 1)
        y = grains(d, lambda t: 220, g, r); y += lp(noise(n, 'brown', r), 250) * 0.5 * smooth(n, 5, r, .6)
        return y
    L('grain_earth_pour', loop_of(lambda d: earth(d, rng(seed_of('earthp')))), meta=dict(drive='flow rate -> gain'), lufs=-27)

    def rock(d, r):
        def g(rr, i):
            return impact('stone', rr.uniform(600, 2600), .3, .8, .12, int(rr.integers(1e9))) * rr.uniform(.25, 1)
        y = grains(d, lambda t: 30, g, r); y += ticks(d, lambda t: 150, r, 1500, 6000, 0.003) * .25
        y += lp(noise(n_of(d), 'brown', r), 300) * 0.25 * smooth(n_of(d), 4, r, .5)
        return y
    L('grain_rock_pour', loop_of(lambda d: rock(d, rng(seed_of('rockp')))), meta=dict(drive='flow rate -> gain and rate'), lufs=-26)

    def metal(d, r):
        def g(rr, i):
            return impact('steel', rr.uniform(2500, 7000), .2, .9, .08, int(rr.integers(1e9))) * rr.uniform(.2, 1)
        y = grains(d, lambda t: 40, g, r); y += ticks(d, lambda t: 200, r, 4000, 11000, 0.0015) * .2
        return y
    L('grain_metal_pour', loop_of(lambda d: metal(d, rng(seed_of('metp')))), meta=dict(drive='flow rate -> gain'), lufs=-28)

    def slump(size):
        def f(i):
            r = rng(seed_of('slump%s' % size, i)); d = 1.3 if size == 's' else 3.2; n = n_of(d); t = np.arange(n) / SR
            tau = .4 if size == 's' else 1.1
            env = S.env_attack(n, 0.05) * np.exp(-t / tau)
            y = S.tv_filter(noise(n, 'pink', r), 2500 * np.exp(-t / tau) + 250, 'lp', 2) * env
            y += ticks(d, lambda tt_: (150 if size == 's' else 280) * math.exp(-tt_ / tau), r, 500, 5000, 0.005) * 0.4
            y += lp(noise(n, 'brown', r), 120 if size == 'l' else 220) * env * (1.5 if size == 'l' else 0.6)
            put(y, sine(70 if size == 'l' else 110, .4, .15) * (1.0 if size == 'l' else .4), 0.02)
            return y
        return f
    V('pile_slump_small', 4, slump('s'), peak=-8, weight=3, meta=mat_meta('granular', 's', (0.5, 5), dict(note='pile collapses; material picks pitch via lowpass')))
    V('pile_slump_large', 4, slump('l'), peak=-3, weight=6, max_dist=160, meta=mat_meta('granular', 'l', (1, 10)))

    def slide(d, r):
        n = n_of(d); y = S.tv_filter(noise(n, 'pink', r), 1800 * (0.5 + 0.5 * smooth(n, 2, r)) + 300, 'lp', 2) * (0.6 + 0.4 * smooth(n, 6, r))
        y += ticks(d, lambda t: 120, r, 700, 5000, 0.005) * .5 + lp(noise(n, 'brown', r), 150) * 0.5
        return y
    L('mat_slide_loop', loop_of(lambda d: slide(d, rng(seed_of('slide')))), meta=dict(drive='sliding mass speed -> gain, lowpass, rate'), lufs=-26, peak=-5)

    def thud(i):
        r = rng(seed_of('thud', i)); n = n_of(0.3); out = np.zeros(n)
        put(out, sweep(jit(r, 120, .2), 55, .2, tau=.06), 0, 1)
        put(out, lp(noise(n, 'white', r), 500) * edec(n, 0.03), 0, .4)
        return out
    V('mat_thud_soft', 6, thud, peak=-9, weight=2, meta=mat_meta('soft', 'm', (0.3, 6), dict(note='sand/earth/body landing')))

    def dig(i):
        r = rng(seed_of('dig', i)); d = .8; n = n_of(d); t = np.arange(n) / SR; out = np.zeros(n)
        put(out, S.tv_filter(noise(n_of(.45), 'pink', r), 3000 * np.exp(-np.arange(n_of(.45)) / SR / .2) + 400, 'lp') * np.sin(np.pi * np.linspace(0, 1, n_of(.45))) ** .8, 0, .7)
        put(out, ticks(.5, lambda tt_: 200 * math.exp(-tt_ / .2), r, 1500, 7000, 0.003), 0, .5)
        put(out, sweep(100, 60, .15, tau=.05), .42, .5)
        return out
    V('mat_dig', 4, dig, peak=-9, weight=2, meta=mat_meta('earth', 's', (0.5, 3), dict(note='Dig tool stroke')))

    def drum(i):
        r = rng(seed_of('dr', i)); n = n_of(0.9); f0 = jit(r, 95, .2); t = np.arange(n) / SR
        y = np.sin(2 * np.pi * np.cumsum(f0 * (1 + 0.6 * np.exp(-t / .05))) / SR) * np.exp(-t / .22)
        y += 0.5 * np.sin(2 * np.pi * f0 * 1.6 * t) * np.exp(-t / .12)
        y += 0.3 * resonator(noise(n, 'white', r), 380, 8) * edec(n, .1)
        put(y, burst(r, .015, 1500, 6000, .003), 0, .35)
        return y
    V('mat_drum_hollow', 4, drum, peak=-6, weight=3, meta=mat_meta('plastic-drum', 'm', (0.5, 8)))

    def ball(i):
        r = rng(seed_of('ball', i)); d = 1.6; out = Z(d); t = 0.0; g = 1.0; gap = jit(r, .34, .1); f0 = jit(r, 170, .15)
        while gap > 0.045 and t < d - .1:
            hit = sweep(f0 * 1.35, f0 * .8, .09, tau=.035) + burst(r, .006, 1000, 5000, .002) * .3
            put(out, hit, t, g); t += gap; gap *= .66; g *= .62
        return out
    V('mat_ball_bounce', 4, ball, peak=-9, weight=2, meta=mat_meta('rubber', 's', (1, 8), dict(note='whole sequence; skip if you animate bounces yourself and use mat_thud_soft')))


# ---------------------------------------------------------------- lava / glass / misc
def lava_misc():
    def lava(d, r):
        n = n_of(d); t = np.arange(n) / SR
        y = lp(noise(n, 'brown', r), 160) * 1.0 * (0.7 + 0.3 * smooth(n, 0.8, r))
        y += lp(noise(n, 'pink', r), 700) * 0.25 * smooth(n, 2, r)
        y += bubble_cloud(d, 90, 420, 4, 1e9, r, 3.0, 1.2) * 1.2
        y += ticks(d, lambda t: 18, r, 1500, 6500, 0.003) * 0.35
        y += hp(noise(n, 'white', r), 4000) * 0.03 * smooth(n, 4, r)
        return y
    L('lava_flow_loop', loop_of(lambda d: lava(d, rng(seed_of('lava')))), weight=3, meta=dict(drive='lava cell count within 40 m -> gain; flow speed -> rate'), lufs=-26)

    def lcrack(i):
        r = rng(seed_of('lcc', i)); d = .8; out = Z(d)
        put(out, burst(r, 0.015, 600, 7000, 0.004), 0, 1)
        put(out, impact('stone', jit(r, 600, .2), 1.2, .8, .25, i + 2100, thump=.7), 0, .7)
        put(out, ticks(.5, lambda t: 60 * math.exp(-t / .12), r, 1000, 5000), 0.02, .5)
        put(out, bubble_cloud(.5, 120, 400, 20, .15, r, 2.5), .03, .6)
        return out
    V('lava_crust_crack', 4, lcrack, peak=-8, weight=3, meta=mat_meta('lava-crust', 'm', (0, 2)))

    def lhw(i):
        r = rng(seed_of('lhw', i)); d = 2.6; n = n_of(d); t = np.arange(n) / SR
        env = (1 - np.exp(-t / .06)) * np.exp(-np.maximum(0, t - .2) / 1.2)
        y = S.tv_filter(noise(n, 'white', r), 1200 + 5000 * (1 - np.exp(-t / .4)), 'hp', 2) * env * .7
        y += bubble_cloud(d, 150, 900, 130, .7, r, 1.8) * .6
        put(y, sweep(90, 40, .5, tau=.2), 0, 1.0); put(y, burst(r, .05, 400, 6000, .012), 0, 1)
        y += lp(noise(n, 'pink', r), 500) * env * .3
        return y
    V('lava_hit_water_hiss', 4, lhw, peak=-4, weight=5, max_dist=140, meta=mat_meta('lava+water', 'l', (0, 4), dict(note='steam explosion burst; scale gain with lava mass')))

    def gform(i):
        r = rng(seed_of('gf', i)); f = jit(r, 1320, .35)
        return impact('glass', f, 1.2, .5, 1.6, i + 2200) * 0.8
    V('glass_form_ping', 4, gform, peak=-11, weight=1, lazy=True, meta=mat_meta('glass', 's', (0, 1), dict(note='sand fuses into glass: soft warm ping')))

    def furnace(d, r):
        n = n_of(d); t = np.arange(n) / SR
        y = lp(noise(n, 'pink', r), 900) * (0.6 + 0.4 * smooth(n, 1.5, r)) + lp(noise(n, 'brown', r), 120) * 1.2
        y *= 1 + 0.15 * np.sin(2 * np.pi * 6 * t)
        y += hp(noise(n, 'white', r), 3500) * .05 * smooth(n, 5, r) + ticks(d, lambda t: 10, r, 1000, 5000) * .2
        return y
    L('furnace_roar_loop', loop_of(lambda d: furnace(d, rng(seed_of('furn')))), weight=3, meta=dict(drive='furnace heat -> gain, lowpass'), lufs=-25)

    def seed(i):
        r = rng(seed_of('seed', i)); d = .9; out = Z(d)
        out += ticks(d, lambda t: 70 * math.exp(-t / .3) + 4, r, 2500, 8500, 0.002, spread=(.2, .8))
        out += pings(d, lambda t: 8 * math.exp(-t / .3), r, 3000, 7000, 0.01) * .15
        return out
    V('seed_scatter_patter', 4, seed, peak=-12, weight=1, lazy=True, meta=mat_meta('seed', 's', (0, 1), dict(note='Seed tool scatter')))

    def sprout(i):
        r = rng(seed_of('sprout', i)); d = 1.4; out = Z(d)
        notes = [784, 988, 1175, 1568]; start = r.integers(0, 2)
        for k, f in enumerate(notes[start:start + 3]):
            f = f * jit(r, 1, .005)
            put(out, S.tone(f, 1.0, harmonics=(1, .3, .1), decay=.25, attack=.004), k * .09, .6 - .12 * k)
            put(out, S.tone(f * 2.76, .5, harmonics=(1,), decay=.08, attack=.002), k * .09, .08)
        return out
    V('sprout_chime', 4, sprout, peak=-14, weight=1, lazy=True, meta=mat_meta('chime', 's', (0, 0), dict(note='sapling sprouts; soft and rare')))

    def quake(i):
        r = rng(seed_of('qc', i)); d = 1.8; out = Z(d)
        put(out, sweep(80, 28, .7, tau=.25), 0, 1.0)
        put(out, burst(r, .03, 200, 5000, .006), .0, .8)
        put(out, resonator(noise(n_of(1.2), 'white', r), jit(r, 140, .2), 2.5) * edec(n_of(1.2), .35), .02, .8)
        put(out, ticks(1.2, lambda t: 40 * math.exp(-t / .5), r, 400, 3500, 0.008), .05, .7)
        put(out, impact('stone', jit(r, 240, .3), 2.0, .5, .6, i + 2300, thump=.8), .25, .6)
        return out
    V('quake_crack', 4, quake, peak=-3, weight=8, max_dist=240, meta=mat_meta('ground', 'xl', (0, 5), dict(note='ground fractures during a quake')))

    def rain(d, r):
        def g(rr, i):
            return impact('stone', rr.uniform(500, 2400), .5, .55, .18, int(rr.integers(1e9))) * rr.uniform(.15, 1)
        y = grains(d, lambda t: 22 + 14 * math.sin(t * 1.3), g, r)
        y += ticks(d, lambda t: 90, r, 800, 5500, 0.004) * .4 + lp(noise(n_of(d), 'brown', r), 250) * 0.3 * smooth(n_of(d), 3, r, .5)
        return y
    L('rubble_rain', loop_of(lambda d: rain(d, rng(seed_of('rrain')))), meta=dict(drive='falling debris count -> gain'), lufs=-27)


def render():
    S.set_manifest('materials')
    wood(None); stone(); metal(); glass(); ice(); terrain(); lava_misc()


if __name__ == '__main__':
    render()
