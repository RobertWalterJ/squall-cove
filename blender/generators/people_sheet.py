"""Render the sixteen in-game people from the game GLB as a contact sheet.
  blender -b --python people_sheet.py -- people.glb OUT.png [cols] [portraits]
Front view, orthographic, the rest pose the game's idle clip starts from."""
import bpy, sys, os, math
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
GLB, OUT = argv[0], argv[1]
COLS = int(argv[2]) if len(argv) > 2 else 8
PORTRAIT = len(argv) > 3
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
tops = sorted([o for o in bpy.data.objects if o.parent is None and o.name.startswith('facetex_')], key=lambda o: int(o.name.split('_')[1].split('.')[0]))
for o in bpy.data.objects:                       # rest pose, not frame 1 of the idle clip
    if o.type == 'ARMATURE': o.animation_data_clear()
bpy.context.view_layer.update()
CELL = 1.25; ROW = 2.2 if not PORTRAIT else 0.9
for i, t in enumerate(tops):
    t.location = ((i % COLS) * CELL, 0, 0) if False else Vector(((i % COLS) * CELL, -(i // COLS) * 0.0, 0)) + Vector((0, 0, -(i // COLS) * ROW))
sc = bpy.context.scene
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.74, 0.77, 0.80, 1); bg.inputs[1].default_value = 1.0
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(sun)
sun.data.energy = 3.2; sun.data.angle = math.radians(6); sun.rotation_euler = (math.radians(58), math.radians(10), math.radians(25))
rows = (len(tops) + COLS - 1) // COLS
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam; cam.data.type = 'ORTHO'
cx = (COLS - 1) * CELL / 2; cz = -(rows - 1) * ROW / 2 + (0.9 if not PORTRAIT else 1.45)
cam.location = (cx, -30, cz); cam.rotation_euler = (math.radians(90), 0, 0)
W = COLS * CELL + 0.2; Hh = rows * ROW + (0.0 if not PORTRAIT else 0.0)
if PORTRAIT:                                      # heads and shoulders only
    cam.data.ortho_scale = W; res = (2400, int(2400 * (rows * ROW + 0.5) / W)); cz = -(rows - 1) * ROW / 2 + 1.5; cam.location = (cx, -30, cz)
else:
    cam.data.ortho_scale = W; res = (2400, int(2400 * (rows * ROW + 0.35) / W))
sc.render.resolution_x, sc.render.resolution_y = res
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'AgX'
# floor
bpy.ops.mesh.primitive_plane_add(size=80, location=(cx, 0, 0)); fl = bpy.context.active_object
fm = bpy.data.materials.new('floor'); fm.use_nodes = True; fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.82, 0.82, 0.80, 1)
fl.data.materials.append(fm); fl.visible_shadow = False        # floors must not shadow the row below
for r in range(1, rows):
    p = bpy.data.objects.new('floor%d' % r, fl.data.copy()); sc.collection.objects.link(p); p.location = (cx, 0, -r * ROW); p.visible_shadow = False
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print('PEOPLE DONE', len(tops))
