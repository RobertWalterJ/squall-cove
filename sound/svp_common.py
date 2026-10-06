"""Shared helpers for gen_vehicles / gen_people / gen_ui_music (does not modify synthlib)."""
import math
import numpy as np
from scipy import signal
import synthlib as S

SR = S.SR
TWO_PI = 2 * math.pi


def fit(x, n):
    x = np.asarray(x, dtype=np.float64)
    if len(x) >= n:
        return x[:n]
    return np.concatenate([x, np.zeros(n - len(x))])


def r32(x):
    """44.1 kHz -> 32 kHz (polyphase, for small one-shots). Returns float64."""
    return signal.resample_poly(np.asarray(x, dtype=np.float64), 320, 441, axis=0)


def r32_circ(x):
    """Circular (FFT) resample 44.1 -> 32 kHz so loops stay perfectly periodic."""
    n = x.shape[0]
    m = int(round(n * 32000 / 44100))
    return signal.resample(x, m, axis=0)


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12.0)


def place(buf, x, t, gain=1.0, sr=SR):
    """Add x into buf at time t (s); clips at the end."""
    s0 = int(round(t * sr))
    if s0 >= len(buf):
        return buf
    n = min(len(x), len(buf) - s0)
    buf[s0:s0 + n] += x[:n] * gain
    return buf


def circ_place(buf, x, t, gain=1.0, sr=SR):
    """Add x into a circular buffer (wraps around) so loops stay seamless."""
    n = len(buf)
    s0 = int(round(t * sr)) % n
    k = len(x)
    i = 0
    while i < k:
        m = min(k - i, n - s0)
        buf[s0:s0 + m] += x[i:i + m] * gain
        i += m
        s0 = (s0 + m) % n
    return buf


def echo(x, rt60=1.0, wet=0.3, seed=1, damping=0.7, size=0.6, pre=0.02):
    """Mono outdoor/room echo tail via synthetic IR. Output is longer than input by the tail."""
    ir = S.reverb_ir(rt60, size, damping, SR, seed, pre, stereo=False)[:, 0]
    w = signal.fftconvolve(x, ir)
    d = np.pad(x, (0, len(w) - len(x)))
    return d * (1 - wet) + w * wet * (np.max(np.abs(d)) / (np.max(np.abs(w)) + 1e-9))


def circ_reverb(x, rt60=3.0, wet=0.4, seed=5, damping=0.7, stereo=True):
    """Circular convolution reverb: tail wraps around so a loop stays seamless. x is (n,) or (n,2)."""
    n = x.shape[0]
    ir = S.reverb_ir(rt60, 0.8, damping, SR, seed, 0.02, stereo=True)
    ir = ir[:min(len(ir), n)]
    ir = ir / np.sqrt(np.sum(ir ** 2, axis=0, keepdims=True))
    xs = x if x.ndim == 2 else np.stack([x, x], axis=1)
    out = np.zeros_like(xs)
    for c in range(xs.shape[1]):
        irc = np.zeros(n); irc[:len(ir)] = ir[:, c % ir.shape[1]]
        out[:, c] = np.fft.irfft(np.fft.rfft(xs[:, c]) * np.fft.rfft(irc), n)
    out *= (np.std(xs) / (np.std(out) + 1e-9))
    return xs * (1 - wet) + out * wet


def pnoise(n, shape_fn, r, sr=SR):
    """Exactly periodic (over n samples) noise with spectral magnitude shape_fn(f_hz). Unit std."""
    f = np.fft.rfftfreq(n, 1.0 / sr)
    mag = shape_fn(f)
    sp = mag * np.exp(1j * r.uniform(0, TWO_PI, len(f)))
    sp[0] = 0
    x = np.fft.irfft(sp, n)
    return x / (np.std(x) + 1e-12)


def band_shape(lo, hi, slope=0.0, order=2):
    """Magnitude shape: bandpass lo..hi with spectral slope in dB/oct (negative darker)."""
    def fn(f):
        f = np.maximum(f, 1.0)
        m = (1 / (1 + (lo / f) ** (2 * order))) * (1 / (1 + (f / hi) ** (2 * order)))
        return np.sqrt(m) * (f / 1000.0) ** (slope / 6.0206)
    return fn


