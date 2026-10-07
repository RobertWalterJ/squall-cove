"""Parses assets/air.glb.b64.txt: node names, triangle counts, accessor validity; optional previews -> blender/review/air/ (numpy painter's renderer + PIL).
usage (from game dir): python blender/air/verify_air.py [--render]"""
import json, struct, base64, sys, os, math
import numpy as np
b = base64.b64decode(open('assets/air.glb.b64.txt').read())
assert b[:4] == b'glTF' and struct.unpack('<I', b[8:12])[0] == len(b)
jl = struct.unpack('<I', b[12:16])[0]; J = json.loads(b[20:20 + jl]); BIN = b[20 + jl + 8:]
N = J['nodes']; A = J['accessors']; BV = J['bufferViews']
assert J['buffers'][0]['byteLength'] == len(BIN)
CT = {5126: ('<f4', 4), 5125: ('<u4', 4), 5123: ('<u2', 2)}; NC = {'SCALAR': 1, 'VEC3': 3}
def acc(i):
    a = A[i]; bv = BV[a['bufferView']]; dt, sz = CT[a['componentType']]; n = NC[a['type']]
    assert bv['byteOffset'] + bv['byteLength'] <= len(BIN) and bv['byteOffset'] % 4 == 0
    assert a['count'] * n * sz <= bv['byteLength']
    return np.frombuffer(BIN, dt, a['count'] * n, bv['byteOffset']).reshape(a['count'], n)
def mesh_tris(m):
    out = []
    for p in J['meshes'][m]['primitives']:
        P = acc(p['attributes']['POSITION']); Nn = acc(p['attributes']['NORMAL']); I = acc(p['indices'])[:, 0]
        assert len(P) == len(Nn) and I.max() < len(P) and len(I) % 3 == 0 and np.isfinite(P).all()
        mm = J['materials'][p['material']]
        out.append((P[I.reshape(-1, 3)], Nn[I.reshape(-1, 3)[:, 0]], mm['pbrMetallicRoughness']['baseColorFactor'][:3]))
    return out
def T(n):
    t = np.eye(4); t[:3, 3] = n.get('translation', [0, 0, 0]); return t
tot = {}
def walk(i, M, acc_out, depth=0, root=None):
    n = N[i]; M2 = M @ T(n)
    if 'mesh' in n:
        for P, Nn, col in mesh_tris(n['mesh']): acc_out.append((P @ M2[:3, :3].T + M2[:3, 3], col)); tot[n['name']] = tot.get(n['name'], 0) + len(P)
    for c in n.get('children', []): walk(c, M2, acc_out, depth + 1)
roots = J['scenes'][0]['nodes']
def subtree_tris(i): return sum(tot.get(N[i]['name'], 0) for i in [i]) + sum(subtree_tris(c) for c in N[i].get('children', []))
geo = {}
for r in roots:
    lst = []; walk(r, np.eye(4), lst); geo[N[r]['name']] = lst
def pr(i, d=0):
    print('  ' * d + N[i]['name'], N[i].get('translation', ''), ('%d tris' % tot[N[i]['name']]) if N[i]['name'] in tot else '')
    for c in N[i].get('children', []): pr(c, d + 1)
for r in roots:
    pr(r); print('   TOTAL', subtree_tris(r), 'tris', 'OK' if subtree_tris(r) < 4000 else 'OVER 4000')
print('materials', len(J['materials']), 'accessors', len(A), 'bytes', len(b))
if '--render' in sys.argv:
    from PIL import Image, ImageDraw
    os.makedirs('blender/review/air', exist_ok=True)
    L = norm = lambda v: v / (np.linalg.norm(v) + 1e-12)
    light = norm(np.array([-.4, .8, .5]))
    def render(lst, eye_dir, up, size=900):
        Z = norm(np.array(eye_dir, float)); X = norm(np.cross(up, Z)); Y = np.cross(Z, X)
        allp = np.vstack([p.reshape(-1, 3) for p, _ in lst]); ctr = (allp.max(0) + allp.min(0)) / 2
        R = np.stack([X, Y, Z]); q = (allp - ctr) @ R.T; ext = max(np.ptp(q[:, 0]), np.ptp(q[:, 1])) * 1.1
        img = Image.new('RGB', (size, size), (205, 215, 225)); d = ImageDraw.Draw(img); polys = []
        for P, col in lst:
            Q = (P - ctr) @ R.T; nrm = np.cross(Q[:, 1] - Q[:, 0], Q[:, 2] - Q[:, 0]); nl = nrm / (np.linalg.norm(nrm, axis=1)[:, None] + 1e-12)
            lw = nl @ (R @ light); sh = .35 + .65 * np.clip(lw, 0, 1)
            for k in range(len(Q)):
                z = Q[k][:, 2].mean(); polys.append((z, Q[k], sh[k], col))
        polys.sort(key=lambda t: t[0])
        for z, Qk, s, col in polys:
            c = tuple(int(min(255, (x ** (1 / 2.2)) * 255 * s * 1.15)) for x in col)
            pts = [(size / 2 + v[0] / ext * size, size / 2 - v[1] / ext * size) for v in Qk]; d.polygon(pts, fill=c)
        return img
    views = {'3q': ((-1, .7, 1.2), (0, 1, 0)), 'side': ((1, .0, 0), (0, 1, 0)), 'top': ((0, 1, .001), (0, 0, 1)), 'back': ((.6, .5, -1), (0, 1, 0))}
    for name, lst in geo.items():
        for vn, (e, u) in views.items():
            render(lst, e, np.array(u, float)).save('blender/review/air/%s_%s.png' % (name, vn))
    print('rendered')
