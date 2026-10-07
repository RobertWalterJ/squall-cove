# Squall Cove: Menu and UI Information Architecture Audit

Source: `index.snapshot.html` (6812 lines). All line numbers refer to that snapshot. Nothing in the game was edited.
Result of the em dash check: grep for U+2014, U+2013, `&mdash;`, `&#8212;` and the JS escape for U+2014 found **zero** hits anywhere in the file. The house rule is currently met. (Middle dots and the multiplication sign are used as separators, which is fine.)

---

## A. Current structure (tree)

### A1. Always-on screen furniture

```
Top-left      Instruments card (brand, boat name / "Overview", rose, SOG, Wind, Point, Sheet)   L281-293
Left edge     "Edit" burger (L247) -> Side pane (L248, renderSide L3397)
Top-right     Actions column (L294-310), scrolls; collapsed by body.ui-min (L78) to:
                 Log, Menu, More, Take the helm / Overview, Deselect, Rescue helicopter
              "More" reveals the rest (toggle text becomes "Less", L5665)
Bottom        [Fleet and select] toggle (L312, only when idle in Command)
              Category chips  #cats  (Place only, L313)
              Tray            #tray  (L314)
              Mode tabs       #tabs  Command | Place | Land | Sky (L3849)
Floating      Calm all (red, appears while a disaster runs, L276, L4394)
              Deselect (n) (L343), Undo (Land), Sculpt, Place, Turn (L278), Camera pad (L275)
              Objective bar with End (L277), Legend, Show buttons (L273)
```

### A2. Top-right buttons

```
Actions column (L294-310)
  Take the helm / Overview     (bMode)
  First person                 (bJoin, shown when in overview)
  Next boat                    (bBoat)
  Zoom to selection            (bZoom)
  Recenter                     (bCenter)
  Follow / Stop following      (bFollow)
  Anchor | Remove boat         (bStop, bDel)
  Topple/Stand up | Remove person(s) | Drop   (bTopple, bDelP, bDrop)
  Install app                  (bInstallTop)
  Deselect                     (bDesel)
  Rescue helicopter            (bHeli, shown only when PEOPLE are selected)
  More / Less                  (bMore)
  Menu                         (bMenu)
  Log (n)                      (bLog)
  Right the boat               (bRight)
```

### A3. Menu sheet (`Menu`, L249-272)

```
The world
  New world       -> sheet: Now: <map>; 7 MAPS (The Cove, Archipelago, Atoll, Fjord, Volcano island,
                     River valley, Barrier coast); Surprise me; Same map, new seed;
                     Map size: Large/Standard; Type a seed        (L5385-5390)
  Start over      -> confirm sheet "Start a new cove? ..." -> "Yes, new cove"   (L4273)
  Save            -> Slot 1, 2, 3                                  (L4259-4271)
  Load            -> Last session, Slot 1, 2, 3
  Scenarios       -> list of SCENARIOS (L4367)  + End  (L4425)
  Things to try   -> TRIES checklist, 15 rows, rows do nothing when tapped (L5391)
Help on the way
  Call rescue helicopter / Recall helicopter   (mHeli)
  Call water bomber / Recall water bomber      (mBomber)
  People          -> who is doing what  (L6681)
  Fleets          -> missions at sea    (L6396)
  Cove report     -> stat rows + "Secrets right now"  (L6217-6230)
Settings
  Sandbox settings -> Camera pad, Gentle mode, Effects at once, Threats, Cove life, Sound, Music,
                      Coast Guard missions, Calm all           (L5298-5310)
  Quality: High/Low
  Hide buttons  (-> Show buttons, L5666)
  Help          -> the opening help card (L346-379), has Read aloud, Install, Continue last session
  Read help aloud
  Install on phone -> install steps sheet (L3966)
Close
```

### A4. Mode tabs and trays (L3849, renderTray L3854)

```
COMMAND (select)
  [Deselect n selected] | Select: Box, Fire, Add, Route, Loop, All people, Idle people, All boats
  Fleet: one chip per boat (name + status)   | All stop
  (Selection panel = top-right buttons in A2; Inspector dialog for devices L338)

PLACE   chips (PLACE_CATS, L3831), 14 of them, in this order:
  Boats | Big ships | People | Cargo | Trees and rocks | Hold to apply | Work sites | Factions |
  Vehicles | Sides | Springs and pours | Lava and volcano | Sand and earth | Devices
  then the item tray for the chosen chip, then "Remove" chip at the end (L3886)
  Cargo chip also shows: Squall x10, Clear, count   (L3887)
  In helm mode the tray is cargo only (L3881)

LAND
  Brush: Raise, Lower, Flatten, Smooth, Sand, Earth
  Size: Small, Medium, Large
  Finger: Hold button / Finger paints / Tap to dab (one cycling chip)
  History: Undo, Reset

SKY (L3905-3937), one 60-chip horizontal strip, in this order:
  Things that happen: Destructive (sheet), Arrivals (sheet), Events (sheet), Calm all
  Wind: Light, Moderate, Fresh, Gale, Hurricane
  From: Auto, N, NE, E, SE, S, SW, W, NW
  Time of day: Dawn, Day, Golden, Dusk, Night
  Rain: Auto, Dry, Showers, Downpour
  Fog: Auto, Clear, Haze, Fog
  Air: Freezing, Cold, Cool, Mild, Warm, Hot, Scorching
  Map: Off, Heat, Wet, Pressure
  Ocean: Sea level (info only), Refill
  Wind view: Off, Ground, Aloft
  Warm layer aloft: Off, Weak, Strong
  Try: Heat wave, Ice age, Super storm, Fog bank, Boil the sea, Clear and calm, Clear devices
```

