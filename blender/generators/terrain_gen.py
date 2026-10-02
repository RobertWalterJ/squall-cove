"""Noise terrain generator: gradient noise, fBm / ridged / billow, domain warping, masks, terracing,
thermal + hydraulic (droplet) erosion, and map export (16-bit height, normal, splat, hillshade, flow).

Run:  python3 terrain_gen.py [preset ...]      (numpy + numba)
Units: one cell = CELL metres; heights in metres; sea level = 0.
"""
import sys, os, json, math
import numpy as np
from numba import njit
from PIL import Image

OUT = '/home/claude/procgen/out/terrain'
N = 257          # grid points per side
CELL = 1.0       # metres per cell  (257 x 1 m = 256 m tile)

# ---------------------------------------------------------------- gradient noise (Perlin, vectorised)
def _perm(seed):
    rng = np.random.default_rng(seed)
    p = rng.permutation(256)
    return np.concatenate([p, p])

def perlin(x, y, seed=0):
    p = _perm(seed)
    xi, yi = np.floor(x).astype(int) & 255, np.floor(y).astype(int) & 255
    xf, yf = x - np.floor(x), y - np.floor(y)
    u, v = xf * xf * xf * (xf * (xf * 6 - 15) + 10), yf * yf * yf * (yf * (yf * 6 - 15) + 10)
    def grad(h, x, y):
        a = h * 2.399963  # golden-angle gradients: 256 directions, no axis-aligned bias
        return np.cos(a) * x + np.sin(a) * y
    n00 = grad(p[p[xi] + yi], xf, yf)
    n10 = grad(p[p[xi + 1] + yi], xf - 1, yf)
    n01 = grad(p[p[xi] + yi + 1], xf, yf - 1)
    n11 = grad(p[p[xi + 1] + yi + 1], xf - 1, yf - 1)
    x1 = n00 + u * (n10 - n00); x2 = n01 + u * (n11 - n01)
    return (x1 + v * (x2 - x1)) * 1.41

ROT = (math.cos(0.6435), math.sin(0.6435))  # rotate every octave by ~37 degrees to break lattice alignment
def _rot(x, y, o):
    c, s_ = math.cos(0.6435 * o), math.sin(0.6435 * o)
    return x * c - y * s_ + o * 17.13, x * s_ + y * c - o * 9.71

def fbm(x, y, seed, octaves=6, lac=2.0, gain=0.5):
    s, a, f, norm = 0.0, 1.0, 1.0, 0.0
    for o in range(octaves):
        rx, ry = _rot(x * f, y * f, o)
        s = s + a * perlin(rx, ry, seed + o * 101)
        norm += a; a *= gain; f *= lac
    return s / norm

def ridged(x, y, seed, octaves=6, lac=2.0, gain=0.5, sharp=2.0):
    """Ridged multifractal: 1-|n| folded into sharp crests, each octave weighted by the one above."""
    s, a, f, w, norm = 0.0, 1.0, 1.0, 1.0, 0.0
    for o in range(octaves):
        rx, ry = _rot(x * f, y * f, o)
        n = (1.0 - np.abs(perlin(rx, ry, seed + o * 131))) ** sharp
        s = s + n * a * w
        w = np.clip(n * 1.5, 0, 1)
        norm += a; a *= gain; f *= lac
    return s / norm

def billow(x, y, seed, octaves=5):
    s, a, f, norm = 0.0, 1.0, 1.0, 0.0
    for o in range(octaves):
        rx, ry = _rot(x * f, y * f, o)
        s = s + a * (np.abs(perlin(rx, ry, seed + o * 77)) * 2 - 1)
        norm += a; a *= 0.5; f *= 2.0
    return s / norm

def warp(x, y, seed, amount, scale):
    """Domain warping: offset the lookup coordinates by another noise field (gives folded, organic coastlines)."""
    qx = fbm(x * scale, y * scale, seed + 7, 4)
    qy = fbm(x * scale + 5.2, y * scale + 1.3, seed + 13, 4)
    return x + amount * qx, y + amount * qy

def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)

