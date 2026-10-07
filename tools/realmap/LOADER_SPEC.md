# Loader specification for `assets/map_<id>.json`

For the game integrator. Files: `assets/map_lemnos_myrina.json`, `map_lemnos_mudros.json`, `map_lemnos_airport.json` (each well under 3 MB).
Every file carries the `attribution` string (OSM ODbL + Mapzen terrain); the game must show it somewhere (map screen / credits).

## Coordinates (match index.html: `TN = 257`, `TH = 128`, battle maps `CELL = 3`)

* World metres, **x east, z south**, origin at the map centre. `center_lat_lon` is that origin.
* `W2G(x) = x/CELL + 128`, `G2W(j) = (j-128)*CELL`. Heights are **row-major `h[i*257 + j]`**, `i` = z index (row), `j` = x index. So `h[i*257+j]` is the ground at world `x=(j-128)*3, z=(i-128)*3`. The map spans +-384 m (768 m square), `cell_m = 3`.
* All vector coordinates in the file (`p` arrays, `x`/`z`/`cx`/`cz`) are in the **same world metres**; a polyline `p` is a flat array `[x0,z0,x1,z1,...]`. No conversion needed. Rotation: `rot` (radians) is the angle of the building's long axis measured from +x toward +z (clockwise seen from above with z south), range [0, pi).
* Sea level = 0 m. Heights are metres above sea level (geoid-referenced Terrarium data, so no datum shift). Dry land is `>= 0.25`; water cells are `<= -0.2`, sea floor reaches `-9` at about 130 m from shore (inland salt water is capped at -2.5). The game clamps terraforming at `-9.2 .. 34`: **raise the upper clamp (e.g. to 120) on real maps** or hills will be flattened by the first crater (index.html ~line 6628, and `clamp(HGT[k], ...)` sites near 4329/2152).

## Feeding the heights to `genTerrain`

```js
// in index.html, next to: if (MAP.t !== 'cove') genTerrain(HGT, MAP.t, MAP.seed) ...
function decodeH(b64) {                       // Float32 little endian, 257*257
  const bin = atob(b64), u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return new Float32Array(u8.buffer);         // browsers are little endian
}
if (MAP.real) {                               // e.g. MAP.t === 'lemnos_myrina'
  const d = await (await fetch(`assets/map_${MAP.t}.json`)).json();
  HGT.set(decodeH(d.h));                      // instead of genTerrain(HGT, ...)
  REAL = d;                                   // keep for buildings/roads/points
}
```
Because `genTerrain` is synchronous and `fetch` is not, fetch the JSON before terrain generation (or embed the three files in a `.js` module). The existing post-step `if (CELL > 1) HGT *= 1.45` applies only to the `cove` template; do not apply it to real maps. Do not run `genTerrain` at all for real maps (it would overwrite the data); everything after it (AO, normals, water depth, material masks) runs as usual off `HGT`.

## JSON schema (`format: "squallcove-realmap/1"`)

