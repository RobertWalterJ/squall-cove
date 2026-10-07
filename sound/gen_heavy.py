"""Heavy-weapon and explosion pack: deep (35-90 Hz sub body with a fast pitch drop), mid crack, decaying room/distance tail.
Mono 44.1 kHz Ogg Vorbis like the rest of the weapons pack. Deterministic (seeded from stem name).

    python gen_heavy.py            # render into out/ and merge into ../audio (+ ../audio/manifest.json), touching only the new stems
    python gen_heavy.py --no-deploy

Levels: every one-shot is gain-staged here (not by synthlib's peak normaliser) so that the LOUDEST 400 ms RMS is the same inside each
class (see CLASS_RMS), with a soft limiter holding the peak at CEIL_DB. See NOTES-heavy.md.
"""
import math, os, sys, json, shutil
import numpy as np
from scipy import signal
import synthlib as S
import gen_util as U
from wpn_common import *

TWO_PI = 2 * math.pi
CEIL_DB = -2.2                      # pre-encode peak ceiling; Vorbis overshoot stays below -1 dBFS
CLASS_RMS = dict(fire=-19.0, boom=-17.0, far=-23.0, sub=-19.0, loop=-21.0, whistle=-23.0, foley=-25.0)


# ------------------------------------------------------------------ building blocks
def tt(n): return np.arange(n) / SR


def unit(x):
    x = np.asarray(x, dtype=np.float64); s = np.std(x)
    return x / s if s > 1e-12 else x


def sub(dur, f0, f1, td, tau, att=0.003, harm=0.0):
    """Sine with an exponential pitch drop f0 -> f1 (time constant td) and exponential decay tau."""
    n = n_of(dur); t = tt(n); f = f1 + (f0 - f1) * np.exp(-t / td); ph = TWO_PI * np.cumsum(f) / SR
    y = np.sin(ph) + harm * np.sin(2 * ph + 0.6)
    return y * np.minimum(1, t / att) * np.exp(-t / tau)


def crack(r, dur, lo, hi, tau, level=1.0):
    n = n_of(dur); t = tt(n)
    return unit(bp(noise(n, 'white', r), lo, hi, SR, 2)) * np.exp(-t / tau) * np.minimum(1, t / 0.0006) * level


def body(r, dur, fc, tau, level=1.0, lo=50):
    n = n_of(dur); t = tt(n)
    return unit(bp(noise(n, 'white', r), lo, fc, SR, 2)) * np.exp(-t / tau) * np.minimum(1, t / 0.002) * level


def tail(r, dur, tau_lo, tau_hi, fc0, fc1, lo_level=1.0, hi_level=0.6, swell=0.015):
    """Room/distance tail: a long low rumble band plus a mid band whose low-pass closes with time."""
    n = n_of(dur); t = tt(n)
    low = unit(bp(noise(n, 'white', r), 35, 170, SR, 2)) * np.exp(-t / tau_lo)
    fc = fc1 + (fc0 - fc1) * np.exp(-t / (dur / 3.0))
    mid = unit(S.tv_filter(hp(noise(n, 'white', r), 90, SR, 1), fc, 'lp', 2, SR, 512)) * np.exp(-t / tau_hi)
    return (low * lo_level + mid * hi_level) * (1 - np.exp(-t / swell))


def echoes(x, taps):
    """Add dark reflections: taps = [(delay_s, gain, lowpass_hz)]."""
    out = x.copy()
    for d, g, fc in taps:
        y = lp(x, fc, SR, 2) * g; s = n_of(d)
        if s < len(out): out[s:] += y[:len(out) - s]
    return out


def reverb(x, rt, wet, fc, r, pre=0.0):
    """Dark synthetic-IR reverb (decaying low-passed noise); returns dry*(1-wet)+wet*convolved at the original length plus rt of tail."""
    n = n_of(rt); t = tt(n); ir = lp(noise(n, 'white', r), fc, SR, 2) * np.exp(-t / (rt / 6.9)) * np.minimum(1, t / 0.02)
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    w = signal.fftconvolve(x, ir)
    d = np.zeros(len(w)); d[:len(x)] = x
    return d * (1 - wet) + w * wet * 2.2


def debris(r, dur, t0, rate0, tau, lo=900, hi=7000, thud=0.5, level=1.0):
    """Patter of falling debris: inhomogeneous Poisson ticks (thinning) with rate0*exp(-(t-t0)/tau)."""
    n = n_of(dur); out = np.zeros(n); t = t0
    while t < dur - 0.05:
        t += r.exponential(1.0 / max(rate0, 1.0))
        if t >= dur - 0.05: break
        if r.random() > math.exp(-(t - t0) / tau): continue
        g = r.uniform(0.15, 1.0) * level
        if r.random() < thud:
            g2 = g * r.uniform(0.6, 1.4)
            x = thump(n_of(0.07), r.uniform(120, 420), r.uniform(0.012, 0.035), g2, 0.2)
        else:
            x = tickn(r, r.uniform(0.002, 0.009), r.uniform(lo, lo * 2), r.uniform(hi * 0.5, hi), g)
        put(out, x, t, 1.0)
    return out


