"""AC-130 per-surface impact stems: Vulcan (tiny sharp hits + stitch burst) and 40 mm Bofors (rich crump + crack + zing + debris).
    python gen_ac130_imp.py [--no-deploy]
Existing ac130_bofors_hit_NN (generic) is untouched and keeps working."""
import math, os, sys, json, shutil
import numpy as np
import synthlib as S
import gen_util as U
from gen_heavy import *
import gen_ac130 as A
import gen_heavy as H

CLASS_RMS['hit'] = -22.0
SURF = ['dirt', 'concrete', 'metal', 'water']


def zing(r, f0=None, dur=None, lvl=1.0):
    f0 = f0 or r.uniform(4200, 7500); dur = dur or r.uniform(0.05, 0.14); n = n_of(dur); t = tt(n)
    f = f0 * np.exp(-t / (dur * 0.5)) + 1200; ph = TWO_PI * np.cumsum(f) / SR
    return (np.sin(ph) + 0.3 * np.sin(2.01 * ph)) * np.exp(-t / (dur * 0.35)) * np.minimum(1, t / 0.002) * lvl


def ticks_at(r, dur, k, t0, t1, lo, hi, lvl):
    out = np.zeros(n_of(dur))
    for _ in range(k):
        put(out, tickn(r, r.uniform(0.002, 0.007), r.uniform(lo, lo * 1.8), r.uniform(hi * 0.6, hi), r.uniform(0.3, 1) * lvl), r.uniform(t0, t1), 1.0)
    return out


# ------------------------------------------------------------------ Vulcan hits (0.15 to 0.5 s)
def punch(r, pj=1.0, lvl=1.0, f0=170.0, f1=62.0, tau=0.022):
    """Heavy low front: fast-attack 60-180 Hz sub drop plus a short low-mid slap, about 70 ms, tight tail."""
    return sumv(sub(0.07, f0 * pj, f1 * pj, 0.006, tau, 0.0004, 0.2), body(r, 0.03, 320, 0.008, 0.9, 70) * 0.8) * lvl


def zip_short(r, f0, f1, dur, lvl=1.0):
    """Brief pitch-falling zip (20 to 80 ms) with a very fast decay."""
    n = n_of(dur); t = tt(n); f = f1 + (f0 - f1) * np.exp(-t / (dur * 0.35)); ph = TWO_PI * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / (dur * 0.28)) * np.minimum(1, t / 0.0006) * lvl


def hiss_short(r, dur, lo, hi, lvl=1.0):
    n = n_of(dur); t = tt(n)
    return unit(bp(noise(n, 'white', r), lo, hi, SR, 2)) * np.exp(-t / (dur * 0.3)) * np.minimum(1, t / 0.0006) * lvl


def grit(r, k, t0, t1, lvl=1.0, lo=4000, hi=11000):
    out = np.zeros(n_of(t1 + 0.02))
    for _ in range(k):
        put(out, tickn(r, r.uniform(0.001, 0.003), r.uniform(lo, lo * 1.5), r.uniform(hi * 0.8, hi), r.uniform(0.5, 1.0) * lvl), r.uniform(t0, t1), 1.0)
    return out


def place(d, parts):
    buf = np.zeros(n_of(d))
    for x, t in parts: put(buf, x, t, 1.0)
    return buf


def v_dirt(r, i):
    pj = r.uniform(0.92, 1.08)
    return place(0.25, [(punch(r, pj, 1.6), 0.0), (body(r, 0.08, 900, 0.02, 0.45, 150), 0.01), (hiss_short(r, 0.06, 4500, 11500, 0.7), 0.012),
                        (grit(r, 7, 0.012, 0.11, 0.9), 0.0), (zip_short(r, r.uniform(7500, 10500), 3500, r.uniform(0.03, 0.05), 0.3), 0.02)])


def v_concrete(r, i):
    pj = r.uniform(0.92, 1.08)
    return place(0.25, [(punch(r, pj, 1.4, 190, 70, 0.018), 0.0), (crack(r, 0.03, 3000, 12000, 0.0015, 1.3), 0.003),
                        (grit(r, 8, 0.008, 0.1, 1.0, 4500, 12000), 0.0), (zip_short(r, r.uniform(9500, 12500), 4000, r.uniform(0.04, 0.075), 0.7), 0.015)])


