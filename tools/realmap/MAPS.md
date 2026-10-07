# Lemnos maps: design notes

Three 768 m windows of the real island of Lemnos, Greece, at 1:1 scale, built from open data only (OpenStreetMap + Mapzen/AWS terrain tiles; see `README.md` for attribution). Files: `assets/map_lemnos_myrina.json` (0.42 MB), `map_lemnos_mudros.json` (0.44 MB), `map_lemnos_airport.json` (0.36 MB). Format and loader notes: `LOADER_SPEC.md`. Previews: `preview/<id>.png` (terrain, roads, buildings) and `preview/<id>_points.png` (capture points; blue/red/white dots). Coordinates below are game metres (x east, z SOUTH, origin at the window centre); every point was checked by `check.py` to be dry (>1.5 m), on ground that is flat within 12 m (slope under 13 to 16 degrees), not inside a building footprint, and connected to all the others over walkable land (slope under 30 degrees).

All three are real places, so they are not balanced like a designed map: the first two are dense town maps, the third is an open airfield with almost no cover. Sea floor is a generic shore ramp (no real bathymetry).

## lemnos_myrina: castle hill, harbour and old town (centre 39.87605 N, 25.05666 E)

* **In the window:** the castle hill (Myrina Kastro) filling the west half, rising to 89 m with a ridge, steep flanks and a rim wall path; the old town and market streets climbing the east side; the small harbour at the south foot of the hill (breakwater, quay road with roundabout, lighthouse tip at (60, 312)); Romeikos Gialos beach curving off to the south-east; a small boat basin on the north shore at (130, -200); open sea on the west and south (39% of the window is water).
* **Counts:** 272 buildings (128 house_a, 98 house_b, 22 house_c, 9 office, 9 workshop, 3 watchtower, 2 warehouse, 1 ruin), 92 road pieces (6.9 km: 30 residential, 17 service, 16 footway, 11 tertiary, 8 path, 5 steps, 3 pedestrian), 17 land cover polygons, 1 breakwater, 1 lighthouse.
* **Slopes:** the hardest of the three. 35% of dry land is 15 to 30 degrees and 9% is over 30 degrees (castle flanks). Only 37% is under 5 degrees: the town fringe, the harbour apron and the castle summit plateau (the old fortress area at about 85 m).
* **Issues:** SRTM is about 30 m resolution, so the hill is smooth (no ramparts, cliffs or terraces). The coast is eased down to a low beach/quay edge within 45 m of the water to keep it walkable, so the real sea cliffs on the north and west of the hill are gentler than reality. No `place` or tower data except the lighthouse. Almost no height/levels tags (2 buildings). The castle wall is only a footpath line (the building polygon was 12,000+ m2 and is excluded). Vehicles are limited to the town roads and the one paved/track route up the hill.
* **Play:** a defended hill fortress against a push from the town: blue holds the castle summit, red holds the east town, the harbour and the market streets are the contested middle.

| id | type | side | x | z | note |
|---|---|---|---|---|---|
| B1 | hq | blue | -159 | -120 | castle summit plateau, 86 m |
| B2 | strongpoint | blue | -63 | -90 | castle east shoulder, covers the town approach, 87 m |
| B3 | battery | blue | -126 | -69 | summit south, long sight over harbour and bay, 87 m |
| B4 | radio | blue | -231 | -309 | north-west beach spit (the only flat ground away from the summit), far from roads, 1.5 m |
| N1 | harbour | neutral | 63 | 219 | harbour quay road end beside the lighthouse spit, 2 m |
| N2 | choke | neutral | 147 | -84 | road junction where the castle track meets the town, 20 m |
| N3 | plain | neutral | 111 | 72 | open lot at the foot of the hill on the town edge, 20 m |
| N4 | depot | neutral | 171 | 69 | town-edge yard beside N3, 14 m |
| R1 | strongpoint | red | 204 | 6 | main square, 15 m |
| R2 | depot | red | 303 | 105 | south-east town, near the beach road, 9 m |
| R3 | hq | red | 330 | -39 | east edge of town, 12 m |

Blue and red are 450 to 500 m apart across the town. B4 is a deliberate detached outpost (about 330 m from B1).

## lemnos_mudros: Moudros harbour and town (centre 39.87281 N, 25.26742 E)

