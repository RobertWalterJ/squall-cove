"""Four loopable ambience beds for the battle layer: distant battle, farm, town, quay. Events are placed circularly so every bed loops seamlessly."""
import math
import numpy as np
import synthlib as S
import gen_util as U
import svp_common as C
from wpn_common import *
import gen_weapons as W

DUR = 16.0


def periodic_hum(n, comps, r):
    """Sum of sines with an integer number of cycles in n samples (perfectly periodic)."""
    t = np.arange(n) / SR; y = np.zeros(n); T = n / SR
    for f, a in comps:
        f = round(f * T) / T; y += a * np.sin(TWO_PI * f * t + r.uniform(0, TWO_PI))
    return y


def cplace(buf, x, t, g=1.0): return C.circ_place(buf, x, t, g)


def bed(maker, dur=DUR, xf=0.6):
    return S.make_loop(maker(dur + xf), xf)


def far_pop(r, kind='rifle', lp_hz=None):
    s = W.far_shot(r, kind)
    return s[:n_of(1.6)]


def far_boom(r, dur=3.0, level=1.0):
    n = n_of(dur); t = np.arange(n) / SR
    f = 42 + 38 * np.exp(-t / 0.2)
    y = np.sin(TWO_PI * np.cumsum(f) / SR) * np.exp(-t / 0.7) + lp(noise(n, 'brown', r), 160, SR, 2) * np.exp(-t / 0.9) * 2.0
    y += lp(noise(n, 'white', r), 700, SR, 2) * np.exp(-t / 0.15) * 0.5
    for k in range(3):
        put(y, lp(noise(n_of(0.6), 'brown', r), 250, SR, 2) * edec(n_of(0.6), 0.2), 0.5 + 0.55 * k + r.uniform(0, 0.2), 0.4 / (k + 1))
    return fade_out(y * level * 0.5, 0.3)


def amb_battle(r):
    n = n_of(DUR); out = np.zeros(n)
    def wind(d):
        w = lp(noise(n_of(d), 'pink', r), 450, SR, 2); return w * S.smooth_random(len(w), 0.2, r, 0.5) * 0.02
    out += bed(wind)
    windows = [(0.8, 4.0), (8.2, 10.5), (12.4, 15.0)]                    # fire fights only inside windows; the rest is quiet
    for lo, hi in windows:
        t = r.uniform(lo, hi - 0.6); kind = r.choice(['rifle', 'smg', 'pistol']); cnt = int(r.integers(3, 8))
        for k in range(cnt):
            cplace(out, far_pop(r, str(kind)), t, r.uniform(0.12, 0.3))
            t += r.uniform(0.07, 0.28) if k % 3 else r.uniform(0.3, 0.6)
    for t in (5.6, 11.0):
        cplace(out, far_boom(r), t, r.uniform(0.5, 0.8))
    cplace(out, far_pop(r, 'sniper'), 6.8, 0.2)                           # one lone shot in the gap
    return out


def bird(r, f0=None):
    f0 = f0 or r.uniform(2400, 4800); k = int(r.uniform(0.05, 0.14) * SR); t = np.arange(k) / SR
    f = f0 * (1 + r.uniform(-0.3, 0.4) * np.sin(np.pi * t / t[-1] * r.uniform(1, 2.5)) + r.uniform(-0.2, 0.2))
    y = np.sin(TWO_PI * np.cumsum(f) / SR) * np.sin(np.pi * t / t[-1]) ** 1.5
    return y * r.uniform(0.3, 1.0)


def amb_farm(r):
    n = n_of(DUR); out = np.zeros(n)
    def crops(d):
        m = n_of(d); w = bp(noise(m, 'white', r), 600, 3200, SR, 2); w2 = lp(noise(m, 'pink', r), 300, SR, 2) * 0.6
        g = 0.2 + 0.8 * S.smooth_random(m, 0.3, r, 1.0) ** 1.5
        return (w * 0.04 + w2 * 0.03) * g
    out += bed(crops)
    for k in range(5):                                                 # phrases of birdsong
        t0 = r.uniform(0.3, DUR - 2.0); f0 = r.uniform(2800, 4600)
        for j in range(int(r.integers(2, 6))):
            cplace(out, bird(r, f0 * r.uniform(0.85, 1.2)), t0 + j * r.uniform(0.11, 0.2), r.uniform(0.012, 0.03))
    for t in (3.1, 9.7):                                               # a distant crow-ish lone chirp
        cplace(out, bird(r, 1600) * 1.2, t, 0.02)
    m = n_of(DUR); t = np.arange(m) / SR                                  # distant tractor: periodic engine, swells in and out
    eng = S.engine(780, 3, DUR, 77, rough=0.2, exhaust=0.8, load=0.3)[:m]
    eng = lp(eng, 380, SR, 2); eng /= (np.max(np.abs(eng)) + 1e-9)
    swell = np.sin(np.pi * np.clip((t - 2.0) / 11.5, 0, 1)) ** 2
    out += eng * swell * 0.05
    return out


