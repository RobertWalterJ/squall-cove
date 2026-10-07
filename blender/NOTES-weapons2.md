# Weapons 2 (assets/weapons2.glb, assets/weapons2.glb.b64.txt)

14 nodes, 3,996 triangles, 244 KB GLB, 325 KB base64. Source `blender/weapons2/build_weapons2.py` (reuses `blender/generators/pg_set2.py`/`pg_core.py`). Rebuild: `../squall-cove/_tools/blender-4.2.9-windows-x64/blender.exe -b --python blender/weapons2/build_weapons2.py -- --review`. Renders in `blender/review/weapons2/` (`contact.png` is a sheet), manifest `weapons2.json`, muzzles `muzzles.json`.

## Conventions (same as weapons.glb)
Top-level mesh nodes, life size, flat PBR base-colour materials, no textures. Muzzle along three -Z; up is +Y; gun's right is +X. Origin is the hold point (grip centre for guns, handle apex for bags, body centre for grenades, binoculars, radio, tablet). `muzzles.json` values are in **Blender axes (x, y, z)**; for three use (x, z, -y).

| Node | W x H x L (m) | Tris | Muzzle (three) | Notes |
|---|---|---|---|---|
| lmg | 0.20 x 0.30 x 1.38 | 520 | (0, 0.14, -0.85) | belt-fed, ammo box on the left (-x) with belt, deployed bipod, carry handle, stock to z +0.53 |
| rpg | 0.14 x 0.29 x 0.93 | 412 | exit (0, 0.12, -0.55) | tube centre 0.12 above the grip; pistol grip + foregrip, optic on the right, rubber shoulder pad; flared rear |
| rpg > rocket | 0.11 x 0.11 x 0.48 | 168 | n/a | CHILD node of rpg; its own origin is at its centre (node translation (0, 0.12, -0.45) in rpg space); warhead protrudes from the tube. Hide it after firing, spawn the projectile at that node; flies along its -Z |
| grenade | 0.07 x 0.12 x 0.07 | 392 | n/a | frag, upright, lever + pin ring |
| smoke_grenade | 0.06 x 0.16 x 0.06 | 272 | n/a | grey canister, blank yellow band, lever + ring |
| binoculars | 0.15 x 0.07 x 0.21 | 288 | looking dir (0, 0, -0.117) | objectives toward -Z |
| flare_gun | 0.04 x 0.21 x 0.27 | 192 | (0, 0.075, -0.22) | orange wide barrel |
| marksman | 0.07 x 0.34 x 1.32 | 500 | (0, 0.125, -0.845) | semi-auto, 20 rd magazine, scope, folded bipod, cheek riser; same frame as rifle |
| carbine_scoped | 0.05 x 0.35 x 0.87 | 284 | (0, 0.125, -0.535) | short, red-dot housing with red lens, collapsible stock |
| revolver | 0.05 x 0.21 x 0.26 | 224 | (0, 0.082, -0.21) | six chambers, wooden grip |
| satchel_charge | 0.27 x 0.26 x 0.13 | 232 | n/a | origin at the carry-strap apex (bag hangs below), blocks, detonator box and wires on the +Z face |
| radio_handset | 0.07 x 0.36 x 0.05 | 152 | n/a | handheld radio, antenna up, speaker side faces the user (three +z) |
| medkit_bag | 0.30 x 0.26 x 0.14 | 244 | n/a | origin at handle apex; flat blank red cross on both faces |
| tablet_device | 0.26 x 0.19 x 0.03 | 116 | n/a | landscape in the x-y plane (three), screen (material `weapon_screen`, emissive cyan) faces +Z toward the viewer; orange bumper corners |

## Caveats
- Review renders use Workbench lighting; emissive `weapon_screen` is a Principled emission (strength 1.5), not unlit.
- The rocket is a separate child node so the game can hide it; the tube has no visible bore, and fins are omitted (not visible in the tube).
- Tablet and radio have no text/UI; satchel wires are decorative rods.
- Muzzle flash is not included; reuse `muzzle_flash` from weapons.glb.
