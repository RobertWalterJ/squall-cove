"""Ambience beds for Squall Cove: sea, surf, wind, rain, fire, lava, steam, birds, gulls, crickets, forest, harbour, underwater.

Loop construction: every bed is rendered as (a) a 'noise part' of length D+xfade that is equal-power crossfaded by make_loop (all its
modulators are exactly periodic with period D, so the head and the tail carry the same envelope but different noise) plus (b) a
'circular part' of length D whose events (grains, calls, tonal whistles) wrap around the loop point, so it is seamless by construction.
Left and right channels use different noise seeds; event placement is shared and panned.
"""
import math
import numpy as np
import synthlib as S
from synthlib import SR, rng, lp, hp, bp, noise, tv_filter, tv_bandpass, peak_eq

TWO_PI = 2 * math.pi


# ------------------------------------------------------------------ helpers
def pmod(n, D, r, kmin=1, kmax=6, slope=1.0):
    """Smooth random modulation in [0,1] that is exactly periodic with period D seconds."""
    t = np.arange(n) / SR
    y = np.zeros(n)
    for k in range(kmin, kmax + 1):
        y += r.uniform(0.5, 1.0) * k ** -slope * np.cos(TWO_PI * k * t / D + r.uniform(0, TWO_PI))
    return (y - y.min()) / (y.max() - y.min() + 1e-12)


def circ_add(buf, i0, g):
    n = len(buf)
    i0 = int(i0) % n
    m = min(len(g), n)
    e = min(n - i0, m)
    buf[i0:i0 + e] += g[:e]
    if e < m:
        buf[:m - e] += g[e:m]


def circ_dt(n, D, t0):
    """Time since t0 on a circular timeline of period D, for the sample grid of length n."""
    return (np.arange(n) / SR - t0) % D


def bed(mk, D, seed, xf=1.0):
    """Assemble a stereo seamless loop of D seconds. mk(r, n, D, ch, shared) -> (noise_part_len_n | None, circ_part_len_nD | None)."""
    k = int(xf * SR)
    nD = int(round(D * SR))
    n = nD + k
    chans = []
    for ch in range(2):
        r = rng(seed * 7 + ch * 101 + 3)
        shared = rng(seed * 7 + 55)
        a, c = mk(r, n, D, ch, shared)
        y = np.zeros(nD)
        if a is not None:
            y += S.make_loop(a, xf)[:nD]
        if c is not None:
            y += c[:nD]
        chans.append(y)
    return np.stack(chans, axis=1)


def pan_gains(p):
    """p in [-1,1] -> (gL, gR) constant power."""
    a = (p + 1) * math.pi / 4
    return math.cos(a), math.sin(a)


def scatter_rate(nD, D, rate_fn, rmax, pool, r, amp_fn=None, pan=None, ch=0, lognorm=0.5):
    """Inhomogeneous Poisson scatter of pool grains on a circular buffer. rate_fn(t_array_s)->events/s (vectorised)."""
    buf = np.zeros(nD)
    cnt = r.poisson(rmax * D)
    ts = r.random(cnt) * D
    keep = r.random(cnt) < (np.asarray(rate_fn(ts)) / rmax)
    for tsec in ts[keep]:
        g = pool[r.integers(len(pool))] * math.exp(r.normal(0, lognorm))
        if amp_fn is not None:
            g = g * amp_fn(tsec)
        if pan is not None:
            p = r.uniform(-pan, pan)
            g = g * pan_gains(p)[ch] * math.sqrt(2) / 1.0
        circ_add(buf, tsec * SR, g)
    return buf


def sweep(f_arr, harm=(1.0,), phase0=0.0):
    ph = TWO_PI * np.cumsum(f_arr) / SR + phase0
    y = np.zeros(len(f_arr))
    for h, a in enumerate(harm, start=1):
        y += a * np.sin(h * ph)
    return y


def hann_env(n):
    return np.hanning(n + 2)[1:-1]


def clip_pool(maker, count, seed):
    r = rng(seed)
    return [maker(r, i) for i in range(count)]


# grain makers --------------------------------------------------------------------
def g_click(r, i, lo=1200, hi=7000, dmin=0.002, dmax=0.012):
    k = int(r.uniform(dmin, dmax) * SR)
    x = r.standard_normal(k) * np.exp(-np.arange(k) / (k * 0.3))
    c = r.uniform(lo, hi)
    return bp(x, c * 0.7, min(c * 1.4, 12000), SR, 1) * r.uniform(0.4, 1.0)


def g_ping(r, i, lo=2000, hi=5000, dur=0.025):
    f = r.uniform(lo, hi)
    k = int(dur * SR * r.uniform(0.6, 1.4))
    t = np.arange(k) / SR
    return np.sin(TWO_PI * f * t) * np.exp(-t / (dur * 0.3)) * r.uniform(0.3, 1.0)