| key | type | meaning |
|---|---|---|
| `id`, `attribution`, `center_lat_lon [lat,lon]`, `size_m` (768), `cell_m` (3), `grid` (257), `coords` (text) | | header |
| `h` | base64 | Float32Array LE, 257x257, metres |
| `coast` | `[[x,z,...],...]` | OSM coastline polylines clipped to the window. Land is on the LEFT of travel in a y-north frame, i.e. on the RIGHT in the game's z-south frame. Informational: the heightfield already encodes land/sea |
| `roads` | `[{c, n, w, s, br, tn, oneway, p}]` | `c` OSM highway class (motorway, trunk, primary, secondary, tertiary, unclassified, residential, living_street, service, track, path, footway, steps, pedestrian...), `n` name, `w` suggested width in m, `s` surface tag, `br` bridge, `tn` tunnel, `p` polyline |
| `buildings` | `[{t, m, lv, ht, n, cx, cz, w, d, rot, a, p}]` | `t` raw OSM building tag, **`m` suggested game model** (table below), `lv` levels (0 unknown), `ht` height in m (0 unknown), `n` name, `cx,cz` centre, `w` long side, `d` short side (min-area bounding rectangle), `rot` radians, `a` footprint area m2, `p` footprint polygon (open ring) |
| `landcover` | `[{k, a, p, n?}]` | polygons (clipped to the window). `k` in: forest, farmland, grass, scrub, orchard, vineyard, urban, industrial, military, harbour, rock, beach, water, bay, wetland, bare, cemetery, pitch, parking, airfield, apron, runway_area, taxiway_area, site. Use for ground material masks and vegetation density (scrub/forest -> trees, farmland -> crop rows, beach -> sand texture, rock -> cliff texture, urban/industrial/apron -> concrete or asphalt) |
| `harbour` | `[{k, n, w, p, closed}]` | piers, quays, breakwaters, docks, jetties (`k`: pier, quay, breakwater, groyne, jetty, dock...) as polylines of width `w` (default 5 m). Place `jetty_section` / flat concrete decks along them; boats berth along quays |
| `aeroways` | `[{k, ref, w, p}]` | `k` runway / taxiway / taxilane; `w` width in m. Paint asphalt + markings (existing `t_road_markings`), flatten nothing: the real runway is already flat in the DEM |
| `towers` | `[{k, n, h, x, z, r}]` | water_tower, tower, mast, lighthouse, chimney, storage_tank, silo, windmill, power_tower, wind_turbine, crane. `r` = radius for tank footprints |
| `places` | `[{k, n, x, z}]` | place names (town, village, suburb, locality ...) |
| `poi` | `[{k, n, x, z, ele?}]` | named peaks, capes, beaches, fuel, churches, ferry terminals, military nodes etc. |
| `water_lines` | `[{k, n, p}]` | streams, ditches |
| `barriers`, `power`, `rail` | polylines | walls/fences, power lines, railway |
| `stats` | | build summary (counts, slope share) |

Points of interest for gameplay (`points`) are **not** in the JSON; they are hand-chosen and validated per map in `tools/realmap/points_<id>.json` and listed in `MAPS.md` (format `{id,type,side,x,z}`; copy them into the map template).

## Placing buildings

For each `b` in `buildings`:

1. Model = `b.m` (already chosen by the tool: tag first, else footprint size). Spawn at `(b.cx, heightAt(b.cx,b.cz), b.cz)`; set the base height to the **minimum** `heightAt` over the 4 footprint corners so the building is never buried on slopes (add a skirt/foundation if the slope across the footprint exceeds 1 m).
2. Rotation about Y: the model's long axis lies along local +x (as in port.glb). World yaw `= -b.rot` (three.js rotation.y is counter-clockwise seen from above with +z towards the viewer; our `rot` is measured from +x toward +z, hence the minus sign). If a model is long along z, add pi/2. Verify with one building and flip the sign if it is mirrored.
3. Scale: `sx = b.w / model.w`, `sz = b.d / model.d`, clamp each to `[0.6, 2.2]`; if the clamp bites, still honour the footprint for collision/occupancy and just let the model be smaller/larger. Height scale `sy`: if `b.ht` or `b.lv` known use `ht = b.ht || b.lv*3.2`, `sy = clamp(ht / model.h, 0.7, 2.5)`; else `sy = 1`. House models: pick `house_a/b/c` by area (already encoded in `m`).
4. Skip buildings with `a < 12` m2 and any whose centre is in water (`heightAt <= 0.2`). Cap total buildings at ~350 for frame rate: sort by area and drop the smallest sheds first. Footprints > 900 m2 that are not warehouse/hangar: use the largest-model scale limits and split into 2-3 instances along the long axis.
5. Mark the footprint (expanded 1.5 m) in the existing `maskGrass`/`noGrassData` mask (index.html ~4328) and add it to the building occupancy so props and capture-point auto-placement avoid it. Collisions: one oriented box per building (`cx, cz, w, d, rot`).

### OSM building tag -> game model (the tool already writes this into `m`)

