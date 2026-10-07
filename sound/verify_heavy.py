"""Decode every heavy stem back from Ogg and print length / peak / loudest-400ms RMS / whole RMS / DC / seam / band energy.
Usage: python verify_heavy.py [dir]   (default ../audio, reading the ids from out/manifest.heavy.json)"""
import os, sys, json, math
import numpy as np
import soundfile as sf
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), 'audio')
ids = list(json.load(open(os.path.join(HERE, 'out', 'manifest.heavy.json'), encoding='utf-8')))
man = json.load(open(os.path.join(HERE, 'out', 'manifest.heavy.json'), encoding='utf-8'))
db = lambda v: 20 * math.log10(v + 1e-12)


def wrms(x, sr, win=0.4):
    w = int(win * sr)
    if len(x) <= w: return db(math.sqrt(np.mean(x ** 2)))
    c = np.concatenate([[0], np.cumsum(x ** 2)]); st = np.arange(0, len(x) - w + 1, w // 8)
    return db(math.sqrt(np.max((c[st + w] - c[st]) / w)))


def bands(x, sr):
    f, p = signal.welch(x, sr, nperseg=4096); tot = p.sum() + 1e-18
    e = lambda a, b: 100 * p[(f >= a) & (f < b)].sum() / tot
    return e(20, 35), e(35, 90), e(90, 400), e(400, 4000), e(4000, 22050)


print('%-34s %5s %6s %6s %6s %7s %7s | %s' % ('id', 'dur', 'peak', 'rms400', 'rmsAll', 'dc', 'seam', '%e 20-35/35-90/90-400/400-4k/4k+'))
bad = []
rows = []
for id_ in ids:
    x, sr = sf.read(os.path.join(D, id_ + '.ogg'), dtype='float64')
    ch = 1 if x.ndim == 1 else x.shape[1]
    if ch != 1: x = x.mean(1)
    pk = db(np.max(np.abs(x))); r4 = wrms(x, sr); ra = db(math.sqrt(np.mean(x ** 2))); dc = abs(np.mean(x))
    k = int(0.005 * sr); loop = man[id_]['loop']
    seam = ''
    if loop:
        # continuity: jump at the wrap compared with the typical sample step, plus level of last vs first 5 ms
        jump = abs(x[0] - x[-1]); step = np.mean(np.abs(np.diff(x))) + 1e-9
        l5 = db(math.sqrt(np.mean(x[:k] ** 2))); e5 = db(math.sqrt(np.mean(x[-k:] ** 2)))
        seam = 'j/step %.1f dRMS %.1f' % (jump / step, abs(l5 - e5))
    b = bands(x, sr)
    dur = len(x) / sr
    lim = 4.0 if id_.startswith(('imp_', 'wpn_rpg_hit')) else (1.6 if ('_fire_' in id_ or id_.startswith(('veh_gunship_cannon', 'wpn_flak_burst', 'wpn_mortar_launch', 'wpn_rpg_launch', 'wpn_tank')) and '_far' not in id_ and '_sub' not in id_) else 9)
    flags = []
    if pk > -1.0: flags.append('PEAK')
    if dc > 0.001: flags.append('DC')
    if dur > lim: flags.append('LONG')
    if ch != 1: flags.append('CH')
    if x[0] != x[0] or abs(x[0]) > 0.02 and not loop: flags.append('HEADCLICK')
    if not loop and abs(x[-1]) > 0.005: flags.append('TAILCLICK')
    if flags: bad.append((id_, flags))
    rows.append((id_, dur, pk, r4, ra, dc, seam, b))
    print('%-34s %5.2f %6.1f %6.1f %6.1f %7.5f %-18s| %4.1f %4.1f %4.1f %4.1f %4.1f %s' % (id_, dur, pk, r4, ra, dc, seam, *b, ' '.join(flags)))

# per-class loudness spread
print()
def grp(f): return [r for r in rows if f(r[0])]
for name, f in [('fire/boom main (non-far, non-sub, non-loop, non-whistle, non-foley)', lambda i: '_far_' not in i and '_sub_' not in i and 'loop' not in i and 'whistle' not in i and not i.startswith(('foley', 'wpn_ammo', 'wpn_bolt', 'wpn_barrel', 'imp_flak_frag'))),
                ('far', lambda i: '_far_' in i), ('sub', lambda i: '_sub_' in i), ('loops', lambda i: 'loop' in i)]:
    g = grp(f); v = [r[3] for r in g]
    print('%-70s n=%2d rms400 min %.1f max %.1f (spread %.1f dB)  peak max %.1f' % (name, len(g), min(v), max(v), max(v) - min(v), max(r[2] for r in g)))
print('flags:', bad if bad else 'none')
