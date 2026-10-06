# Squall Cove land vehicles

Nine low-poly vehicles in one GLB: `assets/vehicles.glb.b64.txt` (741 KB GLB, about 12,900 triangles, one-line base64 like the other assets).
Sources: `blender/generators/pg_vehicles.py` (one builder per vehicle) and `build_vehicles.py`.
Manifest with every node's size, pivot and wheel position: `blender/review/vehicles/vehicles.json`. Renders and contact sheets: `blender/review/vehicles/`.

Rebuild: `_tools/blender-4.2.9-windows-x64/blender.exe -b --python blender/generators/build_vehicles.py -- --review` (the `_tools` folder lives in the sibling `squall-cove` repo). `--only ambulance,tractor` builds a subset for testing and does not overwrite the asset.

## Conventions (read this first)

- Blender is Z up, the vehicle faces **+X**, and the glTF export maps Blender (x, y, z) to Three.js (x, z, -y). So the vehicle faces +X in Three.js too, up is +Y, and the vehicle's **left side is Blender +Y = Three.js -Z**.
- Every vehicle is a top-level node named by its key (`ambulance`, `firetruck`, ...). The nine roots sit in a row 7 m apart along Blender Y for preview. **Clone the root and set its position to wherever you want it; ignore the row offset.**
- The root origin is on the ground (z = 0) under the centre of the wheelbase. Every wheel touches z = 0.
- All parts are children of the root (or of a named sub-node). `<key>_body` is the static hull.
- **Wheels**: `<key>_wheel_<FL|FR|ML|MR|RL|RR>`. Each node's origin is the wheel centre; the mesh is centred on it with no baked rotation, so the node is ready to animate. Axle = node-local **Z in Three.js (Blender Y)**. Forward roll: `wheel.rotation.z -= distance / radius` (negative about +Z when moving toward +X). Steering (FL/FR only): `rotation.y = steer`. Use the default Euler order `XYZ` (spin is applied first, then steer), so spin and steer compose correctly. Wheel local positions and radii are in `vehicles.json`.
- **Empties**: `<key>_seat` (driver hip position, on the left-hand side), `<key>_cargo` (centre of the load area), `<key>_hitch` (rear tow point). Every vehicle has all three; `handcart_seat` is the handle grip point (where a pusher stands, behind the cart).
- Materials are plain base colour; lamp materials are emissive (headlamps white, tail lamps red, beacons amber, light bars red and blue). No textures or vertex colours.
- Driving rule of thumb: min turn radius (centre-line) is wheelbase / tan(max steer angle).

## Per-vehicle data

Sizes are the measured bounding boxes (length x width x height, m). Speeds are for the game's scale: a comfortable range, then the cap that still looks right.

| Key | L x W x H | Wheels | Speed (m/s) | Turn radius |
|---|---|---|---|---|
| ambulance | 6.0 x 2.5 x 2.8 | r 0.40, w 0.28, axles x = +1.65 / -1.65, track y = +-0.98 | 6 to 18 (cap 24) | 6 m at 30 degrees steer |
| firetruck | 8.5 x 2.9 x 3.95 | r 0.52, w 0.38, axles x = +2.57 (FL, FR), -1.29 (ML, MR), -2.57 (RL, RR), y = +-0.97 | 4 to 14 (cap 18) | 8.5 m |
| forklift | 3.25 x 1.4 x 2.45 | front r 0.34 (x +0.7, y +-0.53), rear r 0.24 (x -0.7, y +-0.40) | 1 to 4 (cap 5.5) | 1.6 m (rear steer; steer the RL and RR wheels, not FL and FR) |
| cargotruck | 7.6 x 2.9 x 3.4 | r 0.50, w 0.36 front and 0.42 rear, axles x = +2.1 / -2.1, y = +-0.98 | 4 to 13 (cap 18) | 7.3 m |
| patrolcar | 5.1 x 2.3 x 2.0 | r 0.37, w 0.25, axles x = +1.4 / -1.4, y = +-0.86 | 7 to 20 (cap 28) | 4.2 m at 35 degrees |
| tractor | 4.0 (7.3 with trailer) x 2.55 x 3.1 | front r 0.45 (x +0.95, y +-0.70), rear r 0.75, w 0.46 (x -0.95, y +-1.0), treaded | 2 to 7 (cap 10) | 2.4 m at 40 degrees; trailer pivots about the hitch |
| quadbike | 2.15 x 1.4 x 1.23 | r 0.28, w 0.24, axles x = +0.62 / -0.62, y = +-0.54, treaded | 3 to 12 (cap 17) | 1.8 m at 38 degrees |
| handcart | 1.8 x 1.15 x 0.97 | ML, MR r 0.30, w 0.07 at x = 0, y = +-0.50 | 0.8 to 1.8 (a person pushing) | spins about its axle, about 0.6 m |
| cranetruck | 9.5 body (10.9 with boom at rest) x 4.05 incl. outrigger pads x 6.3 | r 0.60, w 0.40, axles x = +3.0 (FL, FR), -1.6 (ML, MR), -3.0 (RL, RR), y = +-0.98 | 3 to 10 (cap 14) | 9.2 m |