def v_metal(r, i):
    pj = r.uniform(0.92, 1.08); f = r.uniform(2200, 3800)
    ping = fit(pingn(f, 0.018, 0.08, ((1, 1.0, 1.0), (2.76, 0.5, 0.6), (5.4, 0.3, 0.35)), None, r), n_of(0.08))
    return place(0.3, [(punch(r, pj, 1.25, 180, 75, 0.02), 0.0), (crack(r, 0.02, 3500, 12000, 0.0012, 0.9), 0.002), (ping * 0.8, 0.008),
                       (zip_short(r, r.uniform(10000, 12500), 5000, r.uniform(0.04, 0.07), 0.8), 0.012), (zip_short(r, r.uniform(8000, 10500), 4500, 0.035, 0.5), 0.03 + 0.01 * (i % 3))])


def v_water(r, i):
    pj = r.uniform(0.92, 1.08)
    bub = fit(U.bubble(r, 1500, 3500), n_of(0.06)) * 0.9
    return place(0.25, [(punch(r, pj, 1.3, 140, 55, 0.022), 0.0), (hiss_short(r, 0.07, 5000, 11500, 0.7), 0.01), (bub, 0.015),
                        (grit(r, 4, 0.02, 0.11, 0.6, 5000, 11000), 0.0)])


def v_person(r, i):
    pj = r.uniform(0.92, 1.08)      # cartoon thump + cloth slap; no vocal, no gore
    return place(0.25, [(punch(r, pj, 1.8, 130, 58, 0.03), 0.0), (body(r, 0.08, 700, 0.025, 0.7, 120), 0.004), (tickn(r, 0.004, 2000, 6500, 0.5, n_of(0.02)), 0.006)])


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
    return sumv(fit(s, n_of(d)), c, punch(r, pj, 1.1, 150, 55, 0.03), crack(r, 0.03, 3000, 12000, 0.002, 0.9))


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
    return sumv(s, punch(r, pj, 1.1, 140, 52, 0.03), crack(r, 0.04, 2500, 11000, 0.003, 0.9), crack(r, 0.1, 500, 7000, 0.012, 1.0), body(r, 0.5, 500, 0.12, 1.0, 60), plume, fit(bub, n), drops,
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


PART = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ('v', 'b') else 'vb'


def render():
    if 'v' in PART:
        S.set_manifest('ac130imp_v'); H.CEIL_DB = -4.5
        for sf, mk in V_MAKERS.items():
            reg('ac130_vulcan_hit_' + sf, mk, 4, 'hit', 'mat', weight=4, max_dist=250, tags=['impact', 'ac130', 'vulcan', sf])
        reg('ac130_vulcan_stitch', m_stitch, 3, 'loop', 'mat', far=dict(stem='ac130_vulcan_stitch_far', count=3, lp=900, delay=0.1, rt=0.8, wet=0.4, fc=700),
            weight=6, max_dist=500, tags=['impact', 'ac130', 'vulcan', 'stitch'])
    if 'b' in PART:
        S.set_manifest('ac130imp_b'); H.CEIL_DB = -2.2
        for sf, mk in B_MAKERS.items():
            reg('ac130_bofors_hit_' + sf, mk, 4, 'fire', 'mat', far=dict(stem='ac130_bofors_hit_%s_far' % sf, count=3, lp=650, delay=0.15, rt=1.4, wet=0.6, fc=550),
                weight=8, max_dist=600, tags=['impact', 'ac130', 'bofors', '40mm', sf])


def deploy():
    here = os.path.dirname(os.path.abspath(__file__)); dst = os.path.join(os.path.dirname(here), 'audio')
    frag = json.load(open(os.path.join(here, 'out', 'manifest.ac130imp_%s.json' % PART[0] + ''), encoding='utf-8'))
    mp = os.path.join(dst, 'manifest.json'); man = json.load(open(mp, encoding='utf-8'))
    for id_, e in frag.items():
        shutil.copy2(os.path.join(here, 'out', id_ + '.ogg'), os.path.join(dst, id_ + '.ogg')); man['assets'][id_] = e
    json.dump(man, open(mp, 'w', encoding='utf-8')); print('deployed %d' % len(frag))


if __name__ == '__main__':
    render()
    if '--no-deploy' not in sys.argv: deploy()
