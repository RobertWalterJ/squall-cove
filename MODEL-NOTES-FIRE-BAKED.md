# Baked fire sprites (assets/fire/*)

Hyper-real but cheap fire for Squall Cove: 38 baked fire types, each a set of flipbook atlases with lifecycle clips, made
from a small 3D combustion simulation. The low-poly `assets/fire.glb` stays as the cheap far LOD.
Rerun and parameters: `tools/fire/README.md`. Preview: `docs/fire_preview_sheet.png`. Live viewer (animated, lifecycle,
spreading front, explosion with flaming debris): `docs/fire_viewer.html` (or `tools/fire/Open fire viewer.bat`).

## What is physical, and what is not
Inspired by Fire-X (Wrede et al., SIGGRAPH Asia 2025), an offline multi-species solver. This is our own reduced model,
not a reproduction, tuned by eye against the look of real fires.

Modelled: stable-fluids flow (MacCormack advection, FFT pressure projection, buoyancy from temperature, vorticity
confinement, drag); fields for fuel, oxidiser (air = 1, nitrogen implicit), temperature, soot, burned products and fuel age;
the reaction F + s O -> products, mixing-limited, heat release proportional to burnt fuel, ignition above a threshold
temperature, radiative cooling (more with soot); soot formed only when fuel-rich, hot and old enough, burnt off in hot air;
blue premixed colour from the lean part of the reaction, orange from soot incandescence (blackbody-like ramp); a water-spray
sink (heat removal, steam, fuel and soot washout, raised ignition threshold) which makes the extinguish clips.

Scripted rather than simulated: the **lifecycle** is a fuel-supply schedule (ignite, growth, developed, decay) applied to the
vents; **explosions** inject an expanding sphere of burning soot-laden fuel plus a radial kick (the solver is incompressible, so
the expansion itself is scripted; the rising bubble, curling head and smoke are simulated); **carried flames** (flaming debris)
are a flame on a fixed object in a uniform wind equal to the object's speed (the flame seen from the object); **front tiles**
are the same solver periodic in x so they tile; **fuel flare-ups** are random fuel pulses that also throw off a puff of soot.
Approximated or missing: real chemistry and kinetics, thermal expansion, radiative transfer between cells, lumped products
(CO2 and water vapour are one field, used only for steam), sub-grid turbulence in the solver. The sim grid is coarse
(about 32x32x48 cells, 0.025 to 0.5 m per cell by type); fine detail is a scrolling procedural noise volume plus a small 2D warp
added at render time (cosmetic). Smoke shading is single-scatter style (light from above through the column) with an
orange under-light from the temperature field. Embers, sparks, droplets, ash and the burnt-ground strip are drawn analytically, not simulated.
A finer 64x64x96 grid looked worse (thin blue sheets, no sooty orange): numerical mixing falls with cell size and the
tuning does not carry over, so the coarse grid is what was tuned. Variants A, B, C of a loop are three time windows of one
run (B is mirrored) with different detail noise, not three independent simulations; the explosion clips have two independent runs.

Shape handling: fields are multiplied by a soft 3D window (alpha reaches zero well inside the domain, the top tapers so smoke
thins out), sprites are cropped to the real extent of the fire with a margin, frames are non-square (tall narrow for trunks,
wide for pools, roofs and fronts). The domain is sized in metres so the sprite world size matches the real thing.

