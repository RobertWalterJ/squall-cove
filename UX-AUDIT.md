# Squall Cove: UX/UI audit and redesign specification

Scope: `index.html` (8,691 lines, 1,000,429 bytes), `sw.js`, branch `large-map`. Read-only audit: nothing was edited, no browser was run. Line numbers are for the file as audited. Positions and sizes below are computed from the CSS (and the JS that sets `--bh`), not measured in a browser, so treat pixel values as plus or minus 10 px. Contrast ratios are computed (WCAG 2.x relative luminance).

Relationship to earlier notes: `MENU-AUDIT.md` was a content audit of an older snapshot (Sky sub-tabs, "Sides" and some Place groups have since been implemented). This document is about the interface shell: layout, duplication, naming, accessibility, cost, and a replacement design. It does not repeat feature gaps (that is AUDIT-FEATURES.md).

House rules applied: no em dashes, no timers or countdowns shown by default, short plain wording, sentence case.

---

## 1. Headline findings

1. **Four generations of menus sit on top of each other.** Bottom tabs plus a bottom tray (Command, Place, Land, Sky), a left side pane with six tabs (Place, Events, Live, Map, Battle, Play), a right-hand button column with a hidden "More" half, a Menu sheet with 25 entries, and a "tablet". The same action is reachable from two to five places and no two places agree on its name.
2. **Fire control has three names and four entrances.** "Fire control" (right column button and Menu), "Command tablet" (its title), "Tablet (T)" (battle HUD), "Tablet" (first-person button). Meanwhile the first bottom tab is also called "Command", which means something else.
3. **Every `<button>` has `backdrop-filter: blur(8px)`** (line 43, the global `button` rule). The side pane Place tab renders about 150 buttons, so up to 150 blurred layers sit above a full-screen animating WebGL canvas. This is the single biggest "not lightweight" cost, and it hits phones hardest.
4. **Things are covered or collide.** The red "Calm all" emergency button sits at `left:12px` under the side pane (z 5 versus 8), so on desktop at 1000 px or wider (pane opens by default) the button is invisible. Toasts sit over the top-right buttons on a phone and capture taps. Four floating items use hand-typed `bottom` offsets (150, 172, 200, 228 px) instead of the measured `--bh`, so they land on the tray in Place mode.
5. **Keyboard is the only way to do a dozen things, with no on-screen hint** (R rain crates, Shift+C clear cargo, F, B, G, 5 to 9 groups, Ctrl+Z, `[ ]`, comma and period, PageUp and PageDown, X, Y, N). One key means different things by mode (T is autopilot at the helm and the tablet elsewhere; R is rain crates in the overview and reload in first person; P is the side pane in the overview and prone in first person; F is gunfire mode and sandbags).
6. **Not dyslexia friendly as shipped.** All-caps with letter-spacing on every button (`text-transform:uppercase`), a condensed display face for body labels, monospace sub-labels at 10.5 to 12 px, and jargon (SOG, Sheet, Point, F4, Flechette, Griffon, Hot spot). Auto-dismissing toasts (3 to 9 s, the only timers in the UI) vanish before a slow reader finishes.
7. **Two start screens in a row.** `#intro` (pick a map) then, underneath, `#help` (a 700-word key list card with "Open the cove"). A new player must pass both before touching anything.
8. **Touch targets under 44 px despite a global coarse-pointer rule**, because ID selectors override it: `#trayTog` 36, `#objective button` 36, `#inspector` buttons 36, `.mback` 40, `#hudOn` 40.
9. **Two themes only in practice (one).** There is a single dusk palette. No low-light red or green, no easy-read text option.
10. **The right-hand column is a bag of 17 buttons** whose visibility is toggled from 10 places (`refreshPanel`, `updateHud`, the frame loop, CSS `ui-min`), which is why controls appear in modes where they do nothing (see section 4).

---

## 2. Inventory of every UI surface

Legend: `pos` = where it is; `z` = z-index; "mode" = when it shows. Mode names: **Ov** overview (god), **Helm**, **FP** first person, **B-Ov** battle overview, **B-FP** battle first person, **Dep** deploy.

| # | Surface (id/class) | Position and size (CSS) | z | Shows when | Duplicates / overlaps / contradicts |
|---|---|---|---|---|---|
| 1 | Loading (`.loading`) | full screen, brass 4 px bar | 5 | boot, fades .6 s | none, but sits at z 5, below the menu and intro |
| 2 | Start screen (`#intro`) | full screen grid, 6 map cards (Sail, Port, Urban, Desert, Battle, Large), `introCtl`, version | 40 | first visit per session | followed by #help (item 3). Version text "v8.9 battle depth" is developer wording |
| 3 | Help card (`#help`, `.help .card`) | full screen, card 430 px wide, 15 key rows, install button, Read aloud, Continue, "Open the cove" | in flow (inside `.hud`) | after intro, and from Menu > Help | long (about 700 words). Second copy of the keys in `controlsNodes()` (menu sheet) and a third in `fpHint` |
| 4 | Instruments (`.inst`) | top-left 12,12; about 190 x 140 desktop (rose 76 px), phone max-width `100vw-130` | auto | always except `ui-min` hides it when Ov and nothing selected (`noinst`); hidden in FP | SOG, Wind, Point, Sheet. Moves right by 332 when side pane open. On phone overlaps `#notes` |
| 5 | Right button column (`.actions`) | top-right 12,12; vertical, wraps; `max-height:100dvh-196px`, scrolls | auto | always (hidden in FP and hud-off) | 17 buttons (below). Collapsed by `ui-min` to Menu, More, Log (+ Take the helm, Deselect, Rescue helicopter when valid) |
| 6 | Burger "Edit" (`#burger`) | left edge, mid height, 44 px high | 7 | pane closed | name "Edit" says nothing: it opens a Place list, Events, Live, Map, Battle and Play |
| 7 | Side pane (`#side`) | left, full height, 332 px (90vw max), translucent .92 + blur 10 | 8 | Ov, Helm, B-Ov. Opens by default at 1000 px or wider with a mouse | six tabs; duplicates Place, Events (Sky), Live (Menu > People/Fleets), Battle (tablet, HUD). Covers `#calmBtn` and `#selFloat` |
| 8 | Bottom bar (`.bottom`) | bottom 10 px, full width (left = 332 when pane open); grid: trayTog, cats, tray, tabs, helm pads | auto | Ov, Helm, B-Ov (hidden FP) | height changes per tool (about 110 idle, 135 Command with selection, 175 Place, 175 Sky); `--bh` follows it |
| 9 | Tool tabs (`#tabs`) | bottom centre, 4 buttons Command, Place, Land, Sky | in bar | Ov (hidden at Helm) | "Command" tab is not the "Command tablet" |
| 10 | Fleet toggle (`#trayTog`) "Fleet and select" | above tabs, 36 px | in bar | Ov idle only | shows the tray that the Command tab already shows |
| 11 | Category chips (`#cats`) | above tray, 15 mini chips (Boats, Big ships, People, Factions, Cargo, Trees and rocks, Buildings, Scenery, Port props, Roads and ground, Sites, Elements, Sand and earth, Water and fire, Devices) | in bar | Place tool | same 15 groups as side pane Place tab |
| 12 | Tray (`#tray`) | above tabs, one scrolling row of chips (2-line chips, 10.5 px sub text), horizontal scroll | in bar | per tool: Command (up to about 25 chips), Place items, Land brushes, Sky (3 sub-tabs, up to 60 chips) | Sky tray duplicates side Events tab and Sky sheets |
| 13 | Helm pad (`.helm`) | bottom row, steer left and right, Ease, Trim, Auto (58 px) | in bar | Helm, touch only (`pointer:coarse`) | desktop has no on-screen helm controls or key hint |
| 14 | Selection float (`#selFloat`) "Deselect (n)" | left 16, `--bh+24`, red pill 52 px | 6 | Ov, Command tool, selection | Deselect a 3rd and 4th time (also `#bDesel`, tray chip). Under the side pane on desktop |
| 15 | Calm all (`#calmBtn`) | left 12, bottom 228 | 5 | effects running | **covered by side pane** at wide desktop. Also in Sky, Events tab, Sandbox settings, Destructive sheet |
| 16 | Objective bar (`#objective`) | left 12 (344 with pane), bottom 172, max 360 px | 4 | scenario running | collides with the tray in Place and Sky (bar 175 px) |
| 17 | Legend (`#legend`) | bottom centre, bottom 150, max 420 | 4 | map overlays | collides with tray; non-interactive |
| 18 | Camera pad (`#camPad`) | left 8, centre, 2 x 4 buttons 52 px | 4 | Ov, `prefs.camPad` | duplicates wheel, right-drag, WASD, Recenter, Zoom to selection |
| 19 | Land and Place circles (`#sculpt`, `#placeBtn`, `#landUndo`, `#turnBtn`) | right 16 / 118, bottom `--bh+22..30`; 92 px and 64 px circles | 5 | touch only | on phone these 4 sit left of where the toast appears |
| 20 | Inspector (`#inspector`) | bottom centre, `--bh+24`, 460 px, blur 10 | 12 | tapping a device | per-device sliders; fine, but it is a 3rd bottom-centre panel |
| 21 | Menu sheet (`#menuSheet`) | full screen scroll, card 430 | 30 | Menu button | 25 entries in 4 groups plus sub-sheets (below) |
| 22 | Command tablet (`#tablet`) | centre, 540 x 84vh, gold border, shadow 12/40 | 9 | key T, Fire control button, Tablet buttons | title "Command tablet"; contains Aim, Size, Pattern, Aim (again), Mark target, 8 fire buttons, Support, Squad. **Opens in the middle of the screen over the thing you are aiming at** |
| 23 | Fire-armed pill (`#fireArm`) | bottom centre, 200 | 8 | fire control armed | tells you to tap the map; no cancel button, only Esc |
| 24 | Battle HUD (`#bHud`) | top centre, top 8 (60 in Ov, 72 in FP): ticket bar + 4 buttons (Jump in, Watch next, Overview, Tablet (T)) | 6 | battle on | "Overview" here is not the same as the "Overview" helm button. Offsets 60/72 and the toast offsets 104/126/160 are hand-tuned per mode |
| 25 | Battle stat (`#bStat`) | bottom-left, hp bar plus weapon and ammo | 6 | B-FP | with the FP stick on phone, at `left 18 bottom 20`, **collides with `#fpStick`** (left 18, bottom 24, 132 px) |
| 26 | Hurt flash (`#bHurt`) | full screen, inset shadow 120/40 | 5 | damage | OK, but an always-present full-screen box-shadow layer |
| 27 | Deploy window (`#bSpawn`) | centre, 260+ px | 12 | knocked out | loadout buttons plus every owned point as a button; no explanation of what a loadout is |
| 28 | Notes (`#notes`) | top centre, `min(88vw,360px)`, up to 3, 13.5 px | 60 | any toast, not in battle | auto-fades 3 to 9 s; `pointer-events:auto`, so on a phone it **blocks the top-right buttons** |
| 29 | Side feed (`#sideFeed`) | right 10, top 240 (140 in FP), 250 px, up to 5 | 7 | toasts in battle | a second feed with a different place and style. In Ov battle it runs into the 17-button column (column is up to 524 px tall) |
| 30 | `.toast` class | top centre | 0 | **never created** (the class is dead CSS, plus 6 more rules referencing it) | dead code |
| 31 | FP top-left hint (`.fpHint`) | left 14, top 12, max 420 px, 12.5 px mono | in `#fp` | FP | permanent paragraph of keys; **overlaps `#fpTools`** which is centred and about 700 px wide on desktop |
| 32 | FP tools (`#fpTools`) | top centre, 44 px buttons, 3 to 12 depending on kit | 5 | FP | key numbers shown; overlaps hint and "Leave first person" at 390 px |
| 33 | FP leave (`.fpTop`) | top-right | 5 | FP | duplicate of Esc, `fpHint` and `.actions` (which is hidden in FP) |
| 34 | FP prompt (`.fpPrompt`) | bottom 128 (172 touch), centre, blur 8 | auto | FP | OK |
| 35 | FP buttons (`.fpBtns`) | right 14, bottom 24, column of 7 (Helm, Drop, Fire, Tablet, Stance, Jump, Use) | auto | FP touch | "Tablet" again; 7 x 46 + gaps = 380 px tall |
| 36 | FP stick and look (`#fpStick`, `#fpLook`) | left 18 bottom 24, 132 px; right 62 percent look area | auto | FP touch | look area covers the buttons' column (buttons sit above it, fine) |
| 37 | FP scope (`#fpScope`) | full screen vignette | 4 | scoped weapon | OK |
| 38 | Labels over flags and boats | WebGL sprites from `addLabel` (canvas 512 x 128 textures, one per label) | scene | labels on | small text in 3D; no text-size control; one canvas texture per label |
| 39 | Marquee, `#dropTag` | follows the pointer | 4 and 6 | box select and cargo drop | fine |
| 40 | Show buttons (`#hudOn`) | top-right 12, 40 px | 6 | after Hide buttons | sits where the actions column was; 40 px target |