def g_plop(r, i, flo=300, fhi=2200, dlo=0.015, dhi=0.07):
    f0 = r.uniform(flo, fhi)
    d = r.uniform(dlo, dhi)
    k = int(d * SR)
    t = np.arange(k) / SR
    f = f0 * (1 + 1.6 * t / d)
    return np.sin(TWO_PI * np.cumsum(f) / SR) * np.exp(-t / (d * 0.35)) * np.minimum(1, t / 0.002) * r.uniform(0.3, 1.0)


def g_drip(r, i):
    f0 = r.uniform(500, 1500)
    d = r.uniform(0.04, 0.12)
    k = int(d * 2.5 * SR)
    t = np.arange(k) / SR
    f = f0 * (1 - 0.15 * (1 - np.exp(-t / 0.02)))
    y = np.sin(TWO_PI * np.cumsum(f) / SR) * np.exp(-t / d)
    y += 0.5 * np.sin(TWO_PI * np.cumsum(f * 2.3) / SR) * np.exp(-t / (d * 0.5))
    thud = lp(r.standard_normal(k), 900, SR, 1) * np.exp(-t / 0.01)
    y = y * np.minimum(1, t / 0.0015)
    return (y + 1.2 * thud) * r.uniform(0.5, 1.0)


# ------------------------------------------------------------------ sea
def make_sea(period, n_primary, n_secondary, level, crest, chop, rumble, bubbles, lo_cut, hi_cut, D, seed):
    def mk(r, n, D, ch, shared):
        t = np.arange(n) / SR
        # wave event times (shared across channels, jittered per channel)
        env = np.zeros(n)
        evs = []
        for cnt, amp, per in ((n_primary, 1.0, D / n_primary), (n_secondary, 0.45, D / n_secondary)):
            base = shared.random() * D
            for k in range(cnt):
                t0 = base + (k + shared.uniform(-0.22, 0.22)) * per + (r.uniform(-0.25, 0.25) if ch is not None else 0)
                a = amp * shared.uniform(0.7, 1.15)
                evs.append((t0, a, per))
        for t0, a, per in evs:
            dt = (t - t0) % D
            rise = 0.18 * per + 0.2
            tau = 0.3 * per + 0.3
            sh = np.sin(np.minimum(dt / rise, 1.0) * math.pi / 2) ** 2 * np.exp(-np.maximum(dt - rise * 0.6, 0) / tau)
            env += a * sh
        env = env / env.max()
        # body: pink noise with cutoff and amplitude following the swell
        x = noise(n, 'pink', r)
        cut = lo_cut + (hi_cut - lo_cut) * env ** 0.8
        body = tv_filter(x, cut, 'lp', 2, SR, 1024) * (0.22 + 0.78 * env)
        # underlying low rumble
        rum = lp(noise(n, 'brown', r), 110, SR, 2) * (0.5 + 0.5 * env) * rumble
        # crest hiss on the wave face
        hiss = hp(lp(noise(n, 'white', r), 9000, SR, 1), 2500, SR, 2) * (env ** 2.2) * crest
        out = body + rum * 1.5 + hiss
        if chop > 0:
            cm = pmod(n, D, r, 4, 24, 0.6)
            ch_n = tv_bandpass(noise(n, 'pink', r), 500 + 700 * cm, 1.6, 2, SR, 1024)
            out += chop * ch_n * (0.3 + 0.7 * cm ** 2) * (0.4 + 0.6 * env)
        # circular part: bubbles and slaps on wave faces
        nD = int(round(D * SR))
        circ = np.zeros(nD)
        if bubbles > 0:
            for t0, a, per in evs:
                for _ in range(int(bubbles * a * 30)):
                    g = g_plop(r, 0, 500, 3200, 0.01, 0.05) * r.uniform(0.2, 1.0) * a * 0.5
                    circ_add(circ, (t0 + r.uniform(0.0, 0.7 * per)) * SR, g)
        return out, circ * level * 0.25
    return bed(lambda r, n, D, ch, sh: _lv(mk(r, n, D, ch, sh), level), D, seed)


def _lv(pair, level):
    a, c = pair
    return a * level, c


