# Squall Cove: sound requirements and design

Status: the game has no audio today. This document is the requirements list, the design, the asset list and the plan. Assets are synthesised procedurally (Python, numpy and scipy, ffmpeg for encoding) so every sound can be regenerated, tuned and versioned. The runtime is Web Audio inside `index.html`.

## 1. Requirements

### 1.1 Product
1. Sound must explain the simulation. A player who closes their eyes should hear the wind change direction and build, the sea get bigger, a boat's engine labour, a stone block land, a pane of glass break, a fire take hold, a storm approach.
2. Sound must come from the physics, not from canned triggers: mass, speed, material, temperature, depth, distance and weather decide which sound plays and how loud, bright and long it is.
3. Sound is information for the player who is a god in a sandbox: events that matter (threats, rescues, unmasked smugglers, finished circles, disasters) get audible cues that are readable but never shrill or repetitive.
4. Sound must never be required. Everything audible also has a visual or text equivalent (toast, log, People and Fleets sheets). Provide a sound-captions option later that lists the loudest nearby sounds as icons.
5. Dyslexia-friendly: audio cues should reinforce text, and long text-heavy sheets should be readable aloud later (out of scope here, noted).
6. No timers or countdown ticks as audio. No sounds that punish.
7. Cartoon violence only: gun and impact sounds are punchy and non-gory. No screams, no wet sounds. People react with short neutral vocal sounds (a grunt when toppled, a shout to call a boat).

### 1.2 Technical
1. Desktop and phone. Phones get fewer voices (14), mono panning instead of HRTF, shorter reverb, no convolution on the master bus.
2. Browser autoplay rules: audio starts on the first tap or key; a visible Sound toggle and per-bus volume sliders live in the Menu.
3. Size budget: initial download under 4 MB (core loops and UI), the rest streamed lazily by category and cached by the service worker. Total under 18 MB.
4. Formats: Ogg Vorbis (quality 3 to 5). Mono for point sources and one-shots, stereo for ambience beds. 44.1 kHz for beds and engines, 32 kHz for small one-shots.
5. Voice limit 24 on desktop, 14 on phones, with priority stealing (loudest, nearest, most important wins).
6. Loops must be seamless: crossfaded and verified (seam discontinuity below -50 dBFS).
7. Deterministic renders (seeded) so assets are reproducible and diffable.
8. Respect the shared-origin PWA rules: asset cache name prefixed `squall-cove-`, never touch other apps' caches.
9. Frame cost: audio parameter updates at 10 Hz for beds, per event for one-shots, never per physics step.

### 1.3 Quality
1. Loudness: ambience beds around -26 LUFS (short-term), engines -24, impacts peak -3 dBFS, UI -20 LUFS, master limiter at -1 dBFS.
2. Every one-shot family has at least 4 variants (8 for frequent sounds like footsteps and splashes), randomised pitch within +-6 percent and gain within +-1.5 dB at play time.
3. No two identical samples back to back.
4. Distance model: inverse distance rolloff with a lowpass that closes with distance (air absorption) and an extra lowpass when something is behind terrain (line of sight) or the listener is underwater.
5. Doppler is not used.

## 2. Mix design

### 2.1 Buses
master (limiter) with these children:
- `amb` ambience beds: sea, surf, wind, rain, fire bed, lava bed, birds, insects, forest, distant harbour
- `wx` weather events: thunder, lightning crack, tornado, hurricane, quake, tsunami, meteor
- `water` splashes, wake, pours, bubbles, swash
- `mat` material impacts and destruction: wood, stone, metal, glass, ice, sand, earth, rock, rubble, scrap
- `veh` boats, aircraft, helicopters, horns, bells, sirens, weapons
- `ppl` people: footsteps, voices (non-verbal), work sounds, camera shutter, whistle, radio
- `ui` taps, menus, toasts, stingers, hold-tool loops
- `mus` optional score: pad and stingers (default low, user can switch off)

