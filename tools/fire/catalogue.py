"""
catalogue.py - rewrite the generated tables between the CATALOGUE markers of MODEL-NOTES-FIRE-BAKED.md from assets/fire/fire_atlas.json.

    python tools/fire/catalogue.py
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
atlas = json.load(open(os.path.join(ROOT, "assets", "fire", "fire_atlas.json")))
P = atlas["presets"]
rows = ["| Type | Kind | Real size | Domain (m) | Flame sprite (m) | Clips | Full KB (flame / smoke / heat) | Low KB (flame / smoke) |", "|---|---|---|---|---|---|---|---|"]
tot = tot_low = 0
for n, p in P.items():
    L = p["layers"]
    fl = L.get("flame")
    kb = lambda x: f"{x / 1024:.0f}"
    fb, sb, hb = (fl["bytes"] if fl else 0), L["smoke"]["bytes"], L["heat"]["bytes"]
    lf, ls = (fl["low_bytes"] if fl else 0), L["smoke"]["low_bytes"]
    tot += fb + sb + hb
    tot_low += lf + ls + hb
    names = [c["name"] for c in p["clips"]]
    clips = ", ".join(sorted(set(re.sub(r"_[abc]$", "", x) for x in names)))
    rows.append(f"| `{n}` | {p['kind']} | {p['size_note']} | {' x '.join(map(str, p['domain_m']))} | {'x'.join(map(str, fl['size_m'])) if fl else 'smoke only'} | {clips} | {kb(fb)} / {kb(sb)} / {kb(hb)} | {kb(lf)} / {kb(ls)} |")
cat = "\n".join(rows) + f"\n\nTotal full-size atlases: {tot / 1048576:.2f} MB. Total phone (low) set: {tot_low / 1048576:.2f} MB (the heat atlas is shared).\n"
rows = ["| Type | Haze strength | Radius (m) | Height (m) | Rise (m/s) | Shape |", "|---|---|---|---|---|---|"]
for n, p in P.items():
    h = p["haze"]
    rows.append(f"| `{n}` | {h['strength']} | {h['radius_m']} | {h['height_m']} | {h['rise_speed_mps']} | {h['shape']} |")
haze = "\n".join(rows) + "\n"
if "particles" in atlas:
    pa = atlas["particles"]
    cat += f"\nParticles: dots {pa['dots']['bytes'] // 1024} KB, streaks {pa['streaks']['bytes'] // 1024} KB, burnt strip {pa['burnt_strip']['bytes'] // 1024} KB.\n"
fn = os.path.join(ROOT, "MODEL-NOTES-FIRE-BAKED.md")
s = open(fn, encoding="utf-8").read()
for tag, body in (("CATALOGUE", cat), ("HAZE", haze)):
    s = re.sub(rf"(<!-- {tag} -->).*?(<!-- /{tag} -->)", lambda m: m.group(1) + "\n" + body + m.group(2), s, flags=re.S)
open(fn, "w", encoding="utf-8").write(s)
print("updated", fn, f"full {tot / 1048576:.2f} MB, low {tot_low / 1048576:.2f} MB")