# ------------------------------------------------------------------ surf
def make_surf(events, heavy, D, seed):
    """events: list of (t0, size 0..1). Each = burst, roll, backwash."""
    def mk(r, n, D, ch, shared):
        t = np.arange(n) / SR
        env_roll = np.zeros(n); env_back = np.zeros(n); env_thump = np.zeros(n)
        evs = [(t0 + r.uniform(-0.3, 0.3), s) for t0, s in events]
        for t0, s in evs:
            dt = (t - t0) % D
            att = 0.18 + 0.2 * s
            tau = 0.9 + 1.5 * s * (1.4 if heavy else 1.0)
            env_roll += s * np.sin(np.minimum(dt / att, 1) * math.pi / 2) ** 2 * np.exp(-np.maximum(dt - att, 0) / tau)
            db = dt - (0.7 + 0.6 * s)
            env_back += s * 0.45 * np.where(db > 0, np.sin(np.minimum(db / 0.9, 1) * math.pi / 2) ** 2 * np.exp(-np.maximum(db - 0.9, 0) / (1.6 + s)), 0)
            env_thump += s * np.exp(-dt / 0.35) * np.minimum(1, dt / 0.02)
        pk = max(env_roll.max(), 1e-9)
        env_roll /= pk; env_back /= pk; env_thump /= pk
        x = noise(n, 'pink', r)
        top = 3800 if heavy else 6500
        cut = 400 + (top - 400) * env_roll ** 0.7
        roll = tv_filter(x, cut, 'lp', 2, SR, 1024) * env_roll
        back = bp(noise(n, 'white', r), 700, 3200 if heavy else 5000, SR, 2) * env_back * 0.8
        rum = lp(noise(n, 'brown', r), 130 if heavy else 200, SR, 2) * (env_thump * 1.4 + env_roll * 0.6) * (2.0 if heavy else 0.8)
        floor = lp(noise(n, 'pink', r), 900, SR, 2) * 0.06
        spit = hp(noise(n, 'white', r), 4000, SR, 2) * env_roll ** 2.5 * (0.25 if heavy else 0.4)
        out = roll + back + rum + floor + spit
        nD = int(round(D * SR))
        circ = np.zeros(nD)
        for t0, s in evs:   # foam bubbles trailing the roll
            for _ in range(int(25 * s) + 4):
                g = g_plop(r, 0, 600, 3500, 0.008, 0.04) * r.uniform(0.1, 0.5) * s
                circ_add(circ, (t0 + 0.2 + r.exponential(0.9 + s)) * SR, g)
        return out, circ * 0.3
    return bed(mk, D, seed)


# ------------------------------------------------------------------ wind
def make_wind(lo, hi, c0, roar, flutter_hz, flutter_depth, floor_amp, D, seed, howl=0.0, whistle=None, base_pink=1.0):
    def mk(r, n, D, ch, shared):
        g = pmod(n, D, r, 1, 7, 0.9)              # gust envelope (periodic)
        g2 = pmod(n, D, r, 6, 30, 0.8)            # fast turbulence
        gg = np.clip(0.8 * g + 0.2 * g2, 0, 1)
        cut = lo + (hi - lo) * (0.15 + 0.85 * gg)
        a = tv_filter(noise(n, 'pink', r), cut, 'lp', 2, SR, 1024) * base_pink
        b = tv_bandpass(noise(n, 'white', r), c0 * (0.65 + 0.9 * gg), 1.3, 2, SR, 1024) * 0.9
        body = (a + b * 1.4) * (floor_amp + (1 - floor_amp) * gg ** 1.2)
        if roar > 0:
            ro = lp(noise(n, 'brown', r), 170, SR, 2) * (0.3 + 0.7 * gg ** 1.5) * roar
            body = body + ro * 2.0
        if flutter_depth > 0:
            fl = lp(noise(n, 'white', r), flutter_hz, SR, 2)
            fl = fl / (np.std(fl) + 1e-9)
            body = body * np.clip(1 + flutter_depth * fl * (0.4 + 0.6 * gg), 0.1, 3)
        nD = int(round(D * SR))
        circ = np.zeros(nD)
        if howl > 0 or whistle:
            gD = g[:nD]
            gloc = np.clip(gD, 0, 1)
            fw = [(whistle or 0)] if whistle else []
            if howl > 0:
                fw += [150.0]
            for idx, f0 in enumerate(fw):
                if f0 <= 0:
                    continue
                lowhowl = f0 < 300
                dev = r.uniform(0.9, 1.1)
                if lowhowl:
                    f_t = f0 * dev * (0.8 + 0.5 * gloc) * (1 + 0.02 * np.sin(TWO_PI * 5.5 * np.arange(nD) / SR))
                    amp = howl * gloc ** 1.5
                    harm = (1.0, 0.6, 0.35, 0.2)
                else:
                    f_t = f0 * dev * (0.8 + 0.6 * gloc) * (1 + 0.01 * np.sin(TWO_PI * 7.0 * np.arange(nD) / SR + idx))
                    amp = np.clip((gloc - 0.25) / 0.75, 0, 1) ** 1.6
                    harm = (1.0, 0.45, 0.2)
                ph = TWO_PI * np.cumsum(f_t) / SR
                # force an integer number of cycles over the loop so the tone is periodic
                ph = ph - (ph[-1] + TWO_PI * f_t[-1] / SR - TWO_PI * round((ph[-1] + TWO_PI * f_t[-1] / SR) / TWO_PI)) * np.arange(nD) / nD
                y = np.zeros(nD)
                for h, ah in enumerate(harm, start=1):
                    y += ah * np.sin(h * ph + r.uniform(0, TWO_PI) * 0)
                circ += y * amp * (0.35 if not lowhowl else 1.0)
        return body, circ
    return bed(mk, D, seed)


