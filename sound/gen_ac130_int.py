"""AC-130 INTERIOR pack: what the sensor-station operator hears through an aircrew headset / ear defenders.
Cabin ambience loops, headset comms bed + squelch clicks, interior versions of the howitzer, 40 mm and Vulcan, breech/loader
mechanics, casing clatter, ready-up cues and soft headset tones. Procedural, seeded, licence-free, mono 44.1 kHz Ogg Vorbis.

    python gen_ac130_int.py             # render to out/, trim, merge into ../audio and manifest.json (only ac130_int_* stems)
    python gen_ac130_int.py --no-deploy
    python gen_ac130_int.py how         # render only stems whose name contains 'how' (for iteration)

Two level modes: RMS classes (weapons and beds, via gen_heavy.stage_save) and a fixed-peak mode (clicks, tones, cues).
"""
import math, os, sys, json, shutil, wave, tempfile, subprocess, re
import numpy as np
import synthlib as S
import gen_util as U
from gen_heavy import *            # building blocks, CLASS_RMS, stage_save, put_circ, circ_noise ...
from gen_ac130 import circ_lp, rattle

# interior classes: weapons sit 3 to 6 dB under the matching exterior near class (boom -17.5, fire -19.3, loop -21.3)
CLASS_RMS.update(iwhine=-33.5, ihow=-22.0, ifire=-23.5, iloop=-25.5, ibed=-26.5, icomm=-34.0)
EXT = 'aircraft'


def ear(x, fc=2400, order=4):
    """Ear-defender / headset muffling: steep low-pass."""
    return lp(np.asarray(x, dtype=np.float64), fc, SR, order)


def circ_band(x, lo, hi, w=0.35):
    """Smooth circular band-pass by FFT mask (for periodic loops)."""
    sp = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1.0 / SR)
    lo_m = np.clip((f - lo * (1 - w)) / (lo * w + 1e-9), 0, 1); hi_m = np.clip((hi * (1 + w) - f) / (hi * w + 1e-9), 0, 1)
    return np.fft.irfft(sp * lo_m * hi_m, len(x))


def snap(f, D): return round(f * D) / D


def sine_tone(f, dur, att=0.008, rel=0.04, sweep=None, h2=0.0):
    n = n_of(dur); t = tt(n); ff = f if sweep is None else sweep[0] + (sweep[1] - sweep[0]) * np.clip(t / dur, 0, 1)
    ph = TWO_PI * np.cumsum(ff * np.ones(n)) / SR
    env = np.minimum(1, t / att) * np.minimum(1, (dur - t) / rel)
    return (np.sin(ph) + h2 * np.sin(2 * ph)) * env


# ------------------------------------------------------------------ cabin ambience (loops)
WHINE_HZ = (2950.0, 3250.0)       # per variant, snapped to the loop length
WHINE_DB = -10.0                  # whine amplitude relative to the drone (throb band) peak


def whine_core(r, D, i):
    """Thin steady 2 to 4 kHz tone, faint 2nd partial, +-4 Hz wavering at 3 Hz plus a slow 0.25 Hz drift, quiet sibilant turbine hiss above. Unit peak on the main tone."""
    n = n_of(D); t = tt(n); f = snap(WHINE_HZ[i], D)
    fm = 3.0; drift = 2.0 / D
    ph = TWO_PI * f * t + (4.0 / fm) * np.sin(TWO_PI * fm * t + r.uniform(0, 6)) + (22.0 / drift) * np.sin(TWO_PI * drift * t + r.uniform(0, 6)) + r.uniform(0, 6)
    am = 1 + 0.08 * np.sin(TWO_PI * (2 / D) * t + r.uniform(0, 6))
    tone = np.sin(ph) * am + 0.16 * np.sin(2 * ph + 0.7)
    hiss = circ_band(circ_noise(n, 4500, 9500, r, 0.0), 4500, 9500) * (1 + 0.3 * np.sin(TWO_PI * (3 / D) * t + r.uniform(0, 6)))
    return tone + 0.045 * hiss


def m_whine(r, i):
    return whine_core(r, 8.0, i)


