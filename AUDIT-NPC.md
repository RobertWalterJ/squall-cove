# Squall Cove NPC / Objectives Engine Audit (read-only)

Source: `index.html` (5636 lines). All line numbers refer to it. Core engine lives in lines 5272-5508 plus person model 1731-1837.

## 0. Architecture in one paragraph

NPCs are not autonomous populations. People exist only when the player places them (`placePeople` 1812, `crewOn` 3705, `spawnThreat` 5276). Each person has `p.role` (from `PERSON_ROLES` 1733, or overridden by the palette 1607-1620) and runs a per-person utility-ish loop: `updateAgents` (5434) -> `think` (5409) picks a goal by a fixed role if-chain; goals are `ag.goal = {kind,...}` executed by a big if/else on `g.kind` (5453-5491). Boats have a second, separate layer: `updateFleet` (5305) drives only Coast Guard and hostile boats; civilian boats do nothing (5309). Hostiles (smuggler/raider/medic) come from `updateThreats` (5283), a timer spawner capped at 2 hostiles. There is no shared world model of "demand", "stock", "territory" or "ownership": only a few global lists (`sites` 5344, `poiList` 5366, `poiVisits` 5365, `objects` cargo) read ad hoc.

Gating: threats are off by default (`prefs.threats:'off'`, 4619) and off in gentle mode (5284). Coast Guard missions on by default.

## 1. Objective map

### 1a. Land people (`think` 5409-5433)

Priority order inside `think`: carrying -> role-specific -> generic POI viewing -> idle. Danger override first (5448-5449). Player order pauses AI 12 s (5446).

| Role | Goal(s) (`g.kind`) | How chosen | Trigger world state | World change |
|---|---|---|---|---|
| any carrying cargo | `deliver` (5411, 5462) | forced, first check | `p.carry` set | drops crate at `yardPt` (round-robin 24-slot grid via `yardN`), `agentStat.crates++` |
| Dock worker | `haul` + helper `help` (5412, 5463-5464) | `freeCrate` (5401): nearest unclaimed loose cargo within 90 m, on land, not already in the yard (<6 m), slow-moving, `liftNeed<=2`, `safeSpot`. Heavy items need a second idle dock worker within 30 m | loose `objects` exist | creates a `pickup` job, then `deliver`. Moves physics bodies |
| Dock worker | `wander` "Waiting for cargo at the yard" (5430) | fallback if >10 m from yard | none | none |
| Forester | `plant` at plant site (5414-5415, 5470-5474) | first `plant` site with `planted<10`; random point within 1.5-8 m passing `safeSpot` and tree/prop spacing | a hand-placed Plant site | `plantTree` (5355): adds a tree prop (palm <3.2 m, pine >11 m, else random), sets soil moisture 0.4 (`SM`), cap 70 land props |
| Forester | `plant` replant (5416) | nearest dead tree with `regrowAt` within 80 m | burned tree | sets `regrowAt`, soil moisture; `updatePlants` (5510) does actual regrowth gated by climate cell `CT`, `SM`, `LV`, `GT`, snow |
| Builder | `build` (5419-5420, 5475-5480) | first not-done `build` site | hand-placed Build site | every 7 s places a boulder prop (`rockb`) in a ring of 8; `st.done`, toast |
| Builder | `wall` (5421, 5481-5482) | surge >0.6 or deluge or hurricane: random coast point with h<1.6 | storm state (`surge`, `dis`) | spawns decorative grains for 12 s; only `agentStat.built++`, **no terrain/flood change** |
| Medic | `heal` (5423, 5465-5467) | nearest (<50 m) person who is `rag`, frozen, cold>0.6 or heat>0.8 | injured/cold people | resets cold/heat, stands them up |
| Firefighter | `extinguish` (5424, 5468-5469) | nearest burning tree <45 m | fire | `extinguishTree` + smoke |
| Lifeguard | signals boat to swimmer (5425) | swimmer within 80 m; finds a free crewed civilian boat with capacity; sets `bt.rescue`, `orderTo` | swimmer/floating rag | boat goes to swimmer. Then `fish`-guard "lookout" (5426) otherwise |
| Fisher / Lifeguard | `fish` (5426, 5483) | random coast point with deep water 5 m out | none | 60% per catch tick: `agentStat.fish++`, splash. **No fish stock, no catch deposited** |
| Hiker | `hike` to summit (5427, 5484) | 70% chance, random spot 2-9 m from `peak` | `peak` = max `HGT` cell (5375) | none (stats only) |
| Tourist | `hail` -> `ferry` (5428, 5485-5489, 5498-5504) | 20% chance if a free crewed civilian boat is not ordered | pier exists | boat is ordered across the cove, pax landed at a coast point. `agentStat.ferried++` |
| Tourist / Photographer / Hiker / "Scout" | `photo` (5429, 5453-5461) | `pickPOI` (5396): `appeal / (1+0.45*visits) / (1+d/90) * rand(0.7..1.3)` over `poiList`; `viewSpot` (5389) picks a safe ring point at `far` radius | POIs from `computePOIs` | `poiVisits` rises 0.25 per shot and 0.5 on finish: crowding discount. Nothing else changes |
| any | `wander`, `flee` (5432, 5448-5449, 5490) | idle fallback; `agentUnsafe` (5408) triggers on lava/ground temp >330/burning tree | hazards | none |

