# Ladder and deck markers (what the game reads from a model file)

The game builds climbable ladders and standable decks from empties in any GLB it places (`ladMarkers` in `index.html`). Nothing else is needed in the model: no collision, no extra nodes.

For a model named `guard_tower` (the name of its top-level node, as used by the game) add these empties, **named exactly**:

| Name | Meaning |
|---|---|
| `guard_tower_ladder_bottom` | the foot of the rungs: on the ground, the ladder's centre line |
| `guard_tower_ladder_top` | the top of the rungs, at the deck edge (the climber steps off here onto the deck, 0.8 m further in) |
| `guard_tower_deck` | the centre of the deck, at the height people stand (the top surface of the boards) |
| `guard_tower_seat` | optional, as many as you like (`guard_tower_seat`, `guard_tower_seat.001` ...): where a soldier stands to shoot from the deck. Without seats the game picks spots near the deck centre |

A model with several towers can use a prefix per tower (`guard_tower_a_ladder_bottom` and so on) as long as each prefix starts with the model name.

Frame: metres, the model's own frame (+Z forward, +Y up, the same as the other models). Positions are read from the empties' world positions in the file, so they can sit anywhere in the node tree. A ladder may lean (bottom further out than the top); the climber always faces the deck centre.

Optional custom properties on the `_deck` empty (glTF extras):

| Property | Default | Meaning |
|---|---|---|
| `hx`, `hz` | 1.4 | half sizes of the deck rectangle in metres (along the model's X and Z) |
| `r` | none | use a circular deck of this radius instead |
| `rail` | 1 | 1 means people cannot walk off the edge (they use the ladder); 0 lets them step off and fall |
| `roof` | 0 | informational (a roof over the deck) |
| `mat` | metal | `wood` or `metal`: the sound of the rungs |

What the game does with them: the player walks to the foot of the ladder, faces it and presses E; W and S climb at 1.5 m/s with a rung sound every 0.3 m; at the top W steps onto the deck. Soldiers (snipers first, and any squad told to follow the player up) use the same ladder and stand at the seats. At most 2 soldiers are assigned to a tower and 3 people stand on a deck. Bullets from the deck are not blocked by the tower's own collision box.

Models without markers use a hand table (`LAD_HAND` in `index.html`) for: `port:watchtower`, `port:silo`, `port:fuel_tank`, `battle:watch_tower_wood`, `battle:radar_station`, `battle:searchlight_tower`, `battle:radio_mast`. Markers win over the table for the same model.

Test from the browser console: `__sc.LADDERS`, `__sc.PLATFORMS`, `__sc.ladAddModel(glbKey, nodeName, group, prop)`.
