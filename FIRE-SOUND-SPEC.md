# Fire sound pack: spec and integration

Procedural, licence-free, deterministic (seeded from the stem name). Generator `sound/gen_fire.py`, verifier `sound/verify_fire.py`. 115 new stems (`fire_*`), 1.76 MB download. Written by ear-less measurement only: nobody has listened to these yet (see "Honest limits").

The older fire stems stay untouched and remain valid: `fire_crackle_loop_s/m/l`, `fire_ember_pop_01..06`, `fire_extinguish_hiss_01..04`, `fire_ignite_whoomp_01..04`, `fire_tree_burn_roar`, `fire_tree_fall_01..04`, `amb_fire_bed`, `amb_steam_hiss`, `veh_fire_on_boat_loop`, `veh_fire_hose_spray_loop`. The new pack adds size classes, fuel types, distance and interior versions; use the new loops for any fire that has a size class, keep `fire_tree_fall_*` for the fall itself and `amb_fire_bed` for the global background.

Rebuild: `cd sound; python gen_fire.py` (about 4 minutes; renders to `sound/out/`, copies into `audio/`, merges only the new `fire_*` ids into `audio/manifest.json`). `python gen_fire.py camp --no-deploy` renders a subset. `python gen_fire.py --meta-only` re-applies the manifest hints. Check: `python verify_fire.py --audio`.

## Format (deviation from the 44.1 kHz convention)

Mono Ogg Vorbis. To keep the pack under 2.5 MB all loops and all dark or low-frequency one-shots are 22.05 kHz (content below 11 kHz, which holds everything that matters in fire; the manifest `sr` says 22050 and `decodeAudioData` resamples to the context rate, so nothing in the engine changes). Only the short bright one-shots (`pop_ember`, `spark`, `log_crack`, `glass`, `clatter`) stay 44.1 kHz. Peak is at or below -2.6 dBFS decoded everywhere. Loops are exactly periodic by construction (circular FFT noise, wrap-around event placement, circular filters), no crossfade needed; loop in the engine with the normal `loop = true`.

## Stems

Naming: loops `fire_<kind>_loop_NN`; distant twin `fire_<kind>_loop_far_NN`; interior twin `fire_<kind>_loop_int_NN`; one-shots `fire_<what>_NN`. Level columns are measured on the decoded files: `rms` over the whole file, `loud400` the loudest 400 ms (the class the other packs use).

