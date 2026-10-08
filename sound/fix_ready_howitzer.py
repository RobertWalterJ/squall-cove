"""Rebuild the opening and middle of ac130_int_ready_howitzer with real mechanical sounds (iron clanks, steel resonances, grip clunks,
hydraulic growl; no sine sweeps), keeping the final latch/seat tail of the previous file byte-for-byte in the sample domain
(the previous file is read from out_old4/ and joined with a 40 ms equal-power crossfade at 1.58 s).
    python fix_ready_howitzer.py
"""
import os, json, math
import numpy as np
import gen_ac130_int as G
from gen_ac130_int import *

here = os.path.dirname(os.path.abspath(__file__)); AUD = os.path.join(os.path.dirname(here), 'audio')
XF0, XF1 = 1.58, 1.62


def iron(r, f, g=1.0, heavy=1.0):
    """Impulsive iron clank: broadband strike plus short, inharmonic, quickly damped steel resonances and a small body thud."""
    ring = np.zeros(n_of(0.2))
    t = np.arange(len(ring)) / SR
    for ratio, a, tau in ((1.0, 0.35, 0.03), (1.63, 0.25, 0.022), (2.41, 0.18, 0.016), (3.37, 0.1, 0.01)):
        ring += a * np.sin(TWO_PI * f * ratio * r.uniform(0.96, 1.04) * t + r.uniform(0, 6)) * np.exp(-t / (tau * r.uniform(0.8, 1.2)))
    return g * sumv(tickn(r, 0.004, 350, 5200, 0.9, n_of(0.09)), ring, thump(n_of(0.1), 135 * heavy, 0.016, 0.45, 0.2))


def head(r):
    n = n_of(1.8); out = np.zeros(n); t = tt(n)
    pump = unit(bp(noise(n, 'white', r), 85, 520, SR, 2)) * slowmod(n, 7.0, r, 0.6) * np.minimum(1, t / 0.08) * np.clip((1.05 - t) / 0.1, 0, 1)
    out += pump * 0.4
    out += unit(bp(noise(n, 'white', r), 600, 1900, SR, 2)) * slowmod(n, 11.0, r, 0.8) * (t < 0.95) * 0.07
    tk = 0.02                                                                    # chain links clanking over the sprocket
    while tk < 0.98:
        put(out, iron(r, r.uniform(650, 1700), r.uniform(0.25, 0.6)), tk, 1.0)
        tk += (1.0 / r.uniform(8, 13)) * r.uniform(0.7, 1.3)
    for tg, f, g in ((0.2, 480, 0.9), (0.57, 560, 1.0), (0.9, 420, 1.1)):         # shifting grip clunks
        put(out, sumv(iron(r, f, g, 1.0), thump(n_of(0.2), r.uniform(105, 150), 0.04, 0.6, 0.2), body(r, 0.1, 600, 0.02, 0.5, 90)), tg, 1.0)
    put(out, hyd_hiss(r, 0.4, 250, 1200, 0.8, 0.45), 1.0, 1.0)                    # ram pushing
    put(out, sumv(iron(r, 440, 1.25, 0.8), thump(n_of(0.35), 78, 0.07, 1.0, 0.3)), 1.3, 1.0)
    put(out, iron(r, 560, 0.7), 1.42, 1.0)
    return ear(out, 4500)


def main():
    p_old = os.path.join(here, 'out_old4', 'ac130_int_ready_howitzer.ogg')
    old = load(p_old); a0 = int(XF0 * SR); a1 = int(XF1 * SR)
    new = head(rng(U.seed_of('ac130_int_ready_howitzer_v2')))[:a1]
    pk_old = np.max(np.abs(old[:a0])); new *= 1.6 * pk_old / (np.max(np.abs(new[:a0])) + 1e-12)
    w = np.linspace(0, math.pi / 2, a1 - a0); y = np.concatenate([new[:a0], new[a0:a1] * np.cos(w) + old[a0:a1] * np.sin(w), old[a1:]])
    for d in (os.path.join(here, 'out'), AUD): enc(y, os.path.join(d, 'ac130_int_ready_howitzer.ogg'), 4)
    yy = load(os.path.join(AUD, 'ac130_int_ready_howitzer.ogg'))
    mp = os.path.join(AUD, 'manifest.json'); man = json.load(open(mp, encoding='utf-8')); e = man['assets']['ac130_int_ready_howitzer']
    e['dur'] = round(len(yy) / SR, 3); e['peakDb'] = round(db(np.max(np.abs(yy))), 1); e['rmsDb'] = round(db(np.sqrt(np.mean(yy ** 2))), 1)
    json.dump(man, open(mp, 'w', encoding='utf-8'))
    tail_err = np.max(np.abs(yy[a1 + 200:len(old) - 200] - old[a1 + 200:len(old) - 200])) if len(yy) >= len(old) else -1
    print('ready_howitzer: dur %.2f peak %.1f (old peak %.1f) tail max diff after re-encode %.4f (%.1f dB)' % (len(yy) / SR, e['peakDb'], db(np.max(np.abs(old))), tail_err, db(tail_err)))


if __name__ == '__main__':
    main()
