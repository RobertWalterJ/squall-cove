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


def chips(r, dur, t0, rate0, tau, lo=1500, hi=7000, lvl=1.0, dull=0.12):
    """Real concrete/gravel debris: dry hard fragments. Irregular broadband noise bursts (0.7-5 ms, fast decay, bandpassed lo-hi),
    random timing and level, occasional 2-3 chip skitters, and a few very small dull damped 'tok' bits (fixed pitch, no sweeps)."""
    out = np.zeros(n_of(dur)); t = t0
    while t < dur - 0.03:
        t += r.exponential(1.0 / max(rate0, 1.0))
        if t >= dur - 0.03: break
        if r.random() > math.exp(-(t - t0) / tau): continue
        for j in range(int(r.integers(1, 4)) if r.random() < 0.3 else 1):
            tj = t + j * r.uniform(0.001, 0.008); g = lvl * (r.uniform(0.08, 1.0) ** 1.6)
            k = int(r.uniform(0.0007, 0.005) * SR); x = r.standard_normal(k) * np.exp(-np.arange(k) / (k * 0.22))
            c = r.uniform(lo * 1.3, hi * 0.7); x = bp(x, max(lo, c * 0.6), min(hi, c * 1.5), SR, 2)
            put(out, x * g, tj, 1.0)
            if r.random() < dull:
                m = int(r.uniform(0.003, 0.008) * SR); tx = np.arange(m) / SR
                put(out, np.sin(TWO_PI * r.uniform(500, 1500) * tx) * np.exp(-tx / r.uniform(0.002, 0.004)) * g * 0.25, tj, 1.0)
    return out


def sprinkle(r, dur, t0, rate0, tau, lvl=1.0, lo=3500, hi=10000, gmin=0.04, gmax=0.6):
    """Tiny light droplets: very short quiet high ticks at random times, slowly thinning out (rate0 * exp(-(t-t0)/tau))."""
    out = np.zeros(n_of(dur)); t = t0
    while t < dur - 0.02:
        t += r.exponential(1.0 / max(rate0, 1.0))
        if t >= dur - 0.02: break
        if r.random() > math.exp(-(t - t0) / tau): continue
        k = int(r.uniform(0.0006, 0.002) * SR); x = r.standard_normal(k) * np.exp(-np.arange(k) / (k * 0.25))
        c = r.uniform(lo * 1.2, hi * 0.8); x = bp(x, max(lo, c * 0.7), min(hi, c * 1.4), SR, 2)
        put(out, x * lvl * (r.uniform(gmin, gmax) ** 1.5), t, 1.0)
    return out


def spray(r, dur, rise, hold, fall, lo, hi, lvl=1.0):
    """Spray column: soft broadband hiss that swells, holds and falls back, with irregular flutter."""
    n = n_of(dur); t = tt(n)
    env = np.where(t < rise, np.sin(np.clip(t / rise, 0, 1) * math.pi / 2) ** 2, np.where(t < rise + hold, 1.0, np.exp(-(t - rise - hold) / fall)))
    return unit(bp(noise(n, 'white', r), lo, hi, SR, 2)) * env * slowmod(n, 14, r, 0.6) * lvl


def slap(r, dur, tau, fc=800, lvl=1.0):
    """Dull water slap: low-passed noise, quick decay."""
    n = n_of(dur); t = tt(n)
    return unit(lp(noise(n, 'white', r), fc, SR, 2)) * np.exp(-t / tau) * np.minimum(1, t / 0.0015) * lvl


def v_dirt(r, i):
    pj = r.uniform(0.92, 1.08)
    return place(0.25, [(punch(r, pj, 1.6), 0.0), (body(r, 0.08, 900, 0.02, 0.45, 150), 0.01), (hiss_short(r, 0.06, 4500, 11500, 0.7), 0.012),
                        (grit(r, 7, 0.012, 0.11, 0.9), 0.0), (zip_short(r, r.uniform(7500, 10500), 3500, r.uniform(0.03, 0.05), 0.3), 0.02)])


