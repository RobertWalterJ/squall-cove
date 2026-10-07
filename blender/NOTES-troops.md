# Troops (assets/troops.glb.b64.txt)

Twelve low poly characters on the people skeleton. Built by `blender/troops/build_troops.py` (python + numpy only, no Blender needed; reads `assets/people.glb.b64.txt`). `review_troops.py` renders the review images (Blender), `verify_troops.py` checks the GLB.

## Nodes (scene order = animation order)
Top-level nodes, each with a mesh node `<name>_mesh` (skinned) and a `root` bone tree:
trooper_guard_0..2, trooper_soldier_0..2, trooper_swat_0..2, trooper_raider_0..2.
Animation i belongs to character i (same convention as people.glb: clip i is bound to person i's bone names; every clip is named `idle`).

| Node | Triangles |
|---|---|
| guard_0 / 1 / 2 | 1672 / 1736 / 1884 |
| soldier_0 / 1 / 2 | 2076 / 2148 / 2180 |
| swat_0 / 1 / 2 | 2148 / 2076 / 2184 |
| raider_0 / 1 / 2 | 1726 / 1798 / 1966 |

Flat shaded, plain colour materials (named `tp_#hex`), no textures, no UVs. Skin tones from a 5-colour palette, varied across variants. File: troops.glb 3.1 MB, base64 4.13 MB.

## Skeleton
Bones (skin joint order, identical to facetex_0): root, hips, spine, chest, neck, head, upper_arm.L, forearm.L, hand.L, upper_arm.R, forearm.R, hand.R, thigh.L, shin.L, foot.L, thigh.R, shin.R, foot.R.
The 18 bone nodes are copied from facetex_0 verbatim: same names, hierarchy, rotations and scales, same node order. Only the translations are multiplied by 1.10 (a uniform size change, the same way the existing 16 people differ in height), so all characters are about 1.76 m to the head top (hip height 0.90 m). facetex_0 itself is 1.57 m. Inverse bind matrices were recomputed and the method was checked against facetex_0's own at scale 1.0. Verified by `verify_troops.py`: joint names equal facetex_0's for all 12, rotations equal, translation ratio exactly 1.1 everywhere. Facing +Z, feet at y = 0. The character's right is -x.
Skinning: per-vertex weights (max 4 bones, stored as normalized u16) from distance to bone segments, limited to the relevant bones per part (torso, arm, leg, neck). Small gear is rigid to one bone (helmet, cap and goggles to head; pouches to spine or chest; holster to hips or thigh; knee pads to shin; backpack to chest).

## Animation
The facetex_0 `idle` clip (breathing sway, 54 channels) is copied for every character with translations scaled by 1.10 and shared data. Walking, waving and sitting are driven from code in the game, as for the people.

## Kinds
- **guard**: navy shirt (long sleeves, short on n=1) and trousers, peaked cap with blank plate, duty belt with buckle, holster and pistol grip, pouches, epaulettes, blank badge, chest radio, black boots. n=2 adds a hi-vis vest with reflective bands.
- **soldier**: olive fatigues, helmet with net cover (scrim loops, band, chin strap), chest rig with mag pouches and straps, belt, cargo pockets, knee pads, gloves, boots. n=1 and 2 have a backpack; n=2 also a bedroll.
- **swat**: black kit, balaclava with eye slit, ballistic helmet with side rails and mount; goggles pushed up (n=0, 2), raised visor (n=1), headset (n=2); plate carrier with front and back plates, pouches, blank patch panels (front and back), shoulder pads, drop-leg holster, gloves, knee pads, boots.
- **raider**: civilian mix. n=0 dark red hoodie, grey pocket, dark red bandana; n=1 grey jacket with red sleeves, grey balaclava, dark red beanie, gloves; n=2 grey hoodie, dark red bandana, bandolier front and back. Cargo trousers with pockets, work boots with light soles, hood collar, cuffs.

## Not done / caveats
- No walk or wave clips (the existing GLB has idle only).
- No faces textured; faces are small boxes (eyes, brows, nose, mouth) in the model.
- Gear is rigid, so it can poke through the body on extreme poses (holster against a raised thigh, knee pads when kneeling).
- The game must load `troops` itself (no index.html changes were made) and pick clip i for character i.
- Heights are all the same; scale the node for variety.

Review renders: `blender/review/troops/trooper_<kind>_<n>_front.png` and `_back.png`.