# ---------------------------------------------------------------- erosion
@njit(cache=True)
def thermal_erosion(h, iters, talus, rate):
    """Material slides downhill wherever the slope exceeds the talus angle (scree slopes, softened cliffs)."""
    n = h.shape[0]
    for _ in range(iters):
        d = np.zeros_like(h)
        for i in range(1, n - 1):
            for j in range(1, n - 1):
                hc = h[i, j]; dmax = 0.0; tot = 0.0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0: continue
                        dd = hc - h[i + di, j + dj]
                        if dd > talus:
                            tot += dd
                            if dd > dmax: dmax = dd
                if tot > 0:
                    move = rate * (dmax - talus)
                    for di in (-1, 0, 1):
                        for dj in (-1, 0, 1):
                            if di == 0 and dj == 0: continue
                            dd = hc - h[i + di, j + dj]
                            if dd > talus:
                                f = move * dd / tot
                                d[i, j] -= f; d[i + di, j + dj] += f
        h += d
    return h

@njit(cache=True)
def hydraulic_erosion(h, drops, seed, inertia=0.05, capacity=4.0, deposit=0.3, erode=0.3, evap=0.01, gravity=4.0, radius=2, max_steps=64):
    """Droplet erosion (after Hans Beyer's method): each raindrop runs downhill, picks up sediment where it
    accelerates and drops it where it slows. Carves gullies and builds fans. Also returns a flow-count map."""
    n = h.shape[0]
    np.random.seed(seed)
    flow = np.zeros_like(h)
    # precompute brush weights
    rr = radius
    for _ in range(drops):
        x = np.random.random() * (n - 2); y = np.random.random() * (n - 2)
        dx = 0.0; dy = 0.0; speed = 1.0; water = 1.0; sed = 0.0
        for step in range(max_steps):
            ix = int(x); iy = int(y)
            if ix < 1 or iy < 1 or ix >= n - 2 or iy >= n - 2: break
            fx = x - ix; fy = y - iy
            h00 = h[iy, ix]; h10 = h[iy, ix + 1]; h01 = h[iy + 1, ix]; h11 = h[iy + 1, ix + 1]
            gx = (h10 - h00) * (1 - fy) + (h11 - h01) * fy
            gy = (h01 - h00) * (1 - fx) + (h11 - h10) * fx
            hh = h00 * (1 - fx) * (1 - fy) + h10 * fx * (1 - fy) + h01 * (1 - fx) * fy + h11 * fx * fy
            dx = dx * inertia - gx * (1 - inertia); dy = dy * inertia - gy * (1 - inertia)
            ln = math.sqrt(dx * dx + dy * dy)
            if ln < 1e-9: break
            dx /= ln; dy /= ln
            nx = x + dx; ny = y + dy
            jx = int(nx); jy = int(ny)
            if jx < 1 or jy < 1 or jx >= n - 2 or jy >= n - 2: break
            if hh < 0.0 and step > 2:  # reached the sea: drop the load and stop
                break
            gfx = nx - jx; gfy = ny - jy
            nh = h[jy, jx] * (1 - gfx) * (1 - gfy) + h[jy, jx + 1] * gfx * (1 - gfy) + h[jy + 1, jx] * (1 - gfx) * gfy + h[jy + 1, jx + 1] * gfx * gfy
            dh = nh - hh
            cap = max(-dh, 0.01) * speed * water * capacity
            if sed > cap or dh > 0:
                amt = min(dh, sed) if dh > 0 else (sed - cap) * deposit
                sed -= amt
                h[iy, ix] += amt * (1 - fx) * (1 - fy); h[iy, ix + 1] += amt * fx * (1 - fy)
                h[iy + 1, ix] += amt * (1 - fx) * fy; h[iy + 1, ix + 1] += amt * fx * fy
            else:
                amt = min((cap - sed) * erode, -dh)
                wsum = 0.0
                for a in range(-rr, rr + 1):
                    for b in range(-rr, rr + 1):
                        d2 = a * a + b * b
                        if d2 <= rr * rr and 0 < iy + a < n - 1 and 0 < ix + b < n - 1:
                            wsum += rr - math.sqrt(d2)
                for a in range(-rr, rr + 1):
                    for b in range(-rr, rr + 1):
                        d2 = a * a + b * b
                        if d2 <= rr * rr and 0 < iy + a < n - 1 and 0 < ix + b < n - 1:
                            w = (rr - math.sqrt(d2)) / wsum
                            h[iy + a, ix + b] -= amt * w
                sed += amt
            flow[iy, ix] += 1.0
            speed = math.sqrt(max(speed * speed + dh * -gravity, 0.0))
            water *= (1 - evap)
            x = nx; y = ny
    return h, flow