### 2.2 Dynamics
- Sidechain ducking: thunder and strikes duck `amb` by 6 dB for 1.5 s; `ui` stingers duck `mus`; explosions duck everything but `wx` by 8 dB with a 0.4 s release.
- Listener: the camera. Boats under the helm camera use an interior mix (engine louder, wind and water lower).
- Distance cull: no voice starts beyond 160 m (large map 240 m) unless it is an event of weight greater than 8 (explosions, thunder, volcano).

### 2.3 State-driven beds (updated at 10 Hz)
| Bed | Driver | Behaviour |
|---|---|---|
| sea | `sea.amp`, swell wavelength | level up with amplitude, pitch and swash rhythm follow wavelength (longer swell, slower, deeper) |
| surf | distance to shore along camera, `shoal` | louder near a sloping shore, rhythm from the swell period |
| wind | `wind.ms`, gusts, camera height | level and highpass by speed, whistle band near rigging or cliffs, gust modulation |
| rain | `wx.rainAmt`, surface under camera | broadband plus drop texture; on water, on land, under a canopy (lowpass) |
| fire | number and distance of burning trees, burning blocks | crackle density and low roar |
| lava | `lavaOn` cells near camera | slow bubbling and hiss, steam hiss where lava meets water |
| birds, insects | time of day, weather | birds by day and in fair weather, crickets at night, silence in a gale |
| harbour | pier, boats, people count | distant bell buoy, creaks, murmur |

### 2.4 Event sounds
Every event carries `{kind, x, y, z, mass, speed, material, wet, weight}`. The resolver picks a family by material and size, a variant at random, a rate from mass, a lowpass from distance and wetness.

## 3. Sound inventory (what must exist)

### 3.1 Ambience and weather (loops, stereo)
amb_sea_calm, amb_sea_moderate, amb_sea_rough (crossfaded by state), amb_surf_gentle, amb_surf_heavy, amb_wind_light, amb_wind_fresh, amb_wind_gale, amb_wind_hurricane, amb_wind_rigging (tonal whistle), amb_rain_light, amb_rain_heavy, amb_rain_on_water, amb_rain_on_canopy, amb_snow_hush, amb_fire_bed, amb_lava_bubble, amb_steam_hiss, amb_birds_day, amb_gulls, amb_crickets_night, amb_forest_air, amb_harbour_far, amb_underwater, amb_cave_drip (optional).

Events: wx_thunder_near_01..04, wx_thunder_far_01..04, wx_lightning_crack_01..03, wx_tornado_loop, wx_quake_rumble, wx_tsunami_rumble, wx_meteor_whistle, wx_meteor_impact, wx_eruption_boom, wx_eruption_loop, wx_landslide, wx_hail.

### 3.2 Water (one-shots and loops, mono)
water_splash_xs/s/m/l/xl (6 variants each), water_rock_in, water_object_in_small, water_object_in_large, water_drip, water_bubbles, water_swash, water_pour_loop, water_wake_loop (by speed), water_hull_slap_01..06, water_boil_hiss, water_quench_hiss, water_flood_trickle, water_ripple_tick.

### 3.3 Materials (families x 6 variants; sizes s/m/l where it matters)
- wood: knock, thump, creak, crack, splinter, snap, plank_drop, barrel_knock, crate_slam, burn_crackle, collapse
- stone: tock (block placed), scrape, crumble, shatter, rock_roll, rubble_settle, quarry_chink
- metal: clang (small, large), scrape, bend_groan, scrap_clatter, ingot_clunk, container_boom, chain_rattle, anchor_drop, sizzle_melt
- glass: ping, crack, shatter_large, shatter_small, shards_settle
- ice: crack, crunch, tinkle, groan, creak (sea ice), break_large, melt_drip
- sand and earth: pour_loop (granular), slide_loop, thud_soft, dig, slump
- plastic and rubber: drum_hollow, ball_bounce
- fire: ignite_whoomp, crackle_loop_s/m/l, extinguish_hiss, ember_pop, tree_burn_roar, tree_fall
- electricity: arc_zap, hum_loop, strike_crack, spark_crackle, shock_pop

