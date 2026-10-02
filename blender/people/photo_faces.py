"""Photoreal heads for the low poly people, from the CC0 MakeHuman system assets (photo based skins, eyes, brows, lashes).
The head of the MakeHuman low poly proxy is cut at the neck, scaled to the person's head and skinned to the head bone;
the body stays faceted, so a real looking face sits on a low poly figure."""
import bpy, bmesh, json, os, random
from mathutils import Vector
MH = os.environ.get('PF_MH', '/home/claude/mh/x')
SK = json.load(open('/home/claude/mh/skins.json'))
_T = {}

def _imp(path):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path, forward_axis='NEGATIVE_Z', up_axis='Y')
    o = [x for x in bpy.data.objects if x not in before][0]
    from mathutils import Matrix
    # OBJ data stays Y up with the face toward +Z (the importer only rotates the object): bake Z up, face toward -Y, metres
    o.data.transform(Matrix(((0.1, 0, 0, 0), (0, 0, -0.1, 0), (0, 0.1, 0, 0), (0, 0, 0, 1))))
    o.rotation_euler = (0, 0, 0); o.scale = (1, 1, 1)
    for c in list(o.users_collection): c.objects.unlink(o)
    return o

def _img(path):
    n = os.path.basename(path); return bpy.data.images.get(n) or bpy.data.images.load(path)

def _mat(name, tex, alpha=False, rough=0.55, sss=0.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links
    b = N['Principled BSDF']; it = N.new('ShaderNodeTexImage'); it.image = _img(tex)
    L.new(it.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = rough
    if sss: b.inputs['Subsurface Weight'].default_value = sss; b.inputs['Subsurface Radius'].default_value = (0.9, 0.45, 0.25)
    if alpha:
        L.new(it.outputs['Alpha'], b.inputs['Alpha']); m.blend_method = 'HASHED'
    m['role'] = 'paint'
    return m

def load():
    if _T: return _T
    for sex, f in (('m', 'proxymeshes/male1591/male1591.obj'), ('f', 'proxymeshes/female1605/female1605.obj')):
        o = _imp(f'{MH}/{f}')
        zt = max(v.co.z for v in o.data.vertices)
        bm = bmesh.new(); bm.from_mesh(o.data)
        cut = zt - 0.31
        # keep the head and a column of neck; drop the shoulder flaps
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < cut or (v.co.z < zt - 0.235 and abs(v.co.x) > 0.06)], context='VERTS')
        bm.to_mesh(o.data); bm.free()
        ys = [v.co.y for v in o.data.vertices if v.co.z > zt - 0.2]
        _T[sex] = dict(obj=o, top=zt, yc=(min(ys) + max(ys)) / 2)
    eyes = _imp(f'{MH}/eyes/low-poly/low-poly.obj')
    brow = _imp(f'{MH}/eyebrows/eyebrow001/eyebrow001.obj')
    lash = _imp(f'{MH}/eyelashes/eyelashes01/eyelashes01.obj')
    # eyes, brows and lashes are authored on the base mesh; move them into each proxy head's eye sockets
    for sex in ('m', 'f'):
        o, zt = _T[sex]['obj'], _T[sex]['top']
        bm = bmesh.new(); bm.from_mesh(o.data)
        rim = [e for e in bm.edges if e.is_boundary and all(v.co.z > zt - 0.145 and v.co.y < -0.05 for v in e.verts)]   # sockets, not the mouth
        sock = {}
        for side in (1, -1):
            pts = [v.co.copy() for e in rim for v in e.verts if v.co.x * side > 0.005]
            sock[side] = sum(pts, Vector()) / max(1, len(pts))
        bm.free()
        ev = [v.co for v in eyes.data.vertices]
        ec = {side: sum((c for c in ev if c.x * side > 0), Vector()) / max(1, len([c for c in ev if c.x * side > 0])) for side in (1, -1)}
        sc = (sock[1].x - sock[-1].x) / max(1e-4, ec[1].x - ec[-1].x)
        mid_s = (sock[1] + sock[-1]) / 2; mid_e = (ec[1] + ec[-1]) / 2
        fit = lambda c, mid_e=mid_e, sc=sc, mid_s=mid_s: (c - mid_e) * sc + mid_s + Vector((0, 0.004, 0))
        _T[sex]['fit'] = fit
        _T[sex]['parts'] = {}
        for key, src in (('eyes', eyes), ('brow', brow), ('lash', lash)):
            me = src.data.copy()
            for v in me.vertices: v.co = fit(v.co)
            _T[sex]['parts'][key] = bpy.data.objects.new(f'tpl_{key}_{sex}', me)
    return _T

