# Troops 2 (assets/troops2.glb, assets/troops2.glb.b64.txt)

36 low poly characters (12 kinds x 3 variants) on the same skeleton as troops.glb. Built by `blender/troops2/build_troops2.py` (python + numpy, no Blender needed; it executes the skeleton, geometry, skinning and GLB-writer parts of `blender/troops/build_troops.py`, so conventions are identical). `verify_troops2.py` checks the GLB; `review_troops2.py` (Blender) + `compose_sheet.py` (PIL) make the renders.
Run: `python blender/troops2/build_troops2.py .` from the game dir.

## Conventions (same as troops.glb)
Top-level node `trooper2_<kind>_<n>` (extras: height 1.731, hip_height 0.9, kind, variant), child skinned mesh node `<name>_mesh`, 18-bone tree, skin joint order root, hips, spine, chest, neck, head, upper_arm.L, forearm.L, hand.L, upper_arm.R, forearm.R, hand.R, thigh.L, shin.L, foot.L, thigh.R, shin.R, foot.R. 36 `idle` clips, clip i bound to character i (scene order = animation order). Facing +Z, feet at y 0, character's right is -x. Flat colour materials `tp_#hex`, doubleSided, no textures. Faces are tiny boxes. Skin tones vary per variant.

## Nodes and triangles (n = 0 / 1 / 2)
desert 2000/1964/2224 (helmet cover, boonie, helmet+goggles; shemagh-style scarf, plate carrier) | urban 2568/2568/2640 (grey-blue camo patches, helmet, goggles on eyes, knee and elbow pads) | sniper 2576/2586/2576 (hanging strips, boonie or hood, rifle sling) | medic 2012/2012/2084 (white helmet band or cap band, flat red cross on chest, bag, helmet sides) | engineer 1980/2012/1980 (hard hat, tool belt, backpack with coiled wire) | pilot 2012/1992/2092 (flight suit, visored helmet, orange life vest) | officer 1772/1672/1708 (peaked cap, beret, cap; holster, cross strap, map case) | militia 1786/2058/1918 (mismatched civilian clothes, face scarf, bandolier, no insignia) | riot 2128/2148/2148 (visor helmet up/down, arm/shin/thigh guards, baton, no shield) | special 2284/2260/2308 (black or dark green, NVG flipped up, plate carrier, sling + suppressor pouch) | heavy 2292 x3 (bulky armour, pauldrons, ammo belt, hip ammo box, pack) | port_worker 1900/1924/1900 (hi-vis vest, hard hat, gloves, overalls; ear defenders n=1, glasses n=2).
Max 2640 triangles. Verified: all 36 joint lists equal troops.glb's, weights sum to 1 (max error 2e-16), indices and accessors in range.
File: 10.0 MB GLB, 13.3 MB base64 (the 36 skins and 36 idle clips are not shared, as in troops.glb).

## Caveats
- Gear is rigid to one bone (as in troops.glb), so it can poke through on extreme poses (map case, hip boxes, riot thigh guards while kneeling).
- Medic cross is flat blank red geometry; no text or real-world insignia anywhere. Engineer wire coil reads as a disc from behind.
- Heavy variants differ only by colour. The pilot visor (n=0, 2) and riot visor (n=1) hide the face.
- Sniper strips and ghillie are boxes hanging rigidly; they do not sway.
- Heights are all 1.73 m; scale nodes for variety.
Renders: `blender/review/troops2/` (`contact_front.png`, `contact_back.png`, `contact_heads.png`, plus per character `_front/_back/_head`).