### 2.1 The right-hand column, button by button (`.actions`, lines 355 to 372)

Take the helm or Overview (`bMode`), First person (`bJoin`), Next boat (`bBoat`), Zoom to selection (`bZoom`), Recenter (`bCenter`), Follow (`bFollow`), Anchor (`bStop`), Remove boat (`bDel`), Topple or Stand up (`bTopple`), Remove person (`bDelP`), Drop (`bDrop`), Install app (`bInstallTop`), Deselect (`bDesel`), Rescue helicopter (`bHeli`), **First person again** (`bFP`), More (`bMore`), Fire control (`bFire`), Menu (`bMenu`), Log (`bLog`), Right the boat (`bRight`). That is 20 ids. Collapsed (default, `ui-min`) only Menu, More, Log, Take the helm, Deselect and Rescue helicopter show.

### 2.2 Menu sheet entries (25)

Command: Fire control, Controls. The world: New world, Start over, Save, Load, Scenarios, Things to try. Help on the way: Call rescue helicopter, Call water bomber, People, Fleets, Cove report. Settings: Sandbox settings, Quality, Hide buttons, Help, Read help aloud, Install on phone. Plus Close. Sub-sheets: map picker (7 maps, seed, size), save slots, load slots, scenarios, things to try (15 rows that do nothing when tapped), people, fleets, report, sandbox (9 toggles), controls, install steps, log.

### 2.3 Distinct top-level controls visible at once in overview mode

Counted as buttons or inputs that are on screen without scrolling and are not rows of a list.

| Situation (1280 x 720, mouse) | Chrome controls | Plus |
|---|---|---|
| Idle, side pane open on Place (default at 1000 px and wider) | 15: pane tabs 5 (6 on battle maps), pane Close, search box, Menu, More, Log, 4 tool tabs, Fleet and select | about 150 item buttons in the pane (about 14 visible) |
| Idle, pane closed | 10: Edit burger, Menu, More, Log, 4 tabs, Fleet and select, plus camera pad 8 if turned on | |
| One boat selected, Command tool | 19 to 22: above plus Take the helm, Deselect (top), Deselect (n) float, tray: Deselect chip, Box, Gunfire, Add, Route, Loop, All people, Idle, All boats, All stop, one chip per boat | tray scrolls horizontally |
| Same, "More" opened | add First person x2, Next boat, Zoom to selection, Follow, Anchor, Remove boat, Fire control: about 30 to 45 | |
| Place tool, pane closed | 4 tabs + 15 category chips + 6 to 30 item chips + Remove + Menu, More, Log + burger: 28 to 55 | |
| Sky tool | 4 tabs + 3 sub-tabs + up to about 25 chips per sub-tab + Menu, More, Log | |

Answer: **15 persistent chrome controls when idle, 30 to 55 when something is selected or Place or Sky is open**, plus the Menu sheet's 25 entries and the pane's 150 rows behind them. The target in section 5 is at most 9 persistent controls in any mode.

---

## 3. Collisions and layout faults by viewport

Method: take the fixed and absolute offsets above, `--bh` = measured bottom bar height + 10, and intersect the rectangles.

### 3.1 Desktop 1280 x 720 (mouse)

| Fault | Detail |
|---|---|
| Calm all hidden | `#calmBtn` left 12, z 5, under `#side` (332 px, z 8). Visible only if the pane is closed |
| `#selFloat` hidden | same cause (left 16, z 6). Harmless today because the top-right Deselect exists, but it is dead on desktop |
| Objective and legend on the tray | bar is about 175 px tall in Place and Sky; objective at 172 and legend at 150 overlap its top chips |
| Fire-armed pill on the tray | `#fireArm` at bottom 200 sits inside the Place or Sky bar (175 + 10) region edge; it works only while Command is the tool, but the pill is tied to nothing |
| FP hint versus tools | hint x 14 to 434, tools centred about 290 to 990: overlap 290 to 434 at 1280 px |
| Tablet opens in the middle | 540 x 84 percent height at centre, over the target area. On 720 px height that is 605 px tall |
| Right column versus side feed (battle) | feed starts at y 252, column can extend to y 536 |
| Pane pushes content | `.inst`, camPad, objective move right; `.actions` does not, so on a 1000 px window the centre gap is 1000 - 332 - 150 = about 520 px, and the tabs (about 330 px) fit but the Place chips scroll |

### 3.2 Desktop 1920 x 1080

The same layout, with more air. Faults left: Calm all hidden (pane opens by default), the tablet is 540 px wide in a 1920 px window (tiny), bottom tray is capped by the pane edge and centred in the remaining 1588 px, the right column is 75 to 200 px wide, far from the tablet and the left pane (eye travel about 1,500 px between a list item in the pane and the Menu button). Nothing uses the extra width.

### 3.3 Phone 390 x 844 (touch)

| Fault | Detail |
|---|---|
| Toast covers buttons | `#notes` is `min(88vw,360px)` = 343 px centred at top 10 (x 23 to 366); the actions column occupies x about 250 to 378 at top 12. Notes have `pointer-events:auto`, 3 s to 9 s each, up to 3 at once: the player cannot tap Menu or Log while messages show |
| Instruments versus notes | `.inst` max width 260 starts at x 12: overlaps the same rectangle |
| More opened | 20 buttons x (44 + 6) = about 1,000 px in a column limited to 648 px, so the column scrolls inside the game view, fighting map gestures |
| Place mode stack | cats row (46) + item row (56) + tabs (56) + gaps + inset = about 190 px, and `--bh` pushes sculpt, place, turn and selFloat above it; `#calmBtn` (bottom 228), `#objective` (172) and `#legend` (150) are hand-placed and overlap the bar |
| Place and Turn circles | `#placeBtn` 92 px at right 16, `#turnBtn` 64 px at right 118: together they cover x 156 to 374 across the middle of the map area, where the player is trying to aim |
| FP top row | `#fpTools` centred, 3 buttons (about 240 px) with `.fpHint` (max 60 vw = 234 px) at the same y and `.fpTop` "Leave first person" (about 170 px, right 12): the three overlap across 390 px |
| FP bottom | `#bStat` (left 18, bottom 20, width 180) is under `#fpStick` (left 18, bottom 24, 132 px) |
| Pane is a drawer | `#side` takes 90 vw with `inert` handling; fine, but tabs wrap to two rows with 6 tabs |
| Landscape (844 x 390) | `max-height:480` rules shrink things, but the column becomes 270 px tall and the tray plus tabs are 140 px of 390: 36 percent of the screen is chrome |

---

## 4. Problems by category