Sky sheets (same content also reachable in the side pane, tab Events):
```
Destructive (DISASTERS L5315): Hurricane, Tsunami, Tornado, Lightning storm, Earthquake, Meteor, Volcano, Deluge
Arrivals    (ARRIVALS  L5354): Supply drop, Shipwreck, Stone delivery, Meteor shower, Fleet arrives
Events      (EVENTS    L5361): Smuggling run, Raider attack, Landing party, Foreign invasion, SWAT team,
                               Gang fight, Developer rush, Salvage tug
```
The Destructive chip opens `disastersSheet` (L5371) which ALSO contains Calm all, Restore the cove, Arrivals and Events. The Arrivals chip and Events chip open their own sheets with the same rows.

### A5. Side pane (L3397, `Edit` button, key P)

```
Tabs: Place | Events | Live | Play
Place   search box; every BUILD item grouped by PLACE_CATS (same 14 groups) + "Other: Remove things (tap to erase)"
Events  Destructive, Arrivals, Events groups + Calm all
Live    chips All, People, Boats, Vehicles, Things; each row: Go to it, "Be" (people only), "X" (remove)
Play    Drop in (V); Dropping things: Drop height slider, Size slider; Pick the boulder;
        Your catch: n fish; Knock-outs by you: n
```

### A6. BUILD item inventory by `cat` (L1942-2040)

```
Elements (12)  Heat, Cold, Water, Lightning, Electricity, Fire, Lava, Sand, Earth, Rock, Metal, Seeds
Boats (3)      Petrel, Kestrel, Bollard
Coast Guard (11) Bay class, Hero class, Hovercraft + 8 big ships (BIGSHIPS L3830, own chip "Big ships")
Cargo (CARGO.map)
Island (6)     Pine, Oak, Palm, Boulder, Lighthouse, Race mark (a buoy, in "Trees and rocks")
People (10+1)  Person, Crowd, Tourist, Photographer, Dock worker, Fisher, Hiker, Medic, Firefighter,
               Forester, Builder, ... and Lifeguard (L2013, defined far from the others)
Sides (10)     Guard (blue), Guard squad (5), Raider (red), Raider band (5), Blue patrol boat,
               Blue patrol cutter, Response RIB (blue), Foreign landing craft, Red raider runner,
               Red raider gunboat
Vehicles (8)   Ambulance, Fire truck, Forklift, Cargo truck, Crane truck, Tractor, Port patrol, Quad bike
Factions (4)   Smuggler run, Salvage tug, Developer crew, Informant
Sites (4)      Plant site, Build site, Cargo yard, Viewpoint
Water (6)      Volcano (!), Geyser, Water dump, Spring, Big spring, Pour, Drain
Materials (10) Sand pile/fountain, Furnace, Lightning rod, Earth pile/fountain, Rock dump/fountain, Scrap metal/fountain
Lava (2)       Lava vent, Lava pour
Devices (6)    Heater, Cooler, Humidifier, Air dryer, Low pressure, High pressure
Tools (1)      Remove
```

### A7. First person (L328-337, L3315)

```
Top centre   Hands (1) | Rod (2) | Rifle (3)         fpTools, 44 px
Top          Leave first person
Right        Helm (hidden), Drop (hidden), Fire (label becomes "Pick up / throw" / "Cast / reel" / "Fire"), Jump, Use
Keys         WASD, mouse, Space jump, E use, G drop, Q overboard, H helm, 1/2/3 tool, Esc/Tab/O leave, V drop out
```

### A8. Input map (desktop)

```
Left click    select; on empty ground it DESELECTS when something is selected (L3696)
Right click   give orders (boats go, people walk, board, carry)           (L3695, L3597)
Right-drag / middle-drag  turn and tilt camera (L3634)
Left drag     pan; Shift+drag box select; double-click picks every one on screen
Wheel         zoom to pointer; in Place with a CARGO item selected it changes DROP HEIGHT instead (L3661)
Keys          1-4 tools, Tab next boat, H helm, Esc deselect/leave helm, Delete/Backspace remove,
              R squall, C clear all cargo, F fire mode, B box select, G drop carried, P side pane,
              V drop in/out, Ctrl+5..9 save group, 5..9 recall, Ctrl+A select all, Ctrl+Z land undo,
              [ ] drop size, PageUp/PageDown drop height, comma/period rotate placement, WASD QE ZX camera, T auto-trim, X right boat (helm)
```

---

## B. Findings

Severity: high = player-visible confusion, wrong information, or unsafe action; medium = hard to find or inconsistent; low = polish.

### Factions and Sides

1. **HIGH. Two parallel concepts for "who a unit belongs to".** Place has both a `Factions` chip (L3839; items L2005-2008: Smuggler run, Salvage tug, Developer crew, Informant) and a `Sides` chip (L3841; items L1987-1996: blue/red guards and boats). Meanwhile the code uses at least five vocabularies: `side` 'blue'/'red' (L1987), `side` 'hostile' on boats (L3026, L6235), `b.blue` flag (L3436, L6235), the `FACTIONS` relation table with Civilian/Coast Guard/Port/Raiders/Smugglers (L6003), `factionOf` returning also 'Their medics' (L6334), and site owners Port/Developers/Raiders (L6499). Developers, Invaders, SWAT, Salvage and Informants have no row in FACTIONS, so their relations are implicit. Fix: one `faction` field on every unit and BUILD item, one relations table including every faction, `side` derived from faction (see section C).
2. **HIGH. "Sides" names the team colour, not what a thing is.** Labels such as "Guard (blue)", "Raider (red)", "Response RIB (blue)", "Blue patrol boat" (L1987-1993) put the colour in the name and the faction nowhere. A player looking for the Port's patrol boat will not search "Sides". Fix: group by faction name and show colour only as the swatch.
3. **HIGH. Roles Invader and SWAT are unreachable as single placements.** `Invader` and `SWAT` exist as roles (L2200-2201, L5333) but only appear through Events (Foreign invasion, SWAT team). Place only offers Guard and Raider. The "Foreign landing craft" boat (L1994) is under Sides with a red swatch and no Invader crew item. Fix: add "Invader" and "SWAT officer" (and squads) to Place under their factions.
4. **MEDIUM. Duplicate boats in Sides and Coast Guard.** "Blue patrol boat" (boat 'bay') and "Blue patrol cutter" (boat 'hero') are the same hulls as "Bay class" and "Hero class" in Coast Guard (L1958-1959 vs L1991-1992), differing only by an armed side flag. A player sees two entries for one boat. Fix: one "Coast Guard patrol" entry with a toggle "Armed", or rename clearly "Bay class (armed)".
5. **MEDIUM. Smuggler, Salvage and Developer exist three times.** "Smuggler run", "Salvage tug", "Developer crew" are Place items (L2005-2007) AND Events rows "Smuggling run", "Salvage tug", "Developer rush" (L5362, L5369, L5368). Near-identical names with different spellings (Smuggler run vs Smuggling run). Fix: keep them under Place > Smugglers/Salvage/Developers, drop the Events duplicates (or make Events call out "Wave" versions only).
6. **MEDIUM. `Informant` is built on a Photographer.** It is placed by `placePeople(..., 'Photographer')` (L6071) and then relabelled; in Live it will read "Photographer". Fix: set role to "Informant" or label "Informant (looks like a photographer)".
7. **LOW. `factionOf` collapses blue boats to "Civilian".** L6334 returns 'Civilian' for any non-CG, non-hostile boat, so a blue Response RIB is "Civilian" in mission text (L6375, L6382). Fix: return the unit's faction.
8. **LOW. "hostile" leaks into Live.** L3436 labels boats "(hostile)" or "(blue)" but people "(blue)"/"(red)" (L3435). Mixed words for the same idea. Fix: always show the faction name.

