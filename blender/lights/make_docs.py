"""Writes MODEL-NOTES-LIGHTS.md from assets/lights_pack.manifest.json (node tables) + the hand-written sections below.
usage: python blender/lights/make_docs.py"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); GAME = os.path.abspath(os.path.join(HERE, '..', '..'))
m = json.load(open(os.path.join(GAME, 'assets', 'lights_pack.manifest.json')))['pieces']
HEAD = """# Lighting pack (assets/lights_pack.glb + .b64.txt)

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
"""
TAIL = """
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
"""
DESC = {'light_tower': 'Trailer (rails, deck, axle, wheels, mudguards, A-frame drawbar, coupler, jockey wheel), 4 outriggers DOWN on pads, genset enclosure (louvres, door, rear control panel, side connector plate, muffler, exhaust stack with cap), fuel tank with filler cap and gauge, mast cradle, hinged pedestal, 3-section telescoping mast with collars, a cable from the control panel up the mast (clips) to the head junction box, head bar with 6 floodlight panels (3 front, 3 back, tilted 22 deg down). 9.6 m tall.',
        'light_tower_lowered': 'Same trailer with outriggers stowed, mast collapsed to one section laid on the cradle, head on its end. Off pose.',
        'floodlight_pole_2': '8 m: concrete pier, base plate, anchor bolts, tapered steel pole, base shroud, junction box, conduit up the pole and down into the pier, clamp bands, collar, 2 m cross-arm with junction box, 2 lamp heads (bezel, fins, hood, lens) on stems.',
        'floodlight_pole_4': '10 m version, 3 m arm, 4 lamp heads fanned +-8 deg.',
        'floodlight_wall': 'Wall plate with bolts, arm, brace, knuckle, lamp with hood and lens, conduit stub.',
        'floodlight_roof': 'Base plate with bolts, stand pole, two braces, knuckle, lamp.',
        'lamp_cobra': '7.2 m street light: base shaft with service door, tapered pole, curved arm (points +X) with collar, cobra-head luminaire with an underside lens.',
        'lamp_harbour': '4.3 m classic lantern: fluted foot, post with brass collars, scroll arm with banner hook, hexagonal glass lantern with ribs, roof and finial.',
        'lamp_bollard': '0.86 m: base plate, shaft, light band with 4 ribs, cap and dome.',
        'string_lights_8m': 'Two 2.7 m poles with bases and an 8 m catenary cable with 13 evenly spaced bulbs on sockets (sag 0.5 m).',
        'string_lights_span_8m': 'The span only (cable, end hooks, 13 bulbs) for hanging between any two attachment points: ends are `cable_string_lights_span_8m_a/_b`. Parametric builder `string_span(a, b, nb, sag)` in `lights_lib.py`; in JS `y = ya + (yb-ya)*u - sag*4*u*(1-u)`, a bulb every `L/nb`.',
        'generator_small': 'Open-frame portable set: tube frame, engine, alternator, fuel tank, muffler, front control panel with 2 sockets, status lamp, pull handle.',
        'generator_medium': 'Skid-mounted enclosure, belly fuel tank with filler, louvres, door seams, connector panel (4 cam-lock sockets, breakers, e-stop, status lamp), silencer and exhaust stack with rain cap, lifting eye.',
        'generator_large': 'Container-size set: skid with fork pockets, belly tank, radiator housing with grille, louvres, connector bay (2 rows of 5 sockets), exhaust stack, lifting eyes.',
        'cableseg_straight_4m': '4 m ground cable, plugs at both ends.', 'cableseg_90': 'Quarter-turn ground cable (R 1.2 m): starts at the origin heading +Z, ends at about (1.34, 0, 1.34) heading +X.',
        'cableseg_sag_6m': '6 m cable hanging from two sockets 0.9 m high, touching the ground at mid-span.', 'cablereel': 'Reel on an A-frame stand with a 2 m tail ending in a plug (spin axis X).',
        'junction_box': '3-socket ground box with feet, handle and input gland.', 'junction_box_dist': '8-socket distribution box.',
        'searchlight_ground': 'Concrete pad, base drum, bearing ring, rotating yoke (turntable, arms, bosses), head (drum, tapered back, bezel, lens, trunnions, vent, handle), power box with sockets, and the supply cable running onto the base.',
        'spotlight_tripod': 'Tripod with braces, centre column, yoke, spot head (pitch) and a 3 m supply cable with plug.',
        'vehicle_headlights': 'Pair of round headlamps on a 1.3 m mounting bar (origin = bar centre, +Z = out).', 'vehicle_taillights': 'Pair of red lenses and reverse lamps on a bar (+Z = out; turn 180 deg for a rear mount).',
        'vehicle_lightbar': '1.1 m roof bar with 6 lenses, rubber feet and a pigtail.', 'lights_materials_ref': 'Seven small cubes carrying the lamp_on / lamp_off / lens_glass / tail / ind materials. Do not place.'}
L = [HEAD, '## Pieces (triangle counts from the build)\n']
for k, v in m.items():
    L.append('### `%s` (%d tris)\n%s\n' % (k, v['tris'], DESC.get(k, '')))
    if v['empties']:
        L.append('| node | parent | pos (m) | light / role |\n|---|---|---|---|')
        for e in v['empties']:
            x = e['extras']
            if 'light' in x:
                l = x['light']
                r = 'indicator (ind_off -> ind_on)' if l['type'] == 'indicator' else '%s, colour %s, I %s, cone %s deg, range %s m%s' % (l['type'], l['color'], l['I'], l.get('cone_deg', '-'), l['range'], (', group ' + l['group']) if 'group' in l else '')
            else: r = x.get('kind', '') + ((': ' + x['note']) if 'note' in x else '')
            L.append('| `%s` | %s | %s | %s |' % (e['node'], e['parent'], tuple(e['pos']), r))
        L.append('')
L.append(TAIL)
open(os.path.join(GAME, 'MODEL-NOTES-LIGHTS.md'), 'w', encoding='utf-8').write('\n'.join(L))
print('ok')
