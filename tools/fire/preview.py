"""
preview.py - compose preview sheets from the baked atlases in assets/fire.

    python tools/fire/preview.py                                  # docs/fire_preview_sheet.png (overview, one row per type)
    python tools/fire/preview.py --detail campfire,pool --out docs/fire_preview_detail_a.png   (two rows per type, larger)
    python tools/fire/preview.py --dir _fire_tmp --types campfire --out _fire_tmp/sheet.png

Overview row cells: dark background x4, daylight grey x4, heat map x1. The cells follow the type's own clips
(life: loop, ignite, growth, decay, extinguish; blast: fireball, plume, residue; tile/carried: loops; shot: the one-shots).
"""
import argparse, json, os
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DARK, GREY = 0.012, 0.40


def dec(x):
    return np.power(np.clip(x, 0, 1), 2.2)


def enc(x):
    return np.power(np.clip(x, 0, 1), 1 / 2.2)


class Atlas:
    def __init__(self, d, name, info):
        self.d, self.name, self.info = d, name, info
        self.img = {}

    def layer(self, lay):
        if lay not in self.img:
            L = self.info["layers"][lay]
            im = Image.open(os.path.join(self.d, L["file"]))
            im = im.convert("RGBA" if lay != "heat" else "L")
            self.img[lay] = (np.asarray(im).astype(np.float32) / 255.0, L)
        return self.img[lay]

    def frame(self, lay, idx):
        a, L = self.layer(lay)
        fw, fh = L["frame_px"]
        r, c = divmod(idx, L["cols"])
        return a[r * fh:(r + 1) * fh, c * fw:(c + 1) * fw]


def clip_frame(at, clip, lay, frac):
    c = clip.get(lay)
    if c is None:
        return None
    i = int(round(np.clip(frac, 0, 1) * (c["count"] - 1)))
    return at.frame(lay, c["first"] + i)


def resize(img, s):
    h, w = img.shape[:2]
    nh, nw = max(1, int(round(h * s))), max(1, int(round(w * s)))
    if img.ndim == 2:
        return np.asarray(Image.fromarray(img).resize((nw, nh), Image.BILINEAR))
    return np.stack([np.asarray(Image.fromarray(img[..., k]).resize((nw, nh), Image.BILINEAR)) for k in range(img.shape[2])], -1)


def place(canvas, sprite, anchor, gx, gy, s):
    sp = resize(sprite, s)
    h, w = sp.shape[:2]
    x0 = int(round(gx - anchor[0] * w))
    y0 = int(round(gy - anchor[1] * h))
    H, W = canvas.shape[:2]
    cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if cx1 <= cx0 or cy1 <= cy0:
        return None
    return (slice(cy0, cy1), slice(cx0, cx1)), sp[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]


def cell_geom(info, hpx):
    L = info["layers"]
    sizes = [L[k]["size_m"] for k in ("flame", "smoke") if k in L]
    hm = max(s[1] for s in sizes)
    wm = max(s[0] for s in sizes)
    pxm = hpx / hm
    return pxm, int(np.ceil(wm * pxm)) + 8, hpx + 4


def ground(info, cw, ch):
    carried = info["kind"] == "carried"
    return (cw * (0.18 if carried else 0.5), ch * (0.55 if carried else 0.985))


def compose(at, clip, frac, bg, pxm, cw, ch, with_flame=True, with_smoke=True):
    info = at.info
    L = info["layers"]
    canvas = np.ones((ch, cw, 3), np.float32) * bg
    gx, gy = ground(info, cw, ch)
    if with_smoke and "smoke" in clip:
        f = clip_frame(at, clip, "smoke", frac)
        pl = place(canvas, f, L["smoke"]["anchor"], gx, gy, L["smoke"]["m_per_px"] * pxm)
        if pl:
            sl, sp = pl
            a = sp[..., 3:4]
            canvas[sl] = dec(sp[..., :3]) * a + canvas[sl] * (1 - a)
    if with_flame and "flame" in clip and "flame" in L:
        f = clip_frame(at, clip, "flame", frac)
        pl = place(canvas, f, L["flame"]["anchor"], gx, gy, L["flame"]["m_per_px"] * pxm)
        if pl:
            sl, sp = pl
            a = sp[..., 3:4]          # straight alpha, linear
            canvas[sl] = dec(sp[..., :3]) * a + canvas[sl] * (1 - a)
    return enc(canvas)


def inferno(v):
    stops = np.array([[0, 0, 0.02], [0.2, 0.05, 0.35], [0.55, 0.1, 0.4], [0.85, 0.3, 0.2], [0.98, 0.65, 0.05], [0.99, 0.95, 0.6]])
    x = np.clip(v, 0, 1) * (len(stops) - 1)
    i = np.minimum(x.astype(int), len(stops) - 2)
    f = (x - i)[..., None]
    return stops[i] * (1 - f) + stops[i + 1] * f