# ------------------------------------------------------------------ rain
def make_rain(rate, bed_gain, bed_lp, bed_hp, body_gain, drop_lo, drop_hi, D, seed, plop_rate=0, plop_gain=0.0, drip_rate=0.0, drip_gain=0.0,
              fine_lp=None, drop_gain=1.0):
    pool = clip_pool(lambda r, i: g_click(r, i, drop_lo, drop_hi, 0.002, 0.01) if i % 4 else g_ping(r, i, drop_lo, drop_hi, 0.015), 96, seed + 1)
    ploppool = clip_pool(lambda r, i: g_plop(r, i, 300, 2400, 0.012, 0.06), 48, seed + 2) if plop_rate else None
    drippool = clip_pool(g_drip, 32, seed + 3) if drip_rate else None

    def mk(r, n, D, ch, shared):
        nD = int(round(D * SR))
        x = noise(n, 'pink', r)
        x = hp(lp(x, bed_lp, SR, 2), bed_hp, SR, 2) * bed_gain
        mod = pmod(n, D, r, 2, 9, 0.8)
        x = x * (0.85 + 0.3 * mod)
        if body_gain:
            x += bp(noise(n, 'pink', r), 250, 1400, SR, 2) * body_gain
        rr = rng(seed * 31 + ch * 9)
        dens = lambda ts: rate * (0.85 + 0.3 * np.interp(ts, np.linspace(0, D, 64), pmod(64, D * 64 / 63, rr, 1, 5)))
        c = scatter_rate(nD, D, dens, rate * 1.2, pool, rr, lognorm=0.6) * drop_gain
        if fine_lp:
            c = lp(c, fine_lp, SR, 2)
        if plop_rate:
            c += scatter_rate(nD, D, lambda ts: plop_rate + 0 * ts, plop_rate, ploppool, rr, lognorm=0.5) * plop_gain
        if drip_rate:
            c += scatter_rate(nD, D, lambda ts: drip_rate + 0 * ts, drip_rate, drippool, rr, lognorm=0.5) * drip_gain
        return x, c
    return bed(mk, D, seed)


# ------------------------------------------------------------------ fire / lava / steam / snow
def make_fire(D, seed):
    pops = clip_pool(lambda r, i: g_click(r, i, 900, 6000, 0.001, 0.02) if i % 3 else hp(g_plop(r, i, 150, 500, 0.03, 0.09), 80, SR, 1) * 1.5, 120, seed + 1)

    def mk(r, n, D, ch, shared):
        nD = int(round(D * SR))
        fl = pmod(n, D, r, 2, 18, 0.7)
        roar = lp(noise(n, 'brown', r), 350, SR, 2) * (0.5 + 0.5 * fl) * 3.0
        mid = tv_bandpass(noise(n, 'pink', r), 500 + 900 * fl, 1.6, 2, SR, 1024) * 0.25 * (0.4 + 0.6 * fl)
        hiss = hp(lp(noise(n, 'white', r), 7000, SR, 2), 1800, SR, 2) * 0.08 * (0.5 + 0.5 * pmod(n, D, r, 3, 20, 0.7))
        rr = rng(seed * 13 + ch)
        cl = pmod(256, D * 256 / 255, rr, 1, 7, 0.6)
        rate = lambda ts: 10 + 45 * np.interp(ts, np.linspace(0, D, 256), cl) ** 2
        c = scatter_rate(nD, D, rate, 60, pops, rr, lognorm=0.7)
        return roar + mid + hiss, c * 2.5
    return bed(mk, D, seed)


def make_lava(D, seed):
    def bub(r, i):
        f0 = r.uniform(60, 220); d = r.uniform(0.12, 0.35); k = int(d * SR); t = np.arange(k) / SR
        f = f0 * (1 + 0.8 * t / d)
        y = np.sin(TWO_PI * np.cumsum(f) / SR) * np.exp(-t / (d * 0.45)) * np.minimum(1, t / 0.015)
        y += 0.4 * np.sin(TWO_PI * np.cumsum(f * 2.01) / SR) * np.exp(-t / (d * 0.25))
        k2 = int(0.02 * SR); pop = hp(r.standard_normal(k2), 600, SR, 1) * np.exp(-np.arange(k2) / (k2 * 0.25)) * 0.12
        y[:k2] += pop
        return y * r.uniform(0.4, 1.0)
    pool = clip_pool(bub, 60, seed + 1)

    def mk(r, n, D, ch, shared):
        nD = int(round(D * SR))
        m = pmod(n, D, r, 1, 6, 0.8)
        rum = lp(noise(n, 'brown', r), 160, SR, 2) * (0.6 + 0.4 * m) * 2.0
        sizz = hp(lp(noise(n, 'white', r), 9000, SR, 2), 3000, SR, 2) * 0.05 * (0.5 + 0.5 * pmod(n, D, r, 4, 24, 0.6))
        rr = rng(seed * 17 + ch)
        c = scatter_rate(nD, D, lambda ts: 2.4 + 0 * ts, 3.0, pool, rr, lognorm=0.5, pan=0.8, ch=ch)
        return rum + sizz, c * 1.4
    return bed(mk, D, seed)


