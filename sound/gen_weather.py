"""Weather and disaster events for Squall Cove: thunder, lightning crack, tornado, quake, tsunami, meteor, eruption, landslide, hail.

Events are mono one-shots (peak -3 dBFS); the loops (tornado, eruption, hail) are stereo beds built with gen_ambience.bed().
"""
import math
import numpy as np
import synthlib as S
from synthlib import SR, rng, lp, hp, bp, noise, tv_filter, tv_bandpass, n_of
from gen_ambience import (bed, pmod, circ_add, pan_gains, scatter_rate, clip_pool, g_click, g_ping, TWO_PI)


def _t(dur):
    return np.arange(n_of(dur)) / SR


def _taper(x, tail=0.4):
    k = int(tail * SR)
    x = x.copy()
    x[-k:] *= np.cos(np.linspace(0, math.pi / 2, k)) ** 2
    return x


# ------------------------------------------------------------------ thunder
def thunder(seed, near, dur):
    r = rng(seed)
    n = n_of(dur); t = np.arange(n) / SR
    env = np.zeros(n)
    t_first = 0.04 if near else 0.1
    npulse = int(r.integers(7, 12))
    gaps = r.exponential(0.5 if near else 0.75, npulse)
    gaps[0] = 0
    times = t_first + np.cumsum(gaps)
    for i, t0 in enumerate(times):
        a = r.uniform(0.35, 1.0) * math.exp(-(t0 - t_first) / (dur * (0.32 if near else 0.4)))
        if i == 0:
            a = 1.0
        att = r.uniform(0.02, 0.12) if near else r.uniform(0.18, 0.55)
        tau = r.uniform(0.35, 1.1) * (1.0 if near else 1.35)
        dt = t - t0
        sh = np.where(dt > 0, (1 - np.exp(-np.maximum(dt, 0) / att)) * np.exp(-np.maximum(dt, 0) / tau), 0)
        env += a * sh
    # long tail: a slow swell of distant reflections
    tail = (1 - np.exp(-np.maximum(t - 0.6, 0) / 0.8)) * np.exp(-t / (dur * 0.3))
    env += 0.35 * tail
    env /= env.max()
    if near:
        cut = 180 + 1400 * np.exp(-t / 0.9) + 600 * np.exp(-t / (dur * 0.3))
    else:
        cut = 130 + 520 * np.exp(-t / (dur * 0.45))
    src = 0.6 * noise(n, 'brown', r) + 0.6 * noise(n, 'pink', r)
    x = tv_filter(src, cut, 'lp', 2, SR, 512) * env
    sub = lp(noise(n, 'brown', r), 60, SR, 2)
    x = x / (np.std(x) + 1e-9) + (0.7 if near else 0.5) * sub / (np.std(sub) + 1e-9) * env ** 1.3
    if near:  # branching: a few mid-frequency tears in the first 1.5 s
        for _ in range(int(r.integers(5, 9))):
            t0 = r.uniform(0.0, 1.5); d = r.uniform(0.04, 0.16); k = int(d * SR)
            b = bp(r.standard_normal(k), r.uniform(200, 500), r.uniform(900, 1800), SR, 2) * np.exp(-np.arange(k) / (k * 0.3))
            x[int(t0 * SR):int(t0 * SR) + k] += b * r.uniform(0.2, 0.7) * math.exp(-t0 / 1.5)
    x = x * np.minimum(1, t / (0.01 if near else 0.2))
    return _taper(x, 0.6)


