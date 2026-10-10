"""Squall Cove fire sprites, Blender Mantaflow track.

Run (one Blender at a time):
  blender.exe --background --factory-startup --python bake_fire.py -- PRESET WORKDIR [--res N] [--frames N] [--samples N] [--warm N]

Bakes a Mantaflow gas domain (fuel + heat + flame + smoke), then renders three
looping-window layers with Cycles (orthographic, front-on, transparent):
  flame  = blackbody-style emission driven by the flame attribute
  smoke  = scattering volume driven by density, neutral grey lighting
  heat   = grey emission of flame/temperature (thermal / night vision)
Layers are written as float16 .npy files in WORKDIR/PRESET/ for pack_atlas.py.
"""
import sys, os, time, math, random
import bpy, bmesh
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
PRESET = argv[0]
WORK = argv[1]
def opt(name, default, cast=int):
    return cast(argv[argv.index(name) + 1]) if name in argv else default

LOOP = 44                              # output frames in the loop
XFADE = 12                             # crossfade frames
FPS = 24

# Per preset: domain height H (m; width = depth = 2H/3), sim res on the tall axis,
# source shape, flame/smoke parameters. Heights/widths match the sprite world size.
PRESETS = {
    'campfire': dict(H=3.0, res=112, shape='sphere', pos=(0, 0, 0.30), size=(0.42, 0.42, 0.25),
        flow='BOTH', fuel=1.0, temp=1.0, dens=0.6, surf=1.6, vel=0.0,
        burn=0.9, fsmoke=0.7, fvort=0.55, ign=1.25, maxt=2.6, vort=0.28, alpha=1.0, beta=1.6,
        smokecol=(0.35, 0.33, 0.31), blue_h=0.0, flame_k=5.0, smoke_k=7.0, flame_gain=1.0, warm=1.0,
        wind=(0.0, 0.0, 0.0), flicker=0.35),
    'gas': dict(H=3.0, res=112, shape='cylinder', pos=(0, 0, 0.10), size=(0.14, 0.14, 0.03),
        flow='BOTH', fuel=0.8, temp=1.0, dens=0.0, surf=1.2, vel=1.6, flame_pow=1.0,
        burn=0.9, fsmoke=0.04, fvort=0.22, ign=1.3, maxt=3.0, vort=0.14, alpha=0.2, beta=2.0,
        smokecol=(0.5, 0.5, 0.5), blue_h=1.1, flame_k=9.0, smoke_k=2.0, flame_gain=1.0, warm=0.7,
        wind=(0.0, 0.0, 0.0), flicker=0.12),
    # --- wide/low pool: 6 m x 4 m frame, flames up to ~2 m
    'pool': dict(H=9.0, fw=128, fh=192, res=88, warmup=120, shape='cylinder', pos=(0, 0, 0.10), size=(1.5, 1.5, 0.05),
        flow='BOTH', fuel=2.2, temp=1.0, dens=2.4, surf=1.5, vel=0.0, dissolve=0,
        burn=0.5, fsmoke=3.2, fvort=0.8, ign=1.2, maxt=2.5, vort=0.35, alpha=1.2, beta=1.5,
        smokecol=(0.07, 0.065, 0.06), blue_h=0.0, flame_k=5.0, smoke_k=7.0, flame_gain=0.95, warm=1.0,
        flicker=0.3),
    # --- vehicle: 6.9 m x 5 m frame, ~4 m long body, flames 1.5-3 m, engine bay hot spot
    'vehicle': dict(H=9.0, fw=160, fh=192, res=96, D=7.5, dissolve=0, warmup=80,
        srcs=[('box', (0, 0, 0.85), (1.9, 0.8, 0.30), 1.0), ('box', (-1.6, 0, 1.35), (0.55, 0.6, 0.25), 1.6)],
        flow='BOTH', fuel=1.0, temp=1.0, dens=2.0, surf=1.5, vel=0.0,
        burn=0.8, fsmoke=2.8, fvort=0.7, ign=1.2, maxt=2.5, vort=0.30, alpha=1.1, beta=1.5,
        smokecol=(0.09, 0.085, 0.08), blue_h=0.0, flame_k=5.0, smoke_k=6.0, flame_gain=0.95, warm=1.0,
        flicker=0.3),
    # --- building: 16 m x 16 m frame; three window flames + a roof fire
    'building': dict(H=16.0, fw=160, fh=160, res=80, D=10.0, warmup=110, dissolve=0,
        srcs=[('box', (-4.2, 0, 3.2), (0.7, 0.35, 0.9), 1.3), ('box', (0, 0, 3.2), (0.7, 0.35, 0.9), 1.1),
              ('box', (4.2, 0, 3.2), (0.7, 0.35, 0.9), 1.2), ('box', (0, 0, 7.6), (3.4, 1.0, 0.25), 0.7)],
        flow='BOTH', fuel=1.0, temp=1.0, dens=1.2, surf=1.5, vel=0.15,
        burn=0.75, fsmoke=1.5, fvort=0.9, ign=1.2, maxt=2.5, vort=0.38, alpha=1.0, beta=1.6,
        smokecol=(0.13, 0.12, 0.115), blue_h=0.0, flame_k=4.5, smoke_k=5.0, flame_gain=0.7, warm=1.0,
        flicker=0.25),
    # --- grass / brush fire front: 4 m wide x 2.5 m high frame, 0.3-1.5 m flames licking along a line
    'grass': dict(H=2.5, fw=256, fh=160, res=128, D=2.0, dissolve=0,
        srcs=[('box', (0, 0, 0.10), (2.3, 0.28, 0.07), 1.0)],
        flow='BOTH', fuel=0.8, temp=1.0, dens=0.5, surf=1.4, vel=0.25,
        burn=1.4, fsmoke=0.6, fvort=1.1, ign=1.1, maxt=2.4, vort=0.5, alpha=0.8, beta=1.4,
        smokecol=(0.25, 0.23, 0.2), blue_h=0.0, flame_k=5.0, smoke_k=6.0, flame_gain=1.0, warm=1.0,
        flicker=0.55),
    # --- tree: crown + trunk fire, 8 m x 12 m frame
    'tree': dict(H=12.0, fw=128, fh=192, res=72, D=8.0, warmup=110, dissolve=0,
        srcs=[('sphere', (0, 0, 6.0), (1.9, 1.9, 2.4), 1.0), ('cylinder', (0, 0, 2.0), (0.35, 0.35, 2.0), 0.7)],
        flow='BOTH', fuel=1.0, temp=1.0, dens=1.0, flame_pow=3.4, surf=1.5, vel=0.0,
        burn=0.75, fsmoke=1.4, fvort=0.9, ign=1.2, maxt=2.5, vort=0.4, alpha=1.0, beta=1.6,
        smokecol=(0.12, 0.11, 0.1), blue_h=0.0, flame_k=5.0, smoke_k=5.0, flame_gain=0.55, warm=1.0,
        flicker=0.35),

    # --- explosion fireball, 8 m class, ONE-SHOT 3 s clip: fuel burst with an outward velocity impulse (game scales for 3 m / 20 m)
    'fireball': dict(H=24.0, fw=128, fh=192, res=72, D=16.0, oneshot=True, frames=72,
        srcs=[('sphere', (0, 0, 2.2), (1.3, 1.3, 1.3), 1.0)], pulse=(16, 5.0),
        flow='BOTH', fuel=1.0, temp=3.0, dens=1.5, surf=2.0, vel=7.0, dissolve=0,
        burn=0.9, fsmoke=1.4, fvort=1.2, ign=1.0, maxt=3.5, vort=0.5, alpha=1.0, beta=1.8,
        smokecol=(0.06, 0.055, 0.05), blue_h=0.0, flame_k=4.0, smoke_k=7.0, flame_gain=0.55, warm=1.0, flicker=0.0),
    # --- carried flame / flaming debris trail: stationary burning chunk in a steady wind (force field with air flow), flame streams back
    'trail_slow': dict(H=2.0, fw=192, fh=128, res=96, D=2.0, wind=5.0, warmup=30,
        srcs=[('sphere', (-1.0, 0, 1.0), (0.10, 0.10, 0.10), 1.0)],
        flow='BOTH', fuel=1.0, temp=1.2, dens=0.5, surf=1.6, vel=0.0,
        burn=0.9, fsmoke=0.6, fvort=0.9, ign=1.2, maxt=2.6, vort=0.3, alpha=0.6, beta=1.0,
        smokecol=(0.2, 0.19, 0.18), blue_h=0.0, flame_k=5.0, smoke_k=5.0, flame_gain=0.55, warm=0.5, flicker=0.3),
    'trail_med': dict(H=2.6, fw=192, fh=128, res=96, D=2.6, wind=11.0, warmup=30,
        srcs=[('sphere', (-1.4, 0, 1.3), (0.12, 0.12, 0.12), 1.0)],
        flow='BOTH', fuel=1.0, temp=1.2, dens=0.5, surf=1.6, vel=0.0,
        burn=0.9, fsmoke=0.6, fvort=0.9, ign=1.2, maxt=2.6, vort=0.3, alpha=0.6, beta=1.0,
        smokecol=(0.2, 0.19, 0.18), blue_h=0.0, flame_k=5.0, smoke_k=5.0, flame_gain=0.55, warm=0.5, flicker=0.3),
    'trail_fast': dict(H=3.4, fw=192, fh=128, res=96, D=3.4, wind=20.0, warmup=30,
        srcs=[('sphere', (-1.9, 0, 1.7), (0.14, 0.14, 0.14), 1.0)],
        flow='BOTH', fuel=1.0, temp=1.2, dens=0.5, surf=1.6, vel=0.0,
        burn=0.9, fsmoke=0.6, fvort=0.9, ign=1.2, maxt=2.6, vort=0.3, alpha=0.6, beta=1.0,
        smokecol=(0.2, 0.19, 0.18), blue_h=0.0, flame_k=5.0, smoke_k=5.0, flame_gain=0.55, warm=0.5, flicker=0.3),
}
P = PRESETS[PRESET]
import ast
for _i, _a in enumerate(argv):
    if _a == '--set':
        _k, _v = argv[_i + 1].split('=', 1); P[_k] = ast.literal_eval(_v)
