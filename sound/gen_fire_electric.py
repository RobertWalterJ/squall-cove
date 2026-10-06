"""Fire, electricity, heat/cold hold tools (bus 'mat')."""
import math
import numpy as np
import synthlib as S
from synthlib import SR, rng, n_of, noise, lp, hp, bp, resonator
from gen_util import *


def V(name, count, maker, peak=-6, weight=2, max_dist=90, group='core', lazy=False, meta=None):
    S.variants(maker, name, count, bus='mat', peak=peak, weight=weight, max_dist=max_dist, group=group, lazy=lazy, meta=meta)


def L(name, x, lufs=-26, peak=-6, weight=2, max_dist=70, group='core', lazy=False, meta=None):
    S.save(name, x, bus='mat', loop=True, target_lufs=lufs, peak=peak, weight=weight, max_dist=max_dist, lazy=lazy, group=group, meta=meta)


def pop(r, f_lo=900, f_hi=5000, tau=0.012, lo_tone=0.0):
    d = tau * 8; k = n_of(d); c = r.uniform(f_lo, f_hi)
    x = noise(k, 'white', r) * np.exp(-np.arange(k) / (tau * SR))
    x = bp(x, c * 0.5, min(c * 1.8, 18000), SR, 1)
    x[:int(0.0005 * SR)] *= 0.3
    if lo_tone:
        x += lo_tone * np.sin(2 * math.pi * r.uniform(120, 300) * np.arange(k) / SR) * np.exp(-np.arange(k) / (tau * 2 * SR))
    return x


def crackle(d, r, rate, roar_lp, roar_g, hiss_g, big=0.0):
    n = n_of(d)
    def g(rr, i):
        big_ = rr.random() < (0.08 + big)
        return pop(rr, 700, 4500 if not big_ else 2500, 0.004 + 0.02 * rr.random() * (3 if big_ else 1), lo_tone=0.4 if big_ else 0) * (rr.uniform(.3, .8) if not big_ else rr.uniform(.9, 1.6))
    y = grains(d, lambda t: rate * (0.6 + 0.8 * (0.5 + 0.5 * math.sin(t * 1.7))), g, r)
    t = np.arange(n) / SR
    y += lp(noise(n, 'pink', r), roar_lp) * roar_g * smooth(n, 2.0, r, .5)
    y += hp(noise(n, 'white', r), 3000) * hiss_g * smooth(n, 7, r, .6)
    return y


