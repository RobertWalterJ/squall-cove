"""
bake.py - run sim.py for a preset and bake flipbook atlases.

    python tools/fire/bake.py campfire            # one preset, final quality
    python tools/fire/bake.py all                 # all five, one after another
    python tools/fire/bake.py campfire --quick    # 16 frames, short warm-up, to ./_fire_tmp/ (look-dev)

Writes assets/fire/fire_<preset>_flame.png / _smoke.png / _heat.png and merges the
preset into assets/fire/fire_atlas.json.

Rendering model (orthographic, camera looks along +y through the 3D grid):
  * flame: emission-absorption ray march. Soot incandescence (colour from a
    blackbody-like ramp of the local temperature, brightness ~ soot * theta^3),
    blue chemiluminescence from the lean / premixed part of the reaction rate,
    orange from the rich part. Soot absorbs what is behind it. Tone-mapped
    (1 - exp(-expo*I)), stored premultiplied, alpha = max(r, g, b).
  * smoke: absorption + single-scatter-ish shading (light from above through the
    smoke column), grey LA texture, straight alpha.
  * heat: max temperature along the ray, 8-bit.
  * sub-grid detail: a periodic 3D noise volume scrolls upward and modulates the
    soot / temperature before emission, plus a small 2D warp of the final image.
    It is purely cosmetic (it is not part of the solver).
  * seamless loop: the sim is run for frames+overlap frames; the first `overlap`
    output frames are a cross-fade from the continuation (frames N..N+M-1) into the
    start (frames 0..M-1), so the last output frame flows into the first.
"""
import argparse, json, os, sys, time
import numpy as np
from scipy import ndimage as ndi
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import sim as S  # noqa: E402

N_FRAMES = 64
OVERLAP = 16
FPS = 24
UP = 4  # flame render supersample of the sim grid in x and z
SMOKE_SCALE = 0.5
HEAT_SCALE = 0.5
GRID_COLS = 8

# per-preset look parameters
LOOK = {
    "campfire": dict(cs=4.5, ka=0.10, cb=0.15, co=1.0, expo=1.5, scroll=3, warp=1.6, noise=0.45, smoke_k=1.6, smoke_albedo=0.40, smoke_pv=0.5, fps=24),
    "gas": dict(cs=4.5, ka=0.10, cb=0.5, co=0.6, expo=1.7, scroll=4, warp=1.0, noise=0.30, smoke_k=0.5, smoke_albedo=0.35, smoke_pv=0.0, fps=24),
    "pool": dict(cs=4.5, ka=0.09, cb=0.2, co=0.8, expo=1.8, scroll=1, warp=1.6, noise=0.55, smoke_k=0.7, smoke_albedo=0.06, smoke_pv=0.0, fps=20),
    "vehicle": dict(cs=4.5, ka=0.09, cb=0.2, co=0.8, expo=1.8, scroll=1, warp=1.8, noise=0.55, smoke_k=0.7, smoke_albedo=0.08, smoke_pv=0.0, fps=20),
    "building": dict(cs=4.5, ka=0.09, cb=0.2, co=0.8, expo=1.8, scroll=1, warp=1.8, noise=0.55, smoke_k=0.55, smoke_albedo=0.14, smoke_pv=0.0, fps=18),
}


def planck_rgb(tc):
    """Approximate colour of a blackbody at tc kelvin (Tanner Helland fit), linear-ish 0..1."""
    t = tc / 100.0
    r = np.where(t <= 66, 255.0, 329.698727446 * np.power(np.maximum(t - 60, 1e-3), -0.1332047592))
    g = np.where(t <= 66, 99.4708025861 * np.log(np.maximum(t, 1)) - 161.1195681661,
                 288.1221695283 * np.power(np.maximum(t - 60, 1e-3), -0.0755148492))
    b = np.where(t >= 66, 255.0, np.where(t <= 19, 0.0, 138.5177312231 * np.log(np.maximum(t - 10, 1)) - 305.0447927307))
    return np.clip(np.stack([r, g, b], -1) / 255.0, 0, 1)


def build_lut():
    th = np.linspace(0, 1.15, 256)
    tc = 950.0 + 1900.0 * th          # visible colour temperature of the emitting soot, K
    rgb = planck_rgb(tc)
    # soft desaturation toward white only at the very hot end (flame cores read yellow-white)
    return rgb.astype(np.float32)


LUT = build_lut()


