"""AC-130 gunship pack: 105 mm howitzer (fire + impact), 40 mm Bofors-style cannon, 25 mm Vulcan loop with spin-up/down,
four-engine turboprop drone, airframe creak. Procedural, seeded, mono 44.1 kHz Ogg Vorbis, same gain staging as gen_heavy.py.

    python gen_ac130.py            # render into out/ and merge into ../audio (+ manifest.json), touching only ac130_* stems
    python gen_ac130.py --no-deploy
"""
import math, os, sys, json, shutil
import numpy as np
import synthlib as S
import gen_util as U
from gen_heavy import *          # building blocks + stage_save + CLASS_RMS (gen_heavy.render is not run on import)

GROUP = 'weapons'


def circ_lp(x, fc):
    sp = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1.0 / SR)
    return np.fft.irfft(sp / np.sqrt(1 + (f / fc) ** 8), len(x))


def far_mix(x, r, lp_hz, delay, rt, wet, fc):
    y = lp(x, lp_hz, SR, 4)
    if delay > 0: y = np.concatenate([np.zeros(n_of(delay)), y])
    return reverb(y, rt, wet, fc, r)


def rattle(r, dur, t0, level=1.0, rate0=45.0, tau=1.1):
    """Airframe rattle: loose-panel buzz (amplitude-modulated mid noise) plus ringing metal ticks."""
    n = n_of(dur); t = tt(n)
    buzz = unit(bp(noise(n, 'white', r), 110, 520, SR, 2)) * (0.5 + 0.5 * np.sign(np.sin(TWO_PI * r.uniform(24, 34) * t)) * 0.6)
    buzz = buzz * np.exp(-np.maximum(t - t0, 0) / tau) * np.minimum(1, np.maximum(t - t0, 0) / 0.06) * (t >= t0)
    out = buzz * 0.5 * level
    tk = t0
    while tk < dur - 0.2:
        tk += r.exponential(1.0 / rate0)
        if r.random() > math.exp(-(tk - t0) / (tau * 1.2)): continue
        f = r.uniform(180, 1100); k = n_of(r.uniform(0.03, 0.09)); tx = np.arange(k) / SR
        put(out, np.sin(TWO_PI * f * tx + r.uniform(0, 6.28)) * np.exp(-tx / r.uniform(0.012, 0.035)) * r.uniform(0.15, 0.6) * level, tk, 1.0)
    return out


# ------------------------------------------------------------------ 105 mm howitzer: firing
def m_how_fire(r, i):
    pj = r.uniform(0.9, 1.1); dur = 3.4
    s = sumv(sub(3.0, 64 * pj, 24 * pj, 0.16, 0.95, 0.006, 0.1),
             sub(2.2, 42 * pj, 30 * pj, 0.35, 0.7, 0.02, 0.0) * 0.8,
             sub(0.5, 130 * pj, 55 * pj, 0.05, 0.1, 0.002, 0.2) * 0.6)
    c = sumv(crack(r, 0.2, 300, 5200, 0.016, 1.0), crack(r, 0.5, 80, 700, 0.07, 1.2), body(r, 0.9, 260, 0.26, 1.3, 40))
    tl = tail(r, 3.2, 1.35, 0.5, 600, 110, 1.0, 0.3, 0.06)
    tl = echoes(tl, [(0.25, 0.5, 450), (0.55, 0.38, 350), (0.95, 0.26, 260), (1.5, 0.15, 220)])
    rt = rattle(r, dur, 0.05, 0.85)
    return fit(s, n_of(dur)), sumv(c, tl * 0.9, rt)


# ------------------------------------------------------------------ 105 mm howitzer: impact
def m_how_hit(r, i):
    pj = r.uniform(0.9, 1.1); dur = 4.8
    s = sumv(sub(4.2, 78 * pj, 27 * pj, 0.12, 0.85, 0.004, 0.14),
             sub(3.0, 50 * pj, 32 * pj, 0.3, 0.8, 0.014, 0.0) * 0.7,
             sub(0.6, 150 * pj, 60 * pj, 0.04, 0.12, 0.002, 0.2) * 0.5)
    c = sumv(crack(r, 0.12, 700, 10000, 0.0065, 1.3), crack(r, 0.4, 150, 1500, 0.05, 1.1), body(r, 0.9, 380, 0.2, 1.2, 50))
    rum = tail(r, 4.5, 1.7, 0.7, 950, 130, 1.0, 0.45, 0.04)
    rum = echoes(rum, [(0.22, 0.5, 600), (0.5, 0.4, 450), (1.0, 0.28, 330), (1.7, 0.16, 260)])
    deb = debris(r, dur, 0.35, 170, 1.2, 650, 6000, 0.6, 0.55)
    deb2 = debris(r, dur, 1.1, 60, 1.0, 400, 3500, 0.7, 0.45)   # heavier, later clods
    return fit(s, n_of(dur)), sumv(c, rum * 0.9, deb, deb2)


