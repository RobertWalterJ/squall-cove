"""Run inside Blender: blender -b --factory-startup -P render_fire_blender.py -- <fire.glb> <outdir>
Workbench, flat lighting, vertex colours. Renders each group front and 3/4 view to <outdir>/g_<group>_{front,3q}.png"""
import bpy, sys, math, os
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
GLB, OUT = argv[0], argv[1]
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'FLAT'; sh.color_type = 'VERTEX'; sh.show_backface_culling = False
sc.render.film_transparent = False
sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new('w'); w.color = (0.07, 0.08, 0.10); sc.world = w
sc.render.image_settings.file_format = 'PNG'
sc.frame_set(1)

tops = {o.name: o for o in bpy.data.objects if o.parent is None and o.type != 'CAMERA'}
GROUPS = [
    ('small', ['flame_s_01', 'flame_s_02', 'flame_s_03'], 0.55),
    ('medium', ['flame_m_01', 'flame_m_02', 'flame_m_03'], 1.1),
    ('large', ['flame_l_01', 'flame_l_02', 'flame_l_03'], 2.2),
    ('camp', ['fire_camp'], 1),
    ('vehicle', ['fire_vehicle'], 1),
    ('ground', ['fire_ground'], 1),
    ('building', ['fire_building'], 1),
    ('tree', ['fire_tree'], 1),
    ('bits', ['ember_01', 'ember_02', 'ember_03', 'ash_flake_01', 'ash_flake_02', 'smoke_puff_01', 'smoke_puff_02', 'smoke_puff_03'], 0.5),
    ('smoke', ['smoke_column'], 1),
]
cam_d = bpy.data.cameras.new('c'); cam_d.type = 'ORTHO'
cam = bpy.data.objects.new('cam', cam_d); sc.collection.objects.link(cam); sc.camera = cam

def descendants(o):
    yield o
    for c in o.children: yield from descendants(c)

def bbox(objs):
    dg = bpy.context.evaluated_depsgraph_get(); lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for r in objs:
        for o in descendants(r):
            if o.type != 'MESH': continue
            e = o.evaluated_get(dg)
            for v in e.data.vertices:
                p = e.matrix_world @ v.co
                lo = Vector((min(lo[i], p[i]) for i in range(3))); hi = Vector((max(hi[i], p[i]) for i in range(3)))
    return lo, hi

for gname, names, spacing in GROUPS:
    objs = [tops[n] for n in names]
    for o in tops.values():
        for d in descendants(o): d.hide_render = o not in objs
    for i, o in enumerate(objs): o.location = Vector(((i - (len(objs) - 1) / 2) * spacing * (1 if gname != 'bits' else 1), 0, 0))
    bpy.context.view_layer.update()
    lo, hi = bbox(objs); c = (lo + hi) / 2; ext = max(hi.x - lo.x, hi.z - lo.z, hi.y - lo.y) if False else max(hi.x - lo.x, hi.z - lo.z)
    # glTF y-up became blender z-up: height is z
    ext = max(hi.x - lo.x, hi.z - lo.z); ext = max(ext * 1.18, 0.1)
    sc.render.resolution_x = 520; sc.render.resolution_y = 520
    cam_d.ortho_scale = ext
    for view, az in (('front', 0.0), ('3q', math.radians(55))):
        d = Vector((math.sin(az), -math.cos(az), 0.25)).normalized()
        cam.location = c + d * 40
        cam.rotation_euler = (d * -1).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(OUT, 'g_%s_%s.png' % (gname, view))
        bpy.ops.render.render(write_still=True)
print('RENDER DONE')