RES = opt('--res', P['res'])
NFRAMES = opt('--frames', P.get('frames', LOOP))
SAMPLES = opt('--samples', 20)
WARM = opt('--warm', 0 if P.get('oneshot') else P.get('warmup', 36))
if P.get('oneshot'): XFADE = 0
FW, FH = P.get('fw', 128), P.get('fh', 192)
H = P['H']; W = H * FW / FH; D = P.get('D', W)
SRCS = P.get('srcs') or [(P['shape'], P['pos'], P['size'], 1.0)]
total_out = NFRAMES + XFADE            # sim frames rendered
last_frame = WARM + total_out
t0 = time.time()
def log(*a):
    print('[fireb %6.1fs]' % (time.time() - t0), *a, flush=True)

outdir = os.path.join(WORK, PRESET)
os.makedirs(outdir, exist_ok=True)
cache = os.path.join(outdir, 'cache')
os.makedirs(cache, exist_ok=True)

# ---------------------------------------------------------------- scene
RENDERONLY = '--renderonly' in argv
WORKBLEND = os.path.join(outdir, 'work.blend')
if RENDERONLY:
    # the 'baked' flags live in the .blend written right after the bake: start a clean process from it
    bpy.ops.wm.open_mainfile(filepath=WORKBLEND)
    sc = bpy.context.scene
    dom = bpy.data.objects['Domain']
    ds = dom.modifiers['Fluid'].domain_settings
    fuel_objs = [o for o in bpy.data.objects if o.name.startswith('Fuel')]
    fl = fuel_objs[0]
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start = 1
    sc.frame_end = last_frame
    sc.frame_current = 1

    def mesh_obj(name, kind, loc, size):
        bm = bmesh.new()
        if kind == 'sphere':
            bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=1.0)
        elif kind == 'cylinder':
            bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=1.0, radius2=1.0, depth=2.0)
        else:
            bmesh.ops.create_cube(bm, size=2.0)
        for v in bm.verts:
            v.co.x *= size[0]; v.co.y *= size[1]; v.co.z *= size[2]
            v.co += Vector(loc)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(name, me)
        sc.collection.objects.link(ob)
        return ob

    # domain: real size W x W x H, bottom on z=0
    dom = mesh_obj('Domain', 'box', (0, 0, H / 2), (W / 2, D / 2, H / 2))
    bpy.context.view_layer.objects.active = dom
    m = dom.modifiers.new('Fluid', 'FLUID'); m.fluid_type = 'DOMAIN'
    ds = m.domain_settings
    ds.domain_type = 'GAS'
    ds.resolution_max = RES
    ds.use_noise = False
    ds.use_dissolve_smoke = bool(P.get('dissolve'))
    if P.get('dissolve'):
        ds.dissolve_speed = P['dissolve']; ds.use_dissolve_smoke_log = False
    ds.cache_directory = cache
    ds.cache_type = 'ALL'
    ds.cache_frame_start = 1
    ds.cache_frame_end = last_frame
    ds.use_adaptive_timesteps = True
    ds.cfl_condition = 3.0
    ds.alpha = P['alpha']; ds.beta = P['beta']
    ds.vorticity = P['vort']
    ds.burning_rate = P['burn']
    ds.flame_smoke = P['fsmoke']
    ds.flame_vorticity = P['fvort']
    ds.flame_ignition = P['ign']
    ds.flame_max_temp = P['maxt']
    ds.flame_smoke_color = P['smokecol']
    for side, on in (('front', False), ('back', False), ('left', False), ('right', False), ('top', False), ('bottom', True)):
        setattr(ds, 'use_collision_border_' + side, on)

    rnd = random.Random(7)
    fk = P['flicker']
    fuel_objs = []
    if isinstance(P.get('wind'), (int, float)) and P['wind']:
        bpy.ops.object.effector_add(type='WIND', location=(0, 0, H / 2))
        wind = bpy.context.active_object; wind.name = 'Wind'
        wind.rotation_euler = (0, math.pi / 2, 0)           # local +Z -> world +X
        wind.field.type = 'WIND'; wind.field.strength = P['wind']; wind.field.flow = 1.0
    for si, (shape, pos, size, mult) in enumerate(SRCS):
        fl = mesh_obj('Fuel%d' % si, shape, pos, size)
        fl.hide_render = True
        bpy.context.view_layer.objects.active = fl
        fm = fl.modifiers.new('Fluid', 'FLUID'); fm.fluid_type = 'FLOW'
        fs = fm.flow_settings
        fs.flow_type = P['flow']; fs.flow_behavior = 'INFLOW'; fs.flow_source = 'MESH'
        fs.fuel_amount = P['fuel'] * mult; fs.temperature = P['temp']; fs.density = P['dens']
        fs.surface_distance = P['surf']; fs.smoke_color = P['smokecol']
        if P['vel'] > 0:
            fs.use_initial_velocity = True
            fs.velocity_normal = P['vel']
        # gentle seeded fuel flicker (not looped; the crossfade handles the seam)
        if P.get('pulse'):
            pn, pm = P['pulse']
            for f in range(1, pn + 4):
                fs.fuel_amount = P['fuel'] * mult * (pm if f <= pn else 0.0)
                fs.keyframe_insert('fuel_amount', frame=f)
            for f in range(1, pn + 4):
                fs.density = P['dens'] * (1.0 if f <= pn else 0.0)
                fs.keyframe_insert('density', frame=f)
            for f in range(1, pn + 4):
                fs.velocity_normal = P['vel'] * (1.0 if f <= pn else 0.0)
                fs.keyframe_insert('velocity_normal', frame=f)
        else:
          for f in range(1, last_frame + 1, 3):
            fs.fuel_amount = P['fuel'] * mult * (1.0 + fk * (rnd.random() - 0.5) * 2.0)
            fs.keyframe_insert('fuel_amount', frame=f)
        fuel_objs.append(fl)
    fl = fuel_objs[0]