# ------------------------------------------------------------------ 40 mm Bofors-style cannon
def m_bofors(r, i):
    pj = r.uniform(0.92, 1.08); dur = 0.95
    s = sub(0.7, 150 * pj, 58 * pj, 0.03, 0.11, 0.002, 0.25)
    c = sumv(crack(r, 0.1, 900, 9000, 0.0055, 1.2), crack(r, 0.2, 220, 2200, 0.02, 1.2), body(r, 0.35, 700, 0.07, 1.0, 100))
    clank = sumv(thump(n_of(0.12), 190 * pj, 0.02, 0.5, 0.25), tickn(r, 0.003, 1200, 5000, 0.6, n_of(0.12)))
    tl = tail(r, 0.9, 0.22, 0.14, 1800, 300, 0.5, 0.45, 0.01)
    return fit(s, n_of(dur)), sumv(c, mix(0.2, [(clank * 0.35, 0.06 + 0.01 * i, 1.0)]), echoes(tl, [(0.09, 0.4, 1200), (0.2, 0.22, 700)]))


def m_bofors_hit(r, i):
    pj = r.uniform(0.92, 1.08); dur = 1.0
    s = sub(0.8, 100 * pj, 42 * pj, 0.05, 0.18, 0.003, 0.15)
    c = sumv(crack(r, 0.1, 500, 7000, 0.008, 1.0), crack(r, 0.2, 120, 1000, 0.03, 1.0), body(r, 0.4, 420, 0.09, 1.0, 60))
    deb = debris(r, dur, 0.08, 90, 0.35, 700, 5500, 0.5, 0.5)
    tl = tail(r, 0.9, 0.3, 0.18, 800, 150, 0.8, 0.3, 0.02)
    return fit(s, n_of(dur)), sumv(c, tl * 0.7, deb)


# ------------------------------------------------------------------ Vulcan
VUL_DUR = 1.2; VUL_N = 80          # 66.7 rounds/s, integer pulses per loop => seamless
RATE = VUL_N / VUL_DUR


def vpulse(r, a=1.0, hi=1.0):
    return sumv(sub(0.04, 125, 60, 0.009, 0.014, 0.0008, 0.3) * 0.9,
                crack(r, 0.014, 1400, 7500 * hi, 0.0016, 0.6 * a),
                body(r, 0.035, 520, 0.007, 0.5, 110)) * a


def m_vul_loop(r, i):
    n = n_of(VUL_DUR); per = n / VUL_N; out = np.zeros(n); t = tt(n)
    am = 1 + 0.1 * np.sin(TWO_PI * 2 * t / 1.2 * 1 + r.uniform(0, 6.28)) + 0.06 * np.sin(TWO_PI * 5 / 1.2 * t + r.uniform(0, 6.28))
    for k in range(VUL_N):
        put_circ(out, vpulse(r, r.uniform(0.8, 1.0)), k * per + r.uniform(-0.0005, 0.0005) * SR)
    out *= am
    out += circ_noise(n, 400, 3500, r, 0.0) * 0.12 * (0.6 + 0.4 * np.sin(TWO_PI * RATE * t))   # ripping air between rounds
    out += circ_noise(n, 30, 150, r, 0.0) * 0.22
    return Z, out


def spin_pulses(r, dur, rate_fn, amp_fn, tmax=None):
    """Time-warped pulse train: a pulse each time the integral of rate_fn(t) crosses an integer."""
    n = n_of(dur); t = tt(n); ph = np.cumsum(rate_fn(t)) / SR
    k = np.floor(ph).astype(int); idx = np.nonzero(np.diff(k) > 0)[0] + 1
    out = np.zeros(n)
    for j in idx:
        tj = j / SR
        if tmax is not None and tj > tmax: break
        put(out, vpulse(r, amp_fn(tj) * r.uniform(0.82, 1.0)), tj - 0.0, 1.0)
    return out


