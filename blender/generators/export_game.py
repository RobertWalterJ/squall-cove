import sys, os, json, math
sys.path.insert(0, '/home/claude/procgen')
from pg_core import *
import pg_boats as B, pg_cargo as C, pg_harbour as Hb, pg_nature as N
OUT = '/home/claude/squall2/assets'
meta = {}
def bundle(name, objs):
    export_glb(objs, f'{OUT}/{name}.glb')
    meta[name] = {o.name: dict(tris=tri_count(o), dims=dims(o)) for o in objs}
# fleet: hull + rig (+ jib) as separate nodes
reset(); B.GAME['split'] = True
fleet = []; fm = {}
for key, fn, seed in (('petrel', B.dinghy, 1), ('kestrel', B.keelboat, 4), ('bollard', B.tug, 1)):
    objs = fn(seed=seed, name=key)
    fleet += objs; fm[key] = dict(B.GAME['meta'])
bundle('fleet', fleet); meta['fleet_meta'] = fm
# nature
reset()
nat = [N.pine(seed=s, name=f'pine{s}') for s in (1, 2, 3, 4)] + [N.broadleaf(seed=s, name=f'broadleaf{s}') for s in (1, 2, 3)] + \
      [N.palm(seed=s, name=f'palm{s}') for s in (1, 2)] + [N.shrub(seed=s, name=f'shrub{s}') for s in (1, 2, 3)] + \
      [N.boulder(seed=s, name=f'boulder{s}') for s in (1, 2, 3, 4, 5, 6)]
bundle('nature', nat)
# harbour
reset()
har = [Hb.lighthouse(seed=1, name='lighthouse'), Hb.pier(seed=1, name='pier', length=9.0)] + \
      [Hb.buoy(seed=s, name=f'buoy{s}') for s in (0, 1, 2, 5)] + [Hb.bollard(seed=0, name='bollard')]
bundle('harbour', har)
# cargo
reset()
car = [C.crate(seed=1, name='crate'), C.barrel(seed=1, name='barrel'), C.drum(seed=1, name='drum_a'), C.drum(seed=2, name='drum_b'),
       C.ingot_pallet(seed=1, name='ingots'), C.ice(seed=0, name='ice'), C.beach_ball(seed=1, name='ball'),
       C.container(seed=1, name='container_a', length=20), C.container(seed=3, name='container_b', length=20)]
bundle('cargo', car)
json.dump(meta, open(f'{OUT}/assets.json', 'w'), indent=1)
