"""Low poly people for Coilover and Squall Cove.

Every person is built from faceted parts (lathed torso and head, tapered limbs, box hands and feet) in flat colours that
match the rest of the kit, then joined into one mesh skinned rigidly to a 17 bone armature: each part follows one bone,
which keeps the low poly look when it moves and keeps the mesh light. Four actions ship with every person: idle, walk
(a one second loop, in place), sit (for benches, patios and boats) and wave.

Blender frame: Z up, people face -Y (game +Z). Origin between the feet. Heights in metres."""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix, Euler
from pg_core import *

SKIN = ['#f3d4bf', '#eac0a0', '#d9a77f', '#c68b62', '#a8704a', '#8a5636', '#6e4128', '#53301d', '#3f2416']
HAIR = ['#1c1714', '#2e2119', '#4a3021', '#6b4a2e', '#8c6a3f', '#b38b55', '#d2b483', '#9a9a96', '#e6e2da', '#7a2f1d']
CLOTH = {
    'city':   ['#2f3a4a', '#4f6d8a', '#a33b2f', '#d9cfb8', '#2d2d30', '#6f7d55', '#c98b2e', '#e7e2d6', '#5a4a6e', '#8a3d52', '#3f6b63'],
    'desert': ['#c76b3a', '#e0b06a', '#8a5a3c', '#f0e6d2', '#5f7f8c', '#a14a2e', '#d9c39a', '#3d4e5c', '#7b6a4a'],
    'shield': ['#8c2f24', '#2f4a36', '#c7a24a', '#3b4a5c', '#6b5a3a', '#d8d2c2', '#a8432f', '#4a5a3a', '#26323c'],
    'harbour': ['#f2c12e', '#e0542b', '#1f3a5a', '#e9e4d8', '#2e5e7a', '#c43a2f', '#3a3a3a', '#f0f0ea', '#4a7a6a'],
}
DENIM = ['#2c3e5c', '#3a4f72', '#1f2a3a', '#4a5a6e']
SHOE = ['#2a2420', '#4a3424', '#e8e4dc', '#6b5a48', '#1a1a1c', '#8a5a32']

def taper(p0, p1, r0, r1, seg, m, name):
    """A tapered faceted limb from p0 to p1."""
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r0, radius2=r1, depth=d.length,
                          matrix=Matrix.Translation((0, 0, d.length / 2)))
    bmesh.ops.transform(bm, matrix=Matrix.Translation(p0) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4(), verts=bm.verts)
    return obj_from_bm(bm, name, m)

def lathe_part(profile, seg, m, name, sy=1.0, z0=0.0, rot=0.0):
    o = lathe(profile, seg=seg, material=m, name=name)
    o.data.transform(Matrix.Rotation(rot, 4, 'Z')); o.data.transform(Matrix.Diagonal((1, sy, 1, 1)))
    o.data.transform(Matrix.Translation((0, 0, z0))); return o

FACE_TEX = True        # faces come from a painted texture; False draws box eyes instead

def uv_box(me, head):
    """UVs for every face: a box projection in metres (one texture tile per 0.3 m) so fabric and skin textures can be
    stretched over any part, and a front projection for the face slot so a portrait texture lands on the face."""
    m = me.data; uv = m.uv_layers[0] if len(m.uv_layers) else m.uv_layers.new(name='UVMap'); uv.name = 'UVMap'; tile = 0.3
    face_slots = {i for i, mt in enumerate(m.materials) if mt and mt.name.startswith('pp_face_')}
    mh = {i for i, mt in enumerate(m.materials) if mt and mt.name.startswith('mh_')}
    old = m.uv_layers[0] if len(m.uv_layers) else None
    for pg in m.polygons:
        if pg.material_index in mh: continue
        n = pg.normal; ax = max(range(3), key=lambda k: abs(n[k]))
        for li in pg.loop_indices:
            co = m.vertices[m.loops[li].vertex_index].co
            if pg.material_index in face_slots:
                uv.data[li].uv = ((co.x - head['cx']) / (2.2 * head['hr']) + 0.5, (co.z - head['z0']) / head['hh'])
            else:
                a, b = [(co.y, co.z), (co.x, co.z), (co.x, co.y)][ax]
                uv.data[li].uv = (a / tile, b / tile)