* **In the window:** the south-west corner of Moudros town (the bay's north-west shore). The waterfront runs diagonally from the north-west to the south-east with a long main road along it; the working harbour sits in the south-west: one large pier/mole at (-260 to -170, 80), three long finger piers running south-south-east, and a long breakwater (about 250 m) closing the south; the compact old town street grid fills the north-east; wetland and a stream south-east; farmland and low scrub elsewhere. 21% of the window is water.
* **Counts:** 366 buildings (200 house_a, 86 house_b, 45 house_c, 24 workshop, 10 warehouse, 1 office), 90 road pieces (9.3 km: 62 residential, 12 service, 5 tertiary, 4 unclassified, 3 secondary, 3 footway, 1 pedestrian), 28 land cover polygons, 8 harbour features (6 piers, 2 breakwaters). Place: Moudros (town).
* **Slopes:** the gentlest town map: 84% of land is under 5 degrees, nothing is over 15 degrees; highest point is 31 m. The "hills" are low ridges (about 15 to 30 m) in the north-west and south-east.
* **Issues:** very flat, so sight lines are long and cover is only buildings. Pier heights are derived from the shore, not surveyed; the piers/breakwaters are polylines (width about 5 m), not solid polygons, so the integrator must build the decks (the quay area at the foot of the big mole is dry land). OSM quays and warehouses at the harbour are sparse (10 warehouses, none tagged as port buildings). Names are almost absent (3 named roads). The harbour as drawn is the real Moudros fishing/ferry port, which is small; it is not the large natural bay anchorage (that lies mostly outside this window, to the east and south).
* **Play:** a harbour-fight map: blue holds the high ground and shore in the north-west, red the east town, with the harbour road, the main waterfront road and the road junction (N2) between.

| id | type | side | x | z | note |
|---|---|---|---|---|---|
| B1 | hq | blue | -231 | -210 | north-west scrub rise, 10 m |
| B2 | strongpoint | blue | -111 | -150 | low ridge east of B1, 16 m |
| B3 | battery | blue | -291 | -150 | north-west shore terrace, covers the whole bay and harbour, 1.5 m |
| B4 | radio | blue | -291 | -279 | north-west corner rise, 8 m |
| N1 | harbour | neutral | -81 | 78 | harbour road end at the pier roots, 7 m |
| N2 | choke | neutral | 51 | 90 | road junction between harbour and town, 8 m |
| N3 | depot | neutral | 111 | -75 | warehouse/yard block on the town edge, 17 m |
| N4 | plain | neutral | 39 | 270 | open farmland south of the town beside the coast road, 3 m |
| R1 | hq | red | 339 | 21 | east edge of town, 10 m |
| R2 | strongpoint | red | 255 | -129 | town centre, 20 m |
| R3 | depot | red | 321 | 210 | south-east yard beside the stream, 7 m |

## lemnos_airport: Lemnos Airport (LXS) apron and runway (centre 39.91997 N, 25.23659 E)

Centred 330 m north and 50 m east of the airport reference point (39.917 N, 25.236 E) so that the apron, the taxiways and the end of runway 04R/22L are all in the window.

* **In the window:** the runway (04R/22L) crossing the south-east of the window at 45 m wide; a parallel taxiway on its north-west side with a loop at the end; the apron with a comb of hardstand/taxilane stubs in the north-west (many small taxiway pieces, 24 in all); a perimeter road (service, 2.5 km of road pieces) on both sides; gently sloping fields and scrub. No water.
* **Counts:** 1 building (OSM has no terminal or hangars here), 14 roads (2.5 km, all service/unclassified), 5 land cover polygons (airfield, apron, military, 2 parking), 25 aeroway lines (1 runway piece of 677 m, 24 taxiway pieces, about 4.1 km of taxiway in total).
* **Slopes:** flat: everything is under 5 degrees; elevation 0.5 to 12.5 m (the runway is nearly level, 6 to 7 m).
* **Issues:** no buildings in OSM, so the integrator must place hangars, a tower and a terminal on the apron (suggested near (-200 to -50, -330 to -180)); no towers, no markings data, no water, no cover other than a few trees. A very open map: it favours vehicles and aircraft; there is almost no concealment (no tree or building data), so the integrator should scatter scrub on the darker south-east and west fringes. Runway centreline is not exactly straight to the map axes (it runs at about 45 degrees), so lay `aeroways` as polylines rather than assuming an axis.
* **Play:** air-base seizure: blue holds the apron and perimeter road (north-west), red holds the south-east side beyond the runway; the runway and taxiway are the no-man's land.

| id | type | side | x | z | note |
|---|---|---|---|---|---|
| B1 | hq | blue | -300 | -99 | west perimeter road, 7 m |
| B2 | airfield | blue | -189 | -249 | the apron stub field, 10 m |
| B3 | radio | blue | -330 | 201 | south-west perimeter road end, 6 m |
| B4 | depot | blue | -201 | 120 | beside the one mapped building, 7 m |
| N1 | airfield | neutral | 0 | 21 | the taxiway/loop junction by the runway, 7 m |
| N2 | choke | neutral | 129 | -309 | perimeter road crossing the taxiway at the north edge, 5 m |
| N3 | strongpoint | neutral | 60 | -120 | grass between the apron and runway, 7 m |
| N4 | plain | neutral | 120 | 120 | open grass in the middle of the airfield, 7 m |
| R1 | hq | red | 330 | 270 | south-east corner, open farmland, 6 m |
| R2 | strongpoint | red | 231 | 150 | south-east of the runway, 5 m |
| R3 | battery | red | 321 | -39 | north-east side of the runway, 7 m |
| R4 | depot | red | 351 | -249 | north-east apron/parking, 6 m |

## Summary of issues across all three

* Network: the public Overpass servers frequently returned 504 or 429; the pipeline retries and caches, so the final data is complete (a few optional groups, power lines, walls, military ways and harbour ways, were allowed to be skipped if they kept failing: `harbour` data did load for Myrina and Mudros).
* Terrain resolution is about 30 m native; the 3 m grid is a smooth interpolation, with a 1-cell Gaussian smoothing and an engineered shore.
* Vegetation, rocks and individual trees are not in the data: use the land cover polygons plus slope to scatter them.
* Real sea depth is not used; sea floor reaches -9 m about 130 m from shore.