def make_steam(D, seed):
    def mk(r, n, D, ch, shared):
        m = pmod(n, D, r, 2, 14, 0.7)
        w = noise(n, 'white', r)
        x = tv_filter(w, 5500 + 2500 * m, 'lp', 2, SR, 1024)
        x = hp(x, 1400, SR, 2)
        x += tv_bandpass(noise(n, 'white', r), 2500 + 2500 * pmod(n, D, r, 1, 4, 0.8), 1.5, 2, SR, 1024) * 0.7
        x *= 0.8 + 0.35 * m
        return x, None
    return bed(mk, D, seed)


def make_snow(D, seed):
    ticks = clip_pool(lambda r, i: g_ping(r, i, 4200, 6200, 0.004), 24, seed + 1)
    flump = clip_pool(lambda r, i: lp(r.standard_normal(int(0.4 * SR)), 280, SR, 2) * np.exp(-np.arange(int(0.4 * SR)) / (0.08 * SR)) * 4, 8, seed + 2)

    def mk(r, n, D, ch, shared):
        nD = int(round(D * SR))
        m = pmod(n, D, r, 1, 4, 0.8)
        x = lp(noise(n, 'pink', r), 1500, SR, 2) * (0.5 + 0.5 * m)
        x += bp(noise(n, 'white', r), 3500, 6500, SR, 2) * 0.03 * (0.3 + 0.7 * m)
        rr = rng(seed * 5 + ch)
        c = scatter_rate(nD, D, lambda ts: 4 + 0 * ts, 5, ticks, rr, lognorm=0.6, pan=1, ch=ch) * 0.015
        c += scatter_rate(nD, D, lambda ts: 0.15 + 0 * ts, 0.3, flump, rr, lognorm=0.3, pan=1, ch=ch) * 0.4
        return x, c
    return bed(mk, D, seed)


def make_forest(D, seed):
    def mk(r, n, D, ch, shared):
        nD = int(round(D * SR))
        g = pmod(n, D, r, 1, 6, 0.9)
        base = tv_bandpass(noise(n, 'pink', r), 450 + 700 * g, 1.8, 2, SR, 1024) * (0.5 + 0.5 * g)
        leaf = hp(lp(noise(n, 'white', r), 6000, SR, 2), 1800, SR, 2)
        rm = lp(noise(n, 'white', r), 9, SR, 2); rm = np.clip(rm / (np.std(rm) + 1e-9) * 0.6 + 0.4, 0, None) ** 2
        leaf = leaf * rm * (0.15 + 0.5 * g) * 0.35
        drone = lp(noise(n, 'brown', r), 120, SR, 2) * 0.8 * (0.5 + 0.5 * g)
        rr = rng(seed * 3 + ch)
        pool = [g_click(rr, i, 1500, 4500, 0.003, 0.012) for i in range(24)]
        c = scatter_rate(nD, D, lambda ts: 6 + 0 * ts, 8, pool, rr, pan=1, ch=ch) * 0.06
        return base + leaf + drone, c
    return bed(mk, D, seed)


def make_underwater(D, seed):
    def mk(r, n, D, ch, shared):
        nD = int(round(D * SR))
        m = pmod(n, D, r, 1, 4, 0.8)
        x = tv_filter(noise(n, 'brown', r), 250 + 350 * m, 'lp', 2, SR, 1024) * 2.0
        x += lp(noise(n, 'pink', r), 600, SR, 2) * 0.5 * (0.4 + 0.6 * pmod(n, D, r, 2, 7, 0.8))
        x += 0.3 * np.sin(TWO_PI * 58 * np.arange(n) / SR + r.uniform(0, 6) ) * (0.4 + 0.6 * m) * 0  # no tonal hum (avoid loop phase issue)
        rr = rng(seed * 11 + ch)
        pool = [lp(g_plop(rr, i, 250, 1100, 0.02, 0.09), 700, SR, 2) for i in range(40)]
        c = scatter_rate(nD, D, lambda ts: 1.6 + 0 * ts, 2.2, pool, rr, lognorm=0.5, pan=0.9, ch=ch) * 0.35
        return x, c
    return bed(mk, D, seed)


# ------------------------------------------------------------------ biological
def bird_note(r, f0, f1, dur, harm=(1.0, 0.2, 0.05), curve=1.0):
    n = int(dur * SR)
    u = np.arange(n) / n
    f = f0 + (f1 - f0) * u ** curve
    y = sweep(f, harm, r.uniform(0, 6))
    e = np.sin(np.pi * u) ** 0.7
    return y * e