### 4.1 Duplicated functions across surfaces

| Function | Where it lives today |
|---|---|
| Deselect | `#bDesel`, `#selFloat`, tray chip "Deselect n selected", Esc, click on empty ground (5) |
| First person | `#bJoin` "First person", `#bFP` "First person" (same label, same column), Play tab "Drop in (V)", Live tab "Be", V key, battle HUD "Jump in", Battle tab "Drop in as a Port soldier" and "Fight for the Port (first person)" (8) |
| Fire control and support | right column `bFire`, Menu `mFire`, T key, battle HUD `bTab`, FP `fpTab`, side Battle tab "Call support for your side" (6, two different UIs: tablet and pane) |
| Calm all | `#calmBtn`, Sky strip, Events tab, Destructive sheet, Sandbox settings (5) |
| Disasters, arrivals, events | Sky tray (3 sub-tabs), side Events tab, 3 sheets (3 parallel lists of the same 21 items) |
| Place lists | bottom Place tab (15 chips then items), side Place tab (same 15 groups, searchable) |
| Remove | Delete key, `bDel`, `bDelP`, Remove chip in Place, "Remove things" in pane, Live row "X", inspector Remove (6) |
| Help | help card, Menu > Help, Menu > Controls, intro > Controls, `fpHint`, Things to try (6 texts that drift: T is autopilot in one, tablet in another; "Esc deselects" versus "Esc opens menu") |
| Helicopter | `#bHeli` (when people selected) and Menu > Call rescue helicopter |
| Install | `#bInstall` (menu), `#bInstallTop`, `#bInstall2`, `#installNote` (4) |
| Read aloud | `#mRead`, `#bRead` (reads only the help card) |
| Camera | camPad, Recenter, Zoom to selection, Follow, mouse, keys |
| Hide UI | Menu > Hide buttons plus the "Show buttons" floater |
| Log and feed | `#bLog`, `#notes`, `#sideFeed` (two feeds, two styles, one log) |
| Battle control | pane Battle tab (setup, call support, plan), battle HUD (4 buttons), tablet (support), nothing in Menu |

### 4.2 Inconsistent naming, capitalisation and wording

- Case: visible labels are authored mixed case but forced upper by `text-transform:uppercase` on `button`, so "SOG", "Take the helm" and "Tilt" look identical; sub-labels switch to lower case; the pane items switch to sentence case. Three looks in one screen.
- Same thing, different names: Overview (helm button, battle HUD button and the mode name), Command (tab and tablet), Tablet (3 forms), Anchor, All stop and "anchor everyone", "Gunfire" (chip), "Fire:" (toast), "Fire mode" (toast), "Fire control" (button), Remove (6 forms), "Drop" (cargo drop, carried item drop, Drop in as person), "Be" in Live.
- Verb style: "Take the helm" (verb phrase), "Overview" (noun), "Recenter" (verb), "Follow" (verb), "Menu" (noun), "Log (n)" (noun), "More" (nothing). Menu entries are nouns ("People", "Fleets", "Cove report"): the player must guess what each does.
- Jargon and unclear: SOG, Sheet, Point (and "Status" for the same dt), F4, kn, Flechette strike, Hot spot, Griffon, Gunship, "Right the boat", Ease, Trim, Astern, Ahead, Cove report, Hold to apply, Springs and pours, "Squall x10", Loop, Idle, Add, Route, Gunfire, Marker, "Pattern", "Aim" used twice in the tablet (Target and Aim spread). "Edit" for the pane.
- Version line "v8.9 battle depth" in the intro.

### 4.3 Controls that appear where they do nothing, or are unclear

- `Take the helm` is `disabled` and hidden when nothing is selected (good), but `Next boat` (N) and `Recenter` appear in Ov with no boats to move to.
- `First person` appears with no person selected (it then enters as a default person; unclear what happens).
- `Rescue helicopter` requires people selected, but Menu offers the same with no selection.
- Tablet "Squad" only in FP + battle, but Fire control appears in battle HUD and Menu in plain overview where "Support" does nothing (hidden only when `BATTLE.on` is false: acceptable), yet "Mark target" and "Target: Crosshair or Marker or Hot spot" are shown with no hot spot defined.
- `#bFire` "Fire control" sits in the hidden "More" half, so the main weapons feature of battle is two taps away.
- "Things to try" rows look like buttons and do nothing.
- Pane Map tab changes meaning per map (capture points, port objectives, or "Switch to" other maps).
- Helm touch pad: Ease, Trim, Auto relabel to Astern, Ahead, Stop for motor boats: same buttons change meaning with no visual cue.
- `Zoom to selection` and `Recenter` swap, so the same screen position holds two different actions.

### 4.4 Keyboard-only and undiscoverable

Keyboard only, no on-screen hint outside the help text: R (rain crates), Shift+C (clear cargo), F (gunfire), B (box select), G (drop carried), Ctrl+5 to 9 and 5 to 9 (groups), Ctrl+A, Ctrl+Z (land undo), `[` `]` (size), comma and period (rotate), PageUp and PageDown (drop height), X (right boat), T (autopilot), Q (overboard), Y (take over friend), N, Tab, 1 to 4, J, K (battle), WASD QE ZX. Touch-only gestures: long press for box select, two-finger twist. Undiscoverable on desktop: right-click orders (the single most important input, one line in a 15-row card), double-click select all on screen, mouse wheel meaning change in Place with a cargo item.

### 4.5 Touch targets (under 44 px)

`#trayTog` 36, `#objective button` 36, `#inspector .ifoot button`, `.ihead button` 36, `#inspector input[type=range]` height 30, `.mback` 40, `#hudOn` 40, `#bBtns button` 44 only through the coarse rule; `#side .sMini` buttons about 30 on a mouse (fine) and 44 on touch; pane tab buttons 44 on coarse. FP buttons 46 (ok). Desktop (mouse) buttons are about 35 px high: acceptable for a mouse, but the owner sometimes uses touch on a laptop (hybrid): `pointer:coarse` will not fire there. Recommend `min-height:44px` at all times for primary controls, 36 for dense list rows only.

### 4.6 Contrast (computed, see tokens in 5.7)

| Pair | Ratio | Verdict |
|---|---|---|
| paper #f1ece2 on ink #0c1a20 | 15.1 | pass |
| muted #a7b5b2 on ink | 8.4 | pass |
| brass #e3a948 on ink | 8.5 | pass |
| white on signal #d64b2c | 4.28 | **fail for normal text** (the Remove and Deselect pills use it at 15 px bold: borderline, passes only as large text) |
| muted on panel over bright sand (panel is .76 alpha, blur is the only separator) | 4.7 | marginal, worse over sunlit sea and white spray |
| paper on `#fpStick` or panel .45 alpha over bright sky | 3.9 | fail |
| white on `#fpFire` rgba(214,75,44,.7) over sky | 3.6 | fail |
| introFoot #9a937f on near black | 6.5 | pass but at 12 px mono |

The real problem is not the tokens, it is **translucent panels over a full-screen scene whose brightness changes** (day, snow, sand, spray). Contrast must be guaranteed by an opaque panel colour, not by a blur. Sizes: 10.5 px sub-labels (`.chip .dn`, `.tool .dn`), 11 px (`dt`, `.sep`, `.logrow span`, `#iNote`), 11 to 12.5 px mono hints are all below a comfortable size for a dyslexic reader on a phone (the coarse-pointer rule lifts only some to 13).

### 4.7 Motion, blur, shadow, DOM and size

| Measure | Now | Comment |
|---|---|---|
| `backdrop-filter` declarations | **15** (8 rule lines): `button` (global), `.inst`, `#inspector` (10), `.tabs`, `.note`, `#intro .introBg` (4), `#side` (10), `.fpPrompt`. Because of the global `button` rule, a blurred layer exists for **every button on the page** | remove all from always-visible things |
| Large shadows | tablet 0 12 40 (.6), `#bHurt` inset 120/40 (full screen, always in DOM at opacity 0), two 18 px on the circles, one 16 px on selFloat, text-shadows on intro title | 5 in total: low, but the full-screen inset one repaints when opacity changes |
| Transitions and animation | 8 transitions (`.note` 220 ms, `#sideFeed` 250 ms, side drawer 200 ms, loading 600 ms, intro hover 120 ms translateY, bar width 300 ms), **0 keyframes** | light, but only `.toast` (dead) is under `prefers-reduced-motion`; the others ignore it |
| CSS size | lines 20 to 294: **26,154 bytes** in one block (plus 1 line in head) | includes 6 dead `.toast` rules and the duplicated `[hidden]` rule |
| HTML (static body, lines 295 to 455) | 13,655 bytes | about 120 nodes static |
| Fonts | 3 families via Google CSS (Barlow Condensed 3 weights, Barlow 3 weights, IBM Plex Mono 1), render-blocking `<link>` in the body; `sw.js` caches only `./`, `index.html` and icons, so **offline on a phone falls back to Arial Narrow** | fine for a PWA after fix: self-host or cache |
| `<title>` | placed inside `<body>` (line 16) | invalid HTML, harmless in practice |
| DOM nodes built by UI per render | Place tab: about 150 items x (button + 2 spans) = about 450 + group headers; Live tab: up to 160 rows x 7 = about 1,100 nodes; Command tray: 9 helpers + n boats x 3 | `renderSide` clears with `innerHTML=''` and rebuilds the whole tab on every tab change and (Map, Battle) on every ownership change |
| Live tab refresh | `setInterval` 900 ms rebuilds the whole list if any row's text changed (status words change constantly), so about 1,100 nodes torn down and rebuilt about once a second while the tab is open | main source of UI garbage |
| Per-frame DOM writes | the frame loop writes `wind`, `sog`, `pos`, `sheet`, posLbl, sheetLbl, rose canvas redraw every 0.12 s (8 per second, about 6 `textContent` writes plus a canvas draw); `renderTray(false)` every 0.5 s in Command (signature compare: cheap); `battleHud` every 0.5 s and rewrites `#bTick.innerHTML` and `#bStat.innerHTML` each time (rebuilds 6 nodes); no per-rAF writes | modest. Write only when the value changed |
| Layout shift | `--bh` is set from the bottom bar's measured height with a ResizeObserver, so the floating buttons jump when the bar height changes (tool switch: 110 to 175 px); `.actions` changes height as buttons show and hide per selection; the Place chip row changes height when a group has 2-line labels; the side pane open pushes the HUD by 332 px with no transition |
| Always-on listeners | 8 separate `keydown` listeners on `window` (lines 3751, 3954, 4780, 5259, 5532, 5546, 5562, 6142), each re-parsing `e.key` and checking `mode`: key behaviour is spread across the file and conflicts are invisible |

