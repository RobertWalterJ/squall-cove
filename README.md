# Squall Cove

A browser harbour sandbox, version 4. You run the cove from above ("god mode") and can drop into the helm of any boat.

- **Command**: tap a boat, then tap open water to send it there. Sailboats tack on their own.
- **Build**: launch dinghies, a keelboat, a tug and eleven Coast Guard vessels (Bay class, Hero class, hovercraft and eight icebreakers, patrol and science ships up to 138 m, loaded the first time you place one), drop cargo that floats or sinks by its real density, plant trees, rocks, a lighthouse and race marks.
- **Land**: raise, lower, flatten or smooth the island. On a phone, dragging moves the map; switch Drag to "Paints land" to shape with one finger.
- **Weather**: wind strength and direction, dawn to night, rain, fog.
- **People**: Build > Person or Crowd places up to 14 people on land, the pier or a boat deck (crew stand on the aft deck of powered boats). Tap a person to select them, then tap dry land to walk. They wave at passing boats. Heavy cargo, a capsized boat or land lowered under their feet topples them into a floating ragdoll; Topple and Stand up are buttons in the top right.
- **Helm**: sail or drive the selected boat yourself, with a chase camera.

Keyboard: Delete removes the selected boat or person, or whatever is under the pointer. The tray scrolls with the mouse wheel or by dragging.

Touch: drag moves the map and keeps the ground under your finger. Two fingers pinch to zoom and twist to turn.

Three.js and cannon-es load from a CDN; everything else is in this folder.

Play: open the GitHub Pages address for this repository. On a phone, use Share > Add to Home Screen
to launch it full screen like an app.

To run locally on Windows, double-click `Launch Squall Cove.bat` (or the Desktop shortcut). It serves the folder and opens a
dedicated Chrome window on the high performance GPU. Or serve the folder yourself (for example `python serve.py`) and open
http://localhost:8771. Opening index.html straight from disk will not work, because browsers block file fetches.

People are the 16 CC0 MakeHuman faces on the Coilover low poly kit (`assets/people.glb.b64.txt`).
