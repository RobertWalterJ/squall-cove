"""Measure every file in audio/crew_samples: duration, size, peak, RMS, spectral centroid."""
import os, glob
import numpy as np, soundfile as sf

D = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "audio", "crew_samples"))
rows = {}
for p in sorted(glob.glob(os.path.join(D, "*.ogg"))):
    x, sr = sf.read(p)
    if x.ndim > 1: x = x.mean(1)
    pk = 20 * np.log10(np.abs(x).max() + 1e-12)
    rms = 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-12)
    S = np.abs(np.fft.rfft(x)); f = np.fft.rfftfreq(len(x), 1 / sr)
    cen = (S * f).sum() / (S.sum() + 1e-12)
    n = os.path.basename(p)
    rows[n] = (len(x) / sr, os.path.getsize(p), pk, rms, cen, sr)
    flag = "" if (pk <= -1.9 and os.path.getsize(p) < 100000 and sr == 44100) else "  <-- CHECK"
    print(f"{n:38s} {len(x)/sr:5.2f}s {os.path.getsize(p)/1024:6.1f}KB peak {pk:6.2f} rms {rms:6.1f} cen {cen:6.0f}Hz{flag}")
print("\nraw vs headset spectral centroid (Hz):")
for n, r in rows.items():
    if n.endswith("_hs.ogg"):
        raw = rows.get(n.replace("_hs.ogg", ".ogg"))
        if raw: print(f"{n[:-7]:30s} raw {raw[4]:5.0f} -> hs {r[4]:5.0f}")
