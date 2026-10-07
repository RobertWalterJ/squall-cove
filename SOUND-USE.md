# Sound use: recommended events for the heavy-weapon pack

Stems are families (strip `_NN`); `Snd.fx('<stem>', x, z, opts)` picks a variant. Far stems replace the near one beyond roughly 90 m, as `wpn_*_far` already does. Heavy-weapon stems live in groups `weapons` (wpn_, imp_, veh_gun*) and `people` (foley_), all lazy; call `A.loadStem` when the first emplacement or vehicle of that kind spawns.

| stem | recommended game event | notes |
|---|---|---|
| `wpn_hmg_fire` / `wpn_hmg_far` | manned MG nest, vehicle-mounted .50 cal: one play per burst (about 0.5 s of fire plus tail) | bus veh, 6 rounds baked in; for sustained fire retrigger every 0.5 s with overlap |
| `wpn_aa_fire` / `wpn_aa_far` | AA gun firing at aircraft, twin AA on ships | one play per short burst, retrigger at about 0.6 s |
| `wpn_flak_burst` / `wpn_flak_burst_far` | air-burst of an AA shell near the target aircraft | play at the burst point; follow with `imp_flak_fragments` after about 0.2 s if the player is near |
| `wpn_mortar_launch` / `_far` | mortar pit firing | then `wpn_mortar_whistle` near the target for the flight time, then `imp_blast_*` |
| `wpn_mortar_whistle` | incoming mortar round, near the impact point | 1.5 s: start it 1.5 s before the burst; it ends abruptly by design |
| `imp_shell_whistle` | incoming artillery, naval or bomb | 1.8 s, deeper than the mortar one; start 1.8 s before impact |
| `wpn_howitzer_fire` / `wpn_howitzer_far` / `_sub` | artillery battery firing | stagger several guns by 0.2 to 0.6 s; add `_sub` for the player's own battery |
| `wpn_naval_gun_fire` / `wpn_naval_gun_far` / `_sub` | warship main gun, shore battery on the coast | metallic ring plus water slap: best over water, quieter on land |
| `wpn_tank_cannon_fire` / `_far` | tank main gun | sharp crack: pair with `wpn_bolt_heavy` about 0.8 s later for the reload |
| `wpn_rpg_launch` / `_far` | RPG or rocket launcher firing | then `wpn_rocket_loop` on the in-flight rocket and `wpn_rpg_hit` on impact |
| `wpn_rocket_loop` | in-flight rocket, burning motor, one loop per rocket, attached to the projectile | seamless 2 s; fade out on impact |
| `wpn_rpg_hit` | RPG or rocket impact | 2.4 s, with fragments |
| `imp_blast_small` | grenade, small charge, fuel drum, vehicle death | |
| `imp_blast_medium` (+ `_sub`) | bomb hit on a structure, mortar or shell burst, vehicle magazine explosion | |
| `imp_blast_large` (+ `_sub`) | air-strike or bomber bomb, big fuel/ammo dump, building collapse by explosion, hard crash of a large aircraft | play the sub for the player's own camera within about 80 m; duck other buses 8 dB per SOUND-DESIGN |
| `imp_crater_thud` (+ `_sub`) | ground thump when a bomb or shell makes a crater, aircraft crash into land | start about 0.1 s after the blast for a layered feel |
| `imp_flak_fragments` | shrapnel rain after a flak burst, fragments around a near miss | quiet; mat bus |
| `veh_gunship_cannon` / `_far` | gunship heavy cannon shot | one shot per trigger, slower cadence than the minigun |
| `veh_gunship_minigun_loop` | gunship minigun firing | loop while firing; tail it with `wpn_gun_echo_tail`; fade out in about 0.1 s |
| `wpn_ammo_chain` | belt-fed gun reload or belt pull on a nest | foley, near only |
| `wpn_bolt_heavy` | charging a heavy gun, tank breech close, AA reload | |
| `wpn_barrel_overheat` | heavy MG or AA gun after a long sustained burst | 2.4 s hiss and ticks |
| `foley_turret_traverse_loop` | any turret or gun mount rotating (nest, AA, tank, ship) | loop while the aim changes; level and rate from angular speed |
| `foley_turret_stop` | turret stops after traversing | play when the loop ends |

Lightning bolts: not used here. Keep the existing `wx_lightning_crack` / `wx_thunder_*` family, which has the right character.

Needs game code (nothing in `index.html` was changed): new `Snd.fx` calls at the event sites above, loop start/stop for the three loops, scheduling of whistle then blast with a flight time, and an optional separate play of the `_sub` file. Existing family resolution (`_NN` stripped) already finds all of these.
