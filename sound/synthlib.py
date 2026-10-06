"""Squall Cove procedural sound toolkit (numpy + scipy).

Everything here is deterministic given a seed. Generators build float32 arrays in [-1, 1]; `save()` writes Ogg Vorbis via ffmpeg and
records an entry in a manifest fragment. See ../SOUND-DESIGN.md for what each family needs to be.
"""
import os, json, math, subprocess, tempfile, wave
import numpy as np
from scipy import signal

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
os.makedirs(OUT, exist_ok=True)
try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG = 'ffmpeg'


def rng(seed=0):
    return np.random.default_rng(int(seed) & 0xFFFFFFFF)


def n_of(dur, sr=SR):
    return int(round(dur * sr))


def tt(dur, sr=SR):
    return np.arange(n_of(dur, sr)) / sr


# ------------------------------------------------------------------ noise
def noise(n, kind='white', r=None):
    r = r or rng(1)
    w = r.standard_normal(n).astype(np.float64)
    if kind == 'white':
        return w
    spec = np.fft.rfft(w)
    f = np.fft.rfftfreq(n, 1.0)
    f[0] = f[1] if len(f) > 1 else 1.0
    if kind == 'pink':
        spec = spec / np.sqrt(f / f[1])
    elif kind == 'brown':
        spec = spec / (f / f[1])
    elif kind == 'blue':
        spec = spec * np.sqrt(f / f[1])
    elif kind == 'violet':
        spec = spec * (f / f[1])
    x = np.fft.irfft(spec, n)
    return x / (np.std(x) + 1e-12)


# ------------------------------------------------------------------ filters
def _sos(kind, fc, sr, order=2, q=None):
    nyq = sr / 2.0
    if kind in ('lp', 'hp'):
        fc = min(max(fc, 5.0), nyq * 0.98)
        return signal.butter(order, fc / nyq, btype='low' if kind == 'lp' else 'high', output='sos')
    if kind == 'bp':
        lo, hi = fc
        lo = min(max(lo, 5.0), nyq * 0.9); hi = min(max(hi, lo * 1.05), nyq * 0.98)
        return signal.butter(order, [lo / nyq, hi / nyq], btype='band', output='sos')
    raise ValueError(kind)


def lp(x, fc, sr=SR, order=2): return signal.sosfilt(_sos('lp', fc, sr, order), x)
def hp(x, fc, sr=SR, order=2): return signal.sosfilt(_sos('hp', fc, sr, order), x)
def bp(x, lo, hi, sr=SR, order=2): return signal.sosfilt(_sos('bp', (lo, hi), sr, order), x)


def peak_eq(x, f0, q, gain_db, sr=SR):
    """RBJ peaking biquad."""
    A = 10 ** (gain_db / 40.0); w0 = 2 * math.pi * f0 / sr; al = math.sin(w0) / (2 * q); c = math.cos(w0)
    b = [1 + al * A, -2 * c, 1 - al * A]; a = [1 + al / A, -2 * c, 1 - al / A]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x)


def resonator(x, f0, q=20.0, sr=SR):
    """Narrow band-pass (constant skirt gain) biquad, unity peak."""
    w0 = 2 * math.pi * f0 / sr; al = math.sin(w0) / (2 * q)
    b = [al, 0, -al]; a = [1 + al, -2 * math.cos(w0), 1 - al]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x)


def tv_filter(x, cutoff, kind='lp', order=2, sr=SR, block=512):
    """Time-varying Butterworth: `cutoff` is an array the length of x (Hz) or a scalar. Zi state carried between blocks."""
    n = len(x); out = np.zeros(n)
    cutoff = np.broadcast_to(np.asarray(cutoff, dtype=np.float64), (n,))
    zi = None
    for s0 in range(0, n, block):
        s1 = min(n, s0 + block); fc = float(np.mean(cutoff[s0:s1]))
        sos = _sos(kind, fc, sr, order)
        if zi is None or zi.shape[0] != sos.shape[0]:
            zi = np.zeros((sos.shape[0], 2))
        y, zi = signal.sosfilt(sos, x[s0:s1], zi=zi)
        out[s0:s1] = y
    return out


