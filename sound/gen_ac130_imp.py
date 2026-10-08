"""AC-130 per-surface impact stems: Vulcan (tiny sharp hits + stitch burst) and 40 mm Bofors (rich crump + crack + zing + debris).
    python gen_ac130_imp.py [--no-deploy]
Existing ac130_bofors_hit_NN (generic) is untouched and keeps working."""
import math, os, sys, json, shutil
import numpy as np
import synthlib as S
import gen_util as U
from gen_heavy import *
import gen_ac130 as A

CLASS_RMS['hit'] = -22.0
SURF = ['dirt', 'concrete', 'metal', 'water']


def zing(r, f0=None, dur=None, lvl=1.0):
    f0 = f0 or r.uniform(4200, 7500); dur = dur or r.uniform(0.12, 0.35); n = n_of(dur); t = tt(n)
    f = f0 * np.exp(-t / (dur * 0.5)) + 1200; ph = TWO_PI * np.cumsum(f) / SR
    return (np.sin(ph) + 0.3 * np.sin(2.01 * ph)) * np.exp(-t / (dur * 0.35)) * np.minimum(1, t / 0.002) * lvl


def ticks_at(r, dur, k, t0, t1, lo, hi, lvl):
    out = np.zeros(n_of(dur))
    for _ in range(k):
        put(out, tickn(r, r.uniform(0.002, 0.007), r.uniform(lo, lo * 1.8), r.uniform(hi * 0.6, hi), r.uniform(0.3, 1) * lvl), r.uniform(t0, t1), 1.0)
    return out


# ------------------------------------------------------------------ Vulcan hits (0.15 to 0.5 s)
def v_dirt(r, i):
    d = 0.35
    return sumv(thump(n_of(d), r.uniform(80, 120), 0.03, 1.0, 0.3),
                body(r, 0.2, r.uniform(1200, 2500), 0.05, 0.9, 200),
                ticks_at(r, d, r.integers(2, 5), 0.01, 0.2, 700, 3000, 0.35))


def v_concrete(r, i):
    d = 0.3
    return sumv(crack(r, 0.05, 1800, 9500, 0.0025, 1.3), thump(n_of(d), 150, 0.012, 0.4, 0.2),
                ticks_at(r, d, r.integers(4, 8), 0.01, 0.22, 2500, 9000, 0.5),
                zing(r, None, r.uniform(0.1, 0.22), 0.35) * (1 if i % 2 == 0 else 0.0))


def v_metal(r, i):
    d = 0.5; f = r.uniform(900, 2300)
    ping = pingn(f, 0.07, d, ((1, 1.0, 1.0), (2.76, 0.5, 0.6), (5.4, 0.3, 0.35)), None, r)
    return sumv(fit(ping, n_of(d)) * 0.8, crack(r, 0.03, 2500, 10000, 0.0015, 1.0), zing(r, None, r.uniform(0.15, 0.3), 0.5))


def v_water(r, i):
    d = 0.35
    bub = U.bubble(r, 600, 1900) * 1.2
    return sumv(fit(bub, n_of(d)), crack(r, 0.12, 1500, 6500, 0.02, 0.8), fit(U.bubble(r, 1500, 3200) * 0.5, n_of(d)),
                ticks_at(r, d, r.integers(2, 4), 0.05, 0.3, 3000, 8000, 0.25))


def v_person(r, i):
    d = 0.3     # cartoon thump, cloth slap, no vocal
    return sumv(thump(n_of(d), r.uniform(95, 140), 0.045, 1.0, 0.35), body(r, 0.15, 900, 0.04, 0.8, 120), tickn(r, 0.004, 1200, 4500, 0.4, n_of(d)))


V_MAKERS = dict(dirt=v_dirt, concrete=v_concrete, metal=v_metal, water=v_water, person=v_person)


