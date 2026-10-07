"""Shared helpers for gen_weapons / gen_weapons_move / gen_weapons_amb (synthlib, gen_util and svp_common are untouched)."""
import math
import numpy as np
from scipy import signal
import synthlib as S
import gen_util as U
import svp_common as C

SR = S.SR
TWO_PI = 2 * math.pi
rng, n_of, noise = S.rng, S.n_of, S.noise
lp, hp, bp = S.lp, S.hp, S.bp
put, edec = U.put, U.edec


def fit(x, n):
    """Pad or trim to exactly n SAMPLES (gen_util.fit takes seconds)."""
    x = np.asarray(x, dtype=np.float64)
    return x[:n] if len(x) >= n else np.pad(x, (0, n - len(x)))


def save(name, x, bus, group, **kw):
    kw.setdefault('lazy', True); kw.setdefault('weight', 1.0); kw.setdefault('quality', 4)
    if kw.get('loop'):
        x = U.loop_clean(x)
    return S.save(name, x, bus, group=group, **kw)


def fam(prefix, count, maker, bus, group, **kw):
    """Render count numbered variants (a single variant keeps the plain name). maker(r, i) -> array, r seeded from the stem name so reruns are identical."""
    tags = kw.pop('tags', [prefix])
    for i in range(count):
        save(prefix if count == 1 else '%s_%02d' % (prefix, i + 1), maker(rng(U.seed_of(prefix, i)), i), bus, group, variants=count, tags=tags, **kw)


def thump(n, f, tau, level=1.0, drop=0.3):
    t = np.arange(n) / SR
    return np.sin(TWO_PI * f * t * (1 - drop * np.exp(-t / 0.02))) * np.exp(-t / tau) * level


def tickn(r, dur=0.006, lo=1500, hi=6000, level=1.0, n=None):
    k = max(8, int(dur * SR * 6)); x = r.standard_normal(k) * np.exp(-np.arange(k) / (dur * SR))
    x = bp(x, lo, hi, SR, 2) * level
    return x if n is None else fit(x, n)


def pingn(f, tau, dur=None, partials=((1, 1.0, 1.0),), ph=None, r=None):
    """Sum of decaying sines. partials: (ratio, amp, tau scale)."""
    dur = dur or tau * 7; n = n_of(dur); t = np.arange(n) / SR; y = np.zeros(n)
    for k, a, ts in partials:
        if f * k > SR * 0.45: continue
        p0 = 0.0 if r is None else r.uniform(0, TWO_PI)
        y += a * np.sin(TWO_PI * f * k * t + p0) * np.exp(-t / (tau * ts))
    return y


def brass_note(f, dur, att=0.03, rel=0.15, bright=1.0, vib=0.0, r=None):
    """Synthetic brass: sawtooth-ish harmonic stack, filter that opens with the attack."""
    r = r or rng(int(f))
    n = n_of(dur); t = np.arange(n) / SR
    fv = f * (1 + vib * 0.006 * np.sin(TWO_PI * 5.2 * t) * np.clip(t / 0.4, 0, 1))
    ph = TWO_PI * np.cumsum(fv) / SR; y = np.zeros(n)
    for h in range(1, 14):
        if f * h > 9000: break
        y += (1.0 / h ** 0.9) * np.sin(h * ph + r.uniform(0, TWO_PI))
    cut = f * (2.0 + 4.0 * bright * (1 - np.exp(-t / (att * 2.0 + 0.04))))
    y = S.tv_filter(y, np.minimum(cut, 7000), 'lp', 2, SR, 256)
    return y * S.env_adsr(n, att, 0.08, 0.8, rel)


def pad_note(f, dur, att=0.2, rel=0.5, bright=0.5):
    n = n_of(dur); t = np.arange(n) / SR; y = np.zeros(n)
    for dt in (-0.004, 0.0, 0.004):
        y += np.sin(TWO_PI * f * (1 + dt) * t) + 0.5 * np.sin(TWO_PI * 2 * f * (1 + dt) * t) * bright + 0.25 * np.sin(TWO_PI * 3 * f * (1 + dt) * t) * bright
    return y * S.env_adsr(n, att, 0.2, 0.85, rel) / 3.0


def timpani(f=90.0, dur=1.2, level=1.0, r=None):
    r = r or rng(3); n = n_of(dur); t = np.arange(n) / SR
    y = np.sin(TWO_PI * f * t * (1 + 0.25 * np.exp(-t / 0.05))) * np.exp(-t / 0.35)
    y += 0.4 * np.sin(TWO_PI * f * 1.5 * t) * np.exp(-t / 0.2) + 0.25 * np.sin(TWO_PI * f * 2.0 * t) * np.exp(-t / 0.15)
    y += lp(noise(n, 'white', r), 1500) * np.exp(-t / 0.012) * 0.5
    return y * level


def mix(dur, parts):
    """parts: list of (array, time, gain)."""
    buf = np.zeros(n_of(dur))
    for x, t, g in parts: put(buf, x, t, g)
    return buf


def fade_out(x, frac=0.12):
    k = max(8, int(len(x) * frac)); x = x.copy(); x[-k:] *= np.cos(np.linspace(0, math.pi / 2, k)) ** 2
    return x


def sumv(*xs):
    """Sum arrays of different lengths (zero padded to the longest)."""
    n = max(len(x) for x in xs); out = np.zeros(n)
    for x in xs: out[:len(x)] += x
    return out
