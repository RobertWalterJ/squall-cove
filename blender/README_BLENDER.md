# Squall Cove Blender files

Editable Blender 4.2 scenes for every Squall Cove model. Open them in Blender 4.2 or newer.

| File | Contents |
|---|---|
| `squall_cove_game_models.blend` | exactly what the game loads: the fleet, harbour, nature, cargo, the Coast Guard boats (`ccg`, `ccgfleet`) and the 16 people (`assets/*.glb.b64.txt` are these, base64 encoded) |
| `squall_cove_kit_coastguard.blend` | the eleven Coast Guard hulls as separate models (rebuilt October 2026, see below) |
| `squall_cove_kit_watercraft.blend` | dinghy, dory, gaff cutter, keelboat, tug and workboat in four styles each |
| `squall_cove_kit_harbour.blend` | piers, bollards, buoys, channel markers and lighthouses |
| `squall_cove_kit_cargo.blend` | barrels, crates, drums, sacks, rope, ice, ingot pallets |
| `squall_cove_kit_containers.blend` | 10, 20 and 40 foot containers |
| `squall_cove_kit_rocks.blend` | boulders, pebbles, sea stacks and slabs |
| `squall_cove_kit_vegetation.blend` | broadleaf, pine and palm trees, shrubs and grass |
| `people/coilover_people_photo_faces.blend` | the people source: bodies, CC0 MakeHuman faces, idle / walk / sit / wave actions (the game GLB carries idle only; walking and waving are driven from code) |

## Coast Guard ships: how they were corrected

The October 2026 audit compared each hull with side-on photographs and published dimensions (length, beam and draught were already right; the layouts were not).
Every position in `generators/pg_marine.py` is now a fraction of hull length counted from the **bow**, so a ship spec reads like a general arrangement drawing:

- **House**: tiers step aft from a forward bridge, 0.5 to 0.86 of the beam wide (was 0.8 to 0.94 with wide ledges), 12 to 15 m tall (about twice the hull side).
- **Position** (house, from the bow): Louis S. St-Laurent 29 to 54 percent, Terry Fox 20 to 47, Pierre Radisson 25 to 64, Capt. Molly Kool 35 to 75, Martha L. Black 43 to 76, Sir John Franklin 13 to 62, Donjek 24 to 77. Martha L. Black and Capt. Molly Kool were wrong by 15 to 25 percent of the hull length.
- **Funnels, masts, hangars, helidecks, cranes** are placed from the same photographs; masts take the ship's own colour (orange on the St-Laurent and Radisson, black on Terry Fox and Capt. Molly Kool).
- **Livery**: one wide white diagonal bar (6 to 12 percent of the hull length) edged with thin dark lines, raked 60 degrees, sitting 28 to 70 percent back from the bow. The old thin double bar was always 17 to 22 percent back.
- **Game draught** is capped at 5 to 5.5 m (the cove's seabed is 9.3 m down), with the bow rise given in metres.

`generators/pg_marine_v1.py` is the generator before the audit.

## Rebuilding

Blender is not installed system-wide; a portable copy lives in `_tools/` (not in git).

```
blender -b --python generators/build_ccg_all.py -- <game assets dir> <Model Library marine dir>
blender -b --python generators/ccg_review.py -- <out dir> pg_marine louis_st_laurent terry_fox   # side / plan / 3q renders
blender -b --python generators/blend_pack.py -- out.blend "Title" a.glb b.glb ...
python generators/compose_sheets.py <render dir> <sheets dir>                                      # contact sheet + to-scale lineup
blender -b --python generators/people_sheet.py -- people.glb people_sheet.png 8                    # the people sheet
```

`build_ccg_all.py` writes `ccg.glb` (Bay, Hero, hovercraft) and `ccgfleet.glb` (the eight larger ships, loaded by the game the first time one is placed). Base64 encode them into `assets/*.glb.b64.txt`.

## Notes

- **Terrain and sky are not here.** The game builds its island from `assets/terrain_257.f32.b64.txt` and uses `assets/sky_2k.jpg`. The terrain generator is `generators/build_terrain.py`.
- **Where the models come from.**
  - `generators/` holds the Python scripts that build every model: `pg_*.py` are the model libraries and `build_*.py` and `export_*.py` the batch builders.
  - Those scripts are the source of truth. Hand edits made in these .blend files stay in the files; to keep one, re-export the GLB, or change the generator and rebuild.
- **Frames.** Scenes are Z up. glTF export with "+Y Up" gives the game's frame.

## Animated ship parts (v4.4)

The Coast Guard ships now export a few moving parts as their own nodes, named `<gamekey>_<part>N`: `radar` (spins), `flag` (a pennant that streams downwind), and on the hovercraft `propL` and `propR` (spin with the throttle). Each part's origin sits on its pivot. `generators/pg_marine.py` builds them (`pivoted`, `flag_on`, the `ANIM` list) and `build_ccg_all.py` names and exports them. The game finds them by name in `makeBoat` and moves them in `updateBoatParts`.