def bird_phrase(r, kind):
    parts = []
    if kind == 'tweet':
        f = r.uniform(3200, 4100); k = r.integers(3, 7)
        for i in range(k):
            parts.append(bird_note(r, f * 0.92, f * r.uniform(1.05, 1.15), r.uniform(0.045, 0.08)))
            parts.append(np.zeros(int(r.uniform(0.04, 0.09) * SR)))
    elif kind == 'whistle':
        f = r.uniform(1800, 2600)
        parts.append(bird_note(r, f, f * 1.25, r.uniform(0.28, 0.4), (1.0, 0.1)))
        parts.append(np.zeros(int(0.07 * SR)))
        parts.append(bird_note(r, f * 1.25, f * 0.78, r.uniform(0.35, 0.55), (1.0, 0.1)))
    elif kind == 'warble':
        d = r.uniform(0.6, 1.1); n = int(d * SR); t = np.arange(n) / SR
        fc = r.uniform(2600, 3400)
        f = fc + 450 * np.sin(TWO_PI * r.uniform(14, 24) * t) + 350 * np.sin(TWO_PI * 3.1 * t)
        parts.append(sweep(f, (1.0, 0.15)) * np.sin(np.pi * t / d) ** 0.6)
    elif kind == 'trill':
        f = r.uniform(2400, 3200); k = r.integers(8, 16)
        for i in range(k):
            parts.append(bird_note(r, f * (1 + 0.02 * i), f * (1.12 + 0.02 * i), 0.035))
            parts.append(np.zeros(int(0.045 * SR)))
    else:  # cheep
        f = r.uniform(3600, 4300)
        parts.append(bird_note(r, f * 1.15, f * 0.8, r.uniform(0.07, 0.13)))
    y = np.concatenate(parts)
    return lp(y, 5200, SR, 2) * 0.5


def make_birds(D, seed):
    def mk(r, n, D, ch, shared):
        nD = int(round(D * SR))
        circ = np.zeros(nD)
        kinds = ['tweet', 'whistle', 'warble', 'trill', 'cheep']
        for j in range(24):
            kind = kinds[shared.integers(len(kinds))]
            t0 = shared.random() * D
            y = bird_phrase(shared, kind)
            far = shared.random() < 0.45
            g = shared.uniform(0.25, 0.7)
            if far:
                y = lp(y, 3200, SR, 2); g *= 0.45
            p = shared.uniform(-0.9, 0.9)
            # repeat a phrase once or twice, like real song bouts
            reps = int(shared.integers(1, 4)) if kind in ('tweet', 'whistle', 'cheep') else 1
            tt = t0
            for k in range(reps):
                circ_add(circ, tt * SR, y * g * pan_gains(p)[ch] * math.sqrt(2) * (1 - 0.1 * k))
                tt += len(y) / SR + shared.uniform(0.3, 0.9)
        # distant ambience: leaves
        x = bp(noise(n, 'pink', r), 300, 2000, SR, 2) * 0.012 * (0.5 + 0.5 * pmod(n, D, r, 1, 4, 0.8))
        return x, circ
    return bed(mk, D, seed)


def gull_call(r, f0, dur, hoarse=0.1):
    n = int(dur * SR); t = np.arange(n) / SR; u = t / dur
    f = f0 * np.interp(u, [0, 0.12, 1.0], [0.82, 1.12, 0.5]) * (1 + 0.03 * np.sin(TWO_PI * 26 * t))
    y = sweep(f, tuple(1.0 / h ** 1.0 for h in range(1, 8)), r.uniform(0, 6))
    y += hoarse * hp(noise(n, 'white', r), 900, SR, 1) * 0.6
    e = np.minimum(1, t / 0.02) * np.maximum(0, np.sin(np.pi * u ** 0.8)) ** 0.6
    e *= 1 + 0.35 * np.sin(TWO_PI * 22 * t + r.uniform(0, 6)) * u
    y = peak_eq(y, 1500, 2.0, 9.0); y = peak_eq(y, 2800, 3.0, 5.0)
    return lp(y * e, 5200, SR, 2) * 0.5


def make_gulls(D, seed):
    def mk(r, n, D, ch, shared):
        nD = int(round(D * SR)); circ = np.zeros(nD)
        for s in range(7):
            t0 = shared.random() * D; far = shared.random() < 0.5
            g = shared.uniform(0.4, 1.0) * (0.4 if far else 1.0)
            p = shared.uniform(-0.9, 0.9)
            f0 = shared.uniform(1350, 2000)
            k = int(shared.integers(1, 5)); tt = t0
            style = shared.random()
            for i in range(k):
                d = shared.uniform(0.28, 0.5) if style < 0.65 else shared.uniform(0.12, 0.2)
                y = gull_call(shared, f0 * shared.uniform(0.93, 1.07) * (1.1 if style >= 0.65 else 1.0), d)
                if far:
                    y = lp(y, 2800, SR, 2)
                circ_add(circ, tt * SR, y * g * pan_gains(p)[ch] * math.sqrt(2) * (1 - 0.08 * i))
                tt += d + shared.uniform(0.1, 0.32)
        wash = tv_filter(noise(n, 'pink', r), 300 + 500 * pmod(n, D, r, 1, 3, 0.8), 'lp', 2, SR, 1024) * 0.06
        return wash, circ
    return bed(mk, D, seed)


