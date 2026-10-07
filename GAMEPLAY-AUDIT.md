# Squall Cove: gameplay audit of Battle mode and the sandbox

Read-only audit of `index.html` (v8.9+ battle depth). Nothing was run in a browser. Line numbers are `index.html` lines from Grep. Numbers marked **[calc]** are computed straight from code constants; numbers marked **[model]** come from a crude node model (`scratchpad/sim.mjs`, copies the capture, bleed, ticket, respawn and planBattle rules, but uses a rough movement and duel model with 40% fire uptime and 70 m sight), so read them as order of magnitude and direction, not as measurements. Feature presence is in AUDIT-FEATURES.md and UX in UX-AUDIT.md; this file is about how it plays.

---

## 0. Headlines

1. **The player can end any battle alone, for free.** The tablet's "Fire control" block (L4774, `fc(...)` rows -> `fireAt` L4721 -> `fireOne` L4705) has no cooldown, no ticket cost and no battle gate: bombs (dmg 240, kill radius 9 m at Medium, 19 m at Large), artillery, mortar, air strike, Griffon and gunship cover, lightning storm, all repeatable every tap. The cooldown-protected "Support for your side" rows (L4780) are only the second menu. One tap on "Hot spot" + Bomb + Large + Ring pattern clears a point.
2. **Tickets are a fixed 80 whatever the army size** (L4381). At 9 a side a battle is 10 to 12 minutes AI against AI **[model]**, at 30 a side about 5 minutes, at the slider maximum of 70 a side about 3 to 4 minutes. A bigger battle is a shorter battle.
3. **The AI has no defence below 13 bots a side** (`planBattle` L4781: defenders only for `squad % 4 === 3`, which needs bot index 12 or more). At the default 9, all three squads attack, and every point is taken by whoever walks in. At any size, 3 of every 4 squads only ever head for the 3 nearest non-owned points.
4. **One-sided by map, not by luck** **[model]**: with identical AI, one side wins 35 of 40 on Port, 34 of 40 on Urban and 27 of 40 on Desert (swapping the team labels flips the winner, so it is geometry, see 1.5). In the model Red/Raiders wins Port and Urban, Blue wins Desert at size 5, Red at 9+.
5. **The player is a 15-times soldier.** Rifle TTK 0.48 s hitscan, 100 hp, 3 hp/s regen, instant free respawn at any owned point. A bot rifleman needs about 7 to 11 s to kill a standing player at 30 to 100 m **[calc]**. One human outkills the nine bots on their side.
6. **Gunship and strike aircraft are balance outliers, and a manned AA gun deletes them.** AI gunship 64 dps minigun + 150 dmg shell every 4.5 s, 85 s life, picked from a hot spot with no counter other than a crewed AA gun (crew dies first). A player manning an AA nest does 170 dps, no heat, no ammo: a gunship in 2.2 s (L3633).
7. **Spectating blue is lopsided:** `airAuto` (L4645) and the battery auto-fire (L5128) skip `BATTLE.team`, which defaults to `'blue'` even when nobody is playing, so in "watch the battle" only Red calls air, artillery, paras, boats.
8. **"Reinforcements" cost the losing side tickets twice.** `paraWave` (L4634) debits 1 ticket per trooper, then each trooper costs another ticket when knocked out; `updateEvents` (L5118) fires it when tickets < 28, accelerating the loss.
9. **Match end is a toast and a freeze.** `BATTLE.over` stops `botThink` (L4797) so bots stand where they were; there is no end screen, no restart prompt, no stats.
10. Good: rubber-banding on AI air calls exists (55 percent vs 25 percent), supply crate race, weather and counter-attack events are well scaled, bot cover/peek/suppress logic is genuinely decent. The problems are rules and numbers, not the AI's moment-to-moment behaviour.

---

## 1. Core loop and objectives

### 1.1 How a battle is won (all from code)

| Rule | Where | Value |
|---|---|---|
| Starting tickets | `battleStart` L4381 | **80 each**, regardless of `BATTLE.size` (default 9 desktop, 5 touch, slider 3 to 70 / 10) |
| Knock-out cost | `downPerson` L4428 | 1 ticket to the knocked-out person's side, for anyone (bot, crew, landing boat troops, civilians with a side, the player) |
| Win | `updateBattle` L4808 | a side reaches 0 tickets |
| Bleed | `updateBattle` L4805, every 8 s | `lead = ownedPoints(A) - ownedPoints(B)`; if `lead > 1`, the other side loses `lead - 1` tickets |
| Capture ring | L4800 | radius `p.r = 16` (L4376), counts every non-ragdoll, non-riding, non-swimming person with a side, **including crew bots and the player** |
| Capture speed | L4801 | `prog += clamp(nb-nr, -4, 4) * 0.11` every 0.5 s; owner flips when `|prog| > 0.5` |
| Stall | L4801 | exactly equal counts (`nb && nr && |nb-nr| < 1`) freeze progress |
| HQ rule | L4801 | an hq cannot flip while its owner holds any other point (`hql` note) |
| Respawn | L4807 | every 2.5 s each side spawns one bot if alive (non-crew) < size and tickets > size - alive. Free (the death already paid) |
| Match end | L4808 | toast "Open the Battle tab to play again", `BATTLE.over = true`, bots frozen |

**Capture times [calc]** (clamped net count n, starting with `prog` = +1 owned, 0 neutral):

| Net attackers | neutral -> yours | owned by enemy -> neutral | owned by enemy -> yours |
|---|---|---|---|
| 1 | 2.5 s | 2.5 s | 7.0 s |
| 2 | 1.5 s | 1.5 s | 3.5 s |
| 3 | 1.0 s | 1.0 s | 2.5 s |
| 4 (cap) | 1.0 s | 1.0 s | 2.0 s |