def group(o, bone):
    vg = o.vertex_groups.new(name=bone); vg.add(list(range(len(o.data.vertices))), 1.0, 'REPLACE'); return o

def person(spec, name):
    """Build one person from a spec dict. Returns (armature, mesh)."""
    H, b = spec['height'], spec['build']
    if spec.get('photo') or spec.get('photo_tex'):
        import photo_faces as PF
        spec['skin'] = PF.SK[spec.get('photo') or spec['photo_tex']]['avg']   # hands and neck match the photographed skin
    M = lambda key, rough=0.85: mat(f'pp_{key}_{spec[key]}', spec[key], rough)
    skin, shoe, hair = M('skin', 0.7), M('shoes', 0.6), M('hair', 0.9)
    top = mat(f"pp_top_{spec['top_kind']}_{spec['top']}", spec['top'], 0.85 if spec['top_kind'] != 'slicker' else 0.35)
    bot = mat(f"pp_bottom_{'denim' if spec['bottom'] in DENIM else 'cotton'}_{spec['bottom']}", spec['bottom'], 0.85)
    face_m = (mat(f"pp_face_mh_{spec['photo_tex']}_{spec.get('eye', 'brown')}", spec['skin'], 0.6) if spec.get('photo_tex')
              else mat(f"pp_face_{spec['skin'][1:]}_{spec.get('face', 0)}", spec['skin'], 0.7))
    J = dict(ankle=0.045 * H, knee=0.285 * H, hip=0.52 * H, waist=0.6 * H, chest=0.71 * H, shoulder=0.815 * H, neck=0.84 * H,
             head=0.875 * H, top=H)
    hx = 0.052 * H * b; sx = 0.118 * H * (0.92 + 0.08 * b) * (1.0 if spec['sex'] == 'm' else 0.93)
    tw = 0.105 * H * b                       # half torso width
    parts = []
    def P(o, bone): parts.append(group(o, bone)); return o
    # ---- legs
    sleeve_long = spec['top'] in () or spec['sleeves'] == 'long'
    for s, side in ((1, 'L'), (-1, 'R')):
        x = s * hx
        legm = skin if spec['legs'] == 'shorts_skin' else bot
        thigh_m = bot if spec['legs'] != 'skirt_skin' else skin
        P(taper((x, 0, J['hip']), (x * 0.95, 0, J['knee']), 0.07 * H * b * 0.85, 0.05 * H * b * 0.85, 6, bot if spec['bottom_kind'] not in ('skirt', 'dress') else skin, f'{name}_thigh{side}'), f'thigh.{side}')
        shin_m = skin if spec['bottom_kind'] in ('shorts', 'skirt', 'dress') else bot
        P(taper((x * 0.95, 0, J['knee']), (x * 0.92, 0.005 * H, J['ankle'] + 0.01 * H), 0.048 * H * b * 0.85, 0.032 * H * b * 0.9, 6, shin_m, f'{name}_shin{side}'), f'shin.{side}')
        P(box((0.07 * H * b * 0.8, 0.15 * H * 0.85, 0.05 * H), (x * 0.92, -0.035 * H, 0.025 * H), material=shoe, name=f'{name}_foot{side}'), f'foot.{side}')
    # ---- hips and torso
    P(lathe_part([(0.0, J['hip'] - 0.04 * H), (0.82 * tw, J['hip'] - 0.035 * H), (0.92 * tw, J['hip'] + 0.02 * H), (0.88 * tw, J['waist']), (0.0, J['waist'])],
                 8, bot if spec['bottom_kind'] != 'dress' else top, f'{name}_pelvis', sy=0.62, rot=math.pi / 8), 'hips')
    if spec['bottom_kind'] in ('skirt', 'dress'):
        P(lathe_part([(0.0, J['hip'] - 0.17 * H), (1.25 * tw, J['hip'] - 0.17 * H), (0.9 * tw, J['hip'] + 0.02 * H), (0.0, J['hip'] + 0.02 * H)],
                     8, top if spec['bottom_kind'] == 'dress' else bot, f'{name}_skirt', sy=0.75, rot=math.pi / 8), 'hips')
    chest_w = tw * (1.08 if spec['sex'] == 'm' else 0.98)
    P(lathe_part([(0.0, J['waist']), (0.86 * tw, J['waist']), (0.92 * chest_w, J['chest']), (0.0, J['chest'])], 8, top, f'{name}_belly', sy=0.6, rot=math.pi / 8), 'spine')
    P(lathe_part([(0.0, J['chest']), (0.94 * chest_w, J['chest']), (1.0 * chest_w, J['shoulder'] - 0.015 * H), (0.55 * chest_w, J['neck']), (0.0, J['neck'])],
                 8, top, f'{name}_chest', sy=0.62, rot=math.pi / 8), 'chest')
    if spec['top_kind'] in ('jacket', 'slicker', 'plaid', 'vest', 'lifevest', 'apron'):
        acc = M('accent')
        if spec['top_kind'] in ('vest', 'lifevest'):
            P(lathe_part([(0.0, J['waist'] + 0.01 * H), (0.95 * tw, J['waist'] + 0.01 * H), (1.06 * chest_w, J['shoulder'] - 0.04 * H), (0.0, J['shoulder'] - 0.04 * H)],
                         8, acc, f'{name}_vest', sy=0.7, rot=math.pi / 8), 'chest')
        elif spec['top_kind'] == 'apron':
            P(box((1.3 * tw, 0.01 * H, 0.3 * H), (0, -0.068 * H, J['hip'] + 0.09 * H), material=acc, name=f'{name}_apron'), 'spine')
        else:   # a jacket hem and collar in the accent colour
            P(lathe_part([(0.0, J['waist'] - 0.03 * H), (0.98 * tw, J['waist'] - 0.03 * H), (0.98 * tw, J['waist'] + 0.015 * H), (0.0, J['waist'] + 0.015 * H)], 8, acc, f'{name}_hem', sy=0.68, rot=math.pi / 8), 'spine')
            P(lathe_part([(0.0, J['neck'] - 0.025 * H), (0.6 * chest_w, J['neck'] - 0.025 * H), (0.45 * chest_w, J['neck'] + 0.01 * H), (0.0, J['neck'] + 0.01 * H)], 8, acc, f'{name}_collar', sy=0.8, rot=math.pi / 8), 'chest')
    if 'backpack' in spec['extras']:
        P(box((1.2 * tw, 0.09 * H, 0.2 * H), (0, 0.105 * H, J['chest'] - 0.01 * H), material=mat('pp_pack', '#3d4a3a', 0.85), name=f'{name}_pack'), 'chest')
    # ---- arms, A pose
    a = math.radians(12)
    for s, side in ((1, 'L'), (-1, 'R')):
        sh = Vector((s * sx, 0.005 * H, J['shoulder'] - 0.012 * H))
        el = sh + Vector((s * math.sin(a), 0, -math.cos(a))) * 0.175 * H
        wr = el + Vector((s * math.sin(a * 0.6), -0.01, -math.cos(a * 0.6))) * 0.155 * H
        tip = wr + Vector((s * 0.01, -0.005, -1)) * 0.085 * H
        arm_m = top if spec['sleeves'] != 'none' else skin
        P(taper(sh, el, 0.042 * H * b, 0.033 * H * b, 6, arm_m, f'{name}_uarm{side}'), f'upper_arm.{side}')
        P(taper(el, wr, 0.032 * H * b, 0.025 * H * b, 6, top if spec['sleeves'] == 'long' else skin, f'{name}_farm{side}'), f'forearm.{side}')
        P(box((0.045 * H * b, 0.03 * H, 0.085 * H), (tip + wr) / 2, material=skin, name=f'{name}_hand{side}'), f'hand.{side}')
        P(ico(0.037 * H * b, 1, sh + Vector((0, 0, -0.012 * H)), arm_m, name=f'{name}_shoulder{side}'), f'upper_arm.{side}')
    # ---- neck and head
    if not spec.get('photo'):
        P(taper((0, 0.005 * H, J['neck'] - 0.01 * H), (0, 0.005 * H, J['head'] + 0.01 * H), 0.034 * H, 0.032 * H, 6, skin, f'{name}_neck'), 'neck')
    hh = J['top'] - J['head']                                           # head height
    hr = 0.062 * H
    head = lathe_part([(0.0, J['head']), (0.62 * hr, J['head'] + 0.02 * H), (0.98 * hr, J['head'] + 0.45 * hh), (0.92 * hr, J['head'] + 0.78 * hh), (0.55 * hr, J['top'] - 0.005 * H), (0.0, J['top'])],
                      8, skin, f'{name}_head', sy=1.1, rot=math.pi / 8)
    if spec.get('photo'):
        for o in PF.photo_head(name, spec['sex'], spec['photo'], spec.get('eye', 'brown'), H, J, spec['hair_kind'], spec['hair']): P(o, 'head')
        bpy.data.objects.remove(head)
    head = None if spec.get('photo') else head
    if head is not None: head.data.update(); head.data.materials.append(face_m)
    if head is not None:
        for pg in head.data.polygons:
            if spec.get('photo_tex'):
                if pg.normal.y < 0.3: pg.material_index = 1     # the photo wraps the front and stretches round the sides
            elif pg.normal.y < -0.35 and pg.center.z > J['head'] + 0.08 * hh: pg.material_index = 1
        P(head, 'head')
    fy = -1.1 * hr * 0.98
    if not spec.get('photo'):
        P(box((0.018 * H, 0.025 * H, 0.03 * H), (0, fy - 0.006 * H, J['head'] + 0.4 * hh), rot=(0.4, 0, 0), material=face_m if spec.get('photo_tex') else skin, name=f'{name}_nose'), 'head')
    eye = mat('pp_eye', '#1e1a18', 0.6)
    for s in ((1, -1) if not (FACE_TEX or spec.get('photo')) else ()):
        P(box((0.012 * H, 0.006 * H, 0.009 * H), (s * 0.026 * H, fy + 0.008 * H, J['head'] + 0.56 * hh), material=eye, name=f'{name}_eye'), 'head')
    if 'glasses' in spec['extras'] and not (spec.get('photo') or spec.get('photo_tex')):
        gm = mat('pp_glasses', '#2a2a2a', 0.4)
        P(box((0.11 * H, 0.008 * H, 0.012 * H), (0, fy - 0.002 * H, J['head'] + 0.57 * hh), material=gm, name=f'{name}_glasses'), 'head')
    # ---- hair
    hs = spec['hair_kind']
    cap_prof = lambda lo, r=1.06: [(0.0, J['head'] + lo * hh), (r * hr, J['head'] + lo * hh), (r * 1.0 * hr, J['head'] + 0.78 * hh), (0.62 * r * hr, J['top'] + 0.012 * H), (0.0, J['top'] + 0.016 * H)]
    if hs != 'bald' and not spec.get('photo'):
        lo = {'short': 0.62, 'crop': 0.7, 'long': 0.35, 'bob': 0.4, 'bun': 0.6, 'ponytail': 0.6, 'curls': 0.5}[hs]
        cap = lathe_part(cap_prof(lo, 1.08 if hs != 'curls' else 1.22), 8, hair, f'{name}_hair', sy=1.12, rot=math.pi / 8)
        # open the face: push front verts back behind the face plane
        for v in cap.data.vertices:
            if v.co.y < -0.6 * hr and v.co.z < J['head'] + 0.82 * hh: v.co.y = -0.55 * hr
        P(cap, 'head')
        if hs == 'long':
            P(box((1.7 * hr, 0.06 * H, 0.17 * H), (0, 0.55 * hr, J['head'] + 0.05 * hh), material=hair, name=f'{name}_hairlong'), 'head')
        if hs == 'bun': P(ico(0.4 * hr, 1, (0, 0.7 * hr, J['head'] + 0.85 * hh), hair, name=f'{name}_bun'), 'head')
        if hs == 'ponytail': P(taper((0, 0.9 * hr, J['head'] + 0.7 * hh), (0, 1.25 * hr, J['head'] - 0.05 * hh), 0.25 * hr, 0.12 * hr, 5, hair, f'{name}_tail'), 'head')
    # ---- hats
    hat = spec['hat'] if not spec.get('photo') else None
    if hat:
        hm = M('hat_col', 0.8)
        top_z = J['top'] + 0.01 * H
        if hat == 'cap':
            P(cyl(1.08 * hr, 0.95 * hr, 0.07 * H, 8, (0, 0, J['head'] + 0.7 * hh), material=hm, name=f'{name}_cap'), 'head')
            P(box((1.3 * hr, 1.0 * hr, 0.008 * H), (0, -1.2 * hr, J['head'] + 0.7 * hh), material=hm, name=f'{name}_brim'), 'head')
        elif hat == 'beanie':
            P(lathe_part([(0.0, J['head'] + 0.6 * hh), (1.1 * hr, J['head'] + 0.6 * hh), (1.0 * hr, top_z), (0.0, top_z + 0.03 * H)], 8, hm, f'{name}_beanie', sy=1.12, rot=math.pi / 8), 'head')
        elif hat in ('sunhat', 'souwester'):
            brim_r = 2.1 * hr if hat == 'sunhat' else 1.7 * hr
            P(cyl(brim_r, brim_r * 0.92, 0.012 * H, 10, (0, 0, J['head'] + 0.72 * hh), material=hm, name=f'{name}_hatbrim'), 'head')
            P(cyl(1.05 * hr, 0.85 * hr, 0.08 * H, 8, (0, 0, J['head'] + 0.72 * hh), material=hm, name=f'{name}_hatcrown'), 'head')
        elif hat == 'hardhat':
            P(lathe_part([(0.0, J['head'] + 0.68 * hh), (1.3 * hr, J['head'] + 0.68 * hh), (1.1 * hr, J['head'] + 0.74 * hh), (1.05 * hr, top_z), (0.0, top_z + 0.04 * H)], 8, hm, f'{name}_hardhat', sy=1.1, rot=math.pi / 8), 'head')
    me = join(parts, name + '_mesh')
    for p in me.data.polygons:
        if not me.data.materials[p.material_index].name.startswith('mh_'): p.use_smooth = False
    uv_box(me, dict(cx=0.0, hr=hr, z0=J['head'], hh=hh))
    # ---- armature
    arm = bpy.data.armatures.new(name + '_rig'); rig = bpy.data.objects.new(name, arm); link(rig)
    bpy.context.view_layer.objects.active = rig; rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    E = arm.edit_bones
    def bone(n, h, t, parent=None):
        e = E.new(n); e.head = h; e.tail = t
        if parent: e.parent = E[parent]
        return e
    bone('root', (0, 0, 0), (0, 0.15 * H, 0))
    bone('hips', (0, 0, J['hip']), (0, 0, J['waist']), 'root')
    bone('spine', (0, 0, J['waist']), (0, 0, J['chest']), 'hips')
    bone('chest', (0, 0, J['chest']), (0, 0, J['neck'] - 0.01 * H), 'spine')
    bone('neck', (0, 0.005 * H, J['neck'] - 0.01 * H), (0, 0.005 * H, J['head']), 'chest')
    bone('head', (0, 0.005 * H, J['head']), (0, 0.005 * H, J['top']), 'neck')
    for s, side in ((1, 'L'), (-1, 'R')):
        sh = Vector((s * sx, 0.005 * H, J['shoulder'] - 0.012 * H))
        el = sh + Vector((s * math.sin(a), 0, -math.cos(a))) * 0.175 * H
        wr = el + Vector((s * math.sin(a * 0.6), -0.01, -math.cos(a * 0.6))) * 0.155 * H
        bone(f'upper_arm.{side}', sh, el, 'chest'); bone(f'forearm.{side}', el, wr, f'upper_arm.{side}')
        bone(f'hand.{side}', wr, wr + Vector((0, 0, -0.085 * H)), f'forearm.{side}')
        x = s * hx
        bone(f'thigh.{side}', (x, 0, J['hip']), (x * 0.95, 0, J['knee']), 'hips')
        bone(f'shin.{side}', (x * 0.95, 0, J['knee']), (x * 0.92, 0.005 * H, J['ankle'] + 0.01 * H), f'thigh.{side}')
        bone(f'foot.{side}', (x * 0.92, 0.005 * H, J['ankle'] + 0.01 * H), (x * 0.92, -0.11 * H, 0.012 * H), f'shin.{side}')
    for e in E:                                         # zero roll keeps every bone's X axis on world X: one rule for poses
        e.roll = 0.0
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in rig.pose.bones: pb.rotation_mode = 'XYZ'      # the shared actions key Euler rotations
    me.parent = rig
    mod = me.modifiers.new('rig', 'ARMATURE'); mod.object = rig
    rig['height'] = H; rig['hip_height'] = J['hip']
    for k in ('theme', 'sex', 'top_kind', 'bottom_kind', 'hair_kind'): rig[k] = spec[k]
    return rig, me

