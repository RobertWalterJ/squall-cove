# Battlefield vehicles (assets/bveh.glb + assets/bveh.glb.b64.txt)

Built with Blender 4.2 (headless) by `blender/bveh/`: `v_lib.py` (node tree with relative pivots, wheels, seats, machine gun, helpers; reuses `blender/helis/heli_lib.py`), `v_light.py` (jeep, technical, quad_atv), `v_heavy.py` (apc, light_tank), `v_truck.py` (supply_truck, ambulance, fuel_truck), `build_bveh.py` (build, export, b64, review renders), `verify_bveh.py`, `run.sh`.

    sh blender/bveh/run.sh [model,model] [--norender] [--noexport]     (B_VIEWS=3q,3q_rear,side,front,top B_SIZE=800 B_SAMPLES=12)
    python blender/bveh/verify_bveh.py                                 (from the game dir)

NOTE: build only a subset WITH export and the GLB will contain only that subset. To re-render one model keep the full GLB: `run.sh --norender` first, then `run.sh model --noexport`.

Metres, +Z forward, +Y up, model's left = +X. Origin = centre of the footprint on the ground; wheels / tracks touch y = 0 (verified: lowest point of every model is y = 0.00). 8 top-level empties at the origin (they overlap; pick by name). Nodes carry translation only (no rotation/scale), so rotating a node about its local axis rotates exactly about its pivot. No textures/UVs/text/insignia (the red crosses are flat boxes). All faces single sided except `veh_canvas`, `veh_canvas_dark` and `veh_glass`.

## Materials (18)
`veh_paint` is the ONLY body-paint material; recolour it per team/map (`material.color`). It is a light neutral olive in the GLB (`#8f9478`, roughness 0.7), so set the colour directly rather than multiplying. Everything else is fixed: `veh_glass` (alpha 0.5, BLEND, double sided; set depthWrite false), `veh_rubber`, `veh_metal`, `veh_steel_dark`, `veh_dark`, `veh_rust` (exhausts), `veh_seat`, `veh_wood`, `veh_canvas` / `veh_canvas_dark` (double sided), `veh_can` (olive jerry cans and ammo boxes, NOT team paint), `veh_hose`, `veh_white`, `veh_red_cross`, `veh_light_white` / `veh_light_red` / `veh_light_amber` (emissive).

## Triangles, footprint, wheel radius, collision box
Footprint = bounding box of the model with the gun at rest (mirrors, hooks, antennas included). Collision box = recommended hull box (centre x, y, z; size x, y, z), excluding antennas, guns and mirrors.

| Model | Tris | Footprint (x by z, height) | Wheel r (tyre width) | Collision box centre / size |
|---|---|---|---|---|
| jeep | 5824 | 1.94 x 4.02, 1.64 | 0.36 (0.20) | (0, 0.70, -0.05) / (1.8, 1.4, 3.9) |
| technical | 6052 | 2.04 x 5.32, 2.31 | 0.40 (0.26) | (0, 1.00, 0.0) / (2.0, 1.9, 5.2) |
| apc | 7956 | 3.20 x 8.55 (hull + ramp 8.1), 3.80 incl. antenna | 0.54 (0.36) | (0, 1.15, 0.05) / (3.0, 2.3, 8.0) |
| light_tank | 7960 | 2.56 x 6.34 (hull 5.3 + barrel to 3.72), 2.90 incl. antenna | road wheel 0.29, sprocket 0.32, idler 0.30 | (0, 1.0, 0.0) / (2.56, 1.95, 5.1) |
| supply_truck | 7779 | 2.80 x 8.91, 3.14 | 0.55 (0.32) | (0, 1.6, -0.15) / (2.4, 3.1, 8.6) |
| ambulance | 4302 | 3.16 x 7.68, 4.20 incl. antenna (2.70 body) | 0.50 (0.34) | (0, 1.4, 0.05) / (2.3, 2.8, 7.5) |
| fuel_truck | 8344 | 2.80 x 8.66, 3.41 incl. tank rail | 0.52 (0.32) | (0, 1.5, -0.2) / (2.3, 3.0, 8.5) |
| quad_atv | 4036 | 1.38 x 2.25, 1.23 | 0.31 (0.24) | (0, 0.65, 0.0) / (1.4, 1.2, 2.25) |