### 3.4 Vehicles
- boats: sail_luff, sail_flap, sheet_creak, rope_rattle, hull_creak_01..04; engines (loops with RPM layers low/mid/high for each): dinghy_none, tug_diesel, lifeboat_diesel_fast, patrol_twin_diesel, hovercraft_fan, icebreaker_heavy_diesel, ship_prop_wash; horn_short, horn_long, foghorn, ship_bell, buoy_bell (wave-driven), siren_wail, siren_yelp, deck_gun_fire, deck_gun_shell_fly, mg_burst, hull_hit_light, hull_hit_heavy, hull_breach, sinking_gurgle, fire_on_boat_loop, fire_hose_spray_loop, winch_loop, anchor_chain, ice_crunch_hull
- aircraft: heli_rotor_loop (blade pass rate), heli_whine, heli_wash_loop, prop_engine_loop (small), prop_engine_big, bomber_pass, water_drop_whoosh, siren_distant

### 3.5 People
footsteps (sand, grass, gravel, wood pier, rock, shallow water, snow, deck, metal) x 8 variants; voice (neutral, non-verbal): breath, grunt_topple, shout_call_boat, shout_help, whistle_lifeguard, hail_horn_voice, laugh_small, murmur_crowd_loop (small/medium), cough, shiver; actions: camera_shutter, shovel_dig, hammer_tap, stone_place, axe_chop, tree_plant_pat, haul_grunt, drum_carry_slosh, radio_click, radio_squelch, radio_chatter_loop, binocular_click, fishing_cast, fishing_reel.

### 3.6 NPC engine cues
informant_report_blip, decoy_tip_blip (slightly different), unmask_sting, courier_caught_sting, contraband_seized_sting, trust_up, trust_down, drop_thud_sand, stash_cover, salvage_winch_loop, salvage_sold_coin, circle_done_fanfare_short, sabotage_topple, site_taken_sting, developer_arrive, smuggler_arrive_low_engine, rescue_success, rescue_start_alert, threat_alert, disaster_alert.

### 3.6a Terrain and materials in the sandbox
grain_sand_pour (granular loop with density control), grain_earth_pour, grain_rock_pour (clacks), grain_metal_pour (tinkle), pile_slump_small, pile_slump_large, lava_flow_loop, lava_crust_crack, lava_hit_water_hiss, glass_form_ping, furnace_roar_loop, heat_hold_hiss_loop, cold_hold_wind_loop, seed_scatter_patter, sprout_chime, quake_crack, rubble_rain.

### 3.7 UI
ui_tap, ui_select, ui_deselect, ui_place, ui_erase, ui_error, ui_open, ui_close, ui_tab, ui_toggle_on, ui_toggle_off, ui_slider_tick, ui_toast_info, ui_toast_good, ui_toast_warn, ui_toast_alert, ui_log_open, ui_try_done, ui_new_world, ui_undo, hold_tool loops (heat, cold, water, lightning_charge, electricity, fire, lava, sand, earth, rock, metal, seed).

### 3.8 Music (optional layer, default low)
mus_pad_dawn, mus_pad_day, mus_pad_dusk, mus_pad_night (60 to 90 s loops, tonal, slow), mus_tension_layer, mus_storm_layer, stingers: mus_sting_discovery, mus_sting_success, mus_sting_loss, mus_sting_arrival.

## 4. Runtime design (Web Audio)