def crack(seed, dur):
    r = rng(seed)
    n = n_of(dur); t = np.arange(n) / SR
    x = np.zeros(n)
    x[:int(0.0006 * SR)] += 1.0                         # the strike click
    k = int(0.03 * SR)
    cr = hp(r.standard_normal(k), 1500, SR, 2) * np.exp(-np.arange(k) / (k * 0.2))
    x[:k] += cr * 3.0
    for _ in range(int(r.integers(14, 26))):            # tearing pops along the channel
        t0 = r.exponential(0.14); k = int(r.uniform(0.003, 0.02) * SR)
        b = bp(r.standard_normal(k), r.uniform(900, 2500), r.uniform(3000, 7000), SR, 2) * np.exp(-np.arange(k) / (k * 0.3))
        i0 = int(t0 * SR)
        if i0 + k < n:
            x[i0:i0 + k] += b * r.uniform(0.3, 1.2) * math.exp(-t0 / 0.25)
    # body boom and tail
    bd = tv_filter(noise(n, 'pink', r), 100 + 1400 * np.exp(-t / 0.18), 'lp', 2, SR, 256) * np.exp(-t / 0.45) * np.minimum(1, t / 0.004)
    x += bd / (np.std(bd) + 1e-9) * 0.12
    th = np.sin(TWO_PI * (62 - 20 * (1 - np.exp(-t / 0.4))) * t) * np.exp(-t / 0.3) * 0.15
    x += th
    tl = lp(noise(n, 'brown', r), 220, SR, 2) * np.exp(-t / 0.9) * np.minimum(1, t / 0.08)
    x += tl / (np.std(tl) + 1e-9) * 0.08
    x = lp(x, 14000, SR, 1)
    return _taper(S.soft_clip(x * 0.8, 1.2), 0.3)


# ------------------------------------------------------------------ loops
def make_tornado(D, seed):
    def mk(r, n, D, ch, shared):
        nD = int(round(D * SR))
        g = pmod(n, D, r, 1, 5, 0.9)
        sw = pmod(n, D, r, 14, 45, 0.5)
        roar = tv_filter(noise(n, 'brown', r), 220 + 380 * g, 'lp', 2, SR, 1024) * 2.2 * (0.6 + 0.4 * g)
        train = tv_filter(noise(n, 'pink', r), 900 + 1400 * g, 'lp', 2, SR, 1024) * 0.7 * (0.4 + 0.6 * g)
        swirl = tv_bandpass(noise(n, 'white', r), 350 + 650 * sw, 1.4, 2, SR, 1024) * (0.3 + 0.7 * sw) * 0.9
        flut = lp(noise(n, 'white', r), 11, SR, 2); flut /= (np.std(flut) + 1e-9)
        x = (roar + train + swirl) * np.clip(1 + 0.3 * flut, 0.3, 2)
        rr = rng(seed * 3 + ch)
        pool = [g_click(rr, i, 300, 2500, 0.004, 0.03) for i in range(40)]
        c = scatter_rate(nD, D, lambda ts: 22 + 0 * ts, 26, pool, rr, lognorm=0.7, pan=1, ch=ch) * 0.6
        return x, c
    return bed(mk, D, seed)


