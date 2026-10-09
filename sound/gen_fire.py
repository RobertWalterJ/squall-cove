"""FIRE pack: procedural, licence-free fire sounds scaled by fire size and heard with distance.
Seamless loops (campfire, medium, building, vehicle/fuel, oil pool, grass/brush, burning tree, gas flame, spray over fire, distant overview),
near/far/interior versions, plus one-shots (pops, sparks, log cracks, creaks, glass, flare-ups, ignition, tank burst, lick, collapse, clatter),
water/extinguish hiss, sizzle. Mono 44.1 kHz Ogg Vorbis, peak <= -2.2 dBFS, deterministic (seeded from the stem name).
Does NOT touch the older fire_crackle_loop_* / fire_ember_pop_* / fire_extinguish_hiss_* / fire_ignite_whoomp_* / fire_tree_* stems.

    python gen_fire.py              # render into out/ and merge into ../audio + manifest.json (only the new fire_* stems)
    python gen_fire.py --no-deploy
    python gen_fire.py camp         # render only stems whose name contains 'camp'
See ../FIRE-SOUND-SPEC.md.
"""
import math, os, sys, json, shutil, time
import numpy as np
from scipy import signal
import synthlib as S
import gen_util as U
from synthlib import SR, rng, n_of, noise, lp, hp, bp
import gen_heavy as H
from gen_heavy import unit, tt, sub, softlimit, wrms_db, circ_hp, reverb, echoes

TWO_PI = 2 * math.pi
CEIL_DB = -3.2          # pre-encode ceiling; Vorbis overshoot + decimation ringing keep the decoded peak under -2.0 dBFS
BUS = 'mat'
GROUP = 'fx'
PROTECTED = {'fire_ignite_whoomp', 'fire_crackle_loop', 'fire_extinguish_hiss', 'fire_ember_pop', 'fire_tree_burn_roar', 'fire_tree_fall'}


# ------------------------------------------------------------------ periodic (loop-safe) building blocks
def sstep(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


def per_smooth(n, fmax, r):
    """Periodic smooth random, unit std, bandwidth about fmax Hz (exactly periodic over n samples)."""
    sp = np.fft.rfft(r.standard_normal(n)); f = np.fft.rfftfreq(n, 1.0 / SR)
    w = np.exp(-(f / fmax) ** 2); w[0] = 0
    x = np.fft.irfft(sp * w, n)
    return x / (np.std(x) + 1e-12)


def gust(n, fmax, depth, r):
    g = np.exp(depth * per_smooth(n, fmax, r)); return g / np.sqrt(np.mean(g * g))


def band_noise(n, lo, hi, r, slope=0.0, edge=0.5):
    """Periodic band noise with smooth log-frequency edges, amplitude slope f^-slope, unit RMS."""
    f = np.fft.rfftfreq(n, 1.0 / SR); f[0] = 1; lf = np.log2(f)
    m = sstep((lf - (math.log2(lo) - edge / 2)) / edge) * (1 - sstep((lf - (math.log2(hi) - edge / 2)) / edge))
    m = m * f ** (-slope); m[0] = 0
    sp = m * (r.standard_normal(len(f)) + 1j * r.standard_normal(len(f)))
    return unit(np.fft.irfft(sp, n))


def clp(x, fc, order=4):
    """Circular (periodic) low-pass by FFT, keeps a loop seamless."""
    sp = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1.0 / SR)
    return np.fft.irfft(sp / np.sqrt(1 + (f / fc) ** (2 * order)), len(x))


def chp(x, fc, order=2):
    sp = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1.0 / SR); f[0] = 1e-3
    return np.fft.irfft(sp * (1 - 1 / np.sqrt(1 + (f / fc) ** (2 * order))), len(x))


def addwrap(out, g, i, a):
    n = len(out); e = i + len(g)
    if e <= n: out[i:e] += g * a
    else:
        k = n - i; out[i:] += g[:k] * a; out[:e - n] += g[k:] * a


# ------------------------------------------------------------------ grains (peak 1)
def pk1(x):
    x = np.asarray(x, dtype=np.float64); m = np.max(np.abs(x)); return x / m if m > 1e-12 else x


def g_tick(r, fc, dur=0.003):
    k = int(dur * SR * 6) + 8; t = np.arange(k) / SR
    x = r.standard_normal(k) * np.exp(-t / dur)
    return pk1(bp(x, fc * 0.55, min(fc * 1.7, 17000), SR, 1))


def g_snap(r, fc=None):
    fc = fc or r.uniform(900, 2400); k = int(0.05 * SR); t = np.arange(k) / SR
    x = np.zeros(k); x[:int(0.004 * SR)] = r.standard_normal(int(0.004 * SR)) * np.exp(-np.arange(int(0.004 * SR)) / (0.0012 * SR))
    x = bp(x, 1500, 11000, SR, 1)
    x = x + 0.9 * np.sin(TWO_PI * fc * t + r.uniform(0, 6)) * np.exp(-t / r.uniform(0.004, 0.011))
    return pk1(x)


def g_pop(r, f=None):
    f = f or r.uniform(110, 280); k = int(0.16 * SR); t = np.arange(k) / SR
    x = np.sin(TWO_PI * f * t * (1 - 0.35 * np.exp(-t / 0.02))) * np.exp(-t / r.uniform(0.018, 0.045))
    tk = g_tick(r, r.uniform(2500, 6000), 0.002); x[:len(tk)] += tk * 0.45
    return pk1(x)


def g_lowpop(r):
    f = r.uniform(52, 105); k = int(0.4 * SR); t = np.arange(k) / SR
    x = np.sin(TWO_PI * f * t * (1 - 0.3 * np.exp(-t / 0.04))) * np.exp(-t / r.uniform(0.07, 0.14))
    b = bp(r.standard_normal(k), 90, 600, SR, 1) * np.exp(-t / 0.03); x = x + 0.6 * b / (np.max(np.abs(b)) + 1e-9)
    s = g_snap(r, r.uniform(500, 1100)); x[:len(s)] += 0.35 * s
    return pk1(x)


def g_softpop(r):
    f = r.uniform(140, 380); k = int(0.07 * SR); t = np.arange(k) / SR
    return pk1(np.sin(TWO_PI * f * t) * np.exp(-t / r.uniform(0.008, 0.02)) * (1 - np.exp(-t / 0.0007)))


def g_spit(r):
    n = r.integers(3, 8); L = int(0.07 * SR); x = np.zeros(L); pos = np.sort(r.uniform(0, 0.05, n))
    for j, p in enumerate(pos):
        tk = g_tick(r, r.uniform(2500, 8000), 0.0018); i = int(p * SR); e = min(L, i + len(tk)); x[i:e] += tk[:e - i] * (1 - 0.1 * j) * r.uniform(0.5, 1)
    return pk1(x)