Note: `'Scout'` (5429) appears in no role list and no palette entry. Dead code.

### 1b. Boat factions (`updateFleet` 5305-5338, `updateThreats` 5283-5297, `factionOf` 5302)

| Faction | Goal | Scoring / choice | Trigger | World change |
|---|---|---|---|---|
| Civilian boats | none (label only: 'Ferrying visitors', 'Under way', 'At anchor', 5309) | n/a | n/a | only act when a Tourist hails or a Lifeguard calls them |
| Coast Guard (`isCG` 5300) | Intercept hostile | nearest non-medic hostile within 230 m (5325); also anyone with `lastHitBy` hostile within 25 s (5326) | hostile exists, boat armed | sets `bt.target`, `aiGo` |
| Coast Guard | Fight fire on a boat | `burn` = any non-hostile boat `fire>0.25` within 260 m, only if `isFireboat` (5328-5329) | burning boat | goes within `ffSpec` range |
| Coast Guard | Break ice | random point within 10-70 m of pier end with sea ice >0.18, icebreakers only (5330-5333) | `iceAny` | moves; icebreaking itself is physics |
| Coast Guard | Patrol | random coast point 28-58 m offshore every 8-22 s (5335) | idle | none |
| Raider (`b.raider` or `side==='hostile'` & `threat==='raider'`) | Raid prey | nearest non-hostile boat within 260 m, armed targets weighted 1.3x distance (5319) | civilian/CG boat exists | combat via the generic scan 2524-2526 |
| Smuggler (`threat==='smuggler'`) | Run to shore, drop 2 crates, leave | `spawnThreat` picks a random wet coastPoint (5279); `updateThreats` 5288 drops `CARGO[0]` x2 when `order===null`, then flees to edge and despawns (5289) | threat timer | spawns **free crates on the shore**: these are the only cross-faction cargo flow (dock workers will haul them to the yard) |
| Their medics (`b.medic`) | Rescue their own swimmers | spawn when any `fromHostile` person is in water and no medic boat exists (5292-5294); leaves with >1 aboard (5295) | defeated hostile crew | despawns people: removes them |

Combat enemy test is just `theirs === mine` (2525): one binary hostile/friendly flag.

## 2. How terrain is used

Short answer: weakly. There is **no derivation of viewpoints, yards or build sites**. Three tiers:

1. Hand-placed by the player: `sites` (`addSite` 5345, placed by `place` 1654; max 12 at 5346). Plant, Build, Cargo yard, Viewpoint. A "view" site gets a fixed `appeal:6.5, far:7` (5377) regardless of elevation or visibility. A Viewpoint may even be placed on water (`item.site !== 'view'` exemption at 1654).
2. Fixed or global-argmax heuristics:
   - Lighthouse (1285-1289): max `heightAt` along a western arc at 7 m inset; hard-coded arc, fires once at build.
   - `peak` (5375): brute-force argmax over the HGT grid every 20 s (step 3 cells, h>3). Only one summit, appeal 4. This is the only genuinely terrain-derived POI, and it ignores view extent.
   - Pier-based yard fallback (5406): `pierInfo.c - dir*9`. Pier itself is "first coast south of the island centre" (1265-1267).
