"""Builds NOTES-weapons.md (stem table from the manifest + prose) and appends the weapons entry to LISTENING.md. Safe to re-run."""
import json, os, collections
H = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(os.path.dirname(H), 'audio')
new = json.load(open(os.path.join(H, 'out', 'manifest.weapons.json'), encoding='utf-8'))
fam = collections.OrderedDict()
for k, e in new.items():
    st = k.rsplit('_', 1)[0] if k.rsplit('_', 1)[-1].isdigit() and e['variants'] > 1 else k
    fam.setdefault(st, []).append(e)
rows = []; tot = 0
for st, l in sorted(fam.items()):
    d = [x['dur'] for x in l]; pk = max(x['peakDb'] for x in l); kb = sum(os.path.getsize(os.path.join(A, x['id'] + '.ogg')) for x in l) / 1024; tot += kb
    rows.append('| %s | %d | %s | %.1f | %s | %s | %s | %.0f |' % (st, len(l), ('%.2f' % d[0]) if min(d) == max(d) else '%.2f-%.2f' % (min(d), max(d)), pk, l[0]['bus'], l[0]['group'], 'loop' if l[0]['loop'] else 'one-shot', kb))
txt = open(os.path.join(H, 'notes_weapons_template.md'), encoding='utf-8').read().replace('@@TABLE@@', '\n'.join(rows)).replace('@@TOTAL@@', '%d files, %.2f MB' % (len(new), tot / 1024))
open(os.path.join(H, 'NOTES-weapons.md'), 'w', encoding='utf-8').write(txt)
print('notes written', len(new), 'files', round(tot / 1024, 2), 'MB')
