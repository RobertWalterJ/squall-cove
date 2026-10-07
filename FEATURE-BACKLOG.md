# Squall Cove feature backlog and audit plan (Oct 2026)

Purpose: one list of everything asked for, started, or promised that is not finished, so a later audit can decide for each item whether it still makes sense for gameplay and how to integrate it. Nothing here is a commitment. Value is for the sandbox (H, M, L). Effort is rough (S under a day, M a few days, L a week or more).

## A. Gameplay systems asked for and not built yet

| Item | State | Value | Notes for the audit |
|---|---|---|---|
| Ravenfield-style FPS: bots with health, ranged combat, weapons (pistol, SMG, rifle, shotgun, sniper, melee), capture points, tickets, respawn | Not started. First-person has Hands, Rod and a one-hit knock-out Rifle. NPC fights are fist scuffles. | H | Needs: person health, NPC aiming and firing with line of sight, weapon table, capture points on yards, sites and lookouts, bot roles (assault, defend, medic, sniper), squad orders. Keeps the no-gore rule: knock-out and medics. Biggest single feature. |
| Garry's Mod set pieces and editable attributes (health, speed, faction, weapon, size, mass, heat) on any entity | Not started. Inspector exists for devices only. | H | One generic inspector for people, boats, vehicles, objects. Saved scenarios as set pieces. |
| The Sandbox (mobile) feel: drawable elements, cool environmental effects | Partly: elements to hold and apply, materials, weather. No freehand drawing of structures. | M | Draw-to-build (walls, ramps, bridges) from materials; pixel look is optional. |
| Faction relations in code (one faction field per unit, 8 factions, derived team colour) | Menu merged; code still uses side, raider, blue, hostile flags. | M | Do before the FPS work so bots use it. |
| Armed toggle on Coast Guard boats, single Events sheet | Not done (menu audit item) | L | |
| Rival developers: take over, compete for stone, sabotage | Built; slow and unclear to watch | M | Needs a visible stone count, a clearer takeover rule, and a speed setting. |
| Builders and yards: stage progress very slow (one block per trip) | Works, slow | M | Crane truck now works. Add carry capacity or a second builder per site. |
| Cargo truck and forklift loop near the yard without completing jobs | Bug seen in the Port test | H | Reproduce on the Port map, fix pickup and delivery. |
| Fishing: sell fish to the yard, fish stocks by depth | Rod works to catch; nothing uses the catch | L | Verify over real water. |
| Raider camp (bunker, tents), invader beachhead objectives | Models exist; not placed by any scenario | M | Part of the capture-point mode. |
| Barter, trust and economy from raids and robberies | ECON.trust only | L | |

## B. Physics and simulation

| Item | State | Value | Notes |
|---|---|---|---|
| Soft structures (VBD solver in softlab/) | Prototype passes 12 of 14 checks; not in the game | H | Use for planks, rope bridges, cables, sails, glass. Do not use for stone or fast impacts. Phone budget unmeasured. |
| Water conservation (springs, rain, evaporation, ocean level) in the ledger | Not done | M | Ledger covers loose ground, surface water, soil water, cargo mass. |
| Lava ledger, one-flag-per-cell limit, multi-layer ground columns | Not done | M | The single material flag per cell limits stacked materials. |
| Ray-traced and volumetric caustics | Cheap seabed caustics only | L | Desktop-only nicety. |
| Liquid solver (Takahashi and Batty 2024) | Judged too heavy for a phone browser | L | Revisit only for a desktop mode. |
| Wind field spatial variation | Added (veering and surging bands); not judged by eye | M | Needs a visible cue: gust fronts on the water and grass. |
| Whitecap froth shader | Written; not judged by eye | M | |
| Wave energy, bounce feedback | Fixed and tested | | |
| Vehicle tilt and ground contact | Gaps under 0.4 m in tests; user still reported floating cars | H | Get a screenshot of the failing case; check pier and slope cases. |
| Large map (512 m) and phone performance of the 1 MB port building set | Large map has known gaps; port glb loads lazily | M | Measure on the S23. |

## C. Content and assets

| Item | State | Notes |
|---|---|---|
| Raider, gunboat, landing craft, response RIB models | In the game | Landing ramp animates. |
| Port buildings (24), concrete, asphalt, gravel, road markings | In the game (Port and mountains map) | Fence transparency sort order; windows are coloured boxes. |
| Hangar, bunker, tents, fences, houses unused by the scenario | Placeable from Place > Buildings | Use in the raider camp and the airfield idea. |
| Weapon models for first person and NPC hands | Only a box rifle and a rod | Needed for the FPS work. |
| Uniform kits | Guard, Raider, Invader, SWAT | Add medic, engineer, sniper. |
| Sound: gunfire variants, footsteps on concrete or gravel, swim strokes, crane, containers | Core library exists; none of these | Use the sound pipeline (sound/). |
| Listening pass on the horn and engine change | Not done by ear | LISTENING.md loop. |

## D. Interface

| Item | State |
|---|---|
| Remaining menu audit items (focus management, read-aloud on every sheet, non-button rows, top-right order, duplicate Calm all and Install) | Open, see MENU-AUDIT.md section D |
| Side pane Map tab list refresh, labels on phones | Works; labels need a phone check |
| Keyboard and mouse help card | Updated; needs touch parity check |

## E. Release and housekeeping

| Item | State |
|---|---|
| large-map branch is not pushed or merged; live game is v8.4.0 | Needs the user's approval; then bump sw.js VERSION |
| Save and load for new props, paving, scenario sites, factions | Not checked |
| IDEAS.md update with everything since v8.5 part 2 | Not done |
| Memory file updated through the side pane and menus | Partly |

## How to run the audit

1. For each row, play it on the Port map for five minutes and mark: works, works but unclear, broken, missing.
2. Cut anything that does not make a visible, understandable moment in under a minute of play.
3. Order what is left by value over effort. The proposed order is: cargo truck and forklift fix, faction field, person health and NPC shooting, capture points and bot roles, weapons, editable attributes, soft structures for planks and ropes, then polish.
