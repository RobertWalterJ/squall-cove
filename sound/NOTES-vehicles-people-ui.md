# Notes: vehicles, people, NPC cues, UI, hold tools, music

Modules: `gen_vehicles.py`, `gen_people.py`, `gen_ui_music.py` (shared helpers in `svp_common.py`; `synthlib.py` untouched).
308 assets, 7.2 MB total, 1.3 MB of it in group `core` (footsteps and UI, plus tug and outboard engines). Everything is deterministic (seeded).
All loops are rotated by `svp_common.seal()` so the saved file ends and starts on a near-zero flat spot (seam under -44 dB). The loops are circular, so this does not change the sound.
Loops built from tones (engines, sirens, heli, pads, hold tools) snap tone frequencies to an integer number of cycles per loop, so they are periodic by construction.

Level convention: engines target -25 / -24 / -22.5 LUFS (lo / mid / hi), UI peak -10 dBFS, stings -6 dBFS, pads -28 LUFS (night -30), heli -22 LUFS, other one-shots peak -3 dBFS.
Mono 44.1 kHz for vehicles; 32 kHz for UI, people, NPC cues and music (stereo for music).

## Engines (`veh_eng_<type>_lo|mid|hi`, 5 s loops, meta has `rpm`, `rpmRange`, `throttleRange`, `rateRange`, `firingHz`)
Recipe: `synthlib.engine()` at the layer rpm (firing rate snapped to whole cycles per loop, periodic wobble), then lowpass, spectral tilt, body resonances (peak EQ), diesel knock bursts gated to the firing rate. The mid layer carries 30 percent of the lo layer's low band and the hi layer 18 percent of mid's, so the three share a timbre and can be crossfaded.
Runtime: crossfade by throttle with equal-power gains: lo 0 to 0.40, mid 0.25 to 0.78, hi 0.60 to 1.0 (these ranges are in `meta.throttleRange`). Play every layer at the same time with `playbackRate = targetRpm / meta.rpm`, clamped to 0.8..1.25 (hi layer 0.85..1.15) so the firing pitch stays believable. The 10 Hz update loop should smooth rpm (about 0.3 s).
Measured firing fundamentals and centroids (Hz): tug 18.8/30/43.8 (centroid 162/230/310), lifeboat 50/100/160 (250/421/651), patrol 45/75/115 (212/243/441, twin engines detuned about 1.1 percent so they beat), icebreaker 9/14/19.6 (71/84/94; 70 to 80 percent of the energy is in 40 to 120 Hz), outboard 66.6/116.6/183.4 (339/520/810), hover blade-pass 288/408/552 (494/981/1459). First versus last second RMS differs by 1.6 dB at most.
- hover: noise-dominated (band-passed pink roar, 12-blade pass tone with harmonics, turbine whine, low engine rumble). Rate range 0.8 to 1.25 moves blade pass.
- tug and outboard are `core` (not lazy). The rest are lazy, group `boats`.

## Boat and rigging
- `veh_prop_wash_loop` 5 s: churned pink noise, 11 Hz prop AM, bubble grains. Gain by speed; rate 0.9 to 1.1 with throttle.
- `veh_sail_luff` loop: irregular cloth flutter (band-passed noise gated by 9 to 13 Hz flutter). Level by luffing amount (sail angle error).
- `veh_sail_flap` x4, `veh_sheet_creak` x4 (stick-slip sawtooth through moving resonators), `veh_rope_rattle` x4, `veh_hull_creak` x4 (0.9 to 1.8 s): trigger on gusts, tacking and heel changes.
- Horns: `veh_horn_short` 0.65 s, `veh_horn_long` 2.2 s (196 + 247 Hz stacked harmonics, three detuned copies each, breath noise); `veh_foghorn` 4.2 s (98 + 104.5 Hz, 16 harmonics, echo); `veh_ship_bell` 6 s (MODES bell, f0 520 Hz); `veh_buoy_bell` x4 (bell, f0 1050 to 1500 Hz, short decay, 3 to 5 irregular strikes). Trigger buoy bell from wave height or buoy tilt (more strikes when rougher).
- Sirens: `veh_siren_wail` (4 s, 650 to 1500 Hz exponential sweep) and `veh_siren_yelp` (0.2 s sweeps), loops, periodic.