def m_cabin(r, i):
    D = (10.0, 12.0)[i]; n = n_of(D); t = tt(n)
    bases = ((63.0, 64.4, 66.1, 67.7), (61.6, 63.8, 65.4, 68.1))[i]          # four props, 60 to 70 Hz, detuned => beating throb
    th = np.zeros(n)
    for f in bases:
        f = snap(f, D); p0 = r.uniform(0, TWO_PI)
        for h in range(1, 10):
            th += (1.0 / h ** 0.85) * (1.35 if h == 2 else 1.0) * np.sin(TWO_PI * f * h * t + p0 * h + r.uniform(0, TWO_PI)) * 0.3
    th = circ_lp(th, 900)
    gust = 1 + 0.11 * np.sin(TWO_PI * (3 / D) * t + r.uniform(0, 6)) + 0.07 * np.sin(TWO_PI * (7 / D) * t + r.uniform(0, 6))
    roar = circ_lp(circ_noise(n, 70, 3200, r, 0.75), 2800) * gust
    rumble = circ_noise(n, 28, 170, r, 0.3)
    whine = np.zeros(n)
    f4 = snap(400, D); whine += 0.6 * np.sin(TWO_PI * f4 * t + r.uniform(0, 6)) + 0.3 * np.sin(TWO_PI * 2 * f4 * t + r.uniform(0, 6)) + 0.14 * np.sin(TWO_PI * 3 * f4 * t + r.uniform(0, 6))   # 400 Hz electrical hum
    fh = snap(1260 + 90 * i, D); whine += 0.5 * np.sin(TWO_PI * fh * t + 1.4 * np.sin(TWO_PI * (2 / D) * t) + r.uniform(0, 6)) * (1 + 0.3 * np.sin(TWO_PI * (5 / D) * t))   # hydraulic pump
    fg = snap(1860 - 130 * i, D); whine += 0.3 * np.sin(TWO_PI * fg * t + 0.8 * np.sin(TWO_PI * (3 / D) * t + r.uniform(0, 6)) + r.uniform(0, 6))
    rt = np.zeros(n)
    for _ in range(9):                                                         # loose panels: ringing ticks
        f = r.uniform(170, 880); k = n_of(r.uniform(0.05, 0.12)); tx = np.arange(k) / SR
        put_circ(rt, np.sin(TWO_PI * f * tx + r.uniform(0, 6)) * np.exp(-tx / r.uniform(0.012, 0.04)) * r.uniform(0.2, 0.7), r.uniform(0, n))
    for _ in range(3):                                                         # and a short buzz
        k = n_of(r.uniform(0.12, 0.25)); tx = np.arange(k) / SR
        bz = unit(bp(noise(k, 'white', r), 110, 520, SR, 2)) * (0.5 + 0.5 * np.sign(np.sin(TWO_PI * r.uniform(24, 34) * tx))) * np.sin(np.pi * tx / tx[-1]) ** 2 * r.uniform(0.15, 0.3)
        put_circ(rt, bz, r.uniform(0, n))
    out = unit(th) * 1.0 + unit(roar) * 0.62 + unit(rumble) * 0.4 + unit(whine) * 0.075 + rt * 0.14
    out = circ_lp(out, 3200)
    drone_pk = np.max(np.abs(circ_band(out, 40, 160)))                       # throb-band peak
    w = whine_core(rng(U.seed_of('ac130_int_whine', i)), D, i)
    return out + w * drone_pk * 10 ** (WHINE_DB / 20) / np.max(np.abs(w))


def m_headset(r, i):
    D = 10.0; n = n_of(D); t = tt(n)
    hiss = circ_noise(n, 300, 3400, r, 0.0) * (1 + 0.18 * np.sin(TWO_PI * (2 / D) * t + r.uniform(0, 6)))
    room = circ_noise(n, 300, 800, r, 0.5) * 0.35 * (1 + 0.3 * np.sin(TWO_PI * (3 / D) * t + r.uniform(0, 6)))
    fc = snap(1020, D)                                                        # faint intercom carrier
    car = (0.5 * np.sin(TWO_PI * fc * t + 0.6 * np.sin(TWO_PI * (1 / D) * t)) + 0.14 * np.sin(TWO_PI * 2 * fc * t + 1)) * (0.8 + 0.2 * np.sin(TWO_PI * (4 / D) * t))
    out = unit(hiss) * 0.5 + unit(room) * 0.3 + car * 0.1
    return circ_band(out, 300, 3400)


def m_click(r, i):
    pj = r.uniform(0.9, 1.15)
    x = sumv(tickn(r, 0.0016, 700, 3200, 1.0), pingn(1250 * pj, 0.004, 0.03, ((1, 0.5, 1.0), (1.9, 0.25, 0.6))), thump(n_of(0.012), 520 * pj, 0.003, 0.4, 0.2))
    if i % 2: x = sumv(x, mix(0.06, [(tickn(r, 0.0012, 900, 3000, 0.45), 0.034, 1.0)]))        # double-tap variants
    return bp(x, 300, 3400, SR, 2)


def m_squelch(r, i):
    dur = 0.2 + 0.03 * i; n = n_of(dur); t = tt(n)
    burst = bp(noise(n, 'white', r), 500, 3200, SR, 2) * np.exp(-t / (0.045 + 0.01 * i)) * np.minimum(1, t / 0.002)
    f = 1700 - 800 * np.clip(t / 0.05, 0, 1); drop = np.sin(TWO_PI * np.cumsum(f) / SR) * np.exp(-t / 0.03) * 0.22
    return bp(sumv(burst, drop, mix(0.01, [(tickn(r, 0.0014, 700, 3200, 0.9), 0.0, 1.0)])), 300, 3400, SR, 2)


# ------------------------------------------------------------------ interior howitzer
def hyd_hiss(r, dur, lo=450, hi=1800, peak_t=0.6, level=1.0):
    n = n_of(dur); t = tt(n)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1) ** peak_t) ** 1.5
    return unit(bp(noise(n, 'white', r), lo, hi, SR, 2)) * env * level