### Place tab

9. **HIGH. 14 category chips in a single strip, in no meaningful order.** L3831-3846. Order mixes things (Boats, Big ships, People, Cargo, Trees and rocks, Hold to apply, Work sites, Factions, Vehicles, Sides, Springs..., Lava..., Sand..., Devices). "Hold to apply" (the 12 elements, most used for sandbox play) is sixth; Devices is last and has weather. Fix: reorder by task and cap at about 8 (section C).
10. **HIGH. Category name "Hold to apply" is an instruction, not a category.** L3837. It holds Heat, Cold, Water, Lightning, Electricity, Fire, Lava, Sand, Earth, Rock, Metal, Seeds. Fix: rename "Elements" (the code already calls them that).
11. **MEDIUM. Items filed under the wrong category.** Volcano is `cat: 'Water'` (L2014) and gets pulled into the "Lava and volcano" chip only by a special test (L3843); Lifeguard (L2013) is People but defined after Sites; "Race mark" is a buoy in Island and shows under "Trees and rocks" (L1975); Furnace and Lightning rod are Materials but show under "Devices" (L3845); Scrap metal and Scrap fountain are Materials in "Sand and earth" though they are metal. Fix: re-test by explicit `group` field rather than ad hoc id lists.
12. **MEDIUM. Name collisions across categories.** "Fire" is an Element (L1948), a Command tray chip (L3868, fire mode meaning gunnery), a first-person button (L336), and the chip category 'fire' = "Lava and volcano" (L3843). "Water" is an Element and a category. "Sand" and "Earth" are Elements, Land brushes (L3895), and Materials. "Remove" is a Place chip (L3886), a side-pane row (L3430), "Remove boat/person" (L302), and "X" with aria-label "Remove" (L3444). Fix: name by action: "Gunfire" (command), "Burn" (element), "Cast / reel" stays.
13. **MEDIUM. Vague, jargon or inconsistent item names.** "Bay class" / "Hero class" (note "lifeboat"/"patrol", L1958-1959) mean nothing to a player; "Hovercraft" has note "ACV" (L1960); big ships show note "m heavy icebreaker" with a leading "m" (L1961-1968, the "m" is metres with the number missing, reads as a typo); "Low pressure" note "storm maker" and "High pressure" "clear and calm" (L2033-2034); "Pour" (L2037) vs "Water dump" (L2028) vs "Pour"/"Spring"/"Big spring" ; "Sand pile"/"Sand fountain"/"Rock dump"/"Rock fountain"/"Earth pile" (L2015-2022): "pile", "dump" and "fountain" are used inconsistently. Fix: one verb set: "X (one pour)" and "X (keeps pouring)".
14. **MEDIUM. Capitalisation and punctuation inconsistent.** "Guard (blue)", "Raider (red)", "Response RIB (blue)" vs "Blue patrol boat"; "Louis S. St-Laurent" and "Capt. Molly Kool" fine as proper names, but "Squall x10" in the tray uses the multiplication sign (L3888) while the toast says "10 ×" (L3795). Fix: sentence case for everything except proper names; one x style.
15. **MEDIUM. Items with no useful note or an inaccurate note.** Cargo notes only say "floats" or "sinks" (L1969). Fix: add size or weight in plain words.
16. **LOW. "Trees and rocks" includes a lighthouse and a race mark.** L1974-1975. Fix: rename "Nature and landmarks" or move buoy/lighthouse to "Harbour".
17. **LOW. Duplicate Place entry paths.** Place exists in the bottom tray (chip strip) and in the side pane (flat list with search). The side pane has the only search; the bottom tray has the Squall and Clear tools that the side pane lacks. Fix: put "Squall x10" and "Clear" on the Cargo group in both.

### Sky tray

