# Squall Cove: phone audit and edition strategy

Snapshot of `index.html` taken 2026-10-07 (sw VERSION v9.2.0, boot menu "v9.1 start menu"). Read-only audit; nothing was edited. Line numbers are in the current file and will drift while another agent edits. Evidence tags: **[code]** read in source, **[shot]** seen in a headless capture or the owner's screenshot, **[audit]** taken from an existing audit file, **[est]** my estimate (not measured on a phone).

Captures used: owner's S23 screenshot (old v9.0 start card under live UI), `cdp/mob2/m_01..09` (current build, boot menu fine, later shots stuck on the loading screen), `cdp/mob/m_*` (previous build, 23-state sweep) and its `log.json` overlap report.

---

## 0. The honest answer

**Yes, a good phone version is possible, and it is mostly a UI and content-profile problem, not an engine problem.** The engine already runs on the phone (the headless sweep reached overview, command, setup, battle, first person, deploy and end screen at 390 x 844) and already has about 40 `isTouch` caps. What makes the phone "crazy" is that the phone is shown the desktop game's *surface*: roughly 30 persistent fixed elements stacked in a 390 x 844 box, a 7-button first-person cluster, menus that assume keys, and a first run that downloads 18 to 46 MB.

What a phone edition will be: a **commander's game** (Sandbox on Cove and Port, and Command battles from above with fire missions, squads and a tactical map), with an **optional, simplified first-person** mode. What it will not be: the 70-a-side, all-vehicles, 13 MB-skins, Lemnos-city, cheats-panel game. That stays on desktop.

**Recommended path (one sentence):** keep one codebase and one `index.html`, add an explicit **edition** (`phone` / `desktop`, auto-detected, user-overridable, stored in the URL and localStorage) that gates content packs, caps and UI layout through a single `ED` object and one body class, ship it in six small phases starting with an overlap-removal pass, and do **not** fork the repository. A true fork would double a 1.46 MB, 12,000-line file that three agents are editing daily, for no technical gain.

---

## 1. Feasibility: what makes the phone build hard

### 1.1 Download size

Source of truth: boot-menu table `MB = { base: 11.1, town: 2.7, build: 5.5, men: 7.4, skins: 12.7, sound: 6.6 }` (L122), `MAPS[...].real` for Lemnos (L125 to 129), `plan()` (L203 to 208).

| What | Groups | MB |
|---|---|---|
| Cove or large cove, sandbox, sound on (menu says "18 MB") | base + sound | 11.1 + 6.6 = **17.7** |
| Port / Urban / Desert, sandbox | + town (port.glb) | **20.4** |
| Lemnos (any), sandbox (menu "21 MB") | + town + 0.34 to 0.42 JSON | **20.8 to 20.9** |
| Any battle map, no skins | + build 5.5 + men 7.4 | **33.3** (Lemnos 33.7) |
| Battle with `troops2` skins | + 12.7 | **46.0** |
| Sound, full set | `audio/` folder is 26 MB on disk; boot loads 6.6, "the rest arrives while you play" | up to ~**26** more |
| Fetched later, not in the table | `helis.glb` 1.37, `air.glb` 1.02, `weapons*.glb` ~0.5, `vehicles.glb` 0.99, `aircraft.glb.b64` 3.74, `fleet`/`ccg`/`ccgfleet` 0.95/1.29/7.83, Lemnos thumbs | **~3 to 15** depending on what is used [est: I did not trace every lazy fetch] |

Notes that matter:
* These are `.b64.txt` sizes. If the host gzips or brotlis text (GitHub Pages does), base64 of a compressed GLB compresses back to roughly the binary size, so real wire bytes are about 25 percent lower than the menu says (troops2 is 13.3 MB b64 / 10.0 MB binary; bveh 3.16 / 2.37; battle 3.37 / 2.53). The menu numbers are an upper bound; fine, they are honest-ish.
* Decode cost is separate: each `.b64.txt` is fetched as a string, base64-decoded, then parsed by GLTFLoader. Peak RAM during load for people.glb is about string (5.6 MB, UTF-16 so ~11 MB) + decoded buffer (4.2 MB) + parsed geometry [est]. troops2 triples that. On a phone the load *spike* is what kills tabs, not the resting size.
* **Hard problem found in `sw.js`:** the cache is named `squall-cove-` + `VERSION` (L2 to 3) and `activate` deletes every other `squall-cove-v*` cache (L6). Every release therefore **re-downloads the whole game (18 to 46 MB) on every phone**, and the boot menu's "nothing new to download" check (`checkCache`, L194) only matches the *current* version's cache. For a game that ships several times a day this is the single most expensive thing to a phone owner on mobile data. Fix: a second, stable cache `squall-cove-assets` for immutable files (`assets/*.glb.b64.txt`, `audio/*`, textures, thumbs) that is never deleted by version, with `index.html` alone in the versioned cache. Keep the `MINE` regex exact so other apps on the shared origin are never touched (standing rule).
* Over mobile data: 18 MB is about 1 minute on mediocre 4G; 46 MB with skins is 3+ minutes and, with the above, repeats per release. Wi-Fi first run is fine.

### 1.2 Memory (Android Chrome WebGL)

