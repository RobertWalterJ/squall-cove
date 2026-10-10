# Fire sprites, Blender Mantaflow track (assets/fire_blender)

Second fire track, for comparison with the numpy combustion bake in `tools/fire/`. Built by `tools/fire_blender/` (see its README for how to re-run). This note covers what is in the atlases, how the game should use them, what is simulated and what is baked or faked, and what is unverified.

## What is in `assets/fire_blender/`

All images are **WebP with straight (non-premultiplied) alpha**, one atlas per layer, laid out 8 columns wide, row-major, frame 0 at top-left. `fireb_atlas.json` is the single source of truth: per preset the frame size in pixels, grid, frame count, world size in metres, anchor, light colour and intensity, a per-frame flicker array, file names and byte sizes, variants, lifecycle clips and a heat-haze descriptor.

| Layer | File | Use |
|---|---|---|
| flame | `fireb_<preset>_flame.webp` | emission. Colour is hue-normalised and alpha equals brightness, so additive blending (`AdditiveBlending`, SRC_ALPHA + ONE) reproduces the render. |
| smoke | `fireb_<preset>_smoke.webp` | lit, near-neutral grey with a warm underlight at the base on fuel fires. Normal blending. |
| heat | `fireb_<preset>_heat.webp` | opaque grey image (no alpha). Draw additively into a thermal buffer or map through a white-hot palette. |
| `*_low.webp` | half-size copies of each of the above for phones. Same frame count and layout; the JSON lists the half frame size. |

Presets: campfire, gas (burner), pool (sooty fuel pool), vehicle, building, grass (front), tree, fireball (one-shot), trail_slow / trail_med / trail_fast (carried flame). Extras: `spread_grass` (tileable front segment, lead and trail ends, spot fire, smouldering burnt strip), `embers`, `spatter`, `ember_streak`.

Frames are not square. Each fire has the aspect and metre size of the thing it depicts (tall narrow for campfire, tree, pool plume; wide and low for the grass front; wide for vehicle and trails; roughly square for the building). The flame, smoke and heat layers are faded to zero alpha inside the frame on every side (a soft framing window, plus a soft plume silhouette on the smoke), so a sprite quad never shows a straight edge. Place the quad using `worldWidth` by `worldHeight` from the JSON with the anchor at bottom centre.

## Using them in the game

**Billboards.** One camera-facing quad per fire, anchored at the base. For large fires (vehicle, building, tree) use two or three quads crossed at 60 to 90 degrees with different variants (below) and `depthWrite=false`. Add a soft depth fade in the fragment shader (fade alpha by `saturate((sceneDepth - fragDepth) / 0.5)`) so quads do not cut hard into the ground. Flame quads: additive. Smoke quads: normal blending, drawn after opaque and before flame, sorted far to near. Smoke can be tinted with the ambient light colour; its baked underglow is only a hint.

**Flipbook.** `frame = floor(t * fps) % frames`, then `col = frame % cols`, `row = floor(frame / cols)`. Sample with linear filtering and, for best results, blend with the next frame (`fract(t * fps)`); this hides the 24 fps stepping at low speed. Flip U for mirrored variants.

**Variants.** The JSON lists four variants (A to D) per loop preset: start offset into the loop and an optional horizontal mirror. They come from one simulation per type, so they are different phases and mirror images rather than independent simulations. Give each quad its own variant and speed jitter (0.9 to 1.1) and neighbouring fires will not look identical.

**Flicker and light.** `flicker[frame]` is the relative flame brightness (mean 1). Drive a point light with `light.color` and `light.intensity * flicker[frame]`. Intensity is a starting point, tune it against the game's light units.

**Thermal and night vision.** Draw the heat layer additively into the thermal pass (or full screen palette): the grey ramps from black to white at the hottest core. For night vision, draw flame and smoke as usual and push the result through the green mapping; flame will bloom, which is what it does on real goggles.

**Heat haze.** Every preset has `haze: {strength 0..1, radiusM, heightM, riseSpeed}`. Attach a haze volume at the base with that radius and height; scroll the distortion noise upward at `riseSpeed` m/s. Oil, fuel, vehicle, building and tree fires get strong, tall haze; the grass front gets wide and low haze (about 3 m radius, 1.2 m high). The fireball haze is a large, short-lived volume to pair with the shock ring.

