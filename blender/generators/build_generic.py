import sys, os, json
sys.path.insert(0, '/home/claude/procgen')
from pg_core import *
from pg_sheet import render_sheet, report
import importlib; MOD = importlib.import_module(os.environ.get('PGMOD', 'pg_cargo'))

OUT = '/home/claude/procgen/out/' + os.environ.get('PGOUT', 'cargo')
os.makedirs(OUT, exist_ok=True)
reset()
items = []
seeds = [int(a) for a in sys.argv[sys.argv.index('--') + 1:]] if '--' in sys.argv else [1]
for label, fn in getattr(MOD, os.environ.get('PGTYPES', 'TYPES')):
    for s in seeds:
        o = fn(seed=s, name=f'{fn.__name__}_s{s}')
        export_glb([o], f'{OUT}/{o.name}.glb')
        items.append((f'{label}  seed {s}', o))
json.dump(report(items), open(f'{OUT}/report.json', 'w'), indent=1)
render_sheet(items, cols=int(os.environ.get('PGCOLS', '6')), out_png=f'{OUT}/sheet.png', gap=float(os.environ.get('PGGAP', '0.6')), samples=24)
