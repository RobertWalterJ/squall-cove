import sys, os, json, math
sys.path.insert(0, '/home/claude/procgen')
import numpy as np
from pg_core import *
from pg_sheet import label
OUT = '/home/claude/procgen/out/terrain'
NAMES = ['archipelago', 'alpine', 'hills', 'mesa', 'cliffs', 'volcano']
COLS = np.array([[0.85, 0.77, 0.56], [0.42, 0.55, 0.27], [0.52, 0.49, 0.45], [0.93, 0.94, 0.96]])
reset()
def terrain_obj(name, step=1, src=None):
    src = src or name
    h = np.load(f'{OUT}/{src}_h.npy')[::step, ::step]; spl = np.load(f'{OUT}/{src}_splat.npy')[::step, ::step]
    n = h.shape[0]; cell = 1.0 * step
    xs = (np.arange(n) - (n - 1) / 2) * cell
    X, Y = np.meshgrid(xs, -xs)
    verts = np.dstack([X, Y, h]).reshape(-1, 3)
    idx = np.arange(n * n).reshape(n, n)
    a, b, c, d = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()
    faces = np.stack([a, d, c, b], 1)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts)); me.vertices.foreach_set('co', verts.astype(np.float32).ravel())
    me.loops.add(faces.size); me.loops.foreach_set('vertex_index', faces.astype(np.int32).ravel())
    me.polygons.add(len(faces)); me.polygons.foreach_set('loop_start', np.arange(0, faces.size, 4, dtype=np.int32)); me.polygons.foreach_set('loop_total', np.full(len(faces), 4, np.int32))
    me.update(); me.validate()
    rgb = (spl[..., :, None] * COLS[None, None]).sum(axis=2).reshape(-1, 3)
    # subtle per-vertex variation, darker underwater
    rgb *= (0.92 + 0.16 * np.random.default_rng(1).random((len(rgb), 1)))
    under = verts[:, 2] < -0.3
    rgb[under] = rgb[under] * 0.75 + np.array([0.55, 0.5, 0.35]) * 0.25
    rgb = np.clip(rgb, 0, 1)
    lin_ = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', np.hstack([lin_, np.ones((len(lin_), 1))]).astype(np.float32).ravel())
    o = bpy.data.objects.new(name, me); link(o)
    me.materials.append(mat('terrain', '#ffffff', 0.95, vcol=True))
    for p in me.polygons: p.use_smooth = False
    return o, h
objs = []
gap = 40; tile = 256
for i, n in enumerate(NAMES):
    # game-ready copy at half resolution (129 x 129) for GLB, full res for the render
    lo, _ = terrain_obj(n + '_lod1', 2, n)
    export_glb([lo], f'{OUT}/{n}_terrain_129.glb'); bpy.data.objects.remove(lo)
    o, h = terrain_obj(n)
    meta = json.load(open(f'{OUT}/{n}.json'))
    cx, cy = (i % 3) * (tile + gap), -(i // 3) * (tile + gap + 60)
    o.location = (cx, cy, 0)
    if meta['sea_level'] is not None:
        bpy.ops.mesh.primitive_plane_add(size=tile, location=(cx, cy, 0.0))
        w = bpy.context.active_object; w.data.materials.append(mat('water', '#2f7f8c', 0.08, alpha=0.82, transmission=0.0))
    # skirt so the tile reads as a block
    lowest = float(h.min()) - 6
    label(f'{n}', (cx, cy - tile / 2 - 30, lowest), 16, 0)
    objs.append(o)
sc = bpy.context.scene
world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (0.6, 0.65, 0.72, 1)
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); link(sun)
sun.data.energy = 3.5; sun.data.angle = math.radians(2); sun.data.color = (1, 0.92, 0.82)
sun.rotation_euler = (math.radians(58), 0, math.radians(-40))
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); link(cam); sc.camera = cam
cam.data.type = 'ORTHO'
cen = Vector(((tile + gap), -(tile + gap + 60) / 2, 0))
el = math.radians(38)
d = Vector((0, -math.cos(el), math.sin(el)))
cam.location = cen + d * 2000; cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
cam.data.ortho_scale = 3 * tile + 2 * gap + 40; cam.data.clip_end = 6000
sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1800, 1000
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.render.filepath = f'{OUT}/terrain_sheet.png'
bpy.ops.render.render(write_still=True)
