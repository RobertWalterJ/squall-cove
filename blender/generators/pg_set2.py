"""Shared helpers for build_weapons.py and build_props2.py: palette, part collector (class M), closed-ring lofts,
double-sided cloth, manifest, GLB/base64 export and Workbench 3/4 review renders.
Blender Z up; glTF export maps Blender (x, y, z) -> three (x, z, -y)."""
import bpy, bmesh, sys, os, json, base64, math, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from mathutils import Vector, Matrix
from pg_core import *

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))

PAL = {
    'gun_metal': dict(color='#2b2e32', rough=0.45, metal=0.7),
    'gun_dark':  dict(color='#1a1b1d', rough=0.5, metal=0.6),
    'gun_steel': dict(color='#555b61', rough=0.4, metal=0.7),
    'gun_wood':  dict(color='#5a3a20', rough=0.75),
    'gun_wood2': dict(color='#3c2616', rough=0.8),
    'gun_poly':  dict(color='#25272a', rough=0.7),
    'blade':     dict(color='#9aa1a7', rough=0.3, metal=0.8),
    'brass':     dict(color='#a7863a', rough=0.4, metal=0.7),
    'lens_g':    dict(color='#1d2c36', rough=0.1, metal=0.2),
    'flash':     dict(color='#ffd36a', rough=1.0, emit='#ffc04a', emit_str=6.0),
    'skin':      dict(color='#c68e68', rough=0.8),
    'olive_cloth': dict(color='#5c6440', rough=0.95),
    'cuff':      dict(color='#3f4529', rough=0.95),
    'concrete':  dict(color='#a3a39e', rough=0.9),
    'concrete2': dict(color='#7b7c79', rough=0.9),
    'metal_d':   dict(color='#4a5157', rough=0.6, metal=0.4),
    'steel':     dict(color='#a4abb2', rough=0.4, metal=0.5),
    'galv':      dict(color='#9aa3a8', rough=0.5, metal=0.5),
    'frame':     dict(color='#2a2d31', rough=0.6, metal=0.4),
    'black':     dict(color='#1b1c1e', rough=0.8),
    'wood':      dict(color='#8f6638', rough=0.9),
    'wood2':     dict(color='#6b4a2a', rough=0.9),
    'wood_g':    dict(color='#7d6e5a', rough=0.95),
    'wood_end':  dict(color='#c9a574', rough=0.9),
    'olive':     dict(color='#58623b', rough=0.85),
    'olive2':    dict(color='#464e2e', rough=0.9),
    'sand1':     dict(color='#a99668', rough=0.95),
    'sand2':     dict(color='#93825a', rough=0.95),
    'white':     dict(color='#e6e6e0', rough=0.7),
    'cream':     dict(color='#d9ceb0', rough=0.85),
    'red':       dict(color='#b3262b', rough=0.55),
    'red_d':     dict(color='#8a1f1f', rough=0.7),
    'barn_red':  dict(color='#8e2d25', rough=0.85),
    'yellow':    dict(color='#d9a62b', rough=0.6),
    'orange':    dict(color='#d27a22', rough=0.6),
    'glass':     dict(color='#27394a', rough=0.15, metal=0.1),
    'roof_grey': dict(color='#5d6166', rough=0.7, metal=0.2),
    'roof_dark': dict(color='#3b3f44', rough=0.8),
    'rust':      dict(color='#7a4a30', rough=0.9, metal=0.2),
    'rubber':    dict(color='#202123', rough=0.95),
    'straw':     dict(color='#c4a24a', rough=1.0),
    'rope':      dict(color='#b9a577', rough=1.0),
    'pump_red':  dict(color='#b02a24', rough=0.5, metal=0.2),
    'boat_hull': dict(color='#2f5f7f', rough=0.7),
    'tank':      dict(color='#d9dbd6', rough=0.6, metal=0.2),
    'tent':      dict(color='#6a7144', rough=0.95),
    'tent2':     dict(color='#555c36', rough=0.95),
    'camo1':     dict(color='#4d5a34', rough=1.0),
    'camo2':     dict(color='#6b6a3f', rough=1.0),
    'camo3':     dict(color='#3a4429', rough=1.0),
    'flag':      dict(color='#ffffff', rough=0.9),
    'dune':      dict(color='#b3a860', rough=1.0),
    'sign_g':    dict(color='#2f6a4a', rough=0.6),
    'phone_red': dict(color='#b3201f', rough=0.5),
    'ring_red':  dict(color='#d8351f', rough=0.6),
    'grey_l':    dict(color='#b8bcbe', rough=0.7),
}
FLAT_NAMES = set()
CLAMP = False   # props scripts set pg_set2.CLAMP = True