def tv_res(x, f, q, block=128, sr=SR):
    """Time-varying resonant band-pass (unity peak). f array (len x) or scalar."""
    n = len(x); out = np.zeros(n)
    f = np.broadcast_to(np.asarray(f, dtype=np.float64), (n,))
    zi = np.zeros(2)
    for s0 in range(0, n, block):
        s1 = min(n, s0 + block)
        fc = float(np.mean(f[s0:s1])); fc = min(max(fc, 20.0), sr * 0.45)
        w0 = TWO_PI * fc / sr; al = math.sin(w0) / (2 * q); c = math.cos(w0)
        b = np.array([al, 0, -al]) / (1 + al); a = np.array([1, -2 * c / (1 + al), (1 - al) / (1 + al)])
        y, zi = signal.lfilter(b, a, x[s0:s1], zi=zi)
        out[s0:s1] = y
    return out


# ------------------------------------------------------------------ vocal tract
VOW = {
    'a': (730, 1090, 2440), 'e': (530, 1840, 2480), 'i': (270, 2290, 3010), 'o': (570, 840, 2410),
    'u': (300, 870, 2240), 'ae': (660, 1720, 2410), 'uh': (640, 1190, 2390), 'er': (490, 1350, 1690),
    'oo': (390, 1100, 2400),
}
BW = (90, 110, 170, 250)
FAMP = (1.0, 0.7, 0.45, 0.2)


def glottal(f0, n, r, tilt=1.5, fmax=6500, jitter=0.006, sr=SR):
    """Band-limited harmonic glottal source. f0: scalar or array (Hz)."""
    f0 = np.broadcast_to(np.asarray(f0, dtype=np.float64), (n,)).copy()
    f0 *= 1 + jitter * S.lp(r.standard_normal(n), 30, sr, 1) * 4
    ph = TWO_PI * np.cumsum(f0) / sr
    y = np.zeros(n)
    hmax = int(fmax / max(np.min(f0), 40.0))
    for h in range(1, min(hmax, 80) + 1):
        a = h ** -tilt
        y += a * np.sin(h * ph + r.uniform(0, TWO_PI)) * (h * f0 < fmax)
    return y / (np.max(np.abs(y)) + 1e-9)


def vocal(f0, dur, formants, r, breath=0.1, tilt=1.5, bwscale=1.0, env=None, sr=SR, block=128):
    """Voiced sound through a parallel formant bank. formants: list of 3 tuples/arrays (F1,F2,F3) or (3,) per-sample arrays."""
    n = S.n_of(dur, sr)
    src = glottal(f0, n, r, tilt, sr=sr)
    asp = S.noise(n, 'white', r)
    ex = src + breath * asp
    F = [np.broadcast_to(np.asarray(fv, dtype=np.float64), (n,)) for fv in formants]
    y = np.zeros(n)
    for i, fv in enumerate(F):
        bw = BW[i] * bwscale
        y += FAMP[i] * tv_res(ex, fv, np.mean(fv) / bw, block, sr)
    y += FAMP[3] * 0.5 * tv_res(ex, 3600, 3600 / BW[3], block, sr)
    if env is not None:
        y = y * env
    return S.lp(y, 6500, sr, 2)


def syllable(f0, dur, vowel, r, breath=0.08, sr=SR, glide=0.0):
    """Short voiced syllable with fixed formants (fast, for murmur/laugh)."""
    n = S.n_of(dur, sr)
    f = f0 * (1 + glide * np.linspace(0, 1, n))
    src = glottal(f, n, r, 1.5, sr=sr) + breath * S.noise(n, 'white', r)
    F = VOW[vowel] if isinstance(vowel, str) else vowel
    y = np.zeros(n)
    for i, fv in enumerate(F):
        y += FAMP[i] * S.resonator(src, fv * r.uniform(0.96, 1.04), fv / BW[i], sr)
    e = np.sin(np.linspace(0, math.pi, n)) ** 1.5
    return y * e


def dom_freq(x, lo, hi, sr=SR):
    """Frequency of the strongest FFT bin between lo and hi Hz (Hann window, zero padded for resolution)."""
    xm = x if x.ndim == 1 else x.mean(axis=1)
    N = 1 << int(math.ceil(math.log2(len(xm) * 4)))
    sp = np.abs(np.fft.rfft(xm * np.hanning(len(xm)), N))
    f = np.fft.rfftfreq(N, 1.0 / sr)
    m = (f >= lo) & (f <= hi)
    return float(f[m][np.argmax(sp[m])])


def centroid(x, sr=SR):
    xm = x if x.ndim == 1 else x.mean(axis=1)
    f, p = signal.welch(xm, sr, nperseg=min(4096, len(xm)))
    return float((f * p).sum() / (p.sum() + 1e-18))


def hf_ratio(x, split=8000, sr=SR):
    xm = x if x.ndim == 1 else x.mean(axis=1)
    f, p = signal.welch(xm, sr, nperseg=min(4096, len(xm)))
    return float(p[f > split].sum() / (p.sum() + 1e-18))


