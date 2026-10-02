"""blender -b --python build_photo_people.py
Photo faces stretched over the faceted low poly heads (baked from the CC0 MakeHuman skins). One GLB of sixteen people
with idle, walk, sit and wave, a .blend, a full length sheet and a row of close portraits."""
import sys, os, math, random, json
os.environ.setdefault('PF_MH', '/home/claude/mh/x1k')
sys.path.insert(0, '/home/claude/procgen')
import bpy
from mathutils import Vector
from pg_core import *
import cv_people as CP, photo_faces as PF
OUT = '/home/claude/procgen/out/coilover/assets/people'; os.makedirs(OUT, exist_ok=True)
reset()
rr = random.Random(21)
KEYS = [k for k in PF.SK]
rr.shuffle(KEYS); KEYS = (KEYS * 2)[:16]
THEMES = ['city', 'desert', 'shield', 'harbour']
people = []; man = {}
for i, key in enumerate(KEYS):
    th = THEMES[i % 4]; sp = CP.spec_for(th, 500 + i * 17)
    sp['photo_tex'] = key; sp['sex'] = 'f' if key.endswith('female') else 'm'
    if sp['height'] < 1.45: sp['height'] = rr.uniform(1.58, 1.85)
    sp['height'] = rr.uniform(1.68, 1.9) if sp['sex'] == 'm' else rr.uniform(1.56, 1.76)
    age = key.split('_')[0]
    sp['hair_kind'] = rr.choice(['short', 'crop', 'curls', 'bald'] if sp['sex'] == 'm' else ['long', 'bob', 'ponytail', 'curls', 'bun']); sp['hat'] = sp['hat'] if rr.random() < 0.3 else None
    if 'african' in key and rr.random() < 0.5: sp['hair_kind'] = 'curls'
    sp['hair'] = rr.choice(['#8a8a86', '#b8b4ac', '#d8d4cc']) if age == 'old' else rr.choice(['#1c1714', '#2e2119', '#4a3021', '#6b4a2e', '#8c6a3f', '#b38b55'] if 'african' not in key else ['#1c1714', '#2e2119'])
    dark = sum(int(PF.SK[key]['avg'][j:j + 2], 16) for j in (1, 3, 5)) < 400
    sp['eye'] = 'brown' if dark else rr.choice(['brown', 'blue', 'green'])
    r, m = CP.person(sp, f'facetex_{i}')
    people.append(r); man[r.name] = dict(theme=th, skin=key, height=round(sp['height'], 2), hair=sp['hair_kind'], eyes=sp['eye'])
acts = CP.make_actions(people[0])
for r in people: r.animation_data_create(); r.animation_data.action = acts['idle']
CP.texture_people()
for part, sl in (('all', people),):
    bpy.ops.object.select_all(action='DESELECT')
    for r in sl:
        r.select_set(True)
        for c in r.children: c.select_set(True)
    bpy.ops.export_scene.gltf(filepath=f'{OUT}/people_photo_faces.glb', use_selection=True, export_yup=True, export_extras=True,
                              export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True, export_skins=True)
json.dump(dict(people=man, source='Heads, skins, eyes, brows, lashes and hair: MakeHuman system assets, CC0 (public domain). Bodies: Coilover low poly kit.'),
          open(f'{OUT}/people_photo_faces.json', 'w'), indent=1)
print('EXPORTED')
# ---- sheet
POSES = [('idle', 1), ('walk', 5), ('wave', 6), ('idle', 40), ('walk', 15), ('sit', 1), ('idle', 70), ('wave', 14)]
bench = mat('bench', '#8a6a4a', 0.8)
for i, r in enumerate(people):
    a, f = POSES[i % len(POSES)]
    row, col = divmod(i, 8)
    r.location = (col * 1.0, row * 2.6, 0); r.rotation_euler = (0, 0, 0.2 * math.sin(i * 1.3))
    r.animation_data.action = None; tr = r.animation_data.nla_tracks.new(); st = tr.strips.new(a, 1, acts[a]); st.action_frame_start = f; st.action_frame_end = f + 1
    if a == 'sit': box((0.7, 0.42, 0.44), (col * 1.0, row * 2.6 + 0.12, 0.22), material=bench, name='bench')
floor = mat('floor', '#d9d4c8', 0.9); box((12, 9, 0.02), (3.5, 1.8, -0.01), material=floor, name='floor')
bpy.context.scene.frame_set(1)
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 40; sc.cycles.use_denoising = True; sc.view_settings.view_transform = 'AgX'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.8, 0.82, 0.85, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 0.9
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); link(sun); sun.data.energy = 3.0; sun.rotation_euler = (math.radians(50), 0, math.radians(-25)); sun.data.angle = math.radians(5)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); link(cam); sc.camera = cam
cam.data.lens = 50; cam.location = (3.5, -9.0, 3.2); look = Vector((3.5, 1.6, 0.95)); cam.rotation_euler = (look - cam.location).to_track_quat('-Z', 'Y').to_euler()
sc.render.resolution_x, sc.render.resolution_y = 2400, 1400
sc.render.filepath = '/home/claude/procgen/out/phototex_sheet.png'; bpy.ops.render.render(write_still=True)
# ---- close portraits: front row, chest up, soft key light
for o in bpy.data.objects:
    if o.name.startswith('bench') or o.name == 'floor': o.hide_render = True
key = bpy.data.objects.new('key', bpy.data.lights.new('key', 'AREA')); link(key); key.data.energy = 300; key.data.size = 2.5
for i, r in enumerate(people[:8]):
    r.animation_data.nla_tracks.remove(r.animation_data.nla_tracks[0]); r.animation_data.action = acts['idle']
    r.location = (i * 0.5, 0, 1.74 - r['height']); r.rotation_euler = (0, 0, 0.1 * ((i % 3) - 1))
for r in people[8:]:
    r.hide_render = True
    for c in r.children: c.hide_render = True
bpy.context.scene.frame_set(1)
key.location = (1.75, -2.8, 2.6); key.rotation_euler = (math.radians(55), 0, 0)
cam.data.lens = 70; cam.location = (1.75, -5.4, 1.62); cam.rotation_euler = (math.radians(90), 0, 0)
sc.render.resolution_x, sc.render.resolution_y = 2400, 820
sc.render.filepath = '/home/claude/procgen/out/phototex_portraits.png'; bpy.ops.render.render(write_still=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath='/home/claude/blend_out/coilover/coilover_people_photo_faces.blend', compress=True)
print('DONE')
