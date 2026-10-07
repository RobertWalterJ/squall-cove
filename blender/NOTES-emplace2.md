# Emplacements, guard towers, ladders (assets/emplace2.glb + assets/emplace2.glb.b64.txt) and the rebuilt vehicle turrets (assets/bveh.glb)

Built with Blender 4.2 (headless) by `blender/emplace2/`: `e_lib.py` (palette, plates, sandbags, ladders, cage hoops, node tree), `e_guns.py` (5 gun emplacements), `e_towers.py` (3 towers + 3 ladders), `build_emplace2.py` (build, export, b64, review renders with poses), `verify_emplace2.py`, `run.sh`.

    sh blender/emplace2/run.sh [model,model] [--norender] [--noexport]     (B_VIEWS=3q,3q_rear@up,3q@down B_SIZE=720 B_SAMPLES=8; B_AIM="x,y,z" B_EXT=m for close-ups)
    python blender/emplace2/verify_emplace2.py                              (from the game dir)

NOTE: build only a subset WITH export and the GLB contains only that subset (`run.sh --norender` with no model list writes the full file). Review PNGs: `blender/review/emplace2/<model>_<view>[_<pose>].png` (poses `up`, `vert`, `down`, `high` show the chain moving: shield plates and sights turn with the barrels).

Metres, +Z forward, +Y up, model's left = +X. 11 top-level empties at the origin (they overlap; pick by name), base on y = 0. **Every node carries translation only** (no rotation, no scale; the one exception is the `_deck` / `_roof` marker empties, which carry a scale = walkable half-extents). Rotating a node about its local axis rotates exactly about its pivot (the node origin). No textures, UVs, text or insignia. All faces single sided except `emp_glass` (alpha 0.5, BLEND, double sided; set depthWrite false).

## Materials (25, all `emp_*`)
`emp_paint` is the ONLY body-paint material (gun bodies, shield plates, mantlets; light neutral olive `#8f9478`, set the colour directly to recolour). Everything else is fixed: `emp_steel`, `emp_steel_dark`, `emp_galv`, `emp_black`, `emp_rubber`, `emp_brass`, `emp_ammo` (ammo boxes, NOT team paint), `emp_shell`, `emp_shell_band`, `emp_wood`, `emp_wood_dark`, `emp_wood_light`, `emp_crate`, `emp_sandbag_a/b/c`, `emp_concrete`, `emp_concrete_dark`, `emp_earth`, `emp_olive` (steel-tower cabin), `emp_roof` (corrugated roof), `emp_yellow`, `emp_glass`, `emp_lens` (emissive: lamp lenses).

