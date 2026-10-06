"""Review renders for the aircraft: orthographic side / plan / front / rear and perspective 3/4 high, 3/4 low (Cycles, CPU)."""
import bpy, math, os
from mathutils import Vector
from pg_core import link

def setup_scene(samples=16):
    sc = bpy.context.scene
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; bg = nt.nodes['Background']
    # gradient sky: light blue-grey above, warm ground below
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); ramp = nt.nodes.new('ShaderNodeValToRGB')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0]); nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (0.30, 0.28, 0.25, 1)
    ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = (0.70, 0.80, 0.95, 1)
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 1.0
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); link(sun)
    sun.data.energy = 3.4; sun.data.angle = math.radians(4); sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-40))
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = -0.1
    sc.render.image_settings.file_format = 'PNG'
    return sc

def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))), Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))

VIEWS = {
    'side':  dict(d=(0, -1, 0.0), ortho=True),       # looking at the starboard side
    'port':  dict(d=(0, 1, 0.0), ortho=True),
    'front': dict(d=(1, 0, 0.0), ortho=True),
    'rear':  dict(d=(-1, 0, 0.0), ortho=True),
    'plan':  dict(d=(0, 0, 1), ortho=True),
    'belly': dict(d=(0, 0, -1), ortho=True),
    '3q_high': dict(d=(0.75, -0.85, 0.55), ortho=False),
    '3q_low': dict(d=(0.8, -0.8, -0.18), ortho=False),
    '3q_rear': dict(d=(-0.75, -0.8, 0.45), ortho=False),
    '3q_port': dict(d=(0.8, 0.8, 0.35), ortho=False),
    'frontlow': dict(d=(1.0, -0.45, -0.22), ortho=False),
    'fronthigh': dict(d=(1.0, 0.5, 0.35), ortho=False),
}

def shoot(sc, path, kind, objs, size=1500, zoom=1.0, target=None):
    mn, mx = bounds(objs); c = (mn + mx) / 2 if target is None else Vector(target)
    L, B, H = mx.x - mn.x, mx.y - mn.y, mx.z - mn.z
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); link(cam); sc.camera = cam
    cam.data.clip_end = 5000; v = VIEWS[kind]; d = Vector(v['d']).normalized()
    cam.location = c + d * 150
    if v['ortho']:
        cam.data.type = 'ORTHO'
        up = 'Y'
        cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
        if kind in ('plan', 'belly'):
            cam.rotation_euler = (0, 0, -math.pi / 2 if kind == 'plan' else -math.pi / 2)
            if kind == 'belly': cam.rotation_euler = (math.pi, 0, -math.pi / 2)
        ext = {'side': (L, H), 'port': (L, H), 'front': (B, H), 'rear': (B, H), 'plan': (L, B), 'belly': (L, B)}[kind]
        cam.data.ortho_scale = max(ext[0], ext[1] * 1.0) * 1.08 / zoom
        res = (size, int(size * ext[1] / ext[0] * 1.0) + 60) if ext[0] >= ext[1] else (int(size * ext[0] / ext[1]) + 60, size)
        if kind in ('front', 'rear'): res = (size, int(size * (H * 1.08) / (max(B, H) * 1.08)) + 40); cam.data.ortho_scale = max(B, H) * 1.08 / zoom
        if kind in ('plan', 'belly'): res = (size, int(size * L / B) + 40)
        res = (max(res[0], 400), max(res[1], 300))
    else:
        cam.data.type = 'PERSP'; cam.data.lens = 38
        cam.location = c + d * (max(L, B * 0.8, H * 1.2) * 1.12 / zoom)
        cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler(); res = (size, int(size * 0.68))
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path; bpy.ops.render.render(write_still=True); bpy.data.objects.remove(cam)