* Canvas: `setPixelRatio(min(dpr, 2))` on Low (L7689), `antialias: true` (L1164). On the S23 (dpr about 2.8) that is 2.0, so 780 x 1688 = 1.32 MP; with 4x MSAA the colour+depth targets are about 40 MB [est]. Shadow map 1024 x 1024 depth (L7690) about 4 to 5 MB.
* Textures: the ground/PBR set is 512 x 512 JPGs (27 maps + macro + water) so about 1.4 MB each with mips, **about 40 MB** total, plus the 2048 x 1024 sky (~11 MB with mips) [code: `file` on the assets]. Fine.
* Embedded GLB textures: unknown. `troops2.glb` is 10.0 MB binary; if it carries 1k to 2k textures per skin the GPU cost is 100 MB or more [est, not inspected]. That is the strongest reason the skins must default off on phone.
* Geometry/object counts: urban phone props alone are ~1,761 draw calls and 165 k triangles with ~312 static `CANNON.Body` [audit, MAP-VIBRANCY-AUDIT 6.1]. Each `place()` clones a node with its own geometry references (shared) but its own meshes, so JS heap grows with draw calls, not triangles.
* **No context-loss handling:** grep finds no `webglcontextlost`/`restored` handler and no `pagehide` fallback beyond `visibilitychange -> saveWorld('auto')` (L8100). Android Chrome does drop GL contexts for backgrounded tabs and under memory pressure; today that means a black canvas until reload. The autosave helps (it saves on hide), so recovery is "reload and Continue", but the boot menu would need a "Continue" path that is quick.
* Realistic ceiling: an S23 (8 GB, Chrome tab budget around 1 to 1.5 GB total, GPU share smaller) is comfortable at Cove/Port sandbox and Port battle with skins off; marginal at Urban/Desert battle; no headroom for skins + Lemnos + 70 a side. Older 3 to 4 GB phones would not survive the battle packs [est].

### 1.3 GPU: draw calls and fill rate (per map, phone profile)

From the audit (props only) plus other sources [audit, MAP-VIBRANCY-AUDIT 6.1]:

