# Baked steam, mist and fog sprites (assets/atmos/*)

Flipbook sprites for Squall Cove: 6 steam types, 6 spray / mist types, 7 fog and low-mist strips and a set of fog blobs,
baked from a small moist-air solver. Rerun and parameters: `tools/atmos/README.md`. Preview: `docs/atmos_preview_sheet.png`;
live viewer: `docs/atmos_viewer.html` (double-click `tools/atmos/Open atmos viewer.bat`). The fire sprites in `assets/fire` are a separate track.

## What is physical, and what is not

Modelled (tools/atmos/fluid.py, flow numerics copied from the fire solver):

* Stable-fluids flow: MacCormack advection, FFT pressure projection, vorticity confinement, drag, sponge boundaries.
* Moist thermodynamics: temperature excess, vapour excess and liquid water per kg of air. Vapour above the Clausius-Clapeyron
  saturation value condenses (with latent heating, so condensing steam gets MORE buoyant); subsaturated air evaporates droplets
  (cooling the air). Buoyancy is `th/T0 + 0.608 qe - ql`. This is what makes steam leave a clear gap above a hot source, thicken as it
  mixes and cools, then thin out and vanish in dry air.
* Entrainment: a turbulent mixing term proportional to local speed (a coarse stand-in for resolved turbulence).
* Fog: ground cooling / moistening schedules (fog forms), warming (burn-off), droplet fall speed (fog sinks and flattens),
  stable inversion lid (valley fog gets a flat top), downslope drainage, wind profile advection, patchy forcing, noise churn.
* Spray (Lagrangian droplet parcels): log-normal size distribution, Stokes drag with a Reynolds correction, gravity, evaporation
  (d(r^2)/dt law), eddy random walk, two-way drag on the air. Parcels carry real mass, so extinction is in 1/m (1.5 m / (rho_w r) per volume).
* Extinction to alpha: `alpha = 1 - exp(-tau)`, tau along the view ray. Sizes are real (domain = grid x dx metres, in the JSON).

Approximated or missing:

* The grids are coarse (32x32x48, 128x20x32 for strips) so billows are about 1/10 of the sprite size; fine detail is a procedural,
  noise-eroded density field added at render time (cosmetic, not simulated). The optical-density scale (`gain`, `vref`) is an art control.
* Single-scatter style shading (light from above and the left through the column above each voxel plus a silhouette bump term),
  not true radiative transfer. The `scatter` layer is a heuristic: strongest where optical depth is about 1.
* No droplet microphysics (CCN, growth), no collisions or breakup, no salt, no compressibility, no real boundary layer.
* Large plumes (steam burst, lava) fill the width of their domain: they look like a tall column with a soft cloud edge, not a
  true widening plume. The edges are masked by a soft 3D window so alpha reaches zero inside the frame, which also rounds the shape.
* Spray reads as a dense white mound with a speckled top rather than distinct sheets and streaks; sheets are only loosely formed.
* Fog strips are Galilean-stabilised (the mean drift is removed so loops are seamless): the game must scroll them. Lifecycle clips of
  different sims cross-fade; they are time-lapses (see `sim_s_per_frame`).
* Seams: loops are cross-faded (not mathematically periodic); strips are exactly periodic in x. `seam` in the JSON compares the loop
  point difference with the average frame-to-frame difference.
* Banding: soft alpha gradients quantise in 8-bit lossy WebP; a little dither is baked, visible on pure dark backgrounds.
* Frame counts: 2 distinct loop windows per type; draw any loop mirrored (`scale.x = -1`) for 4 looks.

## Using the sprites in the game

Layers (one frame index shared by all of them):

* `main` (`<name>.webp`, `_low.webp`): RGBA, grey sRGB-encoded colour + straight alpha. Use an sRGB texture. Normal blending
  `(SRC_ALPHA, ONE_MINUS_SRC_ALPHA)`, or premultiply on load and use `(ONE, ONE_MINUS_SRC_ALPHA)`. Do not use additive for the main layer.