**Lifecycle (`clips`).** Ignite, growth, developed, decay and extinguish are curves, not extra atlases. Each clip gives a duration, whether it loops, and `[start, end]` ramps for scaleX, scaleY, flameGain, smokeGain and erosion. Drive them from fire state: scale the quad by fuel load (a 0.5 to 1.5 multiplier works), multiply flame alpha by flameGain, smoke alpha by smokeGain, and apply erosion in the shader as `flameAlpha = max(0, flameAlpha - erosion)` (then renormalise brightness), which gives a convincing shrink to embers. On decay, fade in the `embers` atlas at the base and let smoke thin. On water: erode fast, boost the smoke layer toward white for a second or two (steam), then thin it. Ignition by spread: start a new fire at `ignite`, run `growth` over about 6 s, then `developed` until fuel is gone, then `decay`. Spread by wind and fuel is game logic: advance the front along fuel cells and place `spread_grass` tiles along it.

**Spread front.** `spread_grass` gives a tile (2 m wide, seamless left to right; the seam is a baked blend, so the middle of each tile is a soft mix of two frames) with lead and trail end pieces, a spot-fire clip for spotting ahead of the front, and a tileable smouldering strip for burnt ground behind it.

**Explosions and thrown fire.** `fireball` is a one-shot 3 s clip (8 m class, flash, expansion, rising bubble with smoke head, residue); scale it for other sizes (3 m: scale 0.4 and time 0.6; 20 m: scale 2.5 and time 1.6). Fire thrown with debris uses the `trail_*` loops (a stationary burning chunk in a steady air stream, flame bent back along +X), the `ember_streak` and `spatter`. Attach a trail to a fraction of thrown chunks in `debrisBurst`/`blast()`: pick the speed class from the chunk speed, rotate the quad so +X points opposite the velocity vector (the tail then points backwards), stretch its length by about speed / reference speed (5, 11, 20 m/s) and fade alpha as the chunk cools. When a burning chunk lands on flammable ground, start the `ignite` clip there. Hook the fireball to a heat haze volume and the shockwave ring.

## Cost per fire

Atlases are tiny; the cost is fill rate. One crossed pair of quads of a building-sized fire at full screen is at most four large transparent layers with a texture fetch each (two flame, two smoke). On a desktop GPU that is negligible; budget about 2 to 4 fires at full-screen size and any number at small size. On phones use the `_low` atlases (about 0.4 times the bytes, 0.25 times the texels), one quad per fire, and skip the heat layer unless thermal vision is on. Texture memory when decoded (RGBA8): a 128 by 192 frame atlas at 8 by 6 frames is about 4.7 MB, the wide grass atlas about 12 MB, half those on low. Total download is under 6 MB with the low versions included (see the size table at the end).

## What is simulated, what is baked, what is faked

Simulated by Blender's Mantaflow (gas domain, fuel, heat, flame, smoke, vorticity, buoyancy): the flame and smoke motion and density for campfire, gas burner, pool, vehicle, building, grass front, tree, fireball and carried-flame presets.

Baked or art-directed after the simulation: the flame colour is a hand-tuned blackbody-like ramp driven by the flame field (blue premixed hue preserved for the gas burner); the smoke lighting is a fixed neutral studio setup with a warm point light for the underglow, not a true radiative solution; the thermal layer is a grey emission render (or derived from the flame layer where noted); Monte Carlo noise is blurred out in smoke and heat; loops are made by crossfading the tail of the simulation into the head, so a faint ghost is possible at the seam (the pack step prints a seam metric against the typical frame-to-frame change, and the preview sheet has a last-frame and first-frame pair); the soft framing windows and plume silhouettes are applied in the pack step.

Faked or derived (not Mantaflow): lifecycle clips (parametric curves over the loop), variants (offset and mirror of the same simulation), the lead, trail and spot pieces of the spread tiles (cut and faded from the grass simulation), the smouldering strip, `embers`, `spatter` and `ember_streak` (small numpy particle systems), and the fireball size classes other than 8 m. This is not Fire-X: there is no multi-species stoichiometric chemistry. Mantaflow has one fuel and one flame field. The blue-to-orange transition in the gas preset is a colour mix by height, standing in for the premixed to diffusion transition.

