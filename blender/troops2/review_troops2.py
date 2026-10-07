"""blender -b --python review_troops2.py -- <troops2.glb> <out dir> : front/back render per trooper (flat studio light), then compose_sheet.py"""
import sys, os, math, bpy
glb, out = sys.argv[sys.argv.index('--') + 1:][:2]; os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
def top(o):
    while o.parent: o = o.parent
    return o
groups = {}
for o in bpy.data.objects: groups.setdefault(top(o).name, []).append(o)
sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_cavity = False; sh.show_object_outline = False
sc.render.resolution_x, sc.render.resolution_y = 360, 600; sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new('w'); sc.world = w; w.color = (.82, .84, .86)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.0
views = (('front', -6, 0), ('back', 6, math.pi), ('head', -6, 0))
for name in sorted(k for k in groups if k.startswith('trooper2_')):
    for k, objs in groups.items():
        for o in objs: o.hide_render = (k != name); o.hide_viewport = (k != name)
    for view, y, rz in views:
        if view == 'head': cam.data.ortho_scale = .55; cam.location = (0, y, 1.5)
        else: cam.data.ortho_scale = 2.0; cam.location = (0, y, .92)
        cam.rotation_euler = (math.pi / 2, 0, rz)
        if view == 'head': sc.render.resolution_x, sc.render.resolution_y = 360, 360
        else: sc.render.resolution_x, sc.render.resolution_y = 360, 600
        sc.render.filepath = os.path.join(out, f'{name}_{view}.png'); bpy.ops.render.render(write_still=True)
print('REVIEW DONE')
