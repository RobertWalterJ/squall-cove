# Ambience and weather assets (gen_ambience.py, gen_weather.py)

Render: `python render_all.py gen_ambience gen_weather` (about 90 s). Check: `python check_aw.py amb_ wx_` (centroid, band split, first/last-second RMS, L/R correlation, seam).
44 assets, 5.7 MB total (24 beds, 20 weather). All beds are 44.1 kHz stereo Vorbis q3, about -26 LUFS, seamless to the sample (decoded seam below -65 dBFS). The three weather loops are -22 to -24 LUFS.
All beds sit at the SAME loudness: the game must scale gain by state (wind speed, rain amount, distance). Suggested drivers are in each line.

How loops are built: each bed = a noise part (equal-power crossfade, every modulator exactly periodic) plus a circular part (grains, calls, whistles wrap around the loop point), then a circular 18 Hz high-pass, a 3.6 ms end ramp and a start-up compensation for synthlib.normalize's high-pass. Left and right use different noise seeds; discrete events are shared and panned.

## Sea and surf (amb, core)
- amb_sea_calm: 14 s. Pink noise, lowpass 180..1400 Hz and level follow two swell trains (7 s and 4.7 s), brown rumble, few bubbles. Centroid 640 Hz. meta swellPeriodS 7, swellWavelengthM 76. Level up with sea.amp; playbackRate 0.9..1.1 by wavelength.
- amb_sea_moderate: 10 s, period 5 s (39 m), crest hiss, light chop. Centroid 790 Hz.
- amb_sea_rough: 12 s, period 4 s (25 m), chop band 500-1200 Hz, bubbles. Centroid 1.1 kHz. Crossfade calm, moderate, rough on sea.amp (equal power between neighbours).
- amb_surf_gentle: 14 s, three breaking events (burst, roll, backwash, foam bubbles) at irregular times. Centroid 2.6 kHz. Level from shore distance (near a sloping shore only).
- amb_surf_heavy: 14 s, darker and larger, with a 130 Hz thump per break. Centroid 1.5 kHz. Crossfade gentle to heavy with shoal or wave height.

## Wind (amb, core); meta.windMs is the speed the loop represents
- amb_wind_light 3 m/s (centroid 295 Hz), amb_wind_fresh 9 m/s (460), amb_wind_gale 20 m/s (830; brown roar, 14 Hz flutter, faint low howl), amb_wind_hurricane 35 m/s (1280; stronger roar, 24 Hz flutter, howl).
  Recipe: pink noise through a lowpass whose cutoff and gain ride a periodic gust curve, plus a swept resonant band. Crossfade neighbours by wind.ms; playbackRate 0.92..1.08 and a highpass for camera height are fine. Gusts are baked in (12 s period), so keep runtime gain jitter slow.
- amb_wind_rigging: 12 s, 12 m/s. Tonal whistle with 3 harmonics gliding about 650-1300 Hz with the gusts (periodic, exact phase wrap) over a light wind. Mix in near rigging, wires, masts and cliffs; fade with distance to them.

## Rain and snow (amb, core)
- amb_rain_light: intensity 0.3. Dense click/ping grains (160/s) over filtered pink noise (700-6500 Hz). Centroid 5.0 kHz.
- amb_rain_heavy: intensity 0.9. 650 grains/s, wider bed plus 250-1400 Hz body. Centroid 4.8 kHz, 12 percent above 8 kHz (one of the brightest beds).
- amb_rain_on_water: intensity 0.6. Duller bed (250-5200 Hz) plus 230/s soft plops and bubbles. Centroid 2.1 kHz. Use when the camera is over water.
- amb_rain_on_canopy: intensity 0.55. Muffled bed (lowpass 3.2 kHz) plus 9/s large irregular drips with a body thud. Centroid 1.25 kHz. Under trees or roofs.
- Drive level from rainAmt; crossfade light and heavy by rainAmt; swap surface variant by what is under the camera.
- amb_snow_hush: 12 s, very soft lowpassed hush, rare crystal ticks, occasional faint flumps. Centroid 420 Hz. Low gain with snow cover or snowfall.

## Fire, lava, steam (amb, core)
- amb_fire_bed: 12 s. Flickering roar (brown, lowpass 350), mid body, hiss, band-limited pops and low pops at a flickering rate (10-55/s). Centroid 740 Hz. Gain by burning count; playbackRate 0.9..1.1; layer two copies at different rates for bigger fires.
- amb_lava_bubble: 12 s. Slow viscous low bubbles (60-220 Hz, about 2.4/s), brown rumble, faint sizzle. Centroid 260 Hz. Level from lava cells near the camera.
- amb_steam_hiss: 10 s. Bright broadband hiss with a swept band and slow modulation, 13 percent above 8 kHz, centroid 5.1 kHz. Where lava meets water, geysers, quench; keep at low gain.