**Reading:** capturing is nearly instant. A single unopposed soldier flips a neutral flag in 2.5 s and an enemy flag in 7 s; the clamp at 4 means a crowd above 4 net gains nothing (at 70 a side, 20 bots crowding one flag is waste). Capturing is a binary "anyone standing there", not a contest. The real defender's advantage is the **stall rule**: one defender cancels one attacker completely, so a lone sniper cannot be removed by a single rusher. Because crew bots count (the AA gun sits 15 m from its flag, inside the 16 m ring, `layAA` L4579, `d = 15`), a crewed AA nest is a permanent +1 defender on every held point: an attacker needs 2.

**Bleed rates [calc]** (`lead - 1` per 8 s): lead 2 = 0.125/s, lead 3 = 0.25/s, lead 4 = 0.375/s, lead 6 = 0.625/s. On Port (9 points) a 6 to 3 hold bleeds 2 per 8 s: 80 tickets lasts 320 s, versus kills that burn about 10 tickets a minute at 9 a side **[model]**. Bleed is therefore a secondary clock until a lead of 4+ (Urban has 11 points, so lead 6 is reachable). At 70 a side kills dwarf bleed completely.

### 1.2 Expected battle length [model, AI against AI, no player]

| Map | size 5 | size 9 (default) | size 30 | size 70 |
|---|---|---|---|---|
| Port | 15 min | 10 min | 4 min | 3 min |
| Urban | 16 min | 12 min | 6 min | 4 min |
| Desert | 15 min | 12 min | 6 min | 4 min |

p10 to p90 at size 9 is roughly 6 to 14 min. Sensitivity: halving the duel fire uptime (more cover play) roughly doubles these times. First contact is not before 60 to 120 s (see 1.4). **With a human playing, expect 4 to 6 minutes at size 9** (the player alone kills several times faster than 9 bots, see 3.1).

### 1.3 Snowball and comeback