def m_stitch(r, i):
    d = 1.15; out = np.zeros(n_of(d)); t = 0.0; w = [('dirt', 4), ('concrete', 2), ('metal', 1), ('dirt', 2)]
    names = ['dirt', 'dirt', 'dirt', 'concrete', 'concrete', 'metal', 'dirt', 'water'] if i == 2 else ['dirt', 'dirt', 'concrete', 'dirt', 'metal', 'dirt', 'dirt', 'concrete']
    k = 0
    while t < 0.95:
        nm = names[k % len(names)]; k += 1
        h = V_MAKERS[nm](r, k)
        put(out, h * r.uniform(0.6, 1.0), t, 1.0)
        t += 1.0 / 66.7 * r.integers(2, 4) * r.uniform(0.85, 1.15)    # every 2-3 rounds => about 25 hits
    return out * (0.6 + 0.4 * np.sin(np.pi * np.clip(tt(len(out)) / d, 0, 1)) ** 0.5)


# ------------------------------------------------------------------ Bofors hits (about 1.3 s)
def bof_core(r, d, pj, crack_hi, crump):
    s = sub(d * 0.8, 105 * pj, 38 * pj, 0.06, 0.22 * crump, 0.003, 0.15)
    c = sumv(crack(r, 0.1, 600, crack_hi, 0.006, 1.2), crack(r, 0.25, 130, 1200, 0.04, 1.1), body(r, 0.5, 450, 0.12 * crump, 1.1, 60))
    return sumv(fit(s, n_of(d)), c)


def b_dirt(r, i):
    d = 1.4; pj = r.uniform(0.92, 1.08)
    cloud = unit(lp(noise(n_of(d), 'white', r), 1100, SR, 2)) * np.exp(-tt(n_of(d)) / 0.3) * np.minimum(1, tt(n_of(d)) / 0.03) * 0.5
    return sumv(bof_core(r, d, pj, 6500, 1.3), cloud, debris(r, d, 0.12, 80, 0.5, 400, 3500, 0.75, 0.6),
                mix(d, [(zing(r, None, None, 0.3), 0.05, 1.0), (zing(r, None, None, 0.22), 0.1 + 0.05 * i, 1.0)]),
                tail(r, d - 0.05, 0.4, 0.2, 700, 150, 0.7, 0.2, 0.02) * 0.5)


def b_concrete(r, i):
    d = 1.3; pj = r.uniform(0.92, 1.08)
    return sumv(bof_core(r, d, pj, 10000, 0.9), crack(r, 0.06, 2500, 11000, 0.003, 1.0),
                debris(r, d, 0.1, 140, 0.45, 1500, 8000, 0.25, 0.7),
                mix(d, [(zing(r, None, None, 0.45), 0.03, 1.0), (zing(r, None, None, 0.35), 0.06 + 0.03 * i, 1.0), (zing(r, None, None, 0.25), 0.14, 1.0)]),
                echoes(tail(r, d - 0.05, 0.35, 0.2, 1200, 250, 0.6, 0.35, 0.02), [(0.1, 0.4, 1500), (0.22, 0.25, 900)]) * 0.5)


def b_metal(r, i):
    d = 1.5; pj = r.uniform(0.92, 1.08); f = r.uniform(380, 700)
    ring = fit(pingn(f, 0.22, d, ((1, 1.0, 1.0), (2.32, 0.6, 0.7), (4.1, 0.45, 0.45), (6.7, 0.25, 0.3)), None, r), n_of(d)) * 0.8
    return sumv(bof_core(r, d, pj, 9000, 0.8), ring, debris(r, d, 0.15, 70, 0.6, 1800, 7500, 0.15, 0.6),
                mix(d, [(zing(r, None, None, 0.5), 0.02, 1.0), (zing(r, None, None, 0.4), 0.05 + 0.02 * i, 1.0), (zing(r, None, None, 0.3), 0.11, 1.0)]),
                tail(r, d - 0.05, 0.3, 0.25, 1500, 300, 0.4, 0.4, 0.02) * 0.4)


