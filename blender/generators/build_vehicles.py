"""Build the Squall Cove land vehicles.
  blender -b --python build_vehicles.py -- [--review] [--only key,key]
Writes ../../assets/vehicles.glb.b64.txt (one-line base64 of the GLB), ../review/vehicles/vehicles.json (manifest)
and, with --review, flat-lit Workbench renders (3/4 front, side, top per vehicle + contact sheets) into ../review/vehicles/."""
import bpy, sys, os, json, base64, math, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from mathutils import Vector, Matrix
from pg_core import *
import pg_vehicles as PV

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
REVIEW = os.path.join(ROOT, 'blender', 'review', 'vehicles')
ASSET = os.path.join(ROOT, 'assets', 'vehicles.glb.b64.txt')
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
os.makedirs(REVIEW, exist_ok=True)
SPACING = 7.0

reset()
builders = PV.ALL
if '--only' in argv:
    keys = argv[argv.index('--only') + 1].split(',')
    builders = [b for b in builders if b.__name__ in keys]
vs = [b(y=i * SPACING) for i, b in enumerate(builders)]
bpy.context.view_layer.update()


def wm(o):
    return (wm(o.parent) if o.parent else Matrix.Identity(4)) @ o.matrix_basis


def world_bounds(objs):
    pts = [wm(o) @ Vector(c) for o in objs if o.type == 'MESH' for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def r3(x): return round(float(x), 3)

manifest = {}
total_tris = 0
for v in vs:
    meshes = list(v.nodes)
    mn, mx = world_bounds(meshes)
    mn -= Vector((0, v.root.location.y, 0)); mx -= Vector((0, v.root.location.y, 0))
    tris = sum(tri_count(o) for o in meshes); total_tris += tris
    ent = dict(root=v.key, size=dict(length=r3(mx.x - mn.x), width=r3(mx.y - mn.y), height=r3(mx.z - mn.z)),
               bounds=dict(min=[r3(c) for c in mn], max=[r3(c) for c in mx]), tris=tris, nodes=[], empties=[], wheels=[])
    for o in v.nodes:
        n = dict(name=o.name, parent=o.parent.name, pivot=[r3(c) for c in v.piv[o.name]], tris=tri_count(o), dims=list(dims(o)))
        if o.rotation_euler.y: n['rest_rotation_y_deg'] = round(math.degrees(o.rotation_euler.y), 1)
        ent['nodes'].append(n)
    for e in v.empties:
        ent['empties'].append(dict(name=e.name, parent=e.parent.name, local=[r3(c) for c in e.location], world_in_root=[r3(c) for c in (wm(e).translation - Vector((0, v.root.location.y, 0)))]))
    for w in v.wheels:
        ent['wheels'].append(dict(name=w['name'], parent=w['parent'] or v.key, centre=[r3(w['x']), r3(w['y']), r3(w['z'])], radius=r3(w['r']), width=r3(w['w'])))
    manifest[v.key] = ent
    print('VEHICLE', v.key, ent['size'], 'tris', tris, 'min z', r3(mn.z))
json.dump(manifest, open(os.path.join(REVIEW, 'vehicles.json'), 'w'), indent=1)

# ---- export every object (roots, meshes, empties) as one GLB, then base64 it
tmp = os.path.join(tempfile.gettempdir(), 'sc_vehicles.glb')
export_glb(list(bpy.context.scene.objects), tmp)
data = open(tmp, 'rb').read()
print('GLB bytes', len(data), 'total tris', total_tris)
if '--only' not in argv:
    open(ASSET, 'w', newline='').write(base64.b64encode(data).decode('ascii'))
    print('WROTE', ASSET)

# ---- review renders
if '--review' in argv:
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_object_outline = False; sh.show_cavity = False
    sc.render.film_transparent = False
    w = bpy.data.worlds.new('rw'); w.color = (0.74, 0.80, 0.86); sc.world = w
    sc.render.image_settings.file_format = 'PNG'
    for mt in bpy.data.materials:                          # Workbench shows diffuse_color, so copy the base colour (or lamp emission)
        b = mt.node_tree.nodes['Principled BSDF']
        c = b.inputs['Emission Color'].default_value if b.inputs['Emission Strength'].default_value > 0 else b.inputs['Base Color'].default_value
        mt.diffuse_color = (c[0], c[1], c[2], 1)
    gm = mat('ground', '#9aa18c', 1.0); gm.diffuse_color = (0.38, 0.42, 0.34, 1)
    ground = box((400, 400, 0.04), (0, 0, -0.02), (0, 0, 0), gm)

    def descendants(root):
        out = []
        for o in bpy.data.objects:
            p = o
            while p:
                if p is root: out.append(o); break
                p = p.parent
        return out

    def shoot(v, kind, path, res):
        for o in bpy.data.objects:
            o.hide_render = True
        for o in descendants(v.root): o.hide_render = False
        ground.hide_render = False
        ground.location.y = v.root.location.y
        mn, mx = world_bounds(v.nodes)
        c = (mn + mx) / 2; L, Wd, H = mx.x - mn.x, mx.y - mn.y, mx.z - mn.z
        cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); link(cam); sc.camera = cam
        cam.data.clip_end = 500
        sc.render.resolution_x, sc.render.resolution_y = res
        asp = res[0] / res[1]
        if kind == 'side':
            cam.data.type = 'ORTHO'; cam.location = (c.x, c.y - 60, c.z); cam.rotation_euler = (math.pi / 2, 0, 0)
            cam.data.ortho_scale = max(L, H * asp) * 1.15
        elif kind == 'top':
            cam.data.type = 'ORTHO'; cam.location = (c.x, c.y, c.z + 60); cam.rotation_euler = (0, 0, 0)
            cam.data.ortho_scale = max(L, Wd * asp) * 1.15
        else:
            d = Vector((0.8, -0.62, 0.42)) if kind == '3q_front' else Vector((-0.8, -0.62, 0.42))
            cam.data.type = 'PERSP'; cam.data.lens = 40
            cam.location = c + d.normalized() * (max(L, Wd, H) * 1.7)
            cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam)

    files = {}
    for v in vs:
        files[v.key] = []
        for kind in ('3q_front', '3q_rear', 'side', 'top'):
            p = os.path.join(REVIEW, f'{v.key}_{kind}.png')
            shoot(v, kind, p, (800, 520) if kind != 'top' else (800, 380))
            files[v.key].append(p)

    # contact sheet: 3 x 3, the 3/4 front view of each vehicle, plus a second sheet of side views, composed with numpy
    import numpy as np
    def load(p):
        im = bpy.data.images.load(p); w_, h_ = im.size
        a = np.empty(w_ * h_ * 4, dtype=np.float32); im.pixels.foreach_get(a); bpy.data.images.remove(im)
        return a.reshape(h_, w_, 4)
    def sheet(idx, out, cell=(400, 260), cols=3):
        rows = math.ceil(len(vs) / cols)
        W_, H_ = cell[0] * cols, cell[1] * rows
        S = np.ones((H_, W_, 4), dtype=np.float32)
        for i, v in enumerate(vs):
            a = load(files[v.key][idx])
            h_, w_ = a.shape[:2]
            ys = (np.arange(cell[1]) * h_ / cell[1]).astype(int); xs = (np.arange(cell[0]) * w_ / cell[0]).astype(int)
            t = a[ys][:, xs]
            r_, c_ = i // cols, i % cols
            S[H_ - (r_ + 1) * cell[1]: H_ - r_ * cell[1], c_ * cell[0]:(c_ + 1) * cell[0]] = t
        im = bpy.data.images.new('sheet', W_, H_, alpha=True); im.pixels.foreach_set(S.ravel()); im.filepath_raw = out; im.file_format = 'PNG'; im.save()
    sheet(0, os.path.join(REVIEW, 'contact_3q.png'))
    sheet(2, os.path.join(REVIEW, 'contact_side.png'))
    print('REVIEW DONE')
print('BUILD DONE')
