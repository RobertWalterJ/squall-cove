# Squall Cove gameplay plan: one living world (written 2026-10-05)

Owner feedback: it is not yet playable the way they hoped. They want to chuck stuff down and have it merge into the landscape, shift when the landscape changes, and have heat, cold, wind and water make other things happen. They also want new maps and a seed, a bigger play space, a better view, enemies that ships fire on, and people with their own jobs.

Method: I read CLAUDE.md, PLAN.md, IDEAS.md, AUDIT-2026-10.md and the simulation code in index.html (line numbers are for the current 4733-line file), and ran web searches on how comparable games do it. I did not run the game for this document. Search snippets were used, not full articles, so the research notes are directional, not a close reading. Items marked (not fetched) come from general knowledge and are not backed by a source here.

No em dashes, no timers by default, phone first (per the standing rules).

---

## 1. Diagnosis in one paragraph

The game has many good separate simulations (water layer `WD`, lava `LV/LT`, a 64 by 64 air grid `CT/CH/CC/CW`, snow and ice, sand/earth flags, trees that burn) but each one reads the ground height and little else. There is **no shared material field**. The ground is one height number per cell plus four flag bytes in `matData` (R glass, G sand, B molten, A earth, line 545). Rock, soil, snow, water, lava and ice do not know about each other, so nothing you drop "becomes part of" the landscape: sand only slumps if it was flagged sand (stepSand, 3941), plain painted land never slumps, ground has no temperature of its own, water carries no sediment, and nothing grows or dies on a schedule driven by wetness. The cure is a small set of per-cell fields (ground temperature, soil moisture, a material id, sediment) and a reaction table that every existing system writes to, as Noita and The Powder Toy do. It is mostly new loops over arrays you already have, not new rendering.

---

## 2. Research findings (with sources)

