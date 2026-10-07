"""Parses assets/emplace2.glb: node tree, kinematic chains, triangles per model, accessor validity, unit normals, materials, pivots, markers, bounds.
usage (from the game dir): python blender/emplace2/verify_emplace2.py"""
import json, struct, base64, sys
import numpy as np
b = open('assets/emplace2.glb', 'rb').read()
assert b[:4] == b'glTF' and struct.unpack('<I', b[8:12])[0] == len(b)
raw = open('assets/emplace2.glb.b64.txt').read()
assert base64.b64decode(raw) == b, 'b64 does not match glb'; assert '\n' not in raw, 'b64 not one line'
jl = struct.unpack('<I', b[12:16])[0]; J = json.loads(b[20:20 + jl]); BIN = b[20 + jl + 8:]
N = J['nodes']; A = J['accessors']; BV = J['bufferViews']
CT = {5126: ('<f4', 4), 5125: ('<u4', 4), 5123: ('<u2', 2), 5121: ('<u1', 1)}; NC = {'SCALAR': 1, 'VEC3': 3, 'VEC2': 2, 'VEC4': 4}
MATS = [m['name'] for m in J['materials']]
def acc(i):
    a = A[i]; bv = BV[a['bufferView']]; dt, sz = CT[a['componentType']]; n = NC[a['type']]
    assert a.get('byteOffset', 0) + a['count'] * n * sz <= bv['byteLength']
    return np.frombuffer(BIN, dt, a['count'] * n, bv.get('byteOffset', 0) + a.get('byteOffset', 0)).reshape(a['count'], n)
def mat4(n):
    t = np.eye(4); t[:3, 3] = n.get('translation', [0, 0, 0]); return t
CHAIN = {  # node -> expected parent
    'emp_aa_yaw': 'emp_aa', 'emp_aa_pitch': 'emp_aa_yaw', 'emp_aa_barrels': 'emp_aa_pitch', 'emp_aa_muzzle_L': 'emp_aa_barrels', 'emp_aa_muzzle_R': 'emp_aa_barrels',
    'emp_aa_casing': 'emp_aa_barrels', 'emp_aa_seat': 'emp_aa_yaw',
    'emp_mg_yaw': 'emp_mg', 'emp_mg_pitch': 'emp_mg_yaw', 'emp_mg_barrel': 'emp_mg_pitch', 'emp_mg_muzzle': 'emp_mg_barrel', 'emp_mg_casing': 'emp_mg_pitch', 'emp_mg_seat': 'emp_mg',
    'emp_mortar_yaw': 'emp_mortar', 'emp_mortar_pitch': 'emp_mortar_yaw', 'emp_mortar_muzzle': 'emp_mortar_pitch',
    'emp_howitzer_yaw': 'emp_howitzer', 'emp_howitzer_pitch': 'emp_howitzer_yaw', 'emp_howitzer_barrel': 'emp_howitzer_pitch', 'emp_howitzer_muzzle': 'emp_howitzer_barrel',
    'emp_howitzer_crew_gunner': 'emp_howitzer_yaw', 'emp_howitzer_crew_loader': 'emp_howitzer', 'emp_howitzer_crew_ammo': 'emp_howitzer', 'emp_howitzer_crew_commander': 'emp_howitzer',
    'emp_flak_yaw': 'emp_flak', 'emp_flak_pitch': 'emp_flak_yaw', 'emp_flak_barrel': 'emp_flak_pitch', 'emp_flak_muzzle': 'emp_flak_barrel', 'emp_flak_casing': 'emp_flak_barrel', 'emp_flak_seat': 'emp_flak_yaw',
    'tower_guard_wood_lamp': 'tower_guard_wood', 'tower_guard_steel_lamp': 'tower_guard_steel',
}
for t in ('wood', 'concrete', 'steel'):
    for m in ('ladder_bottom', 'ladder_top', 'deck', 'seat'): CHAIN['tower_guard_%s_%s' % (t, m)] = 'tower_guard_' + t
CHAIN['tower_guard_concrete_roof'] = 'tower_guard_concrete'
for l in ('ladder_4m', 'ladder_8m', 'ladder_hoops_6m'):
    for m in ('ladder_bottom', 'ladder_top'): CHAIN[l + '_' + m] = l
ROOTS = ['emp_aa', 'emp_mg', 'emp_mortar', 'emp_howitzer', 'emp_flak', 'tower_guard_wood', 'tower_guard_concrete', 'tower_guard_steel', 'ladder_4m', 'ladder_8m', 'ladder_hoops_6m']
roots = [N[r]['name'] for r in J['scenes'][0]['nodes']]
print('top-level:', roots); assert sorted(roots) == sorted(ROOTS), 'root names'
parent = {}
for i, n in enumerate(N):
    for c in n.get('children', []): parent[N[c]['name']] = n['name']
