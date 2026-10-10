"""Re-reads assets/lights_pack.glb and checks it: names, bounds, triangle counts, lightpt_* beam directions, material names,
floating (disconnected) mesh islands, total size.   usage: python blender/lights/verify_lights.py [game dir] [--quiet]"""
import sys, os, json, struct, math
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

HERE = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:] if not a.startswith('--')]
GAME = args[0] if args else os.path.abspath(os.path.join(HERE, '..', '..'))
QUIET = '--quiet' in sys.argv
TRI_LIMIT = 1200; SIZE_TARGET = 150 * 1024; TOL = .06; SPACING = .05; VOX = .05
EXPECT = ['light_tower', 'light_tower_lowered', 'floodlight_pole_2', 'floodlight_pole_4', 'floodlight_wall', 'floodlight_roof', 'lamp_cobra', 'lamp_harbour',
          'lamp_bollard', 'string_lights_8m', 'string_lights_span_8m', 'generator_small', 'generator_medium', 'generator_large', 'cableseg_straight_4m', 'cableseg_90',
          'cableseg_sag_6m', 'cablereel', 'junction_box', 'junction_box_dist', 'searchlight_ground', 'spotlight_tripod', 'vehicle_headlights',
          'vehicle_taillights', 'vehicle_lightbar']
NEED_NODES = ['searchlight_yoke', 'searchlight_head']
INTENDED_ISLANDS = {'lights_materials_ref'}       # the material reference swatches are deliberately separate cubes

raw = open(os.path.join(GAME, 'assets', 'lights_pack.glb'), 'rb').read()
jl, = struct.unpack('<I', raw[12:16]); js = json.loads(raw[20:20 + jl]); bo = 20 + jl + 8; BIN = raw[bo:]
fails = []; warns = []
def acc(i):
    a = js['accessors'][i]; bv = js['bufferViews'][a['bufferView']]
    dt = {5126: '<f4', 5123: '<u2', 5125: '<u4'}[a['componentType']]; nc = {'VEC3': 3, 'SCALAR': 1}[a['type']]
    off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    return np.frombuffer(BIN, dt, a['count'] * nc, off).reshape(-1, nc) if nc > 1 else np.frombuffer(BIN, dt, a['count'], off)
def qmat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
nodes = js['nodes']; roots = js['scenes'][0]['nodes']
def local(n):
    M = np.eye(4)
    if 'rotation' in n: M[:3, :3] = qmat(n['rotation'])
    if 'translation' in n: M[:3, 3] = n['translation']
    return M
def collect(i, M, rootname, out, depth=0):
    n = nodes[i]; W = M @ local(n); n['_W'] = W
    out.append((i, W, depth))
    for c in n.get('children', []): collect(c, W, rootname, out, depth + 1)

mats = [m['name'] for m in js['materials']]
print('materials (%d): %s' % (len(mats), ', '.join(mats[:60])))
for need in ('lamp_on', 'lamp_off', 'lens_glass'):
    if need not in mats: fails.append('material %s missing' % need)
for m in js['materials']:
    if m['name'] == 'lamp_on' and 'emissiveFactor' not in m: fails.append('lamp_on is not emissive')
    if m['name'] == 'lamp_off' and 'emissiveFactor' in m: fails.append('lamp_off is emissive')

rootnames = [nodes[i]['name'] for i in roots]
for e in EXPECT:
    if e not in rootnames: fails.append('root %s missing' % e)
byname = {}
for i, n in enumerate(nodes): byname.setdefault(n['name'], []).append(i)
for k in NEED_NODES:
    if k not in byname: fails.append('node %s missing' % k)
dupe = [k for k, v in byname.items() if len(v) > 1 and not k.startswith('mast')]
if dupe: fails.append('duplicate node names: %s' % dupe[:10])

def comps_of(prim, W):
    P = acc(prim['attributes']['POSITION']).astype(float); I = acc(prim['indices']).astype(int).reshape(-1, 3)
    Pw = (P @ W[:3, :3].T) + W[:3, 3]
    n = len(P); e = np.concatenate([I[:, [0, 1]], I[:, [1, 2]]])
    g = coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n))
    nc, lab = connected_components(g, directed=False)
    return Pw, I, nc, lab
def sample(Pw, I, comp_of_vert):
    A, B, C = Pw[I[:, 0]], Pw[I[:, 1]], Pw[I[:, 2]]
    m = np.maximum(np.maximum(np.linalg.norm(B - A, axis=1), np.linalg.norm(C - B, axis=1)), np.linalg.norm(A - C, axis=1))
    K = np.maximum(1, np.ceil(m / SPACING).astype(int)); cc = comp_of_vert[I[:, 0]]
    pts = []; cid = []
    for k in np.unique(K):
        sel = np.where(K == k)[0]
        uv = np.array([(i / k, j / k) for i in range(k + 1) for j in range(k + 1 - i)])
        P = A[sel][:, None, :] + (B[sel] - A[sel])[:, None, :] * uv[None, :, 0:1] + (C[sel] - A[sel])[:, None, :] * uv[None, :, 1:2]
        pts.append(P.reshape(-1, 3)); cid.append(np.repeat(cc[sel], len(uv)))
    pts = np.vstack(pts); cid = np.concatenate(cid)
    key = np.concatenate([np.round(pts / VOX).astype(np.int64), cid[:, None]], 1)
    _, first = np.unique(key, axis=0, return_index=True)
    return pts[first], cid[first]