3. Random sampling with a safety predicate: `viewSpot` (5389), forester spots (5415), fishing spots (5426: coast point plus deep water 5 m out), wall spots (5421: coast h<1.6). These use `heightAt`, `coastPoint`, `safeSpot` (5368: land, grid margin, ground temp GT<=160, water depth WD<=0.45, no lava within +-4).

Quoted core: `peak` loop

    for (let i = 8; i < TN - 8; i += 3) for (let j = 8; j < TN - 8; j += 3) { const h = HGT[i*TN+j]; if (h > 3 && (!b || h > b.h)) b = {...} }

and view appeal is entirely POI-driven: `appeal / (1 + 0.45*v) / (1 + d/90)`. No slope, curvature, prominence, line-of-sight, water-adjacency, flatness, or soil/material inputs anywhere in `computePOIs`. `computePOIs` does react to events (fire, lava, lightning, helicopter, bomber, burning boats, ice, strange devices), which is the best emergent-ish piece: spectacle attracts crowds.

So: high points do attract tourists (summit + lighthouse + viewpoint) but only the global maximum and the single lighthouse; terrain edits (earth pile, rock dump, volcano) that create a new high point do get a new summit after <=20 s, but sub-peaks, ridgelines and headlands never become attractions. Flat-by-water cargo yards, flat build sites and material stockpiles are not derived at all.

## 3. Faction and conflict structure

Factions that exist: Civilian (unaligned, inert), Coast Guard, Raiders, Smugglers, "Their medics" (`factionOf` 5302). Land roles are not factions: they are job classes with no allegiance.

- Hostility: a single boolean (`isHostile` 5301 / `theirs===mine` 2525). Hostile vs everyone-else. Raiders prey on civilians and CG alike; CG attacks all hostiles (smugglers included, even unarmed ones, 5325 excludes only medics). No raider-vs-smuggler, no CG-vs-civilian, no rival CG/civilian relations.
- What they want: Raiders: damage/sink nearest boat. Smugglers: deposit 2 crates. CG: remove hostiles/fires/ice, patrol. Nothing else.
- Competition over a shared resource: essentially none.
  - Cargo: dock workers claim crates (`o.claimed`, 25 s lease, 5403) but only against other dock workers. Smuggler crates do land in the same pool, but no one cares who dropped them and no one is penalised or rewarded.
  - Sites: `sites.find(...)` returns the first matching site; all builders pile onto the same site. No capacity, no ownership, no contest.
  - Land/boats: no claims. Lifeguard can commandeer any civilian boat without competition.
- Deception / neutral third parties: not present. Civilian boats and land people are passive and truthful. Smugglers are visibly flagged `side:'hostile'` with a toast ("Smugglers") and are treated by CG as a threat regardless; they never pose as civilians. `fromHostile` crew are only used for the medic-boat logic.
- Casualty handling is correct to spec: toppled people float, medic boats collect them (`updateThreats` 5292-5296); no gore.

Missing: neutral/deceitful class, informants, reputation/suspicion, rival builders, salvage, markets/value for cargo, any consequence for stockpiling or stealing.

## 4. Gaps and dead ends

