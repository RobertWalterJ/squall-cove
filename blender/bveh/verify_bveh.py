"""Parses assets/bveh.glb: node tree, triangles per model, accessor validity, unit normals, materials, pivots, footprints, wheel ground contact.
usage (from the game dir): python blender/bveh/verify_bveh.py"""
import json, struct, base64
import numpy as np
b = open('assets/bveh.glb', 'rb').read()
assert b[:4] == b'glTF' and struct.unpack('<I', b[8:12])[0] == len(b)
assert base64.b64decode(open('assets/bveh.glb.b64.txt').read()) == b, 'b64 does not match glb'
assert '\n' not in open('assets/bveh.glb.b64.txt').read(), 'b64 not one line'
jl = struct.unpack('<I', b[12:16])[0]; J = json.loads(b[20:20 + jl]); BIN = b[20 + jl + 8:]
N = J['nodes']; A = J['accessors']; BV = J['bufferViews']
CT = {5126: ('<f4', 4), 5125: ('<u4', 4), 5123: ('<u2', 2), 5121: ('<u1', 1)}; NC = {'SCALAR': 1, 'VEC3': 3, 'VEC2': 2, 'VEC4': 4}
MATS = [m['name'] for m in J['materials']]
def acc(i):
    a = A[i]; bv = BV[a['bufferView']]; dt, sz = CT[a['componentType']]; n = NC[a['type']]
    assert a['count'] * n * sz <= bv['byteLength']
    return np.frombuffer(BIN, dt, a['count'] * n, bv.get('byteOffset', 0) + a.get('byteOffset', 0)).reshape(a['count'], n)
def mat4(n):
    t = np.eye(4); t[:3, 3] = n.get('translation', [0, 0, 0]); return t
EXPECT = {
    'jeep': ['jeep_wheel_FL', 'jeep_wheel_FR', 'jeep_wheel_RL', 'jeep_wheel_RR', 'jeep_steer_FL', 'jeep_steer_FR', 'jeep_gun', 'jeep_muzzle', 'jeep_seat_driver', 'jeep_seat_gunner', 'jeep_seat_p0', 'jeep_exit_L', 'jeep_exit_R'],
    'technical': ['technical_wheel_FL', 'technical_steer_FR', 'technical_gun', 'technical_muzzle', 'technical_seat_driver', 'technical_seat_gunner', 'technical_exit_L', 'technical_exit_R'],
    'apc': ['apc_turret', 'apc_gun', 'apc_muzzle', 'apc_ramp', 'apc_wheel_F1L', 'apc_wheel_R2R', 'apc_steer_F2L', 'apc_seat_driver', 'apc_seat_gunner', 'apc_seat_p7', 'apc_exit_L', 'apc_exit_R'],
    'light_tank': ['light_tank_turret', 'light_tank_barrel', 'light_tank_muzzle', 'light_tank_track_L', 'light_tank_track_R', 'light_tank_wheel_L1', 'light_tank_wheel_R5', 'light_tank_seat_driver', 'light_tank_seat_gunner', 'light_tank_exit_L', 'light_tank_exit_R'],
    'supply_truck': ['supply_truck_wheel_R2R', 'supply_truck_steer_F1L', 'supply_truck_wheel_F1L', 'supply_truck_seat_driver', 'supply_truck_seat_p8', 'supply_truck_exit_L', 'supply_truck_exit_R'],
    'ambulance': ['ambulance_wheel_FL', 'ambulance_steer_FR', 'ambulance_wheel_RR', 'ambulance_seat_driver', 'ambulance_seat_p3', 'ambulance_exit_L', 'ambulance_exit_R'],
    'fuel_truck': ['fuel_truck_wheel_R2L', 'fuel_truck_steer_F1R', 'fuel_truck_seat_driver', 'fuel_truck_exit_L', 'fuel_truck_exit_R'],
    'quad_atv': ['quad_atv_wheel_FL', 'quad_atv_steer_FR', 'quad_atv_wheel_RR', 'quad_atv_seat_driver', 'quad_atv_seat_p0', 'quad_atv_exit_L', 'quad_atv_exit_R'],
}
def walk(i, M, out, depth):
    n = N[i]; M2 = M @ mat4(n); name = n['name']
    if n.get('rotation') and any(abs(x) > 1e-6 for x in n['rotation'][:3]): print('WARN rotation on', name)
    if n.get('scale') and any(abs(x - 1) > 1e-6 for x in n['scale']): print('WARN scale on', name)
    tris = 0; bb = None; used = set()
    if 'mesh' in n:
        for p in J['meshes'][n['mesh']]['primitives']:
            P = acc(p['attributes']['POSITION']); Nn = acc(p['attributes']['NORMAL']); I = acc(p['indices'])[:, 0]
            assert I.max() < len(P) and len(I) % 3 == 0 and np.isfinite(P).all() and np.isfinite(Nn).all()
            assert abs(np.linalg.norm(Nn, axis=1) - 1).max() < 1e-2, 'normals not unit ' + name
            used.add(MATS[p['material']]); tris += len(I) // 3
            W = P @ M2[:3, :3].T + M2[:3, 3]
            mn, mx = W.min(0), W.max(0); bb = (mn, mx) if bb is None else (np.minimum(bb[0], mn), np.maximum(bb[1], mx))
    out.append(dict(name=name, tris=tris, pos=M2[:3, 3].copy(), bb=bb, mats=used, local=n.get('translation', [0, 0, 0]), depth=depth, mesh='mesh' in n))
    for c in n.get('children', []): walk(c, M2, out, depth + 1)
