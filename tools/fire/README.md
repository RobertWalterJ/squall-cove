# tools/fire - baked combustion flipbooks

A reduced 3D combustion solver (`sim.py`), a catalogue of fire types (`presets.py`) and a baker (`bake.py`) that turn
it into looping sprite atlases with lifecycle clips for Squall Cove. Inspired by the multi-species, stoichiometric approach of
Fire-X (Wrede et al., SIGGRAPH Asia 2025); it is NOT a reproduction. See `MODEL-NOTES-FIRE-BAKED.md` for what is physical,
the catalogue, the JSON, and how the game should use it.

Needs Python with numpy, scipy and Pillow (WebP support) - all already installed. No downloads.

## Rerun

    python tools/fire/bake.py campfire            # one type (3 to 6 minutes each)
    python tools/fire/bake.py campfire,pool,vehicle
    python tools/fire/bake.py all --force         # every type (about 3 hours); without --force it skips types already in fire_atlas.json
    python tools/fire/particles.py                # embers, sparks, droplets, streaks, ash, burnt-ground strip (seconds)
    python tools/fire/preview.py                  # docs/fire_preview_sheet.png (overview of every baked type)
    python tools/fire/preview.py --detail campfire,pool --out docs/fire_preview_detail.png   # larger, three rows per type
    python tools/fire/build_viewer.py             # docs/fire_viewer.html (atlases embedded; --low for a smaller page)
    python tools/fire/catalogue.py                # refresh the generated tables in MODEL-NOTES-FIRE-BAKED.md
    python tools/fire/lookdev.py campfire,pool    # quick look at a type without baking (about 30 s each)

Run one heavy job at a time (the solver uses 4 threads). Long bakes should run in the background with output to a log.

## Viewer

Double-click `tools/fire/Open fire viewer.bat` (or open `docs/fire_viewer.html`). Modes: one fire (any type, variants, layers, heat map), lifecycle
(ignite, grow, burn, die down, put out with water, play-through, fuel load), spreading front (tiles advancing over a burnt strip with spot fires),
and explosion (fireballs with flaming debris on ballistic arcs). Backgrounds, thermal and night-vision looks, light glow, size and speed.
The page has the atlases embedded (needed because browsers block pixel reads of local files); re-run `build_viewer.py` after re-baking.

## Files

- `sim.py` - solver. Optional per-type features: `grid` (non-square), `periodic` (tileable in x), `wind` (m/s along x), `blast` (explosion source), vent start delays,
  `puff_every` / `puff_soot` (fuel flare-ups with soot puffs), `supply(t)` (lifecycle schedule), `water(t)` (spray).
- `presets.py` - every fire type: size in metres, vents, kind, look settings (`LOOK`), haze strength. Most types are scaled copies of the five hand-tuned bases.
- `bake.py` - lifecycle runs, ray-march renderer, loop cross-fade, crop, WebP/PNG encoding, JSON. `particles.py` - analytic sprites. `preview.py`, `lookdev.py`, `build_viewer.py`, `viewer_template.html`, `catalogue.py`.

## Parameters worth knowing (in `PRESETS`)

| Key | Meaning |
|---|---|
| `dx`, `grid` | metres per cell and cell counts; sets the real size of the sprite |
| `s`, `theta_ad` | stoichiometric oxidiser per fuel; adiabatic temperature of a stoichiometric mixture (1 = about 2000 K) |
| `t_ign`, `k` | ignition threshold and reaction speed |
| `rad`, `rad_soot`, `mixc` | radiative cooling, extra for soot, entrainment cooling (lower = hotter plume that keeps rising) |
| `beta`, `drag`, `vc` | buoyancy, drag, vorticity confinement |
| `F_src`, `O_src`, `w_src` | vent fuel, premix oxidiser, vent velocity; flame height grows with `F_src * w_src * vent area` |
| `soot_k`, `soot_ox`, `delay` | soot yield, burn-off, residence time before soot forms |
| `vents` | (x, y, rx, ry, height, amplitude, flicker, kind, delay): fuel patches; kind `line` runs along x |
| `warm` | seconds before the developed fire is recorded |

`LOOK` (per type) in `presets.py`: `cs` soot glow, `ka` absorption, `cb` blue, `co` orange, `expo`, `scroll`, `noise`, `warp`, `smoke_k`, `smoke_albedo`, `smoke_glow` (orange under-light), `tint`.