def subr(r, dur, f0, f1, td, tau, att=0.003, harm=0.0):
    """Like gen_heavy.sub but with a random start phase (variants decorrelate)."""
    n = n_of(dur); t = tt(n); f = f1 + (f0 - f1) * np.exp(-t / td); ph = TWO_PI * np.cumsum(f) / SR + r.uniform(0, TWO_PI)
    return (np.sin(ph) + harm * np.sin(2 * ph + 0.6)) * np.minimum(1, t / att) * np.exp(-t / tau)


def g_whoomph(r, dur, f0, noisefc):
    n = n_of(dur); t = tt(n)
    s = subr(r, dur, f0 * 1.3, f0 * 0.75, 0.12, dur * 0.35, 0.02) * (1 - np.exp(-t / (dur * 0.12)))
    b = lp(noise(n, 'white', r), noisefc, SR, 2); b = unit(hp(b, 40, SR, 2)) * (1 - np.exp(-t / (dur * 0.2))) * np.exp(-t / (dur * 0.4))
    return pk1(unit(s) * 0.8 + b * 0.8)


def g_gust_whoosh(r, dur, fc):
    n = n_of(dur); t = tt(n); env = np.sin(np.pi * t / dur) ** 2
    return pk1(unit(bp(noise(n, 'white', r), fc * 0.35, fc * 1.8, SR, 2)) * env)


def bank(r, kind):
    if kind == 'tick': return [g_tick(r, fc) for fc in np.geomspace(2000, 9000, 24)]
    if kind == 'dtick': return [g_tick(r, fc, 0.004) for fc in np.geomspace(700, 2600, 16)]
    if kind == 'snap': return [g_snap(r) for _ in range(20)]
    if kind == 'pop': return [g_pop(r) for _ in range(14)]
    if kind == 'lowpop': return [g_lowpop(r) for _ in range(8)]
    if kind == 'softpop': return [g_softpop(r) for _ in range(16)]
    if kind == 'spit': return [g_spit(r) for _ in range(12)]
    raise KeyError(kind)


def scatter(n, rate, bk, r, amp_pow=2.0, amp_min=0.05):
    """Inhomogeneous Poisson placement (circular). rate: scalar or per-sample array in events/s."""
    p = np.clip(np.broadcast_to(np.asarray(rate, dtype=np.float64), (n,)) / SR, 0, 1)
    idx = np.nonzero(r.random(n) < p)[0]; out = np.zeros(n)
    for i in idx:
        g = bk[r.integers(len(bk))]; a = amp_min + (1 - amp_min) * r.random() ** amp_pow
        addwrap(out, g, int(i), a)
    return out


# ------------------------------------------------------------------ the generic fire loop
def fire_loop(r, D, spec):
    n = n_of(D); t = tt(n)
    gm = gust(n, spec.get('gust', 1.0), spec.get('depth', 0.3), r)
    roar = np.zeros(n)
    for (lo, hi, db, slope, gf, gd) in spec['bands']:
        roar += band_noise(n, lo, hi, r, slope) * 10 ** (db / 20.0) * gust(n, gf, gd, r)
    roar = roar * gm ** spec.get('master_pow', 1.0)
    if spec.get('drive'): roar = np.tanh(roar / np.std(roar) * spec['drive'])
    roar = roar / (np.sqrt(np.mean(roar ** 2)) + 1e-12)
    # periodic tones (burner hum)
    for (f, db, am) in spec.get('tones', ()):
        f = round(f * D) / D
        tone = np.sin(TWO_PI * f * t + r.uniform(0, 6)) * (1 + am * np.sin(TWO_PI * (2 / D) * t + r.uniform(0, 6)))
        roar += tone * 10 ** (db / 20.0) * math.sqrt(2) * 0.5
    # slow level swell (front passing / crown gusts): multiplicative bump(s)
    swell = np.ones(n)
    if spec.get('swell'):
        for (amount, width) in spec['swell']:
            tc = r.uniform(0.25, 0.75) * D; d = np.minimum(np.abs(t - tc), D - np.abs(t - tc))
            swell = swell + amount * np.exp(-(d / (width * D)) ** 2)
    roar = roar * swell ** spec.get('swell_roar', 0.5)
    out = roar.copy(); banks = {}
    for ev in spec.get('events', ()):
        k = ev['kind']
        if k not in banks: banks[k] = bank(r, k)
        rate = ev['rate'] * gm ** ev.get('follow', 1.0) * swell ** ev.get('swell_pow', 1.0)
        out += scatter(n, rate, banks[k], r, ev.get('pow', 2.0)) * 10 ** (ev['db'] / 20.0)
    for wh in spec.get('whoomphs', ()):
        for _ in range(wh['count']):
            g = g_whoomph(r, r.uniform(*wh['dur']), r.uniform(*wh['f']), wh['fc'])
            addwrap(out, g, int(r.uniform(0, n)), 10 ** (wh['db'] / 20.0) * r.uniform(0.7, 1.0))
    for cr in spec.get('creaks', ()):
        for _ in range(cr['count']):
            g = pk1(creak(r, r.uniform(*cr['dur']), r.uniform(*cr['f']), 25, 70))
            addwrap(out, g, int(r.uniform(0, n)), 10 ** (cr['db'] / 20.0) * r.uniform(0.6, 1.0))
    for ws in spec.get('whooshes', ()):
        for _ in range(ws['count']):
            g = g_gust_whoosh(r, r.uniform(*ws['dur']), ws['fc'])
            addwrap(out, g, int(r.uniform(0, n)), 10 ** (ws['db'] / 20.0) * r.uniform(0.7, 1.0))
    if spec.get('lp'): out = clp(out, spec['lp'], spec.get('lp_order', 4))
    return out


def creak(r, D, f0, rate0, rate1, grit=1.0):
    """Stick-slip wood creak/groan: pulse train (rate sweeping rate0->rate1->rate0) through moving resonances."""
    n = n_of(D); t = tt(n); sw = np.sin(np.pi * t / D)
    rate = rate0 + (rate1 - rate0) * sw ** 1.3 + 4 * per_smooth(n, 3, r)
    ph = np.cumsum(np.clip(rate, 5, None)) / SR; ev = np.floor(ph); idx = np.nonzero(np.diff(ev, prepend=0) > 0)[0]
    exc = np.zeros(n); exc[idx] = r.uniform(0.35, 1.0, len(idx)) * (0.6 + 0.8 * sw[idx])
    bu = r.standard_normal(int(0.014 * SR)) * np.exp(-np.arange(int(0.014 * SR)) / (0.0035 * SR))
    exc = signal.fftconvolve(exc, bu)[:n] + grit * 0.02 * noise(n, 'white', r) * sw
    fc = f0 * (1 + 0.7 * sw ** 1.5)
    y = unit(S.tv_bandpass(exc, fc, 0.45, 2, SR, 256)); y2 = unit(S.tv_bandpass(exc, fc * 2.4, 0.5, 2, SR, 256))
    g = unit(np.sin(TWO_PI * np.cumsum(fc * 0.5) / SR)) * (1 + 0.5 * unit(lp(exc, 90, SR, 1)))
    env = sw ** 1.1 * np.clip(1 + 0.3 * per_smooth(n, 3, r), 0.2, None)
    return (y + 0.5 * y2 + 0.25 * g) * env


