"""Squall Cove crew/squad voice sample generator.

Offline TTS (Kokoro-82M via kokoro-onnx, Apache-2.0; Piper, MIT) is used ONLY as a
tool to render small ogg assets. Models live in tools/voices/models (git-ignored)
and are never shipped with the game.

Setup (once):  py -3.11 -m venv tools/voices/.venv
               tools/voices/.venv/Scripts/python -m pip install truststore kokoro-onnx piper-tts soundfile scipy numpy
               tools/voices/.venv/Scripts/python tools/voices/fetch_models.py
Run:           tools/voices/.venv/Scripts/python tools/voices/make_samples.py
Output:        audio/crew_samples/*.ogg  (mono 44.1 kHz vorbis q~4, peak <= -2 dBFS)
"""
import os, sys
import numpy as np
from scipy import signal
import soundfile as sf

try:
    import truststore; truststore.inject_into_ssl()
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "models")
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "audio", "crew_samples"))
SR = 44100
PEAK = 10 ** (-2.0 / 20)          # -2 dBFS
rng = np.random.default_rng(7)    # deterministic hiss/clicks

CREW_LINES = {            # slug: (text, per-line speed bump)
    "up":          ("Up!", 1.15),
    "weaponup":    ("Weapon up!", 1.15),
    "ready":       ("Ready!", 1.15),
    "readytofire": ("Ready to fire!", 1.15),
    "loaded":      ("Loaded!", 1.15),
}
SQUAD_LINES = {
    "contactfront": ("Contact front!", 1.1),
    "movingup":     ("Moving up!", 1.1),
    "coverme":      ("Cover me!", 1.1),
}
# (id, engine, model voice, lang, speed)
CREW_VOICES = [
    ("michael", "kokoro", "am_michael", "en-us", 1.15),
    ("adam",    "kokoro", "am_adam",    "en-us", 1.15),
    ("george",  "kokoro", "bm_george",  "en-gb", 1.15),
    ("eric",    "kokoro", "am_eric",    "en-us", 1.15),
    ("joe",     "piper",  "en_US-joe-medium", "en-us", 1.15),   # Piper joe: CC0 dataset
]
SQUAD_VOICES = [
    ("liam",  "kokoro", "am_liam",   "en-us", 1.1),
    ("lewis", "kokoro", "bm_lewis",  "en-gb", 1.1),
    ("onyx",  "kokoro", "am_onyx",   "en-us", 1.1),
]

_kokoro = None
_piper = {}

def synth_kokoro(text, voice, lang, speed):
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
    a, sr = _kokoro.create(text, voice=voice, speed=speed, lang=lang)
    return np.asarray(a, dtype=np.float32), sr

def synth_piper(text, voice, lang, speed):
    from piper import PiperVoice, SynthesisConfig
    if voice not in _piper:
        _piper[voice] = PiperVoice.load(os.path.join(MODELS, voice + ".onnx"))
    v = _piper[voice]
    cfg = SynthesisConfig(length_scale=1.0 / speed, noise_scale=0.8, noise_w_scale=0.9)
    parts = [c.audio_float_array for c in v.synthesize(text, syn_config=cfg)]
    return np.concatenate(parts).astype(np.float32), v.config.sample_rate

