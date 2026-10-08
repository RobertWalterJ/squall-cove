"""Before/after durations and release-tail measure (ms between last >-20 dB and last >-42 dB frame, 2 ms frames; raw files only)."""
import os, glob, sys
import numpy as np, soundfile as sf
H = os.path.dirname(os.path.abspath(__file__))
NEW = os.path.normpath(os.path.join(H, "..", "..", "audio", "crew_samples")); OLD = os.path.join(H, "work", "prev")
def meas(p):
    x, sr = sf.read(p); x = x if x.ndim == 1 else x.mean(1)
    n = int(sr * .002); m = len(x) // n
    d = 20 * np.log10(np.sqrt((x[:m * n].reshape(m, n) ** 2).mean(1)) + 1e-12); d -= d.max()
    a = np.where(d > -20)[0]; b = np.where(d > -42)[0]
    return len(x) / sr, (b[-1] - a[-1]) * 2, 20 * np.log10(np.abs(x).max()), os.path.getsize(p) / 1024
for p in sorted(glob.glob(os.path.join(NEW, "*.ogg"))):
    n = os.path.basename(p)
    if n.endswith("_hs.ogg"): continue
    d, t, pk, kb = meas(p)
    o = os.path.join(OLD, n)
    od, ot = (meas(o)[:2]) if os.path.exists(o) else (float("nan"), float("nan"))
    print(f"{n:34s} dur {od:4.2f}->{d:4.2f}s  tail {ot:4.0f}->{t:4.0f}ms  peak {pk:5.2f} {kb:5.1f}KB")
