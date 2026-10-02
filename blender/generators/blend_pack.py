"""Pack GLBs into an editable .blend: each file in its own collection, laid out in rows so nothing overlaps.
blender -b --python blend_pack.py -- out.blend title file1.glb file2.glb ...
Material roles (glTF extras) come through as custom properties on the materials."""
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
out, title, files = argv[0], argv[1], argv[2:]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.name = title
root = bpy.data.collections.new(title); sc.collection.children.link(root)

items = []
for f in files:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=f)
    new = [o for o in bpy.data.objects if o not in before]
    if not new: continue
    col = bpy.data.collections.new(os.path.splitext(os.path.basename(f))[0]); root.children.link(col)
    for o in new:
        for c in list(o.users_collection): c.objects.unlink(o)
        col.objects.link(o)
    tops = [o for o in new if o.parent is None]
    bpy.context.view_layer.update()
    groups = [[t] for t in tops] if (len(files) == 1 or len(tops) > 6) else [tops]        # a single library file: lay out each model on its own
    for g in groups:
        objs = [d for t in g for d in [t] + list(t.children_recursive)]
        pts = [o.matrix_world @ Vector(c) for o in objs if o.type == 'MESH' for c in o.bound_box]
        if not pts: continue
        mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        items.append((col, g, mn, mx))

# rows by width, wrapping near a square overall footprint
total = sum((mx.x - mn.x + 2) * (mx.y - mn.y + 2) for _, _, mn, mx in items)
row_w = max(12.0, math.sqrt(total) * 1.3)
x = y = row_h = 0.0
for col, tops, mn, mx in items:
    w, d = mx.x - mn.x, mx.y - mn.y
    gap = max(1.0, 0.15 * max(w, d))
    if x > 0 and x + w > row_w: x = 0.0; y -= row_h + gap; row_h = 0.0
    off = Vector((x - mn.x, y - mx.y, -mn.z))
    for o in tops: o.location += off
    x += w + gap; row_h = max(row_h, d)

# weather layers ship hidden: unhide *_snow and *_puddles nodes to see snow caps and ponds
for o in bpy.data.objects:
    if o.name.endswith('_snow') or o.name.endswith('_puddles') or '_snow.' in o.name:
        o.hide_set(True); o.hide_render = True
# a sun, a sky and a camera that frames the lot, so it opens ready to look at
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(sun)
sun.data.energy = 3.5; sun.rotation_euler = (math.radians(55), 0, math.radians(-35))
w = bpy.data.worlds.new('sky'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.62, 0.66, 0.72, 1); sc.world = w
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in sc.objects if o.type == 'MESH' for c in o.bound_box]
if pts:
    c = sum(pts, Vector()) / len(pts); r = max((p - c).length for p in pts)
    cam = bpy.data.objects.new('camera', bpy.data.cameras.new('camera')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.clip_end = max(1000, r * 6); cam.location = c + Vector((r * 0.9, -r * 1.4, r * 1.0))
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
print('SAVED', out, len(items), 'files', os.path.getsize(out) // 1024, 'KB')
