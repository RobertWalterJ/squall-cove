"""Re-reads assets/fire.glb and checks names, bounds, triangle counts, animation loops, size.
usage: python verify_fire.py [game dir] [--render]   (--render runs ONE background Blender, polls a log, writes blender/review/fire/)"""
import sys, os, json, struct, subprocess, time
import numpy as np

args = [a for a in sys.argv[1:] if not a.startswith('--')]
GAME = args[0] if args else os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BLENDER = r'C:\Users\Robert Walter-Joseph\Code Projects\squall-cove\_tools\blender-4.2.9-windows-x64\blender.exe'
glb = open(os.path.join(GAME, 'assets', 'fire.glb'), 'rb').read()
jl = struct.unpack('<I', glb[12:16])[0]; js = json.loads(glb[20:20 + jl]); bin_ = glb[20 + jl + 8:]
bad = []
def chk(c, m):
    if not c: bad.append(m)

def acc(i):
    a = js['accessors'][i]; bv = js['bufferViews'][a['bufferView']]
    dt = {5126: '<f4', 5125: '<u4', 5123: '<u2'}[a['componentType']]; nc = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}[a['type']]
    return np.frombuffer(bin_, dt, a['count'] * nc, bv['byteOffset'] + a.get('byteOffset', 0)).reshape(a['count'], nc)

nodes = js['nodes']; byname = {n['name']: i for i, n in enumerate(nodes)}
need = ['flame_%s_%02d' % (k, i) for k in 'sml' for i in (1, 2, 3)] + ['fire_camp', 'fire_building', 'fire_vehicle', 'fire_tree', 'fire_ground'] + \
       ['ember_%02d' % i for i in (1, 2, 3)] + ['ash_flake_%02d' % i for i in (1, 2)] + ['smoke_puff_%02d' % i for i in (1, 2, 3)] + ['smoke_column']
for n in need: chk(n in byname, 'missing node ' + n)
mats = {m['name'] for m in js['materials']}; chk('fire_vc' in mats, 'no fire_vc material')