| family | n | dur s | peak dBFS | rms | loud400 | centroid Hz | KB each |
|---|---|---|---|---|---|---|---|
| `fire_camp_loop` | 2 | 6.0 | -7.6 | -27.9 | -21.8 | 3657 | 30 |
| `fire_camp_loop_far` | 1 | 6.0 | -17.0 | -32.1 | -27.4 | 355 | 19 |
| `fire_medium_loop` | 2 | 7.0 | -7.0 | -25.9 | -19.9 | 2916 | 40 |
| `fire_medium_loop_far` | 2 | 7.0 | -10.9 | -30.1 | -23.4 | 438 | 20 |
| `fire_medium_loop_int` | 2 | 7.0 | -9.9 | -28.4 | -22.1 | 893 | 26 |
| `fire_large_loop` | 2 | 8.0 | -6.1 | -23.2 | -18.5 | 2602 | 45 |
| `fire_large_loop_far` | 2 | 8.0 | -10.7 | -27.3 | -22.2 | 262 | 21 |
| `fire_large_loop_int` | 2 | 8.0 | -8.9 | -25.2 | -20.4 | 732 | 29 |
| `fire_vehicle_loop` | 2 | 7.0 | -10.6 | -23.6 | -21.2 | 3771 | 30 |
| `fire_vehicle_loop_far` | 1 | 7.0 | -15.4 | -28.0 | -24.7 | 498 | 20 |
| `fire_pool_loop` | 2 | 8.0 | -6.8 | -23.3 | -18.4 | 1926 | 45 |
| `fire_pool_loop_far` | 1 | 8.0 | -10.1 | -27.4 | -21.4 | 249 | 19 |
| `fire_grass_loop` | 2 | 7.0 | -3.9 | -24.2 | -18.2 | 4742 | 32 |
| `fire_grass_loop_far` | 1 | 7.0 | -13.3 | -28.8 | -24.8 | 917 | 24 |
| `fire_tree_loop` | 2 | 7.0 | -4.2 | -23.8 | -17.5 | 3058 | 33 |
| `fire_tree_loop_far` | 1 | 7.0 | -11.3 | -28.0 | -22.0 | 458 | 19 |
| `fire_gas_loop` | 2 | 6.0 | -12.9 | -27.0 | -26.1 | 4950 | 27 |
| `fire_spray_loop` | 2 | 6.0 | -11.3 | -25.9 | -23.6 | 5214 | 27 |
| `fire_distant_loop` | 2 | 8.0 | -9.0 | -32.1 | -23.6 | 857 | 28 |
| `fire_pop_ember` | 6 | 0.13 | -4.4 | -26.1 | -26.1 | 4918 | 4 |
| `fire_spark` | 5 | 0.14 | -4.5 | -25.8 | -25.8 | 7699 | 4 |
| `fire_log_crack` | 5 | 0.49 | -3.4 | -23.1 | -22.2 | 4670 | 7 |
| `fire_beam_creak` | 5 | 2.0 | -17.2 | -31.8 | -27.1 | 893 | 11 |
| `fire_glass` | 4 | 1.35 | -8.6 | -26.7 | -22.2 | 5979 | 16 |
| `fire_flare_small` | 4 | 1.0 | -9.6 | -26.9 | -23.2 | 1569 | 7 |
| `fire_flare_medium` | 4 | 1.6 | -9.9 | -26.4 | -21.3 | 1359 | 9 |
| `fire_flare_large` | 4 | 2.6 | -7.8 | -25.6 | -19.7 | 1222 | 13 |
| `fire_flare_large_far` | 2 | 3.4 | -14.4 | -30.8 | -23.8 | 258 | 10 |
| `fire_ignite_soft` | 4 | 0.86 | -8.0 | -26.5 | -23.2 | 1222 | 6 |
| `fire_ignite_large` | 4 | 2.4 | -6.4 | -25.4 | -18.5 | 1684 | 12 |
| `fire_tank_burst` | 4 | 2.6 | -4.2 | -26.1 | -18.6 | 2439 | 13 |
| `fire_tank_burst_far` | 2 | 3.4 | -8.8 | -29.9 | -22.4 | 292 | 10 |
| `fire_lick` | 5 | 0.73 | -7.8 | -28.0 | -25.6 | 2405 | 6 |
| `fire_collapse` | 4 | 4.2 | -5.1 | -26.7 | -18.4 | 1644 | 20 |
| `fire_collapse_far` | 2 | 5.1 | -14.2 | -32.3 | -23.8 | 251 | 13 |
| `fire_clatter` | 4 | 1.35 | -9.5 | -29.2 | -25.1 | 3027 | 12 |
| `fire_water_hiss_short` | 4 | 0.97 | -2.6 | -24.9 | -21.2 | 4881 | 7 |
| `fire_water_hiss_long` | 4 | 3.0 | -3.8 | -28.0 | -21.2 | 4937 | 15 |
| `fire_out_fade` | 3 | 2.1 | -8.3 | -31.1 | -24.9 | 4815 | 11 |
| `fire_sizzle` | 3 | 2.6 | -9.1 | -30.9 | -26.5 | 5604 | 17 |

What each is:

