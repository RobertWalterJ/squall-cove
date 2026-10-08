"""Concrete debris and water-hit metrics, old (out_old3) vs new (../audio). Run: python compare_water.py
 conc: after 60 ms, 1.5-7 kHz band flatness (1 = noise-like; bubbly/tonal debris is lower), share of post-60 ms energy below 1 kHz (tonal bloops live there),
       and the number of separate clicks (envelope peaks > -40 dB re. the file peak, min spacing 3 ms)
 water: lowT = time for the 60-300 Hz band to fall 30 dB (heavy part dissipation); splashT = time the 3-10 kHz band stays within 40 dB of its post-30 ms peak;
        drops = count of droplet clicks (3-10 kHz envelope peaks > -50 dB re. the file's 3-10 kHz peak after 60 ms); wetRel = 3-10 kHz RMS after 60 ms minus total RMS (dB)"""
import os, glob, subprocess, numpy as np
from scipy import signal
import synthlib as S
SR = 44100; here = os.path.dirname(os.path.abspath(__file__))


def load(p):
    r = subprocess.run([S.FFMPEG, '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True)
    return np.frombuffer(r.stdout, dtype='<f4').astype(float)


def db(v): return 20 * np.log10(max(v, 1e-9))
def band(x, lo, hi): return signal.sosfiltfilt(signal.butter(4, [lo, hi], 'bp', fs=SR, output='sos'), x)
def env(x, ms=1.0):
    k = max(1, int(ms / 1000 * SR)); return np.sqrt(np.convolve(x ** 2, np.ones(k) / k, 'same'))


def clicks(e, thr, gap=0.003):
    pk, _ = signal.find_peaks(e, height=thr, distance=int(gap * SR)); return len(pk)


def conc(x):
    s = int(0.06 * SR); y = x[s:]
    if len(y) < 512: return (np.nan,) * 3
    f, P = signal.welch(y, SR, nperseg=min(512, len(y))); m = (f >= 1500) & (f <= 7000); Pb = P[m] + 1e-18
    flat = np.exp(np.mean(np.log(Pb))) / np.mean(Pb); low = P[f < 1000].sum() / P.sum()
    b = band(x, 1500, 7000); e = env(b, 0.5); return flat, low, clicks(e[s:], e.max() * 10 ** (-40 / 20))


def water(x):
    lo = band(x, 60, 300); e = env(lo, 3); ip = e.argmax(); idx = np.nonzero(e[ip:] > e.max() * 10 ** (-30 / 20))[0]; lowT = idx[-1] / SR * 1000
    hi = band(x, 3000, 10000); eh = env(hi, 2); s30 = int(0.03 * SR); pk = eh[s30:].max(); idh = np.nonzero(eh[s30:] > pk * 10 ** (-40 / 20))[0]
    splT = idh[-1] / SR * 1000 + 30 if len(idh) else 0
    s60 = int(0.06 * SR); e2 = env(hi, 0.4)[s60:]; drops = clicks(e2, eh[s60:].max() * 10 ** (-50 / 20) if len(e2) else 1, 0.004)
    wet = db(np.sqrt(np.mean(hi[s60:] ** 2))) - db(np.sqrt(np.mean(x ** 2)))
    return lowT, splT, drops, wet


def group(d, stem):
    return sorted(glob.glob(os.path.join(here, d, stem + '_0?.ogg')))


print('CONCRETE debris (post-60 ms)        flatness  <1kHz share  clicks')
for stem in ('ac130_vulcan_hit_concrete', 'ac130_bofors_hit_concrete'):
    for tag, d in (('old', 'out_old3'), ('new', '../audio')):
        r = np.nanmean([conc(load(p)) for p in group(d, stem)], axis=0)
        print('  %-28s %s   %6.2f    %6.3f     %5.1f' % (stem, tag, *r))
print('\nWATER                               lowT ms  splashT ms  drops  wetRel dB')
for stem in ('ac130_vulcan_hit_water', 'ac130_bofors_hit_water', 'ac130_howitzer_hit_water', 'ac130_howitzer_hit', 'ac130_vulcan_hit_dirt'):
    for tag, d in (('old', 'out_old3'), ('new', '../audio')):
        fs = group(d, stem)
        if not fs: continue
        r = np.mean([water(load(p)) for p in fs], axis=0)
        print('  %-28s %s   %7.0f  %9.0f   %6.0f  %7.1f' % (stem, tag, *r))
st = [load(p) for p in sorted(glob.glob(os.path.join(here, '..', 'audio', 'ac130_vulcan_stitch_0?.ogg')))]
print('\nstitch new (3 variants) drops/splash: ', [tuple(np.round(water(x), 0)) for x in st])
