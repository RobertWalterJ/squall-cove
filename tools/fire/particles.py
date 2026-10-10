"""
particles.py - procedural (no simulation) small sprites: embers, sparks, burning droplets, ember streaks, ash flakes, and a
smouldering ground strip. Everything is drawn analytically with numpy, so it is tiny and exactly repeatable.

    python tools/fire/particles.py          # writes assets/fire/fire_particles_*.webp, fire_burnt_strip.webp, merges "particles" into fire_atlas.json

Conventions:
  * dot sprites (ember, spark, droplet, ash) are 32x32 px, straight-alpha RGBA (sRGB colour, linear alpha), head at the anchor.
  * streak sprites are 64x16 px with the HEAD at the left (anchor x 0.12) and the tail towards +x (rotate so +x points against the velocity).
  * spark / droplet frames are drawn with the tail pointing DOWN (-y), i.e. for a particle that moves up; rotate to the velocity.
"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from bake import planck_rgb  # noqa: E402


def heat_rgb(h):
    """0 (dark ember) .. 1 (white-hot) colour"""
    h = np.clip(h, 0, 1)
    tc = 800.0 + 2200.0 * h
    c = planck_rgb(tc)
    return c * (0.25 + 0.75 * h)[..., None]


def enc(x):
    return np.power(np.clip(x, 0, 1), 1 / 2.2)


def to8(x):
    return np.clip(np.round(x * 255), 0, 255).astype(np.uint8)


def finish(rgb, a):
    """linear premultiplied rgb + alpha -> sRGB uint8 RGBA, STRAIGHT alpha (colour = rgb / alpha, alpha linear)"""
    a = np.clip(a, 0, 1)
    rgb = np.minimum(rgb, a[..., None])
    straight = np.where(a[..., None] > 1e-4, rgb / np.maximum(a[..., None], 1e-4), 0.0)
    return to8(np.concatenate([enc(straight), a[..., None]], -1))


def yy_xx(h, w):
    return np.mgrid[0:h, 0:w].astype(np.float32)


def ember(var, i, n=16, S=32):
    rng = np.random.default_rng(100 + var)
    t = i / (n - 1)
    cx, cy = S / 2 + rng.uniform(-0.6, 0.6), S / 2 + rng.uniform(-0.6, 0.6)
    r0 = 3.4 + 0.8 * var
    flick = 1.0 + 0.18 * np.sin(2 * np.pi * (i / n) * (1 + var % 2) + var)
    yy, xx = yy_xx(S, S)
    d = np.hypot(xx - cx, yy - cy)
    heat = (1 - t) ** 1.3 * flick
    r = r0 * (0.9 + 0.2 * (1 - t))
    core = np.exp(-(d / r) ** 2)
    halo = np.exp(-(d / (r * 2.6)) ** 2) * 0.35
    a = np.clip((core + halo) * (0.25 + 0.75 * heat) , 0, 1)
    col = heat_rgb(np.clip(heat * core + 0.25 * halo, 0, 1) * 1.1)
    return finish(col * a[..., None] / np.maximum(a.max(), 1e-3) * 1.0, a)


def spark(var, i, n=10, S=32):
    rng = np.random.default_rng(200 + var)
    t = i / (n - 1)
    cx = S / 2 + rng.uniform(-0.5, 0.5)
    head = S * 0.22
    L = (12 + 3 * var) * (1 - 0.6 * t)           # the streak shortens as it cools
    yy, xx = yy_xx(S, S)
    # tail runs downward from the head
    s = (yy - head)
    along = np.clip(s / max(L, 1e-3), 0, 1.5)
    inside = (s >= -1.5) & (s <= L)
    w = 0.9 + 0.5 * (1 - along)
    prof = np.exp(-((xx - cx) / w) ** 2) * np.exp(-3.2 * along ** 1.3) * inside
    head_g = np.exp(-(((xx - cx) ** 2 + (yy - head) ** 2) / 2.2))
    a = np.clip(prof + 1.2 * head_g, 0, 1) * (1 - 0.8 * t ** 2)
    heat = np.clip((1 - t) * (0.55 + 0.45 * np.exp(-2 * along)) + 0.2 * head_g, 0, 1)
    return finish(heat_rgb(heat) * a[..., None], a)


def droplet(var, i, n=12, S=32):
    rng = np.random.default_rng(300 + var)
    t = i / (n - 1)
    cx, head = S / 2, S * 0.28
    yy, xx = yy_xx(S, S)
    L = 11 + 2 * var
    s = yy - head
    along = np.clip(s / L, 0, 1.4)
    flick = 1 + 0.25 * np.sin(2 * np.pi * (i / n) * 2 + var) * np.exp(-along)
    wid = (1.7 + 2.4 * along) * (1 - 0.15 * np.sin(2 * np.pi * i / n + var))
    tail = np.exp(-((xx - cx - 0.8 * np.sin(2 * np.pi * (i / n) + along * 5 + var) * along) / wid) ** 2) * np.exp(-2.2 * along ** 1.2) * (s > -2)
    head_g = np.exp(-(((xx - cx) ** 2 + (yy - head) ** 2) / 4.0))
    a = np.clip(tail * 0.9 * flick + 1.2 * head_g, 0, 1) * (1 - 0.35 * t)
    heat = np.clip(0.95 * head_g + 0.75 * tail * np.exp(-1.5 * along), 0, 1) * (1 - 0.25 * t)
    col = heat_rgb(heat) * np.array([1.0, 0.93, 0.8], np.float32)
    return finish(col * a[..., None], a)


def streak(speed, i, n=8, W=64, H=16):
    t = i / (n - 1)
    L = {"slow": 14, "med": 30, "fast": 56}[speed] * (1 - 0.5 * t)
    yy, xx = yy_xx(H, W)
    hx, hy = 7.0, H / 2
    s = xx - hx
    along = np.clip(s / L, 0, 1.5)
    prof = np.exp(-((yy - hy) / (0.9 + 0.8 * (1 - along))) ** 2) * np.exp(-3.0 * along ** 1.2) * (s >= -1)
    head_g = np.exp(-(((xx - hx) ** 2 + (yy - hy) ** 2) / 3.0))
    a = np.clip(prof + 1.1 * head_g, 0, 1) * (1 - 0.6 * t)
    heat = np.clip((1 - 0.7 * t) * (0.5 + 0.5 * np.exp(-2.2 * along)) + 0.25 * head_g, 0, 1)
    return finish(heat_rgb(heat) * a[..., None], a)


def ash(var, i, n=12, S=32):
    rng = np.random.default_rng(400 + var)
    yy, xx = yy_xx(S, S)
    ang = 2 * np.pi * (i / n) + var
    cx, cy = S / 2, S / 2
    u = (xx - cx) * np.cos(ang) + (yy - cy) * np.sin(ang)
    v = -(xx - cx) * np.sin(ang) + (yy - cy) * np.cos(ang)
    sq = 0.35 + 0.65 * abs(np.cos(ang * 0.7 + var))   # tumble: flake foreshortens
    a = np.clip(1.6 - np.hypot(u / 5.5, v / (3.2 * sq + 0.4)) * 1.2, 0, 1)
    g = 0.10 + 0.08 * np.sin(ang * 2 + var) + 0.05 * rng.standard_normal()
    out = np.zeros((S, S, 4), np.uint8)
    out[..., :3] = to8(enc(np.full((S, S, 3), np.clip(g, 0.03, 0.3)) * a[..., None]))
    out[..., 3] = to8(a)
    return out


def burnt_strip(n=16, W=128, H=64):
    """Top-down smouldering ground, tileable in both directions; embers glow and breathe (loops over n frames)."""
    rng = np.random.default_rng(7)
    def nz(sig, s):
        r = ndi.gaussian_filter(np.random.default_rng(s).standard_normal((H, W)), sig, mode="wrap")
        return (r / r.std()).astype(np.float32)
    base = 0.55 * nz(2.5, 1) + 0.35 * nz(1.2, 2) + 0.2 * nz(0.6, 3)
    ash_ = np.clip(0.5 + 0.5 * nz(5.0, 4), 0, 1)
    emb = nz(1.6, 5)
    phase = nz(3.0, 6) * 2.0
    frames = []
    for i in range(n):
        br = 0.5 + 0.5 * np.sin(2 * np.pi * i / n + phase)
        glow = np.clip((emb - 1.15) * 1.6, 0, 1) * (0.35 + 0.65 * br)
        char = np.clip(0.045 + 0.02 * base + 0.06 * ash_ * (base > 0.2), 0.01, 0.2)
        rgb = char[..., None] * np.array([1.0, 1.0, 1.02], np.float32)
        rgb = rgb + glow[..., None] * heat_rgb(0.25 + 0.5 * glow)
        frames.append(to8(enc(np.clip(rgb, 0, 1))))
    return frames


def pack(frames, cols):
    n = len(frames)
    h, w, c = frames[0].shape
    rows = (n + cols - 1) // cols
    at = np.zeros((rows * h, cols * w, c), np.uint8)
    for i, f in enumerate(frames):
        r, cc = divmod(i, cols)
        at[r * h:(r + 1) * h, cc * w:(cc + 1) * w] = f
    return at, rows


def main(outdir=None):
    outdir = outdir or os.path.join(ROOT, "assets", "fire")
    os.makedirs(outdir, exist_ok=True)
    dots, clips = [], []

    def addclip(name, kind, frames, fps, loop, anchor):
        clips.append(dict(name=name, kind=kind, first=len(dots), count=len(frames), fps=fps, loop=loop, duration_s=round(len(frames) / fps, 3), anchor=anchor))
        dots.extend(frames)
    for v in range(4):
        addclip(f"ember_{'abcd'[v]}", "ember", [ember(v, i) for i in range(16)], 12, False, [0.5, 0.5])
    for v in range(4):
        addclip(f"spark_{'abcd'[v]}", "spark", [spark(v, i) for i in range(10)], 24, False, [0.5, 0.22])
    for v in range(3):
        addclip(f"droplet_{'abc'[v]}", "droplet", [droplet(v, i) for i in range(12)], 24, True, [0.5, 0.28])
    for v in range(2):
        addclip(f"ash_{'ab'[v]}", "ash", [ash(v, i) for i in range(12)], 12, True, [0.5, 0.5])
    cols = 16
    at, rows = pack(dots, cols)
    p = os.path.join(outdir, "fire_particles_dots.webp")
    Image.fromarray(at, "RGBA").save(p, "WEBP", lossless=True, method=6, exact=True)
    d_info = dict(file="fire_particles_dots.webp", frame_px=[32, 32], cols=cols, rows=rows, bytes=os.path.getsize(p), clips=clips,
                  blend="straight alpha: normal, or additive (SRC_ALPHA, ONE); ash is normal blend (dark)", note="spark and droplet frames have the tail pointing down; rotate to the velocity")
    streaks, sclips = [], []
    for sp in ("slow", "med", "fast"):
        sclips.append(dict(name=f"ember_streak_{sp}", first=len(streaks), count=8, fps=24, loop=False, duration_s=round(8 / 24, 3), anchor=[7 / 64, 0.5]))
        streaks.extend(streak(sp, i) for i in range(8))
    at, rows = pack(streaks, 8)
    p = os.path.join(outdir, "fire_particles_streaks.webp")
    Image.fromarray(at, "RGBA").save(p, "WEBP", lossless=True, method=6, exact=True)
    s_info = dict(file="fire_particles_streaks.webp", frame_px=[64, 16], cols=8, rows=rows, bytes=os.path.getsize(p), clips=sclips,
                  note="head at the left, tail towards +x; rotate so +x points against the velocity", blend="straight alpha: normal or additive (SRC_ALPHA, ONE)")
    bs = burnt_strip()
    at, rows = pack(bs, 4)
    p = os.path.join(outdir, "fire_burnt_strip.webp")
    Image.fromarray(at, "RGB").save(p, "WEBP", quality=72, method=5)
    b_info = dict(file="fire_burnt_strip.webp", frame_px=[128, 64], cols=4, rows=rows, frames=16, fps=6, loop=True, bytes=os.path.getsize(p),
                  size_m=[2.0, 1.0], note="top-down ground decal, opaque, tileable in both directions; embers breathe over the 16-frame loop; lay it behind a fire front")
    ap = os.path.join(outdir, "fire_atlas.json")
    data = json.load(open(ap)) if os.path.exists(ap) else {"version": 2, "presets": {}}
    data["particles"] = dict(dots=d_info, streaks=s_info, burnt_strip=b_info)
    json.dump(data, open(ap, "w"), separators=(",", ":"))
    print("particles:", d_info["bytes"] // 1024, "KB dots,", s_info["bytes"] // 1024, "KB streaks,", b_info["bytes"] // 1024, "KB strip")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
