"""Contact-sheet renderer and exporter shared by every asset class."""
import bpy, math, os, json
from mathutils import Vector
from pg_core import *

def lay_out(items, cols, gap=1.0, cell=None, el=30):
    """items: list of (label, obj). Grid in XY, each object's footprint centred in its cell and resting on z=0."""
    sizes = []
    for _, o in items:
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        mn = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
        mx = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
        sizes.append((mn, mx))
    cw = cell or max(max(mx.x - mn.x, mx.y - mn.y) for mn, mx in sizes) + gap
    rows = math.ceil(len(items) / cols)
    maxh = max(mx.z - mn.z for mn, mx in sizes)
    rs = max(cw, cw * 0.75 + maxh / math.tan(math.radians(el)))
    for i, ((label, o), (mn, mx)) in enumerate(zip(items, sizes)):
        cx, cy = (i % cols) * cw, -(i // cols) * rs
        c = (mn + mx) / 2
        o.location += Vector((cx - c.x, cy - c.y, -mn.z))
    return cw, rows, rs

def label(text, loc, size, rotz):
    bpy.ops.object.text_add(location=loc, rotation=(0, 0, rotz))
    t = bpy.context.active_object
    t.data.body = text; t.data.size = size; t.data.align_x = 'CENTER'; t.data.extrude = 0.0
    t.data.materials.append(mat('label', '#2b2b2b', 0.9))
    return t

def render_sheet(items, cols, out_png, title=None, gap=1.0, cell=None, elev=30, azim=0, res=(1800, 1150), samples=32, labels=True, obj_rot=35):
    for _, o in items:
        o.rotation_euler.z += math.radians(obj_rot)
    bpy.context.view_layer.update()
    cw, rows, rs = lay_out(items, cols, gap, cell, elev)
    W, H = cols * cw, rows * rs
    centre = Vector(((cols - 1) * cw / 2, -(rows - 1) * rs / 2, 0))
    az = math.radians(azim); el = math.radians(elev)
    dh = Vector((math.cos(el) * math.sin(az) * -1, -math.cos(el) * math.cos(az), 0)).normalized()
    if labels:
        for i, (lab, o) in enumerate(items):
            cx, cy = (i % cols) * cw, -(i // cols) * rs
            p = Vector((cx, cy, 0.01)) + dh * cw * 0.42
            label(lab, tuple(p), cw * 0.05, math.atan2(dh.x, -dh.y))
    # ground
    bpy.ops.mesh.primitive_plane_add(size=max(W, H) * 6, location=(centre.x, centre.y, -0.001))
    g = bpy.context.active_object; g.data.materials.append(mat('ground', '#d9d4c9', 0.95))
    # world + light
    sc = bpy.context.scene
    world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
    bg = world.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.62, 0.66, 0.72, 1); bg.inputs[1].default_value = 0.9
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); link(sun)
    sun.data.energy = 3.2; sun.data.angle = math.radians(4); sun.data.color = (1.0, 0.93, 0.84)
    sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    # camera: orthographic, looking from the starboard-bow quarter
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'
    d = Vector((math.cos(el) * math.sin(az) * -1, -math.cos(el) * math.cos(az), math.sin(el)))
    cam.location = centre + d * (max(W, H) * 3) + Vector((0, 0, 1.0))
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    aspect = res[0] / res[1]
    bpy.context.view_layer.update()
    inv = cam.matrix_world.inverted()
    pts = []
    for o in bpy.context.scene.objects:
        if o.type in ('MESH', 'FONT') and o.name != g.name:
            pts += [inv @ (o.matrix_world @ Vector(c)) for c in o.bound_box]
    x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
    y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
    cam.location = cam.matrix_world @ Vector(((x0 + x1) / 2, (y0 + y1) / 2, 0))
    cam.data.sensor_fit = 'HORIZONTAL'
    cam.data.ortho_scale = (x1 - x0) * 1.06
    res = (res[0], int(min(4400, max(500, res[0] * (y1 - y0) * 1.1 / ((x1 - x0) * 1.06)))))
    cam.data.clip_end = 10000
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.filepath = out_png
    bpy.ops.render.render(write_still=True)

def report(items):
    return [dict(name=o.name, label=lab, tris=tri_count(o), dims_m=dims(o), materials=len(o.data.materials)) for lab, o in items]
