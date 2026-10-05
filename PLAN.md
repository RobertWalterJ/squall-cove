# Squall Cove plan: rain, lava, heat and cold, classes and menus

Written October 2026 from three planning reviews (simulation, menus and classes, effects on people and ships). Plain language. No clocks in the game.

## What gets built, in order

Each stage ships on its own and is tested before the next starts.

### Stage A (v5.0): catastrophic rain and lava flows
- Rain adds a thin layer of water to every land cell. It runs downhill with the existing water solver, ponds in hollows and returns to the sea. A new Deluge disaster is 24 times heavier.
- Lava gets its own thickness and heat grids. It flows slowly downhill from the crater, cools, and turns into dark rock that raises the ground. In water it hisses, makes steam and builds new land.
- Lava glows through the terrain surface (a texture read by the terrain shader, no new mesh).

### Stage B (v5.1): heat, humidity and clouds
- A coarse 64 by 64 grid for temperature, vapour and cloud water, updated 5 times a second.
- Hot ground and lava evaporate water. Vapour drifts with the wind. Where the air is cool it condenses into cloud and then rain. When everything stays hot it stays clear vapour.
- Tools: a global temperature slider, a local Heat brush and a Cool brush (hold button like Sculpt), and Pull humidity.

### Stage C (v5.2): freezing and effects on actors
- Below freezing water skins over with ice and snow settles on land. Ice slows and holds boats, makes the ground slippery and lets cargo rest on top.
- People get simple states: Wet, Cold, Hot, Burning, Frozen. No deaths in safe mode. Boats gain ice weight in the cold and take fire near lava.

### Stage D (v5.3): classes and menus
- One registry of items with a class and a handler, so adding an item is one line.
- A class picker sheet so the build tray shows one class at a time.
- A Calm all button that is always on screen, a global Undo, effect limits and a Gentle mode that hides disasters.

## Design rules from the reviews
- Two resolutions only: the 257 grid for water, lava and ground, and a 64 grid for air.
- New behaviour must stay under 1.5 ms a frame on a phone. Lava only runs inside its own box and costs nothing when idle.
- Share the existing smoke and glow particle pools. Cap new emitters.
- Never leave a player stuck. Frozen, trapped and grounded things always get a way out.
- Save and load every new field, with defaults so older saves still open.
- No em dashes in game text. Plain, short labels.

## Known risks
- Solid lava changes the ground, which rebuilds the physics heightfield. Batch it twice a second at most.
- Floods will trigger the rule that removes cargo that stays fully under water. Add a grace period.
- Sea ice can trap boats. First version only freezes shallow shore water.
