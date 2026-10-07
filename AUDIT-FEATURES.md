# Squall Cove: feature audit (7 Oct 2026, read-only)

Method: read the code and the asset files only. No browser, no Blender, no git, nothing edited except this file. `index.html` was being edited by another agent while I worked (strategic points, structures, crews, events, troop skins, weapons2, battle vehicles). I took a snapshot at 12:34 (8,690 lines) and cite **line numbers from that snapshot**; the live file had drifted by only a line or two at 12:42, so they are close but will move. Anything marked *(in progress)* belongs to the other agent's batch and its own header says "written without a browser: none of this has been seen running". Nothing below was seen running by me either: PRESENT means the code exists and is wired to something a player can reach, not that it looks right.

Status words: PRESENT (code exists and is reachable), PARTIAL (exists but unreachable, buggy by reading, or incomplete), MISSING.

## Counts

See the end of the file (section 9), written after the tables.

---

## 1. Sandbox basics

| # | Feature | Status | Evidence | What is needed |
|---|---|---|---|---|
| 1 | Destructive as its own menu | PRESENT | Sky tray chip `Destructive` L5719 opens `disastersSheet` L7220 over `DISASTERS` L7156; gentle mode and `gateDisaster` guard it | The sheet also stacks Arrivals and Events under it (L7225-7227) and the side Events tab shows all three stacked (L3873): three ways in, not one clean menu each. Pick one. |
| 2 | Arrivals as its own menu | PRESENT | Chip L5720 opens a sheet of `ARRIVALS` L7203 | Same duplication as above. |
| 3 | Events as its own menu | PRESENT | Chip L5721, `EVENTS` L7210 | Same. |
| 4 | Factions and Sides reconciled into one grouped Factions menu | PRESENT | One `Factions` category in `PLACE_CATS` L5645 with `grp` sub-headings (Port and Coast Guard, Raiders, Foreign invaders, Smugglers, Developers, Traders) at L2286-2302; `fillPlace` L3922 prints the group headers | The code still has no single faction field (`side`, `raider`, `blue`, `hostile` flags coexist; FEATURE-BACKLOG says so). Menu is fine. |
| 5 | Menu audit: no overlapping panels (side pane tabs, person panel, fleet bar, top notices) | PARTIAL | Layout rules exist: `body.sideopen` shifts (L194-200), battle offsets for `#bHud`/`#notes` (L225-229), battle notices to `#sideFeed` L231 | Unverified by eye. Likely collision: `#sideFeed` sits `right:10px; top:240px` (L231) over the top-right `.actions` column (right:12px, up to `100dvh-196px` tall, L61) whenever "More" is open on a desktop-height window. Needs a screenshot pass in battle with the side pane open, the person panel showing and More expanded. |
| 6 | Boulders and piles dropped from height; wheel sets height; `[` and `]` set size | PRESENT | `dropH`, `dropSize` L2389; wheel handler L5468 (`isDropItem` L2390 covers cargo, sand, earth, rock dump, scrap); keydown `[`/`]` L6141; ghost ring/pole L6135; Play-tab sliders L3914 | None. (Wheel only works in Place > build with a drop item chosen; documented in help card.) |
| 7 | Wading and swimming for walkers | PRESENT | `WADE = -0.9` L3196; `stepFoot` L3249 slows when wading, sets `p.swim`, `poseSwim` L3205, swimmers head for `nearestLand` | None. |
| 8 | Fast light raider boats that rob sailboats | PRESENT | `runner` and `gunboat` specs L1722-1723 (`raiders` glb); robbery loop in `updateFleet` (hostile branch, L8239-8247: picks the nearest `sail` boat, 7 s alongside, takes up to 2 crates, flees, "Nobody was hurt") | None. |
| 9 | Raiders never shoot civilians | PRESENT | Boat target scan in `updateCombat` L3449 only accepts `isCG`, `blue`, armed or `lastHitBy` boats for hostile mounts; on foot `senseEnemy` L4455 only targets the other `side`, and civilians have none | None. |
| 10 | Landing-craft invasions with ramp animation; parties unload and fight | PRESENT | `landingParty` L7172, `runLandings` L7188 (run, ground, "ramp goes down", crew hop off one by one, boat leaves); `landing_ramp` node in raiders.glb is bound as `bt.rampNode` L1752 and rotated -1.745 rad; parties get `side`/`role` so `armedLayer` L4436 and `skirmishThink` make them fight | Ramp pivot/axis never seen; check by eye. |
| 11 | Landing boat waves in a battle join the battle | PARTIAL | `boatWave` L4641 calls `landingParty`, which makes sandbox units (`p.gun`, no `q.bot`) | These soldiers ignore squads, objectives, medics and capture logic; on Urban/Desert there are no `sites`, so blue ones fall to "On guard"/idle (`skirmishThink` returns false) and red wander. Spawn them through `spawnBot` after the hop ashore (or give them a `bot` record). |
| 12 | Vehicles removed from the sandbox | PRESENT | `VEHICLES_ON = false` L7981; `makeVehicle`, `vehDispatch` L8069 return early; no `BUILD` entry carries `veh` | Dead code (`VSPEC`, `vehMove`, `findPath`...) and `vehicles.glb.b64.txt` remain in the repo. |
| 13 | Drivable battle vehicles (planned back in battle mode only) | MISSING | `bveh.glb` has apc, light_tank, quad_atv with seats, exits, wheels, turret, barrel, muzzle nodes (read from the file), but `index.html` contains no reference to `bveh`, no loader, no driving, no seats. File was rebuilt at 12:43, so the other agent is on it | All of it: `ensureBvehicles` loader, spawn at points, enter/exit (E), drive model, turret/gun fire, bots as drivers/passengers. *(in progress)* |
| 14 | "First person" button | PRESENT | Two buttons: `#bJoin` L5801 (select a person first) and `#bFP` L3950 (`dropIn`). Battle HUD has Jump in (`#bJump`) | Both are hidden by default: `body.ui-min` (L7504, rule L78) hides every top-right button except Log, Menu, More, Take the helm, Deselect, Rescue helicopter. First person and Fire control are behind **More**. Also two buttons with the same label; merge them. |
| 15 | Left click selects, right click commands | PARTIAL | Left select works (L5498-5507). Right click on boats orders them (`orderBoats` L5528, no button test). For **people**, the whole command block is guarded `if (sp.length && btn !== 2)` L5508, and the person-select block `pe && btn !== 2` L5498, so a right click with people selected falls through to the boat/object code and does nothing; on desktop a left click on empty ground deselects first (L5507) | Bug by reading: people cannot be commanded with the mouse on desktop. Change L5508 to run for right click (or for any touch tap) and keep the left-click deselect. Highest-value one-line fix in the sandbox. |
| 16 | People stagger rather than topple on small hits | PRESENT | `stagger` L2760 (0.8 s lurch plus `poseBend`); crate impact: stagger above 28 J, topple above 160 J (L2645); hulls, blasts, flechettes, vehicles all choose stagger or topple by size | None. |
| 17 | Buildings solid to people | PRESENT | `pushOutOfProps` L2763 runs every step in `stepFoot`; `detourAround` L2769; battle structures that are `SOLID` become `props` with a box (`bTry` L4887) | Small cover pieces (`sandbag_corner`, trenches, wire) are not solid, see next row. |
| 18 | Foot routing round water, buildings and sandbags | PARTIAL | `setFootOrder` L3001 + `findFootPath` L7970 (A* on the 64x64 land map; blocks water, slope >0.75 and every `props` box via `footGrid`) | `footGrid` reads only `props`. `sandbag_corner` structures are pushed to `FOOT` and `STRUCT` but not to `props` (`soft`, not `SOLID`), so people walk straight through them and plan routes over them. `x-sandbag_wall` props (battle cover, L4388) are routed. Add `STRUCT`/`FOOT` entries with `cover` to `footGrid` and `pushOutOfProps`, or make them solid. |
| 19 | People never stand around idle in a battle | PARTIAL | `botThink` L4473 has a 4 s stuck watchdog (drops the order, walks 16 m elsewhere, drops the objective after 2 strikes), medics hunt the fallen, squads follow their leader | Gaps: landed boat parties (row 11); a bot whose objective ground is under 0.5 m (`standY(tx,tz) > 0.5` fails every time) idles; `if (tx === undefined) return` idles; crews are meant to stand at posts. Needs a play test with the 70-per-side setting. |
| 20 | No big name labels (labels off by default) | PRESENT | `labelsOn = false` L3961; `setLabels` L3966; toggled only from the Map tab | None. |