state = {'bad': 0}
for nm, par in CHAIN.items():
    if parent.get(nm) != par: print('CHAIN ERROR', nm, 'parent', parent.get(nm), 'expected', par); state['bad'] += 1
def walk(i, M, out, depth):
    n = N[i]; M2 = M @ mat4(n); name = n['name']
    if n.get('rotation') and any(abs(x) > 1e-6 for x in n['rotation'][:3]): print('WARN rotation on', name); state['bad'] += 1
    if n.get('scale') and any(abs(x - 1) > 1e-6 for x in n['scale']) and not (name.endswith('_deck') or name.endswith('_roof')): print('WARN scale on', name); state['bad'] += 1
    tris = 0; bb = None; used = set()
    if 'mesh' in n:
        for p in J['meshes'][n['mesh']]['primitives']:
            P = acc(p['attributes']['POSITION']); Nn = acc(p['attributes']['NORMAL']); I = acc(p['indices'])[:, 0]
            assert I.max() < len(P) and len(I) % 3 == 0 and np.isfinite(P).all() and np.isfinite(Nn).all()
            assert abs(np.linalg.norm(Nn, axis=1) - 1).max() < 1e-2, 'normals not unit ' + name
            used.add(MATS[p['material']]); tris += len(I) // 3
            W = P @ M2[:3, :3].T + M2[:3, 3]
            mn, mx = W.min(0), W.max(0); bb = (mn, mx) if bb is None else (np.minimum(bb[0], mn), np.maximum(bb[1], mx))
    out.append(dict(name=name, tris=tris, pos=M2[:3, 3].copy(), bb=bb, mats=used, depth=depth, mesh='mesh' in n, scale=n.get('scale')))
    for c in n.get('children', []): walk(c, M2, out, depth + 1)
for r in J['scenes'][0]['nodes']:
    out = []; walk(r, np.eye(4), out, 0); name = N[r]['name']
    total = sum(o['tris'] for o in out)
    allmn = np.min([o['bb'][0] for o in out if o['bb']], 0); allmx = np.max([o['bb'][1] for o in out if o['bb']], 0)
    print('== %-22s tris %5d %s  bounds x[%.2f,%.2f] y[%.2f,%.2f] z[%.2f,%.2f]' % (name, total, 'OK' if total < 8000 else 'OVER', allmn[0], allmx[0], allmn[1], allmx[1], allmn[2], allmx[2]))
    if total >= 8000: state['bad'] += 1
    if abs(allmn[1]) > 0.02: print('   %s lowest mesh point y=%.3f%s' % ('NOTE' if name == 'emp_mortar' else 'WARN', allmn[1], ' (rest pose, rotation 0 = horizontal tube: bipod feet are underground until elevated; at 65 degrees they sit on y=0)' if name == 'emp_mortar' else ''))
    if abs(allmn[1]) > 0.02 and name != 'emp_mortar': state['bad'] += 1
    if name.startswith('emp_') and not any('emp_paint' in o['mats'] for o in out): print('   MISSING emp_paint'); state['bad'] += 1
    for o in out[1:]:
        sc = ' scale (%.2f,%.2f,%.2f)' % tuple(o['scale']) if o['scale'] else ''
        print('   %s%-34s %5s pivot (%.3f, %.3f, %.3f)%s' % ('  ' * o['depth'], o['name'], o['tris'] if o['mesh'] else 'empty', *o['pos'], sc))
    # per-node bounds of the moving parts (for the notes): shield plates must live under the pitch node
    for o in out[1:]:
        if o['mesh'] and o['name'].endswith(('_pitch', '_barrels', '_barrel')):
            print('      bounds %-26s x[%.2f,%.2f] y[%.2f,%.2f] z[%.2f,%.2f]' % (o['name'], o['bb'][0][0], o['bb'][1][0], o['bb'][0][1], o['bb'][1][1], o['bb'][0][2], o['bb'][1][2]))
print('materials', len(MATS), MATS)
assert 'emp_paint' in MATS and 'emp_glass' in MATS and all(m.startswith('emp_') for m in MATS), 'material names'
print('alpha materials', [(m['name'], m.get('alphaMode')) for m in J['materials'] if m.get('alphaMode') == 'BLEND'])
print('accessors', len(A), 'bytes', len(b), 'no textures:', 'images' not in J, 'problems:', state['bad'])
for r in J['scenes'][0]['nodes']:
    n = N[r]; assert not n.get('translation') or all(abs(x) < 1e-6 for x in n['translation']), n['name']
print('all roots at origin')
sys.exit(1 if state['bad'] else 0)