---

## 5. The redesign

### 5.1 Principles

1. **One thing, one place, one name.** Every action has exactly one on-screen home plus (optionally) a key. No mirrored buttons.
2. **Four persistent surfaces at most**, and at most **9 persistent controls** in the busiest mode. Everything else is one tap deeper in a labelled place.
3. **The world is the star.** The scene is never covered by more than about 30 percent of the screen at rest (panel closed: under 12 percent).
4. **Opaque, flat, light.** No `backdrop-filter`. Panels are solid colour with one 1 px border. No shadows except the dock.
5. **Say what it does.** Verb labels, sentence case, 2 to 4 words, no jargon; the key is shown in the label's tooltip and the key strip, not in the label.
6. **Same layout logic on phone and desktop.** Phone is a bottom sheet, desktop is a left drawer. The content of both is the same component.
7. **No clock on the player.** No countdown numbers. Messages stay until dismissed or replaced; the feed is also the log.

### 5.2 Information architecture

Persistent surfaces per mode (max 4). "Panel" = the one drawer.

| Mode | Surface 1: HUD | Surface 2: Dock | Surface 3: Panel | Surface 4: Sheet (on demand) |
|---|---|---|---|---|
| Overview | status chip, Log, Menu | Command, Place, Land, Sky | content follows the dock tool | World sheet (Menu) |
| Helm | readouts (Speed, Wind, Angle, Trim), Log, Menu | helm pad (touch) or key strip (desktop) | closed (Command available on T) | World sheet |
| First person | crosshair, health, ammo, tool slots, prompt | (none) | Command overlay on T | World sheet |
| Battle overview | ticket bar, status chip, Log, Menu | Command, Place, Land, Sky | Command panel opens on a Battle section | World sheet |
| Battle first person | ticket bar, health, ammo, tool slots | (none) | Command overlay on T | World sheet |
| Deploy | none | none | none | Deploy sheet (modal; replaces `#bSpawn`) |
| Tablet | removed: it becomes the Command panel (below) | | | |

The four names and roles:

- **HUD** (always on, read-only plus two icon buttons): what you are looking at and what is happening. Nothing here changes the world.
- **Dock** (bottom centre on desktop, bottom edge on phone): the four tools. One extra: when something is selected, the **selection bar** (below) docks above it.
- **Panel** (one drawer: left on desktop, bottom sheet on phone): the working surface for the current tool. It shows **Command** for the Command tool, **Place** for Place, **Land**, **Sky**. Collapsible; remembers open or closed per tool.
- **World sheet** (modal, replaces the Menu sheet): save, load, new world, settings, help. Opened by the Menu icon or M. Closes with Esc.

**Command** is the one command surface. It is what the tablet becomes: the same Command panel in every mode; in first person and at the helm it opens as an overlay on key T, in the overview it is the Command tool's panel. Sections inside Command (collapsible, only the relevant ones show):

1. **Selected** (when something is selected): the selection bar actions in a vertical list for the panel view.
2. **Fleet** (boats, one row each: name, status word, hull percent if damaged). Replaces the tray chips and the pane Live tab (boats).
3. **People** (rows, grouped by job). Replaces Menu > People and the pane Live tab (people).
4. **Orders** (Route, Loop, Box select, Add, All stop). Replaces the tray helper chips.
5. **Fire** (Lightning, Missile, Bomb, Mortar, Artillery, Air strike...). Replaces the tablet and `bFire`. Contains Target, Size, Pattern, Accuracy as one compact row of segmented controls.
6. **Support** (Rescue helicopter, Water bomber, and in battle: Griffon, Gunship, Air strike). Replaces Menu > Help on the way and the Battle tab support list.
7. **Squad** (first person plus battle only).
8. **Battle** (only on battle maps: Begin, Stop, Enemy, Size, Loadout, Plan). Replaces the pane Battle tab.

**Place** is the one building surface: group chips (7 groups, section 5.4), a search box, and a grid of tiles (name plus a 40 px swatch). Replaces the 15 category chips, the item tray and the pane Place tab and Events tab's duplication of Sky.

**World sheet** replaces Menu, Sandbox settings, Help, Controls, Install, and the pane tabs Map and Play (see mapping table).

### 5.3 Wireframes

Legend: `[ ]` button, `( )` chip, `{ }` panel, `~ ~` the world, `^` anchor edge. Widths are in px.

#### Desktop 1280 x 720, overview, Command tool, panel open (default)

```
+--------------------------------------------------------------------------------+
| (Petrel . anchored)                                          [Log o] [Menu]    |  <- HUD  top bar, 12 px inset, 44 px high
|{ Command ---------- } ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ |
|{ Selected: Petrel   } ~                                                      ~ |
|{ [Helm] [Follow]     } ~                                                      ~ |
|{ [Anchor] [Deselect] } ~                                                      ~ |
|{ Fleet               } ~                                                      ~ |
|{  Petrel  anchored   } ~               the sea                                ~ |
|{  Kestrel under way  } ~                                                      ~ |
|{ Orders  Route Loop  } ~                                                      ~ |
|{ Fire    (collapsed) } ~                                                      ~ |
|{ Support (collapsed) } ~                                                      ~ |
|{ 320 px wide         } ~       [ Petrel: Helm | Follow | Anchor | x ]         ~ |  <- selection bar, 44 px, above dock
|{                     } ~     [ Command ][ Place ][ Land ][ Sky ]              ~ |  <- Dock, 52 px high, centred in the free area
|                          Right-click: send   H: helm   T: command   ?: all keys   |  <- key strip, 12 px, right aligned, dim
+--------------------------------------------------------------------------------+
```

Persistent controls: Log, Menu, 4 dock tools, panel collapse handle = 7 (plus the selection bar's 4 when something is selected = 11 only while selected; the panel's Selected section is the same actions, shown as a bar when the panel is closed and as a list when open, never both).

Collapsed panel (key P or the chevron): the world fills the window; only HUD, dock and key strip remain: **7 controls**.

#### Desktop, Place tool

```
|(Overview . 6 boats, 12 people)                                [Log] [Menu]     |
|{ Place ---------------------- } ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ |
|{ [ Search things...        ] } ~                                              ~ |
|{ (Boats)(People)(Cargo)(Nature)(Port)(Elements)(Devices) }                      |
|{ [swatch] Petrel   [swatch] Kestrel }                                         ~ |
|{ [swatch] Bollard  [swatch] Bay class}                                        ~ |
|{ ... 2 columns, scroll, max 30 per group }                                    ~ |
|{ Placing: Petrel   [Remove tool]    } ~    [ Command ][ Place*][ Land ][ Sky ] |
```

#### Desktop, Sky tool

```
|{ Sky -------------------------------- }                                       |
|{ Weather   Wind (Light)(Moderate)(Fresh)(Gale)  From (Auto)(N)...             }|
|{ Time      (Dawn)(Day)(Golden)(Dusk)(Night)                                    }|
|{ Rain/Fog/Air: segmented controls                                              }|
|{ Events    Destructive > | Arrivals > | Raids > | [Calm all]                   }|
```

"Calm all" lives in the Sky panel and as a **permanent red pill in the HUD while any effect is running** (top centre, 44 px; one place, never hidden by the panel).

#### Phone 390 x 844, overview, Place open (peek)

```
+------------------------------------+
|(Overview 6 boats)       [o Log] [Menu]|  HUD 44 px, safe-area aware, 12 px gutters
|                                    |
|                                    |
|            the world               |
|                                    |
|                                    |
|  [Calm all]  (only while needed)   |  bottom-left, above the sheet
|------------------------------------|
|=== Place  (Boats)(People)(Cargo)>  |  <- bottom sheet, peek 1 row: 96 px (drag handle 24 px)
| [Petrel][Kestrel][Bollard][Bay cl >|  <- one scrolling row of tiles, 56 px high
|[ Command ][ Place ][ Land ][ Sky ] |  <- Dock 56 px, 4 equal columns of 97 px
+------------------------------------+
```

Half-open sheet: 45 percent height (380 px) with a 2-column tile grid, search on top, collapse by tapping the handle or the world. With a selection, a floating selection bar (44 px, 4 actions) sits between the world and the sheet.

#### Phone, helm

```
| (Petrel . 6.2 kn)  [Wind 12 kn NE] [o][Menu]|
|                                              |
|                  the world                  |
|                                              |
| [ <  ][ >  ]   [Ease][Trim][Auto]      [Back to map]|
+----------------------------------------------+
```

Helm pad 64 px buttons; "Back to map" is the one exit (replaces the `bMode` "Overview" label).

#### First person (phone and desktop)

```
Desktop:                                          Phone:
+----------------------------------------+        +--------------------------+
| (Port 120 [o][o][o] Raiders 98)  [Leave]|        |(Port 120 [o][o][o] 98)[x]|
|                                        |        |                          |
|                  +                     |        |            +             |
|              (prompt, low centre)      |        |                          |
| [HP ======]  Rifle 24/30    [1][2][3]..|        | [stick]        [Use][Fire]|
|                                        |        | [HP ===] Rifle 24 [Jump] |
|                       Esc: leave  T: command    |        [1][2][3] slots     |
+----------------------------------------+        +--------------------------+
```