## 2. Maps

| # | Feature | Status | Evidence | What is needed |
|---|---|---|---|---|
| 21 | Port and mountains: organic coast, harbour, town, farms, forests, scenery, seam-free | PRESENT (unseen by me) | `genTerrain` L1007 port branch; `layPortBuildings` L3998, `layScenery` L4237, `layFarms` L4247, `scatterVegetation`; sea ring, MAP-AUDIT.md v2 says coast and harbour read well | MAP-AUDIT.md lists "bad" items from the 00:16 pass (sparse streets, empty quay, few people, thin forest, flat ground colour, hills not mountains). I could not tell which were done afterwards; about 37 people are placed (L3975-3985, 4192) against the audit's target of 50. |
| 22 | Larger map | PRESENT | `CELL = 3` (768 m) for any battle map L750; `?size=large` (CELL 2) as "The large cove" | The audit says phone performance of the large map is unmeasured. |
| 23 | Gravel yards as real loose rock | PRESENT | `layGravel` L4296 raises the height grid and flags cells as loose material (`flagMat(k,120)`, `slumpArm`), ragged outline, can be dug and heaped; `stockYard` L3990 adds a loose rock heap | Gravel **roads** on the Desert use a textured strip (`mat:'gravel'`), not loose rock; acceptable but not "real". |
| 24 | Physical container yards | PRESENT | `CARGO` id `box` (container_a/b from cargo.glb, density 380) L1894 is spawned in stacks by `stockYard` L3997 (`put('box', ..., 4.2)` is a second tier); quay containers on Urban/Desert are static `port.glb` props | The static quay containers do not move. Fine, but say so. |
| 25 | Grass never grows in roads | PRESENT | `maskGrass` L4283 called for every ribbon sample (square of width+2) in `buildRoadMesh` L4313 and for every paved patch | None. |
| 26 | No repeating white lines on roads | PARTIAL | Junction patches (`ROAD_JUNCTIONS` loop L4332-4340) stop side-road lines at the kerb; marking texture cropped to plain line work (L4279); QA-LOG items 2 and 15 | Never rendered after the fix. QA-LOG still lists two unexplained painted lines (qa_s2, a blue and a yellow line on concrete). Needs one street-level screenshot per map. |
| 27 | Roads modelled properly and graded | PRESENT | `roadDense`, `roadGrade` L987 (level across, smooth along), one ribbon mesh per road, junction patches, `ROADCELL` for path costs | None. |
| 28 | Urban port map | PRESENT (unseen) | `urbanRoads`, `urbanStamp`, `layoutUrban` L4076, `BATTLE_MAPS.urban` L883; MAP-URBAN-DESERT.md says nobody has seen it | Visual check: block floors vs roads (render order), crane footprints, building facing, frame rate with about 300 props. |
| 29 | Desert map with a far port | PRESENT (unseen) | `desertRoads`, `desertStamp`, `layoutDesert` L4139, highway from the quay road to the Wadi fort; `BATTLE_MAPS.desert` L889 | Same unseen caveat. |
| 30 | Battle options removed from maps that do not support battle | PRESENT | Side-pane Battle tab only when `isBattleMap()` L3868; intro Battle button hidden L6001; `battleStart`/`playBattle` call `offerBattleMaps` L4202 | None. |
| 31 | Start screen with map choices; battle setup does not auto-start | PARTIAL | `#intro` L405-413, handler block L6000-6004: `?battle=1` only opens the Battle tab (`openBattleSetup` L5999) | Bug: `go('sail')` returns before it switches maps (L6000: `if (what === 'sail') return;`), and the later `what === 'sail' && MAP.t === 'cove'` test is unreachable. "Sail the cove" just dismisses the card and leaves you on whatever map `localStorage squall-cove-map` holds (probably Port). Also the card says "v8.9 battle depth" while `sw.js` is v8.6.0. |
| 32 | Controls list in the Menu | PRESENT | Menu `Controls` button `#mCtl` -> `controlsNodes` L6020 (overview, first person, boats, tablet) | Several lines do not match the key handlers; see section 8. |
| 33 | Esc opens the menu | PRESENT | Overview keydown L5536: Esc cascade is tablet/armed fire first, then leave helm, then deselect, then `openMenu`/`closeMenu` | In first person Esc is taken first by the FP handler (L3756, `exitFP`), and because `exitFP` leaves the person selected, the overview handler then sees `sel.length` and deselects in the same keypress (a second Esc is needed to reach the menu). Harmless but surprising. |

