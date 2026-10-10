"""
lookdev.py - fast look check of fire types without baking atlases.

    python tools/fire/lookdev.py campfire,pool,blast_medium --out _fire_tmp/look.png

Runs a short scripted lifecycle (or the blast timeline) and composites 5 developed frames of flame + smoke on a dark
and a grey background, in world scale, one column per type.
"""
import argparse, os, sys, time
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sim as S  # noqa: E402
import presets as PR  # noqa: E402
import bake as B  # noqa: E402


def frames_for(name, nshow=5):
    kind = PR.META[name]["kind"]
    p = S.PRESETS[name]
    if kind == "blast":
        sim = S.Sim(name, 0, supply=lambda t: 0.3 * B.ss(1.5, 3.0, t))
        times = [0.12, 0.4, 0.9, 1.8, 3.5]
    elif kind == "shot":
        sim = S.Sim(name, 1, supply=lambda t: B.ss(0.0, 0.12, t) * (1.0 - B.ss(0.35, 0.75, t)))
        times = [0.1, 0.25, 0.4, 0.55, 0.75]
    else:
        sim = S.Sim(name, 0, supply=lambda t: min(1.0, 0.06 + t / 2.0))
        tdev = min(p.get("warm", 3.0), 7.0)
        times = [tdev + 0.35 * i for i in range(nshow)]
    rend = B.Renderer(name, sim.grid, 1)
    out = []
    for t in times:
        while sim.t < t:
            sim.step()
        f = S.record(sim, 2)
        fl, lum, _ = rend.flame(f, 0, 0)
        sm = rend.smoke(f, 0, 0)
        out.append((fl, sm))
    return sim, rend, out


def comp(fl, sm, bg, upf):
    H, W = fl.shape[:2]
    a = sm[..., 3:4]
    col = np.where(a > 1e-4, sm[..., :3] / np.maximum(a, 1e-4), 0)
    k = H / sm.shape[0]
    a = ndi.zoom(a, (k, W / sm.shape[1], 1), order=1)[:H, :W]
    col = ndi.zoom(col, (k, W / sm.shape[1], 1), order=1)[:H, :W]
    base = np.ones((H, W, 3), np.float32) * bg
    base = col * a + base * (1 - a)
    fa = fl.max(-1, keepdims=True)
    return np.power(np.clip(fl + base * (1 - fa), 0, 1), 1 / 2.2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("types")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "_fire_tmp", "look.png"))
    a = ap.parse_args()
    cols = []
    for nm in a.types.split(","):
        t0 = time.time()
        sim, rend, fr = frames_for(nm)
        rows = []
        for bg in (0.012, 0.40):
            rows.append(np.concatenate([comp(f, s, bg, B.UP_F) for f, s in fr], axis=1))
        img = np.concatenate(rows, axis=0)
        im = Image.fromarray((img * 255).astype(np.uint8))
        canvas = Image.new("RGB", (im.width, im.height + 16), (24, 24, 28))
        canvas.paste(im, (0, 16))
        d = sim.dx * np.array(sim.grid)
        ImageDraw.Draw(canvas).text((4, 2), f"{nm}  domain {d[0]:.1f} x {d[1]:.1f} x {d[2]:.1f} m", fill=(235, 235, 235))
        cols.append(canvas)
        print(f"{nm} {time.time() - t0:.0f}s", flush=True)
    W = sum(c.width for c in cols) + 6 * (len(cols) + 1)
    Hh = max(c.height for c in cols) + 12
    sheet = Image.new("RGB", (W, Hh), (24, 24, 28))
    x = 6
    for c in cols:
        sheet.paste(c, (x, 6))
        x += c.width + 6
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sheet.save(a.out)
    print("wrote", a.out, sheet.size)


if __name__ == "__main__":
    main()
