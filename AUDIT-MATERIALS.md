# Squall Cove: materials-interaction audit (read-only, 2026-10-06)

Scope: `index.html` (5636 lines). All line numbers refer to the file as read today. Nothing was executed; every claim below is from reading the code, and anything that needs a run to confirm is marked "verify". Test hooks assume the existing headless harness and `window.__sc` (line 5632). `CELL` is not exported there, so tests for item 4.3 need `CELL` added to `__sc`, or the `?size=large` query (line 427).

Legend for the matrix: **I** implemented, **P** partial, **M** missing. Number after the colon is the line of the main implementation.

---

## 0. Headline findings

1. The ground is the only thing with real material physics. Sand, earth, rock rubble and scrap metal are four "kinds" of loose cell (`kindAt` 4375, `MATP` 4374). Everything else (cargo, props, glass, ice blocks, boats) is inert to heat, fire, lava, impact and electricity.
2. There is no structural model at all. Built things are either static `mass: 0` spheres (props, 1693-1696; builders' stone circle is eight `rockb` props, 5479) or free dynamic cargo bodies (spawn 1336) with no health, no fracture, no burning. Nothing a user builds can collapse, crack, burn or melt.
3. Heating the ground does not set trees alight unless lava exists. The only `GT > 560` tree test is inside `if (lavaOn)` (5269). A furnace, heat hold, hot device or meteor-heated ground with no lava does not ignite trees, although the comments (4390) and the device note (4323) say it does. Verify, then fix first; it is a one-line move.
3b. `removeObj(objects[0])` (1359) evicts the oldest cargo when `MAX_OBJ` (90 on phones, 220 otherwise, line 369) is reached. A built stack silently loses its bottom block first.
4. Several per-cell constants do not scale with `CELL` (section 4). On the Large map sand piles at half the angle, and "volume" poured is 4x larger per metre of radius.
5. Material identity is a single flag per cell with last writer wins (`flagMat` 4437). A 0.03 m spill of scrap on a 3 m earth hill makes the whole cell conduct current.

---

## 1. Material x process matrix

Rows are materials or things. Columns are processes.

| | Heat | Cold | Water | Wind | Electricity | Fire | Impact / weight | Slope / slump | Freeze / melt | Erosion | Explosion / lightning |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Sand** | I:4552 glass via MH, GT 4397 | P:4265 quench only | I:3832 soak 0.1, 3825 erode x2.2, repose drops with SM 4533 | I:4541 dunes creep (wind>5) | P:4573 fulgurite (strike only) | P: heat only, no burn | M: grains splash only | I:4527 stepSand | P: melts to glass 4562; no frozen sand | I:3824 | P:4573 fulgurite, 3922 meteor heatGround |
| **Earth** | P: GT cap 4376; SM boils 4410; no baking | P:4265 | I:3832 soak 0.04, 3825 erode, SM lowers repose | M: only sand drifts | M | P: seeds rot GT>60 4491 | M | I:4527 rep 1.05 | M: snow cover only | I:3824 | P:3919 crater height only |
| **Rock** (bedrock kind 0, rubble kind 4) | P: lava at GT>1050 4412; no spall | M | P:3832 soak 0.01/0.05, bedrock erodes only 0.6 m 3825 | M | M | M | M: no break, no crater debris | P: rubble rep 1.5 4374; bedrock never moves 4531 | M: no freeze-thaw | P:3825 | P:3919 crater, 5532 six boulders thrown |
| **Metal** (scrap, kind 5; MET>200) | P: cap 0.45*7800 4376, k 0.6 4374, "melts" GT>1100 4407 to plain ground, no molten metal | M | M-bug: soaks and erodes like earth (3832, 3825 ignore MET) | M | I:4420 shock flood-fill 1400 cells, heats, sparks, topples people | P: heats only | M | I:4527 rep 1.25 flagged cells | M | P: 3825 bug | I:3904 strike calls shock(…,3) |
| **Glass** (matData R) | M: never remelts (heatGround needs sand/MOLT 4554); blocks lava creation 4412 | M | P: never soaks 3832, never erodes 3824 | M | M | M | M: no shatter | P: rigid crust, blocks slumping 4532, 4535 | M | P: immune | M: no shatter on quake/strike |
| **Water** (WD lakes, sea) | I:4199 evaporation; 4410 steam | I:4693 sea ice; 4700 surface ice; 4265 hold cold | I:3806 flow (4-neighbour) | P: waves, surge; no wind drift on lakes | M: no conduction or electrocution | I: rain 3x burn-out 5251; spray 5602 | P: splash 4462 | I:3806 | I:4693, 4700 | I:3824 (carries soil) | P: tsunami 3931; nothing from strikes |
| **Ice** (surface G channel, sea SIf; cargo ice) | I:4409 melt, 4677 meltAround | I:4695 growth (Stefan) | P: blocks flow at G>128 3813 | M | M | P: melts | P: traps boats 4734, icebreakers clear 4735; no fracture from impact; no load bearing | M | I:4700 melt, 4696 | M | P: strike clears nothing |
| **Snow** (R channel) | I:4409, 4706 | I:4703 fall | P: melts to WD 4706 (no absorption, no water removed from sky) | M: no drifting | M | P: melts | M: no tracks | M: no avalanche | I:4409 | M | M |
| **Lava** (LV, LT) | I:4088 cooling; 4152 heats ground; 4185 heats air | P: quench by water 4090, hold cold/water 4265/4269 | I:4090 steam, no obsidian/explosion | M | M | I: trees 5269, boats 4155, meltAround 4153 | P: bombs 4044 | I:4065 stepLava | I:4091 solidifies; 4590 sand to glass | M | P: volcano, 5527 meteor lava |
| **Wood / trees** | P: only via fire or lava | M | P: SM slows spread 5259; flood kills 1529 | I:5256 downwind spread | P:3904 strike <5 m; 4428 power>1.5 | I:5240 igniteTree, 5248 | M | P: slide smothers 1529 | M | M | P: 5532 clearTreesNear 9 m |
| **Cargo** (crate, barrel, granite, drum, ingots, ice, ball, container) | M | M | P: buoyancy only 1357; ignores SM | P: air drag 1139 | M | M | P: kick() 3884; topples people 1805; **no damage** | P: cannon vs heightfield 756; HF rebuilt only on full commit 1513 | M: ice block never melts | M | P: kick 3907, 3923, 3960 |
| **Boats** | P: fire flag from lava/fire 4155, 4277 | P: ice trap 4734 | I:2477 flood; 1196 buoyancy | I | P:3905 strike damage | I:2547 hp loss; 5025/5602 fighting | P: damageBoat from guns/bombs; hull collisions undamaged | M | I:4734 frozen in | M | I:3925, 4053 |
| **People** | P: heat stress 4724; topple on GT>330 4154; flee 5408 | I:4723 frozen | I: swim, cold x4 4723 | M | I:4427 shock topple | P: avoid only, no burns | I:1805 topple on heavy impact | M | I:4727 | M | I:3906, 3924, 4054 |

Reading the matrix: strong columns are Heat, Slope and Water for sand and earth; the weakest cells are every Impact/weight, Cold, Wind and Electricity entry outside metal. Cargo and Glass rows are almost entirely missing, and those are exactly the materials a user would build with.

---

## 2. Physical properties actually modelled

| Material | Density | Heat capacity | Conductivity | Melting point | Strength | Brittleness | Porosity | Flammability |
|---|---|---|---|---|---|---|---|---|
| Bedrock (kind 0) | 2400 (4374) | 0.85 rel., via `capAt` 4376 | k 0.16 diffusion coefficient | GT>1050 makes lava, 4412 | none (never moves) | none | soak 0.01 (3832) | none |
| Sand (1) | 1600 | 0.8 | 0.10 | MH 1.0 to molten, then glass 4562; GT>900 triggers 4411 | repose 0.7 m/cell (~35 deg at CELL 1) | none | 0.1 | none |
| Earth (3) | 1500 | 1.0 | 0.14 | none | repose 1.05 | none | 0.04 | none |
| Rubble (4) | 2700 | 0.85 | 0.16 | as bedrock | repose 1.5 | none | 0.05 (loose) | none |
| Metal (5) | 7800 | 0.45 | 0.60 | GT>1100 flag cleared 4407 | repose 1.25 | none | 0.05 (bug) | none |
| Glass | n/a (flag) | n/a | uses bedrock | none | rigid | none | 0 | none |
| Water | RHO_W 1025 (369) | wetq cooling 4404, moisture x(1+1.6 SM) 4376 | none | boils off soil above total 100 (4410) | none | none | n/a | extinguishes |
| Ice / snow | cargo ice 917 only | none | snow insulates (cond 0.05, 4402) | melt when air+GT>1 (4409) | none | none | none | none |
| Lava | none (thickness only) | LT 0..1 | n/a | solidifies LT<0.12 (4091) | none | none | n/a | ignites |
| Cargo | density per item (1310-1317) | none | none | none | none | none | none | none |
| Trees | none | none | none | none | none | none | none | burn 7-13 s (5240), spread p=0.32 (5259) |

Absent everywhere: specific heat in J terms, true thermal diffusivity, latent heat (melting and freezing cost no energy), melting points as data, tensile/compressive strength, fracture toughness, brittleness, thermal shock, hardness, friction per material pair beyond the cargo table, flammability for anything but trees and boats, moisture content for wood, electrical conductivity beyond the MET flag, permeability for rock.

---

## 3. Strength, brittleness and a structural model

### 3.1 What exists

- No structural model. No object has health, load, temperature or a material record.
- Cargo (spawn 1336-1361): a cannon-es body with `mass = density * volume`, friction and restitution (1310-1333), sleeping at speed 0.12 for 1.2 s. No `collide` listener (only people have one, 1805-1809).
- Props (place 1675-1697): optional static sphere body (`mass: 0`, 1693). No collapse, no burn.
- Builders (5475-5479): every 7 s place a static `rockb` prop on a ring of eight positions, `st.stage` counts to 8, then `done`. A "stone circle" is eight immovable meshes; nothing can knock it over.
- Cargo yard (5406): a position only; workers carry crates to a 6x4 grid (5411) and drop them. Crates stack by plain physics.
- Failure modes in the game today: trees burn and hide, then regrow (5265, 5515); boats lose hp, flood, burn and sink (2477, 2547, 2488); land slumps (4527). That is all.

### 3.2 Proposed minimal model ("MATB")

Design rule: keep one rigid body per block, no joints, no per-frame loops over heightfield cells. Everything is sparse (up to `MAX_OBJ` bodies, 90 on phones) and event-driven, so cost is a few hundred cheap checks at 4 Hz plus one callback per collision.

**A. Material record** (new table beside `CARGO`, 1309). One row per cargo and per new block type:

```
MATB = { oak:   { str: 40,  brit: .3, flam: 1, burnT: 280, melt: 0,   cond: 0,  rubble: 3 },
         ice:   { str: 12,  brit: .9, flam: 0, burnT: 0,   melt: 0,   cond: 0,  rubble: 0 },   // melts above 0 C
         rock:  { str: 120, brit: .8, flam: 0, shock: 250, melt: 1050, cond: 0, rubble: 4 },
         metal: { str: 300, brit: .1, flam: 0, soft: 450,  melt: 1100, cond: 1, rubble: 5 },
         glass: { str: 6,   brit: 1,  flam: 0, shock: 120, melt: 900,  cond: 0, rubble: 1 } }
```
`str` is an impact energy per kg at which the block breaks; `brit` decides fracture (many fragments) versus dent (none, just heating); `shock` is a quench temperature drop that cracks it. Add `o.m`, `o.T`, `o.hp` in `spawn()` right where `objects.push({ body, mesh, fl, c, pr })` is (1358). Add three new CARGO rows (`plank`, `brick`, `beam`) as boxes with the oak/rock/metal records. `prepCargo` (1321) needs a GLB node per item, so use a primitive `BoxGeometry` fallback in place of `nodeByName` for those rows.

**B. Impact fracture.** In `spawn()`, `body.addEventListener('collide', e => ...)` using the same pattern already at 1805-1809: `imp = Math.abs(e.contact.getImpactVelocityAlongNormal())`, reduced mass `mu = m1*m2/(m1+m2)` (use the static ground as infinite mass), energy `E = 0.5*mu*imp*imp`. If `E/mass > m.str` then `fracture(o)`. Fracture removes the body and spawns 2-4 fragment bodies (half-size boxes, mass divided, same `m`, `frag: true`, `life: 6`). When a fragment sleeps or its life expires, `depositGrain(x, z, vol, m.rubble)` (4439) converts it into rubble so it joins the heightfield and slumps with the existing pile logic. This keeps body count bounded: fragments never persist. Ductile metal does not break; it adds heat to `o.T` instead (E to degrees by `E / (mass * cp)`).

**C. Heat, fire, quench.** One loop at 4 Hz, called from `updateMaterials` (4583) next to `stepGround`: for each object, read `GT[cell] + CT[aircell]` into target temperature, relax `o.T` toward it with `k = 0.3/s * (1+wet)`; then:
- Wood: `o.T > m.burnT` and the cell is not wet (`SM < 0.3`, `WD < 0.03`) sets `o.burn = 12`. While burning: emit fire (copy 5252-5253), `heatGT(x, z, 1.6, 330)` (as 5256), ignite trees/objects/boats within 6 m using the 5259 probability, and lose mass at 8%/s with `body.mass = ...; body.updateMassProperties()` so the stack above collapses naturally. At zero mass the block is removed and ash is painted as at 5266. Rain (`wx.rainAmt > 0.3`) triples burn-out exactly like trees (5251).
- Metal: `o.T > m.soft` scales `str` by `1 - (T-450)/650`; above `melt` convert to a metal grain pour (`spawnGrain` kind 5, 4445), which is already a heap that conducts.
- Ice: `o.T > 0` shrinks `mesh.scale` and body half-extents slowly (rebuild shape every 20% loss), adds `WD += lost volume` at its cell (conserves water).
- Rock, glass: thermal shock. Track `o.dT = o.T - prevT` over the last second; if the cell turns wet or snowy (`WD>0.04` or `snowData>40`) while `o.T > m.shock` then `fracture(o)`. That implements "fire cracks rock when quenched".

**D. Weight and crushing, from existing contacts.** In `world.addEventListener('postStep')` iterate `world.contacts` (cannon already built them). For each equation with a mostly vertical normal (`|n.y| > 0.7`) add the upper body's `mass*G` to the lower body's `load`. Then `if (o.load / footprintArea > m.str * K) fracture(o)`. Ice and glass columns fail first, oak next, granite carries a tall stack. Zero extra broadphase cost. Sleeping bodies are skipped by cannon-es, so a settled structure costs nothing.

**E. Electricity.** `shock()` (4420) already floods connected MET cells. Add: after `cells` is computed, loop `objects` with `o.m.cond` within 1.5 cells of any `seen` cell, mark them electrified (`o.T += power*40`, sparks), so an ingot pallet or metal block carries current and an electrified wet crate next to it can ignite.

**F. Build and amass by NPCs.** Replace the static ring at 5479 with a blueprint: `st.plan = [{x, z, y, rot, cargoId}...]` (a ring wall of 8 blocks per course, 3 courses). The builder goal `build` (5475) first asks `freeCrate`-style (5401) for a block of the right type in the yard (5406), uses the existing carry job (2138-2246, `dropCarry`) to bring it to the slot, then calls `dropCarry` at the slot centre and `settle(body)` (1098). Sleep it. The `agentStat.built` counters (5479) stay as they are. A stack the agent builds is then just dynamic blocks, so every failure above applies to it.

**G. Eviction rule.** Change 1359 so the evicted body is the oldest non-structure object, fragments first, then free cargo. Mark blocks with `o.struct = true` when they are placed by a builder or the user.

**Cost estimate:** `fracture` is rare. The 4 Hz loop is O(objects) plus an array lookup per object. The postStep pass is O(contacts). Neither touches the 257x257 grid.

---

## 4. Conservation, consistency and time-step checks (by reading)

### 4.1 Mass and volume

- **stepSand (4527-4551):** slumping moves `m` from `HGT[k]` to `HGT[n]` (4536). Conserved, except `Math.min(34, ...)` on the receiver silently destroys material above 34 m (also 4441). Wind transport (4546) conserves. Verified by inspection.
- **depositGrain (4439-4444):** adds `vol` to the cell, clamped at 34. Grains that leave the map or fall below -12 are deleted with their volume (4471). When the pool is full a grain deposits instantly where it spawned (4446). Mostly conserved; the three loss paths are not logged.
- **Identity is not conserved:** the whole cell takes one kind. `flagMat` (4437) only upgrades (`MET[k] >= v` returns), so a cell never goes from metal back to rock until `loose < 0.004` (4532). Slumping copies the source flag onto the neighbour (4537) regardless of how little moved. A thin skin of metal, or a trace of earth on sand (`depositGrain` 4441 sets kind 3 without clearing kind 1; `kindAt` then prefers sand), reclassifies a whole cell. This is a correctness issue for the planned "surprising interactions", because conduction, melting and repose all read `kindAt`.
- **Lava (4065-4095):** flow is conservative (`LDl` sums to zero). Losses and gains: `LV` is clamped at 8 (4092) so a deeper cell destroys lava; on solidifying, thickness becomes `v*0.75` on land and `v*1.1` at sea (4091). Sea solidification creates 47% more volume than land per unit, and crater lava (meteor 5527, `addLava`) is created without removing ground. Plausible as design; not a ledger.
- **Magma from rock (4412):** removes 0.25 of ground, adds 0.3 lava; later returns 0.225 as rock. Net loss 10%, acceptable but untracked. Creates lava in the sea? It requires `HGT > 0.3` so land only.
- **Quake (3911) and meteor (3919):** craters remove height with only a partial rim (+0.9 over 4 cells); `BED` is not touched, and `slumpArm` is not called, so a quake leaves unstable steps until some other event wakes stepSand.
- **Erosion (3824-3827):** conservative (`a = er / tot` returns exactly `er`). Bounded by `HGT0 - 0.6`, so bedrock can erode 0.6 m. Metal and rubble cells erode as earth (no `MET` check).

### 4.2 Energy (stepGround 4397-4418)

- `GT` is temperature, not energy. Conduction (4402-4403) averages the four neighbours with the *receiving* cell's `cond`. The flux between two different materials is therefore asymmetric (A pulls with its k, B pulls with its k) and ignores heat capacity: energy `sum(cap*T)` is not conserved at interfaces. A rock-to-metal edge conducts with k 0.16 one way and 0.6 the other.
- `heatGT` (4392-4394) is a max-set (`GT = max(GT, val*falloff/cap)`), a fixed-temperature source. Holding Heat for 3 s gives the same ground as holding for 0.3 s once the ceiling is reached (`pw` only sets the ceiling, 4262). A long fire never accumulates energy, and a quench removes energy at a fixed `700*dt` (4265), independent of what is being cooled.
- Latent heat is absent: snow and ice melt by subtracting `4+n*0.5` units (4409), not by consuming heat. Soil moisture boils (4410) without cooling the cell. So "melt ice with lava" does not cool the lava edge or the ground.
- Cooling terms: `-(n*wetq*dt + 2dt)/cap` (4405). A constant 2 K/s sink applies everywhere, even in an insulating pile. Sea cells (`wetq 1.2`) can never be heated.
- Ground to air: only lava (4185), burning trees (4186), devices and sources raise `CHT`. Hot ground in general does not warm the air, and the cold hold does not chill it, so a heated field creates no convection.
- Thresholds are hard-wired in `stepGround` (900, 1050, 1100) instead of in `MATP`; adding a material means editing three call sites.

### 4.3 Water (stepLake 3806, updateSoil 3841, stepClimate 4181)

- Surface flow (3815-3823) is conservative; `LD` sums to zero, except the explicit sinks: `w - 0.00005*dt` (3830), cells with `HGT<0` forced to 0 (3814, 3835, sea absorbs), map border cleared (3837).
- Infiltration: `w -= sk; SM += sk*3` (3833). SM is a 0..1 fraction, not a volume, so the factor 3 and the cap at 1 make soak a sink that discards water once SM saturates. It then evaporates into `CH += d*0.03` (3848), creating vapour from a different quantity. The two do not share units.
- Rain: `rr` (3810) puts depth on land independent of `precipSum`, which is computed (4227) and never used. The sky loses cloud (4227) but not the same amount as it gives to the ground. The global ocean tally (4231) counts only `CH + CC`, so land water, soil moisture, snow and ice are outside the ledger.
- Snow melt to water: 255 snow units = 0.1 m of water (4706, 4409); snowfall (4703) adds snow without removing cloud. Net water source.
- Lake evaporation (4202) takes `e*0.003` per 16 cells from `WD`: a unit conversion that was tuned, not derived.
- Lava on water (4090): `CH += 0.9*dt` is created from nothing (no `WD` or sea draw).
- `ocean.lvl` follows total air water (4231-4232) clamped to +/-8 m, so the model is globally closed for sea-air only.

### 4.4 CELL scaling (CELL 1 vs 2; line 427)

Things that scale correctly: `W2G`/`G2W` (429), seed slope (4497), seed dispersal (4504), air advection and device radius (4188, 4189, 4214), heightfield element size (756), climate grid (`4 * CELL` cell).

Flagged, do not scale:

| Constant | Line | Problem on Large map |
|---|---|---|
| `MATP.rep` (m of drop per cell) | 4374, used 4533-4535 | Angle halves: sand 35 deg becomes 19 deg, earth 46 to 28, rubble 56 to 37. Should be `rep*CELL`. |
| `addSand` height `A = vol/(1.2 R^2)`, `R` in cells | 4381-4384 | Volume is in cell-heights, so 4x the real metres cubed. |
| `dumpGrains` radius `q.R` used as metres (4454) but `vol` deposited as height per cell (4439-4441) | 4450, 4454 | Same radius in metres covers a quarter of the cells, so the pile is ~4x taller. |
| Hold grains `vol 0.02/0.03` | 4280 | 4x cubic metres per second at CELL 2. |
| `heatGT` radius, arguments in cells | 4392; callers 4262 (3.2), 4277 (2), 4585 (6), 4152 (2), 5256 (1.6), 5526 (12), 4314 (`d.r*0.35`, metres) | Mixed units: device passes metres as cells (up to 63 cells = 126 m at CELL 2). Hold brush 3.2 cells is 6.4 m on Large. |
| Fire spread `reach 6.5 + wind` m | 5256 | Metres, so fine, but trees are 1.7x denser (821) and `igniteTreesNear(…, 2.2)` is metres. Inconsistent with cell-based heat. |
| Scorch ash radius 3 cells | 5266 | 6 m on Large. |
| Lava flow, thickness rules, erosion `0.03`, lake flow `0.25` | 4078, 3822, 3825 | Flow per step is per cell, so a front crosses 2x the distance per step on Large (faster in m/s). |
| Heightfield rebuild | 1513 | Fine, but `HGT *= 1.45` (561) applies only to Large cove. |
| `hotData`/`matData` 257 textures | 633 etc. | Fine; shader divides by CELL. |

### 4.5 Time-step dependence

- `stepSand` (4527) takes no `dt`: runs once per 1/12 s accumulator pass (4587); wind transport `0.0016*(ms-4)` (4546) and slump fraction `0.22` (4536) are per call. Correct at 12 Hz; below 12 fps it slows, and on a tab that stalls the accumulator fires once (not a catch-up).
- `stepLava` (4065): `dt` only cools (4088). Flow fraction `0.02 + 0.1*temp^2` (4078) is per call, and the call rate is `min(lavaAcc, 0.25)` per 1/8 s (4140). Slower below 8 fps.
- `stepLake` (3854): runs at fixed 1/15 s, maximum 2 per frame, and `if (lakeAcc > 0.2) lakeAcc = 0` throws time away below ~7.5 fps. Water is slower at low frame rate. `rr` is multiplied by `dt` (3810) but is passed `1/15` always, fine.
- `stepGround` (4589) at 0.25 s: conduction `min(0.9, cond*dt*4)` is stable (0.6*4*0.25 = 0.6). A long frame hitch clamps at 0.9, still stable. `n -= (n*min(1,wetq*dt) + dt*2)/cap` is scaled.
- `stepHeat` (4588): scaled. `stepIce` (4741): scaled.
- Grains (4453): emission uses `dt`; gravity and motion are integrated per frame without sub-stepping. Large dt could tunnel through the ground; grains have a floor check (4466) so impact is robust.
- Physics: fixed 60 Hz with max 5 substeps (3415). Fine.

---

## 5. Ranked fixes (max 15)

Test harness note: all tests run in headless Chrome against `window.__sc`; add `CELL` (and `MET`/`GT` already present) to the export list at 5632.

| # | Fix | Size | Lines | Headless test |
|---|---|---|---|---|
| 1 | Move the `GT > 560` tree ignition out of `if (lavaOn)`; also ignite on `GT > 560` for any burnable object | S | 5269 | `heatGT(x,z,2,1200)` on a tree with no lava; step `stepGround` + `updateTreeFire` for 5 s; expect `burning.length > 0`. Currently fails (verify). |
| 2 | Protect built things from eviction: evict fragments first, then non-structure cargo; flag structure blocks | S | 1359, 1358 | Spawn `MAX_OBJ + 5` crates, mark the first 3 `struct`; assert those three remain. |
| 3 | Scale repose by `CELL`; make all `heatGT` radii metres (`r/CELL`) | S | 4374, 4533-4535, 4392, 4314, 4262, 4277, 4585, 5256, 5526 | Run `?size=large` and standard; pour sand with `dumpGrains`; step `stepSand` until quiet; max slope `atan(dh/CELL)` must agree within 3 deg. Also `heatGT` footprint area in m^2 equal. |
| 4 | Convert piles to cubic metres: `A = vol/(CELL^2 ...)` and grain `vol` per cell | S | 4382-4384, 4450, 4280, 4584 | Dump 150 units; assert `sum(dHGT)*CELL^2` within 5% of 150 on both sizes (excluding the 34 m clamp). |
| 5 | Make soaking and erosion honour `MET` (metal and rubble do not soak; erosion rate by material) | S | 3825, 3832 | Set a MET=255 cell, `WD=1`; step `stepLake`; assert `SM` stays 0 and `HGT` unchanged. |
| 6 | Material identity by thickness: flag only if the deposit exceeds a share of `loose`; allow downgrade; do not clear sand on earth deposit | M | 4437-4442, 4532-4537 | Spill 0.03 metal on a 3 m earth hill; `kindAt` must not be 5. Pour 1 m metal then bury under 2 m sand; expect `kindAt` 1. |
| 7 | Material table carries thresholds (melt, soften) and `stepGround` reads them; metal melts to metal grains, not to plain ground | S | 4374, 4407, 4411, 4412 | Heat a metal pile to 1200; assert `MET` cleared and `ng` (grains) of kind 5 emitted; rock to 1100 still gives lava. |
| 8 | Heat as energy: `heatGT` adds `E/cap` clamped to a ceiling, so duration matters; quench removes energy proportional to cap | S | 4392, 4265, 4269 | Hold `heatGT` 10 times at `val` on one cell; temperature after 10 calls > after 1 call; and `stepGround` with cond and no source: `sum(cap*T)` non-increasing. |
| 9 | Flux-form conduction with symmetric pair conductance and cap weighting | M | 4402-4403 | Two-material strip (sand | metal), no source, no sink, run 200 steps; assert `sum(cap*T)` constant within 1% and temperatures converge. |
| 10 | Object material layer (`MATB`, `o.T`, `o.hp`) with the 4 Hz thermal loop: wood burns, ice melts, metal softens, shock cracks | M | 1309-1361, 4583-4589 | Crate on `GT 600` ground ignites inside 10 s and loses mass; ice block on `GT 100` shrinks and `WD` rises by its volume; granite in `GT 400` then `WD` added fractures. |
| 11 | Impact fracture with fragments converted to rubble grains | M | 1336-1361, 4439 | Drop ice, glass, granite, oak, ingots from 15 m; ice and glass fracture (>= 2 fragments), ingots do not; `objects.length` returns to the pre-test count after 10 s. |
| 12 | Contact-load crushing from `world.contacts` | M | new `postStep` near 1395 | Stack N ice blocks and N granite blocks; ice column collapses at a lower N, granite does not; sleeping stack costs zero (compare `world.step` time). |
| 13 | Water ledger: one conserved currency across WD, SM, snow, ice, cloud; unify soil units; use `precipSum` as the rain source | M | 3810, 3833, 3848, 4227, 4231, 4706 | Closed-box test (stop edge inflow): total water drift < 2% over 5 simulated minutes of rain, melt and heat; add `__sc.waterTotal()`. |
| 14 | Time-step independence: subcycle `stepSand`, `stepLava` with `dt` factors; remove the lake time dump | S | 4527, 4078, 3854 | Run 20 s of a sand slump and a lava pour at dt 1/60 and dt 1/10; compare centroid and spread within 5%. |
| 15 | Metal conduction extends to objects, and builders place blocks from a blueprint (NPC construction) | M | 4420-4429, 5475-5479 | Strike a rod beside an ingot pallet; assert it heats. Place a build site with 8 crates in the yard; assert 8 dynamic bodies at blueprint slots after N seconds, none `mass: 0`. |

Order rationale: items 1-5 are small, fix wrong behaviour that will confuse any later layer, and unlock Large-map fairness. 6-9 make the ground trustworthy. 10-12 are the structural layer, which only becomes meaningful once 2 is done. 13-15 are consistency and NPC building.

---

## 6. Ten "surprising but plausible" chains with small additions

1. **Lightning, scrap pile, timber stack.** Strike a metal heap beside oak blocks. `shock()` (4420) already heats the pile; with fix 15 and the thermal loop (fix 10) the neighbouring wood passes `burnT`, ignites, and the fire spreads by 5259 to a tree line. Then rain cuts burn time (5251) and the charred stack collapses as mass is lost.
2. **Fire then flood cracks granite.** A burning wooden structure heats rock blocks through `heatGT` (5256); a deluge (4162) wets the cell; the quench rule (fix 10) fractures the rock into rubble that slumps down the bank. Needs only the shock threshold and the wet-cell test.
3. **Lava meets ice cargo.** Lava creeping onto an ice-block wall: ice shrinks, the meltwater `WD` pours out (4409) and flows downhill (3806), quenching the lava edge (4090), which crusts; steam raises local humidity (4090). Only the ice melt rule (fix 10) is new.
4. **Glass bridge.** A furnace (4585) melts a sand strip to glass (4565); glass is a rigid crust (4535) that stops slumping. Add a glass fracture rule: a boulder dropped on it shatters the crust into sand grains. A drop from low height just chips it.
5. **Metal quench hardening.** A metal pile above 450 C softens (fix 7), settles lower under its own weight (rep drops), and quenching it cools in a controlled slope; if re-heated unevenly the top slumps off. Uses `soft` threshold and the existing quench at 4269.
6. **Ice dam.** Freeze a stream with the Cold hold (4265, 4700): surface ice above 128 blocks flow (3813), a lake builds behind it, then a heat hold or a rise in air temperature melts the dam and releases a flood (`WD` front) that carries sand downhill and exposes bedrock (3824). All existing; only the heat-above-ice interplay needs checking.
7. **Wet sand does not liquefy but earth does.** Rain raises `SM` (3833); repose drops with SM (4533). Add a quake (3911) with `slumpArm` after it, and a wet earth slope fails in a mudflow that buries a yard of stacked crates (4440 lift rule 1519 moves them onto the new surface). Needs only the missing `slumpArm` call in `startQuake`.
8. **Builders wall the shore with their own rubble.** Existing `wall` goal (5481) piles rock; with fix 6 each grain stays rock and a heavy sea (surge 3931) erodes the pile edge (3825 with MET check), so builders keep repairing it. Surprise comes from erosion rates differing by material.
9. **Frozen sea carries cargo.** Sea ice thicker than ~0.4 m can hold crates: add a support rule to buoyancy so a block on `seaIceAt > 0.4` rests on the ice (1357), and a thaw (4696) drops the stack through the surface into the water at once. Sinks by density (1310-1317) and floats the oak.
10. **Meteor in a lumber yard.** `meteorAftermath` (5525) already heats a 12-cell radius and throws six boulders (5532). With impact fracture, the thrown granite shatters stacks it lands on, the heat ignites every wooden block in radius, and the lava ring (5527) seals the ash. All existing triggers, only the object layer needs to listen.

---

## 7. Verify-first list (cannot be settled by reading)

- Whether any code path sets trees alight from `GT` without lava: searched for `GT[` and `igniteTree`; only 5269 inside `lavaOn`. Confirm with test 1.
- Whether `HF.update()` (1514) on the physics heightfield at every land edit is cheap enough once structures sit on piles; objects rely on a full commit (`commitLand(true)`) to see new ground. Quiet sand slumping uses `commitLand(false)` path (4591 commits via `land.dirty`), check that blocks do not hover over a slump.
- Phone cost of the 4 Hz object loop at 90 bodies: expected negligible.
