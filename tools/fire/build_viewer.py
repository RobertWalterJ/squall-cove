"""build_viewer.py - write docs/fire_viewer.html with the atlas JSON and PNGs embedded as data URIs
(so the page works from file:// where pixel reads of file images are blocked).
    python tools/fire/build_viewer.py [--dir assets/fire] [--out docs/fire_viewer.html]"""
import argparse, base64, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ap = argparse.ArgumentParser()
ap.add_argument("--dir", default=os.path.join(ROOT, "assets", "fire"))
ap.add_argument("--out", default=os.path.join(ROOT, "docs", "fire_viewer.html"))
a = ap.parse_args()
atlas = json.load(open(os.path.join(a.dir, "fire_atlas.json")))
data = {}
for name, p in atlas["presets"].items():
    data[name] = {}
    for k in ("flame", "smoke", "heat"):
        b = open(os.path.join(a.dir, p[k]["file"]), "rb").read()
        data[name][k] = "data:image/png;base64," + base64.b64encode(b).decode()
html = open(os.path.join(HERE, "viewer_template.html"), encoding="utf-8").read()
html = html.replace("/*ATLAS_JSON*/null", json.dumps(atlas, separators=(",", ":")))
html = html.replace("/*ATLAS_DATA*/{}", json.dumps(data, separators=(",", ":")))
os.makedirs(os.path.dirname(a.out), exist_ok=True)
open(a.out, "w", encoding="utf-8").write(html)
print("wrote", a.out, os.path.getsize(a.out) // 1024, "KB")
