"""Builds the battlefield props, exports assets/battle.glb (+ .b64.txt, one line) and renders review images.
  blender.exe -b --python build_battle.py -- GAME_ASSETS_DIR REVIEW_DIR [models comma list] [--norender] [--noexport]
Game coords: +Z forward, +Y up, +X = model's left, metres.
"""
import bpy, sys, os, math, base64
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from mathutils import Vector
import v_lib as BL
import v_light, v_heavy, v_truck
L = BL.L

argv = sys.argv[sys.argv.index('--') + 1:]
pos = [a for a in argv if not a.startswith('--')]
GAME, REV = pos[0], pos[1]
ALL = ['jeep', 'technical', 'apc', 'light_tank', 'supply_truck', 'ambulance', 'fuel_truck', 'quad_atv']
names = pos[2].split(',') if len(pos) > 2 else ALL
os.makedirs(GAME, exist_ok=True); os.makedirs(REV, exist_ok=True)
FUN = {}
for mod in (v_light, v_heavy, v_truck):
    for n in dir(mod):
        if n in ALL: FUN[n] = getattr(mod, n)

L.reset(); BL.palette()
models = {}
for n in names:
    M = FUN[n](); root = M.build(); models[n] = (M, root)
    print('MODEL', n, 'tris', M.total(), [(x['name'], x['part'].tris()) for x in M.nodes if x['part']])
    if M.total() >= 9000: print('OVER BUDGET', n)

glb = os.path.join(GAME, 'bveh.glb')
if '--noexport' not in argv:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=glb, use_selection=True, export_apply=True, export_yup=True, export_extras=False,
                              export_cameras=False, export_lights=False, export_image_format='NONE', export_materials='EXPORT')
    open(os.path.join(GAME, 'bveh.glb.b64.txt'), 'w').write(base64.b64encode(open(glb, 'rb').read()).decode('ascii'))
    print('GLB', os.path.getsize(glb), 'bytes')

if '--norender' in argv:
    print('DONE (no render)'); sys.exit(0)

# ---------------------------------------------------------------- review renders
sc = bpy.context.scene
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
nt = w.node_tree; bg = nt.nodes['Background']
tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); ramp = nt.nodes.new('ShaderNodeValToRGB')
nt.links.new(tc.outputs['Generated'], sep.inputs[0]); nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (0.30, 0.28, 0.25, 1)
ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = (0.70, 0.80, 0.95, 1)
nt.links.new(ramp.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 1.0
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(sun)
sun.data.energy = 3.6; sun.data.angle = math.radians(4); sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-40))
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = int(os.environ.get('B_SAMPLES', '12')); sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'Standard'; sc.render.image_settings.file_format = 'PNG'
bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 0, -0.002)); gp = bpy.context.object; gp.name = 'review_ground'
gm = bpy.data.materials.new('review_ground'); gm.use_nodes = True; gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.30, 0.27, 0.2, 1)
gp.data.materials.append(gm)

def game_to_b(p): return Vector(L.b_of(p))
def objs_of(root): return [o for o in [root] + list(root.children_recursive) if o.type == 'MESH']

VIEWS = {
    'side':  dict(d=(1, 0, 0), ortho=True), 'front': dict(d=(0, 0, 1), ortho=True), 'top': dict(d=(0, 1, 0), ortho=True),
    '3q': dict(d=(0.8, 0.55, 0.85), ortho=False), '3q_rear': dict(d=(-0.8, 0.5, -0.85), ortho=False), '3q_low': dict(d=(0.9, 0.1, 0.8), ortho=False),
}
def shoot(path, key, root, size, zoom=1.0):
    ms = objs_of(root)
    pts = [o.matrix_world @ Vector(c) for o in ms for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (mn + mx) / 2; ext = max(mx.x - mn.x, mx.y - mn.y, mx.z - mn.z)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.clip_end = 2000; v = VIEWS[key]; d = game_to_b(Vector(v['d'])).normalized()
    if v['ortho']:
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = ext * 1.08 / zoom; cam.location = c + d * 100
        if key == 'top': cam.rotation_euler = (0, 0, math.pi)
        else: cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    else:
        cam.data.type = 'PERSP'; cam.data.lens = 40; cam.location = c + d * (ext * 1.35 / zoom)
        cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.resolution_x = size; sc.render.resolution_y = int(size * 0.72)
    sc.render.filepath = path; bpy.ops.render.render(write_still=True); bpy.data.objects.remove(cam)

views = os.environ.get('B_VIEWS', '3q,3q_rear,side').split(',')
for n, (M, root) in models.items():
    for n2, (_, r2) in models.items():
        for o in [r2] + list(r2.children_recursive): o.hide_render = (n2 != n)
    for vw in views: shoot(os.path.join(REV, '%s_%s.png' % (n, vw)), vw, root, int(os.environ.get('B_SIZE', '800')))
print('DONE')
