"""Decode every new fire_* stem (those in out/manifest.fire.json, or ../audio with --audio) and report duration, peak, RMS, loudest-400ms RMS,
spectral centroid, loop seam (step at the wrap vs typical sample step, and 5 ms RMS at the join vs the loop median), size, plus variant diversity.
    python verify_fire.py            (reads out/)
    python verify_fire.py --audio    (reads ../audio, only ids listed in out/manifest.fire.json)"""
import sys, os, json, subprocess, numpy as np
import synthlib as S
here = os.path.dirname(os.path.abspath(__file__))
d = os.path.join(here, '..', 'audio') if '--audio' in sys.argv else os.path.join(here, 'out')
SR = 44100
ids = sorted(json.load(open(os.path.join(here, 'out', 'manifest.fire.json'), encoding='utf-8')).keys())


def load(p):
    r = subprocess.run([S.FFMPEG, '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True)
    return np.frombuffer(r.stdout, dtype='<f4').astype(float)


def db(v): return 20 * np.log10(max(v, 1e-9))


def wrms(x, w=0.4):
    k = int(w * SR)
    if len(x) <= k: return db(np.sqrt(np.mean(x ** 2)))
    c = np.concatenate([[0], np.cumsum(x ** 2)]); st = np.arange(0, len(x) - k, k // 8)
    return db(np.sqrt(np.max((c[st + k] - c[st]) / k)))


def seam(x):
    """(wrap step / largest in-body step in dB; <= 0 means the wrap is no bigger than any natural step, join-window 20 ms RMS minus median 20 ms RMS in dB)."""
    stp = abs(x[0] - x[-1]); typ = np.max(np.abs(np.diff(x))) + 1e-12
    w = int(0.02 * SR); xx = np.concatenate([x[-w:], x[:w]]); j = db(np.sqrt(np.mean(xx ** 2)))
    c = np.concatenate([[0], np.cumsum(x ** 2)]); st = np.arange(0, len(x) - w, w); m = np.median(np.sqrt((c[st + w] - c[st]) / w))
    return db(stp / typ), j - db(m)


tot = 0; fam = {}; rows = []
print('%-30s %5s %6s %6s %7s %6s %5s  %s' % ('stem', 'dur', 'peak', 'rms', 'loud400', 'cent', 'KB', 'loop seam: step/maxstep dB, join-vs-median dB'))
for n in ids:
    p = os.path.join(d, n + '.ogg')
    if not os.path.exists(p): print('MISSING', n); continue
    x = load(p); kb = os.path.getsize(p) / 1024; tot += kb
    sp = np.abs(np.fft.rfft(x)); f = np.fft.rfftfreq(len(x), 1 / SR); cen = (sp * f).sum() / sp.sum()
    sm = ''
    if '_loop' in n:
        a, b = seam(x); sm = '%+.1f / %+.1f' % (a, b)
        P = sp ** 2; bands = [P[(f >= lo) & (f < hi)].sum() / P.sum() * 100 for lo, hi in ((0, 150), (150, 800), (800, 3000), (3000, 30000))]
        w = int(0.05 * SR); e = 10 * np.log10(np.add.reduceat(x ** 2, np.arange(0, len(x) - w, w)) / w + 1e-12)
        sm += '  abs wrap step %.0f dBFS; bands %%<150/150-800/0.8-3k/>3k = %.0f/%.0f/%.0f/%.0f; 50 ms level std %.1f dB' % (db(abs(x[0] - x[-1])), *bands, np.std(e))
    print('%-30s %5.2f %6.1f %6.1f %7.1f %6.0f %5.0f  %s' % (n, len(x) / SR, db(np.max(np.abs(x))), db(np.sqrt(np.mean(x ** 2))), wrms(x), cen, kb, sm))
    fam.setdefault(n.rsplit('_', 1)[0], []).append(x)
print('TOTAL: %.0f KB (%.2f MB), files %d' % (tot, tot / 1024, len(ids)))
print('variant diversity: max cross-correlation over +-5 ms lags (1.0 = identical, under 0.3 = distinct)')
for k, v in fam.items():
    if len(v) < 2: continue
    m = 0
    for i in range(len(v)):
        for j in range(i + 1, len(v)):
            n = min(len(v[i]), len(v[j]), 44100 * 2); a = v[i][:n]; b = v[j][:n]
            c = np.fft.irfft(np.fft.rfft(a, 2 * n) * np.conj(np.fft.rfft(b, 2 * n)))
            m = max(m, np.max(np.abs(np.concatenate([c[:220], c[-220:]]))) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
    print('  %-30s %.2f' % (k, m))