# ---------------------------------------------------------------- bake
log('preset', PRESET, 'res', RES, 'frames', last_frame, 'domain %.2f x %.2f x %.2f m' % (W, D, H))
bpy.context.view_layer.objects.active = dom
dom.select_set(True)
tb = time.time()
if not RENDERONLY:
    for _try in range(12):     # the wind effector makes ViewLayer.update() fail at random: just retry
        try:
            bpy.ops.fluid.bake_data(); break
        except (SystemError, RuntimeError) as _e:
            log('bake retry', _try, str(_e)[:60])
    bpy.ops.wm.save_as_mainfile(filepath=WORKBLEND)          # keep the post-bake file for render-only reruns
t_bake = time.time() - tb
log('BAKE DONE in %.1fs' % t_bake)

# ---------------------------------------------------------------- materials
def new_mat(name):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    return mat, nt, out

def attr(nt, name):
    a = nt.nodes.new('ShaderNodeAttribute'); a.attribute_name = name
    return a

# flame colour ramp, deep red -> orange -> yellow -> pale yellow-white (blackbody-ish, hand-tuned)
def flame_material(heat=False):
    mat, nt, out = new_mat('flame_heat' if heat else 'flame')
    fa = attr(nt, 'flame')
    ta = attr(nt, 'heat')
    em = nt.nodes.new('ShaderNodeEmission')
    # strength shape: flame^1.3 * k
    pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = P.get('flame_pow', 2.2)
    nt.links.new(fa.outputs['Fac'], pw.inputs[0])
    mk = nt.nodes.new('ShaderNodeMath'); mk.operation = 'MULTIPLY'
    mk.inputs[1].default_value = 0.17 * P['flame_k'] * P['flame_gain'] / max(0.2, H / 3.0) ** 0.5
    nt.links.new(pw.outputs[0], mk.inputs[0])
    if heat:
        # grey: scaled so the hottest core is ~1, includes a little of the hot-gas heat field above the flame
        g = nt.nodes.new('ShaderNodeMath'); g.operation = 'ADD'
        hh = nt.nodes.new('ShaderNodeMath'); hh.operation = 'MULTIPLY'; hh.inputs[1].default_value = 0.12
        nt.links.new(ta.outputs['Fac'], hh.inputs[0])
        nt.links.new(mk.outputs[0], g.inputs[0]); nt.links.new(hh.outputs[0], g.inputs[1])
        em.inputs['Color'].default_value = (1, 1, 1, 1)
        nt.links.new(g.outputs[0], em.inputs['Strength'])
        nt.links.new(em.outputs[0], out.inputs['Volume'])
        return mat
    cr = nt.nodes.new('ShaderNodeValToRGB')
    cr.color_ramp.interpolation = 'EASE'
    els = cr.color_ramp.elements
    els[0].position = 0.0; els[0].color = (0.25, 0.012, 0.0, 1)
    els[1].position = 1.0; els[1].color = (1.0, 0.74, 0.30, 1)
    e = els.new(0.22); e.color = (1.0, 0.10, 0.008, 1)
    e = els.new(0.50); e.color = (1.0, 0.36, 0.035, 1)
    e = els.new(0.78); e.color = (1.0, 0.55, 0.10, 1)
    nt.links.new(fa.outputs['Fac'], cr.inputs['Fac'])
    col = cr.outputs['Color']
    if P['blue_h'] > 0:
        # premixed (lean, blue) zone near the burner, shifting to orange diffusion flame with height
        tc = nt.nodes.new('ShaderNodeTexCoord')
        sp = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(tc.outputs['Generated'], sp.inputs[0])
        zm = nt.nodes.new('ShaderNodeMapRange')
        zm.inputs['From Min'].default_value = 0.0
        zm.inputs['From Max'].default_value = P['blue_h'] / H
        zm.inputs['To Min'].default_value = 1.0; zm.inputs['To Max'].default_value = 0.0
        zm.clamp = True; zm.interpolation_type = 'SMOOTHSTEP'
        nt.links.new(sp.outputs['Z'], zm.inputs['Value'])
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
        mix.inputs[7].default_value = (0.10, 0.28, 1.0, 1)  # B (blue)
        nt.links.new(zm.outputs[0], mix.inputs[0])
        nt.links.new(col, mix.inputs[6])
        col = mix.outputs[2]
    nt.links.new(col, em.inputs['Color'])
    nt.links.new(mk.outputs[0], em.inputs['Strength'])
    nt.links.new(em.outputs[0], out.inputs['Volume'])
    return mat