def boom_grain(r, f0, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 * (1 + 0.8 * np.exp(-t / 0.08))
    y = np.sin(TWO_PI * np.cumsum(f) / SR) * np.exp(-t / (dur * 0.3)) * np.minimum(1, t / 0.01)
    k = int(0.06 * SR)
    y[:k] += lp(r.standard_normal(k), 900, SR, 2) * np.exp(-np.arange(k) / (k * 0.3)) * 0.8
    return y


def make_eruption_loop(D, seed):
    def mk(r, n, D, ch, shared):
        nD = int(round(D * SR))
        g = pmod(n, D, r, 1, 6, 0.9)
        roar = tv_filter(noise(n, 'brown', r), 160 + 180 * g, 'lp', 2, SR, 1024) * 2.5 * (0.6 + 0.4 * g)
        mid = tv_bandpass(noise(n, 'pink', r), 250 + 600 * pmod(n, D, r, 3, 14, 0.7), 1.5, 2, SR, 1024) * 0.55 * (0.4 + 0.6 * g)
        hiss = hp(lp(noise(n, 'white', r), 6500, SR, 2), 1800, SR, 2) * 0.04 * (0.4 + 0.6 * g)
        c = np.zeros(nD)
        for tb in (1.1, 4.7, 5.9, 9.3):                    # irregular big booms (shared timing, per-channel pan)
            gr = boom_grain(shared, shared.uniform(42, 62), 1.6) * shared.uniform(0.6, 1.0)
            circ_add(c, (tb + shared.uniform(-0.2, 0.2)) * SR, gr * 1.3)
        rr = rng(seed * 5 + ch)
        pool = [g_click(rr, i, 500, 4500, 0.003, 0.03) for i in range(60)]
        pool += [S.modal(float(rr.uniform(300, 1200)), 'stone', 0.25, 0.9, 0.7, 0.01, rr) * 0.4 for _ in range(20)]
        c += scatter_rate(nD, D, lambda ts: 14 + 0 * ts, 18, pool, rr, lognorm=0.8, pan=1, ch=ch) * 0.45
        return roar + mid + hiss, c
    return bed(mk, D, seed)


def make_hail(D, seed):
    def mk(r, n, D, ch, shared):
        nD = int(round(D * SR))
        rr = rng(seed * 9 + ch)
        small = [g_click(rr, i, 1800, 6500, 0.002, 0.008) for i in range(40)] + [g_ping(rr, i, 1500, 4200, 0.012) for i in range(24)]
        small += [S.modal(float(rr.uniform(900, 3200)), 'plastic', 0.06, 0.7, 1.0, 0.02, rr) for _ in range(30)]
        big = [S.modal(float(rr.uniform(500, 1500)), 'stone', 0.15, 0.6, 0.8, 0.02, rr) * 0.9 for _ in range(16)]
        dens = pmod(256, D * 256 / 255, rr, 1, 6, 0.8)
        rate = lambda ts: 70 + 70 * np.interp(ts, np.linspace(0, D, 256), dens)
        c = scatter_rate(nD, D, rate, 150, small, rr, lognorm=0.6, pan=1, ch=ch) * 1.2
        c += scatter_rate(nD, D, lambda ts: 7 + 0 * ts, 8, big, rr, lognorm=0.5, pan=1, ch=ch) * 1.5
        x = bp(noise(n, 'pink', r), 700, 5500, SR, 2) * 0.2 * (0.7 + 0.3 * pmod(n, D, r, 2, 9, 0.8))
        return x, c
    return bed(mk, D, seed)


# ------------------------------------------------------------------ disasters
def quake(seed, dur=6.0):
    r = rng(seed); n = n_of(dur); t = np.arange(n) / SR
    env = np.minimum(1, t / 0.8) ** 1.5 * np.exp(-np.maximum(t - 3.4, 0) / 0.9)
    puls = 0.6 + 0.4 * np.interp(t, np.linspace(0, dur, 40), r.random(40))
    shake = lp(noise(n, 'white', r), 7, SR, 2); shake = 0.7 + 0.5 * shake / (np.std(shake) + 1e-9)
    x = lp(noise(n, 'brown', r), 85, SR, 2); x = x / (np.std(x) + 1e-9) * 1.0
    for f in (33.0, 46.0, 58.0, 71.0):
        x += 0.5 * np.sin(TWO_PI * np.cumsum(f * (1 + 0.04 * np.sin(TWO_PI * r.uniform(0.3, 0.9) * t + r.uniform(0, 6)))) / SR)
    x *= env * puls * np.clip(shake, 0.2, 2)
    rat = tv_bandpass(noise(n, 'pink', r), 220 + 400 * pmod(n, dur, r, 5, 18), 1.4, 2, SR, 512) * env * 0.5 * (0.3 + 0.7 * pmod(n, dur, r, 8, 30, 0.5))
    x += rat / (np.std(rat) + 1e-9) * 0.35
    for _ in range(5):                                   # rock and masonry cracking
        t0 = r.uniform(0.8, 4.0); k = int(r.uniform(0.05, 0.14) * SR)
        b = bp(r.standard_normal(k), 150, r.uniform(700, 1500), SR, 2) * np.exp(-np.arange(k) / (k * 0.25))
        x[int(t0 * SR):int(t0 * SR) + k] += b * r.uniform(1.0, 2.2)
    return _taper(x, 0.7)


def tsunami(seed, dur=6.0):
    r = rng(seed); n = n_of(dur); t = np.arange(n) / SR
    pk = 2.9
    env = np.where(t < pk, (t / pk) ** 2.2, np.exp(-(t - pk) / 1.1)) + 0.0
    cut = 70 + 600 * np.clip(env, 0, 1) ** 1.2
    x = tv_filter(noise(n, 'pink', r), cut, 'lp', 2, SR, 512)
    x = x / (np.std(x) + 1e-9)
    sub = lp(noise(n, 'brown', r), 55, SR, 2); sub = sub / (np.std(sub) + 1e-9)
    surge = tv_bandpass(noise(n, 'pink', r), 300 + 700 * env, 1.5, 2, SR, 512) * (0.4 + 0.6 * pmod(n, dur, r, 4, 14, 0.6))
    surge = surge / (np.std(surge) + 1e-9)
    y = (x * 0.9 + sub * 1.3 + surge * 0.45) * env
    y += 0.5 * np.sin(TWO_PI * np.cumsum(38 + 6 * env) / SR) * env
    return _taper(y, 0.8)


def meteor_whistle(seed, dur=3.2):
    r = rng(seed); n = n_of(dur); t = np.arange(n) / SR; u = t / dur
    env = u ** 2.2 * np.minimum(1, (dur - t) / 0.05)
    f = 2600 * np.exp(-1.6 * u) + 500
    tonal = sweep_tone(f, (1.0, 0.35, 0.15)) + 0.7 * sweep_tone(f * 1.013, (1.0, 0.3))
    tonal *= (1 + 0.15 * np.sin(TWO_PI * 11 * t))
    hs = tv_bandpass(noise(n, 'white', r), f * 0.9, 0.9, 2, SR, 512)
    roar = tv_filter(noise(n, 'brown', r), 120 + 600 * u ** 1.5, 'lp', 2, SR, 512)
    y = (tonal * 0.45 + hs / (np.std(hs) + 1e-9) * 0.45 + roar / (np.std(roar) + 1e-9) * 0.7) * env
    y = lp(y, 7000, SR, 2)
    return y


def sweep_tone(f, harm):
    ph = TWO_PI * np.cumsum(f) / SR
    return sum(a * np.sin((h + 1) * ph) for h, a in enumerate(harm))


def big_boom(seed, dur, f_hi, f_lo, debris, crackle_len, tail_tau):
    r = rng(seed); n = n_of(dur); t = np.arange(n) / SR
    f = f_lo + (f_hi - f_lo) * np.exp(-t / 0.28)
    boom = np.sin(TWO_PI * np.cumsum(f) / SR) * np.exp(-t / (dur * 0.2)) * np.minimum(1, t / 0.006)
    k = int(0.35 * SR)
    burst = np.zeros(n)
    burst[:k] = tv_filter(r.standard_normal(k), 2500 * np.exp(-np.arange(k) / (0.07 * SR)) + 200, 'lp', 2, SR, 128) * np.exp(-np.arange(k) / (0.08 * SR))
    burst *= 1.5
    cut = 90 + 1300 * np.exp(-t / 0.5)
    roll = tv_filter(noise(n, 'brown', r), cut, 'lp', 2, SR, 512)
    roll = roll / (np.std(roll) + 1e-9) * np.exp(-t / tail_tau) * np.minimum(1, t / 0.02)
    x = boom * 1.4 + burst / (np.std(burst) + 1e-9) * 0.6 * np.exp(-t / 0.15) + roll * 0.9
    sub = np.sin(TWO_PI * np.cumsum(38 * (1 + 0.4 * np.exp(-t / 0.4))) / SR) * np.exp(-t / (tail_tau * 0.6)) * 0.7
    x += sub
    for i in range(debris):                              # falling rock and clatter
        t0 = 0.4 + r.exponential(crackle_len)
        if t0 > dur - 0.8:
            continue
        g = S.modal(float(r.uniform(180, 1100)), 'stone', 0.3, 1.0, 0.8, 0.02, r) * r.uniform(0.04, 0.2) * math.exp(-t0 / (crackle_len * 1.6))
        i0 = int(t0 * SR); x[i0:i0 + len(g)] += g[:n - i0]
    x = S.soft_clip(x * 0.7, 1.6)
    return _taper(x, 0.8)


def eruption_boom(seed, dur=5.5):
    r = rng(seed)
    x = big_boom(seed, dur, 85, 28, 28, 0.9, 1.5)
    n = len(x); t = np.arange(n) / SR
    gas = hp(lp(noise(n, 'white', r), 5000, SR, 2), 500, SR, 2) * np.exp(-t / 1.2) * np.minimum(1, t / 0.15) * 0.35
    return _taper(x + gas / (np.std(gas) + 1e-9) * 0.18 * np.exp(-t / 1.2), 0.8)


def meteor_impact(seed, dur=4.5):
    return big_boom(seed, dur, 150, 30, 40, 0.7, 1.2)


def landslide(seed, dur=6.0):
    r = rng(seed); n = n_of(dur); t = np.arange(n) / SR
    env = np.minimum(1, t / 0.7) ** 1.3 * np.exp(-np.maximum(t - 2.6, 0) / 1.1)
    irr = 0.65 + 0.35 * np.interp(t, np.linspace(0, dur, 60), r.random(60))
    cut = 90 + 420 * np.exp(-t / 2.2)
    x = tv_filter(noise(n, 'brown', r), cut, 'lp', 2, SR, 512)
    x = x / (np.std(x) + 1e-9) * env * irr
    mid = tv_bandpass(noise(n, 'pink', r), 300 + 400 * np.exp(-t / 2.0), 1.6, 2, SR, 512) * env * irr
    x += mid / (np.std(mid) + 1e-9) * 0.35
    pool = []
    for i in range(48):
        f0 = float(r.uniform(140, 1500)); sz = float(r.uniform(0.4, 1.4))
        pool.append(S.modal(f0, 'stone', 0.35, sz, 0.6 + 0.5 * r.random(), 0.02, r) * r.uniform(0.3, 1.0))
    clat = S.grains(dur - 0.5, lambda tt: 4 + 55 * np.exp(-tt / 1.6) * min(1, tt / 0.4), lambda rr, i: pool[rr.integers(len(pool))], r)
    clat = np.pad(clat, (0, n - len(clat)))[:n]
    x += clat * 0.45 * np.exp(-np.maximum(t - 3.0, 0) / 1.4)
    for _ in range(4):                                   # big boulder thumps
        t0 = r.uniform(0.6, 3.2); g = S.impact('stone', float(r.uniform(90, 200)), 1.4, 0.35, 0.6, int(r.integers(1, 9999)), thump=1.2) * r.uniform(0.5, 1.0)
        i0 = int(t0 * SR); x[i0:i0 + len(g)] += g[:n - i0]
    return _taper(x, 0.6)


# ------------------------------------------------------------------ render
def W(name, x, meta, **kw):
    kw.setdefault('group', 'weather')
    kw.setdefault('max_dist', 400)
    return S.save(name, x, 'wx', meta=meta, **kw)


def render():
    S.set_manifest('weather')
    near_d = [5.5, 6.5, 7.5, 8.5]
    far_d = [6.0, 7.0, 8.0, 9.0]
    for i in range(4):
        W('wx_thunder_near_%02d' % (i + 1), thunder(2001 + i, True, near_d[i]),
          dict(kind='thunder', distClass='near', typicalDelayS=[0.4, 3.0], rumbleS=near_d[i], delayToRumbleRatio=0.25,
               hint='play after distance/343 s; duck amb 6 dB for 1.5 s; lowpass further with distance'),
          weight=10.0, max_dist=2500, rate=(0.92, 1.05), lazy=False, quality=4, variants=4)
    for i in range(4):
        W('wx_thunder_far_%02d' % (i + 1), thunder(2101 + i, False, far_d[i]),
          dict(kind='thunder', distClass='far', typicalDelayS=[5.0, 14.0], rumbleS=far_d[i], delayToRumbleRatio=1.4,
               hint='no crack, dark; play after distance/343 s; quieter, slower attack'),
          weight=9.0, max_dist=6000, rate=(0.92, 1.05), lazy=False, quality=4, variants=4)
    for i, d in enumerate([1.6, 2.0, 2.4]):
        W('wx_lightning_crack_%02d' % (i + 1), crack(2201 + i, d),
          dict(kind='lightning_crack', distClass='very_near', typicalDelayS=[0.0, 0.8], hint='play with the strike flash; follow with thunder_near after delay'),
          weight=10.0, max_dist=1500, rate=(0.95, 1.05), quality=4, variants=3)
    W('wx_tornado_loop', make_tornado(12.0, 2301), dict(kind='tornado', loop=True, hint='level by distance to vortex; lowpass with distance'),
      weight=9.0, max_dist=1200, lazy=True, loop=True, peak=-3.0, target_lufs=-22.0, quality=3, rate=(0.9, 1.1))
    W('wx_quake_rumble', quake(2401), dict(kind='quake', hint='play at quake start, global (non-spatial); can pitch 0.8-1.2 by magnitude'),
      weight=10.0, max_dist=5000, lazy=True, rate=(0.8, 1.2), quality=4)
    W('wx_tsunami_rumble', tsunami(2501), dict(kind='tsunami', hint='play as the wave approaches the shore; peak near arrival'),
      weight=10.0, max_dist=5000, lazy=True, rate=(0.85, 1.1), quality=4)
    W('wx_meteor_whistle', meteor_whistle(2601), dict(kind='meteor_whistle', hint='start ~3.2 s before impact; impact sound at the end'),
      weight=9.0, max_dist=3000, lazy=True, rate=(0.9, 1.1), quality=4)
    W('wx_meteor_impact', meteor_impact(2602), dict(kind='meteor_impact', hint='duck all but wx by 8 dB, 0.4 s release'),
      weight=12.0, max_dist=5000, lazy=True, rate=(0.9, 1.1), quality=4)
    W('wx_eruption_boom', eruption_boom(2701), dict(kind='eruption_boom', hint='on eruption start'),
      weight=12.0, max_dist=6000, lazy=True, rate=(0.9, 1.1), quality=4)
    W('wx_eruption_loop', make_eruption_loop(12.0, 2702), dict(kind='eruption', loop=True, hint='level by distance and eruption rate'),
      weight=9.0, max_dist=3000, lazy=True, loop=True, peak=-3.0, target_lufs=-22.0, quality=3, rate=(0.9, 1.1))
    W('wx_landslide', landslide(2801), dict(kind='landslide', hint='scale rate/level by mass'),
      weight=8.0, max_dist=1200, lazy=True, rate=(0.85, 1.15), quality=4)
    W('wx_hail', make_hail(10.0, 2901), dict(kind='hail', loop=True, intensity=0.7, hint='rain bed with this on top; stops in clear weather'),
      weight=8.0, max_dist=400, lazy=True, loop=True, peak=-3.0, target_lufs=-24.0, quality=3, rate=(0.95, 1.05))


if __name__ == '__main__':
    render()