18. **HIGH. Sky is a 60-chip, one-row horizontal strip with the important things buried.** L3905-3937. Wind, time of day and rain are what a player uses most; they sit after four "things that happen" chips and 24 chips deep to reach "Wind view", "Warm layer aloft", "Try". There is no grouping or collapsing and a mouse user must drag-scroll (L3815-3819). Fix: split Sky into sub-tabs: Weather (wind, from, time, rain, fog), Climate (air, warm layer, map, wind view, ocean), Events (disasters, arrivals, raids), Toys.
19. **HIGH. "Destructive", "Arrivals", "Events" are three chips that open sheets, and the Destructive sheet also contains Arrivals and Events.** L3907-3909 vs L5371-5380. Different content depending on which chip: the Destructive chip opens a sheet with Calm all, Restore the cove, all three groups; the other two chips open their group alone. Fix: one "Events" entry with three clear groups, or three sheets that never duplicate.
20. **HIGH. "Destructive" is jargon; "Arrivals" and "Events" overlap.** "Arrivals" holds Supply drop, Shipwreck, Stone delivery, Meteor shower, Fleet arrives (L5354) where Meteor shower is a disaster by any reading and also near-duplicates Destructive > Meteor (L5321). "Events" holds both people-events (Raider attack) and Salvage tug. Fix: rename groups "Disasters", "Deliveries and wrecks", "Visitors and raids" and move Meteor shower to Disasters.
21. **MEDIUM. "Calm all" appears in five places.** Sky chip (L3910), Sandbox sheet (L5309), Destructive sheet (L5372), Events side tab (L3406), and the floating red button (L276). Not harmful, but the Sandbox copy is a settings sheet containing an action. Fix: remove from Sandbox settings.
22. **MEDIUM. "Sea level" chip is not a control.** L3929 renders as a button but only shows a toast. Fix: show it as a read-out text (`aria-pressed` omitted, not a button) next to Refill.
23. **MEDIUM. "Hurricane" and "Light" collide.** Wind level "Hurricane" (L1025, 38 m/s) and disaster "Hurricane" (L5316) are different things; wind "Light" vs "Lightning". Fix: wind levels "Light, Moderate, Fresh, Gale, Storm force" and keep Hurricane a disaster.
24. **MEDIUM. Inconsistent chip units and "Auto" semantics.** "Auto" appears three times with three subtitles ("wanders" L3914, "from the air" L3919 and L3922). Air chips show "28 C" without a degree sign. Fix: "28 °C" and one consistent "Auto: follows the weather".
25. **MEDIUM. Mixed vocabulary for the same map.** Sky "Map" chips (Off/Heat/Wet/Pressure) are a data overlay, while the Menu has "New world" with "Map size" (L5385-5389) and Sandbox has nothing for it. "Map" in Sky means overlay; everywhere else it means terrain. Fix: rename Sky "Map" to "Weather map".
26. **LOW. "Try" chips have a cryptic sublabel and one destructive entry.** "Clear devices: remove all" (L5014) sits next to scenario presets with no confirmation. Fix: put it first or move it to a menu.

### Command tray and selection panel

27. **HIGH. Left click and right click behaviour is invisible and contradicts the help card on desktop.** Help card (L353) says "Click a boat, then click open water to send it there." Code: with a mouse, a left click on empty ground when anything is selected DESELECTS (L3696); orders are right click (L3695). Right click is not mentioned anywhere in the UI. Fix: change desktop help text to "Left click selects. Right click sends it." and show a one-time toast on first left click on water with a boat selected.
28. **MEDIUM. The Command tray is a toggle farm with a hidden state.** L3865-3877: Box, Fire, Add, Route, Loop, All people, Idle, All boats. Box, Fire, Add, Route and Loop are modes (they show "on: drag"/"off") while the others are one-shot actions; they look identical. "Idle people" is labelled "Idle" with sub "people". "Loop" does nothing unless Route is on. Fix: group "Modes" vs "Pick" with separators and disable Loop when Route is off.
29. **MEDIUM. Three Deselect buttons.** Tray chip (L3865), top-right `bDesel` (L304) and floating `selFloat` "Deselect (n)" (L343). Fix: keep the floating one on phones and the Esc key on desktop; drop the others.
30. **MEDIUM. "Rescue helicopter" is on the selection panel only when people are selected, and again in Menu as "Call rescue helicopter".** L305, L3952, L260. Different names and different conditions for one action. Fix: one name, "Call helicopter", in Menu; selection panel button only as "Rescue these people".
31. **MEDIUM. "Remove boat", "Remove person", "Remove people", "Remove", "X", "Remove things (tap to erase)".** Six labels for deletion (L302, L3953, L3886, L3444, L3430). Fix: "Remove" everywhere, with the noun in a toast.
32. **LOW. "Take the helm" is a verb, the other mode name "Overview" is a noun.** L3949. Fix: "Helm" / "Overview" as a pair.
33. **LOW. "Fleet and select" toggle name.** L5661 reads like a category. Fix: "Boats and selection".
34. **LOW. "Anchor" vs "All stop".** Same effect on one vs all boats (L3877, L3960). Fix: "Anchor" and "Anchor all".

### Menu, More, Log, Help