Goals that cannot complete or have no consequence:
1. `wall` (5481): builders "shore up the coast" for 12 s but change nothing (only grains for show). Surge/flood is unaffected. Pure theatre.
2. `fish` (5483): no fish stock, no market, nothing deposited. Fishers have no interaction with boats, yards, or smugglers.
3. `hike`, `photo`: counters only. `poiVisits` is never decayed (a place can be "used up" forever: `/(1+0.45*v)` only grows). Over long sessions all POIs flatten to indifference; there is no recovery or novelty regeneration.
4. `build`: always the same fixed 8-boulder ring (5479), regardless of site flatness, material, or stockpile. No materials are consumed: builders do not gather rock, earth or scrap; `rockb` is conjured from nothing. The sandbox's real materials (sand/earth/rock piles, scrap metal, 1622-1631) have no NPC meaning.
5. `yard`: unlimited capacity, no flat/near-water requirement, delivered crates just sit; dock workers never load boats or move cargo to ships (cargo is not demand-driven).
6. `plant`: cap 70 land props shared with the player (5356) silently stops all foresters; `planted<10` per site then the site is "done" without visual change.
7. `'Scout'` role (5429) unreachable. `ROLES` array (1732) unused. A no-op loop at 5496. `clipSeed` (5367) dead.
8. `hail`/`ferry`: the Tourist hails only a boat with `!b.order`; if the boat is ordered by the player the trip is cancelled silently (5501). Ferry always lands at `coastPoint(ang(boat),3)` not a chosen destination.

Roles without interaction: Fisher (island), Hiker (only POI crowd), Lifeguard (reactive only), Forester and Builder (site-fed only, nothing from other roles), civilian boats (inert), Coast Guard (never interacts with land people or cargo, never inspects, never escorts).

Missing feedback loops: no NPC output ever becomes another NPC's input except (i) smuggler crates -> dock worker hauling, (ii) poiVisits crowding, (iii) burning trees -> foresters replant, firefighters, spectators. No economy, no population growth/leaving, no persistence of NPC goals through save (only sites saved, 3578).

Physics / material state that should change behaviour but does not (checked against `safeSpot` 5368 and `agentUnsafe` 5408):
- Temperature: only ground temp (`GT>160` unsafe for destination, `>330` flee). Air temp, snow, cold are consumed by Medic only; others never seek shelter, never prefer warm yards. `p.cold`/`p.heat` do not affect goal choice.
- Fire: handled (flee, firefighters, spectators) but `safeSpot` only uses 9 m radius around burning trees; smoke/ash ignored.
- Flooding/surge: `WD>0.45` is blocked as destination only; no behavioural retreat to high ground, no Builder wall effect, no yard relocation when the yard floods.
- Loose sand / earth slides / rock piles: ignored. A cargo crate sitting on a sliding pile counts as `Math.abs(op.y - standY) <= 1.6` and may be picked; people can path across unstable material freely.
- Metal / lightning: `dis.lastStrike` is a spectacle POI (5381) but conductive scrap near people, rods, or open peaks do not make hikers/tourists avoid the summit in a storm; a thunderstorm should invert summit appeal.
- Ice: tourists treat frozen sea as an attraction (5386) and `viewSpot` accepts any `safeSpot`; no thin-ice risk.
- Loose cargo physics: `liftNeed` weight only gates a second worker; no one avoids drum/unstable loads.
- Scale/perf: `computePOIs` iterates boats each 4 s and `pickPOI` is O(POIs) per thinker; the `peak` brute force (~1000+ cells every 20 s) is fine. `freeCrate` is O(people * objects). With MAX_PEOPLE 60 this is fine, but any big population needs spatial hashing.

## 5. Prioritised design proposal (12 items)

Goal: derive objectives from terrain and materials, add competing factions with opposed objectives, add neutral/deceitful civilians. Cartoon violence only: all "defeat" outcomes = crew knocked out, collected by medics, boats towed/impounded; never gore.

Core architectural change first (items 1-2), the rest layer onto it.

1. **Terrain analysis cache ("land value maps")**. S-M. Build once per terrain edit (debounced) a coarse grid (e.g. TN/4) with: slope, prominence (height minus local mean over ~30 m), view extent (count of visible sea/land cells along 8-16 rays, cheap line-of-sight on `HGT`), distance to shore (`coastPoint`/depth sign), flatness (max slope in 6 m disc), material at cell (sand/earth/rock/metal from the existing pile systems), soil moisture `SM`, ground temp `GT`. Expose `terrainScore.view(x,z)`, `.yard(x,z)`, `.site(x,z)`. Hook: where terrain is edited (earth/rock piles, volcano, lava) set a dirty flag; read from `computePOIs` (5373), `yardPt` (5406), `think` (5409). Test: headless -- build 5 random terrains from the generator seed; assert the argmax view cell has prominence >= p95 and that it differs from `peak` in >=30% of seeds; assert yard score cells are within 12 m of shore and slope <3 deg for 100% of picks.

