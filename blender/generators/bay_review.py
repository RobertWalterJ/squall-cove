"""Perspective review renders for the Bay-class lifeboat.  blender -b --python bay_review.py -- OUTDIR [tag]
Writes OUTDIR/bay_<tag>_{side,plan,front,bow3q,stern3q,high}.png"""
import bpy, sys, os, math
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pg_core import *
import pg_marine as M
argv = sys.argv[sys.argv.index('--') + 1:]; OUT = argv[0]; TAG = argv[1] if len(argv) > 1 else 'x'
os.makedirs(OUT, exist_ok=True)
reset(); o = M.build('bay_class'); o.name = 'bay_hull'
print('DIMS', dims(o), 'TRIS', tri_count(o), [a.name for a in M.ANIM])
sc = bpy.context.scene
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.55, 0.68, 0.82, 1); bg.inputs[1].default_value = 1.0
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); link(sun)
sun.data.energy = 3.5; sun.data.angle = math.radians(5); sun.rotation_euler = (math.radians(50), math.radians(8), math.radians(-40))
sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('CCG_SAMPLES', '16')); sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'AgX'
# a flat sea plane at z=0 so the waterline reads
sea = bpy.data.objects.new('sea', bpy.data.meshes.new('sea')); link(sea)
sea.data.from_pydata([(-60, -60, -0.0), (60, -60, 0), (60, 60, 0), (-60, 60, 0)], [], [(0, 1, 2, 3)]); sea.data.materials.append(mat('sea', '#2c5a78', 0.2))
def shoot(name, loc, target, ortho=None, res=(1500, 1000), lens=45):
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); link(cam); sc.camera = cam
    cam.location = loc; cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); cam.data.clip_end = 500
    if ortho: cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho
    else: cam.data.lens = lens
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.filepath = os.path.join(OUT, f'bay_{TAG}_{name}.png'); bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
c = (0, 0, 2.2)
shoot('side', (0, -60, 2.8), (0, 0, 2.8), ortho=21, res=(1600, 800))
shoot('plan', (0, 0, 60), (0, 0, 0), ortho=21, res=(1600, 800))
shoot('front', (40, 0, 4), (0, 0, 3.2), lens=60, res=(1000, 1000))
shoot('bow3q', (22, -16, 11), c, lens=50)
shoot('stern3q', (-22, 17, 9), c, lens=50)
shoot('high', (3, -18, 24), (0, 0, 2), lens=50)
print('REVIEW DONE')