def lut_rgb(th):
    i = np.clip((th * (255 / 1.15)).astype(np.int32), 0, 255)
    return LUT[i]


def make_noise(shape, seed):
    rng = np.random.default_rng(seed)
    nz, ny, nx = shape
    out = 0
    for sig, wgt in (((9, 4, 7), 1.0), ((4.5, 2, 3.5), 0.75), ((2.2, 1, 1.8), 0.45)):
        r = rng.standard_normal(shape).astype(np.float32)
        r = ndi.gaussian_filter(r, sig, mode="wrap")
        r /= r.std() + 1e-6
        out = out + wgt * r
    out /= out.std()
    return out.astype(np.float32)


def up2(f):
    """sim field (nx,ny,nz) -> volume V[z(top first), y, x] upsampled 2x in x and z."""
    v = np.transpose(f.astype(np.float32), (2, 1, 0))[::-1]
    return ndi.zoom(v, (UP, 1, UP), order=1)


def warp2d(img, nz, ny, amp, seed_off):
    """small displacement warp of an (H,W,...) image using two noise slices"""
    H, W = img.shape[:2]
    dy = amp * nz[:H, :W]
    dx = amp * ny[:H, :W]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    coords = np.stack([np.clip(yy + dy, 0, H - 1), np.clip(xx + dx, 0, W - 1)])
    if img.ndim == 2:
        return ndi.map_coordinates(img, coords, order=1, mode="nearest")
    return np.stack([ndi.map_coordinates(img[..., c], coords, order=1, mode="nearest") for c in range(img.shape[2])], -1)


class Renderer:
    def __init__(self, preset, grid, seed):
        self.k = LOOK[preset]
        self.preset = preset
        nx, ny, nz = grid
        self.shape = (nz * UP, ny, nx * UP)
        self.noise = make_noise(self.shape, seed + 7)
        # displacement noise: two independent slices
        n2 = make_noise((self.shape[0], 1, self.shape[2]), seed + 31)[:, 0, :]
        n3 = make_noise((self.shape[0], 1, self.shape[2]), seed + 53)[:, 0, :]
        self.disp = (n2, n3)
        self.period = self.shape[0]

    def rolled(self, i):
        # `scroll` whole periods of the noise volume per loop of N_FRAMES -> the texture loops exactly
        shift = -(i * self.k["scroll"] * self.period) // N_FRAMES
        return np.roll(self.noise, int(shift), axis=0)

    def flame(self, f, i):
        k = self.k
        th, Sm, R, Rb = (up2(f[n]) for n in ("th", "S", "R", "Rb"))
        n = self.rolled(i)
        am = k["noise"]
        thm = np.clip(th * (1 + 0.22 * am * n) + 0.03 * am * n * (th > 0.05), 0, 1.15)
        Sx = np.clip(Sm, 0, None) * np.clip(1 + 0.9 * am * n, 0.05, None)
        g = S.smoothstep(0.15, 0.42, thm) * thm ** 3
        col = lut_rgb(thm)
        Es = k["cs"] * Sx[..., None] * g[..., None] * col
        Rm = np.clip(R, 0, None) * np.clip(1 + 0.7 * am * n, 0.1, None)
        Rbm = np.clip(Rb, 0, None) * np.clip(1 + 0.7 * am * n, 0.1, None)
        blue = np.array([0.16, 0.38, 1.0], np.float32)
        Eb = k["cb"] * Rbm[..., None] * blue * 0.35
        Eo = k["co"] * np.clip(Rm - Rbm, 0, None)[..., None] * col * 0.35
        E = Es + Eb + Eo
        tau = k["ka"] * Sx + 0.02 * np.linalg.norm(E, axis=-1)
        cum = np.cumsum(tau, axis=1) - tau
        Tr = np.exp(-cum)[..., None]
        I = (E * Tr).sum(axis=1)  # (H, W, 3)
        I = warp2d(I, self.disp[0], self.disp[1], k["warp"], 0)
        out = 1 - np.exp(-k["expo"] * I)
        return out.astype(np.float32), float(E.sum()), float((E.sum(-1) * th).sum() / max(E.sum(), 1e-6))

    def smoke(self, f, i):
        k = self.k
        Sm, P, th = (up2(f[n]) for n in ("S", "P", "th"))
        n = self.rolled(i + 11)
        Sx = np.clip(Sm, 0, None) * np.clip(1 + 0.8 * k["noise"] * n, 0.05, None)
        steam = k["smoke_pv"] * np.clip(P, 0, None) * (1 - S.smoothstep(0.08, 0.30, th)) * np.clip(1 + 0.6 * n, 0.1, None)
        dens = Sx + steam
        tau = k["smoke_k"] * dens
        above = np.cumsum(tau, axis=0) - tau
        lit = np.exp(-0.55 * above)
        shade = 0.30 + 0.70 * lit
        alb = (k["smoke_albedo"] * Sx + 0.88 * steam) / np.maximum(dens, 1e-6)
        col = alb * shade
        cum = np.cumsum(tau, axis=1) - tau
        contrib = (1 - np.exp(-tau)) * np.exp(-cum)
        alpha = contrib.sum(axis=1)
        L = (contrib * col).sum(axis=1)
        alpha = warp2d(alpha, self.disp[0], self.disp[1], 1.0, 0)
        L = warp2d(L, self.disp[0], self.disp[1], 1.0, 0)
        return alpha.astype(np.float32), L.astype(np.float32)

    def heat(self, f):
        th = np.transpose(f["th"].astype(np.float32), (2, 1, 0))[::-1]
        return th.max(axis=1)