2. **Derived POIs and sites replace hand-placed-only**. M. `computePOIs`: add top-K (K=3-5) view cells by `terrainScore.view` as 'natural lookout' POIs with appeal scaled by prominence * view extent (and a lookout structure bonus: Viewpoint site or lighthouse x2). Add auto "proposed yards" (flat, shore-adjacent, near pier/deep water) and "proposed build sites" (flat, stable material, near material stockpile) as ghost sites that become real when the first NPC claims them (`addSite` 5345 with `auto:true`, count against the 12 cap or use a separate cap of 6). Player-placed sites still override. Test: sim 20 min; count visits (photo goal starts) per POI; assert >=70% of tourist photo goals target a POI whose view score is in the top quartile; assert no auto-site on water or slope >8 deg over 50 seeds.

3. **Resource ledger and stockpiles**. M-L. Add `world.stock = {rock, earth, sand, scrap, cargo, timber}` per site (not global), with capacities. `deliver` (5411, 5462) credits the yard's ledger by cargo type (`o.c.id`); yard ownership recorded (`site.owner = faction`). `build` (5475) consumes N units from a stockpile at the same or nearest site before placing `rockb`; if empty, builder switches to a `gather` goal (go to rock pile / rock dump terrain cells, loose granite cargo; `spawn` objects are already physical). Test: sim with 3 builders, zero stock: assert stage never increments until `stock.rock` >=1, then increments by exactly 1 per consumed unit; assert conservation (sum of crate counts delivered = ledger increments) over 10 min.

4. **Objective scoring layer (single utility function)**. M. Replace the role if-chain in `think` (5409-5433) with `candidates = role.goals.map(g => g.score(p, world))`, then argmax with the existing noise and crowd discount. Each candidate returns `{score, goal}`; role = weights (a Hiker values view 1.0, risk 0.3; Builder values build 1.0). Reuse existing goal executors (5453-5491) unchanged. Add weather/physics terms: risk(p, x, z) from lightning/storm/GT/WD/ice/slope, cold/heat need, daylight. Test: golden-output test: with the same seed, new `think` reproduces role choice distribution of the old chain within +-10% in a neutral world; storm world: hiker summit attempts drop to <10% when thunder present.

5. **Material and physics-aware behaviour**. M. Feed hazards into scoring (item 4): (a) lightning/storm -> summit and metal-adjacent spots score negative, people seek low flat ground; (b) surge/flood: yard score drops where `WD>0.2`, dock workers relocate cargo ("evacuate yard" goal) and Builders' `wall` actually raises a real barrier (add dirt via the existing earth pile system or `place` boulders on the coast line, and reduce flood in `surge` handling); (c) cold/snow: Fishers/Tourists retreat to warm, people head to a furnace/sheltered spot; (d) loose sand slopes: `safeSpot` rejects cells whose local slope exceeds the material's angle of repose. Test: inject surge in sim; assert yard cargo moved above flood line within 90 s in >=80% of runs; assert 0 NPC "stuck in flood/lava" frames; lightning scenario: summit visits drop >=70%.

6. **Faction registry with relations matrix**. S-M. Replace booleans (`isHostile` 5301, `theirs===mine` 2525) by `FACTIONS = {id, relation: {other: -1..1}, goals[]}`; keep `isHostile` as derived (`rel<-0.5`). `factionOf` (5302) returns the id. Combat scan (2524-2526) uses `rel(a,b) < -0.5`. Test: unit test that existing scenarios ('raid', 3726) still pass; new test with 3 factions asserts fire only occurs between pairs with negative relation over a 10 min run.

7. **Competing yards and territory (cargo contest)**. M. Two or more opposed cargo claimants: the Port Authority (dock workers, CG-aligned) and Smugglers/Salvage crews. Each site has `owner`. Smuggler crew (land) will `steal` from a stockpile of an opposing owner if guard presence is low; Coast Guard and Dock workers `guard`/`inspect`; contested cargo flips ownership when carried into the other yard. Hook: `freeCrate` (5401) consults owner and yard ledger; `updateThreats` smuggler drop (5288) targets an enemy yard or hidden cache near terrain `shore + low visibility` score instead of random shore. Test: sim 15 min with both factions: assert total cargo conserved (no creation); assert >=1 steal and >=1 interdiction event in 80% of seeds; assert ownership flips are bounded (no thrash >4/min).