Triangles: ambulance 1.1k, firetruck 2.1k, forklift 1.2k, cargotruck 1.3k, patrolcar 1.2k, tractor 2.2k, quadbike 1.4k, handcart 0.5k, cranetruck 2.0k.

### Nodes, pivots and what animates

- **ambulance**: `ambulance_body`, `ambulance_wheel_FL/FR/RL/RR`, `_seat`, `_cargo`, `_hitch`. Animate wheels (FL, FR steer). The roof light bar (red left, blue right) is part of the body; flash it by swapping the emissive strength of the `lamp_r` and `lamp_b` materials (they are shared by all vehicles, so clone the material per instance if you do).
- **firetruck**: `firetruck_body`, wheels FL, FR, ML, MR, RL, RR (only FL, FR steer), empties. Short ladder and hose reel are fixed to the roof; the cargo empty is the roof centre.
- **forklift**: `forklift_body`, `forklift_mast` (pivot at the mast foot, x = 1.05, z = 0.5; tilt about local Z in Three.js, plus or minus 6 degrees), `forklift_forks` (a **child of the mast**; pivot at the fork heel on the floor, so lift by raising `position.y` from 0 to about 1.6 m and the forks follow any tilt), wheels FL, FR (drive, fixed), RL, RR (steering). `forklift_cargo` is a child of the forks, at the fork centre (put crates there). Seat is under the overhead guard.
- **cargotruck**: `cargotruck_body`, `cargotruck_bed` (pivot at the centre of the deck surface, x = -1.1, z = 1.3, so crates parented at local (0,0,0) sit on the deck; deck is 4.6 m x 2.4 m; side boards 0.5 m high; you could tilt the bed for tipping about its own pivot, but it is not a hinged tipper), `cargotruck_cargo` (child of the bed, at its origin), wheels, seat, hitch.
- **patrolcar**: `patrolcar_body`, wheels, empties. Roof light bar is blue and white; crest is a yellow disc with a navy centre on both front doors and on the grille.
- **tractor**: `tractor_body`, wheels FL, FR (steer), RL, RR, and `tractor_trailer` (pivot at the drawbar hitch, x = -1.95, z = 0.58, so rotate it about local Y in Three.js to follow behind; at rest it extends 3 m straight back). The trailer's wheels are its children: `tractor_trailer_wheel_ML`, `tractor_trailer_wheel_MR` (r 0.50, axle at trailer-local x = -1.95), and the trailer's deck centre is `tractor_cargo` (a child of the trailer). `tractor_hitch` is on the tractor at the pivot point. Seat is in the cab.
- **quadbike**: `quadbike_body`, wheels, empties. Front and rear racks are part of the body; `quadbike_cargo` is the rear rack.
- **handcart**: `handcart_body` (the tray, two long handles, grips and two rear legs that rest on the ground), `handcart_wheel_ML`, `handcart_wheel_MR`. It rests on the wheels and the stand legs; if the game tilts it, pivot about the axle (the root origin). `handcart_cargo` is the tray centre.
- **cranetruck**: `cranetruck_body` (includes turret and stowed outriggers), `cranetruck_boom` (pivot at the turret top, (x -0.9, z 2.8); the mesh points along local +X and the node has a **rest rotation of 25 degrees elevation**; set `rotation.z` in Three.js from 0 (horizontal) up to about +1.3 rad, with its rest value 0.4363 rad; also rotate the whole boom about the vertical to slew), `cranetruck_cable` (a 1 m dark line pivoting at the boom tip; scale its Y to the rope length, the mesh hangs below the pivot), `cranetruck_hook` (hook block, pivot at its top). Both cable and hook are children of the **root**, not the boom, so the rope stays vertical; their rest positions are the boom tip at 25 degrees (x 5.63, z 5.84) and the hook 2.2 m below it. If you raise or slew the boom, reposition the cable and hook from the tip yourself: tip = pivot + 7.2 m x (cos elevation) along the boom direction; set `hook.position.y = tip.y - ropeLength` and `cable.scale.y = ropeLength`. Cargo empty is the centre of the deck behind the cab.

## Caveats

- The nine vehicles share materials by name (`white`, `dark`, `glass`, `lamp_*`, ...). Colours are fixed in the generator; to recolour one vehicle (the generator takes a `paint` argument) rebuild with a different key from `PAL` or a hex string.
- Every wheel has hubs that are chunky 10-sided discs; at under 30 m distance they read as round. Treads are small boxes on the tractor and quad wheels.
- Body lengths include bumpers. The crane's reported 10.9 m includes the boom at rest; the chassis itself is 9.5 m.
- Wheel arches are drawn as dark patches on the body side (no cut-out); the wheels sit partly inside the hull, so keep them at their node positions rather than offsetting them outward.
- The `length` parameter of each builder rescales only the body and the wheel spacing along X (sub-nodes such as the mast, bed, boom and trailer are not rescaled), so it is meant for small tweaks of a vehicle that has no sub-nodes.
- The handcart's wheel is a thin disc (0.07 m); it may look flat from the front at long distances.
- No collision shapes or suspension are included; wheels have no bounce nodes. Ground contact is exact at z = 0.
- Review renders use Workbench lighting and viewport colours, so the in-game look (PBR, sun, fog) will be a little warmer and more contrasty.
