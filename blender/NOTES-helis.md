# Helicopters (assets/helis.glb + assets/helis.glb.b64.txt)

Built with Blender 4.2 (headless) by `blender/helis/`: `heli_lib.py` (superellipse hull loft with recessed doors/windows, patches, prisms, blades), `heli_parts.py` (skids, rotor heads, M60 / minigun, seats), `m_<model>.py` (one per helicopter), `build_helis.py` (build, export, b64, review renders), `verify_helis.py` (pure-python GLB parser), `run.sh`.

    blender.exe -b --python blender/helis/build_helis.py -- <abs assets dir> <abs review dir> [model,model] [--norender] [--noexport]
    python blender/helis/verify_helis.py        (run from the game dir)

Use ABSOLUTE paths (Blender resolves relative render paths against the drive root). Review PNGs: `blender/review/helis/<model>_{side,front,top,3q,3q_rear}.png`.

Metres, +Z forward, +Y up, model's left = +X. Origin on the ground at the centre between the skids / wheels. Each model is a top-level empty at the origin; they overlap, pick by name. Nodes carry translation only (no rotation/scale), so rotating a node about its local axis is exactly rotating about the pivot. Smooth shaded hulls, flat shaded details, no textures/UVs/text/insignia. Material names are `<model>_<colour>` for the livery and `heli_*` for shared (glass `heli_glass` alpha 0.5, `heli_rotor_blur` alpha 0.12 double sided, emissive `heli_light_red/green/white`).

| Model | Triangles (all nodes) | Notes |
|---|---|---|
| bell206 | 3068 | red/white colour panels, 5.1 m blades, 9.4 m fuselage (nose to tail-rotor), windows are real recesses with glass so the seats show |
| huey | 4446 | 7.3 m two-blade rotor + stabiliser bar, doors slid open (seats inside), slid door panel on its rail |
| griffon | 4602 | four blades 7.0 m, right door open with minigun, wire cutters above (roof) and below (chin), FLIR ball, left door closed |
| blackhawk | 4508 | four blades 8.18 m, stabilator, main wheels + tail wheel, both sliding doors open |
| cobra | 5026 | tandem canopies (glass shells), stub wings, 4 rocket pods, chin turret |
| chinook | 5962 | two 3-blade 9.15 m rotors, sponsons, 4 wheels, ramp, right cargo door open, left gun window |

## Nodes (each name is `<model>_...`; origin = rotation pivot)
- `_body` fuselage, skids/gear, fins, pylons, interior, cockpit furniture (origin 0,0,0).
- `_mainrotor` pivot at the hub, spin about local **Y**. Blades + hub + rotating swashplate (+ stabiliser bar on huey/cobra). Hub height: bell206 (0,2.80,0.05), huey (0,3.62,-0.35), griffon (0,3.56,-0.30), blackhawk (0,4.05,-0.30), cobra (0,3.05,-0.90).
- `_tailrotor` pivot at the tail hub, spin about local **X**; sits on the model's LEFT (+X) of the fin. Not on chinook.
- chinook: `chinook_rotor_front` (0,4.9,5.0) and `chinook_rotor_rear` (0,6.15,-6.9), both spin about Y (they counter-rotate in reality; the game must flip one).
- `_rotor_blur` (chinook: `_rotor_front_blur`, `_rotor_rear_blur`) and `_tailrotor_blur`: thin translucent discs, same pivot as their rotor, alpha 0.12; toggle `visible` in the game. Rotor discs are flat at hub height + 0.1..0.2 m.
- `_navlights` small emissive octahedra (red = left/+X, green = right/-X, white tail, red beacon); origin 0,0,0.
- Guns (pivot at the mount, rest pose horizontal): `huey_gun_L/R` (barrel along +X / -X), `griffon_gun` (minigun, barrel along -X, right door), `blackhawk_gun_L/R`, `chinook_gun_L` (left window, +X) / `chinook_gun_R` (right door, -X): all barrels point straight out sideways; the door post rotates with the gun. `cobra_turret` pivot under the nose (0,0.62,3.2), three barrels along **+Z**.
- `chinook_ramp` pivot at the hinge (0,1.30,-6.78); closed pose is a sloping panel under the rear fuselage (slopes up toward -Z); open it by rotating about local X (positive Blender-style rotation lowers it: try about -50 degrees and check direction).
- Seat markers (empties, origin at the occupant's hip, face along +Z unless sat in a door): bell206 `_seat_0..4`, huey `0..7`, griffon `0..7`, blackhawk `0..7`, cobra `0..1` (gunner, pilot), chinook `0..12` (left wall 0-5, right-door seats 6-8, pilots 9-10, left gun window 11, ramp 12). Door-gunner seats are the ones at x = +/-0.9..1.0, z about 0.

## Caveats
- Fuselages are solid shells: the only visible interiors are the recessed doors/windows (huey/griffon/blackhawk/chinook cabin doors, bell206 windows). Interior is a floor, back bulkhead and sideways canvas seats, with the pilots' seats behind the cockpit door windows.
- Door panels shown "slid open" are fixed geometry on the hull; there is no animated door node.
- Tail rotors are not canted (blackhawk's real 20 degree cant omitted) so they spin about plain X. Blades are solid lens sections with 0.25-0.45 m cone; rotor discs/blur discs are flat.
- Blur discs are separate meshes with `alphaMode BLEND`; depth sorting against glass may flicker in three.js (set `depthWrite=false`).
- Hulls are stylised proportions (not scaled from drawings); main rotor diameters follow the real aircraft, fuselage lengths are about 9.4 (206), 13 (UH-1), 13.4 (Griffon), 15.5 (UH-60), 13.1 (AH-1), 15.5 m (CH-47).
- Chinook rear pylon is a big chamfered block with two engine nacelles; the rear opening behind the ramp is a dark plate, not a hollow cargo bay.
- Gunship nav light colours follow the aviation convention (red left, green right). Not checked in-game or in a glTF viewer; only Blender-rendered and parsed with `verify_helis.py` (normals unit length, indices valid, base64 matches the GLB).
- A stray folder (4 old PNGs) `C:\blender\review\helis` was created by a first run that used a relative render path; it can be deleted.