## Catalogue (generated from fire_atlas.json)
<!-- CATALOGUE -->
| Type | Kind | Real size | Domain (m) | Flame sprite (m) | Clips | Full KB (flame / smoke / heat) | Low KB (flame / smoke) |
|---|---|---|---|---|---|---|---|
| `campfire` | life | flames 0.5 to 0.9 m | 1.06 x 1.06 x 1.58 | 0.792x1.188 | decay, extinguish, growth, ignite, loop | 74 / 53 / 8 | 29 / 35 |
| `pool` | life | pool 2 to 3 m wide, flames 3 m | 5.12 x 5.12 x 7.68 | 4.693x5.867 | decay, extinguish, growth, ignite, loop | 91 / 62 / 8 | 34 / 39 |
| `vehicle` | life | car or truck, 4 to 5 m | 5.44 x 5.44 x 8.16 | 5.44x7.027 | decay, extinguish, growth, ignite, loop | 144 / 65 / 10 | 54 / 41 |
| `building` | life | 9 m wide, flames 8 to 12 m | 11.52 x 11.52 x 17.28 | 11.52x13.92 | decay, extinguish, growth, ignite, loop | 127 / 48 / 11 | 48 / 32 |
| `tree_crown` | life | tree 8 to 12 m, flames 6 to 12 m | 15.36 x 15.36 x 23.04 | 15.36x20.48 | decay, extinguish, growth, ignite, loop | 125 / 42 / 10 | 46 / 27 |
| `tree_trunk` | life | trunk 4 to 5 m, flames up the trunk | 3.36 x 3.36 x 6.72 | 3.36x5.6 | decay, extinguish, growth, ignite, loop | 88 / 34 / 7 | 34 / 22 |
| `grass` | life | patch 2 m wide, flames 0.4 to 1.2 m | 2.72 x 2.04 x 2.72 | 2.607x2.04 | decay, extinguish, growth, ignite, loop | 74 / 42 / 6 | 29 / 26 |
| `front_lead` | tile | 2 m wide tile, flames 0.8 to 1.5 m | 2.01 x 1.0 x 2.01 | 2.006x1.965 | loop | 93 / 30 / 5 | 36 / 18 |
| `front_body` | tile | 2 m wide tile, flames 0.5 to 1.0 m | 2.01 x 1.0 x 2.01 | 2.006x1.505 | loop | 60 / 25 / 5 | 23 / 17 |
| `front_trail` | tile | 2 m wide tile, low flames, smoke | 2.01 x 1.0 x 2.01 | 2.006x0.711 | loop | 30 / 23 / 3 | 11 / 14 |
| `gas` | life | flame 0.5 to 0.7 m | 0.8 x 0.8 x 1.2 | 0.5x0.95 | decay, extinguish, growth, ignite, loop | 75 / 44 / 8 | 29 / 28 |
| `barrel` | life | 0.6 m drum, flames 1 to 1.4 m | 1.21 x 1.21 x 1.82 | 1.012x1.746 | decay, extinguish, growth, ignite, loop | 127 / 64 / 8 | 49 / 43 |
| `torch` | life | flame 0.35 to 0.5 m | 0.58 x 0.58 x 0.87 | 0.363x0.641 | decay, extinguish, growth, ignite, loop | 58 / 40 / 6 | 22 / 26 |
| `flare` | life | flame 0.25 to 0.4 m | 0.53 x 0.53 x 0.79 | 0.308x0.561 | decay, extinguish, growth, ignite, loop | 51 / 34 / 6 | 20 / 23 |
| `debris` | life | pile 1 m, flames 0.4 to 0.9 m | 1.37 x 1.37 x 2.06 | 1.316x1.115 | decay, extinguish, growth, ignite, loop | 61 / 58 / 7 | 24 / 35 |
| `gas_jet` | life | jet flame 0.9 to 1.2 m | 0.6 x 0.6 x 1.44 | 0.44x0.98 | decay, extinguish, growth, ignite, loop | 48 / 20 / 6 | 18 / 13 |
| `shrub` | life | shrub 2 m, flames 1.5 to 2.5 m | 2.53 x 2.53 x 3.8 | 2.112x3.221 | decay, extinguish, growth, ignite, loop | 95 / 59 / 8 | 36 / 40 |
| `spot_fire` | life | small, flames 0.3 to 0.6 m | 0.79 x 0.66 x 1.06 | 0.616x0.792 | decay, extinguish, growth, ignite, loop | 39 / 28 / 4 | 16 / 17 |
| `oil_slick` | life | slick 4 m wide, flames 2 to 3.5 m | 7.2 x 4.32 x 7.2 | 6.48x4.44 | decay, extinguish, growth, ignite, loop | 88 / 52 / 7 | 33 / 31 |
| `boat_deck` | life | deck fire 5 m, flames 3 to 4 m | 8.0 x 4.0 x 8.0 | 7.733x5.733 | decay, extinguish, growth, ignite, loop | 123 / 61 / 8 | 48 / 38 |
| `smoke_column` | life | column 7 m tall, smoke only | 4.47 x 4.47 x 8.94 | smoke only | decay, extinguish, growth, ignite, loop | 0 / 53 / 6 | 0 / 34 |
| `vehicle_engine` | life | engine bay, flames 1 to 1.5 m | 2.72 x 2.72 x 4.08 | 2.493x3.797 | decay, extinguish, growth, ignite, loop | 121 / 63 / 8 | 47 / 42 |
| `vehicle_small` | life | small car, flames 1.5 to 2.5 m | 3.84 x 3.84 x 5.76 | 3.84x5.04 | decay, extinguish, growth, ignite, loop | 124 / 67 / 9 | 47 / 42 |
| `roof` | life | 12 m roof, flames 6 to 10 m | 20.0 x 12.0 x 20.0 | 18.667x14.667 | decay, extinguish, growth, ignite, loop | 116 / 46 / 10 | 43 / 28 |
| `window` | life | window 1.2 m, flames 2.5 to 4 m | 4.03 x 4.03 x 6.05 | 3.36x5.124 | decay, extinguish, growth, ignite, loop | 75 / 33 / 8 | 29 / 21 |
| `doorway` | life | door 1 m, flames 3 to 4 m | 4.03 x 4.03 x 6.05 | 3.36x5.208 | decay, extinguish, growth, ignite, loop | 91 / 40 / 9 | 35 / 27 |
| `blast_small` | blast | fireball about 3 m | 6.4 x 6.4 x 9.6 | 5.333x7.733 | fireball, plume, residue | 114 / 72 / 7 | 45 / 44 |
| `blast_medium` | blast | fireball about 8 m | 16.0 x 16.0 x 24.0 | 15.333x14.333 | fireball, plume, residue | 118 / 56 / 8 | 47 / 36 |
| `blast_large` | blast | fireball about 20 m | 40.0 x 40.0 x 60.0 | 38.333x34.167 | fireball, plume, residue | 113 / 48 / 7 | 43 / 29 |
| `blast_fuel` | blast | rolling fireball about 12 m, heavy black smoke | 19.2 x 19.2 x 28.8 | 19.2x21.6 | fireball, plume, residue | 175 / 55 / 10 | 67 / 33 |
| `blast_ground` | blast | burst 12 m wide, 4 m tall | 20.0 x 16.0 x 16.0 | 17.333x11.333 | fireball, plume, residue | 120 / 49 / 8 | 47 / 30 |
| `debris_slow` | carried | object speed about 4 m/s | 2.88 x 0.96 x 1.44 | 2.52x1.04 | loop | 54 / 16 / 3 | 23 / 10 |
| `debris_med` | carried | object speed about 12 m/s | 2.88 x 0.96 x 1.44 | 2.86x0.8 | loop | 51 / 11 / 3 | 20 / 7 |
| `debris_fast` | carried | object speed about 30 m/s | 2.88 x 0.96 x 1.44 | 2.8x0.76 | loop | 42 / 8 / 3 | 16 / 5 |
| `trail_tile` | tile | 2 m long streaming ribbon, repeat or stretch along the path | 2.01 x 0.75 x 1.0 | 2.006x1.003 | loop | 46 / 15 / 1 | 17 / 10 |
| `lick` | shot | 0.5 to 0.9 m, about 0.8 s | 0.99 x 0.79 x 1.39 | 0.594x0.396 | lick | 5 / 1 / 0 | 2 / 1 |
| `spatter_fan` | shot | 0.5 to 0.9 m, about 0.8 s | 1.58 x 0.99 x 1.39 | 1.056x0.429 | spatter_fan | 11 / 2 / 1 | 4 / 1 |
| `splash_fire` | life | splash 1 m, spreads over about 1.2 s, flames 0.8 to 1.2 m | 1.79 x 1.34 x 1.79 | 1.643x1.717 | decay, extinguish, growth, ignite, loop | 91 / 39 / 7 | 35 / 25 |

