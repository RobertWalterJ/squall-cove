"""
preview.py - compose docs/fire_preview_sheet.png (+ docs/fire_preview.gif) from the baked atlases.

    python tools/fire/preview.py                       # reads assets/fire, writes docs/
    python tools/fire/preview.py --dir _fire_tmp --out _fire_tmp/sheet.png --presets campfire
"""
import argparse, json, os
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CW, CH = 128, 192          # canvas = the full sim domain at flame resolution (px)
DARK = (0.012, 0.015, 0.02)
GREY = (0.40, 0.44, 0.48)  # linear value of a daylight-ish sky grey (about sRGB 0.67)
ORDER = ["campfire", "gas", "pool", "vehicle", "building"]


def dec(x):
    return np.power(x, 2.2)


def enc(x):
    return np.power(np.clip(x, 0, 1), 1 / 2.2)


def load_atlas(path, info, mode):
    im = Image.open(path)
    if im.mode == "P":
        im = im.convert("RGBA")
    a = np.asarray(im).astype(np.float32) / 255.0
    if a.ndim == 2:
        a = a[..., None]
    cols, rows = info["grid"]
    fw, fh = info["frame_px"]
    out = []
    for i in range(info["frames"]):
        r, c = divmod(i, cols)
        out.append(a[r * fh:(r + 1) * fh, c * fw:(c + 1) * fw])
    return out


def to_canvas(img, m_ratio):
    """paste a bottom-centre anchored sprite (H,W,C) onto the domain canvas after scaling by m_ratio"""
    h, w, c = img.shape
    if abs(m_ratio - 1) > 1e-3:
        chans = [np.asarray(Image.fromarray(img[..., k]).resize((max(1, int(round(w * m_ratio))), max(1, int(round(h * m_ratio)))), Image.BILINEAR)) for k in range(c)]
        img = np.stack(chans, -1)
        h, w, c = img.shape
    cv = np.zeros((CH, CW, c), np.float32)
    x0 = CW // 2 - w // 2
    xs0, xs1 = max(0, x0), min(CW, x0 + w)
    ys0 = max(0, CH - h)
    cv[ys0:CH, xs0:xs1] = img[h - (CH - ys0):, xs0 - x0:xs1 - x0]
    return cv


def inferno(v):
    stops = np.array([[0, 0, 0.02], [0.2, 0.05, 0.35], [0.55, 0.1, 0.4], [0.85, 0.3, 0.2], [0.98, 0.65, 0.05], [0.99, 0.95, 0.6]])
    x = np.clip(v, 0, 1) * (len(stops) - 1)
    i = np.minimum(x.astype(int), len(stops) - 2)
    f = (x - i)[..., None]
    return stops[i] * (1 - f) + stops[i + 1] * f


def frames_for(d, name, picks):
    atl = json.load(open(os.path.join(d, "fire_atlas.json")))["presets"][name]
    fl = load_atlas(os.path.join(d, atl["flame"]["file"]), dict(atl["flame"], grid=atl["grid"], frames=atl["frames"]), "rgba")
    sm = load_atlas(os.path.join(d, atl["smoke"]["file"]), dict(atl["smoke"], grid=atl["grid"], frames=atl["frames"]), "la")
    ht = load_atlas(os.path.join(d, atl["heat"]["file"]), dict(atl["heat"], grid=atl["grid"], frames=atl["frames"]), "l")
    mf = atl["flame"]["m_per_px"]
    out = []
    for i in picks(atl["frames"]):
        f = to_canvas(fl[i], 1.0)
        s = to_canvas(sm[i], atl["smoke"]["m_per_px"] / mf)
        h = to_canvas(ht[i], atl["heat"]["m_per_px"] / mf)
        out.append((f, s, h))
    return out


def composite(f, s, bg):
    base = np.ones((CH, CW, 3), np.float32) * np.array(bg, np.float32)
    sa = s[..., 1:2]
    base = dec(s[..., 0:1]) * sa + base * (1 - sa)
    fa = dec(f[..., 3:4])
    return enc(dec(f[..., :3]) + base * (1 - fa))


def render_row(items, kind, bg=None):
    tiles = []
    for f, s, h in items:
        if kind == "comp":
            t = composite(f, s, bg)
        elif kind == "smoke":
            t = composite(np.zeros_like(f), s, GREY)
        else:
            t = inferno(np.power(h[..., 0], 1.0))
        tiles.append(t)
    return np.concatenate(tiles, axis=1)


def sheet(d, out, presets, gif=None):
    picks = lambda n: [int(round(k * (n - 1) / 5)) for k in range(6)] if n > 6 else list(range(min(6, n)))
    blocks = []
    for nm in presets:
        items = frames_for(d, nm, picks)
        rows = [render_row(items, "comp", DARK), render_row(items, "comp", GREY), render_row(items, "smoke"), render_row(items, "heat")]
        blk = np.concatenate(rows, axis=0)
        img = Image.fromarray((np.clip(blk, 0, 1) * 255).astype(np.uint8))
        canvas = Image.new("RGB", (img.width, img.height + 20), (24, 24, 28))
        canvas.paste(img, (0, 20))
        ImageDraw.Draw(canvas).text((6, 4), f"{nm}  |  rows: flame+smoke on dark, on daylight grey, smoke only, heat", fill=(235, 235, 235))
        blocks.append(canvas)
    w, h = blocks[0].size
    ncol = 2 if len(blocks) > 1 else 1
    nrow = (len(blocks) + ncol - 1) // ncol
    sh = Image.new("RGB", (ncol * (w + 10) + 10, nrow * (h + 10) + 10), (24, 24, 28))
    for i, b in enumerate(blocks):
        r, c = divmod(i, ncol)
        sh.paste(b, (10 + c * (w + 10), 10 + r * (h + 10)))
    sh.save(out, optimize=True)
    print("sheet", out, sh.size)
    if gif:
        allf = {nm: frames_for(d, nm, lambda n: list(range(n))) for nm in presets}
        n = min(len(v) for v in allf.values())
        ims = []
        for i in range(0, n, 1):
            top = np.concatenate([composite(allf[nm][i][0], allf[nm][i][1], DARK) for nm in presets], axis=1)
            bot = np.concatenate([composite(allf[nm][i][0], allf[nm][i][1], GREY) for nm in presets], axis=1)
            im = Image.fromarray((np.clip(np.concatenate([top, bot], 0), 0, 1) * 255).astype(np.uint8))
            ims.append(im.resize((int(im.width * 0.8), int(im.height * 0.8)), Image.LANCZOS))
        ims[0].save(gif, save_all=True, append_images=ims[1:], duration=int(1000 / 24), loop=0, optimize=True)
        print("gif", gif, os.path.getsize(gif) // 1024, "KB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "assets", "fire"))
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "fire_preview_sheet.png"))
    ap.add_argument("--gif", default=None)
    ap.add_argument("--presets", nargs="*", default=ORDER)
    a = ap.parse_args()
    sheet(a.dir, a.out, a.presets, a.gif)
