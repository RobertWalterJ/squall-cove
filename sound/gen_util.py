"""Shared helpers for gen_water / gen_materials / gen_fire_electric (my own module; synthlib.py is untouched)."""
import zlib, math
import numpy as np
import synthlib as S
from synthlib import SR, rng, n_of, noise, lp, hp, bp, resonator, tv_filter, tv_bandpass, grains, make_loop

def seed_of(name, i=0):
    return (zlib.crc32(name.encode()) * 7 + (i + 1) * 1013) & 0xFFFFFFFF

def Z(dur): return np.zeros(n_of(dur))

def put(buf, x, t, g=1.0):
    s = int(t * SR)
    if s >= len(buf) or s < 0: return buf
    e = min(len(buf), s + len(x)); buf[s:e] += x[:e - s] * g
    return buf

def fit(x, dur):
    n = n_of(dur)
    return x[:n] if len(x) >= n else np.pad(x, (0, n - len(x)))

def edec(n, tau): return np.exp(-np.arange(n) / (tau * SR))

def bubble(r, f_lo, f_hi, dscale=1.0, rise=2.0):
    f0 = r.uniform(f_lo, f_hi); T = r.uniform(0.012, 0.06) * dscale; k = max(8, int(T * SR)); t = np.arange(k) / SR
    f = f0 * (1 + rise * t / T); ph = 2 * math.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / (T * 0.35)) * r.uniform(0.25, 1.0)

def bubble_cloud(dur, f_lo, f_hi, rate0, tau, r, dscale=1.0, rise=2.0, rate_min=0.0):
    return grains(dur, lambda t: rate0 * math.exp(-t / tau) + rate_min, lambda rr, i: bubble(rr, f_lo, f_hi, dscale, rise), r)

def burst(r, dur, lo=None, hi=None, tau=None, color='white'):
    n = n_of(dur); x = noise(n, color, r)
    if lo: x = hp(x, lo)
    if hi: x = lp(x, hi)
    return x * edec(n, tau or dur / 3)

def sweep(f0, f1, dur, tau=None, curve=1.0):
    n = n_of(dur); t = np.linspace(0, 1, n) ** curve; f = f0 + (f1 - f0) * t
    ph = 2 * math.pi * np.cumsum(f) / SR
    return np.sin(ph) * (edec(n, tau) if tau else 1.0)

def sine(f, dur, tau, ph0=0.0):
    t = np.arange(n_of(dur)) / SR; return np.sin(2 * math.pi * f * t + ph0) * np.exp(-t / tau)

def crack_grain(r, dur=0.004, lo=1500, hi=9000):
    k = max(8, int(dur * SR)); x = r.standard_normal(k) * np.exp(-np.arange(k) / (k * 0.3))
    return bp(x, lo, hi, SR, 1)

def ticks(dur, rate_fn, r, lo=1500, hi=8000, gdur=0.004, amp=lambda t: 1.0, spread=(0.3, 1.0)):
    def g(rr, i):
        c = rr.uniform(lo, hi); return crack_grain(rr, gdur * rr.uniform(.6, 1.6), c * .6, c * 1.4) * rr.uniform(*spread)
    return grains(dur, rate_fn, g, r, amp_fn=amp)

def pings(dur, rate_fn, r, flo, fhi, tau=0.05, amp=lambda t: 1.0, mat=None):
    def g(rr, i):
        f = rr.uniform(flo, fhi); k = int(tau * 6 * SR); t = np.arange(k) / SR
        y = np.sin(2 * math.pi * f * t) * np.exp(-t / tau)
        if mat: y = y + 0.4 * np.sin(2 * math.pi * f * mat * t) * np.exp(-t / (tau * .5))
        return y * rr.uniform(.2, 1)
    return grains(dur, rate_fn, g, r, amp_fn=amp)

def smooth(n, rate, r, depth=1.0): return S.smooth_random(n, rate, r, depth)

def loop_clean(x, fc=28.0, edge=0.003):
    """Circularly remove content below fc (so normalize()'s 20 Hz high-pass has no start transient), then fade the first/last
    few ms to zero so the wrap point is a true zero crossing (seam stays below the QA threshold even on clicky material)."""
    x = np.asarray(x, dtype=np.float64); ch = [x] if x.ndim == 1 else [x[:, c] for c in range(x.shape[1])]; out = []
    for v in ch:
        sp = np.fft.rfft(v); f = np.fft.rfftfreq(len(v), 1.0 / SR); sp *= np.clip((f - fc * 0.5) / (fc * 0.5), 0, 1) ** 2
        v = np.fft.irfft(sp, len(v)); k = int(edge * SR); w = np.sin(np.linspace(0, np.pi / 2, k)) ** 2
        v[:k] *= w; v[-k:] *= w[::-1]; out.append(v)
    return out[0] if x.ndim == 1 else np.stack(out, axis=1)


def loop_of(maker, dur=5.0, xf=0.5):
    """maker(total_dur) -> array; returns seamless loop of length dur."""
    x = maker(dur + xf)
    return loop_clean(make_loop(x, xf))

def stereo_loop(maker, dur=5.0, xf=0.5, seeds=(1, 2)):
    L = maker(dur + xf, rng(seeds[0])); R = maker(dur + xf, rng(seeds[1]))
    return loop_clean(make_loop(np.stack([L, R], axis=1), xf))

def jit(r, v, pct=0.08): return v * (1 + r.uniform(-pct, pct))
