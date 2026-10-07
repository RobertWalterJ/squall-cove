# Battle depth plan (next build, after the maps agent finishes)

Goal: a battle with real places to hold, assault and defend, and things that change as it goes.

## Strategic point types (each map picks from these)
- **HQ / base**: spawn point, cannot be taken until the side has lost its other points. Heavy defences: two MG nests, AA gun, mortar pit, sandbag ring.
- **Strongpoint**: bunker plus MG nest and a mortar pit. Hard to take; holding it feeds tickets.
- **Radio mast / radar**: holding it shows the enemy's positions on the overview and delays their air support (offline for longer).
- **Supply depot**: holding it gives your bots more ammo and quicker revives, and fills the player's grenades and charges.
- **Artillery battery**: holding it unlocks free artillery calls for that side.
- **Airfield / helipad**: holding it speeds up helicopter and paratroop calls.
- **Harbour**: holding it allows boat landings on that side.
- **Bridge / choke**: no bonus, but a place where fights pile up.

## Emplacements
- MG nest, AA gun (exist), **mortar pit** (AI fires at enemy clusters seen by the squad; the player can man it and aim), **searchlight** at night, **sandbag walls and trenches** dug as craters, **barbed wire**, **mines** (small blasts).
- A nest has a crew of one bot who mans it; if the crew is killed it goes quiet until someone takes the post. Players press E to man any friendly one.

## Dynamic events
- Counter-attack: when a side loses a point, it sends a squad to retake it within about a minute.
- Supply drops by parachute: a crate lands somewhere neutral; both sides race for it.
- Air raids on the strongest point; AA nests matter.
- Weather shift mid-battle (fog or rain lowers sight range and air support accuracy).
- Commander calls: each side's AI decides attack, defend or flank from the plan, with squads as the unit.

## Player roles
- Squad leader (orders, tablet), sniper (scope), engineer (builds sandbags, repairs, lays charges), medic (revives), AA specialist, pilot later.

## Order of work
1. Point types and per-map tables (needs the new BATTLE_MAPS table from the maps agent).
2. Mortar pit and crewed nests.
3. Counter-attacks and supply drops.
4. Radio mast, depot, battery bonuses.
5. Engineer role and building.


---

# Status: what was built (v8.9 battle depth). Nothing here has been seen running.

Everything is in `index.html` (one new block fenced by `/*BD-START*/ ... /*BD-END*/`, plus small edits at the places named below). Syntax and scope were checked, and the layout, crew, mortar, battery and event logic was run in node against the real terrain, the real `battle.glb` and `weapons2.glb` with stubs for the rest of the game. No browser was opened.

## 1. Point types (done)
Each row of `BATTLE_MAPS[map].points` now has a fifth entry, its type (`POINT_TYPES`: hq, strongpoint, radio, depot, battery, airfield, harbour, choke, plain). The type shows as a letter on the flag, in the HUD dot tooltip, in the Battle and Map tab lists and under the point's name label.
* Port: Quay West hq, Quay East harbour, Town centre strongpoint, West farm depot, East farm battery, Lighthouse radio, Mountain lake plain, Landing beach harbour, Raider camp hq (no airfield: the shore of Mountain lake is too steep for a helipad).
* Urban: Quay West hq, Quay East harbour, Container terminal airfield, Town square plain, Market quarter choke, Old town radio (a radar station), The stadium strongpoint, Rail yard depot, Hill park battery, North barracks hq, North depot strongpoint.
* Desert: Port quay harbour, Customs yard hq, Dune ridge airfield, Oil pump station strongpoint, Fuel depot depot, Ruined village choke, Oasis plain, Radio outpost radio, Northern camp hq, Wadi fort battery.
Bonuses while held (`holdN`, `cdRate`, `boatAllowed`, `batteryFire`, `updateKit`): radio slows the enemy's air support (Griffon, gunship, paratroops, strike) by 1.6 and shows the enemy as red or blue points on the overview (god mode only); depot gives bots instant reloads, 1.4 s revives (was 2.2 s) and the player a grenade, a charge and a smoke grenade back each time they come within 12 m (never above the starting count); battery gives a free barrage every 80 s (Ready or Recharging in the tablet, fired automatically for the side the player is not on); airfield makes paratroop and helicopter calls 1.5 times faster; harbour allows boat landings (a side without one can still land if it holds the point nearest its stretch of coast); hq cannot be taken until its owner holds no other point.

