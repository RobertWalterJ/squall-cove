"""Quick review: build one aircraft and render chosen views.
  blender -b --python air_review.py -- cormorant|cl415 TEX_DIR OUT_DIR view1,view2,... [samples] [size]
"""
import bpy, sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pg_core import *
import air_render as R

args = sys.argv[sys.argv.index('--') + 1:]
which, tex, out, views = args[0], args[1], args[2], (args[3].split('+') if '+' in args[3] or ':' in args[3] else args[3].split(','))
samples = int(args[4]) if len(args) > 4 else 16; size = int(args[5]) if len(args) > 5 else 1400
os.makedirs(out, exist_ok=True)
if which == 'cormorant':
    import pg_cormorant as MOD
else:
    import pg_cl415 as MOD
reset()
hull, parts, anim, M = MOD.build(tex)[:4]
hull = join([o for o in parts], which + '_hull') if len(parts) > 1 else hull
objs = [hull] + anim
print('TRIS', which, tri_count(hull), [tri_count(a) for a in anim], dims(hull))
sc = R.setup_scene(samples)
for v in views:
    # view spec: name[:tx,ty,tz[:zoom]]  e.g. 3q_high:8,0,2:3.5
    parts_ = v.split(':'); tgt = [float(t) for t in parts_[1].split(',')] if len(parts_) > 1 and parts_[1] else None; zm = float(parts_[2]) if len(parts_) > 2 else 1.0
    R.shoot(sc, os.path.join(out, f"{which}_{parts_[0]}{'' if not tgt else '_z%d_%d' % (int(tgt[0]), int(zm * 10))}.png"), parts_[0], objs, size, zm, tgt)
print('REVIEW DONE')
