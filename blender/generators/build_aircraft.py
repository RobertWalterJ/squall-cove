"""Build the two aircraft (CH-149 Cormorant and Canadair CL-415) and render review views.
  blender -b --python build_aircraft.py -- GAME_DIR REVIEW_DIR [TEX_DIR]
Writes GAME_DIR/aircraft.glb and GAME_DIR/aircraft.glb.b64.txt (one line, no newline; copy it to assets/aircraft.glb.b64.txt)
with nodes cormorant_hull, cormorant_rotor0, cormorant_tail0, cormorant_winch0, cl415_hull, cl415_prop0, cl415_prop1,
and REVIEW_DIR/<model>_<view>.png for side, port, front, rear, plan, belly and the 3/4 views.
The livery atlases (colour + normal) are painted by air_tex.py with a normal Python that has Pillow and numpy (found as `python` on PATH, or $AIR_PY);
set AC_NOTEX=1 to reuse the textures already in TEX_DIR. AC_NORENDER=1 skips the review renders, AC_SAMPLES sets the render samples.
"""
import bpy, sys, os, math, base64, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pg_core import *
import air_render as R

argv = sys.argv[sys.argv.index('--') + 1:]
GAME, REV = argv[0], argv[1]
TEX = argv[2] if len(argv) > 2 else os.path.join(GAME, 'tex')
os.makedirs(GAME, exist_ok=True); os.makedirs(REV, exist_ok=True); os.makedirs(TEX, exist_ok=True)

if not os.environ.get('AC_NOTEX'):
    py = os.environ.get('AIR_PY') or shutil.which('python') or shutil.which('python3')
    subprocess.check_call([py, os.path.join(HERE, 'air_tex.py'), TEX])

import pg_cormorant, pg_cl415
reset(); built = {}; everything = []
for key, mod in (('cormorant', pg_cormorant), ('cl415', pg_cl415)):
    fus, parts, anim, M = mod.build(TEX)
    hull = join(parts, key + '_hull')
    built[key] = (hull, anim); everything += [hull] + anim
    print('MODEL', key, dims(hull), 'tris hull', tri_count(hull), 'anim', [(a.name, tri_count(a)) for a in anim])

glb = os.path.join(GAME, 'aircraft.glb')
bpy.ops.object.select_all(action='DESELECT')
for o in everything: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=glb, use_selection=True, export_apply=True, export_yup=True, export_extras=True, export_image_format='AUTO', export_jpeg_quality=88)
open(os.path.join(GAME, 'aircraft.glb.b64.txt'), 'w').write(base64.b64encode(open(glb, 'rb').read()).decode('ascii'))
print('GLB', os.path.getsize(glb), 'bytes')

if os.environ.get('AC_NORENDER'):
    print('AIRCRAFT DONE (no renders)'); sys.exit(0)
sc = R.setup_scene(int(os.environ.get('AC_SAMPLES', '20')))
views = os.environ.get('AC_VIEWS', 'side,port,front,rear,plan,belly,3q_high,3q_low,3q_rear,3q_port').split(',')
for key, (hull, anim) in built.items():
    for k2, (h2, a2) in built.items():
        for o in [h2] + a2: o.hide_render = (k2 != key)
    for v in views: R.shoot(sc, os.path.join(REV, f'{key}_{v}.png'), v, [hull] + anim, int(os.environ.get('AC_SIZE', '1500')))
print('AIRCRAFT DONE')