- **camp**: soft crackle, hiss, gentle roar, sparse pops and resin spits (campfire, barrel, brazier).
- **medium**: denser crackle, low roar bed, occasional low pops.
- **large** (building): deep roaring bed with a 25 to 140 Hz turbulent rumble that gusts, wood-structure creaks and low pops built in; glass is a one-shot.
- **vehicle**: harsher, saturated roar, rapid soft pops, hiss, two bigger whoomphs per loop.
- **pool** (oil or fuel pool): heavy low roar, a 1 to 2 Hz rolling swell in the 70 to 230 Hz band, three slow "whoomp" breaths per loop.
- **grass** (grass or brush front): fast dense crackle and sizzle, a wind-driven mid rush, one swell per loop where crackle density rises about 2.6 times and falls again (the front passing). Variant 02 swells at a different point.
- **tree**: loud snapping crackle, resin spit pops, two crown "whoosh" swells per loop.
- **gas**: steady 2.5 to 9.5 kHz burner hiss, 200 to 1300 Hz blue-flame roar, 112 Hz hum with 2nd and 3rd harmonics; almost no crackle, level varies by under 1 dB.
- **spray**: sprinkler or hose spray over fire (water hiss, jet body, steam hiss, a few crackles); a loop, level varies by about 1.3 dB.
- **distant**: soft band-limited bed of many fires far away (low roar, filtered crackle, slow swells as fires come and go); the overview-camera and far-listener bed.
- **`_far`**: the near loop through a 4th-order circular low-pass (camp 1000, medium 850, large 520, vehicle 800, pool 450, grass 1300, tree 800 Hz) and 4 dB quieter, so a near and far pair of the same number are the same sound at two distances.
- **`_int`**: the near loop through a 2 kHz 4th-order low-pass at the interior level (-2.5 dB), for the gunship station and enclosed spaces.
- **pop_ember**: six different kinds (soft thump, dry tick, double tick, hollow tup, snap with thump, tiny spit). **spark**: sharp bright crack with micro-ticks. **log_crack**: pre-ticks, then a broadband crack with a wood body and a short low thump, then splinter ticks. **beam_creak**: stick-slip wood creak or groan, 1.5 to 2.6 s, quiet by design.
- **glass**: crack, low thud, big shard rings, then a tinkle shower. **flare_small/medium/large**: the whoomph of a fire taking a breath (sub thump, swelling filtered noise, large adds a rumble tail). **ignite_soft / ignite_large**: soft "fwump" ignition; large fuel ignition with rolling whoosh and rumble. **tank_burst**: short fireball: low thump, bright to dark whoosh, rumble, a little debris, no blast crack (it is not an explosion: use the explosion pack for those). **lick**: soft flame lick whoosh. **collapse**: creak, rising snaps, crash of debris with low thuds, dust whoosh, settling ticks. **clatter**: burning debris landing. `_far` of flare_large, tank_burst, collapse: low-passed (650/600/650 Hz) with reverb tail.
- **water_hiss_short/long**: water meets fire (steam hiss with bubbles and spits). **out_fade**: 2 to 2.2 s extinguish hiss fading with a closing low-pass and last spits. **sizzle**: embers dying, dense ticks thinning out.

## Integration

### Manifest hints

Every entry has `meta.kind` (`loop` or `oneshot`) and `meta.play` = `{gapMs, maxVoices, rotate, preload:false, bus}` (the engine does not read them yet; same convention as the AC-130 pack). Loops also carry `meta.fire` (size or fuel), `meta.role` (`near`, `far`, `interior`), `meta.xfadePair` (the stem to cross-fade to, same number) and `meta.xfade = [d0, d1]` metres. `maxDist` is the distance beyond which the stem should be silent. All `lazy: true`, group `fx`, bus `mat` (the distant bed is on `amb`). One-shots have weight 2 (culled first under pressure when gain is below 0.35), loops weight 3.

### Picking a loop by fire size and fuel