def v_concrete(r, i):
    pj = r.uniform(0.92, 1.08)
    return place(0.25, [(punch(r, pj, 1.4, 190, 70, 0.018), 0.0), (crack(r, 0.03, 3000, 12000, 0.0015, 1.3), 0.003),
                        (chips(r, 0.24, 0.006, 420, 0.07, 1500, 7000, 1.0), 0.0), (zip_short(r, r.uniform(9500, 12500), 4000, r.uniform(0.04, 0.075), 0.6), 0.015)])


SQ_LOG = []      # (element length ms) of every metal squeak element generated (for the QA report)
PING_TAUS = []


def v_metal(r, i):
    """Heavy punch, then many very short variable-length squeaks (10-60 ms, rising or falling, 6-13 kHz), plus a bright inharmonic
    ping cluster (3-9 kHz, decays over roughly 80-200 ms) like struck sheet metal."""
    pj = r.uniform(0.92, 1.08); d = 0.36
    parts = [(punch(r, pj, 1.25, 180, 75, 0.02), 0.0), (crack(r, 0.02, 3500, 12000, 0.0012, 0.9), 0.002)]
    # ping cluster: 4-5 slightly inharmonic partials, 3-9 kHz
    base = r.uniform(3000, 4200); ratios = [1.0, r.uniform(1.38, 1.5), r.uniform(1.85, 2.05), r.uniform(2.3, 2.55), r.uniform(2.6, 2.95)]
    tau = r.uniform(0.022, 0.04); PING_TAUS.append(tau)
    n = n_of(0.3); t = tt(n); ping = np.zeros(n)
    for k, q in enumerate(ratios):
        f = min(base * q, 9000.0)
        ping += np.sin(TWO_PI * f * t + r.uniform(0, 6.28)) * np.exp(-t / (tau * (1.0 - 0.12 * k))) * (1.0 - 0.12 * k)
    ping *= np.minimum(1, t / 0.0006)
    parts.append((ping * 0.45, 0.004))
    # squeaks
    for _ in range(int(r.integers(5, 10))):
        L = float(np.exp(r.uniform(math.log(0.010), math.log(0.060)))); SQ_LOG.append(L * 1000)
        f0 = r.uniform(6000, 12500); f1 = f0 * (r.uniform(0.45, 0.8) if r.random() < 0.5 else r.uniform(1.25, 1.7))
        parts.append((zip_short(r, min(f0, 13000), min(f1, 13500), L, r.uniform(0.35, 0.8)), r.uniform(0.004, 0.15)))
    return place(d, parts)


def v_water(r, i, more=False):
    pj = r.uniform(0.92, 1.08)
    parts = [(punch(r, pj, 1.5, 140, 52, 0.022), 0.0), (slap(r, 0.07, 0.02, 900, 0.7), 0.002), (hiss_short(r, 0.04, 3500, 11000, 0.45), 0.008),
             (sprinkle(r, 0.22, 0.0, 90, 0.07, 0.3), 0.02)]
    if more:
        parts += [(sprinkle(r, 0.65, 0.0, 170, 0.28, 0.35), 0.03), (sprinkle(r, 0.65, 0.0, 380, 0.25, 0.12, 3000, 8000), 0.03)]
    return place(0.7 if more else 0.25, parts)


def v_person(r, i):
    pj = r.uniform(0.92, 1.08)      # cartoon thump + cloth slap; no vocal, no gore
    return place(0.25, [(punch(r, pj, 1.8, 130, 58, 0.03), 0.0), (body(r, 0.08, 700, 0.025, 0.7, 120), 0.004), (tickn(r, 0.004, 2000, 6500, 0.5, n_of(0.02)), 0.006)])


V_MAKERS = dict(dirt=v_dirt, concrete=v_concrete, metal=v_metal, water=v_water, person=v_person)


