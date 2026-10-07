"""Procedural tiling PBR sets for the port: concrete, asphalt, gravel (512 x 512 jpeg q90, 4:2:0) + road markings decal.
  python tex_port.py        (needs numpy + pillow)
Writes ../../assets/t_<name>_{albedo,normal,orh}.jpg and t_road_markings.png.
orh: R = ambient occlusion, G = roughness, B = height. Normal map is tangent space, +Y up (three.js default), flat = 128,128,255."""
import numpy as np, os
from PIL import Image
OUT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets'))
N = 512


def noise(seed, beta=2.0, n=N, lo=1):
    """Periodic (tileable) fractal noise by spectral filtering, normalised to 0..1."""
    r = np.random.default_rng(seed)
    f = np.fft.fft2(r.standard_normal((n, n)))
    fx = np.fft.fftfreq(n)[:, None] * n; fy = np.fft.fftfreq(n)[None, :] * n
    k = np.sqrt(fx ** 2 + fy ** 2); k[0, 0] = 1
    f *= (np.maximum(k, lo) ** (-beta / 2.0)); f[0, 0] = 0
    a = np.real(np.fft.ifft2(f)); a -= a.min(); a /= a.max()
    return a


def white(seed, n=N):
    return np.random.default_rng(seed).random((n, n))


def blur(a, s):
    f = np.fft.fft2(a); fx = np.fft.fftfreq(a.shape[0])[:, None]; fy = np.fft.fftfreq(a.shape[1])[None, :]
    return np.real(np.fft.ifft2(f * np.exp(-2 * (np.pi * s) ** 2 * (fx ** 2 + fy ** 2))))