def spec_for(theme, seed):
    r = random.Random(seed)
    sex = r.choice('mf'); C = CLOTH[theme]
    H = r.uniform(1.66, 1.9) if sex == 'm' else r.uniform(1.55, 1.78)
    if r.random() < 0.1: H = r.uniform(1.15, 1.4)                      # a kid now and then
    top_kind = r.choice({'city': ['tee', 'long', 'jacket', 'jacket', 'tee', 'dress' if sex == 'f' else 'long'],
                         'desert': ['tee', 'tee', 'vest', 'apron', 'long'],
                         'shield': ['plaid', 'jacket', 'tee', 'lifevest', 'long'],
                         'harbour': ['slicker', 'slicker', 'lifevest', 'tee', 'jacket']}[theme])
    bottom_kind = 'dress' if top_kind == 'dress' else r.choice(['pants', 'pants', 'pants', 'shorts'] + (['skirt'] if sex == 'f' and theme == 'city' else []))
    if theme in ('shield', 'harbour') and bottom_kind == 'shorts' and r.random() < 0.6: bottom_kind = 'pants'
    hair_kind = r.choice(['short', 'crop', 'bald', 'curls'] if sex == 'm' else ['long', 'bob', 'bun', 'ponytail', 'curls', 'short'])
    hat = r.choice({'city': [None, None, None, 'cap', 'beanie'], 'desert': ['sunhat', 'cap', None, 'cap', 'hardhat'],
                    'shield': ['beanie', 'cap', None, None], 'harbour': ['souwester', 'beanie', None, 'cap']}[theme])
    top = r.choice(C)
    if top_kind == 'slicker': top = r.choice(['#f2c12e', '#e0542b', '#2e5e7a'])
    if top_kind == 'plaid': top = r.choice(['#8c2f24', '#2f4a36', '#3b4a5c'])
    accent = r.choice(C)
    if top_kind == 'lifevest': accent = r.choice(['#e0542b', '#f2c12e'])
    if top_kind == 'apron': accent = r.choice(['#e9e4d8', '#6b4a2e', '#2d2d30'])
    return dict(theme=theme, sex=sex, height=H, build=r.uniform(0.88, 1.2), skin=r.choice(SKIN), hair=r.choice(HAIR[:8] if H > 1.4 else HAIR[:7]),
                top=top, accent=accent, top_kind=top_kind, sleeves='none' if (top_kind == 'tee' and r.random() < 0.25) else ('long' if top_kind in ('long', 'jacket', 'slicker', 'plaid') else 'short'),
                bottom=r.choice(DENIM + C[:3]), bottom_kind=bottom_kind, legs='', shoes=r.choice(SHOE), hair_kind=hair_kind, hat=hat,
                hat_col=r.choice(C), face=r.randrange(3), extras=[e for e in ('backpack', 'glasses') if r.random() < 0.18])