35. **HIGH. "More" hides the camera and boat controls, with nothing indicating what is inside.** L306, L78, L5665. On a phone the collapsed column shows only Log, Menu, More, Take the helm/Overview, Deselect, Rescue helicopter; Next boat, Zoom to selection, Recenter, Follow, Anchor, Remove boat, Install app are two taps away. Fix: rename "More" to "Boat and camera" or promote Anchor and Follow into the selection panel.
36. **HIGH. Top-right order is Install app / Deselect / Rescue helicopter / More / Menu / Log with the most-used (Menu, Log) in the middle of the column, and the column scrolls (L32, max-height).** Three controls the player needs always can fall below the scroll on a phone held sideways. Fix: pin Menu, Log and More to the top; scroll only the contextual buttons.
37. **HIGH. Help is hidden three levels deep and out of date.** Help only opens from Menu > Settings > Help (L266). Its text (L346-379) misses: right click, P (side pane), V (drop in), R (squall), C (clear cargo), F/B/G, Ctrl+Z (land undo), wheel changes drop height, `[`/`]`, comma/period, and the touch card calls the tab "Build" (L368) though the tab is "Place". Fix: move Help to the top level, and add the missing rows.
38. **MEDIUM. Menu groups mix unlike things.** "Help on the way" (L258) contains rescue helicopter, water bomber, People, Fleets, Cove report; People, Fleets and Report are information, not help. Settings contains Help, Hide buttons and Install. Fix: Info group "Cove" (People, Fleets, Report) and Help group.
39. **MEDIUM. Duplicate Save controls and a hidden one.** Auto save runs every 30 s (L4274) but the only evidence is "Continue last session" on the opening help card (L4277). In Menu, Load lists "Last session" but the player cannot tell. Fix: show "Autosaved just now" in the Menu head.
40. **MEDIUM. Three Install entries.** Help card "Install on this phone" (L375), Menu "Install on phone" (L267), top-right "Install app" (L303). Fix: one, in Menu, with a banner only when the browser offers the prompt.
41. **MEDIUM. Two read-aloud buttons with different names.** "Read aloud" (L376) vs "Read help aloud" (L267); both read only the help card. Text-heavy sheets (Cove report L6217, Log L4017, People L6681, Fleets L6396, Scenarios L4425, Things to try L5391) have no read-aloud. Fix: a "Read aloud" button on openMenu's back bar for any sheet.
42. **MEDIUM. "Things to try" rows look like buttons but do nothing.** L5391 passes `() => {}`. Install sheet rows (L3968-3970) also pass no-op handlers and look like buttons. Fix: render as text rows, not buttons.
43. **MEDIUM. Log is a modal, not a panel, and has no unread cue except a small number.** L4017. "Messages, newest first" vs button "Log". Fix: name them the same.
44. **LOW. "Sandbox settings" is a catch-all.** It holds settings (Camera pad, Gentle mode, Sound) and gameplay balance (Threats, Cove life, Coast Guard missions). "Gentle mode" is a safety switch that disables Destructive but is two levels deep; the Destructive sheet only tells you after the fact (L5373). Fix: split "Display and sound" from "Gameplay", and put Gentle mode on the Sky Events entry itself.
45. **LOW. "Quality: High" / "Quality: Low" toggles by tap.** L265, L3990. Fine, but the label shows the current value as if it were the action. Fix: "Quality: High (tap for Low)".
46. **LOW. Sandbox cycle buttons show state in the label and cycle on tap (Effects at once, Threats, Cove life, Sound, Music).** Three-state cyclers cannot be reversed in one tap. Fix: segmented chips.

### First person, side pane, input

47. **HIGH. Side pane "Play" tab does not tell you how to move.** L3411 note says tools are keys 1, 2, 3 and V drops in but omits WASD, E, G, Q, Space. Those are only in the opening Help card, which is hidden in Menu. Fix: show controls on first drop-in as a card with "Read aloud".
48. **HIGH. `C` clears all cargo and `R` rains ten crates with no confirmation or undo and work in every tool.** L3729. A stray C removes everything the player placed on purpose. Fix: require Shift+C or move to the Cargo group only, with Undo.
49. **MEDIUM. Side pane tab "Events" vs bottom tray Sky.** The side pane has Place/Events/Live/Play; the bottom has Command/Place/Land/Sky. "Events" in the pane equals "Sky > Destructive + Arrivals + Events" so the word means a group and a tab. Fix: pane tabs "Place", "Disasters and visitors", "Live", "Play".
50. **MEDIUM. The pane opens by default only on desktop (L3454), and its toggle is a left-edge "Edit" button (L247) whose label does not say what it edits.** Fix: "Place and Live" or a panel icon with an aria-label that matches.
51. **MEDIUM. Live tab row buttons "Be" and "X".** L3444. "Be" is cryptic and "X" has aria-label "Remove" but the visible label is X. Fix: "Play as" and "Remove".
52. **MEDIUM. First-person Fire button label changes by tool ("Fire", "Pick up / throw", "Cast / reel") but the key bindings do not appear on touch.** L3330. Fix: keep a stable name "Action" with the tool name beneath.
53. **MEDIUM. Wheel in Place changes drop height only for Cargo items (L3661), otherwise zooms.** The only cue is the first toast after "Pick the boulder" (L3416). Fix: show "Wheel: height" on the drop tag (the `#dropTag` already exists).
54. **LOW. Esc, Tab and O all leave first person; V and H also work.** L3311, L3455. Fix: document Esc and V only.

### House style, accessibility, parity

