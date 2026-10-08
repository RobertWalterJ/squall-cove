"""Decode every ac130_* stem and report duration, peak, RMS, loudest-400ms RMS, spectral centroid, loop seam, size, variant correlation.
    python verify_ac130.py [dir]      (default ../audio; use out/ before deploy)"""
import sys, os, glob, subprocess, numpy as np
import synthlib as S
here = os.path.dirname(os.path.abspath(__file__))
d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, '..', 'audio')
SR = 44100


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
    k = 64; return db(abs(x[0] - x[-1])) , db(np.max(np.abs(np.diff(np.concatenate([x[-k:], x[:k]])))))


files = sorted(glob.glob(os.path.join(d, 'ac130_*.ogg'))); tot = 0; fam = {}
print('%-34s %5s %6s %6s %7s %7s %6s  %s' % ('stem', 'dur', 'peak', 'rms', 'loud400', 'cent', 'KB', 'seam(step, maxdiff dB)'))
for p in files:
    n = os.path.basename(p)[:-4]; x = load(p); kb = os.path.getsize(p) / 1024; tot += kb
    sp = np.abs(np.fft.rfft(x)); f = np.fft.rfftfreq(len(x), 1 / SR); cen = (sp * f).sum() / sp.sum()
    sm = ''
    if 'loop' in n:
        a, b = seam(x); sm = '%.1f / %.1f (body step %.1f)' % (a, b, db(np.max(np.abs(np.diff(x)))))
    print('%-34s %5.2f %6.1f %6.1f %7.1f %7.0f %6.0f  %s' % (n, len(x) / SR, db(np.max(np.abs(x))), db(np.sqrt(np.mean(x ** 2))), wrms(x), cen, kb, sm))
    fam.setdefault(n.rsplit('_', 1)[0], []).append(x)
print('TOTAL KB: %.0f (%.2f MB), files %d' % (tot, tot / 1024, len(files)))
print('variant max cross-correlation (zero-lag-normalised, +-5ms lags)')
for k, v in fam.items():
    if len(v) < 2: continue
    m = 0
    for i in range(len(v)):
        for j in range(i + 1, len(v)):
            n = min(len(v[i]), len(v[j]), 44100 * 2); a = v[i][:n]; b = v[j][:n]
            c = np.fft.irfft(np.fft.rfft(a, 2 * n) * np.conj(np.fft.rfft(b, 2 * n)))
            m = max(m, np.max(np.abs(np.concatenate([c[:220], c[-220:]]))) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
    print('  %-30s %.2f' % (k, m))
