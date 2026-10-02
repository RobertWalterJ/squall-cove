"""Squall Cove procedural asset kit: shared geometry and material helpers.
Blender 4.2, Z-up, metres. Boats face +X. glTF export converts to Y-up.
"""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise

# ---------------------------------------------------------------- scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.clear()

def link(o):
    bpy.context.scene.collection.objects.link(o)
    return o

# ---------------------------------------------------------------- colour + materials
def lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def hexrgb(h):
    h = h.lstrip('#')
    return tuple(lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))

MATS = {}
def mat(name, color='#888888', rough=0.6, metal=0.0, emit=None, emit_str=3.0, alpha=1.0, transmission=0.0, vcol=False):
    """Principled material. vcol=True multiplies base colour by the mesh's 'Col' attribute (exported to glTF as COLOR_0)."""
    key = (name, color, rough, metal, emit, alpha, transmission, vcol)
    if key in MATS:
        return MATS[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*hexrgb(color), 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if vcol:
        ca = nt.nodes.new('ShaderNodeVertexColor'); ca.layer_name = 'Col'
        nt.links.new(ca.outputs['Color'], b.inputs['Base Color'])
    if emit:
        b.inputs['Emission Color'].default_value = (*hexrgb(emit), 1)
        b.inputs['Emission Strength'].default_value = emit_str
    if transmission:
        b.inputs['Transmission Weight'].default_value = transmission
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
        m.blend_method = 'BLEND'
    MATS[key] = m
    return m

# ---------------------------------------------------------------- mesh building
def obj_from_bm(bm, name, material=None, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    if material:
        me.materials.append(material)
    for p in me.polygons:
        p.use_smooth = smooth
    return link(o)

def mesh(name, verts, faces, material=None, smooth=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate(); me.update()
    o = bpy.data.objects.new(name, me)
    if material:
        me.materials.append(material)
    for p in me.polygons:
        p.use_smooth = smooth
    return link(o)

def xf(loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    return Matrix.LocRotScale(Vector(loc), Matrix.Rotation(rot[2], 3, 'Z') @ Matrix.Rotation(rot[1], 3, 'Y') @ Matrix.Rotation(rot[0], 3, 'X'), Vector(scale))

def box(size, loc=(0, 0, 0), rot=(0, 0, 0), material=None, bevel=0.0, name='box'):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=min(bevel / max(min(size), 1e-3), 0.45), segments=1, affect='EDGES')
    bmesh.ops.transform(bm, matrix=xf(loc, rot, size), verts=bm.verts)
    return obj_from_bm(bm, name, material)

def cyl(r1, r2, h, seg=12, loc=(0, 0, 0), rot=(0, 0, 0), material=None, caps=True, name='cyl', smooth=False):
    """Cylinder/cone along local Z, base at z=0."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=r1, radius2=r2, depth=h,
                          matrix=Matrix.Translation((0, 0, h / 2)))
    bmesh.ops.transform(bm, matrix=xf(loc, rot), verts=bm.verts)
    return obj_from_bm(bm, name, material, smooth)

def rod(p0, p1, r, seg=6, material=None, name='rod'):
    """Cylinder between two points (stays, rails, braces)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    q = d.to_track_quat('Z', 'Y')
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r, depth=d.length,
                          matrix=Matrix.Translation((0, 0, d.length / 2)))
    bmesh.ops.transform(bm, matrix=Matrix.Translation(p0) @ q.to_matrix().to_4x4(), verts=bm.verts)
    return obj_from_bm(bm, name, material)

def torus(R, r, seg=16, sides=6, loc=(0, 0, 0), rot=(0, 0, 0), material=None, arc=2 * math.pi, name='torus'):
    verts, faces = [], []
    closed = abs(arc - 2 * math.pi) < 1e-6
    n = seg if closed else seg + 1
    for i in range(n):
        a = arc * i / seg
        for j in range(sides):
            b = 2 * math.pi * j / sides
            rr = R + r * math.cos(b)
            verts.append((rr * math.cos(a), rr * math.sin(a), r * math.sin(b)))
    for i in range(seg):
        i2 = (i + 1) % n
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append((i * sides + j, i2 * sides + j, i2 * sides + j2, i * sides + j2))
    M = xf(loc, rot)
    return mesh(name, [M @ Vector(v) for v in verts], faces, material)

def ico(r, sub=2, loc=(0, 0, 0), material=None, name='ico'):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r, matrix=Matrix.Translation(loc))
    return obj_from_bm(bm, name, material)

def lathe(profile, seg=16, material=None, name='lathe', cap_top=True, cap_bottom=True, smooth=False):
    """profile: list of (r, z) bottom->top. Revolved around Z."""
    verts, faces = [], []
    for (r, z) in profile:
        for i in range(seg):
            a = 2 * math.pi * i / seg
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for k in range(len(profile) - 1):
        for i in range(seg):
            i2 = (i + 1) % seg
            faces.append((k * seg + i, k * seg + i2, (k + 1) * seg + i2, (k + 1) * seg + i))
    if cap_bottom and profile[0][0] > 1e-4:
        faces.append(tuple(reversed(range(seg))))
    if cap_top and profile[-1][0] > 1e-4:
        base = (len(profile) - 1) * seg
        faces.append(tuple(base + i for i in range(seg)))
    return mesh(name, verts, faces, material, smooth)

def join(objs, name):
    objs = [o for o in objs if o is not None]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = name
    o.data.name = name
    return o

def place(o, loc=(0, 0, 0), rotz=0.0):
    o.location = loc
    o.rotation_euler = (0, 0, rotz)
    return o

def apply_mods(o):
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)

def solidify(o, t, offset=-1):
    m = o.modifiers.new('solid', 'SOLIDIFY'); m.thickness = t; m.offset = offset
    apply_mods(o)
    return o

def set_vcol(o, fn):
    """Per-corner colour from fn(vertex_co, normal) -> (r,g,b) linear. Stored as 'Col'."""
    me = o.data
    attr = me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index]
            c = fn(v.co, poly.normal)
            attr.data[li].color = (*c, 1.0)

def tri_count(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)

def dims(o):
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return tuple(round(max(v[i] for v in bb) - min(v[i] for v in bb), 2) for i in range(3))

def export_glb(objs, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, use_selection=True, export_apply=True, export_yup=True, export_extras=True)

def fbm3(p, octaves=4, lac=2.0, gain=0.5):
    s, a, f = 0.0, 0.5, 1.0
    for _ in range(octaves):
        s += a * noise.noise(p * f, noise_basis='PERLIN_NEW')
        f *= lac; a *= gain
    return s

def rng(seed):
    """Seeded generator salted with the calling generator's name, so seed 2 of a dinghy and seed 2 of a tug differ independently."""
    import sys
    return random.Random(f'{sys._getframe(1).f_code.co_name}:{seed}')
