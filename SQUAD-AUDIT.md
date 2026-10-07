# Squad audit: dynamics and the player's command of squads

Static audit of `index.html` (read, then changed; nothing was run in a browser, so every result below is by reading code). Line numbers were taken before the changes and drift. The sections are: what existed, failure modes, player-control gaps, numbers, then what was changed and the tuning constants.

## 1. What existed

* **Squad identity.** `joinSquad` (once, at spawn) puts a soldier in the fullest living squad of their team that has fewer than 4, else starts a new one: `bot.sq` (id such as `blue3`) and `bot.sqi` (rank, 0 is the leader). A fallen leader is replaced by the next lowest rank because `squadOf` (rebuilt every 1 s) sorts living members by `sqi`.
* **Squad targets.** `planBattle` (every 12 s) gives each squad a point: every third squad defends, the rest spread over the points their side does not own (nearer points take more, 6 squads at most per point). The player's team can override with Attack and Defend toggles in the Command panel.
* **`botThink`** (every frame, per bot). Order of business: stuck watchdog (4 s, drops the order, walks 16 m elsewhere), morale and retreat (morale under 0.3 sends the bot to a spawn point for 12 s), sense enemies every 0.25 to 0.4 s (85 m, 200 m for snipers, wall-checked with `losFull`), then either **combat** (share a hint with the squad every 1.5 s, crouch when suppressed, grenades at 9 to 30 m, cover run-duck-peek, flank or push or hold per bot, fire-and-move by `simT` phase and `sqi`) or **no target** (medic revive, crew post, investigate a squad hint within 70 m, formation behind the squad leader, walk to the objective).
* **Formation.** Followers of a squad leader keep a fixed offset (side by rank, back 3 m plus 1.2 m per rank) when within 60 m of the leader.
* **The player's squad.** On `deploy` the 4 nearest friendly bots get `bot.follow = true` (walk to a random point within 6 m of the player, re-picked every 1.5 to 4 s). `X` toggled follow and hold, `Z` sent them to the crosshair, nothing else. A helicopter boarded by the player takes `follow` bots within 30 m. Ground vehicles did not take the squad.
* **Medics** revive the nearest fallen friend within 60 m for 7 s after the fall; the player's squad got no priority.
* **Voices.** None. Shouts were one sound (`ppl_shout_help` at hp under 35).

## 2. Failure modes found

1. **A squad of "four nearest" is not a squad.** The four were chosen by distance at deploy, never named, never shown, never replaced. When one died the squad shrank for good, and after a respawn a different four could be picked.
2. **Follow was a random walk.** Followers re-picked a random point within 6 m every 1.5 to 4 s: no formation, no facing, and a mate would stand in the player's line of fire. They did not wait for or catch up with a sprinting player. The player runs 6.4 m/s; a bot runs 3.2 m/s on the small map (4.1 on the large), so after 10 s of sprinting the squad was 30 to 60 m behind.
3. **Hold did not hold.** `squadOrder('hold')` set the objective to the spot, but the combat code then pushed, flanked and strafed toward any enemy, so "hold" drifted up to 20 m forward.
4. **Contact sharing stopped at the squad edge.** Only the 4 members of the same `sq` heard a sighting. A soldier 10 m away in another squad stood still next to a firefight.
5. **Orphans.** A squad down to one soldier stayed alone for the rest of the battle.
6. **Retreat went to the spawn point**, often 200 m away, and the player's squad retreated away from the player.
7. **Fire discipline did not exist:** no way to stop mates opening up and giving the player's position away, and the player's own bullets and grenades hurt friends.
8. **No ground-vehicle boarding by the squad** and no way to get them out again.
9. **No feedback:** no callsigns, no health, no status, no marker. The player could not tell who was alive, down or lost.
10. **Medics ignored the player** and wounded mates; they only revived.
11. **AT-class bots (engineers) only fired rockets from `bvThreat` once a second**, with no call-out and no reaction from the squad.
12. **Snipers stood in the open** wherever the objective walk put them; towers were scenery.

