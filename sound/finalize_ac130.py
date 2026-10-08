"""Post-pass over the deployed ac130_* stems:
 1. trim dead tails of one-shots (last sample above -58 dBFS + 10 ms, fade 8 ms; Vulcan hits capped at 0.30 s), re-encode (q4; far/sub q2), refresh dur/peak/rms in the manifest
 2. write per-family play hints into manifest meta.play (gapMs, maxVoices, rotate, preload, aggregateHz)
 3. print the memory/download table (decoded = samples x 4 bytes at 44.1 kHz; x1.09 if the context runs at 48 kHz)
usage: python finalize_ac130.py [--no-trim]"""
import os, sys, json, wave, tempfile, subprocess, re, math
import numpy as np
import synthlib as S
here = os.path.dirname(os.path.abspath(__file__)); AUD = os.path.join(os.path.dirname(here), 'audio'); SR = 44100
mp = os.path.join(AUD, 'manifest.json'); man = json.load(open(mp, encoding='utf-8')); A = man['assets']


def load(p):
    r = subprocess.run([S.FFMPEG, '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True)
    return np.frombuffer(r.stdout, dtype='<f4').astype(float)


def enc(x, p, q):
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tf: tmp = tf.name
    with wave.open(tmp, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    subprocess.run([S.FFMPEG, '-y', '-loglevel', 'error', '-i', tmp, '-c:a', 'libvorbis', '-q:a', str(q), p], check=True); os.remove(tmp)


def fam_of(id_): return re.sub(r'_\d\d$', '', id_)


def db(v): return 20 * math.log10(max(v, 1e-9))


# (gapMs, maxVoices, rotate, preload, aggregateHz)
def hint(f):
    if f.startswith('ac130_vulcan_hit_'): return dict(gapMs=40, maxVoices=8, preload=True, aggregateHz=12, note='all vulcan_hit_* families share one cap of 8 voices and 12 plays/s, nearest first')
    if f in ('ac130_vulcan_stitch', 'ac130_vulcan_stitch_far'): return dict(gapMs=500, maxVoices=3, preload=f == 'ac130_vulcan_stitch', note='stands in for impacts that are throttled out or far')
    if f.startswith('ac130_vulcan_loop') or f.startswith('ac130_vulcan_start') or f.startswith('ac130_vulcan_end'): return dict(gapMs=0, maxVoices=1, preload=not f.endswith('_far'), note='one per firing gun; far set loads on first distant gunship')
    if f == 'ac130_bofors_shot': return dict(gapMs=300, maxVoices=5, preload=True)
    if f == 'ac130_bofors_shot_far': return dict(gapMs=300, maxVoices=3, preload=False)
    if f.startswith('ac130_bofors_hit') and f.endswith('_far'): return dict(gapMs=250, maxVoices=3, preload=False)
    if f.startswith('ac130_bofors_hit'): return dict(gapMs=250, maxVoices=4, preload=True)
    if f.startswith('ac130_howitzer') and f.endswith('_far'): return dict(gapMs=1200, maxVoices=3, preload=False)
    if f.startswith('ac130_howitzer') and '_sub' in f: return dict(gapMs=1200, maxVoices=2, preload=False, note='play with the same _NN as the near stem')
    if f.startswith('ac130_howitzer'): return dict(gapMs=1200, maxVoices=3, preload=True)
    if f.startswith('ac130_prop_loop'): return dict(gapMs=0, maxVoices=1, preload=not f.endswith('_far'), note='one per aircraft, nearest 3 only')
    if f == 'ac130_creak': return dict(gapMs=6000, maxVoices=1, preload=False)
    return dict(gapMs=100, maxVoices=4, preload=False)


ids = sorted(k for k in A if k.startswith('ac130_'))
if '--no-trim' not in sys.argv:
    for id_ in ids:
        e = A[id_]
        if e.get('loop'): continue
        p = os.path.join(AUD, id_ + '.ogg'); x = load(p); f = fam_of(id_)
        cap = 0.30 if f.startswith('ac130_vulcan_hit_') else None
        idx = np.nonzero(np.abs(x) > 10 ** (-58 / 20))[0]; end = (idx[-1] + int(0.010 * SR)) if len(idx) else len(x)
        if cap: end = min(end, int(cap * SR))
        end = min(end, len(x))
        far_or_sub = f.endswith('_far') or '_sub' in f
        if len(x) - end < int(0.02 * SR) and not far_or_sub: continue
        y = x[:end].copy(); k = min(len(y), int(0.008 * SR)); y[-k:] *= np.cos(np.linspace(0, math.pi / 2, k)) ** 2
        enc(y, p, 2 if far_or_sub else 4)
        y = load(p); e['dur'] = round(len(y) / SR, 3); e['peakDb'] = round(db(np.max(np.abs(y))), 1); e['rmsDb'] = round(db(np.sqrt(np.mean(y ** 2))), 1)
        print('trimmed %-34s %.2f -> %.2f s' % (id_, len(x) / SR, len(y) / SR))
for id_ in ids:
    e = A[id_]; f = fam_of(id_); h = hint(f); m = e.setdefault('meta', {}); m['play'] = dict(h, rotate=e.get('variants', 1), bus=e['bus'])
    if f.startswith('ac130_vulcan_hit_'): e['weight'] = 2        # engine culls weight<3 first when voices are tight
json.dump(man, open(mp, 'w', encoding='utf-8'))
fams = {}
for id_ in ids:
    e = A[id_]; f = fam_of(id_); kb = os.path.getsize(os.path.join(AUD, id_ + '.ogg')) / 1024
    d = fams.setdefault(f, dict(n=0, kb=0, samples=0, pre=e['meta']['play']['preload'], dur=e['dur'], loop=e['loop'])); d['n'] += 1; d['kb'] += kb; d['samples'] += int(e['dur'] * SR)
print('\n%-36s %3s %7s %7s %6s %5s  %s' % ('family', 'n', 'dur s', 'KB', 'MB dec', 'pre', 'loop'))
tot = dict(kb=0, mb=0); pre = dict(kb=0, mb=0)
for f, d in fams.items():
    mb = d['samples'] * 4 / 1048576; print('%-36s %3d %7.2f %7.0f %6.2f %5s  %s' % (f, d['n'], d['dur'], d['kb'], mb, 'yes' if d['pre'] else 'lazy', 'loop' if d['loop'] else ''))
    tot['kb'] += d['kb']; tot['mb'] += mb
    if d['pre']: pre['kb'] += d['kb']; pre['mb'] += mb
print('TOTAL all %d stems: download %.2f MB, decoded %.2f MB (x1.09 at 48 kHz = %.2f MB)' % (len(ids), tot['kb'] / 1024, tot['mb'], tot['mb'] * 1.09))
print('PRELOAD set: download %.2f MB, decoded %.2f MB | LAZY set: download %.2f MB, decoded %.2f MB' % (pre['kb'] / 1024, pre['mb'], (tot['kb'] - pre['kb']) / 1024, tot['mb'] - pre['mb']))