## Weapons and hull (group `weapons`, lazy)
- `veh_gun_fire` x4: 1.2 ms crack (bandpassed, lowpassed at 5.2 kHz), noise tail, 125 to 52 Hz boom sweep, outdoor echo. Energy above 6 kHz under 0.01 percent.
- `veh_gun_shell_fly` x4 (1.4 s whistle swell, bandpass sweeping down), `veh_mg_burst` x4 (9 to 14 taps at 11 to 14 per second).
- `veh_hull_hit_light/heavy` x4: modal plank or wood plus an independent low thump (frequency and phase random per variant). Choose by impact mass x speed. `veh_hull_breach` x4 (splinter crack plus water gush and bubbles).
- Loops: `veh_sinking_gurgle`, `veh_fire_on_boat_loop` (crackle plus roar plus pops), `veh_fire_hose_spray_loop` (hiss capped at 7.5 kHz), `veh_winch_loop` (ratchet plus motor). `veh_anchor_chain` x4, `veh_ice_crunch_hull` x4.

## Aircraft (group `aircraft`, lazy)
- `veh_heli_rotor_loop` (4 s, blade pass 18 Hz exactly, thump harmonics, blade slap gated to the pulse, 4.5 Hz rotor modulation, low turbine whine): rate 0.9 to 1.1 scales blade pass. `veh_heli_whine_loop` (2.2 kHz + 3.3 kHz turbine), `veh_heli_wash_loop` (downwash noise with 18 Hz AM). Layer by speed and by altitude above the camera (wash only when low).
- `veh_prop_small_loop` (80 Hz firing, 4 cylinder), `veh_prop_big_loop` (9-cylinder radial, 33.75 Hz three-blade thrum). Rate 0.85 to 1.2 follows throttle.
- `veh_bomber_pass` x4: four detuned engines, doppler-free swell peaking at 2 s with a filter opening toward the peak. Trigger when the aircraft is within about 300 m. `veh_water_drop_whoosh` x4: whoosh then splash-down at 0.85 s (start it about 0.85 s before the drop lands).

## People (bus `ppl`)
- Footsteps `ppl_step_<sand|grass|gravel|wood|rock|water|snow|deck|metal>_01..08`, 32 kHz, group `core`, max_dist 25, `meta.surface`. Two taps 40 to 90 ms apart (heel then softer toe). Mean centroids (Hz): wood 296, deck 556, grass 641, water 1692, metal 1748, sand 1968, rock 3157, gravel 4627, snow 5014. Choose surface from the terrain under the foot; pitch by walking speed.
- Voices (formant-filtered band-limited glottal source, no screams, no wet sounds): `ppl_breath`, `ppl_grunt_topple` x4, `ppl_shout_boat` x3 (rising f0 and F1/F2 sweep, echo), `ppl_shout_help` x3, `ppl_whistle_lifeguard` x3 (pea whistle about 2.9 kHz with 35 Hz trill, peak -14 dB so it does not jump out), `ppl_laugh_small` x3, `ppl_cough` x3, `ppl_haul_grunt` x4, `ppl_shiver` (2.4 s loop). All have 85 to 99 percent of energy in 300 to 3000 Hz (grunts and hauls 85 to 93 percent) and under 0.01 percent above 8 kHz.
- `ppl_murmur_loop_s` / `_m` (12 s, many overlapping random-pitch syllables, high-passed at 170 Hz and lowpassed at 3.3 kHz so no words form). Pick by people count in earshot (s under about 6, m above), level by count, lowpass with distance.
- Actions: `ppl_camera_shutter`, `ppl_shovel_dig`, `ppl_hammer_tap`, `ppl_stone_place`, `ppl_axe_chop`, `ppl_tree_plant_pat`, `ppl_drum_slosh`, `ppl_radio_click`, `ppl_radio_squelch`, `ppl_fishing_cast` (all x4), `ppl_binocular_click`, loops `ppl_radio_chatter_loop` (12 s) and `ppl_fishing_reel`. Hammer and shovel are the brightest (centroids about 3 kHz and 1.4 kHz).

