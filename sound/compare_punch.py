"""Before/after for the punch pass. usage: python compare_punch.py  (old = out_old, new = ../audio)
low30   = RMS dBFS of the 60-200 Hz band in the first 30 ms
low30rel= low30 minus whole-file RMS dBFS (how front-loaded the low end is)
sqC     = spectral centroid (Hz) of the squeak layer = content after 25 ms, high-passed at 2.5 kHz
sqDur   = time (ms) from 25 ms until the >2.5 kHz envelope (2 ms smoothing) falls 30 dB below its own peak for good
"""
import os, glob, subprocess, numpy as np
from scipy import signal
import synthlib as S
SR = 44100; here = os.path.dirname(os.path.abspath(__file__))


def load(p):
    r = subprocess.run([S.FFMPEG, '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True)
    return np.frombuffer(r.stdout, dtype='<f4').astype(float)


def db(v): return 20 * np.log10(max(v, 1e-9))


def metrics(x):
    k = int(0.03 * SR)
    lo = signal.sosfiltfilt(signal.butter(2, [60, 200], 'bp', fs=SR, output='sos'), x)
    low30 = db(np.sqrt(np.mean(lo[:k] ** 2))); tot = db(np.sqrt(np.mean(x ** 2)))
    hi = signal.sosfiltfilt(signal.butter(4, 2500, 'hp', fs=SR, output='sos'), x)
    s0 = int(0.025 * SR); h = hi[s0:]
    sp = np.abs(np.fft.rfft(h)); f = np.fft.rfftfreq(len(h), 1 / SR); cen = (sp * f).sum() / (sp.sum() + 1e-12)
    env = np.sqrt(np.convolve(hi ** 2, np.ones(int(0.002 * SR)) / int(0.002 * SR), 'same'))[s0:]
    pk = env.max(); idx = np.nonzero(env > pk * 10 ** (-30 / 20))[0]
    dur = (idx[-1] / SR * 1000) if len(idx) else 0.0
    return low30, low30 - tot, cen, dur


def fam(files):
    return np.array([metrics(load(p)) for p in files])


groups = {}
for p in sorted(glob.glob(os.path.join(here, 'out_old', 'ac130_*.ogg'))):
    n = os.path.basename(p)[:-4]
    if '_far_' in n: continue
    groups.setdefault(n.rsplit('_', 1)[0], []).append(n)
print('%-30s | %8s %8s | %8s %8s | %8s %8s | %8s %8s' % ('family', 'low30 old', 'new', 'rel old', 'new', 'sqCen old', 'new', 'sqDur old', 'new'))
for g, names in groups.items():
    o = fam([os.path.join(here, 'out_old', n + '.ogg') for n in names]).mean(0)
    w = fam([os.path.join(here, '..', 'audio', n + '.ogg') for n in names]).mean(0)
    print('%-30s | %8.1f %8.1f | %8.1f %8.1f | %8.0f %8.0f | %8.0f %8.0f' % (g, o[0], w[0], o[1], w[1], o[2], w[2], o[3], w[3]))