def tv_bandpass(x, center, width_oct=1.0, order=2, sr=SR, block=512):
    n = len(x); out = np.zeros(n); center = np.broadcast_to(np.asarray(center, dtype=np.float64), (n,)); zi = None
    for s0 in range(0, n, block):
        s1 = min(n, s0 + block); fc = float(np.mean(center[s0:s1]))
        lo = fc / (2 ** (width_oct / 2)); hi = fc * (2 ** (width_oct / 2))
        sos = _sos('bp', (lo, hi), sr, order)
        if zi is None or zi.shape[0] != sos.shape[0]:
            zi = np.zeros((sos.shape[0], 2))
        y, zi = signal.sosfilt(sos, x[s0:s1], zi=zi); out[s0:s1] = y
    return out


def spectral_tilt(x, db_per_oct):
    """Apply a spectral slope in the FFT domain (positive tilts brighten)."""
    n = len(x); sp = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1.0 / SR); f[0] = 1.0
    g = (f / 1000.0) ** (db_per_oct / 6.0206)
    return np.fft.irfft(sp * g, n)


# ------------------------------------------------------------------ envelopes
def env_exp(n, tau, sr=SR):
    return np.exp(-np.arange(n) / (tau * sr))


def env_attack(n, a, sr=SR):
    e = np.ones(n); k = min(n, max(1, int(a * sr)))
    e[:k] = np.linspace(0, 1, k) ** 2
    return e


def env_adsr(n, a, d, s, r, sr=SR):
    e = np.ones(n); ia = int(a * sr); idd = int(d * sr); ir = int(r * sr)
    ia = min(ia, n); e[:ia] = np.linspace(0, 1, max(ia, 1))
    d_end = min(n, ia + idd)
    if d_end > ia: e[ia:d_end] = np.linspace(1, s, d_end - ia)
    e[d_end:] = s
    if ir > 0 and ir < n: e[n - ir:] *= np.linspace(1, 0, ir)
    return e


def smooth_random(n, rate_hz, r=None, depth=1.0, sr=SR):
    """Low-rate smooth modulation in [0,1] (used for gusts, swells, flicker)."""
    r = r or rng(2); k = max(4, int(n / sr * rate_hz) + 4)
    pts = r.random(k); xs = np.linspace(0, n - 1, k)
    cs = np.interp(np.arange(n), xs, pts)
    w = int(sr / max(rate_hz, 0.01) * 0.25) | 1
    cs = np.convolve(cs, np.hanning(w) / np.hanning(w).sum(), mode='same')
    cs = (cs - cs.min()) / (cs.max() - cs.min() + 1e-9)
    return 1.0 - depth + depth * cs


