import sys; sys.path.insert(0,'/home/claude/procgen')
import pg_marine as M
from pg_core import *
reset()
objs=[]
for k,f in (('bay',M.bay_lifeboat),('hero',lambda: M.ship('hero_class')),('hover',M.hovercraft)):
    o=f(); o.name=k+'_hull'; objs.append(o); print(k,dims(o),tri_count(o))
export_glb(objs,'/home/claude/squall4/assets/ccg.glb')
