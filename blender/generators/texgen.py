"""Tileable PBR ground textures from periodic noise.

Every map wraps seamlessly: noise lattices are taken modulo their period and all filters use wrap-around.
Per material: <name>_albedo (sRGB), <name>_normal (OpenGL, +Y up), <name>_orh (R ambient occlusion,
G roughness, B height), <name>_height16 (16-bit), plus a 2x2 tiling check.

Run: python3 texgen.py [size] [names...]
"""
import sys, os, math, json
import numpy as np
from PIL import Image

OUT = '/home/claude/procgen/out/textures'

# ---------------------------------------------------------------- periodic noise
def _grad_table(seed, n=256):
    rng = np.random.default_rng(seed)
    a = rng.random(n) * 2 * np.pi
    return np.cos(a), np.sin(a), rng.permutation(n)

def perlin_p(S, period, seed=0):
    """Periodic gradient noise on an S x S image with `period` lattice cells across (integer => tiles)."""
    gx, gy, perm = _grad_table(seed)
    u = (np.arange(S) + 0.5) / S * period
    X, Y = np.meshgrid(u, u)
    xi, yi = np.floor(X).astype(int), np.floor(Y).astype(int)
    xf, yf = X - xi, Y - yi
    def h(ix, iy):
        return perm[(perm[(ix % period) & 255] + (iy % period)) & 255]
    def dot(ix, iy, dx, dy):
        k = h(ix, iy)
        return gx[k] * dx + gy[k] * dy
    fade = lambda t: t * t * t * (t * (t * 6 - 15) + 10)
    uu, vv = fade(xf), fade(yf)
    n00 = dot(xi, yi, xf, yf); n10 = dot(xi + 1, yi, xf - 1, yf)
    n01 = dot(xi, yi + 1, xf, yf - 1); n11 = dot(xi + 1, yi + 1, xf - 1, yf - 1)
    a = n00 + uu * (n10 - n00); b = n01 + uu * (n11 - n01)
    return (a + vv * (b - a)) * 1.4

def fbm_p(S, period, seed, octaves=6, gain=0.5):
    s = np.zeros((S, S)); a = 1.0; norm = 0
    for o in range(octaves):
        p = period * 2 ** o
        if p > S // 2: break
        s += a * perlin_p(S, p, seed + 31 * o); norm += a; a *= gain
    return s / norm

def worley_p(S, cells, seed, jitter=0.9):
    """Periodic Worley: returns F1, F2 distances (in cell units) and the id of the nearest cell."""
    rng = np.random.default_rng(seed)
    pts = rng.random((cells, cells, 2)) * jitter + (1 - jitter) / 2
    u = (np.arange(S) + 0.5) / S * cells
    X, Y = np.meshgrid(u, u)
    ci, cj = np.floor(X).astype(int), np.floor(Y).astype(int)
    F1 = np.full((S, S), 9.0); F2 = np.full((S, S), 9.0); ID = np.zeros((S, S), int)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            ni, nj = ci + di, cj + dj
            p = pts[nj % cells, ni % cells]
            dx = ni + p[..., 0] - X; dy = nj + p[..., 1] - Y
            d = np.sqrt(dx * dx + dy * dy)
            idx = (nj % cells) * cells + (ni % cells)
            closer = d < F1
            F2 = np.where(closer, F1, np.minimum(F2, d))
            ID = np.where(closer, idx, ID)
            F1 = np.where(closer, d, F1)
    return F1, F2, ID

def warp_sample(img, dx, dy):
    """Wrap-around bilinear resample of img at (x+dx, y+dy) pixels."""
    S = img.shape[0]
    y, x = np.mgrid[0:S, 0:S].astype(float)
    xs, ys = (x + dx) % S, (y + dy) % S
    x0, y0 = np.floor(xs).astype(int), np.floor(ys).astype(int)
    fx, fy = xs - x0, ys - y0
    x1, y1 = (x0 + 1) % S, (y0 + 1) % S
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x1] * fx * (1 - fy) + img[y1, x0] * (1 - fx) * fy + img[y1, x1] * fx * fy)

