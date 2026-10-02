"""blender -b --python bake_faces.py
Bake a flat, front-on photo of each CC0 MakeHuman face (skin, eyes, brows, lashes) into a texture laid out exactly like
the low poly head's face UVs (u across 2.2 head radii, v from chin to crown). The low poly people then wear these
photos stretched over their faceted heads."""
import sys, os, math, json
os.environ.setdefault('PF_MH', '/home/claude/mh/x')
sys.path.insert(0, '/home/claude/procgen')
import bpy
from pg_core import *
import photo_faces as PF
OUT = '/home/claude/procgen/out/people_tex/photo'; os.makedirs(OUT, exist_ok=True)
H = 1.75
J = dict(head=0.875 * H, top=H)
hr, hh = 0.062 * H, J['top'] - J['head']
W_M, H_M = 2.2 * hr, hh                          # metres the texture spans
reset()
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 48; sc.cycles.use_denoising = True
sc.render.film_transparent = True; sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (1, 1, 1, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 0.85
key = bpy.data.objects.new('key', bpy.data.lights.new('key', 'AREA')); link(key); key.data.energy = 9; key.data.size = 1.5
key.location = (0.15, -1.2, J['head'] + 0.7 * hh + 0.4); key.rotation_euler = (math.radians(70), 0, math.radians(8))
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = max(W_M, H_M) / 1.12          # features a touch larger than life, to fill the faceted head
cam.location = (0, -2.0, J['head'] + hh / 2); cam.rotation_euler = (math.radians(90), 0, 0)
px = 512; sc.render.resolution_x = int(px * W_M / max(W_M, H_M)); sc.render.resolution_y = int(px * H_M / max(W_M, H_M))
done = []
for k in PF.SK:
    sex = 'f' if k.endswith('female') else 'm'
    dark = sum(int(PF.SK[k]['avg'][j:j + 2], 16) for j in (1, 3, 5)) < 400
    for eye in (['brown'] if dark else ['brown', 'blue', 'green']):
        objs = PF.photo_head(f'bake_{k}_{eye}', sex, k, eye, H, J)
        sc.render.filepath = f'{OUT}/{k}_{eye}.png'; bpy.ops.render.render(write_still=True)
        for o in objs: bpy.data.objects.remove(o)
        done.append(f'{k}_{eye}')
json.dump(done, open(f'{OUT}/index.json', 'w'))
print('BAKED', len(done))
