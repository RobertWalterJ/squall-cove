# Water, materials, fire and electricity assets (gen_water, gen_materials, gen_fire_electric)

Total 352 files, about 5.6 MB (water 72 files 1.2 MB, materials 240 files 3.6 MB, fire/electric 40 files 0.8 MB). All mono, 44.1 kHz, Vorbis q4, seeded (CRC32 of id plus variant index). Helpers live in `gen_util.py`; `wm_stats.py [prefix...]` prints per-family duration, centroid and peak.
Bus: water assets use `water`, everything else here uses `mat`. `group` is `core` for splashes, wood/stone/glass/ice/metal impacts, sand/earth pours and fire crackle; the rest are `lazy`. Every manifest entry has a `meta` dict (sizeClass, massKg, material, impactSpeed, drive, note).
Runtime rule for all one-shots: pick variant at random without repeat, gain from speed (and mass), lowpass from distance/wetness, rate from mass (heavier = lower rate, within the manifest rate range).

## Water (peak dBFS in brackets)
- water_splash_xs/s/m/l/xl_01..06 (-12/-9/-6/-4.5/-3): choose class by object mass at entry (meta.massKg: xs 0.005-0.05, s 0.05-1, m 1-20, l 20-300, xl 300-5000 kg); entry speed scales gain and lowpass. Recipe: noise burst + bubble cloud (rising chirps; size lowers pitch and lengthens bubbles) + low thump sweep; l and xl add a delayed column collapse (0.3 s / 0.55 s) and xl a rolling fall-back plus spray hiss. Measured centroid 6100/3270/1540/680/330 Hz, duration 0.45/0.8/1.4/2.4/4.0 s.
- water_rock_in (4), water_object_in_small (4, floating light things), water_object_in_large (4, crates/barrels/blocks): dense object plop with thud / bright small splash / heavy slosh.
- water_drip (4), water_bubbles (4, rate by volume), water_ripple_tick (4, rain/ripple events), water_swash (4, 2.4 s run-up and backwash; gain by wave height), water_hull_slap (6, hull-and-wave, wave height at hull).
- water_pour_loop (gain by flow rate), water_wake_loop (stereo, drive by hull speed 0..12 m/s: gain, lowpass opens, rate 0.85..1.3), water_boil_hiss (gain by hot-cell count), water_flood_trickle (gain by flowing cells). Loops 5 s, -26/-28 LUFS.
- water_quench_hiss (4, 1.8 s): hot object in water; hiss rises over about 0.5 s, then decays; pair with a splash.

## Wood (mat_wood_*)
knock (6, 0.4 s), thump (6, heavy, low), creak (6, lazy, stick-slip noise through gliding resonators, for loaded structures), crack (6), splinter (6, dense ticks), snap (6), plank_drop (6, bounces), barrel_knock (6, hollow), crate_slam (6, thump + board rattle), collapse (4, 3.2 s, many hits with decaying density, weight 8).
Pick by mass (pitch/size class), speed (gain); `crack`/`collapse` for fracture events.

## Stone and terrain
mat_stone_tock (6, short dense block-on-stone with grit; the Place tool), scrape (4), crumble (4), shatter (4), rock_roll (loop, gain/rate by boulder speed), rubble_settle (4, aftermath), quarry_chink (4, pick on rock, lazy).
grain_sand_pour / grain_earth_pour / grain_rock_pour / grain_metal_pour (loops, 5 s): drive gain by flow rate and (sand) lowpass by fall height; rock has modal clacks, metal sparse pings and tinkles.
pile_slump_small (4, 1.3 s), pile_slump_large (4, 3.2 s): by pile volume; material picks a lowpass at play time. mat_slide_loop (gain, lowpass, rate by slide speed), mat_thud_soft (6, sand/earth/body landing), mat_dig (4).

## Metal
clang_s (6, steel, bright, 1.3 s), clang_l (6, 3 s, low, thump), scrape (4), bend_groan (4, gliding resonators), scrap_clatter (4), ingot_clunk (4, short iron), container_boom (4, 3.4 s, weight 8), chain_rattle (loop; rate by chain speed), anchor_drop (4, 2.8 s: chain runs out then a heavy hit at about 1.2 s; play a water splash then if over water), sizzle_melt (4).