def heat_cell(at, clip, frac, pxm, cw, ch):
    info = at.info
    L = info["layers"]["heat"]
    f = clip_frame(at, clip, "heat", frac)
    rgb = inferno(f)
    rgba = np.concatenate([rgb, np.ones(f.shape + (1,), np.float32)], -1)
    canvas = np.zeros((ch, cw, 3), np.float32) + np.array([0, 0, 0.02], np.float32)
    gx, gy = ground(info, cw, ch)
    pl = place(canvas, rgba, L["anchor"], gx, gy, L["m_per_px"] * pxm)
    if pl:
        sl, sp = pl
        canvas[sl] = sp[..., :3]
    return canvas


def specs(info):
    clips = {c["name"]: c for c in info["clips"]}
    k = info["kind"]

    def pick(*pairs):
        return [(clips[n], f) for n, f in pairs if n in clips]
    if k == "life":
        return pick(("loop_a", 0.0), ("loop_a", 0.5), ("ignite", 0.9), ("growth", 0.5), ("loop_b", 0.25), ("loop_c", 0.6), ("decay", 0.35), ("extinguish", 0.5))
    if k in ("tile", "carried"):
        return pick(("loop_a", 0.0), ("loop_a", 0.5), ("loop_b", 0.25), ("loop_b", 0.75), ("loop_c", 0.0), ("loop_c", 0.5))
    if k == "blast":
        return pick(("fireball_a", 0.05), ("fireball_a", 0.25), ("fireball_a", 0.6), ("fireball_a", 1.0), ("plume_a", 0.4), ("plume_a", 1.0), ("residue_a", 0.5), ("fireball_b", 0.5))
    return [(c, f) for c in info["clips"] for f in (0.3, 0.7)]


def type_rows(at, hpx, detail=False):
    info = at.info
    sp = specs(info)
    pxm, cw, ch = cell_geom(info, hpx)
    cells_dark = [compose(at, c, f, DARK, pxm, cw, ch) for c, f in sp]
    cells_grey = [compose(at, c, f, GREY, pxm, cw, ch) for c, f in sp]
    heat = heat_cell(at, sp[min(1, len(sp) - 1)][0], 0.5, pxm, cw, ch)
    if detail:
        smk = [compose(at, c, f, GREY, pxm, cw, ch, with_flame=False) for c, f in sp[:4]]
        r3 = np.concatenate(smk + [heat], 1)
        r3 = np.pad(r3, ((0, 0), (0, cells_dark[0].shape[1] * len(cells_dark) - r3.shape[1]), (0, 0)), constant_values=0.02)
        return [np.concatenate(cells_dark, 1), np.concatenate(cells_grey, 1), r3]
    n = min(3, len(sp))
    return [np.concatenate(cells_dark[:n] + cells_grey[:n] + [heat], 1)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "assets", "fire"))
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "fire_preview_sheet.png"))
    ap.add_argument("--types", default=None, help="comma list (default: every baked type)")
    ap.add_argument("--detail", default=None, help="comma list: three-row detail sheet with bigger cells")
    ap.add_argument("--hpx", type=int, default=0)
    a = ap.parse_args()
    data = json.load(open(os.path.join(a.dir, "fire_atlas.json")))["presets"]
    names = (a.detail or a.types or ",".join(data)).split(",")
    names = [n for n in names if n in data]
    detail = bool(a.detail)
    hpx = a.hpx or (200 if detail else 104)
    blocks = []
    for n in names:
        rows = type_rows(Atlas(a.dir, n, data[n]), hpx, detail)
        img = Image.fromarray((np.clip(np.concatenate(rows, 0), 0, 1) * 255).astype(np.uint8))
        lab = Image.new("RGB", (img.width, img.height + 16), (24, 24, 28))
        lab.paste(img, (0, 16))
        d = data[n]
        ImageDraw.Draw(lab).text((4, 2), f"{n}: {d['title']} | {d['size_note']} | domain {d['domain_m'][0]} x {d['domain_m'][1]} x {d['domain_m'][2]} m", fill=(235, 235, 235))
        if not detail and lab.width > 1000:
            lab = lab.resize((1000, int(lab.height * 1000 / lab.width)), Image.LANCZOS)
        blocks.append(lab)
    cwid = max(b.width for b in blocks)
    rh = max(b.height for b in blocks)
    ncol = (2 if detail else 3) if len(blocks) > 1 else 1
    nrow = (len(blocks) + ncol - 1) // ncol
    sh = Image.new("RGB", (ncol * (cwid + 8) + 8, nrow * (rh + 4) + 8), (24, 24, 28))
    for i, b in enumerate(blocks):
        r, c = (i % nrow, i // nrow) if not detail else (i // ncol, i % ncol)
        sh.paste(b, (8 + c * (cwid + 8), 8 + r * (rh + 4)))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sh.save(a.out, optimize=True)
    print("sheet", a.out, sh.size)


if __name__ == "__main__":
    main()
