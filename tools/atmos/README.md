# tools/atmos - baked steam, mist and fog flipbooks

A reduced moist-air solver (`fluid.py`), a renderer (`render.py`) and a baker (`bake.py`) that turn it into sprite atlases for Squall Cove.
The flow numerics are copied from `tools/fire/sim.py`; see `MODEL-NOTES-ATMOS.md` (repo root) for what is and is not physical and for game-use notes.
Needs Python with numpy, scipy and Pillow. No downloads.

## Rerun

    python tools/atmos/bake.py steam_pipe            # one preset (about 1 to 4 minutes; fog strips 3 to 5 minutes)
    python tools/atmos/bake.py steam                 # a family: steam | mist | fog, or a comma list, or all
    python tools/atmos/bake.py fog_ground --quick --out _atmos_tmp
    python tools/atmos/preview.py                    # docs/atmos_preview_sheet.png (6 frames per preset, dark and grey day)
    python tools/atmos/build_viewer.py               # docs/atmos_viewer.html (embeds the atlases)

Run one heavy job at a time. Every preset is independent; `assets/atmos/atmos_atlas.json` is merged per preset.
Tip: on a busy machine, run the bake in a foreground console; a hidden background process can be starved of CPU.

## Viewer

Double-click `tools/atmos/Open atmos viewer.bat` (or open `docs/atmos_viewer.html`). Modes: single sprite (preset, clip, lifecycle play-through,
size, speed, wind, day / night / dusk / bright backlit, thermal and night-vision looks, low atlas, scatter layer), three parallax fog layers,
and a procedural landscape with overlays (bow spray, steam, splashes, dawn mist, harbour fog).

## Files

* `fluid.py`  `Air` (moist solver) and `Spray` (droplet parcels).
* `presets.py`  the catalogue: sim parameters, look, clips, game hints (wind, lighting). Sizes are real metres.
* `render.py`  extinction volume to alpha, shading, scatter; noise; atlas packing helpers.
* `bake.py`  pipelines `life` (start, loops, fade / settle), `shot` (splashes), `strip` (tileable fog lifecycle), `blobs`; JSON writer.
* `preview.py`, `build_viewer.py`, `viewer_template.html`, `Open atmos viewer.bat`.

## Output

Per preset in `assets/atmos/`: `<p>.webp` + `<p>_low.webp` (grey + alpha), `<p>_scatter.webp` + `_low` (forward-scatter layer, half and quarter size),
`<p>_heat.webp` (steam only, thermal view). JSON: frame size, atlas grid, metres per pixel, anchor, clips (name, stage, variant, loop, fps, first, count,
duration), wind response, lighting by time of day, sensor behaviour, heat-haze descriptor (steam), fog state machine and tiling data (strips), seam statistics.

## Presets

steam: `steam_pipe`, `steam_pot`, `steam_engine`, `steam_burst`, `steam_geyser`, `steam_lava`. mist: `mist_bow`, `mist_surf`, `splash_small`, `splash_medium`,
`splash_large`, `spray_cone`, `mist_dawn`. fog: `fog_ground`, `fog_bank`, `fog_sea`, `fog_valley`, `fog_wisps`, `fog_forest`, `fog_blobs`.