## NPC cues (`npc_*`; musical ones are bus `ui`, non-spatial; physical ones are bus `ppl`, spatial)
D minor pentatonic (D F G A C), soft sine, triangle, marimba and bell timbres, 0.5 to 2.5 s, peak -6 dB: report_blip (A5 to D6, marimba), decoy_blip (A5 to a slightly flat C6, sine), unmask (rising arpeggio to a chord), courier_caught (falling triad), contraband_seized (low D and A chord, then G, then D), trust_up / trust_down, circle_done_fanfare, site_taken (falling), developer_arrive (two dyads plus a click), rescue_success, rescue_start_alert, threat_alert (D D A low pulses), disaster_alert (low D, G, A cluster with 5.5 Hz tremolo, sub D).
Physical: `npc_drop_thud_sand` x4, `npc_stash_cover` x4, `npc_sabotage_topple` x4, `npc_salvage_winch_loop`, `npc_salvage_sold_coin`, `npc_smuggler_arrive_low_engine` (loop with `meta.fadeInS`: fade gain in over 2.5 s as the boat approaches).

## UI, hold tools, music
- 20 UI sounds, 0.06 to 0.7 s, peak -10 dB, warm marimba or bell plus airy noise ticks, over 99.9 percent of the energy below 6 kHz. `ui_slider_tick` should be played at rate 0.8 to 1.4 across the slider range and rate-limited.
- 12 `hold_<tool>` loops (4 s, periodic, -30 LUFS, peak about -12 to -20 dB): start on press, fade on release; level may follow tool strength.
- Pads `mus_pad_dawn|day|dusk|night` (40 s stereo, -28 LUFS, night -30): detuned sines on snapped frequencies, periodic slow envelopes, periodic filtered noise, circular reverb so the tail wraps. Dawn open fifths with a brightness swell, day D major pentatonic with sparse swells, dusk sus4 with C and slow tremolo, night D2/A2 with 4 sparse long bells. Crossfade 6 to 10 s by time of day. `mus_tension_layer` (D1 pulse at 1.25 Hz plus an A/Bb/B cluster), `mus_storm_layer` (rolling toms plus drone): mix over a pad, level from threat or wind.
- Stingers `mus_sting_discovery` 3.2 s, `_success` 3.8 s, `_loss` 4.0 s, `_arrival` 3.8 s (stereo, reverb tail faded). Duck pads while one plays.

## Known weaknesses (not audible to me, so these are from analysis only)
- Nothing has been auditioned. All claims are from spectra, loop seams and levels. The voices in particular (grunt, shout, laugh, cough) are formant models and may sound synthetic or sit in the uncanny range; the shouts and whistle are the most likely to need re-tuning by ear.
- Engines are bass-weighted (centroid under 1 kHz except hover) so on phone speakers they will rely on the harmonics and exhaust pulses; add a high-shelf at runtime if too thin. Icebreaker fundamentals under 20 Hz are partly removed by the 20 Hz high-pass in `synthlib.normalize`.
- Engine layers differ in loudness only by the LUFS targets; real engines get louder with rpm, so the runtime should scale gain with throttle on top.
- Rope rattle, buoy bell and hammer/shovel are the least convincing physical models (simple grain and modal approximations).
- Pads are very quiet and low in centroid (95 to 220 Hz); on small speakers they will mostly vanish. `mus_pad_night` is nearly inaudible by design.
- Patrol mid/lo centroids are close (212 vs 243 Hz); the layers differ mainly in firing rate and brightness of the exhaust.
