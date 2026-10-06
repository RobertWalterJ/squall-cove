"""Self-check for ambience/weather assets: spectral character, loop pumping, band energies."""
import sys, os, json, glob, math
import numpy as np, soundfile as sf
from scipy import signal
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
def main(prefixes):
    m = {}
    for n in ('ambience', 'weather'):
        p = os.path.join(OUT, 'manifest.%s.json' % n)
        if os.path.exists(p): m.update(json.load(open(p)))
    print('%-24s %5s %6s %6s %6s | <200 200-1k 1-4k 4-8k >8k (%%) | rms1s_first/last dB  L/R corr  seam' % ('id', 'dur', 'peak', 'lufs', 'cent'))
    for id_, e in m.items():
        if prefixes and not any(id_.startswith(p) for p in prefixes): continue
        x, sr = sf.read(os.path.join(OUT, id_ + '.ogg'))
        xm = x if x.ndim == 1 else x.mean(1)
        f, p = signal.welch(xm, sr, nperseg=4096); tot = p.sum() + 1e-18
        cen = (f * p).sum() / tot
        b = lambda lo, hi: 100 * p[(f >= lo) & (f < hi)].sum() / tot
        r1 = 20 * math.log10(np.sqrt(np.mean(xm[:sr] ** 2)) + 1e-9); r2 = 20 * math.log10(np.sqrt(np.mean(xm[-sr:] ** 2)) + 1e-9)
        cc = np.corrcoef(x[:, 0], x[:, 1])[0, 1] if x.ndim == 2 else float('nan')
        print('%-24s %5.1f %6.1f %6.1f %6d | %4.0f %4.0f %4.0f %4.0f %4.0f | %6.1f %6.1f  %5.2f  %s' % (id_, len(xm) / sr, 20 * math.log10(np.max(np.abs(x))), e.get('lufs', 0), cen, b(0, 200), b(200, 1000), b(1000, 4000), b(4000, 8000), b(8000, 30000), r1, r2, cc, e.get('seamDb')))
main(sys.argv[1:])