# ---------------------------------------------------------------- presets
def grid():
    c = (np.arange(N) - (N - 1) / 2) * CELL
    X, Y = np.meshgrid(c, c)
    return X, Y

def radial(X, Y, r0):
    return np.sqrt(X ** 2 + Y ** 2) / r0

def preset_archipelago(seed=3):
    X, Y = grid()
    wx, wy = warp(X / 90, Y / 90, seed, 0.55, 1.2)
    base = fbm(wx, wy, seed, 6)
    isl = np.clip(1 - radial(X, Y, 118) ** 2, 0, 1)
    h = (base * 0.55 + 0.25) * 38 * isl + isl * 10 - 9
    h += ridged(X / 60, Y / 60, seed + 5, 5) * 14 * smoothstep(0.2, 0.9, isl)
    return dict(h=h, erosion=(30000, 10), sea=True, snow=99, desc='Domain-warped fBm under an island falloff, ridged peaks, droplet erosion.')

def preset_alpine(seed=11):
    X, Y = grid()
    r = ridged(X / 110, Y / 110, seed, 7, sharp=2.2)
    valleys = fbm(X / 200, Y / 200, seed + 3, 3)
    h = r * 95 + valleys * 25 + 8
    return dict(h=h, erosion=(45000, 25), sea=False, snow=66, desc='Ridged multifractal (weighted octaves) for knife-edge arêtes, heavy droplet and thermal erosion, snowline.')

def preset_hills(seed=5):
    X, Y = grid()
    h = billow(X / 140, Y / 140, seed, 5) * 30 + fbm(X / 60, Y / 60, seed + 1, 4) * 6 + 20
    return dict(h=h, erosion=(12000, 4), sea=False, snow=99, desc='Billow noise (|n| folded) for rounded drumlin-like hills, light erosion.')

def preset_mesa(seed=21):
    X, Y = grid()
    wx, wy = warp(X / 120, Y / 120, seed, 0.4, 1.0)
    b = fbm(wx, wy, seed, 5) * 0.5 + 0.5
    steps = 5
    t = b * steps
    terr = (np.floor(t) + smoothstep(0.82, 1.0, t - np.floor(t))) / steps   # flat benches, steep risers
    river = np.abs(fbm(X / 160 + 3, Y / 160, seed + 9, 3))
    carve = smoothstep(0.0, 0.08, river)
    h = terr * 60 * carve + 4
    return dict(h=h, erosion=(15000, 6), sea=False, snow=99, desc='Warped fBm quantised into benches (terracing), a river canyon from |noise| carving, mild erosion.')

def preset_cliffs(seed=8):
    X, Y = grid()
    wx, wy = warp(X / 100, Y / 100, seed, 0.6, 1.3)
    m = fbm(wx, wy, seed, 5) + 0.25 - (Y / 256)          # land to the north, sea to the south
    plateau = smoothstep(-0.02, 0.06, m)                  # sharp step = sea cliff
    h = plateau * (26 + fbm(X / 50, Y / 50, seed + 2, 4) * 6) + (1 - plateau) * (-6 + m * 10)
    return dict(h=h, erosion=(15000, 3), sea=True, snow=99, desc='Warped coastline mask through a hard smoothstep: a plateau that ends in sea cliffs and a wave-cut platform.')

def preset_volcano(seed=4):
    X, Y = grid()
    rd = radial(X, Y, 120)
    ang = np.arctan2(Y, X)
    cone = np.clip(1 - rd, 0, 1) ** 1.6
    rib = ridged(ang * 3, rd * 6, seed, 3, sharp=1.5) * 0.25 * cone           # radial lava ribs
    crater = np.exp(-(rd / 0.12) ** 2) * 0.45
    h = (cone + rib - crater) * 80 + fbm(X / 40, Y / 40, seed, 3) * 2 - 8
    return dict(h=h, erosion=(25000, 6), sea=True, snow=99, desc='Power-curve cone, ridged noise in polar coordinates for radial ribs, Gaussian crater.')

