"""Blender (background) preview renders for assets/lights_pack.glb.
  blender -b --factory-startup -P render_lights.py -- tiles <out_dir> [size] [piece,piece]
  blender -b --factory-startup -P render_lights.py -- night <out_png> [w h samples]
Tiles use Workbench (flat colours, lenses shown lit); the night scene uses Cycles with real spot lights placed on the lightpt_* empties
and lamp_off swapped for an emissive lamp_on. One Blender process at a time."""
import bpy, sys, os, math, json, time
from mathutils import Vector, Matrix, Euler

argv = sys.argv[sys.argv.index('--') + 1:]
MODE = argv[0]; OUT = argv[1]
HERE = os.path.dirname(os.path.abspath(__file__)); GAME = os.path.abspath(os.path.join(HERE, '..', '..'))
GLB = os.path.join(GAME, 'assets', 'lights_pack.glb')
def log(*a): print('[lights]', *a, flush=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
scene = bpy.context.scene
ROOTS = [o for o in bpy.data.objects if o.parent is None]
BYNAME = {o.name: o for o in ROOTS}
log('imported', len(bpy.data.objects), 'objects,', len(ROOTS), 'roots')

def descendants(o):
    out = [o]
    for c in o.children: out += descendants(c)
    return out
def set_vis(objs, vis):
    for o in objs: o.hide_render = not vis; o.hide_viewport = not vis

def mat_color(m):
    if m.use_nodes:
        b = m.node_tree.nodes.get('Principled BSDF')
        if b: return tuple(b.inputs['Base Color'].default_value)
    return tuple(m.diffuse_color)

def bbox(objs):
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3); any_ = False
    for o in objs:
        if o.type != 'MESH': continue
        for v in o.bound_box:
            w = o.matrix_world @ Vector(v); any_ = True
            lo = Vector((min(lo[i], w[i]) for i in range(3))); hi = Vector((max(hi[i], w[i]) for i in range(3)))
    return lo, hi

def frame_camera(cam, lo, hi, dirv, fov=34, margin=1.12):
    c = (lo + hi) / 2; dirv = dirv.normalized(); th = math.tan(math.radians(fov) / 2)
    fwd = -dirv; right = fwd.cross(Vector((0, 0, 1))).normalized(); up = right.cross(fwd).normalized()
    d = 0
    for i in range(8):
        p = Vector((hi[0] if i & 1 else lo[0], hi[1] if i & 2 else lo[1], hi[2] if i & 4 else lo[2])) - c
        x, y, w = p.dot(right), p.dot(up), p.dot(dirv)
        d = max(d, max(abs(x), abs(y)) * margin / th + w)
    cam.location = c + dirv * d
    cam.rotation_euler = (-dirv).to_track_quat('-Z', 'Y').to_euler()
    cam.data.angle = math.radians(fov); cam.data.clip_start = .05; cam.data.clip_end = 400

# ---------------------------------------------------------------------------------- tiles
if MODE == 'tiles':
    size = int(argv[2]) if len(argv) > 2 else 360
    only = argv[3].split(',') if len(argv) > 3 else None
    os.makedirs(OUT, exist_ok=True)
    for m in bpy.data.materials:
        c = mat_color(m)
        if m.name in ('lamp_off', 'lamp_on'): c = (1, .93, .62, 1)
        elif m.name == 'ind_off' or m.name == 'ind_on': c = (.3, 1, .45, 1)
        elif m.name in ('tail_off', 'tail_on'): c = (1, .1, .06, 1)
        elif m.name == 'lens_glass': c = (.5, .7, .8, 1)
        m.diffuse_color = c
    scene.render.engine = 'BLENDER_WORKBENCH'
    sh = scene.display.shading; sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_object_outline = True; sh.show_shadows = True; sh.shadow_intensity = .35
    sh.show_cavity = False; sh.object_outline_color = (0, 0, 0)
    scene.render.resolution_x = scene.render.resolution_y = size; scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new('w'); scene.world.color = (.78, .82, .86)
    scene.render.image_settings.file_format = 'PNG'
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scene.collection.objects.link(cam); scene.camera = cam
    ground = bpy.data.objects.new('ground', bpy.data.meshes.new('ground')); scene.collection.objects.link(ground)
    ground.data.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [], [(0, 1, 2, 3)])
    gm = bpy.data.materials.new('gmat'); gm.diffuse_color = (.56, .58, .56, 1); ground.data.materials.append(gm)
    for r in ROOTS:
        if r.name in ('ground', 'cam') or r.type == 'CAMERA' or (only and r.name not in only) or r.name == 'lights_materials_ref': continue
        t0 = time.time()
        set_vis(bpy.data.objects, False); objs = descendants(r); set_vis(objs, True)
        lo, hi = bbox(objs); ext = max(hi.x - lo.x, hi.y - lo.y) * .9 + 2
        c = (lo + hi) / 2; ground.scale = (ext, ext, 1); ground.location = (c.x, c.y, min(lo.z, 0.0) - .004); set_vis([ground], True)
        # glTF +Z (front) is Blender -Y; model-left (+X) stays +X
        for tag, d in (('3q', Vector((.85, -1.0, .62))), ('front', Vector((0, -1.0, .12))), ('side', Vector((1.0, 0, .12)))):
            lo2, hi2 = lo.copy(), hi.copy()
            frame_camera(cam, lo2, hi2, d)
            scene.render.filepath = os.path.join(OUT, '%s_%s.png' % (r.name, tag)); bpy.ops.render.render(write_still=True)
        log('tile', r.name, '%.1fs' % (time.time() - t0))