def m_ihow_fire(r, i):
    pj = r.uniform(0.92, 1.08); dur = 2.1; n = n_of(dur); t = tt(n)
    th = sumv(sub(1.7, 52 * pj, 24 * pj, 0.12, 0.6, 0.004, 0.22), sub(0.9, 90 * pj, 40 * pj, 0.05, 0.2, 0.002, 0.3) * 0.7)
    bl = sumv(crack(r, 0.12, 90, 900, 0.03, 1.0), body(r, 0.5, 420, 0.12, 1.0, 40)) * 0.8
    fm = r.uniform(13, 19)
    sh = unit(bp(noise(n, 'white', r), 28, 180, SR, 2)) * (0.55 + 0.45 * np.sin(TWO_PI * fm * t + r.uniform(0, 6))) * np.exp(-t / 0.7) * np.minimum(1, t / 0.012) * 0.75
    recoil_t = 0.13 + 0.01 * i
    clunk = sumv(thump(n_of(0.3), 112 * pj, 0.05, 0.95, 0.3), tickn(r, 0.005, 250, 1800, 0.55, n_of(0.12)), pingn(240 * pj, 0.03, 0.2, ((1, 0.5, 1), (2.6, 0.3, 0.5)), r=r) * 0.5)
    hyd = hyd_hiss(r, 0.55, 500, 1800, 0.7, 0.18)
    clang_t = 0.40 + 0.03 * i + r.uniform(0, 0.02)
    clang = sumv(pingn(380 * pj, 0.11, 0.7, ((1, 1.0, 1.0), (2.32, 0.55, 0.7), (3.6, 0.3, 0.5), (5.1, 0.12, 0.4)), r=r) * 0.45, tickn(r, 0.004, 400, 2400, 0.8, n_of(0.1)), thump(n_of(0.2), 150 * pj, 0.03, 0.5, 0.3))
    rt = lp(rattle(r, dur, 0.06, 0.75), 1500, SR, 2)
    x = mix(dur, [(th, 0.0, 1.0), (bl, 0.0, 1.0), (sh, 0.0, 1.0), (clunk, recoil_t, 1.0), (hyd, recoil_t + 0.04, 1.0), (clang, clang_t, 1.0), (rt, 0.0, 0.75)])
    return ear(x, 2100)


# ------------------------------------------------------------------ mechanics (howitzer loader, cannon loader)
def m_hoist(r, dur=1.3, up=1.0):
    n = n_of(dur); t = tt(n); rise = np.clip(t / (dur * 0.8), 0, 1)
    f = (62 + 100 * rise ** 1.2) * np.ones(n); ph = TWO_PI * np.cumsum(f) / SR
    mot = (np.sin(ph) + 0.55 * np.sin(2 * ph + 0.5) + 0.3 * np.sin(3 * ph + 1.1) + 0.15 * np.sin(5 * ph)) * np.minimum(1, t / 0.12) * np.minimum(1, (dur - t) / 0.18)
    whine = np.sin(TWO_PI * np.cumsum((560 + 600 * rise) * np.ones(n)) / SR) * 0.1 * np.minimum(1, t / 0.2) * np.minimum(1, (dur - t) / 0.15)
    out = unit(mot) * 0.7 + unit(whine) * 0.14
    tk = 0.04
    while tk < dur - 0.1:                                                        # chain links
        put(out, sumv(tickn(r, 0.004, 300, 1500, 0.4 * r.uniform(0.6, 1.0)), thump(n_of(0.04), 160, 0.012, 0.25, 0.2)), tk, up)
        tk += 1.0 / (13 + 6 * (tk / dur)) * r.uniform(0.9, 1.1)
    out += unit(bp(noise(n, 'white', r), 200, 1100, SR, 2)) * 0.12 * np.minimum(1, t / 0.2) * np.minimum(1, (dur - t) / 0.2)
    return out


def m_ram(r, dur=0.9):
    push = hyd_hiss(r, 0.5, 350, 1500, 0.8, 0.5)
    stroke = sine_tone(95, 0.45, 0.06, 0.2, (80, 125), 0.4) * 0.35
    hit = sumv(thump(n_of(0.35), 78, 0.07, 1.0, 0.3), thump(n_of(0.25), 150, 0.03, 0.5, 0.3), tickn(r, 0.005, 250, 2200, 0.9, n_of(0.1)),
               pingn(310, 0.05, 0.3, ((1, 0.6, 1), (2.4, 0.3, 0.6)), r=r) * 0.5)
    return mix(dur, [(push, 0.0, 1.0), (stroke, 0.05, 1.0), (hit, 0.46, 1.0)])


def m_latch(r, big=1.0):
    return sumv(thump(n_of(0.3), 66, 0.09, 0.9 * big, 0.3), pingn(335, 0.12, 0.8, ((1, 1, 1), (2.28, 0.6, 0.7), (3.7, 0.3, 0.5), (5.3, 0.12, 0.4)), r=r) * 0.45 * big,
                tickn(r, 0.003, 800, 3200, 0.9, n_of(0.08)), mix(0.2, [(tickn(r, 0.002, 1000, 3500, 0.6, n_of(0.05)), 0.07, 1.0)]))


def m_breech(r):
    return mix(0.9, [(m_latch(r, 1.0), 0.0, 1.0), (thump(n_of(0.4), 48, 0.12, 0.6, 0.3), 0.01, 1.0), (hyd_hiss(r, 0.3, 500, 1600, 0.6, 0.12), 0.1, 1.0)])


def clack(r, f=620, g=1.0, hard=1.0):
    return g * sumv(tickn(r, 0.004, 500, 3500, 0.9, n_of(0.06)), pingn(f * r.uniform(0.95, 1.05), 0.018, 0.12, ((1, 1, 1), (2.2, 0.6, 0.6), (3.7, 0.3, 0.4)), r=r) * 0.7,
                    thump(n_of(0.09), 150 * hard, 0.02, 0.55, 0.2))


