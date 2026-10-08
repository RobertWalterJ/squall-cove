"""Render the concrete/water fix families. usage: python fix3.py a|b|c   (a = Vulcan concrete+water+stitch, b = Bofors concrete+water, c = howitzer water)
Each part writes out/manifest.fix3<part>.json; merge_fix3.py deploys all."""
import sys
part = sys.argv[1]; sys.argv = ['x', 'v']
import synthlib as S, gen_heavy as H, gen_util as U
import gen_ac130_imp as G
from gen_heavy import *

if part == 'a':
    S.set_manifest('fix3a'); H.CEIL_DB = -4.5
    for sf in ('concrete', 'water'):
        G.reg('ac130_vulcan_hit_' + sf, G.V_MAKERS[sf], 4, 'hit', 'mat', weight=4, max_dist=250, tags=['impact', 'ac130', 'vulcan', sf])
    G.reg('ac130_vulcan_stitch', G.m_stitch, 3, 'loop', 'mat', far=dict(stem='ac130_vulcan_stitch_far', count=3, lp=900, delay=0.1, rt=0.8, wet=0.4, fc=700),
          weight=6, max_dist=500, tags=['impact', 'ac130', 'vulcan', 'stitch'])
elif part == 'b':
    S.set_manifest('fix3b'); H.CEIL_DB = -2.2
    for sf in ('concrete', 'water'):
        G.reg('ac130_bofors_hit_' + sf, G.B_MAKERS[sf], 4, 'fire', 'mat', far=dict(stem='ac130_bofors_hit_%s_far' % sf, count=3, lp=650, delay=0.15, rt=1.4, wet=0.6, fc=550),
              weight=8, max_dist=600, tags=['impact', 'ac130', 'bofors', '40mm', sf])
else:
    S.set_manifest('fix3c'); H.CEIL_DB = -2.2
    tags = ['impact', 'ac130', 'howitzer', '105mm', 'explosion', 'water']
    G.reg('ac130_howitzer_hit_water', G.h_water, 4, 'boom', 'mat', far=dict(stem='ac130_howitzer_hit_water_far', count=4, lp=520, delay=0.2, rt=3.0, wet=0.7, fc=450),
          weight=10, max_dist=1200, tags=tags)
    for i in range(4):
        x = G.h_water(rng(U.seed_of('ac130_howitzer_hit_water', i)), i)
        stage_save('ac130_howitzer_hit_water_sub_%02d' % (i + 1), lp(x, 100, SR, 4), 'sub', 'mat', variants=4, group='weapons', tags=tags + ['sub'], rate=(0.96, 1.04), gain=0.8,
                   weight=10, max_dist=1200, meta=dict(kind='sub-layer', note='mono 25-90 Hz body to layer under the full stem'))
print('done', part)