## 2. Structures (done)
`battle.glb` loads when a battle starts (`ensureBattleKit`). `layPoint` builds a layout per type with `bTry`, which uses the scenery's own `mapFits` (water, slope, roads, other footprints) and also refuses spots on top of anything in `props`, an AA or MG emplacement or another flag. Big solid ones (bunker, command post, depot buildings, mast, tower, battery, mortar pit, searchlight) are pushed into `props` with a box, so `pushOutOfProps`, the foot grid, line of sight and the vehicle grid already treat them as solid, and they get a physics box. Wire, trenches, sandbags and the helipad are not solid (so a ring of wire can never trap a spawning bot) but sandbags and trenches are in `coverList`. Touch devices build half as many repeated pieces and at most 90 structures (190 on desktop). Everything is removed in `battleStop` (`kitStop`); the models share geometry and materials with the loaded file, so only what this code made (cones, flags' sprites, markers) is disposed.
Animated: radar dish, windsock (downwind), pumpjack head, searchlight lamp sweep and an additive beam at dusk and night, howitzer barrels (elevation, recoil, turning to aim), mortar tubes.

## 3. Crewed emplacements (done)
Up to 10 (4 on phones) emplacements at points owned at the start get a crew bot (`assignCrew`, priority hq, strongpoint, then the rest; mortars first). Later captures add crews up to 14 (6 on phones). A crewed gun fires only while its crew is alive and at the post; when the crew is knocked out it goes quiet, the nearest idle friendly bot walks up and takes the post (`crewTick`, `botPost`), or the player mans it with E. Crew bots are not counted for reinforcements or squads. Mortar pits (`addMortar`, `updateMortar`, `mortarShoot`) fire three rounds at a cluster of enemy contacts reported through `bot.hint`, never near friends, with the tube elevating and the pit turning; the player can man one with E and click to send two rounds to the crosshair. Pace is 15 s for the AI and 10 s for the player, shown as Ready or Recharging.

## 4. Events (done, `updateEvents`)
Counter-attack (the nearest squad of the side that lost a point is sent back for 75 s, and paratroops if it holds an airfield), supply drop (a crate on a parachute every 150 to 210 s at a spot away from every point: first person to stand within 4 m takes it for their side: full ammo for bots within 120 m and the player, and one banked artillery call), air raid (alternating sides, a strike or a gunship on the other side's hottest point), weather (fog or heavy rain for 150 to 210 s: sight range 0.55 to 0.75, air accuracy 0.55 to 0.7) and reinforcement waves (paratroops and boats when a side drops below 28 tickets). All go through `noteOnce`, none shows a number.

## 5. Skins (done) and 6. Weapons (done)
`troops2.glb` loads at battle start with the toast "Loading troops" (the battle starts with `troops.glb` and the first bots are swapped when the file arrives). Blue wears desert or urban on those maps and the old soldier on the port map; red wears militia (Raiders) or special (Invaders); bot classes medic, sniper, heavy and engineer wear their own; SWAT wear riot gear on the urban map; civilians placed on the urban and desert maps wear port worker skins. Not done: the pilot skin (the Griffon has no crew people).
`weapons2.glb` loads with `weapons.glb`: LMG, marksman rifle, revolver, rocket launcher (child `rocket` hides until reloaded), scoped carbine (replaces the old carbine model), binoculars, smoke grenade, satchel, radio, medical kit, tablet (shown while the tablet is open in first person). New loadouts: Heavy, Engineer (F builds up to six sandbag corners), Spotter, Medic; Marksman now carries the marksman rifle and the carbine. In a battle the number keys pick the tools of the loadout in order, V cycles them.

## Not done or not checked
Rendering, scale and placement of every structure, the feel of the new weapons, the crew pose, bot behaviour around the structures, frame rate with the extra meshes, the load time of `troops2` (13 MB of base64). Strongpoint trench lines often fit only partly on cramped ground.