# ------------------------------------------------------------------ loop specs
# bands: (lo Hz, hi Hz, dB, amplitude slope, gust Hz, gust depth)   events: rate /s, dB re bed RMS (peak-normalised grains)
SPEC = {
    'camp': dict(D=6.0, gust=1.1, depth=0.3, bands=[(55, 320, 0, 0.0, 1.2, 0.35), (1100, 6500, -9, 0.3, 4.0, 0.45), (6500, 12000, -18, 0.0, 5.0, 0.5)],
                 events=[dict(kind='tick', rate=55, db=9, follow=1.5), dict(kind='snap', rate=3.5, db=12, follow=1.5),
                         dict(kind='pop', rate=0.7, db=13), dict(kind='spit', rate=1.2, db=9)]),
    'medium': dict(D=7.0, gust=0.9, depth=0.35, bands=[(45, 420, 0, 0.0, 0.9, 0.45), (420, 2000, -4, 0.0, 3.0, 0.4), (2000, 7500, -12, 0.2, 5.0, 0.45)],
                   events=[dict(kind='tick', rate=110, db=8, follow=1.5), dict(kind='snap', rate=7, db=11, follow=1.5), dict(kind='pop', rate=1.6, db=13),
                           dict(kind='spit', rate=2.2, db=9), dict(kind='lowpop', rate=0.3, db=11)]),
    'large': dict(D=8.0, gust=0.6, depth=0.35, bands=[(25, 90, 3, 0.0, 0.5, 0.45), (25, 140, 0, 0.0, 6.0, 0.5), (90, 520, 3, 0.0, 0.8, 0.4),
                                                     (520, 2200, -3, 0.0, 1.6, 0.45), (2200, 6500, -13, 0.2, 4.0, 0.45)],
                  events=[dict(kind='tick', rate=130, db=5, follow=1.5), dict(kind='snap', rate=9, db=8, follow=1.5), dict(kind='pop', rate=2.2, db=10),
                          dict(kind='lowpop', rate=0.9, db=11), dict(kind='spit', rate=2.0, db=6)],
                  creaks=[dict(count=3, dur=(1.0, 1.8), f=(70, 150), db=-3)]),
    'vehicle': dict(D=7.0, gust=1.3, depth=0.4, drive=1.7, bands=[(100, 900, 0, 0.0, 1.5, 0.45), (900, 4200, -2, 0.0, 5.0, 0.5), (4200, 10000, -8, 0.0, 7.0, 0.5)],
                    events=[dict(kind='tick', rate=90, db=6, follow=1.5), dict(kind='softpop', rate=7, db=7, follow=1.5), dict(kind='snap', rate=3, db=8),
                            dict(kind='spit', rate=3, db=5)],
                    whoomphs=[dict(count=2, dur=(0.7, 1.2), f=(55, 90), fc=900, db=8)]),
    'pool': dict(D=8.0, gust=0.7, depth=0.4, bands=[(28, 110, 4, 0.0, 0.6, 0.5), (110, 600, 0, 0.0, 0.8, 0.45), (70, 230, 2, 0.0, 1.9, 0.7), (600, 2500, -9, 0.0, 2.5, 0.5),
                                                  (2500, 7000, -17, 0.0, 4.0, 0.5)],
                 events=[dict(kind='tick', rate=40, db=4, follow=1.0), dict(kind='pop', rate=1.0, db=8), dict(kind='snap', rate=2, db=7), dict(kind='lowpop', rate=0.5, db=8)],
                 whoomphs=[dict(count=3, dur=(0.9, 1.6), f=(42, 70), fc=500, db=7)]),
    'grass': dict(D=7.0, gust=1.4, depth=0.35, swell=[(1.6, 0.14)], swell_roar=0.7,
                  bands=[(60, 220, -8, 0.0, 1.0, 0.4), (260, 3200, -2, 0.0, 1.7, 0.55), (3200, 11500, -3, 0.0, 6.0, 0.45)],
                  events=[dict(kind='tick', rate=240, db=7, follow=1.5, swell_pow=1.2), dict(kind='snap', rate=14, db=9, follow=1.5, swell_pow=1.2),
                          dict(kind='pop', rate=0.8, db=9), dict(kind='spit', rate=6, db=5, swell_pow=1.0)]),
    'tree': dict(D=7.0, gust=1.0, depth=0.4, swell=[(1.2, 0.1), (0.8, 0.08)], swell_roar=0.8,
                 bands=[(70, 620, 0, 0.0, 1.0, 0.45), (620, 3200, -4, 0.0, 1.4, 0.7), (3200, 9000, -12, 0.0, 4.0, 0.5)],
                 events=[dict(kind='snap', rate=22, db=12, follow=1.5, pow=1.6), dict(kind='tick', rate=120, db=6, follow=1.5), dict(kind='spit', rate=5, db=10),
                         dict(kind='lowpop', rate=1.0, db=9), dict(kind='pop', rate=1.5, db=11)],
                 whooshes=[dict(count=2, dur=(0.9, 1.5), fc=1500, db=2)]),
    'gas': dict(D=6.0, gust=3.0, depth=0.06, bands=[(2500, 9500, 0, 0.0, 3.0, 0.08), (200, 1300, -3, 0.0, 2.0, 0.12), (4800, 5700, -14, 0.0, 0.7, 0.3),
                                                  (60, 160, -12, 0.0, 1.0, 0.1)],
                tones=[(112, -10, 0.1), (224, -17, 0.15), (336, -24, 0.2)],
                events=[dict(kind='tick', rate=2.5, db=4, follow=0.0), dict(kind='softpop', rate=0.5, db=4, follow=0.0)]),
    'spray': dict(D=6.0, gust=1.0, depth=0.1, bands=[(1500, 9500, 0, 0.0, 9.0, 0.18), (300, 1500, -6, 0.0, 3.0, 0.2), (80, 300, -9, 0.0, 1.0, 0.25),
                                                    (5000, 12000, -6, 0.0, 14.0, 0.2)],
                  events=[dict(kind='tick', rate=45, db=4, follow=0.0), dict(kind='dtick', rate=10, db=3, follow=0.0), dict(kind='pop', rate=0.4, db=6)]),
    'distant': dict(D=8.0, gust=0.4, depth=0.55, bands=[(32, 260, 0, 0.0, 0.5, 0.45), (260, 1300, -9, 0.0, 0.8, 0.6), (1300, 4000, -18, 0.0, 1.5, 0.6)],
                    swell=[(0.6, 0.18), (0.4, 0.12)], swell_roar=0.5,
                    events=[dict(kind='dtick', rate=22, db=6, follow=1.5, swell_pow=1.0), dict(kind='lowpop', rate=0.35, db=8), dict(kind='dtick', rate=3, db=11, pow=3.0)],
                    lp=3200),
}

