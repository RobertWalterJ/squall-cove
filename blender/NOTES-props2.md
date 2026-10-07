# Squall Cove props, set 2

28 static nodes in one GLB: `assets/props2.glb.b64.txt` (714 KB GLB, 952 KB one-line base64, 12,364 triangles in total, none over 1,040).
Source: `blender/generators/build_props2.py` (uses `pg_set2.py`, `pg_core.py`). Manifest: `blender/review/props2/props2.json`. One 3/4 render per node in `blender/review/props2/`.

Rebuild: `_tools/blender-4.2.9-windows-x64/blender.exe -b --python blender/generators/build_props2.py -- --review` (`--only barn,bench` builds a subset without overwriting the asset).

## Conventions

Same as the port set. One top-level mesh node per name, origin at the centre of the footprint, bottom at y = 0 (rod end caps within 5 cm below the ground are flattened to 0). Flat base-colour materials, no textures, shared names across nodes. Long axis along +X unless noted. Blender +y = three -z, so "front" below is given in three axes.

Materials worth knowing: `flag` (flagpole cloth, pure white, **double sided**, for the game to tint on a cloned material), `camo1/2/3` (net, double sided), `dune` (grass, double sided), `glass` (dark blue-grey, opaque).

## Nodes (width x height x depth in metres, three x, y, z)

| Node | W x H x D | Tris | Notes |
|---|---|---|---|
| sandbag_wall | 2.99 x 1.10 x 0.62 | 624 | 3 m, 8 courses, two tan shades, tapers from 0.6 to 0.46 m thick toward the top |
| jersey_barrier | 3.00 x 0.81 x 0.60 | 112 | concrete, classic profile, orange reflectors on both faces |
| ammo_crate | 0.86 x 0.37 x 0.45 | 144 | olive, steel handles on the two ends, yellow stencil panel on both long sides. The box is 0.8 m long, handles add 0.06 |
| medkit_box | 0.50 x 0.39 x 0.19 | 156 | white, red cross on both faces (+Z and -Z), handle on top |
| flagpole | 2.15 x 8.00 x 0.60 | 208 | 8.0 m pole with ball finial and concrete footing plate; flag 1.8 x 1.1 m streams toward +X from the top, material `flag` |
| market_stall | 3.00 x 2.70 x 1.96 | 408 | red and cream striped awning; counter and produce crates face three +Z, back shelf and back fall at -Z |
| bench | 1.80 x 0.92 x 0.57 | 168 | wooden; seat faces +Z, backrest on the -Z side |
| hay_bale | 1.50 x 1.50 x 1.23 | 380 | round bale lying on its side, axis along Z (1.2 m wide), two twine bands |
| picnic_table | 1.80 x 0.76 x 1.50 | 156 | table and two benches, A-frame legs |
| tyre_stack | 0.73 x 0.66 x 0.72 | 672 | three car tyres, slightly offset and rotated |
| log_pile | 2.08 x 1.08 x 1.20 | 840 | 10 logs (4-3-2-1), about 2 m long, pale cut ends, along X |
| rowboat_beached | 3.58 x 0.67 x 1.44 | 348 | hollow hull on a keel strip, blue outside, thwarts, oars, rowlocks, two stone chocks; bow toward +X, closed transom at -X; the bow lifts slightly off the ground (keel rocker) |
| fishing_hut | 4.60 x 4.37 x 3.96 | 616 | shack body 4 x 3 m on 6 stilts (deck 1.2 m up), grey gabled roof; door and front window on the -Z side, ladder at the +X end of that side. Bounding box includes roof overhang (4.6) and ladder (4.37 deep) |
| jetty_section | 8.00 x 1.46 x 3.08 | 1040 | 8 x 3 m, deck top at **1.2 m**; the node bottom (y = 0) is the sea or river bed. 10 piles, 40 deck boards, four bollards, rubbing rails. Place so y = 0 is the bed, or the deck sits 1.2 m above whatever y = 0 is |
| life_ring_post | 0.53 x 1.65 x 0.31 | 312 | 1.6 m post, red and white ring on the +Z side |
| signboard | 1.50 x 2.30 x 0.14 | 120 | 1.5 m board on a single 2.3 m post, cream face with three black text bars, both sides |
| windmill | 6.37 x 12.40 x 3.33 | 568 | farm windmill without its wheel: 10.8 m lattice tower, head, tail boom and vane (trailing toward +X), pump rod. See pairing below |
| windmill_blades | 0.40 x 4.96 x 4.88 | 604 | 18-blade wheel, radius 2.5, axle along X. **Origin is the hub**: node translation (-0.55, 11.5, 0) in three |
| water_tower | 5.43 x 14.00 x 5.50 | 880 | steel lattice stand 10 m, tank and dome top at 14.0 m, ladder on the three -Z face |
| barn | 14.02 x 8.00 x 8.93 | 408 | red gambrel barn, long axis X; big doors with white X-braces and a hay-loft door on the **+X end**; windows on both long sides. 8.93 deep includes the roof eaves (body 8.6) |
| hay_rack | 3.00 x 1.18 x 1.32 | 480 | cattle feeding frame, V of slats, hay inside |
| fuel_pump | 1.40 x 2.20 x 0.90 | 304 | pump on a concrete island, hose and holster on the +X side, two yellow bollards at the island ends |
| phone_box | 1.00 x 2.40 x 1.05 | 492 | red kiosk, glazed on all four sides, 1.05 deep includes the door handle on the -Z face |
| bus_stop | 3.15 x 3.26 x 1.50 | 244 | shelter 3 x 1.5 m, 2.5 m high, glass back (-Z side) and left end, bench, timetable panel; 3.26 m is the stop sign on its own pole at the +X front corner |
| tent_large | 8.14 x 4.05 x 5.10 | 220 | olive command tent 8 x 5 x 4, ridge along X, dark door opening on the +X end, window patches on both sides, no guy ropes |
| camo_net | 6.04 x 3.00 x 5.04 | 568 | draped sheet (double sided, three greens) on two poles at x = +-2.5 (top 3.0 m); lower edges hang to 0.3 m |
| radio_mast | 1.80 x 20.00 x 1.60 | 832 | triangular lattice, red and white bays to 18.6 m, whip to 20.0 m, two dishes and a panel on the +X side, concrete footing |
| sand_dune_grass | 0.96 x 0.90 x 0.89 | 460 | 46 curved blades, single mesh, single material `dune`, double sided; 0.9 m tall at the tallest blade |

## windmill and windmill_blades

Both nodes share one frame (windmill base on the ground at the origin). Put them in one group at the same transform. `windmill_blades` carries its own translation to the hub (three (-0.55, 11.5, 0)) and its mesh is centred on that point, so rotating the node about its **local X axis** spins the wheel in place. The wheel faces -X; rotate the whole group about Y to face the wind (the vane trails toward +X). Assembled height is 14.0 m (wheel top at 11.5 + 2.5).

## Caveats

- Spec sizes are met on the main body. Extras (roof overhangs, ladders, handles, poles) enlarge some bounding boxes; the table says where.
- Flat-shaded and low poly: windows and doors are coloured boxes standing a few centimetres proud, not cut-outs.
- Thin lattice members (radio_mast, windmill, water_tower) are 3 to 6 sided rods: they read well up close and at mid distance but will shimmer at long range, where a billboard or hiding them is better.
- `flag`, `camo*`, `dune` are double sided in the GLB; all other materials are single sided.
- Review renders use Workbench studio lighting, so in-game PBR will look warmer.
