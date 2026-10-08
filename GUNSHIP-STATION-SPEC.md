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