def scrape(r, dur, lo=700, hi=2600, level=0.3):
    n = n_of(dur); t = tt(n); fc = lo + (hi - lo) * t / dur
    return unit(S.tv_bandpass(noise(n, 'white', r), fc, 0.8, 2, SR, 256)) * np.sin(np.pi * t / dur) ** 0.7 * level


def m_clip(r, i):
    dur = 0.5; g2 = 0.13 + 0.02 * i
    return mix(dur, [(clack(r, 560 + 40 * i), 0.0, 1.0), (scrape(r, 0.1, 800, 2400, 0.28), 0.045, 1.0), (clack(r, 700, 0.8), g2, 1.0),
                     (clack(r, 480, 1.15, 1.2), g2 + 0.12 + 0.02 * i, 1.0), (hyd_hiss(r, 0.18, 400, 1200, 0.5, 0.06), g2 + 0.1, 1.0)])


def m_ready_cannon(r):
    return mix(1.0, [(clack(r, 560), 0.0, 1.0), (scrape(r, 0.18, 700, 2300, 0.3), 0.05, 1.0), (clack(r, 690, 0.8), 0.27, 1.0), (clack(r, 520, 0.9), 0.41, 1.0),
                     (scrape(r, 0.12, 900, 2000, 0.22), 0.5, 1.0), (clack(r, 440, 1.2, 1.2), 0.74, 1.0), (thump(n_of(0.2), 70, 0.05, 0.5, 0.3), 0.75, 1.0)])


def m_ready_howitzer(r):
    return mix(2.1, [(m_hoist(r, 1.05, 0.7), 0.0, 0.85), (m_ram(r, 0.8), 1.0, 0.9), (m_latch(r, 0.8), 1.62, 1.0)])


def m_ready_vulcan(r):
    return sumv(tickn(r, 0.002, 600, 3200, 0.9, n_of(0.04)), pingn(880, 0.012, 0.1, ((1, 1, 1), (2.5, 0.4, 0.5)), r=r) * 0.6, thump(n_of(0.06), 140, 0.012, 0.4, 0.2),
                mix(0.12, [(tickn(r, 0.0014, 900, 3500, 0.5, n_of(0.03)), 0.045, 1.0)]))


def m_casing(r, i):
    out = np.zeros(n_of(1.0)); t0 = 0.0
    for c in range(2 + (i % 3)):
        f = r.uniform(1700, 3100); a = r.uniform(0.5, 1.0); dt = r.uniform(0.07, 0.11); tc = t0 + c * r.uniform(0.07, 0.19)
        for b in range(int(r.integers(4, 8))):
            put(out, sumv(pingn(f * r.uniform(0.98, 1.02), 0.012 * r.uniform(0.8, 1.4), 0.1, ((1, 1, 1), (2.7, 0.5, 0.5), (4.9, 0.25, 0.3)), r=r) * a, tickn(r, 0.002, 1500, 4500, 0.4 * a, n_of(0.02))), tc, 1.0)
            tc += dt; dt *= r.uniform(0.6, 0.78); a *= r.uniform(0.6, 0.78)
    return ear(out, 4200)


def m_rearm_how(r, i):
    pj = r.uniform(0.93, 1.07); dur = 0.8
    click = sumv(tickn(r, 0.002, 800, 3500, 0.9, n_of(0.05)), pingn(1450 * pj, 0.008, 0.06, ((1, 0.6, 1), (2.3, 0.3, 0.6)), r=r) * 0.5)
    seat = hyd_hiss(r, 0.28, 400, 1500, 0.6, 0.35)
    tt1 = 0.17 + 0.02 * i
    thunk = sumv(thump(n_of(0.35), 62 * pj, 0.08, 1.0, 0.3), thump(n_of(0.2), 125 * pj, 0.03, 0.6, 0.3), tickn(r, 0.005, 200, 1600, 0.6, n_of(0.08)))
    latch = sumv(pingn(300 * pj, 0.07, 0.4, ((1, 0.8, 1), (2.3, 0.5, 0.7), (3.8, 0.25, 0.5)), r=r) * 0.6, tickn(r, 0.003, 600, 2800, 0.8, n_of(0.06)), thump(n_of(0.15), 95 * pj, 0.025, 0.6, 0.3))
    return ear(mix(dur, [(click, 0.0, 1.0), (seat, 0.05, 1.0), (thunk, tt1, 1.0), (latch, tt1 + 0.2 + 0.015 * i, 0.95)]), 2800)


def m_rearm_can(r, i):
    pj = r.uniform(0.94, 1.06); dur = 0.4
    click = sumv(tickn(r, 0.002, 900, 3800, 0.9, n_of(0.04)), pingn(1250 * pj, 0.008, 0.06, ((1, 0.6, 1), (2.4, 0.3, 0.6)), r=r) * 0.5)
    thunk = sumv(thump(n_of(0.2), 85 * pj, 0.045, 1.0, 0.3), thump(n_of(0.1), 170 * pj, 0.02, 0.5, 0.3), tickn(r, 0.003, 300, 2000, 0.5, n_of(0.05)))
    return ear(mix(dur, [(click, 0.0, 1.0), (thunk, 0.09 + 0.015 * i, 1.0)]), 3000)


