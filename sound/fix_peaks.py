"""Scale any ac130_* one-shot whose decoded peak is above -2.05 dBFS down to -2.6 dBFS and re-encode (q4). Updates manifest peak/rms."""
import os, sys, json, math, wave, tempfile, subprocess
import numpy as np
import synthlib as S
here = os.path.dirname(os.path.abspath(__file__)); AUD = os.path.join(os.path.dirname(here), 'audio'); SR = 44100
mp = os.path.join(AUD, 'manifest.json'); man = json.load(open(mp, encoding='utf-8')); A = man['assets']
names = sys.argv[1:]


def load(p):
    r = subprocess.run([S.FFMPEG, '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True)
    return np.frombuffer(r.stdout, dtype='<f4').astype(float)


def db(v): return 20 * math.log10(max(v, 1e-9))


for id_ in names:
    p = os.path.join(AUD, id_ + '.ogg'); x = load(p); pk = db(np.max(np.abs(x))); g = 10 ** ((-2.6 - pk) / 20)
    if g >= 1: continue
    for _ in range(3):
        y = x * g
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tf: tmp = tf.name
        with wave.open(tmp, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(y, -1, 1) * 32767).astype('<i2').tobytes())
        subprocess.run([S.FFMPEG, '-y', '-loglevel', 'error', '-i', tmp, '-c:a', 'libvorbis', '-q:a', '4', p], check=True); os.remove(tmp)
        z = load(p); pz = db(np.max(np.abs(z)))
        if pz <= -2.1: break
        g *= 10 ** ((-2.6 - pz) / 20)
    e = A[id_]; e['peakDb'] = round(pz, 1); e['rmsDb'] = round(db(np.sqrt(np.mean(z ** 2))), 1)
    print(id_, round(pk, 1), '->', round(pz, 1))
json.dump(man, open(mp, 'w', encoding='utf-8'))