def render():
    S.set_manifest('fire_electric')

    # ---------- fire
    def whoomp(i):
        r = rng(seed_of('whoomp', i)); d = 1.6; n = n_of(d); t = np.arange(n) / SR; out = np.zeros(n)
        put(out, sweep(jit(r, 85, .15), 38, .5, tau=.18), 0, 1.0)
        env = (1 - np.exp(-t / .08)) * np.exp(-np.maximum(0, t - .15) / .5)
        rise = S.tv_filter(noise(n, 'pink', r), 300 + 2500 * (1 - np.exp(-t / .3)), 'lp', 2) * env
        out += rise * 0.9
        out += hp(noise(n, 'white', r), 2500) * env * 0.12
        put(out, burst(r, 0.03, 200, 4000, 0.008), 0, .5)
        out += grains(d, lambda tt_: 30 * math.exp(-tt_ / .5), lambda rr, k: pop(rr, 700, 4000, .01), r) * .4
        return out
    V('fire_ignite_whoomp', 4, whoomp, peak=-5, weight=5, max_dist=160, meta=dict(note='fuel catches: gas/flammable ignites; size by fuel mass', massKg=[1, 5000]))

    for name, rate, rlp, rg, hg, big, lufs in [('s', 7, 220, .35, .02, 0.0, -29), ('m', 18, 380, .6, .05, .03, -27), ('l', 38, 650, 1.0, .09, .06, -25)]:
        L('fire_crackle_loop_' + name, loop_of(lambda d, rate=rate, rlp=rlp, rg=rg, hg=hg, big=big, nm=name: crackle(d, rng(seed_of('crk' + nm)), rate, rlp, rg, hg, big), 6.0),
          lufs=lufs, weight=2 + 'sml'.index(name), max_dist=60 + 30 * 'sml'.index(name), meta=dict(drive='burning cell/tree count near listener picks s/m/l; distance low-passes; flame intensity -> gain', size=name))

    def ext(i):
        r = rng(seed_of('ext', i)); d = 2.0; n = n_of(d); t = np.arange(n) / SR
        env = (1 - np.exp(-t / .05)) * np.exp(-np.maximum(0, t - .1) / .7)
        y = S.tv_filter(noise(n, 'white', r), 700 + 3500 * np.exp(-t / .6), 'hp', 2) * env * .7
        y = lp(y, 8000)
        y += bubble_cloud(d, 300, 1800, 90, .5, r, 1.0) * .4
        y += lp(noise(n, 'pink', r), 500) * env * .3
        put(y, burst(r, .03, 600, 5000, .008), 0, .8)
        return y
    V('fire_extinguish_hiss', 4, ext, peak=-8, weight=3, max_dist=100, meta=dict(note='fire put out by water/sand; scale with fire size'))

    def ember(i):
        r = rng(seed_of('ember', i)); n = n_of(0.2); out = np.zeros(n)
        put(out, pop(r, 900, 3800, jit(r, .007, .4), lo_tone=0.6), 0, 1)
        if r.random() < .5: put(out, pop(r, 1500, 5000, .005), r.uniform(.02, .06), .5)
        return out
    V('fire_ember_pop', 6, ember, peak=-15, weight=0.5, max_dist=40, meta=dict(note='single spark/ember; triggered stochastically near fire at rate by intensity'))

    def roar(d, r):
        n = n_of(d); t = np.arange(n) / SR
        y = lp(noise(n, 'pink', r), 1100) * (0.55 + 0.45 * smooth(n, 1.2, r)) + lp(noise(n, 'brown', r), 150) * 1.4 * smooth(n, .7, r, .4)
        y += S.tv_bandpass(noise(n, 'white', r), 600 + 500 * smooth(n, 1.5, r), 1.5, 2) * 0.35
        y += hp(noise(n, 'white', r), 3500) * .08 * smooth(n, 6, r)
        y += grains(d, lambda tt_: 40, lambda rr, k: pop(rr, 600, 3500, .012, .5) * rr.uniform(.4, 1.2), r) * .5
        return y
    L('fire_tree_burn_roar', loop_of(lambda d: roar(d, rng(seed_of('troar')))), lufs=-24, weight=4, max_dist=110, meta=dict(drive='burning tree count / canopy fire intensity -> gain; wind -> lowpass up'))

    def tfall(i):
        r = rng(seed_of('tfall', i)); d = 3.0; n = n_of(d); out = np.zeros(n)
        # creak and crack while the trunk gives
        cr = S.tv_bandpass(noise(n_of(.9), 'white', r), np.linspace(380, 900, n_of(.9)), .3, 2) * (0.5 + 0.5 * smooth(n_of(.9), 30, r)) * np.sin(np.pi * np.linspace(0, 1, n_of(.9)))
        put(out, cr, 0, .5)
        put(out, burst(r, .03, 1000, 9000, .006), .7, 1.0)
        put(out, ticks(.6, lambda t: 80 * math.exp(-t / .2), r, 800, 5000), .72, .6)
        # whoosh of branches
        wh = S.tv_filter(noise(n_of(1.1), 'white', r), 600 + 1800 * np.sin(np.pi * np.linspace(0, 1, n_of(1.1))), 'lp') * np.sin(np.pi * np.linspace(0, 1, n_of(1.1))) ** 1.5
        put(out, wh, .9, .45)
        # impact: thud + crash of branches
        t0 = 1.85 + r.uniform(0, .1)
        put(out, sweep(jit(r, 85, .15), 35, .6, tau=.2), t0, 1.2)
        put(out, burst(r, .5, 150, 4000, .12), t0, .7)
        put(out, ticks(1.0, lambda t: 70 * math.exp(-t / .3), r, 500, 4000, .008), t0, .6)
        out += grains(d, lambda tt_: 25 * math.exp(-tt_ / 1.4) + 5, lambda rr, k: pop(rr, 700, 4000, .012, .4), r) * .3 * S.env_attack(n, .1)
        return out
    V('fire_tree_fall', 4, tfall, peak=-3, weight=7, max_dist=180, meta=dict(note='burned-through tree topples; thud at about 1.9 s, pair with water splash if it lands in water'))

    # ---------- electricity
    def zap(i):
        r = rng(seed_of('zap', i)); d = jit(r, .42, .25); n = n_of(d); t = np.arange(n) / SR
        f = jit(r, 1800, .3) * np.exp(-t / (d * .6)) + 120
        ph = 2 * np.pi * np.cumsum(f * (1 + .15 * smooth(n, 80, r, 1) - .07)) / SR
        saw = (ph / np.pi % 2) - 1; sq = np.sign(np.sin(ph * .5))
        y = saw * .6 + sq * .35
        y = y * (0.4 + 0.6 * smooth(n, 300, r, 1))
        y = y * 0.5 + noise(n, 'white', r) * .5 * np.exp(-t / (d * .3))
        y = lp(hp(y, 150), 7000)
        y *= (1 - np.exp(-t / .002)) * np.exp(-t / (d * .55))
        return y
    V('elec_arc_zap', 6, zap, peak=-6, weight=3, max_dist=90, meta=dict(note='electric arc / short shock; pitch by voltage'))

    def hum(d, r):
        n = n_of(d); t = np.arange(n) / SR; f0 = 60.0
        mod = 1 + 0.08 * np.sin(2 * np.pi * 0.7 * t) + .04 * np.sin(2 * np.pi * 3.1 * t)
        y = 0
        for h, a in [(1, 1.0), (2, .8), (3, .5), (4, .25), (5, .22), (6, .12), (8, .08), (10, .05)]:
            y = y + a * np.sin(2 * np.pi * f0 * h * t + h * 1.3)
        y = y * mod
        buzz = lp(noise(n, 'white', r), 2500) * (0.5 + 0.5 * (np.sin(2 * np.pi * 120 * t) ** 2)) * 0.05 * smooth(n, 4, r, .5)
        return lp(y, 1500) + buzz
    L('elec_hum_loop', loop_of(lambda d: hum(d, rng(seed_of('hum'))), 4.0), lufs=-32, peak=-8, weight=2, max_dist=55, meta=dict(drive='charge / electric field strength -> gain, buzz grows with level; 60 Hz mains with harmonics, kept quiet'))

    def strike(i):
        r = rng(seed_of('strike', i)); d = 1.6; n = n_of(d); out = np.zeros(n)
        put(out, burst(r, .02, 400, 16000, .004), 0, 1.0)
        put(out, burst(r, .12, 300, 6000, .035), 0, .6)
        put(out, sweep(60, 28, .4, tau=.12), .005, .8)
        put(out, resonator(noise(n_of(.8), 'white', r), jit(r, 3300, .15), 40) * edec(n_of(.8), .12) * .25, 0)
        put(out, lp(noise(n_of(1.2), 'pink', r), 500) * edec(n_of(1.2), .35) * .4, .02)
        return out
    V('elec_strike_crack', 4, strike, peak=-3, weight=8, max_dist=240, meta=dict(note='lightning/arc strike near; weight>8 audible beyond cull distance; duck amb 6 dB'))

    def spark(d, r):
        n = n_of(d)
        y = grains(d, lambda t: 11, lambda rr, k: pop(rr, 2500, 9000, rr.uniform(.0015, .006)) * rr.uniform(.3, 1), r)
        y += grains(d, lambda t: 3, lambda rr, k: S.tone(rr.uniform(1500, 4000) , .03, harmonics=(1, .5), decay=.008, attack=.0005) * rr.uniform(.3, .7), r)
        y *= (0.5 + 0.5 * smooth(n, 1.5, r))
        y += hp(noise(n, 'white', r), 6000) * 0.01
        return y
    L('elec_spark_crackle', loop_of(lambda d: spark(d, rng(seed_of('spark')))), lufs=-29, peak=-3, weight=2, max_dist=55, meta=dict(drive='electrified area / charge -> gain and rate'))

    def shock(i):
        r = rng(seed_of('shock', i)); d = .5; n = n_of(d); out = np.zeros(n)
        put(out, sweep(jit(r, 180, .2), 70, .12, tau=.04), 0, 1.0)
        put(out, burst(r, .02, 500, 9000, .005), 0, .9)
        put(out, zap(i + 50)[:n_of(.25)], 0, .5)
        return out
    V('elec_shock_pop', 4, shock, peak=-6, weight=3, max_dist=80, meta=dict(note='person / object shocked; short, never punishing'))

    # ---------- tool holds
    def heat(d, r):
        n = n_of(d); y = hp(lp(noise(n, 'pink', r), 9000), 2500) * (0.6 + 0.4 * smooth(n, 8, r)) * .25
        y += lp(noise(n, 'pink', r), 400) * .5 * smooth(n, 2, r, .5)
        y += grains(d, lambda t: 12, lambda rr, k: pop(rr, 900, 3500, .01), r) * .4
        y += S.tv_bandpass(noise(n, 'white', r), 1800 + 1200 * smooth(n, 1.5, r), 1.0, 2) * .15
        return y
    L('heat_hold_hiss_loop', loop_of(lambda d: heat(d, rng(seed_of('heat')))), lufs=-27, peak=-7, weight=1, lazy=True, group='tools', meta=dict(note='hold-tool loop for the Heat tool; rises in gain as the held cell warms'))

    def cold(d, r):
        n = n_of(d); t = np.arange(n) / SR; src = noise(n, 'white', r)
        f = 700 + 500 * smooth(n, .8, r) ; f2 = 1500 + 700 * smooth(n, .6, r)
        y = S.tv_bandpass(src, f, .25, 2) * 1.0 + S.tv_bandpass(src, f2, .2, 2) * .6
        y *= (0.6 + 0.4 * smooth(n, 2, r)); y += hp(noise(n, 'pink', r), 5000) * .03 * smooth(n, 3, r)
        y += pings(d, lambda t: 2, r, 3500, 7500, .02, mat=3.45) * .07
        return y
    L('cold_hold_wind_loop', loop_of(lambda d: cold(d, rng(seed_of('cold')))), lufs=-27, peak=-7, weight=1, lazy=True, group='tools', meta=dict(note='hold-tool loop for the Cold tool; icy whistle with sparse crystal tinkles'))


if __name__ == '__main__':
    render()