# ---------------------------------------------------------------- actions (shared by every rig: same bone names)
FPS = 24
def _key(rig, bone, rot, frame, loc=None):
    pb = rig.pose.bones[bone]; pb.rotation_mode = 'XYZ'; pb.rotation_euler = rot; pb.keyframe_insert('rotation_euler', frame=frame)
    if loc is not None: pb.location = loc; pb.keyframe_insert('location', frame=frame)

def make_actions(rig):
    """Builds idle, walk, sit and wave on this rig and returns the actions (reuse them on other rigs)."""
    H = rig['height']; hip = rig['hip_height']; acts = {}
    bones = [b.name for b in rig.pose.bones]
    def start(name):
        rig.animation_data_create(); act = bpy.data.actions.new(name); rig.animation_data.action = act
        for b in rig.pose.bones: b.rotation_mode = 'XYZ'; b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
        return act
    def finish(name, act):
        for fc in act.fcurves:
            for k in fc.keyframe_points: k.interpolation = 'BEZIER'
        act.use_fake_user = True; acts[name] = act
    # walk: one stride per leg in 24 frames
    act = start('walk')
    for f in range(0, 25, 3):
        t = f / 24 * 2 * math.pi; s = math.sin(t)
        _key(rig, 'thigh.L', (-0.45 * s, 0, 0), f); _key(rig, 'thigh.R', (0.45 * s, 0, 0), f)
        _key(rig, 'shin.L', (0.75 * max(0.0, math.sin(t + 1.6)), 0, 0), f); _key(rig, 'shin.R', (0.75 * max(0.0, math.sin(t + 1.6 + math.pi)), 0, 0), f)
        _key(rig, 'foot.L', (0.2 * s, 0, 0), f); _key(rig, 'foot.R', (-0.2 * s, 0, 0), f)
        _key(rig, 'upper_arm.L', (0.4 * s, 0, 0), f); _key(rig, 'upper_arm.R', (-0.4 * s, 0, 0), f)
        _key(rig, 'forearm.L', (-0.35 - 0.2 * max(0, s), 0, 0), f); _key(rig, 'forearm.R', (-0.35 - 0.2 * max(0, -s), 0, 0), f)
        _key(rig, 'hips', (0, 0, 0.08 * s), f, loc=(0, 0.02 * H * abs(math.cos(t)), 0))
        _key(rig, 'chest', (0.05, 0, -0.1 * s), f)
    finish('walk', act)
    # idle: breathing and a slow weight shift over four seconds
    act = start('idle')
    for f in range(0, 97, 12):
        t = f / 96 * 2 * math.pi
        _key(rig, 'chest', (0.02 * math.sin(2 * t), 0, 0), f); _key(rig, 'hips', (0, 0.03 * math.sin(t), 0), f)
        _key(rig, 'head', (0.03 * math.sin(t + 1), 0, 0.08 * math.sin(t * 0.5)), f)
        for side, sg in (('L', 1), ('R', -1)):
            _key(rig, f'upper_arm.{side}', (0.03 * math.sin(2 * t), 0, 0), f); _key(rig, f'forearm.{side}', (-0.12, 0, 0), f)
    finish('idle', act)
    # sit: hips down to a 0.46 m seat, thighs forward, shins down
    act = start('sit')
    for f in (0, 24):
        _key(rig, 'root', (0, 0, 0), f, loc=(0, 0, 0))
        _key(rig, 'hips', (0, 0, 0), f, loc=(0, -(hip - 0.46), 0))     # hips bone local Y is world up
        for side in 'LR':
            _key(rig, f'thigh.{side}', (-1.5, 0, 0), f); _key(rig, f'shin.{side}', (1.45, 0, 0), f); _key(rig, f'foot.{side}', (0.05, 0, 0), f)
            _key(rig, f'upper_arm.{side}', (-0.35, 0, 0), f); _key(rig, f'forearm.{side}', (-0.9, 0, 0), f)
        _key(rig, 'chest', (0.06 * math.sin(f), 0, 0), f)
    finish('sit', act)
    # wave: right arm up, forearm swinging
    act = start('wave')
    for f in range(0, 25, 4):
        t = f / 24 * 2 * math.pi
        _key(rig, 'upper_arm.R', (0, 0, 2.5), f); _key(rig, 'forearm.R', (0, 0, 0.35 + 0.35 * math.sin(2 * t)), f)
        _key(rig, 'upper_arm.L', (0.03, 0, 0), f); _key(rig, 'forearm.L', (-0.15, 0, 0), f); _key(rig, 'head', (0.05, 0, 0.1), f)
    finish('wave', act)
    rig.animation_data.action = acts['idle']
    return acts