- `Sound` object: `init()` on first gesture; `buses`; `loops` (named, with `setLevel`, `setRate`, `setFilter`); `play(id, opts)`; `voices` pool with stealing; `setListener(camera)` each frame; `tick(dt)` at 10 Hz computing bed levels from game state; `unlock` for iOS.
- Loading: manifest.json lists every asset with `{id, file, bus, loop, gain, rate:[lo,hi], variants, maxDist, weight, lazy}`. Core assets load at start; lazy groups load when first needed (vehicles when a boat is placed, aircraft when a heli is called, etc.). Fetch with the service worker's runtime cache.
- Spatialisation: `PannerNode` equalpower on phones, HRTF on desktop; distance model inverse with refDistance by weight; extra BiquadFilter lowpass driven by distance and occlusion.
- Variation: variant pick avoids repeat, random rate within the manifest range, plus gain jitter.
- Engines: crossfaded layers by throttle (low, mid, high) and rate by RPM, panned at the boat; the helm camera uses an interior filter.
- Hooks (events to wire): `splash`, `ripple`, `onImpact`, `fracture`, `depositGrain`, `spawn`, `igniteTree`, `strikeAt`, `shock`, `placeBlock`, `quarry`, `stash`, `unmask`, `observe` reports, `toast` category, tool holds, `startVolcano`, `quake`, meteor, tsunami, UI taps, boat horns, deck guns, heli and bomber updates, footsteps (gait events), ferry, rescue.
- Settings: master and per-bus sliders, mute, music toggle, `prefs.sound` saved with prefs.
- Debug: `?audio=debug` shows voice count and the nearest sounds.

## 5. Production design (synthesis)

Toolkit `sound/synthlib.py` (numpy and scipy):
- noise (white, pink, brown, blue), shaped by Butterworth and resonant filters, time-varying cutoff via block processing
- modal synthesis for struck objects: lists of (frequency ratio, decay, amplitude) per material (wood, stone, steel, glass, ice, ceramic, hollow barrel), excited by short noise bursts, with material-specific damping and inharmonicity
- granular synthesis for sand, gravel, rubble, rain, fire and applause-like textures: grains of filtered noise or impulse responses scattered by a density function
- FM and additive for engines: firing frequency from RPM and cylinders, harmonic stack, exhaust pulses, turbo whine, noise bed; layers rendered at three RPMs
- wave synthesis: swash envelopes with bubble clouds (random sinusoid chirps) for splashes and surf
- wind: broadband turbulence shaped by moving resonators, gust envelopes, whistle partials
- thunder: low-frequency noise bursts with branching reflections, long exponential tail, multiple pulses
- voices: formant filtered pulse and noise for non-verbal sounds (breath, grunt, shout, murmur)
- reverb: synthetic impulse responses (cove, forest, hull interior, room) via filtered decaying noise, applied offline to some assets and at runtime to a send bus
- loop making: render long, equal-power crossfade the tail into the head, verify seam
- mastering: peak and LUFS-style loudness normalisation per category, high-pass at 20 Hz, optional soft clip
- encode: ffmpeg libvorbis, mono or stereo as listed

Modules (one per family, each writes its assets and a manifest fragment): `gen_ambience.py`, `gen_weather.py`, `gen_water.py`, `gen_materials.py`, `gen_fire_electric.py`, `gen_vehicles.py`, `gen_people.py`, `gen_ui_music.py`. `render_all.py` runs them, merges the manifest, then `analyze.py` produces the QA report.

## 6. QA

Automated: file exists and decodes; duration within spec; peak below -1 dBFS; RMS and approximate LUFS inside the category window; no DC offset above 0.001; no clipping; loop seam below -50 dBFS; spectral centroid and bandwidth recorded for regression; variant diversity (cross-correlation below 0.5 within a family). Runtime: voice count caps, no overlap storms (rate-limit per family), memory cap for decoded buffers (decode lazily, drop buffers after 3 minutes unused for rare sounds).

Human: a listening checklist is written to `sound/LISTENING.md` (what to listen for in each scene). The author should play the Large map in each wind level, watch for repetition, and report anything harsh, thin or wrong.

## 7. Phasing
1. Toolkit, manifest, QA and the core set: ambience beds, water, material impacts, fire, UI, weather. Engine core and hooks. (this pass)
2. Vehicles, aircraft, people, NPC cues, hold tools, music.
3. Refinement from listening notes, occlusion and reverb sends, captions, per-asset tuning, mobile profiling.
