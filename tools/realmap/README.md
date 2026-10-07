# realmap: real places to Squall Cove map files (open data only)

Turns a real place into `assets/map_<id>.json`: a 257 x 257 heightfield at 3 m per cell (768 m square, sea at 0 m) plus roads, buildings, land cover, harbour structures, aeroways, towers and place names, all in game metres (x east, z south, origin at the map centre).

Nothing here comes from any game's files. The three Lemnos maps are built from the real island (the island Arma 3's Altis is modelled on) using only open data.

## Attribution (required, ODbL)

* **Map data (c) OpenStreetMap contributors**, licensed under the Open Database License 1.0. https://www.openstreetmap.org/copyright . Buildings, roads, land cover, coastline, harbour, aeroway, tower and place data are derived from OSM; the derived files are a Derived Database under the ODbL and must carry this notice (every generated JSON has it in its `attribution` field, and every preview PNG carries it in its footer).
* **Terrain data from Mapzen terrain tiles (SRTM, GMTED, NED, etc.)**, via the AWS Terrain Tiles dataset (Terrarium encoding). https://registry.opendata.aws/terrain-tiles/
* Place lookup used OSM Nominatim conventions; Overpass API queries identify as `SquallCoveMapTool/1.0 (personal game)`.

If the game ships or shows these maps, show the attribution string on a credits or map screen.

## Files

| file | purpose |
|---|---|
| `realmap.py` | the pipeline: `fetch_dem` (Terrarium tiles, z14, cubic resample to 257 x 257), `fetch_osm_raw` + `process_osm` (Overpass, in small cached groups), `shape_heights` (sea mask from the coastline, sea floor by distance from shore, coastal ease), `render_preview`, `build` |
| `build_all.py` | runs builds and scans, retrying until every Overpass query is cached (the public servers often answer 504 or 429) |
| `check.py` | validates a map and its capture points, `snap` moves points onto flat, dry, connected ground |
| `points_<id>.json` | the hand-chosen, validated capture points per map |
| `MAPS.md` | per-map design notes and capture points |
| `LOADER_SPEC.md` | JSON schema, coordinate conventions, how to feed `genTerrain`, OSM building to game model table |
| `cache/` | every HTTP response (Terrarium PNG tiles, Overpass JSON). Delete nothing: a rebuild then needs no network |
| `preview/` | `<id>.png` (hillshaded height, roads, buildings, 100 m grid), `<id>_points.png` (capture points), `scan_*.png` (wider scouting views) |

## Usage

```
python tools/realmap/build_all.py                       # rebuild everything (cached after the first run)
python tools/realmap/realmap.py build my_map 39.87 25.06   # new 768 m map centred there
python tools/realmap/realmap.py scan  scout 39.88 25.27 --size 2500   # preview only, no asset
python tools/realmap/check.py my_map snap               # snap capture points to good ground
python tools/realmap/check.py my_map                    # validate + preview with points
```

Python 3 with numpy, Pillow and scipy. No keys, no accounts.

## Method notes and known limits

* Elevation is SRTM-derived (about 30 m source resolution), so hills are smooth; there are no cliffs, walls or terraces. Land within about 45 m of the shore is eased down toward a low quay/beach edge so the shore is walkable; the real shoreline is otherwise kept.
* Sea mask: nearest-coastline-segment side test (OSM puts land on the left of a coastline way). Sea floor depth = 0.35 m + 0.055 m per metre from shore, capped at 9 m with a little low-frequency undulation. Real bathymetry is not used (Terrarium has none worth using this close to shore).
* Buildings are footprints only. OSM coverage on Lemnos is good in towns, patchy in the countryside; height/levels are mostly missing.
* `out geom` is requested per tag group in small Overpass queries; the coastline query is snapped to a 0.05 degree box so neighbouring windows share one cached response.