def mesh_tris(mi):
    return sum(len(acc(p['indices'])) // 3 for p in js['meshes'][mi]['primitives'])
def qm(q):
    x, y, z, w = q; return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
def local(n):
    M = np.eye(4); M[:3, :3] = qm(n.get('rotation', [0, 0, 0, 1])) @ np.diag(n.get('scale', [1, 1, 1])); M[:3, 3] = n.get('translation', [0, 0, 0]); return M
def walk(i, P, acc_):   # returns tris, min, max
    n = nodes[i]; M = P @ local(n); t = 0; lo = np.full(3, 1e9); hi = np.full(3, -1e9)
    if 'mesh' in n:
        t += mesh_tris(n['mesh'])
        for p in js['meshes'][n['mesh']]['primitives']:
            V = acc(p['attributes']['POSITION']); W = (M[:3, :3] @ V.T).T + M[:3, 3]; lo = np.minimum(lo, W.min(0)); hi = np.maximum(hi, W.max(0))
            chk(len(acc(p['attributes']['COLOR_0'])) == len(V), 'colour count ' + n['name'])
    for c in n.get('children', []):
        a, b, c3 = walk(c, M, acc_); t += a; lo = np.minimum(lo, b); hi = np.maximum(hi, c3)
    acc_[n['name']] = (t, lo, hi); return t, lo, hi
res = {}
for r in js['scenes'][0]['nodes']: walk(r, np.eye(4), res)
print('%-18s %5s  %-22s %-22s' % ('node', 'tris', 'min xyz', 'max xyz'))
for n in need:
    t, lo, hi = res[n]; print('%-18s %5d  %-22s %-22s h=%.2f w=%.2f' % (n, t, np.round(lo, 2), np.round(hi, 2), hi[1] - lo[1], max(hi[0] - lo[0], hi[2] - lo[2])))
    if n.startswith('flame_l'): chk(t < 150, n + ' tris >= 150')
    if n.startswith('fire_'): chk(t < 700, n + ' tris >= 700')
    if n.startswith('flame_'): chk(abs(lo[1]) < 1e-3, n + ' base not at y=0')
H = {'s': .4, 'm': 1.0, 'l': 2.5}
for k in 'sml':
    for i in (1, 2, 3):
        h = res['flame_%s_%02d' % (k, i)][2][1]; chk(abs(h - H[k]) < 0.1 * H[k] + 0.03, 'height %s %d = %.2f' % (k, i, h))
for nm, tgt in (('fire_building', 5), ('fire_vehicle', 3), ('fire_tree', 6)):
    t, lo, hi = res[nm]; print(nm, 'extent', np.round(hi - lo, 2))
# animations
names = {a['name'] for a in js['animations']}
for a in ('flicker_s', 'flicker_m', 'flicker_l', 'flicker_cluster'): chk(a in names, 'missing animation ' + a)
for a in js['animations']:
    for ch in a['channels']:
        s = a['samplers'][ch['sampler']]; T = acc(s['input'])[:, 0]; O = acc(s['output'])
        chk(np.allclose(O[0], O[-1], atol=1e-7), 'not looped %s %s' % (a['name'], nodes[ch['target']['node']]['name']))
        chk(abs(T[-1] - 1.2) < 1e-5 and T[0] == 0, 'bad duration ' + a['name'])
        chk(ch['target']['path'] in ('scale', 'rotation'), 'path')
        if ch['target']['path'] == 'rotation': chk(np.allclose(np.linalg.norm(O, axis=1), 1, atol=1e-3), 'unnormalised quats')
    print('animation %-16s channels=%d' % (a['name'], len(a['channels'])))
size = len(glb); print('size %d bytes (%.0f KB)' % (size, size / 1024)); chk(size < 250 * 1024, 'glb over 250 KB')
b64 = os.path.join(GAME, 'assets', 'fire.glb.b64.txt')
if os.path.exists(b64): print('b64 %d bytes' % os.path.getsize(b64))
print('FAIL: ' + '; '.join(bad) if bad else 'ALL CHECKS PASSED')

if '--render' in sys.argv:
    out = os.path.join(GAME, 'blender', 'review', 'fire'); os.makedirs(out, exist_ok=True)
    log = os.path.join(out, 'render.log')
    scr = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'render_fire_blender.py')
    with open(log, 'w') as lf:
        p = subprocess.Popen([BLENDER, '-b', '--factory-startup', '-P', scr, '--', os.path.join(GAME, 'assets', 'fire.glb'), out], stdout=lf, stderr=subprocess.STDOUT)
    print('blender pid', p.pid)
    t0 = time.time()
    while p.poll() is None and time.time() - t0 < 200: time.sleep(2)
    if p.poll() is None: p.kill(); print('blender killed (timeout)')
    print(open(log, errors='replace').read()[-600:])
    from PIL import Image, ImageDraw
    groups = ['small', 'medium', 'large', 'camp', 'vehicle', 'ground', 'building', 'tree', 'bits', 'smoke']
    W = 260
    sheet = Image.new('RGB', (W * 5, (W + 18) * 4), (18, 20, 26)); d = ImageDraw.Draw(sheet)
    for gi, g in enumerate(groups):
        for vi, v in enumerate(('front', '3q')):
            f = os.path.join(out, 'g_%s_%s.png' % (g, v))
            if not os.path.exists(f): continue
            im = Image.open(f).convert('RGB').resize((W, W), Image.LANCZOS)
            x = (gi % 5) * W; y = ((gi // 5) * 2 + vi) * (W + 18) + 18
            sheet.paste(im, (x, y)); d.text((x + 4, y - 15), '%s %s' % (g, v), fill=(220, 220, 220))
    sheet.save(os.path.join(out, 'fire_preview_sheet.png')); print('sheet written')