Footprint x includes tyres that stick out past the body (tyre centre x: jeep 0.75, technical 0.84, apc 1.30, tank track centre 1.03, trucks 0.98, ambulance 1.0, quad 0.52).

## Animation nodes (all origins = pivot; all rotate with plain `rotation.x / .y`)
Wheel nodes `<model>_wheel_<id>`: origin at the wheel centre, spin about **X**. Forward travel = positive `rotation.x` (top of the tyre moves toward +Z) by `distance / radius`; both sides spin the same sign. Hub caps and lug nuts are on the outer side, tread lugs make spin visible.
Steering: front wheels sit inside `<model>_steer_<id>` (empty, origin at the wheel centre/kingpin), rotate it about **Y**; positive `rotation.y` turns the nose to the vehicle's left (+X). Wheel node inside is at local (0,0,0).

Wheel ids: jeep, technical, ambulance, quad_atv: `FL FR RL RR` (steer FL, FR). apc: `F1L F1R F2L F2R R1L R1R R2L R2R` (steer F1*, F2*; F1 front-most, R2 rear-most). supply_truck, fuel_truck: `F1L F1R R1L R1R R2L R2R` (steer F1*). Steering names are `<model>_steer_FL`, `apc_steer_F1L`, ... (same id as the wheel). L = +X.

| Model | Weapon / moving nodes (pivot in model coords) |
|---|---|
| jeep | `jeep_gun` (0, 1.52, 0.20) pivots on the pedestal: yaw about Y, pitch about X (positive `rotation.x` lowers the barrel). `jeep_muzzle` child at local (0,0,1.04). Spare wheel, pedestal are static. |
| technical | `technical_gun` (0, 1.98, -1.55), same axes, DShK-style gun with a shield that turns with it; `technical_muzzle` child at local (0,0,1.66). Ring rail and pedestal static. |
| apc | `apc_turret` (0, 2.02, 1.35) yaw about Y. `apc_gun` (0, 2.32, 2.17) child of the turret, pitch about X (mantlet + barrel + coax); `apc_muzzle` child of the gun at local (0,0,2.40). `apc_ramp` (0, 0.72, -3.83) closed = vertical panel on the rear face; open by `rotation.x = -90 deg` (flat, outer face up) or about -60 deg for a ramp. |
| light_tank | `light_tank_turret` (0, 1.27, 0.12) yaw about Y (3 smoke launchers per side, cupola, bustle are in it). `light_tank_barrel` (0, 1.62, 1.10) child of the turret, pitch about X; `light_tank_muzzle` child at local (0,0,2.64). `light_tank_track_L/R` (+-1.03, 0.382, 0) static geometry (band + cleats; origin is the track loop centre so you can scroll a texture / swap it). Spinning: `light_tank_wheel_L1..L5 / R1..R5` (road wheels, z = -1.2, -0.6, 0, 0.6, 1.2, y 0.362), `light_tank_sprocket_L/R` (z 1.85, front drive, r 0.32) and `light_tank_idler_L/R` (z -1.85, r 0.30), all spin about X. Return rollers are static in the body. |
| supply_truck, ambulance, fuel_truck, quad_atv | wheels / steering only. Ambulance rear doors and cab doors are fixed geometry. |

