import sys, os, json
sys.path.insert(0, '/home/claude/procgen')
from pg_core import *
from pg_sheet import render_sheet, report
import pg_harbour as H
group = sys.argv[sys.argv.index('--') + 1]
OUT = '/home/claude/procgen/out/harbour'; os.makedirs(OUT, exist_ok=True)
reset(); items = []
plans = {'structures': [('Pier bay', H.pier, [1, 2, 3]), ('Lighthouse', H.lighthouse, [1, 2, 3, 4, 5])],
         'marine': [('Buoy', H.buoy, [0, 1, 2, 3, 4, 5]), ('Bollard / cleat', H.bollard, [0, 1, 2]), ('Channel marker', H.channel_marker, [0, 1])]}
for label, fn, seeds in plans[group]:
    for s in seeds:
        o = fn(seed=s, name=f'{fn.__name__}_s{s}')
        export_glb([o], f'{OUT}/{o.name}.glb'); items.append((f'{label}  seed {s}', o))
json.dump(report(items), open(f'{OUT}/report_{group}.json', 'w'), indent=1)
render_sheet(items, cols=4 if group == 'structures' else 6, out_png=f'{OUT}/sheet_{group}.png', gap=1.0, samples=24)