def normal_from_height(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * strength   # row index grows downward
    nx, ny, nz = -dx, dy, np.ones_like(h)                           # +Y up: image rows go down, so +dy of height downward tilts normal up
    l = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    return np.stack([nx / l, ny / l, nz / l], -1) * 0.5 + 0.5


def save(name, albedo, normal, ao, rough, height):
    def u8(a): return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(u8(albedo)).save(f'{OUT}/t_{name}_albedo.jpg', quality=90)
    Image.fromarray(u8(normal)).save(f'{OUT}/t_{name}_normal.jpg', quality=90)
    Image.fromarray(u8(np.stack([ao, rough, height], -1))).save(f'{OUT}/t_{name}_orh.jpg', quality=90)


def lines_mask(n, cells, w, jitter_seed=None):
    """Periodic grid lines (cells x cells panels), line half-width w px."""
    i = np.arange(n)
    step = n // cells
    d = np.minimum(i % step, step - (i % step))
    L = (d < w).astype(float)
    return L[:, None], L[None, :]


# ---------------------------------------------------------------- concrete
def concrete():
    h = 0.55 * noise(1, 2.6) + 0.25 * noise(2, 1.5, lo=8) + 0.12 * blur(white(3), 0.6) + 0.08 * noise(4, 3.5)
    h = (h - h.min()) / (h.max() - h.min())
    hl, vl = lines_mask(N, 2, 2.2)                       # expansion joints: 256 px slabs, tiles seamlessly
    joint = np.clip(np.maximum(hl, vl) * 1.0, 0, 1)
    joint = blur(np.broadcast_to(np.maximum(hl, vl), (N, N)).copy(), 0.9)
    joint = joint / joint.max()
    # slab-to-slab tone shift
    sx = (np.arange(N) // 256)[None, :]; sy = (np.arange(N) // 256)[:, None]
    tone = 0.035 * (np.sin(sx * 2.1 + sy * 3.7 + 1.0))
    base = 0.60 + 0.16 * (noise(5, 2.2, lo=2) - 0.5) + tone
    speck = (white(6) > 0.985) * 0.12 - (white(7) > 0.985) * 0.12
    stain = np.clip((noise(8, 3.2, lo=2) - 0.55) * 2.2, 0, 1) * 0.12      # faint dark stains
    streak = blur(white(9)[:, :64].repeat(8, 1), 3.0) if False else 0
    v = base + 0.08 * (h - 0.5) + speck - stain - joint * 0.28
    v = np.clip(v, 0, 1)
    alb = np.stack([v * 1.0, v * 1.0, v * 0.98], -1)
    hh = h * 0.8 + 0.2 - joint * 0.6 + 0.0
    hh = np.clip(hh, 0, 1)
    nrm = normal_from_height(hh + 0.4 * blur(white(10), 0.5) * 0.15, 3.5)
    ao = np.clip(1.0 - joint * 0.6 - (1 - noise(11, 2.5)) * 0.08, 0, 1)
    rough = np.clip(0.82 + 0.1 * (noise(12, 2.5) - 0.5) + stain * 0.5, 0, 1)
    save('concrete', alb, nrm, ao, rough, hh)


# ---------------------------------------------------------------- asphalt
def cracks(seed, count=5, n=N):
    """Thin meandering periodic cracks drawn as polylines on a torus."""
    r = np.random.default_rng(seed)
    m = np.zeros((n, n))
    for _ in range(count):
        x, y = r.random(2) * n; a = r.random() * 6.28
        for _ in range(r.integers(80, 220)):
            a += r.normal(0, 0.35); x += np.cos(a) * 2.0; y += np.sin(a) * 2.0
            m[int(y) % n, int(x) % n] = 1
            if r.random() < 0.02:
                bx, by, ba = x, y, a + r.choice([-1, 1]) * 0.8
                for _ in range(r.integers(10, 40)):
                    ba += r.normal(0, 0.3); bx += np.cos(ba) * 2; by += np.sin(ba) * 2
                    m[int(by) % n, int(bx) % n] = 1
    return np.clip(blur(m, 0.7) * 4.0, 0, 1)


def asphalt():
    fine = white(21)
    agg = blur(white(22), 0.8); agg = (agg - agg.min()) / (agg.max() - agg.min())
    big = (white(23) > 0.992).astype(float); big = np.clip(blur(big, 1.2) * 9, 0, 1)
    h = 0.45 * agg + 0.25 * noise(24, 2.4) + 0.2 * big + 0.1 * fine
    h = (h - h.min()) / (h.max() - h.min())
    cr = cracks(25, 4)
    patch = noise(26, 3.0, lo=2)
    v = 0.17 + 0.05 * (patch - 0.5) + 0.07 * (agg - 0.5) + 0.12 * big * (white(27) > 0.5) - 0.07 * cr
    v = np.clip(v, 0, 1)
    alb = np.stack([v, v, v * 1.04], -1)
    hh = np.clip(h - cr * 0.5, 0, 1)
    nrm = normal_from_height(hh, 5.0)
    ao = np.clip(1.0 - cr * 0.6 - (1 - agg) * 0.18, 0, 1)
    rough = np.clip(0.88 + 0.08 * (noise(28, 2.0) - 0.5) - 0.12 * big, 0, 1)
    save('asphalt', alb, nrm, ao, rough, hh)


# ---------------------------------------------------------------- gravel
def gravel():
    n = N; r = np.random.default_rng(31)
    h = np.zeros((n, n)); col = np.zeros((n, n, 3)); idm = np.zeros((n, n))
    yy, xx = np.mgrid[0:n, 0:n]
    pal = np.array([[0.55, 0.52, 0.47], [0.42, 0.40, 0.38], [0.64, 0.60, 0.52], [0.36, 0.35, 0.34], [0.60, 0.50, 0.40], [0.50, 0.50, 0.50]])
    stones = []
    for sz, cnt in ((15, 120), (10, 300), (6, 600), (3.5, 1200)):
        for _ in range(cnt):
            stones.append((r.random() * n, r.random() * n, sz * (0.6 + 0.8 * r.random()), r.random() * 3.14, 0.65 + 0.3 * r.random(), r.integers(0, len(pal)), r.random() * 0.15))
    stones.sort(key=lambda s: -s[2])               # big first, small ones fill on top is wrong; use max-height blend instead
    for (cx, cy, rad, ang, el, ci, hv) in stones:
        R = int(rad * 1.5) + 2
        ys = np.arange(int(cy) - R, int(cy) + R + 1); xs = np.arange(int(cx) - R, int(cx) + R + 1)
        Y, X = np.meshgrid(ys, xs, indexing='ij')
        dx, dy = X - cx, Y - cy
        u = (dx * np.cos(ang) + dy * np.sin(ang)) / rad; w = (-dx * np.sin(ang) + dy * np.cos(ang)) / (rad * el)
        d = u * u + w * w
        m = d < 1
        zz = np.sqrt(np.clip(1 - d, 0, 1)) * (0.45 + 0.55 * rad / 15)
        iy, ix = Y % n, X % n
        cur = h[iy, ix]
        upd = m & (zz + hv * 0.1 > cur)
        h[iy[upd], ix[upd]] = (zz + hv * 0.1)[upd]
        base = pal[ci] * (0.85 + 0.3 * r.random())
        for c in range(3):
            tmp = col[iy, ix, c]; tmp[upd] = base[c]; col[iy, ix, c] = tmp
        tmp = idm[iy, ix]; tmp[upd] = 1; idm[iy, ix] = tmp
    # fill gaps with dusty sand
    fill = noise(33, 2.0)
    dust = np.array([0.35, 0.32, 0.28])
    for c in range(3):
        col[:, :, c] = np.where(idm > 0, col[:, :, c], dust[c] * (0.8 + 0.4 * fill))
    h = h / h.max()
    sp = (white(34) - 0.5) * 0.12
    alb = np.clip(col * (0.86 + 0.28 * h[..., None]) + sp[..., None] + 0.06 * (noise(35, 2.5) - 0.5)[..., None], 0, 1)
    nrm = normal_from_height(h, 9.0)
    ao = np.clip(0.35 + 0.65 * h ** 0.6, 0, 1)
    rough = np.clip(0.88 - 0.12 * h + 0.06 * (white(36) - 0.5), 0, 1)
    save('gravel', alb, nrm, ao, rough, h)


# ---------------------------------------------------------------- road markings decal (512 x 512 RGBA)
def markings():
    """Road strip, tileable along V (rows). Layout across U (columns), 512 px = ~8 m wide road strip (1 px = 1.56 cm).
    Left edge line x 16..28, right edge line 484..496, yellow double? no: single white dashed centre (white), plus yellow
    solid line pair beside the zebra? Kept simple: dashed WHITE centre line, solid WHITE edge lines, YELLOW solid kerb line
    inside each edge, and a zebra crossing band (rows 0..?) of white bars across the width. Rows wrap seamlessly."""
    n = 512
    img = np.zeros((n, n, 4), np.uint8)
    white_c = (236, 236, 228, 255); yel = (232, 186, 40, 255)
    def rect(x0, x1, y0, y1, c):
        img[y0:y1, x0:x1] = c
    rect(14, 26, 0, n, white_c); rect(486, 498, 0, n, white_c)            # solid white edge lines, run through the crossing rows
    for k in range(2):                                                    # yellow dashed centre line (128 on / 128 off), clear of the crossing
        rect(250, 262, k * 256, k * 256 + 128 if k == 0 else k * 256 + 96, yel)
    # rows 384..512 hold the zebra crossing (crop V 0.75..1 for it, 0..0.75 for plain line work)
    img[384:512, 30:482, :] = 0
    rect(44, 468, 372, 380, white_c)                                     # stop line
    for i in range(10):
        x0 = 54 + i * 40
        rect(x0, x0 + 22, 392, 504, white_c)
    # scuff: knock out a little alpha with noise so the paint looks worn
    wear = noise(41, 1.8, n=n)
    sp = white(42, n)
    a = img[..., 3].astype(float) * np.clip(0.78 + 0.5 * wear - 0.12 * (sp > 0.93), 0, 1)
    img[..., 3] = a.astype(np.uint8)
    Image.fromarray(img, 'RGBA').save(f'{OUT}/t_road_markings.png', optimize=True)


if __name__ == '__main__':
    concrete(); asphalt(); gravel(); markings()
    print('textures done')
