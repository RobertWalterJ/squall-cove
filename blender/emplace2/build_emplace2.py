"""Builds the emplacement / guard-tower set, exports assets/emplace2.glb (+ .b64.txt, one line) and renders review images.
  blender.exe -b --python build_emplace2.py -- GAME_ASSETS_DIR REVIEW_DIR [models comma list] [--norender] [--noexport]
Env: B_VIEWS=3q,3q_rear@up,side  (view[@pose])  B_SIZE=800  B_SAMPLES=12
Game coords: +Z forward, +Y up, +X = model's left, metres.
"""
import bpy, sys, os, math, base64
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from mathutils import Vector
import e_lib as EL
import e_guns, e_towers
L = EL.L

argv = sys.argv[sys.argv.index('--') + 1:]
pos = [a for a in argv if not a.startswith('--')]
GAME, REV = pos[0], pos[1]
ALL = ['emp_aa', 'emp_mg', 'emp_mortar', 'emp_howitzer', 'emp_flak', 'tower_guard_wood', 'tower_guard_concrete', 'tower_guard_steel',
       'ladder_4m', 'ladder_8m', 'ladder_hoops_6m']
names = pos[2].split(',') if len(pos) > 2 else ALL
os.makedirs(GAME, exist_ok=True); os.makedirs(REV, exist_ok=True)
FUN = {}
for mod in (e_guns, e_towers):
    for n in dir(mod):
        if n in ALL: FUN[n] = getattr(mod, n)

L.reset(); EL.palette()
models = {}
for n in names:
    M = FUN[n](); root = M.build(); models[n] = (M, root)
    print('MODEL', n, 'tris', M.total(), [(x['name'], x['part'].tris()) for x in M.nodes if x['part']])
    if M.total() >= 8000: print('OVER BUDGET', n)

glb = os.path.join(GAME, 'emplace2.glb')
if '--noexport' not in argv:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=glb, use_selection=True, export_apply=True, export_yup=True, export_extras=False,
                              export_cameras=False, export_lights=False, export_image_format='NONE', export_materials='EXPORT')
    open(os.path.join(GAME, 'emplace2.glb.b64.txt'), 'w').write(base64.b64encode(open(glb, 'rb').read()).decode('ascii'))
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

# poses: node -> (kind, value). kinds: yaw (deg, about game Y), elev (deg, barrel up; rotation.x = -elev), rec (m along game -Z)
POSES = {
    'emp_aa': {'up': {'emp_aa_yaw': ('yaw', 35), 'emp_aa_pitch': ('elev', 55), 'emp_aa_barrels': ('rec', 0.12)},
               'vert': {'emp_aa_yaw': ('yaw', -60), 'emp_aa_pitch': ('elev', 85)},
               'down': {'emp_aa_yaw': ('yaw', 20), 'emp_aa_pitch': ('elev', -10)}},
    'emp_mg': {'up': {'emp_mg_yaw': ('yaw', 30), 'emp_mg_pitch': ('elev', 35), 'emp_mg_barrel': ('rec', 0.04)},
               'down': {'emp_mg_yaw': ('yaw', -25), 'emp_mg_pitch': ('elev', -15)}},
    'emp_mortar': {'up': {'emp_mortar_yaw': ('yaw', 0), 'emp_mortar_pitch': ('elev', 65)},
                   'low': {'emp_mortar_yaw': ('yaw', 40), 'emp_mortar_pitch': ('elev', 45)},
                   'high': {'emp_mortar_yaw': ('yaw', -30), 'emp_mortar_pitch': ('elev', 85)}},
    'emp_howitzer': {'up': {'emp_howitzer_yaw': ('yaw', 25), 'emp_howitzer_pitch': ('elev', 40), 'emp_howitzer_barrel': ('rec', 0.45)},
                     'vert': {'emp_howitzer_yaw': ('yaw', -35), 'emp_howitzer_pitch': ('elev', 80)},
                     'down': {'emp_howitzer_yaw': ('yaw', 0), 'emp_howitzer_pitch': ('elev', -10)}},
    'emp_flak': {'up': {'emp_flak_yaw': ('yaw', 40), 'emp_flak_pitch': ('elev', 50), 'emp_flak_barrel': ('rec', 0.1)},
                 'down': {'emp_flak_yaw': ('yaw', -20), 'emp_flak_pitch': ('elev', -10)}},
    'tower_guard_wood': {'lamp': {'tower_guard_wood_lamp': ('yaw', 35)}},
    'tower_guard_steel': {'lamp': {'tower_guard_steel_lamp': ('yaw', 30)}},
}

def apply_pose(root, pose, undo=False):
    for nm, (kind, val) in (POSES.get(root.name, {}).get(pose, {}) or {}).items():
        o = bpy.data.objects[nm]
        if kind == 'yaw': o.rotation_euler = (0, 0, 0 if undo else math.radians(val))
        elif kind == 'elev': o.rotation_euler = (0 if undo else -math.radians(val), 0, 0)
        elif kind == 'rec':
            if not hasattr(o, '_base'): pass
            o.location = o.location + Vector((0, (-1 if undo else 1) * val, 0))
    bpy.context.view_layer.update()

VIEWS = {
    'side':  dict(d=(1, 0, 0), ortho=True), 'front': dict(d=(0, 0, 1), ortho=True), 'top': dict(d=(0, 1, 0), ortho=True),
    '3q': dict(d=(0.8, 0.55, 0.85), ortho=False), '3q_rear': dict(d=(-0.8, 0.5, -0.85), ortho=False), '3q_low': dict(d=(0.9, 0.1, 0.8), ortho=False),
    '3q_left': dict(d=(-0.85, 0.35, 0.8), ortho=False), 'rear': dict(d=(0, 0.3, -1), ortho=False),
}
def shoot(path, key, root, size, zoom=1.0, aim=None):
    ms = objs_of(root)
    pts = [o.matrix_world @ Vector(c) for o in ms for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (mn + mx) / 2; ext = max(mx.x - mn.x, mx.y - mn.y, mx.z - mn.z)
    if aim is not None: c = Vector(L.b_of(aim)); ext = float(os.environ.get('B_EXT', '4'))
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.clip_end = 2000; v = VIEWS[key]; d = game_to_b(Vector(v['d'])).normalized()
    if v['ortho']:
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = ext * 1.08 / zoom; cam.location = c + d * 100
        if key == 'top': cam.rotation_euler = (0, 0, math.pi)
        else: cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    else:
        cam.data.type = 'PERSP'; cam.data.lens = 40; cam.location = c + d * (ext * 1.75 / zoom)
        cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.resolution_x = size; sc.render.resolution_y = int(size * 0.72)
    sc.render.filepath = path; bpy.ops.render.render(write_still=True); bpy.data.objects.remove(cam)

views = os.environ.get('B_VIEWS', '3q,3q_rear').split(',')
aim = None
if os.environ.get('B_AIM'): aim = tuple(float(t) for t in os.environ['B_AIM'].split(','))
for n, (M, root) in models.items():
    for n2, (_, r2) in models.items():
        for o in [r2] + list(r2.children_recursive): o.hide_render = (n2 != n)
    for vw in views:
        key, _, pose = vw.partition('@')
        if pose: apply_pose(root, pose)
        shoot(os.path.join(REV, '%s_%s.png' % (n, vw.replace('@', '_'))), key, root, int(os.environ.get('B_SIZE', '800')), float(os.environ.get('B_ZOOM', '1')), aim)
        if pose: apply_pose(root, pose, undo=True)
print('DONE')
