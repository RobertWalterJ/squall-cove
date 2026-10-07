# Map vibrancy audit: Port, Urban port, Desert, Cove

Read-only audit, 7 Oct 2026. Nothing in `index.html` or any asset was changed. No browser, Blender or git was used.

How the numbers were made, so you can trust or discount them:

* **Layout counts and occupancy grids** come from a node harness that runs the *real* `layoutUrban`, `layoutDesert`, `mapPut`, `mapFits`, `urbanRoads`, `desertRoads`, `roadDense`, `urbanTrees`, `desertTrees` text cut out of `index.html`, with the terrain replaced by a stub (flat plateau at 4.0 m, quay at 1.6 m, water elsewhere). It reproduces the owner's own harness exactly for the prop totals (urban 306 big + 170 tiny, desert 89 + 101). Slope and oasis-pond rejections are ignored, which is why desert rejections differ by one or two. Scripts are in the session scratchpad only (`h.js`, `run.js`).
* **Draw calls and triangles** are the placed counts multiplied by the real primitive and triangle counts read out of `assets/port.glb.b64.txt` and `props2.glb.b64.txt` (every building is 7 to 9 primitives, one per material). `place()` clones the node and adds it to the scene as its own group, so one primitive is one draw call. Port and Cove draw calls are **estimates** (they need `genTerrain` and a browser).
* **Screenshots viewed**: `sc_shots/urban_1..5.jpg`, `desert_1..5.jpg`, `qa/qa_05.jpg`, `qa/qa_08.jpg` (Port, old). All are daytime or hazy, none at night, none at street level on the new maps, none during a battle. Nothing about battle visuals or night was seen; those sections come from code.
* Headless frame times in `sc_shots/urban.json` (9.6 ms) and `desert.json` (4.6 ms) show the urban map costs about twice the desert before any vibrancy is added. They are software-rendered, so use them only as a ratio.

---

## 0. Headline findings

1. **The urban map reads as a model railway because every block is one grey tiled slab.** All 35 blocks, the dock yard, apron and piers are `pavedGrid('concrete', ..., tile 8)` with the same material. The 8 m tile is plainly visible in every screenshot, there is no tint per block, no kerb, no pavement, no yard grass. Only the two parks (which are *not* paved) look alive. This is the single biggest visual problem and it is nearly free to fix.
2. **Variety is three houses and one office.** Of 306 big props in the urban plan, 121 are `b-house-a/b/c` and 53 are `b-office` (57 % between four models). Models are placed at scale 1.0 (`fixed` items), yaw in multiples of 90 degrees, no per-instance colour. Total distinct building models in the game: 14.
3. **The desert is empty by design but nothing fills the empty.** 85 % of 32 m land cells hold nothing; the median distance from a random land point to the nearest prop or tree is **54 m** (urban: 13 m); 44 % of the land is more than 60 m from anything. 34 trees on 45 ha. No scrub, no tracks of use, no animals, one terrain colour.
4. **Almost nothing moves.** The only animated prop in the whole game is the windmill (`SPINNERS`). Flags are static planes (`makeFlag`), cranes are single-mesh models (cannot be animated), no chimney smoke, no birds (only the sound bed `amb_gulls`), no animals, no window or lamp light at night (zero lights and zero emissive materials; `glass` is a plain `#2b3c4b`), no ambient aircraft, no moving boats on the new maps (4 and 3 anchored boats), 12 and 9 civilians.
5. **There is no day/night cycle.** `wx.sky` is only changed by the tray chips and scripted events. The dusk and night presets exist but nobody sees them unless they ask.
6. **The coast is a razor-straight rectangle on both new maps.** `genTerrain` uses `sd = Math.min(335 - |x|, z + 335, COAST - z) + wob` with `wob` only on the south coast and only 5 to 6 m. North, east and west are ruler lines. There is also a pale turquoise "shelf ring" round the island that makes the edge look like a tray.
7. **Draw calls are the budget problem, not triangles.** Urban props alone are about **2,860 draw calls and 236 k triangles (desktop), 1,760 and 165 k (phone)**, plus about 480 static physics bodies, before terrain, roads (about 76 ribbon meshes plus 80 to 150 junction patches), people and effects. A phone should be near 600 to 800 total. **Instancing plus a vertex-colour bake is a prerequisite to adding any detail.**
8. **Battle life is thin.** 9 bots a side on desktop, 5 on phones (`BATTLE.size`, line 4364) on a 768 m map. Craters are refused on anything `asphalt` or `concrete` (`crater()`), and every urban block is "concrete" (`BM().concrete = inPaved`), so an urban battle leaves **no ground memory at all**. No wrecks, no casings, no scorch decals on paved ground (scorch exists only through `heatGround`/ash on soft terrain).
9. **Sound is the cheapest life you are not using.** The urban map gets `amb_town` and `amb_quay` beds; the desert gets only `amb_quay`; all land also gets the global `bed:forest` and, by day, `bed:birds` (amb_birds_day) (code at line 591), which is wrong in a desert or a paved city. The manifest already contains unused one-shots that suit these maps (`mat_metal_clang_l`, `ppl_hammer_tap`, `veh_horn_*`, `veh_ship_bell`, `veh_buoy_bell`, `ppl_radio_chatter_loop`, `elec_hum_loop`, `ppl_murmur`, `ppl_laugh`, `ppl_whistle`, `mat_metal_chain_rattle`).
10. **Shaded sides of buildings go black** in the shots (urban_2, urban_4, desert_4: offices and houses are near-black silhouettes against the haze). Not strictly vibrancy but it kills colour; likely low `hemi`/`envI` in the sky preset used for the shots. Worth one look when the lighting pass is done.

---

## 1. Density and variety

### 1.1 Numbers per map

Map area 768 x 768 m = 59 ha. "Big" = building-size props, "tiny" = benches, lamps, fences, barriers, pallets and so on (the `PUTS` split in `mapPut`).

