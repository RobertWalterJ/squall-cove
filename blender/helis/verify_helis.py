"""Parses assets/helis.glb: node tree, triangles per node/model, accessor validity, world bounds.  usage (from game dir): python blender/helis/verify_helis.py"""
import json, struct, sys, base64, os
import numpy as np
path = 'assets/helis.glb'
b = open(path, 'rb').read()
assert b[:4] == b'glTF' and struct.unpack('<I', b[8:12])[0] == len(b)
b64 = base64.b64decode(open('assets/helis.glb.b64.txt').read()); assert b64 == b, 'b64 does not match glb'
jl = struct.unpack('<I', b[12:16])[0]; J = json.loads(b[20:20 + jl]); BIN = b[20 + jl + 8:]
N = J['nodes']; A = J['accessors']; BV = J['bufferViews']
CT = {5126: ('<f4', 4), 5125: ('<u4', 4), 5123: ('<u2', 2), 5121: ('<u1', 1)}; NC = {'SCALAR': 1, 'VEC3': 3, 'VEC2': 2, 'VEC4': 4}
def acc(i):
    a = A[i]; bv = BV[a['bufferView']]; dt, sz = CT[a['componentType']]; n = NC[a['type']]
    assert a['count'] * n * sz <= bv['byteLength']
    return np.frombuffer(BIN, dt, a['count'] * n, bv.get('byteOffset', 0) + a.get('byteOffset', 0)).reshape(a['count'], n)
def mat4(n):
    t = np.eye(4); t[:3, 3] = n.get('translation', [0, 0, 0]); return t
res = {}
def walk(i, M, model, out):
    n = N[i]; M2 = M @ mat4(n); name = n['name']
    if n.get('rotation') and any(abs(x) > 1e-6 for x in n['rotation'][:3]): print('WARN rotation on', name)
    tris = 0; bb = None
    if 'mesh' in n:
        for p in J['meshes'][n['mesh']]['primitives']:
            P = acc(p['attributes']['POSITION']); Nn = acc(p['attributes']['NORMAL']); I = acc(p['indices'])[:, 0]
            assert I.max() < len(P) and len(I) % 3 == 0 and np.isfinite(P).all() and np.isfinite(Nn).all()
            assert abs(np.linalg.norm(Nn, axis=1) - 1).max() < 1e-2, 'normals not unit'
            tris += len(I) // 3
            W = P @ M2[:3, :3].T + M2[:3, 3]
            mn, mx = W.min(0), W.max(0); bb = (mn, mx) if bb is None else (np.minimum(bb[0], mn), np.maximum(bb[1], mx))
        out.append((name, tris, M2[:3, 3].round(3).tolist(), bb))
    else:
        out.append((name, 0, M2[:3, 3].round(3).tolist(), None))
    for c in n.get('children', []): walk(c, M2, model, out)
for r in J['scenes'][0]['nodes']:
    out = []; walk(r, np.eye(4), N[r]['name'], out)
    total = sum(o[1] for o in out)
    print('==', N[r]['name'], 'TOTAL tris', total, 'OK' if total < 9000 else 'OVER')
    allmn = np.min([o[3][0] for o in out if o[3]], 0); allmx = np.max([o[3][1] for o in out if o[3]], 0)
    print('   bounds x[%.2f,%.2f] y[%.2f,%.2f] z[%.2f,%.2f]' % (allmn[0], allmx[0], allmn[1], allmx[1], allmn[2], allmx[2]))
    for name, tr, pos, bb in out[1:]:
        print('   %-28s %5s  pivot %s' % (name, tr if tr else 'empty', pos))
print('materials', len(J['materials']), [m['name'] for m in J['materials']])
print('alpha materials', [(m['name'], m.get('alphaMode'), m['pbrMetallicRoughness']['baseColorFactor'][3]) for m in J['materials'] if m.get('alphaMode') == 'BLEND'])
print('accessors', len(A), 'bytes', len(b))
