"""Water one-shots and loops (bus 'water')."""
import math
import numpy as np
import synthlib as S
from synthlib import SR, rng, n_of, noise, lp, hp, bp, resonator
from gen_util import *

# size class params
SPL = {
    'xs': dict(dur=0.45, fr=(2200, 6500), rate=380, tau=0.045, blp=11000, bhp=2500, btau=0.012, tf=None, tg=0, ds=0.6, stau=0.0, slp=0, pk=-12, mass=(0.005, 0.05), w=1.0, md=60),
    's':  dict(dur=0.8,  fr=(1000, 3800), rate=300, tau=0.09, blp=8500, bhp=900, btau=0.03, tf=(260, 110), tg=0.15, ds=1.0, stau=0.12, slp=7000, pk=-9, mass=(0.05, 1.0), w=2.0, md=90),
    'm':  dict(dur=1.4,  fr=(450, 1900), rate=260, tau=0.18, blp=5500, bhp=300, btau=0.06, tf=(150, 62), tg=0.45, ds=1.5, stau=0.3, slp=5000, pk=-6, mass=(1, 20), w=4.0, md=130),
    'l':  dict(dur=2.4,  fr=(220, 1000), rate=220, tau=0.32, blp=3600, bhp=120, btau=0.12, tf=(100, 42), tg=0.9, ds=2.3, stau=0.6, slp=3800, pk=-4.5, mass=(20, 300), w=7.0, md=190),
    'xl': dict(dur=4.0,  fr=(100, 600), rate=200, tau=0.55, blp=2400, bhp=50, btau=0.22, tf=(70, 30), tg=1.5, ds=3.3, stau=1.1, slp=2800, pk=-3, mass=(300, 5000), w=10.0, md=240),
}


def splash(k, i):
    p = SPL[k]; r = rng(seed_of('splash_' + k, i)); J = lambda v: jit(r, v, 0.12)
    n = n_of(p['dur']); out = np.zeros(n)
    fl, fh = J(p['fr'][0]), J(p['fr'][1])
    b = burst(r, min(p['dur'], p['btau'] * 8), p['bhp'], p['blp'] * r.uniform(.85, 1.15), J(p['btau']))
    put(out, b, 0, 1.0)
    bc = bubble_cloud(p['dur'], fl, fh, J(p['rate']), J(p['tau']), r, p['ds'], rise=r.uniform(1.4, 2.6))
    put(out, bc * 0.9, 0.004)
    if p['tf']:
        th = sweep(J(p['tf'][0]), J(p['tf'][1]), min(p['dur'], p['tau'] * 3 + .3), tau=p['tau'] * 0.9 + 0.05)
        put(out, th, 0.0, p['tg'])
    if p['stau'] > 0:
        sp = hp(lp(noise(n, 'white', r), p['slp']), 1500) * edec(n, J(p['stau'])) * 0.18 * S.env_attack(n, 0.03)
        out += sp
    if k in ('l', 'xl'):
        t2 = J(0.30 if k == 'l' else 0.55)
        d2 = p['dur'] - t2
        c = fit(burst(r, min(d2, 0.5), 60, p['blp'] * 0.5, 0.15 if k == 'l' else 0.25), d2)
        c += bubble_cloud(d2, fl * 0.8, fh * 0.7, p['rate'] * 0.6, p['tau'] * 0.9, r, p['ds'] * 1.1) * 0.8
        c += fit(sweep(55 if k == 'l' else 38, 30, 0.6, tau=0.25), d2) * (0.7 if k == 'l' else 1.1)
        put(out, c, t2, 0.6)
        if k == 'xl':
            roll = lp(noise(n, 'pink', r), 900) * S.env_attack(n, 0.4) * edec(n, 1.3) * smooth(n, 6, r, .6)
            out += roll * 0.5
    return out