| thing burning | loop | extra triggers |
|---|---|---|
| campfire, barrel, brazier, torch cluster | `camp` | `pop_ember`, `spark`, rare `lick` |
| gas flame, burner, flare stack | `gas` | none (steady) |
| small wreck, shrub cluster, 3 to 10 burning cells | `medium` | `pop_ember`, `log_crack`, `lick`, `flare_small` |
| burning vehicle (car, truck, boat) | `vehicle` | `flare_medium` on tank flare, `tank_burst` on fuel tank failure, `glass` when windows go, `clatter` on part fall |
| oil or fuel pool | `pool` | `ignite_large` at ignition, `flare_large` / `flare_medium` as it feeds, `ignite_soft` for small spills |
| building, large timber structure, 10+ cells | `large` | `log_crack`, `beam_creak`, `glass`, `flare_large`, `collapse` + `clatter` |
| grass or brush front | `grass` | `ignite_soft` at the start; `pop_ember` |
| burning tree | `tree` | existing `fire_tree_fall_*` at the fall, `pop_ember` |
| embers, smouldering | no loop (or `camp` at gain 0.25) | `pop_ember`, `sizzle` |

Size is the flame height or area from the baked fire presets (`MODEL-NOTES-FIRE-BAKED.md`): below about 1.2 m flame use `camp`, 1.2 to 3 m `medium`, above that `large` for structures. When several fires of the same type are within 15 m of each other, play one loop of the same class for the whole cluster at `+3 dB * log2(count)` (cap +6 dB) instead of one per fire; stepping a cluster up a class (medium to large) when it passes 12 burning cells. Take the variant with `fireId % variants` so neighbouring fires differ, and start each loop at a random offset (or detune the playback rate by 0.97 to 1.03 per fire) so that two fires of the same stem do not phase together.

### Gain and distance

Reference gain 1.0 is the file level (the loops sit at -23 to -28 dB RMS, matching `fire_crackle_loop_m` at -26.8 and the AC-130 loops). Scale by flame intensity 0.3 to 1.0 (`intensity` from the fire sim). Distance gain `g(d) = min(1, refDist / d)` (6 dB per doubling) with `refDist`: camp 3 m, medium 5, large 12, vehicle 6, pool 9, grass 8, tree 6, gas 2, spray 4. Then fade to silence over the last 15 percent before `maxDist`.

| loop | cross-fade near to far, m | near silent / far silent, m |
|---|---|---|
| camp | 12 to 40 | 40 / 40 (far only to 25 m beyond the fade, then the distant bed) |
| medium | 20 to 64 | 64 / 75 |
| large | 45 to 144 | 144 / 220 |
| vehicle | 22 to 72 | 72 / 110 |
| pool | 32 to 104 | 104 / 160 |
| grass | 25 to 80 | 80 / 130 |
| tree | 22 to 72 | 72 / 100 |
| gas, spray | none (fade out, no far twin) | 30 / 60 |

(The exact numbers are in `meta.xfade` and `maxDist`.) Beyond the far range the fire is carried by `fire_distant_loop`.

### Near and far cross-fade

Both twins play at the same time inside the cross-fade zone, same variant number, and are phase-coherent by construction (the far file is a filtered copy of the near one), so equal-power fading has no comb effect. With `w = smoothstep((ln d - ln d0) / (ln d1 - ln d0))`: near gain `cos(w * pi/2) * g(d)`, far gain `sin(w * pi/2) * g(d)`. Stop the near loop when `w = 1` and start the far loop when `w > 0` (lazy load the far files when a fire of that class is within 2 times `d1`). When a fire has no far twin (camp variant 02, vehicle 02 etc. map to the single far file: use `min(variant, farCount)`), play the single far loop. Playing the far twin for a distant fire needs no near file at all, so a battlefield of far fires only loads the far set.

### One-shots: when and how often