# ------------------------------------------------------------------ interior 40 mm
def m_icannon(r, i):
    pj = r.uniform(0.93, 1.07); dur = 0.7
    th = sub(0.45, 118 * pj, 52 * pj, 0.03, 0.11, 0.002, 0.25)
    bang = sumv(crack(r, 0.1, 140, 1700, 0.014, 1.0), body(r, 0.2, 520, 0.035, 0.9, 60))
    clank = sumv(thump(n_of(0.14), 185 * pj, 0.022, 0.55, 0.25), tickn(r, 0.003, 700, 3200, 0.55, n_of(0.1)), pingn(520 * pj, 0.03, 0.2, ((1, 0.6, 1), (2.4, 0.3, 0.6)), r=r) * 0.5)
    spring = sumv(thump(n_of(0.2), 80 * pj, 0.05, 0.45, 0.3), tickn(r, 0.004, 300, 1500, 0.3, n_of(0.08)))
    rt = lp(rattle(r, dur, 0.04, 0.35, rate0=70.0, tau=0.22), 1400, SR, 2)
    x = mix(dur, [(th, 0.0, 1.0), (bang, 0.0, 1.0), (clank, 0.045 + 0.008 * i, 1.0), (spring, 0.19 + 0.01 * i, 1.0), (rt, 0.0, 0.5)])
    return ear(x, 2500)


# ------------------------------------------------------------------ interior Vulcan
VD = 1.2; VN = 80; VRATE = VN / VD


def ipulse(r, a=1.0):
    return a * sumv(sub(0.06, 95, 52, 0.01, 0.02, 0.0008, 0.25) * 0.9, lp(crack(r, 0.03, 200, 1600, 0.004, 0.8), 2000, SR, 2), body(r, 0.06, 420, 0.012, 0.7, 70))


def m_ivul_loop(r, i):
    n = n_of(VD); t = tt(n); per = n / VN; out = np.zeros(n)
    for k in range(VN): put_circ(out, ipulse(r, r.uniform(0.8, 1.0)), k * per + r.uniform(-0.0006, 0.0006) * SR)
    out *= 1 + 0.08 * np.sin(TWO_PI * 2 / VD * t + r.uniform(0, 6))
    whirr = np.zeros(n)
    for kk, a in ((400, 0.55), (800, 0.32), (1200, 0.16), (300, 0.3), (200, 0.35)):        # multiples of 1/1.2 Hz: gear whine around 13.3 rev/s
        whirr += a * np.sin(TWO_PI * (kk / VD) * t + r.uniform(0, 6) + 0.35 * np.sin(TWO_PI * (5 / VD) * t + r.uniform(0, 6)))
    gear = circ_noise(n, 300, 1500, r, 0.2) * (0.7 + 0.3 * np.sin(TWO_PI * 16 / VD * t))
    out = out * 0.85 + whirr * 0.34 + gear * 0.14 + circ_noise(n, 30, 140, r, 0.0) * 0.18
    return circ_lp(out, 2300)


def spin_pulses_i(r, dur, rate_fn, amp_fn):
    n = n_of(dur); t = tt(n); ph = np.cumsum(rate_fn(t)) / SR; k = np.floor(ph).astype(int); idx = np.nonzero(np.diff(k) > 0)[0] + 1
    out = np.zeros(n)
    for j in idx: put(out, ipulse(r, amp_fn(j / SR) * r.uniform(0.82, 1.0)), j / SR, 1.0)
    return out


def m_ivul_start(r, i):
    dur = 1.4; n = n_of(dur); t = tt(n); T = 0.95
    sm = lambda x: (lambda s_: s_ * s_ * (3 - 2 * s_))(np.clip(x / T, 0, 1))
    out = spin_pulses_i(r, dur, lambda x: 3 + (VRATE - 3) * sm(x), lambda tj: 0.35 + 0.65 * min(1, tj / T))
    s = sm(t); f = 60 + 273.3 * s; ph = TWO_PI * np.cumsum(f) / SR
    whirr = (np.sin(ph) + 0.55 * np.sin(2 * ph + 0.4) + 0.3 * np.sin(3 * ph + 1.0)) * np.minimum(1, t / 0.1) * (0.25 + 0.75 * s)
    gear = unit(S.tv_filter(noise(n, 'white', r), 300 + 1200 * s, 'lp', 2, SR, 512)) * 0.12 * (0.3 + 0.7 * s)
    clunk = mix(0.3, [(sumv(thump(n_of(0.2), 100, 0.04, 0.8, 0.3), tickn(r, 0.004, 300, 1800, 0.6, n_of(0.08))), 0.0, 1.0)])   # clutch engages
    x = out * 0.85 + whirr * 0.3 + gear + fit(clunk, n)
    return ear(x, 2300)


