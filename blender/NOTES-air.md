# Air + emplacements (assets/air.glb.b64.txt)

Built by `blender/air/build_air.py` (python + numpy only; `python blender/air/build_air.py <game dir>` writes `assets/air.glb` and `assets/air.glb.b64.txt`, 0.76 MB / 1.02 MB base64). `blender/air/verify_air.py [--render]` parses the GLB (node tree, per-node triangles, accessor bounds) and renders previews to `blender/review/air/<model>_{3q,side,top,back}.png` (own numpy/PIL painter's renderer, not Blender).

Metres, +Z forward, +Y up, model's left = +X (right = -X). No skins, no animations, no textures/UVs/text. Flat shaded (un-indexed, face normals), plain materials named `air_#hex`. All eight models are separate top-level scene nodes, all at the world origin (they overlap if viewed together; pick by name). Every child node's origin is its pivot, geometry is local to it.

| Top node | Child nodes (pivot / axis) | Tris (total) |
|---|---|---|
| `griffon` (~11 m nose to tail-rotor, origin = on the ground between the skids, fuselage centre z=0) | `griffon_mainrotor` (hub, spin about Y, 14 m disc), `griffon_tailrotor` (hub on the left of the fin, spin about X), `griffon_gun` (pintle pivot in the open right door; barrel points -X; aim by rotating) | 1332 |
| `gunship` (30.4 m, 40 m span, origin = fuselage axis at mid-length, wheels hang to y=-2.6, tail fin top y=7) | `gunship_prop_0..3` (hub, spin about Z; 0 = left outer x=+12, 1 = left inner +5.5, 2 = right inner -5.5, 3 = right outer -12), `gunship_minigun` (z=8.0), `gunship_cannon` (z=4.3), `gunship_howitzer` (z=-2.0): all at x=+1.92, y=-0.35, barrels point +X (left), rest pose horizontal | 2864 |
| `parachute` (origin = harness point, canopy 6 m span, 12 red/white gores centred 6.1 m above) | none | 420 |
| `emplacement_mg` (ring r 1.4 m, open at the rear -Z, gun faces +Z) | `emplacement_mg_gun` (tripod head, pivot for yaw and pitch) | 948 |
| `emplacement_aa` (concrete pad r 2.2 m) | `emplacement_aa_barrels` (trunnion, barrels along +Z, pitch about X) | 656 |
| `emplacement_mortar` (base plate at the origin, tube 72 degrees elevated toward +Z, loose shells and a crate) | none | 1488 |
| `shell_heavy` (0.5 m 105 mm: brass case, olive body, copper band, yellow stripe; nose +Z, origin = centre) | none | 310 |
| `crate_drop` (0.8 m crate, origin = centre of its base) | `crate_drop_chute` (origin at crate base; hide on landing) | 404 |

## Caveats
- The two parachute canopies (and their lines) use `doubleSided` red/white materials; everything else is single sided.
- Gunship guns are in a horizontal rest pose; the real aircraft fires out and down, so the game should tilt or aim them. The fuselage has a fixed port box behind each barrel.
- Propeller blades are flat pitched boxes (no blur disc); the game can swap in a disc when spinning fast.
- The griffon door opening is a dark patch on the hull (no modelled interior beyond two seats); the sliding door panel sits slid back on the rear cabin.
- Rotating parts rotate about their node's local axis only if the game applies the rotation to the node itself (`rotation` is not set in the file).
- Emplacement yaw is not a separate node: rotate the whole model, or `emplacement_*_gun` for the MG.
- Mortar shells are lying on the ground; the tube has no separate node.
- Not checked in a real glTF viewer or in-game (no Chrome run, per instructions); only parsed and software-rendered.
