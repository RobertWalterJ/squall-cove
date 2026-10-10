# Lighting pack (assets/lights_pack.glb + .b64.txt)

Built by `blender/lights/build_lights.py` (python + numpy; Blender 4.2 is used only for the preview renders). Verified by `blender/lights/verify_lights.py`. Preview: `docs/lights_preview_sheet.png` (night scene + every piece, 3/4 view with a front-view inset). FX: `assets/lights_fx_*` (see the end).

Metres, +Z = front / beam, +Y up, model's left = +X. 26 top-level nodes at the origin (they overlap; pick by name and `.clone(true)` for each instance). Base on y = 0 unless a piece says otherwise. Flat shaded: **the file has no normals**, so three.js GLTFLoader flat-shades it (vertices welded, uint16 indices). Nodes carry translation, and the empties plus the pivot groups carry a rotation quaternion. No textures or UVs.

## Materials
Plain colours are `lights_#hex`. Lighting materials (toggle by swapping, or drive `emissiveIntensity`):

| name | use |
|---|---|
| `lamp_off` | every lens / bulb / glass body: dull warm white. Swap to `lamp_on` when lit. |
| `lamp_on` | emissive lens (emissive 1, .88, .58). Only the swatch cubes in `lights_materials_ref` use it (GLTFLoader creates materials only when used), so take it from there, or clone `lamp_off` and set `emissive`. |
| `tail_off` / `tail_on` | red tail / brake lens, off and emissive. |
| `ind_off` / `ind_on` | green status lamp on generators, junction boxes and the searchlight power box (the game's GENON equivalent). |
| `lens_glass` | translucent glass (alpha 0.38, blend, double sided). Defined for the game; no piece uses it (solid `lamp_off` lenses are cheaper and read well). |

In game: traverse the clone, collect meshes whose `material.name === 'lamp_off'` into a `lens` list, and assign the shared on/off materials (what `LENSON/LENSOFF` does today); `material.clone()` first if one instance needs its own colour.

## Empties
* `lightpt_*`: a light emitter. Local +Z is the beam direction (rotation baked into the quaternion; in moving parts it is a child of the moving node so it turns with it). Position is just in front of the lens. `extras.light` = `{type: spot|point|indicator, color, I, cone_deg (full angle), range, group?}`. `I` is in the game's `LIGHT.fix .I` units (v9.9.11 uses tower 1100, flood 700, lamp 190, string 70); `indicator` is the green status lamp (swap `ind_off` to `ind_on`, no real light).
* `cable_*`: an attachment end for a cable. +Z points out of the socket / gland, the way a plug goes. `extras.kind = 'cable_end'`.
* `pivot_*`, `searchlight_yaw_axis`: documented axes. `smoke_*`: exhaust point (puffs / smoke when damaged).
Three.js: `node.getWorldPosition(p)`, `node.getWorldQuaternion(q)`, beam = `(0,0,1).applyQuaternion(q)`. For a SpotLight: `light.position` = the empty, `light.target` at `p + beam * range`.

## How the game should use it
1. Load once (`loadGLB('lights_pack')`, same b64 form as the other packs). `const proto = scene.getObjectByName('light_tower')`; per capture point `const g = proto.clone(true)`.
2. Put `g.position` at the ground point and `g.rotation.y` = facing (+Z is the way the lamps shine).
3. For each `lightpt_*` found by `g.traverse`, create the real light through the budget system (`lightWant`) from `extras.light`. A shot-out lamp swaps its lens to `lamp_off`. Group lights: the light tower has 6 lamps in two groups (`front`, `back`, three each): drive one light per group (I 1100, cone 62, range 58) instead of six. String lights have 13 bulbs: use 1 to 3 point lights along the span.
4. Generators: the front (+Z) face has the connector panel. To connect a light, run cables from a `cable_generator_*_out_N` empty to the light's `cable_*` empty with `cableseg_*` pieces: move the cable root so its `_a` empty coincides with the socket empty (position and, if you want, yaw), then chain the next piece on `_b`. For a free span use `cableseg_sag_6m` (parametric builder `cable_sag_6m(L, h, sag)` in `pieces_b.py`; scaling its z by +-30% is fine) or draw `TubeGeometry` (radius 0.026, 6 sides) along a `CatmullRomCurve3` with the middle sagged by about 0.15 x length. Ground cables lie at y = 0.042.
5. Origins: wall floodlight = the wall surface at the lamp height (back plate flush, extends +Z out of the wall, the lamp hangs 0.28 m below the origin); roof floodlight = the roof surface.
6. Searchlight: `searchlight_yoke` rotation.y = bearing; its child `searchlight_head` rotation.x = elevation (negative = up). `lightpt_searchlight_ground` is a child of the head and follows. `spotlight_head` of `spotlight_tripod` is the same (rotation.x; yaw by rotating the root).
7. The lowered light tower is a separate root `light_tower_lowered` (swap the roots). Hinge empties: `pivot_light_tower_mast_hinge`, `pivot_light_tower_lowered_mast_hinge`.
8. Shadows: leave off for this pack (small pieces); at most the tower mast and poles.

## Pieces (triangle counts from the build)

### `light_tower` (1762 tris)
Trailer (rails, deck, axle, wheels, mudguards, A-frame drawbar, coupler, jockey wheel), 4 outriggers DOWN on pads, genset enclosure (louvres, door, rear control panel, side connector plate, muffler, exhaust stack with cap), fuel tank with filler cap and gauge, mast cradle, hinged pedestal, 3-section telescoping mast with collars, a cable from the control panel up the mast (clips) to the head junction box, head bar with 6 floodlight panels (3 front, 3 back, tilted 22 deg down). 9.6 m tall.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `lightpt_light_tower_0` | light_tower | (-0.62, 9.345, -0.889) | spot, colour [1, 0.93, 0.78], I 370, cone 62 deg, range 58 m, group front |
| `lightpt_light_tower_1` | light_tower | (0.0, 9.345, -0.889) | spot, colour [1, 0.93, 0.78], I 370, cone 62 deg, range 58 m, group front |
| `lightpt_light_tower_2` | light_tower | (0.62, 9.345, -0.889) | spot, colour [1, 0.93, 0.78], I 370, cone 62 deg, range 58 m, group front |
| `lightpt_light_tower_3` | light_tower | (-0.62, 9.345, -1.711) | spot, colour [1, 0.93, 0.78], I 370, cone 62 deg, range 58 m, group back |
| `lightpt_light_tower_4` | light_tower | (0.0, 9.345, -1.711) | spot, colour [1, 0.93, 0.78], I 370, cone 62 deg, range 58 m, group back |
| `lightpt_light_tower_5` | light_tower | (0.62, 9.345, -1.711) | spot, colour [1, 0.93, 0.78], I 370, cone 62 deg, range 58 m, group back |
| `cable_light_tower_genset` | light_tower | (0.0, 1.2, -1.1) | cable_end: generator control panel (rear), internal cable leaves here |
| `cable_light_tower_ext` | light_tower | (0.83, 1.1, 0.3) | cable_end: external feed socket on the +X side of the enclosure |
| `cable_light_tower_head` | light_tower | (0.0, 9.25, -1.3) | cable_end: cable gland on the lamp head junction box |
| `pivot_light_tower_mast_hinge` | light_tower | (0.0, 1.85, -1.3) | pivot: mast hinge axis (X). node pose is fixed in this file; the lowered pose is a separate root |

### `light_tower_lowered` (1530 tris)
Same trailer with outriggers stowed, mast collapsed to one section laid on the cradle, head on its end. Off pose.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `cable_light_tower_lowered_genset` | light_tower_lowered | (0.0, 1.2, -1.1) | cable_end: generator control panel (rear), internal cable leaves here |
| `cable_light_tower_lowered_ext` | light_tower_lowered | (0.83, 1.1, 0.3) | cable_end: external feed socket on the +X side of the enclosure |
| `cable_light_tower_lowered_head` | light_tower_lowered | (0.0, 1.85, 1.4) | cable_end: cable gland on the lamp head junction box |
| `pivot_light_tower_lowered_mast_hinge` | light_tower_lowered | (0.0, 1.85, -1.3) | pivot: mast hinge axis (X). node pose is fixed in this file; the lowered pose is a separate root |

### `floodlight_pole_2` (818 tris)
8 m: concrete pier, base plate, anchor bolts, tapered steel pole, base shroud, junction box, conduit up the pole and down into the pier, clamp bands, collar, 2 m cross-arm with junction box, 2 lamp heads (bezel, fins, hood, lens) on stems.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `lightpt_floodlight_pole_2_0` | floodlight_pole_2 | (-0.7, 8.215, 0.319) | spot, colour [1, 0.93, 0.78], I 700, cone 72 deg, range 44 m |
| `lightpt_floodlight_pole_2_1` | floodlight_pole_2 | (0.7, 8.215, 0.319) | spot, colour [1, 0.93, 0.78], I 700, cone 72 deg, range 44 m |
| `cable_floodlight_pole_2_feed` | floodlight_pole_2 | (0.0, 0.2, 0.45) | cable_end: ground feed enters the pier on the +Z side |

### `floodlight_pole_4` (1154 tris)
10 m version, 3 m arm, 4 lamp heads fanned +-8 deg.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `lightpt_floodlight_pole_4_0` | floodlight_pole_4 | (-1.172, 10.215, 0.317) | spot, colour [1, 0.93, 0.78], I 560, cone 72 deg, range 52 m |
| `lightpt_floodlight_pole_4_1` | floodlight_pole_4 | (-0.422, 10.215, 0.317) | spot, colour [1, 0.93, 0.78], I 560, cone 72 deg, range 52 m |
| `lightpt_floodlight_pole_4_2` | floodlight_pole_4 | (0.422, 10.215, 0.317) | spot, colour [1, 0.93, 0.78], I 560, cone 72 deg, range 52 m |
| `lightpt_floodlight_pole_4_3` | floodlight_pole_4 | (1.172, 10.215, 0.317) | spot, colour [1, 0.93, 0.78], I 560, cone 72 deg, range 52 m |
| `cable_floodlight_pole_4_feed` | floodlight_pole_4 | (0.0, 0.2, 0.45) | cable_end: ground feed enters the pier on the +Z side |

### `floodlight_wall` (296 tris)
Wall plate with bolts, arm, brace, knuckle, lamp with hood and lens, conduit stub.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `lightpt_floodlight_wall` | floodlight_wall | (0.0, -0.155, 0.71) | spot, colour [1, 0.93, 0.78], I 560, cone 80 deg, range 36 m |
| `cable_floodlight_wall` | floodlight_wall | (0.0, 0.17, 0.02) | cable_end: conduit entry at the top of the wall plate |

### `floodlight_roof` (332 tris)
Base plate with bolts, stand pole, two braces, knuckle, lamp.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `lightpt_floodlight_roof` | floodlight_roof | (0.0, 1.131, 0.295) | spot, colour [1, 0.93, 0.78], I 620, cone 75 deg, range 40 m |
| `cable_floodlight_roof` | floodlight_roof | (0.0, 0.06, -0.2) | cable_end: cable enters at the base plate edge (-Z) |

### `lamp_cobra` (236 tris)
7.2 m street light: base shaft with service door, tapered pole, curved arm (points +X) with collar, cobra-head luminaire with an underside lens.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `lightpt_lamp_cobra` | lamp_cobra | (1.66, 7.02, 0.0) | spot, colour [1, 0.8, 0.5], I 190, cone 110 deg, range 27 m |
| `cable_lamp_cobra` | lamp_cobra | (0.0, 0.35, 0.16) | cable_end: ground feed enters the service door of the base |

### `lamp_harbour` (448 tris)
4.3 m classic lantern: fluted foot, post with brass collars, scroll arm with banner hook, hexagonal glass lantern with ribs, roof and finial.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `lightpt_lamp_harbour` | lamp_harbour | (0.0, 3.78, 0.0) | point, colour [1, 0.82, 0.52], I 150, cone 160 deg, range 22 m |
| `cable_lamp_harbour` | lamp_harbour | (0.0, 0.3, -0.2) | cable_end: ground feed enters the foot on the -Z side |

### `lamp_bollard` (196 tris)
0.86 m: base plate, shaft, light band with 4 ribs, cap and dome.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `lightpt_lamp_bollard` | lamp_bollard | (0.0, 0.62, 0.0) | point, colour [1, 0.8, 0.5], I 60, cone 150 deg, range 9 m |
| `cable_lamp_bollard` | lamp_bollard | (0.0, 0.04, -0.18) | cable_end: ground feed under the base plate edge |

### `string_lights_8m` (942 tris)
Two 2.7 m poles with bases and an 8 m catenary cable with 13 evenly spaced bulbs on sockets (sag 0.5 m).

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `lightpt_string_lights_8m_00` | string_lights_8m | (-3.698, 2.42, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_8m_01` | string_lights_8m | (-3.089, 2.291, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_8m_02` | string_lights_8m | (-2.477, 2.185, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_8m_03` | string_lights_8m | (-1.861, 2.101, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_8m_04` | string_lights_8m | (-1.242, 2.041, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_8m_05` | string_lights_8m | (-0.622, 2.005, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_8m_06` | string_lights_8m | (0.0, 1.993, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_8m_07` | string_lights_8m | (0.622, 2.005, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_8m_08` | string_lights_8m | (1.242, 2.041, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_8m_09` | string_lights_8m | (1.861, 2.101, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_8m_10` | string_lights_8m | (2.477, 2.185, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_8m_11` | string_lights_8m | (3.089, 2.291, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_8m_12` | string_lights_8m | (3.698, 2.42, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `cable_string_lights_8m_a` | string_lights_8m | (-4.06, 2.6, 0.0) | cable_end: attachment end A (x = -L/2) |
| `cable_string_lights_8m_b` | string_lights_8m | (4.06, 2.6, 0.0) | cable_end: attachment end B (x = +L/2) |

### `string_lights_span_8m` (782 tris)
The span only (cable, end hooks, 13 bulbs) for hanging between any two attachment points: ends are `cable_string_lights_span_8m_a/_b`. Parametric builder `string_span(a, b, nb, sag)` in `lights_lib.py`; in JS `y = ya + (yb-ya)*u - sag*4*u*(1-u)`, a bulb every `L/nb`.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `lightpt_string_lights_span_8m_00` | string_lights_span_8m | (-3.698, 2.42, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_span_8m_01` | string_lights_span_8m | (-3.089, 2.291, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_span_8m_02` | string_lights_span_8m | (-2.477, 2.185, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_span_8m_03` | string_lights_span_8m | (-1.861, 2.101, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_span_8m_04` | string_lights_span_8m | (-1.242, 2.041, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_span_8m_05` | string_lights_span_8m | (-0.622, 2.005, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_span_8m_06` | string_lights_span_8m | (0.0, 1.993, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_span_8m_07` | string_lights_span_8m | (0.622, 2.005, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_span_8m_08` | string_lights_span_8m | (1.242, 2.041, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_span_8m_09` | string_lights_span_8m | (1.861, 2.101, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_span_8m_10` | string_lights_span_8m | (2.477, 2.185, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_span_8m_11` | string_lights_span_8m | (3.089, 2.291, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `lightpt_string_lights_span_8m_12` | string_lights_span_8m | (3.698, 2.42, 0.0) | point, colour [1, 0.82, 0.5], I 6, cone 160 deg, range 5 m |
| `cable_string_lights_span_8m_a` | string_lights_span_8m | (-4.06, 2.6, 0.0) | cable_end: attachment end A (x = -L/2) |
| `cable_string_lights_span_8m_b` | string_lights_span_8m | (4.06, 2.6, 0.0) | cable_end: attachment end B (x = +L/2) |

### `generator_small` (490 tris)
Open-frame portable set: tube frame, engine, alternator, fuel tank, muffler, front control panel with 2 sockets, status lamp, pull handle.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `cable_generator_small_out` | generator_small | (-0.125, 0.3, 0.34) | cable_end: power socket pair on the front panel |
| `lightpt_generator_small_status` | generator_small | (0.2, 0.35, 0.3) | indicator (ind_off -> ind_on) |

### `generator_medium` (788 tris)
Skid-mounted enclosure, belly fuel tank with filler, louvres, door seams, connector panel (4 cam-lock sockets, breakers, e-stop, status lamp), silencer and exhaust stack with rain cap, lifting eye.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `cable_generator_medium_out_0` | generator_medium | (-0.02, 0.72, 0.5) | cable_end: cam-lock socket 0 |
| `cable_generator_medium_out_1` | generator_medium | (0.13, 0.72, 0.5) | cable_end: cam-lock socket 1 |
| `cable_generator_medium_out_2` | generator_medium | (0.28, 0.72, 0.5) | cable_end: cam-lock socket 2 |
| `cable_generator_medium_out_3` | generator_medium | (0.43, 0.72, 0.5) | cable_end: cam-lock socket 3 |
| `lightpt_generator_medium_status` | generator_medium | (0.3, 0.62, 0.47) | indicator (ind_off -> ind_on) |
| `smoke_generator_medium_exhaust` | generator_medium | (0.6, 2.03, -0.16) | fx: puff / smoke emitter when damaged |

### `generator_large` (1200 tris)
Container-size set: skid with fork pockets, belly tank, radiator housing with grille, louvres, connector bay (2 rows of 5 sockets), exhaust stack, lifting eyes.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `cable_generator_large_out_0` | generator_large | (-0.3, 0.72, 0.75) | cable_end: cam-lock socket (bottom row) 0 |
| `cable_generator_large_out_1` | generator_large | (-0.1, 0.72, 0.75) | cable_end: cam-lock socket (bottom row) 1 |
| `cable_generator_large_out_2` | generator_large | (0.1, 0.72, 0.75) | cable_end: cam-lock socket (bottom row) 2 |
| `cable_generator_large_out_3` | generator_large | (0.3, 0.72, 0.75) | cable_end: cam-lock socket (bottom row) 3 |
| `cable_generator_large_out_4` | generator_large | (0.5, 0.72, 0.75) | cable_end: cam-lock socket (bottom row) 4 |
| `lightpt_generator_large_status` | generator_large | (0.6, 1.3, 0.7) | indicator (ind_off -> ind_on) |
| `smoke_generator_large_exhaust` | generator_large | (1.1, 3.01, 0.1) | fx: puff / smoke emitter when damaged |

### `cableseg_straight_4m` (120 tris)
4 m ground cable, plugs at both ends.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `cable_straight_4m_a` | cableseg_straight_4m | (0.0, 0.042, 0.0) | cable_end |
| `cable_straight_4m_b` | cableseg_straight_4m | (0.0, 0.042, 4.0) | cable_end |

### `cableseg_90` (216 tris)
Quarter-turn ground cable (R 1.2 m): starts at the origin heading +Z, ends at about (1.34, 0, 1.34) heading +X.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `cable_90_a` | cableseg_90 | (0.0, 0.042, 0.0) | cable_end |
| `cable_90_b` | cableseg_90 | (1.34, 0.042, 1.34) | cable_end |

### `cableseg_sag_6m` (300 tris)
6 m cable hanging from two sockets 0.9 m high, touching the ground at mid-span.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `cable_sag_6m_a` | cableseg_sag_6m | (0.0, 0.9, 0.0) | cable_end |
| `cable_sag_6m_b` | cableseg_sag_6m | (0.0, 0.9, 6.0) | cable_end |

### `cablereel` (436 tris)
Reel on an A-frame stand with a 2 m tail ending in a plug (spin axis X).

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `cable_reel_end` | cablereel | (0.0, 0.042, 2.35) | cable_end: free end of the reel (plug) |
| `pivot_cablereel_hub` | cablereel | (0.0, 0.5, 0.0) | pivot: reel spin axis (X) |

### `junction_box` (300 tris)
3-socket ground box with feet, handle and input gland.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `cable_junction_box_out_0` | junction_box | (-0.14, 0.22, 0.23) | cable_end: output socket 0 |
| `cable_junction_box_out_1` | junction_box | (0.0, 0.22, 0.23) | cable_end: output socket 1 |
| `cable_junction_box_out_2` | junction_box | (0.14, 0.22, 0.23) | cable_end: output socket 2 |
| `cable_junction_box_in` | junction_box | (0.0, 0.2, -0.23) | cable_end: fixed input gland |

### `junction_box_dist` (540 tris)
8-socket distribution box.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `cable_junction_box_dist_out_0` | junction_box_dist | (-0.3, 0.2, 0.25) | cable_end: lower row socket 0 |
| `cable_junction_box_dist_out_4` | junction_box_dist | (-0.3, 0.38, 0.25) | cable_end: upper row socket 4 |
| `cable_junction_box_dist_out_1` | junction_box_dist | (-0.1, 0.2, 0.25) | cable_end: lower row socket 1 |
| `cable_junction_box_dist_out_5` | junction_box_dist | (-0.1, 0.38, 0.25) | cable_end: upper row socket 5 |
| `cable_junction_box_dist_out_2` | junction_box_dist | (0.1, 0.2, 0.25) | cable_end: lower row socket 2 |
| `cable_junction_box_dist_out_6` | junction_box_dist | (0.1, 0.38, 0.25) | cable_end: upper row socket 6 |
| `cable_junction_box_dist_out_3` | junction_box_dist | (0.3, 0.2, 0.25) | cable_end: lower row socket 3 |
| `cable_junction_box_dist_out_7` | junction_box_dist | (0.3, 0.38, 0.25) | cable_end: upper row socket 7 |
| `cable_junction_box_dist_in` | junction_box_dist | (-0.2, 0.3, -0.25) | cable_end: fixed input gland |

### `searchlight_ground` (946 tris)
Concrete pad, base drum, bearing ring, rotating yoke (turntable, arms, bosses), head (drum, tapered back, bezel, lens, trunnions, vent, handle), power box with sockets, and the supply cable running onto the base.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `lightpt_searchlight_ground` | searchlight_head | (0.0, 0.0, 0.8) | spot, colour [1, 0.96, 0.88], I 2400, cone 14 deg, range 190 m |
| `cable_searchlight_power` | searchlight_ground | (1.15, 0.3, 0.0) | cable_end: power box socket pair (socket face looks -X toward the base) |
| `searchlight_yaw_axis` | searchlight_ground | (0.0, 0.78, 0.0) | pivot: yoke yaw axis (Y); node searchlight_yoke carries it |

### `spotlight_tripod` (582 tris)
Tripod with braces, centre column, yoke, spot head (pitch) and a 3 m supply cable with plug.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `lightpt_spotlight_tripod` | spotlight_head | (0.0, 0.0, 0.27) | spot, colour [1, 0.96, 0.88], I 800, cone 16 deg, range 90 m |
| `cable_spotlight_tripod` | spotlight_tripod | (0.0, 0.042, -3.13) | cable_end: plug end of the supply cable (lying on the ground) |

### `vehicle_headlights` (288 tris)
Pair of round headlamps on a 1.3 m mounting bar (origin = bar centre, +Z = out).

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `lightpt_vehicle_headlight_l` | vehicle_headlights | (0.55, 0.0, 0.12) | spot, colour [1, 0.95, 0.82], I 160, cone 40 deg, range 45 m, group headlights |
| `lightpt_vehicle_headlight_r` | vehicle_headlights | (-0.55, 0.0, 0.12) | spot, colour [1, 0.95, 0.82], I 160, cone 40 deg, range 45 m, group headlights |
| `cable_vehicle_headlights` | vehicle_headlights | (0.0, 0.0, -0.14) | cable_end: harness entry at the centre mount |

### `vehicle_taillights` (96 tris)
Pair of red lenses and reverse lamps on a bar (+Z = out; turn 180 deg for a rear mount).

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `lightpt_vehicle_tail_l` | vehicle_taillights | (0.55, 0.018, 0.06) | point, colour [1, 0.08, 0.05], I 12, cone 100 deg, range 7 m, group tail |
| `lightpt_vehicle_reverse_l` | vehicle_taillights | (0.55, -0.04, 0.06) | point, colour [1, 0.97, 0.9], I 20, cone 90 deg, range 9 m, group reverse |
| `lightpt_vehicle_tail_r` | vehicle_taillights | (-0.55, 0.018, 0.06) | point, colour [1, 0.08, 0.05], I 12, cone 100 deg, range 7 m, group tail |
| `lightpt_vehicle_reverse_r` | vehicle_taillights | (-0.55, -0.04, 0.06) | point, colour [1, 0.97, 0.9], I 20, cone 90 deg, range 9 m, group reverse |
| `cable_vehicle_taillights` | vehicle_taillights | (0.0, 0.0, -0.1) | cable_end: harness entry at the centre mount |

### `vehicle_lightbar` (168 tris)
1.1 m roof bar with 6 lenses, rubber feet and a pigtail.

| node | parent | pos (m) | light / role |
|---|---|---|---|
| `lightpt_vehicle_lightbar_0` | vehicle_lightbar | (-0.45, 0.19, 0.082) | spot, colour [0.95, 0.97, 1], I 120, cone 24 deg, range 55 m, group lightbar |
| `lightpt_vehicle_lightbar_1` | vehicle_lightbar | (-0.27, 0.19, 0.082) | spot, colour [0.95, 0.97, 1], I 120, cone 24 deg, range 55 m, group lightbar |
| `lightpt_vehicle_lightbar_2` | vehicle_lightbar | (-0.09, 0.19, 0.082) | spot, colour [0.95, 0.97, 1], I 120, cone 24 deg, range 55 m, group lightbar |
| `lightpt_vehicle_lightbar_3` | vehicle_lightbar | (0.09, 0.19, 0.082) | spot, colour [0.95, 0.97, 1], I 120, cone 24 deg, range 55 m, group lightbar |
| `lightpt_vehicle_lightbar_4` | vehicle_lightbar | (0.27, 0.19, 0.082) | spot, colour [0.95, 0.97, 1], I 120, cone 24 deg, range 55 m, group lightbar |
| `lightpt_vehicle_lightbar_5` | vehicle_lightbar | (0.45, 0.19, 0.082) | spot, colour [0.95, 0.97, 1], I 120, cone 24 deg, range 55 m, group lightbar |
| `cable_vehicle_lightbar` | vehicle_lightbar | (0.55, 0.05, -0.3) | cable_end: pigtail end (12 V plug) |

### `lights_materials_ref` (84 tris)
Seven small cubes carrying the lamp_on / lamp_off / lens_glass / tail / ind materials. Do not place.


## Light FX (assets/lights_fx_*): design notes, no game code
| file | what | how to draw |
|---|---|---|
| `lights_fx_cone.glb` + `lights_fx_cone.png` | open cone (apex at the lens = origin, opens along +Z, length 1, far radius 0.5, 24 sides, UV u = along the beam, v = around). Texture is alpha only: bright at the lens fading along the length, a hotspot near the lens, faint dust streaks around the circumference (seamless in v) | Unlit, additive, `depthWrite false`, double sided. Scale x,y by `2*tan(cone/2)*L` and z by `L` where `L = 0.6..1 x range`. Tint with the lamp colour. In the shader multiply alpha by `pow(abs(dot(N,V)), 1.5)` (soft silhouette edge) and by `haze`. A second thinner copy (scale 0.35, alpha x0.6) gives the hot core. Scroll `uv.y` slowly (0.01/s) for drifting dust, only in fog or smoke. |
| `lights_fx_beam_glow.png` | long soft streak (x along the beam, 512x64), widens with distance | One axis-aligned billboard strip from the lens along the beam, length `min(range,120)` m, additive. It is what stays visible from far away. |
| `lights_fx_flare.png` | lens flare / bloom sprite: core, halo, 4-point star, faint ring | Screen-space sprite at the lens, additive, depth-tested (depth read or a ray) so a lamp behind a wall does not glare. Size in pixels `clamp(900 * lensSize / dist, 12, 220)`, alpha x `max(0, dot(beam, toCamera))^2` (no flare from behind). |
| `lights_fx_pool.png` | ground light pool, soft elliptical edge, brighter centre | Quad on the ground (polygonOffset), additive, tinted. Centre = beam hit point (spot) or foot (lamp); long axis along the beam's ground projection, semi-axes `range*tan(cone/2)` along (divide by cos(tilt) for a tilted spot) and 0.6x across. Omni lamps: round, radius 0.6 x range. |
| `lights_fx_wet.png` | wet-ground reflection smear (x across, y = distance from the lamp foot) | Wet or raining ground only: a strip on the ground under each bright lamp, pointing away from the camera, additive, alpha x `wetness * 0.7`, length about 1.5 x lamp height. |

### Strength against the air
`haze = clamp(0.15 + 1.0*fog + 0.8*mist + 1.2*smoke + 0.5*rain + 0.4*dust, 0.1, 1)` (clear air about 0.15, thick fog 1). Cone and beam-glow alpha scale with `haze`; flare size x `(1 + 0.8*haze)` and alpha x `(0.6 + 0.4*haze)` (the bloom round a bare lamp is bigger in fog); pool alpha x `(1 - 0.3*haze)`. In clear air you see only the hot core, the flare and the pool; the full cone appears in fog, mist or smoke. Night only (x `LIGHT.lampK`). Distance: beyond about 150 m replace the cone by the beam-glow strip plus the flare; beyond about 400 m only the flare (6 to 14 px, additive; it also reads as a lit base). Budget: at most about 6 cones and 12 flares on screen; phones draw flares and pools only.