| | Urban (desktop) | Urban (phone) | Desert | Port | Cove |
|---|---|---|---|---|---|
| Land area | 37 ha | 37 ha | 45 ha | about 25 to 30 ha (est.) | about 4 to 6 ha (est.) |
| Big props | 306 | 202 | 89 | about 140 (per MAP-URBAN-DESERT) | few (pier, harbour kit) |
| Tiny props | 170 | 110 | 101 | about 90 | none |
| Props per ha | 12.9 (8.3 big) | 8.5 (5.5 big) | 4.2 (2.0 big) | about 8 to 9 (est.) | < 3 |
| Trees | 231 | 236 | 34 | up to 3,640 high / 2,380 low scatter, plus designed planting, hard cap 4,600 | 340 to 520 |
| Trees per ha | 6.3 | 6.4 | 0.75 | high (about 100+) | about 80 to 100 |
| Footprint cover | 8.0 % | 5.5 % | 1.5 % | n/a | n/a |
| Empty 32 m cells (nothing in them) | 26 % | 36 % | **85 %** | n/a | n/a |
| Cells with 0 to 2 things | 46 % | 45 % | 95 % | n/a | n/a |
| Median distance to nearest prop or tree | 13 m | 15 m | **54 m** | n/a | n/a |
| Land more than 30 m from anything | 9 % | 13 % | 72 % | n/a | n/a |
| Land more than 60 m from anything | 0 % | 0 % | 44 % | n/a | n/a |
| Ambient civilians placed | 12 (+ 2 skipper crews) | same | 9 (+ crews) | about 54 | few |
| Boats | 4 anchored | 4 | 3 | 11 | 1 to 2 |
| Vehicles | 2 | 2 | 2 | 3 to 4 | 0 |
| Battle bots per side | 9 | 5 | 9 | 9 | no battle |

(Reference: a dense Ravenfield-style town map runs 30 to 60 props per ha in the contested area. The urban map's problem is not count but sameness and flatness; the desert's problem is plain emptiness.)

### 1.2 Distribution

Occupancy grids at 32 m (digits = count of props plus trees in the cell, `.` = empty land, `~` = water). Rows run north (top) to south (bottom).

Urban, desktop:

```
 2 1 5 4 5 3 . . . 1 1 1 1 . 1 6 4 4 2 .
 . . 1 1 2 . . . . 3 . . . . . 2 1 1 . .
 . . 1 3 1 . 1 1 . 1 1 . . 1 . 2 3 . . 1
 . 3 1 1 2 2 5 3 . 1 1 2 . 3 1 . . . 2 .
 2 2 1 . 1 6 9 8 . 1 1 1 3 . 2 3 2 1 . .
 ...                                    (the middle three rows hold 2 to 8 per cell)
 . . 1 2 2 1 5 6 1 1 1 . . . . 2 2 1 2 .      near the south
 2 5 . . . . 5 . . . . . 6 . . . . 1 6 .      the quay row: cranes and warehouses with gaps of 80 to 130 m
```

Findings:

* **Clustering.** Objects hug the block edges (`rowX`/`colZ` put rows against the street) and the block centres are empty slab: every block shows a rectangle of grey with a fringe of buildings. Dense cells are 6 to 9 only where `oldtown`, the quay or the container yards are. The "lot" blocks (about a quarter of the map, the whole west and east columns) have 1 to 3 props.
* **Empty zones, urban.** 95 of 360 cells are empty. They are the centres of `lot`, `rail`, `stadium` (pitch), `square`, the north barracks centre and the north half of the map's two edge columns.
* **Desert.** Props exist only at the 9 sites (each a tight pad of 4 to 9 per cell) and along nothing else. The long highway has no poles, no signs, no wrecks, no tyre marks. The wadis (the best cover on the map) have no rocks or scrub in them.
* **Scale variety.** All `fixed` items (all buildings and almost all props) are scale 1.0 (`place()`: `sc = item.id === 'light' || item.fixed ? 1 : ...`). Yaw is 0, 90, 180 or 270 (`rowX` passes 0/180; `colZ` -90/90) except the desert village. Trees do vary (0.7 to 1.2).

### 1.3 Repetition

Urban plan, by model (desktop): house A 57, office 53, fence 48, lamp 39, house B 33, house C 31, bench 22, warehouse 18, green container 18, workshop 15, blue container 13, barrier 12, market stall 12, red container 11, bollard 11, orange container 10, guardhouse 10. Everything else is under 10. So: three houses, one office, one warehouse, one hangar, one tank, one silo, four container colours, one lamp.

Desert plan: fence 38, tent 10, workshop 9, lamp 9, barrier 8, orange container 7, guard 7, tank 7, bunker 7, then a long tail. Houses: 3 + 3 + 3.

### 1.4 Colour variety

Palette of the whole building kit (from the GLB materials, sRGB hex):

* Houses: A white siding with red roof `#893d33`; B yellow siding `#d5be6e` with grey roof `#5d6166`; C stucco `#c1b49a` with dark roof `#3d4146`. Doors `#3f6b50` green, `#a2332f` red, `#8e663b` wood.
* Office: red brick `#9b4b3d` with dark roof. Warehouse and hangar: blue-grey metal `#8ea2ac`, `#adb2b4`. Workshop: grey. Containers: four flat colours.
* Ground: concrete `#a2a29d`-ish tiles, asphalt, sand. Desert terrain is one sand tone.

So the urban map has exactly three roof colours, one brick colour, one metal colour. No two-tone blocks, no neighbourhood character. In the screenshots the brick offices are the only saturated mass and they are identical. Trees are rust-brown (the `broadleaf` models read as dead in urban_5 and urban_3), the only green is the parks.

### 1.5 Night, roofs, windows

* No `PointLight`/`SpotLight` in the file. No emissive material in the GLBs (glass `#2b3c4b` is plain). The only night-aware light is the battle kit lamp cone (`updateStructs`, `s.cone.visible = night or dusk`).
* Roofs are flat colour: no rooftop clutter (no water tanks, AC units, chimneys, dishes, laundry, parapet variation). Houses have no chimney geometry, so smoke would need an asset or an offset guess.
* Streetlamps: 39 urban, 9 desert, none lit.

### 1.6 Signage-free detail inventory

| Detail | Urban | Desert | Port |
|---|---|---|---|
| Laundry lines, washing | none | none | none |
| Fences | 48 sections, only barracks/stadium/yards | 38 sections, around pump station, fuel depot | yard fences |
| Parked things | patrol car 1, cargo truck 1 | same | patrol car, truck, forklift, crane truck |
| Litter, crates, barrels | pallets 4; no litter | pallets 2, tyre stacks 3 | yards stocked with real cargo (good) |
| Hedges | none | none | designed hedgerows along lanes and farms (`portTrees`) |
| Flower beds | none | none | none |
| Street furniture | benches 22, stalls 12, bus stops 2, phone box 1 | stalls 2, benches 2 | benches, stalls, bus stops, picnic tables |
| Vegetation layers | one: a tree every 22 m on 3 avenues and the quay road, parks | oasis only (16 palms, 18 shrubs) | grass blades, shrubs, trees, palms, boulders (best layered of the lot) |