Top: ticket bar centre (battle only), one small Leave icon top-right (also Esc). No permanent hint paragraph. Tool slots bottom centre with number keys on desktop, bottom right row on phone. Stance, Drop, Helm, Command are in the one "More" radial on phone (see 5.8), not 4 separate buttons.

#### Battle overview (desktop)

Same as overview plus: ticket bar at top centre (single row, 40 px: Port 120, three point dots, Raiders 98). The three buttons Jump in, Watch next, Overview move into the Command panel's **Battle** section (names: **Fight**, **Watch next fighter**, **Back to map**). Tablet button removed (Command is already open or on T).

#### Deploy sheet (centre modal, 440 wide, phone full width)

```
{ You were knocked out                       }
{ 1  Choose your kit      (Rifleman)(Medic)(Engineer)(Sniper) }
{ 2  Choose where to start   (Harbour base)(East quay)(Hill post) }
{ [ Start ]   (primary, disabled until both are set) }
```

One step screen, two radio groups, one confirm. Each choice has a one-line plain description. No timer: the player picks when ready.

### 5.4 Mapping: old control to new location

| Old control (id or place) | New location | Notes |
|---|---|---|
| Instruments card `.inst` (SOG, Wind, Point, Sheet, rose) | HUD status chip; at the helm, HUD readouts (Speed, Wind, Angle to wind, Sail trim); rose becomes an optional icon in the chip | `drawRose` canvas kept at helm only (cuts the 8 Hz canvas draw in the overview) |
| `bMode` Take the helm / Overview | Selection bar "Helm" action; at the helm the HUD button "Back to map" | key H unchanged |
| `bJoin` and `bFP` First person | Selection bar "First person" (when a person is selected) and key V; one only | delete `bFP`; "Drop in (V)" in pane Play tab removed |
| `bBoat` Next boat | Command panel > Fleet row tap; key N | button removed |
| `bZoom` Zoom to selection | Selection bar "Zoom" (icon + word) | |
| `bCenter` Recenter | Dock's camera menu: key C hint, HUD chip tap = "Show all" | one place |
| `bFollow` | Selection bar "Follow" | |
| `bStop` Anchor, `bDel` Remove boat | Selection bar "Anchor", "Remove" | |
| `bTopple`, `bDelP`, `bDrop` | Selection bar "Topple" / "Stand up", "Remove", "Drop item" | |
| `bInstallTop`, `bInstall2`, `bInstall` | World sheet > App > "Install on this device" (single) | `#installNote` removed |
| `bDesel`, `selFloat`, tray Deselect chip | Selection bar "x" (close) only; Esc | 4 to 1 |
| `bHeli` | Selection bar "Rescue" (people selected) and Command > Support | |
| `bMore` | removed | the hidden half is gone |
| `bFire` and `mFire` | Command panel > Fire; key T | |
| `bMenu` | HUD "Menu" icon; key M | |
| `bLog` | HUD "Log" icon (dot, not a number); key L | log sheet is the feed history |
| `bRight` Right the boat | HUD helm chip "Right the boat" when capsized | key X |
| Burger `#burger` and side pane `#side` | removed | |
| Pane Place tab | Place panel (search and groups) | |
| Pane Events tab | Sky panel > Events | |
| Pane Live tab | Command > Fleet and People | virtualised |
| Pane Map tab | Command > Battle (capture points), World sheet > Port (objectives, run the day) | |
| Pane Battle tab | Command > Battle | |
| Pane Play tab | World sheet > Play: Drop height and size sliders move to Place panel footer when a cargo item is the tool; catch and knock-outs to Cove report | |
| `#tabs` Command, Place, Land, Sky | Dock | keep names and keys 1 to 4 |
| `#cats` 15 chips | Place group chips (7): Boats (Boats, Big ships), People (People, Factions), Cargo, Nature (Trees and rocks, Scenery), Port (Buildings, Port props, Roads and ground, Sites), Elements (Elements, Sand and earth, Water and fire), Devices | sub-heads inside a group, as `it.grp` does now |
| `#tray` Command chips (Box, Gunfire, Add, Route, Loop, All people, Idle, All boats, All stop, fleet chips) | Command panel > Orders and Fleet | |
| `#tray` Land chips | Land panel (Brush, Size, Finger, Undo, Reset) | |
| `#tray` Sky chips (60) | Sky panel with 4 sections (section 5.2) | |
| `#trayTog` Fleet and select | removed: the Command panel is the toggle | |
| `#camPad` | World sheet > Look > "Camera buttons" (off by default); on touch a two-finger gesture hint in first-run tips | |
| `#sculpt`, `#placeBtn`, `#landUndo`, `#turnBtn` | keep as touch action buttons in one cluster bottom-right above the dock (44 px minimum, 64 px primary) | |
| `#calmBtn` | HUD pill "Calm all" while effects run; also Sky > Events | single visible copy |
| `#objective` | HUD second line (goal text) with "End" in the Scenario row in the World sheet | |
| `#legend` | Panel footer line for the active map overlay | |
| `#inspector` | stays, moved inside the Command panel as the "Selected" section for a device (no floating dialog) | one fewer bottom-centre panel |
| `#tablet` | Command panel (overlay in FP and Helm) | name removed |
| `#fireArm` | Panel footer chip "Fire armed: tap the map. Cancel" | cancel is a button |
| `#bHud` ticket bar | HUD centre (keep `#bTick`) | |
| `#bBtns` Jump in, Watch next, Overview, Tablet | Command > Battle: Fight, Watch next fighter, Back to map | |
| `#bStat` | FP HUD, bottom-left, 56 px clear of the stick | |
| `#bSpawn` | Deploy sheet | |
| `#notes`, `#sideFeed`, `.toast` (dead) | one `#feed` (section 5.8) | |
| `.fpHint` | removed; first-run tips and the key strip | |
| `.fpTop` Leave | small Leave icon top-right; Esc | |
| `.fpBtns` (7) | Fire, Use, Jump always; Drop, Helm, Stance, Command inside a "More" tap-and-hold ring | |
| Menu: New world, Start over, Save, Load, Scenarios | World sheet > Play | |
| Menu: Things to try | World sheet > Ideas (rows get a "Try it" button that actually does it, or become plain text) | |
| Menu: People, Fleets | Command > People, Fleet | |
| Menu: Cove report | World sheet > Report | |
| Menu: Sandbox settings, Quality, Hide buttons | World sheet > Settings (Look, Sound, World rules) | |
| Menu: Help, Controls, Read help aloud | World sheet > Help (Keys, How to play, Read aloud) | |
| Menu: Install on phone | World sheet > App | |
| Intro `#intro` + `#help` | one start screen (5.10) | |

### 5.5 Naming and wording guide

Rules: sentence case everywhere ("Take the helm", not "TAKE THE HELM"); no `text-transform:uppercase` on controls; a button names its action (verb first) or a place (noun) if it only opens a place; 1 to 3 words on the button, one plain sentence of 8 words or fewer in the helper line; numbers are counts only; no abbreviations unless it is on a map or chart. No em dashes, no ellipsis characters in labels.

| Today | Use | Why |
|---|---|---|
| SOG | Speed | plain |
| Point (of sail) / Status | Angle to wind | |
| Sheet | Sail trim | |
| F4 / kn | Force 4 / knots, shown as "12 knots, light breeze" | |
| Throttle | Power | |
| Ease, Trim, Astern, Ahead | Let out, Pull in, Back, Forward | |
| Take the helm | Steer this boat | the helm is jargon |
| Overview, Recenter | Back to map, Show all | |
| First person | Walk as this person | keep "First person" in the Help |
| Fire control, Command tablet, Tablet | Command | one name |
| Gunfire (chip) | Aim guns | |
| Flechette strike | Dart burst | |
| Hot spot | Marked spot | |
| Griffon | Helicopter gunship | |
| Anchor, All stop, anchor everyone | Stop boat, Stop all boats | |
| Remove boat, Remove person, Remove things, X | Remove | context supplies the noun |
| Deselect (n selected) | Clear selection | |
| Drop, Drop in, Be | Drop item, Walk as them | |
| Edit (burger) | removed | |
| Live | Who is where | |
| Cove report | Cove summary | |
| Things to try | Ideas | |
| Hold to apply | Hold on the map | |
| Springs and pours | Water sources | |
| Squall x10 | Rain crates (10) | |
| Right the boat | Turn boat upright | |
| Quality: High | Graphics: High, Low | |
| More | removed | |
| Menu | Menu (keep) | |
| Log (n) | Messages, with a dot, not a count | |

Helper line pattern (under a control or a tile): "Does what, in 8 words." Example: "Stop boat. It drops anchor where it is."
Error and empty states say what to do: "Nothing selected. Tap a boat or a person."
Feed messages: past tense, one sentence, no capital-letter shouting, name first: "Petrel is anchored." not "ANCHORED".

### 5.6 Icons at no asset cost

One inline SVG sprite (`<svg style="display:none"><symbol id="i-..."`) at the top of `<body>`, referenced with `<svg class="ic"><use href="#i-menu"/></svg>`. Drawn on a 24 x 24 grid, 2 px stroke, round caps, `currentColor`, no fills except dots. About 30 icons at roughly 250 bytes each = 7 to 8 KB. Display at **20 px** in buttons beside text (never icon-only except Menu, Log, Close, Leave, Undo), **24 px** in the dock above its word, **28 px** in tiles, **16 px** inside chips. Every icon-only button has `aria-label` and a tooltip `title` with the key.

