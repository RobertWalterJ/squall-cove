# Urban port and Desert: battle maps 2 and 3

Written by the agent that built them. **Nobody has seen these maps yet**: no browser was opened. What was checked is listed under "Checked" and "Not checked" at the end. Everything in `index.html`; no other file changed.

## What was built

* `?map=urban` (Urban port) and `?map=desert` (Desert and far port), both CELL 3 (768 m), both in `const MAPS`, the map picker, the Map tab and the start screen.
* A per-map table, `BATTLE_MAPS = { port, urban, desert }` (data block just under `ROADS_PORT`, marked `/*UD-DATA-START*/`). Each entry has `name`, `points` (`[name, x, z, owner]`), `seaAng` (the sector of coast and sea each side's boat landings use), `airAng` (the sector each side's aircraft and air strikes enter from), `amb` and `concrete(x, z)` (where the ground is paved, for footsteps and craters). The port entry is the old `BPT_DEFS` moved across, unchanged.
* Helpers: `isBattleMap(t)`, `BM()` (the active map's entry, falling back to the port), `angIn([a0, a1])`, `BATTLE_KEYS` (needed before `CELL`).

## Capture points (radius 16 each, as before)

| Map | Blue (Port) bases | Red (raider) bases | Neutral |
|---|---|---|---|
| Urban | Quay West (-190, 224), Quay East (190, 224) | North barracks (-200, -280), North depot (200, -280) | Container terminal (0, 228), Town square (0, 20), Market quarter (-100, 115), Old town (0, -85), The stadium (200, -80), Rail yard (-200, -80), Hill park (-100, -180) |
| Desert | Port quay (-115, 268), Customs yard (115, 268) | Northern camp (-100, -285), Wadi fort (120, -292) | Dune ridge (45, 140), Oil pump station (-200, 75), Fuel depot (160, 30), Ruined village (-20, -60), Oasis (-212, -150), Radio outpost (200, -190) |

Landing and air entry: Urban, blue boats come in from the south coast (angles 1.0 to 2.1), red from the east and north-east (-0.85 to 0.4); aircraft blue from the south, red from the north. Desert, blue from the south coast (the port), red from the north coast (-2.3 to -0.85), same air sectors. The Port map has `seaAng` and `airAng` null, so it behaves as before (random).

## Urban port

* Terrain: one flat plateau at street level (4.0 m), a quay at 1.6 m along the south coast (z 190 to 262) reached by a ramp (z 164 to 190), a deep harbour basin, two piers (x -200..-168 and 100..132, tips at z 326), a low mound under Hill park. No canal or river (skipped on purpose: it would split the bots).
* Roads (`urbanRoads()`, built from the `URB` table): 5 east-west avenues (z -230, -130, -30, 70, 160, 9 m, marked), a quay road (z 196), 6 north-south streets (x -250 to 250, 8 m) built as one segment per block so each segment ends at an avenue, 6 dock streets that run down the ramp, 2 unmarked north lanes. 38 roads. The road mesh ends each street segment at the avenue centreline and puts a clean asphalt patch over the join (`ROAD_JUNCTIONS`, now with one patch per side, so the avenue's lines stop at the street mouth and the street's lines stop at the kerb).
* Blocks: 5 rows by 7 columns, each given a kind in the `T` table inside `layoutUrban`: `houses`, `mixed`, `office`, `oldtown` (dense, rows facing both streets plus a spine row, 3 to 5 m alleys between buildings), `ware`, `rail`, `depot`, `lot` (light industry), `barracks` (red bases: tents, bunkers, fence), `stadium` (fence ring, two stands, four floodlight towers, pitch left as grass), `square` (paved plaza with stalls, benches, bus stops), `park` (Hill park) and `market` (grass square with stalls and tables). Block floors are concrete, except parks and the pitch.
* Quay: four portal cranes, six warehouses, about 50 containers, two guard huts, pallets, lamps along the quay road, bollards, a lighthouse on the east pier, moored boats in the basin, a patrol car and a cargo truck.
* Trees: avenue trees on three avenues and the quay road, plus the parks (`urbanTrees()`); the generic forest scatter is skipped.

## Desert

* Terrain (`genTerrain`, branch `desert`): dunes (soft noise plus ridged crests, 3 to 8 m), flat beside roads and sites, two N-S wadis (dry beds, about 3 m below the dunes, cut off where a road crosses), nine low rock outcrops, the radio hill and the dune ridge (flat tops), a pond at the oasis, a port apron at 1.6 m at the south with a ramp and a harbour basin. Sand everywhere (terrain shader), rock on steep ground, grass only at the oasis (grass shader).
* Roads (`desertRoads()`): a long asphalt "Desert highway" from the quay road at z 246 north through the dunes and the ruined village to the Wadi fort, a quay road, and five gravel tracks (pump station, fuel depot, northern camp, radio outpost, oasis). Roads may carry `mat: 'gravel'`; tracks are drawn 3 cm under the highway.
* Sites (`layoutDesert`): port (cranes, three warehouses, two hangars, containers, lamps, bollards, lighthouse, moored boats), oil pump station (tanks, silos, workshops, fence), fuel depot (tanks, warehouse, towers, pumps), ruined village (houses turned at odd angles, sandbag walls as rubble, stalls), oasis (tents, benches, hay, 16 palms and 18 shrubs round the pond; the only trees on the map), radio outpost on its hill (masts, tower, tents, bunker), northern camp (tents, bunkers, camo nets), Wadi fort (bunkers, towers), dune ridge look-out. Gravel yards (a paved gravel texture, no terrain change) under the sites.

## How placement is kept honest

Every building and prop on these two maps goes through `mapPut(id, x, z, rotDeg, opts)`, which first asks `mapFits`: not in water (the nine sample points of the footprint must be above 0.9 m), not on a slope (spread over 0.7 m), not within 12 m of a capture point (so the points stay open for spawning), not on a road (footprint to every road centreline point must exceed half the road width plus 1 m), not overlapping an earlier footprint (oriented-rectangle test, 0.8 m margin). A thing that does not fit is skipped and counted in `PUTS.rej` (also `window.__layout` after the scenario is laid). Footprints are kept in `FOOT`; `footBlocked(x, z, pad)` is used by bot spawning (`spawnBot`), the cover ring (`layCover`) and the AA and MG nests (`layAA`, which turns the nest round the point until it is clear), so nobody spawns inside a building. On the Port map `FOOT` is empty and those checks do nothing.

Prop limits (`PUTS`, in the data block): desktop 320 big and 170 small props, phones 220 and 110 (the Port map is roughly 140 big and 90 small, estimated from its code, not counted). The urban layout plans slightly more than the limit; the blocks are built in a shuffled order so any shortfall is spread evenly. Tune with `PUTS.capN`, `PUTS.capTiny` and `DS` inside `layoutUrban`. Desert uses about 90 big and 100 small props.

## Functions and places touched

New: `BATTLE_MAPS`, `isBattleMap`, `BM`, `angIn`, `URB`, `urbanRoads`, `urbanStamp`, `DES`, `desertRoads`, `desertStamp`, `MAPGEN`, `roadProbe`, `obbOverlap`, `pointBoxDist`, `footBlocked`, `mapFits`, `mapPut`, `clearTreesRect`, `layoutUrban`, `layoutDesert`, `layMapScenario`, `offerBattleMaps`, `mapTreeAdd`, `urbanTrees`, `desertTrees`, `FOOT`, `PUTS`, `PAVED`, `inPaved`. Markers `/*UD-DATA-START*/ ... /*UD-DATA-END*/` and `/*UD-LAYOUT-START*/ ... /*UD-LAYOUT-END*/` fence the two new blocks.

Changed: `CELL` (any battle map is 3), `MAPS`, `ROADS` and `ROAD_JUNCTIONS` (now chosen per map; the port's are `ROADS_PORT` and `JUNC_PORT`), `roadDense` (bounding boxes), `roadGrade` (same result, culled by bounding box so a street grid stays quick), `genTerrain` (branches `urban` and `desert`, shared battle-map edge and depth rules, post-pass stamp per map), terrain shader (desert sand and oasis), grass shader (oasis only), `scatterVegetation` and `buildRocks` (desert boulders), water shader floor depth, `buildRoadMesh` (gravel material, one junction patch per side), `surfaceAt` and the footstep surface (any battle map), `battleStart`, `playBattle`, `spawnBot`, `layCover`, `layAA`, `landingSpot(side)`, `edgeSpot(side)`, `landingParty`, `airSpawn`, `callStrike`, `portAmbience` (urban and desert beds), `addLabel` (shrinks long names), `renderSide` (Battle tab only on battle maps; Map tab lists the points on the new maps and offers the three battle maps elsewhere), start screen (Urban port and Desert cards; the Battle card reads "Battle on this map" and is hidden on maps without battles; `go()` handles the new values), version line, `window.__sc` (adds `isBattleMap, BM, BATTLE_MAPS, FOOT, PUTS, PAVED, layMapScenario, mapPut, footBlocked`).

Menus: `playBattle` and `battleStart` no longer force the port; on a map without battles they toast and open the Map tab, which offers the three battle maps. Still true: the tablet's battle rows only exist while `BATTLE.on`, so they cannot appear on a map without a battle.

## Checked

* `node --check` on the module script after every batch: clean.
* A static scope check (acorn): no undeclared identifiers and no load-time use of a `const`/`let` before its declaration for any new name.
* A node harness that runs the real `genTerrain` and the real layout functions on the extracted code (stubbed `place`): terrain heights at every capture point and site, land share (urban 68 %, desert 70 %), placement counts and rejection reasons, PNG plans of both maps (1 px per metre) which were looked at for road grid, block kinds, points, footprints, quay and trees. The numbers in this note come from that harness.

## Not checked (the assistant's tests should look at these first)

* **Nothing has been rendered.** All visuals are unseen: terrain colour, dunes, wadis, the oasis pond, road markings and junction patches, block floors against roads (floors use `depthWrite = false` and render order 0.5; roads are 1) and the quay.
* Building orientation assumes a model's front is local +z (as the Port map's own houses do). If houses face away from the street, flip the 180 and 0 in `rowX`, and 90 and -90 in `colZ`.
* Crane footprint is guessed (`box: [7, 6]`) and boats at the quay (positions and depth) have not been seen.
* Bot behaviour in the street grid (detours round buildings, stuck handling, capture flow) and air, paratrooper and landing behaviour on the new coasts are untested. Landing spots depend on `coastPoint` rays from the world centre; the sectors in `seaAng` were chosen so the first water on each ray is open sea, but nothing was run.
* Frame rate, especially the dense urban plan (about 300 props) on desktop and phones, and the load time of `genTerrain` for the desert (about 0.6 s in node).
* Edge-of-world: the sea ring is the same as the Port map (the land ends 20 to 45 m inside the map edge).
* The urban plan skips a canal or river on purpose. Stadium is a fenced grass pitch with two stands, not a bowl.
* `place()` plays a placement sound per prop; the sound engine rate-limits it, but it has not been heard.