The **Port map** is the only one with several vegetation layers (GPU grass in a 60 m patch around the camera, shrubs, broadleaf, pine, palm, shore boulders) and with stocked, physical yards. The new maps skipped all of that: grass is masked everywhere a block is paved; the desert shader turns grass off (`wS = (1 - wW) * (1 - oas) * ...`).

---

## 2. Life and motion

What exists today, by system:

| Category | Port | Urban | Desert | Notes |
|---|---|---|---|---|
| Ambient people | about 54: guards, builders, dock workers, fishers, hikers, tourists, photographers, foresters, farmers, medic | 12: tourists, photographers, dock workers, hikers | 9: dock workers, hikers, photographers, builders | Roles are POI-driven (`pickPOI`); on the new maps there are no yards, farms or plant sites, so dock workers and builders just "stroll" (`think` fallback, 5 to 18 m) |
| Animals | none visible | none | none | `amb_gulls`, `amb_birds_day` are sound beds only; no bird or fish mesh exists anywhere |
| Flags | cloth is `PlaneGeometry(3.2, 2)`, static (`makeFlag`) | same | same | Only 9 to 11 per map |
| Windmill | rotates (`SPINNERS`, the only animated prop) | none | none | |
| Smoke | none ambient | none | none | `puffSmoke` exists for explosions only |
| Water | shader waves, wake, surf | same | same | fine |
| Wind in vegetation | instanced sway (`swayMaterial`) plus GPU grass | few trees | oasis only | good where there is vegetation |
| Cranes | static single mesh (`quay_crane` has no child nodes) | 4 static | 4 static | cannot animate without a new asset |
| Boats moving | fleets, ferry, smugglers, patrols from `updateFleet`/`lifeTick` | 4 anchored, no routes | 3 anchored | `lifeTick` events (smuggler, salvage, developers) are Port-economy features and mostly inert here |
| Aircraft | battle only (`airAuto`) | battle only | battle only | none ambient |
| Vehicles | cargo truck, forklift, crane truck, patrol car, working | 2 parked | 2 parked | no traffic |
| Dust | none | none | none | no wind-blown sand, no footstep dust, no vehicle dust |
| Day / night | manual chip only | same | same | no auto cycle; climate drives rain automatically (`stepClimate`) but not the sun |
| Lights at night | none | none | none | |

Battle-time life: tracers (`addTracer`/`updateTracers`), impact puffs (`impactFx`), explosions with flash + smoke + sparks (`blast`), burning trees (`updateTreeFire`), craters on soft ground (`crater`), shell hits on boats, AA nests, mortars, aircraft, paratroops. Missing: wrecks, persistent fires on structures, scorch on paved ground, shell casings, rubble from buildings (buildings are indestructible: `place()` creates a static box body), smoke columns that persist, dust from footsteps.

**Particle pool.** `fxS` (smoke, normal blend) is 1,400 particles shared by everything and `fxG` (additive) is 700; `update()` loops all N every frame on the CPU. Twenty chimneys at 2 puffs per second with 5 s life would use 200 particles (14 %) of the pool continuously and compete with battle smoke. Give ambient smoke its own small pool (see item 17).

---

## 3. Terrain and ground shading

**Terrain shader** (`terrainMat`, around line 1190): rule-based weights for wet sand, dry sand, grass, forest floor, granite, strata; `macro` sampled at 180 m and 41 m scale gives about 14 % tonal drift (`alb *= 0.86 + 0.28 * macro.g`) and a 12 % green shift on grass. That is good on the Port map but:

* **Desert** forces `wS = 1 - 0.75 * rock` everywhere except the oasis. Result: one sand colour with soft 14 % macro drift. No dune-crest highlight, no wadi bed colour, no rock-red outcrops, no salt-flat patches, no darker compacted ground round sites, no track wear, no ripple normal (the sand normal map tile is the only micro detail; at distance it reads as flat). Cast shadows of dunes appear as big black blobs in urban/desert shots (desert_2, desert_4) because the sun is low in that preset.
* **Urban** has no terrain visible at all except parks and a 0 to 20 m verge; every block is a flat plateau at exactly 4.0 m with a "paved" overlay (`pavedGrid` lifts 3 cm above terrain, `renderOrder` 0.5, `depthWrite = false`).

**Ground details present or missing**