## Glass and ice
glass: ping (6), crack (6), shatter_large (4, 3 s), shatter_small (4), shards_settle (4). Centroids 4.6-7.9 kHz (highest of any family).
ice: crack (6, rising chirp), crunch (6), tinkle (4), groan (4), creak (4, 3.2-5.5 s, long glide of narrow resonators for sea ice), break_large (4, boom + crunch + churn), melt_drip (4, rate by temperature).

## Plastic, lava, misc
mat_drum_hollow (4), mat_ball_bounce (4, whole bounce sequence), lava_flow_loop (low rumble + slow bubble pops; gain by lava cells near camera), lava_crust_crack (4), lava_hit_water_hiss (4, steam burst, weight 5), glass_form_ping (4), furnace_roar_loop, seed_scatter_patter (4), sprout_chime (4, soft pentatonic), quake_crack (4, weight 8, max_dist 240), rubble_rain (loop; gain by falling debris count). Note: unprefixed ids follow the design doc (3.6a); slide_loop, thud_soft, dig, drum_hollow and ball_bounce carry the `mat_` prefix.

## Fire
fire_ignite_whoomp (4, low thump + rising roar), fire_crackle_loop_s/m/l (6 s; pops with a low roar; pick s/m/l by burning cell/tree count; LUFS -29/-27/-25), fire_extinguish_hiss (4), fire_ember_pop (6, stochastic near fires, -15 dB), fire_tree_burn_roar (loop, -24 LUFS), fire_tree_fall (4, 3 s: creak, crack, whoosh, thud at about 1.9 s).

## Electricity and tool holds
elec_arc_zap (6, swept buzz + noise), elec_hum_loop (4 s, 60 Hz and harmonics with slow modulation and a touch of buzz; -32 LUFS, deliberately quiet), elec_strike_crack (4, weight 8, max_dist 240; duck `amb` 6 dB), elec_spark_crackle (loop), elec_shock_pop (4, short), heat_hold_hiss_loop and cold_hold_wind_loop (lazy, group `tools`).
Note: another module (gen_ui_music) also writes `hold_*` loops; the ids here are the heat/cold variants named in the doc section 3.6a.

## QA state
After two full render and analyze cycles none of these assets appear in the report problem list (no clipping, DC, seams, short loops, or similar variants). Fixes made: loops now go through `gen_util.loop_clean` (circular removal of below-28 Hz energy, then 3 ms edge fades), because `synthlib.normalize()` applies a 20 Hz high-pass with a zero-state start that otherwise leaves a step at the loop seam on low-frequency material and the seam metric on clicky material. Other workers' loops (veh_, hold_, mus_, ppl_shiver) still show seams in the report for that reason; calling `gen_util.loop_clean(make_loop(...))` before `save()` fixes them without touching synthlib.

## Known weaknesses
- Nothing was auditioned. Balances come from physical reasoning and measured centroid/duration only.
- Water bubbles are synthetic chirps and read as cartoonish at the quietest settings; xs/s splashes are the most convincing, xl depends on its fall-back roll.
- lava_hit_water_hiss (centroid 7.6 kHz), fire_extinguish_hiss (4.4 kHz), water_quench_hiss (5.9 kHz) and elec_arc_zap are bright; watch for harshness and lower with the runtime lowpass if needed.
- fire_crackle s/m/l differ mainly in density and gain, not timbre (centroids 0.8-1.1 kHz).
- Granular loops (sand, metal pour, sparks) are statistically stationary; fine for continuous use but repetition of the 5 s cycle may be audible when solo.
- pile_slump small and large differ mostly in duration and low end; wood collapse, stone shatter and glass shatter share a similar event structure (burst, pitched hits, decaying scatter).
- Ice groan/creak use gliding band-passes; may sound whistle-like rather than ice-like.
- Multi-hit assets (plank_drop, ball_bounce, anchor_drop) bake in timing; trigger once per event.
