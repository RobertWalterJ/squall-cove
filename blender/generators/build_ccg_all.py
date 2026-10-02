"""Rebuild the whole Canadian Coast Guard fleet.
  blender -b --python build_ccg_all.py -- GAME_DIR MARINE_DIR
Writes GAME_DIR/ccg.glb (bay, hero, hover) and GAME_DIR/ccgfleet.glb (the eight big ships); one node per ship, named <gamekey>_hull, and MARINE_DIR/ccg_<key>.glb for each ship, plus ccg_report.json."""
import bpy, sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pg_core import *
import pg_marine as M

argv = sys.argv[sys.argv.index('--') + 1:]
GAME, MARINE = argv[0], argv[1]
os.makedirs(GAME, exist_ok=True)
os.makedirs(MARINE, exist_ok=True)
# game key -> builder
GAME_KEYS = [('louis', 'louis_st_laurent'), ('arpatuuq', 'arpatuuq'), ('terry', 'terry_fox'), ('radisson', 'pierre_radisson'), ('molly', 'capt_molly_kool'),
             ('martha', 'martha_l_black'), ('donjek', 'donjek_aops'), ('franklin', 'sir_john_franklin'), ('hero', 'hero_class'), ('bay', 'bay_class'), ('hover', 'hovercraft')]
report = {}
reset(); objs = []
for gk, key in GAME_KEYS:
    o = M.build(key); o.name = gk + '_hull'; objs.append(o)
    report[gk] = dict(key=key, dims=dims(o), tris=tri_count(o))
    print('SHIP', gk, dims(o), tri_count(o))
export_glb([o for o in objs if o.name.split('_')[0] in ('hero', 'bay', 'hover')], os.path.join(GAME, 'ccg.glb'))
export_glb([o for o in objs if o.name.split('_')[0] not in ('hero', 'bay', 'hover')], os.path.join(GAME, 'ccgfleet.glb'))
for gk, key in GAME_KEYS:                       # one file per ship for the Model Library (rebuilt in a clean scene each time)
    reset(); o = M.build(key); o.name = key
    export_glb([o], os.path.join(MARINE, f'ccg_{key}.glb'))
json.dump(report, open(os.path.join(MARINE, 'ccg_report.json'), 'w'), indent=1)
print('BUILD DONE')