def smoke_material():
    mat, nt, out = new_mat('smoke')
    da = attr(nt, 'density')
    dp = nt.nodes.new('ShaderNodeMath'); dp.operation = 'POWER'; dp.inputs[1].default_value = 1.6
    nt.links.new(da.outputs['Fac'], dp.inputs[0])
    mk = nt.nodes.new('ShaderNodeMath'); mk.operation = 'MULTIPLY'; mk.inputs[1].default_value = 0.75 * P['smoke_k'] / max(0.3, H / 3.0) ** 0.6
    nt.links.new(dp.outputs[0], mk.inputs[0])
    sc_ = nt.nodes.new('ShaderNodeVolumeScatter')
    sc_.inputs['Color'].default_value = (0.42, 0.42, 0.42, 1)
    nt.links.new(mk.outputs[0], sc_.inputs['Density'])
    ab = nt.nodes.new('ShaderNodeVolumeAbsorption')
    ab.inputs['Color'].default_value = (0.35, 0.35, 0.35, 1)
    mk2 = nt.nodes.new('ShaderNodeMath'); mk2.operation = 'MULTIPLY'; mk2.inputs[1].default_value = 0.4
    nt.links.new(mk.outputs[0], mk2.inputs[0]); nt.links.new(mk2.outputs[0], ab.inputs['Density'])
    add = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(sc_.outputs[0], add.inputs[0]); nt.links.new(ab.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs['Volume'])
    return mat

