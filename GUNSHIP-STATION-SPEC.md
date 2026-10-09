# Gunship station spec (owner decisions, 2026-10-08)

Source of truth for the AC-130 sensor station build. Mockup shown to the owner: sensor view on the left, three weapon cards on the right, mode and zoom bar along the bottom.

## Camera and aiming
- A gyroscopically stabilised camera stays locked on a GROUND POINT as the aircraft orbits and moves. Moving the aircraft never moves the aim point; only the operator slews it (drag, thumb pad, or tap on the map).
- All three weapons aim at the camera's ground point and must match the camera's targeting, within a generous gimbal limit (about 60 to 70 degrees off the aircraft's left side, a wide cone, not a narrow one).
- If the aircraft turns so far away that the point leaves the gimbal limit, the lock does not snap off. The camera eases to its limit, the display shows a plain "Losing target" message (text, not a timer), and after a few seconds of being outside the limit the camera slowly drifts and finally breaks lock. Regaining the angle restores control. The weapons refuse to fire while the point is outside the limit and say why.
- One weapon is active at a time; all three aim at the same ground point. Switch with keys 1 (howitzer), 2 (40 mm cannon), 3 (Vulcan), or the weapon cards. Switching takes a short ready-up before the weapon can fire, shown as a plain "Getting ready" state on its card (no countdown numbers): about 2 s for the howitzer, about 1 s for the 40 mm, almost none for the Vulcan. Each card keeps its own Fire (Hold for the Vulcan) button.
- Track target (optional): lock the camera to a selected unit or vehicle instead of the ground point.

## The aircraft
- It flies HIGH (well above the current 165 m; target about 450 to 600 m, still within draw range, with the camera zoom doing the rest) in its own orbits around the whole theatre, left-wing-down, circling the point of interest.
- It is fairly impervious to ground fire: small arms, machine guns and light AA cannot hurt it. Only heavy anti-air (a missile battery) may damage it, slowly, and it never falls to a single hit. It leaves only when its time on station ends or the operator leaves.
- Controlled by the player (a gunship operator role picked at deploy) or by the overview/god-mode player. The god-mode player gets the same station from the Command panel.

## Station UI
- Sensor view with modes Thermal (white hot), Night vision, Colour. The mode name is always written out; never colour alone.
- Reticle, lock box that tightens onto the target, range and bearing, grid reference, zoom level, contact icons (enemy red diamond, friendly yellow dashed box, unknown white), contact count, danger-close warning when friendlies are near the aim point.
- Weapon cards: 105 mm howitzer, 40 mm cannon, 25 mm Vulcan. Fill bar, plain Ready or Reloading label, large Fire or Hold button.
- Phone: reduced render resolution for the camera, a one-thumb slew pad, large Fire buttons, Leave station always visible.
- No timers or countdown numbers in the UI (dyslexia rule). Plain labels. No em dashes.

## Sensor modes and weather (owner decision)
- Thermal (infrared) sees through ALL clouds. Cloud shows only as a faint soft puff highlight; vehicles and people read clearly and brightly through it. Thermal is the dependable mode.
- Night vision is NOT guaranteed through cloud: dense cloud can wash the view out or blank part of it, thin cloud only dims it. Colour (daylight) is blocked by cloud like the normal view.
- Show the mode's weather limit in plain words on the mode button's hint ("Sees through cloud" / "Clouds can block this").

## Howitzer crew callouts (owner request, simplified)
- Each time the howitzer's ability to fire is re-enabled, a crewman calls ONE short line: "Ready!" or "Ready to fire!" (vary between a few phrases such as "Up!", "Weapon up!", "Ready!"). Only one line per reload, not the full sequence, and not every time: roughly two out of three reloads, never twice in a row with the same phrase.
- Use the existing speech system (VOICE / VLINES / vsay, speechSynthesis) with a loud, clipped crew voice distinct from the squad voices; only while the player is at the station (interior mix). Caption each call via captionAdd. Honour the "Squad voices" setting (off = captions only).
- Optional, same pattern for the 40 mm loader ("Loaded!"), rarer. Vulcan has no callout.

## Built in v9.7.0 (what the code does, where it differs from the mockup)
- Code: the `STN` block at the end of `index.html` (state, camera, post pass, HUD, cards, input), station weapons inside the `AC` block (`AC.stn`), `gunshipFly` for the flight, `damageAir` for the immunity. Checks: `qa/station-check.mjs desktop|portrait|landscape`, pictures: `qa/station-shots.mjs`.
- Orbit: 520 m up, 360 m radius, 54 m/s, left wing down (24 degrees of roll). While the station is open the orbit centre follows the aim point at up to 24 m/s and the aircraft's clock stands still; when the operator leaves it stays 25 to 45 s and goes. Gimbal limit 65 degrees off the left wing; 3.5 s outside it the point starts to drift, 9 s outside it the lock breaks (slew or tap to lock again).
- Weapons: howitzer 7 s reload, 40 mm a string of three per press then 2.2 s, Vulcan about 5 s of fire then a 4 s reload. Switch ready-up 2 s, 1 s, 0.12 s. Shells and rounds land within 3 to 4 m of the point (or on the unit under the reticle when it is within 12 m of the point).
- Input: left click or tap in the view (or on the small map) sets the point, drag slews, arrow keys or WASD slew, the right mouse button or Space or Enter fires (hold for the Vulcan), 1 2 3 choose, + and - or the wheel zoom (x1 to x24), M cycles the sensor, T tracks, Esc or Leave station leaves. Left mouse is not the trigger because a left click already sets the aim point; say if you want that swapped.
- Aircraft immunity: only a missile (`damageAir(..., 'missile')`) hurts it, at 12 percent of its strength and at most 5 percent of its health per hit.
- Not heard by ear and not played on a phone yet: all interior levels, the crew voice, the thermal look on real hardware, the phone layouts beyond the headless checks.

## Built in v9.9.0 (sensor realism)
- Night vision is a light amplifier: the picture is the scene times an auto gain (about 5x to 36x, from a wide average of how bright the scene is), softly compressed, with grain that grows with the gain, a mild bloom, and a local gain drop around very bright sources (flash, flare). Daylight is above the gain floor, so it saturates and washes out. Cloud still dims or blanks it.
- Two phosphor looks: Green (default) and White (neutral grey-white). The "Night: Green" / "Night: White" button sits next to Night in the bottom bar, says the colour in words, is remembered in localStorage `squall-cove-stn-phos`, and pressing it also switches to Night vision.
- Everything is in the sensor picture because the whole scene is drawn into one render target first. A shared uniform `SENSOR` (0 Colour or none, 1 Thermal, 2 Night) is read by the tracer shader and the fire/flash (fxG) and smoke (fxS) particle shaders, and set only for the station's draw. Thermal: tracers, flashes, flames and explosions become hot markers drawn with normal blending (white hot, with a bloom), smoke and dust are a faint mid grey, the illumination flare and shockwave rings turn hot. Night vision: the same things are boosted to HDR values so they bloom. Colour: untouched.
- Unverified: no real phone run; the 8-bit render target fallback (no half float) clips the Night vision bloom.

## Built in v9.9.3 (mouse-first controls, replaces the v9.7.0 Input paragraph)
- The mouse aims. The pointer is captured (pointer lock on the station view) when the station opens or on the first click, like first person; moving the mouse slews the camera with no button held. If the browser refuses the lock, moving the mouse over the view still slews and the hint says "Click the view to aim with the mouse". Speed is ground metres per pixel at the aim range, so it falls as you zoom in; Comma and Period change the overall speed (Very slow to Very fast, remembered). The right button held is a slow, precise aim.
- Left button fires the active gun (hold for the Vulcan and for repeating 40 mm bursts); Space and Enter still fire. The wheel cycles the guns (up next, down previous, wrapping, one step per notch, a touchpad flick gives one step) with the same Getting ready state; 1, 2, 3 choose directly. Zoom: Shift + wheel, keypad + and -, [ and ], Q and E, and the Zoom buttons. WASD and the arrows still slew.
- Touch is unchanged: drag, tap to set the point, pinch, pad, large Fire buttons.
- Esc: the browser eats Esc while the mouse is captured and releases the lock, which leaves the station (also Esc when not captured, and the Leave station button). The mouse is always handed back; first person re-locks on its next click. C frees or recaptures the cursor so you can click the small map and the buttons, and Shift + click (cursor free) sets the aim point at the cursor.
- Not tested with a real mouse and a real pointer lock: the headless browser may refuse the lock, so the check drives the same code with synthetic mouse, wheel and lock events.