| Map | Prop draw calls (phone) | Total in view, estimate | Verdict on S23 |
|---|---|---|---|
| Cove | < 100 | ~300 incl. terrain, water, grass (14 k blades Low), trees (<= 340 Low, ~13 instanced draws), boats (MAX_BOATS 14) | smooth [est] |
| Port | 1,200 to 1,500 est. | ~1,600 to 1,900 | borderline: draw-call bound |
| Urban | **1,761** | **2,100 to 2,300** | over budget (audit's phone target is 700) |
| Desert | 831 | ~1,100 to 1,300 | borderline |

* Trees: Low caps at 340 instances (L1925) / `cap = isTouch ? 300` for the designed forest (L1496); instanced so draws are fine but triangles are not (no LOD [audit]).
* Shadow: PCFSoft single directional map, +/-48 m around the player [audit], 1024 on Low. OK.
* Fill: 2x DPR + MSAA + ACES tone mapping + a full-screen colour `#tint` layer + `backdrop-filter: blur(8px)` on **every `<button>`** (UX-AUDIT item 3: the Place tab renders ~150 blurred buttons over an animating canvas). The blur layer is a real phone GPU cost and is unrelated to the 3D scene. Removing it is a free win (Phase 1).
* The planned fix (bake and instance the props, MAP-VIBRANCY 6.2) cuts urban from 2,860 to roughly 150 to 250 draws on desktop and 120 to 200 on phone. **That work, not a fork, is what makes Urban and Desert phone-viable.** Until it lands, the phone edition should hide Urban and Desert for battles (or offer them behind a "may be slow" label).

### 1.4 CPU (single main thread, no workers)

* Per-frame profiler hooks exist: `PF`/`PFT` at L7754 (`window.__pf`), wrapping `updateBattle`, `updateAgents`, `armedLayer`, etc. plus `PF.worldStep` for cannon-es (fixed 60 Hz, L7785).
* Measured on a desktop JIT [audit, GAMEPLAY-AUDIT 2.4]: `pushOutOfProps` is the biggest cost, 0.5 ms at 9 a side, **2.6 ms at 1,000 props / 160 people**, 3.8 ms at 1,500; `senseEnemy` 0.12 ms/frame; `losFull` cheap; `planBattle` ~10 k ops per call, 1 to 2 calls per second at 70 a side; `hotSpot` allocates per aircraft per frame; `updateAAS` MG nests call `losFull` unthrottled.
* Phone translation [est]: an S23 big core is roughly 2 to 3 times slower than a desktop core on this kind of branchy JS, and sustained clocks drop further when hot. At the phone caps (BATTLE.size 5, up to 10; `peopleCap` 40, `MAX_PEOPLE` 36 in sandbox; `SQD_MAX` 4; `capSide` 3; `capHeli` 1; props cap 220/110 tiny; `cap: isTouch ? 90 : 190`) the per-frame battle cost is about 1 to 3 ms desktop-equivalent, i.e. 3 to 8 ms on the phone. That leaves 8 to 12 ms for rendering at 60 fps, which the urban draw-call count blows through. So **the phone is GPU/driver-call bound on city maps and CPU-comfortable at the caps**. The planned grid for `pushOutOfProps`/`losFull` (CELL 16 m, 5 to 10x cut) is what would let phone armies grow from 10 to about 20 a side.
* Cannon-es with ~312 static bodies on Urban is cheap (static) but the broadphase list is large; `world.broadphase.dirty` is set every step (L7785), which forces a rebuild: worth checking on phone [est].

### 1.5 Battery and thermals

No frame-rate cap option, no "30 fps" quality tier, no `visibilitychange` render stop (only autosave and voice cancel, L8100, L11113). `requestAnimationFrame` pauses by itself in a hidden tab, so that case is fine, but a phone in the hand runs 60 fps at 2x DPR with MSAA: expect thermal throttling in 5 to 10 minutes of battle [est]. Cheap fixes: a **Battery saver** quality tier (DPR cap 1.5, `antialias` off, 30 fps cap in overview when nothing is selected, shadows off), and an adaptive step that lowers DPR when the 2 s average frame time exceeds 24 ms.

### 1.6 Input, platform features

* **Pointer lock:** absent on Android; the code branches on `isTouch` everywhere (`if (!isTouch) lockPointer()` L4208, L5690, L5866). Fine.
* **Web Speech:** `speechSynthesis` exists in Android Chrome with Google TTS voices, but `getVoices()` is empty until `voiceschanged` fires (handled L11070 to 11071), and speech needs a user gesture first; `visibilitychange` cancels the queue (L11113). The "squad voices" feature should work; the boot-menu option "Squad voices" lists no size cost. Risk: the voice picker (per callsign profile `VOICE.prof`) assumes several distinct voices, and Android often exposes only 1 to 4 per language [est]. Test on the S23.
* **Orientation:** manifest `orientation: any`; no `orientationchange` handler found; layout relies on CSS and `resize()`. Landscape is only handled by one `@media (max-height:480px)` block that tightens `.actions`, `.inst`, `.tabs`, `.chip` (L389 to 399); nothing for `#bHud`, `#cmdBtn`, `.fpBtns`, `#sqHud` etc. in landscape.
* **PWA:** installable (manifest id `/squall-cove/`, scope `./`, `display_override` fullscreen first, maskable icon). Install UI exists (`bInstall`, `bInstallTop`, L842 to 845). No wake lock (screen can sleep mid-battle on a long watch), no `screen.orientation.lock`, no `navigator.vibrate` except on long-press (L7291, L8776).
* **Input latency:** touch uses Pointer Events with `touch-action:none` on the canvas and look pad; fire is `pointerdown` on `#fpFire` (L4482), so fire latency is one frame. Good. The stick has a 46 px invisible hit extension (`#fpStick::after inset:-46px`).

### 1.7 Ranked hard limits

1. **UI surface density (not technology).** About 30 independently positioned fixed elements, three different anchoring schemes (`--bh` chain, `top:` offsets, hard-coded `bottom: 168px`), and touch paths for features that only have key paths. This is why it feels "crazy", and it is fixable in CSS plus a handful of JS toggles. See sections 2, 3.
2. **Draw-call count on city maps** (Urban 2,100 to 2,300 vs a 700 phone target). Needs the bake/instance work; until then Urban/Desert battles are off the phone menu.
3. **Download and re-download:** 18 to 46 MB first run and the per-release cache wipe in `sw.js`. Needs a stable asset cache and a phone default of no skins.
4. **Thermal and battery** at 60 fps / 2x DPR / MSAA with no battery tier.
5. **Memory spikes on load** (base64 strings plus decoded buffers; troops2) and **no context-loss recovery**.
6. **Main-thread AI at scale** (`pushOutOfProps`, `losFull`, `planBattle`): caps 5 to 10 a side are safe; 20+ needs the spatial grid.
7. **Missing touch paths** for reload, aim-down-sights, squad ring/ping/mount/heal/hold-fire, helicopter yaw and altitude (section 2).
8. Speech voice variety on Android, orientation handling, no wake lock (small).

---

## 2. Touch input and gameplay audit

Legend: **Works / Partial / Unusable**.

### 2.1 Overview (god camera)

| Feature | Status | Evidence and fix |
|---|---|---|
| Pan, orbit, pinch zoom | Works | Pointer-event state machine `ptrs` (L7289 to 7334): 1 finger pans/orbits, 2 fingers pinch/rotate (`g2 = twoInfo()`). |
| Tap select (people, boats, objects) | Works | Pick radius is widened 1.3x on touch (`bd = 46 * 1.3`, L7263 and L7274). |
| Box select | Works but undiscoverable | Long press 420 ms on empty ground starts a marquee, with vibrate and a toast "Drag to select a group. Lift to deselect." (L7291). Keyboard `B` has no button. Fix: a "Select box" chip in the selection bar or the Select tool row. |
| Select all | Partial | `selectAllVisible` exists; no phone button. |
| Context actions (Topple, Remove, Deselect, Rescue helicopter, First person) | Partial | They render as a right-hand column of buttons (shot m_1_overview: 6 stacked above More/Menu/Log). They cover the right 40 percent of the world view and collide with the instruments card at top-left for tall selections. Fix: one bottom selection bar (UX-AUDIT section 5). |
| Edit (side-pane toggle) | Partial | Floating "Edit" tab at left middle (m_1_overview): 63 x 47, clips the left edge, overlaps nothing but is awkward to reach one-handed. Move to the dock as a 5th "Edit/Place" tab. |
| Tool dock (Select/Place/Land/Sky) | Works | Bottom-centre, 44 px min via the coarse rule. |

### 2.2 Place / build

`#side` (width `min(332px, 90vw)`, L496) slides over everything on a phone; `body.sideopen` only reflows siblings at min-width 700 (L403), so on phone the pane is simply a full-height overlay, hiding the dock and the world. The Place tab is ~150 blurred buttons [audit]. Placement is cross-and-button on touch: `reticlePt()` (L2800) = `pick(innerWidth/2, innerHeight*0.4)`, `#placeBtn` 92 px circle (L288) plus `#turnBtn` rotate (64 px). Tap-to-place is disabled on touch (`if (isTouch) return` L7374), so the player must pan the world under a fixed cross. That is a legitimate phone pattern and works. **Partial:** the tray (`#trayTog`, 36 px) and `#objective` buttons are under 44 px (UX-AUDIT 4.5), and the pane covers the cross. Fix: Place as a 55 percent-height bottom sheet that leaves the cross at 40 percent visible, and a category chip row instead of 150 buttons.

### 2.3 Land sculpt

`land.finger = isTouch ? 'hold' : 'paint'` (L2701): hold the `#sculpt` button (92 px) with the brush at the screen reticle, other thumb pans. **Works** in principle, **partial** in practice: the sculpt/undo/turn/place cluster is at `right:16/118; bottom: --bh+22..30` (L288 to 289) and collides with `#cmdBtn` (moved up by `body:has(...)` rules L553 to 554), `#calmBtn`, `#objective` and the toast column. Land size/strength controls are in the side pane which then hides the terrain being edited. Fix: sculpt cluster in a fixed bottom-right slot that owns that slot while Land is active; hide Command/Calm there.

### 2.4 Helm (boat control)

`body[data-mode="helm"] .helm{display:flex}` under `pointer:coarse` (L335): a bottom pad with steer left/right, Ease/Trim/Auto (relabelled Astern/Ahead/Stop on motor boats without a visual cue, UX-AUDIT 174). **Works.** Fix: one sentence label change and a throttle slider for motor boats.

### 2.5 First person (on foot)

Controls (L4358 to 4482, L775, CSS L515 to 536):
* Move: `#fpStick` 132 px at left 18 / bottom 24, 56 px radius, run at stick magnitude > 0.82 (L4306). Works. No sprint toggle or lock.
* Look: `#fpLook` right 62 percent, 0.0068 rad/px (L4368). Works, but 3x desktop sensitivity with no setting. Add a sensitivity slider in settings.
* Buttons (`.fpBtns`, column on the right, min 84 x 46, Fire 64 tall): Helm, Drop (contextual), **Fire, Command, Stance, Jump, Use**. Stance cycles stand/crouch/prone (L4357). Total height 380 px of 844 (UX-AUDIT 66).
* Tool slots: `#fpTools` top-left row, 52 x 56 px buttons, horizontally scrollable, `max-width: calc(100vw - 150px)` (L4415, CSS L571).

| Function | Touch status | Fix |
|---|---|---|
| Walk, run, look, jump (Jump also gets up from ragdoll, L4296) | Works | |
| Fire | Works | `pointerdown/up` on `#fpFire`; hold repeats for `w.auto` weapons (L4471). Fire sits at the bottom of a 7-button column the right thumb must also use to look: **multitouch conflict**, because the look pad is 62 percent wide and *under* the buttons. A thumb dragging look that slides onto Fire fires; a thumb on Fire cannot look. Fix: dedicate the right thumb to look and put Fire on a **left-index** position above the stick, or add a "Tap to fire" toggle on the look pad (tap = shot) plus auto-fire while the reticle is on an enemy (aim-assist below). |
| Reload | **Missing** | `fpReload` only on `R` (L4389) and automatically when the magazine empties (L4453). Add a Reload button (or double-tap Fire). |
| Zoom / ADS | **Missing** | `fp.zoom` only toggles on right mouse (L7345). Snipers and the carbine cannot use their scope on touch. Add a Zoom toggle button shown only for `scoped` weapons. |
| Crouch / prone | Partial | One cycling button (stand, crouch, prone). OK but toast-driven; label the button with the current state icon. |
| Grenades, charges, mines | Partial | Tools in the top slot row (`grenade`, `c4`, `atmine`), then Fire throws/plants. Works but the row is hidden behind a horizontal scroll, 4 slots visible on 390 px (shot m_11_jump shows Hands/Rod/Pistol/SMG only). Fix: slot chips for the kit's 3 to 5 tools only; a dedicated Throw button when grenades remain. |
| Use / ladders / board / pick up | Works | Contextual prompt text is touch-aware (`isTouch ? 'Use' : 'E'`, L4236 to 4247, L11280). The prompt (`.fpPrompt`, bottom 230 px) overlaps `#bStat` and the stick region (m_11_jump: "Oak crate..." box covers Health and LMG lines). |
| Leave to overview | Works | `#fpExit` top-right 89 x 46 overlaps the tool row and the `Overview` button area (measured: `fpExit x BUTTON [263,12 56x66]`, `x BUTTON [325,12 71x66]`). |
| Squad: ring (N), ping (I), hold fire (K), mount (M), heal (U) | **Unusable** | `sqdWheelOpen` has one caller: the `n` key (L10990). `#sqHud` is `pointer-events:none` (L10941). Squad orders on touch are only the Command panel's Squad tab, which says "Drop into first person" in overview (L10939 region). Fix: a Squad button on the FP cluster that opens the existing `#sqWheel` (it already has `body.touch #sqWheel .s{pointer-events:auto}`, so the ring was designed for touch and simply has no trigger); Ping = tap on look pad with two fingers or a ring slice. |
| Aim assist | **None** | Only effect: accuracy of *bots* vs touch players is x0.8 (L5210). The player's own aim has no magnetism. Add: when Fire is held and an enemy is within 4 degrees of the reticle, bias yaw/pitch 15 to 25 percent toward the chest; plus enlarge hit radius x1.3 for touch players. |
| Auto-fire | Partial | Automatic weapons repeat while held (L4471); no "auto fire when aimed at enemy" option. |
| Fat finger | High risk | Fire/Command/Stance/Jump/Use are 46 px tall with 8 px gaps in one vertical column; Command (opens a full-screen sheet) sits directly above Stance and under Fire. A mis-tap during a firefight takes the player out of the game. Fix: move Command off the cluster (to the top bar or the tactical-map button), enlarge Fire to 72 px, and put Jump on the left. |

### 2.6 Vehicles (driving)

`fp.sx/fp.sy` (the stick) feed `driveVehicle`-style code at L6704 and heli at L6989, so **ground vehicles drive with the left stick** (forward/back/steer) and Fire shoots the gun; Use leaves (hint text at L6676, L6733 says so). **Works.** Gaps: no brake/handbrake, no reverse-lock, gunner seats use the look pad (fine). **Helicopters: Unusable to Partial**: stick = pitch/bank only; yaw is `Q/E`, climb is Space and descent is Shift/Ctrl; on touch `up` is forced to -0.2 (slow sink) and the Jump button gives a 0.5 s climb pulse (`fp.vhb = 0.5`, L4375). Flying is possible but crude. Fix: add Climb and Descend as a vertical slider/two buttons and make look-pad horizontal drag yaw the helicopter.

### 2.7 Battle (overview side)

| Part | Status | Notes |
|---|---|---|
| Battle setup (`#bSetup`) | Works | Full-screen sheet (m_7_setup). Soldiers slider caps at 10 on touch (L10701). The overlap report (`big x BUTTON...`) is the sticky footer covering scrolled content: 4 rows lost under a 130 px footer. Fix: shorter footer (one primary button; Watch/Fight as a segmented pair above it). |
| Deploy (`#bSpawn`) | Partial | Class cards (11) take 5 screens of scroll; the sticky `.dpRow` (`bottom:-12px`, L460) pushes "Replay" and "Back to overview" partly off the bottom (m_13: Replay clipped at y=830 of 844). Fix: 2-column compact classes (icon + name, one-line description), footer inside the safe area. |
| End screen | Partial | Shows stats (m_14) but overlaps FP buttons and the ticket bar beneath; fine once modal has a scrim (`#bSpawn` is not full-bleed). |
| Command panel (`#tablet`) | Works | 390 px, three tabs (Fire, Support, Points), 44 px chips, 60 px rows (m_6_command, m_9). Tall: about 1 screen per section. Fix: collapse Side/Target/Size/Pattern/Aim into one "Mission" row with a summary. |
| Tactical map (`#tmap`, new) | Works | Pan, pinch, tap to mark; column layout under 760 px or portrait (L11912). Best touch surface in the game. Make it the phone's primary battle view. |
| Fire missions | Works | Tap the map, pick type. Costs shown. |
| Select/order units | Works | Same overview gestures. |
| Spectate (Watch next, Jump in) | Works | Buttons at top-centre (m_10); overlap `bMenu` and the Log button (measured: `bR:Raiders 76 x bMenu`). |
| Vehicles/helis/emplacements/ladders | Mixed | Ladders: stick up/down (L11268, works). Manned emplacements: Fire button (`fpManFire`), aim by look pad: Works. Boarding: Use. |
| Cheats | Unusable as designed | `#cheatSheet` is a large sheet with `CH_LIST` toggles (L662, L11335); fine to have, but it is menu clutter on phone. Hide on phone edition. |
| Captions and voice | Works | Captions are on-screen text; voice depends on Android TTS (section 1.6). |

### 2.8 Text size, targets, contrast, one-handed reach

* Min target: the coarse rule gives `button,.chip,.tabs button{min-height:44px}` (L401). Misses (UX-AUDIT 4.5): `#trayTog` 36, `#objective button` 36, `#inspector` buttons 36, `.mback` 40, `#hudOn` 40, `#tmap .tmSide .tbOpt button` 40 (L11910), `#fpTools` buttons are 56 x 52 (ok).
* Text: body 14 to 17 px; `#fpHint` 13 px (hidden in battle); `#sqHud` 13 px (width 150); mono sub-labels 10.5 to 12 px (`.chip .dn`, `#fpTools .k`); readable in the dark theme, thin outdoors. The red and green low-light themes (owner's favourites) are intact. `html[data-text=easy]` doubles via `zoom:1.12` on the HUD (L601), which makes overlap worse.
* Contrast outdoors: panels are translucent `rgba` over a bright scene; UX-AUDIT 194 measured 3.9:1 for paper-on-stick. Phone edition should use opaque panels (`--panel` alpha 0.97) and a 3 px outline on floating buttons.
* Reach: the bottom third has the dock (good), Command (bottom right, good), selection actions (top right, bad), More/Menu/Log (top right, bad), tools row and exit (top, bad). One-handed phone play needs Menu and Exit in the lower half or on a swipe-up sheet.

---

## 3. Menu audit, 390 x 844 and 844 x 390

Measured overlaps (cdp/mob/log.json) and screenshots:

| Surface | 390 x 844 finding | 844 x 390 finding (no landscape capture exists; from CSS) |
|---|---|---|
| **Boot menu** (`#boot`, m_01, m_02) | Fine. Mode cards, map cards with size, options, one Start button. The owner's screenshot shows the *old* v9.0 card sitting under live game UI; the new static start menu fixes that structurally (nothing loads until Start). Issues: map list is long (8 maps, ~3.5 screens) and the Options block shows "Quality: low" and "Squad voices" as 56 px cards; no phone-edition label or switcher. | `#boot` scrolls; cards one column so landscape wastes width: use 2 columns with `@media (orientation:landscape) and (max-height:480px)`. |
| **Overview HUD** (m_1) | Persistent: Edit, Log, Menu, More, instruments card, selection actions (6 buttons), Deselect pill, Command, Select box row, dock. Overlap: `bR:Raiders x bMenu` in every battle overview shot (ticket bar vs Menu button, 19 px wide), toasts and the Command button over menu cards (owner's screenshot), `#feedCol` and `#objective` over the world at left. | `.actions` column scrolls (`max-height: 100dvh - 118px`) but nothing keeps it from overlapping `#bHud`/`#feedCol`. |
| **Side pane** `#side` | Full-height overlay at 90vw; covers the dock; Place tab 150 buttons; 5 tabs (Select/Battle/Map/Events/Live/Play/Place appear in the sweep: m_2_tab_*) | 332 px wide eats 39 percent of 844. |
| **Menu sheet** (`menuSheet`, m_3) | Works: 4 tabs (Play, Settings, Help, App), 12 cards (Command, Battle setup, New world, Start over, Save, Load, Scenarios, Things to try, People, Fleets, Cove report) in a 2-column grid, Close at bottom (44 px). Duplicates: "Command" and "Battle setup" are also on the HUD; New world and Start over vs boot's map picker. **More** (hidden under it) and **Menu** are two buttons for one idea. | Sheet is `max-height: 100dvh - 24px`, the footer Close scrolls under the card; fine. |
| **Command panel** (m_6) | Works; top bar shows Close at top right 80 x 44 and a 3-tab row; long single column. The panel is a modal `tablet` and covers FP view. | Side/Target/Size/Pattern/Aim chips wrap into 5 rows and push the first mission to below the fold at 390 px height: the list would be invisible without scrolling. |
| **Battle setup** (m_7) | Overlap rows reported are scroll content under the sticky footer (false positives), but the footer is 130 px of 844 (15 percent) and the slider/segmented groups below the fold are reachable. | Footer 130 px of 390 = one third; the setup body is ~2 rows high. Unusable until the footer shrinks. |
| **Deploy** (m_13) | 11 class cards + 2 start points + Replay row; Replay/Back clipped at the bottom edge (y 830 of 844). | `#bSpawn` sticky `.dpRow` of 52 px + class grid: only 2 rows visible. |
| **End screen** (m_14) | OK content, 5 stat rows; overlaps FP buttons below (Stance/Jump/Use show through at the bottom). | 5 rows + 3 buttons ~ 420 px > 390: needs scrolling inside. |
| **Cheats panel** | Not captured; `#cheatSheet` with `CH_LIST` (L662, L11335) plus a `#cheatChip` status chip (L663) that sits at the top; one more fixed element. | |
| **Settings / Help** (m_3_menu_settings/help) | OK; Help is a 700-word card (UX-AUDIT 19: two start screens in a row). | |
| **FP HUD** (m_11) | Overlaps measured: `hpn: Health x fpPrompt`, `LMG 60/60 x fpPrompt`, `fpExit x two top buttons`. Ticket bar sits under the tool row (visible in m_11, tickets and tools touch). | Ticket bar plus tool row plus exit consume 70 px of 390 height. |

**Duplicate controls:** Command (HUD pill, FP button, Menu card, tactical-map button), Battle setup (Menu card, HUD), Menu vs More, Fleet and select hint vs dock labels, Quality in boot, Settings and `bQual`, Edit vs Place tab.

**Scroll traps:** nested scrollers: `.sheet` (overflow-y:auto) wrapping `.sc .sb` (overflow:auto) wrapping the lists; Android overscroll behaviour is contained (`overscroll-behavior:contain` L553, L560), so no body scroll trap, but a scroll-in-scroll can make "can't scroll" moments when the inner list is at its end.

**Unreachable on touch:** cheats toggles that need keys; squad ring; ping; mount; heal; reload; zoom; helicopter yaw; box-select button; `selectAllVisible`.

---

## 4. Strategy

### 4.1 Options compared

| | A: one codebase + device profile | B: true fork (`/m/` shell) | C: packages on demand |
|---|---|---|---|
| Fixes overlap | Yes, by one body class and one phone layout | Yes, by writing a second UI | No (size only) |
| Fixes download | Partly (defaults) | Yes | **Yes** |
| Engine cost | None; already has `isTouch` caps | Doubles 1.46 MB / 12 k lines, every bug fixed twice | Moderate (split the single HTML) |
| Risk with 3 agents editing `index.html` | Low (adds one `ED` object) | **High: merge conflicts, drift** | Medium |
| Owner can play both on the same save | Yes | Needs a shared-save contract | Yes |

**Decision: A, plus the part of C that already exists.** The boot menu already is a package manager (`groups()`, `plan()`, `KEYF`, `cached`, `checkCache`): base, town, build, men, skins, sound, plus `m_*` map packs. Make phone defaults pick *smaller packs* rather than inventing new package files. Do not build B: nothing the phone needs requires a different engine, and the feature gaps (reload, zoom, squad ring, aim assist) are bugs that the desktop touch players also have. One thing from B is worth taking: a **separate CSS block for the phone layout** (`body.ed-phone ...`), so that it can be reasoned about independently of the desktop rules.

### 4.2 Edition model

* `ED = { id: 'phone' | 'desktop', ...caps }`, decided once at the top of the boot script (before `launch()`), exposed as `window.__BOOT.edition` and the class `ed-phone` or `ed-desktop` on `<body>` (and `document.documentElement.dataset.edition`).
* Detection: `edition = urlParam('edition') || localStorage['squall-cove-edition'] || (matchMedia('(pointer:coarse)').matches && Math.min(screen.width, screen.height) <= 700 ? 'phone' : 'desktop')`. Tablets (coarse pointer, min dimension > 700) default to **desktop edition with touch controls**, which already works.
* Switcher: a link at the top of the boot menu, "Phone edition  ·  Switch to desktop edition", plus a Menu > App card; stores to `localStorage` and `?edition=` (URL beats storage for sharing). Never hides content a player explicitly chose; desktop edition on a phone simply shows the warning "needs about 46 MB and a recent phone".
* Entry URLs: same URL for everyone (`/squall-cove/`); `?edition=phone` and `?edition=desktop` as shareable overrides. A separate `/m/` is unnecessary and would give a second PWA scope on the shared origin (violates the unique-manifest-id rule's spirit).
* Saves and settings: **shared.** `squall-cove-boot`, `sc-quality`, `squall-cove-voices`, and world saves use the same keys; the edition is stored under one new key. A save made on desktop (more people, props) loads on the phone with caps applied on load (clamp `MAX_PEOPLE`, drop excess) and a toast "trimmed for this phone".
* PWA/service worker: one manifest id, one scope, one SW; the SW learns nothing about editions. Packs a phone edition never requests are never cached. Two changes: the stable asset cache from 1.1, and `precache` stays tiny (index, icons, thumbs).

### 4.3 Budget table (phone vs desktop)

| Item | Phone edition | Desktop edition | Today's phone default |
|---|---|---|---|
| First download (Cove/Port sandbox) | **~18 to 20 MB** | 20 to 25 MB | 18 to 21 MB |
| Download, Command battle | **~28 MB** (base+town+build+troops.glb, no vehicles pack until used, sound 6.6) | 33 MB | 33 MB |
| Skins (troops2) | **off, hidden behind "Wi-Fi only" confirm** | on (13 MB) | off, offered |
| Sound first part | 6.6 MB, rest on Wi-Fi only | all | 6.6 + rest |
| Re-download per release | **0** after the SW fix | 0 | 18 to 46 MB |
| DPR cap | **1.5** (battery saver 1.0) | 2.5 | 2.0 |
| MSAA | off at DPR >= 1.5 | on | on |
| Shadow map | 1024, +/-30 m | 2048, +/-48 m | 1024, +/-48 m |
| Total draw calls in view | **<= 700** | 1,600 | 1,100 to 2,300 |
| Triangles in view | **<= 450 k** | 1.2 M | up to 1.5 M+ trees on Port |
| Trees / grass blades | 300 / 14 k | 780 / 42 k | 340 / 14 k |
| Prop caps (capN / tiny) | 220 / 110 | 320 / 170 | same |
| People (sandbox / battle cap) | 36 / 40 | 170 / 220 | same |
| Bots per side | **6 default, max 14** (20 after the spatial grid) | 9 default, max 70 | 5 default, max 10 |
| Squad size (`SQD_MAX`) | 4 | 5 | 4 |
| Particles alive | 250 ambient + 150 debris (`DEB.N` 90) | 500 / 220 | same |
| Boats / objects | 14 / 90 | 26 / 220 | same |
| Vehicles (battle) | **Jeep, technical, APC, one boat; 1 helicopter** (`capHeli: 1`, `capSide: 3`) | all, 2 helis | cap only |
| Frame rate | 60 in action, 30 when idle in overview | uncapped | 60 |

### 4.4 Feature matrix

| Feature | Phone | Desktop |
|---|---|---|
| Sandbox: Cove, large cove | **on** (large cove: lite, MAX_BOATS 14) | on |
| Sandbox: Port | on (lite) | on |
| Sandbox: Urban, Desert, Lemnos | **off** until the bake/instance pass; then on, lite | on |
| Battle maps | Port only; Urban/Desert after bake; Lemnos off | all |
| Command from above (fire missions, support, squads) | **on, primary** | on |
| Tactical map | **on, primary** | on |
| First person | **lite** (simplified HUD, aim assist, big buttons) | full |
| Class loadouts | 4 (Assault, Marksman, Heavy, Medic) | 11 |
| Tools in FP | rifle, pistol, grenade, one special | all |
| Vehicles drivable | jeep, technical, APC | all |
| Helicopters | watch/command only; pilot optional later | full |
| Emplacements, ladders | on | on |
| Cheats panel | **off** (Developer toggle in Menu > App) | on |
| Squad voices, captions | on (captions default on) | on |
| Soldier skins (troops2) | off | opt-in |
| Disasters, volcano, lava | on, one at a time | on |
| Land sculpt, Place | on (cross + button) | on |
| Build menu categories | 8 phone categories (curated) | all |
| Save/load, share | on | on |
| Keyboard shortcuts hints | none | on |
| Battery saver | **on by default under 30 percent battery** if `navigator.getBattery` exists | n/a |
| Read-aloud, low-light themes, dyslexia text | on, themes untouched | on |

### 4.5 Wireframes

All 390 x 844 unless stated.

**Phone boot menu**
```
+----------------------------------+
| Squall Cove                      |
| Phone edition  [Switch edition]  |
|                                  |
| What do you want to play?        |
| [ Sandbox ] [ Command battle ]   |
|                                  |
| Map (3 big cards)                |
| +------------------------------+ |
| | thumb  The Cove       18 MB  | |
| | thumb  Port & mountains 20MB | |
| | thumb  Large cove     18 MB  | |
| +------------------------------+ |
| More maps (desktop edition) v    |
|                                  |
| Wi-Fi extras:  [ ] Skins +13 MB  |
|                [ ] Full sound    |
| Quality: Battery saver  v        |
|                                  |
| [   Start: The Cove   ]  (sticky)|
| Downloads about 18 MB. Once.     |
+----------------------------------+
```

**Phone overview HUD** (sandbox)
```
+----------------------------------+
| [Log 15]               [ Menu ]  |  top row: 2 buttons only
|                                  |
|        (world view, clear)       |
|                                  |
|                                  |
| toast (one, above dock, 3 s)     |
| [Select bar: Deselect|Box|Info]  |  only when something selected
| [ Select | Place | Land | Sky ]  |  dock, 56 px
+----------------------------------+
Command pill lives in the Sky/Select
dock row as a 5th slot "Command" in
battle; More + Edit fold into Menu.
```

**Phone battle HUD** (overview)
```
+----------------------------------+
| Port 76 (o o . . . . o o) Rd 76 |  ticket bar, top, no buttons under it
| [Menu]                  [Log]    |
|                                  |
|        world view                |
|                                  |
| [Watch next]  [Jump in]          |  contextual row
| [ Command ]  [ Map ]  [ Squad ]  |  big bar, 56 px, bottom
+----------------------------------+
```

**Phone first-person HUD** (touch scheme)
```
+----------------------------------+
| [Hand][Rifle][Nade]*   [Leave]   |  slots (kit only) + one exit
| Port 76  ooooo  Raiders 76       |  tickets
|                                  |
|            +  (look: whole       |
|                  right 2/3)      |
| hint: one line, fades in 4 s     |
| HP ====   LMG 60/60              |  left, above stick
|   ( )  stick        [Zoom][Rld]  |
|  (   )              [ FIRE 72 ]  |
|   ( )   [Jump]      [Use][Squad] |
+----------------------------------+
Fire is the only thing under the
right thumb that fires; look = drag
anywhere else; tap to fire optional.
Auto-fire toggle in Settings.
```

**Phone Command sheet** (bottom sheet, 60 percent height)
```
+----------------------------------+
| (map/world visible above, tap to |
|  place the marker)               |
+==================================+
| Command          [Mission v] [x] |
| [Fire] [Support] [Squad] [Points]|
| Port | Tap map | Medium | Single |  one summary chip row (taps to edit)
| +------------------------------+ |
| | Lightning strike   Ready   > | |
| | Missile            Ready   > | |
| | Bomb               Ready   > | |
| +------------------------------+ |
+----------------------------------+
```

### 4.6 Phased implementation plan

Each phase is one agent session, leaves a working game, and is tested on desktop plus a 390 x 844 and 844 x 390 headless pass (one Chrome window at a time).

**Phase 1: overlap removal (quickest win, CSS and a few toggles).**
1. Remove `backdrop-filter: blur(8px)` from the global `button` rule (line ~43) and `.note`/`#bTick` etc. under `body.touch`.
2. One top-right column owner: in `body.touch` stack `More`/`Menu`/`Log` into a single Menu button; hide `.actions` selection buttons when a bottom `.selbar` is shown (use the existing `#selFloat`); fix `bR x bMenu` by giving `#bHud` `max-width: calc(100vw - 70px)` (L459) and setting `#bMenu` below it (`top: calc(60px + var(--safe-t))`).
3. Anchor everything bottom via `--bh` (L7506 sync); replace `#bStat{bottom: calc(168px...)}` (L476), `.fpPrompt{bottom:230px}` (L526) with `--fpH` (height of the FP cluster measured the same way as `--bh`) so Health/ammo never sit under the prompt.
4. Make `#notes`, `#sideFeed`, `#killFeed`, `#feedCol` share one toast lane above the dock with max 1 visible on phone; stop `#notes` blocking taps (`pointer-events:none` on touch except its close).
5. Menu sheet: shorten cards; remove Command and Battle setup duplicates when `body.battle`.
Exact ids: `#notes #feedCol #sideFeed #killFeed #bHud #bMenu #bStat .fpPrompt #cmdBtn #calmBtn #objective #selFloat #sqHud #fpExit .fpTop #fpTools`.

**Phase 2: FP touch controls.** Add `#fpReload`, `#fpZoom` (only when `WPN[fp.tool].scoped`), `#fpSquad` (calls `sqdWheelOpen`), move `#fpTab` (Command) off the cluster to the top bar, enlarge `#fpFire` to 72 px, put `#fpJump` on the left above the stick, make `#fpTools` render only `kitTools()` slots. Add aim assist in `fpFireGun` (L4452) (bias `fp.yaw/fp.pitch` toward the nearest enemy within 4 degrees when `isTouch`) and a look-sensitivity setting for `0.0068` (L4368). Add `#fpClimb`/`#fpDive` for helicopters (L6989).

**Phase 3: edition object and boot menu.** Add `ED`, the `?edition=` parser, `body.ed-phone` class, the switcher chip in `#boot`, boot menu "Phone edition" label, hide Lemnos/Urban/Desert cards for phone battles (`MAPS[id].b`, `paint()` L157), change `S.b.size` default 6 and max 14 (L10701, L7901 clamp), skins default off with a Wi-Fi confirm (L205), sound split (first 6.6 MB, rest after load on Wi-Fi when `navigator.connection.saveData` is false).

**Phase 4: service worker and downloads.** In `sw.js` split caches: `squall-cove-assets` (never deleted by version, same `MINE` guard) for `assets/*`, `audio/*`; versioned cache only for `index.html`, icons. Update `checkCache()` (L194) to match both. Add a "Update ready" note. Expected result: release = ~1.5 MB.

**Phase 5: command-first phone battle.** Bottom action bar (Command, Tactical map, Squad) replacing the right-side `More/Menu/Log` stack, compact deploy (`#bSpawn` 2-column class tiles, 4 classes, footer in safe area), shorter `#bSetup` footer, Command sheet "Mission" summary row (`#tablet`), tactical map as the default first view on phone battles (`tmInit`, L11909).

**Phase 6: performance and battery.** Quality tiers (Battery saver: DPR 1.0 to 1.5, `antialias:false` requires renderer creation before boot, so recreate on edition change or set at launch from `__BOOT`), adaptive DPR step, 30 fps idle overview cap, `webglcontextlost` handler (`event.preventDefault()`, show a "Reconnecting" card, reload from autosave), wake lock during battle, landscape rules for every fixed element (`@media (orientation:landscape) and (max-height:480px)`). Then the bake/instance pass from MAP-VIBRANCY 6.2 to unlock Urban and Desert on phone; the spatial grid for `pushOutOfProps`/`losFull` to lift bot caps.

### 4.7 What I would not do

* Do not fork the file or add a `/m/` URL.
* Do not touch the low-light themes or the dyslexia text mode (standing rules); verify them on the new phone layout.
* Do not add timers or countdowns to the phone UI (standing rule); the Phase 1 "toast fades" are existing behaviour and stay short but not a game timer.
* Do not ship phone skins by default.

---

## 5. Answers, short

* **Is a good phone version possible?** Yes. The engine, caps and most touch inputs exist. The failures are layout (overlap), five missing touch paths (reload, zoom, squad ring/ping/mount/heal, heli yaw/altitude, box-select button), and an over-heavy default download plus a cache that wipes on every release.
* **What it will be:** a 18 to 28 MB commander's game: Cove and Port sandbox, Command battles with fire missions and a tactical map, optional lite first person, 6 to 14 soldiers a side, a few vehicles, no cheats panel.
* **What it will not be (until the bake/instance and spatial-grid work lands):** Urban/Desert/Lemnos battles, 70-a-side armies, 13 MB skins, all 11 classes, full helicopter piloting.
* **Best path:** one codebase, an `ED` edition with auto-detect and an explicit switcher, six small phases (overlap removal first, then FP touch, edition, service worker, command-first battle, performance). Start with Phase 1: it needs no new feature and removes most of what the owner is seeing in his screenshot.