def resample(x, sr):
    if sr == SR: return x
    g = np.gcd(sr, SR)
    return signal.resample_poly(x, SR // g, sr // g).astype(np.float32)

def trim(x, thresh_db=-40, pad_ms=(6, 40)):
    env = np.abs(x)
    th = env.max() * 10 ** (thresh_db / 20)
    idx = np.where(env > th)[0]
    if len(idx) == 0: return x
    a = max(0, idx[0] - int(SR * pad_ms[0] / 1000))
    b = min(len(x), idx[-1] + int(SR * pad_ms[1] / 1000))
    return x[a:b]

def compress(x, thresh_db=-22, ratio=3.5, attack_ms=2, release_ms=60):
    """Simple feed-forward peak compressor."""
    th = 10 ** (thresh_db / 20)
    at = np.exp(-1 / (SR * attack_ms / 1000)); rl = np.exp(-1 / (SR * release_ms / 1000))
    env = 0.0; g = np.ones_like(x)
    for i, s in enumerate(np.abs(x)):
        c = at if s > env else rl
        env = c * env + (1 - c) * s
        if env > th:
            g[i] = (env / th) ** (1 / ratio - 1)
    return x * g

def shout(x):
    """Clipped, urgent, yelled: presence lift, compress, boost, saturate, fast fade."""
    x = x / (np.abs(x).max() + 1e-9)
    # presence/edge lift (shouting has more energy at 1-4 kHz)
    b, a = signal.butter(2, [1200, 4200], btype="band", fs=SR)
    x = x + 0.55 * signal.lfilter(b, a, x)
    # drop sub-rumble
    b, a = signal.butter(2, 110, btype="high", fs=SR); x = signal.lfilter(b, a, x)
    x = compress(x)
    x = x / (np.abs(x).max() + 1e-9) * 0.9
    x = np.tanh(2.6 * x) / np.tanh(2.6)      # saturation
    x = np.clip(x * 1.25, -0.92, 0.92)       # touch of hard clip
    n = int(SR * 0.012)
    x[-n:] *= np.linspace(1, 0, n)
    x[:int(SR * 0.002)] *= np.linspace(0, 1, int(SR * 0.002))
    return x.astype(np.float32)

def squelch(kind):
    n = int(SR * (0.045 if kind == "open" else 0.06))
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    b, a = signal.butter(2, [500, 3200], btype="band", fs=SR)
    noise = signal.lfilter(b, a, noise)
    env = np.exp(-t / (0.012 if kind == "open" else 0.02))
    env[:int(SR * 0.0015)] *= np.linspace(0, 1, int(SR * 0.0015))
    c = noise * env
    if kind == "close":               # a little tonal tick on release
        c += 0.5 * np.sin(2 * np.pi * 1100 * t) * np.exp(-t / 0.006)
    return (c / (np.abs(c).max() + 1e-9) * 0.5).astype(np.float32)

def headset(x):
    """Aircraft intercom: 300 Hz-3.4 kHz, mild distortion, carrier hiss, squelch before/after."""
    b, a = signal.butter(4, [300, 3400], btype="band", fs=SR)
    y = signal.lfilter(b, a, x)
    y = y / (np.abs(y).max() + 1e-9)
    y = np.tanh(1.8 * y) / np.tanh(1.8)       # mild distortion
    lead, tail = int(SR * 0.03), int(SR * 0.05)
    body = np.concatenate([np.zeros(lead), y, np.zeros(tail)]).astype(np.float32)
    hiss = signal.lfilter(b, a, rng.standard_normal(len(body)))
    hiss = hiss / (np.abs(hiss).max() + 1e-9) * 0.045   # faint carrier hiss
    body = body * 0.85 + hiss
    # squelch click before and after
    sq0, sq1 = squelch("open"), squelch("close")
    out = np.concatenate([sq0, np.zeros(int(SR * 0.012)), body, np.zeros(int(SR * 0.008)), sq1])
    return out.astype(np.float32)

def finalize(x):
    pk = np.abs(x).max()
    if pk > 0: x = x * (PEAK / pk)
    return x.astype(np.float32)

def _enc(path, x):
    try:
        sf.write(path, x, SR, format="OGG", subtype="VORBIS", compression_level=0.4)  # ~ q4
    except TypeError:
        sf.write(path, x, SR, format="OGG", subtype="VORBIS")

def write(path, x):
    """Encode, then decode and verify the DECODED peak (vorbis overshoots); rescale if needed."""
    x = finalize(x)
    for _ in range(4):
        _enc(path, x)
        d, _sr = sf.read(path)
        pk = np.abs(d).max()
        if pk <= PEAK * 0.995: break
        x = x * (PEAK * 0.97 / pk)
    return os.path.getsize(path)

def render(engine, voice, lang, text, speed):
    a, sr = (synth_kokoro if engine == "kokoro" else synth_piper)(text, voice, lang, speed)
    return resample(a, sr)

def main():
    os.makedirs(OUT, exist_ok=True)
    only = set(sys.argv[1:])
    n = 0
    for vid, eng, voice, lang, speed in CREW_VOICES:
        if only and vid not in only: continue
        for slug, (text, bump) in CREW_LINES.items():
            raw = shout(trim(render(eng, voice, lang, text, speed)))
            write(os.path.join(OUT, f"crew_{vid}_{slug}.ogg"), raw)
            write(os.path.join(OUT, f"crew_{vid}_{slug}_hs.ogg"), headset(raw))
            n += 2; print("ok crew", vid, slug, flush=True)
    for vid, eng, voice, lang, speed in SQUAD_VOICES:
        if only and vid not in only: continue
        for slug, (text, bump) in SQUAD_LINES.items():
            raw = shout(trim(render(eng, voice, lang, text, speed)))
            write(os.path.join(OUT, f"squad_{vid}_{slug}.ogg"), raw)
            n += 1; print("ok squad", vid, slug, flush=True)
    print("files", n)

if __name__ == "__main__":
    main()