Set (id, shape): `menu` (3 lines), `log` (speech bubble), `close` (x), `chevron` (open drawer), `command` (cursor arrow), `place` (plus in a square), `land` (mountain), `sky` (cloud), `helm` (wheel: circle and 6 spokes), `person` (circle and shoulders), `follow` (target crosshair), `anchor`, `topple` (tilt), `remove` (bin outline), `zoom` (magnifier), `fire` (target ring), `heli` (rotor line and body), `calm` (wave), `undo`, `play`, `read` (speaker), `save`, `load`, `world` (globe), `help` (question mark in circle), `warn` (triangle), `ok` (tick).

Where an icon does not earn its place, use a CSS shape: status dots (`.dot` 8 px circle, colour from token), ticket points (`i` 13 px circles, already used), the drawer handle (a 36 x 4 px rounded bar), the selection swatch (`.sw`).

Never colour alone: every status dot is paired with a word ("anchored", "under way", "sinking") and the ticket dots with the point name in the tooltip and the Command panel.

### 5.7 Design tokens

Keep brass and dark navy as the default ("Harbour night"); add two low-light themes for dark rooms and for night play. Values below are computed.

**Spacing** (4 px base): `--s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:32px`. Gutters: 12 px (phone), 16 px (desktop). Control gap 8 px. Panel padding 12 px.

**Radii**: `--r1:6px` (chips, inputs), `--r2:10px` (buttons, tiles), `--r3:14px` (panels, sheets), `--rp:999px` (pills).

**Type scale** (fonts already loaded; drop Barlow Condensed from UI; keep it only for the intro title): body and controls Barlow 16 px / 1.45 (min 14 px anywhere); `--t-sm:14px` helper lines; `--t-md:16px` default; `--t-lg:18px` section titles (weight 600); `--t-xl:24px` sheet titles; `--t-hud:15px` HUD numerals in IBM Plex Mono with tabular numbers (mono only for digits). No uppercase, letter-spacing 0 to 0.01em. Minimum line height 1.4.

**Colour: Harbour night (default)**

| Token | Value | Use | Ratio |
|---|---|---|---|
| `--bg` | `#0b1318` | scene fallback, sheet scrim base | |
| `--panel` | `#111d24` | all panels, dock, HUD chips (opaque) | |
| `--raise` | `#182831` | buttons, tiles, rows at rest | |
| `--line` | `#5b7a89` | 1 px borders | 3.75 on panel (meets 3:1 for components) |
| `--text` | `#eef1ee` | primary text | 15.4 on panel |
| `--dim` | `#9db0b0` | helper text, labels | 7.6 on panel |
| `--accent` | `#e8b04e` | selected, primary, focus ring | 8.8 on panel |
| `--on-accent` | `#0b1318` | text on accent fill | 9.6 |
| `--danger` | `#ff7a5c` | warnings text and icons | 6.7 on panel |
| `--danger-fill` | `#b8321a` with white text | Remove, Calm all fill | 6.0 |
| `--ok` | `#6fd08c` | ready, success | 9.0 |
| `--info` | `#7fb4ff` | Port team, info | 8.1 |
| `--enemy` | `#ff9c8a` | Raiders team (never colour alone: the word too) | 7.9 |

**Colour: Red low-light** (`data-theme="red"`): preserves night vision; no blue, minimal green.
`--bg:#0d0303; --panel:#170605; --raise:#240a08; --line:#b84a3c (3.8); --text:#f06a5a (6.5 on panel); --dim:#cc5f52 (5.0); --accent:#ff8a70 as text and #e8574a as fill with #0d0303 text (5.7); --danger:#ff8a70; --danger-fill:#8e1f12 with #ffe0da text; --ok:#ff8a70 with a tick icon (no green); --info:#cc5f52`. Status that used blue or green relies on words and icons. Reduce scene exposure too (tint multiply 0.8, red, applied as a CSS `mix-blend-mode:multiply` overlay div, 0 asset cost, off at helm if it hurts the sea read).

**Colour: Green low-light** (`data-theme="green"`): `--bg:#020a04; --panel:#07140a; --raise:#0e2214; --line:#34914d (4.8); --text:#4fd070 (9.5 on panel); --dim:#3fa85c (6.3); --accent:#4fd070 as text and fill with #020a04 text (10.1); --danger:#ffb347 (amber, 2 hue steps from the green so it still reads) and **always** with a warn icon; --ok:#4fd070; --info:#3fa85c`.

If Night Sky's red and green values differ from these, copy the hex values from Night Sky's CSS; keep the contrast table rows (text 4.5, dim 4.5, line 3 against panel).

**Easy-read text** (`data-text="easy"`, separate from theme, defaults off): font stack `Verdana, Tahoma, "Trebuchet MS", system-ui, sans-serif` (wide, open letterforms, no download), `--t-md:17px`, line-height 1.6, `letter-spacing:.03em`, `word-spacing:.08em`, left aligned, no italics, labels never wrap mid-word, helper lines default shown (not hidden on small screens). Add to the World sheet > Settings > Text: "Standard", "Easy to read". Optional third: Text size Small 100 percent, Large 115, Largest 130 (sets `font-size` on `html`; all sizes are `rem`).

**Motion rules**
- Only `opacity` and `transform`. Durations: 120 ms (press), 160 ms (drawers and sheets), none for content swaps. Easing `cubic-bezier(.2,.8,.2,1)`.
- No continuous animation in UI (the loading bar is a static width step). No bounces, parallax, pulsing.
- `@media (prefers-reduced-motion: reduce){ *{transition:none!important; animation:none!important} }` once, global; plus a Settings toggle "Reduce motion" that sets `data-motion="off"` for people who do not set the OS flag. The camera fly-to respects the same flag (jump-cut).
- Screen shake and the hurt flash: `data-motion="off"` disables shake; the hurt flash becomes a 2 px red border for one frame.

### 5.8 Component specs

**Button** (`.btn`): height 44 (36 in dense lists), padding 0 14, `--r2`, background `--raise`, 1 px `--line`, text `--text` 16 px weight 600, icon 20 left of the word with 8 gap. States: hover border `--accent`; pressed `transform:scale(.97)` 120 ms; selected (`aria-pressed="true"`) accent border plus a 3 px accent bar inside the left edge (so selected is not colour alone); disabled opacity .5 and `aria-disabled`; focus-visible 2 px `--accent` outline offset 2. Variants: `primary` (accent fill, `--on-accent`), `danger` (danger-fill, white), `ghost` (no fill, no border), `icon` (44 x 44, label in `aria-label`).

**Chip** (`.chip`): height 36 (44 on touch), padding 0 12, `--r2`; one line only; optional status dot 8 px; no sub-line (sub-text moves to the helper line or a tooltip). Used for filters, group switchers, segmented controls (a row of chips with one pressed = `role="radiogroup"`).

**Row** (`.row`): 52 px high (dense 44), grid: 28 px icon or dot, 1fr name (16 px) with a second line helper (14 px, `--dim`), trailing slot (status word or chevron). Whole row is the button; secondary action is a trailing icon button at 44 x 44. Used for fleet, people, menu entries, scenarios.

**Tile** (`.tile`, Place items): 2 columns on the panel (136 x 72), swatch 32 px left, name 16 px, no sub-line (helper in tooltip); pressed state as button. 30 tiles per group maximum rendered; search shows up to 40.

**Panel** (`#panel`): desktop left drawer 320 px (360 at 1920), top 0 to bottom 0, solid `--panel`, right border `--line`; head 52 px (title 18 px, collapse chevron 44); sections are `<details>` with 44 px summaries; scroll inside; no backdrop; transform slide 160 ms. Phone bottom sheet: three snaps, closed (0), peek (96 px), half (45 percent); max 70 percent; drag handle 24 px high with a real button (Expand, Collapse) for non-drag users; the dock stays below it; the world remains tappable above it.

**Sheet** (`#sheet`, World sheet and Deploy): centred card 480 max, `--r3`, `--panel`, scrim `rgba(0,0,0,.6)` (no blur), focus trap, `role="dialog" aria-modal="true"`, Esc closes, restores focus to the opener. Header 56 px: title 24 px and a Close icon button 44. Sections are tabs on top for the World sheet: Play, Settings, Help, App (4 tabs, 44 px each); no nested "Back to menu" level (depth of 1).

**Selection bar** (`#selbar`): 44 px pill row above the dock, solid `--panel`, shows only actions that apply to the current selection (a boat: Steer, Follow, Zoom, Stop, Remove; a person: Walk as them, Follow, Rescue, Topple, Drop item, Remove; mixed: Stop, Remove), always ends with a Clear selection icon button. At most 5 visible buttons; the rest in a "..." overflow (a menu with the same buttons).

**Feed** (`#feed`): one list, bottom-right on desktop (above the key strip, 320 px wide, 4 visible), centred above the dock on phone (88 vw, 3 visible), opaque `--panel`, 14 px text, left 3 px bar in a status colour plus an icon (info, ok, warn). **No auto fade timer by default**: the newest message stays until the player taps it, presses Esc, or a newer one pushes the 4th out; setting "Auto-hide messages" (off by default) uses a 6 s fade for players who want it. Repeat messages merge ("Petrel is anchored (3)"). The container has `role="log" aria-live="polite" aria-relevant="additions"`; danger messages are `role="alert"`. In battle the feed is the same list, 4 lines, bottom-left clear of the stat (no second feed, no `top` offsets). `pointer-events:none` on the container, `auto` only on each row's dismiss target, and rows never sit over the HUD buttons (the feed never appears at top).

**HUD chip** (`#hud`): top-left 12 inset, height 44, solid `--panel`, icon 20, text 16 px; tap opens Command. Right cluster: Messages (icon, dot when unread), Menu (icon). Top centre only when needed: battle ticket bar (40 px) or Calm all (44, `danger`).

**Dock** (`#dock`): 4 tool buttons, each 76 x 52 desktop (icon 24 above word 14 px), phone 97 x 56; solid; selected = accent underline 3 px plus pressed state; keys 1 to 4 shown in tooltip and the key strip.