# near loop level (RMS dBFS over the whole loop), q = Vorbis quality, far = lowpass for the far twin (Hz)
LOOPS = [
    # name, spec, variants, rms, quality, far (fc, variants) or None, extra meta
    ('fire_camp_loop', 'camp', 2, -28.0, 3, (1000, 1)),
    ('fire_medium_loop', 'medium', 2, -26.0, 3, (850, 2)),
    ('fire_large_loop', 'large', 2, -23.0, 2, (520, 2)),
    ('fire_vehicle_loop', 'vehicle', 2, -24.0, 3, (800, 1)),
    ('fire_pool_loop', 'pool', 2, -23.0, 2, (450, 1)),
    ('fire_grass_loop', 'grass', 2, -25.0, 3, (1300, 1)),
    ('fire_tree_loop', 'tree', 2, -24.0, 3, (800, 1)),
    ('fire_gas_loop', 'gas', 2, -28.0, 3, None),
    ('fire_spray_loop', 'spray', 2, -27.0, 3, None),
    ('fire_distant_loop', 'distant', 2, -32.0, 1, None),
]
INTERIOR = [('fire_medium_loop', 'fire_medium_loop_int', 2, -28.5, 1), ('fire_large_loop', 'fire_large_loop_int', 2, -25.0, 1)]


def loop_finish(x, rms_db):
    x = np.asarray(x, dtype=np.float64); x = x - np.mean(x); x = circ_hp(x, 28.0)
    g = 10 ** ((rms_db - 10 * math.log10(np.mean(x ** 2) + 1e-18)) / 20.0); y = x * g
    ceil = 10 ** (CEIL_DB / 20.0)
    if np.max(np.abs(y)) > ceil: y = softlimit(y, ceil)
    return np.clip(y, -ceil, ceil)


LOW_SR = 22050
HI_STEMS = {'fire_pop_ember', 'fire_spark', 'fire_log_crack', 'fire_glass', 'fire_clatter'}     # stay 44.1 kHz (sparkle above 11 kHz)


