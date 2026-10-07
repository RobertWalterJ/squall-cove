# Squall Cove port: buildings and props

24 static models in one GLB: `assets/port.glb.b64.txt` (780 KB GLB, 1.04 MB one-line base64, 14,462 triangles in total, none over 1,480).
Source: `blender/generators/build_port.py` (uses `pg_core.py`). Manifest (sizes, bounds, tris, doors): `blender/review/port/port.json`. One 3/4 render per model: `blender/review/port/<name>_3q.png`.

Rebuild: `_tools/blender-4.2.9-windows-x64/blender.exe -b --python blender/generators/build_port.py -- --review` (the `_tools` folder lives in the sibling `squall-cove` repo). `--only warehouse,office` builds a subset and does not overwrite the asset.

Textures (all 512 x 512, regenerate with `python blender/generators/tex_port.py`): `t_concrete_*`, `t_asphalt_*`, `t_gravel_*` (`_albedo.jpg`, `_normal.jpg`, `_orh.jpg`, jpeg q90 4:2:0 like the terrain sets; orh = occlusion R, roughness G, height B; normal is +Y up, flat = 128,128,255), and the decal `t_road_markings.png`.

## Conventions

- Blender is Z up; the glTF export maps Blender (x, y, z) to three (x, z, -y). Every model is **one top-level mesh node** (several materials, no child nodes, no empties) named exactly as in the table. Origin = centre of the footprint on the ground, so `y = 0` in three is the ground and `minY` of every model is 0 (watchtower, crane and others touch the ground exactly).
- Long axis is **+X**. "Front" is whichever side carries the doors, listed below. Blender +y is three **-z**, so a door on `+y` below faces three -z.
- Flat base-colour materials only, no textures, no vertex colours. Materials are shared by name across models (`concrete`, `metal_b`, `brick`, `glass`, ...). One material, `mesh` (the chain-link panel on `fence_section`), is **alpha blended** (30% opaque, double sided); put the fence late in the render order or set `depthWrite = false` on it.
- Windows and doors are thin coloured boxes standing 3 to 16 cm proud of the wall (no cut-outs), glass is dark blue-grey and not emissive.

## Nodes and measured sizes (x length, y height, z width in metres; z is the Blender y extent)

