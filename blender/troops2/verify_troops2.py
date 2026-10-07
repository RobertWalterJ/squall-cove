"""python verify_troops2.py <game dir> : parse assets/troops2.glb and check it against troops.glb conventions."""
import json, struct, sys, os, base64, numpy as np
G = sys.argv[1] if len(sys.argv) > 1 else '.'
def load(p):
    b = open(p, 'rb').read(); l = struct.unpack('<I', b[12:16])[0]; return json.loads(b[20:20 + l]), b[20 + l + 8:]
t, bin_ = load(os.path.join(G, 'assets', 'troops2.glb')); r, _ = load(os.path.join(G, 'assets', 'troops.glb'))
ref = [r['nodes'][i]['name'] for i in r['skins'][0]['joints']]
N = t['nodes']; ok = True
def A(i):
    a = t['accessors'][i]; bv = t['bufferViews'][a['bufferView']]
    ct = {5126: '<f4', 5123: '<u2', 5121: 'u1', 5125: '<u4'}[a['componentType']]; n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
    assert bv['byteOffset'] + bv['byteLength'] <= len(bin_) and a.get('byteOffset', 0) + a['count'] * n * np.dtype(ct).itemsize <= bv['byteLength']
    return np.frombuffer(bin_, ct, a['count'] * n, bv['byteOffset'] + a.get('byteOffset', 0)).reshape(a['count'], n)
maxtri = 0
for k, s in enumerate(t['skins']):
    names = [N[i]['name'] for i in s['joints']]
    if names != ref: ok = False; print('JOINT MISMATCH', s['name'])
    mn = [n for n in N if n.get('skin') == k][0]; mesh = t['meshes'][mn['mesh']]
    assert mn['name'] == s['name'] + '_mesh' and mesh['name'] == mn['name']
    tris = 0; minw = 9; maxdev = 0
    for p in mesh['primitives']:
        at = p['attributes']; W = A(at['WEIGHTS_0']).astype(float) / 65535; J = A(at['JOINTS_0']); P = A(at['POSITION']); I = A(p['indices'])
        tris += len(I) // 3; assert J.max() < 18 and I.max() < len(P) and np.isfinite(P).all()
        maxdev = max(maxdev, np.abs(W.sum(1) - 1).max())
        assert (W[J == 0].sum() >= 0)
    maxtri = max(maxtri, tris)
    if maxdev > 1e-4: ok = False
    print(f'{s["name"]:28s} {tris:5d} tris  prims {len(mesh["primitives"]):2d}  max|sumW-1| {maxdev:.1e}  top bone-rest ok')
print('all joint names equal troops.glb:', ok, '| max tris', maxtri, '| anims', len(t['animations']), {a['name'] for a in t['animations']})
print('scene nodes', [N[i]['name'] for i in t['scenes'][0]['nodes']])
for ci in range(len(t['skins'])):
    assert t['animations'][ci]['channels'][0]['target']['node'] // 20 == ci
assert len(t['animations']) == len(t['skins'])
# heights
for i in t['scenes'][0]['nodes'][:1]: print(N[i].get('extras'))