8. **Rival builders and site competition**. M. Add `Rival builder` (aggressive) and `Builder` (port/civic) with the same `build` goal but different scoring: build sites have `capacity`, `owner`, and `contested` flag; a rival site adjacent to a civic one can be "claimed" by whoever gets stage progress first; sabotage = non-violent (cartoon): removing boulders ("knock them over") or fencing. Hook: `think` Builder branch (5418-5422); `build` executor (5475-5480). Test: with one site and 2 builders per faction, assert exactly one faction completes it, other redirects to `gather` or a new auto-site within 60 s; assert no site ends up with stage > 8.

9. **Neutral civilians and the deceit mechanic ("masquerade")**. L. Add a `disguise` layer: `p.trueRole`, `p.shownRole`, `p.suspicion`. Smuggler crews on land masquerade as Tourists/Fishers: they use a civilian POI goal (`photo`/`fish`) and their cover is intact until (a) they carry cargo near a yard owned by someone else, (b) someone with `Informant` skill sees them, or (c) they linger near the cache beyond N seconds. Civilian boats can carry a smuggler: a "fishing boat" that unloads at night at a low-visibility cove (use terrain item 1 with a "seen from" map: few viewpoints in LOS). Reveal triggers the existing hostile pipeline (`side='hostile'`). The CG can inspect (`inspect` goal): with probability tied to suspicion; false positives against truthful civilians reduce "civilian trust" (a public-opinion meter), a feedback loop. Hook: `think`, `updateFleet` civilian branch (5309), `factionOf`, `computePOIs` (so tourists notice suspicious boats), `openPeople`/`openFleet` must show shown role only until revealed. Test: sim 20 min: assert 0 NPCs labelled hostile in UI before reveal; assert reveal events have a cause code logged; assert false-positive inspections > 0 and reduce `trust`; assert cover break rate within 20-60% per smuggler.

10. **Informants, salvage crews, and information flow**. M. Informant (civilian role, e.g. Fisher or Photographer) that observes events with a view cone (uses item 1 visibility) and reports to a faction after delay/travel (information is carried by a person walking to a contact, can be intercepted). Salvage crews: boat-based faction that tows wrecks (`bt.sunk`), recovers cargo from `objects` floating in water, and sells to whichever yard pays (ledger). Hooks: `updateThreats` sunk-boat events, `updateAgents` new goal kinds `observe`, `report`, `salvage`; a `rumour` list of `{faction, kind, x, z, t, reliability}` read by `updateFleet` for CG target choice (false tips from deceitful civilians cause wasted patrols). Test: seeded sim: assert CG response latency is lower when an informant has LOS than when not; assert a false tip causes a patrol to a location with no hostile at least once in 10 runs and the CG returns to patrol within 60 s; assert salvage recovers >=1 floating crate in a wreck scenario.

11. **Civilian boats as agents (cargo and trade)**. M-L. `updateFleet` (5309) currently skips civilians. Add a civilian behaviour set: ferry runs (reuse `stepFerry` 5498), fishing sorties, cargo runs between yards via the pier, anchoring in sheltered water (terrain score), fleeing raiders. This creates competition for boats (Lifeguard, Tourist hail, smuggler front, salvage all want boats): add `bt.reservedBy` and priority rules (emergency > ferry > cargo > hail). Test: assert no boat double-booked (reservedBy collisions = 0) over 15 min; assert a rescue always preempts a ferry within 10 s.

12. **Telemetry and balance harness**. S. Extend `agentStat` (5365) into per-role/faction event counters (goal started/finished/aborted with reason, steals, inspections, reveals, trust, yard stock, rival site progress) and expose `window.__npcStats()` for the existing headless Chrome harness (srv3.py port 8772 per memory). Add decay to `poiVisits` (recover ~1 per 90 s) to stop permanent saturation. Test: CI-style run of 30 simulated minutes at 8x time over 5 seeds; assert no goal kind has 0 completions, abort ratio <40%, `poiVisits` stays bounded, and cumulative cargo conservation holds. Needed first or alongside everything else.