def circ_noise(n, lo, hi, r, slope=0.0):
    """Perfectly periodic band-limited noise (random phase in the FFT domain), unit RMS."""
    f = np.fft.rfftfreq(n, 1.0 / SR); mag = ((f >= lo) & (f <= hi)).astype(float)
    mag *= 1.0 / np.maximum(f, 1.0) ** slope
    sp = mag * np.exp(1j * r.uniform(0, TWO_PI, len(f)))
    return unit(np.fft.irfft(sp, n))


def put_circ(buf, x, pos, g=1.0):
    n = len(buf); idx = (int(pos) + np.arange(len(x))) % n
    np.add.at(buf, idx, x * g)


def wrms_db(x, win=0.4):
    """Loudest windowed RMS in dBFS (win seconds, hop win/8)."""
    w = max(8, int(win * SR)); c = np.concatenate([[0.0], np.cumsum(np.square(x))])
    if len(x) <= w: return 10 * math.log10(max(c[-1] / max(len(x), 1), 1e-18))
    hop = max(1, w // 8); starts = np.arange(0, len(x) - w + 1, hop)
    return 10 * math.log10(max(np.max((c[starts + w] - c[starts]) / w), 1e-18))


def softlimit(x, ceil, knee=0.55):
    k = ceil * knee; a = np.abs(x); over = a > k
    y = x.copy(); y[over] = np.sign(x[over]) * (k + (ceil - k) * np.tanh((a[over] - k) / (ceil - k)))
    return y


def finish(x, cls, tail_fade=0.08, loop=False):
    """DC removal, 22 Hz high-pass, RMS gain staging per class with a soft limiter at CEIL_DB. Loops are left unfaded."""
    x = np.asarray(x, dtype=np.float64); x = x - np.mean(x)
    if not loop:
        x = hp(x, 22, SR, 2)
        k = int(tail_fade * SR); x[-k:] *= np.cos(np.linspace(0, math.pi / 2, k)) ** 2
        h = int(0.002 * SR); x[:h] *= np.linspace(0, 1, h)
    ceil = 10 ** (CEIL_DB / 20.0); target = CLASS_RMS[cls]; g = 10 ** ((target - wrms_db(x)) / 20.0) * 0.3
    for _ in range(8):
        y = softlimit(x * g, ceil)
        err = target - wrms_db(y)
        if abs(err) < 0.05: break
        g *= 10 ** (err / 20.0)
    y = np.clip(softlimit(x * g, ceil), -ceil, ceil)
    return y


def circ_hp(x, fc=28.0):
    """Circular high-pass (FFT) with NO edge fade: the loops are periodic by construction, so the wrap stays continuous."""
    sp = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1.0 / SR); sp *= np.clip((f - fc * 0.5) / (fc * 0.5), 0, 1) ** 2
    return np.fft.irfft(sp, len(x))


def stage_save(name, x, cls, bus, loop=False, **kw):
    y = finish(x, cls, loop=loop)
    # target_lufs = the array's own loudness so synthlib.normalize does not rescale (it only caps the peak)
    yy = hp(y - np.mean(y), 20, SR, 1)
    kw.setdefault('lazy', True); kw.setdefault('group', 'weapons'); kw.setdefault('quality', 4)
    if loop: y = circ_hp(y); yy = hp(y - np.mean(y), 20, SR, 1)
    return S.save(name, y, bus, loop=loop, peak=CEIL_DB + 0.4, target_lufs=S.lufs_approx(yy, SR), **kw)


# ------------------------------------------------------------------ makers: return (sub_layer, rest)
Z = np.zeros(1)


def m_hmg(r, i):
    pj = r.uniform(0.93, 1.07); rate = r.uniform(9.5, 11.5); n = 6; dur = 1.5; subs = []; rest = []
    for k in range(n):
        tk = k / rate + (r.uniform(-0.004, 0.004) if k else 0.0); a = r.uniform(0.82, 1.0)
        subs.append((sub(0.30, 80 * pj, 46 * pj, 0.03, 0.075, 0.003, 0.15), tk, a))
        rest.append((sumv(body(r, 0.22, 280, 0.05, 0.9), crack(r, 0.09, 1200, 6500, 0.0045, 0.7), crack(r, 0.06, 300, 1300, 0.012, 0.5)), tk, a))
    tl = tail(r, 1.45, 0.35, 0.2, 1000, 220, 0.35, 0.28)
    rest.append((echoes(tl, [(0.11, 0.5, 700), (0.23, 0.3, 500)]), 0.02, 1.0))
    return mix(dur, subs), mix(dur, rest)