def m_vul_start(r, i):
    dur = 1.35; n = n_of(dur); t = tt(n); T = 0.95 + 0.05 * i
    sm = np.clip(t / T, 0, 1); rate = 3 + (RATE - 3) * (sm * sm * (3 - 2 * sm))
    out = spin_pulses(r, dur, lambda x: 3 + (RATE - 3) * (lambda s_: s_ * s_ * (3 - 2 * s_))(np.clip(x / T, 0, 1)), lambda tj: 0.45 + 0.55 * min(1, tj / T))
    whine = bp(noise(n, 'white', r), 250, 900, SR, 2) * 0.0
    f = 70 + 330 * np.clip(t / T, 0, 1) ** 1.5; ph = TWO_PI * np.cumsum(f) / SR
    motor = (np.sin(ph) + 0.4 * np.sin(2 * ph)) * 0.05 * np.clip(t / 0.15, 0, 1)
    air = unit(S.tv_filter(noise(n, 'white', r), 300 + 3000 * np.clip(t / T, 0, 1), 'lp', 2, SR, 512)) * 0.04 * np.clip(t / T, 0, 1)
    out = out + motor + air
    # cut at the end so the last pulses sit exactly at loop phase 0; no tail here (the loop takes over)
    return Z, out


def m_vul_end(r, i):
    dur = 1.9; n = n_of(dur); t = tt(n); T = 0.85 + 0.05 * i
    out = spin_pulses(r, dur, lambda x: RATE * np.exp(-np.maximum(x - 0.02, 0) / (T * 0.45)) * (x < T + 0.2), lambda tj: 0.35 + 0.65 * math.exp(-tj / T))
    f = 380 * np.exp(-t / 0.5) + 60; ph = TWO_PI * np.cumsum(f) / SR
    motor = (np.sin(ph) + 0.4 * np.sin(2 * ph)) * 0.05 * np.exp(-t / 0.55)
    ring = echoes(out, [(0.07, 0.45, 900), (0.16, 0.3, 600), (0.32, 0.18, 400)])
    ring = reverb(ring, 1.0, 0.35, 700, r)[:n]
    return Z, fit(ring, n) + motor


# ------------------------------------------------------------------ four-engine turboprop drone
PROP_DUR = 8.0


def m_prop(r, i):
    n = n_of(PROP_DUR); t = tt(n); out = np.zeros(n)
    base = (68.0, 68.25, 67.75, 68.5) if i == 0 else (66.5, 67.0, 66.0, 67.5)     # blade-pass, multiples of 1/8 Hz => exact loop
    for e, f in enumerate(base):
        ph0 = r.uniform(0, TWO_PI)
        for h in range(1, 14):
            a = 1.0 / h ** 1.1 * (1.0 if h != 2 else 1.4)
            out += a * np.sin(TWO_PI * f * h * t + ph0 * h + r.uniform(0, 6.28)) * 0.25
        out += 0.012 * np.sin(TWO_PI * (round(1180 + 6 * e, 0) * 1.0) * t + r.uniform(0, 6)) * 0.25     # turbine whine, faint
    out += circ_noise(n, 40, 420, r, 0.6) * 0.35 + circ_noise(n, 420, 1800, r, 1.0) * 0.07           # slipstream
    out = circ_lp(out, 1400)
    return Z, out * (1 + 0.04 * np.sin(TWO_PI * (3 / PROP_DUR) * t))


def m_prop_far(r, i):
    s, x = m_prop(r, 0)
    return Z, circ_lp(x, 260)


# ------------------------------------------------------------------ airframe creak
def m_creak(r, i):
    dur = [2.2, 1.7, 2.6][i]; n = n_of(dur); t = tt(n)
    f0 = [150, 210, 120][i]; fc = f0 * (1 + 0.8 * np.sin(np.pi * t / dur) ** 1.5)
    slip = (r.random(n) < (22 + 20 * np.sin(np.pi * t / dur)) / SR).astype(float)       # stick-slip impulses
    exc = np.convolve(slip, np.exp(-np.arange(n_of(0.008)) / (0.002 * SR)), 'same')
    y = unit(S.tv_bandpass(exc + 0.03 * noise(n, 'white', r), fc, 0.5, 2, SR, 256))
    y2 = unit(S.tv_bandpass(exc, fc * 2.3, 0.5, 2, SR, 256))
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.2
    return Z, (y + 0.45 * y2) * env


# ------------------------------------------------------------------ table and render
def E(stem, mk, cls, count, bus='veh', far=None, subf=False, loop=False, **kw):
    return dict(stem=stem, mk=mk, cls=cls, count=count, bus=bus, far=far, sub=subf, loop=loop, kw=kw)