mats = {'flame': flame_material(), 'heat': flame_material(heat=True), 'smoke': smoke_material()}
dom.data.materials.append(mats['flame'])

# ---------------------------------------------------------------- camera, light, render
cam_d = bpy.data.cameras.new('Cam'); cam_d.type = 'ORTHO'; cam_d.ortho_scale = W if FW >= FH else H
cam_d.clip_start = 0.1; cam_d.clip_end = 200
cam = bpy.data.objects.new('Cam', cam_d); sc.collection.objects.link(cam)
cam.location = (0, -40, H / 2); cam.rotation_euler = (math.pi / 2, 0, 0)
sc.camera = cam
r = sc.render
r.resolution_x = FW; r.resolution_y = FH; r.resolution_percentage = 100
r.film_transparent = True
r.image_settings.file_format = 'OPEN_EXR'; r.image_settings.color_mode = 'RGBA'; r.image_settings.color_depth = '16'
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
sc.render.engine = 'CYCLES'
cy = sc.cycles
cy.device = 'CPU'; cy.samples = SAMPLES; cy.use_denoising = False
cy.volume_bounces = 2; cy.volume_step_rate = 1.0; cy.volume_max_steps = 512
cy.max_bounces = 4
cy.use_adaptive_sampling = False
sc.render.threads_mode = 'FIXED'; sc.render.threads = 10

