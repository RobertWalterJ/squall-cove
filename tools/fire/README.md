# tools/fire - baked combustion flipbooks

A reduced 3D combustion solver (`sim.py`) plus a baker (`bake.py`) that turns it into
looping sprite atlases for Squall Cove. Inspired by the multi-species, stoichiometric
approach of Fire-X (Wrede et al., SIGGRAPH Asia 2025); it is NOT a reproduction (see
`MODEL-NOTES-FIRE-BAKED.md` for what is and is not physical).

Needs Python with numpy, scipy and Pillow (all already installed here). No downloads.

## Rerun

    python tools/fire/bake.py all            # all five presets, about 3 to 5 minutes each (sim + render)
    python tools/fire/bake.py campfire       # one preset
    python tools/fire/bake.py pool --seed 3  # a different random variant
    python tools/fire/bake.py campfire --quick --out _fire_tmp   # 16 frames, to a scratch folder
    python tools/fire/preview.py --gif docs/fire_preview.gif     # rebuilds docs/fire_preview_sheet.png (gif is optional, about 6 MB)
    python tools/fire/build_viewer.py        # rebuilds docs/fire_viewer.html (embeds the atlases)

Outputs: `assets/fire/fire_<preset>_flame.png`, `_smoke.png`, `_heat.png`, and
`assets/fire/fire_atlas.json` (merged per preset).

Run one heavy job at a time. The solver uses 4 threads. Presets: `campfire`, `gas`, `pool`,
`vehicle`, `building`.

## Viewer

Double-click `tools/fire/Open fire viewer.bat` (or open `docs/fire_viewer.html`). It plays every
preset, with layer, background, size, speed, glow, thermal and night-vision options. The page has
the atlases embedded, so it needs no server. Re-run `build_viewer.py` after re-baking.

## Files

- `sim.py` - solver and `PRESETS` (grid 32x32x48 cells, `dx` metres per cell, step 1/48 s).
- `bake.py` - ray-march renderer, loop cross-fade, crop, quantise, JSON. `LOOK` holds per-preset colour and smoke settings.
- `preview.py` - preview sheet and optional gif. `build_viewer.py` + `viewer_template.html` - the viewer.

## Parameters worth knowing (in `PRESETS`)

| Key | Meaning |
|---|---|
| `dx` | metres per grid cell; sets the sprite's real size |
| `s` | stoichiometric oxidiser per fuel (air-normalised); lower = shorter flames |
| `theta_ad` | adiabatic temperature of a stoichiometric mixture, 1 = about 2000 K |
| `t_ign`, `k` | ignition threshold (normalised) and reaction speed |
| `rad`, `rad_soot`, `mixc` | radiative cooling, extra for soot, and entrainment cooling (1/s) |
| `beta`, `drag`, `vc` | buoyancy (m/s^2 per unit temperature), drag, vorticity confinement |
| `F_src`, `O_src`, `w_src` | vent fuel, vent oxidiser (premix share), vent velocity; flame height grows with `F_src * w_src * vent area` |
| `soot_k`, `soot_ox`, `delay` | soot inception rate, oxidation rate, residence-time window before soot forms |
| `vents` | list of (x, y, rx, ry, height, amplitude, flicker) fuel patches |
| `warm` | seconds simulated before recording starts |

`Sim(preset, water=lambda t: ...)` accepts a water-spray function (0 to 1): a heat sink with
steam plus fuel starvation. It is in the solver but no extinguishing clip is baked.

Look settings in `bake.py` `LOOK`: `cs` soot glow, `ka` soot absorption, `cb` blue, `co` orange, `expo`
exposure, `scroll` sub-grid texture speed (whole periods per loop, keeps the loop seamless), `noise`,
`warp`, `smoke_k`, `smoke_albedo`, `fps`.