* No comeback for the side that is behind except (a) AI air-call probability 0.55 vs 0.25 (L4647, good) and (b) reinforcements at tickets < 28, which **cost** tickets (L4634, L4637 `BATTLE.tickets[team] -= 1`, `updateEvents` L5118). Net effect: a side at 27 tickets spends 5 on paratroopers and 0 on boats (`boatWave` is free) and still pays 1 more per para when they die. Remove the debit (change 4).
* Spawns snowball: `spawnPointOf` (L4399) picks a random **owned** point, so the side holding forward points spawns at the front and the side that lost them spawns far back. Combined with the HQ rule (hq can't flip until nothing else is held), the loser is not locked out, but its respawn walk is 2 to 4 times longer.
* **AI against AI is decided by geometry [model, swapping labels flips winners]:**
  * Port: Port/Blue has 4 nearer neutrals (strongpoint, depot, radio, plain, avg 229 m) vs Raiders 1 (battery, 183 m). Yet Red wins: `planBattle` sends squads 0 to 2 to the three closest non-owned points from the side's base centroid. Red's three (Quay East 183 m, East farm 220 m, Town centre 294 m) are clustered in the east; Blue's three (Town centre 117 m, Landing beach 258 m, Lighthouse 307 m) pull Blue's 9 bots three ways, one to the far west lighthouse. Red wins local numbers (Lanchester).
  * Urban: Blue's squad 0 target is the Container terminal **4 m from its base centroid** (a free capture, then it idles), Red gets 4 nearer neutrals incl. the battery (free barrage) and the radio. Red 34 of 40.
  * Desert: roughly even (3 v 3 neutrals); Blue wins at size 5, Red at 9+.
* The human tips it: the player's team gets `BATTLE.plan` (wantAtt/wantDef, L4783) but only if the player edits it, and the player's squad (4 nearest bots) follows or holds.

### 1.4 Dead time: travel [calc]

Speeds: bot walk 1.45 m/s, bot run 3.19 m/s (`q.run`: 1.45 x 2.2, L3251; bots set `q.run = true` whenever not in a fight), player walk 3.3, player sprint 6.4 (L3679). Route factor 1.3 assumed. There are **no ground vehicles in battle** (only boats from the landing waves), so travel is on foot.

| Map | base to base (straight) | bot run | bot walk | player walk | player sprint |
|---|---|---|---|---|---|
| Port | 301 m | 123 s | 270 s | 119 s | 61 s |
| Urban | 504 m | 205 s | 452 s | 199 s | 102 s |
| Desert | 557 m | 227 s | 499 s | 219 s | 113 s |

Typical point distances (bot run): Port Quay West to Town centre 72 s, to East farm 180 s, to Lighthouse 76 s, to the far Mountain lake 129 s; Urban from either quay to Market quarter 58 to 126 s, to Hill park 169 to 203 s; Desert from Port quay to Dune ridge 84 s, Oil pump 86 s, Radio outpost 227 s. Mean inter-point distance is 330 to 340 m on all three maps (about 140 s at bot run). With the standard 3 contact points per side a bot spends **1 to 2 minutes walking before the first shot**, then fights, then (if it dies) respawns at a random owned point and walks again. The player skips all of this: `deploy` (L4819) teleports to any owned point instantly, and sprint is twice the bot's speed.

Fairness issues: the player has no respawn delay, so dying costs 1 ticket and about 2 seconds of menu clicking (`deployMenu` L4815). That is cheaper than a bot's 60 to 200 s walk.

### 1.5 Capture fairness

* Lone-bot flip speed (7 s) plus equality stall makes "sneak a sniper to the flag" a valid but only half-working tactic: stalls only if a defender is alive in the ring.
* The ring is 16 m radius and the cover (`layCover`, L4388) sits at 8 to 12 m from the flag, so cover is inside the ring, good.
* Ring crowding: bots choose a random target within 10 m of the point (L4531), and the clamp makes extras useless. At 70 a side up to 20 bots stack on 3 flags.
* Crew bots count for capture (the AA and mortar posts sit within about 15 to 18 m).
* Civilians? Removed at battle start (L4382), fine.

### 1.6 Support and fire power table

All values [calc] from code. Kill radius = distance where `dmg*f + 20 >= 100` (`blast`, L4670: `hurt(q, dmg*f + 20)`, `f = 1 - d/R`; everyone inside R takes at least 20, friend and foe alike, owner null).

| Source | Where | Damage / cadence | Kill radius | Cooldown | Cost | Note |
|---|---|---|---|---|---|---|
| Rifle shot (bot) | L4460 | 21 at point blank x accuracy 0.52, 0.5 to 0.7 s per shot | single | - | - | see 3.1 |
| Grenade (player / bot) | L4760 | 150, R8, fuse 3.2 s (player) | 3.7 m | player 0.9 s throw, 3 carried (reset each respawn L4822); bots about 1 per 30 s when engaged | none | bots have no friendly check (L4448) |
| Satchel/C4 | L4764 | 230, R11, all placed charges at B | 7.2 m each | 0.7 s place, 3 carried | none | |
| RPG | L5167 | 170, R9, homes on aircraft inside 0.97 cone | 4.8 m | 4.2 s reload, 1 round | none | only 1 per mag |
| MG nest, AI crew | L4588 | 5 dmg per 0.12 s at 10 percent hit = 4 dps, range 55 m | - | - | crew bot | effectively decorative against infantry |
| MG nest, player manned | L3633 | 20 per 0.1 s hitscan = **200 dps**, range 260 | - | none | none | stronger than any rifle |
| AA gun, AI crew | L4586 | 15 x 30 percent per 0.16 s = 28 dps, range 340 | - | - | crew alive | gunship (380 hp) dies in 13.5 s if crew survives |
| AA gun, player manned | L3633 | 22 per 0.13 s = **170 dps**, range 700, no miss roll (ray tolerance 1.1 x radius) | - | none | none | Griffon 0.7 s, gunship 2.2 s, jet 0.4 s |
| Mortar pit, AI | L5006 | 3 shells x 100, R6.5 | 1.3 m | 15 s | crew | needs squad hints; scatter 12 m; weak |
| Mortar pit, player | L5006 | 2 shells x 100, R6.5 | 1.3 m | 10 s | none | range 35 to 330 m |
| Battery barrage | L5025 | 5 x 160, R11 | 5.5 m each | 80 s (shared, free) | hold a battery point | AI auto-fires, `BKIT.aiT` L5128 |
| Artillery (tablet) | L4695 | 6 x 160, R11, scatter 12 m, 0.9 s apart | 5.5 m each | 70 s; plus banked calls from crates (`BKIT.bank`) | none | |
| Air strike (tablet) | L4689 | 5 bombs x 220, R12, 16 m apart in a line | 7.6 m each | 85 s | none | jet hp 70, flies 540 m run-in |
| Griffon | L4551 | 8 x 0.38 per 0.11 s = 28 dps (19 moving), range 95, hp 120 | - | 70 s | none | 70 s on station |
| Gunship | L4562 | minigun 9 x 0.5 per 0.07 s = **64 dps (45 moving)**, range 150, plus a **150 dmg R11 shell every 4.5 s** on the nearest enemy; hp 380, 85 s on station, flies at 165 m | shell 5.1 m | 140 s (93 s with an airfield) | none | by far the strongest single call; it targets nearest enemy anywhere on the map |
| Paratroops | L4634 | 5 to 7 bodies | - | 90 s | **1 ticket each** | extra bodies, but each later costs a second ticket |
| Boat landing | L4641 | 8 men in 2 boats | - | 120 s | free | `q.ride` men are untargetable until landed |
| Fire control Bomb (player) | L4713 | 240 x m, R14 x m | 9.3 m (Medium m=1), **19 m (Large m=1.7)** | **none** | none | Ring and Scatter patterns multiply it by 6 to 7 |
| Fire control Missile | L4711 | 210 x m, R12 x m | 7.4 m | none | none | |
| Fire control Arty / Mortar / Strike / Gunship cover | L4719 | the tablet versions without cooldown | | none | none | gunship cover spawns a **fresh gunship** (+25 s life) with no `AIR.cd` check |
| Lightning storm | L4708 | 7 bolts x 150 x m, R5 x m, +/-28 m | 2.5 m each | none | none | |
| Air raid (AI event) | L5096 | free strike or gunship (+10 s) alternating sides, every 170 to 260 s | | event timer | none | not cooldown-tracked |

**Outliers:** (1) the whole fire-control block (unlimited); (2) gunship and its shell (a single call is worth about 20 to 40 percent of a side's 80 tickets at size 9: 85 s x about 0.4 kills/s at the minigun's 45 to 64 dps plus up to 19 shells); (3) manned AA and MG (no heat, no ammo, 170 to 200 dps); (4) strike run (5 x 7.6 m kill circles in a line, wipes a squad on a point); (5) AI mortar (needs 2+ hints, rarely fires, harmless); (6) battery barrage is free and strong but only one barrage per 80 s.

### 1.7 Events and pacing [calc, `updateEvents` L5110]

| Event | First | Repeat | Scale |
|---|---|---|---|
| Counter-attack (L5062) | 20 to 40 s after a flip | each flip | the nearest squad (>= 2) of the loser, forced for 75 s; plus 4 paras if the side holds an airfield |
| Supply drop (L5074) | 95 to 135 s | 150 to 210 s after the previous is gone, crate lives 240 s | refills bots within 120 m, resets the player's grenades, +1 banked artillery call; `sendSquad` both sides for 60 s |
| Air raid (L5096) | 130 to 170 s | 170 to 260 s, sides alternate | 55 percent strike, 45 percent gunship (+10 s) on the opponent's hottest point |
| Weather (L5101) | 170 to 230 s | 240 to 330 s after clearing; lasts 150 to 210 s | fog (sight x0.55, air accuracy x0.55) or rain (sight x0.75, air accuracy x0.7) |
| Reinforcements (L5118) | at tickets < 28 | every 50 s | 5 paras (-5 tickets) plus a boat wave (free) |
| AI air calls (`airAuto` L4645) | 10 s | every 14 to 24 s: 25 percent (leading) / 55 percent (trailing) to act; gunship after 90 s, arty 80 s, strike 100 s, boats 60 s | roughly one air action per 40 to 75 s per AI side |

At 9 a side over a 10 minute battle you get about 4 supply drops, 3 raids, 2 weather cycles and 10 to 20 AI air actions. That is a lot of heavy ordnance for 18 soldiers; at 9 a side the aircraft are the main killers, not the infantry.

---

## 2. Bot behaviour

### 2.1 Decision loop (`botThink` L4473), priority order

1. Ragdoll: mark dead, remove after 16 s (L4475). Riding/hopping/hp<=0: skip.
2. Crew (`b.crew`): `crewThink` L4974, stand at the post, do not fire personally.
3. Timers; morale +0.02/s, -0.03/s under 40 hp (L4478).
4. **Stuck watchdog** every 4 s (L4479): if a `q.order` exists, the bot is not at cover and has no target, and it moved < 2 m or got no nearer in 8 s, it drops the order, walks 16 m in a random direction, and after 3 failures clears `b.obj`.
5. **Morale < 0.3** (L4481): retreat to a random owned point for 12 s, drop target, run. Morale resets to 0.6 so each bot retreats only after about 5 nearby deaths. It cannot fire back while retreating.
6. Scan every `0.25 + rand(0.15) + min(0.5, people*0.003)` s (L4486); mean reaction 0.38 s at 18 people, 0.82 s at 170 [calc].
7. **With a target:** share a hint with the squad every 1.5 s (L4491); suppression crouch if `supp > 0.65`; grenades at 9 to 30 m; if 6 < d <= 0.8 range, run to cover found by `findCover` (within 32 m, behind a prop from the enemy), then peek 0.9 to 1.9 s up, 1.1 to 2.9 s down (about 40 percent fire uptime); otherwise tactics `push` (40 percent), `flank` (25), `hold` (35), or sniper `hold`; squads of 2+ do fire-and-move bounding (3.2 s phases, L4506); strafes randomly every 0.5 to 3 s.
8. **Medic** (L4516): nearest fallen friend within 60 m killed within 12 s, 2.2 s revive to 45 hp (1.4 s with a depot). **No ticket refund** (`+ 0`, L4517), whereas the human's `fpRevive` gives +1 (L5164): the human medic is a ticket engine, the AI one is not.
9. Hint investigation (L4520): walk to a squadmate's last contact within 10 to 70 m, only if no order and not following.
10. Objective walking (L4531): follow the squad leader if within 60 m (formation offsets), otherwise walk to a random point within 10 m of `b.obj`, re-picking every 1.5 to 4 s.

### 2.2 Failure modes found

| # | Problem | Evidence | Severity |
|---|---|---|---|
| 1 | **No defenders below 13 bots a side.** Squad 3 is the first defender squad and needs index >= 12 (`squad % 4 === 3`, L4786). All three squads walk off to attack. Also only the nearest 3 enemy points are ever targets (`enemy[min(squad%3, len-1)]`, L4787), so at 70 a side 17 squads pile onto 3 flags | L4781 to L4789 | high |
| 2 | **Squad identity is an array index.** `planBattle` assigns `sq = floor(i/4)` over `people.filter(...)` order every 12 s **and on every spawn** (L4807 calls `planBattle`); one death shifts every later bot into a different squad and re-targets them. Squad cohesion is weak and `sqi` leader roles hop | L4783, L4807 | medium |
| 3 | **Shooting through walls:** `senseEnemy` -> `losFull` (L4410) samples the segment every 3 m against prop boxes; boxes narrower than 3 m (fences, sandbags, wire, thin walls) are skipped most of the time. Worse, `botFire` (L4460) has **no obstruction test at all**: once `b.tgt` is set the bot keeps shooting for up to a full scan interval (0.4 to 0.8 s) after cover or a wall interrupts the line, and bullets hit by probability only. Terrain LOS (`los` L7858) uses 11 samples | L4410, L4460 | medium |
| 4 | **Cover works by AI choice, not by physics.** Bullets never collide; a bot behind a sandbag is safe only because the shooter's `losFull` fails or the bot crouches. The player's hitscan (`fpAim`) does collide with props, so the player is treated differently to the bots | L4460 | medium |
| 5 | **Perfect accuracy at range:** sniper bots use base accuracy 0.75 (L4462) vs 0.52 for everyone else, and the falloff `1 - 0.65 d/range` over a 600 m range makes it 0.57 at 200 m with 67 damage: two hits kill. Sniper sight is 200 m (L4456) against 85 m for rifles, so a sniper bot hits targets that cannot see it. At 200 m the sniper bot does 10.5 hp/s, rifle 4 hp/s | L4456, L4462 | medium |
| 6 | **No friendly fire handling:** bullets cannot hit friends (tracer goes to the target), but blasts, grenades, mortar, artillery, gunship shells all damage everyone (`owner: null`) and no thrower checks for friends in the radius (grenade L4760, `throwNadeAt`). The AI mortar checks 14 m around the target for friends (L5003) but not its 12 m scatter | L4670, L4748 | low |
| 7 | Stuck watchdog is **disabled while the bot has a target** (`!b.tgt`, L4480) and while at cover. A bot that senses an enemy through a thin wall and chooses unreachable cover can loop on the wall, relying on `detourAround` (L2763) | L4480 | low |
| 8 | **Crew bots are sitting ducks:** crew do not shoot back (`crewThink` returns before `senseEnemy`), they stand still at a known point inside the ring, and the MG does 4 dps. An enemy squad that reaches a held point kills the crew first. When the crew dies the gun is quiet until an idle friend arrives (`crewTick` L4982: only bots with no target and not following) | L4974 | medium |
| 9 | Morale retreat sets `b.tgt = null` and runs for 12 s (about 38 m) then turns back: low value, looks like jitter | L4481 | low |
| 10 | Medics revive only if no target is visible, so they never revive under fire; revive window 12 s while bodies persist 16 s; AI revive gives no ticket back | L4516 | low |
| 11 | Revived bot plus the 2.5 s respawn can overfill the side (the respawn counts alive non-dead, revive flips `dead` false later) | L4807 | cosmetic |
| 12 | Hint/alert is only shared inside the squad (4 bots) and by sight; gunfire and explosions do not alert anyone, so a lone bot a few metres from a firefight does nothing | L4491 | low |
| 13 | **Landing-party troops are not bots** (they use the older `armedLayer`, L4440s: `q.gun`), so they ignore squads, cover, morale, objectives and still cost tickets; `q.ride` troops cannot be targeted | L7173 | low |
| 14 | At match end bots stop thinking mid-stride (L4797) | L4797 | cosmetic |

### 2.3 Perception

* Rifle bots see 85 m in a cone (dot > 0.15, about +/-81 degrees) beyond 22 m unless alerted; within 22 m they see all around. Snipers 200 m. Fog multiplies by 0.55 and rain by 0.75 (`BKIT.sightK`, L5104). **Night and dusk do nothing** (no read of `wx.sky` in `senseEnemy`), so time of day has no effect on gameplay.
* Prone player: eye line 0.35 m (L4457) makes LOS harder, and the bot's hit chance multiplier is [1, 0.8, 0.55] for stand/crouch/prone. Prone is a strong option: 0.55 x hit chance, spread x0.45, but speed x0.2 (0.66 m/s).
* Player visibility while moving: `moving` only reduces hit chance by 0.7, not detection.

### 2.4 Per-frame cost at 70 a side

Counts: 140 bots plus about 14 crew plus the player is about 160 people (`MAX_PEOPLE` 170, L2482); props 700 to 1500 (scenery capN 320 plus tiny 170, plus cover about 55 and up to 190 structures).

| Hot spot | Code | Cost [model, node microbenchmark, desktop JIT] | Notes |
|---|---|---|---|
| **`pushOutOfProps` per person per frame** | L3268, L2763 | 2.6 ms at 1000 props, 3.8 ms at 1500 (per frame, 160 people); 0.5 ms at 9 a side | **the largest single cost**; loops every prop for every person; mobile (36 people cap) is about 4x slower per iteration but 4x fewer people |
| `senseEnemy` per bot per scan | L4455 | 0.04 ms per scan, 2.9 scans per frame at 60 fps = 0.12 ms | cheap: the scan interval stretches with population (`+ 0.003*people`), and the distance and cone checks reject most pairs before `losFull` (avg 2 `losFull` calls per scan) |
| `losFull` | L4410 | prop loop with a midpoint reject | cheap |
| `squadOf` | L4469 | rebuilt every 1 s: O(people) plus sorts | cheap |
| Hint broadcast | L4491 | 4 members per bot every 1.5 s | cheap |
| `planBattle` | L4781 | `threat(p)` runs `people.filter` inside a sort comparator per point, run every 12 s and **on every respawn** | about 10k ops per call, but at 70 a side with a respawn every 1 s per side it runs about 1 to 2 times a second |
| `hotSpot` | L4538 | `people.filter` for every point (11 x 160) **per aircraft per frame** (`updateAir` L4620) and per `airAuto` | about 1.8k hypots plus array allocation per aircraft per frame: garbage |
| `updateAAS` | L4586 | 22+ emplacements x people each frame; MG calls `losFull` for each person within 55 m with no throttle before `e.cd` | modest |
| `setFootOrder` / `findFootPath` | L3001 | each strafe (`b.step` 0.5 to 3 s) can recompute a route when `lineBlocked` | unknown cost, probably the next-largest; not measured |
| `capture` loop | L4799 | points x people every 0.5 s | negligible |
| `armedLayer` | L4440 | loops people each frame for non-bot armed people (landing parties) | small |

**Recommended fixes:** (a) a uniform grid (`CELL=16 m`) of props built when props change, queried by `pushOutOfProps` and `losFull`; expected 5 to 10x cut of the 2.6 to 3.8 ms; (b) cache `hotSpot` per team for 1 s; (c) run `planBattle` on a 12 s timer only and mark `BATTLE.planDirty` on spawns, or stop calling it from the spawner; (d) throttle MG-nest person scan to every 0.2 s; (e) cap `setFootOrder` per frame (queue).

---

## 3. Player agency

### 3.1 Weapon table [calc, `WPN` L4348]

| Weapon | Dmg x pellets | Rate s | RPM | Raw dps | Shots to kill 100 hp | TTK (hitscan) | Mag | Range m | Spread | Zoom FOV | Reload s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Pistol | 26 | 0.30 | 200 | 87 | 4 | 0.90 | 12 | 120 | 0.012 | 50 | 1.7 |
| SMG | 11 | 0.08 | 750 | 138 | 10 | 0.72 | 32 | 90 | 0.03 | 46 | 1.7 |
| Rifle | 30 | 0.16 | 375 | 188 | 4 | 0.48 | 25 | 220 | 0.012 | 34 | 1.7 |
| Shotgun | 9 x 8 | 0.85 | 71 | 85 | 2 | 0.85 | 6 | 45 | 0.07 | 52 | 1.7 |
| Carbine (scoped) | 38 | 0.24 | 250 | 158 | 3 | 0.48 | 20 | 320 | 0.0035 | 20 | 1.7 |
| LMG | 14 | 0.075 | 800 | 187 | 8 | 0.53 | 60 | 160 | 0.035 | 48 | 3.2 |
| Marksman | 55 | 0.42 | 143 | 131 | 2 | 0.42 | 12 | 420 | 0.002 | 14 | 2.2 |
| Revolver | 34 | 0.50 | 120 | 68 | 3 | 1.00 | 6 | 110 | 0.01 | 50 | 2.4 |
| Sniper | **110** | 1.30 | 46 | 85 | **1** | 0 (one-shot, any body part; headshot x1.8) | 5 | 600 | 0.0008 | 9 | 1.7 |

Range falloff for the player: `fall = 1 - 0.5 * clamp((d - 0.4 range)/(0.6 range))`, so a rifle still does 15 at 220 m (L3837). Stance: accuracy x[1, 0.7, 0.45], speed x[1, 0.5, 0.2] (L3679).

**Bots against these [calc, `botFire` L4460]:** shot period `rate + bot*(0.7..1.5)` plus a burst pause every 6 shots, hit chance `0.52 x (1 - 0.65 d/range)` x0.7 if the target is moving, damage `dmg x 0.7 x (1 - 0.4 d/range)`.

| Bot weapon | 15 m | 30 m | 60 m | 100 m | 150 m | 200 m |
|---|---|---|---|---|---|---|
| Rifle hp/s (TTK) | 14.5 (7 s) | 13.4 (7) | 11.4 (9) | 9.0 (11) | 6.3 (16) | 4.1 (25) |
| SMG | 7.9 (13) | 6.4 (16) | 3.9 (25) | out of range | | |
| Pistol (medic) | 4.8 (21) | 4.1 (24) | 3.0 (34) | 1.7 (60) | | |
| Shotgun | 4.2 (24) | 2.5 (39) | out | | | |
| LMG (heavy) | 11.6 (9) | 10.5 (10) | 8.3 (12) | 5.7 (17) | 3.1 (32) | out |
| Sniper (accuracy 0.75) | 15.1 (7) | 14.7 (7) | 13.9 (7) | 12.9 (8) | 11.7 (9) | 10.5 (9) |

**Time to kill:** the player kills a bot in 0.5 to 0.9 s (plus aim time). A bot takes 7 to 25 s to kill a standing player (plus 0.4 to 0.8 s reaction), and the player regenerates 3 hp/s after 0.6 s unhurt (L3838). **The player is roughly 15 times as lethal as a bot rifleman and about 10 times as hard to kill.** Prone cuts bot hit chance to 0.55, so the player survives about 12 to 20 s of focused bot fire.

**Class balance:** Sniper one-shots every bot at 600 m (Marksman two-shots at 420): clearly the strongest loadout against bots, since bots have 85 m sight and cannot return fire; shotgun is weakest (range 45, TTK 0.85). Pistol-only kits (Medic) are poor. LMG is a slow-reload bullet hose. Spotter kit has an SMG and revolver, fine. Nothing makes a class feel obligatory; the problem is that there is no "enemy armour" or buildings to demand heavy weapons (RPG has only aircraft or people as targets).

### 3.2 Grenades, charges, AA, RPG

* Grenades: 3 per life, refilled on every respawn (`deploy` L4822: `fp.nades = 3; fp.c4 = 3; fp.smokes = 2`) and at depots. Kill radius 3.7 m, fuse 3.2 s, and enemy bots do not flee them. They are decent for clearing a flag or strongpoint interior but not a game-changer.
* C4/satchel: three charges, all detonate on B. 7.2 m kill radius each; three at a choke point or crew nest is a good squad wipe. Only the Engineer carries a satchel in the loadout; **the `c4` slot exists in the sandbox, unlimited via respawn**.
* AA launcher (`aa`) and RPG: both home on aircraft (cone 0.97). RPG 170 dmg: gunship 3 rockets (4.2 s reload each, about 12 s). The player can counter air; the AI only counters via crewed AA.
* Manning: **E on any friendly gun** (L3633). MG nest 200 dps hitscan is stronger than any rifle and has no ammo or heat, AA 170 dps wipes aircraft. Powerful but static; bots shoot the player there like anyone (no armour).

### 3.3 Tablet fire control (can the player trivialise a battle?) **Yes.**

There are two separate things in `renderTablet` (L4762):

1. **Support** (L4780): `callAir`, `callStrike`, `callArty`, `batteryFire`, `paraWave`, `boatWave`: cooldown-gated (70 to 140 s), shared with the AI's own cooldown table. This is balanced and fine.
2. **Fire control** (L4774): `fireAt(kind, pt)` -> `fireOne`. No cooldown, no ticket cost, no `BATTLE.on` check, targets crosshair, marker or **hot spot** (the point with most enemies, `hotSpot` L4538). Gunship/Griffon cover spawn extra aircraft. With Size Large (m = 1.7, bomb R 24 m dmg 408), Pattern Ring (6 impacts at 380 ms), Aim Exact, and Hot spot, **one tap kills everything within about 40 m of the enemy's busiest point**; repeat every 3 s. Also fire control can strike either team in the god view (`FIRE.team`).

Proposed costs (change 1): in battle, route every fire-control row through a shared `FIRECD` meter; each use costs the **player's own tickets** (`fireOne` kinds: bomb 6, arty 6, mortar 3, strike 8, gunship 15, storm 6, lightning 2, missile 4, flechette 3, cluster 6, incendiary 3, smoke 0, shock 0) and sets a shared 20 s lockout (a 60 s lockout for gunship/strike/Large size). Cheaper alternative: fire control becomes sandbox-only (`!BATTLE.on` or god-view watch mode) and Support is the only battle path.

### 3.4 Respawn flow and spectate

* Death -> `downPerson` -> `BATTLE.down = true`, `deployMenu` (L4815): pick loadout and an **owned** point; `deploy` (L4819) teleports instantly, hp 100, ammo reset, 3 grenades, 3 charges, 2 smokes. No delay, no ticket extra. The four nearest friendly bots are set to follow (`BATTLE.squadMode`).
* Spectate: `specNext` (L5255, bSpec button), overview (`bOver`), `jumpIn` (L5249, becomes that bot with hp >= 70). Fine. One catch: `jumpIn` takes the bot's `botSaved` class and weapon; the bot's squad remains.
* Missing: spawn timer/penalty, spawn selection map (the menu is plain buttons), spawn protection (the player can be shot while the menu is open? `BATTLE.down` blocks fire and spawn happens instantly, so no issue).

---

## 4. Difficulty options that are missing (cheap to add)

All numbers below are hard-coded today. Add one `const DIFF = { tickets: 80, botAcc: 1, botSight: 1, botDmg: 1, ff: 0, night: 1 }` object, persisted with `localStorage`, set from the Battle tab (`renderSide`, L3895 area uses an `rg()` slider helper already).

| Option | Hook | Constant to scale |
|---|---|---|
| Tickets | `battleStart` L4381 | `{blue: DIFF.tickets, red: DIFF.tickets}`; slider 30 to 300; or scale with size: `Math.round(40 + 6 * BATTLE.size)` |
| Bot skill (accuracy) | `botFire` L4462 | multiply `acc` (0.52 base, 0.75 sniper) by `DIFF.botAcc` (0.6, 1, 1.4) |
| Bot reaction | `botThink` L4486 | scan interval `0.25 + rand(0.15)` x `DIFF.react`; cheap and very noticeable |
| Bot damage to player only | `botFire` L4465 | x`DIFF.dmgToPlayer` when `fp.p === e` (0.5, 1, 1.5) |
| Bot sight | `senseEnemy` L4456 | `85 * BKIT.sightK` -> `85 * BKIT.sightK * DIFF.botSight` |
| Enemy count different from yours | `battleStart` L4384, spawn L4807 | split `BATTLE.size` into `sizeBlue` and `sizeRed` |
| Friendly fire | `hurt` L4419 / `botFire` | for gunfire add `friendlyFire` flag; for blasts already on. A cheap switch: in `blast` L4670, if `!DIFF.ff` and `o.owner team` set, skip same-team |
| Time of day | `senseEnemy` L4456 | `BKIT.sightK *= wx.sky === 'night' ? 0.5 : wx.sky === 'dusk' ? 0.75 : 1` in `updateEvents` |
| Air support from AI | `airAuto` L4645 | `DIFF.air` multiplies the 0.25 / 0.55 act probability, and `c.gs` cd |
| Time limit | `updateBattle` L4808 | `BATTLE.t > limit` ends with a decision on tickets then points held |

---

## 5. Fun factors versus Ravenfield / Battlefield-lite, by value for effort

| Rank | Feature | Status | Effort | Value |
|---|---|---|---|---|
| 1 | **End-of-round screen**: winner, time, kills, deaths, points captured, MVP, "Again / Menu" | toast only (L4808) | S (about 40 lines, reuse `bSpawn` overlay) | very high |
| 2 | **Kill feed** (top-right, last 5: "You > Raider", "Gunship > Guard") | `BATTLE.feed: []` declared (L4364), never used | S | high |
| 3 | **Visible hit marker + damage direction** on the HUD (there is only `Snd.ui('ui_hitmarker')` at L3837 and a red vignette `bHurt`) | partial | S | high |
| 4 | **Tickets/time options + match end condition** (see section 4) | missing | S | high |
| 5 | **Scoreboard** (player kills, deaths, captures, assists, squad list) | `fp.ko` only | M | medium-high |
| 6 | **XP / ranks** (per kill 10, capture 50, revive 25; unlock loadouts or cosmetic skins) | missing | M | medium |
| 7 | **Spawn map with point choice, spawn delay of 3 to 5 s** | plain buttons | S | medium |
| 8 | **Vehicle spawn** (jeep/boat at hq; Ravenfield's biggest fun factor) | no ground vehicles in battle | L | high, but costs travel-time fixes too |
| 9 | **Commander map** (tablet map with unit dots, point control, order squads) | god-view overview exists with radio mast markers; squads can't be ordered from it | M | medium |
| 10 | **Replays / kill-cam** | missing | XL | low per effort |

---

## 6. Prioritised changes (20)

| # | Change | Function(s), lines | Suggested constants |
|---|---|---|---|
| 1 | **Gate the fire-control rows in a battle**: shared meter + ticket cost, or sandbox-only | `renderTablet` L4774 `fc(...)`; `fireAt` L4721; `fireOne` L4705 | `FIRECD = {t: 0}`; lockout 20 s (60 s for gunship/strike or `TAB.size === 2`); ticket cost on `BATTLE.tickets[BATTLE.team]`: bomb 6, arty 6, strike 8, gunship 15, storm 6 |
| 2 | **Scale tickets with army size** and make them an option | `battleStart` L4381 | `tickets = Math.round(40 + 6 * BATTLE.size)` (9 -> 94, 30 -> 220, 70 -> 460) or `DIFF.tickets` |
| 3 | **Give the AI defenders at every size**: always at least one squad (or half of bots) on defence; distribute attackers over all non-owned points, not just 3 | `planBattle` L4786 | defender if `squad % 3 === 2` (any size); attack index `squad % min(4, enemy.length)`; cap attackers per point at 4 + 2 |
| 4 | **Stop charging tickets for reinforcements** | `paraWave` L4637 | delete `BATTLE.tickets[team] -= 1`; if kept for balance make it `0.5` |
| 5 | **Fix spectator asymmetry**: AI calls air for both sides when nobody is playing | `airAuto` L4647; `updateKit` L5128 | skip `team === BATTLE.team` only `if (fp.on || BATTLE.team)` flag; set `BATTLE.team = null` in watch mode |
| 6 | **Nerf the gunship and cap it**: shell every 7 s, minigun 6 dmg, `life` 55, a hard cap of 1 gunship per side, and AA gun range bonus | `airSpawn` L4551 (`hp 380 life 85`), `airFire` L4562 (`gun ? 0.07, 9, 4.5`), `callAir` L4558 (`140` cd), `airRaid` L5096 | minigun 6 dmg per 0.09 s; shell 7 s; `life` 60; cd 180; `AIR.list.some(u => u.kind==='gunship' && u.team===team)` -> refuse |
| 7 | **Heat or ammo for manned AA/MG**, and an AA-gun damage cap per second | `fpManFire` L3633 | `e.heat += 0.12; if (e.heat > 1) lock 2.5 s`; AA 22 -> 14, rate 0.13 -> 0.2 (dps 70) |
| 8 | **Add an end-of-round screen** with stats and "play again" | `updateBattle` L4808; new `endScreen()` using `$('bSpawn')` | store `BATTLE.stats = {kills, deaths, caps, revives, t}`; freeze AI via `BATTLE.over` already |
| 9 | **Kill feed + visual hit marker** | `downPerson` L4426 (push to `BATTLE.feed`), `fpFireGun` L3837 (add `#hitm` element flash 0.15 s); `battleHud` L4812 render | `feed.length <= 5`, each 6 s; hit marker white X, headshot red |
| 10 | **Reduce capture trivialness**: slow flips, make the contest meaningful | `updateBattle` L4801 | `0.11` -> `0.05` per step (neutral 5.5 s for 1, 2.5 s for 3); net clamp 4 -> 6; lone-bot unopposed flip about 11 s |
| 11 | **Fix `planBattle` index-based squads**: assign `sq` at spawn, and never reindex | `spawnBot` L4400, `planBattle` L4783 | `q.bot.sq = team + Math.floor(BATTLE.spawnN++ / 4)`; remove the `i/4` assignment and the `planBattle()` call in the spawner |
| 12 | **Spatial grid for `pushOutOfProps` / `losFull`** | L2763, L4410, L3268 | 16 m cells, rebuild when `props.length` changes; also helps `losFull` for thin boxes |
| 13 | **Bullet obstruction + thin-wall LOS**: sample every 1 m for boxes narrower than 3 m, and test a ray once per shot | `losFull` L4410, `botFire` L4460 | `n = Math.ceil(d / (thin ? 1 : 3))`; in `botFire` if `!losFull(...)` skip the shot (cost one more `losFull` per shot, about 10 per frame) |
| 14 | **Human and AI medic parity**; revives return the ticket for both, or neither | L4517 vs L5164 | `+ 1` in both; or `+ 0` in both with the player's revive as pure body |
| 15 | **Spawn delay and loadout on respawn** for the player | `deploy` L4819 | 4 s countdown shown in the `bSpawn` overlay (no timers shown elsewhere; Robert's dyslexia preference means a plain "Deploying..." label, not a countdown) |
| 16 | **Difficulty object and sliders** | new `DIFF`, `renderSide` L3895, `botFire` L4462, `senseEnemy` L4456, `scan` L4486, `battleStart` L4381 | `botAcc` 0.6/1/1.4; `react` 1.5/1/0.7; `botSight` 0.75/1/1.25; `dmgToPlayer` 0.5/1/1.5 |
| 17 | **Night and weather affect sight** | `updateEvents` L5110 | `BKIT.sightK *= {night: 0.5, dusk: 0.75, dawn: 0.8}[wx.sky] || 1` |
| 18 | **Cache `hotSpot` and cull `planBattle` cost** | `hotSpot` L4538, `updateAir` L4620 | memoise per team per 1 s: `HOT[team] = {t, pt}` |
| 19 | **Raid and AI air events should respect cooldowns** | `airRaid` L5096 | require `AIR.cd[A].st <= 0` / `.gs <= 0` and set them; otherwise raids are free extras on top of `airAuto` |
| 20 | **Fairer starting geometry**: Urban Container terminal (4 m from Blue's base centroid) and Port's three-way split | `BATTLE_MAPS` L877 to L899 | move Urban `Container terminal` to z = 190 ... or make it a blue-owned start point; give Red a matching neutral; on Port move `Lighthouse` target to be rarely first (sort by distance from **front-line centre**, not base centroid) in `planBattle` L4784 |

Items 1, 2, 4, 5, 8, 9 are each under a day and remove the biggest player-facing problems; 3, 6, 10, 11 are the next block (AI flow and balance); 12, 13, 18 are the performance and correctness pass.

---

## 7. Method and caveats

* **Read from code:** every constant above. **Computed:** capture times, bleed, travel times (`scratchpad/g2.mjs`), weapon DPS and TTK (`w.mjs`), and a node microbenchmark of `pushOutOfProps`/`senseEnemy` (`bench.mjs`).
* **Model (`sim.mjs`):** crude. Bots walk to their `planBattle` target at 3.19/1.3 m/s, stop at 45 m from the nearest enemy within 70 m, apply the real DPS formula at 40 percent uptime, capture and bleed with the real rules, respawn as the real spawner does. It ignores cover, suppression, medics, crews, aircraft, events and terrain. The *winner bias by map* result survived a team-label swap (so it is geometric); the exact win fractions and lengths should be checked by logging real battles (add a dev-only counter that prints `BATTLE.t`, tickets and point flips at `BATTLE.over`, 20 lines).
* Not checked: findFootPath cost, rendering, sound, `troops2` loading.
