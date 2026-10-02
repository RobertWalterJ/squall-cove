"""Build Coast Guard ships and render side / plan / three-quarter views for checking against photographs.
  blender -b --python ccg_review.py -- OUTDIR MODULE KEY [KEY ...]      (MODULE: pg_marine, pg_marine_v1 or pg_boats; KEY: a fleet key, or petrel/kestrel/bollard for pg_boats)
Writes OUTDIR/KEY.glb and OUTDIR/KEY_side.png (bow LEFT, like the reference photos), KEY_plan.png, KEY_3q.png."""
import bpy, sys, os, math, importlib
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pg_core import *

argv = sys.argv[sys.argv.index('--') + 1:]
OUT, MODN, KEYS = argv[0], argv[1], argv[2:]
os.makedirs(OUT, exist_ok=True)
M = importlib.import_module(MODN)
BOATS = {'petrel': ('dinghy', 1), 'kestrel': ('keelboat', 4), 'bollard': ('tug', 1), 'gaff_cutter': ('gaff_cutter', 1), 'dory': ('dory', 1), 'workboat': ('workboat', 1)}   # pg_boats keys
SAMPLES = int(os.environ.get('CCG_SAMPLES', '14'))

def setup_scene():
    sc = bpy.context.scene
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.80, 0.83, 0.86, 1); bg.inputs[1].default_value = 1.0
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); link(sun)
    sun.data.energy = 3.0; sun.data.angle = math.radians(5); sun.rotation_euler = (math.radians(52), math.radians(8), math.radians(-35))
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.film_transparent = False
    return sc

def shoot(sc, path, kind, o):
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb))); mx = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
    c = (mn + mx) / 2; L = mx.x - mn.x; B = mx.y - mn.y; H = mx.z - mn.z
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); link(cam); sc.camera = cam; cam.data.type = 'ORTHO'; cam.data.clip_end = 5000
    if kind == 'side':
        cam.location = (c.x, c.y + L * 2, c.z); cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.ortho_scale = L * 1.06; res = (1600, int(1600 * (H * 1.12) / (L * 1.06)))
    elif kind == 'plan':
        cam.location = (c.x, c.y, mx.z + 300); cam.rotation_euler = (0, 0, math.pi)
        cam.data.ortho_scale = L * 1.06; res = (1600, int(1600 * (B * 1.15) / (L * 1.06)))
    else:   # three-quarter from the starboard bow quarter... the camera sits on +Y/+X so the bow points to the viewer's right-front
        d = Vector((0.75, 0.9, 0.55)).normalized(); cam.location = c + d * L * 2
        cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.ortho_scale = max(L * 0.95, H * 0.95); res = (1500, 1000)      # tall rigs set the framing, not the hull
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)

for key in KEYS:
    reset()
    o = getattr(M, BOATS[key][0])(seed=BOATS[key][1], name=key) if MODN == 'pg_boats' else M.build(key); o.name = key
    export_glb([o], os.path.join(OUT, key + '.glb'))
    print('SHIP', key, 'dims', dims(o), 'tris', tri_count(o))
    sc = setup_scene()
    for kind in ('side', 'plan', '3q'):
        shoot(sc, os.path.join(OUT, f'{key}_{kind}.png'), kind, o)
print('REVIEW DONE')
