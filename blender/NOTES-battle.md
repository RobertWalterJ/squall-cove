# Battlefield props (assets/battle.glb + assets/battle.glb.b64.txt)

Built with Blender 4.2 (headless) by `blender/battle/`: `b_lib.py` (materials, sandbag/crate/drum/dish/tent helpers, reuses `blender/helis/heli_lib.py`), `b_infra.py`, `b_mil.py`, `b_field.py` (the models), `build_battle.py` (build, export, b64, review renders), `verify_battle.py`, `run.sh`.

    sh blender/battle/run.sh [model,model] [--norender] [--noexport]     (B_VIEWS=3q,top B_SIZE=800 B_SAMPLES=12)
    python blender/battle/verify_battle.py                              (from the game dir)

Metres, +Z forward, +Y up, model's left = +X. 23 top-level empties at the origin (they overlap; pick by name), base on y=0, nodes carry translation only (no rotation/scale), so rotating a node about its local axis rotates about the pivot. No textures/UVs/text/insignia. Materials are `battle_*` (glass `battle_glass` alpha 0.5, emissive `battle_lens`, `battle_light_red`); canvas/camo/wire/palm/flag materials are double sided. Review PNGs in `blender/review/battle/<model>_{3q,3q_rear}.png` (palm_tree and barbed_wire also `_top`, `_side`).

| Model | Tris | Pivot children |
|---|---|---|
| radio_mast | 2186 | none (30 m lattice, 31.5 m with whip, dish at 21 m facing +Z, 9 guy wires to anchors out to 18 m, hut at -5,-2.5) |
| radar_station | 1628 | `radar_dish` (0.6, 11.6, 0.6) spin about Y; dish faces +Z at rest |
| supply_depot | 2917 | none |
| artillery_battery | 4572 | `howitzer_barrel` (0, 1.1, 0) pitch about X; barrel along +Z, horizontal at rest |
| mortar_pit | 4752 | `mortar_tube` (0, 0.16, 0.05) pitch about X; rest pose elevated 72 deg toward +Z (the bipod is fixed in the body) |
| searchlight_tower | 1322 | `searchlight_lamp` (0, 6.55, 0); beam along +Z, lens `battle_lens` |
| bunker_large | 2996 | none (9 m wide, 3 slits and apron on +Z, door on the +X side) |
| command_post | 1862 | none |
| watch_tower_wood | 1260 | none (8.5 m to the roof peak, deck at 6.4, ladder on +Z) |
| trench_straight / _corner / _end | 1064 / 1224 / 1100 | none |
| barbed_wire | 2202 | none (4 m along X) |
| sandbag_corner | 3320 | none |
| helipad | 803 | `windsock` (5.2, 4.15, -5.2) spin about Y; sock points +Z at rest |
| ammo_dump | 2000 | none |
| field_hospital | 961 | none |
| fuel_depot | 2026 | none |
| oil_pumpjack | 944 | `pump_head` (0, 4.5, 0) rocks about X; horsehead and cable on +Z |
| ruined_wall | 1212 | none (6 m along X) |
| ruined_house | 3384 | none |
| dune_rock_cluster | 1044 | none (8, 6, 4 m outcrops) |
| palm_tree | 980 | none (about 9 m with fronds) |

## Caveats
- Trenches are modelled as raised earthworks: the channel floor is at y=0 and the earth walls (the "1.2 m deep") rise 1.2 m above it, with sandbag lips on top (1.5 m). Placed on flat terrain they read as a trench you can stand in; to bury them instead, drop the node 1.2 m (the mud floor and duckboards then sit at -1.2). Open ends of straight/corner pieces are at the model's -Z end and (corner only) the +X end: corner joins at (0,-2) facing -Z and (2,0) facing +X; trench_end is closed at +Z. Footprints are 3.7 m wide.
- Linear pieces run along X (`barbed_wire`, `ruined_wall`) or Z (trenches); walls of ruined pieces are 2.5-4.4 m tall and brick-by-brick (no mortar gaps, bricks touch).
- Only the barrel, tube, dish, lamp, pump head and windsock are separate nodes. The pumpjack has no pitman (it would detach when the beam rocks); the howitzer shield, crew, and the mortar bipod do not follow their pivots. The windsock is always shown streaming along +Z; rotate the node to match the wind.
- The red cross (field_hospital, roof and sign board) is flat geometry, not a texture; the supply depot flag is a plain pennant.
- Sandbags are 20-tri puffy blocks, sandbag-heavy models are the heaviest (artillery_battery, mortar_pit about 4.6-4.8k).
- `radio_mast`: guy wires are 3-sided double-sided tubes; the 0.5 m anchor blocks sit on the ground out to 18 m, so the model footprint is about 36 m across.
- Four tiny dark dots appear at sandbag/brick corners in Cycles renders (shadow terminator); not investigated and not expected in-game.
- Verified only by Blender renders and `verify_battle.py` (indices valid, normals unit length, base64 matches the GLB, 2.5 MB, 61 materials); not loaded in a glTF viewer or the game.
