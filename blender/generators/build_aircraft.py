"""Build the two aircraft and render views for checking against the reference photographs and drawings.
  blender -b --python build_aircraft.py -- GAME_DIR REVIEW_DIR
Writes GAME_DIR/aircraft.glb (nodes cormorant_hull, cormorant_rotor0, cormorant_tail0, cormorant_winch0, cl415_hull, cl415_prop0, cl415_prop1)
and REVIEW_DIR/<model>_{side,plan,front,3q}.png."""
import bpy, sys, os, math
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pg_core import *
import pg_aircraft as A

GAME, REV = sys.argv[sys.argv.index('--') + 1:][:2]
os.makedirs(GAME, exist_ok=True); os.makedirs(REV, exist_ok=True)
MODELS = [('cormorant', A.cormorant, 'cormorant_hull'), ('cl415', A.cl415, 'cl415_hull')]
reset(); allobjs = []; built = {}
for key, fn, nm in MODELS:
    hull = fn(); hull.name = nm; parts = list(A.ANIM); built[key] = (hull, parts); allobjs += [hull] + parts
    print('MODEL', key, dims(hull), tri_count(hull), [p.name for p in parts])
export_glb(allobjs, os.path.join(GAME, 'aircraft.glb'))
# review renders: hide the other model while each is photographed
def setup_scene():
    sc = bpy.context.scene; w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.80, 0.83, 0.86, 1); bg.inputs[1].default_value = 1.0
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); link(sun); sun.data.energy = 3.2; sun.data.angle = math.radians(5); sun.rotation_euler = (math.radians(52), math.radians(8), math.radians(-35))
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = int(os.environ.get('AC_SAMPLES', '12')); sc.cycles.use_denoising = True
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; return sc
def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))), Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
def shoot(sc, path, kind, objs):
    mn, mx = bounds(objs); c = (mn + mx) / 2; L, B, H = mx.x - mn.x, mx.y - mn.y, mx.z - mn.z
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); link(cam); sc.camera = cam; cam.data.type = 'ORTHO'; cam.data.clip_end = 5000
    if kind == 'side':
        cam.location = (c.x, c.y + 200, c.z); cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler(); cam.data.ortho_scale = max(L, H) * 1.1; res = (1600, int(1600 * H * 1.1 / (max(L, H) * 1.1)) + 80)
    elif kind == 'plan':
        cam.location = (c.x, c.y, mx.z + 200); cam.rotation_euler = (0, 0, math.pi); cam.data.ortho_scale = max(L, B) * 1.08; res = (1600, int(1600 * B * 1.08 / (max(L, B) * 1.08)) + 80)
    elif kind == 'front':
        cam.location = (c.x + 200, c.y, c.z); cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler(); cam.data.ortho_scale = max(B, H) * 1.1; res = (1600, int(1600 * H * 1.1 / (max(B, H) * 1.1)) + 80)
    else:
        d = Vector((0.8, 0.9, 0.5)).normalized(); cam.location = c + d * 120; cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler(); cam.data.ortho_scale = max(L, B, H) * 0.95; res = (1500, 1000)
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.filepath = path; bpy.ops.render.render(write_still=True); bpy.data.objects.remove(cam)
if os.environ.get('AC_NORENDER'):
    print('AIRCRAFT DONE (no renders)'); sys.exit(0)
sc = setup_scene()
for key, (hull, parts) in built.items():
    objs = [hull] + parts
    for k2, (h2, p2) in built.items():
        for o in [h2] + p2: o.hide_render = (k2 != key)
    for kind in ('side', 'plan', 'front', '3q'): shoot(sc, os.path.join(REV, f'{key}_{kind}.png'), kind, objs)
print('AIRCRAFT DONE')