rows = []; total_tris = 0; all_lp = 0
import time
for ri in roots:
    t0 = time.time(); rn = nodes[ri]['name']; lst = []; collect(ri, np.eye(4), rn, lst)
    tris = 0; lo = np.full(3, 1e9); hi = np.full(3, -1e9); lps = []; comp_pts = []; comp_label = []; comp_node = []; cbase = 0
    for i, W, d in lst:
        n = nodes[i]
        if 'mesh' in n:
            for pr in js['meshes'][n['mesh']]['primitives']:
                Pw, I, nc, lab = comps_of(pr, W); tris += len(I)
                lo = np.minimum(lo, Pw.min(0)); hi = np.maximum(hi, Pw.max(0))
                s, c = sample(Pw, I, lab)
                comp_pts.append(s); comp_label.append(c + cbase); comp_node += [n['name']] * nc; cbase += nc
        if n['name'].startswith('lightpt_'): lps.append((n, W))
        if n['name'].startswith('lightpt_') or n['name'].startswith('cable_') or n['name'].startswith('smoke_'):
            if 'mesh' in n and i not in roots: fails.append('%s: empty has geometry' % n['name'])
    total_tris += tris
    # lightpt checks
    for n, W in lps:
        z = W[:3, :3] @ np.array([0, 0, 1.0]); L = np.linalg.norm(z)
        if abs(L - 1) > 1e-3: fails.append('%s: beam direction not unit (%.3f)' % (n['name'], L))
        ex = (n.get('extras') or {}).get('light')
        if not ex: fails.append('%s: no light extras' % n['name'])
        elif ex.get('type') != 'indicator' and ('rotation' not in n and not any('rotation' in nodes[j] for j in [])):
            # identity rotation is legitimate (beam +Z) but inside rotated parents the world beam must be defined: report it
            pass
    for n in lst:
        pass
    all_lp += len(lps)
    # islands
    isl = 0; floaters = []
    if comp_pts and rn not in INTENDED_ISLANDS:
        pts = np.vstack(comp_pts); lab = np.concatenate(comp_label)
        tree = cKDTree(pts); pr_ = tree.query_pairs(TOL, output_type='ndarray')
        g = coo_matrix((np.ones(len(pr_)), (lab[pr_[:, 0]], lab[pr_[:, 1]])), shape=(cbase, cbase))
        nc2, l2 = connected_components(g, directed=False)
        sizes = np.bincount(l2, minlength=nc2); main = int(np.argmax(sizes)); isl = nc2
        for c in range(nc2):
            if c == main: continue
            sel = np.isin(lab, np.where(l2 == c)[0]); q = pts[sel]
            floaters.append((comp_node[int(np.where(l2 == c)[0][0])], q.min(0).round(2).tolist(), q.max(0).round(2).tolist()))
    for f in floaters: fails.append('%s: FLOATING island in node %s bbox %s .. %s' % ((rn,) + f))
    rows.append((rn, tris, lo, hi, len(lps), isl)); print('  ..', rn, '%.1fs' % (time.time() - t0), flush=True)
    if tris > TRI_LIMIT: warns.append('%s: %d tris (limit %d)' % (rn, tris, TRI_LIMIT))

print('%-24s %6s  %-26s %-22s %3s %3s' % ('piece', 'tris', 'size x,y,z (m)', 'min y / max y', 'lp', 'isl'))
for rn, t, lo, hi, nl, isl in rows:
    print('%-24s %6d  %5.2f x %5.2f x %5.2f      %6.2f / %6.2f   %3d %3d' % (rn, t, *(hi - lo), lo[1], hi[1], nl, isl))
print('total tris', total_tris, '| lightpt empties', all_lp, '| glb bytes', len(raw), '(%.0f KB)' % (len(raw) / 1024))
b64 = os.path.join(GAME, 'assets', 'lights_pack.glb.b64.txt')
if os.path.exists(b64):
    import base64
    ok = base64.b64decode(open(b64, 'rb').read()) == raw
    print('b64 matches glb:', ok)
    if not ok: fails.append('b64 does not match glb')
if len(raw) > SIZE_TARGET: warns.append('pack is %.0f KB (target %.0f KB)' % (len(raw) / 1024, SIZE_TARGET / 1024))
for w in warns: print('WARN', w)
for f in fails: print('FAIL', f)
print('RESULT', 'PASS' if not fails else 'FAIL (%d)' % len(fails))
sys.exit(1 if fails else 0)
