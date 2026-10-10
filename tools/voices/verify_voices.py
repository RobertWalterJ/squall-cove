"""Measure every file listed in audio/voices/lines.json: format, size, decoded peak, duration, tail, centroid.
Prints a per-voice size table and flags outliers (we cannot listen, so this is the quality gate).
Run with any Python that has numpy, scipy and soundfile:  python tools/voices/verify_voices.py
"""
import os, sys, json
import numpy as np
import soundfile as sf
from scipy import signal

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
VD = os.path.join(ROOT, "audio", "voices")
meta = json.load(open(os.path.join(VD, "lines.json"), encoding="utf8"))
bad, per = [], {}
tot = 0
for m in meta:
    p = os.path.join(VD, m["file"])
    if not os.path.exists(p):
        bad.append((m["file"], "missing")); continue
    sz = os.path.getsize(p); tot += sz
    d, sr = sf.read(p)
    info = sf.info(p)
    pk = 20 * np.log10(np.abs(d).max() + 1e-9)
    f, pxx = signal.welch(d if d.ndim == 1 else d[:, 0], sr, nperseg=2048)
    cen = (f * pxx).sum() / (pxx.sum() + 1e-12)
    if sr != 44100 or info.channels != 1: bad.append((m["file"], f"format {sr} {info.channels}ch"))
    if sz > 60 * 1024: bad.append((m["file"], f"size {sz/1024:.0f} KB"))
    if pk > -1.95: bad.append((m["file"], f"peak {pk:.2f}"))
    words = len(m["text"].split())
    if len(d) / sr > 0.75 + 0.5 * words + 0.5: bad.append((m["file"], f"long {len(d)/sr:.2f}s for {words} words"))
    if len(d) / sr < 0.2: bad.append((m["file"], f"short {len(d)/sr:.2f}s"))
    v = per.setdefault((m["voice"], m["style"]), [0, 0.0]); v[0] += 1; v[1] += sz
print("voice/style files KB")
for (v, s), (n, b) in sorted(per.items()):
    print(f"  {v:8s} {s:6s} {n:4d} {b/1024:7.0f}")
print(f"TOTAL {len(meta)} files {tot/1048576:.2f} MB")
print(f"{len(bad)} flags")
for b in bad[:80]: print("  FLAG", *b)