HAIR = dict(short='short02', crop='short03', curls='afro01', long='long01', bob='bob01', bun='braid01', ponytail='ponytail01')
def _hair_tpl(sex, style):
    key = f'hair_{style}_{sex}'
    if key in _T: return _T[key]
    src = _imp(f'{MH}/hair/{style}/{style}.obj')
    # fit by the skull: match the hair's crown band to the head's crown band (width and centre), then seat it on top
    head = _T[sex]['obj']; ht = _T[sex]['top']
    hv = [v.co for v in head.data.vertices if v.co.z > ht - 0.07]
    hw = max(c.x for c in hv) - min(c.x for c in hv); hy = (max(c.y for c in hv) + min(c.y for c in hv)) / 2
    sv = [v.co for v in src.data.vertices]; st = max(c.z for c in sv)
    band = [c for c in sv if c.z > st - 0.07 - THICK.get(style, 0.015)]
    sw = max(c.x for c in band) - min(c.x for c in band); sy = (max(c.y for c in band) + min(c.y for c in band)) / 2
    k = (hw + 2 * THICK.get(style, 0.015)) / max(sw, 1e-3)
    for v in src.data.vertices:
        c = v.co
        v.co = Vector((c.x * k, (c.y - sy) * k + hy + 0.004, (c.z - st) * k + ht + THICK.get(style, 0.015)))
    _T[key] = src; return src
THICK = dict(afro01=0.05, short02=0.012, short03=0.008, long01=0.012, bob01=0.014, braid01=0.012, ponytail01=0.012)

def _hair_mat(style, hex_col):
    import glob
    name = f'mh_hair_{style}_{hex_col}'
    m = bpy.data.materials.get(name)
    if m: return m
    tex = glob.glob(f'{MH}/hair/{style}/*diffuse*.png')[0]
    m = bpy.data.materials.new(name); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; b = N['Principled BSDF']
    it = N.new('ShaderNodeTexImage'); it.image = _img(tex)
    bw = N.new('ShaderNodeRGBToBW'); L.new(it.outputs['Color'], bw.inputs['Color'])
    h = hex_col.lstrip('#'); col = [((int(h[i:i + 2], 16) / 255) ** 2.2) for i in (0, 2, 4)]
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    gain = N.new('ShaderNodeMath'); gain.operation = 'MULTIPLY'; gain.inputs[1].default_value = 2.4
    L.new(bw.outputs['Val'], gain.inputs[0])
    cmb = N.new('ShaderNodeCombineColor'); [L.new(gain.outputs[0], cmb.inputs[i]) for i in range(3)]
    mul.inputs['A'].default_value = (*col, 1); L.new(cmb.outputs['Color'], mul.inputs['B']); L.new(mul.outputs['Result'], b.inputs['Base Color'])
    L.new(it.outputs['Alpha'], b.inputs['Alpha']); m.blend_method = 'HASHED'; b.inputs['Roughness'].default_value = 0.6
    m['role'] = 'paint'; return m

def pick_skin(sex, skin_hex, age, r):
    """The CC0 skin closest in tone to the person's skin colour, of their sex and age group."""
    def lum(h): h = h.lstrip('#'); return sum(int(h[i:i + 2], 16) for i in (0, 2, 4)) / 3
    want = lum(skin_hex); sx = 'male' if sex == 'm' else 'female'
    cands = [k for k in SK if k.endswith('_' + sx) or k.endswith('_' + sx + '2')]
    aged = [k for k in cands if k.startswith(age)] or cands
    aged.sort(key=lambda k: abs(lum(SK[k]['avg']) - want))
    return aged[0] if r.random() < 0.75 else aged[min(1, len(aged) - 1)]

def photo_head(name, sex, skin_key, eye, H, J, hair_kind=None, hair_hex='#3a2a1e'):
    T = load(); tpl = T[sex]
    s = (J['top'] - J['head']) / 0.235
    def place(src, key):
        o = bpy.data.objects.new(f'{name}_{key}', src.data.copy()); bpy.context.scene.collection.objects.link(o)
        for v in o.data.vertices:
            v.co = Vector((v.co.x * s, (v.co.y - tpl['yc']) * s + 0.005 * H, J['top'] - (tpl['top'] - v.co.z) * s))
        o.data.materials.clear(); return o
    head = place(tpl['obj'], 'photohead'); head.data.materials.append(_mat(f'mh_skin_{skin_key}', f"{MH}/{SK[skin_key]['png']}", sss=0.08))
    for p in head.data.polygons: p.use_smooth = True
    eyes = place(tpl['parts']['eyes'], 'eyes'); eyes.data.materials.append(_mat(f'mh_eye_{eye}', f'{MH}/eyes/materials/{eye}_eye.png', rough=0.15))
    for p in eyes.data.polygons: p.use_smooth = True
    brow = place(tpl['parts']['brow'], 'brow'); brow.data.materials.append(_mat('mh_brow', f'{MH}/eyebrows/eyebrow001/eyebrow001.png', alpha=True, rough=0.8))
    lash = place(tpl['parts']['lash'], 'lash'); lash.data.materials.append(_mat('mh_lash', f'{MH}/eyelashes/eyelashes01/eyelashes01.png', alpha=True, rough=0.8))
    out = [head, eyes, brow, lash]
    if hair_kind and hair_kind != 'bald':
        style = HAIR.get(hair_kind, 'short02')
        hr_ = place(_hair_tpl(sex, style), 'hairmh'); hr_.data.materials.append(_hair_mat(style, hair_hex))
        for p in hr_.data.polygons: p.use_smooth = True
        out.append(hr_)
    return out