def m_aa(r, i):
    pj = r.uniform(0.93, 1.07); rate = r.uniform(13.5, 15.5); n = 8; dur = 1.5; subs = []; rest = []
    ring_f = r.uniform(1650, 2150)
    for k in range(n):
        for b in (0, 1):                                           # twin barrels, ~14 ms apart
            tk = k / rate + b * r.uniform(0.011, 0.017) + (r.uniform(-0.003, 0.003) if k else 0.0); a = r.uniform(0.75, 1.0) * (0.85 if b else 1.0)
            subs.append((sub(0.2, 92 * pj, 54 * pj, 0.022, 0.05, 0.002, 0.2), tk, a))
            rest.append((sumv(body(r, 0.15, 400, 0.035, 0.8), crack(r, 0.06, 1500, 8000, 0.003, 0.9),
                              pingn(ring_f * r.uniform(0.97, 1.03), 0.09, 0.3, ((1, 1.0, 1.0), (2.41, 0.5, 0.6), (3.97, 0.25, 0.4)), r=r) * 0.35), tk, a))
    tl = tail(r, 1.4, 0.3, 0.2, 1400, 250, 0.3, 0.35)
    rest.append((echoes(tl, [(0.13, 0.5, 900), (0.29, 0.3, 600)]), 0.03, 1.0))
    return mix(dur, subs), mix(dur, rest)


def m_flak(r, i):
    pj = r.uniform(0.92, 1.08); dur = 1.45
    s = sub(0.6, 70 * pj, 38 * pj, 0.06, 0.16, 0.004, 0.1)
    n = n_of(0.9); t = tt(n)
    crump = unit(S.tv_filter(noise(n, 'white', r), 1300 * np.exp(-t / 0.12) + 160, 'lp', 2, SR, 256)) * np.exp(-t / 0.2) * np.minimum(1, t / 0.004)
    crump = crump * (1 + 0.5 * np.sin(TWO_PI * r.uniform(18, 26) * t) * np.exp(-t / 0.08))
    pop = sumv(crack(r, 0.12, 700, 6000, 0.01, 0.8), body(r, 0.4, 350, 0.1, 1.0))
    sparkle = debris(r, 1.2, 0.05, 90, 0.35, 1800, 9000, 0.05, 0.4)
    tl = tail(r, 1.4, 0.35, 0.28, 900, 200, 0.45, 0.4)
    return fit(s, n_of(dur)), sumv(crump * 0.9, pop, sparkle * 0.5, echoes(tl, [(0.17, 0.4, 600)]))


def m_mortar_launch(r, i):
    pj = r.uniform(0.93, 1.07); dur = 1.4; t = tt(n_of(0.5))
    s = sub(0.5, 74 * pj, 46 * pj, 0.045, 0.12, 0.003, 0.12)
    bloop = np.sin(TWO_PI * np.cumsum(90 * pj + 190 * pj * np.exp(-t / 0.035)) / SR) * np.exp(-t / 0.09) * np.minimum(1, t / 0.002)   # hollow tube "bloop"
    tube = pingn(r.uniform(150, 175), 0.18, 0.7, ((1, 1.0, 1.0), (2.0, 0.35, 0.6), (3.1, 0.15, 0.4)), r=r)
    pk = sumv(crack(r, 0.1, 500, 4500, 0.007, 0.8), body(r, 0.3, 320, 0.07, 1.0))
    tl = tail(r, 1.3, 0.3, 0.2, 900, 200, 0.35, 0.3)
    return fit(s, n_of(dur)), sumv(bloop * 0.8, tube * 0.45, pk, echoes(tl, [(0.15, 0.35, 600), (0.32, 0.2, 450)]))


def whistle_core(r, dur, f0, f1, curve=0.8, pj=1.0, air=0.8, rumble=0.0):
    n = n_of(dur); t = tt(n); u = t / dur
    f = f0 * pj * (f1 / f0) ** (u ** curve) * (1 + 0.012 * np.sin(TWO_PI * r.uniform(5, 8) * t))
    ph = TWO_PI * np.cumsum(f) / SR
    y = np.sin(ph) + 0.4 * np.sin(2 * ph + 0.3) + 0.15 * np.sin(3 * ph + 1.1)
    a = unit(S.tv_bandpass(noise(n, 'white', r), f * 1.1, 0.8, 2)) * air
    amp = (0.12 + 0.88 * u ** 1.6) * np.minimum(1, t / 0.05) * np.minimum(1, (dur - t) / 0.03)
    out = (y * 0.8 + a) * amp
    if rumble: out += unit(bp(noise(n, 'white', r), 40, 160, SR, 2)) * rumble * u ** 2.2 * np.minimum(1, (dur - t) / 0.03)
    return out


def m_mortar_whistle(r, i):
    return Z, whistle_core(r, 1.5, r.uniform(2300, 2900), r.uniform(900, 1200), 0.8, 1.0, 0.7, 0.25)


def m_howitzer(r, i):
    pj = r.uniform(0.93, 1.07); dur = 1.55
    s = sumv(sub(1.5, 88 * pj, 34 * pj, 0.09, 0.4, 0.004, 0.12), sub(1.0, 55 * pj, 38 * pj, 0.2, 0.3, 0.012, 0.0) * 0.5)
    rumble = tail(r, 1.5, 0.75, 0.35, 700, 150, 1.0, 0.3, 0.05)
    c = sumv(crack(r, 0.15, 400, 6500, 0.012, 1.0), crack(r, 0.3, 120, 900, 0.04, 0.9), body(r, 0.5, 300, 0.14, 1.0))
    return fit(s, n_of(dur)), sumv(c, echoes(rumble, [(0.2, 0.5, 500), (0.48, 0.35, 400), (0.8, 0.2, 300)]) * 0.8)


