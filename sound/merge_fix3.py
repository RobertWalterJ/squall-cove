import json, os, shutil
here = os.path.dirname(os.path.abspath(__file__)); dst = os.path.join(os.path.dirname(here), 'audio')
mp = os.path.join(dst, 'manifest.json'); man = json.load(open(mp, encoding='utf-8')); n = 0
for part in 'abc':
    p = os.path.join(here, 'out', 'manifest.fix3%s.json' % part)
    if not os.path.exists(p): continue
    for id_, e in json.load(open(p, encoding='utf-8')).items():
        shutil.copy2(os.path.join(here, 'out', id_ + '.ogg'), os.path.join(dst, id_ + '.ogg')); man['assets'][id_] = e; n += 1
json.dump(man, open(mp, 'w', encoding='utf-8')); print('merged', n)