## Kinematic chains (the rule for all five guns)
- `<m>_yaw`: rotate about **Y**: `yaw.rotation.y = theta` (a normal right-handed rotation about +Y: +Z turns toward +X, the model's left).
- `<m>_pitch` (child of yaw): rotate about **X**: `pitch.rotation.x = -elevation` (elevation in radians, positive = muzzle up; positive rotation.x lowers the barrel). Pivot = trunnion axis. **Shield plates, ammo boxes, sights and cradle are meshes of the pitch node, so they rotate with the barrels** (verified by render: `*_3q_rear_up.png`).
- `<m>_barrels` / `_barrel` (child of pitch): recoil slide. Game sets `barrel.position.z = origin_z - recoil` (translate along local -Z; the node is inside the pitch node so it recoils along the bore at any elevation). Returns to 0.
- Markers (empties, translation only, +Z = bore direction at rest): muzzle markers are children of the recoil node (they move with recoil and elevation); `casing` ejection ports are children of the recoil node (eject direction in the pitch frame given below).
All pivots below are in model coordinates (the glTF translations are relative to the parent, e.g. `emp_aa_barrels` is (0,0,0) inside `emp_aa_pitch`).

| Model | Tris | yaw pivot | pitch pivot (trunnion) | recoil node pivot | yaw range | elevation range | recoil travel |
|---|---|---|---|---|---|---|---|
| `emp_aa` twin AA cannon | 4928 | (0, 0.86, 0) | (0, 1.32, 0) | `emp_aa_barrels` (0, 1.32, 0) | free 360 | -10 to 85 deg | 0.12 m |
| `emp_mg` heavy MG nest | 2964 | (0, 0.98, 0.15) | (0, 1.12, 0.15) | `emp_mg_barrel` (0, 1.12, 0.45) | +-70 deg (sandbag walls) | -15 to 45 deg | 0.04 m |
| `emp_mortar` | 3208 | (0, 0.20, 0) ball socket | (0, 0.20, 0) same point | none | free 360 | 45 to 85 deg (see below) | none |
| `emp_howitzer` field gun | 3598 | (0, 0.95, 0) | (0, 1.32, 0.10) | `emp_howitzer_barrel` (0, 1.32, 0.10) | +-30 deg (limited by the trails) | -10 to 85 deg | 0.45 m |
| `emp_flak` 37 mm on tripod | 2704 | (0, 0.88, 0) | (0, 1.24, 0) | `emp_flak_barrel` (0, 1.24, 0) | free 360 | -10 to 85 deg | 0.10 m |

Node trees (all child lists as parented in the file):
- `emp_aa` > `emp_aa_base` (pad, sandbag ring open at the rear, outrigger base, pedestal, crates), `emp_aa_yaw` (turntable, yoke, hand wheels, gunner platform) > [`emp_aa_seat`, `emp_aa_pitch` (cradle, 2 magazines, 4 shield plates + struts, ring/bead sight) > `emp_aa_barrels` (2 receivers, jackets, barrels, muzzle brakes) > [`emp_aa_muzzle_L` (0.17,1.32,2.04), `emp_aa_muzzle_R` (-0.17,1.32,2.04), `emp_aa_casing` (0,1.19,0) ejects down]]. `emp_aa_seat` (0, 0.40, -0.66) = gunner's feet on the rotating platform (child of yaw, turns with the gun); gunner stands behind the shield.
- `emp_mg` > `emp_mg_base` (nest, tripod, crates), `emp_mg_seat` (0, 0.09, -0.60) static (feet; gunner kneels/stands behind the gun), `emp_mg_yaw` (pintle head, fork) > `emp_mg_pitch` (receiver, shield plate, ammo box + belt, sights, grips) > `emp_mg_barrel` > `emp_mg_muzzle` (0, 1.12, 1.34); `emp_mg_casing` (-0.06, 1.10, 0.05) child of pitch, ejects to -X.
- `emp_mortar` > `emp_mortar_base` (fixed base plate, sandbag pit open at rear, duckboards, 2 crates, 10 bombs), `emp_mortar_yaw` (traverse ring) > `emp_mortar_pitch` (tube **and bipod legs, collar, cross-brace, dial sight**) > `emp_mortar_muzzle` (0, 0.20, 1.20).
- `emp_howitzer` > `emp_howitzer_base` (wheels, axle, trails with spades, cross-member, ammo), `emp_howitzer_crew_loader` (0,0,-1.20), `emp_howitzer_crew_ammo` (-0.30,0,-2.30), `emp_howitzer_crew_commander` (1.75,0,-1.80) (ground positions, feet, between/behind the trails), `emp_howitzer_yaw` (top carriage, cheeks, hand wheels, seat) > [`emp_howitzer_crew_gunner` (0.62, 1.01, -0.78) hip position of the seated gun layer, turns with the carriage, `emp_howitzer_pitch` (cradle, recoil cylinders, elevating arc, **big shield: 2 wings x 4 plates + 2 centre plates**, telescope + dial sight) > `emp_howitzer_barrel` (breech, tapered barrel, evacuator, muzzle brake) > `emp_howitzer_muzzle` (0, 1.32, 3.25)].
- `emp_flak` > `emp_flak_base` (pad, tripod, half sandbag ring open at the rear, crates), `emp_flak_yaw` > [`emp_flak_seat` (0.64, 1.00, -0.58) hip of the seated gunner on the side arm, `emp_flak_pitch` (sleeve, clip guide + clip, 2 shield wings + 2 centre plates, ring/bead sights) > `emp_flak_barrel` > [`emp_flak_muzzle` (0, 1.24, 1.82), `emp_flak_casing` (0, 1.14, 0) ejects down]].

**Mortar elevation convention.** Same rule as the guns (rest, rotation 0 = tube horizontal along +Z; `rotation.x = -elevation`), but the bipod is rigid with the tube so it is authored to land on the ground at **65 deg** (the default elevation to start with). Rigid legs: feet sink 0.20 m at 45 deg, 0.08 m at 55, float 0.12 m at 75 and 85. At rotation 0 the folded bipod points underground (y -0.51) so never display the mortar un-elevated.

## Footprints and recommended collision (model coordinates)
- `emp_aa`: pad radius 2.6 (earth apron to 3.1), walkable. Sandbag ring centre radius 2.25, 0.30 thick, y 0.10 to 0.70, open to the rear: ring ends at +-150 deg from +Z, so a gap about 2.2 m wide at z = -2. Gun core: cylinder r 0.55, y 0 to 1.0 (base + pedestal; the outriggers are 0.37 high, walkable). Crates at (1.15, -1.95) and (-1.0, -2.0), 0.75 x 0.62 x 0.45. Pitched assembly bounds: x +-0.69, y 0.98 to 1.93.
- `emp_mg`: earth floor 3.5 x 3.0 (x +-1.75, z -1.60 to 1.40). Sandbag boxes: front x +-1.7, z 1.03 to 1.33, y 0 to 0.81; sides x +-(1.40 to 1.70), z -1.30 to 1.33, y 0 to 0.66; rear stub x -1.7 to -0.75, z -1.3 to -1.0, y 0 to 0.51. Open to the rear (+Z is the firing side). Tripod is thin: ignore.
- `emp_mortar`: floor disc r 2.3, ring r 1.55 centre (0.34 thick, y 0.04 to 0.49), open rear (+-150 deg). Base plate r 0.42 y 0 to 0.14.
- `emp_howitzer`: body box centre (0, 0.9, 0.2) size (2.3, 1.8, 1.4) (wheels x +-1.12, shield z up to 0.65); trails: boxes along (+-0.34, 0.8, -0.3) to (+-1.12, 0.17, -3.35), 0.16 wide, 0.8 down to 0.17 high; footprint x +-1.3, z -3.55 to 0.7 (+ barrel to z 3.25 at rest, y 1.14 to 1.50). Earth disc r 3.9 is cosmetic.
- `emp_flak`: pad r 2.1, earth to 2.7; half ring centre radius 1.85, y 0.08 to 0.5, ends at +-115 deg (open to the rear); tripod core cylinder r 0.4, y 0 to 1.0.

## Guard towers (all ladders face +Z; the climber stands at z = rung plane + 0.40, facing -Z)
Heights are exact (model coordinates). Markers are translation-only empties (no rotation): **`_ladder_bottom` = ground point where the climber stands to start (+Z of the marker points away from the rungs; the rungs are 0.40 m in front of it along -Z); `_ladder_top` = point on the deck where the climber steps off, after passing between the rails; the climb line is x = 0, z = ladder_bottom.z, y from 0 to deck, then a 0.5 to 1.5 m horizontal step to `_ladder_top`.** Rails are 0.46 apart (x +-0.23), rung pitch 0.30 m, first rung at y 0.28, rails extend above the deck as grab rails.

| | `tower_guard_wood` | `tower_guard_concrete` | `tower_guard_steel` |
|---|---|---|---|
| Tris | 2680 (lamp 216) | 3528 | 3872 (lamp 92) |
| Overall height | 8.11 (roof ridge 8.0) | 10.2 to rail top, 11.24 mast tip | 12.16 (cabin ridge ~12.15) |
| Deck surface y | **5.00** (plank top) | **6.60** cabin floor / balcony; roof **9.19** | **9.60** |
| Rung plane z | 0.30 | 1.45 (0.35 off the shaft face z 1.1) | 2.05 |
| Ladder rails | y 0 to 6.10 (climb 5.0, ladder_top y 5.0) | 0 to 7.60 (climb 6.6) | 0 to 10.70 (climb 9.6) |
| `_ladder_bottom` | (0, 0, 0.70) | (0, 0, 1.85) | (0, 0, 2.45) |
| `_ladder_top` | (0, 5.00, -0.35) | (0, 6.60, 0.85) | (0, 9.60, 1.35) |
| `_deck` (centre; scale = half extents x, 1, z) | (0, 5.00, 0), (0.98, 1, 0.98) | (0, 6.60, -0.72), (1.70, 1, 1.10) cabin interior | (0, 9.60, 1.20), (1.40, 1, 1.20) |
| `_seat` (sniper feet, faces +Z) | (0.62, 5.00, 0.45) behind the parapet corner | (1.20, 6.60, -0.15) at the +X front window | (-0.90, 9.60, 1.15) at the front-left rail |
| `_roof` | none | (0, 9.19, -0.72), (1.85, 1, 1.12) | none |
| Lamp node | `tower_guard_wood_lamp` pivot (-1.40, 6.45, 1.34): rotate about Y to sweep, lens faces +Z | none | `tower_guard_steel_lamp` pivot (0.95, 11.20, 0.26), same |

Access details: wood: ladder passes through a deck **hatch** (x +-0.40, z 0 to 1.0, open, 0.07 coaming on 3 sides) and stops 1.1 above the deck; step off toward -Z. Concrete: external ladder with **5 safety hoops** (y 2.4 to 6.0, r 0.42, 3 straps) and 5 wall brackets up the +Z face; it rises through a **notch** in the balcony slab (x +-0.46, z 1.2 to 2.0); the cabin door is on the balcony side (+Z face, z 0.4); the roof (rail 1.05 high, radio mast stub at (1.5, 9.19, -1.5), height to 11.24) has no ladder in the model (game teleports/animates). Door at the base on the +X face, z -0.45 to 0.25, y 0.42 to 2.2 (steel door leaf, decorative). Steel: ladder with **7 hoops** (y 2.5 to 7.9) outside the lattice with brackets to the +Z face, through a notch (x +-0.46, z 1.7 to 2.5) in a landing that extends the deck to z 2.5; cabin occupies x +-1.2, z -1.4 to -0.1 on the deck (solid walls, door on the +Z side, windows).
Walkable deck regions: wood x,z +-0.98 minus the hatch and minus the sandbag parapet (+X side: x 0.81 to 1.11, z -1.2 to 0.95; front: z 0.83 to 1.13 for |x| 0.44 to 1.0), 4 sandbag courses (0.59 high); concrete cabin interior x +-1.7, z -1.7 to 0.25 (counter at (0.5 to 1.8, 0.14 to 0.34, y to 0.8)), balcony x +-1.9, z 0.55 to 1.9 minus the notch, roof x +-1.85, z -1.85 to 0.45; steel x +-1.4, z 0.0 to 2.4 minus the notch (cabin in front of that).
Recommended collision (solid parts only, people may walk under the wooden tower):
- wood: footprint 2.5 x 2.5 (legs at (+-1.1, +-1.1), 0.22 square, footings 0.52 x 0.28 square). Four leg boxes 0.30 x 7.2 x 0.30 centred (+-1.1, 3.6, +-1.1); deck box x,z +-1.22, y 4.62 to 5.0; roof box x +-1.5, z +-1.55, y 7.1 to 8.0. Bracing is not solid; the front lower bay (y below 2.4) is open for the ladder. Parapet: boxes as above.
- concrete: footprint plinth 2.7 x 2.7 (y 0 to 0.3); shaft box x,z +-1.1, y 0.3 to 5.9; capital +-1.22, y 5.9 to 6.4; floor slab x +-2.0, z -2.0 to 2.0 (notch x +-0.46, z 1.2 to 2.0 open), y 6.4 to 6.6; cabin walls x +-1.85, z -1.85 to 0.4, y 6.6 to 8.9; roof slab x +-2.1, z -2.1 to 0.62, y 8.9 to 9.19. Ladder/cage sit just outside the +Z face (z 1.1 to 1.9).
- steel: footprint 3.8 x 3.8 at the footings (legs at (+-1.9, +-1.9), tapering to (+-1.2, +-1.2) at y 9.6; leg half-offset h(y) = 1.9 - 0.7 y / 9.6). Four leg boxes 0.35 wide, e.g. at y 1.6 (h 1.77), 4.8 (h 1.55), 8.0 (h 1.32). Lattice is not solid. Deck frame x +-1.5, z -1.5 to 2.5, y 9.42 to 9.6; cabin walls box x +-1.2, z -1.4 to -0.1, y 9.6 to 11.55; roof to 12.15.

## Freestanding ladders (rungs in the plane z = 0, wall at z = -0.25, climber at +Z)
| | `ladder_4m` | `ladder_8m` | `ladder_hoops_6m` |
|---|---|---|---|
| Tris | 452 | 856 | 1176 |
| Climb length (to `_ladder_top` y) | 4.0 | 8.0 | 6.0 |
| Rails | y 0 to 4.9 (0.9 grab extension) | 0 to 8.9 | 0 to 6.9 |
| `_ladder_bottom` | (0, 0, 0.40) | (0, 0, 0.40) | (0, 0, 0.40) |
| `_ladder_top` | (0, 4.0, -0.55) | (0, 8.0, -0.55) | (0, 6.0, -0.55) |
Rails x +-0.23, rung pitch 0.30, wall brackets (plates at z -0.25) every 1.8 m plus one 0.3 below the top, foot plates at the base; `ladder_hoops_6m` has 5 hoops (y 2.3 to 5.9, r 0.42, centred z 0.12) and 3 vertical straps. Footprint 0.58 x 0.33 (hoops 0.86 x 0.8). `_ladder_top` is on the wall top / platform surface y = climb length, 0.55 behind the rung plane (0.30 behind the wall face). Collision: rails only, none needed.

## Vehicle turrets (assets/bveh.glb rebuilt; old files kept as `assets/bveh.glb.bak` and `bveh.glb.b64.txt.bak`)
Every existing node name, pivot, marker and material of bveh was kept (verify_bveh.py: 0 problems, 18 materials, all expected nodes). Changes (a new mesh child under the pitch node, nothing renamed, `veh_paint` still the only paint):
- `jeep_gun` (yaw+pitch node, pivot (0,1.52,0.20)): new child `jeep_gun_shield` (80 tris): two folded wings, upper and lower centre plates, braces; the jeep had no shield before.
- `technical_gun` (pivot (0,1.98,-1.55)): the shield wings and plate were part of the gun mesh; now a slotted shield in the child `technical_gun_shield` (104 tris) so it elevates with the barrel.
- `apc_gun` (pivot (0,2.32,2.17), child of `apc_turret`): the mantlet box moved into the child `apc_gun_mantlet` (44 tris) with two angled cheek plates.
- `light_tank_barrel` (pivot (0,1.62,1.10), child of `light_tank_turret`): the mantlet box moved into the child `light_tank_barrel_mantlet` (44 tris) with two angled cheek plates.
Turret tris: apc 7956 (unchanged total), light_tank 7960, jeep 5904, technical 6120. All muzzle markers stay children of the gun nodes at the same positions.

## Caveats
- Verified by Blender renders (`blender/review/emplace2/`) and `verify_emplace2.py` (indices valid, unit normals, no textures, b64 matches the GLB and is one line, 25 `emp_*` materials, chains parent-child as listed, every model under 8000 tris, base on y = 0 except the mortar's folded bipod, no rotations). Not loaded in three.js; the chains were also checked numerically (pitch subtree never goes below y 0.6 at -10 to 85 deg for AA/howitzer/flak, MG min y 0.60 at 45 deg).
- Pitch subtrees clear the ground and the sandbag ring over the stated ranges. The AA gunner platform (r 0.95) rotates inside the ring; the platform and the seat marker turn with the yaw.
- The bipod of the mortar is rigid with the tube (see the elevation note). Mortar bombs, crates and the pit are static.
- The howitzer shield has an open sight window per wing (0.30 x 0.24 m) and the barrel slot has no cover; its wings are flat (fold 0). Wheels are 18-sided with solid hubs.
- Towers: lattice, bracing and ladders are real geometry but thin (0.07 to 0.14 m); sandbag parapets are 4 courses of loose bags (roughly 1000 tris on the wooden tower deck). The concrete tower roof is not reachable by ladder; the notch/hatch edges are the only openings. Windows are glass panes in frames, closed. Lamps are separate nodes; their lens material `emp_lens` is emissive.
- The sandbag arcs and lines use the same material trio (`emp_sandbag_a/b/c`); orientation of bags is jittered with fixed random seeds (rebuilds are deterministic).
