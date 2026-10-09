# Fire and flame assets (assets/fire.glb, assets/fire.glb.b64.txt)

Built by `blender/fire/build_fire.py` (python + numpy only; `python blender/fire/build_fire.py [game dir]`). 104 KB binary, 138 KB base64. `blender/fire/verify_fire.py [--render]` re-reads the GLB (names, bounds, triangles, loops, size) and, with `--render`, runs one background Blender (Workbench, `render_fire_blender.py`) and writes `blender/review/fire/fire_preview_sheet.png`.

Metres, +Y up, +Z forward. All top-level nodes sit at the world origin (they overlap if viewed together; pick by name, like air.glb). Every pivot is the node origin: flames at the base centre, y=0.

## Material
- `fire_vc`: white base colour times `COLOR_0` (linear vertex colours), `doubleSided`, `KHR_materials_unlit`. No lighting, no emissive texture. If a loader ignores the unlit extension, use `MeshBasicMaterial({vertexColors:true, side:DoubleSide})` (three.js GLTFLoader already does this). Colours run deep red (base), orange, yellow (tip), with a paler yellow-white hot core lobe.
- `smoke_vc`: lit, rough 1, single sided, grey vertex colours (darker underside, lighter top). Used for smoke and ash. Normals are flat (un-indexed, face normals).
- Fire meshes are indexed with no normals (smallest file). Tongue meshes are shared: every cluster child references the same mesh as `flame_*`.

## Nodes
| Node | Contents | Size | Tris |
|---|---|---|---|
| `flame_s_01..03` | tongue (2 blades + core) | 0.4 m tall, ~0.3 wide | 84 |
| `flame_m_01..03` | tongue (3 blades + core) | 1.0 m tall, ~0.6 wide | 112 |
| `flame_l_01..03` | tongue (4 blades + core) | 2.4 m tall, ~1.5 wide | 140 |
| `fire_camp` | children `fire_camp_t0..4`, ring of 5 medium tongues, r 0.32 | 0.8 m tall, 1.0 wide | 560 |
| `fire_building` | `fire_building_t0..4`, 3 large + 2 medium in a row along X, offset in Z | 6 m wide x 4 m tall | 644 |
| `fire_vehicle` | `fire_vehicle_t0..5`, five medium + one small along Z | 3.2 m long, 1.3 m tall | 644 |
| `fire_tree` | `fire_tree_t0..3`, tall narrow stack | 5 m tall, 1.2 wide | 504 |
| `fire_ground` | `fire_ground_t0..7`, ring (r about 1.2) of small tongues leaning outward | 2.6 m across, 0.5 tall | 672 |
| `ember_01..03` | tiny spark shard (6 tris), 0.1 to 0.2 m | `fire_vc` | 6 |
| `ash_flake_01..02` | flat dark flake, 0.1 m | `smoke_vc` | 6 |
| `smoke_puff_01..03` | lumpy blob, about 1 m across, origin at its centre | `smoke_vc` | 20 / 80 / 80 |
| `smoke_column` | `smoke_column_p0..4`, five puffs stacked and widening upward, origin at the base, 7 m tall | `smoke_vc` | 280 |

Cluster children carry their own translation, yaw, lean and (non-uniform) scale in the file; each child's pivot is its base centre. The scale on a child is the cluster's intended size, so to resize a cluster scale the parent. Real tongue heights come out about 5 percent under the nominal figure because the tip is leaned.

## Animations (all 1.2 s, 25 keys, linear, last key equals first so they loop seamlessly)
- `flicker_s`, `flicker_m`, `flicker_l`: scale and rotation channels on `flame_s_01..03`, `flame_m_01..03`, `flame_l_01..03` (each tongue has its own phase).
- `flicker_cluster`: scale and rotation channels on every cluster child (`fire_*_t#`, 28 nodes), different phases per tongue.
- Per tongue: scale Y = base * (1 + about 0.2 sin(w t + p1) + about 0.09 sin(2 w t + p2)), X/Z squeeze the opposite way (about 35 percent), sway about X and Z of up to about 0.1 rad with a second harmonic, all integer harmonics of the loop. The animated scale and rotation already include each child's placed scale and lean, so playing the clip leaves the layout unchanged on average.
- No clip for embers, ash or smoke (they are for the game's particles or a simple drift).

## Three ways to animate in game
1. Play the baked clip: one `AnimationMixer` per placed cluster (or one shared clip with random `time` offset per instance so neighbours do not sync). Cheapest to author, no per-frame JS beyond `mixer.update`.
2. Procedural: ignore the clip and set each child's `scale.y`, `scale.x/z` and `rotation.x/z` from a noise or sine function of game time and a per-child random phase. Lets intensity change live (flare up, die down: multiply the amplitude and a master scale), and needs no mixers when hundreds of fires exist.
3. Freeze and instance: no animation at all; merge the tongue into `InstancedMesh` per flame size, and give each instance a per-frame scale-Y wobble in a shared vertex or time uniform. Best for many distant fires; a static instance already looks stylised because the blades are curved and twisted.

Fade a fire out by shrinking its parent's Y scale to 0 over a second (tongues collapse to the base), not by opacity.

## Suggested game use
- Instancing: `flame_*` and every cluster child share meshes, so one geometry per flame size (and `ember`, `ash`, `smoke_puff`) is enough; clone nodes for clusters or build clusters at runtime from `flame_*` with the child transforms read from `fire_*`.
- Placement: `fire_camp` for barrels and camp fires; `fire_building` along a roof ridge or wall (scale X to the footprint); `fire_vehicle` on a wreck (scale Z to the length); `fire_tree` on a crown (scale Y with tree height); `fire_ground` for fuel pools and burning ground (scale X/Z to the radius). Plain `flame_s/m/l` for single tongues or particle-like billboards.
- Embers/ash/smoke: emit `ember_*` with the existing spark velocities, `ash_flake_*` falling slowly with spin, `smoke_puff_*` rising and scaling up while the grey fades (set material opacity from the game, or keep it as solid low-poly smoke); `smoke_column` is a static optional plume sitting above `fire_building` or a wreck.
- Night vision: the fire material is unlit and bright, so it blooms; give the fire meshes `toneMapped = false` or a colour multiplier above 1 on the night-vision pass if more bloom is wanted. Do not add baked lighting; the vertex colours are the emission.
- Thermal sensor: render fire with a white-hot override (or add it to the heat layer) and the pale core vertices already give a bright centre; smoke and ash (`smoke_vc`) should read mid-warm to cold, so exclude smoke from the hot layer or give it a low heat value.
- Point light: attach a warm point light at about 40 percent of the cluster height and flicker its intensity with the same phase as the tongues.

## Caveats and unverified
- Not loaded in the game or in a browser glTF viewer; only parsed with numpy and rendered in Blender Workbench (flat shading, vertex colours). The `KHR_materials_unlit` extension is assumed to be supported by the game's GLTFLoader (three.js supports it).
- Animation playback not run in game; the verify script checks loop closure (first equals last keyframe, unit quaternions, 1.2 s) but not visual smoothness beyond the sampled keys.
- The tongue heights are nominal (0.38 / 0.95 / 2.38 m measured). The hot core is a separate short lobe that shows through at the base of each tongue, so the base reads orange-yellow at its centre and deep red at the outer blades.
- The sheet shows clusters at frame 1 of the baked loops only.