def m_naval(r, i):
    pj = r.uniform(0.94, 1.06); dur = 1.55
    s = sumv(sub(1.5, 82 * pj, 35 * pj, 0.1, 0.5, 0.005, 0.1), sub(1.2, 52 * pj, 36 * pj, 0.25, 0.42, 0.015, 0.0) * 0.6)
    c = sumv(crack(r, 0.2, 350, 6000, 0.014, 1.0), crack(r, 0.35, 100, 800, 0.05, 1.0), body(r, 0.6, 280, 0.18, 1.0))
    ring = pingn(r.uniform(260, 320) * pj, 0.35, 1.4, ((1, 1.0, 1.0), (1.62, 0.7, 0.8), (2.63, 0.5, 0.6), (4.3, 0.3, 0.4), (6.9, 0.18, 0.25)), r=r)
    rumble = tail(r, 1.5, 0.8, 0.4, 650, 140, 1.0, 0.25, 0.06)
    # water-slap tail: clustered low-passed slaps, rate and size falling
    n = n_of(dur); sl = np.zeros(n); t = 0.35
    while t < 1.4:
        t += r.uniform(0.045, 0.12) * (1 + (t - 0.35) * 0.9)
        g = r.uniform(0.4, 1.0) * math.exp(-(t - 0.35) / 0.6)
        k = n_of(r.uniform(0.05, 0.11)); tk = tt(k)
        slap = unit(S.tv_filter(noise(k, 'white', r), 1800 * np.exp(-tk / 0.025) + 250, 'lp', 2, SR, 128)) * np.exp(-tk / 0.03) * np.minimum(1, tk / 0.004)
        put(sl, slap, t, g * 0.55)
    return fit(s, n), sumv(c, ring * 0.38, echoes(rumble, [(0.25, 0.5, 500), (0.55, 0.35, 400), (0.9, 0.2, 300)]) * 0.8, sl)


def m_tank(r, i):
    pj = r.uniform(0.93, 1.07); dur = 1.35
    s = sub(0.9, 85 * pj, 44 * pj, 0.05, 0.2, 0.002, 0.15)
    c = sumv(crack(r, 0.12, 1500, 9000, 0.0035, 1.4), crack(r, 0.2, 400, 2500, 0.012, 1.0), body(r, 0.45, 340, 0.1, 1.0))
    clank = pingn(r.uniform(700, 900), 0.12, 0.4, ((1, 1.0, 1.0), (2.3, 0.5, 0.6)), r=r)
    tl = tail(r, 1.3, 0.38, 0.22, 1100, 220, 0.5, 0.4)
    return fit(s, n_of(dur)), sumv(c, mix(0.5, [(clank * 0.25, 0.09, 1.0)]), echoes(tl, [(0.14, 0.5, 800), (0.33, 0.3, 550)]))


def m_rpg_launch(r, i):
    pj = r.uniform(0.93, 1.07); dur = 1.3; n = n_of(1.0); t = tt(n); u = t / 1.0
    s = sub(0.5, 76 * pj, 48 * pj, 0.045, 0.1, 0.003, 0.1)
    centre = 500 + 2600 * (1 - np.exp(-t / 0.12)) - 1200 * u
    whoosh = unit(S.tv_bandpass(noise(n, 'white', r), centre, 1.3, 2)) * (1 - np.exp(-t / 0.035)) * np.exp(-t / 0.28)
    roar = unit(S.tv_filter(noise(n, 'white', r), 700 + 1500 * np.exp(-t / 0.2), 'lp', 2, SR, 512)) * np.exp(-t / 0.4) * (1 - np.exp(-t / 0.02))
    pk = sumv(crack(r, 0.1, 500, 5000, 0.006, 0.9), body(r, 0.25, 300, 0.06, 0.9))
    tl = tail(r, 1.2, 0.3, 0.2, 800, 180, 0.3, 0.25)
    return fit(s, n_of(dur)), sumv(whoosh * 0.9, roar * 0.45, pk, echoes(tl, [(0.18, 0.3, 600)]))


def m_rocket_loop(r, i):
    d = 2.0; n = n_of(d); t = tt(n)
    roar = circ_noise(n, 90, 6500, r, 0.7); rumble = circ_noise(n, 28, 170, r, 0.2)
    y = roar * 0.8 + rumble * 0.9
    for f, a in ((42, 0.8), (64, 0.5), (85.5, 0.35)):
        y += a * np.sin(TWO_PI * (f + 0.5 * i) * t + r.uniform(0, 6.28)) * (1 + 0.25 * np.sin(TWO_PI * int(r.integers(3, 12)) * t + r.uniform(0, 6.28)))
    y *= 1 + 0.18 * np.sin(TWO_PI * 5 * t + r.uniform(0, 6.28)) + 0.12 * np.sin(TWO_PI * 13 * t + r.uniform(0, 6.28))
    cr = np.zeros(n)
    for _ in range(int(d * 28)):
        put_circ(cr, tickn(r, 0.0015, 1800, 8000, r.uniform(0.2, 1.0)), r.integers(0, n))
    return Z, y + cr * 0.55