| family | trigger | gapMs | maxVoices | rate guidance |
|---|---|---|---|---|
| `pop_ember` | random from any fire within 40 m | 110 | 3 | 0.4 to 3 per second per near fire, scaled by intensity; at most 8 per second in total; only the 3 nearest fires |
| `spark` | gust, fuel spill, flare, collapse | 90 | 3 | 0.2 to 1.5 per second near fuel and sparks events |
| `log_crack` | wood fuel (building, tree, timber) | 350 | 2 | 0.05 to 0.4 per second; 50 to 100 m max |
| `beam_creak` | structure under load before collapse, or occasional for large | 3500 | 1 | once per 6 to 15 s near the structure; a certain creak 2 to 4 s before `collapse` |
| `glass` | window or glazing fails in fire | 700 | 2 | per event, 90 m max |
| `flare_small/medium/large` | intensity rises by more than about 40 percent in 1 s, new fuel | 900 / 1500 / 3000 | 2 / 2 / 1 | event driven; use the matching size class; `flare_large_far` beyond 120 m |
| `ignite_soft` / `ignite_large` | ignition of a cell, small spill / big fuel or pool | 600 / 2500 | 2 / 1 | event driven; `ignite_large` ducks the loops (below) |
| `tank_burst` | fuel tank fails | 1500 | 2 | event; `tank_burst_far` beyond 150 m; pair with the explosion pack only if there is a real blast |
| `lick` | flame jumps or flares at the edge | 450 | 3 | 0.1 to 0.5 per second on medium and large |
| `collapse` | structure or tree-top collapses | 6000 | 1 | event; `collapse_far` beyond 150 m; follow with 2 or 3 `clatter` 0.6 to 2 s later and a `pop_ember` shower |
| `clatter` | burning debris lands | 900 | 2 | event, 60 m max |
| `water_hiss_short` | each water impact on fire | 250 | 3 | per hit; at hose rates (above 4 per second) play the spray loop instead |
| `water_hiss_long` | big water drop or bucket onto a large fire | 1200 | 2 | event |
| `out_fade` | a fire goes out (the last 2 s) | 800 | 2 | event; follow with `sizzle` after 0.5 s |
| `sizzle` | embers cool, after extinguishing | 1200 | 2 | one per extinguished fire, 30 m max |

Rules: never repeat a variant twice in a row in a family (the engine does this already); rate jitter 0.94 to 1.06, gain jitter 1.5 dB; `pop_ember`, `spark` and `lick` with gain below 0.35 and weight 2 are the first to be culled when voices are tight.

### Water and extinguishing

A fire under water or a spray: start `fire_spray_loop_NN` (key it per spray source, one per hose or sprinkler cluster, `maxVoices` 2), fade out the fire's own loop by the fraction of the fire suppressed (to 0 when out), play a `water_hiss_short` per discrete hit. When a fire is out, play `out_fade` (the 2 s tail) while fading the loop out over the same time, then `sizzle`. The spray loop should fade out over 0.5 s after the last water. The sound of the existing `fire_extinguish_hiss_*` is still good for sand, foam or an instant kill.

### Many fires: ducking and limiting

1. At most 6 fire loops audible at once (a near and far pair crossing counts as one). Rank all fires by `g(d) * intensity * classLoudness` (loudness: large 1.0, pool 1.0, tree 0.8, grass 0.8, vehicle 0.8, medium 0.6, camp 0.4, gas 0.4) and keep the top 6; anything below the cut-off contributes only through `fire_distant_loop`.
2. Power limit: let `S = sum(gain_i^2)` over the playing fire loops; if `S > 2.5` scale all by `sqrt(2.5 / S)` (a total about 4 dB over a single loud fire). This keeps a burning town from clipping the mix and from drowning speech or weapons.
3. One-shot budget from fire as a whole: at most 6 fire one-shots per second and at most 4 fire voices at the same time; only the 3 nearest fires may emit crackle one-shots, and none beyond 40 m (the loops already carry the crackle). Big events (`tank_burst`, `collapse`, `flare_large`, `ignite_large`) are never culled; the rest follow the weight rule.
4. Big-event duck: while `tank_burst`, `collapse`, `ignite_large` or `flare_large` play, duck the fire loops by 4 dB (attack 30 ms, release 600 ms) and `amb_fire_bed` by 6 dB, so the event reads. Weapons and explosions duck fire loops by 2 dB for 250 ms using the existing duck rules.
5. `fire_distant_loop` gain: `min(1, farFireCount / 12) * (1 - 0.7 * nearestFireProximity)` at `0.9 * g`, and always on when the overview camera is active (`cameraHeight` above about 60 m) with the near loops faded by camera height instead of listener distance. It replaces `amb_fire_bed` for that purpose; do not run both at full level.
6. Loops are not counted as voices by the engine (`A.set`), but they cost CPU: keep within the 6-loop cap on touch (cap 4 on touch).

