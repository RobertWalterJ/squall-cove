"""Showcase: the archipelago terrain dressed with generated assets, lit by the golden-hour skybox."""
import sys, os, math, random
sys.path.insert(0, '/home/claude/procgen')
import numpy as np
from pg_core import *
import pg_boats as B, pg_harbour as Hb, pg_nature as Nt, pg_cargo as C
exec(open('/home/claude/procgen/build_terrain.py').read().split('objs = []')[0].split('reset()')[1].replace('\nreset()', ''), globals()) if False else None
OUT = '/home/claude/procgen/out/terrain'
COLS = np.array([[0.85, 0.77, 0.56], [0.42, 0.55, 0.27], [0.52, 0.49, 0.45], [0.93, 0.94, 0.96]])
reset()
src = open('/home/claude/procgen/build_terrain.py').read()
exec(src[src.index('def terrain_obj'):src.index('objs = []')], globals())
ter, h = terrain_obj('archipelago')
spl = np.load(f'{OUT}/archipelago_splat.npy')
n = h.shape[0]; half = (n - 1) / 2
def H(x, y):
    j = min(max(int(round(x + half)), 0), n - 1); i = min(max(int(round(-y + half)), 0), n - 1)
    return float(h[i, j]), spl[i, j]
rng = random.Random(4)
def inst(src_obj, loc, rotz=0.0, s=1.0):
    o = bpy.data.objects.new(src_obj.name + '_i', src_obj.data); link(o)
    o.location = loc; o.rotation_euler = (0, 0, rotz); o.scale = (s, s, s)
    return o
def hide(o): o.location = (0, 0, -500)
# vegetation
pines = [Nt.pine(seed=s, name=f'p{s}') for s in range(1, 5)]
broads = [Nt.broadleaf(seed=s, name=f'b{s}') for s in (1, 2, 3)]
shrubs = [Nt.shrub(seed=s, name=f's{s}') for s in range(1, 4)]
palms = [Nt.palm(seed=s, name=f'pa{s}') for s in (1, 2)]
for o in pines + broads + shrubs + palms: hide(o)
placed = 0
for k in range(9000):
    x, y = rng.uniform(-120, 120), rng.uniform(-120, 120)
    z, sp = H(x, y)
    if z < 1.5 or sp[1] < 0.55: continue
    if Nt.fbm3(Vector((x * 0.03, y * 0.03, 0.5)), 2) < -0.05: continue
    if z < 4 and rng.random() < 0.5: inst(rng.choice(palms), (x, y, z - 0.2), rng.uniform(0, 6.28), rng.uniform(0.7, 1.0))
    elif z > 9: inst(rng.choice(pines), (x, y, z - 0.2), rng.uniform(0, 6.28), rng.uniform(0.6, 1.1))
    else: inst(rng.choice(broads + shrubs), (x, y, z - 0.2), rng.uniform(0, 6.28), rng.uniform(0.6, 1.1))
    placed += 1
    if placed > 420: break
# shore rocks
rocks = [Nt.boulder(seed=s, name=f'r{s}') for s in range(1, 6)]
for o in rocks: hide(o)
for k in range(4000):
    x, y = rng.uniform(-120, 120), rng.uniform(-120, 120)
    z, sp = H(x, y)
    if -1.5 < z < 1.2 and rng.random() < 0.15: inst(rng.choice(rocks), (x, y, z - 0.3), rng.uniform(0, 6.28), rng.uniform(0.5, 1.4))
# coast point due south for the pier, and a lighthouse headland
def coast(ang):
    for r in np.arange(20, 125, 0.5):
        x, y = math.cos(ang) * r, math.sin(ang) * r
        if H(x, y)[0] < 0: return x, y, r
    return None
cx, cy, cr = coast(-math.pi / 2 + 0.25)
pier_parts = []
for k in range(3):
    p = Hb.pier(seed=k + 1, name=f'pier{k}', length=9.0)
    p.rotation_euler = (0, 0, math.pi / 2 + 0.25)
    d = Vector((math.cos(-math.pi / 2 + 0.25), math.sin(-math.pi / 2 + 0.25), 0))
    p.location = Vector((cx, cy, -0.2)) + d * (9.0 * k - 3)
