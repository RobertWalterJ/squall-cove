"""build_viewer.py - write docs/fire_viewer.html with the atlas JSON and images embedded as data URIs
(so the page works from file:// where pixel reads of file images are blocked).
    python tools/fire/build_viewer.py [--dir assets/fire] [--out docs/fire_viewer.html] [--low]
--low embeds the half-size (phone) flame and smoke atlases to make a smaller page."""
import argparse, base64, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ap = argparse.ArgumentParser()
ap.add_argument("--dir", default=os.path.join(ROOT, "assets", "fire"))
ap.add_argument("--out", default=os.path.join(ROOT, "docs", "fire_viewer.html"))
ap.add_argument("--low", action="store_true")
a = ap.parse_args()
atlas = json.load(open(os.path.join(a.dir, "fire_atlas.json")))
MIME = {".webp": "image/webp", ".png": "image/png"}


def uri(fn):
    b = open(os.path.join(a.dir, fn), "rb").read()
    return "data:" + MIME[os.path.splitext(fn)[1]] + ";base64," + base64.b64encode(b).decode()


data = {}
for name, p in atlas["presets"].items():
    data[name] = {}
    for k in ("flame", "smoke", "heat"):
        if k in p["layers"]:
            L = p["layers"][k]
            f = L["low"]["file"] if (a.low and "low" in L) else L["file"]
            if a.low and "low" in L:   # the viewer reads frame sizes from the JSON, so point it at the low atlas geometry
                for key in ("frame_px", "cols", "rows", "file"):
                    L[key] = L["low"][key]
                L["m_per_px"] = L["low_m_per_px"]
            data[name][k] = uri(f)
if "particles" in atlas:
    data["_particles"] = {"strip": uri(atlas["particles"]["burnt_strip"]["file"])}
html = open(os.path.join(HERE, "viewer_template.html"), encoding="utf-8").read()
html = html.replace("/*ATLAS_JSON*/null", json.dumps(atlas, separators=(",", ":")))
html = html.replace("/*ATLAS_DATA*/{}", json.dumps(data, separators=(",", ":")))
os.makedirs(os.path.dirname(a.out), exist_ok=True)
open(a.out, "w", encoding="utf-8").write(html)
print("wrote", a.out, os.path.getsize(a.out) // 1024, "KB")