**Key strip** (`#keys`): desktop only (`pointer:fine`), bottom-right, 12 px minimum 13 px, `--dim`, shows at most 5 context keys, with a "?" chip for all keys. Hidden on phone. Updated by mode and tool, not per frame.

### 5.9 Keyboard map

One central handler (`keyRouter(e)`) replaces the 8 listeners; a table `KEYS[mode]` maps key to a named action, and the same table renders the key strip and the Keys sheet (no more drift between docs).

| Key | Overview | Helm | First person | Battle |
|---|---|---|---|---|
| 1 2 3 4 | Command, Place, Land, Sky | (as overview) | 1 to 9 tool slots (unchanged) | same as the mode |
| Right click | Send selection | | Aim | |
| Left click | Select | | Fire or use | |
| Esc | close topmost: sheet, then overlay, then armed tool, then selection; if nothing, open Menu | leave helm | leave | same |
| M | Menu | Menu | Menu | Menu |
| T | Command panel | Command panel (autopilot moves to Space) | Command overlay | Command panel |
| P | show or hide the panel | | prone (unchanged) | |
| H | steer selected boat | back to map | take helm if near | |
| V | walk as selected person | | back to map | |
| N | next boat | next boat | | |
| Delete | remove selection | | | |
| Ctrl+A | select all | | | |
| Ctrl+Z | undo land | | | |
| 5 to 9, Ctrl+5 to 9 | recall, save group | | | |
| W A S D, Q E, Z X | pan, turn, zoom | steer and trim | walk (Q: overboard, unchanged) | |
| Space | | autopilot | jump | |
| R | rain crates (also in Sky > Events) | | reload | |
| F | aim guns | | build sandbags (engineer) | |
| B | box select | | place charge | |
| G | drop carried | gunnery | drop | |
| L | messages | messages | messages | messages |
| ? | all keys sheet | | | |

Changes versus today: T always opens Command (autopilot to Space at the helm); M for Menu; L for messages; ? for the Keys sheet; Esc has one stated rule. The remaining conflicts (R, P, F, B, G) differ by mode only, which the key strip makes visible because it shows only the keys of the current mode.

**On-screen hint strip content** (desktop):

- Overview, Command: `Right-click send | H steer | T command | ? all keys`
- Overview, Place: `Click place | Right-click cancel | [ ] size | , . turn | ? all keys`
- Overview, Land: `Drag to shape | Ctrl+Z undo | ? all keys`
- Overview, Sky: `Pick a setting | R rain crates | ? all keys`
- Helm: `W A S D steer | Space auto | Esc back | T command`
- First person: `W A S D walk | 1 to 9 tools | T command | Esc leave`
- Battle overview: `T command | H steer | V walk as person | ? all keys`

### 5.10 First-run onboarding (3 short hints, no timers)

Replace `#intro` plus `#help` with **one start screen**: title, tagline (one sentence), 6 map cards (name and one line each; rewrite the lines to under 10 words), a text link "How to play" (opens the Keys and How-to sheet), a Continue button when a save exists, and the version in small `--dim` text only on request (Menu > App). No "Open the cove" second step: picking a map starts the game.

Then 3 dismissible coach hints, one at a time, each anchored to its target with a short pointer, each with **Got it** and **Skip all**; they appear after the first world is ready, never on a timer, and never again once dismissed (`localStorage sc-tips = 3`; if storage fails, show once per page load):

1. Anchored to a boat: "Tap a boat. Then tap the water to send it." (desktop: "Click a boat. Right-click the water to send it.")
2. Anchored to the Place tool: "Place adds boats, people and things to the cove."
3. Anchored to Menu: "Menu has save, settings and help. Press ? for keys."

Menu > Help has "Show tips again". A "Read aloud" speaker button sits on every hint and on the Help sheet.

### 5.11 Accessibility

**Focus order** (desktop): HUD chip, Messages, Menu, then the Panel (head, sections in order), then selection bar, then Dock, then (hidden) key strip. The canvas is `tabindex=0` last, with an instruction in `aria-describedby`. On open, a sheet moves focus to its heading, traps Tab and returns focus on close. The panel closing returns focus to the dock tool.

**Labels**: every icon-only button has `aria-label`; the dock uses `role="tablist"`/`tab` with `aria-selected`; chips groups are `role="radiogroup"`; the panel `aria-labelledby` its heading; the feed `role="log"`; the HUD chip `aria-live="off"` but updates the canvas `aria-label` text (selected object name) with debounce 500 ms so screen reader users can ask "what is selected".

**Targets and spacing**: all primary controls 44 x 44, 8 px gaps; list rows 44 to 52; no control closer than 8 px to another; safe-area insets respected on all four sides (landscape notches included: `padding-left:env(safe-area-inset-left)` on the dock and panel).

**Dyslexia and reading**: easy-read text toggle (5.7), no all caps, no justified text, sentence case, short helper lines (under 10 words), one idea per line, no italics, minimum 14 px, icons paired with words, colour never the only cue. **Read aloud**: a speaker icon button on the start screen's How to play, each Help section, each hint, Ideas rows and Cove summary uses `speechSynthesis` through the existing `say()` (already used by `readHelp`): speak the section's text, a second tap stops it; Settings > "Read messages aloud" (off by default) speaks each new feed message. Voice, rate and a stop button are in the sheet; no countdown or time shown anywhere.

**Motion and sensory**: reduced motion honoured (5.7), the fire and screen-flash effects have a reduce setting, sound has its own mute and "Alert sounds only" in Settings; every audio cue has a matching visual in the feed.

**Contrast**: the three themes pass (text 4.5 or better, large text 3, component borders 3 against the panel); panels are opaque so contrast does not depend on the scene.

**Keyboard-only players** can reach every command through the panel (Tab) and every sheet; the 3D scene operations that need a pointer (right-click orders) get a keyboard equivalent in a later phase (select, then press `Enter` on a tile in Fleet to send to the camera centre).

### 5.12 Performance budget

| Item | Budget | Now |
|---|---|---|
| `backdrop-filter` anywhere in always-visible UI | **0**; sheet scrim none; at most 0 in the whole file | 15 declarations |
| Box-shadows | at most 2 rules: dock (0 2 8 rgba(0,0,0,.35)) and sheet (0 8 24); none above 24 px blur; remove the full-screen inset shadow (use a border flash) | 5 incl. 120 px inset |
| Animated properties | `opacity` and `transform` only, at most 160 ms | width, transform, opacity, border, background |
| UI CSS | **at most 18 KB** unminified in one `<style>`, including 3 themes and easy-read (about 2 KB for the extras), no dead rules | 26 KB (6 dead `.toast` rules) |
| Static HTML for UI | at most 9 KB | 13.6 KB |
| Icon sprite | at most 8 KB | none |
| Fonts | 2 families (Barlow 400/600; IBM Plex Mono 500 for numerals), cached by `sw.js` via `stale-while-revalidate` for the two Google Font hosts, or self-hosted woff2 | 3 families, uncached |
| UI DOM nodes | at most 250 at idle, at most 450 with the Place or Command panel open, never above 600 | about 450 idle on Place tab (150 items x 3), 1,100 on Live |
| List rendering | virtualise or cap: Place group at most 30 tiles; search at most 40; Fleet and People at most 60 visible rows with "Show more" | 150 Place, 160 Live |
| Rebuild policy | diff-update text of existing nodes; rebuild a list only when its ids change (not when a status word changes) | `fillLive` rebuilds when any text changes |
| Per-frame work | **0 DOM writes in `requestAnimationFrame`**; HUD at most 4 Hz (250 ms), only when a value changed; rose canvas only at the helm | 8 Hz, about 6 writes + canvas |
| Key listeners | 1 | 8 |
| Layout shift | 0: reserve panel width and dock height as CSS variables set once at resize; floating buttons use those variables, not measured `--bh` per tool; the HUD never changes height | `--bh` changes 110 to 175 |
| Touch targets | 44 minimum for primary controls | 36 on 4 controls |
| First interactive UI | start screen paints with no JS dependency on Three.js (the 1 MB single file parses first; the start screen markup and CSS are at the top of the document) | loads with the module script |

Measure with a Node script over `index.html` (count of `backdrop-filter`, CSS byte range between the style tags, static node count by regex) as part of `npm run check`-style verification, and add one Playwright-free check: `document.querySelectorAll('#ui *').length` logged on load and on opening each panel (fails above budget).

### 5.13 Phased implementation plan

Order keeps the game playable at every step; each step is a single agent session, touches only the listed ids and functions, and ends with the game loading and the previous controls still working unless the step says it replaces them. Test each on desktop 1280 x 720 and phone 390 x 844 with the existing headless recipe (one window only).

**Step 1: Cheap fixes (CSS and a few lines; no layout change).**
Delete every `backdrop-filter` (lines 43, 48, 123, 132, 157, 213, 243, 273); set `.note`, `.inst`, `.tabs`, `#side`, `button` backgrounds to solid `rgba(17,29,36,.96)`. Add `#notes` `pointer-events:none` and `.note{pointer-events:none}`. Move `#calmBtn` and `#selFloat` to the `body.sideopen` rule list (`left:calc(var(--sideW) + 12px)`). Fix targets: remove `min-height:36px` from `#trayTog`, `#objective button`, `#inspector` buttons; `.mback` and `#hudOn` to 44. Replace hand-typed bottoms for `#objective`, `#legend`, `#fireArm`, `#calmBtn` with `calc(var(--bh,140px) + Npx)`. Delete dead `.toast` rules and the duplicate `[hidden]` rule; move `<title>` into `<head>`. Add the single `prefers-reduced-motion` block. Remove the inset shadow from `#bHurt` (use `border:3px solid rgba(214,40,20,.8)`). Gain: lighter and no hidden Calm all.