def dog_bark(r, f0=300):
    dur = 0.16; n = n_of(dur); f = np.linspace(f0 * 1.25, f0 * 0.75, n)
    y = C.vocal(f, dur, [np.full(n, 700.0), np.full(n, 1250.0), np.full(n, 2600.0)], r, breath=0.5, env=np.sin(np.pi * np.linspace(0, 1, n)) ** 0.6 * np.exp(-np.linspace(0, 1, n) * 2))
    y = lp(y / (np.max(np.abs(y)) + 1e-9), 2600, SR, 2)
    out = np.zeros(n_of(0.6)); put(out, y, 0, 1.0); put(out, lp(y, 1300, SR, 2), 0.2, 0.25)               # a yard echo
    return out


def car_pass(r, dur=4.0, lvl=1.0):
    n = n_of(dur); t = np.linspace(0, 1, n); d = lp(noise(n, 'pink', r), 900, SR, 2)
    c = 500 + 700 * np.exp(-((t - 0.5) / 0.18) ** 2)
    return S.tv_filter(d, c, 'lp', 2, SR, 512) * np.sin(np.pi * t) ** 2 * lvl


def amb_town(r):
    n = n_of(DUR); out = np.zeros(n)
    def hush(d):
        m = n_of(d); w = lp(noise(m, 'pink', r), 700, SR, 2) * (0.5 + 0.5 * S.smooth_random(m, 0.25, r, 1.0)); return w * 0.05
    out += bed(hush)
    for t, d in [(1.0, 4.5), (8.5, 5.0), (13.0, 3.4)]:
        cplace(out, car_pass(r, d, 0.06), t, 1.0)
    for t0 in (4.2, 11.4):                                              # a dog, twice
        for j in range(int(r.integers(2, 4))):
            cplace(out, dog_bark(r, r.uniform(260, 340)), t0 + j * r.uniform(0.34, 0.5), 0.1)
    for t in (6.4, 14.3):                                               # faint distant door/clatter and a high-rise air-con hum
        cplace(out, bp(noise(n_of(0.12), 'white', r), 600, 3500, SR, 1) * edec(n_of(0.12), 0.02), t, 0.03)
    out += periodic_hum(n, [(95, 0.004), (190, 0.0025)], r)
    return out


def amb_quay(r):
    n = n_of(DUR); out = np.zeros(n)
    def water(d):
        m = n_of(d); sw = S.smooth_random(m, 0.18, r, 1.0)
        return lp(noise(m, 'pink', r), 1200, SR, 2) * 0.012 * (0.4 + 0.6 * sw)
    out += bed(water)
    def slap(rr, i):
        k = n_of(0.35); t = np.arange(k) / SR
        return (lp(hp(noise(k, 'white', rr), 150, SR, 1), rr.uniform(900, 1800), SR, 2) * np.exp(-t / rr.uniform(0.04, 0.09)) * np.minimum(1, t / 0.006)
                + thump(k, rr.uniform(80, 130), 0.05, 0.4)) * rr.uniform(0.3, 1.0)
    t = 0.0
    while t < DUR:                                                      # water slap, rate swells
        cplace(out, slap(r, 0), t, 0.05); t += r.exponential(0.9) + 0.18
    t = 0.3
    while t < DUR:                                                      # rigging clinks, bunched like gusts
        burst = int(r.integers(1, 5)); f = r.uniform(1600, 3600)
        for j in range(burst):
            cplace(out, pingn(f * r.uniform(0.9, 1.15), r.uniform(0.02, 0.05), 0.3, ((1, 1, 1), (2.76, .4, .5), (5.4, .2, .3)), r=r) + tickn(r, 0.002, 2500, 8000, 0.4), t + j * r.uniform(0.1, 0.4), r.uniform(0.01, 0.03))
        t += r.uniform(1.5, 3.5)
    out += periodic_hum(n, [(58, 0.006), (116, 0.004), (174, 0.0022), (2300, 0.0008)], r) * (0.7 + 0.3 * np.sin(TWO_PI * 3 * np.arange(n) / n))   # crane/dock machinery hum
    return out


def render():
    kw = dict(loop=True, rate=(1.0, 1.0), weight=3, quality=3, tags=['ambience', 'bed'])
    for nm, mk, lufs, bus, g in [('amb_battle_distant', amb_battle, -29, 'amb', 'weapons'), ('amb_farm', amb_farm, -30, 'amb', 'weather'),
                                 ('amb_town', amb_town, -30, 'amb', 'weather'), ('amb_quay', amb_quay, -29, 'amb', 'weather')]:
        r = rng(U.seed_of(nm))
        save(nm, mk(r), bus, g, target_lufs=lufs, max_dist=400, **kw)