# ---------------------------------------------------------------------------------- night scene
if MODE == 'night':
    W = int(argv[2]) if len(argv) > 2 else 1600; H = int(argv[3]) if len(argv) > 3 else 760; SAMP = int(argv[4]) if len(argv) > 4 else 48
    gj = json.loads(open(GLB, 'rb').read()[20:20 + int.from_bytes(open(GLB, 'rb').read()[12:16], 'little')])
    LIGHTS = {}                                 # root name -> {empty name: extras light dict}
    for n in gj['nodes']:
        if n['name'].startswith('lightpt_') and 'extras' in n and 'light' in n['extras']: LIGHTS[n['name']] = n['extras']['light']
    # materials: lamp_on gets a strong emission
    lon = bpy.data.materials['lamp_on']; b = lon.node_tree.nodes['Principled BSDF']
    b.inputs['Emission Strength'].default_value = 30
    for nm, k in (('tail_on', 12), ('ind_on', 6)):
        mm = bpy.data.materials.get(nm)
        if mm: mm.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = k
    SWAP = {'lamp_off': 'lamp_on', 'tail_off': 'tail_on', 'ind_off': 'ind_on'}
    set_vis(bpy.data.objects, False)
    placed = []
    def instance(rootname, loc, yaw=0.0, scale=1.0):
        src = BYNAME[rootname]; mapping = {}
        def dup(o, parent):
            n = o.copy()
            if o.data is not None and o.type == 'MESH':
                n.data = o.data.copy()
                for i, sl in enumerate(n.material_slots):
                    if sl.material and sl.material.name in SWAP: n.material_slots[i].material = bpy.data.materials[SWAP[sl.material.name]]
            scene.collection.objects.link(n); mapping[o] = n
            n.hide_render = False; n.hide_viewport = False
            if parent: n.parent = parent; n.matrix_parent_inverse = o.matrix_parent_inverse.copy()
            for c in o.children: dup(c, n)
            return n
        top = dup(src, None); top.parent = None
        top.matrix_world = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Diagonal((scale, scale, scale, 1)) @ Matrix.Identity(4)
        bpy.context.view_layer.update()
        for o in mapping.values():
            if o.type == 'EMPTY' and o.name.split('.')[0] in LIGHTS: placed.append((o, LIGHTS[o.name.split('.')[0]]))
        return top
    # --- ground (wet asphalt)
    bpy.ops.mesh.primitive_plane_add(size=220, location=(0, 0, 0)); g = bpy.context.object; gmat = bpy.data.materials.new('asphalt'); gmat.use_nodes = True
    gb = gmat.node_tree.nodes['Principled BSDF']; gb.inputs['Base Color'].default_value = (.05, .055, .06, 1); gb.inputs['Roughness'].default_value = .22
    g.data.materials.append(gmat)
    # --- a building wall for the wall floodlight
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0)); wall = bpy.context.object; wall.scale = (14, .4, 5); wall.location = (-1, 14.2, 2.5)
    wm = bpy.data.materials.new('wallm'); wm.use_nodes = True; wm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.16, .15, .14, 1); wall.data.materials.append(wm)
    # --- scene layout (Blender: +X right, -Y toward camera; glTF +Z front = Blender -Y)
    # yaw: glTF facing +Z = Blender -Y; rotating the instance by `yaw` about Z turns it
    instance('light_tower', (-6.5, 2, 0), math.radians(25))
    instance('generator_large', (-2.2, 4.5, 0), math.radians(-90 + 10))
    instance('cableseg_straight_4m', (-4.3, 3.0, 0), math.radians(120))
    instance('cableseg_90', (-4.9, 6.2, 0), math.radians(-30))
    instance('junction_box', (-3.0, 0.8, 0), math.radians(20))
    instance('floodlight_pole_4', (6.0, 8.0, 0), math.radians(200))
    instance('floodlight_pole_2', (-12.5, 7.0, 0), math.radians(160))
    instance('floodlight_wall', (-1.0, 13.9, 3.6), math.radians(180))
    instance('floodlight_roof', (4.0, 13.0, 5.0), math.radians(180))
    for i in range(4): instance('lamp_cobra', (-15 + i * 8.5, -6, 0), math.radians(-90 if i % 2 == 0 else -90))
    instance('lamp_harbour', (9.5, -1.5, 0), 0); instance('lamp_harbour', (13.5, -1.5, 0), 0)
    for i in range(4): instance('lamp_bollard', (3 + i * 1.8, -2.6, 0), 0)
    instance('string_lights_8m', (7.0, 3.2, 0), math.radians(8))
    instance('searchlight_ground', (16.5, 8.5, 0), math.radians(-60))
    instance('generator_medium', (14.0, 4.0, 0), math.radians(-30))
    instance('spotlight_tripod', (11.0, 7.0, 0), math.radians(160))
    instance('cablereel', (9.2, 5.5, 0), math.radians(10))
    instance('junction_box_dist', (12.2, 3.2, 0), math.radians(180))
    instance('generator_small', (1.8, 2.0, 0), math.radians(200))
    instance('vehicle_headlights', (-6.0, -2.5, .6), math.radians(180 - 25)); instance('vehicle_lightbar', (-6.0, -2.5, 1.5), math.radians(0))
    bpy.context.view_layer.update()
    # --- lights on every lightpt empty (spot lights point along local -Z: rotate so they follow the glTF +Z beam = Blender local -Y)
    nL = 0
    for e, ex in placed:
        if ex.get('type') == 'indicator': continue
        gm_ = e.matrix_world; beam = (gm_.to_3x3() @ Vector((0, -1, 0))).normalized()
        if ex['type'] == 'point':
            ld = bpy.data.lights.new('l', 'POINT'); ld.energy = max(2.0, ex['I'] * .25); ld.shadow_soft_size = .05
        else:
            ld = bpy.data.lights.new('l', 'SPOT'); ld.spot_size = math.radians(min(ex['cone_deg'], 170)); ld.spot_blend = .55; ld.energy = ex['I'] * (6.0 if ex['I'] < 1000 else 2.0); ld.shadow_soft_size = .08
        ld.color = ex['color']
        lo_ = bpy.data.objects.new('L', ld); scene.collection.objects.link(lo_)
        lo_.location = gm_.translation + beam * .02
        lo_.rotation_euler = (-beam).to_track_quat('Z', 'Y').to_euler() if False else (beam).to_track_quat('-Z', 'Y').to_euler()
        nL += 1
    log('lights', nL)
    # --- world + camera
    scene.world = bpy.data.worlds.new('w'); scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (.012, .02, .04, 1); bg.inputs['Strength'].default_value = 1
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scene.collection.objects.link(cam); scene.camera = cam
    cam.location = (5, -26, 6.5); cam.rotation_euler = (Vector((2, 9, 3.2)) - cam.location).to_track_quat('-Z', 'Y').to_euler(); cam.data.angle = math.radians(52)
    scene.render.engine = 'CYCLES'; scene.cycles.samples = SAMP; scene.cycles.use_denoising = True; scene.cycles.device = 'CPU'
    scene.cycles.max_bounces = 4; scene.cycles.diffuse_bounces = 2; scene.cycles.glossy_bounces = 3; scene.cycles.transmission_bounces = 2
    scene.render.resolution_x = W; scene.render.resolution_y = H; scene.render.filepath = OUT; scene.render.image_settings.file_format = 'PNG'
    try: scene.view_settings.view_transform = 'Filmic'
    except Exception: pass
    scene.view_settings.exposure = 0.3
    t0 = time.time(); bpy.ops.render.render(write_still=True); log('night render %.1fs' % (time.time() - t0))