## Honest limits

- The smoke lighting is single-scatter with no flame illumination of the smoke volume other than a warm point light, and it is rendered neutral so the game can tint it.
- Frame count is 44 (about 1.8 s) per loop for the newer presets and 56 for the earliest, with a 12 to 14 frame crossfade. Long staring will show repetition; use variants and phase jitter.
- Mantaflow is not strictly deterministic across rebakes with changed resolution, so a rebake will look similar but not identical.
- Cell sizes are 4 to 15 cm depending on the preset; small-scale flame detail below that is absent, and the vehicle, building and tree flames are softer than the campfire.
- Wind for the carried-flame presets is a Blender force field with fluid flow; its strengths (5, 11, 20) are labels for speed classes, not calibrated m/s.
- The tileable front is a baked blend, not a periodic simulation.
- The viewer's thermal and night-vision looks use SVG filters; the game should use its own post-process.
- Not tested on a phone or in the game: texture upload sizes, blending on the game's renderer, and frame-time cost are estimates from the atlas dimensions.
- Machine note: bakes and renders on this PC slowed or paused whenever other heavy jobs were running or the machine slept; the times below include no waiting.

## Bake and render times (this PC, 16 threads, CPU only)

Wall-clock seconds from the run logs. Times include stalls: the PC went to sleep and froze under other heavy jobs during several bakes (the vehicle bake logged 4611 s, of which well under 30 minutes was computing; the first tree bake logged over three hours for the same reason), so treat the larger numbers as upper bounds. Settings that were final: Cycles CPU, 20 samples flame (10 smoke), smoke every second frame, heat derived in the packer.

| Preset | Cells (tall axis) | Sim frames | Bake | Render | Frame px | World size |
|---|---|---|---|---|---|---|
| campfire | 112 | 106 | 8 min | 13 min | 128 x 192 | 2 x 3 m |
| gas | 112 | 92 | 5 min | 8 min | 128 x 192 | 2 x 3 m |
| pool | 88 | 176 | 6 min | 9 min | 128 x 192 | 6 x 9 m |
| vehicle | 96 | 136 | about 25 min | 2 + 20 min | 160 x 192 | 7.5 x 9 m |
| building | 80 | 166 | 9.5 min | 11 min | 160 x 160 | 16 x 16 m |
| grass front | 128 | 106 | 4 min | 8 min | 256 x 160 | 4 x 2.5 m |
| tree | 72 | 166 | about 12 min | 2 + 5 min | 128 x 192 | 8 x 12 m |
| fireball (8 m) | 72 | 72 | 1.7 min | 5 min | 128 x 192 | 16 x 24 m |
| trail_slow / med / fast | 96 | 86 | 4.2 / 4.9 / 1.8 min | 2.1 / 3.1 / 1.1 min | 192 x 128 | 3 x 2 / 3.9 x 2.6 / 5.1 x 3.4 m |

## Download size

All WebP, quality 88 where the byte budget allowed (the fireball smoke and campfire smoke were reduced to fit). Total in `assets/fire_blender/`: about 3.9 MB including all half-size `_low` versions, spread tiles, embers, spatter and ember streak. Per preset flame atlases are 25 to 211 KB, smoke 38 to 148 KB, heat 17 to 62 KB (full size); the low versions are about 0.35 to 0.45 of those.

## Known visual weaknesses (from the preview sheet)

- Smoke on the fuel fires (pool, vehicle, building, tree) is a dense dark column with little internal structure and an obvious plume cone, because the simulated density was nearly uniform; the soft plume window hides the box edges but it still reads as a cone. A longer warm-up and a lower density would give a more rolling column. There is no separate mushroom-head or soot-puff atlas: the flare-ups and ring appear only to the extent the fuel pulse in the fireball produced them.
- The tree crown reads as a single bright mass on a trunk rather than separate tongues; the building window flames are small isolated blobs plus a roof strip.
- The gas burner flame is small in its frame and the blue zone is a short stub at the burner, not a gradual blue-to-orange transition.
- The grass front shows diagonal streaks (a grid and vorticity artefact) and its smoke is faint.
- The fireball's flame lasts about one second and its late smoke is grainy.
- Trail flames show a regular wave pattern in the tail.