def m_ivul_end(r, i):
    dur = 1.7; n = n_of(dur); t = tt(n); T = 0.9
    out = spin_pulses_i(r, dur, lambda x: VRATE * np.exp(-np.maximum(x - 0.02, 0) / (T * 0.45)) * (x < T + 0.2), lambda tj: 0.3 + 0.7 * math.exp(-tj / T))
    f = 60 + 273.3 * np.exp(-t / 0.5); ph = TWO_PI * np.cumsum(f) / SR
    whirr = (np.sin(ph) + 0.55 * np.sin(2 * ph + 0.4) + 0.3 * np.sin(3 * ph + 1.0)) * np.exp(-t / 0.62)
    gear = unit(S.tv_filter(noise(n, 'white', r), 250 + 1200 * np.exp(-t / 0.5), 'lp', 2, SR, 512)) * 0.1 * np.exp(-t / 0.5)
    x = out * 0.85 + whirr * 0.3 + gear + fit(mix(1.0, [(thump(n_of(0.3), 70, 0.07, 0.35, 0.3), 0.0, 1.0)]), n)
    x = x + 0.25 * lp(echoes(x, [(0.05, 0.4, 700), (0.11, 0.25, 500)]), 900, SR, 2)
    return ear(x, 2300)


# ------------------------------------------------------------------ cues and tones (headset, no voice)
def m_sel(f): return lambda r: bp(sine_tone(f, 0.13, 0.01, 0.06, None, 0.08), 300, 3400, SR, 2)


def m_losing(r):
    a = sine_tone(0, 0.11, 0.012, 0.05, (1320, 990), 0.05)
    return bp(mix(0.4, [(a, 0.0, 1.0), (a, 0.2, 0.85)]), 300, 3400, SR, 2)


def m_lock(r):
    tone = sine_tone(0, 0.3, 0.008, 0.12, (1000, 1175), 0.1)
    n = len(tone); t = tt(n); tone *= np.where(t < 0.06, 1.0, 1.0) * (1 - 0.35 * np.clip((t - 0.06) / 0.2, 0, 1))
    return bp(tone, 300, 3400, SR, 2)


# ------------------------------------------------------------------ table
# mode 'rms' uses a CLASS_RMS key; mode 'pk' sets a fixed peak (dBFS). play = (gapMs, maxVoices, preload, note)
def P(stem, mk, count, mode, lvl, bus, group, loop=False, weight=4, play=None, rate=(0.96, 1.04), tags=(), q=4, plain=False, **kw):
    return dict(stem=stem, mk=mk, count=count, mode=mode, lvl=lvl, bus=bus, group=group, loop=loop, weight=weight, play=play, rate=rate, tags=list(tags), q=q, plain=plain, kw=kw)