def make_crickets(D, seed):
    def mk(r, n, D, ch, shared):
        nD = int(round(D * SR)); circ = np.zeros(nD)
        slow = pmod(nD, D, shared, 1, 3, 0.8)
        cfg = [(4300, 27), (4650, 31), (4050, 34), (4450, 38), (3900, 43), (4800, 29)]
        for ci, (fc, m) in enumerate(cfg):
            P = D / m; pulses = int(shared.integers(3, 5)); gap = 0.021 + 0.004 * shared.random()
            p = shared.uniform(-0.9, 0.9); g = shared.uniform(0.4, 0.9)
            ph0 = shared.random() * P
            for k in range(m):
                t0 = ph0 + k * P + shared.uniform(-0.04, 0.04) * P
                if shared.random() < 0.08:
                    continue                 # an occasional skipped chirp
                a = g * (0.6 + 0.4 * slow[int((t0 % D) * SR) % nD])
                for q in range(pulses):
                    dur = 0.011; nn = int(dur * SR); tp = np.arange(nn) / SR
                    f = fc * (1 + 0.012 * q)
                    pulse = np.sin(TWO_PI * f * tp + shared.uniform(0, 6)) * hann_env(nn)
                    circ_add(circ, (t0 + q * gap) * SR, pulse * a * (0.8 + 0.1 * q) * pan_gains(p)[ch] * math.sqrt(2))
        circ = lp(circ, 5200, SR, 2) * 0.5
        x = lp(noise(n, 'pink', r), 900, SR, 2) * 0.03 * (0.5 + 0.5 * pmod(n, D, r, 1, 3, 0.8))
        x += bp(noise(n, 'white', r), 1500, 4500, SR, 2) * 0.004
        return x, circ
    return bed(mk, D, seed)


def make_harbour(D, seed):
    def mk(r, n, D, ch, shared):
        nD = int(round(D * SR)); circ = np.zeros(nD)
        # bell buoy: bell strikes follow the wave rhythm, at irregular intervals
        bell_t = [1.7, 7.9, 9.6, 15.2]
        for i, t0 in enumerate(bell_t):
            y = S.modal(float(shared.uniform(610, 660)), 'bell', 5.5, 0.9, 0.7, 0.003, shared)
            y = lp(y, 2600, SR, 2)
            circ_add(circ, t0 * SR, y * (0.9 if i != 2 else 0.5) * pan_gains(0.5)[ch] * math.sqrt(2) * 0.08)
        # creaks: lopsided saw through a swept resonator
        for t0 in (3.4, 11.8, 17.6, 4.9):
            d = float(shared.uniform(0.5, 1.2)); nn = int(d * SR); t = np.arange(nn) / SR
            f = 38 + 14 * np.sin(TWO_PI * shared.uniform(2, 5) * t)
            saw = ((np.cumsum(f) / SR) % 1.0) * 2 - 1
            sw = float(shared.uniform(300, 600))
            y = S.tv_bandpass(saw + 0.3 * shared.standard_normal(nn), sw + 250 * (t / d), 0.6, 2, SR, 512) * np.sin(np.pi * t / d) ** 1.2
            circ_add(circ, t0 * SR, lp(y, 1800, SR, 2) * 0.35 * pan_gains(shared.uniform(-0.8, 0.8))[ch] * math.sqrt(2))
        # murmur: syllable bursts through two formants
        for _ in range(60):
            t0 = shared.random() * D; d = float(shared.uniform(0.1, 0.28)); nn = int(d * SR)
            src = hp(shared.standard_normal(nn), 100, SR, 1)
            f1 = shared.uniform(350, 800); f2 = shared.uniform(1000, 2100)
            y = S.resonator(src, f1, 6) + 0.6 * S.resonator(src, f2, 8)
            y *= np.sin(np.pi * np.arange(nn) / nn) ** 1.5
            circ_add(circ, t0 * SR, lp(y, 2800, SR, 2) * 0.012 * pan_gains(0.3 * math.sin(t0))[ch] * math.sqrt(2) * float(shared.uniform(0.3, 1)))
        m = pmod(n, D, r, 1, 4, 0.8)
        x = tv_filter(noise(n, 'pink', r), 300 + 450 * m, 'lp', 2, SR, 1024) * 0.2 * (0.4 + 0.6 * m)
        x += lp(noise(n, 'brown', r), 90, SR, 2) * 0.35
        return x, circ
    return bed(mk, D, seed)


# ------------------------------------------------------------------ render
def A(name, x, D_meta, lufs=-26.0, **kw):
    kw.setdefault('group', 'core')
    return S.save(name, x, 'amb', loop=True, target_lufs=lufs, max_dist=kw.pop('max_dist', 160), weight=kw.pop('weight', 1.0), meta=D_meta, **kw)


