"""
render.py - turns an extinction-coefficient volume (1/m) into sprite layers.

Volumes are V[z (top first), y, x]. The view is orthographic along y (like tools/fire/bake.py). Output per frame:
  alpha    1 - exp(-tau), tau = integral of sigma along the view ray (straight alpha)
  lum      grey shading: ambient + sun term attenuated by the optical depth above (light from above and the left)
  scatter  forward-scatter highlight: strongest where the cloud is thin (tau about 1), weak in thick cores
  heat     max temperature excess along the ray (steam only)
The shading is a cheap single-scatter style approximation, not true radiative transfer.
"""
import numpy as np
from scipy import ndimage as ndi


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def make_noise(shape, seed, scales=((7, 3.5, 6), (3.5, 1.8, 3), (1.8, 0.9, 1.5)), weights=(1.0, 0.7, 0.45), per_x=False, per_z=True):
    """smooth multi-octave noise, shape (P, D, W) with wrap in z (always) and x (optional)"""
    rng = np.random.default_rng(seed)
    out = 0
    mode = ("wrap" if per_z else "nearest", "nearest", "wrap" if per_x else "nearest")
    for sig, wgt in zip(scales, weights):
        r = rng.standard_normal(shape).astype(np.float32)
        r = ndi.gaussian_filter(r, sig, mode=mode)
        r /= r.std() + 1e-6
        out = out + wgt * r
    out /= out.std()
    return out.astype(np.float32)


def take_z(base, H, shift):
    """noise rolled in z by `shift` px, tiled to height H (seamless for any shift because base has period P in z)"""
    P = base.shape[0]
    return base[(np.arange(H) + int(shift)) % P]


def window3d(nx, ny, nz, periodic, top=(0.52, 0.98), bottom=None, xw=0.2, yw=0.25, skew=None):
    x = (np.arange(nx) + 0.5) / nx
    y = (np.arange(ny) + 0.5) / ny
    z = (np.arange(nz) + 0.5) / nz
    wx = np.ones(nx) if periodic else smoothstep(0.0, xw, np.minimum(x, 1 - x))
    if skew:   # carried: head near the left edge, tail to the right
        wx = smoothstep(0.0, skew[0], x) * smoothstep(0.0, skew[1], 1 - x)
    wy = smoothstep(0.0, yw, np.minimum(y, 1 - y))
    wz = 1.0 - smoothstep(top[0], top[1], z)
    if bottom:
        wz = wz * smoothstep(0.0, bottom, z)
    return (wx[:, None, None] * wy[None, :, None] * wz[None, None, :]).astype(np.float32)


def upvol(f, win, up_x, up_z, periodic, soft=0.5):
    """sim field (nx, ny, nz) -> V[z (top first), y, x] upsampled by up_x, up_z in x and z, smooth"""
    v = np.transpose(f.astype(np.float32) * win, (2, 1, 0))[::-1]
    v = np.repeat(np.repeat(v, up_z, axis=0), up_x, axis=2)
    return ndi.gaussian_filter(v, (up_z * soft, 0, up_x * soft), mode=("nearest", "nearest", "wrap" if periodic else "nearest"))


def warp2d(img, dn, amp, periodic):
    H, W = img.shape[:2]
    pad = 4 if periodic else 0
    if periodic:
        img = np.pad(img, ((0, 0), (pad, pad)) + ((0, 0),) * (img.ndim - 2), mode="wrap")
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dy = amp * dn[0][:H, :W]
    dx = amp * dn[1][:H, :W]
    coords = np.stack([np.clip(yy + dy, 0, H - 1), np.clip(xx + dx + pad, 0, W + 2 * pad - 1)])
    if img.ndim == 2:
        return ndi.map_coordinates(img, coords, order=1, mode="nearest")
    return np.stack([ndi.map_coordinates(img[..., c], coords, order=1, mode="nearest") for c in range(img.shape[2])], -1)