## 3. Battle (Ravenfield style)

| # | Feature | Status | Evidence | What is needed |
|---|---|---|---|---|
| 34 | Tickets | PRESENT | `BATTLE.tickets` 80 each; a knock-out costs one (`downPerson` L4425); bleed when a side holds 2+ more points (`updateBattle` L4795); end screen toast and sound; HUD `battleHud` L4810 | None. |
| 35 | Capture points that can really be converted | PRESENT | Count of living people in radius `p.r` every 0.5 s, `p.prog` -1..1, flag repainted, HQ locked until its side holds no other point (L4801); `makeFlag` L4371, `POINT_TYPES` L863 | None. |
| 36 | Bots with classes | PRESENT | `BCLS` L4397: rifle, smg, sniper, medic, shotgun, heavy (LMG), engineer; troop skins by class (`battleSkin` L5141) | Bots never use marksman, breacher, trooper, spotter or AA kits (those are player loadouts only). Probably fine. |
| 37 | Squads: formation | PRESENT | Squads of 4 (`planBattle` L4781 sets `sq`, `sqi`); followers hold offsets behind and beside the leader (`botThink` formation block) | None. |
| 38 | Squads: contact sharing | PRESENT | On sighting an enemy, squadmates get `alert` and a `hint` (1.5 s throttle); hints also feed mortar targeting (`mortarTarget` L4998) | None. |
| 39 | Fire and move | PRESENT | Half the squad advances while the other half crouches and fires, phase by `simT` and `sqi` | None. |
| 40 | Suppression | PRESENT | `b.supp` rises on near misses (`botFire` L4460), above 0.65 the bot ducks and holds | None. |
| 41 | Morale and retreat | PRESENT | Morale drops with nearby deaths (`downPerson`) and low hp; below 0.3 the bot runs to its base for 12 s | None. |
| 42 | Cover seeking; firing from cover; emerging | PRESENT | `coverList` L4445, `findCover` L4450 (far side of a prop from the enemy), `b.peek` cycle toggles `crouch` | Only a crouch pose exists (row 70). |
| 43 | Medics revive | PRESENT | Bot medics walk to the nearest fallen friend within 12 s and stand them up (`botThink`); player medic kit via `fpRevive` L5160 | None. |
| 44 | Grenades thrown by bots | PRESENT | `throwNadeAt` L4733 from rifle, smg and shotgun bots at 9-30 m, 22-42 s apart; blast via `updateBombs` | None. |
| 45 | Flank, push, hold tactics | PRESENT | `b.tac` picked per bot (sniper holds); flank offsets 16 m sideways | None. |
| 46 | Many more bots (up to 70 per side on desktop) | PARTIAL | Slider max 70 (`renderSide` L3895). But `MAX_PEOPLE = 170` L2482 counts corpses (they linger 16 s) and crew/paratroops too, so at 70 per side `spawnBot` returns null and reinforcements and crews stall | Raise the cap in battle (or count only the living) and measure: `senseEnemy` does a line-of-sight test over every prop per candidate, about 470 scans a second at 140 bots. Untested at that size. |
| 47 | Phone limits | PRESENT | Slider max 10 on touch, `MAX_PEOPLE` 36, `PUTS` caps, `BKIT.cap` 90, crew budget 4, fewer structures per point (`layPoint`) | `troops2` is a 13.3 MB base64 file fetched in every battle (10 MB glb); measure load and memory on the S23. |
| 48 | Player can be a Port soldier or a raider | PRESENT | `playBattle(team)` L4824 from the Battle tab (two buttons, `redKind` Raiders/Invaders) | None. |
| 49 | Deploy window with loadout classes (Assault, Marksman, Sniper, Trooper, Breacher, Air defence, plus new) | PRESENT | `LOADOUTS` L4361 has all ten: assault, marksman, heavy, engineer, spotter, medic, scout (named Sniper), trooper, breacher, aa; `kitButtons` L4363 used in the Battle tab and in `deployMenu` L4815 | The window only appears when you are knocked out; at the start you choose in the Battle tab, then `playBattle` deploys at once. Consider showing the deploy window on first drop-in too. |
| 50 | Deploy window releases the mouse and closes on leaving first person | PRESENT | `deployMenu` exits pointer lock; `exitFP` L3593 clears `BATTLE.down` and hides `#bSpawn` | None. |
| 51 | Jump in/out: J, K, Y, V, Jump in / Watch next / Overview buttons | PARTIAL | J/K at L5258 (overview only), Y in first person (same handler), buttons `#bJump/#bSpec/#bOver` wired L5257; `possess` L5239, `specNext` L5252 | **V bug**: in first person V is bound twice. The FP handler (L3755) cycles the tool (`fpCycle`), and the global handler (L3954: `k === 'v' && (mode === 'god' || mode === 'fp')`) calls `dropIn`, which calls `exitFP`. One keypress cycles the tool and kicks you out. Decide: V leaves (drop `fpCycle`'s binding) or V cycles and Esc/Tab/O leave. |
| 52 | Battle notices go to a side feed | PRESENT | `toast` L5827 routes everything to `sideFeedAdd` L5819 while `BATTLE.on` (right edge, five lines max, 3.5-9 s) | See overlap risk in row 5. |
| 53 | Top-of-screen items do not overlap | PARTIAL | CSS offsets per mode (L225-229) | Unverified (row 5). |
| 54 | Strategic point types with structures (HQ, strongpoint, radio, depot, battery, airfield, harbour, choke) *(in progress)* | PRESENT | `POINT_TYPES` L863, `layPoint` L4934 places battle.glb structures per type (all 22 node names it uses exist in battle.glb), `holdN` L4859 and `cdRate` L4860 apply the bonuses, radio mast shows enemies on the overview (`updateMarkers` L5045), depot restocks the player (`updateKit` L5119) | Not seen running. BATTLE-DESIGN.md's "engineer builds sandbags" exists as `fpEngineer` L5178. Barbed wire, trenches and sandbag corners are not solid (row 18). Mines and searchlights: searchlight tower exists (cone at night), **mines are missing**. |
| 55 | Crewed emplacements and mortar pits; man with E *(in progress)* | PRESENT | `assignCrew` L4968 puts a bot at the most important guns, `crewTick` hands an empty post to the nearest free friend, `updateMortar` fires at squad-reported clusters, player E (`fpUse` L3640 -> `nearEmp`) mans MG, AA or mortar | Sandbox maps have no emplacements; E only works inside a battle. |
| 56 | Dynamic events: counter-attacks, supply drop, air raid, weather *(in progress)* | PRESENT | `updateEvents` L5109 (all four plus reinforcements), no countdown text | Not seen. |

## 4. Weapons and first person

| # | Feature | Status | Evidence | What is needed |
|---|---|---|---|---|
| 57 | Weapon models | PRESENT | `ensureWeapons` L5205 loads weapons.glb and weapons2.glb; `applyWeaponModels` L5207 and `applyWeaponModels2` L5192 build first-person groups; `botWeapon` L5217 for NPCs | The AA launcher is procedural (`makeAAMesh` L5206) and the hand grenade is a green sphere; weapons2's `grenade` and `flare_gun`, weapons.glb's `knife` and `magazine` are never used. |
| 58 | Hit effects, sounds, foley | PRESENT | `impactFx` L5226 by surface; fire sounds `wpn_<stem>_fire_0N` and `_far` mapped by `SNDW` L4844; ricochet, whiz, shell casings, reload sounds (`fpReload` L3829), footsteps by surface | Battle aircraft have no engine or rotor loop (only the rescue helicopter and water bomber, L615-616). No sound for the knife, the radio tool or binoculars click. |
| 59 | Pistol with a two-handed hold | PARTIAL | NPCs: `armedPose` L3228 puts the left hand beside the right on pistols and revolvers (IK) | First person pistol, shotgun, sniper, revolver and RPG groups carry **no arms** (arms_idle is only added to rifle, smg, carbine, lmg, marksman, carbine_scoped, L5209 and L5199). You see a floating gun. |
| 60 | SMG, rifle, shotgun, sniper, carbine, AA launcher (homing, key 9), grenades (0), charges (minus, B to detonate) | PRESENT | `WPN` L4348, `FPT` L3764, number keys L3755 (0 grenade, minus c4), homing in `updateMIS` L4606, `detonateC4` L4742, B at L4780 | In a battle the number keys follow your loadout order, not the labels (`kitTools()[k-1]`), so AA is key 9 only in the sandbox. The Controls text explains this. |
| 61 | Two-handed holds for NPCs and proper hand placement via IK | PRESENT | `ikArm` L3215 two-bone solver, `GRIP` offsets per weapon L3222 | Unseen. |
| 62 | No zombie arms | PARTIAL | NPC arms are IK-driven with a pole vector, which should avoid the stiff pose; first person arms are the static `arms_idle` mesh | Needs eyes. |
| 63 | Run animation without glitches | PARTIAL | `poseGait` L2682 with `runK` blend, `poseRifle` leans into a run; only bots and armed people run (`p.bot && p.run`) | Unverified. The only baked clip in every troop and people file is `idle` (checked in the glb JSON); all locomotion is procedural. |
| 64 | Crouch (C) and prone (P) for the player | PRESENT | `fpStance` L3741; keys L3755; `#fpStance` button; eye height 0 / 0.55 / 1.15; body pitches 1.45 rad when prone (`updatePeople` L3304); accuracy and speed scale by stance | None. |
| 65 | NPC kneel, prone, cover, emerge, reload, hit reaction, fall per state and per weapon | PARTIAL | **Exists**: a single crouch pose (`poseCrouch` L2694) driven by `b.crouch`; cover and "emerge" are the peek cycle toggling it; stagger bend (`poseBend`); one ragdoll fall (`topple`/`makeRagdoll` L2719) for every state; gun dropped on death (`dropGun` L3225); pistol vs long-gun grips | **Missing**: kneel (one knee), prone, reload animation (bots just wait `b.reload`), hit-reaction pose (`hitT` only changes AI), fall variants by stance/weapon, emerge/lean-out pose, crouch-walk, weapon-specific stances. All would be procedural poses, since there are no clips. |
| 66 | Right-click zoom: scoped weapons toggle, iron sights hold | PRESENT | `mousedown`/`mouseup` L5462-5463 (`scoped` toggles, others hold; binoculars hold) | Needs pointer lock (`fp.locked`) or the click does nothing. |
| 67 | Sniper scope view with crosshair | PARTIAL | `#fpScope` overlay L298, shown by `fpCamera` L3719 for `SCOPEDT` (sniper, marksman) | (a) The carbine is `scoped:true` and toggles zoom, but `SCOPEDT` excludes it, so no scope mask. (b) **Stuck overlay bug**: the overlay is hidden only inside `fpCamera`, which does not run after you leave first person; `exitFP` never clears `fp.zoom` or `#fpScope`. Press Esc, H or die while scoped and the black mask stays over the overview/helm until the next time you enter first person. Fix: hide it in `exitFP` and `fpHelm`. |
| 68 | Left button fires while the right button is held | PRESENT | Separate `mousedown`/`mouseup` handlers L5462 (left sets `fireHeld`, right toggles zoom) | None. |
| 69 | High accuracy for sniper and carbine | PRESENT | `spread` 0.0008 and 0.0035 in `WPN`; zoomed spread x0.2, stance multiplier (`fpFireGun` L3835) | None. |
| 70 | E to man gun emplacements | PRESENT | `fpUse` L3640, `nearEmp` L3632, `fpManFire` L3633; prompts "E: man this gun" | Battle only (rows 55). |
| 71 | Jump (Space), run (Shift), reload (R), E use, G drop, Q overboard, H helm | PRESENT | FP keydown L3751-3757 | None. |
| 72 | Dead code | n/a | `fpShoot` L3796, `paveRoad` L4342, `lmDirtyMark`, `vehHeight`, `volcanoSurface`, `clipSeed` never called (QA-LOG says the same) | Delete when convenient. |

## 5. Air, support and explosions

| # | Feature | Status | Evidence | What is needed |
|---|---|---|---|---|
| 73 | Griffon with door gunner, real Griffon/Huey/Black Hawk models | PARTIAL | `airSpawn` L4551 picks `griffon`, `griffon`, `huey`, `blackhawk` from helis.glb (`ensureAir` L4530 loads air.glb and helis.glb), rotors spin (`_mainrotor`, `_tailrotor`), fires at enemies in 95 m (`airFire` L4562) | The door gunner is only a tracer from the aircraft; the models' `griffon_gun`, `huey_gun_L/R`, `blackhawk_gun_L/R` nodes and `*_seat_N` nodes are never used (no gunner figure, no aiming gun). The paratroop drop does not use a helicopter at all (parachutes appear from `y 90-130`). |
| 74 | Gunship with minigun and howitzer | PARTIAL | `gunship` node from air.glb, 380 hp, orbits at 165 m, 0.07 s tracer bursts plus a heavy shell every 4.5 s (`airFire`) | `gunship_minigun`, `gunship_cannon`, `gunship_howitzer` nodes are never rotated or recoiled; works, but the weapons do not visibly move. |
| 75 | Strike jet | PARTIAL | `callStrike` L4689 -> `airNode('jet', stubJet)`; flies a 1,250 m run and drops five bombs | air.glb has **no `jet` node** (nodes: griffon, gunship, parachute, emplacement_mg/aa/mortar, shell_heavy, crate_drop). The jet is always the box stub. Needs a jet model (Blender agent) and a `jet` node, then teamMark kind `jet` will paint it. |
| 76 | Artillery | PRESENT | `callArty` L4694 (6 shells, craters), battery barrage `batteryFire` L5024 *(in progress)* | None. |
| 77 | Mortar | PRESENT | Fire control `mortar` (7 rounds); crewed mortar pits fire by themselves; player mans one and aims | Mortar pit model comes from battle.glb; air.glb's `emplacement_mortar` is unused. |
| 78 | Paratroop waves | PRESENT | `paraWave` L4634 (bots on parachutes, `parachute` node) | None. |
| 79 | Boat landing waves | PRESENT | `boatWave` L4641, allowed only for a side holding a harbour (`boatAllowed` L4866) | See row 11. |
| 80 | Aircraft have HP; shot down by AA nests, emplacements, portable AA, high-calibre rifle fire | PRESENT | `damageAir` L4574; nests `layAA` L4579 / `updateAAS` L4586; player AA `fpFireAA` L4596 (homing `updateMIS`); rifle fire `fpAirHit` L4602 (sniper 0.7, marksman 0.5, carbine 0.4, LMG 0.1, rifle 0.12); RPG too (`fpFireRPG` L5166); crash with fire and a blast | None. |
| 81 | OFFLINE for a while, no countdown numbers | PRESENT | `AIR.off[team][kind]` set on shot-down, cooldown 110-160 s; tablet shows Ready / Recharging / Offline (`renderTablet` L4762); toasts are plain text | None. |
| 82 | Team colours painted into the aircraft | PRESENT | `teamMark` L4542 patches the aircraft's own materials (belly, tail stripes, wing tips) by shader, per kind (heli, gunship, jet) | Unseen. |
| 83 | Aircraft keep flying high | PRESENT | Helicopters hold `max(75, ground+62)`, gunship 165, jets 140 | None. |
| 84 | Command tablet: T, Tablet button in first person, Fire control in the overview, in the Menu | PRESENT | T (`toggleTablet` L4759; key at L4780, overview and first person); `#fpTab` L3727; `#bFire` and `#mFire` L6017-6018; battle HUD `#bTab` | Overview Fire control button is behind **More** (row 14). |
| 85 | Fire control weapons: lightning strike, storm, missile, bomb, cluster, incendiary, mortar, artillery, shockwave, smoke, flechette, air strike, Griffon cover, gunship cover | PRESENT | `fireOne` L4705 handles all fourteen; `renderTablet` lists all fourteen (L4771-4772); `setFire` L4731 names them for the armed banner | None. |
| 86 | Aim options: crosshair or tap, marker, hot spot; blast size; pattern (single, line, ring, scatter); aim looseness; Mark target | PRESENT | `TAB` L4698; chips in `renderTablet`; `targetPoint` L4730; `fireAt` L4721 (size x0.6/1/1.7, spread 0/12/30 m); `setMarker` L4700 with a pole and ring | None. |
| 87 | God-mode arming, then tap the map | PRESENT | `FIRE.armed` set by the tablet row, `tapAt` L5487 fires at `pick()`, Esc stands down | None. |
| 88 | Explosions: craters, shockwave, cargo impulses, tree damage | PRESENT | `blast` L4661 (flash, smoke, `crater` L4653 into the height grid and loose grains, quake, boat and person damage, cargo `applyImpulse`, `clearTreesNear` and `igniteTreesNear` for R >= 8/10) | Craters skip paved ground by design. |
| 89 | Dropped guns fall to the ground, not floating | PRESENT | `dropGun` L3225 -> `LOOSE`, gravity and ground clamp in `updateBombs` L4743 (which runs from `updateAir`, outside the `BATTLE.on` gate) | They fall to terrain height only; a gun dropped on a pier, building or deck sinks to the sea floor or terrain below. |
| 90 | Physics step cannot crash | PARTIAL | `world.step` is in a try/catch that removes non-finite bodies and resets contacts (L5892) | The **frame loop is unguarded**: any exception in `updateBattle`, `updateKit`, `updateAir` or any other update before the end of `frame()` (L5865) stops `requestAnimationFrame(frame)` from being called again, and the game freezes for good (the window `error` handler only changes the loading message). Given the battle batch is unseen, wrap each update group in try/catch (and move the rAF call to the top). |

## 6. Naval

| # | Feature | Status | Evidence | What is needed |
|---|---|---|---|---|
| 91 | Deck guns with heavy-calibre shells | PRESENT | `WEAPONS` L3366 kinds mg, gun, heavy; `heavyBlast` L4674 on landing (R 12, crater 5) | None. |
| 92 | Heavy naval gun on larger ships | PRESENT | `k:'heavy'` on the Hero class cutter (L1721) and the Donjek (L1733); `k:'gun'` on the other big ships except Franklin | Franklin has no gun; decide if intended. |
| 93 | Gunnery from the helm (G), click to fire | PRESENT | `G` toggles `gunneryOn` (L5536 helm branch), `tapAt` L5488 calls `gunneryFire` L4677; documented in the Menu | Works only on a boat with mounts ("This ship has no guns"). |
| 94 | Blast effects for naval shells | PRESENT | `heavyBlast`, splash on water (`blast` `wet` branch) | None. |

## 7. Assets built by agents: loaded or not?

Every glb is loaded through `loadGLB(name)`, which fetches `assets/<name>.glb.b64.txt` (not the `.glb`). I decoded each `.b64.txt` and compared it to its `.glb`: for air, battle, bveh, helis, troops, troops2 and weapons2 they are byte-identical (checked). The `.glb` files themselves are not used by the game.

| Asset | Loaded? | Where | Notes |
|---|---|---|---|
| raiders.glb | Yes, at boot | `loadAll` L810 (`glb.raiders`) | Boat specs reference it; all 7 nodes used (hulls, `gunboat_mount0/1`, `landing_ramp`). |
| port.glb | Yes, lazily | `ensurePort` L4282 (on first port prop or map layout) | All 24 nodes are in `BUILD`; no missing node names. |
| props2.glb | Yes, lazily | `ensureProps2` L4308 | 28 nodes; `jetty_section` has no `BUILD` entry. |
| weapons.glb | Yes | `ensureWeapons` L5205 | `knife`, `magazine`, `muzzle_flash` nodes unused. |
| troops.glb | Yes | `ensureTroops` L2587 (via `ensureWeapons`) | All 12 skins used. |
| air.glb | Yes | `ensureAir` L4530 | `gunship_cannon`, `gunship_minigun`, `gunship_howitzer`, `shell_heavy`, `crate_drop`, `crate_drop_chute`, `emplacement_mortar` unused; no `jet` node exists. |
| helis.glb | Yes | `ensureAir` | griffon, huey, blackhawk used. **bell206, cobra, chinook unused** (the rescue helicopter uses aircraft.glb `cormorant`). |
| battle.glb | Yes, battle only | `ensureBattleKit` L4842 (from `kitStart` L5130) *(in progress)* | 52 nodes; only `trench_corner` is unused. |
| troops2.glb | Yes, battle only | `ensureTroops2` L4843 -> `battleSkin` L5141, `reskinBots` L5135 *(in progress)* | 12 skin families: desert, urban, sniper, medic, engineer, heavy, special, militia, riot (SWAT on Urban), port_worker (civilians on Urban/Desert) used; **pilot and officer unused**. 13 MB base64. |
| weapons2.glb | Yes | `ensureWeapons` (second file) *(in progress)* | `grenade` and `flare_gun` unused. |
| bveh.glb | **No** | no reference in `index.html` | See row 13. Rebuilt 12:43. *(in progress)* |
| vehicles.glb (old) | Only `ensureVehicles` L7938, which nothing can reach | `VEHICLES_ON = false` | Dead; only `vehicles.glb.b64.txt` is left, no `.glb`. |
| aircraft.glb | Yes | `ensureAircraft` L804 (rescue helicopter, water bomber) | Only `cormorant_*` and `cl415_*` used. |
| terrain, nature, fleet, harbour, cargo, ccg, ccgfleet, people | Yes | boot or lazy | `ccgfleet` loads when a big ship is placed. |

## 8. Meta

**Sound.** `audio/manifest.json` has 878 ids in 10 groups (core 194, fx 53, mat 201, people 182, music 10, boats 69, aircraft 14, weapons 99, water 33, weather 23). The weapons group is loaded when a battle starts (`Snd.group('weapons')` L4381) and on desktop in the background. Battle-relevant stems **generated but never referenced by name in the code** (some may be reached by computed names; I searched for the literal and for the common prefixes): `wpn_knife_swish`, `wpn_gun_echo_tail`, `veh_heli_whine_loop`, `veh_heli_wash_loop`, `veh_bomber_pass`, `veh_gun_shell_fly`, `ppl_radio_click/squelch/chatter_loop`, `ppl_binocular_click`, `ppl_shout_help`, `ppl_shout_boat`, `ppl_grunt_topple`, `foley_heal`, `mus_sting_*`. In plain terms: aircraft, radio, binoculars, medic revive and knock-down grunts are silent or borrow another sound. Weapon fire, reloads, casings, ricochets, whiz, hitmarker, flags, tickets, victory/defeat, KO, explosions are all wired.

**Service worker.** `sw.js` is `v8.6.0`; the intro card says "v8.9 battle depth". The install precache is only `./`, `index.html` and two icons; every glb, texture and sound is runtime-cached cache-first after first use (`/squall-cove/` path only). Consequences: new assets are cached correctly once fetched, but because they are cache-first, a rebuilt `bveh.glb.b64.txt` or `troops2.glb.b64.txt` will not refresh until `VERSION` is bumped. Bump to match the release (v8.9) when merging. No offline first run (not new). Manifest `id` is `/squall-cove/` (correct per the shared-origin rules). `index.html` navigation is network-first, so code updates do arrive.

**Help card and Menu controls vs real key handlers.** Mismatches found:

1. **V** in first person: Controls says "V: Next tool"; the help card and Play tab say V drops in and out. Both happen at once (row 51).
2. **J, K, Y** are listed under first person; J and K work only in the overview (L5258), Y only in first person.
3. Help card (L420+) says "1 to 4 . Tab: Switch tools . next boat". Tab is not bound in the overview (N is the next-boat key); in first person Tab leaves.
4. Help card does not mention Esc opening the menu, T, J/K, E manning guns; the Menu Controls list has them.
5. Play tab text (L3911) says "Hands, Rod and Rifle ... keys 1, 2, 3"; the real list is 1 to 9, 0, minus.
6. Controls says scoped weapons "(sniper, marksman rifle, carbine) toggle": true, but only sniper and marksman show a scope view.
7. Controls "Esc: Deselect, or open this menu": true in the overview; see row 33 for first person.
8. Controls `H` in first person is "take the helm" and Esc leaves; correct.

**Features in code with no control or documentation.**
- `fpCycle` (V) conflicts and is only in the Controls text.
- Binoculars click marks the target for the tablet (`fpBino` L5152) but a mark only works if the Marker aim mode is chosen; not explained.
- The `?size=large`, `?map=`, `?battle=1`, `?intro=1`, `?nointro=1` URL switches (no UI except the intro).
- `window.__sc` debug object (L8686) and `window.__camOverride`.
- `routeMode` / waypoints, `fireMode` (F) and `boxMode` (B) in the overview are documented only on trays.
- Counter-attacks, supply crates, air raids, fog and rain events in a battle are announced but not described anywhere.
- `Spotter` radio tool opens the tablet; `satchel` is a second charge button.

**Things said to be done in MEMORY, BATTLE-DESIGN.md or the other audit files that are not in the code.**
- BATTLE-DESIGN.md: **mines** (small blasts) missing; **barbed wire as an obstacle** exists as a model only (not solid, no effect); **"holding the radio mast delays enemy air support"** is done (`cdRate`); **harbour allows boat landings** done (`boatAllowed`); **"Commander calls: attack, defend or flank from the plan"** is partly there (`planBattle`, the A/D buttons) but there is no flank order; **player roles**: squad leader, sniper, engineer, medic, AA exist as loadouts; **pilot role** not built.
- MEMORY.md says v8.5 is on an unpushed `large-map` branch with "structures, NPC/faction engine, vehicles, full sound system". Vehicles are now off; the sound system is wired.
- MENU-AUDIT.md (Oct 6) items still open: duplicate Calm all (tray chip L5722, sandbox sheet L7149, disasters sheet L7221, side Events tab L3875) and duplicate Install buttons; Place tab has the Factions category but the audit's Command/Sky sub-tabs were not built.
- FEATURE-BACKLOG.md still says "weapon models only a box rifle" and "Ravenfield FPS: not started"; stale.
- QA-LOG.md "needs the owner's decision" items (raider camp placement, plant site on a mountain top, qa_s1 slab, qa_s2 stray lines) are unresolved.

---

## 9. Counts and the punch list

Of 93 scored rows (row 72 is a note, not a feature): **73 PRESENT, 19 PARTIAL, 1 MISSING.**

- PRESENT rows that rest on code nobody has seen running: rows 21, 28, 29 (maps), 54-56 (strategic points, crews, events, the other agent's batch), 82 (aircraft team paint), 61 (IK holds). Treat them as "wired, unverified".
- PARTIAL rows by cause: bugs by reading (15, 31, 51, 67, 90), unseen layout (5, 26, 53), missing art or animation (59, 62, 63, 65, 73, 74, 75), gameplay gaps (11, 18, 19, 46).
- MISSING: drivable battle vehicles (row 13). `bveh.glb` exists and is being rebuilt, but nothing in `index.html` loads or drives it.
- In progress (other agent): rows 13, 54, 55, 56 and the troops2, weapons2, battle and bveh assets.
- Four real bugs stand out: right click does not command people (15), V both cycles the tool and leaves first person (51), the scope mask is left on screen after leaving first person (67), and a thrown exception in any update freezes the whole game (90).

### Top 15 fixes, in order

1. **Wrap the frame loop** (row 90). One exception in any battle update stops the game forever. Put `requestAnimationFrame(frame)` first and each update group in try/catch with a one-line console report. Cheap, and protects every unseen battle system.
2. **Right click must command people on desktop** (row 15, L5508 and L5498). Without it the mouse cannot order a person, which breaks "left selects, right commands" for the whole sandbox.
3. **V in first person** (row 51, L3755 vs L3954). Remove one of the two bindings; update the help card, Play tab and Controls so they agree.
4. **Hide `#fpScope` and reset `fp.zoom` in `exitFP` and `fpHelm`** (row 67). A scoped Esc leaves a black mask over the map.
5. **Make the intro's "Sail the cove" work** (row 31, L6000): switch to `?map=cove` unless already there; stop opening on a stale stored map; align the version string with `sw.js`.
6. **Bring First person and Fire control out from behind More** (row 14): put them in the always-visible set (L78) and merge the duplicate First person buttons.
7. **Take a screenshot pass of the UI in battle** (rows 5 and 53): sideFeed vs the actions column, the Battle HUD vs notices, the person panel and the side pane. Fix whatever collides.
8. **Make boat-wave troops real bots** (row 11) so they join squads and objectives and never stand idle.
9. **Raise or rework `MAX_PEOPLE` for battles and profile 70 per side** (row 46); consider cheaper line of sight (cache per target, grid for props) before promising 70.
10. **Make sandbag corners, trenches and wire count for routing** (row 18): add `STRUCT`/`FOOT` entries to `footGrid` and `pushOutOfProps`.
11. **Build the missing NPC poses** (row 65): prone, kneel, reload, hit reaction, lean-out. Procedural, in `armedPose` and `botThink`, keyed off `b.crouch`/`b.reload`/`b.hitT`.
12. **Visible door gunner, minigun and howitzer** (rows 73-74): use the existing `*_gun`, `gunship_minigun`, `gunship_howitzer` nodes and seats; ask for a `jet` model (row 75) so the strike aircraft stops being a box.
13. **Drivable battle vehicles** (row 13): load `bveh.glb`, spawn at points, E to enter, drive, shoot, bots crew them. Wait for the other agent to finish, then audit.
14. **First-person arms for pistol, shotgun, sniper, revolver and RPG** (row 59) and a scope overlay for the carbine (row 67).
15. **Housekeeping**: bump `sw.js` to the release version; add battle aircraft engine sounds and the unused radio, binocular and grunt stems; delete dead code and `vehicles.glb.b64.txt`; write the real list of key bindings once and generate the help card, Menu and Play text from it.