# ------------------------------------------------------------------ modal synthesis
MODES = {
    # ratios, decays (s at size=1), amps, brightness bias
    'wood':   ([1, 2.35, 3.7, 5.4, 7.9, 11.0], [0.16, 0.11, 0.07, 0.05, 0.035, 0.02], [1, .7, .55, .35, .22, .12]),
    'plank':  ([1, 2.1, 3.3, 4.9, 7.2], [0.28, 0.2, 0.12, 0.08, 0.05], [1, .8, .5, .35, .2]),
    'barrel': ([1, 1.94, 2.9, 4.3, 6.2], [0.35, 0.22, 0.15, 0.09, 0.06], [1, .8, .5, .35, .2]),
    'stone':  ([1, 1.58, 2.61, 3.92, 5.74, 8.1], [0.09, 0.06, 0.045, 0.03, 0.02, 0.012], [1, .6, .5, .4, .3, .2]),
    'steel':  ([1, 2.76, 5.40, 8.93, 13.34, 18.6], [1.4, 1.0, 0.65, 0.42, 0.26, 0.15], [1, .8, .55, .4, .28, .18]),
    'iron':   ([1, 2.45, 4.1, 6.6, 9.7], [0.7, 0.45, 0.3, 0.2, 0.12], [1, .7, .5, .35, .2]),
    'glass':  ([1, 2.32, 4.25, 6.63, 9.38, 12.6], [0.9, 0.65, 0.45, 0.32, 0.22, 0.14], [1, .75, .55, .4, .3, .2]),
    'ice':    ([1, 2.1, 3.45, 5.2, 7.4], [0.35, 0.22, 0.14, 0.09, 0.05], [1, .65, .5, .35, .22]),
    'ceramic':([1, 2.65, 4.8, 7.4, 10.6], [0.5, 0.33, 0.2, 0.13, 0.08], [1, .7, .5, .35, .2]),
    'bell':   ([1, 2.0, 2.4, 3.0, 4.07, 5.4, 6.8], [4.0, 3.2, 2.6, 2.0, 1.4, 1.0, 0.7], [1, .9, .7, .6, .45, .3, .2]),
    'plastic':([1, 1.8, 2.9, 4.4], [0.1, 0.07, 0.05, 0.03], [1, .6, .4, .25]),
}


def modal(f0, material='wood', dur=1.0, size=1.0, bright=1.0, detune=0.01, r=None, sr=SR, amp_jitter=0.2):
    """Sum of damped sinusoids. `size` stretches decays, `bright` weights upper modes."""
    r = r or rng(3); ratios, decays, amps = MODES[material]
    n = n_of(dur, sr); t = np.arange(n) / sr; y = np.zeros(n)
    for k, (rt, dc, am) in enumerate(zip(ratios, decays, amps)):
        f = f0 * rt * (1 + r.uniform(-detune, detune))
        if f > sr * 0.45: continue
        a = am * (bright ** (k * 0.5)) * (1 + r.uniform(-amp_jitter, amp_jitter))
        y += a * np.exp(-t / max(dc * size, 1e-3)) * np.sin(2 * math.pi * f * t + r.uniform(0, 6.283))
    return y


def strike_noise(n, dur=0.01, color='white', r=None, sr=SR):
    """Short noise burst used as the contact transient of a strike."""
    r = r or rng(4); x = noise(n, color, r); k = max(2, int(dur * sr)); e = np.zeros(n); e[:k] = np.exp(-np.arange(k) / (k * 0.35)); return x * e


def impact(material='wood', f0=300.0, size=1.0, hardness=0.5, dur=0.8, seed=0, sr=SR, thump=0.0):
    """A struck object. hardness raises the bright transient; thump adds a low-frequency body hit."""
    r = rng(seed); n = n_of(dur, sr)
    y = modal(f0, material, dur, size, bright=0.8 + hardness * 0.6, r=r, sr=sr)
    tr = strike_noise(n, 0.004 + 0.01 * (1 - hardness), 'white', r, sr)
    tr = hp(tr, 800 + 4000 * hardness, sr) if hardness > 0.2 else lp(tr, 2500, sr)
    out = y * 0.7 + tr * (0.35 + 0.5 * hardness)
    if thump > 0:
        tb = np.arange(n) / sr; f = 55 + 40 * (1 - size * 0.3)
        out += thump * np.sin(2 * math.pi * f * tb * (1 - 0.35 * np.exp(-tb * 30))) * np.exp(-tb / (0.06 + 0.05 * size))
    return out


# ------------------------------------------------------------------ granular
def grains(dur, rate_fn, grain_fn, r=None, sr=SR, amp_fn=None):
    """Scatter grains at a time-varying density. rate_fn(t)->events/s, grain_fn(r, idx)->array. amp_fn(t)->gain."""
    r = r or rng(5); n = n_of(dur, sr); out = np.zeros(n + sr); t = 0.0; i = 0
    while t < dur:
        rate = max(0.01, float(rate_fn(t)))
        t += r.exponential(1.0 / rate)
        if t >= dur: break
        g = grain_fn(r, i); s0 = int(t * sr); a = 1.0 if amp_fn is None else float(amp_fn(t))
        out[s0:s0 + len(g)] += g * a; i += 1
    return out[:n]