55. **HIGH. Touch targets below 44 px.** `button` base: 15 px text + 20 px padding is about 35 px (L43); `.actions button` on a phone is 12.5 px text + 16 px padding, about 29 px (L174), 12 px landscape (L180); `.tabs button` on a phone about 29 px (L176, L186); `.chip.mini` has only min-width 44 (L137) so about 30 px tall (all Land, Wind, From, Time, Rain, Fog, Air, Map, Wind view chips); `#cats .chip` about 27 px (L122); `#trayTog` 36 (L81); `#objective button` 36 (L68); `.mback` 40 (L94); inspector buttons 36 (L131); `.sTabs button` about 33 (L196); `.sRow button.sMini` about 28 (L205); `#hudOn` 40 (L83). Fix: add `@media (pointer:coarse){ button{min-height:44px} }` and let chips wrap their padding.
56. **HIGH. Fixed-size text in the chip subtitle is tiny.** `.chip .dn` 10.5 px mono (L81 relative, `.chip .dn`), `.mrow span` 12 px, `.mgrid small` 11 px, `dt` 11 px. Dyslexia-friendly guidance wants 14 px minimum for body and good contrast; the muted colour on the dark panel is low contrast. Fix: 13 px minimum and raise `--muted` contrast.
57. **MEDIUM. All-caps button text.** `button{text-transform:uppercase}` with letter-spacing (L43) is harder for dyslexic readers. Fix: sentence case for button text, caps only for brand.
58. **MEDIUM. No timers or countdowns found in UI text.** Search for countdown, seconds and timer in toasts and sheets found none. Note `sheet` rows show "just now / 12 s ago / 3 min ago" in Log (L4018) and Save slots show times; they are timestamps, not countdowns, so they pass. Scenarios say "no clocks" (L4425). OK.
59. **MEDIUM. Missing or weak ARIA.** Good: tab `aria-pressed` (L3828), `#tray role="toolbar"`, `#notes aria-live`. Missing: tray chips are not announced as groups (the `sep()` labels are plain spans, L3825), Menu dialog `role="dialog"` has no `aria-modal` and no focus trap (L249); `openMenu` does not move focus into the sheet or back on close (L4184-4189); Help button `$('go').focus()` is the only managed focus (L3975); `#side` is an `aside` but off-screen `translateX(-104%)` content stays focusable when closed (L164); side `Place` search is not labelled (L3401 placeholder only); Place chips for "Remove" have no aria-label; `#inspector role="dialog"` OK; the emoji-free glyph buttons "+", "-" have aria-labels, good.
60. **MEDIUM. Keyboard reachability of the bottom tray.** Keys 1-4 switch tools but there is no key to move through the category chips or Sky chips; Tab navigation reaches them, but `Tab` is also bound to "next boat" (L3727) with `preventDefault`, which hijacks keyboard navigation for everyone. Fix: change next boat to `]` or `N`, keep Tab for focus.
61. **MEDIUM. Desktop/phone parity gaps.** Desktop only: right click orders, wheel zoom, Shift-box, Ctrl+5..9 groups, Delete key, side pane `P`, Ctrl+Z land undo. Phone has: long-press marquee (L3605), Camera pad option, Sculpt/Place/Turn buttons, Add/Box/Route toggles. Not reachable on phone: group save/recall (5-9), `R` squall, `C` clear cargo (Place tray has Squall and Clear only for Cargo chip, OK), build rotation `,`/`.` (Turn button exists, OK), Delete (use Remove), size `[`/`]` and drop height wheel (side pane Play sliders, OK). Not reachable on desktop except by tapping: "Hold to apply" press-and-hold elements need a held mouse (works, but the hint is only a one-time toast, L3884).
62. **LOW. Rose and instruments use abbreviations.** "SOG", "Point", "Sheet", "Wind 12 kn F4" (L287-290); jargon for non-sailors. Fix: "Speed", "Heading to wind", "Sail trim", "Wind 12 knots".
63. **LOW. Mixed units and number formats.** "kn" vs "knots", "m", "C", "kg", "x1.5" (L3415, `'x' + ...`). Fix: one style.
64. **LOW. "Squall" is both the game name, a tray button ("Squall x10") and a toast.** L3888. Fix: "Rain crates (x10)".

---

## C. Recommended information architecture

### C1. Principles

1. One concept for allegiance: every unit and every placeable has a **faction**. The red/blue colour is derived from faction (and shown only as the swatch and an optional outline). Remove the words "Sides", "blue", "red", "hostile" from all player-facing text.
2. Four mode tabs stay (Command, Place, Land, Sky), because they match the player's mental model and keys 1 to 4.
3. Place has at most 8 groups, ordered by how often a sandbox player uses them, each group showing the faction name where relevant.
4. Sky becomes four sub-tabs instead of one 60-chip strip.
5. Every action lives in one place; where it also needs a shortcut, the shortcut points to that one place.
6. Sentence case, plain words, no jargon in labels; detail goes in the second line.

### C2. Factions model (one concept)

```
FACTION      who they are                          team colour   role names (people)            boats / vehicles
Civilians    visitors and workers (neutral)        grey/white    Tourist, Photographer, Fisher,  Petrel, Kestrel, Bollard
                                                                 Hiker, Lifeguard, Dock worker, 
                                                                 Builder, Forester, Medic*,
                                                                 Firefighter*
Port and     Coast Guard + Port authority          blue          Guard, Guard squad, SWAT        Bay class, Hero class, Hovercraft,
Coast Guard  (Medics and Firefighters belong here  (all blue)    officer, Port patrol officer    8 big ships, Response RIB, armed
             when placed under this group)                                                        variants, Port patrol, Quad bike,
                                                                                                 Ambulance, Fire truck
Raiders      local criminals who hit yards          red           Raider, Raider band             Red raider runner, Red raider gunboat
Foreign      organised landing force                dark olive    Invader, Invader squad          Foreign landing craft, gunboat
invaders
Smugglers    disguised runners                      brown         Smuggler agent (secret)          Smuggler boat (disguised)
Developers   rival builders                          steel blue    Developer crew                  Crane truck (their own), Forklift
Salvage      salvage crews                          orange        Salvage crew                    Salvage tug
Informants   watchers (neutral, report to Port)     tan           Informant                       -
```
*Medics and Firefighters stay selectable from Civilians for quick placement but their `faction` is Port and Coast Guard; their menu entry appears in both groups (one source, one id).

Relations table (replaces `FACTIONS` L6003, keyed by the same names, symmetrical by default, includes every faction):

```
                    Civilians  Port+CG  Raiders  Invaders  Smugglers  Developers  Salvage  Informants
Civilians              1        +0.6    -0.9     -0.9        0         +0.2       +0.2     +0.3
Port and CG           +0.6       1      -1.0     -1.0      -0.9        +0.3       +0.3     +0.5
Raiders               -0.9     -1.0      1       -0.3      -0.3        -0.5       -0.3     -0.9
Foreign invaders      -0.9     -1.0     -0.3      1        -0.3        -0.5       -0.3     -0.9
Smugglers               0      -0.9     -0.3     -0.3       1           0          0       -0.9
Developers            +0.2     +0.3     -0.5     -0.5        0          1         +0.1       0
Salvage               +0.2     +0.3     -0.3     -0.3        0         +0.1        1         0
Informants            +0.3     +0.5     -0.9     -0.9      -0.9         0          0         1
```
(Values for new rows are proposals; existing numbers from L6003 are kept for Civilian, Coast Guard, Port, Raiders and Smugglers; "Port" and "Coast Guard" merge into "Port and Coast Guard".)

Derived team colour (replaces `side`/`b.blue`/`'hostile'`):
```
teamColour(faction) = rel(faction, 'Port and Coast Guard') > 0.5 ? 'blue'
                    : rel(faction, 'Port and Coast Guard') < -0.5 ? 'red' : 'neutral'
isHostile(b)        = rel(b.faction, 'Port and Coast Guard') < -0.5
```
`SK.blue/red`, `SIDE_OPP`, `b.raider`, `b.blue` and `side:'hostile'` collapse into `faction`. `factionOf(b)` (L6334) becomes `return b.faction`. Site owners (L6499) use the same names.