def project(sig, dy, dz, look, light_dir=(-0.45, -0.89)):
    """sig V[z,y,x] (1/m) -> dict(alpha, lum, scatter, tau). dy, dz: metres per voxel along y and z."""
    k = look
    tau_v = (sig * dy).astype(np.float32)
    cum_y = np.cumsum(tau_v, axis=1) - tau_v
    contrib = (1.0 - np.exp(-tau_v)) * np.exp(-cum_y)
    # sun from above: optical depth of the column above each voxel (top-first arrays => cumsum along z)
    tz = np.cumsum(sig * dz, axis=0) - sig * dz
    light = np.exp(-k["ks"] * tz)
    lum_v = k["amb"] + (1.0 - k["amb"]) * light
    alpha = contrib.sum(1)
    lum = (contrib * lum_v).sum(1) / np.maximum(alpha, 1e-5)
    tau = tau_v.sum(1)
    # bump shading from the silhouette gradient (billow edges facing the light are brighter)
    kb = k.get("bump", 0.0)
    if kb > 0:
        sm = ndi.gaussian_filter(tau, k.get("bump_sig", 1.6), mode="nearest")
        gz, gx = np.gradient(sm)
        g = (light_dir[0] * (-gx) + light_dir[1] * (-gz)) * k.get("bump_gain", 1.0)
        lum = lum + kb * np.tanh(g * 3.0) * np.clip(alpha * 2, 0, 1)
    lum = np.clip(lum, 0, 1)
    scat = np.clip(k.get("sc_gain", 1.8) * (1 - np.exp(-tau)) * np.exp(-k.get("sc_kap", 0.55) * tau), 0, 1)
    return dict(alpha=np.clip(alpha, 0, 1).astype(np.float32), lum=lum.astype(np.float32), scatter=scat.astype(np.float32), tau=tau)


# ---------------------------------------------------------------------------------------------
def srgb(x):
    return np.power(np.clip(x, 0, 1), 1 / 2.2)


def to8(x, dither=None):
    x = np.asarray(x, np.float32) * 255.0
    if dither is not None:
        x = x + dither
    return np.clip(np.round(x), 0, 255).astype(np.uint8)


def bbox(frames, thr, margin, mult=2, periodic=False, free=True):
    H, W = frames[0].shape[:2]
    any_ = np.zeros((H, W), bool)
    for f in frames:
        any_ |= f > thr
    ys = np.where(any_.any(axis=1))[0]
    xs = np.where(any_.any(axis=0))[0]
    if len(ys) == 0:
        return 0, W, 0, H
    x0, x1 = max(0, xs.min() - margin), min(W, xs.max() + 1 + margin)
    y0, y1 = max(0, ys.min() - margin), min(H, ys.max() + 1 + margin)
    if periodic:
        x0, x1 = 0, W
    x1 = x0 + int(np.ceil((x1 - x0) / mult) * mult)
    y1 = y0 + int(np.ceil((y1 - y0) / mult) * mult)
    return x0, min(x1, W), y0, min(y1, H)


def atlas_cols(n, fw, fh, target_w=2048):
    c = int(max(1, min(n, round(np.sqrt(n * fh / fw)))))
    if fw * c > target_w:
        c = max(1, target_w // fw)
    return c


def make_atlas(frames, cols):
    n = len(frames)
    h, w = frames[0].shape[:2]
    ch = frames[0].shape[2] if frames[0].ndim == 3 else 1
    rows = (n + cols - 1) // cols
    at = np.zeros((rows * h, cols * w, ch), np.uint8)
    for i, im in enumerate(frames):
        r, c = divmod(i, cols)
        at[r * h:(r + 1) * h, c * w:(c + 1) * w] = im.reshape(h, w, ch)
    return at, rows


def resize_u8(f, scale, box=True):
    from PIL import Image
    h, w = f.shape[:2]
    nh, nw = max(2, int(round(h * scale / 2) * 2)), max(2, int(round(w * scale / 2) * 2))
    ch = f.shape[2] if f.ndim == 3 else 1
    ff = f.reshape(h, w, ch)
    out = np.stack([np.asarray(Image.fromarray(ff[..., c]).resize((nw, nh), Image.BOX if box else Image.BILINEAR)) for c in range(ch)], -1)
    return out


def shape_density(V, n, look):
    """cloud-style erosion: irregular, wispy boundaries from a noise field, billow lumps from the same field at low weight.
    V: extinction (1/m); n: noise (unit std). Returns the visual extinction (1/m)."""
    vref = look["vref"]
    b = V / vref
    n01 = 0.5 + 0.5 * np.tanh(n * 0.75)
    e = look["erode"]
    d = np.clip((b - e * n01) / (1.0 - e * n01 + 1e-3), 0.0, 3.0)
    d = d * (1.0 + look.get("lump", 0.0) * n)
    return np.maximum(d, 0) * vref * look.get("gain", 1.0)
