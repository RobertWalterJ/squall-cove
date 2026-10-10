# Fire sprites from Blender Mantaflow (second track)

Bakes Blender 4.2's Mantaflow gas simulator (fuel, heat, flame, smoke fields) for several fire types, renders orthographic front-on transparent flame, smoke and heat layers with Cycles, and packs them into looping WebP flipbook atlases for the Squall Cove browser game. The first track (numpy combustion bake) lives in `tools/fire/` and is separate.

Output: `assets/fire_blender/` (WebP atlases + `fireb_atlas.json`), `docs/fireb_preview_sheet.png`, `docs/fireb_viewer.html`. Game usage notes: `MODEL-NOTES-FIRE-BLENDER.md` at the repo root.

## Files

| File | Purpose |
|---|---|
| `bake_fire.py` | Runs inside Blender. Builds the domain and fuel sources for one preset, bakes the cache, renders flame / smoke / heat layers to float arrays, saves the scene to `scenes/`. |
| `pack_atlas.py` | Plain Python (Pillow, numpy, scipy). Loop crossfade, colour grade, denoise blur, soft edge fade, WebP packing, low versions, spread tiles, ember/spatter/streak atlases, JSON, preview sheet. |
| `build_viewer.py`, `viewer_template.html` | Builds `docs/fireb_viewer.html` with the atlas JSON embedded (works from `file://`). |
| `Open fire viewer.bat` | Double-click to open the viewer. |
| `run_all.sh` | Runs presets one after another (one Blender at a time). |
| `scenes/fireb_<preset>.blend` | Saved Blender scenes (no cache inside). |

## Re-running

Blender is the portable copy at `Code Projects\squall-cove\_tools\blender-4.2.9-windows-x64\blender.exe`.

```
# one preset (bake + render), work files in WORK
blender.exe --background --factory-startup --python tools/fire_blender/bake_fire.py -- PRESET WORK --samples 20
# several in a row
bash tools/fire_blender/run_all.sh WORK vehicle pool building gas
# re-render without re-baking (cache kept in WORK/PRESET/cache):  PRESET:--renderonly
# then pack everything and rebuild the viewer
python tools/fire_blender/pack_atlas.py WORK .
python tools/fire_blender/build_viewer.py
```

Presets: `campfire`, `gas`, `pool`, `vehicle`, `building`, `grass`, `tree`, `fireball`, `trail_slow`, `trail_med`, `trail_fast`. All parameters are in the `PRESETS` table at the top of `bake_fire.py` (domain size, source shapes, burn rate, flame vorticity, smoke, dissolve, wind). Options: `--res N`, `--frames N`, `--warm N`, `--samples N`, `--renderonly`, `--blendonly`, `--noblend`.

## Opening and tweaking the scenes

`scenes/fireb_<preset>.blend` holds the domain, fuel objects (with keyframed flicker), the three layer materials (swap material slot 1 of `Domain` between `flame`, `smoke` and `heat`), the orthographic camera and Cycles settings. The cache path is stored relative (`//cache_<preset>/`), and the cache itself is **not** in the file (it is hundreds of MB). To rebake: open the file, select `Domain`, Physics tab, Bake Data. To change a look, edit the Domain's Fire / Smoke settings or the fuel object's Flow settings, rebake, then render frames (the script's render loop shows the camera and layer settings used).

## Cost notes (this PC, 16 threads, CPU only)

Per-preset bake and render times are listed in `MODEL-NOTES-FIRE-BLENDER.md`. Expect roughly 10 to 35 minutes of bake and 8 to 15 minutes of render per fire type at 96 to 128 cells on the tall axis. Bakes slowed a lot when other heavy jobs ran at the same time.
