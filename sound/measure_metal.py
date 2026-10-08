import sys, os, glob, subprocess, numpy as np
sys.argv = ['x', 'v']
from scipy import signal
import synthlib as S
import gen_ac130_imp as G
from gen_heavy import rng
import gen_util as U
SR = 44100; here = os.path.dirname(os.path.abspath(__file__))
for i in range(4):
    G.v_metal(rng(U.seed_of('ac130_vulcan_hit_metal', i)), i)
sq = np.array(G.SQ_LOG); tau = np.array(G.PING_TAUS)
print('generator log: %d squeak elements, length ms min %.1f median %.1f max %.1f' % (len(sq), sq.min(), np.median(sq), sq.max()))
print('ping tau %.0f-%.0f ms => time to -30 dB %.0f-%.0f ms, to -40 dB %.0f-%.0f ms' % (tau.min() * 1e3, tau.max() * 1e3, tau.min() * 3.45e3, tau.max() * 3.45e3, tau.min() * 4.6e3, tau.max() * 4.6e3))


def load(p):
    r = subprocess.run([S.FFMPEG, '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True)
    return np.frombuffer(r.stdout, dtype='<f4').astype(float)


def band_decay(x, lo, hi, db=-30, t0=0.004):
    b = signal.sosfiltfilt(signal.butter(4, [lo, hi], 'bp', fs=SR, output='sos'), x)
    k = int(0.002 * SR); env = np.sqrt(np.convolve(b ** 2, np.ones(k) / k, 'same')); s = int(t0 * SR); e = env[s:]
    pk = e.max(); ip = e.argmax(); idx = np.nonzero(e[ip:] > pk * 10 ** (db / 20))[0]
    return (ip + idx[-1]) / SR * 1000, np.mean([np.sum(np.abs(np.fft.rfft(b)) * np.fft.rfftfreq(len(b), 1 / SR)) / np.sum(np.abs(np.fft.rfft(b)))])


for fam in ('ac130_vulcan_hit_metal',):
    for new, d in (('old', 'out_old2'), ('new', '../audio')):
        res = [band_decay(load(p), 3000, 9000)[0] for p in sorted(glob.glob(os.path.join(here, d, fam + '_0?.ogg')))]
        hf = [band_decay(load(p), 9500, 16000, -30)[0] for p in sorted(glob.glob(os.path.join(here, d, fam + '_0?.ogg')))]
        print('%s %s: 3-9 kHz band decay to -30 dB (ms, per variant): %s | 9.5-16 kHz band: %s' % (fam, new, ['%.0f' % v for v in res], ['%.0f' % v for v in hf]))