| Detail | State |
|---|---|
| Road vs shoulder | Road ribbons are laid 5 cm above terrain; `roadGrade` flattens a 6 m shoulder; no kerb, no verge texture. Urban roads sit flush on paved blocks: asphalt on concrete with nothing between |
| Macro texture on paved surfaces | none (the block floors tile `t_concrete` every 8 m with no macro, visible chequer) |
| Paths worn by traffic | none anywhere (no desire lines between sites, no tyre ruts on gravel tracks) |
| Shorelines | wet sand band is good; quay edge is a hard step with no shadow, fenders or ropes |
| Beaches | Port yes (sand by height rule); urban none (the plateau edge is a straight rock-free line); desert a straight 26 m ramp |
| Cliffs | Port north coast; none on new maps |
| Shallows | sea colour ramp is shared; the pale "shelf ring" is visible as a tray rim (also noted in MAP-AUDIT #9) |
| Sand ripples | none |
| Rock outcrops | Port: boulders on steep hills and shore; Desert: 9 bump outcrops (`DES.rocks`) but `buildRocks` places boulders only where `h > 1.8 && slope > 0.2 && hash < 0.5`; no boulder is visible in any desert shot, so the outcrops are bare humps |
| Erosion gullies | wadis are two smooth channels 3 m deep with no colour change or debris |
| Decals | `scatterStains` makes individual meshes (6 to 8 per yard) using one soft blob texture; none on the new maps; no tyre marks, puddles, cracks, paint |
| Scorch / craters | craters only on soft ground; urban battles leave no marks on pavement |

**Square coast** (both new maps): `sd = Math.min(335 - |x|, z + 335, COAST - z) + wob`, `wob = 5 to 6 m * fbm * (1 - sstepP(170 or 200, 230 or 260, z))`. The wobble is masked off at the south on purpose (the quay) and is far too small elsewhere. Beyond the plateau the sea ring is flat water; the horizon shows hills but the island itself is a rectangle with a pale rim. Also affects gameplay: landing and air sectors (`seaAng`, `airAng`) are chosen by `coastPoint` rays from the centre and work because the shape is regular.

---

## 4. Sound ambience per zone

Beds currently driven (global code at line 577 to 595; per-map code in `portAmbience`):

| Bed | Where it plays | Gap |
|---|---|---|
| `amb_sea_*`, `amb_surf_*`, `amb_wind_*` | global, by weather and shore distance | fine |
| `bed:gulls` (`amb_gulls`) | day, near shore (distance to coast, peaks 25 m inland) | no gull mesh to match |
| `bed:birds` (`amb_birds_day`) | any land, day, calm | **plays in the desert and the paved city** |
| `bed:forest` (`amb_forest_air`) | any land, always | **plays in the desert and the paved city** (0.35 gain) |
| `bed:crick` (`amb_crickets_night`) | land, night | wrong for city centre |
| `bed:harbour` (`amb_harbour_far`) | exists in manifest; only code path found is the global block | not placed per zone |
| Port: `amb_farm` (near farms), `amb_town` (near Main Street), `amb_quay` (near yards) | `portAmbience` | only three zones |
| Urban: `amb_town` (centred 0,20 radius 330, floor 0.2), `amb_quay` (0,228, r150) | | one town bed for 35 blocks: stadium, rail yard, barracks, market, old town all sound the same |
| Desert: `amb_quay` (0,268 r140) | | nothing for the wadis, the oil station, the village, the oasis, the camps, the radio outpost |
| Battle: `amb_battle_distant` at 0.5 while `BATTLE.on` | | no direction or proximity to action |

Gaps, by zone (suggested bed or one-shot from the existing manifest first, new recordings after):

* Urban: market and square (`ppl_murmur`, `ppl_laugh`, `ppl_whistle`), stadium (low crowd murmur, whistle, PA), rail yard (`mat_metal_chain_rattle`, `mat_metal_clang_l`, `veh_horn_long` distant), container terminal (`amb_harbour_far`, `mat_metal_clang_l`, `ppl_hammer_tap`), old town (reduced birds, `ppl_murmur`), barracks (`ppl_radio_chatter_loop` spatial, `ppl_shout`), parks (`amb_birds_day` only here).
* Desert: wind bed with sand hiss (`amb_wind_light` low-passed and slowly gusting), no birds or forest, oil pump station (`elec_hum_loop`, `mat_metal_clang_s` slow knock), fuel depot (hum), village (`ppl_murmur` very low, loose-sheet metal), oasis (`amb_birds_day` plus `water_drip`/`water_ripple`), radio outpost (`ppl_radio_chatter_loop`, `elec_hum_loop`), camps (`ppl_radio_*`, `ppl_hammer_tap`).
* New recordings worth commissioning or synthesising: distant diesel generator, desert wind with fine sand, loose corrugated sheet flapping, crow/raven, cicada or insect drone (day, desert), rooster, dog bark pair, goat/sheep bleat, camel groan, distant city hum and traffic horn, PA crackle, train shunting and couplers.

---

## 5. Readability for gameplay

What works: points have a 16 m ring, a 9 m pole, a floating label (`addLabel`) at 9 m, type icon at 11 m; HQ colours via `paintFlag` and `TEAMCOL`; long avenues give MG sight lines; plateau city has fixed 100 m blocks so orientation is easy.

What does not:

* **Landmarks.** Urban has none taller than offices (about 7 m): no tower, no spire, no stack. From a ground position every block reads the same. The stadium is a fence ring and two warehouses with four floodlight towers (a good silhouette from far, but no one sees it from the street). The desert has the radio mast (10 m) and the oil tanks; the dune ridge is the best landmark.
* **Ownership colour-coding** is limited to the flag cloth and ring. Nothing on buildings, nothing at 150 m. A captured point looks the same from the next block.
* **Cover distribution.** Urban: 5 to 9 high buildings per block edge plus barriers and sandbags from `layCover` (`coverList` skips lamps, signs, bollards, pallets). Open ground: every plaza (square, market, stadium pitch, rail yard) is 80 to 100 m of nothing, which is fine as a design but unfurnished. Desert: median 54 m between objects; cover is dunes and wadis, but the wadi floors are bare, so a soldier in a wadi stands in smooth sand against smooth sand with no rocks or debris to read as cover.
* **Colour contrast.** Black-silhouette lighting problem (finding 10) and the all-grey ground reduce unit readability: soldiers (olive and blue) against grey paving are low contrast in urban shots. Grass between buildings, as on the Port map, would help.
* **Sight lines.** Urban: five E-W avenues and six N-S streets are straight 100 to 600 m lines, so the long axes are lethal. Break with a few road "jinks", trees and parked vehicles in the road. Desert: 700 m dunes (3 to 8 m) are good; add telegraph poles and wrecks along the highway as range markers.

---

## 6. Performance cost of vibrancy

### 6.1 Current cost

Static props (placed through `place()` with `shadowAll(node.clone())`; each primitive is its own draw call and a `CANNON.Body` is made for every item with a `box`):

| | Draw calls (props only) | Triangles | Static physics bodies |
|---|---|---|---|
| Urban desktop | **2,860** | 236 k | 476 |
| Urban phone | **1,761** | 165 k | 312 |
| Desert | **831** | 95 k | 190 |
| Port (est.) | about 1,200 to 1,500 | about 150 k | about 230 |
| Cove | < 100 | small | < 10 |

Per-model primitive counts: warehouse 9 prims/1,380 tris, office 9/972, house A/B/C 9,8,9/268 to 376, hangar 7/764, tank 5/1,476, silo 5/1,120, crane 7/852, container 3/748, lamp 4/132, fence 2/384, barrier 3/244, market stall 8/408.

Other draw-call sources on the new maps: road ribbons (38 roads x asphalt + marks = about 76), junction patches (38 junctions, up to 4 sides each, each its own mesh and material clone use: 80 to 150), 35 block floor meshes plus quay/pier floors, gravel yards, `scatterStains` meshes, flag poles and rings and cloth (3 per point x 10), labels, instanced trees (13 variant meshes), instanced rocks (6), grass (1, 42 k blades high / 14 k low, 60 m patch), terrain (1), water (1), sky, two particle `Points`, people (skinned, several each). **Urban touch total is therefore about 2,100 to 2,300 draw calls**; a mid phone budget is 600 to 800, and a fast desktop is comfortable under 2,000.

Shadows: the sun shadow camera is +/-48 m around the player (line 780), so the shadow pass draws only nearby props (frustum culled): acceptable. The cost is in the main pass.

Trees are fine: instanced (about 13 draws) but on the Port map up to 3,640 + designed planting at about 450 tris is 1.5 M+ triangles, the biggest triangle cost of any map and with **no LOD**. Cap or LOD them before adding more.

### 6.2 What to fix first (this is the budget for all the adds below)

1. **Bake each building/prop node into a vertex-colour geometry** (at load, once): for each primitive set a `color` attribute from the material colour and `mergeGeometries` into 1 opaque primitive (and 1 glass primitive if you want a lit window material). Warehouse 9 draws becomes 2. (`BufferGeometryUtils.mergeGeometries` is already available with three; `buildVegetation` shows the pattern for cloning geometry with `matrixWorld`.)
2. **Instance by model and by chunk**: in `mapPut` call `place(itm, {x, z}, {batch: chunkKey})`; `place` then skips `scene.add` and pushes a matrix (and an instance colour) into `IBATCH[id][chunk]`; a new `flushBatches()` at the end of `layMapScenario` builds one `InstancedMesh` per (id, chunk) from the baked geometry, `castShadow = receiveShadow = true`. Use 4 x 4 chunks of 200 m so frustum culling still works. Keep the static `CANNON.Body` per big building (cheap with `SAPBroadphase`), drop it for tiny props (benches, fences, lamps, bollards, hay, tyre stacks) which do not need one (`pushOutOfProps` uses `props`, not bodies). Store `pr.inst = {im, i}` so `erase()` can hide an instance (zero its matrix).
3. **Expected result**: urban desktop props 2,860 draw calls to about 150 to 250; phone about 120 to 200; per-instance colour is free (`instanceColor`).
4. **Particles**: separate 300-particle `fxA` ambient pool, updated only when the camera is within 250 m of an emitter; skip the CPU update loop when the pool is empty.
5. **Birds, crowd, decals** each as one `InstancedMesh` with vertex-shader animation (no per-frame CPU matrix writes except for the orbit update of 20 to 40 birds).
6. **Kerbs**: merge all kerb ribbons into one geometry (1 draw call, not 76).
7. **Junction patches and block floors**: merge into one mesh per material (3 draws instead of 100+).
8. **Phone caps**: `LIFE` budgets by `isTouch`: birds 12, crowd 40, smoke emitters 8, decals 150, boats moving 2.

### 6.3 Budget to hold after adding vibrancy (phone target / desktop target)

| Item | Phone | Desktop |
|---|---|---|
| Total draw calls in view | 700 | 1,600 |
| Triangles in view | 450 k | 1.2 M |
| Static bodies | 250 | 500 |
| Ambient particles alive | 250 | 500 |
| Instanced crowd/birds | 40 / 12 | 120 / 30 |
| Decals | 150 | 400 |
| Real (skinned) ambient people | 12 | 30 |

LOD ideas: swap a house to its bake (already single-prim) beyond 200 m; hide tiny props beyond 120 m (per-chunk `visible` flag by distance); kill grass blades on paved zones (already masked). **Bakes that can be done offline** (outside the game): vertex-colour merged GLBs (`port_baked.glb`), a pre-baked 512 px macro tint texture per map (`tintTex`), AO baked into the vertex colours of buildings and into the paved floors (the terrain already has `bakeAO`).

---

## 7. Improvements: 25 items in 4 phases

Cost key: S = under half a day, M = 1 to 2 days, L = 3 to 5 days. Impact key: 1 to 5 stars on how alive/varied/readable the map becomes per unit effort. All costs are code-only unless it says asset.

### Phase 1: foundation and free wins (about 3 to 4 days total)

1. **Tinted, broken-up block floors.** In `layMapScenario`, replace `fm = PAVE.concrete.clone()` with a material that has `vertexColors = true`, and give `pavedGrid` an optional `tint` argument that writes a per-vertex `color` attribute (base from a per-kind table `BLOCKTINT = { houses:[.95,.93,.88], mixed:[.9,.9,.9], office:[.82,.84,.88], lot:[.72,.7,.68], ware:[.62,.62,.6], rail:[.56,.52,.48], depot:[.66,.66,.64], square:[1,.96,.88], oldtown:[.9,.84,.76], barracks:[.7,.74,.62] }`, multiplied by `0.9 + 0.2 * vnoise(x * 0.05, z * 0.05)`). Also multiply by the existing `macroTex` in the floor material's `onBeforeCompile` at `vWPos.xz / 41.0 + 0.37` to kill the 8 m tile pattern. Impact 5 stars, cost S, zero draw calls.
2. **Stop paving residential blocks.** In `layoutUrban`, the final line `if (k !== 'park' && k !== 'market' && k !== 'stadium') paved.push(b.px)` should also exclude `houses`, half of `mixed`, `oldtown` courtyards and `barracks` (those get a narrow paved forecourt rectangle `[x0, x1, zEdge, zEdge + 9]` and a path strip instead). The terrain shader and GPU grass then show through (as in the two parks, the best-looking blocks in the shots). Add `T` kind `'garden'` for a mix. Impact 5, cost S. Watch the 60 m grass patch budget and `maskGrass` calls.
3. **Kerbs and pavements.** New `buildKerbs()` called at the end of `buildRoadMesh()` on urban only: for every road in `roadDense()` add two 2.2 m ribbons at offset `r.w / 2 + 1.1`, 0.14 m above the road (`+0.14` lifted `y`), `PAVE.concrete` lighter by `vertexColors` (0.95), plus a 0.12 m dark inner edge. Merge into one `BufferGeometry` so all 38 roads cost 1 draw call. Door-to-street readability and the first thing that makes it feel like a street. Impact 5, cost S to M.
4. **Instance and bake props (see 6.2).** `bakeNode(glb, name)`, `IBATCH`, `place(item, p, o)`, `flushBatches()`. Prerequisite for everything else. Impact 2 for looks, 5 for frame rate, cost M.
5. **Per-instance variety.** With item 4 the colour is `instanceColor`: `PALETTE = { house: [0xffffff, 0xe6d3b0, 0xcfd8dc, 0xd9b8a0, 0xb5c4a8], office: [0xffffff, 0xc9a98f, 0xaab4bd], roof tint via vertex colour channels }`. In `mapPut` accept `o.var` and pick `Math.floor(R() * PALETTE[kind].length)` with block bias so a block has a character (one dominant colour per block `b.pal`). Add yaw jitter of +/-3 degrees, height scale 0.92 to 1.12 (y only, so footprints stay valid), and `rowX` random choice among 3 or 4 models plus gaps. Impact 4, cost S once 4 exists. Without item 4, only the material swap is possible: do not clone materials per building.
6. **Night windows and lamps.** In `place()` when a primitive's material name is `glass`, use one shared `GLASS_LIT` (`MeshStandardMaterial`, same colour, `emissive 0xffc27a`) for 60 % of buildings and `GLASS_DARK` for the rest (hash of x,z), and for `lamp_post` heads a shared `LAMP_LIT`. In `stepWeather(dt)` set `GLASS_LIT.emissiveIntensity = night * 1.1 + dusk * 0.5` and `LAMP_LIT.emissiveIntensity = night * 2.5`. Add 40 to 80 additive ground-glow quads (`LIFE.glow`, one `InstancedMesh`, radial gradient texture) under lamps that fade in with the same value. Impact 4 (night only), cost S, no real lights, no draw calls beyond 1.
7. **Waving flags and ownership banners.** `makeFlag`: `new THREE.PlaneGeometry(3.2, 2, 10, 1)`; a function `updateFlags(t)` called from `updateLife(dt)` displaces vertices (`z = sin(x * 2.4 - t * 6 + phase) * 0.28 * (x / 3.2) * (0.4 + wind.ms / 12)`), cloth yaw follows `wind.ang`. In `paintFlag` also tint a banner (two flat cloth panels hung on the nearest 4 buildings in `FOOT` within 28 m, coloured by owner). Impact 3 (flag) and 4 (banners for readability), cost S.
8. **Per-map ambience table and sound fix.** Add `beds: [{ k, f, x, z, r, g }]` to each `BATTLE_MAPS` entry and iterate it in `portAmbience` (`Snd.set('bed:' + k, f, near(x, z, r) * g, { tc: 1.5 })`). In the global block (line 591) gate `bed:forest`, `bed:birds` and `bed:crick` with `!isBattleMap() || MAP.t === 'port' || inGreen(L.x, L.z)` (parks, oasis). Zones from section 4. One-shots in `updateLife`: `LIFE.snd = [{ id, x, z, r, every:[a, b] }]` driven by `Snd.fx(id, x, z, { gain, y })` with a per-zone random timer. Impact 4, cost S.

### Phase 2: place-making (about 5 to 7 days)

9. **Round the coast.** In `genTerrain` urban and desert branches replace the straight `335 - Math.abs(x)` and `z + 335` terms with a warped distance: `const w1 = 26 * (fbm(x / 150 + 4, z / 150 + 9) - 0.5) * 2, w2 = 8 * (fbm(x / 40 + 3, z / 40 + 1) - 0.5) * 2; sd = Math.min(335 - Math.abs(x) + w1 + w2, z + 335 + w1 + w2, URB.COAST - z + wob)`. The urban plateau fills to 318 m, so clamp the inward warp: `w1 = Math.max(w1, -10)`. Add two or three headlands and coves per edge with `bump()`, a sand beach band, rock groups (see 11), and a faint far ring of mainland silhouettes (low-poly ridge ring, 1 mesh, fogged) to hide the straight edge from the sea. Fix the pale shelf ring by tuning `sea = Math.max(-16, -2.2 + sd * 0.075)` (steeper first 20 m). Impact 4, cost M.
10. **Ground tint texture.** Add `tintTex` (257 x 257 `RGBA8`, same grid as `heightTex`), filled in `genTerrain` post pass and sampled once in the terrain fragment shader as `alb *= texture2D(tTint, vUv).rgb`. Desert: wadi beds greyer and darker with gravel tint, dune crests lighter, outcrops red-brown, 3 to 5 pale salt/clay pans, darker compacted ground around each site, desire-line paths between sites (polyline stamps, 3 m wide). Urban: parks green variation, verge strips, worn dirt under barracks tents. Gravel tracks: in `buildRoadMesh` for `r.mat === 'gravel'` add two darker 0.5 m rut ribbons at +/-1.1 m (1 mesh, merged). Impact 5 for the desert, cost M, zero draw calls.
11. **Desert scrub, boulders, dead trees.** New `desertScrub()` called after `scatterVegetation`: 600 to 900 instances of `shrub1..3` (dry tint via `swayMaterial(src.material.clone().color.multiplyScalar(...))`), clustered along `DES.wadis` (distance < 14 m) and around `DES.rocks` and the oasis, plus 120 boulders (`buildRocks` rule loosened: `hill` condition `h > 1.8 && slope > 0.14`, and add shore and wadi-edge spots), 30 dead trees (new asset, see Blender list; interim: `pine` models with brown tint, no leaves impossible: needs asset), `sand_dune_grass` tufts at 400 spots (props2 node exists, 1 prim 460 tris, instance it). Impact 5, cost M, 6 to 10 draw calls total.
12. **Urban green layers.** New `gardenTrees()` in `urbanTrees()`: for each house footprint in `FOOT` (add `id` to the `FOOT.push({ ... })`) put a broadleaf or shrub at the back with 45 % chance and a hedge line (shrub every 2.5 m, scale 0.7) along the front on `houses` and `mixed` blocks; planting beds as flat coloured quads in `LIFE.decals`; fix the rust-brown `broadleaf` read with a seasonal tint (`swayMaterial` colour multiply, green and a few autumn); extend `urbanTrees` avenues to all five avenues and all six streets (every 14 m, alternating species), parks 30 to 60 trees. Budget 600 to 900 trees (about 4 draws, but triangles 400 each = 300 k, so use `shrub` for half). Impact 5, cost M.
13. **Decal layer.** `LIFE.decals`: one `InstancedMesh(PlaneGeometry(1, 1).rotateX(-PI / 2))` with a 512 px atlas drawn on a canvas at start (8 cells: oil stain, tyre mark pair, puddle, crack, hopscotch/painted bay line, leaf litter, paper litter, scorch blob), `polygonOffset` like `stainMat`, 400 cap. Scatter by block kind (parking bays and oil on `lot`/`depot`, leaves under trees, puddles at low spots) and replace the per-mesh `scatterStains`. Battle: in `blast()` push a scorch (radius `R * 1.1`) into a 64-entry ring buffer on any surface, including pavement (fixes "no ground memory"); craters stay soft-ground only. Impact 4, cost M.
14. **Poles and wires.** `buildPoles()`: instanced pole model (60 tris) every 38 m along the desert highway and the four gravel tracks that lead to sites and along urban avenues 1, 3, 5, plus one `LineSegments` of sagging wires (catenary of 5 points per span). Gives rhythm, scale, range-finding, and a silhouette. Impact 4, cost M (needs a 60-tri pole; interim use `x-radio_mast` scaled 0.5, 10 m tall is too tall).
15. **Clutter tables.** `CLUTTER = { urban: { houses: [['x-bench', ...]], market: [...], lot: [['p-pallets', ...], ['x-tyre_stack', ...], ['p-cont-*', 1 to 3 loose]] }, desert: { village: [['x-hay_bale'...], ['x-log_pile'...]], camp: [['x-ammo_crate', ...]] } }` and a `scatterClutter(block)` that calls `mapPut` with `{ tiny: true }` (instanced, no body). 150 to 300 extra items for about 6 extra draw calls after item 4. Add the existing unused `x-ammo_crate`, `x-medkit_box`, `x-hay_rack`, `x-life_ring_post`, `x-jersey_barrier`, `x-sandbag_wall` (placed only in battle covers today) as barricades and yards. Impact 4, cost M.

### Phase 3: life (about 8 to 10 days)

16. **Birds.** `LIFE.birds`: one `InstancedMesh` of a 6-triangle V-bird (`flap = sin(uTime * 9 + aPhase)` applied to the wing vertices in a patched `MeshBasicMaterial`), 24 desktop / 12 phone. Flocks: urban 3 gull flocks orbiting (0,285), (-180,300), (180,300) at 25 to 45 m radius and 12 to 35 m altitude plus 2 pigeon flocks round the squares (0,20) and (-100,115) that scatter on `blast()`; desert 8 gulls at the port, 4 kites circling over the wadis at 60 to 90 m, swallows round the oasis; Port gulls over the harbour. Day only (fade by `wx.sky`), perch on cranes and bollards. Pair with `bed:gulls` positions. Impact 5, cost M, 1 draw call.
17. **Smoke, fire and flare.** `LIFE.smoke = [{ x, y, z, rate, dark, kind }]` into `fxA` (item 4.4): chimney offsets on 12 to 20 houses (urban oldtown and houses), 3 cooking fires and camp fires (`fxG` flame plus `fxA` smoke) at both desert camps and the village, an oil flare at pump-station tank 3 (a tall additive flame + a column of dark smoke, plus `amb_fire_bed` spatial) as the desert's visual landmark, stack smoke at the urban rail yard and the container-terminal generator, burning barrels. Update only within 220 m of the camera. Impact 5, cost M.
18. **Crowd and townsfolk.** (a) `LIFE.crowd`: one `InstancedMesh` of a 90-triangle walker with a vertex-shader walk bob, 40 to 120 figures following polylines on a `NAVLINES` list built from the kerbs (item 3) and plaza loops, pausing at benches and stalls; they hide in battle (`BATTLE.on`) and flee on `blast()` within 40 m. (b) 8 to 20 real NPCs using a new role `Townsfolk` added to `think()` (`pickNode(LIFE.nodes)` with stall/bench/shopfront nodes) for close interaction; dock workers get `LIFE.nodes` at containers since the new maps have no yards. Desert: a herder with 8 sheep/goats around the oasis (asset), patrols between camps. Impact 5, cost L.
19. **Harbour traffic and traffic.** `LIFE.traffic`: 2 to 3 boats on looping routes (use existing `orderTo` + `addWaypoint`), a ferry between the two piers (Urban), a fishing boat trawling with gulls following it, dhow-like boat at the desert port; 2 to 3 cars on urban loops (`makeVehicle('patrolcar', ...)` with `vehGo` routes, parked beside kerbs the rest), a cargo truck shuttle quay to terminal; phone caps 2 boats, 1 vehicle. Impact 4, cost M.
20. **Working cranes (fake until the asset exists).** A looping `LIFE.cranes`: a container mesh (clone of `container_*`, 1 draw) hung under each crane on two thin line segments, travelling quay to ship to stack on a 40 s path with `mat_metal_clang_l` at the touchdown and a `veh_winch` loop (manifest has `veh_winch`); after the asset in section 8, replace with the animated trolley. Impact 4, cost S to M.
21. **Time of day and weather per map.** Optional auto-cycle (off by default, no on-screen timer): `LIFE.tod` advances `wx.sky` through `dawn, day, golden, dusk, night` on a 20-minute loop with `stepWeather`'s existing lerp. Per-map weather presets in `BATTLE_MAPS[t].weather`: desert heat shimmer (fog tint) + dust haze in wind, wind-blown sand streaks (`fxA` lines near the camera in gusts), dust devils (3 `fxS` columns on slow paths); urban drizzle option with wet-road roughness (`PAVE.asphalt.roughness` lerp by `wx.rainAmt`) and puddle decals visible when raining (item 13). Impact 4, cost M.

### Phase 4: battle life, readability and assets (about 6 to 8 days plus art)

22. **Battle residue.** `LIFE.wrecks`: when a vehicle or boat is destroyed or a point changes hands, spawn a persistent burnt hulk (baked vertex-colour models, black) with a low-rate fire + dark smoke (cap 6 active), `LIFE.casings` ring buffer of 300 brass instances ejected in `botFire`/`fpFireGun`, rubble puffs at hit buildings (spray `fxS` with `SURF.concrete`), bullet-hole decals on building faces (item 13), `burnArea` leaves scorch decals on paved ground. Impact 4, cost M.
23. **Dust.** `dustAt(x, z, strength)` into `fxA` from footsteps on `sand`/`gravel` surfaces (`surfaceAt`), from running people, vehicles and shell hits (`SURF` colours already provided), plus lingering dust after `blast()` (spawn 20 particles drifting with `wind.v`). Impact 4 in the desert, cost S.
24. **Readability pass.** Landmarks: per capture point a distinct tall silhouette (urban: clock tower at Town square, stack at Rail yard, stadium floodlights lit at dusk, water tower at Hill park; desert: flare stack at the Pump station, mast at the Radio outpost, minaret-style tower at the Ruined village); ownership beacon (a thin tinted light column, additive `fxG` quad, 40 m tall, fades by distance, hidden in fog) and `instanceColor` roof tint on buildings within 28 m of a captured point (cheap once item 4 exists: write instance colours on `paintFlag`); fix black shaded sides (raise `hemi` and `envI` for `wx.sky` presets or add a sun-opposite fill: `fillLight = DirectionalLight(0x8899aa, 0.25)` with no shadow); add cover to the desert (rocks and hulks along the wadis, 3 to 5 pieces each 40 m); break two avenues with a roundabout or a jinked street to shorten the longest sight lines. Impact 5 for play, cost M.
25. **Blender kit and animals** (section 8): replace stand-ins, add sheep/camel/dog, animated cranes and pumpjacks, rooftop clutter, wrecks, vegetation. Impact 5, cost L (art time, not code).

### Suggested order inside the first week

1. Items 1, 2, 3 (floors, grass blocks, kerbs): the urban map changes character in a day with no assets.
2. Item 4 (instancing) next, because items 5, 6, 12, 15 and 16 all depend on it and the phone budget is already blown.
3. Item 10 and 11 for the desert, the sparsest map.
4. Items 8, 16, 17 (sound table, birds, smoke): the three that make a still image feel alive.

---

## 8. New Blender assets worth commissioning

Triangle budgets are per model for a low-poly flat-shaded look matching the existing kit (house 270 to 380 tris, warehouse 1,380). All should export as single-material or vertex-coloured nodes (for the bake in 6.2), origin at ground centre, front toward +z, names matching `snake_case`. "anim" = needs separate nodes or morph for code animation.

| Asset | Tris | Used for |
|---|---|---|
| **quay_crane_v2** (anim: separate nodes `crane_trolley`, `crane_hook`, `crane_cab`) | 1,600 | working cranes, item 20 |
| **gantry_container_stacker** (anim: `spreader`) | 900 | terminal activity |
| house_terrace_3 (row of three, shared walls) | 700 | oldtown density with one draw |
| house_shop_corner (shop front, awning) | 500 | squares and market quarter |
| apartment_block_4s, apartment_block_6s | 900 / 1,300 | skyline height variety (urban only offers 2-storey offices today) |
| office_tower_10s | 1,400 | landmark and silhouette |
| clock_tower / church_spire | 1,500 | town square landmark (secular option: civic tower) |
| stadium_stand_curved (bowl segment x4) | 2,500 total | real stadium instead of fence ring |
| train_loco + wagon x2 + rail_segment | 900 / 400 each / 120 | rail yard (currently two warehouses) |
| mudbrick_house_a/b/c, compound_courtyard | 250 to 350 each / 600 | desert village that does not look like the port's houses |
| mudbrick_wall_segment, arch_gate, rubble_pile x3, collapsed_wall | 150 to 600 | ruins, cover |
| water_well_and_trough, shade_awning, market_umbrella | 200 / 120 / 200 | oasis and bazaar |
| **roof_clutter_kit**: water_tank, ac_unit, dish, chimney (with smoke offset), skylight, laundry_line | 600 total | every roof, instanced onto building tops |
| laundry_line_balcony, awning_a/b, shutters | 150 / 120 each | facade variation |
| street kit: power_pole (60), street_light_tall (120), traffic_light (150), hydrant (80), bin (80), bollard_chain (100), planter (100), flower_bed (150), kiosk (400), bus_shelter_v2 (300) | 60 to 400 | street furniture |
| vehicles (static, parked, or driven): sedan, hatchback, van, pickup, bus, truck_tarp, tractor | 500 / 450 / 600 / 550 / 900 / 1,100 / 700 | traffic, wrecks (burnt variant by recolour) |
| **wreck_kit**: burnt_car, burnt_truck, burnt_hull_apc, ruined_house_variant of house_a/b/c (roof collapsed), rubble_house | 500 / 900 / 1,100 / 350 each | battle residue |
| vegetation: acacia/tamarisk (500), date_palm_a/b (700), dead_tree_a/b/c (300), dry_bush_a/b (150), reed_clump (100), cactus not needed (region), aloe/agave (120) | | desert and urban variety |
| rock kit: slab_cliff_a/b (800), wadi_boulder_cluster (500), flat_rock (150), gravel_heap (100) | | outcrops, wadi dressing, cliff coast |
| animals: sheep (350, `walk` shape-keys or 2 poses), goat (350), camel (600), dog (400), chicken (150), gull (80, wing up/down morph), crow/kite (80), fish (40) | | herders, birds, harbour life |
| oil kit: pumpjack (700, anim: `beam`), flare_stack (300), pipe_run_straight/elbow (120), manifold (250), storage_tank_floating_roof (900) | | desert pump station as landmark |
| ships: cargo_ship_small (3,000), fishing_trawler (1,200), dhow (800), tug already exists | | harbour life |
| airliner_far (800), light_plane (500) | | ambient fly-bys |
| signage-free decal atlas (PNG, 2048): oil, tyre marks, cracks, puddle, paint bays, leaves, litter, scorch, bullet holes, footpath wear, sand ripples | n/a | item 13 |
| tileable textures: `t_concrete_slab` (no visible tile; 4 variants), `t_asphalt_worn`, `t_sand_ripple_normal`, `t_cobble` | n/a | block variety, plazas |

Total unique new geometry is about 40 to 50 k triangles; with the bake and instancing it adds fewer than 100 draw calls.

---

## 9. What was not measured or seen

* No night shot, no street-level shot on the new maps, no battle shot exists; sections 2, 4, 5 on battle and night come from code only.
* Real land areas and exact tree counts for the Port and the Cove (require `genTerrain` plus the vegetation pass).
* True frame time on the owner's PC and phone; draw calls are computed, not read from `renderer.info`.
* Rock counts on the desert (`buildRocks` rule) were not run; none are visible in any shot.
* Whether the black shading is the sky preset used for the shots or a general ambient light problem.
