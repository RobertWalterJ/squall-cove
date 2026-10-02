import sys, os, json
sys.path.insert(0, '/home/claude/procgen')
from pg_core import *
from pg_sheet import render_sheet, report
import pg_boats

OUT = '/home/claude/procgen/out/watercraft'
os.makedirs(OUT, exist_ok=True)
reset()
items = []
seeds = [int(a) for a in sys.argv[sys.argv.index('--') + 1:]] if '--' in sys.argv else [1]
for label, fn in pg_boats.TYPES:
    for s in seeds:
        o = fn(seed=s, name=f'{fn.__name__}_s{s}')
        export_glb([o], f'{OUT}/{o.name}.glb')
        items.append((f'{label}  seed {s}', o))
json.dump(report(items), open(f'{OUT}/report.json', 'w'), indent=1)
render_sheet(items, cols=4, out_png=f'{OUT}/watercraft_sheet.png', gap=1.5, samples=24, obj_rot=-35)