def m_rpg_hit(r, i):
    pj = r.uniform(0.93, 1.07); dur = 2.4
    s = sumv(sub(1.2, 85 * pj, 40 * pj, 0.05, 0.3, 0.002, 0.1))
    c = sumv(crack(r, 0.14, 800, 9000, 0.006, 1.2), crack(r, 0.25, 150, 1200, 0.03, 1.0), body(r, 0.6, 320, 0.13, 1.0))
    frags = debris(r, dur, 0.1, 60, 0.5, 1500, 8000, 0.1, 0.5)
    ring = pingn(r.uniform(1400, 2400), 0.15, 0.6, ((1, 1.0, 1.0), (2.7, 0.5, 0.6)), r=r)
    tl = tail(r, 2.3, 0.55, 0.35, 900, 180, 0.8, 0.5)
    return fit(s, n_of(dur)), sumv(c, ring * 0.12, frags * 0.55, echoes(tl, [(0.2, 0.4, 600), (0.45, 0.25, 450)]))


def blast(r, size, dur, f0, f1, tau, rumble_tau, dens, c_lo, name_pj=(0.93, 1.07)):
    pj = r.uniform(*name_pj)
    s = sumv(sub(dur * 0.8, f0 * pj, f1 * pj, 0.08 + 0.02 * size, tau, 0.003 + 0.002 * size, 0.1),
             sub(dur * 0.7, 56 * pj, 36 * pj, 0.25, tau * 0.8, 0.012 * (1 + size), 0.0) * (0.35 + 0.15 * size))
    c = sumv(crack(r, 0.15, 500, 9000, 0.008, 1.0), crack(r, 0.3, c_lo, 1200, 0.03 + 0.01 * size, 1.0), body(r, 0.6 + 0.2 * size, 350, 0.1 + 0.04 * size, 1.1))
    rumble = tail(r, dur - 0.05, rumble_tau, rumble_tau * 0.55, 900, 150, 1.0, 0.45, 0.05)
    rumble = echoes(rumble, [(0.22, 0.5, 550), (0.5, 0.35, 420), (0.9, 0.22, 320), (1.4, 0.12, 260)])
    deb = debris(r, dur, 0.3 + 0.1 * size, dens, 0.8 + 0.4 * size, 700, 6500, 0.55, 0.6)
    return fit(s, n_of(dur)), sumv(c, rumble * 0.85, deb)


def m_blast_small(r, i): return blast(r, 0, 2.2, 82, 40, 0.28, 0.7, 70, 150)
def m_blast_medium(r, i): return blast(r, 1, 3.0, 78, 38, 0.38, 1.0, 100, 120)
def m_blast_large(r, i): return blast(r, 2, 3.8, 74, 35, 0.5, 1.4, 140, 90)


def m_shell_whistle(r, i):
    return Z, whistle_core(r, 1.8, r.uniform(1700, 2100), r.uniform(520, 700), 0.7, 1.0, 1.0, 0.5)


def m_crater(r, i):
    pj = r.uniform(0.93, 1.07); dur = 1.8
    s = sumv(sub(1.5, 62 * pj, 34 * pj, 0.12, 0.3, 0.006, 0.05), sub(1.0, 45 * pj, 35 * pj, 0.3, 0.3, 0.02, 0.0) * 0.5)
    n = n_of(dur); t = tt(n)
    dirt = unit(S.tv_filter(noise(n, 'white', r), 600 * np.exp(-t / 0.08) + 120, 'lp', 2, SR, 256)) * np.exp(-t / 0.12) * np.minimum(1, t / 0.005)
    deb = debris(r, dur, 0.22, 45, 0.55, 500, 3500, 0.85, 0.7)
    return fit(s, n), sumv(dirt * 0.9, body(r, 0.7, 200, 0.2, 0.9, 35), deb * 0.7)


def m_flak_frag(r, i):
    pj = r.uniform(0.93, 1.07); dur = 1.6
    pop = sub(0.3, 85 * pj, 55 * pj, 0.02, 0.06, 0.002) * 0.7
    n = n_of(dur); fr = np.zeros(n); t = 0.04
    while t < 1.45:
        t += r.exponential(0.02 + 0.07 * (t / 1.45) ** 1.2)
        f = r.uniform(1500, 5200); g = r.uniform(0.2, 1.0) * math.exp(-t / 0.7)
        if r.random() < 0.3:      # a fragment whizzing past: falling zing
            k = n_of(0.12); tk = tt(k); y = np.sin(TWO_PI * np.cumsum(f * (1.3 - 0.9 * tk / 0.12)) / SR) * np.exp(-tk / 0.05) * np.minimum(1, tk / 0.004)
        else:
            y = pingn(f, r.uniform(0.01, 0.05), 0.2, ((1, 1.0, 1.0), (2.4, 0.4, 0.6)), r=r)
        put(fr, y, t, g * 0.5)
    tick = debris(r, dur, 0.04, 70, 0.5, 2500, 9000, 0.0, 0.5)
    return fit(pop, n), sumv(fr, tick * 0.5, crack(r, 0.08, 800, 6000, 0.008, 0.7), body(r, 0.2, 300, 0.05, 0.6))