def click_grain(r, i, f_lo=800, f_hi=6000, dur=0.01, sr=SR):
    k = int(dur * sr * r.uniform(0.6, 1.4)); x = r.standard_normal(k) * np.exp(-np.arange(k) / (k * 0.25))
    return bp(x, r.uniform(f_lo, f_hi * 0.5), r.uniform(f_hi * 0.5, f_hi), sr, 1) * r.uniform(0.3, 1.0)


def ping_grain(r, i, f_lo=1200, f_hi=6000, dur=0.08, sr=SR):
    f = r.uniform(f_lo, f_hi); k = int(dur * sr * r.uniform(0.5, 1.5)); t = np.arange(k) / sr
    return np.sin(2 * math.pi * f * t) * np.exp(-t / (dur * 0.3)) * r.uniform(0.2, 1.0)


def bubble_grain(r, i, f_lo=300, f_hi=3000, sr=SR):
    f0 = r.uniform(f_lo, f_hi); k = int(r.uniform(0.012, 0.06) * sr); t = np.arange(k) / sr
    f = f0 * (1 + 2.0 * t / (k / sr)); ph = 2 * math.pi * np.cumsum(f) / sr
    return np.sin(ph) * np.exp(-t / (k / sr * 0.35)) * r.uniform(0.2, 1.0)


# ------------------------------------------------------------------ engines and tonal
def engine(rpm, cyl=4, dur=4.0, seed=0, sr=SR, rough=0.25, exhaust=0.6, whine=0.0, load=0.5, stroke=4):
    """Combustion engine: firing-rate harmonic stack plus pulsed exhaust noise. rpm may be a scalar or an array (len n)."""
    r = rng(seed); n = n_of(dur, sr); rpm_a = np.broadcast_to(np.asarray(rpm, dtype=np.float64), (n,))
    f_fire = rpm_a / 60.0 * cyl / (2.0 if stroke == 4 else 1.0)
    ph = 2 * math.pi * np.cumsum(f_fire) / sr; y = np.zeros(n)
    for h in range(1, 14):
        a = (1.0 / h ** (1.1 - 0.4 * load)) * (1 + 0.3 * math.sin(h * 1.7))
        y += a * np.sin(h * ph + r.uniform(0, 6.283))
    pulse = np.maximum(0, np.sin(ph)) ** (3 + 4 * (1 - load))
    ex = lp(noise(n, 'pink', r), 600 + 1800 * load, sr) * pulse * exhaust
    jit = lp(noise(n, 'white', r), 40, sr) * rough
    y = y * (1 + jit) + ex * 1.5
    y += 0.25 * lp(noise(n, 'brown', r), 160, sr)
    if whine:
        fw = rpm_a / 60.0 * 7.0; y += whine * np.sin(2 * math.pi * np.cumsum(fw) / sr) * 0.3
    return y


def tone(f, dur, sr=SR, harmonics=(1.0,), decay=None, attack=0.005):
    t = np.arange(n_of(dur, sr)) / sr; y = np.zeros_like(t)
    f = np.broadcast_to(np.asarray(f, dtype=np.float64), t.shape); ph = 2 * math.pi * np.cumsum(f) / sr
    for h, a in enumerate(harmonics, start=1): y += a * np.sin(h * ph)
    e = env_attack(len(t), attack, sr)
    if decay: e = e * np.exp(-t / decay)
    return y * e