**Noita and falling-sand games.** Every cell has a material; gases, liquids and powders each have a small move rule (gas: try up, then sideways), and reactions are table lookups on neighbours. Slow reactions are what make worlds feel alive: grass creeping over soil, moss on rock, water freezing, snow melting, corpses decomposing. Lesson for us: a **reaction table keyed by (material, neighbour or heat state)** plus a few slow "background" reactions (grow, wet, dry, freeze, melt). Sources: [Noita wiki, Falling Sand Game](https://noita.wiki.gg/wiki/Falling_Sand_Game), [80.lv, Noita a game based on falling sand](https://80.lv/articles/noita-a-game-based-on-falling-sand-simulation), [Wikipedia, Falling-sand game](https://en.wikipedia.org/wiki/Falling-sand_game).

**The Powder Toy.** Each element has a heat-conduction value (0 to 255) and `LowTemperature` / `HighTemperature` thresholds that transform it into another element (ice melts to water at 0 C, and so on), plus pressure thresholds. That is the whole thermal model: a temperature per particle, conduction to neighbours scaled by a per-material constant, and phase changes by threshold. Lesson: **one temperature field for the ground with per-material conductivity and transition thresholds** gives melt, boil, freeze, lava solidifying and glass for free, and it is cheap on a grid. Sources: [Powder Toy wiki, element properties](https://powdertoy.co.uk/Wiki/W/Weight.html), [Powder Toy forum, Element V3](https://powdertoy.co.uk/Discussions/Thread/View.html?PageNum=0&Thread=19765).

**Dwarf Fortress.** Temperature is tracked per tile and per item; magma sits near 1100 C and heats adjacent tiles; magma meeting water makes obsidian plus a lot of steam; materials burn, melt or evaporate at set points. Lesson: the **lava + water = new rock + steam** rule is a fixed, well-loved interaction, and steam should be a real vapour source, not only a puff. Sources: [DF wiki, Magma](https://dwarffortresswiki.org/index.php/Magma), [DF wiki, Temperature](https://dwarffortresswiki.org/index.php/Temperature), [DF wiki, v0.31 Obsidian](https://dwarffortresswiki.org/index.php/v0.31:Obsidian).

**From Dust (the closest ancestor).** One dedicated simulation of terrain, water, vegetation and their interactions. Water runs downhill, carves paths and deposits soil as deltas; vegetation resists erosion; solidified lava makes barriers; lava touching a forest starts a fire that spreads until it reaches a river. Lesson: the fun is **pushing materials against each other and watching consequences**: plant to hold the shore, wall off lava with water, redirect a river. Sources: [Wikipedia, From Dust](https://en.wikipedia.org/wiki/From_Dust), [Not Indie Time: From Dust](https://waltoriouswritesaboutgames.com/2012/01/31/not-indie-time-from-dust/).

**Sandspiel.** CPU particle grid plus a GPU fluid solver for wind, with data passed both ways so wind moves particles and particles disturb wind. Lesson: our 64 grid wind (`computeWinds`, 4179) is already the right shape; the missing half is **wind carrying sand, snow, ash and smoke, and terrain bending the wind**. Sources: [Making Sandspiel](https://maxbittker.com/making-sandspiel/), [sandspiel README](https://github.com/MaxBittker/sandspiel/blob/master/README.md).

**Erosion and sediment.** Standard real-time recipe on a height grid: per cell keep terrain height, water depth, suspended sediment, outflow and velocity (virtual pipe model); water picks up sediment by slope times speed and deposits where it slows; thermal erosion relaxes slopes past a talus angle, with harder rock moving less. Lesson: our `stepLake` already moves water over the grid, so adding a **sediment field and a talus pass** is a modest extension, not a new engine. Sources: [Fast hydraulic and thermal erosion on GPU (Jako)](https://old.cescg.org/CESCG-2011/papers/TUBudapest-Jako-Balazs.pdf), [Daniel Gray, erosion simulation](https://www.danbgray.com/blog/Coding/The_3D_Background/Erosion_Simulation), [terrain-erosion-3-ways](https://github.com/dandrino/terrain-erosion-3-ways).

**Procedural islands and seeds.** Common recipe: fractal noise, an island mask (radial or noise-warped falloff) subtracted from the height, domain warping for coast character, then erosion to remove the "noise look". Red Blob's mapgen2 builds volcanic-style islands with moisture and biomes from the height field. Islanders uses a fresh generated island each run and a score loop to carry replayability while keeping mechanics simple. Sources: [Red Blob Games, mapgen2](https://www.redblobgames.com/maps/mapgen2/), [Here Dragons Abound, Making Islands](https://heredragonsabound.blogspot.com/2016/10/making-islands.html), [Travall, island noise functions](https://medium.com/@travall/procedural-2d-island-generation-noise-functions-13976bddeaf9), [Islanders, Wikipedia](https://en.wikipedia.org/wiki/Islanders_(video_game)), [Jonas Tyroller, Islanders](https://jonastyroller.myportfolio.com/islanders).

**Not fetched (general knowledge, treat as ideas):** Townscaper (gentle, no fail state, strong "toy" feel, tap to place and the system makes it look right); Cities Skylines and Banished share map seeds as short strings; Terraria and Minecraft fluids use a per-cell water level that spreads and settles (a cheap cellular rule, and lava plus water makes obsidian in Minecraft too); Black and White uses creatures that learn from being rewarded, which maps to our autonomous people; Universe Sandbox is a "what if" sandbox where editing a parameter and watching the result is the whole appeal; Kerbal and Poly Bridge have optional challenges layered on a physics toy.

**What makes sandboxes sticky (synthesis).** (1) Few materials, many interactions; (2) slow background processes so the world changes while you watch; (3) every tool also works as a weapon against a different tool; (4) a seed or a share code so a good result can be repeated; (5) optional goals that ask for a specific interaction ("stop the lava with water", "hold the shore through a storm") instead of a timer.

---

## 3. Code audit: interaction matrix

Legend: YES = exists, PART = partly, NO = missing. Lines are index.html.

| Interaction | Status | Where / what is there | What is missing |
|---|---|---|---|
| Dropped sand slumps to an angle | YES | `stepSand` 3941, repose 0.7 sand, 1.05 earth, flags in `matData` G/A | Only for flagged cells. Raise/Lower/Flatten land edits do not set a material, so unflagged ground never slumps |
| Earth/sand pile merges into landscape | PART | `addSand` 3932 raises `HGT` and flags | No blending with the underlying colour/soil, no distinction between "bare earth" and "bedrock", pile stays pale sand or flat earth look |
| Slump when terrain under it changes | NO | `brush` 1376 edits `HGT`, calls `commitLand` | Sand box (`sbx`) is not re-armed when you dig under an old pile, so a undermined heap stays hanging until something else touches it |
| Trees and rocks ride terrain changes | YES (visual) | `commitLand` ~1396 repositions instances to `heightAt` | Trees are never buried, drowned, or uprooted by a slide, flood or lava. No regrow: `hideTree` 4605 is permanent |
| Props and cargo follow terrain | PART | props follow (1405); physics heightfield rebuilt at 2 m (1399); bodies woken | Crates do not slide down a slope that slumps; no sinking into soft sand or mud |
| Boats ride terrain changes | YES | floating on `heightAt`/lake via `makeFloater` 1011 | Grounding on rising sand is basic; no wake or silt |
| Heat conducts through ground | NO | Ground has no temperature. `MH` 3927 exists only on sand cells (`heatGround` 3954) | A ground temperature field and conduction. Heat only reaches the 4 m air grid (`CHT` 3849) |
| Melts snow and ice | PART | `stepIce` 4080 melts by air temperature `CT` | No direct melt next to lava/furnace/fire; no meltwater into `WD`; snow does not insulate |
| Makes lava | PART | vents, volcano, meteor, "Lava pour" (`stepLava` 3778, `placeLavaThing` 4580) | Cannot melt ordinary rock or earth with sustained heat; only sand melts (to glass). No magma from deep heat |
| Lava + water = steam + rock | PART | 3803 to 3807: cools, puffs smoke, solidifies (`HGT += v*0.75`, ash) | Steam is only a puff; it does not raise `CH` humidity, so no steam-to-cloud-to-rain. No obsidian/pillow-lava distinction, no heating of the water |
| Lava ignites trees | YES | 4619 | Does not ignite grass/ground; fire does not spread over land except tree to tree within 6.5 m (4615) |
| Fire heats air, makes wind | NO | Fire is visual plus tree state | Burning trees and boats should add `CHT`, which would feed the thermal wind and convection already built |
| Evaporation | YES | `stepClimate` 3862 from sea and `WD` lakes | Not from wet soil; no cooling of the water; no salt/steam |
| Rain loop (evap, cloud, rain, runoff) | YES | 3880 to 3889, `stepLake` rain term | Rain never soaks in. `WD` just runs downhill and vanishes at the sea or decays at 0.00005 per second. No groundwater, springs from wet ground, or soil wetness |
| Wind from heating | YES | `computeWinds` 4179, `windAt` 4190, sea breeze, convection `CUP` | Terrain does not deflect or channel wind (no orographic lift, no valley wind); wind does not move sand, snow, ash or smoke |
| Erosion and sediment | NO | none (grep for erosion, sediment finds nothing) | Water moves no soil; no deltas, gullies, undercut shores, beach drift |
| Soil moisture and vegetation response | NO | trees fixed at `scatterVegetation` 731; grass is a shader | Wetness map, grass density that follows it, tree growth, burnt then green again, desert under heat |
| Snow load and meltwater | PART | snow texture `snowData` R, ice G | Snow does not become `WD` when it melts; snow/ice do not change ground heat |
| Ash | PART | `ashData` from lava and volcano | Ash does not affect temperature (shading), soil fertility, or drift in the wind |
| Disasters changing ground | YES (several) | quake, tsunami, meteor scorch, deluge | They do not seed lasting second-order effects (landslides after quake, mud after deluge) |
| Dunes walk in the wind | NO | PLAN.md Stage E promised it; `stepSand` has no wind term | Wind-driven transport of flagged sand |
| Maps / seeds | NO | One baked island: `terrain_257.f32.b64.txt` loaded at 447, `HGT = D.h` at 473; harbour/pier fixed | Procedural generator, seed UI, map templates |
| Opponents | PART | Boats shoot back when hit and retaliate for 15 s (2307, 2342); `WEAPONS` gun and mg (2260); one scenario `raid` sets `rb.raider = true` and its own tick assigns targets (3479 to 3487) | No free-play enemies, no spawn rules, no auto-engage by Coast Guard or navy boats; `raider` exists only inside the scenario |
| Autonomous people | PART | jobs `board/unload/pickup` (1971, 2046); skipper on every boat (4417); crew fight fire and patch (4366); rescue helicopter (4452); water bomber auto-calls at 8 burning trees (4691) | Role strings (`ROLES[variant % 4]`, 1581) are labels, not behaviours. Idle people stand still until ordered |

---

## 4. World size, view and draw distance: what is set and what it would take

**Current settings (from the code).**
- Ground: `TN = 257`, `TH = 128`, 1 m cells, one 257 by 257 vertex mesh (641 to 660), uncut, so any edit rewrites all 66k vertices and recomputes normals (`commitLand` 1383 to 1388).
- Physics heightfield 129 by 129 at 2 m (1398).
- Water surface: one 460 by 460 plane with 230 segments (993), centred; the ground tile is 256 m, so the water extends about 100 m past each ground edge.
- Seabed: a ring 180 to 2600 m plus a 380 m square at y -9.3 (659 to 660).
- `heightAt` returns -9.3 for anything outside plus or minus 128 (394), so the open sea is a flat seabed in physics.
- Camera: `PerspectiveCamera(52, 1, 0.1, 3000)` at 408, then `far` set to 4000 in god mode and 3000 otherwise every frame (3214). Near is 0.1, which is very small for a far of 4000 with a 24-bit depth buffer.
- Fog: `FogExp2` base density 0.0032 (493), scaled by weather and in god mode by `clamp(90 / god.dist, 0.3, 1)` (2655). At 0.0032 the exponential-squared fog is about 80 percent opaque by 500 m, so nothing beyond about 500 to 700 m is seen on a clear day. Raising `far` alone buys nothing. The view limit is the fog, the water plane edge and the seabed ring.
- Shadows: ortho box sized from camera distance, 48 to 200 m (3228).
- Simulation grids: 257 by 257 `WD`, `LV`, `LT`, `MH`, `snowData`, `matData`, `hotData`, `SIf`, `ashData`; plus the 64 by 64 air grid (4 m cells). `stepIce` and `stepLake` loop the whole 66k grid each tick.

**Options, cheapest first.**

| Option | What it takes | Cost | Verdict |
|---|---|---|---|
| A. Horizon sea and sky blend | Make the water plane follow the camera in x/z (snap to a grid of 4 m so ripples do not swim), grow it to ~2000 m with a few rings of falling resolution (a 3 ring clipmap: 128 segs at 460 m, then 64 at 1200 m, 32 at 3000 m), fade water colour to the fog colour; move seabed ring with it. Tune fog (lower to ~0.0016 in god mode) and raise `near` to 1 in god mode (keeps depth precision for 4000 far) | Two extra draw calls, ~8k vertices. Negligible for phones | **Do first.** Gives "better view" immediately even on the old island |
| B. Far-field terrain ring (visual only) | Second coarse mesh, 2 m or 4 m cells covering 1024 to 2048 m, built once from the seed (noise only, no sim), hidden under the sim tile where they overlap; neighbouring islands and mountains on the horizon; trees as billboards or none | One draw call, 16 to 65k vertices static | **Do second.** It also makes seeds feel big. Physics beyond the tile can stay "sea" unless a boat reaches a far island (then clamp or turn back, like an edge of the world current) |
| C. Bigger sim tile by cell size | Make the cell size a constant `CELL` (2 m) while `TN` stays 257, so the play space is 512 m with the same loops and memory. Every place that does `x + TH` becomes `x / CELL + TH` (`heightAt`, brush, `addSand`, lava, `stepLake`, etc.; roughly 150 sites by grep count of `+ TH`) | Same CPU as today | **Good for the "bigger" ask if detail loss is OK.** Sand repose, lava thickness and flow rates need rescaling by `CELL`. Trees/people stay 1:1 in metres |
| D. True 513 by 513 tile (1 m cells, 512 m) | `TN = 513`, `TH = 256`. 4 times the memory (about 1 MB per Float32 layer, 14 layers is 14 MB, fine) and 4 times the per-tick loops. Needs: active-region bitmap per 32 by 32 chunk for `stepLake`, `stepIce`, `stepSand`, `stepLava`; chunked terrain mesh (16 chunks, update only dirty ones) instead of rewriting 263k vertices in `commitLand`; physics heightfield 257 at 2 m; air grid 128 or keep 64 at 8 m; shadow and grass uCam ranges; bake AO per chunk | Terrain mesh is 263k vertices (~520k triangles). That is too heavy for a mid phone with grass and trees, so use a 2-level LOD: the 129 m around the camera at 1 m, the rest at 2 m | **Largest win, largest cost.** Do last, behind the active-chunk work, which also speeds up the existing game |
| E. Streaming / infinite world | Chunked tiles with sim sleeping outside the camera area | Large | Not recommended for this release series |

**Recommendation:** A and B in the first release (visual, safe), C as a "Large map" switch in the second (gives 512 m using today's loops, then measure on the phone), D only if C is not enough. Performance budget from PLAN.md stays: new behaviour under 1.5 ms per frame on a phone, new loops run inside active boxes and chunks and cost nothing when idle.

---

## 5. Ranked improvements

Effort: S is under a day of focused work, M is one to three days, L is a week or more. "Needs" names the code hooks. Ranked within group by value to the owner's stated wish (merge, shift, heat melts, wind and water make things happen).

### Living materials (everything merges and shifts)

1. **One material layer and a shared slump rule.** (M) Replace the four flag bytes with a material id per cell: rock, earth, sand, mud, snow, ice, glass, obsidian, ash (keep `matData` for rendering). Give each material a repose angle and a hardness. Run the talus pass for **every** cell above its repose angle, not only flagged ones, and re-arm the active box (`sbx`) whenever `brush`, `commitLand` or a quake edits `HGT`, so digging under a pile makes it slump and any steep cliff of earth relaxes. Needs: edit `stepSand` 3941 into `stepSlump`, hook `brush` 1376 and `commitLand` 1383, shader reads the id for albedo (terrain shader around 539 to 640 already reads `matTex`). Why fun: this is the "chuck stuff down and it merges, then shifts when the land changes" in one rule; Land brush ops (raise, lower) become materials too.
2. **Water carries soil (erosion and deltas).** (M) Add a sediment array `SD` next to `WD`. In `stepLake` (3543) lifting = k times flow speed times slope, drop sediment where flow slows or enters the sea; lower `HGT` where lifted and raise where dropped; mark soft materials only (rock is hard). Thermal erosion is item 1. Rain on an earth hill carves gullies; a river you spring from a Water dump builds a delta; a deluge makes mud. Cost: a few more reads in the existing loop, inside the active box. Why fun: From Dust's best moments are exactly this; it makes the Deluge and Tsunami leave a changed coast.
3. **Soaking and soil moisture.** (M) Add `SM` (soil moisture). Rain and `WD` soak in at a rate set by the material (sand fast, rock zero, earth medium) and `WD` shrinks accordingly (the missing sink at 3563). Wet soil evaporates back to air humidity `CH` in `stepClimate` 3862 (currently only open water does). Wet sand slumps at a gentler angle, mud at a gentler still. Why fun: rain makes the island visibly wetter and then drier; floods go somewhere; springs form where moisture pools.
4. **Plants that respond.** (M) Grass density and tree growth follow `SM` and temperature; trees that burn leave a burnt patch and slowly regrow if wet and not frozen (replace permanent `hideTree` 4605 with a `t.regrow` countdown and a scale ramp); trees die when buried by sand, flooded for long, or in lava; seeds spread to bare wet earth. Grass shader (817) already reads `canopyTex`, so add a "green" channel from `SM`. Why fun: you can grow a forest by watering sand, lose it to drought, or fireproof a shore with trees (From Dust's lever).
5. **Loose things move with the ground.** (S) In `commitLand`, if a cell under a crate, barrel, prop or tree has changed by more than a threshold, wake it and nudge it downhill; trees whose root cell is buried deeper than ~1.5 m or flooded deeper than ~2 m are uprooted and become floating logs (objects). Why fun: slides take your buildings and boats with them; cheap and very visible.

### Heat and weather chain reactions

6. **Ground temperature field with conduction and phase changes.** (M) New `GT` Float32 (same 257 grid, updated 4 to 8 times a second inside an active box). Sources: lava, furnace, fire, heat lamp (via `heatGround` and `addSource`), sun by day; sinks: Cooler, snow, water, night. Per-material conductivity (rock high, sand low, snow very low) and a table of transitions (the Powder Toy model): snow above 0 C becomes `WD` meltwater, ice melts, sand over ~1500 C melts to glass (already), earth/rock over a hotter threshold becomes lava (magma), cooled lava becomes rock or obsidian, wet soil above 100 C boils into vapour. Replaces `MH` (3927). Why fun: heating and cooling "heats the earth and melts stuff and creates lava and other things" is literally this table.
7. **Lava meets water properly.** (S) In `stepLava` 3803 to 3807: add humidity `CH` and `CT` heat to the air cell above (steam that then rises, clouds, rains, per the existing `stepClimate`), flash-boil adjacent `WD`, produce obsidian (new material, hard, black glass-like) when lava meets sea, and pillow-lava ridges (solidify at a lower height so new land is spiky). A steam burst scares people and boats. Why fun: DF's best-known reaction; creates a cloud and rain you did not paint.
8. **Fire as a real thing.** (M) Grass and bush fire on dry ground (uses `SM`), spreading by wind direction and dryness, stopping at water and wet soil and bare sand; burning cells add `CHT` (heat to the air grid) and smoke, so big fires pull wind in (the thermal wind and convection already exist at 4179 and `CUP`) and can build a pyrocumulus storm. Leaves scorched ground and ash that fertilises regrowth. Extends `igniteTree` 4606 and the spread rule at 4615. Water bomber and fire boats already react. Why fun: lets lava, lightning and meteors do their natural thing; fire you can fight with terrain (dig a firebreak, flood a gully).
9. **Wind that reads the terrain and moves stuff.** (M) Add terrain deflection in `computeWinds` 4179: speed up over ridges, slow in lee, channel along valleys, orographic lift on windward slopes (feeds `CUP`, so hills wring rain out of onshore wind and make dry lee sides). Let wind blow dry loose sand into dunes, lift ash and snow (snow drifts into hollows), and push smoke. Why fun: shapes you sculpt change the weather; a mountain makes a rain shadow; dunes migrate across your island.
10. **Snow, melt and flood chain.** (S) Snow melting (stepIce 4098) feeds `WD` (meltwater) in proportion to melt, frozen ground (`GT` below 0) does not soak (item 3), ice dams hold lakes then fail when warmed. Why fun: a warm spell after a snowfall floods the valley; one lever (heat lamp) produces a flood.

### Maps and seeds

11. **Seeded procedural islands.** (M) Replace the loaded `D.h` (473) with `genTerrain(seed, template)` run at start (257 by 257 fBm, domain warp, island mask, ~50 ms) and write the usual `HGT0` for Reset. Keep the baked island as "The Cove" template. Seed as a short word string, shown in the Menu with Copy and Enter; same seed gives the same terrain, trees (`hash2` already deterministic at 746) and weather start. Needs: `scatterVegetation` 731 and `bakeAO` 531 must run after generation; a mulberry32 PRNG replacing `Math.random` in the generator only. The existing fixed pier and harbour (`pierInfo`) need a "find a sheltered shore" placer or become an optional item you place. Why fun: replayability, shareable seeds, a reason to return (Islanders).
12. **Map templates.** (M, after 11) Archipelago (many small islands, shallow shoals), Atoll (ring reef with a lagoon), Fjord (steep walls, deep channel, glacier at the head), Volcanic (central cone with a caldera lake, ready to erupt), Lake and river valley (ocean at one side, river to a lake), Barrier coast (long sand bar with a lagoon behind, perfect for storms and sand). Each is a function of noise plus a mask shape plus a few rules (sand where slope is low near sea, rock where steep). Add climate presets per template (cold fjord, hot atoll). Why fun: very different problems per map; a fjord is about ice and tsunami, an atoll is about storm surge.
13. **Pre-aged landscape.** (S) After generating, run 200 to 500 ticks of the thermal slump and a short hydraulic erosion pass offline so coasts look natural and rivers exist from minute one. Why fun: removes the "noisy bump" look; makes rivers and beaches that your later edits then interact with.

### World size and view

14. **Horizon sea, fog tuning, depth precision.** (S) Option A above. Raise `near` in god mode, lower god-mode fog density, move the seabed ring and water with the camera. Why fun: first visible "bigger" feeling for almost no cost.
15. **Far-field ring of distant land.** (M) Option B above, built from the same seed so neighbours of your island are consistent. Optional: boats can sail to a far island and trigger a "new map" jump with the same weather. Why fun: sense of a world, and a natural travel goal.
16. **Large map switch (512 m).** (L) Option C (`CELL = 2`) first, option D with active chunks later. Add a Quality line "Map size: Standard / Large". Measure with the existing quality toggle (`setQuality`, 3115). Why fun: more room for archipelagos and for lava, floods and storms to travel before they hit something.

### Toys and goals

17. **Weather and elements as a pairing board.** (S) A tiny in-game "Things to try" card that lists 6 to 8 reaction pairs that exist (water on lava, cold on lava, sand over a spring, fire into wind, rain on a slope) and ticks them off as you do them. No clock, no fail. Why fun: teaches the interactions the game now has; gives the "chuck stuff" players direction (Noita and Powder Toy rely on discovery).
18. **Challenge cards that use the simulation.** (M) Add to `SCENARIOS` (3460) goals that check the material layer: "Hold the beach through a deluge" (shoreline loss under a threshold), "Stop the lava before the village" (lava cells in a zone), "Make an island from nothing" (land above sea level count), "Grow a forest on sand", "Free the frozen harbour". Each reuses `check(s)` with array scans. Why fun: goals that need the new interactions to be solved; seeds make them replayable (a daily seed).
19. **Save, share and photo.** (S to M) Already top of the October audit: Save the world (IndexedDB, prefixed `squall-cove-`), plus a share string of seed plus template plus tools used. Add the new fields (`GT`, `SM`, material ids, `SD`) to the world snapshot with defaults so old saves open (`snapshotWorld`, 3316). Why fun: lasting builds are the pay-off for all the above.
20. **Sculpt feel.** (S) Soft preview of the brush (height ghost), and "pile" and "dig" brushes that move material rather than add or delete it (dig removes it from here and drops it in a pile next to the brush), so the player feels like they are moving real stuff. Fits with item 1. Why fun: matches the "chuck stuff down" feeling better than a raise button.

---

## 6. Opponents and people

### What the code does today
- Combat exists: `WEAPONS` (gun, mg), `setupBoatCombat` 2274 (HP, flooding, fire, sinking, mounts from `sp.guns`), `fireShot` 2283, damage and retaliation at 2307 and 2342. Bay and Hero class Coast Guard boats have guns. A boat shoots back for 15 s after being hit if it has armed crew.
- The only enemy is the **scenario** "Harbour defence" (3479): it spawns two `scnBoat('hero', ...)` with `raider = true`, gives them a target, and the scenario tick chases and assigns targets. Outside it, nothing is hostile, and no boat chooses to shoot something it was not ordered to.
- People: `makePerson` 1579 labels by `ROLES[variant % 4]`; jobs are only ones you order (board, unload, pickup). Boats get a skipper (4417); crew patch hull and fight small fires (4366); Coast Guard boats spray fires; a helicopter rescues; a water bomber auto-launches at 8 burning trees (4691). Idle people stand still; extreme cold, heat and lava just topple them.

### Improvements

**O1. Hostile factions with auto-engage.** (M) Add `bt.side` ('player', 'hostile', 'neutral'), generalising `raider`. In the boat update loop (2334 to 2350), armed player boats with crew auto-pick the nearest hostile in range (not neutral), respecting a stance toggle (hold fire, return fire only, engage). Hostiles auto-pick the nearest player boat or pier. Needs: a `stance` field in the boat panel, a small range scan every 0.5 s (cap at 30 boats), a clear red marker for hostile boats. Why fun: Coast Guard and navy boats guard the cove without micromanagement; you can park a Hero on the approach and it does its job.

**O2. Threat spawner with escalation (free play, optional).** (M) A "Threats" setting in the sandbox sheet (`sandboxSheet` 4044): Off (default), Occasional, Busy. Spawns by simple rules:
- *Smugglers*: a small fast boat drives from the map edge to the nearest quiet shore, drops cargo or people, leaves; navy boats auto-engage if they notice.
- *Pirates / raiders*: appear at dusk or in fog (use `wx` and `clim`), attack the nearest unarmed boat or pier, flee when HP below 40 percent.
- *Storm-driven threats*: a drifting derelict or a fire ship swept in by a hurricane or tsunami; the lava or ice makes new hazards for them too.
- *Sea monster* (optional toggle, off by default for realism): rises in a deep basin, rams boats; fire, mg or a deep-water charge drives it off.
Escalation: threat level rises slowly with the number of boats you own and falls after a quiet period; waves get bigger, never past what the effect limit (`effectsCount`) allows. Gentle mode hides this (the existing Gentle setting). No clocks shown to the player. Why fun: gives free play a pulse and a reason to build defences; consequences use the same physics as the player's boats.

**O3. Defence structures and tools.** (M) Place coastal guns, mines (triggered by hostile hulls, blast with the existing meteor/mg particle effects), nets (a rope barrier that jams a propeller), searchlights (night sight range), harbour chain booms. Terrain edits become defence: raise a shoal and hostiles ground. Why fun: terrain and materials matter for the fight, linking this to Section 5.

**O4. People with roles that act on their own.** (M to L) Replace the label array with a real `role` and a small behaviour table (priority list, evaluated every 0.5 s when a person is idle):
- *Fisher* (placed near a shore or on a small boat): walks to the nearest shallow water with fish (a cheap noise-based "fish" map), casts, catches, drops catch at the nearest crate (cargo items already exist). Why fun: quiet life in the harbour.
- *Medic*: finds people with `rag` state or `cold/heat` over 0.7 and carries them to shelter or a boat (uses `topple/standUp`, `walkTo`).
- *Firefighter*: walks to the nearest burning tree or boat and puts it out (reuses `extinguishTree` 4687); with a fire boat, boards it.
- *Builder*: if a pile or crate is nearby, carries it to the nearest low point of a shoreline, building a wall or pier (uses the pickup job, 2046; later a "build plan" brush).
- *Sailor*: on boarding a boat at a pier, takes a station (helm, gunner) per `boatCrew`; a skipper already exists (4417).
- *Scout*: wanders to high ground and reveals fog or marks lava, fire and enemy boats on the map.
- *Lifeguard*: stays on a beach or pier, swims to anyone in the water (`swim` or `floating`), tows to shore.
How roles emerge from what is placed nearby: a person standing within 8 m of a fishing hut or net becomes a fisher; near a fire station/boat, a firefighter; near a medical tent, a medic; near a crate stack or sand pile, a builder; on a pier by a boat, a sailor; on a hill or tower, a scout; on a beach with a lifeguard stand, a lifeguard. Players can also set a role by tapping the person (a short list). Fallback: people who are not near anything wander lightly and wave (the existing `wk` waving state). Needs: new placeable items in the Build registry (a handful of small props: hut, tent, station, stand, tower), a `role` field saved in snapshots, and a cap on active behaviours (`MAX_PEOPLE`). Why fun: Townscaper-like calm; the island fills with small stories, and the reaction loops from Section 5 give them things to react to (people flee lava, fight fires, rescue frozen).

**O5. People react to the living world.** (S to M) Use `GT`, `SM`, `clim` and lava/fire cells: people seek shelter in rain, shade in heat, flee rising water or lava (topple only as last resort), warm up near fires or furnaces, wade into shallows to cool. They carry out their jobs in this context (a fisher stops in a gale). Why fun: no new menu, the world feels inhabited.

---

## 7. Recommended build order (three releases)

All releases: bump version, update IDEAS.md "Done in", test on the phone (emulated touch is not enough), keep prefixed storage, no timers.

**Release 7.0, "Merge and shift" (the owner's core ask).** Items 1 (material layer plus universal slump), 5 (loose things move with ground), 3 (soaking), 7 (lava meets water properly), 10 (meltwater chain), 14 (horizon sea and fog), and 17 (Things to try card). All of these work on the existing 257 grid and existing loops. Exit test: pile sand, dig under it, it slides; pour water on earth, it soaks and the soil darkens; lava into the sea makes steam, then cloud, then rain.

**Release 7.1, "The world answers" (heat, weather, life).** Items 6 (ground temperature field), 2 (erosion and deltas), 4 (plants respond and regrow), 8 (fire as a real thing), 9 (terrain-aware wind and dunes), 19 (save and share, with new fields), and O1 (hostile side and auto-engage, which is a small change that makes combat usable). Exit test: a heat lamp over snow produces meltwater that floods a gully and carries mud to the sea; a burning forest builds a cloud; Coast Guard boats engage hostile boats on their own.

**Release 7.2, "New worlds" (maps, seed, size, people).** Items 11 (seeded islands), 12 (templates), 13 (pre-aged landscape), 15 (far-field ring), 16 (Large map, option C first), 18 (challenge cards using the simulation), O2 (threat spawner, off by default), O4 (roles) and O5 (people react), O3 later if time. Exit test: seed "kestrel" gives the same island on two phones; an atoll and a fjord play differently; Large map holds 30 fps on the phone with grass on, otherwise it stays a Quality option.

**Why this order.** Release 7.0 changes the feel with the smallest risk and no new rendering; 7.1 deepens it using the ground temperature and sediment fields that 7.0 prepares; 7.2 adds breadth once the world is rich enough that new maps are interesting. The map generator (item 11) could go earlier if the owner wants new maps first, but templates look flat until slump, erosion and soaking exist, so generating them before 7.0 and 7.1 is less rewarding.

## 8. Risks and notes

- **Performance.** Every new field is another 66k-float array and a loop. Only run loops inside the active box (as `lbx`, `sbx`, `hbx` do now); move to chunk bitmaps before any grid growth. Budget 1.5 ms a frame on a phone (PLAN.md).
- **Terrain rebuilds.** `commitLand` rewrites all 66k vertices and recomputes normals. With more processes dirtying land (erosion, slump, fire scars) throttle to 4 times a second and rebuild by chunk. The physics heightfield update is already batched to twice a second for lava (PLAN.md risk); keep that for all sources.
- **Saves.** Add fields with defaults; old saves must open. Material id arrays should be stored as bytes, run-length compressed if the snapshot grows.
- **Realism versus play.** Keep parameters exaggerated for fun (erosion fast, soaking visible, lava solidifies in tens of seconds). Add a "Realism" slider only if asked.
- **Safety rules.** Never leave people trapped; frozen, buried, stuck and grounded things get a way out (PLAN.md rule). Burying a person under sand should lift them to the surface.
- **Unverified.** Draw distance numbers (fog opacity, sea beyond 230 m) are from reading the shader and constants, not measured. Please check them on the phone before building A. Wind-driven dune walking is described in PLAN.md Stage E but I found no code for it in `stepSand`.
- **Content and tone.** Enemies are optional and off by default, no real-world factions, no clocks, no blood. Sea monsters are a toggle.

## Owner rule for opponents (added after the plan)

Violence is simulated and cartoon only. No person is ever shown coming to real harm and there is no gore. Anyone put out of action (civilian, crew, smuggler, pirate or other combatant) is knocked out of the fight and then collected: paramedics and medics come for civilians and combatants, and the criminal factions send their own "mob doctors" or "cartel medics" to take their people away, the same way the rescue helicopter lifts people out. Rescue and medical evacuation are the way people leave the scene.