def m_gunship_cannon(r, i):
    pj = r.uniform(0.93, 1.07); dur = 1.5
    s = sumv(sub(1.3, 90 * pj, 40 * pj, 0.07, 0.3, 0.003, 0.12))
    c = sumv(crack(r, 0.12, 500, 7000, 0.008, 1.1), crack(r, 0.25, 130, 1000, 0.035, 1.0), body(r, 0.5, 320, 0.12, 1.0))
    clunk = sumv(thump(n_of(0.15), 110 * pj, 0.03, 0.8, 0.3), tickn(r, 0.004, 700, 3500, 0.7, n_of(0.15)))
    tl = tail(r, 1.45, 0.45, 0.28, 1100, 200, 0.5, 0.4)
    # airborne platform: tail darkens quickly (doppler-ish roll-off) and has a short flutter
    t = tt(len(tl)); tl = tl * (1 + 0.25 * np.sin(TWO_PI * 22 * t) * np.exp(-t / 0.5))
    return fit(s, n_of(dur)), sumv(c, mix(0.3, [(clunk * 0.4, 0.08, 1.0)]), echoes(tl, [(0.16, 0.45, 700), (0.36, 0.25, 500)]))


def m_minigun_loop(r, i):
    d = 1.5; n = n_of(d); N = 90; per = n / N; out = np.zeros(n)
    am = 1 + 0.12 * np.sin(TWO_PI * 2 * tt(n) + r.uniform(0, 6.28)) + 0.08 * np.sin(TWO_PI * 7 * tt(n) + r.uniform(0, 6.28))
    for k in range(N):
        pos = k * per + r.uniform(-0.0004, 0.0004) * SR; a = r.uniform(0.8, 1.0)
        p = sumv(sub(0.035, 118, 62, 0.008, 0.012, 0.0008, 0.3), crack(r, 0.012, 1500, 7000, 0.0014, 0.55), body(r, 0.03, 500, 0.006, 0.45, 120))
        put_circ(out, p, pos, a)
    out *= am
    out += circ_noise(n, 30, 150, r, 0.0) * 0.25
    return Z, out


def m_ammo_chain(r, i):
    dur = 1.0; n = n_of(dur); out = np.zeros(n)
    put(out, thump(n_of(0.12), 95 * r.uniform(0.9, 1.1), 0.03, 0.7, 0.3), 0.0, 1.0)
    t = 0.03; rate = r.uniform(11, 14)
    while t < 0.8:
        f = r.uniform(1800, 3600) if r.random() < 0.7 else r.uniform(900, 1500)
        y = pingn(f, r.uniform(0.012, 0.035), 0.15, ((1, 1.0, 1.0), (2.76, 0.5, 0.5), (5.4, 0.2, 0.3)), r=r)
        put(out, y, t, r.uniform(0.3, 1.0) * 0.6); put(out, tickn(r, 0.003, 2000, 8000, 0.5), t, 0.4)
        t += r.uniform(0.5, 1.5) / rate
    put(out, slide_rasp_local(r, 0.7), 0.0, 0.25)
    return Z, out


def slide_rasp_local(r, dur):
    n = n_of(dur); t = np.linspace(0, 1, n)
    return unit(S.tv_bandpass(noise(n, 'white', r), 700 + 600 * np.sin(6 * t), 1.5, 2)) * np.sin(np.pi * t) ** 0.8


def m_bolt_heavy(r, i):
    bt = r.uniform(0.92, 1.08); dur = 0.85
    cl = lambda f, a, tau: sumv(thump(n_of(0.18), 85 * bt, 0.05, 1.0, 0.3), pingn(f * bt, tau, 0.4, ((1, 1.0, 1.0), (2.4, 0.5, 0.6), (4.1, 0.25, 0.4)), r=r) * a, tickn(r, 0.004, 1200, 6000, 0.8, n_of(0.18)))
    x = mix(dur, [(cl(620, 0.6, 0.06), 0.0, 0.9), (slide_rasp_local(r, 0.22) * 0.35, 0.1, 1.0), (cl(980, 0.7, 0.08), 0.34, 1.0), (sub(0.3, 80 * bt, 50 * bt, 0.03, 0.09, 0.002) * 0.8, 0.34, 1.0)])
    return Z, x


def m_overheat(r, i):
    dur = 2.4; n = n_of(dur); t = tt(n)
    env = np.minimum(1, t / 0.12) * np.exp(-t / 1.1) * (1 + 0.3 * np.sin(TWO_PI * r.uniform(1.5, 2.6) * t + r.uniform(0, 6)))
    hiss = unit(S.tv_filter(hp(noise(n, 'white', r), 2500, SR, 2), 9500 - 3500 * t / dur, 'lp', 2, SR, 512)) * env
    ticks = np.zeros(n); tk = 0.2
    while tk < dur - 0.1:
        f = r.uniform(1800, 4200)
        put(ticks, pingn(f, r.uniform(0.01, 0.03), 0.12, ((1, 1.0, 1.0), (2.3, 0.4, 0.5)), r=r), tk, r.uniform(0.4, 1.0) * math.exp(-tk / 1.4))
        tk += r.exponential(0.12 + 0.35 * tk / dur)
    low = body(r, 1.6, 180, 0.5, 0.4, 60)
    return Z, sumv(hiss * 0.75, ticks * 0.9, fit(low, n) * 0.2)


