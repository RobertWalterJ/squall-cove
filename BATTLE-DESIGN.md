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