| OSM `building=` (or tag) | `m` | source file |
|---|---|---|
| hangar, `aeroway=hangar` | `hangar` | port.glb |
| warehouse, industrial, factory, manufacture | `warehouse` | port.glb |
| commercial, retail, office, hotel, public, civic, government, hospital, school, university, supermarket, kindergarten, train_station, transportation, dormitory; apartments/residential with >= 3 levels; untyped >= 350 m2 with >= 3 levels | `office` | port.glb |
| garage(s), shed, hut, cabin, service, carport, roof, greenhouse, barn, farm_auxiliary, stable, boathouse, kiosk, container; untyped < 30 m2 | `workshop` | port.glb (small shed look). For `barn`/`farm_auxiliary` in rural land you may swap to props2 `barn`; for `boathouse` on a pier, props2 `fishing_hut` |
| house, detached, semidetached_house, terrace, residential, yes, untyped: < 100 m2 | `house_a` | port.glb |
| untyped 100-180 m2 (also apartments with <= 2 levels) | `house_b` | port.glb |
| church, chapel, cathedral, monastery, mosque; untyped 180-350 m2 | `house_c` | port.glb (for churches add a small flagpole/tower prop if desired) |
| silo, grain_silo, `man_made=silo` | `silo` | port.glb |
| storage_tank, `man_made=storage_tank` | `fuel_tank` | port.glb |
| tower, watchtower, `man_made=tower` | `watchtower` | port.glb |
| bunker | `bunker` | port.glb |
| any building with a `military=` tag | `guardhouse` | port.glb |
| ruins, collapsed | `ruin` | battle.glb `ruined_house` (or `ruined_wall` along the long side) |
| untyped >= 350 m2 and < 3 levels | `warehouse` | port.glb |
| (area > 12000 m2 outlines such as the Myrina castle) | not a building: written to `landcover` with `k:"site"` | place a `ruined_wall` ring / `bunker_large` / `command_post` set-piece instead |

### Towers and other nodes

| JSON | model |
|---|---|
| `towers` k=`water_tower` | props2 `water_tower` |
| `towers` k=`mast`/`tower`/`power_tower` | props2 `radio_mast` / battle.glb `radio_mast` (the latter doubles as a radio capture point) |
| `towers` k=`lighthouse` | `watchtower` scaled 1.6 on height (no dedicated model) |
| `towers` k=`windmill`/`wind_turbine` | props2 `windmill` + `windmill_blades` (wind_turbine: scale 2.5) |
| `towers` k=`storage_tank` | `fuel_tank` scaled to radius `r` |
| `towers` k=`crane` | port.glb `quay_crane` |
| `towers` k=`chimney`, `silo` | `silo` |
| harbour `quay` polylines | `quay_bollard` every 25 m, `lamp_post` every 40 m, `container_*` stacks / `pallets` on wide quays (port.glb) |
| harbour `pier`, `jetty` | props2 `jetty_section` tiled along the polyline; `fishing_hut` at the root |
| `aeroways` runway ends / apron | battle.glb `windsock`, `helipad`; port.glb `fence_section` around the airfield boundary |
| `poi` k=`fuel` | props2 `fuel_pump` |
| `barriers` | port.glb `fence_section` (fence), battle.glb `ruined_wall` (wall) |

## Roads

Draw each road polyline as an asphalt ribbon of width `w`, draped on the heightfield (drape by sampling `heightAt` every <= 3 m, add 0.05 m). Surface: `s` in {unpaved, gravel, dirt, ground, sand, compacted, grass} or `c` in {track, path} -> gravel texture, else asphalt (`t_asphalt_*`). Skip `tn` (tunnel) segments, and keep bridge segments (`br`) flat and level between their endpoints. Do not draw `footway/steps/cycleway` wider than 1.5 m (or skip them for performance; they are ~10% of the total). Mark road cells in the game's `ROADCELL` grid exactly as the existing road code does (index.html ~4369) so surfaces/footsteps/vehicle-grip work. For AI pathing, roads + dry land with slope < 30 deg define the graph; `tools/realmap/check.py` already computes the walkable region used to validate capture points.

## Ground materials from `landcover`

Rasterise polygons into the 257 x 257 material masks (point-in-polygon on cell centres; later polygons win; sort so `forest/farmland/grass/scrub` go first and `water`, then `urban/industrial/apron/runway_area/site` last): forest -> forest floor + dense trees (nature.glb), scrub/orchard/vineyard -> sparse trees/shrubs, farmland/grass -> meadow, beach -> sand_beach, rock -> rock_granite (also anywhere slope > 35 deg), bare -> gravel, urban/industrial/harbour/apron/parking -> concrete/asphalt. Everything not covered: Mediterranean default = dry meadow plus rock by slope.

## Re-generating / extending

`python tools/realmap/build_all.py` rebuilds the maps (network needed on first run, then served from `tools/realmap/cache/`). Overpass often returns 504/429; the driver retries and keeps every successful response cached, so just re-run. New place: `python tools/realmap/realmap.py build my_map <lat> <lon>`, then add capture points in `points_my_map.json` and run `python tools/realmap/check.py my_map snap` (moves each point to the nearest flat dry reachable cell) followed by `python tools/realmap/check.py my_map` (validates and draws the point preview).