* `scatter` (`_scatter.webp`): grey, half size (low: quarter size), 0 to 1. Draw additively on top, multiplied by sun colour,
  `dot(viewDir, sunDir)` backlight factor and the `lighting.<time>.scatter` gain, and masked by the main alpha. It brightens the thin edges
  when the sun is behind the sprite and does nothing otherwise.
* `heat` (steam only, `_heat.webp`, quarter size): temperature above ambient, `(v/255)^(1/0.8)` of `th_ref_k`. Used for thermal view.

Lighting: multiply main by `lighting.<day|dusk|night|backlit>.tint * brightness`. At night steam, mist and fog are only lit by lamps and fires:
do not draw them at the day brightness; add the colour of the nearest light instead.

Placement:

* Billboard facing the camera, origin at `anchor` (u, v from the top-left of the frame; steam: the vent; bow spray: the bow crest; strips: the ground).
  `size_m` is the world size of the whole frame at 1:1. Rotate the quad about the vertical axis only (cylindrical billboard); never tilt it.
* Soft-depth fade: fade alpha with scene depth difference over about 0.3 x the sprite depth (steam), 1 m (mist) or 3 m (fog)
  so the quad does not cut hard lines where it meets ground, water or walls.
* Draw order: opaque, then fog strips far to near, then spray / steam, then blob billboards. Transparent sorting by distance. Disable depth write.
* Strips: keep 3 or 4 layers at different heights (`game.layer_heights_m`) and scroll factors (`game.wind.scroll_factor`); scroll at
  `fog.u_ref_mps` + wind x factor. Bottom edge sits on the ground and has already faded to alpha 0; sink the quad about 5 to 10 percent.
* Wind: lean the quad about its anchor (`wind.lean_deg_per_mps`, `max_lean_deg`) and translate the top by `drift_top` x wind speed, the base by `drift_base` x wind speed.

Connecting to game systems:

* Fires: when a fire is extinguished by water, play `steam_burst` (`start`, loop while spraying, `fade`). Hot wrecks cooling: `steam_engine`.
  Fire intensity can drive the `supply` of the `steam_*` loop by choosing the clip (start, loop, fade) and scaling alpha with the stage.
* Lava vents: `steam_lava` where a lava flow reaches water; `steam_geyser` for hot springs.
  Steam sources should also register a heat-haze source: `haze` in the JSON (strength, radius, height, rise speed, shape).
* Impacts: pick `splash_small | medium | large` by projectile mass; play one clip (random of `splash_a/b/c`), `loop: false`.
* Waves and boat bows: `mist_bow` clips: `start` when the bow throws a wave, loop while speed is high, `settle` when slowing; orientation: frame x = aft.
  `mist_surf` along a shore or under a waterfall; `spray_cone` for hoses (rotate to the nozzle direction; frame x = jet direction).
* Weather: `fog_*` strips via the state machine in the JSON (form, drift, linger, thin, fall). `mist_dawn` over still water in the morning.

Sensors (`sensors` in the JSON): thermal view: steam is bright (draw the heat layer through the white-hot palette), mist is a faint cool smudge,
fog is faint and cool (alpha x 0.1 in the cold end). Night vision: fog and mist scatter the illuminator: add the scatter layer and a veil
(alpha x 0.35) and reduce the contrast of what is behind it; fog washes out the view.

Cost: one quad per sprite, 1 texture fetch for main (+1 for scatter when backlit). Fill rate is the cost: a 16 m fog strip covers a lot of the screen
at 512x128. Budget about 8 to 12 full-screen-equivalent transparent layers. Frame texture sizes are small (see JSON `frame_px`); atlases are at most
2048 px wide. Use the `_low` atlases (half size) on phones and drop the scatter layer (or use its `_low`) and the heat layer (not needed outside thermal view).

## Honest limits

See "Approximated or missing" above. In short: the shapes are plausible clouds, not measured data; the big steam plumes and the sprays are the weakest;
there is no per-frame temporal coherence beyond what the solver gives, so slowed-down playback shows pops; the loop seams are cross-fades; the JSON sensor
values are suggestions, not calibrated; the viewer's landscape demo is a procedural drawing, not the game scene; none of this was tested inside the game.
