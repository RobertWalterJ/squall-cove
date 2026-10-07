# Squall Cove weapons and first-person arms

Nine nodes in one GLB: `assets/weapons.glb.b64.txt` (113 KB GLB, 151 KB one-line base64, 1,796 triangles in total, none over 440).
Source: `blender/generators/build_weapons.py` (uses `pg_set2.py`, `pg_core.py`). Manifest: `blender/review/weapons/weapons.json`, muzzle table `blender/review/weapons/muzzles.json`. One 3/4 render per node in `blender/review/weapons/`, plus `arms_with_rifle_3q.png` (arms and rifle together).

Rebuild: `_tools/blender-4.2.9-windows-x64/blender.exe -b --python blender/generators/build_weapons.py -- --review` (the `_tools` folder lives in the sibling `squall-cove` repo).

## Conventions

- Every node is a top-level mesh, life size, flat base-colour materials (dark metal, walnut-brown wood, black polymer), no textures.
- **Muzzle points along three -Z** (Blender +y). Up is three +Y, the gun's right side is three +X. The **origin is the centre of the grip** (the pistol grip, or the wrist of the shotgun and the handle of the knife), so `camera.add(gun)` or a hand-bone parent needs no rotation. Offset the gun by the hand position only.
- Sizes are width (x) x height (y) x length (z, along the barrel) in metres. Muzzle positions are in node space in **three coordinates** (x, y, z).

| Node | W x H x L (m) | Tris | Muzzle (three x, y, z) | Notes |
|---|---|---|---|---|
| pistol | 0.03 x 0.18 x 0.22 | 148 | (0, 0.07, -0.178) | grip box centred on the origin, slide above; sights on the slide |
| smg | 0.04 x 0.33 x 0.66 | 232 | (0, 0.102, -0.37) | vertical stick magazine, folded wire stock to the rear, foregrip at z -0.19 to -0.25 (left hand) |
| rifle | 0.06 x 0.35 x 1.19 | 256 | (0, 0.125, -0.78) | assault rifle, curved magazine, wooden handguard from z -0.20 to -0.46 (left hand holds here), stock to z +0.41 |
| shotgun | 0.07 x 0.20 x 1.25 | 208 | (0, 0.052, -0.89) | pump: forend (the sliding part) at z -0.15 to -0.32; origin is at the wrist behind the trigger guard |
| sniper | 0.12 x 0.32 x 1.50 | 436 | (0, 0.112, -0.96) | scope 0.4 m long above the receiver (axis 0.15 m above the bore), bolt handle on the +X side, folded bipod under the forend |
| knife | 0.04 x 0.05 x 0.36 | 88 | tip at (0, -0.008, -0.285) | edge down, tip forward; origin is the middle of the handle |
| magazine | 0.04 x 0.22 x 0.11 | 60 | n/a | loose spare rifle magazine, curved; **stands on y = 0** and is centred on its footprint, not at a grip (it is a ground prop) |
| muzzle_flash | 0.28 x 0.24 x 0.00 | 32 | n/a | see below |
| arms_idle | 0.56 x 0.39 x 1.00 | 336 | n/a | see below |

Grip notes, if a hand bone must be placed: pistol, smg, rifle and sniper are held by the pistol grip at the origin; the left hand goes on the foregrip or handguard (smg z -0.20, rifle z -0.30, sniper z -0.25 in three). The shotgun's right hand is at the origin (wrist) and the left on the forend.

## muzzle_flash

A flat 8-point star, 0.28 x 0.24 m, double sided, in the plane facing the shooter (normal along z), emissive amber material named `flash` with `doubleSided` set. It is a separate top-level node whose **origin is its centre**, placed at the **rifle** muzzle plus 2 cm (node translation (0, 0.125, -0.795) in the rifle's frame). For the other weapons, move it to that weapon's muzzle from the table (and a little further forward) and scale as wanted (the pistol wants about 0.5). The material is a Principled shader with strong emission, not KHR unlit, so in the game set `toneMapped = false` or swap in a `MeshBasicMaterial` with additive blending. Toggle `visible` for a frame or two per shot and spin it randomly about z.

## arms_idle

Two low-poly forearms and hands in the **rifle's own frame** (same origin as the rifle node, grip centre = origin). Parent `arms_idle` and `rifle` to the same camera group at the same offset and the right hand sits on the pistol grip, the left under the handguard, forearms running back and down toward the camera and out of frame. Skin is `skin` (#c68e68, plain), sleeves are `olive_cloth` (neutral olive) with darker `cuff` rings at the wrist. The sleeves extend to z +0.62 and y -0.24 so they run off the bottom of a typical first-person frustum.

For the pistol, smg and shotgun the arms do not line up exactly (their grips sit at different heights relative to the receiver): shift the arms group by the difference, or hide `arms_idle` and show the weapon alone. The left hand will float for the pistol.

## Caveats

- Hands are blocky (a mitten plus curled finger boxes and a thumb); they read fine at first-person distance, not in close-up.
- `arms_idle` is one rigid pose with no skeleton, so no reload or recoil animation beyond moving the whole group.
- Barrels are 6 to 8 sided rods.
- Review renders use Workbench studio lighting, so in-game PBR will look warmer and glossier on the metal.