def render():
    S.set_manifest('ambience')
    # --- sea
    A('amb_sea_calm', make_sea(7.0, 2, 3, 1.0, 0.25, 0.0, 0.8, 0.2, 180, 1400, 14.0, 101),
      dict(kind='sea', swellPeriodS=7.0, swellWavelengthM=76, dutyHint='level up with sea.amp'), tags=['sea'], quality=3)
    A('amb_sea_moderate', make_sea(5.0, 2, 3, 1.0, 0.55, 0.12, 0.9, 0.5, 220, 2200, 10.0, 102),
      dict(kind='sea', swellPeriodS=5.0, swellWavelengthM=39, dutyHint='crossfade between calm and rough by sea.amp'), tags=['sea'], quality=3)
    A('amb_sea_rough', make_sea(4.0, 3, 5, 1.0, 1.0, 0.45, 1.2, 1.0, 300, 3200, 12.0, 103),
      dict(kind='sea', swellPeriodS=4.0, swellWavelengthM=25, chop=True), tags=['sea'], quality=3)
    # --- surf
    A('amb_surf_gentle', make_surf([(1.0, 0.45), (5.4, 0.35), (9.6, 0.55)], False, 14.0, 111),
      dict(kind='surf', wavePeriodS=4.5, nearShoreOnly=True, heavy=False), tags=['surf'], quality=3)
    A('amb_surf_heavy', make_surf([(1.2, 1.0), (7.4, 0.8), (10.8, 0.5)], True, 14.0, 112),
      dict(kind='surf', wavePeriodS=6.5, nearShoreOnly=True, heavy=True), tags=['surf'], quality=3)
    # --- wind (windMs = the speed the loop represents)
    A('amb_wind_light', make_wind(250, 800, 300, 0.0, 0, 0, 0.45, 12.0, 121), dict(kind='wind', windMs=3.0, band='200-800 Hz'), quality=3)
    A('amb_wind_fresh', make_wind(450, 1700, 550, 0.0, 0, 0, 0.4, 12.0, 122), dict(kind='wind', windMs=9.0), quality=3)
    A('amb_wind_gale', make_wind(800, 2800, 850, 0.7, 14, 0.35, 0.35, 12.0, 123, howl=0.04), dict(kind='wind', windMs=20.0, flutter=True), quality=3)
    A('amb_wind_hurricane', make_wind(1100, 3800, 1100, 1.4, 24, 0.5, 0.35, 12.0, 124, howl=0.09), dict(kind='wind', windMs=35.0, flutter=True), quality=3)
    A('amb_wind_rigging', make_wind(350, 1100, 450, 0.0, 0, 0, 0.35, 12.0, 125, whistle=820.0, base_pink=0.7),
      dict(kind='wind', windMs=12.0, tonalWhistleHz='650-1300', useNear='rigging, cliffs, wires'), quality=3, group='core')
    # --- rain
    A('amb_rain_light', make_rain(160, 0.5, 6500, 700, 0.0, 2000, 7000, 12.0, 131, drop_gain=3.0), dict(kind='rain', intensity=0.3, surface='land'), quality=3)
    A('amb_rain_heavy', make_rain(650, 1.0, 8000, 400, 0.5, 1500, 8000, 12.0, 132, drop_gain=1.6), dict(kind='rain', intensity=0.9, surface='land'), quality=3)
    A('amb_rain_on_water', make_rain(260, 0.55, 5200, 250, 0.2, 1200, 5000, 12.0, 133, plop_rate=230, plop_gain=1.3, fine_lp=6000, drop_gain=1.5),
      dict(kind='rain', intensity=0.6, surface='water'), quality=3)
    A('amb_rain_on_canopy', make_rain(180, 0.7, 3200, 300, 0.4, 1200, 3800, 12.0, 134, drip_rate=9, drip_gain=3.2, fine_lp=4200, drop_gain=1.8),
      dict(kind='rain', intensity=0.55, surface='canopy', muffled=True), quality=3)
    A('amb_snow_hush', make_snow(12.0, 141), dict(kind='snow', note='play with snowfall or snow cover; very quiet'), quality=3)
    # --- fire, lava, steam
    A('amb_fire_bed', make_fire(12.0, 151), dict(kind='fire', note='scale level and rate with burning count; rate 0.9-1.1'), quality=3)
    A('amb_lava_bubble', make_lava(12.0, 152), dict(kind='lava', note='level from lava cells near camera'), quality=3)
    A('amb_steam_hiss', make_steam(10.0, 153), dict(kind='steam', note='lava meeting water, geysers'), quality=3)
    # --- life
    A('amb_birds_day', make_birds(22.0, 161), dict(kind='birds', note='day, fair weather only; fade out by wind > 8 m/s and any rain'), group='core', lazy=True, quality=3)
    A('amb_gulls', make_gulls(20.0, 162), dict(kind='gulls', note='near the shore, day'), group='core', lazy=True, quality=3)
    A('amb_crickets_night', make_crickets(16.0, 163), dict(kind='crickets', note='night, calm, dry, land side'), group='core', lazy=True, quality=3)
    A('amb_forest_air', make_forest(12.0, 164), dict(kind='forest', note='under trees, any weather; rate 0.9-1.1'), quality=3, lazy=True)
    A('amb_harbour_far', make_harbour(20.0, 165), dict(kind='harbour', note='scale by pier/boat/people counts'), group='core', lazy=True, quality=3)
    A('amb_underwater', make_underwater(12.0, 166), dict(kind='underwater', note='replaces everything when camera below water'), quality=3)


if __name__ == '__main__':
    render()
