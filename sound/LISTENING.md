# Listening checklist (the sounds were designed and measured, not heard)

I could not listen to any of these. They are built from physical models and checked by numbers (levels, spectra, loop seams, variant differences). Please play the Large map on desktop with headphones, then tell me what is wrong. Menu > Sandbox settings has Sound, Music and Cove life. Press any key or tap once to start audio.

## Scenes to try, and what to listen for

1. **Calm cove (Light wind, Sky > Day).** A quiet sea bed, a few gulls and birds, faint harbour sounds near the pier. Nothing should pump, click or repeat obviously within a minute. Gulls and birds should not be shrill.
2. **Raise the wind step by step to Gale.** The wind should rise and darken, the sea bed should become rougher and louder, surf should grow on the beaches, rigging whistles should appear on boats. The change should be smooth, no jumps between layers.
3. **Rain (Sky > Rain).** Light then heavy, different on water and on land. Not hissy or painful.
4. **Thunder (let a storm build or strike by hand).** Crack first, then a rumble that arrives later when the strike is far. Should not hurt on laptop speakers; the far thunder is deep and may be weak on small speakers (tell me).
5. **Splashes.** Drop cargo of different sizes in the sea: a ball, a crate, a rock, a container. Bigger and heavier should be deeper and longer, not just louder.
6. **Materials.** Drop a stone block, a glass pane (from high), a crate (from high), an ice block; build a stack and let it crush. Wood should knock, stone tock, glass ring then shatter into tinkling, ice crack and crunch, metal clang. Listen for any that sounds like another material.
7. **Fire.** Heat or fire on trees: ignite whoomp, crackle that grows with the number of burning trees, hiss when put out.
8. **Poured materials.** Hold sand, earth, rock, scrap metal: each should have its own granular texture.
9. **Boats.** A tug, the lifeboat, the patrol boat, an icebreaker: engines should be believable at idle and at full throttle and sound different from one another. Horns, bells, deck guns (punchy, not harsh).
10. **People and work.** Footsteps on sand, grass, pier, shallow water; builders placing stone; the camera shutter; radio blips when an informant reports.
11. **Vehicles.** Ambulance and fire truck sirens, the forklift and trucks (their engines reuse the boat engine layers at different speeds, so tell me if that sounds wrong).
12. **UI.** Taps, toasts, menu open and close: soft and pleasant, never annoying after ten minutes.
13. **Music (Menu > Music).** Slow pads by time of day, a tension layer when a threat is near and a storm layer in storms. Should be unobtrusive.

## Weapons and battle pack (added Oct 2026; `NOTES-weapons.md` has the stem list and how to trigger each)
14. **Gunshots.** Pistol, SMG, rifle, shotgun and sniper (three variants each), their distant versions and two outdoor echo tails. They should be punchy, never harsh or clipping; the sniper has a long tail; the far versions should be faint cracks with echoes. Tell me if the rifle or sniper sounds boomy instead of cracking, or small on laptop speakers.
15. **Handling and shells.** Magazine out and in, bolt, shotgun pump, dry click, draw, knife swish; brass casings on concrete, dirt and metal. Clear but quiet.
16. **Bullet passes and impacts.** Whiz (crack plus whip), ricochet (sharp tick then a falling "pee-yow"), impacts on dirt, concrete, wood, metal, glass, sand and water. The body hit is a cartoon thump with a short "oof" breath; the knock-out is a longer thump, a wobble and a star tinkle. No gore or screams are expected; tell me if the oof or the hurt breath sounds creepy.
17. **Footsteps and foley.** Nine surfaces with six walking variants each, hard and soft runs, jump and landings, cloth and gear rustle, pickup, crate drop, swim stroke, hurt breath, heal chime. Listen for any surface that sounds like another (mud, gravel and water are my weakest).
18. **Battle UI stings.** Flag capture (rising brass), flag lost (falling), tickets low (tense pulse, must not feel like a timer), respawn, victory and defeat (4 s each), hitmarker tick, kill double tick. Short, readable, and not annoying after many repeats.
19. **Battle ambience beds.** `amb_battle_distant` (thin far-off gunfire and booms with real gaps), `amb_farm`, `amb_town` (with a distant dog), `amb_quay`. Each loops in about 16 s; tell me if a loop point or a repeated event is noticeable.

## Things I expect to need tuning
- Overall balance between beds, effects and music.
- Very low sounds (far thunder, quakes) on small speakers.
- Birds, gulls and crickets sound synthetic up close.
- Fire crackle sizes differ mostly in density.
- Car engines sharing boat engine layers.
- Repetition in 10 to 20 second loops after a minute or two.
- Gunshots are low-heavy on small speakers; the dog bark, the "oof" and the brass stings are synthetic approximations.

## How to report
Say the scene number and what you heard ("scene 6, glass sounds like a bell and never shatters"). I will adjust the generator in `sound/` and re-render everything in about ten minutes.
