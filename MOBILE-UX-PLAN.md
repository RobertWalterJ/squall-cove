# Squall Cove: Mobile UX plan (Samsung S23, portrait and landscape)

Written 2026-10-07. Builds on `MOBILE-AUDIT.md` (feasibility, caps, edition decision), `UX-AUDIT.md` (one thing one place, opaque flat panels), `MENU-AUDIT.md` (IA), `GAMEPLAY-AUDIT.md` (Command is overpowered; phone is a commander's game). Those are not repeated here; this file turns them into a spec and a task list.

**State at writing:** another agent is already landing the first phone pieces in `index.html`: `window.__ED`, `html/body.ed-phone`, `#phoneStack`, `#selBar`, `#cmdRow`, FP ids `#fpReload #fpZoom #fpSquad #fpScope #fpStance #fpJump #fpUse #fpHL/#fpHR/#fpHUp/#fpHDn`, and `sw.js` v9.3.0 (stable `squall-cove-assets-a1` cache). Each task below says "verify, then complete"; do not redo what exists. Line numbers are deliberately omitted because the file is moving.

Standing constraints (from Robert's memory, binding): no timers or countdowns in phone UI; Robert is dyslexic, so plain labels and read-aloud on text-heavy screens; the red and green low-light themes are never changed; cartoon violence only (no gore); shared-origin PWA rules (see `CLAUDE.md`); double-click launcher exists; one codebase, desktop stays the most capable.

---

## 1. Principles, with sources

| # | Principle | Spec consequence | Source |
|---|---|---|---|
| P1 | **Targets**: primary controls at least 48 CSS px (Material 48dp); never below 44 (Apple HIG 44pt). WCAG 2.2 AA 2.5.8 floor is 24 px or 24 px spacing; AAA 2.5.5 is 44. We meet AAA. Gaps at least 8 px. | Every button on `body.ed-phone` has `min-height:48px` (44 for dense chips). Fire 72, Jump/Use/Reload 56. | [Touch targets guide](https://frontendchecklist.io/rules/accessibility/touch-targets), [WCAG 2.5.8 guide](https://allaccessible.org/blog/wcag-258-target-size-minimum-implementation-guide), [Touch target size](https://specification.website/spec/accessibility/touch-target-size/) |
| P2 | **Thumb zones**: portrait play lives in the lower half; landscape in the lower-left and lower-right quadrants. Anything in the top third is read-only or rarely used. | No frequent control above mid-screen in portrait. Menu/Exit are reachable (sheet or lower half). | [Touch-stick controllers / thumb comfort](https://www.construct.net/en/tutorials/touch-stick-controllers-241), [Godot touch guide](https://inairspace.com/ja/blogs/learn-with-inair/godot-touch-controls-for-mobile-a-complete-practical-guide-1) |
| P3 | **Virtual stick**: floating (appears under first touch) feels natural and adapts to grip; fixed builds muscle memory. Keep a held touch alive when the thumb slides off the visual; allow direction change without lifting. Show pressed state and stick position. | Left stick is floating by default inside the left 40 percent zone with a "Fixed stick" setting; the 46 px invisible extension stays. | [Construct tutorial](https://www.construct.net/en/tutorials/touch-stick-controllers-241), [Virtual joystick guide](https://www.abratabia.com/game-controls/virtual-joystick.php), [Bugnet joystick feel](https://bugnet.io/blog/how-to-fix-mobile-virtual-joystick-feeling-bad) |
| P4 | **One thumb, one job**: right thumb looks (drag zone), left thumb moves; fire and context buttons must not sit inside the look zone's drag path. Mobile shooters keep Fire fixed, offer aim assist, optional gyro, and layout customisation. | Fire is a dedicated fixed button; look pad excludes button rects (already `pointer` capture per id); aim assist on; layout "Left-handed" mirror and button size setting. | [CoD Mobile settings roundup](https://www.charlieintel.com/call-of-duty-mobile/best-cod-mobile-settings-multiplayer-145921/), [gyro note](https://www.sportskeeda.com/esports/cod-mobile-best-gyroscope-sensitivity-settings), [Game Accessibility Guidelines](https://igda-gasig.org/get-involved/sig-initiatives/resources-for-game-developers/sig-guidelines/) |
| P5 | **Command UIs use standard touch grammar and a bottom bar**: pinch/spread/rotate/pan as users expect (Rome: Total War mobile), tap-to-move and context commands, radial wheels, UI along the bottom. | Tactical map and overview use pointer-event pan/pinch; actions in a bottom bar/sheet; squad ring is a wheel. | [Feral Rome TW mobile](https://www.feralinteractive.com/CN/games/rometw/android-ios/building/), [Brass Tactics RTS interactions](https://www.gamedeveloper.com/design/brass-tactics-evolving-classic-rts-interactions-for-vr-part-2), [Mobile RTS overview](https://scholar-khgjei.upenn-edu.pp.ua/post/766980674241) |
| P6 | **Safe areas and edge-to-edge**: `viewport-fit=cover` plus `env(safe-area-inset-*)` on every fixed element, bottom ones also for the Android gesture bar. | Single set of vars `--safe-t/-r/-b/-l`; all fixed UI offsets use them, landscape included (punch-hole on the left or right). | [Chrome edge-to-edge guide](https://developer.chrome.com/docs/css-ui/edge-to-edge), [Chromium display cutout notes](https://chromium.googlesource.com/chromium/src.git/+/fafff21/docs/ui/android/display_cutout.md) |
| P7 | **Orientation**: lock via `screen.orientation.lock()` only works in fullscreen, and PWA `display: fullscreen` does not count as element fullscreen. So never rely on lock: support both orientations and switch layout on `orientation` media queries. | No forced lock. Optional "Lock rotation" hint in settings only. First person and tactical map get a landscape-preferred nudge (a line of text, never a block). | [MDN lock()](https://developer.mozilla.org/en-US/docs/Web/API/ScreenOrientation/lock), [HTML5 game orientation lock fails](https://bugnet.io/blog/fix-html5-game-orientation-lock-fails-pwa-android) |
| P8 | **Haptics and wake lock**: `navigator.vibrate` for short confirmations (Android Chrome supports it); Screen Wake Lock during active play so the screen does not sleep mid-battle; re-acquire on `visibilitychange`. | Haptic table in section 4; wake lock while mode is battle/fp/helm and not paused. | [MDN Wake Lock](https://developer.mozilla.org/en-US/docs/Web/API/WakeLock), [W3C Wake Lock](https://www.w3.org/TR/wake-lock/) |
| P9 | **Accessibility for a dyslexic player**: no timed challenges or countdowns; plain sentence-case verb labels; icon plus word; text-to-speech on text-heavy screens; sensitivity and left-hand options; never colour alone. | Read-aloud button on Help, Command mission text, end screen summary, deploy class descriptions; "Easy text" must not overflow phone layout. | [Game Accessibility Guidelines (IGDA SIG)](https://igda-gasig.org/get-involved/sig-initiatives/resources-for-game-developers/sig-guidelines/), [Accessible games overview](https://www.webbie.org.uk/blog/?p=115) |
| P10 | **Performance is a feature**: mobile budgets are far tighter (cap DPR about 1.5, drop MSAA and shadows when needed, instancing for repeats). Thermal throttling is solved by lowering resolution first, then frame rate (floor 30), and raising again when cool. | Section 5. | [Three.js mobile optimisation](https://digitalstrategyforce.com/journal/how-do-you-optimize-threejs-performance-for-mobile-devices/), [Codrops efficient Three.js](https://tympanus.net/codrops/?p=86572), [Android ADPF case study](https://developer.android.com/stories/games/netmarble-got-adpf), [Samsung Adaptive Performance](https://developer.samsung.com/codelab/gamedev/adaptive-performance-unity.html) |
| P11 | **Survive context loss**: listen for `webglcontextlost` (call `preventDefault()`), rebuild on `webglcontextrestored`, otherwise reload from autosave. Common on mobile when the tab is backgrounded or memory is tight. | Section 5.4. | [Khronos: Handling context lost](https://wikis.khronos.org/webgl/HandlingContextLost), [three.js forum on restoration](https://discourse.threejs.org/t/handling-context-restoration-in-2021/29371) |
| P12 | **Local rules**: one thing one place; at most 4 persistent surfaces; opaque panels, no `backdrop-filter`; world covered less than 30 percent at rest. | Carried over from UX-AUDIT 5.1. | `UX-AUDIT.md` |

Note on figures: the "under 50 draw calls" mobile figure in generic Three.js blogs is for casual scenes; this game's phone budget (section 5) is a realistic one measured from its own audits. Treat generic numbers as direction, not law.

---

## 2. Per-screen spec

Conventions. P = portrait 360 to 412 CSS px wide (S23 about 360 x 780 visible; dvh varies with the Chrome bar, so size with `dvh` and `--vh` fallback). L = landscape about 780 x 360 visible. `safe` = respect `--safe-*`. Thumb zones: **T-low** = bottom 40 percent; **T-side** = left/right 30 percent columns in landscape; **Top** = reach-poor, read-only or rare. "Hidden vs desktop" lists what the phone does not show.

Shared phone shell (all in-game screens):
* Top bar (one row, 44 px, safe): left status chip (mode/objective, read-only), right two icon buttons: **Log**, **Menu**. In battle the ticket bar replaces the status chip. Nothing else is persistent up top.
* Toast lane: one lane, one message, above the bottom bar (existing `#phoneStack`); `pointer-events:none`; never over a control.
* Bottom bar owns the thumb zone and changes per mode (below).
* Menu opens the **World sheet** (see 2.12 Escape menu). Android back button closes the topmost sheet (push a history state per sheet; `popstate` closes).

### 2.1 Boot menu (`#boot`)

| | Portrait | Landscape |
|---|---|---|
| Layout | One column, scroll. Header "Squall Cove" + edition line "Phone edition. Switch to desktop edition". Step 1 Mode (2 big cards: Sandbox / Command battle). Step 2 Map (3 big cards with thumb and MB; "More maps" collapsed, with desktop-only ones greyed with reason). Step 3 Extras collapsed ("Wi-Fi extras": skins, full sound). Sticky bottom bar: **Start: The Cove** + one line "Downloads about 18 MB, once". | Two columns: left Mode+Map, right Extras+Start (sticky). Cards 2 per row. |
| Controls | Tap cards; radio semantics. | Same. |
| Thumb zone | Start button at bottom, full width 56 px. | Start at right column bottom. |
| Hidden vs desktop | Lemnos/Urban/Desert battles, skins default, cheats option, size slider max. | Same. |
| Extras | "Read this aloud" speaker on the intro text. Quality shows "Auto (recommended)" with battery saver as a choice. Continue card at top if an autosave exists (reload path after context loss). | |

### 2.2 Sandbox overview (god camera)

| | Portrait | Landscape |
|---|---|---|
| HUD | Top bar as above. | Same; ticket/status chip left, Log/Menu right inside safe insets. |
| Bottom bar | Dock: **Select, Place, Land, Sky** (56 px, labelled). In battle maps: 5th slot **Command**. | Dock as a vertical rail on the **right** (T-side), 4 to 5 buttons 48 px; keeps the world wide. |
| Selection | Selection bar docks directly above the dock when something is selected (scrolls horizontally: Info, Topple/Remove, Deselect, Box select, First person, Rescue). Single-line chips 44 px. | Selection bar becomes a left-edge vertical strip, max 4 visible + scroll. |
| Place/Land/Sky panels | Bottom sheet, 45 percent height, drag handle, never covers the reticle (reticle at 40 percent height; sheet top at 55 percent). Place = group chips + search + 2-column tile grid (name + swatch). | Sheet at the left, 40 percent width, full height; reticle stays visible at centre-right. |
| Land sculpt | Sculpt/Undo cluster owns bottom-right while Land is active; Command/Calm hidden then. Hold-to-sculpt button 92 px, other thumb pans. | Cluster bottom-right, dock rail moves to left. |
| Gestures | 1 finger pan/orbit, 2 fingers pinch/rotate, tap select, long-press 420 ms box select (also a labelled **Box select** chip). | Same. |
| Hidden vs desktop | Edit side pane tabs (Map/Events/Live/Play collapse into Menu and sheets), More button, Cheats, key hints, big Place categories (8 curated), instruments card unless asked (Info chip). | |

### 2.3 Battle overview

| | Portrait | Landscape |
|---|---|---|
| HUD | Top: ticket bar (Port 76 ... Raiders 76) alone; Log/Menu icons on the row below or inside the bar's ends; no overlap (ticket bar `max-width: calc(100vw - 110px)`). | Ticket bar centred top; Log/Menu at corners. |
| Bottom bar | Large 3-button bar: **Command, Map, Squad** (56 px). Contextual row above it when spectating: **Watch next, Jump in**. | Same three as a right rail; contextual row bottom-centre. |
| Behaviour | Default battle view on phone = overview with auto "Watch" until the player acts; **Map** opens the tactical map (2.4). | |
| Hidden vs desktop | Battle tab of side pane (setup lives in its own sheet 2.5), kill-feed beyond 2 lines, Place/Land/Sky tools during battle (dock shrinks to Command/Map/Squad plus Menu), support tickers beyond a one-line summary. | |

### 2.4 Command panel, tactical map, fire missions

Command is the phone's primary battle surface (MOBILE-AUDIT 4.5). Make it a **bottom sheet at 60 percent height** (portrait) or **right 45 percent** (landscape), world visible and tappable above/left of it.

* Tabs: **Fire, Support, Squad, Points** (4, 48 px). One summary chip row under the tabs: `Port | Tap map | Medium | Single` (taps open a small picker for Side/Target/Size/Pattern/Aim). Only the active mission list scrolls; header and tabs are pinned. Rows 56 px: name, status word (Ready / Reloading is a word, not a countdown), cost; tap arms it, then **tap the map or world** to place (arming shows one line: "Tap where to fire. Cancel"). A **Cancel** button is always visible while armed.
* Read-aloud: speaker on the sheet header reads the armed mission and cost.
* **Tactical map** (`#tmap`): full-screen on phone. P: map fills, controls in a bottom strip (Side, Target, Size, Pattern as 4 chips) and the Fire list as a bottom sheet pulled up by a handle; L: map left 62 percent, panel right 38 percent. Gestures: pan, pinch, tap mark; **Back** is a 56 px bottom-left button (never only top-right). Compass/north-up toggle chip. Tap a squad icon to select, tap map to order (move), double-tap to centre.
* Fire missions on phone keep desktop rules; phone-only helper: after placing, a single **Fire** confirmation for expensive missions (Large bomb, air strike) to prevent fat-finger. No countdown shown.
* Hidden vs desktop: per-weapon accuracy detail rows, 70-unit group lists (shows squads, not individuals), keyboard hints.

### 2.5 Battle setup (`#bSetup`)

* P: full-screen sheet; header with Close (top-left, 48), body scroll, **footer 72 px max**: segmented **Watch | Fight** above, one **Begin** primary below (or both in a 2-row footer under 120 px total with safe-b). Soldiers slider 4 to 14 (phone cap) with value text, not tick overload; "Wi-Fi extras" shown only if relevant. Read-aloud on the description.
* L: two columns (left options, right summary + Begin). Footer is not full-width; no more than 25 percent of height.
* Hidden vs desktop: size above 14, Urban/Desert/Lemnos unless unlocked (greyed with "Desktop edition"), advanced AI toggles, cheats.

### 2.6 Deploy / side pick (`#bSpawn`)

* P: modal sheet full width. Side pick = 2 large buttons (Port / Raiders) with flag colour and word. Class picker = 2-column tiles (icon, name, one-line description) showing **4 classes on phone** (Assault, Marksman, Heavy, Medic), 11 on desktop. Start point = a segmented control (2 points) + a tiny map preview. Footer pinned inside safe-b: **Deploy** primary 56 px, **Back to overview** secondary; **Replay** moves into the end screen only.
* L: classes left (grid 4 across), start point + Deploy right.
* Read-aloud on class description (speaker per tile press-and-hold is too hidden; use one speaker on the sheet reading the selected class).

### 2.7 First person on foot (touch scheme)

Portrait is playable but landscape is the intended posture; show a one-line "Landscape works best" hint once, dismissible, no timer.

| Zone | Portrait (360 x 780) | Landscape (780 x 360) |
|---|---|---|
| Move | Floating stick in the left 45 percent, lower 45 percent. Run when magnitude > 0.82 (existing) or Sprint lock chip. | Left 35 percent. |
| Look | Right 55 percent of screen except button rects; sensitivity setting 0.3 to 2.0x default 1.0 (current 0.0068 rad/px is about 3x desktop; lower the default). | Right 55 percent. |
| Fire | 72 px, right edge, vertical centre of the lower half; hold repeats for automatic weapons; optional "Tap look-pad to fire" toggle; optional auto-fire when reticle on enemy. | 72 px, right, 60 percent down. |
| Right cluster (arc around Fire) | Reload 56, Zoom 56 (only for scoped weapons), Use 56 (contextual, shows verb), Stance 52 (icon shows current). | Same arc, wider spacing. |
| Left extras | Jump 56 above the stick's top-left; Squad 52 left of Jump. | Jump above stick; Squad near. |
| Tools | Chips only for the kit's 3 to 5 tools, row above the stick's top (not top-left), 52 px; throw button appears when grenades remain. | Row bottom-centre. |
| Top | Status: health bar left, ammo right as text "LMG 60/60" large; ticket bar thin; **Leave** (to overview) a 48 px icon top-right with confirm if in vehicle; **Command** moved off the cluster into the top bar next to Leave. | Same. |
| Prompt | One line above the cluster, never over health/ammo; fades after use, no timer logic beyond existing fade. | Same. |

Rules: Command is no longer in the fire cluster. Fire never sits in a column with a menu-opening button. Aim assist (section 4.3) on by default for touch; hit radius 1.3x for touch players. Optional gyro (off by default; button in Settings, `DeviceOrientation`/`devicemotion` permission on first enable).

Hidden vs desktop: full class list (4 of 11), weapon mod UI, cheats, keyboard hint strip, detailed damage numbers, mouse-only secondary actions (all remapped to buttons).

### 2.8 Vehicle (ground)

Left stick = throttle/steer (existing). Right look-pad = gun/camera. Fire button for turrets. Added: **Brake/Reverse-lock** is not needed if stick down = reverse; add a **Handbrake** 56 px only for jeep/technical (rare, optional). **Exit** = Use button relabelled "Get out" (48+, bottom-right). Seat switch chip when more than one seat is free ("Move seat"). Landscape identical. Hidden: vehicle spawn menus in battle (Command only), tuning.

### 2.9 Helicopter

Phone edition: piloting is **optional later**; first release lets the player ride as gunner/passenger, command it from overview, and fly it only through a simplified model. When piloting is enabled: left stick = pitch/bank (existing); **right look-pad horizontal drag = yaw**, vertical = camera pitch; **Climb / Descend**: a vertical 2-button strip at the left of the stick (`#fpHUp`, `#fpHDn`, exist) 56 px each, hold; **Hover assist** on by default (neutral stick levels the helicopter and holds altitude); Fire button for gun; Use = "Get out" only when landed or low (else disabled with a word, "Land first"). Landscape preferred; portrait works with the same layout.

### 2.10 Emplacement (mounted gun, AA, mortar nest)

Look-pad aims (reduced sensitivity 0.6x while mounted); **Fire** 72 px right (existing `fpManFire`); **Get off** (Use) 56 px; **Zoom** if the mount has optics. Stick hidden (nothing to move), freeing the lower-left; a left-bottom **Reload/Heat** word indicator (text: "Ready / Cooling"; no timer numbers). Landscape identical. AA gun: a single auto-lock assist chip "Assist: on" (aim assist toward aircraft within 6 degrees).

### 2.11 End screen

Modal full-width sheet, scrollable; summary line first ("Port won. 5 people survived. 12 knocked out."), a speaker button to read it aloud, 5 stat rows, then **Play again** (primary), **Change sides**, **Back to cove** (secondary). Buttons pinned at the bottom with safe-b. No countdown to auto-restart. Scrim blocks FP controls underneath (pointer-events off). Landscape: stats left, buttons right.

### 2.12 Escape menu / World sheet (Menu)

Phone has no Esc; the **Menu** icon (top-right) and Android back both open it. Bottom sheet 70 percent (P) / right panel 45 percent (L). Tabs (48): **Play, Settings, Help, App**. Play: Resume, Command (battle only), Battle setup, New world, Save, Load, Scenarios, Cove report. Settings are in 2.13. Help: short cards with a speaker per card; "Things to try". App: Install, Update ready (if SW waiting), Edition switch, Developer (Cheats) toggle, Storage ("Clear game downloads"). Resume is always the first and largest button. Pausing: opening the sheet pauses the sim for battle too (existing behaviour assumed; verify), with a plain "Paused" word, never a timer.

### 2.13 Settings

Grouped, plain-language, each row = label + one-line help + control (48 px). Sections:
* **Display**: Quality (Auto / Battery saver / Balanced / Best), Frame rate (Auto / 30 / 60), Text size (Normal / Easy read), Theme (existing four, unchanged), Reduce motion.
* **Controls**: Left-handed layout, Button size (S/M/L), Stick (Floating/Fixed), Look sensitivity, Invert Y, Tap to fire, Auto-fire on target, Aim assist (Off/Low/Normal), Gyro aim (off), Vibration (on).
* **Sound and voice**: Master, Effects, Squad voices, Voice speed, Read messages aloud, Captions (on).
* **Game**: Soldiers per side (4 to 14 phone), Skins (Wi-Fi), Edition, Developer mode (cheats).
* **Data**: Downloaded files list with sizes, "Free space" button (clears the assets cache with a warning that it re-downloads), Install app.

All values persist under `squall-cove-` prefixed keys, shared across editions where meaningful.

---

## 3. Phone vs desktop feature matrix

Bounded by MOBILE-AUDIT 4.3 and 4.4 (budget and features); this is the consolidated, UX-oriented view. "Why" explains each difference.

| Area | Phone edition | Desktop edition | Why |
|---|---|---|---|
| Maps (sandbox) | Cove, Large cove, Port | + Urban, Desert, Lemnos | Draw calls; downloads (MOBILE-AUDIT 1.3) |
| Maps (battle) | Port; Urban/Desert after bake pass | All | Same |
| Input | Touch, optional gyro, haptics | Mouse + keyboard (pointer lock), touch also works | Hardware |
| Primary battle mode | Command from above + tactical map; lite first person | Full first person + Command | Screen size, comfort |
| Bots per side | 6 default, 4 to 14 | 9 default, up to 70 | CPU, thermal |
| Classes | 4 | 11 | Screen space; fat finger |
| Vehicles | Jeep, technical, APC, one boat; one heli | All | Controls and draw calls |
| Helicopter | Ride/command; optional simplified piloting | Full piloting | Control complexity |
| Skins (troops2) | Off, Wi-Fi opt-in | Opt-in | 13 MB, GPU memory |
| Cheats | Hidden behind Developer toggle | On | Menu clutter |
| Panels | Bottom/side sheets, one at a time | Side pane + panels together | Screen real estate |
| Edit pane tabs (Map/Events/Live/Play) | Folded into Menu and sheets | Present | One thing one place |
| Keyboard hints | None | On | No keyboard |
| Quality | Auto with Battery saver; DPR cap 1.5; MSAA off at DPR >= 1.5; 30 fps idle | DPR up to 2.5, MSAA | Thermal, battery |
| Shadows | 1024, +/-30 m | 2048, +/-48 m | Fill rate |
| Particles | Reduced | Full | Draw cost |
| Sound | Core 6.6 MB first; rest on Wi-Fi | All | Data |
| Wake lock, haptics, back-button handling | Yes | No | Phone-only APIs |
| Read-aloud, themes, easy text, captions, no timers | Yes | Yes | Shared accessibility baseline |
| Saves | Shared format; trimmed on load with a toast | Shared | Cross-device play |
| Switching | Boot menu link, `?edition=`, Menu > App | Same | Never lock anyone out |

Tablets (coarse pointer, min dimension above 700) default to desktop edition with touch controls.

Rule of thumb: **anything the phone omits must degrade by choice, not by breakage**: a desktop save with 70 bots loads on the phone and is trimmed with a message; a desktop-only map shows greyed with the reason.

---

## 4. Touch control scheme

### 4.1 Gesture table

| Context | Gesture | Action |
|---|---|---|
| Overview/tactical map | 1-finger drag | Pan (orbit in overview) |
| | 2-finger pinch / twist | Zoom / rotate |
| | Tap | Select (pick radius 1.3x); tap empty = deselect |
| | Double-tap | Centre/zoom on point |
| | Long-press 420 ms on ground | Box select (haptic 15 ms); also the Box select chip |
| | Tap armed fire mission target | Place; second tap confirms for expensive missions |
| | Drag a selected squad to ground | Move order (tactical map) |
| First person | Drag in look zone | Look |
| | Floating stick | Move; Run when pushed past 0.82 or Sprint lock |
| | Tap look zone | Fire (only if "Tap to fire" on) |
| | Two-finger tap look zone | Ping/mark (squad) |
| | Hold Fire | Auto-fire weapons repeat |
| | Double-tap Fire | Reload (alt; button also exists) |
| | Tap Zoom | Toggle scope (hold-to-zoom as option) |
| | Swipe up from stick | Jump (alt; Jump button remains) |
| Vehicle | Left stick | Throttle/steer; right drag = gun aim |
| Heli | Left stick pitch/bank; right drag yaw; Up/Down strip | Fly |
| Sheets | Drag handle down / Android back / tap scrim | Close |
| Everywhere | Edge-swipe back from the OS | Closes the top sheet first (history state) |

Rule: every gesture also exists as a labelled button (no gesture-only features; dyslexia and motor accessibility).

### 4.2 Haptics (all optional via Settings > Vibration)

| Event | Pattern (ms) |
|---|---|
| Button press (primary) | 8 |
| Box-select start | 15 |
| Fire mission confirmed | 25 |
| Hit marker on enemy | 10 |
| Taking damage | 30 |
| Knocked out / game end | 60, 40, 60 |
| Reload done | 12 |

Never vibrate on every frame; throttle to one pattern per 120 ms; respect Reduce motion.

### 4.3 Aim assist and gyro

Aim assist (default Normal for touch): while Fire is held or the reticle is within 4 degrees of a living enemy, bias yaw/pitch 15 to 25 percent toward the chest; touch player hit radius 1.3x; slows look speed 30 percent near a target (friction). Off for desktop mouse. Gyro (opt-in): `devicemotion` rate gating, low gain 0.6, a "Recentre" button; disabled while a sheet is open. Reference norms: aim assist on, optional gyro, layout customisation in mobile shooters ([CoD Mobile guide](https://www.charlieintel.com/call-of-duty-mobile/best-cod-mobile-settings-multiplayer-145921/)).

### 4.4 Layout customisation

Left-handed mirror; button size S/M/L (scales 0.85 / 1.0 / 1.2, all stay at least 44); optional drag-to-reposition later (phase 6, not first release). Stored per orientation.

---

## 5. Performance budget and plan

### 5.1 Budget (S23, Chrome, Cove/Port first, city maps later)

| Metric | Phone target | Hard fail |
|---|---|---|
| Frame time p95, battle at default 6 a side, Port | <= 20 ms (50 fps+) | > 33 ms |
| Frame time p95, Cove sandbox | <= 16.7 ms | > 25 ms |
| Draw calls per frame | <= 700 (`renderer.info.render.calls`) | > 1,200 |
| Triangles per frame | <= 450 k | > 800 k |
| GPU textures + buffers | <= 250 MB estimated | tab killed |
| JS heap after 10 min | <= 350 MB, no growth > 10 percent minute 5 to 10 | growth > 30 percent |
| First paint of boot menu | <= 1.5 s warm, 3 s cold | > 5 s |
| First launch download | <= 20 MB sandbox, <= 30 MB battle | > 46 MB default |
| Release re-download | <= 2 MB (assets cache stable) | any asset re-fetch |
| Battery drain (20 min battle) | <= 12 percent [est, measure] | > 20 percent |
| Thermal | no sustained fps below 30 after 10 min | < 24 fps |

### 5.2 Plan

1. **Measure first**: add a hidden overlay (`?perf=1`) printing fps, p95 frame, draw calls, triangles, heap, DPR, quality tier; record per scene into `QA-LOG.md`. The code already has `window.__pf` and `PFT`.
2. **Quality tiers**: Best / Balanced / Battery saver / Auto. Auto starts Balanced on phone; every 2 s compares the 2-s average frame to target and steps **resolution first** (DPR in 0.25 steps between 1.5 and 0.75), then shadows (1024 to off), then grass/trees caps, then frame cap 30 floor. Steps back up only after 10 s comfortably under budget (hysteresis; invisible to the player, not a visible timer). Matches the ADPF approach: resolution first, FPS floor 30 ([Android case study](https://developer.android.com/stories/games/netmarble-got-adpf)).
3. **Renderer settings**: DPR cap 1.5 (battery 1.0), `antialias` false at DPR >= 1.5 (set at renderer creation from edition, since it cannot change later), shadow map 1024 with +/-30 m, tone mapping kept (cheap).
4. **Draw calls**: bake/instance the urban and desert props (MAP-VIBRANCY 6.2) before enabling those maps on phone; until then they stay greyed. Merge static meshes by material per tile; use `InstancedMesh` for repeats ([Three.js optimisation guide](https://tympanus.net/codrops/?p=86572)). Cull the UI: remove `backdrop-filter` from phone UI entirely.
5. **Idle cap**: 30 fps in overview when nothing selected/moving; 60 in FP/vehicle; pause rendering when `document.hidden`; low-power when battery < 20 percent and `getBattery` exists.
6. **Context loss**: add `webglcontextlost` (preventDefault, show "Reconnecting" card, stop loop) and `webglcontextrestored` (let three.js rebuild; then re-upload dynamic textures; if the first frame after restore throws, reload with Continue from autosave). Autosave on `visibilitychange: hidden` and every 60 s in battle ([Khronos](https://wikis.khronos.org/webgl/HandlingContextLost)).
7. **Load-time memory**: decode packs one at a time, drop base64 strings after decode, avoid keeping `.b64.txt` in memory; keep skins off.
8. **PWA cache strategy** (mostly done in sw v9.3.0): page cache replaced each release; stable assets cache `squall-cove-assets-aN` for `assets/` and `audio/`; only the app's own prefix is ever deleted; never cache the manifest; navigation network-first with offline fallback. Remaining: precache the phone's minimum set on first Wi-Fi load only if user opts ("Download for offline"), show "Update ready" when a new SW waits, and a Data section listing cached sizes via `caches` + `navigator.storage.estimate()`. Bump `VERSION` for each shell release (see EDITION-RULES.md); bump `ASSETS` only if an asset's content changes under the same name.
9. **Wake lock**: request during battle/FP/helm; release on pause/menu; re-request on `visibilitychange`.
10. **Input latency**: pointer events with `touch-action:none`; passive listeners elsewhere; avoid layout reads in `pointermove`.

---

## 6. Test plan

### 6.1 Devices and viewports

* Primary: the real S23 (Chrome, installed PWA), portrait and landscape, with gesture navigation. Secondary: headless Chrome emulation at 360x780, 390x844, 412x915 (P) and 780x360, 844x390, 915x412 (L) with touch and `deviceScaleFactor` 2.8; desktop 1280x720 and 1920x1080 mouse.
* Standing hazard: **one headless Chrome window at a time, and kill it afterwards** (froze Robert's PC once). Use the existing `srv3.py` / `act.js` recipe; first screenshot after a warm-up frame (first shot is black otherwise).
* Themes: run the key screens in all four themes (dark, light, red low-light, green low-light); low-light themes must be pixel-identical to before for colour tokens.

### 6.2 State sweep (both orientations, both editions)

Boot menu, sandbox overview (nothing selected, something selected), Place/Land/Sky sheets, helm, battle setup, deploy, battle overview, Command (each tab), tactical map, FP (on foot), FP vehicle, heli, emplacement, end screen, Menu/World sheet, Settings, Help, cheats (desktop only), context-loss card, update-ready note.

### 6.3 Pass/fail criteria (automated where possible)

| # | Check | Pass |
|---|---|---|
| T1 | **Overlap**: for each state, query bounding rects of visible fixed interactive elements | No two overlap by more than 2 px; none under the safe-area; none covers the reticle zone (centre 20 percent) |
| T2 | **Targets** | Every visible interactive element on `ed-phone` >= 44x44 (primary >= 48); gaps >= 8 px (warn <8, fail <4) |
| T3 | **Thumb zones** | Frequently used controls (Fire, Jump, dock, Command, Deploy) have their centres in the lower 60 percent (P) or side 30 percent columns (L) |
| T4 | **No horizontal page scroll** | `document.documentElement.scrollWidth <= innerWidth` in every state |
| T5 | **Reachability** | Every action in the desktop key map has a phone control (checked from a JSON table `qa/action-parity.json`) |
| T6 | **Persistent controls count** | <= 9 visible persistent controls in overview and in FP; <= 4 surfaces |
| T7 | **No timers** | No visible countdown text; grep for `setInterval` writing digits into UI fails the check |
| T8 | **Text** | Min 14 px body, 12 px for tertiary labels; Easy text mode produces no overflow |
| T9 | **Performance** | Section 5.1 numbers measured 60 s in Cove, Port sandbox, Port battle at 6 and 10 per side, both orientations |
| T10 | **Soak** | 10 min battle: heap growth < 10 percent, no crash, fps >= 30 |
| T11 | **Context loss** | `WEBGL_lose_context.loseContext()` then `restoreContext()`: game recovers or offers Continue within 5 s; autosave loads |
| T12 | **Orientation** | Rotate during FP, Command, deploy, menu: no layout break, state kept, sheets still reachable |
| T13 | **Back button** | Android back closes sheet/menu in order, then offers Menu; never exits the app mid-battle |
| T14 | **Offline and update** | After first load, airplane mode: boots and plays Cove; after a VERSION bump, assets not re-fetched (network log) |
| T15 | **Shared origin** | `caches.keys()` after visits: only `squall-cove-*` changed; other apps' caches/localStorage untouched |
| T16 | **Console** | Zero uncaught errors in the sweep |

### 6.4 Standing parity guard (runs in every future release)

A script `qa/parity-check.js` (Node + the one-window headless harness) runs the same ordered set of actions in **both editions** and compares:

1. **Feature parity table** (`qa/parity-matrix.json`): list of capabilities (place object, sculpt, start battle, fire mission, deploy, FP shoot, drive, board heli, save/load, change theme...). Each has `phone: control selector`, `desktop: control selector or key`, or an explicit `desktopOnly`/`phoneOnly` with a reason. The check fails if a capability exists in the code but is missing from the table (scan for registered keys/actions) or if a listed selector does not exist/visible in the right edition.
2. **Desktop regression**: on `ed-desktop` at 1280x720, screenshot diffs of boot, overview, FP, Command, battle setup against golden images with a tolerance; any diff > 0.5 percent of pixels needs an explicit "golden updated" note in `QA-LOG.md`.
3. **Class integrity**: every phone rule is under `body.ed-phone` or `html.ed-phone`; a lint script greps the CSS for new rules that touch phone-only properties (`env(safe-area`, `touch`, `phoneStack`) outside that scope.
4. **Persisted data**: save from desktop edition loads in phone edition and back; settings keys unchanged.
5. **Console and network clean** on both.

Merge gate: parity check green on both editions + T1, T2, T4, T16, or the change does not ship.

---

## 7. Phased task list (for the implementation agent)

Each phase leaves a working game, runs the parity guard (once it exists), and ends with a VERSION bump. Never push without Robert's approval.

**Phase 0: baseline and harness (small).**
* Confirm what the other agent already landed (ED, `#phoneStack`, `#selBar`, FP ids, sw v9.3.0). Do not redo.
* Create `qa/measure-ui.js`: for a state, dump rects of visible interactive elements, safe-area overlap, size violations (T1, T2, T4). One headless window.
* Create `qa/parity-matrix.json` seeded from the key map in `UX-AUDIT.md` 5.9 and MOBILE-AUDIT 2.5; create `qa/parity-check.js` (6.4). Record desktop goldens.

**Phase 1: overlap and shell (CSS + toggles).**
1. Safe-area vars on all fixed UI; `viewport-fit=cover` verified.
2. Top bar owner: only status/ticket + Log + Menu on phone; merge More into Menu.
3. Bottom bar per mode (dock; Command/Map/Squad in battle); toast lane stays in `#phoneStack`.
4. Landscape rules: rail on the right for dock and FP clusters; sheets on the side; all under `@media (orientation:landscape) and (max-height:480px)` scoped to `body.ed-phone`.
5. Remove `backdrop-filter` on phone, opaque panels (`--panel` alpha 0.97), 3 px outline on floating buttons for outdoor contrast.
6. Back-button/history handling for sheets.

**Phase 2: first person touch.**
* Verify `#fpReload`, `#fpZoom`, `#fpSquad`; move Command to the top bar; Fire 72 px; Jump left; relabel Use by context ("Get out", "Board", "Open"); stance icon shows state; tools row only kit slots; floating stick and left-handed mirror; look sensitivity setting and lower default; tap-to-fire and two-finger ping; aim assist (4.3); sprint lock chip.
* Haptics (4.2). Gyro behind a setting (can slip to Phase 6).

**Phase 3: vehicles, heli, emplacements.**
* Heli yaw on look-pad, Climb/Descend strip, hover assist, "Land first" word. Emplacement layout (no stick, Get off, Zoom). Seat switch chip. Handbrake optional.

**Phase 4: Command, map, setup, deploy, end, menu.**
* Command bottom sheet with Mission summary row and pinned tabs; tactical map portrait/landscape layouts; confirm step for large missions; shorter setup footer; compact 4-class deploy; end screen with read-aloud and pinned buttons; Menu/World sheet as 2.12; Settings as 2.13; read-aloud speakers on Help/Command/End/Deploy.

**Phase 5: performance and resilience.**
* `?perf=1` overlay; quality tiers + Auto governor (DPR first, 30 fps floor); `antialias` at renderer creation by edition; idle 30 fps cap; context-loss handlers; wake lock; battery-saver when battery low; load-time memory trimming.
* PWA: Update-ready note, Data section, optional "Download for offline"; keep `MINE` regex exact.

**Phase 6: content and polish.**
* Edition switcher UX polish; phone map list greyed reasons; class set of 4; vehicles subset; save trimming toast.
* Bake/instance pass for Urban and Desert (MAP-VIBRANCY 6.2), then unlock them for phone behind "may be slow" label; spatial grid for `pushOutOfProps`/`losFull` to raise bot caps.
* Optional: drag-to-reposition controls, piloting full mode.

**Phase 7: S23 acceptance.**
* Install on the S23, run 6.3 manually in both orientations and four themes; record in `QA-LOG.md`; Robert signs off before any push.

Order of payoff: Phase 1, Phase 2, Phase 4 (setup/deploy/end), Phase 5 (context loss, tiers), then Phases 3 and 6.

---

## 8. Open questions for Robert (decide, do not block)

* Is landscape the expected FP posture? (Plan assumes yes, portrait still fully playable.)
* Gyro aim: keep as opt-in or drop?
* Helicopter piloting on phone: ride-only first (assumed) or simplified pilot now?