## 3. Player-control gaps (before)

Follow, hold, move to crosshair, and nothing else. No attack target, no defend, no cover, no fall back, no suppression, no heal, no mount, no ping, no formation choice, no hold fire, and no way to see or number the squad. The order UI was three rows in the Command panel and two keys.

## 4. Numbers (small map unless noted)

* Bot walk 1.45 m/s, run 3.2 m/s (CELL 2: 1.86 and 4.1). Player walk 3.3, run 6.4. Sight 85 m, snipers 200 m. Rifle range per `WPN`; bot cool-down is `rate + bot * (0.7 to 1.5)`.
* Contact hint lifetime 8 s; hint share interval 1.5 s; stuck watchdog 4 s.
* Fire-and-move phase 3.2 s per half. Medic revive 2.2 s (1.4 s on a held depot) within 2.5 m.
* Old follow slot: random within 6 m. New follow slot tolerance 5.5 m, regroup trigger 35 m.

## 5. What changed (all in `index.html`)

### The player's squad (`SQD`)
* **Binding.** `sqdBind(me)` runs on deploy, on respawn and on jump-in. It takes 3 to 5 (4 on a phone) of the nearest friendly bots within 90 m (up to the nearest ones anywhere if fewer than 3 are close), preferring the previous squad and, after a jump-in, the soldier's old squadmates. Each gets a unique callsign from a pool of 24 first names (`SQD_NAMES`, unique per battle, then a number is added), `bot.psq = true`, `bot.follow = true`, and a slot number. The squad is dissolved by `sqdOff()` when the player leaves first person and rebuilt on the next deploy.
* **Leader.** The player. If the player is down, the first living mate is the acting leader and runs the ordinary soldier AI while the others follow it; on the next deploy the squad is rebuilt. If fewer than 3 mates are alive, `sqdFrame` adopts the nearest free friendly bot within 70 m every 6 s.
* **Orders** (`sqdSet`, the ring, the keys and the Command panel all call it): Follow me, Hold here, Move to my crosshair, Attack that, Defend this point, Take cover, Fall back, Suppress, Heal me, Mount up or Dismount. Formations wedge, line and column (Command panel). Hold fire and free fire.
  * *Follow*: slots behind and beside the player's direction of travel (`SQD.hd`, smoothed). Past 5.5 m from the slot they walk, past 8 m they run; beyond 35 m they call "On you" and run. In contact, **bounding**: while the player moves, half the squad (alternating every 3.2 s by slot) advances to its slot and the other half kneels and fires; while the player stands they all kneel and fire from the slot. Under suppression (over 0.65) they duck, over 0.8 they go prone.
  * *Hold*: each stays exactly where it stood when the order was given, kneels, fires only from there, never advances.
  * *Move*: walk and run to a ring around the mark, snap-firing on the way; at the mark they hold.
  * *Attack*: aimed enemy (or the last ping) becomes `bot.focus`; the ordinary assault code is used (tactic push, preferred range 0.12 of the weapon range, no cover seeking) so they close and shoot.
  * *Defend*: the nearest capture point to the crosshair within 80 m; a ring around it, facing out, kneeling.
  * *Take cover*: each finds a prop between itself and the direction the player faces (`findCover`), crouches, peeks; lapses to Follow after 20 s.
  * *Fall back*: run to a line 14 m behind the player, snap shots only; lapses after 20 s.
  * *Suppress*: for 8 s each fires bursts into the crosshair area (tracers, dust, anyone within 7 m is pinned) and fires at any visible enemy as well; then Follow.
  * *Heal me*: the squad medic (or the nearest free medic within 90 m, who is adopted) goes to the player and heals 26 hp per second until 99 or 70 (the order itself runs 25 s).
  * *Mount up*: mates within reach walk to the vehicle (the one the player is in, else the nearest friendly one without a bot driver within 24 m) and take passenger seats first, a gun seat only if there is no passenger seat. They follow the player into a vehicle automatically if the order is Follow. When the player gets out they all get out (`sqdDismountAll`, hooked in `bvLeavePlayer`); if the vehicle catches fire they bail out and call it.