Suggested order: 12 -> 1 -> 4 -> 2 -> 3 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10 -> 11.

### Proposed archetypes

| Archetype | Faction | Overt behaviour | True objective | Counterplay |
|---|---|---|---|---|
| Tourist / Photographer / Hiker | Civilian (neutral) | view POIs (items 1-2), avoid hazards | crowd demand drives viewpoint appeal and unwitting witnesses | the player builds lookouts; storms scatter them |
| Fisher | Civilian | fishes shore, possible informant | reports/sells information; competes for fishing spots | CG patrol, rumours |
| Dock worker | Port | hauls cargo to owned yard | maximise yard stock | smuggler theft, flooding |
| Builder | Port/Civic | build civic sites from stock | finish sites before rival | rival claims, supply shortage |
| Rival builder | Developer bloc | same as builder, own sites | grab flat, valuable ground first | sabotage by fencing/knocking over boulders (non-violent) |
| Smuggler (hidden) | Smugglers | tourist/fisher cover, night boat runs | move cargo to a hidden cache, buy/sell | CG inspection, informants, suspicion meter |
| Raider | Raiders | open attack on boats | take cargo off boats, disrupt traffic | CG, armed civilians, convoys |
| Informant | Civilian-aligned | watches from high ground | sells tips to CG or smugglers (may lie) | cross-checking tips |
| Salvage crew | Independent | follows wrecks | recover floating cargo, sell to highest bidder | CG claims, raider hunting |
| Coast Guard | Law | patrol, intercept, rescue, inspect | maintain trust, safety | false positives lower trust |
| Medic / Firefighter / Lifeguard | Service | respond to injury, fire, swimmers | keep the cove running, neutral to all factions, collect casualties of all sides | can be misdirected by false alarms |

### Objective-competition rules (proposed)

1. Every claimable thing (crate, site, boat, cache) has `owner` and `claimedBy` with a timeout lease (extend the existing 25 s crate lease, 5403).
2. Claim priority: emergency > owner faction > ally > neutral > hostile; ties break by distance, then random.
3. Contests resolve by presence: a site/yard flips owner if a rival has >=2x people within 10 m for 20 s and no defender; no deaths, only "driven off" (they walk away, stunned for 10 s).
4. Cargo is conserved (no creation outside player and scenario spawners); ownership changes by carrying across yard borders.
5. Detection: any act against an owner is visible within the line-of-sight map; unseen acts create no rumour.
6. Deceit: cover holds while behaviour matches `shownRole`; any contradicting act adds suspicion; reveal at threshold; false accusation lowers civilian trust and raises smuggler boldness.
7. Casualties: always knocked out, collected by that side's medics (existing `updateThreats` 5292-5296 pattern), no gore; and medics are neutral to all.
8. Hazards outrank goals: lightning, flood, fire, lava and ice cause all factions to abandon objectives (reuse the danger override at 5448).

## Appendix: key line index

- Roles list 1733; palette roles 1607-1620; people spawn 1812; person model 1757.
- POIs: `computePOIs` 5373, `pickPOI` 5396, `viewSpot` 5389, `safeSpot` 5368, `peak` 5375, lighthouse 1263-1289.
- Sites: `SITE_INFO`/`addSite` 5344-5352, placement 1654, load 3578.
- Agents: `think` 5409, `updateAgents` 5434, `freeCrate` 5401, `yardPt` 5406, `agentUnsafe` 5408, `stepFerry` 5498, `openPeople` 5505.
- Fleet/threats: `spawnThreat` 5276, `updateThreats` 5283, `isCG`/`isHostile`/`factionOf` 5300-5302, `updateFleet` 5305, `openFleet` 5339; boat combat scan 2524.
- Update loop call site: 3417. Prefs: 4619, 4635-4636. TRIES: 1535 (12 tries; none about NPC objectives).