### Thermal, night vision, and the gunship station

- The thermal and night-vision filters are video effects; the audio does not change with them. For the sensor operator inside the gunship, use the interior set: `fire_medium_loop_int` for medium, vehicle, tree, grass fires and `fire_large_loop_int` for large and pool fires within about 250 m of the aircraft; beyond that only `fire_distant_loop` at -3 dB. Interior one-shots: use the exterior one-shots through the existing 2 kHz headset low-pass (the cabin bus), gain -6 dB, and skip `pop_ember`, `spark`, `lick`, `clatter`, `sizzle` (inaudible through ear defenders).
- When the listener is inside a building or vehicle with the fire outside, use the `_int` loop for that fire at gain -2 dB; no cross-fade, just switch with a 0.4 s fade when the cabin state changes.
- Thermal view is dominated visually by fire; it is reasonable (not required) to add +2 dB to `fire_distant_loop` and the interior large loop while thermal is on, so the audio matches what the operator is watching.
- On the overview camera: no near loops at all above the cut-off height, only `fire_distant_loop` (and `_far` loops for fires inside the frame at 0.6 gain if wanted).

### High rate of fire playback

Same engine facts as `AC130-SOUND-SPEC.md` ("High rate of fire playback"): the 45 ms per-family gap does not limit separate stems, the voice budget `A.max` is 24 (desktop) and 14 (touch), loops via `A.set` do not count as voices, `A.loadStem` loads a whole family on the first miss and that first call is silent. For fire:

1. Fire one-shot families are short and many, so game code must aggregate: a single fire coordinator that runs once per frame, collects fire events, and applies the `gapMs` table above per family plus the total of 6 per second.
2. Budget on desktop (24 voices) for fire: 4 at the same time (pops and sparks 2, event stems 2); on touch (14): 3.
3. Call `A.loadStem` at ignition time for the class of fire being created (`pop_ember`, `spark`, and the loop family of that size), not when the first pop is wanted. Event stems (`tank_burst`, `collapse`, `glass`, `flare_*`, `ignite_*`) load when the first fire with the matching fuel or structure exists (a vehicle with fuel, a building, a pool).
4. A loop is only requested for a fire that is within `d1 * 2` of the listener (near and far) or within the distant-bed condition, and is released when the fire has been out of range for 20 s.

### Memory and download

Download is the Ogg size: 115 stems, 1.76 MB total (loops 1.07 MB, one-shots 0.69 MB). Decoded memory is `dur * context rate * 4` bytes (about 0.18 MB per second at 44.1 kHz, 0.19 at 48 kHz) because `decodeAudioData` resamples the 22.05 kHz files to the context rate. A large near loop is 8 s and about 1.4 MB decoded; a medium 1.2 MB; a camp 1.1 MB; one far loop 1.2 to 1.4 MB. Loading discipline: loops are never preloaded (`preload: false`); load a class only when a fire of that class exists or comes within range, keep only the variants in use (two at most per class), and on touch release non-core fire buffers 90 s after the last fire of that class went out. A typical battle with a campfire, one vehicle fire and one building fire: camp 1 variant + vehicle 1 + large near and far = about 5 MB decoded, 130 KB downloaded.

### What to change in the game, concretely

1. A `Fire` audio coordinator keyed by fire id: size class, fuel type, intensity, distance; ranking, cluster merging, cross-fade, ducking and the one-shot budget as above.
2. Replace the single `crackle_loop_s/m/l` choice by the table in "Picking a loop by fire size and fuel"; keep the old stems as fallback.
3. Hook one-shots to the sim events listed in the table (fuel tank failure, glass, structure collapse, ignition, flare-up, suppression).
4. Hook `fire_spray_loop`, `water_hiss_*`, `out_fade`, `sizzle` to the water and extinguish code.
5. Hook the interior set to the station and enclosed-listener state; `fire_distant_loop` to the overview camera and to the far-fire count.