def m_turret_loop(r, i):
    d = 2.0; n = n_of(d); t = tt(n); ph0 = r.uniform(0, 6.28, 6)
    f0 = 210.0 + 14.0 * i
    fm = 1.2 * np.sin(TWO_PI * 1 * t + ph0[0]) + 0.7 * np.sin(TWO_PI * 3 * t + ph0[1])
    y = np.sin(TWO_PI * f0 * t + fm) + 0.45 * np.sin(TWO_PI * 2 * f0 * t + 2 * fm + ph0[2]) + 0.15 * np.sin(TWO_PI * 3 * f0 * t + ph0[3])
    gear = circ_noise(n, 250, 1900, r, 0.0) * (0.55 + 0.3 * np.sin(TWO_PI * 14 * t + ph0[4]))
    hum = np.sin(TWO_PI * 55 * t + ph0[5]) + 0.5 * np.sin(TWO_PI * 110 * t) + circ_noise(n, 35, 120, r) * 0.5
    ticks = np.zeros(n)
    for k in range(10): put_circ(ticks, tickn(r, 0.003, 600, 3500, 0.8), (k / 10.0 + r.uniform(-0.005, 0.005)) * n)
    return Z, y * 0.55 + gear * 0.45 + hum * 0.75 + ticks * 0.35


def m_turret_stop(r, i):
    bt = r.uniform(0.92, 1.08); dur = 0.55; n = n_of(0.3); t = tt(n)
    wind = np.sin(TWO_PI * np.cumsum(300 * bt * np.exp(-t / 0.12) + 70) / SR) * np.exp(-t / 0.1) * 0.5
    thud = sub(0.35, 78 * bt, 48 * bt, 0.03, 0.09, 0.002, 0.2)
    clunk = sumv(pingn(r.uniform(500, 750), 0.09, 0.35, ((1, 1.0, 1.0), (2.3, 0.5, 0.6), (4.2, 0.25, 0.4)), r=r), tickn(r, 0.004, 900, 5000, 0.9, n_of(0.2)))
    return Z, fit(sumv(wind * 0.5, mix(0.5, [(thud, 0.12, 1.2), (clunk * 0.7, 0.12, 1.0)])), n_of(dur))


# ------------------------------------------------------------------ table
# stem, maker, class, bus, variants, extra manifest kw, far?, sub?
def T(stem, mk, cls, bus='veh', far=False, subf=False, loop=False, **kw):
    return dict(stem=stem, mk=mk, cls=cls, bus=bus, far=far, sub=subf, loop=loop, kw=kw)


TABLE = [
    T('wpn_hmg_fire', m_hmg, 'fire', far='wpn_hmg_far', weight=8, max_dist=300, tags=['weapon', 'gunshot', 'heavy', 'hmg']),
    T('wpn_aa_fire', m_aa, 'fire', far='wpn_aa_far', weight=8, max_dist=320, tags=['weapon', 'gunshot', 'heavy', 'aa']),
    T('wpn_flak_burst', m_flak, 'boom', far='wpn_flak_burst_far', weight=9, max_dist=400, tags=['weapon', 'burst', 'heavy', 'flak']),
    T('wpn_mortar_launch', m_mortar_launch, 'fire', far='wpn_mortar_launch_far', weight=8, max_dist=350, tags=['weapon', 'launch', 'heavy', 'mortar']),
    T('wpn_mortar_whistle', m_mortar_whistle, 'whistle', weight=6, max_dist=250, tags=['weapon', 'whistle', 'incoming', 'mortar']),
    T('wpn_howitzer_fire', m_howitzer, 'boom', far='wpn_howitzer_far', subf=True, weight=10, max_dist=700, tags=['weapon', 'gunshot', 'heavy', 'howitzer', 'artillery']),
    T('wpn_naval_gun_fire', m_naval, 'boom', far='wpn_naval_gun_far', subf=True, weight=10, max_dist=800, tags=['weapon', 'gunshot', 'heavy', 'naval']),
    T('wpn_tank_cannon_fire', m_tank, 'fire', far='wpn_tank_cannon_far', weight=9, max_dist=500, tags=['weapon', 'gunshot', 'heavy', 'tank']),
    T('wpn_rpg_launch', m_rpg_launch, 'fire', far='wpn_rpg_launch_far', weight=7, max_dist=250, tags=['weapon', 'launch', 'rpg']),
    T('wpn_rocket_loop', m_rocket_loop, 'loop', loop=True, weight=5, max_dist=200, tags=['weapon', 'rocket', 'loop']),
    T('wpn_rpg_hit', m_rpg_hit, 'boom', bus='mat', weight=9, max_dist=450, tags=['impact', 'explosion', 'rpg']),
    T('imp_blast_small', m_blast_small, 'boom', bus='mat', weight=8, max_dist=450, tags=['impact', 'explosion', 'small']),
    T('imp_blast_medium', m_blast_medium, 'boom', bus='mat', subf=True, weight=9, max_dist=650, tags=['impact', 'explosion', 'medium']),
    T('imp_blast_large', m_blast_large, 'boom', bus='mat', subf=True, weight=10, max_dist=900, tags=['impact', 'explosion', 'large']),
    T('imp_shell_whistle', m_shell_whistle, 'whistle', bus='mat', weight=6, max_dist=300, tags=['impact', 'whistle', 'incoming', 'shell']),
    T('imp_crater_thud', m_crater, 'boom', bus='mat', subf=True, weight=7, max_dist=400, tags=['impact', 'ground', 'crater']),
    T('imp_flak_fragments', m_flak_frag, 'foley', bus='mat', weight=4, max_dist=200, tags=['impact', 'fragments', 'flak']),
    T('veh_gunship_cannon', m_gunship_cannon, 'fire', far='veh_gunship_cannon_far', weight=9, max_dist=600, tags=['weapon', 'gunshot', 'heavy', 'gunship', 'aircraft']),
    T('veh_gunship_minigun_loop', m_minigun_loop, 'loop', loop=True, weight=7, max_dist=400, tags=['weapon', 'minigun', 'gunship', 'loop']),
    T('wpn_ammo_chain', m_ammo_chain, 'foley', weight=3, max_dist=60, tags=['weapon', 'handling', 'belt']),
    T('wpn_bolt_heavy', m_bolt_heavy, 'foley', weight=3, max_dist=60, tags=['weapon', 'handling', 'bolt']),
    T('wpn_barrel_overheat', m_overheat, 'foley', weight=3, max_dist=60, tags=['weapon', 'handling', 'overheat']),
    T('foley_turret_traverse_loop', m_turret_loop, 'loop', bus='veh', loop=True, weight=3, max_dist=120, tags=['foley', 'turret', 'servo', 'loop']),
    T('foley_turret_stop', m_turret_stop, 'foley', bus='veh', weight=3, max_dist=120, tags=['foley', 'turret', 'clunk']),
]
# loops use bus 'veh' for weapon loops, but the sub layers go on 'veh' too