def blur_w(a, r):
    """Wrap-around box blur, radius r pixels, three passes (≈ Gaussian)."""
    for _ in range(3):
        for ax in (0, 1):
            c = np.cumsum(np.concatenate([a.take(range(-r - 1, 0), axis=ax), a, a.take(range(0, r), axis=ax)], axis=ax), axis=ax)
            n = a.shape[ax]
            a = (c.take(range(2 * r + 1, 2 * r + 1 + n), axis=ax) - c.take(range(0, n), axis=ax)) / (2 * r + 1)
    return a

def norm01(a):
    return (a - a.min()) / (a.max() - a.min() + 1e-9)

def ramp(t, stops):
    """Colour ramp: stops = [(pos, (r,g,b) 0..255), ...] over t in 0..1."""
    t = np.clip(t, 0, 1)
    out = np.zeros(t.shape + (3,))
    pos = [s[0] for s in stops]
    cols = np.array([s[1] for s in stops], float) / 255
    for c in range(3):
        out[..., c] = np.interp(t, pos, cols[:, c])
    return out

def strokes(S, n, length, width, seed, angle_mean=None, angle_spread=math.pi, curl=0.0):
    """Rasterise n short tapered strokes (grass blades, pine needles) with wrap-around; returns height and an id map."""
    rng = np.random.default_rng(seed)
    H = np.zeros((S, S)); ID = np.zeros((S, S))
    L = np.arange(-length // 2, length // 2 + 1)
    for k in range(n):
        x0, y0 = rng.random() * S, rng.random() * S
        a = (angle_mean if angle_mean is not None else 0) + (rng.random() - 0.5) * angle_spread
        ca, sa = math.cos(a), math.sin(a)
        val = 0.5 + 0.5 * rng.random()
        for w in range(-(width // 2), width // 2 + 1):
            t = (L + length / 2) / length
            bend = curl * (t ** 2) * length
            xs = (x0 + L * ca - (w + bend) * sa).astype(int) % S
            ys = (y0 + L * sa + (w + bend) * ca).astype(int) % S
            prof = val * (1 - abs(w) / (width / 2 + 0.5)) * (0.4 + 0.6 * t)
            np.maximum.at(H, (ys, xs), prof)
            ID[ys, xs] = k % 97 / 97
    return H, ID

# ---------------------------------------------------------------- maps out
def normal_from_height(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    n = np.dstack([-dx * strength, dy * strength, np.ones_like(h)])  # OpenGL convention (green = +Y up the image)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n

def cavity_ao(h, r1, r2, k=1.0):
    big = blur_w(h, r2); small = blur_w(h, r1)
    c = np.clip(1 - k * np.maximum(big - small, 0) / (h.std() + 1e-6) * 0.6, 0, 1)
    return c

def save(name, S, alb, h, rough, nstr, ao_k=1.0, ao_r=(2, 12), meta=None):
    os.makedirs(OUT, exist_ok=True)
    h = norm01(h)
    ao = cavity_ao(h, ao_r[0], ao_r[1], ao_k)
    alb = np.clip(alb * (0.55 + 0.45 * ao[..., None]), 0, 1)       # bake a little occlusion into albedo for depth
    n = normal_from_height(h, nstr * S / 1024)
    Image.fromarray((alb * 255).astype(np.uint8)).save(f'{OUT}/{name}_albedo.png')
    Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8)).save(f'{OUT}/{name}_normal.png')
    rough = np.broadcast_to(np.asarray(rough, float), h.shape)
    orh = np.dstack([ao, np.clip(rough, 0, 1), h])
    Image.fromarray((orh * 255).astype(np.uint8)).save(f'{OUT}/{name}_orh.png')
    Image.fromarray((h * 65535).astype(np.uint16)).save(f'{OUT}/{name}_height16.png')
    a8 = (alb * 255).astype(np.uint8)
    Image.fromarray(np.tile(a8, (2, 2, 1))).resize((512, 512), Image.LANCZOS).save(f'{OUT}/{name}_tilecheck.jpg', quality=85)
    return dict(name=name, size=S, mean_albedo=[round(float(x), 3) for x in alb.reshape(-1, 3).mean(0)], roughness=round(float(np.mean(rough)), 2), **(meta or {}))

# ---------------------------------------------------------------- materials
def grass_meadow(S):
    base = fbm_p(S, 4, 1, 5)
    clumps = 1 - worley_p(S, 24, 2)[0]
    bl, bid = strokes(S, int(S * S / 70), max(8, S // 64), 2, 3, angle_mean=-math.pi / 2, angle_spread=1.6, curl=0.08)
    bl = blur_w(bl, 1)
    h = 0.55 * bl + 0.25 * clumps + 0.2 * norm01(base)
    t = norm01(h)
    alb = ramp(t, [(0, (38, 48, 22)), (0.35, (66, 88, 34)), (0.7, (104, 130, 52)), (1, (168, 176, 92))])
    hue = norm01(fbm_p(S, 3, 4, 4))[..., None]
    alb = alb * (1 - 0.25 * hue) + alb[..., [0, 0, 2]] * 0.25 * hue * np.array([1.25, 1.05, 0.8])   # patches drift toward straw
    rough = 0.82 + 0.1 * (1 - t)
    return save('grass_meadow', S, alb, h, rough, 6)

def grass_dry(S):
    base = fbm_p(S, 4, 11, 5)
    bl, _ = strokes(S, int(S * S / 80), max(8, S // 56), 2, 12, angle_mean=-math.pi / 2, angle_spread=2.4, curl=0.15)
    bl = blur_w(bl, 1)
    soil = norm01(fbm_p(S, 16, 13, 4))
    h = 0.6 * bl + 0.15 * soil + 0.25 * norm01(base)
    t = norm01(h)
    alb = ramp(t, [(0, (92, 74, 50)), (0.3, (134, 112, 70)), (0.7, (188, 164, 104)), (1, (222, 204, 150))])
    green = (norm01(fbm_p(S, 5, 14, 4)) > 0.62)[..., None] * 0.35
    alb = alb * (1 - green) + green * alb * np.array([0.8, 1.05, 0.65])
    return save('grass_dry', S, alb, h, 0.88 + 0.05 * (1 - t), 5)

def sand_beach(S):
    grain = np.random.default_rng(21).random((S, S))
    grain = blur_w(grain, 1)
    f = fbm_p(S, 4, 22, 6)
    wx = fbm_p(S, 2, 23, 4) * S * 0.12 + fbm_p(S, 6, 25, 3) * S * 0.02
    y, x = np.mgrid[0:S, 0:S].astype(float)
    rip = np.sin((y + 0.2 * x + wx) / S * 2 * np.pi * 11) * 0.5 + 0.5
    fade = norm01(fbm_p(S, 3, 26, 3))
    rip = rip ** 1.6 * fade                      # ripples come and go instead of striping the whole tile
    h = 0.45 * norm01(f) + 0.2 * rip + 0.35 * grain
    shells = (np.random.default_rng(24).random((S, S)) > 0.9993)
    shells = blur_w(shells.astype(float), 1) > 0.02
    t = norm01(h)
    alb = ramp(t, [(0, (176, 152, 112)), (0.5, (212, 190, 146)), (1, (234, 218, 182))])
    alb = alb * (0.92 + 0.16 * grain[..., None])
    alb[shells] = alb[shells] * 0.4 + 0.6 * np.array([0.95, 0.93, 0.88])
    return save('sand_beach', S, alb, h, 0.9 - 0.05 * t, 3.0, ao_k=0.6)

def sand_wet(S):
    grain = blur_w(np.random.default_rng(31).random((S, S)), 1)
    f = norm01(fbm_p(S, 3, 32, 6))
    puddle = np.clip((f - 0.62) * 6, 0, 1)
    h = 0.6 * f * (1 - puddle * 0.8) + 0.25 * grain
    alb = ramp(norm01(h), [(0, (96, 84, 64)), (1, (138, 122, 92))]) * (0.95 + 0.1 * grain[..., None])
    alb = alb * (1 - 0.35 * puddle[..., None]) + 0.35 * puddle[..., None] * np.array([0.32, 0.34, 0.33])
    rough = 0.45 - 0.35 * puddle + 0.1 * grain
    return save('sand_wet', S, alb, h, rough, 2.0, ao_k=0.5)

def pebbles(S):
    rng = np.random.default_rng(42)
    pal = np.array([[0.56, 0.54, 0.5], [0.42, 0.4, 0.38], [0.66, 0.6, 0.52], [0.34, 0.33, 0.33], [0.72, 0.69, 0.62], [0.5, 0.42, 0.36]])
    h = np.zeros((S, S)); col = np.zeros((S, S, 3)) + np.array([0.42, 0.36, 0.28]); rough = np.full((S, S), 0.92)
    for layer, (cells, seed) in enumerate([(9, 41), (15, 45), (26, 47)]):
        y, x = np.mgrid[0:S, 0:S].astype(float)
        F1, F2, ID = worley_p(S, cells, seed, 0.95)
        n = cells * cells
        r = (0.3 + 0.16 * rng.random(n))[ID]
        dome = np.sqrt(np.clip(1 - (F1 / r) ** 2, 0, 1)) * (1.0 - 0.25 * layer)
        top = dome > h
        h = np.maximum(h, dome)
        c = pal[(rng.random(n) * len(pal)).astype(int)][ID] * (0.85 + 0.3 * rng.random(n)[ID])[..., None]
        col = np.where(top[..., None] & (dome[..., None] > 0.01), c, col)
        rough = np.where(top & (dome > 0.01), 0.5 + 0.25 * rng.random(n)[ID], rough)
    speck = blur_w(np.random.default_rng(44).random((S, S)), 1)
    alb = col * (0.88 + 0.24 * speck[..., None])
    h = h + 0.05 * speck
    return save('pebbles', S, alb, h, rough, 10, ao_k=1.5)

def rock_granite(S):
    f = fbm_p(S, 3, 51, 7, 0.55)
    F1, F2, _ = worley_p(S, 5, 52)
    mask = norm01(fbm_p(S, 3, 55, 3)) > 0.45                         # cracks only run through part of the face
    cracks = 1 - (1 - np.clip((F2 - F1) * 30, 0, 1)) * mask * 0.6
    h = 0.92 * norm01(f) + 0.08 * cracks
    rng = np.random.default_rng(53)
    feld = blur_w((rng.random((S, S)) > 0.985).astype(float), 1) > 0.15
    mica = blur_w((rng.random((S, S)) > 0.99).astype(float), 1) > 0.15
    t = norm01(h)
    alb = ramp(t, [(0, (92, 88, 84)), (0.5, (132, 126, 120)), (1, (172, 166, 158))]) * (0.93 + 0.07 * cracks[..., None])
    alb[feld] = alb[feld] * 0.5 + 0.5 * np.array([0.72, 0.6, 0.55])
    alb[mica] = alb[mica] * 0.35
    lichen = (norm01(fbm_p(S, 6, 54, 4)) > 0.7)[..., None] & (t[..., None] > 0.5)
    alb = np.where(lichen, alb * 0.5 + 0.5 * np.array([0.62, 0.64, 0.48]), alb)
    return save('rock_granite', S, alb, h, 0.7 + 0.15 * (1 - t), 10, ao_k=1.3, ao_r=(2, 20))

def rock_strata(S):
    y, x = np.mgrid[0:S, 0:S].astype(float)
    rng = np.random.default_rng(62)
    warp = fbm_p(S, 2, 61, 4) * S * 0.05 + fbm_p(S, 8, 66, 3) * S * 0.006
    # beds of uneven thickness: a periodic monotone map from height to bed index
    nb = 11
    th = rng.random(nb) + 0.35; edges = np.concatenate([[0], np.cumsum(th) / th.sum()])
    yy = ((y + warp) / S) % 1.0
    layer = np.searchsorted(edges, yy, side='right') - 1
    frac = (yy - edges[layer]) / (edges[layer + 1] - edges[layer])
    ledge = np.clip(frac * 4, 0, 1) * (0.6 + 0.4 * rng.random(nb)[layer])          # each bed overhangs the one below
    f = fbm_p(S, 6, 63, 6)
    xw = (x + fbm_p(S, 4, 64, 3) * S * 0.04) / S * 5
    jl = np.abs((xw % 1.0) - 0.5) * 2
    keep = rng.random(nb * 5)[(layer * 5 + np.floor(xw).astype(int)) % (nb * 5)] > 0.6
    joints = np.where(keep, np.clip((jl - 0.03) * 25, 0, 1), 1.0)
    h = 0.5 * ledge + 0.35 * norm01(f) + 0.15 * joints
    lc = np.array([[150, 118, 86], [178, 146, 104], [128, 100, 76], [196, 170, 130], [110, 90, 72], [164, 136, 100]]) / 255
    col = lc[rng.integers(0, 6, nb)[layer]]
    alb = col * (0.7 + 0.45 * norm01(f)[..., None]) * (0.65 + 0.35 * joints[..., None]) * (0.85 + 0.15 * ledge[..., None])
    return save('rock_strata', S, alb, h, 0.8, 9, ao_k=1.4, ao_r=(2, 16))

def forest_floor(S):
    base = norm01(fbm_p(S, 4, 71, 5))
    needles, _ = strokes(S, int(S * S / 110), max(6, S // 80), 1, 72, angle_spread=2 * math.pi)
    leafs, lid = strokes(S, int(S * S / 500), max(6, S // 60), max(3, S // 170), 73, angle_spread=2 * math.pi, curl=0.1)
    leaf = blur_w(leafs, 1)
    ID = (lid * 1599).astype(int)
    moss = np.clip((norm01(fbm_p(S, 6, 75, 5)) - 0.68) * 4, 0, 1) * 0.7
    h = 0.3 * base + 0.35 * needles + 0.35 * leaf + 0.15 * moss
    soil = ramp(base, [(0, (46, 34, 24)), (1, (84, 64, 44))])
    leafc = ramp(np.random.default_rng(76).random(1600)[ID], [(0, (120, 66, 30)), (0.5, (168, 108, 46)), (1, (110, 92, 50))])
    needc = np.array([0.42, 0.3, 0.18])
    alb = soil
    alb = np.where((leaf > 0.06)[..., None], leafc * (0.7 + 0.3 * leaf[..., None]), alb)
    alb = np.where((needles > 0.3)[..., None], needc * (0.7 + 0.4 * needles[..., None]), alb)
    alb = alb * (1 - moss[..., None] * 0.7) + moss[..., None] * 0.7 * np.array([0.28, 0.38, 0.16])
    return save('forest_floor', S, alb, h, 0.85, 6, ao_k=1.2)

def dirt(S):
    f = norm01(fbm_p(S, 4, 81, 6))
    F1, F2, ID = worley_p(S, 48, 82, 0.95)
    stones = np.clip(1 - F1 / 0.42, 0, 1) ** 0.6 * (np.random.default_rng(83).random(48 * 48)[ID] > 0.88)
    h = 0.7 * f + 0.4 * stones
    alb = ramp(f, [(0, (78, 58, 40)), (0.6, (112, 86, 60)), (1, (140, 112, 80))])
    alb = np.where((stones > 0.05)[..., None], np.array([0.44, 0.39, 0.33]) * (0.8 + 0.3 * stones[..., None]), alb)
    return save('dirt', S, alb, h, 0.9 - 0.2 * stones, 7)

def desert_ripples(S):
    """Wind ripples: asymmetric sawtooth (gentle stoss, steep lee) along a warped axis; for Coilover."""
    y, x = np.mgrid[0:S, 0:S].astype(float)
    warp = fbm_p(S, 2, 91, 4) * S * 0.06 + fbm_p(S, 6, 92, 3) * S * 0.01
    ph = ((y + 0.15 * x + warp) / S * 18) % 1.0
    saw = np.where(ph < 0.78, ph / 0.78, (1 - ph) / 0.22)
    grain = blur_w(np.random.default_rng(93).random((S, S)), 1)
    h = 0.75 * saw + 0.1 * norm01(fbm_p(S, 4, 94, 5)) + 0.15 * grain
    t = norm01(h)
    alb = ramp(t, [(0, (182, 128, 82)), (0.6, (214, 162, 108)), (1, (232, 188, 136))]) * (0.94 + 0.12 * grain[..., None])
    return save('desert_ripples', S, alb, h, 0.93, 4, ao_k=0.8)

def cracked_earth(S):
    """Dry playa: Voronoi plates whose edges curl up, separated by dark cracks; for Coilover."""
    F1, F2, ID = worley_p(S, 9, 101, 0.95)
    edge = F2 - F1
    crack = np.clip(edge * 14, 0, 1)
    curl = np.clip(1 - edge * 3, 0, 1) ** 3 * 0.35
    F1b, F2b, _ = worley_p(S, 27, 102)
    fine = np.clip((F2b - F1b) * 20, 0, 1)
    h = crack * (0.65 + curl) * (0.8 + 0.2 * fine) + 0.1 * norm01(fbm_p(S, 8, 103, 4))
    rng = np.random.default_rng(104)
    plate = (0.9 + 0.2 * rng.random(81))[ID]
    alb = ramp(norm01(fbm_p(S, 3, 105, 4)), [(0, (176, 150, 120)), (1, (210, 186, 154))]) * plate[..., None]
    alb = alb * (0.35 + 0.65 * crack[..., None]) * (0.85 + 0.15 * fine[..., None])
    return save('cracked_earth', S, alb, h, 0.9, 8, ao_k=1.2)

def gravel_track(S):
    """Graded haul-road gravel: packed tan fines with lighter stones, two faint wheel ruts. Brighter than v1, which read as wet tar."""
    F1, F2, ID = worley_p(S, 70, 111, 0.95)
    rng = np.random.default_rng(112)
    dome = np.sqrt(np.clip(1 - (F1 / (0.5 + 0.14 * rng.random(4900)[ID])) ** 2, 0, 1))
    y = np.mgrid[0:S, 0:S][1].astype(float)
    rut = np.exp(-((((y / S * 2) % 1) - 0.3) / 0.07) ** 2) + np.exp(-((((y / S * 2) % 1) - 0.7) / 0.07) ** 2)
    fines = norm01(fbm_p(S, 6, 113, 4))
    h = dome * (1 - 0.3 * rut) + 0.12 * fines
    pal = np.array([[0.78, 0.73, 0.65], [0.66, 0.62, 0.56], [0.80, 0.70, 0.56], [0.58, 0.56, 0.53], [0.72, 0.64, 0.52]])
    col = pal[(rng.random(4900) * 5).astype(int)][ID]
    base = ramp(fines, [(0, (150, 128, 100)), (1, (186, 164, 132))])
    alb = np.where((dome > 0.12)[..., None], col * (0.86 + 0.18 * dome[..., None]), base)
    alb = alb * (1 - 0.10 * rut[..., None])
    return save('gravel_track', S, alb, h, 0.85, 6, ao_k=0.7, ao_r=(2, 8))

def asphalt(S):
    """Worn city asphalt: fine aggregate speckle, tar patches, polished wheel tracks."""
    rng = np.random.default_rng(141)
    speck = blur_w(rng.random((S, S)), 1)
    f = norm01(fbm_p(S, 4, 142, 5))
    F1, F2, ID = worley_p(S, 5, 143)
    patch = (rng.random(25)[ID] > 0.75) * np.clip((F2 - F1) * 10, 0, 1)
    h = 0.5 * speck + 0.3 * f - 0.15 * patch
    alb = ramp(norm01(0.6 * speck + 0.4 * f), [(0, (70, 70, 78)), (1, (118, 116, 122))]) * (1 - 0.18 * patch[..., None])
    return save('asphalt', S, alb, h, 0.85, 3, ao_k=0.5)

def muskeg(S):
    """Shield bog: sphagnum hummocks, rust sedge strokes, dark peat between."""
    F1, F2, ID = worley_p(S, 14, 151, 0.9)
    hum = np.clip(1 - F1 / 0.75, 0, 1) ** 0.7
    sedge, _ = strokes(S, 900, S * 0.03, 1, 152)
    sedge = norm01(sedge)
    f = norm01(fbm_p(S, 5, 153, 5))
    h = 0.6 * hum + 0.2 * f + 0.25 * sedge
    rng = np.random.default_rng(154)
    tint = np.array([[0.48, 0.50, 0.30], [0.56, 0.44, 0.26], [0.44, 0.48, 0.34], [0.60, 0.52, 0.32]])[(rng.random(196) * 4).astype(int)][ID]
    alb = tint * (0.55 + 0.5 * hum[..., None])
    alb = np.where((sedge > 0.3)[..., None], np.array([0.62, 0.42, 0.24]) * (0.8 + 0.3 * f[..., None]), alb)
    return save('muskeg', S, alb, h, 0.95, 6, ao_k=1.0)

def snow(S):
    f = norm01(fbm_p(S, 3, 121, 6))
    drift = norm01(fbm_p(S, 2, 122, 3))
    grain = blur_w(np.random.default_rng(123).random((S, S)), 1)
    h = 0.6 * f + 0.3 * drift + 0.1 * grain
    alb = ramp(norm01(h), [(0, (196, 206, 222)), (1, (244, 247, 252))])
    sparkle = (np.random.default_rng(124).random((S, S)) > 0.997)
    rough = np.where(sparkle, 0.15, 0.75 + 0.1 * grain)
    return save('snow', S, alb, h, rough, 2.5, ao_k=0.5)

def water_normal(S):
    """Tileable ripple normal map for water shaders (two of these, scrolled in different directions)."""
    os.makedirs(OUT, exist_ok=True)
    h = np.zeros((S, S))
    for o, (p, a) in enumerate([(4, 1.0), (8, 0.55), (16, 0.3), (32, 0.15)]):
        h += a * perlin_p(S, p, 131 + o)
    F1, F2, _ = worley_p(S, 12, 135)
    h += 0.25 * norm01(F1)
    n = normal_from_height(norm01(h), 5 * S / 1024)
    Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8)).save(f'{OUT}/water_normal.png')
    return dict(name='water_normal', size=S)

MATERIALS = dict(grass_meadow=grass_meadow, grass_dry=grass_dry, sand_beach=sand_beach, sand_wet=sand_wet, pebbles=pebbles,
                 rock_granite=rock_granite, rock_strata=rock_strata, forest_floor=forest_floor, dirt=dirt,
                 desert_ripples=desert_ripples, cracked_earth=cracked_earth, gravel_track=gravel_track, asphalt=asphalt, muskeg=muskeg, snow=snow, water_normal=water_normal)

if __name__ == '__main__':
    S = int(sys.argv[1]) if len(sys.argv) > 1 else 1024
    names = sys.argv[2:] or list(MATERIALS)
    meta = []
    for n in names:
        meta.append(MATERIALS[n](S)); print(json.dumps(meta[-1]), flush=True)
    json.dump(meta, open(f'{OUT}/materials_{S}.json', 'w'), indent=1)
