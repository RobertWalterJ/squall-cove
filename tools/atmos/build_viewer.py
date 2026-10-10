"""build_viewer.py - write docs/atmos_viewer.html with the atlas JSON and WebP atlases embedded as data URIs (works from file://).
    python tools/atmos/build_viewer.py [--dir assets/atmos] [--out docs/atmos_viewer.html]"""
import argparse, base64, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ap = argparse.ArgumentParser()
ap.add_argument("--dir", default=os.path.join(ROOT, "assets", "atmos"))
ap.add_argument("--out", default=os.path.join(ROOT, "docs", "atmos_viewer.html"))
a = ap.parse_args()
atlas = json.load(open(os.path.join(a.dir, "atmos_atlas.json")))
data = {}
for name, p in atlas["presets"].items():
    L = p["layers"]
    d = {"main": L["main"]["file"], "main_low": L["main"]["low"]["file"], "scatter": L["scatter"]["file"], "scatter_low": L["scatter"]["low"]["file"]}
    if "heat" in L:
        d["heat"] = L["heat"]["file"]
    data[name] = {k: "data:image/webp;base64," + base64.b64encode(open(os.path.join(a.dir, v), "rb").read()).decode() for k, v in d.items()}
html = open(os.path.join(HERE, "viewer_template.html"), encoding="utf-8").read()
html = html.replace("/*ATLAS_JSON*/null", json.dumps(atlas, separators=(",", ":")))
html = html.replace("/*ATLAS_DATA*/{}", json.dumps(data, separators=(",", ":")))
os.makedirs(os.path.dirname(a.out), exist_ok=True)
open(a.out, "w", encoding="utf-8").write(html)
print("wrote", a.out, os.path.getsize(a.out) // 1024, "KB")