TABLE = [
    E('ac130_howitzer_fire', m_how_fire, 'boom', 4, far=dict(stem='ac130_howitzer_fire_far', lp=480, delay=0.2, rt=2.6, wet=0.7, fc=420), subf=True,
      weight=10, max_dist=1000, tags=['weapon', 'ac130', 'howitzer', '105mm']),
    E('ac130_howitzer_hit', m_how_hit, 'boom', 4, bus='mat', far=dict(stem='ac130_howitzer_hit_far', lp=520, delay=0.2, rt=3.0, wet=0.7, fc=450), subf=True,
      weight=10, max_dist=1200, tags=['impact', 'ac130', 'howitzer', '105mm', 'explosion']),
    E('ac130_bofors_shot', m_bofors, 'fire', 5, far=dict(stem='ac130_bofors_shot_far', lp=700, delay=0.1, rt=1.2, wet=0.6, fc=600, count=3),
      weight=9, max_dist=700, tags=['weapon', 'ac130', 'bofors', '40mm']),
    E('ac130_bofors_hit', m_bofors_hit, 'fire', 4, bus='mat', weight=7, max_dist=500, tags=['impact', 'ac130', 'bofors', '40mm']),
    E('ac130_vulcan_loop', m_vul_loop, 'loop', 2, loop=True, far=dict(stem='ac130_vulcan_loop_far', circ=900),
      weight=8, max_dist=450, tags=['weapon', 'ac130', 'vulcan', '25mm', 'loop']),
    E('ac130_vulcan_start', m_vul_start, 'loop', 2, far=dict(stem='ac130_vulcan_start_far', lp=1000, delay=0.0, rt=0.6, wet=0.25, fc=900),
      weight=8, max_dist=450, tags=['weapon', 'ac130', 'vulcan', 'spinup']),
    E('ac130_vulcan_end', m_vul_end, 'loop', 2, far=dict(stem='ac130_vulcan_end_far', lp=1000, delay=0.0, rt=1.2, wet=0.4, fc=800),
      weight=8, max_dist=450, tags=['weapon', 'ac130', 'vulcan', 'spindown']),
    E('ac130_prop_loop', m_prop, 'loop', 2, loop=True, far=dict(stem='ac130_prop_loop_far', circ=260, count=1), weight=6, max_dist=600, group='aircraft',
      rate=(0.9, 1.15), tags=['prop', 'ac130', 'loop', 'four-engine']),
    E('ac130_creak', m_creak, 'foley', 3, weight=3, max_dist=120, group='aircraft', tags=['ac130', 'creak', 'airframe']),
]


def render():
    S.set_manifest('ac130')
    for e in TABLE:
        stem = e['stem']; kw = dict(e['kw']); loop = e['loop']; grp = kw.pop('group', GROUP)
        for i in range(e['count']):
            r = rng(U.seed_of(stem, i)); s, rest = e['mk'](r, i)
            full = sumv(s, rest) if len(s) > 1 else rest
            kk = dict(kw); kk.update(variants=e['count'], group=grp); kk.setdefault('rate', (0.94, 1.06))
            stage_save('%s_%02d' % (stem, i + 1), full, e['cls'], e['bus'], loop=loop, **kk)
            f = e['far']
            if f and i < f.get('count', e['count']):
                rf = rng(U.seed_of(f['stem'], i)); nx = full / (np.max(np.abs(full)) + 1e-9)
                fx = circ_lp(nx, f['circ']) if 'circ' in f else far_mix(nx, rf, f['lp'], f['delay'], f['rt'], f['wet'], f['fc'])
                fk = dict(kk); fk.update(weight=max(2, kw.get('weight', 5) - 3), max_dist=max(1800, kw.get('max_dist', 300) * 2), gain=0.7,
                                         variants=f.get('count', e['count']), tags=kw['tags'] + ['far'])
                stage_save('%s_%02d' % (f['stem'], i + 1), fx, 'loop' if loop else 'far', e['bus'], loop=loop, **fk)
            if e['sub']:
                sx = lp(s, 100, SR, 4)
                k2 = dict(kk); k2.update(gain=0.8, tags=kw['tags'] + ['sub'], rate=(0.96, 1.04), meta=dict(kind='sub-layer', note='mono 25-90 Hz body to layer under the full stem'))
                stage_save('%s_sub_%02d' % (stem, i + 1), sx, 'sub', e['bus'], **k2)
        print('rendered', stem)


def deploy():
    here = os.path.dirname(os.path.abspath(__file__)); dst = os.path.join(os.path.dirname(here), 'audio')
    frag = json.load(open(os.path.join(here, 'out', 'manifest.ac130.json'), encoding='utf-8'))
    mp = os.path.join(dst, 'manifest.json'); man = json.load(open(mp, encoding='utf-8'))
    for id_, e in frag.items():
        shutil.copy2(os.path.join(here, 'out', id_ + '.ogg'), os.path.join(dst, id_ + '.ogg'))
        man['assets'][id_] = e
    json.dump(man, open(mp, 'w', encoding='utf-8'))
    print('deployed %d ac130 assets into %s' % (len(frag), dst))


if __name__ == '__main__':
    render()
    if '--no-deploy' not in sys.argv: deploy()