roots = [N[r]['name'] for r in J['scenes'][0]['nodes']]
print('top-level:', roots)
assert sorted(roots) == sorted(EXPECT), 'root names'
bad = 0
for r in J['scenes'][0]['nodes']:
    out = []; walk(r, np.eye(4), out, 0); name = N[r]['name']
    total = sum(o['tris'] for o in out); names = {o['name'] for o in out}
    allmn = np.min([o['bb'][0] for o in out if o['bb']], 0); allmx = np.max([o['bb'][1] for o in out if o['bb']], 0)
    print('== %-13s tris %5d %s  bounds x[%.2f,%.2f] y[%.2f,%.2f] z[%.2f,%.2f]' % (name, total, 'OK' if total < 9000 else 'OVER', allmn[0], allmx[0], allmn[1], allmx[1], allmn[2], allmx[2]))
    miss = [e for e in EXPECT[name] if e not in names]
    if miss: print('   MISSING', miss); bad += 1
    if abs(allmn[1]) > 0.02: print('   WARN lowest point y=%.3f (not on the ground)' % allmn[1])
    for o in out[1:]:
        extra = ''
        if o['mesh'] and '_wheel_' in o['name'] or (o['mesh'] and ('_idler_' in o['name'] or '_sprocket_' in o['name'])):
            mn, mx = o['bb']; c = (mn + mx) / 2 - o['pos']; rr = (mx[1] - mn[1]) / 2
            extra = ' r=%.3f bottom y=%.3f centre-offset (%.3f,%.3f,%.3f)' % (rr, mn[1], c[0], c[1], c[2])
            if abs(c[1]) > 0.03 or abs(c[2]) > 0.03: print('   WARN wheel not centred on its pivot', o['name'])
            if o['name'].startswith(name + '_wheel_') and abs(mn[1]) > 0.02: print('   WARN wheel not touching ground', o['name'])
        print('   %s%-30s %5s pivot (%.2f, %.2f, %.2f)%s' % ('  ' * o['depth'], o['name'], o['tris'] if o['mesh'] else 'empty', *o['pos'], extra))
    for o in out:
        if o['mesh']:
            m = o['mats']
            if 'veh_paint' in m and any(x.startswith('veh_paint') and x != 'veh_paint' for x in m): print('   WARN second paint material in', o['name'])
print('materials', len(MATS), MATS)
assert 'veh_paint' in MATS and 'veh_glass' in MATS
print('alpha materials', [(m['name'], m.get('alphaMode')) for m in J['materials'] if m.get('alphaMode') == 'BLEND'])
print('paint materials:', [m for m in MATS if 'paint' in m])
print('accessors', len(A), 'bytes', len(b), 'no textures:', 'images' not in J, 'problems:', bad)
for r in J['scenes'][0]['nodes']:
    n = N[r]; assert not n.get('translation') or all(abs(x) < 1e-6 for x in n['translation']), n['name']
print('all roots at origin')