## Verification (script `sound/verify_fire.py --audio`, decoded files)

- Peaks: highest decoded peak -2.6 dBFS (water_hiss_short); every stem is at or below -2.6 dBFS.
- Loudness: loop RMS -23 to -28 dB (camp -27.9, medium -25.9, large -23.2, vehicle -23.6, pool -23.3, grass -24.2, tree -23.8, gas -27.0, spray -25.9, distant -32.1; far twins 4 dB under their near twin; interior 2.5 to 3 dB under); one-shot loudest-400-ms RMS by class: pops and sparks -26, log crack -22, glass -22, flare small -23, medium -21, large -20, ignite soft -23, large -18.5, tank burst -18.6, collapse -18.4, water hiss -21, out fade -25, sizzle -26.5. For reference the existing `fire_crackle_loop_m` is -26.8 RMS and the AC-130 loops are about -21 loud400.
- Loop seams (decoded): the step between the last and first sample is at or below -23 dBFS absolute for every loop and no larger than the largest in-body step for 31 of 33 loops; the two exceptions (`large_loop_far_02` +4.2 dB, `pool_loop_far_01` +5.4 dB over the largest step of a very quiet dark file) are at -40 and -37 dBFS absolute, far below audibility. The 20 ms RMS at the join is within +/-2 dB of the median window for most loops (largest +6.6 dB in `distant_02` and +4.2 in `vehicle_far_01`, where a crackle event straddles the wrap). Loops are periodic by construction; the residual is Vorbis encoder edge effects.
- Spectral centroid: near loops 1.9 to 5.2 kHz (large 2.6, pool 1.9, gas 4.95, spray 5.2), far twins 0.25 to 0.9 kHz, interior 0.73 to 0.89 kHz, distant 0.86 kHz. Energy split of the large loop: 54 to 57 percent below 150 Hz, 32 to 35 percent 150 to 800 Hz; campfire: 26 to 29 percent below 150 Hz, 52 to 56 percent 150 to 800 Hz.
- Liveliness: 50 ms level standard deviation 2.9 to 4.7 dB for the crackling loops (4.4 camp, 4.0 medium, 4.1 large), 1.8 to 2.1 dB vehicle, 0.7 to 0.9 dB gas, 1.3 dB spray, 4.7 to 6.4 dB distant (by design).
- Variant diversity: cross-correlation of the loop variants 0.01 to 0.08 (distinct); one-shot families: ember 0.19, spark 0.10, beam creak 0.17, glass 0.05, lick 0.08, clatter 0.06, collapse 0.30, tank burst 0.32, flare small 0.40, flare medium 0.32, flare large 0.07, water hiss 0.03 to 0.06, sizzle 0.02, out fade 0.05. Higher values (ignite soft 0.57, ignite large 0.58, log crack 0.57) come from a shared low sub thump: the metric allows lags of +/-5 ms, a full period of a 95 Hz sine, so any two low thumps read as correlated; the variants differ in pitch, phase, timing and noise.
- Size: 115 files, 1799 KB (1.76 MB). Loops 33 files, one-shots 82.

## Honest limits

Nothing here has been listened to. The numbers above only show levels, spectra, seams and variant difference. Things most likely to need an ear pass: the campfire and medium crackle density (rate/amplitude of ticks against the roar), whether the large loop's creaks read as wood rather than a squeak, the pool "rolling" swell, the grass front swell, the tank burst (is it a believable fireball and not too close to an explosion), and the glass shower. The tuning knobs are the `SPEC` dict and the maker functions at the top of `sound/gen_fire.py`; change a number, rerun the single family with `python gen_fire.py <stem fragment>`.