def to_sr(y, sr):
    """FFT decimation (exactly periodic for loops): 44.1 kHz -> 22.05 kHz keeps content below 11 kHz."""
    if sr == SR: return y
    if len(y) % 2: y = np.append(y, 0.0)
    n = len(y); k = SR // sr; sp = np.fft.rfft(y)
    return np.fft.irfft(sp[:n // (2 * k) + 1], n // k) / k


def save_loop(name, y, quality, meta, **kw):
    y = to_sr(y, LOW_SR); yy = hp(y - np.mean(y), 20, LOW_SR, 1)
    return S.save(name, y, BUS, loop=True, peak=CEIL_DB + 0.4, target_lufs=S.lufs_approx(yy, LOW_SR), quality=quality, sr=LOW_SR, lazy=True, group=GROUP, meta=meta, **kw)


def save_one(sid, y, name, q, **kw):
    sr = SR if name in HI_STEMS else LOW_SR
    y = to_sr(y, sr); yy = hp(y - np.mean(y), 20, sr, 1)
    return S.save(sid, y, BUS, loop=False, peak=CEIL_DB + 0.4, target_lufs=S.lufs_approx(yy, sr), quality=(2 if sr == SR else 1), sr=sr, lazy=True, group=GROUP, **kw)


# ------------------------------------------------------------------ one-shot building blocks
def E_att(n, att, tau):
    t = tt(n); return (1 - np.exp(-t / att)) * np.exp(-t / tau)


def whoosh(r, D, fc0, fc1, tdc, att, tau, lo=70, lump=0.4):
    n = n_of(D); t = tt(n); x = noise(n, 'white', r)
    x = S.tv_filter(x, fc1 + (fc0 - fc1) * np.exp(-t / tdc), 'lp', 2, SR, 256); x = hp(x, lo, SR, 2)
    return unit(x) * E_att(n, att, tau) * np.exp(lump * per_smooth(n, 9, r))


def rumble(r, D, lo, hi, att, tau, lump=0.35):
    n = n_of(D); return unit(band_noise(n, lo, hi, r)) * E_att(n, att, tau) * np.exp(lump * per_smooth(n, 6, r))


def ping(r, f, tau, partials=((1, 1.0, 1.0),), dur=None):
    dur = dur or tau * 6; n = n_of(dur); t = np.arange(n) / SR; y = np.zeros(n)
    for k, a, ts in partials:
        if f * k < 18000: y += a * np.sin(TWO_PI * f * k * t + r.uniform(0, 6.28)) * np.exp(-t / (tau * ts))
    return y


def clack(r, flo=150, fhi=1500):
    f = r.uniform(flo, fhi); tau = r.uniform(0.012, 0.055)
    y = ping(r, f, tau, ((1, 1.0, 1.0), (2.7, 0.5, 0.5), (5.1, 0.2, 0.3)))
    tk = g_tick(r, r.uniform(1500, 5000), 0.002); y[:len(tk)] += tk * 0.5
    return y


def rain_events(out, r, t0, t1, rate_fn, grain_fn, g_fn=lambda t: 1.0, rmax=None):
    rmax = rmax or max(rate_fn(t0), rate_fn(t1), 1.0); t = t0
    while t < t1:
        t += r.exponential(1.0 / rmax)
        if t >= t1: break
        if r.random() < rate_fn(t) / rmax: U.put(out, grain_fn(), t, g_fn(t) * r.uniform(0.4, 1.0))


def trim_tail(x, thr_db=-56.0, keep=0.04):
    a = np.abs(x); pk = np.max(a); w = int(0.01 * SR); env = np.sqrt(np.convolve(a * a, np.ones(w) / w, 'same'))
    idx = np.nonzero(env > pk * 10 ** (thr_db / 20.0))[0]
    end = min(len(x), (idx[-1] if len(idx) else len(x)) + int(keep * SR)); return x[:end]


def one_finish(x, rms_db, tail_fade=0.06):
    x = trim_tail(np.asarray(x, dtype=np.float64)); x = x - np.mean(x); x = hp(x, 22, SR, 2)
    k = min(len(x), int(tail_fade * SR)); x[-k:] *= np.cos(np.linspace(0, math.pi / 2, k)) ** 2
    h = int(0.0015 * SR); x[:h] *= np.linspace(0, 1, h)
    ceil = 10 ** (CEIL_DB / 20.0); g = 10 ** ((rms_db - wrms_db(x)) / 20.0) * 0.3
    for _ in range(10):
        y = softlimit(x * g, ceil); err = rms_db - wrms_db(y)
        if abs(err) < 0.05: break
        g *= 10 ** (err / 20.0)
    return np.clip(softlimit(x * g, ceil), -ceil, ceil)


# ------------------------------------------------------------------ one-shot makers: (r, i) -> array
def m_ember_pop(r, i):
    """Six distinct kinds: soft thump, dry tick, double tick, hollow tup, snap-with-thump, tiny spit."""
    n = n_of(0.24); t = tt(n); kind = i % 6; x = np.zeros(n)
    def add(g, at=0.0, a=1.0):
        j = int(at * SR); e = min(n, j + len(g)); x[j:e] += g[:e - j] * a
    f = r.uniform(130, 340)
    if kind == 0: add(np.sin(TWO_PI * f * t * (1 - 0.3 * np.exp(-t / 0.015)) + r.uniform(0, 6)) * np.exp(-t / r.uniform(0.02, 0.04))); add(g_tick(r, r.uniform(2000, 4000), 0.0025), 0, 0.5)
    elif kind == 1: add(g_tick(r, r.uniform(3500, 7500), 0.0022), 0, 1.0); add(g_snap(r, r.uniform(1800, 2800)), 0.001, 0.35)
    elif kind == 2: add(g_tick(r, r.uniform(2500, 6000), 0.002)); add(g_tick(r, r.uniform(3000, 8000), 0.0018), r.uniform(0.012, 0.05), r.uniform(0.5, 0.9))
    elif kind == 3: add(np.sin(TWO_PI * r.uniform(420, 800) * t + r.uniform(0, 6)) * np.exp(-t / r.uniform(0.01, 0.02)) * (1 - np.exp(-t / 0.0006))); add(g_tick(r, 2500, 0.002), 0, 0.3)
    elif kind == 4: add(g_snap(r, r.uniform(700, 1300))); add(g_pop(r, r.uniform(110, 200)), 0.002, 0.7)
    else: add(g_spit(r), 0, 1.0)
    return x


def m_spark(r, i):
    n = n_of(0.2); x = np.zeros(n); t = tt(n)
    c = bp(r.standard_normal(n), 2800, 14000, SR, 1) * np.exp(-t / 0.0014); x += c / (np.max(np.abs(c)) + 1e-9)
    x += 0.5 * np.sin(TWO_PI * r.uniform(3000, 6500) * t) * np.exp(-t / 0.006)
    for _ in range(r.integers(2, 6)):
        tk = g_tick(r, r.uniform(3000, 9000), 0.0015); j = int(r.uniform(0.004, 0.12) * SR); x[j:j + len(tk)] += tk * r.uniform(0.1, 0.45)
    return x


def m_log_crack(r, i):
    D = 0.75; n = n_of(D); t = tt(n); x = np.zeros(n)
    pre = r.integers(2, 6)
    for k in range(pre):
        tk = g_tick(r, r.uniform(1500, 5000), 0.002); j = int(r.uniform(0.0, 0.07) * SR); x[j:j + len(tk)] += tk * r.uniform(0.15, 0.4) * (k + 1) / pre
    t0 = int(r.uniform(0.07, 0.12) * SR); m = n - t0; tm = np.arange(m) / SR
    c = bp(r.standard_normal(m), 300, 10000, SR, 1) * np.exp(-tm / 0.0045) * np.minimum(1, tm / 0.0003); x[t0:] += 2.0 * c / (np.max(np.abs(c)) + 1e-9)
    body = ping(r, r.uniform(180, 420), r.uniform(0.04, 0.08), ((1, 1.0, 1.0), (2.3, 0.5, 0.6), (3.9, 0.25, 0.4)), 0.4); x[t0:t0 + len(body)] += body * 0.9
    sb = subr(r, 0.35, r.uniform(85, 120), 55, 0.04, 0.09, 0.002); x[t0:t0 + len(sb)] += sb * 0.9
    fol = np.zeros(m)
    rain_events(fol, r, 0.0, 0.35, lambda tq: 130 * math.exp(-tq / 0.1) + 5, lambda: g_snap(r, r.uniform(900, 2400)) * 0.5)
    x[t0:] += fol * 0.6
    return x


def m_beam_creak(r, i):
    D = (2.2, 1.7, 2.6, 2.0, 1.5)[i % 5]; f0 = (75, 105, 62, 130, 90)[i % 5]
    x = creak(r, D, f0, 22 + 6 * i, 55 + 10 * i)
    n = len(x); tk = scatter(n, 8 * np.sin(np.pi * np.arange(n) / n), bank(r, 'tick'), r, 2.0) * 0.12
    return x / (np.max(np.abs(x)) + 1e-9) + tk


def m_glass(r, i):
    D = 1.5; n = n_of(D); x = np.zeros(n); t = tt(n)
    c = hp(r.standard_normal(n), 2200, SR, 2) * np.exp(-t / 0.003); x += 1.2 * c / (np.max(np.abs(c)) + 1e-9)
    x += 0.4 * np.sin(TWO_PI * 190 * t) * np.exp(-t / 0.025)
    for _ in range(r.integers(5, 10)):
        p = ping(r, r.uniform(1400, 4200), r.uniform(0.07, 0.2), ((1, 1.0, 1.0), (2.76, 0.4, 0.5))); U.put(x, p, r.exponential(0.12), r.uniform(0.15, 0.4))
    rain_events(x, r, 0.01, 1.3, lambda tq: 420 * math.exp(-tq / 0.28) + 8, lambda: ping(r, r.uniform(3000, 9500), r.uniform(0.006, 0.03)), lambda tq: 0.25, 450)
    return x


def m_flare(size):
    P = dict(small=dict(D=1.0, att=0.06, tau=0.26, fc=800, f0=70, lv=0.7, rb=0.0), medium=dict(D=1.6, att=0.1, tau=0.5, fc=650, f0=56, lv=0.9, rb=0.4),
             large=dict(D=2.6, att=0.16, tau=0.85, fc=520, f0=44, lv=1.0, rb=0.9))[size]

    def mk(r, i):
        D = P['D']; n = n_of(D); t = tt(n); j = r.uniform(0.9, 1.15)
        w = whoosh(r, D, P['fc'] * r.uniform(1.6, 3.0) * j, P['fc'] * r.uniform(0.35, 0.7), D * r.uniform(0.15, 0.35), P['att'] * j, P['tau'] * j, 60)
        s = subr(r, D, P['f0'] * r.uniform(1.15, 1.7) * j, P['f0'] * r.uniform(0.65, 0.95), r.uniform(0.08, 0.22), P['tau'] * r.uniform(0.6, 1.0), r.uniform(0.01, 0.05)) * (1 - np.exp(-t / (P['att'] * 0.7)))
        x = w + P['lv'] * unit(s) * 0.9
        if P['rb']: x += P['rb'] * rumble(r, D, 28, 130, P['att'] * 1.5, P['tau'] * 1.6)
        cr = scatter(n, 50 * np.exp(-t / (D * 0.35)) * (1 - np.exp(-t / 0.05)), bank(r, 'tick'), r, 2.0) * 0.5
        return x + cr * 0.8
    return mk


def m_ignite_soft(r, i):
    D = 0.9; n = n_of(D); t = tt(n); j = r.uniform(0.9, 1.15)
    s = subr(r, 0.45, r.uniform(75, 125) * j, r.uniform(38, 58), r.uniform(0.02, 0.06), r.uniform(0.06, 0.14), 0.004); x = np.zeros(n); x[:len(s)] += unit(s) * r.uniform(0.6, 1.1)
    x += r.uniform(0.5, 1.0) * whoosh(r, D, r.uniform(900, 2400), r.uniform(200, 450), r.uniform(0.07, 0.2), r.uniform(0.008, 0.05), r.uniform(0.1, 0.28), r.uniform(60, 160))
    x += 0.25 * scatter(n, 60 * np.exp(-t / 0.3), bank(r, 'tick'), r)
    return x


def m_ignite_large(r, i):
    D = 2.4; n = n_of(D); t = tt(n); j = r.uniform(0.9, 1.12)
    s = subr(r, 1.1, 70 * j, 36, 0.06, 0.28, 0.006); x = np.zeros(n); x[:len(s)] += 1.1 * unit(s)
    x += 1.0 * whoosh(r, D, 2400 * j, 280, 0.35, 0.05, 0.55, 60)
    x += 0.8 * rumble(r, D, 28, 150, 0.08, 0.9)
    rain_events(x, r, 0.2, 2.0, lambda tq: 14 * math.exp(-tq / 0.7) + 1, lambda: g_lowpop(r), lambda tq: 0.25)
    x += 0.3 * scatter(n, 80 * np.exp(-t / 0.7), bank(r, 'tick'), r)
    return x


def m_tank_burst(r, i):
    D = 2.6; n = n_of(D); t = tt(n); j = r.uniform(0.92, 1.1)
    c = bp(r.standard_normal(n_of(0.05)), 400, 6000, SR, 1) * np.exp(-tt(0.05) / 0.005); x = np.zeros(n); x[:len(c)] += 0.8 * c / (np.max(np.abs(c)) + 1e-9)
    s = subr(r, 0.7, 90 * j, 38, 0.05, 0.22, 0.003); x[:len(s)] += 1.0 * unit(s)
    x += 1.1 * whoosh(r, D, 3500 * j, 260, 0.3, 0.03, 0.5, 70, 0.5)
    x += 0.9 * rumble(r, D, 26, 140, 0.05, 0.85)
    rain_events(x, r, 0.4, 2.3, lambda tq: 40 * math.exp(-tq / 0.5) + 1, lambda: clack(r, 120, 900), lambda tq: 0.25)
    x += 0.4 * scatter(n, 100 * np.exp(-t / 0.8), bank(r, 'tick'), r)
    return x


def m_lick(r, i):
    D = (0.6, 0.75, 0.9, 0.65, 0.8)[i % 5]; n = n_of(D); t = tt(n); env = np.sin(np.pi * t / D) ** 2
    fc = 350 + 1700 * env; x = S.tv_filter(noise(n, 'white', r), fc, 'lp', 2, SR, 256); x = hp(x, 180, SR, 2)
    x = unit(x) * env * np.exp(0.35 * per_smooth(n, 9, r))
    x += 0.25 * scatter(n, 40 * env, bank(r, 'tick'), r)
    return x


def m_collapse(far=False):
    def mk(r, i):
        D = 4.2; n = n_of(D); x = np.zeros(n); t = tt(n); t0 = r.uniform(0.9, 1.15)
        g = creak(r, 1.1, r.uniform(60, 95), 20, 50); U.put(x, g / (np.max(np.abs(g)) + 1e-9), 0.0, 0.5)
        rain_events(x, r, 0.1, t0 + 0.05, lambda tq: 4 + 60 * (tq / t0) ** 2, lambda: g_snap(r, r.uniform(500, 1800)), lambda tq: 0.3 + 0.7 * tq / t0, 70)
        rain_events(x, r, t0, t0 + 2.4, lambda tq: 230 * math.exp(-(tq - t0) / 0.55) + 6, lambda: clack(r, 90, 1200), lambda tq: 0.5 * math.exp(-(tq - t0) / 1.2) + 0.12, 240)
        rain_events(x, r, t0, t0 + 1.2, lambda tq: 26 * math.exp(-(tq - t0) / 0.5), lambda: g_lowpop(r), lambda tq: 0.9 * math.exp(-(tq - t0) / 0.8), 26)
        U.put(x, rumble(r, 3.2, 26, 190, 0.12, 1.0), t0, 1.5)
        U.put(x, whoosh(r, 2.0, 2200, 350, 0.4, 0.06, 0.55, 90), t0 + 0.03, 0.7)
        s = subr(r, 0.8, r.uniform(55, 75), r.uniform(30, 38), 0.08, 0.3, 0.01); U.put(x, unit(s), t0, 1.2)
        rain_events(x, r, t0 + 1.0, D - 0.2, lambda tq: 55 * math.exp(-(tq - t0 - 1) / 0.9) + 3, lambda: g_tick(r, r.uniform(2000, 7000)), lambda tq: 0.2)
        return x
    return mk


def m_clatter(r, i):
    D = 1.5; n = n_of(D); x = np.zeros(n)
    rain_events(x, r, 0.0, D - 0.1, lambda tq: 55 * math.exp(-tq / 0.38) + 2, lambda: clack(r, 180, 2600), lambda tq: 0.4 + 0.6 * math.exp(-tq / 0.6), 60)
    rain_events(x, r, 0.0, 0.8, lambda tq: 9 * math.exp(-tq / 0.3), lambda: g_softpop(r), lambda tq: 0.6, 9)
    return x


def m_water_hit(long):
    def mk(r, i):
        D = 3.0 if long else 1.0; n = n_of(D); t = tt(n); tau = 0.9 if long else 0.22; j = r.uniform(0.9, 1.12)
        x = noise(n, 'white', r); x = S.tv_filter(x, 3000 + 7000 * np.exp(-t / (tau * 1.4)), 'lp', 2, SR, 256); x = hp(x, 1100, SR, 2)
        x = unit(x) * np.minimum(1, t / 0.006) * np.exp(-t / tau) * np.exp(0.5 * per_smooth(n, 14, r))
        body = unit(S.tv_filter(noise(n, 'white', r), 1200 * np.exp(-t / tau) + 250, 'lp', 2, SR, 256)) * np.minimum(1, t / 0.01) * np.exp(-t / (tau * 0.8))
        bub = U.bubble_cloud(D, 450 * j, 2200 * j, (45 if long else 70), tau * 0.9, r)
        bub = U.fit(bub, D); bub = bub / (np.max(np.abs(bub)) + 1e-9)
        sp = scatter(n, 70 * np.exp(-t / (tau * 0.8)) + 2, bank(r, 'spit'), r) * 0.35
        return x + 0.55 * body + 0.35 * bub + sp
    return mk


def m_out_fade(r, i):
    D = (2.6, 3.0, 2.3)[i % 3]; n = n_of(D); t = tt(n)
    x = noise(n, 'white', r); x = S.tv_filter(x, 1300 + 6500 * np.exp(-t / 0.9), 'lp', 2, SR, 256); x = hp(x, 900, SR, 2)
    env = np.minimum(1, t / 0.08) * np.exp(-t / (D * 0.3)) * np.cos(np.clip(t / D, 0, 1) * np.pi / 2) ** 2
    x = unit(x) * env * np.exp(0.4 * per_smooth(n, 10, r))
    y = scatter(n, 40 * np.exp(-t / 0.9), bank(r, 'spit'), r) * 0.4 + scatter(n, 3 * np.exp(-t / 1.2), bank(r, 'pop'), r) * 0.35
    return x + y * np.cos(np.clip(t / D, 0, 1) * np.pi / 2)


def m_sizzle(r, i):
    D = (2.5, 3.0, 2.2)[i % 3]; n = n_of(D); t = tt(n)
    tk = scatter(n, 420 * np.exp(-t / (D * 0.35)) + 8, bank(r, 'tick'), r, 1.5, 0.08)
    h = hp(noise(n, 'white', r), 4000, SR, 2); h = unit(lp(h, 11000, SR, 2)) * 0.12 * np.exp(-t / (D * 0.3))
    return tk + h


def farize(maker, lpf, rt, wet):
    def mk(r, i):
        x = maker(r, i); x = lp(np.pad(x, (0, int(0.2 * SR))), lpf, SR, 4)
        return reverb(x, rt, wet, 800, r)
    return mk


# one-shot table: stem, maker, variants, rms class, quality, meta.play, size/kind meta
# play: gapMs, maxVoices, preloadSize ... added generically below
ONE = [
    ('fire_pop_ember', m_ember_pop, 6, -26.0, 3, dict(gapMs=110, maxVoices=3, dist=40), 'ember pop'),
    ('fire_spark', m_spark, 5, -25.5, 3, dict(gapMs=90, maxVoices=3, dist=35), 'spark crack'),
    ('fire_log_crack', m_log_crack, 5, -22.0, 3, dict(gapMs=350, maxVoices=2, dist=70), 'log crack'),
    ('fire_beam_creak', m_beam_creak, 5, -27.0, 2, dict(gapMs=3500, maxVoices=1, dist=80), 'wood beam creak/groan'),
    ('fire_glass', m_glass, 4, -22.0, 3, dict(gapMs=700, maxVoices=2, dist=90), 'glass shatter in fire'),
    ('fire_flare_small', m_flare('small'), 4, -23.0, 2, dict(gapMs=900, maxVoices=2, dist=60), 'flare-up whoomph small'),
    ('fire_flare_medium', m_flare('medium'), 4, -21.0, 2, dict(gapMs=1500, maxVoices=2, dist=110), 'flare-up whoomph medium'),
    ('fire_flare_large', m_flare('large'), 4, -19.0, 2, dict(gapMs=3000, maxVoices=1, dist=220), 'flare-up whoomph large'),
    ('fire_ignite_soft', m_ignite_soft, 4, -23.0, 2, dict(gapMs=600, maxVoices=2, dist=60), 'ignition whump soft'),
    ('fire_ignite_large', m_ignite_large, 4, -18.0, 2, dict(gapMs=2500, maxVoices=1, dist=220), 'large fuel ignition whump'),
    ('fire_tank_burst', m_tank_burst, 4, -18.5, 2, dict(gapMs=1500, maxVoices=2, dist=260), 'fuel tank burst, fireball whoosh'),
    ('fire_lick', m_lick, 5, -26.0, 2, dict(gapMs=450, maxVoices=3, dist=45), 'flame lick whoosh'),
    ('fire_collapse', m_collapse(), 4, -18.0, 2, dict(gapMs=6000, maxVoices=1, dist=300), 'burning timber collapse'),
    ('fire_clatter', m_clatter, 4, -25.0, 3, dict(gapMs=900, maxVoices=2, dist=60), 'burning debris clatter'),
    ('fire_water_hiss_short', m_water_hit(False), 4, -22.0, 3, dict(gapMs=250, maxVoices=3, dist=80), 'water on fire, short hiss'),
    ('fire_water_hiss_long', m_water_hit(True), 4, -22.0, 3, dict(gapMs=1200, maxVoices=2, dist=100), 'water on fire, long hiss + steam'),
    ('fire_out_fade', m_out_fade, 3, -26.0, 3, dict(gapMs=800, maxVoices=2, dist=70), 'extinguish hiss fade tail'),
    ('fire_sizzle', m_sizzle, 3, -27.0, 3, dict(gapMs=1200, maxVoices=2, dist=30), 'embers sizzling out'),
]
FAR_ONE = [
    ('fire_flare_large_far', m_flare('large'), 'fire_flare_large', 2, -23.0, 650, 1.6, 0.4),
    ('fire_tank_burst_far', m_tank_burst, 'fire_tank_burst', 2, -22.0, 600, 2.0, 0.5),
    ('fire_collapse_far', m_collapse(), 'fire_collapse', 2, -23.0, 650, 2.2, 0.5),
]


# ------------------------------------------------------------------ render
def want(name, flt): return not flt or flt in name


def render(flt=None):
    S.set_manifest('fire'); t0 = time.time(); sizes = {}
    for (name, sp, nv, rms, q, far) in LOOPS:
        spec = SPEC[sp]; D = spec['D']; near_all = []
        for i in range(nv):
            sid = '%s_%02d' % (name, i + 1)
            r = rng(U.seed_of(name, i)); x = fire_loop(r, D, {k: v for k, v in spec.items() if k != 'D'})
            if sp == 'grass' and i == 1:   # second grass variant: stronger front passing
                pass
            y = loop_finish(x, rms); near_all.append(y)
            if want(sid, flt):
                save_loop(sid, y, 1, dict(kind='loop', fire=sp, role='near', play=dict(gapMs=0, maxVoices=2, rotate=nv, preload=False, bus=BUS), xfadePair=('%s_far_%02d' % (name, min(i, far[1] - 1) + 1)) if far else None))
        if far:
            fc, fv = far
            for i in range(fv):
                sid = '%s_far_%02d' % (name, i + 1)
                y = loop_finish(clp(near_all[i], fc, 4), rms - 4.0)
                if want(sid, flt):
                    save_loop(sid, y, 1, dict(kind='loop', fire=sp, role='far', play=dict(gapMs=0, maxVoices=2, rotate=fv, preload=False, bus=BUS), xfadePair='%s_%02d' % (name, i + 1)))
        print('loops', name, '%.0fs' % (time.time() - t0), flush=True)
        if flt is None or flt in name:
            for (src, dst, nv2, rms2, q2) in INTERIOR:
                if src != name: continue
                for i in range(nv2):
                    y = loop_finish(clp(near_all[i], 2000, 4), rms2)
                    save_loop('%s_%02d' % (dst, i + 1), y, q2, dict(kind='loop', fire=sp, role='interior', play=dict(gapMs=0, maxVoices=1, rotate=nv2, preload=False, bus=BUS)))
    for (name, mk, nv, rms, q, play, desc) in ONE:
        for i in range(nv):
            sid = '%s_%02d' % (name, i + 1)
            if not want(sid, flt): continue
            r = rng(U.seed_of(name, i)); y = one_finish(mk(r, i), rms)
            p = dict(gapMs=play['gapMs'], maxVoices=play['maxVoices'], rotate=nv, preload=False, bus=BUS)
            save_one(sid, y, name, q,
                   variants=nv, weight=2.0, max_dist=play['dist'], meta=dict(kind='oneshot', what=desc, play=p), tags=['fire'])
        print('one-shot', name, '%.0fs' % (time.time() - t0), flush=True)
    for (name, mk, src, nv, rms, lpf, rt, wet) in FAR_ONE:
        for i in range(nv):
            sid = '%s_%02d' % (name, i + 1)
            if not want(sid, flt): continue
            r = rng(U.seed_of(src, i)); y = one_finish(farize(mk, lpf, rt, wet)(r, i), rms)
            save_one(sid, y, name, 1,
                   variants=nv, weight=2.0, max_dist=600, gain=0.8, meta=dict(kind='oneshot', what='distant version of ' + src, play=dict(gapMs=3000, maxVoices=1, rotate=nv, preload=False, bus=BUS)), tags=['fire', 'far'])
        print('far one-shot', name, flush=True)


def finalize_meta():
    """Add size-driven maxDist / weights / xfade hints to the fragment."""
    mp = os.path.join(S.OUT, 'manifest.fire.json'); d = json.load(open(mp, encoding='utf-8'))
    DIST = dict(camp=(25, 12, 40), medium=(40, 25, 75), large=(90, 60, 220), vehicle=(45, 30, 110), pool=(65, 40, 160), grass=(50, 35, 130), tree=(45, 30, 100),
                gas=(20, 0, 30), spray=(35, 0, 60), distant=(180, 0, 700))
    import re
    cnt = {}
    for k in d: cnt[re.sub(r'_\d\d$', '', k)] = cnt.get(re.sub(r'_\d\d$', '', k), 0) + 1
    for k, e in d.items():
        e['variants'] = cnt[re.sub(r'_\d\d$', '', k)]
        m = e.get('meta', {})
        if m.get('kind') != 'loop': continue
        fk = m['fire']; near, xa, mx = DIST[fk]
        if m['role'] == 'near': e['maxDist'] = near * 1.6 if xa else mx; m['xfade'] = [near * 0.5, near * 1.6] if xa else None; e['weight'] = 3.0
        elif m['role'] == 'far': e['maxDist'] = mx; m['xfade'] = [near * 0.5, near * 1.6]; e['weight'] = 2.0; e['tags'] = ['fire', 'far']
        else: e['maxDist'] = 20; m['xfade'] = None; e['weight'] = 3.0; e['tags'] = ['fire', 'interior']
        if m['role'] == 'near': e['tags'] = ['fire', fk]
        if fk == 'distant': e['maxDist'] = 700; e['gain'] = 0.9; e['bus'] = 'amb'; m['play']['bus'] = 'amb'
        e['rate'] = [0.94, 1.06]
    json.dump(d, open(mp, 'w', encoding='utf-8'), indent=1)


def deploy():
    here = os.path.dirname(os.path.abspath(__file__)); dst = os.path.join(os.path.dirname(here), 'audio')
    frag = json.load(open(os.path.join(here, 'out', 'manifest.fire.json'), encoding='utf-8'))
    mp = os.path.join(dst, 'manifest.json'); man = json.load(open(mp, encoding='utf-8'))
    for id_, e in frag.items():
        base = id_.rsplit('_', 1)[0]
        assert base not in PROTECTED, id_
        shutil.copy2(os.path.join(here, 'out', id_ + '.ogg'), os.path.join(dst, id_ + '.ogg'))
        man['assets'][id_] = e
    json.dump(man, open(mp, 'w', encoding='utf-8'))
    print('deployed %d fire assets into %s' % (len(frag), dst))


if __name__ == '__main__':
    flt = next((a for a in sys.argv[1:] if not a.startswith('--')), None)
    if '--meta-only' in sys.argv:
        finalize_meta(); deploy(); sys.exit(0)
    mpf = os.path.join(S.OUT, 'manifest.fire.json'); old = {}
    if flt and os.path.exists(mpf): old = json.load(open(mpf, encoding='utf-8'))
    render(flt)
    if old:
        new = json.load(open(mpf, encoding='utf-8')); old.update(new); json.dump(old, open(mpf, 'w', encoding='utf-8'), indent=1)
    finalize_meta()
    if '--no-deploy' not in sys.argv: deploy()
