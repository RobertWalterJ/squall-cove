"""
preview.py - docs/atmos_preview_sheet.png: 6 frames per preset on a dark and a grey-day background (plus a backlit row with scatter).

    python tools/atmos/preview.py [--dir assets/atmos] [--out docs/atmos_preview_sheet.png] [--presets a b] [--family steam]
"""
import argparse, json, os
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DARK = (10, 12, 18)
GREY = (150, 164, 178)
BRIGHT = (250, 238, 205)
CELLW = 250


def load_frames(d, info, key="main"):
    lay = info["layers"][key]
    im = Image.open(os.path.join(d, lay["file"])).convert("RGBA" if key == "main" else "RGB")
    a = np.asarray(im)
    fw, fh = lay["frame_px"]
    out = []
    for i in range(sum(c["count"] for c in info["clips"])):
        r, c = divmod(i, lay["cols"])
        out.append(a[r * fh:(r + 1) * fh, c * fw:(c + 1) * fw])
    return out


def picks(info):
    """6 frames: lifecycle spread (steam/mist: start, early loop, mid loop, late loop, fade; fog: form, drift, drift, linger, thin, fall)"""
    first = {}
    i = 0
    for c in info["clips"]:
        first[c["name"]] = (c["first"], c["count"])
    cl = info["clips"]
    names = [c["name"] for c in cl]
    sel = []
    if "form" in first:
        for nm, f in (("form", 0.6), ("drift_a", 0.3), ("drift_b", 0.6), ("linger", 0.5), ("thin", 0.6), ("fall", 0.9)):
            a, n = first[nm]
            sel.append(a + int(f * (n - 1)))
        return sel
    loops = [c for c in cl if c["loop"]]
    non = [c for c in cl if not c["loop"]]
    if non and non[0]["stage"] == "start":
        sel.append(non[0]["first"] + non[0]["count"] // 2)
    for c, f in zip(loops[:4], (0.2, 0.5, 0.3, 0.7)):
        sel.append(c["first"] + int(f * (c["count"] - 1)))
    if non and non[-1]["stage"] == "fade":
        sel.append(non[-1]["first"] + non[-1]["count"] // 2)
    if not sel or info["kind"] in ("shot", "blobs"):
        n = sum(c["count"] for c in cl)
        sel = [int(k * (n - 1) / 5) for k in range(6)]
    return (sel + sel)[:6]


def comp(main, scat, bg, back=0.0):
    rgb = (main[..., :3].astype(np.float32) / 255.0) ** 2.2
    a = main[..., 3:4].astype(np.float32) / 255.0
    bgl = (np.array(bg, np.float32) / 255.0) ** 2.2
    out = rgb * a + bgl * (1 - a)
    if back > 0 and scat is not None:
        s = np.asarray(Image.fromarray(scat[..., 0]).resize((main.shape[1], main.shape[0]), Image.BILINEAR)).astype(np.float32)[..., None] / 255.0
        out = out + np.array([1.0, 0.92, 0.7], np.float32) * s * a * back
    return np.clip(out, 0, 1) ** (1 / 2.2)


def block(d, name, info):
    main = load_frames(d, info, "main")
    scat = load_frames(d, info, "scatter")
    sel = picks(info)
    fw, fh = info["layers"]["main"]["frame_px"]
    sc = CELLW / fw if fw > CELLW else min(2.0, 130 / fh) if fh < 100 else 1.0
    sc = min(sc, 260 / fh) if info["family"] != "fog" or info["kind"] == "blobs" else sc
    cw, ch = max(8, int(fw * sc)), max(8, int(fh * sc))
    rows = []
    if fw >= 400:     # wide strips: 2 columns x 3 rows per background, dark and grey
        cw, ch = 380, int(380 * fh / fw)
        panels = []
        for bg in (DARK, GREY):
            tl = [np.asarray(Image.fromarray((comp(main[i], scat[i], bg) * 255).astype(np.uint8)).resize((cw, ch), Image.LANCZOS)) for i in sel]
            panels.append(np.concatenate([np.concatenate(tl[r * 2:r * 2 + 2], 1) for r in range(3)], 0))
        img = Image.fromarray(np.concatenate(panels, 1))
        canvas = Image.new("RGB", (img.width, img.height + 18), (24, 24, 28))
        canvas.paste(img, (0, 18))
        ImageDraw.Draw(canvas).text((4, 3), f"{name}  {info['title']}  |  left dark, right grey day; frames: form, drift, drift, linger, thin, fall  |  {info['size_note'][:60]}", fill=(235, 235, 235))
        return canvas
    for bg, back in ((DARK, 0.0), (GREY, 0.0), (BRIGHT, 1.0)):
        tiles = []
        for i in sel:
            t = (comp(main[i], scat[i], bg, back) * 255).astype(np.uint8)
            tiles.append(np.asarray(Image.fromarray(t).resize((cw, ch), Image.LANCZOS)))
        rows.append(np.concatenate(tiles, 1))
    img = Image.fromarray(np.concatenate(rows, 0))
    canvas = Image.new("RGB", (img.width, img.height + 18), (24, 24, 28))
    canvas.paste(img, (0, 18))
    ImageDraw.Draw(canvas).text((4, 3), f"{name}  {info['title']}  |  rows: dark, grey day, backlit + scatter  |  {info['size_note'][:70]}", fill=(235, 235, 235))
    return canvas


def sheet(d, out, names):
    atl = json.load(open(os.path.join(d, "atmos_atlas.json")))["presets"]
    blocks = [block(d, n, atl[n]) for n in names if n in atl]
    W = max(b.width for b in blocks)
    ncol = 1 if W > 900 else 2
    colw = W + 10
    rows = [blocks[i:i + ncol] for i in range(0, len(blocks), ncol)]
    H = sum(max(b.height for b in r) + 10 for r in rows) + 10
    sh = Image.new("RGB", (ncol * colw + 10, H), (24, 24, 28))
    y = 10
    for r in rows:
        for c, b in enumerate(r):
            sh.paste(b, (10 + c * colw, y))
        y += max(b.height for b in r) + 10
    sh.save(out, optimize=True)
    print("sheet", out, sh.size)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "assets", "atmos"))
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "atmos_preview_sheet.png"))
    ap.add_argument("--presets", nargs="*", default=None)
    ap.add_argument("--family", default=None)
    a = ap.parse_args()
    import sys
    sys.path.insert(0, HERE)
    import presets as PR
    names = a.presets or [n for n in PR.ORDER if not a.family or n.startswith(a.family)]
    sheet(a.dir, a.out, names)