def render():
    S.set_manifest('water')
    for k, p in SPL.items():
        S.variants(lambda i, k=k: splash(k, i), 'water_splash_' + k, 6, bus='water', peak=p['pk'], weight=p['w'], max_dist=p['md'], group='core',
                   meta=dict(sizeClass=k, massKg=list(p['mass']), pickBy='object mass (kg) at water entry; speed scales gain and lowpass', speedRange=[1, 25]))

    def rock_in(i):
        r = rng(seed_of('rock_in', i)); n = n_of(0.9); out = np.zeros(n)
        put(out, burst(r, 0.08, 500, jit(r, 6000), 0.02), 0, 1)
        put(out, sweep(jit(r, 230), 80, 0.4, tau=0.1), 0, 0.9)
        put(out, bubble_cloud(0.7, 300, 1300, 160, 0.14, r, 1.6), 0.01, 0.8)
        put(out, burst(r, 0.4, 200, 3000, 0.08) * 0.35, 0.28 + r.uniform(0, .05))
        return out
    S.variants(rock_in, 'water_rock_in', 4, bus='water', peak=-5, weight=4, max_dist=130, group='core', meta=dict(massKg=[0.5, 30], note='dense object; pitch by size'))

    def obj(small):
        def f(i):
            r = rng(seed_of('obj_%s' % small, i)); d = 0.55 if small else 1.3; n = n_of(d); out = np.zeros(n)
            put(out, burst(r, 0.06, 900 if small else 300, 8000 if small else 4500, 0.015 if small else 0.04), 0, 1)
            put(out, bubble_cloud(d, *((1200, 4200) if small else (350, 1500)), 220, 0.09 if small else 0.22, r, 0.8 if small else 1.8), 0.005, 0.8)
            if not small:
                put(out, sweep(jit(r, 110), 50, 0.5, tau=0.16), 0, 0.6); put(out, burst(r, 0.5, 100, 2500, 0.15) * .4, 0.12)
            put(out, hp(lp(noise(n, 'white', r), 6000), 2500) * edec(n, 0.08 if small else 0.2) * 0.1, 0)
            return out
        return f
    S.variants(obj(True), 'water_object_in_small', 4, bus='water', peak=-9, weight=2, max_dist=90, group='core', meta=dict(massKg=[0.05, 2], note='light/floating objects'))
    S.variants(obj(False), 'water_object_in_large', 4, bus='water', peak=-5, weight=5, max_dist=150, group='core', meta=dict(massKg=[20, 500], note='crates, barrels, blocks'))

    def drip(i):
        r = rng(seed_of('drip', i)); n = n_of(0.35); f0 = r.uniform(900, 1700); out = np.zeros(n)
        b = bubble(r, f0, f0, 1.6, rise=r.uniform(.6, 1.3)); put(out, b / np.max(np.abs(b)), 0)
        put(out, sine(f0 * 2.1, 0.1, 0.02) * 0.2, 0.0)
        put(out, burst(r, 0.01, 2000, 9000, 0.003) * 0.3, 0)
        return out
    S.variants(drip, 'water_drip', 4, bus='water', peak=-16, weight=1, max_dist=40, lazy=True, group='water', meta=dict(note='cave/leak/melt'))

    def bubbles(i):
        r = rng(seed_of('bubbles', i)); d = 1.3
        x = grains(d, lambda t: 25 + 60 * math.exp(-((t - .35) / .3) ** 2), lambda rr, k: bubble(rr, 250, 1500, 1.2, rise=rr.uniform(1, 4)), r)
        x = x * S.env_attack(len(x), 0.01) * np.exp(-np.maximum(0, np.arange(len(x)) / SR - 0.6) * 2.5)
        return x
    S.variants(bubbles, 'water_bubbles', 4, bus='water', peak=-12, weight=2, max_dist=60, lazy=True, group='water', meta=dict(note='sinking object / gas escaping; rate scales with volume'))

    def swash(i):
        r = rng(seed_of('swash', i)); d = r.uniform(2.2, 2.8); n = n_of(d)
        t = np.arange(n) / SR; env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.6 * np.exp(-t / 2.2)
        x = noise(n, 'white', r); fc = 600 + 5500 * env
        y = S.tv_filter(x, fc, 'lp', 2) * env
        y += bubble_cloud(d, 600, 3500, 90, 0.9, r, 1.0) * env * 0.4
        y += hp(noise(n, 'white', r), 3500) * np.clip((t - d * 0.55) / (d * 0.3), 0, 1) * edec(n, 0.6) * 0.15
        return y
    S.variants(swash, 'water_swash', 4, bus='water', peak=-14, weight=2, max_dist=90, lazy=True, group='water', meta=dict(note='wave run-up on a beach; gain by wave height, rate by swell period'))

    def pour(d, r):
        n = n_of(d); x = bp(noise(n, 'pink', r), 500, 6500) * (0.7 + 0.3 * smooth(n, 7, r))
        x += bubble_cloud(d, 400, 2800, 140, 1e9, r, 0.9) * 0.6
        x += lp(noise(n, 'pink', r), 350) * 0.3
        return x
    S.save('water_pour_loop', loop_of(lambda d: pour(d, rng(seed_of('pour')))), bus='water', loop=True, target_lufs=-26, peak=-6, weight=2, max_dist=70, lazy=True, group='water',
           meta=dict(drive='pour flow rate -> gain (0..1), rate 0.9..1.15'))

    def wake(d, r):
        n = n_of(d); x = lp(noise(n, 'pink', r), 3500) * (0.6 + 0.4 * smooth(n, 3, r, 1))
        x += hp(bubble_cloud(d, 500, 3500, 110, 1e9, r, 0.8), 400) * 0.5
        x += hp(noise(n, 'white', r), 4500) * 0.08 * smooth(n, 5, r)
        return x
    S.save('water_wake_loop', stereo_loop(wake), bus='water', loop=True, target_lufs=-26, peak=-6, weight=3, max_dist=100, lazy=True, group='water',
           meta=dict(drive='hull speed (m/s): gain 0..1 over 0..12, lowpass opens with speed, rate 0.85..1.3'))

    def slap(i):
        r = rng(seed_of('slap', i)); d = 0.55; n = n_of(d); out = np.zeros(n)
        put(out, burst(r, 0.05, 700, jit(r, 5000), 0.012), 0, 1)
        put(out, sweep(jit(r, 170), 90, 0.25, tau=0.07), 0, 0.8)
        put(out, bubble_cloud(0.4, 500, 2000, 140, 0.1, r, 1.1), 0.01, 0.55)
        put(out, resonator(noise(n_of(0.3), 'white', r), jit(r, 260), 14) * edec(n_of(0.3), 0.08) * 0.4, 0.003)
        return out
    S.variants(slap, 'water_hull_slap', 6, bus='water', peak=-8, weight=2, max_dist=70, lazy=True, group='water', meta=dict(drive='wave height at hull and relative motion'))

    def boil(d, r):
        n = n_of(d); x = hp(noise(n, 'white', r), 3500) * 0.35 * (0.7 + 0.3 * smooth(n, 9, r))
        x += bubble_cloud(d, 180, 900, 55, 1e9, r, 1.5, 1.6) * 0.9
        x += lp(noise(n, 'pink', r), 500) * 0.25 * smooth(n, 4, r, .5)
        return x
    S.save('water_boil_hiss', loop_of(lambda d: boil(d, rng(seed_of('boil')))), bus='water', loop=True, target_lufs=-26, peak=-6, weight=3, max_dist=70, lazy=True, group='water',
           meta=dict(drive='hot water / lava contact; gain by hot cell count'))

    def quench(i):
        r = rng(seed_of('quench', i)); d = 1.8; n = n_of(d); t = np.arange(n) / SR
        env = (1 - np.exp(-t / 0.12)) * np.exp(-np.maximum(0, t - 0.25) / 0.8)
        steam = S.tv_filter(noise(n, 'white', r), 1500 + 6500 * (1 - np.exp(-t / 0.5)), 'hp', 2) * env
        steam = lp(steam, 11000)
        ch = bubble_cloud(d, 400, 2600, 110, 0.55, r, 0.9) * 0.6
        out = steam * 0.7 + ch; put(out, burst(r, 0.04, 900, 7000, 0.01), 0, 1)
        out += lp(noise(n, 'pink', r), 400) * env * 0.25
        return out
    S.variants(quench, 'water_quench_hiss', 4, bus='water', peak=-8, weight=3, max_dist=90, lazy=True, group='water', meta=dict(drive='object temperature (hotter = louder), mass scales gain'))

    def trickle(d, r):
        n = n_of(d); x = bubble_cloud(d, 700, 3800, 16, 1e9, r, 0.8)
        x += bp(noise(n, 'white', r), 1500, 5000) * 0.07 * smooth(n, 6, r)
        x += ticks(d, lambda t: 10, r, 2500, 7000, 0.003) * 0.15
        return x
    S.save('water_flood_trickle', loop_of(lambda d: trickle(d, rng(seed_of('trickle')))), bus='water', loop=True, target_lufs=-28, peak=-8, weight=1, max_dist=45, lazy=True, group='water',
           meta=dict(drive='flowing water cell count near camera'))

    def tick(i):
        r = rng(seed_of('ripple', i)); n = n_of(0.12); f = r.uniform(2500, 4200)
        out = np.zeros(n); b = bubble(r, f, f, 0.4, 1.0); put(out, b / np.max(np.abs(b)), 0); put(out, burst(r, 0.008, 3000, 10000, 0.002) * 0.4, 0)
        return out
    S.variants(tick, 'water_ripple_tick', 4, bus='water', peak=-18, weight=0.5, max_dist=25, lazy=True, group='water', meta=dict(note='tiny drop on surface'))


if __name__ == '__main__':
    render()
