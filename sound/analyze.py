"""QA for the generated sound set: decodes every asset in the manifest fragments and reports levels, spectra, loop seams and variant diversity.
Usage: python analyze.py [--fail]"""
import os, sys, json, glob, math
import numpy as np, soundfile as sf
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')

def load_manifest():
    m = {}
    for f in sorted(glob.glob(os.path.join(OUT, 'manifest.*.json'))):
        if f.endswith('manifest.json'): continue
        try: m.update(json.load(open(f, encoding='utf-8')))
        except Exception as e: print('bad fragment', f, e)
    return m

def centroid(x, sr):
    xm = x if x.ndim == 1 else x.mean(axis=1)
    f, p = signal.welch(xm, sr, nperseg=min(4096, len(xm)))
    return float((f * p).sum() / (p.sum() + 1e-18))

def main(fail=False):
    m = load_manifest(); problems = []; total = 0; rows = []
    fam = {}
    for id_, e in m.items():
        path = os.path.join(OUT, id_ + '.ogg')
        if not os.path.exists(path): problems.append((id_, 'missing file')); continue
        x, sr = sf.read(path, always_2d=False); total += os.path.getsize(path)
        pk = 20 * math.log10(np.max(np.abs(x)) + 1e-12); dc = abs(float(np.mean(x)))
        cen = centroid(x, sr)
        dur = len(x) / sr
        if pk > -1.0: problems.append((id_, 'peak %.1f dB' % pk))
        if dc > 0.003: problems.append((id_, 'DC %.4f' % dc))
        if not e.get('loop') and dur > 12: problems.append((id_, 'one-shot too long %.1fs' % dur))
        if e.get('loop'):
            xm = x if x.ndim == 1 else x.mean(axis=1); k = int(0.01 * sr)
            seam = 20 * math.log10(abs(xm[-1] - xm[0]) / (np.std(xm) + 1e-9) + 1e-9)
            if seam > -6: problems.append((id_, 'loop seam %.1f dB re rms' % seam))
            if dur < 2.0: problems.append((id_, 'loop too short %.1fs' % dur))
        if e.get('lufs') is not None and e['bus'] == 'amb' and e['lufs'] > -18: problems.append((id_, 'ambience too loud %.1f LUFS' % e['lufs']))
        stem = id_.rsplit('_', 1)[0] if id_.rsplit('_', 1)[-1].isdigit() else id_
        fam.setdefault(stem, []).append((id_, x if x.ndim == 1 else x.mean(axis=1)))
        rows.append((id_, e['bus'], round(dur, 2), round(pk, 1), e.get('lufs'), int(cen), os.path.getsize(path) // 1024))
    # variant diversity
    for stem, lst in fam.items():
        if len(lst) < 2: continue
        base = lst[0][1][:int(0.4 * 44100)]
        for id_, x in lst[1:]:
            y = x[:len(base)]
            if len(y) < len(base): continue
            c = np.max(np.abs(signal.fftconvolve(base - base.mean(), (y - y.mean())[::-1], mode='valid'))) / (np.linalg.norm(base - base.mean()) * np.linalg.norm(y - y.mean()) + 1e-9)
            if c > 0.8: problems.append((id_, 'too similar to %s (xcorr %.2f)' % (lst[0][0], c)))
    rows.sort()
    with open(os.path.join(OUT, 'report.txt'), 'w', encoding='utf-8') as f:
        f.write('assets %d, total %.1f MB\n' % (len(rows), total / 1048576.0))
        f.write('id | bus | dur s | peak dB | LUFS | centroid Hz | KB\n')
        for r in rows: f.write(' | '.join(str(v) for v in r) + '\n')
        f.write('\nPROBLEMS %d\n' % len(problems))
        for p in problems: f.write('%s: %s\n' % p)
    print('assets %d, %.1f MB, problems %d' % (len(rows), total / 1048576.0, len(problems)))
    for p in problems[:60]: print('  ', p[0], p[1])
    if fail and problems: sys.exit(1)

if __name__ == '__main__': main('--fail' in sys.argv)