**Step 2: Tokens, themes and text options.**
Replace `:root` variables with the 5.7 set (keep old names as aliases so nothing breaks: `--ink`, `--panel`, `--line`, `--paper`, `--muted`, `--brass`, `--signal`). Add `[data-theme="red"]`, `[data-theme="green"]`, `[data-text="easy"]`, `html{font-size}` steps. Remove `text-transform:uppercase` from `button` and the chip classes; set body 16 px. Persist `sc-theme`, `sc-text`, `sc-motion` in `localStorage` (try/catch). Add the three settings to the existing Menu sheet (`#menuSheet`, Settings group) as three new `mgrid` buttons (Theme, Text, Reduce motion). Touch: `sandboxSheet()` unchanged. Gain: low-light themes now, before any layout change.

**Step 3: Icon sprite and wording pass.**
Add the sprite after `<body>`; add `.ic` CSS. Rename visible strings per 5.5 in: static HTML (`bMode`, `bJoin`, `bFP`, `bFire`, `bTab`, `fpTab`, `fpExit`, `introCtl`, menu `mgrid` labels, help card), `refreshPanel()` (title, `bMode`, `bTopple`, `bDelP`, `bFollow` strings), `refreshHelm()` (Ease, Trim, Astern, Ahead, Stop), the `inst` dt labels (`posLbl`, `sheetLbl`: set in the frame loop and `refreshHelm`), `renderTray()` chip labels, `renderTablet()` titles, `renderSide()` tab names and button labels, `toast` strings that mention renamed controls. Keep ids unchanged. Gain: consistent language with zero structural risk.

**Step 4: One keyboard router and the key strip.**
Create `keyRouter` and a `KEYS` table; port the 8 listeners (lines 3751, 3954, 4780, 5259, 5532, 5546, 5562, 6142) into it one by one, deleting each as ported; change T (Command always, autopilot to Space), add M, L, ?, add `#keys` strip element and `renderKeys()` called from `setTool`, `toggleMode`, `enterFP`, `exitFP`. Generate `controlsNodes()` and the help-card key rows from the same table. Gain: no more drifting docs, and the strip answers discoverability.

**Step 5: De-duplicate buttons (small, safe deletions).**
Delete `bFP`, `bInstallTop`, `bInstall2`, `installNote`, `selFloat`, `bMore` (and the `ui-min` rules that hide direct children of `.actions`, `$('bMore')` handler line 7515), `bFire`, `mFire`; point `bTab` and `fpTab` labels to "Command". Keep the tablet functions. Update `refreshPanel()` and `updateHud()` accordingly. `.actions` now holds Menu, Log and the contextual buttons. Gain: 8 fewer controls, none of the features lost.

**Step 6: Selection bar.**
Add `#selbar` above `.bottom`; build from `refreshPanel()` (replace the `hidden` toggling of `bStop`, `bDel`, `bTopple`, `bDelP`, `bDrop`, `bHeli`, `bJoin`, `bZoom`, `bCenter`, `bFollow`, `bMode`, `bDesel`); remove those ids from `.actions` once the bar covers them (the bar function reuses their click handlers: `$('bStop')` handlers etc. become named functions). Remove the tray "Deselect" chip. Gain: contextual actions in one place next to the dock.

**Step 7: HUD and feed unification.**
Make `.inst` the status chip (idle and selection) with helm readouts; Messages and Menu icons in `#hud`; one `#feed` replacing `#notes`, `#sideFeed` and `sideFeedAdd`; edit `toast()` (line 5828 onward: remove the `BATTLE.on` branch, no timeout by default, merge repeats, add `role="log"`), `openLog()` unchanged. Delete `body.battle .toast, body.battle #notes` offsets (lines 227 to 229) and `#sideFeed` rules. Add `Calm all` pill to the HUD (`updateGuards()` line 7244 toggles it) and delete `#calmBtn`. Gain: the feed can never cover a button; battle offset hacks vanish.

**Step 8: Panel shell and Command.**
Add `#panel` (desktop left drawer, phone bottom sheet) with sections as `<details>`; implement `renderCommand()` by converting `renderTablet()` (fire, support, squad) and adding Fleet, People (from `collectLive`), Orders (from `renderTray` select branch) and Battle (from `renderSide` battle branch). `toggleTablet()` becomes `openCommand(force)`: in FP and Helm it opens as an overlay, in Ov it activates the panel. Remove `#tablet`, `#trayTog`, the select branch of `renderTray` and `body.tray-idle` logic. Keep `fireArm` text, add the cancel button. Gain: the command surface exists; tablet is gone.

**Step 9: Place panel.**
Implement `renderPlace()` in `#panel` from `fillPlace()` plus `PLACE_CATS` regrouped into 7 `PLACE_GROUPS` (each with `cats:[...]`); tiles instead of chips; capped render; search across all. Remove `#cats`, the build branch of `renderTray`, the `place` tab of `renderSide`. Keep `buildSel`, `placeCat` (now the group id), `syncCat()` adapted to groups. Drop-height and size sliders appear in the panel footer when a cargo item is selected (from the pane's Play tab). Gain: 150 buttons become at most 30 rendered.

**Step 10: Land and Sky panels.**
`renderLand()` (brush, size, finger, undo, reset) from the land branch of `renderTray`; `renderSky()` with 4 sections from the sky branch (the `SUB` map and `skySub` become section ids), Events section from `DISASTERS`, `ARRIVALS`, `EVENTS` arrays (delete the 3 sheets `disastersSheet` and friends and the pane Events tab). `renderTray()` and `#tray` can now be deleted. The dock is the only thing left in `.bottom` (plus helm pad). Gain: bottom tray gone, `--bh` constant.

**Step 11: World sheet.**
Rebuild `#menuSheet` as tabs Play, Settings, Help, App with flat rows; port `mMap`, `mNew`, `mSave`, `mLoad`, `mScen`, `mTry` (Ideas), `mReport`, `sandboxSheet()` (World rules), `mSandbox`, `bQual`, `mHide` (becomes "Hide buttons" kept), `bHelp`, `mCtl` (Keys), `mRead`, install; delete `mFire`, `mHeli`, `mBomber` (now in Command > Support), `mPeople`, `mFleet`. Remove `#burger`, `#side`, `renderSide`, `fillLive`, the 900 ms `setInterval` (line 3952), and `setSide`. The Map tab's port objectives and "Run the day" move to the Play tab, shown only on the Port map. Gain: single world sheet, nested "Back to menu" depth gone, side pane code removed (about 100 lines).

**Step 12: Start screen merge and onboarding.**
Merge `#intro` and `#help` (`go()` at line 6002; `bContinue`, `bHelp`, `bInstall`); implement `#tips` (3 coach marks), `sc-tips` storage; "How to play" sheet from the key table; read-aloud icon buttons (`say()` exists); remove the `introVer` line (move to Menu > App). Gain: one start screen, no second card.

**Step 13: First person and battle HUD pass.**
Rework `#fp` children: remove `.fpHint`, `.fpTop` becomes an icon; `fpSetTool()` builds slot buttons with number keys; `fpBtns` reduced to Fire, Use, Jump plus a More ring (Drop, Helm, Stance, Command); `#bStat` moved clear of `#fpStick`; `battleHud()` stops rebuilding `#bTick` unless a value changed; `deployMenu()` becomes the Deploy sheet (kit radio, spawn radio, Start). `#bBtns` buttons move into Command > Battle. Gain: FP overlaps gone; deploy is one screen.

**Step 14: Phone layout and verification.**
Bottom-sheet snaps and drag handle for `#panel`; dock 4 columns; touch cluster for `#sculpt`, `#placeBtn`, `#turnBtn`, `#landUndo` above the dock using `--dock-h` (constant); landscape rules; verify all three viewports with screenshots (one headless window at a time, killed after); verify perf budget with the counting script; remove aliases left from Step 2 and any dead CSS; update `README.md` and the Keys sheet. Bump `sw.js` `VERSION` (the existing note says to) so the old UI is not served from cache.

Rough size: steps 1 to 5 are small (under 150 changed lines each); steps 6 to 11 are the main work; 12 to 14 are polish. Stop after step 5 for an immediate, low-risk improvement; stop after step 11 for the full redesign without the first-person pass.

---

## 6. Top 10 changes (in order of payoff per effort)

1. **Remove every `backdrop-filter`** and make panels opaque tokens (Step 1). Lighter, and guarantees contrast.
2. **Fix what is hidden or covered:** Calm all under the side pane, toasts over the buttons, hand-typed bottom offsets (Step 1, then Step 7 for good).
3. **One name for the tablet: "Command"**, and one home for it (Command panel); remove Fire control, Tablet, Command tablet duplicates (Steps 5, 8).
4. **Kill duplicate buttons:** Deselect x4, First person x2, Install x3, Calm all x4, Fire control x4 (Steps 5, 6, 7).
5. **Replace the side pane, bottom tray and 15 category chips with one Panel** (Command, Place, Land, Sky) and a 4-button Dock (Steps 8 to 11). Persistent controls drop from 15 idle (30 to 55 with a selection or Place open) to 7 idle and 11 with a selection.
6. **One World sheet** with 4 tabs instead of a 25-entry Menu plus 9 sub-sheets; move People, Fleets and helicopter into Command (Step 11).
7. **Plain sentence-case wording and icons** (SOG to Speed, Sheet to Sail trim, no all-caps); easy-read text option; no timers on messages (Steps 2, 3, 7).
8. **Red and green low-light themes** with verified contrast, plus Reduce motion, on top of the brass and navy default (Step 2).
9. **One keyboard router plus an on-screen key strip and `?` sheet**, with T always meaning Command (Step 4).
10. **One start screen and three dismissible tips**, with read-aloud on every help text (Step 12), and a first-person HUD without the permanent key paragraph (Step 13).