Total full-size atlases: 4.83 MB. Total phone (low) set: 2.39 MB (the heat atlas is shared).

Particles: dots 63 KB, streaks 6 KB, burnt strip 30 KB.
<!-- /CATALOGUE -->

Kinds: `life` full lifecycle; `tile` periodic in x (tileable) loops; `carried` a flame streaming from a moving object;
`blast` explosion; `shot` one-shot clips. Variants: three loops (a, b, c) per life, tile and carried type; the blasts and the
one-shots have a, b (blasts) or a, b, c (one-shots).

## Files and JSON (assets/fire/)
Per type: `fire_<t>_flame.webp` (RGBA, STRAIGHT alpha: sRGB colour, linear alpha; lossy WebP), `fire_<t>_smoke.webp` (straight alpha, coloured: grey plus
orange glow near the base, 6-bit alpha), `fire_<t>_heat.webp` (8-bit grey stored as lossy WebP), and `fire_<t>_flame_low.webp`, `fire_<t>_smoke_low.webp` (half-size frames
for phones; the heat atlas is shared). Particles: `fire_particles_dots.webp`, `fire_particles_streaks.webp` (lossless, straight alpha), `fire_burnt_strip.webp`.

`fire_atlas.json` (version 2): `presets.<type>` has
- `title`, `kind`, `size_note`, `domain_m`, `has_flame`, `tile`, `variants`
- `layers.flame|smoke|heat`: `file`, `frame_px`, `cols`, `rows`, `m_per_px`, `size_m`, `anchor` (fraction of the frame, bottom centre unless carried), `blend`,
  and `low` (the half-size atlas: same fields) with `low_m_per_px`. Frame i of an atlas is column i % cols, row floor(i / cols).
