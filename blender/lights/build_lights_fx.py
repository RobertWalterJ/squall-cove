"""Builds the light-FX assets: assets/lights_fx_cone.png + lights_fx_cone.glb, lights_fx_beam_glow.png, lights_fx_flare.png,
lights_fx_pool.png, lights_fx_wet.png. numpy + PIL only.  usage: python blender/lights/build_lights_fx.py [game dir]"""
import sys, os, math, json, struct
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
GAME = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(HERE, '..', '..')); A = os.path.join(GAME, 'assets')
rng = np.random.default_rng(7)
def sm(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def save(name, rgb, a):
    img = np.zeros(a.shape + (4,), np.uint8); img[..., :3] = np.clip(np.asarray(rgb) * 255, 0, 255).astype(np.uint8); img[..., 3] = np.clip(a * 255, 0, 255).astype(np.uint8)
    Image.fromarray(img, 'RGBA').save(os.path.join(A, name), optimize=True); print(name, os.path.getsize(os.path.join(A, name)), 'bytes')

# 1. cone texture: x = along the beam (0 at the lens, 1 at the far end), y = around the cone (wraps). White, alpha only (tint in game).
W, H = 256, 128; u = np.linspace(0, 1, W)[None, :]; v = np.linspace(0, 1, H, endpoint=False)[:, None]
along = (1 - u) ** 1.6 * sm(0, .03, u) * sm(1.0, .85, u)           # bright at the lens, fades to nothing at the far end
hot = np.exp(-u * 9) * .55                                          # extra hotspot near the lens
streak = np.zeros((H, 1))
for k, amp in ((3, .5), (7, .3), (13, .2)): streak += amp * np.cos(2 * math.pi * (k * v + rng.random()))
streak = .78 + .22 * (streak / np.abs(streak).max())                 # faint dust streaks around the circumference, seamless in v
sw = 1 + .15 * np.cos(2 * math.pi * (u * 5 + v * 3))                 # slow drift along the beam
a = np.clip((along + hot * along) * streak * sw * .75, 0, 1)
save('lights_fx_cone.png', np.ones(a.shape + (3,)), a)
# cone mesh: apex at the lens (origin), opens along +Z, length 1, far radius 0.5 (scale x,y by 2*tan(half angle) * length in game), 24 sides, UV as above
N = 24; Vs = []; UV = []; F = []
for i in range(2):
    for k in range(N + 1):
        ang = 2 * math.pi * k / N; r = 0 if i == 0 else .5
        Vs.append((r * math.cos(ang), r * math.sin(ang), float(i))); UV.append((float(i), k / N))
for k in range(N): F += [(k, N + 1 + k, N + 2 + k)]            # apex ring is degenerate, one tri per side
for k in range(N): pass
Vs = np.array(Vs, '<f4'); UV = np.array(UV, '<f4'); Fi = np.array(F, '<u2').reshape(-1)
bin_ = Vs.tobytes() + UV.tobytes() + Fi.tobytes()
while len(bin_) % 4: bin_ += b'\0'
js = {'asset': {'version': '2.0', 'generator': 'build_lights_fx.py'}, 'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'name': 'lights_fx_cone', 'mesh': 0}],
      'meshes': [{'name': 'lights_fx_cone_mesh', 'primitives': [{'attributes': {'POSITION': 0, 'TEXCOORD_0': 1}, 'indices': 2, 'material': 0}]}],
      'materials': [{'name': 'lights_fx_cone_mat', 'pbrMetallicRoughness': {'baseColorFactor': [1, .93, .78, 1], 'metallicFactor': 0, 'roughnessFactor': 1}, 'alphaMode': 'BLEND', 'doubleSided': True,
                     'extensions': {'KHR_materials_unlit': {}}}],
      'extensionsUsed': ['KHR_materials_unlit'],
      'accessors': [{'bufferView': 0, 'componentType': 5126, 'count': len(Vs), 'type': 'VEC3', 'min': Vs.min(0).tolist(), 'max': Vs.max(0).tolist()},
                    {'bufferView': 1, 'componentType': 5126, 'count': len(UV), 'type': 'VEC2'}, {'bufferView': 2, 'componentType': 5123, 'count': len(Fi), 'type': 'SCALAR'}],
      'bufferViews': [{'buffer': 0, 'byteOffset': 0, 'byteLength': Vs.nbytes, 'target': 34962}, {'buffer': 0, 'byteOffset': Vs.nbytes, 'byteLength': UV.nbytes, 'target': 34962},
                      {'buffer': 0, 'byteOffset': Vs.nbytes + UV.nbytes, 'byteLength': Fi.nbytes, 'target': 34963}], 'buffers': [{'byteLength': len(bin_)}]}
j = json.dumps(js, separators=(',', ':')).encode()
while len(j) % 4: j += b' '
open(os.path.join(A, 'lights_fx_cone.glb'), 'wb').write(b'glTF' + struct.pack('<II', 2, 28 + len(j) + len(bin_)) + struct.pack('<I', len(j)) + b'JSON' + j + struct.pack('<I', len(bin_)) + b'BIN\0' + bin_)
# 2. beam glow: long soft streak (x along the beam, y across). Billboard stretched from the lens along the beam, additive, visible from far away.
W, H = 512, 64; x = np.linspace(0, 1, W)[None, :]; y = np.linspace(-1, 1, H)[:, None]
width = .12 + .88 * x                                                  # widens with distance like the beam
a = np.exp(-(y / width) ** 2 * 3.5) * sm(0, .02, x) * (1 - sm(.35, 1, x)) ** 1.2 * (.35 + .65 * np.exp(-x * 4))
save('lights_fx_beam_glow.png', np.stack([np.ones_like(a), .94 * np.ones_like(a), .8 * np.ones_like(a)], -1), np.clip(a, 0, 1))
# 3. flare / bloom sprite: soft core + halo + 4-point star + faint ring
S = 256; yy, xx = np.mgrid[-1:1:S * 1j, -1:1:S * 1j]; r = np.hypot(xx, yy); th = np.arctan2(yy, xx)
core = np.exp(-(r / .07) ** 2); halo = np.exp(-r * 5) * .55; star = (np.exp(-np.abs(xx) * 55) * np.exp(-np.abs(yy) * 3.2) + np.exp(-np.abs(yy) * 55) * np.exp(-np.abs(xx) * 3.2)) * .7
ring = np.exp(-((r - .62) / .025) ** 2) * .18
a = np.clip((core + halo + star + ring) * sm(1, .85, r), 0, 1)
save('lights_fx_flare.png', np.stack([np.ones_like(a), .96 * np.ones_like(a), .88 * np.ones_like(a)], -1), a)
# 4. ground light pool decal: soft elliptical edge, brighter centre, long axis along +Z (y of the image = Z); scale in game to the pool size
a = np.clip(1 - np.hypot(xx / .98, yy / .98), 0, 1); a = sm(0, .55, a) ** 1.3 * (.55 + .45 * np.exp(-(r / .45) ** 2))
save('lights_fx_pool.png', np.ones(a.shape + (3,)), a * .9)
# 5. wet-ground reflection hint: a vertical smear (x across, y = distance from the lamp foot), broken by ripples; stretch toward the camera
W, H = 64, 256; x = np.linspace(-1, 1, W)[None, :]; y = np.linspace(0, 1, H)[:, None]
rip = .72 + .28 * np.cos(2 * math.pi * (y * 14 + .6 * np.sin(y * 9))) * np.exp(-y * 1.5)
a = np.exp(-(x / (.16 + .35 * y)) ** 2 * 2.6) * (1 - y) ** 1.1 * sm(0, .02, y) * rip
save('lights_fx_wet.png', np.stack([np.ones_like(a), .95 * np.ones_like(a), .85 * np.ones_like(a)], -1), np.clip(a * .85, 0, 1))