def m_stitch(r, i):
    d = 1.15; out = np.zeros(n_of(d)); t = 0.0; w = [('dirt', 4), ('concrete', 2), ('metal', 1), ('dirt', 2)]
    names = ['metal', 'dirt', 'water', 'concrete', 'metal', 'dirt', 'water', 'metal'] if i == 2 else ['metal', 'dirt', 'concrete', 'metal', 'metal', 'dirt', 'concrete', 'metal']
    k = 0
    while t < 0.95:
        nm = names[k % len(names)]; k += 1
        h = v_water(r, k, True) if nm == 'water' else V_MAKERS[nm](r, k)
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
                chips(r, d, 0.05, 260, 0.45, 1500, 7000, 0.9),
                mix(d, [(zing(r, None, None, 0.45), 0.03, 1.0), (zing(r, None, None, 0.35), 0.06 + 0.03 * i, 1.0), (zing(r, None, None, 0.25), 0.14, 1.0)]),
                echoes(tail(r, d - 0.05, 0.35, 0.2, 1200, 250, 0.6, 0.35, 0.02), [(0.1, 0.4, 1500), (0.22, 0.25, 900)]) * 0.5)


def b_metal(r, i):
    d = 1.5; pj = r.uniform(0.92, 1.08); f = r.uniform(380, 700)
    ring = fit(pingn(f, 0.22, d, ((1, 1.0, 1.0), (2.32, 0.6, 0.7), (4.1, 0.45, 0.45), (6.7, 0.25, 0.3)), None, r), n_of(d)) * 0.8
    return sumv(bof_core(r, d, pj, 9000, 0.8), ring, debris(r, d, 0.15, 70, 0.6, 1800, 7500, 0.15, 0.6),
                mix(d, [(zing(r, None, None, 0.5), 0.02, 1.0), (zing(r, None, None, 0.4), 0.05 + 0.02 * i, 1.0), (zing(r, None, None, 0.3), 0.11, 1.0)]),
                tail(r, d - 0.05, 0.3, 0.25, 1500, 300, 0.4, 0.4, 0.02) * 0.4)


def b_water(r, i):
    d = 1.5; pj = r.uniform(0.92, 1.08)
    A_ = sumv(punch(r, pj, 1.3, 110, 45, 0.035), slap(r, 0.25, 0.05, 700, 0.9), body(r, 0.3, 350, 0.06, 0.6, 60), crack(r, 0.04, 2500, 11000, 0.003, 0.7))
    B_ = place(d, [(hiss_short(r, 0.12, 2500, 10000, 0.6), 0.01), (spray(r, 0.9, 0.05, 0.08, 0.28, 2500, 9000, 0.25), 0.05),
                   (sprinkle(r, 1.4, 0.0, 230, 0.5, 0.35), 0.05), (sprinkle(r, 1.4, 0.0, 500, 0.4, 0.12, 3000, 8000), 0.05)])
    return sumv(A_, B_)


def h_water(r, i):
    """105 mm into water: heavy fast-dissipating thump, then a big splash and a spray column falling back as sprinkles."""
    d = 4.2; pj = r.uniform(0.92, 1.08)
    A_ = sumv(sub(2.0, 72 * pj, 27 * pj, 0.12, 0.5, 0.004, 0.1), sub(1.2, 48 * pj, 30 * pj, 0.3, 0.4, 0.014, 0.0) * 0.6, slap(r, 0.5, 0.12, 700, 1.0),
              crack(r, 0.05, 300, 3500, 0.006, 0.7), body(r, 0.6, 300, 0.1, 0.9, 50))
    B_ = place(d, [(hiss_short(r, 0.3, 2000, 9500, 0.8), 0.02), (spray(r, 2.6, 0.25, 0.35, 0.9, 1800, 8000, 0.3), 0.05),
                   (sprinkle(r, 3.8, 0.0, 260, 1.4, 0.4), 0.1), (sprinkle(r, 3.8, 0.0, 600, 1.2, 0.12, 3000, 8000), 0.1)])
    return sumv(fit(A_, n_of(d)), B_)


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