def b_water(r, i):
    d = 1.7; pj = r.uniform(0.92, 1.08); n = n_of(d); t = tt(n)
    plume = unit(bp(noise(n, 'white', r), 700, 4800, SR, 2)) * np.exp(-t / 0.28) * np.minimum(1, t / 0.01) * 0.9
    bub = U.bubble_cloud(d, 200, 1400, 60, 0.35, r) * 0.7
    drops = ticks_at(r, d, 70, 0.35, 1.5, 2500, 8000, 0.28)
    s = fit(sub(d * 0.6, 85 * pj, 40 * pj, 0.07, 0.3, 0.004, 0.1), n)
    return sumv(s, crack(r, 0.1, 500, 7000, 0.012, 1.0), body(r, 0.5, 500, 0.12, 1.0, 60), plume, fit(bub, n), drops,
                mix(d, [(zing(r, None, None, 0.2), 0.05, 1.0)]), tail(r, d - 0.05, 0.4, 0.2, 600, 120, 0.8, 0.2, 0.03) * 0.5)


B_MAKERS = dict(dirt=b_dirt, concrete=b_concrete, metal=b_metal, water=b_water)


def reg(stem, mk, count, cls, bus, far=None, loop=False, **kw):
    tags = kw.pop('tags')
    for i in range(count):
        r = rng(U.seed_of(stem, i)); x = mk(r, i)
        stage_save('%s_%02d' % (stem, i + 1), x, cls, bus, variants=count, group='weapons', tags=tags, rate=(0.94, 1.06), **kw)
        if far and i < far['count']:
            rf = rng(U.seed_of(far['stem'], i)); fx = A.far_mix(x / (np.max(np.abs(x)) + 1e-9), rf, far['lp'], far['delay'], far['rt'], far['wet'], far['fc'])
            stage_save('%s_%02d' % (far['stem'], i + 1), fx, 'far', bus, variants=far['count'], group='weapons', tags=tags + ['far'], rate=(0.94, 1.06),
                       gain=0.7, weight=max(2, kw.get('weight', 5) - 3), max_dist=1500)
    print('rendered', stem, flush=True)


def render():
    S.set_manifest('ac130imp')
    for sf, mk in V_MAKERS.items():
        reg('ac130_vulcan_hit_' + sf, mk, 4, 'hit', 'mat', weight=4, max_dist=250, tags=['impact', 'ac130', 'vulcan', sf])
    reg('ac130_vulcan_stitch', m_stitch, 3, 'loop', 'mat', far=dict(stem='ac130_vulcan_stitch_far', count=3, lp=900, delay=0.1, rt=0.8, wet=0.4, fc=700),
        weight=6, max_dist=500, tags=['impact', 'ac130', 'vulcan', 'stitch'])
    for sf, mk in B_MAKERS.items():
        reg('ac130_bofors_hit_' + sf, mk, 4, 'fire', 'mat', far=dict(stem='ac130_bofors_hit_%s_far' % sf, count=3, lp=650, delay=0.15, rt=1.4, wet=0.6, fc=550),
            weight=8, max_dist=600, tags=['impact', 'ac130', 'bofors', '40mm', sf])


def deploy():
    here = os.path.dirname(os.path.abspath(__file__)); dst = os.path.join(os.path.dirname(here), 'audio')
    frag = json.load(open(os.path.join(here, 'out', 'manifest.ac130imp.json'), encoding='utf-8'))
    mp = os.path.join(dst, 'manifest.json'); man = json.load(open(mp, encoding='utf-8'))
    for id_, e in frag.items():
        shutil.copy2(os.path.join(here, 'out', id_ + '.ogg'), os.path.join(dst, id_ + '.ogg')); man['assets'][id_] = e
    json.dump(man, open(mp, 'w', encoding='utf-8')); print('deployed %d' % len(frag))


if __name__ == '__main__':
    render()
    if '--no-deploy' not in sys.argv: deploy()