## Life (amb, group core, lazy)
- amb_birds_day: 22 s. 24 phrases (tweets, two-note whistles, warbles, trills, cheeps), about half distant (lowpassed), bouts repeat; 97 percent of energy 1-4 kHz, nothing above 5.2 kHz. Day and fair weather; fade out above 8 m/s wind and in any rain.
- amb_gulls: 20 s. 7 call sequences; falling glissando with 7 harmonics, nasal formants near 1.5 and 2.8 kHz, near and far calls; faint wash underneath. Near coast by day. Quiet gaps are intended.
- amb_crickets_night: 16 s. Six crickets as 3-4 pulse chirp trains at 3.1-4.0 kHz, 1.7-2.7 chirps per second, occasional skipped chirps, slow level drift. Night, calm, dry, land side; playbackRate 0.9..1.1 can stand in for temperature.
- amb_forest_air: 12 s. Swaying leaf band 450-1150 Hz, rustle, low drone, leaf ticks. Centroid 1.2 kHz. Under trees in any weather.
- amb_harbour_far: 20 s. Bell buoy (4 hits, lowpassed), 4 wooden creaks, soft murmur of 60 formant syllables, water lap. Centroid 480 Hz. Scale by pier, boat and people counts.
- amb_underwater: 12 s. Brown plus pink, lowpassed about 600 Hz, slow pulsing, bubble ticks 1.6/s. Centroid 170 Hz. Replaces the other beds when the camera is below the surface.

## Weather events (wx bus, group weather, mono, peak target -3 dBFS)
- wx_thunder_near_01..04: 5.5, 6.5, 7.5, 8.5 s. 7-11 decaying pulses with fast attacks, lowpass closing from about 2 kHz to 180 Hz, sub rumble, mid tearing bursts in the first 1.5 s, long tail. Centroid 190-250 Hz. meta typicalDelayS [0.4, 3.0], delayToRumbleRatio 0.25. Start after distance/343 s, duck amb 6 dB for 1.5 s, extra lowpass with distance.
- wx_thunder_far_01..04: 6, 7, 8, 9 s. Darker (cutoff 130-650 Hz), slower attacks (0.2-0.55 s), no crack. Centroid 130-150 Hz. meta typicalDelayS [5, 14], delayToRumbleRatio 1.4. Choose near or far by distance (about 1.2 km).
- wx_lightning_crack_01..03: 1.6, 2.0, 2.4 s. Click, 30 ms bright crack, 14-25 tearing pops, short boom and rumble tail. Play at the flash, then thunder_near after the delay. Centroid 380-560 Hz.
- wx_tornado_loop: 12 s stereo loop, -22 LUFS. Brown roar with gusts, 'train' band, swirl band 350-1000 Hz, debris ticks. Centroid 550 Hz. Level and lowpass by distance to the vortex.
- wx_quake_rumble: 6 s. 33/46/58/71 Hz wobbling sines plus brown rumble with irregular shaking, rattle band, five rock cracks. Centroid 240 Hz. Global or very wide; playbackRate 0.8..1.2 by magnitude.
- wx_tsunami_rumble: 6 s. Rising roar peaking at 2.9 s then falling; 38 Hz sub, surge band 300-1000 Hz. Centroid 370 Hz. Start as the wave nears shore.
- wx_meteor_whistle: 3.2 s. Falling whistle (3.1 kHz to 500 Hz) with beating partials, following noise band, rising roar, abrupt end. Start 3.2 s before impact.
- wx_meteor_impact: 4.5 s. Boom dropping 150 to 30 Hz, noise burst, rock debris, rumble tail, soft clipped. Duck everything except wx by 8 dB, 0.4 s release.
- wx_eruption_boom: 5.5 s. Boom 85 to 28 Hz, pressure burst, gas hiss, debris. Centroid 835 Hz.
- wx_eruption_loop: 12 s stereo loop, -22 LUFS. Roar, turbulent mid band, four irregular big booms, spatter pops. Centroid 240 Hz. Level by distance and eruption rate.
- wx_landslide: 6 s. Rising rumble with closing lowpass, mid band, rock clatter thinning from 55/s to 4/s, four boulder thumps. Centroid 580 Hz.
- wx_hail: 10 s stereo loop, -24 LUFS. 70-140 small hits per second (clicks, pings, plastic modal) plus 7/s heavy stone tocks over faint noise. Centroid 2.7 kHz. Layer over rain_heavy.

## Known weaknesses (not listened to; designed from physics and checked by analysis)
- Beds share one loudness; realism depends on the game's gain and crossfade curves. The sea beds are noise swells and may sound slightly synthetic next to recordings.
- Far thunder, quake, tsunami, eruption and meteor impact are mostly below 150 Hz and will be weak on phone speakers; consider a waveshaped upper-harmonic layer or extra gain on phones.
- Lightning crack still carries a lot of low boom (centroid 380-560 Hz); the crack itself is a short transient. Decoded peaks of crack and the impacts are about -1.6 dBFS (Vorbis overshoot).
- Birds, gulls and crickets are FM/additive tones: pleasant but obviously synthetic up close. Their L/R correlation is 0.6-0.8 (events are point sources panned between channels).
- Loops are only 10-22 s, so discrete events (bell buoy, creaks, big surf waves, bird phrases) may be noticed repeating after a minute. Use playbackRate jitter or two copies at different offsets and rates.
- Rain heavy and steam are the brightest beds (12 and 13 percent above 8 kHz); lower their bus gain if harsh.
- First-second versus last-second RMS of sea, surf and gale differ by up to 8 dB: that is the wave or gust rhythm built into the loop, not a seam.