def far_of(x, r, stem):
    """Distance version: no crack (low-passed hard), delayed ~0.35 s (sound travel), and a long dark reverb tail."""
    y = lp(x, 520, SR, 4)
    y = np.concatenate([np.zeros(n_of(0.35)), y])
    y = reverb(y, 1.5, 0.65, 500, r)
    return y


def render():
    S.set_manifest('heavy')
    for e in TABLE:
        stem = e['stem']; mk = e['mk']; kw = dict(e['kw']); loop = e['loop']
        for i in range(3):
            r = rng(U.seed_of(stem, i)); s, rest = mk(r, i)
            full = sumv(s, rest) if len(s) > 1 else rest
            kk = dict(kw); kk.update(variants=3, rate=kw.get('rate', (0.94, 1.06)))
            stage_save('%s_%02d' % (stem, i + 1), full, e['cls'], e['bus'], loop=loop, **kk)
            if e['far']:
                rf = rng(U.seed_of(stem + '_far', i)); fx = far_of(full / (np.max(np.abs(full)) + 1e-9), rf, stem)
                fk = dict(kk); fk.update(weight=max(2, kw.get('weight', 5) - 3), max_dist=max(1200, kw.get('max_dist', 300) * 3), gain=0.7, tags=kw['tags'] + ['far'])
                stage_save('%s_%02d' % (e['far'], i + 1), fx, 'far', e['bus'], **fk)
            if e['sub']:
                sx = lp(s, 110, SR, 4)
                k2 = dict(kk); k2.update(weight=kw.get('weight', 5), gain=0.8, tags=kw['tags'] + ['sub'], rate=(0.96, 1.04), meta=dict(kind='sub-layer', note='mono 35-90 Hz body to layer under the full stem'))
                stage_save('%s_sub_%02d' % (stem, i + 1), sx, 'sub', e['bus'], **k2)
        print('rendered', stem)


RULES = [('wpn_', 'weapons'), ('imp_', 'weapons'), ('veh_gun', 'weapons'), ('foley_', 'people')]


def deploy():
    """Copy only the new heavy stems into ../audio and merge their entries into ../audio/manifest.json (other entries untouched)."""
    here = os.path.dirname(os.path.abspath(__file__)); dst = os.path.join(os.path.dirname(here), 'audio')
    frag = json.load(open(os.path.join(here, 'out', 'manifest.heavy.json'), encoding='utf-8'))
    mp = os.path.join(dst, 'manifest.json'); man = json.load(open(mp, encoding='utf-8'))
    for id_, e in frag.items():
        for pre, g in RULES:
            if id_.startswith(pre): e['group'] = g; e['lazy'] = True; break
        shutil.copy2(os.path.join(here, 'out', id_ + '.ogg'), os.path.join(dst, id_ + '.ogg'))
        man['assets'][id_] = e
    json.dump(man, open(mp, 'w', encoding='utf-8'))
    print('deployed %d heavy assets into %s' % (len(frag), dst))


if __name__ == '__main__':
    render()
    if '--no-deploy' not in sys.argv: deploy()