| Node | L (x) x H (y) x W (z) | Tris | Doors (side, offset along wall from centre, w x h) |
|---|---|---|---|
| warehouse | 30.0 x 8.96 x 14.08 | 1380 | three roller doors on +y at x = -9, 0, +9 (4.8 x 4.5); personnel door on -y at x = -11 (1.1 x 2.2); bay door on +x end (3.6 x 4.0) |
| office | 14.0 x 11.0 x 11.25 | 972 | glazed entrance on +y at x = 0 (2.4 x 2.3) with canopy and steps; body is 13.7 x 9.6, the extra width is the entrance steps (y -4.95 to +6.3) |
| hangar | 24.0 x 9.92 x 19.99 | 764 | big double sliding door on the +x end (14.0 x 7.2, two leaves); personnel door on -y at x = +6 (1.1 x 2.2). Arched roof, ribs every 3 m |
| workshop | 12.3 x 5.1 x 7.91 | 304 | roller door on +y at x = -2.5 (3.0 x 2.7); door on +y at x = +2.5 (1.0 x 2.1). Mono-pitch roof, high side on -y |
| house_a | 8.1 x 6.0 x 7.19 | 268 | door on +y at x = -1.5 (1.0 x 2.1), small porch deck. Gable along X, red roof, white siding |
| house_b | 8.35 x 5.9 x 7.3 | 320 | door on +x at z = 0 (1.0 x 2.1) under a porch (porch extends x to +4.5). Hip roof, yellow siding |
| house_c | 8.08 x 6.36 x 7.3 | 376 | door on +x at offset -1.5 (1.0 x 2.1); balcony above the door. Gable end faces +x (ridge along Y), stucco |
| guardhouse | 4.0 x 3.0 x 4.0 | 144 | door on +x (1.0 x 2.1), windows on the other three sides |
| watchtower | 3.0 x 10.0 x 3.0 | 788 | cab door on +x (0.7 x 1.4) at platform height 8.2 m; ladder on the +x face from the ground to the platform |
| fuel_tank | 11.5 x 8.94 x 10.2 | 1476 | none. Diameter 10 m (10.2 with the base ring), caged-free ladder on the +x side, roof handrail; 11.5 in x includes the draw-off pipe on -x |
| silo | 6.25 x 16.0 x 5.5 | 1120 | none. Diameter 5 m, ladder on +x, discharge chute on -x (hence 6.25 in x) |
| quay_crane | 42.5 x 30.13 x 14.8 | 852 | none. See below |
| bunker | 8.02 x 3.35 x 6.0 | 696 | 2.4 m wide, 2.1 m high open entrance on +x, firing slits either side |
| tent | 6.2 x 2.95 x 4.12 | 184 | flap door on +x end (1.4 x 1.9); ridge along X |
| container_red / _blue / _green / _orange | 6.05 x 2.59 x 2.43 | 748 each | door end on +x (two leaves, locking bars); corrugated sides on +y and -y, plain end on -x. Identical shape, only the paint differs |
| lamp_post | 2.32 x 7.05 x 0.44 | 132 | pole at the origin, arm and lamp head point to +x (head from x = 1.3 to 2.1, lens underneath at 6.82 m) |
| quay_bollard | 0.68 x 0.9 x 0.68 | 258 | round, black, with a rust-coloured strap plate |
| fence_section | 4.0 x 2.04 x 0.12 | 384 | 4 m panel along X, 3 posts, top and bottom rail, diagonal wire lattice, translucent mesh body |
| road_barrier | 3.0 x 1.01 x 1.0 | 244 | red and white striped double board along X on two A-frame feet |
| pallets | 1.22 x 1.49 x 1.0 | 512 | four pallets each carrying one layer of goods (alternating shrink-wrapped and cardboard), 0.375 m per level |
| road_sign | 0.24 x 3.0 x 0.62 | 296 | 3 m post, round no-entry sign facing +x (disc centre at 2.55 m, 0.62 m across) |

### Quay crane (portal container crane)

The long axis is the **boom axis**: the boom points to **+X** (over the water) and the machinery house and backreach are on -X (land side). Rail gauge (waterside leg to landside leg) is **20 m along X**: legs at x = -10 (land) and x = +10 (water), and each leg pair is 12 m apart along the quay (three z = +-6). So the portal spans a 20 m wide quay strip and travels along the **z** axis. Place the model so the quay edge is at about x = +10.7 (the waterside wheel trucks) and rotate about the vertical to suit the quay direction. Apex of the A-frame is 30.0 m, boom girders from x = -5 to +30 (35 m), boom tip over the water at x = +30, deck of the boom 22.6 to 23.2 m, trolley and an empty spreader hang at x = 18 to 22 (spreader at 8 m). Ladder on a landside leg.

## Caveats

- The footprint dimensions in your brief are matched on the main body; porches, canopies, roof overhangs and the like add to the bounding boxes above (house_b 8.35 long including a porch 1.0 m deep, office 11.25 deep including entrance steps and canopy). Pivot is the body centre, so those models look slightly off-centre in their bounding box (see `min` and `max` in `port.json`).
- Hip and gable roofs are thin slabs over the walls with a flat underside; walls are plain boxes with coloured patches, so there are no real window reveals.
- Corrugation is real geometry on the warehouse and container sides (vertical ribs); the hangar roof has arch ribs instead.
- The sandbag courses on the bunker are alternating tan and brown boxes (no bevel); at under 30 m they read as banded walls.
- `fence_section`'s translucent panel needs alpha blending; the wire lattice and posts are opaque and still read as a fence if the panel is made invisible.
- Model height spec check: warehouse 8.96 (ridge cap) vs 9, hangar 9.92 vs 10, fuel tank 8.94 vs 9, workshop 5.1 vs 5, guardhouse 3.0, tent 2.95 vs 3 (all within 10 cm of the spec).
- Review renders use Workbench studio lighting and diffuse colours, so the in-game PBR look will be a bit warmer. The warehouse render shows the -y side; its roller doors are on +y.