def band_ratio(x, lo, hi, sr=SR):
    xm = x if x.ndim == 1 else x.mean(axis=1)
    f, p = signal.welch(xm, sr, nperseg=min(4096, len(xm)))
    return float(p[(f >= lo) & (f <= hi)].sum() / (p.sum() + 1e-18))


# ------------------------------------------------------------------ musical notes
def soft_note(f, dur, kind='bell', vel=1.0, decay=None, sr=SR, r=None):
    """Soft pitched note. kinds: bell (sine + inharmonic-ish partials), marimba (sine + 4x quick), tri (triangle-ish), sine."""
    n = S.n_of(dur, sr); t = np.arange(n) / sr
    r = r or S.rng(int(f * 10))
    if kind == 'bell':
        dc = decay or dur * 0.35
        parts = [(1.0, 1.0, dc), (2.0, 0.28, dc * 0.55), (2.76, 0.12, dc * 0.35), (4.1, 0.05, dc * 0.2)]
        y = sum(a * np.sin(TWO_PI * f * k * t + r.uniform(0, 6.28)) * np.exp(-t / d) for k, a, d in parts if f * k < 12000)
        at = 0.003
    elif kind == 'marimba':
        dc = decay or 0.22
        y = np.sin(TWO_PI * f * t) * np.exp(-t / dc) + 0.35 * np.sin(TWO_PI * f * 3.9 * t) * np.exp(-t / (dc * 0.12)) \
            + 0.12 * np.sin(TWO_PI * f * 9.2 * t) * np.exp(-t / (dc * 0.05))
        at = 0.002
    elif kind == 'tri':
        dc = decay or dur * 0.4
        y = sum(((-1) ** ((h - 1) // 2)) / h ** 2 * np.sin(TWO_PI * f * h * t) for h in (1, 3, 5, 7)) * np.exp(-t / dc)
        at = 0.01
    else:
        dc = decay or dur * 0.4
        y = np.sin(TWO_PI * f * t) * np.exp(-t / dc)
        at = 0.006
    y = y * S.env_attack(n, at, sr)
    return y * vel


def tick(dur=0.012, lo=2000, hi=5000, r=None, sr=SR, level=1.0):
    r = r or S.rng(7)
    n = S.n_of(dur, sr)
    x = r.standard_normal(n) * np.exp(-np.arange(n) / (n * 0.22))
    return S.bp(x, lo, hi, sr, 1) * level


def winch_loop(dur, r, clicks_per_s=12, motor=90.0, level=1.0):
    """Winch/ratchet loop (periodic over dur: clicks and motor both integer per loop)."""
    n = S.n_of(dur)
    t = np.arange(n) / SR
    cps = round(clicks_per_s * dur) / dur
    mot = round(motor * dur) / dur
    saw = sum(np.sin(TWO_PI * mot * h * t + r.uniform(0, 6.28)) / h for h in range(1, 12))
    saw = S.lp(saw, 700, SR, 2) * (1 + 0.15 * np.sin(TWO_PI * 2 * t / dur * 2))
    y = np.zeros(n)
    for k in range(int(cps * dur)):
        tk = k / cps
        c = S.impact('iron', r.uniform(1400, 1900), 0.12, 0.9, 0.09, seed=k + 3)
        circ_place(y, c, tk, r.uniform(0.7, 1.0))
    rumble = pnoise(n, band_shape(60, 600, -3), r) * 0.25
    return (y * 0.9 + saw * 0.55 + rumble) * level


def seal(x):
    """Rotate a (seamless, circular) loop so that its first and last samples both sit near zero at a flat spot.
    The loop is continuous across the rotation point (it is circular), and the file-level seam (last vs first sample)
    becomes tiny, which also keeps the 20 Hz high-pass start-up transient in synthlib.normalize negligible."""
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean(axis=0)
    a = np.abs(x / (x.std(axis=0) + 1e-12))
    if a.ndim == 2:
        a = a.max(axis=1)
    cost = a + np.roll(a, 1)
    s = int(np.argmin(cost))
    return np.roll(x, -s, axis=0)


def trim(x, dur, fade=0.15, sr=SR):
    """Crop to dur seconds with a smooth fade-out over the last `fade` seconds."""
    n = S.n_of(dur, sr)
    x = np.asarray(x, dtype=np.float64)[:n]
    k = min(S.n_of(fade, sr), len(x))
    e = np.ones(len(x)); e[len(x) - k:] = np.cos(np.linspace(0, math.pi / 2, k)) ** 2
    return x * (e[:, None] if x.ndim == 2 else e)