# ------------------------------------------------------------------ space
def reverb_ir(rt60=1.2, size=0.5, damping=0.6, sr=SR, seed=11, pre=0.01, stereo=True):
    """Synthetic impulse response: exponentially decaying filtered noise with early reflections."""
    r = rng(seed); n = n_of(rt60 * 1.3 + pre, sr); chans = []
    for c in range(2 if stereo else 1):
        x = noise(n, 'white', r); t = np.arange(n) / sr
        dec = np.exp(-6.9078 * t / rt60)
        # damping: high frequencies decay faster
        lo = lp(x, 6000 * (1 - 0.7 * damping), sr) * dec
        hi = hp(x, 6000 * (1 - 0.7 * damping), sr) * dec * np.exp(-t * 4 * damping)
        h = lo + 0.5 * hi
        er = np.zeros(n)
        for k in range(8):
            d = int((pre + (0.006 + 0.03 * size) * (k + r.random())) * sr)
            if d < n: er[d] += r.uniform(0.3, 0.9) * (-1) ** k
        h = h * 0.6 + er * 0.8; h[:int(pre * sr)] = 0; chans.append(h)
    ir = np.stack(chans, axis=1) if stereo else np.stack(chans, axis=1)
    return ir / (np.max(np.abs(ir)) + 1e-9)


def convolve(x, ir, wet=0.3):
    """Mono in -> stereo out via fftconvolve against a (n, 2) IR (or mono IR)."""
    if ir.ndim == 1: ir = ir[:, None]
    wetm = np.stack([signal.fftconvolve(x, ir[:, c])[:len(x) + len(ir) - 1] for c in range(ir.shape[1])], axis=1)
    dry = np.stack([np.pad(x, (0, len(wetm) - len(x)))] * ir.shape[1], axis=1)
    return dry * (1 - wet) + wetm * wet


def stereo_from_mono(x, width=0.5, r=None, delay_ms=12.0, sr=SR):
    """Pseudo-stereo by complementary all-pass-ish decorrelation (short delay + opposite filtering)."""
    d = int(delay_ms * sr / 1000.0); L = x.copy(); R = np.roll(x, d)
    Lb = lp(L, 3000, sr); Rb = lp(R, 3000, sr)
    L = L + width * (Lb - Rb) * 0.5; R = R - width * (Lb - Rb) * 0.5
    return np.stack([L, R], axis=1)


def decorrelated_stereo(n, maker, seeds=(1, 2)):
    return np.stack([maker(rng(seeds[0])), maker(rng(seeds[1]))], axis=1)


# ------------------------------------------------------------------ loops
def make_loop(x, xfade=0.5, sr=SR):
    """Equal-power crossfade of the tail onto the head so the file loops seamlessly. Shortens the clip by xfade seconds."""
    k = int(xfade * sr); n = x.shape[0]
    if k * 2 >= n: k = n // 4
    head = x[:k]; tail = x[n - k:]
    w = np.linspace(0, math.pi / 2, k)
    if x.ndim == 2: w = w[:, None]
    fade = head * np.sin(w) + tail * np.cos(w)
    return np.concatenate([fade, x[k:n - k]], axis=0)


def seam_db(x):
    """Discontinuity at the loop point relative to typical sample-to-sample change (dBFS of the jump)."""
    a = x[-1] if x.ndim == 1 else x[-1].mean(); b = x[0] if x.ndim == 1 else x[0].mean(); return 20 * math.log10(abs(a - b) + 1e-9)


# ------------------------------------------------------------------ levels
def rms_db(x): return 20 * math.log10(np.sqrt(np.mean(np.square(x))) + 1e-12)
def peak_db(x): return 20 * math.log10(np.max(np.abs(x)) + 1e-12)


def lufs_approx(x, sr=SR):
    """Rough BS.1770-style K-weighted loudness for mono or stereo float arrays."""
    xs = x if x.ndim == 2 else x[:, None]; tot = 0.0
    sh_b, sh_a = signal.iirfilter(1, 1500 / (sr / 2), btype='high', ftype='butter')   # crude high shelf proxy
    for c in range(xs.shape[1]):
        y = signal.lfilter(*signal.butter(2, 38 / (sr / 2), 'high'), xs[:, c])
        y = y + 0.4 * signal.lfilter(sh_b, sh_a, y)
        tot += np.mean(y ** 2)
    return -0.691 + 10 * math.log10(tot + 1e-12)


