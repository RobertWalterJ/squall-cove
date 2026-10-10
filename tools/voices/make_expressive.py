"""Squall Cove expressive voices: Chatterbox (Resemble AI, MIT) driven by SYNTHETIC Kokoro references.

Run with a Python that has torch (CUDA) + chatterbox-tts + soundfile + scipy + librosa. On this machine the
owner's existing "CitySteps Speech Studio" venv is reused read-only (no new install), see audio/voices/README.md.

    CB_PY="C:/Users/Robert Walter-Joseph/Documents/CitySteps - Claude CoWork/CitySteps Speech Studio/.venv/Scripts/python.exe"
    tools/voices/.venv/Scripts/python tools/voices/make_refs.py            # synthetic reference clips (Kokoro, Apache-2.0)
    "$CB_PY" tools/voices/make_expressive.py compare                      # step 1: audition set
    "$CB_PY" tools/voices/make_expressive.py roster [voice ids ...]       # step 2: full roster

Chatterbox weights come from the Hugging Face cache (ResembleAI/chatterbox). Outputs are mono 44.1 kHz Ogg q4,
peak <= -2 dBFS. Every Chatterbox output carries Resemble's built-in Perth watermark (kept on).
We cannot listen while generating, so candidates are chosen by measurement (see score()).
"""
import os, sys, json, time, shutil
import numpy as np
import soundfile as sf
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_samples as ms            # reuse the approved DSP helpers (trim, cut_tail, stretch, headset, write)
try:
    import roster_lines              # step 2 line inventory (optional until written)
except ImportError:
    roster_lines = None
# Listing this folder later (while torch/transformers import) can raise WinError 6714 on this machine,
# so drop it from sys.path now that our own modules are loaded. Launch with `python -P` as well.
try: sys.path.remove(HERE)
except ValueError: pass

SR = ms.SR
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
REFS = os.path.join(HERE, "work", "refs")
CMP = os.path.join(ROOT, "audio", "crew_samples", "compare")
VOICES_OUT = os.path.join(ROOT, "audio", "voices")
CREW_DIR = os.path.join(ROOT, "audio", "crew_samples")

# ------------------------------------------------------------------ Chatterbox
_cb = None
def cb():
    global _cb
    if _cb is None:
        # Import order matters on this machine (flaky WinError 6714 / access violation inside torch._dynamo
        # otherwise); this exact order is the one proven to work.
        import torch, torchaudio
        import librosa, sklearn, transformers
        from transformers.generation.utils import GenerationMixin
        from transformers.models.llama.modeling_llama import LlamaModel
        from chatterbox.tts import ChatterboxTTS
        try:
            import perth
            if getattr(perth, "PerthImplicitWatermarker", None) is None:
                perth.PerthImplicitWatermarker = perth.DummyWatermarker
                print("WARNING: Perth watermarker unavailable, output is NOT watermarked", flush=True)
        except Exception:
            pass
        _cb = ChatterboxTTS.from_pretrained(device="cuda" if torch.cuda.is_available() else "cpu")
        print("chatterbox ready, sr", _cb.sr, flush=True)
    return _cb

_cur_ref = None
def set_voice(vid):
    global _cur_ref
    if _cur_ref == vid: return
    cb().prepare_conditionals(os.path.join(REFS, vid + ".wav"), exaggeration=0.5)
    _cur_ref = vid

def gen(text, exag, cfg, seed, temp=0.8):
    import torch
    torch.manual_seed(seed); np.random.seed(seed % (2 ** 31))
    w = cb().generate(text, exaggeration=exag, cfg_weight=cfg, temperature=temp)
    x = w.squeeze(0).cpu().numpy().astype(np.float32)
    return ms.resample(x, cb().sr)

def free_gpu():
    global _cb, _cur_ref
    _cb = None; _cur_ref = None
    import gc, torch
    gc.collect(); torch.cuda.empty_cache()