TABLE = [
    P('ac130_int_cabin_loop', m_cabin, 2, 'rms', 'ibed', 'veh', EXT, loop=True, weight=6, rate=(1.0, 1.0), q=3, tags=['ac130', 'interior', 'loop', 'cabin'],
      play=dict(gapMs=0, maxVoices=1, preload=True, note='station bed; start on entering the station, crossfade 0.6 to 1.0 s')),
    P('ac130_int_whine_loop', m_whine, 2, 'rms', 'iwhine', 'ui', EXT, loop=True, weight=4, rate=(0.97, 1.03), q=3, tags=['ac130', 'interior', 'loop', 'whine'],
      play=dict(gapMs=0, maxVoices=1, preload=True, note='same whine as in the cabin loops, alone; modulate gain and playbackRate 0.97 to 1.03 with bank and engine load')),
    P('ac130_int_headset_loop', m_headset, 1, 'rms', 'icomm', 'ui', EXT, loop=True, weight=4, rate=(1.0, 1.0), q=2, tags=['ac130', 'interior', 'loop', 'headset'],
      play=dict(gapMs=0, maxVoices=1, preload=True, note='comms bed, 300 Hz to 3.4 kHz; play under the cabin loop')),
    P('ac130_int_comms_click', m_click, 4, 'pk', -21.0, 'ui', EXT, weight=3, rate=(0.92, 1.1), pad=0.1, tags=['ac130', 'interior', 'headset', 'click'],
      play=dict(gapMs=900, maxVoices=2, preload=True, note='random every 3 to 9 s, or with the weapon-select beep')),
    P('ac130_int_comms_squelch', m_squelch, 3, 'pk', -22.0, 'ui', EXT, weight=3, rate=(0.94, 1.08), pad=0.1, tags=['ac130', 'interior', 'headset', 'squelch'],
      play=dict(gapMs=4000, maxVoices=1, preload=True, note='rare, every 12 to 30 s, never within 1 s of a fire event')),
    P('ac130_int_howitzer_fire', m_ihow_fire, 3, 'rms', 'ihow', 'veh', 'weapons', weight=10, tags=['ac130', 'interior', 'weapon', 'howitzer', '105mm'],
      play=dict(gapMs=1200, maxVoices=3, preload=True, note='replaces the near exterior fire + sub while at the station')),
    P('ac130_int_howitzer_hoist', lambda r, i: m_hoist(r, 1.3), 1, 'pk', -18.0, 'veh', 'weapons', weight=4, pad=0.1, tags=['ac130', 'interior', 'howitzer', 'loader'],
      play=dict(gapMs=1500, maxVoices=1, preload=True, note='after fire, as the next shell is lifted')),
    P('ac130_int_howitzer_ram', lambda r, i: m_ram(r, 0.9), 1, 'pk', -13.0, 'veh', 'weapons', weight=4, pad=0.1, tags=['ac130', 'interior', 'howitzer', 'loader'],
      play=dict(gapMs=1500, maxVoices=1, preload=True, note='after the hoist (about 1.1 s later)')),
    P('ac130_int_howitzer_breech', lambda r, i: m_breech(r), 1, 'pk', -12.0, 'veh', 'weapons', weight=4, pad=0.1, tags=['ac130', 'interior', 'howitzer', 'loader'],
      play=dict(gapMs=1500, maxVoices=1, preload=True, note='after the ram; the breech is closed, gun ready')),
    P('ac130_int_cannon_fire', m_icannon, 4, 'rms', 'ifire', 'veh', 'weapons', weight=9, tags=['ac130', 'interior', 'weapon', 'bofors', '40mm'],
      play=dict(gapMs=300, maxVoices=4, preload=True, note='2 to 3 per second; never the same variant twice in a row')),
    P('ac130_int_cannon_clip', m_clip, 3, 'pk', -12.0, 'veh', 'weapons', weight=4, pad=0.1, tags=['ac130', 'interior', 'bofors', 'loader'],
      play=dict(gapMs=700, maxVoices=1, preload=True, note='every 4 to 6 rounds, or when the clip is reloaded')),
    P('ac130_int_vulcan_start', m_ivul_start, 1, 'rms', 'iloop', 'veh', 'weapons', weight=8, tags=['ac130', 'interior', 'weapon', 'vulcan', 'spinup'],
      play=dict(gapMs=0, maxVoices=1, preload=True, note='on trigger press; start the loop at about 1.2 s with a 0.15 s crossfade')),
    P('ac130_int_vulcan_loop', m_ivul_loop, 2, 'rms', 'iloop', 'veh', 'weapons', loop=True, weight=8, rate=(1.0, 1.0), tags=['ac130', 'interior', 'weapon', 'vulcan', 'loop'],
      play=dict(gapMs=0, maxVoices=1, preload=True, note='one variant per burst; do not rate-modulate more than 0.97 to 1.03')),
    P('ac130_int_vulcan_end', m_ivul_end, 1, 'rms', 'iloop', 'veh', 'weapons', weight=8, tags=['ac130', 'interior', 'weapon', 'vulcan', 'spindown'],
      play=dict(gapMs=0, maxVoices=1, preload=True, note='on release; fade the loop out in 80 to 100 ms')),
    P('ac130_int_casing', m_casing, 4, 'pk', -15.0, 'veh', 'weapons', weight=3, rate=(0.92, 1.1), pad=0.1, tags=['ac130', 'interior', 'casing', 'foley'],
      play=dict(gapMs=250, maxVoices=3, preload=True, note='one per cannon or howitzer round, 0.1 to 0.4 s after the shot; at most 3 per second for the Vulcan')),
    P('ac130_int_ready_howitzer', lambda r, i: m_ready_howitzer(r), 1, 'pk', -15.0, 'veh', 'weapons', weight=5, plain=True, pad=0.1, tags=['ac130', 'interior', 'ready', 'howitzer'],
      play=dict(gapMs=2000, maxVoices=1, preload=True, note='on selecting the howitzer ("Getting ready" state, about 2 s)')),
    P('ac130_int_ready_cannon', lambda r, i: m_ready_cannon(r), 1, 'pk', -11.0, 'veh', 'weapons', weight=5, plain=True, pad=0.1, tags=['ac130', 'interior', 'ready', 'bofors'],
      play=dict(gapMs=1200, maxVoices=1, preload=True, note='on selecting the 40 mm (about 1 s)')),
    P('ac130_int_rearm_howitzer', m_rearm_how, 4, 'pk', -9.0, 'veh', 'weapons', weight=5, pad=0.1, tags=['ac130', 'interior', 'rearm', 'howitzer'],
      play=dict(gapMs=600, maxVoices=1, preload=True, note='the moment the howitzer becomes ready, and after every shot when it can fire again')),
    P('ac130_int_rearm_cannon', m_rearm_can, 3, 'pk', -12.0, 'veh', 'weapons', weight=5, pad=0.1, tags=['ac130', 'interior', 'rearm', 'bofors'],
      play=dict(gapMs=250, maxVoices=1, preload=True, note='the moment the 40 mm becomes ready, and after every shot or clip when it can fire again')),
    P('ac130_int_ready_vulcan', lambda r, i: m_ready_vulcan(r), 1, 'pk', -15.0, 'veh', 'weapons', weight=5, plain=True, pad=0.1, tags=['ac130', 'interior', 'ready', 'vulcan'],
      play=dict(gapMs=300, maxVoices=1, preload=True, note='on selecting the Vulcan')),
    P('ac130_int_select_howitzer', lambda r, i: m_sel(523.25)(r), 1, 'pk', -27.0, 'ui', EXT, weight=3, plain=True, rate=(1.0, 1.0), pad=0.1, tags=['ac130', 'interior', 'beep'],
      play=dict(gapMs=150, maxVoices=1, preload=True, note='weapon-select tone 1 (C5)')),
    P('ac130_int_select_cannon', lambda r, i: m_sel(659.25)(r), 1, 'pk', -27.0, 'ui', EXT, weight=3, plain=True, rate=(1.0, 1.0), pad=0.1, tags=['ac130', 'interior', 'beep'],
      play=dict(gapMs=150, maxVoices=1, preload=True, note='weapon-select tone 2 (E5)')),
    P('ac130_int_select_vulcan', lambda r, i: m_sel(783.99)(r), 1, 'pk', -27.0, 'ui', EXT, weight=3, plain=True, rate=(1.0, 1.0), pad=0.1, tags=['ac130', 'interior', 'beep'],
      play=dict(gapMs=150, maxVoices=1, preload=True, note='weapon-select tone 3 (G5)')),
    P('ac130_int_losing_target', lambda r, i: m_losing(r), 1, 'pk', -25.0, 'ui', EXT, weight=3, plain=True, rate=(1.0, 1.0), pad=0.1, tags=['ac130', 'interior', 'cue'],
      play=dict(gapMs=3000, maxVoices=1, preload=True, note='when "Losing target" appears; repeat no faster than every 3 s while it stays')),
    P('ac130_int_lock', lambda r, i: m_lock(r), 1, 'pk', -25.0, 'ui', EXT, weight=3, plain=True, rate=(1.0, 1.0), pad=0.1, tags=['ac130', 'interior', 'cue'],
      play=dict(gapMs=1500, maxVoices=1, preload=True, note='when lock is acquired or regained')),
]