### C3. Place tab: recommended groups and order

Group chips (max 8), left to right. Each BUILD item gets `group` and `faction` fields instead of the ad hoc `cat` plus `test` lambdas.

```
PLACE
1  Boats               Petrel, Kestrel, Bollard (Civilians)
                       Coast Guard: Bay class (lifeboat), Hero class (patrol), Hovercraft
                       Big ships (sub-heading, same group): the 8 icebreakers / patrol ships, each note with real length in metres
2  People              Civilians: Person, Crowd, Tourist, Photographer, Fisher, Hiker, Lifeguard
                       Workers:   Dock worker, Builder, Forester
                       Rescue:    Medic, Firefighter
3  Vehicles            Ambulance, Fire truck, Forklift, Cargo truck, Crane truck, Tractor, Port patrol, Quad bike
4  Factions            sub-groups with the faction name as the heading (this replaces both "Factions" and "Sides"):
                         Port and Coast Guard: Guard, Guard squad (5), SWAT officer, SWAT squad (5),
                                               Patrol boat (armed), Patrol cutter (armed), Response RIB
                         Raiders:              Raider, Raider band (5), Raider runner, Raider gunboat
                         Foreign invaders:     Invader, Invader squad (5), Foreign landing craft
                         Smugglers:            Smuggler run
                         Developers:           Developer crew
                         Salvage:              Salvage tug
                         Informants:           Informant
5  Cargo               all CARGO + "Rain crates (x10)" and "Clear cargo" (confirm)
6  Land and nature     Pine, Oak, Palm, Boulder, Lighthouse, Race mark (rename group "Nature and landmarks" if kept in one group)
7  Materials           Sand pile/fountain, Earth pile/fountain, Rock dump/fountain, Scrap metal/fountain, Furnace, Lightning rod
                       (one name pattern: "X pile (one pour)" and "X fountain (keeps pouring)")
8  Water and fire      Springs: Spring, Big spring, Geyser, Drain; Pours: Pour, Water dump
                       Fire and lava: Lava vent, Lava pour, Volcano
   Elements            12 hold-to-apply: rename and move to the FIRST position in the pill list on a phone
                       (Heat, Cold, Water, Lightning, Electricity, Fire, Lava, Sand, Earth, Rock, Metal, Seeds)
   Work sites          Plant site, Build site, Cargo yard, Viewpoint  (rename group "Work sites" to "Sites")
   Devices             Heater, Cooler, Humidifier, Air dryer, Low pressure, High pressure  (move to Sky > Climate, see C5, keep in Place as a link)
   Remove              last chip, one name everywhere
```
That is 11 groups with Elements, Sites and Devices counted; to reach 8, nest Sites under People/Vehicles ("Workers' places") or fold Sites into Materials and move Devices to Sky. Minimum recommended set: Boats, People, Vehicles, Factions, Cargo, Nature and sites, Materials and elements, Water and fire. Devices live in Sky > Climate and appear in the side pane search too.

Merge or retire:
```
RETIRE  "Sides" group                    -> items move into Factions (renamed, no colour in the name)
RETIRE  "Hold to apply" name             -> "Elements"
RETIRE  Blue patrol boat / cutter        -> the Coast Guard Bay and Hero entries with an "Armed" toggle (default armed)
RETIRE  Events > Salvage tug, Developer rush, Smuggling run  -> Place > Factions (keep Events as "waves" only)
MERGE   Destructive/Arrivals/Events      -> one "Events" entry, see C5
MERGE   People "Lifeguard"               -> in People, defined with the rest
MOVE    Volcano                          -> Water and fire (cat 'Water' removed)
MOVE    Furnace, Lightning rod           -> Materials
```

### C4. Command tab

```
COMMAND
  Pick:   All boats, All people, Idle people     (separator "Pick")
  Modes:  Box select, Add, Route (with Loop only when Route is on), Gunfire  (renamed from Fire)  (separator "Modes")
  Boats:  one chip per boat (separator "Your boats")  + Anchor all
Selection panel (top right, only while something is selected):
  Boats:    Helm, Follow / Stop following, Anchor, Remove
  People:   Play as, Topple / Stand up, Drop, Call helicopter, Remove
  Both:     Zoom to selection, Deselect (floating)
Desktop: left click selects; right click sends; both stated in the Help and in a first-time toast.
```

### C5. Sky tab: sub-tabs

```
SKY
  Weather     Wind (Light, Moderate, Fresh, Gale, Storm force), From (Auto, N..NW), Time of day, Rain, Fog
  Climate     Air (Freezing..Scorching, with "28 °C"), Warm layer aloft, Weather map (Off, Heat, Wet, Pressure),
              Wind view (Off, Ground, Aloft), Sea level (read-out) + Refill, Devices (Heater, Cooler, Humidifier,
              Air dryer, Low pressure, High pressure), Presets: Heat wave, Ice age, Super storm, Fog bank, Boil the sea,
              Clear and calm, Clear devices
  Events      one sheet, 3 headed groups, Calm all and Restore the cove pinned to the top:
                Disasters:                Hurricane, Tsunami, Tornado, Lightning storm, Earthquake, Meteor, Meteor shower, Volcano, Deluge
                Deliveries and wrecks:    Supply drop, Shipwreck, Stone delivery, Fleet arrives
                Visitors and raids:       Smuggling run, Raider attack, Landing party, Foreign invasion, SWAT team, Gang fight,
                                          Developer rush, Salvage tug
              Gentle mode switch is shown at the top of this sheet.
```

### C6. Top right, Menu, side pane

