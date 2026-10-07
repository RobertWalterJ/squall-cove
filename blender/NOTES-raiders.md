# Squall Cove raider boats

Four boats (five meshes) in one GLB: `assets/raiders.glb.b64.txt` (194 KB GLB, 259 KB one-line base64, about 3,180 triangles in total, none over 800).
Source: `blender/generators/build_raiders.py`. Manifest and 3/4 review renders: `blender/review/raiders/`.

Rebuild: `_tools/blender-4.2.9-windows-x64/blender.exe -b --python blender/generators/build_raiders.py -- --review` (the `_tools` folder lives in the sibling `squall-cove` repo). It writes the asset, `raiders.json` and the PNGs.

## Conventions

Same as the other boats. Blender is Z up, bow toward +X; the glTF export maps Blender (x, y, z) to three (x, z, -y), so the bow is +X in three, up is +Y, port is -Z. The origin is the waterline: Blender z = 0 is the painted waterline, the keel is below it. Every node sits at the model origin (no row offset), so `nodeByName(glb, 'runner_hull').clone()` goes straight into the `model` group. Plain base-colour materials, no textures or vertex colours (the red, blue and lamp materials are emissive-free except `lamp_b` on the RIB light bar).

## Nodes and FM-style dimensions

Suggested `FM` entries (L and B are the hull; engines hang 0.3 to 0.7 m past the transom, as on `bollard`):

| Node | Boat | FM |
|---|---|---|
| `runner_hull` | Smuggler runner, charcoal, tarp bay, twin outboards | `{ L: 9.4, B: 2.6, D: 1.05, fb: 0.65, deck_z: 0.62 }` |
| `gunboat_hull` | Raider gunboat, red and black | `{ L: 9.4, B: 2.8, D: 1.2, fb: 0.8, deck_z: 0.75 }` |
| `landing_hull`, `landing_ramp` | Landing craft, olive drab | `{ L: 16.0, B: 4.6, D: 2.3, fb: 1.7, deck_z: 0.6 }` |
| `swatrib_hull` | Response RIB, black hull, grey tubes | `{ L: 8.0, B: 2.7, D: 0.95, fb: 0.65, deck_z: 0.18 }` |

`fb` is the gunwale (or tube-top) height above the waterline, `D = fb + draught` (hull bottom at -(D - fb)), `deck_z` is the walking surface above the waterline (the landing craft's troop well floor). Measured bounding boxes including fittings (x = fore/aft, y = height, three coordinates):

| Node | x range | y range | z range (half beam) |
|---|---|---|---|
| runner_hull | -5.37 to 4.70 | -0.64 to 1.56 | +-1.30 |
| gunboat_hull | -5.12 to 4.70 | -0.55 to 3.05 (aerial) | -1.57 to 1.77 (tyre fenders) |
| landing_hull | -8.40 to 8.15 | -0.90 to 4.00 (aerial) | +-2.33 |
| swatrib_hull | -4.67 to 4.00 | -0.82 to 1.38 | +-1.38 |

The hulls are lofted (keel, chine, deck line per station), so the keel is a V on the runner, gunboat and RIB and flat on the landing craft (flat bottom at -0.6, raked up toward the bow).

### Empties and children

- `gunboat_hull` has two child empties, `gunboat_mount0` (foredeck gun, hull-local three position (2.9, 1.55, 0)) and `gunboat_mount1` (aft gun tub, (-2.5, 1.73, 0)). They sit at the top of each pedestal, centred inside a three-sided shield open toward the stern. The gun meshes are the game's job. They are children of the hull, so `hull.clone()` carries them; look them up by name with `getObjectByName`.
- `landing_ramp` is a **separate top-level node** (not a child of the hull), see below.
- There are no `_rig` nodes, props or radar parts.

### Landing craft ramp

- Hinge: the bow edge of the troop well floor, on the centre line. Blender (8.0, 0, 0.6), which is **three position (8.0, 0.6, 0)** in model coordinates. The `landing_ramp` node's origin and its glTF translation are exactly this point, so cloned into the model group it already sits in place.
- Closed (raised) = rotation 0: a plate 3.5 m wide, 2.0 m long and 0.14 m thick standing vertical on the bow, its top 2.6 m above the waterline (gunwale is 1.7 m). Its inner face is the +X side, with ribs and side flanges.
- Open: rotate about the local **Z axis, negative**. `-Math.PI / 2` lays the ramp level with the troop-well floor, sticking out 2.0 m ahead of the bow (to x = 10.0). The intended open angle for beaching is **-100 degrees (`rotation.z = -1.745`)**, which slopes the ramp tip down about 0.35 m (to y = 0.25) so it lands on a shelving beach. Animate `rotation.z` from 0 down to -1.745 over a couple of seconds; the review render `landing_ramp_open_3q.png` shows the open pose.
- The ramp mesh has no baked rotation, so rotation is the only transform you need to set.

## Review images

`blender/review/raiders/<key>_3q_front.png`, `<key>_3q_rear.png` for runner, gunboat, landing and swatrib, plus `landing_ramp_open_3q.png`. Flat Workbench lighting, so the in-game look will be a bit warmer. `raiders.json` holds the manifest (sizes, triangles, hinge, mount positions).

## Caveats

- Colours are fixed in `PAL` at the top of the generator. The runner is intentionally unmarked.
- The gunboat's deck and wheelhouse are black and read very dark in dim light; the red topsides carry the livery.
- Hull bounding boxes include outboards, fenders and aerials, so use the FM `L` and `B` above (not the bounding box) for the physics box.
- No propellers are separate nodes, so nothing spins; the game's `propL`/`propR` naming scheme is not used.
