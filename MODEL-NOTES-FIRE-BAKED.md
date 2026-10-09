# Baked fire sprites (assets/fire/*)

Hyper-real but cheap fire for Squall Cove: five presets baked from a small 3D combustion
simulation into flipbook atlases. The low-poly `assets/fire.glb` stays as the cheap far LOD.
Rerun and parameters: `tools/fire/README.md`. Preview: `docs/fire_preview_sheet.png`; live viewer: `docs/fire_viewer.html`.

## What is physical, and what is not
Inspired by Fire-X (Wrede et al., SIGGRAPH Asia 2025), which is an offline multi-species solver. This is our
own reduced model, not a reproduction, and it was tuned by eye.

Modelled: stable-fluids flow (MacCormack advection, FFT pressure projection, buoyancy from temperature,
vorticity confinement, drag); fields for fuel, oxidiser (air = 1, nitrogen implicit), temperature, soot,
burned products and fuel age; the reaction F + s O -> products, mixing-limited, with heat release proportional
to burnt fuel and a configurable stoichiometric ratio; ignition above a threshold temperature; radiative cooling
(more with soot); soot formed only when fuel-rich, hot and old enough, burnt off in hot air; blue premixed colour
from the lean part of the reaction, orange from soot incandescence (blackbody-like ramp); a water-spray sink in the
solver (not baked).

Approximated or missing: no real chemistry or kinetics, no thermal expansion, no radiative transfer, nitrogen,
CO2 and water vapour are lumped into one products field (only used for steam), no sub-grid turbulence in the solver.
The sim grid is coarse (32x32x48 cells, 3 to 28 cm per cell by preset). Fine detail comes from a scrolling
procedural noise volume and a small 2D warp added at render time: cosmetic, not simulated. Smoke is single-scatter
style shading (light from above through the column), not true scattering. Light intensity numbers are relative
image brightness, not measured watts.

A finer grid (64x64x96) was tried first and looked worse (thin blue sheets, no sooty orange) because numerical mixing
fell with cell size and the tuning no longer held; the coarse grid is what was tuned.

## Files (all in assets/fire/, total about 2.3 MB)
Per preset: `fire_<p>_flame.png` (RGBA, 8x8 grid, 64 frames, palette-quantised), `fire_<p>_smoke.png` (grey+alpha),
`fire_<p>_heat.png` (8-bit grey). Sizes in KB (flame / smoke / heat): campfire 162/199/43, gas 159/137/40,
pool 153/161/30, vehicle 329/178/54, building 403/165/56. The building flame and several smoke atlases are over
the 350 / 150 KB targets.

`fire_atlas.json` per preset: `frames` (64), `fps`, `loop`, `grid` [cols, rows], and for each of `flame`, `smoke`,
`heat`: `file`, `frame_px`, `m_per_px`, `size_m` (sprite size in metres), `anchor` [0.5, 1.0] (bottom centre), blend note.
Also `emitter` (`radius_m`, `spread_m` of the fuel source), `light` (`color`, `mean_kelvin_visible`,
`color_by_heat` ramp, `intensity_rel`, `intensity_vs_campfire`, `range_m`, `flicker` 64 values, mean 1) and `seam`
(loop check), `sim` (seed, cell size).

Frames: row-major from the top left; frame i is column i % 8, row floor(i / 8). Smoke and flame share the same
bottom-centre anchor but have different `m_per_px` and sizes (smoke is lower resolution and covers the whole plume),
so size each quad from `size_m`, not from pixels.

## Using it in the game
- Quad: a camera-facing billboard (rotate about Y only, so it stands on the ground) anchored at the bottom centre.
  Sprite size is `size_m` times your own scale (a bigger fire = scale the quad; scale width and height together).
- Larger fires (building, long wrecks): two or three crossed quads about 60 to 90 degrees apart, each with a different
  random start frame, to hide the flat look; fade each quad by how face-on it is to the camera.
- Flame: premultiplied alpha, `blending = CustomBlending, src ONE, dst ONE_MINUS_SRC_ALPHA`, `premultipliedAlpha: true`,
  or plain additive (ONE, ONE) ignoring alpha. Textures are sRGB-encoded. `depthWrite: false`. Smoke: `NormalBlending`,
  straight alpha (grey in R=G=B from the L channel, A from the alpha channel), `depthWrite: false`, drawn after the flame
  and sorted back to front. Set flame `toneMapped = false` so it blooms in night vision.
- Soft depth fade: enable the depth texture and fade alpha by `saturate((sceneDepth - fragDepth) / 0.5)` so the quad
  does not cut hard through ground and walls. If no depth texture, lift the quad 5 to 10 cm.
- Frame choice: `f = floor(t * fps * speed) % 64`, with a random per-fire start offset. For smooth playback blend with the
  next frame by the fractional part (two samples, same atlas). To make a fire flare or die, scale the quad and multiply
  alpha by intensity; do not change the playback speed much (0.7 to 1.3) or the buoyancy will look wrong.
- Intensity and size: `size = base_size_m * sqrt(intensity)`; for fires larger than the baked size prefer more crossed quads
  over a bigger one.
- Light: a point light at about 30 percent of the flame height, colour `light.color` (lerp along `color_by_heat` as the fire dies:
  cooler = redder), intensity = your base * `flicker[f]`, range `light.range_m`. `intensity_vs_campfire` is a relative guide only.
- Thermal sensor: draw `_heat` instead of flame and smoke. Value v is `(pixel/255)^(1/0.8)`, 1 = about 2000 K, 0 = ambient.
  Map through the white-hot ramp used by the viewer. Smoke is invisible in thermal (the heat atlas already includes hot gas above the flame).
  Linear filtering is right; the atlas is coarse (32x48 per frame) so smooth it.
- Night vision: render flame (with `toneMapped = false`) and smoke into the NV pass, convert to luminance, apply gain; the flame
  will bloom to white, which is correct for NV.
- Existing DIST haze: keep calling `DIST.haze(id, x, y, z, strength, radius, height)` for each baked fire (as the wreck and `HEATP` code does),
  with strength from fire intensity and radius about `emitter.spread_m * 2`, height about `flame.size_m[1]`. The heat atlas is not needed for that.
- LOD: far away use `fire.glb` clusters or a single quad of frame 0 with no smoke; swap to sprites inside about 60 to 80 m.

## Cost estimate (not measured in game)
Per fire: one flame quad plus one smoke quad (double for crossed quads), 4 vertices each. Fill rate is the cost: a quad covering
a fraction f of a 1080p screen with two layers costs about 2 f of screen pixels; a fire filling 10 percent of the screen is cheap on desktop
and noticeable on a phone (so cap overdraw: fade smoke by distance, limit crossed quads to near fires, and only 1 to 2 near big fires at once).
Texture memory: about 2.3 MB of PNG decodes to about 40 MB of RGBA for all five flame atlases (1024x1536 class), so load presets on demand.
CPU: one frame-index update per fire.

## Unverified
Not loaded in the game; not measured for performance; the viewer was syntax-checked but not run in a browser by me; thermal and night-vision
recipes are suggestions. The loop seam was checked numerically (frame difference across the loop point against the average adjacent difference:
campfire 7.2 vs 7.0, gas 9.2 vs 8.2, pool 3.4 vs 4.2, vehicle 4.4 vs 4.6, building 6.7 vs 6.5), not frame by frame by eye. Campfire smoke is too heavy
and fills the whole sprite; the large fires have blocky smoke and heat structure from the coarse grid; sparks and embers are not baked (use the existing particles).
