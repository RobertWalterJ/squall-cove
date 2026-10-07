"""blender -b --python review_troops.py -- <troops.glb> <out dir>   : front and back review render of each trooper (flat studio light)"""
import sys, os, math, bpy
from mathutils import Vector
glb, out = sys.argv[sys.argv.index('--') + 1:][:2]; os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
def top(o):
    while o.parent: o = o.parent
    return o
groups = {}
for o in bpy.data.objects:
    t = top(o); groups.setdefault(t.name, []).append(o)
sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_cavity = False; sh.show_object_outline = False
sc.render.resolution_x, sc.render.resolution_y = 560, 900; sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new('w'); sc.world = w; w.color = (.82, .84, .86)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.05
for name in sorted(k for k in groups if k.startswith('trooper_')):
    for k, objs in groups.items():
        for o in objs: o.hide_render = (k != name); o.hide_viewport = (k != name)
    for view, y, rz in (('front', -6, 0), ('back', 6, math.pi)):
        cam.location = (0, y, .92); cam.rotation_euler = (math.pi / 2, 0, rz)
        sc.render.filepath = os.path.join(out, f'{name}_{view}.png'); bpy.ops.render.render(write_still=True)
print('REVIEW DONE')