# ------------------------------------------------------------------------------------
def crossfade(frames, n, m):
    out = []
    for i in range(n):
        if i < m:
            w = i / m
            w = w * w * (3 - 2 * w)
            out.append((1 - w) * frames[n + i] + w * frames[i])
        else:
            out.append(frames[i])
    return out


def bbox_symmetric(masks, margin, mult=4):
    """crop that is symmetric about the centre column, bottom anchored; returns (x0, x1, y0) with y1=H"""
    H, W = masks[0].shape
    any_ = np.zeros((H, W), bool)
    for m in masks:
        any_ |= m
    ys = np.where(any_.any(axis=1))[0]
    xs = np.where(any_.any(axis=0))[0]
    if len(ys) == 0:
        return 0, W, 0
    y0 = max(0, ys.min() - margin)
    half = max(W // 2 - xs.min(), xs.max() + 1 - W // 2) + margin
    half = min(W // 2, int(np.ceil(half / mult) * mult))
    h = H - y0
    h = int(np.ceil(h / mult) * mult)
    y0 = max(0, H - h)
    return W // 2 - half, W // 2 + half, y0


def make_atlas(imgs, mode):
    n = len(imgs)
    h, w = imgs[0].shape[:2]
    rows = (n + GRID_COLS - 1) // GRID_COLS
    ch = {"RGBA": 4, "LA": 2, "L": 1}[mode]
    at = np.zeros((rows * h, GRID_COLS * w, ch), np.uint8)
    for i, im in enumerate(imgs):
        r, c = divmod(i, GRID_COLS)
        at[r * h:(r + 1) * h, c * w:(c + 1) * w] = im.reshape(h, w, ch)
    return Image.fromarray(at if ch > 1 else at[..., 0], mode)


def save_png(img, path, palette_colors=None, dither=False):
    if palette_colors and img.mode == "RGBA":
        q = img.quantize(colors=palette_colors, method=Image.Quantize.FASTOCTREE,
                         dither=Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE)
        q.save(path, optimize=True)
    else:
        img.save(path, optimize=True)
    return os.path.getsize(path)


def to8(x):
    return np.clip(np.round(x * 255), 0, 255).astype(np.uint8)


def srgb(x):
    return np.power(np.clip(x, 0, 1), 1 / 2.2)


def bake(preset, seed=1, quick=False, outdir=None, log=print, flame_colors=256, flame_dither=False, grid=S.GRID):
    n, m = (16, 4) if quick else (N_FRAMES, OVERLAP)
    look = LOOK[preset]
    fps = look["fps"]
    outdir = outdir or os.path.join(ROOT, "assets", "fire")
    os.makedirs(outdir, exist_ok=True)
    rend = Renderer(preset, grid, seed)
    flames, smokes, heats, lum, meanth = [], [], [], [], []
    warm = None
    t0 = time.time()
    for fi, (fields, sim) in enumerate(S.run(preset, seed, n + m, fps, warm=warm, log=log, grid=grid)):
        ph = fi % n
        rgb, e_tot, mth = rend.flame(fields, ph)
        a, L = rend.smoke(fields, ph)
        flames.append(rgb)
        smokes.append(np.concatenate([L[..., None], a[..., None]], -1))
        heats.append(rend.heat(fields))
        lum.append(e_tot)
        meanth.append(mth)
    log(f"[{preset}] sim+render {time.time() - t0:.0f}s")
    flames = crossfade(flames, n, m)
    smokes = crossfade(smokes, n, m)
    heats = crossfade(heats, n, m)
    lum = np.array(crossfade([np.array(x) for x in lum], n, m))
    meanth = np.array(crossfade([np.array(x) for x in meanth], n, m))

    # ---- flame crop + atlas (premultiplied RGBA, sRGB-encoded) ----
    alphas = [f.max(axis=-1) for f in flames]
    x0, x1, y0 = bbox_symmetric([a > 0.03 for a in alphas], 5)
    fl8 = []
    for f, a in zip(flames, alphas):
        c = srgb(f)[y0:, x0:x1]
        al = a[y0:, x0:x1]
        # premultiplied: rgb <= alpha holds because alpha = max channel (linear); encode both consistently
        rgba = np.concatenate([c * 1.0, srgb(al)[..., None]], -1)
        rgba[..., :3] = np.minimum(rgba[..., :3], rgba[..., 3:4])
        fl8.append(to8(rgba))
    fh, fw = fl8[0].shape[:2]
    p_flame = os.path.join(outdir, f"fire_{preset}_flame.png")
    sz_flame = save_png(make_atlas(fl8, "RGBA"), p_flame, flame_colors, flame_dither)

    # ---- smoke atlas (LA, straight alpha) ----
    sx0, sx1, sy0 = bbox_symmetric([s[..., 1] > 0.02 for s in smokes], 5)
    sm8 = []
    sh_full, sw_full = smokes[0].shape[:2]
    for s in smokes:
        a = s[..., 1][sy0:, sx0:sx1]
        L = s[..., 0][sy0:, sx0:sx1]
        h2, w2 = int(round(a.shape[0] * SMOKE_SCALE / 4) * 4), int(round(a.shape[1] * SMOKE_SCALE / 4) * 4)
        a2 = np.asarray(Image.fromarray(a).resize((w2, h2), Image.BOX if SMOKE_SCALE < 1 else Image.BILINEAR))
        L2 = np.asarray(Image.fromarray(L).resize((w2, h2), Image.BOX if SMOKE_SCALE < 1 else Image.BILINEAR))
        col = np.where(a2 > 1e-4, L2 / np.maximum(a2, 1e-4), 0.0)       # un-premultiply
        sm8.append(to8(np.stack([np.round(srgb(np.clip(col, 0, 1)) * 24) / 24, np.round(a2 * 48) / 48], -1)))
    smh, smw = sm8[0].shape[:2]
    p_smoke = os.path.join(outdir, f"fire_{preset}_smoke.png")
    sz_smoke = save_png(make_atlas(sm8, "LA"), p_smoke)

    # ---- heat atlas (L) at grid resolution ----
    hx0, hx1, hy0 = bbox_symmetric([h > 0.06 for h in heats], 2)
    ht8 = [to8(np.round(np.power(np.clip(h[hy0:, hx0:hx1], 0, 1), 0.8) * 48) / 48) for h in heats]
    hh, hw = ht8[0].shape
    p_heat = os.path.join(outdir, f"fire_{preset}_heat.png")
    sz_heat = save_png(make_atlas([x[..., None] for x in ht8], "L"), p_heat)
    log(f"[{preset}] flame {fw}x{fh} {sz_flame / 1024:.0f} KB, smoke {smw}x{smh} {sz_smoke / 1024:.0f} KB, heat {hw}x{hh} {sz_heat / 1024:.0f} KB")

    # ---- seam check: frame-to-frame change across the loop point vs typical ----
    def d(a, b): return float(np.abs(a.astype(np.float32) - b.astype(np.float32)).mean())
    adj = np.mean([d(fl8[i], fl8[i + 1]) for i in range(n - 1)])
    seam = d(fl8[-1], fl8[0])
    # light data
    pw = lum / lum.mean()
    ker = np.array([0.25, 0.5, 0.25])
    pw_s = np.convolve(np.concatenate([pw[-2:], pw, pw[:2]]), ker, mode="same")[2:-2]
    pw_s = pw_s / pw_s.mean()
    mt = float(np.average(meanth, weights=np.maximum(lum, 1e-6)))
    tc = 950.0 + 1900.0 * mt
    lc = planck_rgb(np.array([tc]))[0]
    lc = lc / lc.max()
    curve = []
    for h in (0.35, 0.5, 0.65, 0.8, 1.0):
        c = planck_rgb(np.array([950.0 + 1900.0 * h]))[0]
        curve.append([round(h, 2)] + [round(float(v), 3) for v in c / c.max()])
    dxm = sim.dx
    m_flame = dxm / UP
    info = dict(
        frames=n, fps=fps, loop=True, grid=[GRID_COLS, (n + GRID_COLS - 1) // GRID_COLS],
        flame=dict(file=f"fire_{preset}_flame.png", frame_px=[fw, fh], m_per_px=round(m_flame, 5),
                   size_m=[round(fw * m_flame, 3), round(fh * m_flame, 3)], anchor=[0.5, 1.0],
                   blend="premultiplied (ONE, ONE_MINUS_SRC_ALPHA) or additive (ONE, ONE); sRGB-encoded", bytes=sz_flame),
        smoke=dict(file=f"fire_{preset}_smoke.png", frame_px=[smw, smh], m_per_px=round(dxm / UP / SMOKE_SCALE, 5),
                   size_m=[round(smw * dxm / UP / SMOKE_SCALE, 3), round(smh * dxm / UP / SMOKE_SCALE, 3)], anchor=[0.5, 1.0],
                   blend="normal, straight alpha, grey LA", bytes=sz_smoke),
        heat=dict(file=f"fire_{preset}_heat.png", frame_px=[hw, hh], m_per_px=round(dxm, 5),
                  size_m=[round(hw * dxm, 3), round(hh * dxm, 3)], anchor=[0.5, 1.0],
                  encoding="8-bit; heat = (value/255)^(1/0.8); 1.0 = about 2000 K, 0 = ambient", bytes=sz_heat),
        emitter=dict(radius_m=round(float(max(v[2] for v in S.PRESETS[preset]["vents"])), 3),
                     spread_m=round(float(max(abs(v[0]) + v[2] for v in S.PRESETS[preset]["vents"])), 3)),
        light=dict(color=[round(float(c), 3) for c in lc], mean_theta=round(mt, 3), mean_kelvin_visible=round(tc),
                   color_by_heat=curve, intensity_rel=round(float(lum.mean()), 2),
                   range_m=round(fh * m_flame * 3.0, 2), flicker=[round(float(x), 3) for x in pw_s]),
        seam=dict(mean_adjacent_diff=round(float(adj), 3), loop_point_diff=round(float(seam), 3)),
        sim=dict(seed=seed, dx_m=dxm, grid=list(grid), stoich_s=S.PRESETS[preset]["s"]),
    )
    log(f"[{preset}] seam: adjacent {adj:.2f}, loop point {seam:.2f}")
    # normalise intensity_rel across presets later (done in merge, relative to campfire if present)
    ap = os.path.join(outdir, "fire_atlas.json")
    data = {"version": 1, "note": "Baked by tools/fire/bake.py (reduced combustion model; see MODEL-NOTES-FIRE-BAKED.md)", "presets": {}}
    if os.path.exists(ap):
        try:
            data = json.load(open(ap))
        except Exception:
            pass
    data["presets"][preset] = info
    base = data["presets"].get("campfire", {}).get("light", {}).get("intensity_rel")
    if base:
        for p in data["presets"].values():
            p["light"]["intensity_vs_campfire"] = round(p["light"]["intensity_rel"] / base, 2)
    with open(ap, "w") as fh_:
        json.dump(data, fh_, separators=(",", ":"))
    return info


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("preset", help="campfire|gas|pool|vehicle|building|all")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--colors", type=int, default=256)
    ap.add_argument("--dither", action="store_true")
    ap.add_argument("--coarse", action="store_true", help="look-dev: half-resolution sim (32x32x48), same physical size, 4x render upsampling")
    a = ap.parse_args()
    names = list(S.PRESETS) if a.preset == "all" else [a.preset]
    out = a.out or (os.path.join(ROOT, "_fire_tmp") if a.quick else None)

    def lg(msg):
        print(msg, flush=True)
    for nm in names:
        if False:
            UP = 4
            S.PRESETS[nm] = dict(S.PRESETS[nm]); S.PRESETS[nm]["dx"] *= 2
            bake(nm, a.seed, a.quick, out, lg, a.colors, a.dither, grid=(32, 32, 48))
        else:
            bake(nm, a.seed, a.quick, out, lg, a.colors, a.dither)
    print("done", flush=True)