# neutral studio lighting used only for the smoke layer (the game tints/lights the sprite itself)
sun_d = bpy.data.lights.new('Sun', 'SUN'); sun_d.energy = 1.6; sun_d.angle = math.radians(25)
sun = bpy.data.objects.new('Sun', sun_d); sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(55), 0, math.radians(-25))
warm_d = bpy.data.lights.new('Glow', 'POINT'); warm_d.color = (1.0, 0.52, 0.2)
warm_d.energy = 900.0 * P['warm'] * (H / 3.0) ** 2; warm_d.shadow_soft_size = 0.5
warm = bpy.data.objects.new('Glow', warm_d); sc.collection.objects.link(warm)
warm.location = (0, -D * 0.45, SRCS[0][1][2] + 0.3 * H / 3)
sc.world = bpy.data.worlds.new('W'); sc.world.use_nodes = True
bg = sc.world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.75, 0.8, 0.9, 1); bg.inputs['Strength'].default_value = 0.35

def read_exr(path):
    img = bpy.data.images.load(path)
    n = FW * FH * 4
    buf = np.empty(n, dtype=np.float32)
    img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)
    return buf.reshape(FH, FW, 4)[::-1]    # flip so row 0 is the top

arrs = {k: np.zeros((total_out, FH, FW, 4), np.float16) for k in ('flame', 'smoke', 'heat')}
tr = time.time()
tmp = os.path.join(outdir, 'tmp.exr')
BLENDONLY = '--blendonly' in argv
LAYERS = argv[argv.index('--layers') + 1].split(',') if '--layers' in argv else ['flame', 'smoke']   # heat is derived in pack_atlas.py unless --layers lists it
SMOKE_STEP = 2                                   # smoke is smooth in time: render every 2nd frame, interpolate in the packer
for i in range(0 if BLENDONLY else total_out):
    sc.frame_set(WARM + 1 + i)
    for layer in LAYERS:
        if layer == 'smoke' and i % SMOKE_STEP: continue
        dom.data.materials[0] = mats[layer]
        cy.volume_bounces = 0
        cy.samples = max(8, SAMPLES // 2) if layer == 'smoke' else SAMPLES        # smoke is blurred in post, fewer samples are fine
        cy.volume_step_rate = 2.0 if layer == 'smoke' else 1.0
        sun.hide_render = layer != 'smoke'; warm.hide_render = layer != 'smoke'
        sc.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        arrs[layer][i] = read_exr(tmp)
        if i == 0: log('DBG layer', layer, 'mat', dom.data.materials[0].name, len(dom.data.materials), 'cam', sc.camera.name if sc.camera else None, 'res', sc.render.resolution_x, sc.render.resolution_y, 'engine', sc.render.engine, 'dom hide', dom.hide_render, dom.hide_viewport, 'mods', [m.name for m in dom.modifiers], 'max', float(arrs[layer][i].max()), 'file', os.path.getsize(tmp))
    if i % 8 == 0:
        log('rendered', i + 1, '/', total_out, 'max', float(arrs[LAYERS[0]][i].max()), 'frame', sc.frame_current)
t_render = time.time() - tr
for k, v in ([] if BLENDONLY else [(k, v) for k, v in arrs.items() if k in LAYERS]):
    np.save(os.path.join(outdir, k + '.npy'), v[::SMOKE_STEP] if k == 'smoke' else v)
# save the scene (no cache inside the .blend; the cache path is relative, rebake with bake_data)
scn_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scenes')
if '--noblend' not in argv:
    os.makedirs(scn_dir, exist_ok=True)
    dom.data.materials[0] = mats['flame']
    ds.cache_directory = '//cache_' + PRESET + '/'
    sun.hide_render = True; warm.hide_render = True; [o.__setattr__('hide_render', False) for o in fuel_objs]
    sc.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(scn_dir, 'fireb_%s.blend' % PRESET), compress=True, copy=True)
with open(os.path.join(outdir, 'times.txt') if not BLENDONLY else os.devnull, 'w') as f:
    f.write('bake %.1f\nrender %.1f\nres %d\nframes_sim %d\ndomain %.3f %.3f %.3f\n' % (t_bake, t_render, RES, last_frame, W, W, H))
log('RENDER DONE in %.1fs; saved to' % t_render, outdir)

import json
json.dump(dict(loop=NFRAMES, xfade=XFADE, smoke_step=SMOKE_STEP, fw=FW, fh=FH, worldW=W, worldH=H, depth=D, res=RES), open(os.path.join(outdir, 'meta.json'), 'w'))
