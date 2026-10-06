"""Copy the rendered assets and the merged manifest into ../audio (served at audio/<id>.ogg). Run after render_all.py."""
import os, json, glob, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out'); DST = os.path.join(os.path.dirname(HERE), 'audio')
os.makedirs(DST, exist_ok=True)
merged = {}
for f in sorted(glob.glob(os.path.join(OUT, 'manifest.*.json'))):
    if f.endswith('manifest.json'): continue
    merged.update(json.load(open(f, encoding='utf-8')))
n = 0
for id_ in list(merged):
    src = os.path.join(OUT, id_ + '.ogg')
    if not os.path.exists(src): merged.pop(id_); continue
    shutil.copy2(src, os.path.join(DST, id_ + '.ogg')); n += 1
json.dump(dict(version=1, assets=merged), open(os.path.join(DST, 'manifest.json'), 'w', encoding='utf-8'))
tot = sum(os.path.getsize(os.path.join(DST, f)) for f in os.listdir(DST)) / 1048576.0
print('deployed %d assets, %.1f MB' % (n, tot))