* **Ping** (`I`): marks the point or enemy under the crosshair with a blue diamond for 14 s. Enemy pings set `focus`, alert and a hint for every mate; the nearest mate calls the contact. Attack uses a ping up to 30 s old when nothing is aimed at.
* **Fire discipline** (`K`): `botFire` returns early for `psq` mates while `SQD.hf` is set. Friendly fire is removed for everyone in a battle: `hurt()` ignores damage from a source of the same team, and grenade blasts (`blast` option `team`) spare the thrower's side. Bot grenades are not thrown when a friend is within 7 m of the target.
* **HUD** (`#sqHud`, first person, top left): one row per mate: class icon, callsign, status word (Following, Holding, Moving, Covering, Reloading, Down, Mounted, Climbing, Attacking, Defending, Suppressing, Falling back), health bar. **Markers** (`#sqMarks`): callsign and a chevron above each mate within 70 m, drawn over the view (so visible through walls); down mates are dimmed. **Ground markers** (3D, no depth test): gold ring with a bobbing arrow for Move and Defend, a red crosshair ring for Attack and Suppress; they fade over 3 s once half the squad is within 9 m.
* **Ring**: hold `N`, move the mouse (or press 1 to 8), let go. Eight slots: Follow, Move, Attack, Suppress, Take cover, Fall back, Hold, Defend. Touch: the Command panel Squad tab has every order as a row, plus formation, hold fire and ping.
* **Medics** (psq): fallen mates first (25 m bonus in the distance sort), then the player when under 70 hp, then a mate under 60 hp.
* **Stuck handling** (psq): no progress for 3 s drops the path; twice, a new random goal near the slot; four times (or 130 m away) and out of the player's view, a jump to the slot.
* **AT bots.** Engineers (the only class with the rocket launcher) already fire at vehicles within 75 m in `bvThreat`; new: enemy vehicles in sight within 130 m are called out once by the nearest soldier (`voiceWatch`). (Not changed: AI vehicles can still be ignored by non-engineers, who only scratch the paint.)
* **Snipers and high ground.** Snipers (always) and every second rifleman of an ordinary squad that is holding a point they own, and snipers told to Defend, climb a tower within 40 m of the point (see the ladder code below). Plain high-ground search without a tower was not added.

### NPC squads (AI against AI)
* `planBattle` first calls `sqdMergeSmall`: a squad down to one soldier joins the nearest squad of its team with room within 90 m.
* Contact sharing now also reaches every friendly soldier within 40 m (`shareContact`), any squad; they get an alert and, if idle, a hint to investigate.
* Retreat: the bot runs to the nearest point its side holds (not a random base), and squadmates lose 0.2 morale (a nearby squad tends to break together). Retreating bots call it out.
* Not done: whole-squad retreat decision, reinforcement requests, and AI use of the formation choices. The old formation (fixed offsets) and fire-and-move phases are unchanged.

### Constants worth tuning (search for them in `index.html`)
`SQD_MAX` 5 (4 on a phone); bind radius 90 m; regroup 35 m; slot tolerance 5.5 m; replan every 0.6 s; bound phase 3.2 s; suppress 8 s; cover and fall back lapse 20 s; heal 26 hp per second; marker range 70 m; ping lifetime 14 s (30 s for Attack); fill every 6 s below 3 mates; NPC share radius 40 m; merge radius 90 m.

## 6. Open items

Voice lines and ladders are in the same change set (see the report). Not verified in a browser. Known weak spots: a mate on Mount up toward an AI-driven vehicle is refused; helicopters only take passengers when landed or under 3 m; the order ring uses `movementX` so on a browser that refuses pointer lock it falls back to the pointer position over the ring.