def normalize(x, peak=-3.0, target_lufs=None, sr=SR):
    x = np.asarray(x, dtype=np.float64)
    x = x - np.mean(x, axis=0)                                  # remove DC
    x = hp(x, 20, sr, 1) if x.ndim == 1 else np.stack([hp(x[:, c], 20, sr, 1) for c in range(x.shape[1])], axis=1)
    if target_lufs is not None:
        g = 10 ** ((target_lufs - lufs_approx(x, sr)) / 20.0); x = x * g
        pk = np.max(np.abs(x))
        if 20 * math.log10(pk + 1e-12) > peak: x = x * (10 ** (peak / 20.0) / pk)
        return x.astype(np.float32)
    return (x / (np.max(np.abs(x)) + 1e-12) * 10 ** (peak / 20.0)).astype(np.float32)


def fade_ends(x, head=0.002, tail=0.01, sr=SR):
    n = x.shape[0]; h = int(head * sr); t = int(tail * sr); e = np.ones(n)
    if h > 0: e[:h] = np.linspace(0, 1, h)
    if t > 0: e[n - t:] *= np.linspace(1, 0, t)
    return x * (e[:, None] if x.ndim == 2 else e)


def soft_clip(x, drive=1.0): return np.tanh(x * drive) / np.tanh(drive)


# ------------------------------------------------------------------ output
MANIFEST_PATH = os.path.join(OUT, 'manifest.part.json')


def set_manifest(name):
    """Each generator module writes its own fragment (out/manifest.<name>.json) so modules can run in parallel."""
    global MANIFEST_PATH
    MANIFEST_PATH = os.path.join(OUT, 'manifest.%s.json' % name)
    if os.path.exists(MANIFEST_PATH): os.remove(MANIFEST_PATH)



def save(name, x, bus, loop=False, gain=1.0, rate=(0.94, 1.06), variants=1, max_dist=160, weight=1.0, lazy=False, group='core',
         peak=-3.0, target_lufs=None, sr=SR, tags=None, quality=4, meta=None):
    """Normalise, encode to Ogg Vorbis and register in the manifest. `name` is the asset id (also the file stem)."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 2 and x.shape[1] == 1: x = x[:, 0]
    x = fade_ends(x) if not loop else x
    y = normalize(x, peak, target_lufs, sr)
    path = os.path.join(OUT, name + '.ogg')
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tf: tmp = tf.name
    ch = 1 if y.ndim == 1 else y.shape[1]
    pcm = (np.clip(y, -1, 1) * 32767).astype('<i2')
    with wave.open(tmp, 'wb') as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', tmp, '-c:a', 'libvorbis', '-q:a', str(quality), path], check=True)
    os.remove(tmp)
    ent = dict(id=name, file='audio/' + name + '.ogg', bus=bus, loop=bool(loop), gain=gain, rate=list(rate), variants=variants,
               maxDist=max_dist, weight=weight, lazy=lazy, group=group, dur=round(y.shape[0] / sr, 3), ch=ch, sr=sr,
               peakDb=round(peak_db(y), 1), rmsDb=round(rms_db(y), 1), lufs=round(lufs_approx(y, sr), 1),
               seamDb=round(seam_db(y), 1) if loop else None, tags=tags or [])
    if meta: ent['meta'] = meta
    _append(ent)
    return ent


def _append(ent):
    d = {}
    if os.path.exists(MANIFEST_PATH):
        try: d = json.load(open(MANIFEST_PATH, encoding='utf-8'))
        except Exception: d = {}
    d[ent['id']] = ent
    json.dump(d, open(MANIFEST_PATH, 'w', encoding='utf-8'), indent=1)


def variants(maker, name, count, **kw):
    """Render `count` numbered variants name_01..; maker(seed_index)->array. Registers one manifest group per variant."""
    for i in range(count):
        save('%s_%02d' % (name, i + 1), maker(i), variants=1, **kw)