def save_pk(name, x, peak_db, bus, **kw):
    x = np.asarray(x, dtype=np.float64); x = x - np.mean(x); x = hp(x, 60, SR, 2)
    return S.save(name, x, bus, loop=False, peak=peak_db, target_lufs=None, **kw)


def render(only=None):
    S.set_manifest('ac130int')
    for e in TABLE:
        if only and not any(o in e['stem'] for o in only.split(',')): continue
        for i in range(e['count']):
            name = e['stem'] if (e['plain'] or e['count'] == 1 and e['stem'].endswith(('howitzer_hoist', 'howitzer_ram', 'howitzer_breech'))) else '%s_%02d' % (e['stem'], i + 1)
            r = rng(U.seed_of(e['stem'], i)); x = np.asarray(e['mk'](r, i), dtype=np.float64)
            kw = dict(variants=e['count'], group=e['group'], weight=e['weight'], max_dist=99999, rate=e['rate'], tags=e['tags'] + ['nonspatial'], quality=e['q'],
                      meta=dict(kind='interior', play=dict(e['play'], rotate=e['count'], bus=e['bus'])))
            if e['mode'] == 'rms':
                stage_save(name, x, e['lvl'], e['bus'], loop=e['loop'], **kw)
            else:
                x = np.concatenate([x, np.zeros(n_of(0.1))]); save_pk(name, x, e['lvl'], e['bus'], **kw)
        print('rendered', e['stem'], flush=True)


# ------------------------------------------------------------------ post-pass: trim dead tails, size/hints, deploy
def load(p):
    r = subprocess.run([S.FFMPEG, '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True)
    return np.frombuffer(r.stdout, dtype='<f4').astype(float)


def enc(x, p, q):
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tf: tmp = tf.name
    with wave.open(tmp, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    subprocess.run([S.FFMPEG, '-y', '-loglevel', 'error', '-i', tmp, '-c:a', 'libvorbis', '-q:a', str(q), p], check=True); os.remove(tmp)


def db(v): return 20 * math.log10(max(v, 1e-9))


def trim(frag):
    here = os.path.dirname(os.path.abspath(__file__)); qmap = {e['stem']: e['q'] for e in TABLE}
    for id_, m in frag.items():
        if m.get('loop'): continue
        p = os.path.join(here, 'out', id_ + '.ogg'); x = load(p)
        pk = np.max(np.abs(x)); thr = max(10 ** (-58 / 20), pk * 10 ** (-52 / 20))
        idx = np.nonzero(np.abs(x) > thr)[0]; end = min(len(x), (idx[-1] + int(0.012 * SR)) if len(idx) else len(x))
        if len(x) - end < int(0.02 * SR): continue
        y = x[:end].copy(); k = min(len(y), int(0.01 * SR)); y[-k:] *= np.cos(np.linspace(0, math.pi / 2, k)) ** 2
        q = qmap.get(re.sub(r'_\d\d$', '', id_), 4); enc(y, p, q); y = load(p)
        m['dur'] = round(len(y) / SR, 3); m['peakDb'] = round(db(np.max(np.abs(y))), 1); m['rmsDb'] = round(db(np.sqrt(np.mean(y ** 2))), 1)
        print('trimmed %-34s %.2f -> %.2f s' % (id_, len(x) / SR, len(y) / SR))


def deploy():
    here = os.path.dirname(os.path.abspath(__file__)); dst = os.path.join(os.path.dirname(here), 'audio')
    fp = os.path.join(here, 'out', 'manifest.ac130int.json'); frag = json.load(open(fp, encoding='utf-8'))
    trim(frag); json.dump(frag, open(fp, 'w', encoding='utf-8'), indent=1)
    mp = os.path.join(dst, 'manifest.json'); man = json.load(open(mp, encoding='utf-8'))
    for id_, e in frag.items():
        shutil.copy2(os.path.join(here, 'out', id_ + '.ogg'), os.path.join(dst, id_ + '.ogg')); man['assets'][id_] = e
    json.dump(man, open(mp, 'w', encoding='utf-8'))
    print('deployed %d ac130_int assets into %s' % (len(frag), dst))


if __name__ == '__main__':
    only = next((a for a in sys.argv[1:] if not a.startswith('--')), None)
    render(only)
    if '--no-deploy' not in sys.argv: deploy()