def pose_static(rig, act, frame):
    """Set a still pose from an action frame (for sheets and placed props)."""
    rig.animation_data_create(); rig.animation_data.action = act; bpy.context.scene.frame_set(frame)

# ---------------------------------------------------------------- textures stretched over the people
TEX = '/home/claude/procgen/out/people_tex'
def texture_people(px=256):
    """Swap the flat colours of every pp_ material for a texture tinted by that colour: painted faces on the face slot,
    denim, cotton, knit, plaid and slicker on clothes, strands on hair. Uses the UVMap, so it exports with the GLB."""
    import os
    def img(name):
        im = bpy.data.images.get(name) or bpy.data.images.load(f'{TEX}/{name}')
        return im
    for m in bpy.data.materials:
        n = m.name
        if not n.startswith('pp_') or not m.use_nodes: continue
        b = m.node_tree.nodes.get('Principled BSDF')
        if not b: continue
        if n.startswith('pp_face_mh_'):
            fname, tint = f"photo_flat/{n[len('pp_face_mh_'):]}.png", False
        elif n.startswith('pp_face_'):
            parts = n.split('_'); fname = f'face_{parts[2]}_{parts[3]}.png'; tint = False
        elif n.startswith('pp_bottom_denim'): fname, tint = 'denim.png', True
        elif n.startswith('pp_bottom_'): fname, tint = 'cotton.png', True
        elif n.startswith('pp_top_plaid'): fname, tint = 'plaid.png', True
        elif n.startswith('pp_top_slicker'): fname, tint = 'slicker.png', True
        elif n.startswith('pp_top_'): fname, tint = ('knit.png' if any(k in n for k in ('long', 'jacket')) else 'cotton.png'), True
        elif n.startswith('pp_hair_'): fname, tint = 'hair.png', True
        else: continue
        if not os.path.exists(f'{TEX}/{fname}'): continue
        nt = m.node_tree; N = nt.nodes; L = nt.links
        uvn = N.new('ShaderNodeUVMap'); uvn.uv_map = 'UVMap'
        it = N.new('ShaderNodeTexImage'); it.image = img(fname); it.interpolation = 'Linear'
        if n.startswith('pp_face_'): it.extension = 'EXTEND'
        L.new(uvn.outputs['UV'], it.inputs['Vector'])
        if tint:
            mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
            mul.inputs['A'].default_value = b.inputs['Base Color'].default_value
            L.new(it.outputs['Color'], mul.inputs['B']); L.new(mul.outputs['Result'], b.inputs['Base Color'])
        else:
            L.new(it.outputs['Color'], b.inputs['Base Color'])