```
TOP RIGHT (always visible, never scrolls): Menu, Log (n), Help, More
TOP RIGHT (context, scrolls): selection panel buttons only
More (renamed "View"): Next boat, Recenter, Zoom to selection, Follow, First person, Install (only if offered)

MENU (sheet)
  The world:   New world, Start over, Save, Load, Scenarios
  The cove:    People, Fleets, Cove report, Things to try (as a plain list, not buttons)
  Call help:   Call helicopter, Call water bomber
  Settings:    Display and sound (Camera pad, Quality, Sound, Music, Hide buttons)
               Gameplay (Gentle mode, Effects at once, Threats, Cove life, Coast Guard missions)
  Help:        How to play (read aloud on every sheet), Install on phone
  Autosave line at the top: "Autosaved just now"

SIDE PANE (tabs): Place (search) | Events | Live | Play
  Place and Events use the same data as the bottom tray (single source: BUILD groups and EVENT groups)
  Play: Controls card with Read aloud, Drop in (V), Drop height and Size sliders, Your catch, Knock-outs
```

### C7. Keyboard map (documented once, in Help)

```
1-4 tools | Esc deselect/leave | Delete remove | H helm | N next boat (Tab left for focus) | P side pane | V drop in/out
F gunfire mode | B box select | G drop | Shift+C clear cargo (confirm) | R rain crates | Ctrl+Z land undo
Ctrl+5..9 save group | 5..9 recall | [ ] drop size | wheel (cargo selected) drop height | , . rotate
Mouse: left click select, right click order, right-drag turn, wheel zoom
```

---

## D. Prioritised implementation checklist (one pass)

Do in this order; each step is small and independent.

1. [ ] Add a `faction` field to every BUILD item (L1987-2008 and the rest) and to every spawned unit; add `FACTION_REL` with all 8 factions; derive `teamColour`/`isHostile` from it (L6003, L6232-6235, L6296, L6333-6334, L3435-3436, L6499). Remove user-visible "blue/red/hostile".
2. [ ] Replace PLACE_CATS (L3831-3846) with the group list in C3, using an explicit `group` field instead of id lists; delete the Sides and Factions chips and fold into a single Factions group with faction sub-headings (also in `fillPlace`, L3423).
3. [ ] Rename items and groups: "Hold to apply" to "Elements", "Guard (blue)" to "Guard", etc., "Blue patrol boat/cutter" to an Armed toggle on Bay and Hero, "Fire" command chip to "Gunfire", wind "Hurricane" to "Storm force" (L1025), notes "m heavy icebreaker" to a real length (L1961-1968).
4. [ ] Add the missing Invader and SWAT items (and squads) to Place under their factions (L1987-1996, L5333).
5. [ ] Remove the duplicate Events rows that exist as Place items (L5362, L5368, L5369); move "Meteor shower" to Disasters; rename Destructive/Arrivals/Events groups (L5315-5370) and make the Sky chips open one sheet (L3907-3910, L5371-5380).
6. [ ] Convert the Sky tray into four sub-tabs (Weather, Climate, Events) in `renderTray` (L3905-3937); show Sea level as a read-out.
7. [ ] Fix the desktop help text for left and right click (L353), add the missing keys (right click, P, V, R, C, F, B, G, Ctrl+Z, `[`/`]`, wheel height), rename "Build" to "Place" on the touch card (L368), and move Help to the top-right.
8. [ ] Guard the dangerous keys: require Shift+C for clear cargo, add Undo; stop Tab from being bound to next boat (L3727, use N) (L3729).
9. [ ] Touch targets: add `@media (pointer:coarse){button,.chip,.tabs button{min-height:44px}}`; raise `.chip .dn`, `.mrow span`, `.mgrid small` to 13 px; drop `text-transform:uppercase` on buttons (L43, L122, L137, L174-176, L196, L205).
10. [ ] Accessibility: focus the Menu on open and return focus on close, add `aria-modal`, set `inert` or `hidden` on the closed side pane, label the Place search, give "Sea level"/"Things to try"/install rows non-button markup (L249, L4184-4189, L3401, L3929, L5391, L3968-3970).
11. [ ] Consolidate duplicates: one Install (Menu), one Read aloud (and add it to every sheet), one Remove label, one Deselect on touch, one "Call helicopter" name (L303, L375, L267, L260, L305).
12. [ ] Reorder the top-right column so Menu, Log, Help, More are pinned and the context buttons scroll (L294-310, L32).
13. [ ] Re-run the grep for U+2014 after all string edits (currently zero), and run the existing colour and build checks.

---

## Top 10 problems (summary)

1. Factions and Sides are two menus and five code vocabularies for one idea (who a unit belongs to); Developers, Invaders, SWAT, Salvage and Informants are missing from the relations table.
2. Invader and SWAT roles cannot be placed from Place; only through Events.
3. Place has 14 chips in no useful order, with an instruction ("Hold to apply") as a category name and several items in the wrong category.
4. Sky is one 60-chip scroll strip with wind, time and rain buried behind disaster sheets, and the Destructive chip opens a sheet that also contains Arrivals and Events.
5. Desktop help says "click open water to send it"; the real behaviour is right click to order, left click deselects, and right click is documented nowhere.
6. Help is three levels deep (Menu, Settings, Help) and is missing most keys; the side Play tab omits movement keys.
7. `C` clears all cargo and `R` drops ten crates with no confirmation, undocumented; `Tab` is hijacked for next boat.
8. Touch targets are well under 44 px on phones (about 27 to 36 px for tabs, top-right buttons, mini chips, category chips, side pane controls); sub-labels are 10.5 to 12 px and buttons are all caps.
9. Duplicates and name collisions: Calm all in five places, Install in three, Deselect in three, Remove in six labels, Fire in four meanings, Smuggler/Salvage/Developer as both Place items and Events.
10. Accessibility gaps: the Menu sheet traps no focus and does not return it, the closed side pane stays focusable, non-controls (Sea level, Things to try, install steps) are buttons, and long text sheets (Cove report, Log, People, Fleets) have no read-aloud.

Em dash check: zero occurrences; no timers or countdowns in UI text.