- `clips[]`: `name`, `stage` (loop, ignite, growth, decay, extinguish, fireball, plume, residue, shot), `variant`, `loop`, `fps`, `duration_s`,
  and per layer `{first, count, fps}` (indices into that layer's own atlas; smoke runs at half the flame fps, heat at a quarter).
- `emitter` (`radius_m`, `spread_m`), `light` (`color`, `color_by_heat`, `intensity_rel`, `intensity_vs_campfire`, `range_m`, `flicker` per loop frame,
  `stage_energy` per stage clip: relative flame energy per frame for driving the light during the lifecycle), `haze`, `seam`, `sim`.
`particles` (top level): clip tables for the dot and streak atlases and the burnt strip.

## Using the sprites
- Billboard: a camera-facing quad that stands on the ground (rotate about Y only), anchored at the layer anchor (bottom centre). Size from `size_m` times your scale.
  Flame and smoke have different `m_per_px` and sizes (smoke is lower resolution and covers the whole plume): size each quad from `size_m`.
- Larger fires: two or three crossed quads 60 to 90 degrees apart with different variants and start frames; fade each by how face-on it is.
- Flame: straight alpha, so normal blending is right (three.js `NormalBlending`, canvas `source-over`); for a brighter additive look use `CustomBlending` with src `SRC_ALPHA`, dst `ONE`. (Straight alpha was chosen over premultiplied because lossy WebP bleeds colour into transparent pixels, which premultiplied or additive blending would show as bright bars.)
  Smoke: normal blending, straight alpha. `depthWrite: false` on both, sort smoke back to front, draw it after the flame near the base. `toneMapped = false` on flame for night-vision bloom.
- Soft depth fade: `saturate((sceneDepth - fragDepth) / 0.5)` on alpha; without a depth texture lift the quad 5 to 10 cm.
- Frame choice: `f = clip.first + floor(t * layer.fps * speed) % count` for loops, clamp at the last frame for one-shots. Random start offset per fire. Blend with the next frame by the fractional part when playing the 8 fps stage clips.
- LOD and phones: far fires use `fire.glb` or one quad of frame 0 without smoke; on phones use the `low` atlases (half size, about 40 percent of the bytes).

## Lifecycle: how the game should drive it
State machine per burning thing: `out -> ignite -> grow -> burn -> decay -> out`, plus `extinguish` (from any burning state) and `reignite`.
- **ignite** clip (1.25 s, first flicker to small flames, 8 fps) when a thing catches (blast flame, burning chunk landing, flamethrower, spread).
- **growth** clip (2.5 s, small to developed). Start the growth clip at the frame matching the current fuel fraction if the fire is already part-grown.
- **burn**: loop variant a, b or c; pick a new variant (and a new random offset) every loop so repeats do not look the same. Playback speed 0.8 + 0.2 * fuelLoad, sprite scale sqrt(fuelLoad).
- **decay** clip (2.5 s): flames collapse to thin smoke. Start it when the fuel is used up (fuel-load counter reaches zero), then remove the fire. Leave a smouldering patch (burnt strip decal) for 20 to 40 s.
- **extinguish** clip (1.5 s): start it when water hits (fire-fighting spray, rain at high intensity, wading) and the fire's hit counter exceeds its fuel-load threshold; flames drop, steam rises. Keep the smoke for a couple of seconds, then remove.
- Light: intensity = base * `light.flicker[frame]` in the loop, `light.stage_energy[clip][frame]` in the stage clips. Colour from `light.color`, redder with `color_by_heat` as it dies.
- **Fuel load** parameter F (0.4 to 1.8, 1 = as baked): sprite scale sqrt(F), playback speed 0.8 + 0.2 F, burn time proportional to F, light intensity proportional to F, haze strength proportional to F (clamped).
- **Spread rules**: each burning flammable (grass cell, tree, building, fuel pool, vehicle) has fuel load, flammability and wind exposure. Every second, neighbours within `r` metres downwind (r grows with flame height and wind speed: about 1.5 * flame height + 0.4 * wind m/s) get ignition chance p = flammability * (1 + 0.15 * wind) * (1 - distance / r). Fuel pools and vehicles ignite neighbours within one flame height. Burning chunks that land ignite flammables immediately (see below). Rain and water zones reduce p.

## Spreading fronts (grass and brush)
Tile types `front_lead`, `front_body`, `front_trail` are 2 m wide, tileable left to right, loops a, b, c. `fire_burnt_strip.webp` is a 2 m by 1 m top-down ground decal, opaque, tileable both ways, with embers that breathe over 16 frames.
Layout: a front line of tiles across the burning width. Rows by distance behind the leading edge d: 0 to 1 m `front_lead`, 1 to 3 m `front_body`, 3 to 6 m `front_trail` fading out, behind that the burnt strip decal (fade the grass decal out as the front passes). Advance the line at the spread speed (0.1 to 2.5 m/s, faster with wind, slope and dry grass). Tile alpha fades in over the first half metre and the trailing tile fades out over its last 1.5 m.
Extras: `lick` clips (three, one-shot, 0.8 s) pop up in front of the leading tile at random x every 0.5 to 2 s; `spot_fire` (a full lifecycle type) is placed ahead of the front when an ember lands (every 2 to 5 s in strong wind, 2 to 8 m ahead), plays ignite then growth then loops, and merges into the front when the front reaches it. `ember_*` dots and `spark_*` streaks (particles) trail upwind to downwind across the front.

## Heavy black smoke and heat haze
Oil, fuel pool, boat deck, vehicle and tank fires use a high soot yield (soot_k 8 to 16), slow cooling (so the hot plume keeps rising and widening), random fuel flare-ups that throw off puffs of soot, and a dark smoke albedo (0.04). Their smoke atlases are separate, dense (smoke_k 1.6) and three variants, and the plume tapers to nothing at the top instead of ending at the frame. The lower part of the smoke is lit orange by the flames (a warm tint from the temperature field plus an under-light that fades with height), fading to near-black grey above. A mushroom-like head forms on the big fuel fires from the rising soot-laden thermal and the explosions' plumes, but it is a result of the flow, not designed in, and does not appear every time.
The `smoke_column` type is smoke-only (no flame atlas): a tall black column to place downwind of a fire or on the horizon.

Heat haze for the game's DIST sources: every type has `haze` = `{strength 0..1, radius_m, height_m, rise_speed_mps, shape}`. Attach one `DIST.haze(id, x, y, z, strength * stageEnergy, radius_m, height_m)` per fire (the existing calls pass strength, a radius and a height in the same way), drifting upward at `rise_speed_mps`. Intended values: oil, fuel, vehicle, boat, roof and tree-crown fires: strong (0.9 to 1.0) and tall (haze height about 2.4 times the flame height, radius 1.3 to 1.5 times the vent spread); grass and brush fires, spot fires and front tiles: weak to medium (0.25 to 0.4), wide and low (haze height about 0.9 of the flame height, radius half the front or patch width). Explosions: 1.0, tall, and also call `DIST.shock` at the ignition.
<!-- HAZE -->
| Type | Haze strength | Radius (m) | Height (m) | Rise (m/s) | Shape |
|---|---|---|---|---|---|
| `campfire` | 0.45 | 0.28 | 1.9 | 0.3 | default |
| `pool` | 1.0 | 2.11 | 6.91 | 0.3 | tall |
| `vehicle` | 0.9 | 2.45 | 7.34 | 0.3 | tall |
| `building` | 1.0 | 5.18 | 15.55 | 0.3 | tall |
| `tree_crown` | 0.9 | 6.91 | 20.74 | 0.3 | tall |
| `tree_trunk` | 0.6 | 1.51 | 6.05 | 0.3 | tall |
| `grass` | 0.4 | 1.56 | 1.84 | 0.3 | wide |
| `front_lead` | 0.4 | 1.0 | 1.77 | 0.3 | wide |
| `front_body` | 0.4 | 1.0 | 1.35 | 0.3 | wide |
| `front_trail` | 0.25 | 1.0 | 0.64 | 0.3 | wide |
| `gas` | 0.4 | 0.15 | 1.52 | 0.3 | default |
| `barrel` | 0.6 | 0.3 | 2.79 | 0.3 | default |
| `torch` | 0.25 | 0.11 | 1.03 | 0.3 | default |
| `flare` | 0.2 | 0.09 | 0.9 | 0.3 | default |
| `debris` | 0.4 | 0.7 | 1.78 | 0.3 | default |
| `gas_jet` | 0.6 | 0.13 | 1.57 | 0.3 | default |
| `shrub` | 0.55 | 0.88 | 5.15 | 0.3 | default |
| `spot_fire` | 0.25 | 0.37 | 0.71 | 0.3 | wide |
| `oil_slick` | 1.0 | 2.99 | 6.48 | 0.3 | tall |
| `boat_deck` | 0.9 | 3.64 | 7.2 | 0.3 | tall |
| `smoke_column` | 0.7 | 1.17 | 7.66 | 0.3 | tall |
| `vehicle_engine` | 0.6 | 1.12 | 3.67 | 0.3 | tall |
| `vehicle_small` | 0.75 | 1.73 | 5.18 | 0.3 | tall |
| `roof` | 1.0 | 8.4 | 18.0 | 0.3 | tall |
| `window` | 0.6 | 1.01 | 8.2 | 0.3 | default |
| `doorway` | 0.6 | 1.01 | 8.33 | 0.3 | default |
| `blast_small` | 1.0 | 2.4 | 8.64 | 0.43 | tall |
| `blast_medium` | 1.0 | 6.9 | 21.6 | 0.34 | tall |
| `blast_large` | 1.0 | 17.25 | 54.0 | 0.43 | tall |
| `blast_fuel` | 1.0 | 8.64 | 25.92 | 0.54 | tall |
| `blast_ground` | 1.0 | 7.8 | 14.4 | 0.3 | tall |
| `debris_slow` | 0.3 | 1.57 | 1.66 | 0.3 | default |
| `debris_med` | 0.3 | 1.57 | 1.28 | 0.3 | default |
| `debris_fast` | 0.3 | 1.57 | 1.22 | 0.3 | default |
| `trail_tile` | 0.2 | 1.0 | 0.9 | 0.3 | wide |
| `lick` | 0.15 | 0.36 | 0.36 | 0.3 | wide |
| `spatter_fan` | 0.15 | 0.63 | 0.39 | 0.3 | wide |
| `splash_fire` | 0.5 | 0.99 | 1.55 | 0.3 | wide |
<!-- /HAZE -->

## Explosions, flaming debris, spatter
- **Fireballs**: `blast_small` (about 3 m), `blast_medium` (8 m), `blast_large` (20 m), `blast_fuel` (rolling fuel fireball, 12 m, heavy black smoke) and `blast_ground` (ground-hugging burst, 12 m wide and 4 m tall). Each has clips `fireball_a|b` (24 fps, 2 s: white flash and hot core, rapid expansion, then the rising bubble with a curling smoke head), `plume_a|b` (8 fps, 3 s: the rising plume and the head), `residue_a|b` (a seamless loop of low burning residue).
  Play fireball, then plume, then the residue loop. Pick a or b at random.
- **Flaming debris**: `debris_slow`, `debris_med`, `debris_fast` (designed for 4, 12 and 30 m/s) are loops a, b, c of a burning chunk's flame seen from the chunk, so the flame bends back and stretches with the wind of its own motion. Their frame axis is the flame axis: head at the layer `anchor` (left side), the tail towards +x. Orient the quad so +x points opposite to the velocity (angle = atan2(-vy, -vx) in the screen plane; for a world billboard, yaw the quad about its own head so the tail follows the velocity projected onto the camera plane). Stretch along the tail axis by `clamp(speed / designSpeed, 0.6, 1.7)`, pick the clip by speed (below 8 m/s slow, below 20 medium, else fast), crossfade classes if you can, and fade alpha and flame size as the chunk cools (about 4 to 8 s). `trail_tile` is a 2 m streaming ribbon (tileable along x) to repeat or stretch along a debris path behind the head. `ember_streak_slow|med|fast` (particles) are glowing streaks with the head at the left. `spark_*`, `ember_*`, `droplet_*` (burning droplets, tail down, rotate to the velocity) and `ash_*` flakes are 32x32 particles.
- **Spatter and thrown fuel**: `droplet_a|b|c` for airborne burning droplets; `splash_fire` (a lifecycle type: the ignite and growth clips show the splash spreading from the impact over about 1.2 s and it becomes a ground fire, so use it as the landing effect of thrown fuel, then as a pool fire); `spatter_fan` (short-lived fan of flame, 0.8 s, one-shot).
- **Connecting to the game**: `blast()` plays the fireball for its radius (choose small, medium, large by R, `blast_fuel` when the source is a fuel or vehicle explosion, `blast_ground` when it is a surface burst) and calls `DIST.haze` and `DIST.shock` with the same radius. The debris pool (`DEB`, `debrisBurst`) attaches a `debris_*` flame to a fraction of the thrown chunks (about 15 percent for ordinary blasts, 50 to 80 percent for fuel and vehicle explosions); each frame set the sprite from the chunk's velocity; fade it as the chunk cools. When a burning chunk lands: spawn `splash_fire` (if fuel) or `spot_fire` ignite clip at the impact, call `igniteTreesNear`, ignite flammable objects within about 2 m (`q.T += 120` style) and register a `HEATP` patch; chunks that land in water just fizz. Fireballs also set nearby flammables burning (`burnArea`).

## Thermal and night vision
Thermal: draw `_heat` instead of flame and smoke; value v is `(pixel / 255)^(1/0.8)`, 1 = about 2000 K, 0 = ambient; map through the white-hot ramp used in the viewer; smoke is invisible in thermal (the heat atlas already includes the hot gas above the flame). The heat atlas is small, so smooth it (linear filtering).
Night vision: draw flame with `toneMapped = false` and the smoke into the NV pass, convert to luminance and add gain; the flame blooms to white.

## Cost (estimate, not measured in game)
Per fire: one flame quad plus one smoke quad (double for crossed quads). The cost is fill rate: a quad covering 10 percent of a 1080p screen with two layers is about 0.2 screen of fill, cheap on desktop and noticeable on a phone, so cap near fires (a few big ones), fade smoke by distance, use the low atlases, and keep flame quads small. Texture memory: the decoded atlases are far larger than the files (WebP decodes to RGBA): load a type when the first fire of that type appears and drop it when none is left; the full set decodes to a few hundred MB, so never load all at once on a phone. CPU: one frame index per layer per fire, and a handful of state-machine updates.

## Unverified and limits
Not loaded in the game; not measured for performance. The viewer is untested on real devices. The frames were checked by eye in contact sheets and numerically for loop seams (frame difference across the loop point against the average adjacent difference, stored in `seam`). Known weaknesses: three variants share one run (a and c are not independent simulations); the 8 fps stage clips are choppy without frame blending; explosions' expansion is scripted not simulated and the fireballs sit in an incompressible flow; the black smoke head is not guaranteed; smoke and heat from the coarse grid is smooth but can look soft up close; the carried flames are seen from the object and are orthographic (a billboard approximation); the particle sprites are analytic and plain.
