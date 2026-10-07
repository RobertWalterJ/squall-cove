# Heavy weapons and explosions (2026-10)

Generator: `sound/gen_heavy.py` (added to `render_all.py` MODULES). Checker: `sound/verify_heavy.py` (decodes the Ogg files and prints length, peak, RMS, DC, loop-wrap continuity and band energy).

Rebuild: `cd sound && python gen_heavy.py` renders into `sound/out/`, copies the new files into `audio/` and merges only the new entries into `audio/manifest.json` (all other entries untouched). `--no-deploy` renders only. Verify with `python verify_heavy.py` (reads `../audio`) or `python verify_heavy.py out`. Everything is deterministic (seeded from the stem name). Mono 44.1 kHz Ogg Vorbis q4, bus/group as listed below, all `lazy: true`, groups `weapons` (wpn_, imp_, veh_gun*) and `people` (foley_*) by the same prefix rules as `deploy.py`. 114 files, about 1.8 MB.

## Construction
Each shot is three layers plus a tail: a sine sub body (88 to 35 Hz depending on the weapon) with a fast exponential pitch drop (time constant 20 to 100 ms) and its own decay; a mid band (body noise 50-400 Hz plus a crack, 0.5-9 kHz, 3-14 ms); and a tail made of a long 35-170 Hz rumble band plus a mid band whose low-pass closes over time, with a few dark reflections for room/distance character. Naval gun adds an inharmonic metal ring and clustered water slaps; AA gun adds a 1.7-2.2 kHz ring per pulse; howitzer and naval gun carry the longest rumble. Whistles are a descending tone with 2nd/3rd harmonics, tracking air noise and a rising level, cut off just before the "impact". Loops (`wpn_rocket_loop`, `veh_gunship_minigun_loop`, `foley_turret_traverse_loop`) are periodic by construction (FFT-domain noise, integer-Hz modulators, pulses wrapped circularly) and are NOT edge-faded, so the loop point is continuous.

## Levels (gain staged in `finish()`, not by synthlib's peak normaliser)
Loudest 400 ms RMS is matched inside each class and a soft limiter holds the pre-encode peak at -2.2 dBFS (measured after Vorbis decode: peak at or below -1.8 dBFS everywhere).

| class | target RMS (400 ms window) | measured | members |
|---|---|---|---|
| fire | -19 dBFS | -19.4 to -19.2 | hmg, aa, mortar launch, tank, rpg launch, gunship cannon |
| boom | -17 dBFS | -17.5 to -17.2 | flak burst, howitzer, naval gun, rpg hit, imp_blast_*, crater thud |
| far | -23 dBFS | -23.6 to -23.2 | all `_far` |
| sub | -19.7 dBFS | -19.9 to -19.6 | all `_sub` |
| loop | -21 dBFS | -21.4 to -21.3 | rocket, minigun, turret traverse |
| whistle | -23 dBFS | -23.3 to -23.1 | mortar and shell whistles |
| foley | -25 dBFS | -25.3 to -25.1 | ammo chain, bolt, overheat, turret stop, flak fragments |

Booms are 2 dB louder than fire sounds on purpose. DC offset is below 0.0005 everywhere.

## Conventions
- Variants `_01.._03` for everything. Far versions are `<stem-with-_fire-dropped>_far_01.._03` (`wpn_hmg_far`, `wpn_aa_far`, `wpn_howitzer_far`, `wpn_naval_gun_far`, `wpn_tank_cannon_far`, plus `wpn_flak_burst_far`, `wpn_mortar_launch_far`, `wpn_rpg_launch_far`, `veh_gunship_cannon_far`), so the existing `'wpn_' + name + '_far'` lookup works: the game strips `_NN` to form the family. Far files are low-passed at 520 Hz (4th order), delayed 0.35 s (speed of sound at a few hundred metres) and given a 1.5 s dark reverb, so they are about 3.3 s long and 12 dB or so quieter at the same gain; manifest gain 0.7, maxDist 1200+.
- `_sub_01.._03` is a mono 35-90 Hz layer for `wpn_howitzer_fire`, `wpn_naval_gun_fire`, `imp_blast_medium`, `imp_blast_large` and `imp_crater_thud`. The full stems ALREADY contain this layer; play the sub separately only to add weight (for example through a sub-bass bus or at 0.5 to 0.8 gain for a very close or very big event). It is the same seed and same time base as the full stem so the two stay phase-aligned if started together.
- Durations: fire sounds 1.30 to 1.55 s, whistles 1.5 and 1.8 s, explosions 1.8 s (crater), 2.2, 2.4, 3.0 and 3.8 s (large).
- Loop lengths: rocket 2.0 s, minigun 1.5 s (90 pulses, 3600 rpm), turret 2.0 s.

## Tuning
Edit the maker for a stem (`m_*` functions) or the `CLASS_RMS` table, rerun `python gen_heavy.py`, rerun `verify_heavy.py`. Nothing has been auditioned by ear; all balance decisions were made from the band-energy table (about 30 to 60 percent of the energy of every big stem sits at 35-90 Hz, the sub files 70 to 90 percent). A listening pass should check the minigun "brrrt" density, the naval slap tail and the mortar bloop first.