## Markers (empties, origin at the occupant's hip / feet, face +Z; no rotation)
All parented to the model root unless noted. `<model>_muzzle` is a child of the gun node (see above), barrel points +Z at rest.
- jeep: `_seat_driver` (0.33, 0.66, 0.45) left-hand drive, `_seat_p0` (-0.33, 0.66, 0.45), `_seat_p1` (0.31, 0.66, -0.74), `_seat_p2` (-0.31, 0.66, -0.74), `_seat_gunner` (0, 0.62, -0.25) (standing behind the pedestal on the floor, y 0.46), `_exit_L/R` (+-1.35, 0, 0.10).
- technical: `_seat_driver` (0.34, 0.98, 0.45), `_seat_p0` (-0.34, 0.98, 0.45), `_seat_p1/p2` (+-0.34, 0.98, -0.20) rear bench, `_seat_p3/p4` (+-0.58, 1.10, -2.15) bed sides, `_seat_gunner` (0, 1.32, -1.90) standing in the bed (floor y 0.98), `_exit_L/R` (+-1.45, 0, 0.30).
- apc: `_seat_driver` (0.45, 1.20, 2.75), `_seat_gunner` (0, 1.95, 1.20) **child of `apc_turret`** (rotates with it), `_seat_p0..p7` along the sides (x +-0.72, y 1.12, z 0.9, 0.1, -0.7, -1.5; p0-p3 left, p4-p7 right; hull is solid so passengers should be hidden), `_exit_L/R` (+-1.95, 0, 0), `_exit_rear` (0, 0, -4.6) (dismount point behind the ramp).
- light_tank: `_seat_driver` (0.5, 0.9, 1.55), `_seat_p1` (-0.5, 0.9, 1.55) (hull gunner), `_seat_gunner` (-0.34, 1.45, 0.32) and `_seat_p0` (0.30, 1.50, -0.12) (commander) are **children of `light_tank_turret`**, `_exit_L/R` (+-1.8, 0, -0.2).
- supply_truck: `_seat_driver` (0.46, 1.43, 1.15), `_seat_p0` (-0.46, 1.43, 1.15), bench passengers `_seat_p1..p4` (left, x 0.88, y 1.80, z -0.5 / -1.5 / -2.5 / -3.5) and `_seat_p5..p8` (right), `_exit_L/R` (+-1.8, 0, 1.4), `_exit_rear` (0, 0, -5.0). No gunner seat.
- ambulance: `_seat_driver` (0.46, 1.35, 1.35), `_seat_p0` (-0.46, 1.35, 1.35), `_seat_p1/p2` (0.75, 1.30, -0.4 / -1.3) medic seats left, `_seat_p3` (-0.2, 1.0, -1.8) stretcher position, `_exit_L/R` (+-1.8, 0, 1.2), `_exit_rear` (0, 0, -4.4). Body is closed: hide passengers in the rear compartment.
- fuel_truck: `_seat_driver` (0.46, 1.40, 1.10), `_seat_p0` (-0.46, 1.40, 1.10), `_exit_L/R` (+-1.8, 0, 1.3).
- quad_atv: `_seat_driver` (0, 0.88, -0.20), `_seat_p0` (0, 0.92, -0.62) (pillion, straddling), `_exit_L/R` (+-1.0, 0, -0.3). The rifle rack (two rifles) is on the rear left (+X) of the seat.

## Caveats
- Verified by Blender renders (3q, 3q_rear, side, front, top, in `blender/review/bveh/`) and `verify_bveh.py` (indices valid, normals unit length, base64 matches the GLB and is one line, 18 materials, 2.36 MB, no textures, wheels centred on their pivots, lowest point y = 0, all roots at the origin, all expected nodes present). Not loaded in three.js or a glTF viewer.
- Hulls are stylised and solid: only the open-topped ones (jeep, technical bed, quad, truck bed with benches visible through the open rear) have visible occupants' seats. The APC, tank, ambulance and truck cabs are closed shells with window glass; marker positions inside them are for the game to hide or show passengers.
- Doors, the APC ramp aside, are fixed geometry. Steering wheels and quad handlebars do not steer.
- Tank track is a closed band with cleats as separate boxes (static); the road wheels sit 0.00 m inside the band and the sprocket/idler have no teeth meshing with the cleats. Tank wheel bottoms are at y 0.05 (they ride on the band, which touches the ground).
- Wheel radius numbers are the true outer radius including tread lugs (verified from the GLB bounding box), so `y = radius` at the pivot places the wheel exactly on the ground.
- The jeep and technical guns are authored at their pedestal; the jeep gun (barrel 1.04 m) clears the windscreen top at y 1.38 at rest. Technical gun barrel rests above the cab roof at rest (cab roof y 1.78, gun y 1.98).
- Largest model is fuel_truck at 8344 triangles; wheels are about 600-690 tris each (6 wheels = about 4000 of a truck's budget).
- The ambulance cross markings are flat boxes in `veh_red_cross` on `veh_white` panels (sides, roof, rear doors); nothing is textured and no real organisation's emblem is reproduced.