best = None
for k in range(3000):
    a = rng.uniform(math.pi * 0.8, math.pi * 1.3)
    c_ = coast(a)
    if not c_: continue
    x, y, r = c_
    x2, y2 = x * (r - 6) / r, y * (r - 6) / r
    z = H(x2, y2)[0]
    if best is None or z > best[2]: best = (x2, y2, z)
lh = Hb.lighthouse(seed=1, name='lh'); lh.location = (best[0], best[1], best[2] - 1.0)
# boats in the bay south of the pier
d = Vector((math.cos(-math.pi / 2 + 0.25), math.sin(-math.pi / 2 + 0.25), 0))
side = Vector((-d.y, d.x, 0))
base = Vector((cx, cy, 0)) + d * 24
fleet = [(B.keelboat, 2, side * 10 + d * 6, 0.3), (B.dinghy, 3, -side * 8 + d * 2, 1.2), (B.tug, 1, side * 13 - d * 6, 2.6),
         (B.gaff_cutter, 2, -side * 20 + d * 16, -0.4), (B.workboat, 1, side * 22 - d * 4, 1.9), (B.dory, 2, -side * 4 - d * 10, 0.8)]
for fn, s, off, rz in fleet:
    o = fn(seed=s, name=fn.__name__ + '_show'); o.location = base + off; o.rotation_euler = (0, 0, rz)
# a few containers and crates on the pier head
for k, (fn, s) in enumerate([(C.crate, 1), (C.barrel, 2), (C.crate, 3), (C.drum, 1)]):
    o = fn(seed=s, name=f'cargo{k}'); o.location = Vector((cx, cy, 1.4)) + d * (12 + k * 0.9) + side * 0.6 * (1 if k % 2 else -1)
# water with ripples
bpy.ops.mesh.primitive_plane_add(size=1200, location=(0, 0, 0))
w = bpy.context.active_object
wm = bpy.data.materials.new('sea'); wm.use_nodes = True
nt = wm.node_tree; b = nt.nodes['Principled BSDF']
b.inputs['Base Color'].default_value = (0.02, 0.12, 0.15, 1); b.inputs['Roughness'].default_value = 0.06
b.inputs['Transmission Weight'].default_value = 0.55; b.inputs['IOR'].default_value = 1.333
tc = nt.nodes.new('ShaderNodeTexCoord'); wv = nt.nodes.new('ShaderNodeTexNoise'); wv.inputs['Scale'].default_value = 0.35; wv.inputs['Detail'].default_value = 6
nt.links.new(tc.outputs['Object'], wv.inputs['Vector'])
bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.12; bp.inputs['Distance'].default_value = 0.3
nt.links.new(wv.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
w.data.materials.append(wm)
bpy.ops.mesh.primitive_plane_add(size=1200, location=(0, 0, -9.3))
sb = bpy.context.active_object; sb.data.materials.append(mat('seabed', '#8a7d5a', 1.0))
# skybox world
sc = bpy.context.scene
world = bpy.data.worlds.new('sky'); sc.world = world; world.use_nodes = True
env = world.node_tree.nodes.new('ShaderNodeTexEnvironment')
env.image = bpy.data.images.load('/home/claude/skybox_golden_hour_4k.hdr')
mp = world.node_tree.nodes.new('ShaderNodeMapping'); tco = world.node_tree.nodes.new('ShaderNodeTexCoord')
mp.inputs['Rotation'].default_value = (0, 0, math.radians(float(os.environ.get('SKYROT', '120'))))
world.node_tree.links.new(tco.outputs['Generated'], mp.inputs['Vector']); world.node_tree.links.new(mp.outputs['Vector'], env.inputs['Vector'])
world.node_tree.links.new(env.outputs['Color'], world.node_tree.nodes['Background'].inputs['Color'])
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.6
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); link(sun)
sun.data.energy = 4.0; sun.data.angle = math.radians(1.5); sun.data.color = (1.0, 0.78, 0.55)
sun.rotation_euler = (math.radians(74), 0, math.radians(float(os.environ.get('SUNZ', '-60'))))
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); link(cam); sc.camera = cam
cam.data.lens = 30; cam.data.clip_end = 3000
target = Vector((cx, cy, 2)) + d * 8
cam.location = target + d * 70 + side * 38 + Vector((0, 0, 26))
cam.rotation_euler = (target + Vector((0, 0, 6)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('SAMPLES', '40')); sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'
sc.render.filepath = '/home/claude/procgen/out/showcase.png'
bpy.ops.render.render(write_still=True)