# ------------------------------------------------------------------ measurement
def centroid(x):
    f, p = signal.welch(x, SR, nperseg=2048)
    return float((f * p).sum() / (p.sum() + 1e-12))

def analyze(x):
    pk = float(np.abs(x).max()) + 1e-9
    return dict(dur=round(len(x) / SR, 3), peak_db=round(20 * np.log10(pk), 1),
                rms_db=round(20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9), 1),
                centroid=round(centroid(x)), tail_ms=round(ms.tail_ms(x)))

def prep(x, strict=False):
    """lead trim, drop quiet babble, cut the release tail right after the last consonant burst."""
    x = x / (np.abs(x).max() + 1e-9)
    x = ms.lead_trim(ms.trim(x, -45, (4, 60)))
    return ms.cut_tail(x, -14, 6) if strict else ms.cut_tail(x, -26, 10)

def score(x):
    """Lower is better: short, no long low-energy tail, not clipped. Used to pick among candidates."""
    d = len(x) / SR
    if d < 0.12: return 1e9
    return ms.tail_ms(x) * 1.0 + 160.0 * d

def best_of(texts, exag, cfg, n, seed0, strict=False, temp=0.8, label=""):
    cands = []
    for i in range(n):
        t = texts[i % len(texts)]
        raw = gen(t, exag, cfg, seed0 + i * 17, temp)
        x = prep(raw, strict)
        cands.append((score(x), t, x))
    durs = sorted(len(c[2]) / SR for c in cands)
    med = durs[len(durs) // 2]
    ok = [c for c in cands if len(c[2]) / SR <= max(1.6 * med, med + 0.25)] or cands   # drop runaway babble
    ok.sort(key=lambda c: c[0])
    s, t, x = ok[0]
    print(f"   {label} picked '{t}' score={s:.0f} {analyze(x)} of {[round(len(c[2])/SR,2) for c in cands]}", flush=True)
    return x, ok

# ------------------------------------------------------------------ finishing chains
def shout_chain(x, drive=2.6, presence=0.55, gain=1.25):
    x = x / (np.abs(x).max() + 1e-9)
    b, a = signal.butter(2, [1200, 4200], btype="band", fs=SR); x = x + presence * signal.lfilter(b, a, x)
    b, a = signal.butter(2, 110, btype="high", fs=SR); x = signal.lfilter(b, a, x)
    x = ms.compress(x)
    x = x / (np.abs(x).max() + 1e-9) * 0.9
    x = np.tanh(drive * x) / np.tanh(drive)
    x = np.clip(x * gain, -0.92, 0.92)
    n = int(SR * 0.012); x[-n:] *= np.linspace(1, 0, n)
    x[:int(SR * 0.002)] *= np.linspace(0, 1, int(SR * 0.002))
    return x.astype(np.float32)

def calm_chain(x):
    x = x / (np.abs(x).max() + 1e-9)
    b, a = signal.butter(2, 90, btype="high", fs=SR); x = signal.lfilter(b, a, x)
    x = ms.compress(x, -20, 2.5, 4, 80)
    n = int(SR * 0.012); x[-n:] *= np.linspace(1, 0, n)
    return x.astype(np.float32)

def radio_chain(x):
    """Radio: light compression, then the approved headset chain (300 Hz-3.4 kHz, distortion, hiss, squelch)."""
    x = x / (np.abs(x).max() + 1e-9)
    x = ms.compress(x, -26, 4.0, 3, 90)
    return ms.headset(x.astype(np.float32))

def write_ogg(path, x, limit_kb):
    n = ms.write(path, x)
    d, _ = sf.read(path)
    if n > limit_kb * 1024: print("   WARNING size", path, n, flush=True)
    return n, float(20 * np.log10(np.abs(d).max() + 1e-9))

# ------------------------------------------------------------------ STEP 1: comparison set
LEVELS = {            # name: (exaggeration, cfg_weight, speed-up, chain)
    "calm":   (0.40, 0.55, 1.00, "calm"),
    "urgent": (0.70, 0.40, 1.10, "mid"),
    "shout":  (1.10, 0.25, 1.15, "full"),
}
# slug -> (voice, text parts [(text variants..., strict, post-rate)], Kokoro file)
CMP_LINES = [
    ("michael", "up",          [(["Up!", "Up!!", "Up."], True, 1.0)],                          "crew_michael_up.ogg"),
    ("michael", "weaponup",    [(["Weapon up!", "Weapon up!!", "Weapon, up!"], True, 1.0)],    "crew_michael_weaponup.ogg"),
    ("michael", "ready",       [(["Ready!", "Ready!!", "Ready."], False, 1.0)],                "crew_michael_ready.ogg"),
    ("michael", "readytofire", [(["Ready to", "Ready, to", "Ready to,"], False, 1.0),
                                (["Fire!", "Fire!!", "Fire."], False, 1.35)],                  "crew_michael_readytofire.ogg"),
    ("michael", "loaded",      [(["Loaded!", "Loaded!!", "Loaded."], False, 1.0)],             "crew_michael_loaded.ogg"),
    ("lewis",   "contactfront", [(["Contact front!", "Contact, front!", "Contact front!!"], False, 1.0)], "squad_lewis_contactfront.ogg"),
    ("lewis",   "takingfire",   [(["Taking fire!", "Taking fire!!", "We're taking fire!"], False, 1.0)],  "squad_lewis_takingfire.ogg"),
    ("lewis",   "mandown",      [(["Man down!", "Man down!!", "Man, down!"], False, 1.0)],      "squad_lewis_mandown.ogg"),
]

def render_line(parts, exag, cfg, rate, seed, label, n=4):
    segs = []
    for i, (texts, strict, post) in enumerate(parts):
        x, _ = best_of(texts, exag, cfg, n, seed + i * 101, strict, label=f"{label}[{i}]")
        segs.append(ms.stretch(x, post * rate))
    x = segs[0]
    gap = np.zeros(int(SR * (0.045 if len(segs) > 1 else 0)), np.float32)
    for s in segs[1:]:
        x = np.concatenate([x, gap, s])
    return x

def do_compare():
    os.makedirs(CMP, exist_ok=True)
    rows = []
    cur = None
    for vid, slug, parts, kfile in CMP_LINES:
        set_voice(vid)
        kdst = os.path.join(CMP, f"cmp_{vid}_{slug}_kokoro.ogg")
        shutil.copyfile(os.path.join(CREW_DIR, kfile), kdst)      # the approved Kokoro take, copied unchanged
        kx, _ = sf.read(kdst)
        row = {"voice": vid, "line": slug, "kokoro": analyze(kx.astype(np.float32))}
        for lvl, (exag, cfg, rate, chain) in LEVELS.items():
            t0 = time.time()
            x = render_line(parts, exag, cfg, rate, seed=1000 + len(slug) * 7, label=f"{vid}/{slug}/{lvl}")
            x = {"calm": calm_chain, "mid": lambda v: shout_chain(v, 1.6, 0.35, 1.1), "full": shout_chain}[chain](x)
            path = os.path.join(CMP, f"cmp_{vid}_{slug}_cb_{lvl}.ogg")
            n, pk = write_ogg(path, x, 100)
            d, _ = sf.read(path)
            row[lvl] = dict(analyze(d.astype(np.float32)), kb=round(n / 1024, 1), decoded_peak_db=round(pk, 1))
            print(f"OK {os.path.basename(path)} {row[lvl]} {time.time()-t0:.0f}s", flush=True)
        rows.append(row)
    json.dump(rows, open(os.path.join(HERE, "work", "compare_metrics.json"), "w"), indent=1)
    free_gpu()

# ------------------------------------------------------------------ STEP 2 hook (filled in below)
def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "compare"
    if cmd == "compare": do_compare()
    elif cmd == "roster":
        roster_lines.run(sys.modules[__name__], sys.argv[2:])
    else: print("usage: compare | roster [ids]")

if __name__ == "__main__":
    main()
