"""Per-variant stats (centroid, duration, peak, effective 'tail' time) for my three modules. Usage: python wm_stats.py [prefix ...]"""
import sys, os, json, glob, math
import numpy as np, soundfile as sf
from scipy import signal
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
ids = []
for nm in ('water', 'materials', 'fire_electric'):
    p = os.path.join(OUT, 'manifest.%s.json' % nm)
    if os.path.exists(p): ids += list(json.load(open(p)).keys())
pref = sys.argv[1:]
fam = {}
for i in ids:
    if pref and not any(i.startswith(p) for p in pref): continue
    x, sr = sf.read(os.path.join(OUT, i + '.ogg')); xm = x if x.ndim == 1 else x.mean(1)
    f, pw = signal.welch(xm, sr, nperseg=min(4096, len(xm))); cen = (f * pw).sum() / (pw.sum() + 1e-18)
    e = np.abs(xm); w = int(.02 * sr); env = np.sqrt(np.convolve(xm ** 2, np.ones(w) / w, 'same'))
    thr = env.max() * 10 ** (-30 / 20); tail = np.nonzero(env > thr)[0]; t30 = (tail[-1] / sr) if len(tail) else 0
    stem = i.rsplit('_', 1)[0] if i.rsplit('_', 1)[-1].isdigit() else i
    fam.setdefault(stem, []).append((len(xm) / sr, t30, cen, 20 * math.log10(e.max() + 1e-12)))
for s, v in fam.items():
    a = np.array(v)
    print('%-28s n=%d dur %.2f  t-30dB %.2f  centroid %5d (%5d..%5d)  peak %.1f' % (s, len(v), a[:, 0].mean(), a[:, 1].mean(), a[:, 2].mean(), a[:, 2].min(), a[:, 2].max(), a[:, 3].max()))