PRESETS = dict(archipelago=preset_archipelago, alpine=preset_alpine, hills=preset_hills, mesa=preset_mesa, cliffs=preset_cliffs, volcano=preset_volcano)

# ---------------------------------------------------------------- maps
def normals(h):
    gy, gx = np.gradient(h, CELL)
    n = np.dstack([-gx, -gy, np.ones_like(h)])
    return n / np.linalg.norm(n, axis=2, keepdims=True)

def splat(h, nrm, snow, sea):
    slope = 1 - nrm[..., 2]
    sand = smoothstep(2.5, 0.8, h) * (1 if sea else 0.0)
    rock = smoothstep(0.18, 0.32, slope)
    snw = smoothstep(snow - 4, snow + 4, h) * (1 - smoothstep(0.35, 0.5, slope))
    grass = np.clip(1 - sand - rock - snw, 0, 1)
    s = np.dstack([sand, grass, rock, snw]); s /= s.sum(axis=2, keepdims=True) + 1e-6
    return s

def hillshade(h, nrm, spl, sea):
    light = np.array([-0.6, 0.5, 0.62]); light /= np.linalg.norm(light)
    sh = np.clip((nrm * light).sum(axis=2), 0, 1) * 0.85 + 0.15
    cols = np.array([[0.85, 0.77, 0.56], [0.42, 0.55, 0.27], [0.52, 0.49, 0.45], [0.93, 0.94, 0.96]])
    rgb = (spl[..., :, None] * cols[None, None]).sum(axis=2) * sh[..., None]
    if sea:
        w = h < 0
        depth = np.clip(-h / 10, 0, 1)[..., None]
        water = np.array([0.33, 0.62, 0.66]) * (1 - depth) + np.array([0.09, 0.27, 0.36]) * depth
        rgb[w] = (water * 0.8 + rgb * 0.2)[w]
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)

def run(name):
    os.makedirs(OUT, exist_ok=True)
    P = PRESETS[name]()
    h = P['h'].astype(np.float64)
    drops, therm = P['erosion']
    h, flow = hydraulic_erosion(h, drops, 7)
    h = thermal_erosion(h, therm, 0.9 * CELL, 0.25)
    nrm = normals(h); spl = splat(h, nrm, P['snow'], P['sea'])
    np.save(f'{OUT}/{name}_h.npy', h.astype(np.float32))
    np.save(f'{OUT}/{name}_splat.npy', spl.astype(np.float32))
    lo, hi = float(h.min()), float(h.max())
    Image.fromarray(((h - lo) / (hi - lo) * 65535).astype(np.uint16)).save(f'{OUT}/{name}_height16.png')
    Image.fromarray(((nrm * 0.5 + 0.5) * 255).astype(np.uint8)).save(f'{OUT}/{name}_normal.png')
    Image.fromarray((spl * 255).astype(np.uint8), 'RGBA').save(f'{OUT}/{name}_splat_sand-grass-rock-snow.png')
    Image.fromarray(hillshade(h, nrm, spl, P['sea'])).save(f'{OUT}/{name}_hillshade.png')
    f = np.log1p(flow); Image.fromarray((f / max(f.max(), 1e-6) * 255).astype(np.uint8)).save(f'{OUT}/{name}_flow.png')
    meta = dict(preset=name, size_m=(N - 1) * CELL, grid=N, cell_m=CELL, min_m=round(lo, 2), max_m=round(hi, 2), sea_level=0 if P['sea'] else None,
                snowline_m=P['snow'] if P['snow'] < 99 else None, droplets=drops, thermal_iters=therm, method=P['desc'])
    json.dump(meta, open(f'{OUT}/{name}.json', 'w'), indent=1)
    return meta

if __name__ == '__main__':
    names = sys.argv[1:] or list(PRESETS)
    for n_ in names:
        print(json.dumps(run(n_)))
