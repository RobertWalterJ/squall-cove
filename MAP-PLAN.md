# Port and mountains: map plan

A 768 m world (3 m terrain cells, 257 grid), coordinates in metres from the centre, x east, z south. The island is about 600 m across, with open sea all round so there are no visible seams. Designed for: maritime sandbox, an economy that runs by itself (yards, builders, farms, trucks), raids and invasions, and a Ravenfield-style battle for the points on the map.

## 1. What the map must let the game do (checklist)

| Need | Where it lives |
|---|---|
| Boats arrive, dock, load and unload | South harbour: quay, two slips, breakwaters, anchorage with buoys, fishing quay and boat ramp |
| Cargo moves from boat to yard to site | Three yards on the quay apron, one per quay segment, each with real stacked cargo and gravel ground |
| Builders have stone and sites | Three build sites on flat pads (two Port, one rival), a delivery arrives whenever stone runs low |
| Farms feed the economy | Two farms north-west and north-east with fields, farmhouse, barn, silo, produce and grain crates |
| Vehicles have a reason to exist | Cargo truck and forklift between yards, crane truck to sites, patrol car on the town roads. Roads connect everything |
| Raiders and invaders have somewhere to come from | Raider camp in the north-east hills, invasion beach on the south-east coast, smugglers' cove on the west coast |
| Ravenfield battle | Capture points: yards A, B, C, build sites, town hall square, lighthouse, raider camp, farm. Bases: quay (Port), raider camp (raiders), invasion beach (invaders) |
| Something to do on foot | Town with houses and streets, farms, fishing from the quay and rocks, lookout hill, lighthouse |
| Physics playground | Piles, stacked containers, slopes, a lake, a river, cliffs and a beach to dump boulders into |
| Maritime focus | Natural bay, breakwaters, buoys and channel, lighthouse headland, offshore islet with a second light, sandbar, wrecks, anchored fleet |

## 2. Landforms

- **Main island**: ragged coastline made from overlapping blobs plus noise, never a rectangle. Beaches 12 to 40 m wide on the west and south-east, rocky cliffs on the north and north-east.
- **Harbour front**: the one straight man-made edge. Concrete apron x -200 to 160, z 40 to 100. Harbour basin 7 m deep in front of it so big ships can berth. Two slips cut into the apron. A breakwater arm east of the basin and a shorter one west.
- **Plain**: flat 4.4 m ground with gentle swells (1 m). The town block (x -250 to 250, z -80 to 30) is graded flat.
- **Mountains**: north, three massifs up to about 40 m with forest, plus a lake at (-60, -270) and a river to the east coast.
- **West headland** with a lighthouse, **east peninsula** with cliffs, **offshore islet** south with a second light, a **sandbar** west.

## 3. Roads and buildings

- Main Street z = -40, x -230 to 230. Cross streets at x = -150, -50, 70, 150 run south to the quay lane (z = 46). Farm lanes go north from Main Street. All roads are graded into the terrain and drawn as one ribbon with markings.
- Town: houses along both sides of Main Street, about 24, three types, a few workshops. Guard post at the quay gate.
- Quay: warehouse, office, silo, fuel tank, quay crane, container rows, lamp posts every 35 m.
- Farms: farmhouse, barn (workshop), silo, fields.
- Raider camp: bunker, tents, barriers. Invasion beach: nothing built, just sand, dunes and rocks.

## 4. Immersion

Trees clustered by zone (palms on the beaches, mixed forest on the slopes, none on roads, quay, pads, farms). Lamp posts along roads and the quay. Gravel and oil staining on the yards. Boats anchored in the bay, fishers on the rocks. Birds and sound come from the existing systems.

## 5. Build order and checks

1. Terrain from a distance-field coastline, then graded pads and roads. Shot from above and from the sea.
2. Roads, then buildings and props. Shot of the town and the quay.
3. Yards, farms, vehicles, people. Shot of the working port.
4. Population and the economy run for five minutes with no errors.
5. Then capture points and the Ravenfield mode on top.