def mt(k):
    m = mat(k, **PAL[k])
    m.use_backface_culling = False if k in ('flag', 'dune', 'flash', 'camo1', 'camo2', 'camo3') else True
    return m


def recalc(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(o.data); bm.free(); return o


class M:
    """Collects the parts of one top-level node, then joins them into one mesh object."""
    def __init__(s, key, origin=None):
        s.key = key; s.parts = []; s.origin = origin; s.notes = ''
    def add(s, o): s.parts.append(o); return o
    def b(s, x0, x1, y0, y1, z0, z1, k, rot=(0, 0, 0)):
        return s.add(box((x1 - x0, y1 - y0, z1 - z0), ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), rot, mt(k)))
    def c(s, r, h, loc, k, seg=10, r2=None, rot=(0, 0, 0)):
        return s.add(cyl(r, r if r2 is None else r2, h, seg, loc, rot, mt(k)))
    def rd(s, p0, p1, r, k, seg=6):
        return s.add(rod(p0, p1, r, seg, mt(k)))
    def ext(s, pts, a0, a1, fn, k):
        bm = bmesh.new()
        A = [bm.verts.new(fn(u, v, a0)) for u, v in pts]; B = [bm.verts.new(fn(u, v, a1)) for u, v in pts]
        n = len(pts); bm.faces.new(A); bm.faces.new(B[::-1])
        for i in range(n):
            j = (i + 1) % n; bm.faces.new((A[i], A[j], B[j], B[i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        return s.add(obj_from_bm(bm, 'p', mt(k)))
    def ext_x(s, pts_yz, x0, x1, k): return s.ext(pts_yz, x0, x1, lambda u, v, a: (a, u, v), k)
    def slab_yz(s, p0, p1, x0, x1, t, k):
        """Slab along the segment p0 -> p1 in (y, z), thickness t toward the +z side of the segment, extruded x0..x1."""
        dy, dz = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dy, dz)
        n = (dz / L, -dy / L)
        if n[1] < 0: n = (-n[0], -n[1])
        q0 = (p0[0] + n[0] * t, p0[1] + n[1] * t); q1 = (p1[0] + n[0] * t, p1[1] + n[1] * t)
        return s.ext_x([p0, p1, q1, q0], x0, x1, k)
    def poly(s, verts, faces, k):
        return s.add(mesh('p', verts, faces, mt(k)))
    def cloth(s, verts, faces, k):
        """Double-sided sheet: faces plus reversed copies."""
        n = len(verts)
        return s.add(mesh('cloth', list(verts) + list(verts), list(faces) + [tuple(i + n for i in reversed(f)) for f in faces], mt(k)))
    def ring_loft(s, stations, profile_fn, face_mats, k_list):
        """Closed tube lofted along stations. profile_fn(station) -> list of (x, y, z) ring points (same count at every
        station). face_mats[i] gives an index into k_list for the ring edge i -> i+1. Ends are capped. One closed solid."""
        rings = [profile_fn(st) for st in stations]
        n = len(rings[0]); verts = [p for r in rings for p in r]; faces = []; fm = []
        for si in range(len(rings) - 1):
            for i in range(n):
                j = (i + 1) % n
                faces.append((si * n + i, si * n + j, (si + 1) * n + j, (si + 1) * n + i)); fm.append(face_mats[i])
        faces.append(tuple(reversed(range(n)))); fm.append(0)
        faces.append(tuple((len(rings) - 1) * n + i for i in range(n))); fm.append(0)
        me = bpy.data.meshes.new('loft'); me.from_pydata(verts, [], faces); me.validate(); me.update()
        o = bpy.data.objects.new('loft', me)
        for kk in k_list: me.materials.append(mt(kk))
        for p, mi in zip(me.polygons, fm): p.material_index = mi
        link(o); recalc(o)
        return s.add(o)
    def finish(s):
        o = join(s.parts, s.key)
        o.location = (0, 0, 0)
        if s.origin is None and CLAMP:   # flatten rod end caps that poke up to 5 cm below the ground plane
            for v in o.data.vertices:
                if -0.05 < v.co.z < 0: v.co.z = 0.0
        if s.origin is not None:
            h = Vector(s.origin)
            o.data.transform(Matrix.Translation(-h)); o.location = h
        return o


def world_bounds(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def r3(x): return round(float(x), 3)


def run(models, name, review_sub, camdir, argv, ground_big=True, extra_review=None):
    """models: list of (callable returning M or list of M). Writes assets/<name>.glb.b64.txt, review/<sub>/<name>.json, PNGs."""
    REVIEW = os.path.join(ROOT, 'blender', 'review', review_sub); os.makedirs(REVIEW, exist_ok=True)
    ASSET = os.path.join(ROOT, 'assets', name + '.glb.b64.txt')
    only = argv[argv.index('--only') + 1].split(',') if '--only' in argv else None
    reset(); objs = {}
    for f in models:
        r = f(); r = r if isinstance(r, list) else [r]
        for m in r:
            if only and m.key not in only: continue
            objs[m.key] = m.finish()
    bpy.context.view_layer.update()
    manifest = {}; total = 0
    for k, o in objs.items():
        mn, mx = world_bounds(o); t = tri_count(o); total += t
        manifest[k] = dict(size_x=r3(mx.x - mn.x), size_y_height=r3(mx.z - mn.z), size_z_depth=r3(mx.y - mn.y), tris=t,
                           min=[r3(c) for c in mn], max=[r3(c) for c in mx], node_pos_blender=[r3(c) for c in o.location])
        print('MODEL', k, manifest[k]['size_x'], 'x', manifest[k]['size_y_height'], 'x', manifest[k]['size_z_depth'],
              'tris', t, 'minz', r3(mn.z), 'xy', r3((mn.x + mx.x) / 2), r3((mn.y + mx.y) / 2))
    manifest['_total_tris'] = total
    json.dump(manifest, open(os.path.join(REVIEW, name + '.json'), 'w'), indent=1)
    tmp = os.path.join(tempfile.gettempdir(), 'sc_%s.glb' % name)
    export_glb(list(bpy.context.scene.objects), tmp)
    data = open(tmp, 'rb').read()
    print('GLB bytes', len(data), 'total tris', total)
    if not only:
        open(ASSET, 'w', newline='').write(base64.b64encode(data).decode('ascii'))
        print('WROTE', ASSET)
    if '--review' in argv:
        sc = bpy.context.scene
        sc.render.engine = 'BLENDER_WORKBENCH'
        sh = sc.display.shading
        sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_object_outline = False; sh.show_cavity = False
        w = bpy.data.worlds.new('rw'); w.color = (0.74, 0.80, 0.86); sc.world = w
        sc.render.image_settings.file_format = 'PNG'
        for mtl in bpy.data.materials:
            b = mtl.node_tree.nodes['Principled BSDF']
            c = b.inputs['Base Color'].default_value
            e = b.inputs['Emission Strength'].default_value
            mtl.diffuse_color = (c[0], c[1], c[2], 1)
        gm = mat('ground', '#9aa18c', 1.0); gm.diffuse_color = (0.38, 0.42, 0.34, 1)
        shots = [(k, [k]) for k in objs]
        if extra_review: shots += extra_review
        for label, keys in shots:
            if any(k not in objs for k in keys): continue
            for q in bpy.data.objects: q.hide_render = True
            for k in keys: objs[k].hide_render = False
            mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
            for k in keys:
                a, b2 = world_bounds(objs[k]); mn = Vector(map(min, mn, a)); mx = Vector(map(max, mx, b2))
            c = (mn + mx) / 2; sz = max(mx.x - mn.x, mx.y - mn.y, mx.z - mn.z)
            ground = box((sz * 12, sz * 12, 0.02 * max(sz, 0.3)), (c.x, c.y, mn.z - 0.01 * max(sz, 0.3)), (0, 0, 0), gm)
            cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); link(cam); sc.camera = cam
            cam.data.clip_end = 1000; cam.data.clip_start = 0.01; cam.data.lens = 40
            sc.render.resolution_x, sc.render.resolution_y = 800, 560
            cam.location = c + Vector(camdir).normalized() * sz * 1.75
            cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
            sc.render.filepath = os.path.join(REVIEW, f'{label}_3q.png')
            bpy.ops.render.render(write_still=True)
            bpy.data.objects.remove(cam); bpy.data.objects.remove(ground)
        print('REVIEW DONE')
    print('BUILD DONE')
    return objs, manifest
