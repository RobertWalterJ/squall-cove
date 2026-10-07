# Plugging softsolver.js into Squall Cove (`index.html`)

Nothing here has been applied: `index.html` was off limits. Line numbers refer to the `large-map` worktree as read on 2026-10-06 and will drift.
Read `NOTES.md` first: it says what the solver is good and bad at, and several decisions below follow from the two failed verification tests (fast impacts, masonry).

## 0. Decision in one paragraph

Use the soft solver for **members that sag, bend, stretch and snap under sustained load**: timber and steel beams used as bridges, spars and cantilevers, glass panes (as thin
beams), ropes and cables, sails, jelly-like cargo. Keep **everything impact-driven and everything masonry on the existing cannon rigid bodies and the existing `MATB` / `onImpact` /
`updateStructures` rules**. The two systems exchange impulses once per fixed tick. Do not turn the 1.0 x 0.5 x 0.5 stone blocks into soft bodies: test (9) shows tunnelling through block
faces and 20x energy gain in a hit, and a 1 mm drop already breaks tall stacks.

## 1. Loading

```js
import { SoftWorld, makeMaterial, MATERIALS, buildBeam, buildRope, buildCloth } from './softlab/softsolver.js';   // next to the other imports (L390)
```

* No new dependency (pure ES module, typed arrays). `index.html` already uses an import map for three and cannon-es; nothing to add there.
* `sw.js` runtime-caches same-origin GETs cache-first under `squall-cove-<VERSION>`. A changed `softsolver.js` is not seen until `VERSION` is bumped. Do not touch manifest ids or cache
  prefixes (shared-origin rule).
* One `SoftWorld` for the whole game is fine (components are independent); create it next to `const world = new CANNON.World(...)` (L710), `new SoftWorld({ substeps: 4, iterations: 1, seed: <world seed>, sleep: true })`,
  and set `soft.heightfield = (x, z) => groundAt(x, z)` and `soft.heightfieldMax = <highest terrain>` (the callback is skipped for particles above that, which is most of them).
  Terrain edits (`commitLand`, `landRestore`) must call `soft.wakeAll()`.

## 2. Structure layer: MATB and the soft material

`MATB` rows (L1645) stay as they are for rigid objects: `str` is a specific impact energy in J/kg (`onImpact` compares `0.5 v^2 * share` with it), `crush` is in kPa (`updateStructures` compares
`load / area` with `crush * 1000` Pa). Add an optional block per row that only soft members read:

```js
beam:  { ..., soft: { density: 650, youngs: 1.0e10, yield: 4.0e7, fracture: 6.0e7, crush: 1.2e8, damping: 0.2, snap: true } },   // = MATERIALS.wood
steel: { ..., soft: { density: 7800, youngs: 2.0e11, yield: 2.5e8, fracture: 4.0e8, damping: 0.1 } },                         // ductile: yields, then necks bar by bar
glass: { ..., soft: { density: 2500, youngs: 7.0e10, yield: 1e13, fracture: 3.0e7, damping: 0.1, snap: true } },              // brittle, no yield
ice:   { ..., soft: { density: 917,  youngs: 9.0e9,  yield: 1e13, fracture: 1.5e6, damping: 0.2, snap: true } },
```

`const softMat = (m) => m._soft ||= makeMaterial(m.soft)`. Stresses are real SI values; do not reuse `str` or `crush`, they are game-scaled (a crate's `crush` of 40 kPa is not wood). The existing
`T` temperature field (`o.T`, `soft`/`melt` thresholds in `MATB`) can scale `youngs` / `yield` per member each second (`mat` is immutable, so build one `makeMaterial` per 100 K band or add a per-bar `dK` scale).

## 3. Which objects become soft, and when

A `CARGO` object (`spawn`, L1620) is a cannon box with `o.body`, `o.mesh`, `o.m = MATB[id]`, `o.size`. For `beam`, `steel` and `glass` keep the rigid body while the object is free,
carried, sliding or floating. Swap it for a soft member when it is **loaded as a span**: `updateStructures` already builds the support graph from `world.contacts` (`up` / `lowersOf`);
a beam with two or more distinct lowers more than ~0.3 of its length apart, or one lower plus a pinned end, is a span. Swap at that moment (not at spawn) and swap back (rebuild a
cannon box at the member's current centre and orientation) when its supports go away and it is free again.

Build the member from the rigid object so size and mass agree:

```js
const [L, w, h] = [o.size.x, o.size.z, o.size.y]; // long axis = x for beam/steel; panes: length = max, thickness = min
const b = buildBeam(soft, { a: endA, b: endB, width: w, height: h, mat: softMat(o.m), up: [0, 1, 0] });
// supports: for every cannon body touching the member, add a collider (section 4); for terrain, the heightfield already supports it
removeRigid(o); o.soft = b;     // hide the cannon body (world.removeBody) but keep o in `objects` so MATB, burning, T and the inspector still see it
```

Density times volume gives the same mass as the cannon box (`o.body.mass`); check `b` particle masses sum to it (the builder does this exactly).
Ropes (`buildRope`, 12 to 24 links) and sails (`buildCloth`, at most about 20 x 15 particles) are new entities and attach with `soft.pin(i)` to a boat or block position;
a pinned particle that must move with a rigid body is moved by the host each tick (`soft.pos`, `soft.prev` and `soft.invM = 0`), never integrated.

Boat sails: `soft.wind = (x, y, z) => [wx, wy, wz]` uses the game's `windAt`; the aerodynamic triangles come from `buildCloth`. The existing `boatForces` model can read the summed sail
force from the cloth particles (`soft.aeroF`) instead of its own sail polar once this is trusted; until then run both and compare.

## 4. Rigid and soft bodies exchange impulses (once per fixed tick)

Hook next to the existing `world.addEventListener('preStep', ...)` (L1750), which already runs once per fixed 1/60 s step (`world.step(1/60, dt, 5)`, L4072). Add a `postStep` listener; do
not step the soft world from the render loop, or the 0 to 5 fixed steps per frame will desynchronise it from cannon.

```js
const SOFT_DT = 1 / 60, cols = new Map();           // cannon body -> collider
world.addEventListener('postStep', () => {
  // 1. mirror nearby dynamic bodies as colliders (velocity matters: it drives friction and the inelastic contact)
  for (const o of objects) {
    if (o.gone || o.soft || !nearAnySoft(o.body)) { dropCollider(o); continue; }
    let c = cols.get(o.body) || addColliderFor(o.body);          // sphere for CANNON.Sphere; box (+ quaternion) for CANNON.Box; bounding box otherwise
    const p = o.body.position, v = o.body.velocity, q = o.body.quaternion;
    c.c[0] = p.x; c.c[1] = p.y; c.c[2] = p.z; c.v[0] = v.x; c.v[1] = v.y; c.v[2] = v.z; if (c.q) { c.q[0] = q.x; c.q[1] = q.y; c.q[2] = q.z; c.q[3] = q.w; }
  }
  // 2. soft step
  soft.clearImpulses(); soft.step(SOFT_DT);
  // 3. give the reaction back to the rigid bodies
  for (const [body, c] of cols) {
    if (c.j[0] === 0 && c.j[1] === 0 && c.j[2] === 0) continue;
    body.velocity.x += c.j[0] * body.invMass; body.velocity.y += c.j[1] * body.invMass; body.velocity.z += c.j[2] * body.invMass;
    // torque impulse about the centre of mass: c.tq (world frame): body.angularVelocity += body.invInertiaWorld.vmult(c.tq)
  }
});
```

* `c.j` is the total momentum the contacts took from the collider during this tick (N s), `c.tq` the angular part about the collider centre. A resting 80 kg crate on a plank returns
  `m g dt` of upward impulse per tick, which is what holds it up, and what bends the plank.
* The soft world never moves a collider: particles yield. Static scenery (piers, hull sides) can be colliders with `c.v = [0,0,0]` and their `j` ignored.
* Collider budget: only mirror bodies within ~2 m of a soft particle (use `o.body.aabb` against the structure bounds from `soft.pieces()`); at most 6 to 8 per structure. Each
  collider costs a bounding-box test per particle per sweep and a triangle test per touched bay.
* The solver adds up to 4x substeps while a collider moves fast (`maxSubstepBoost`) so it cannot jump through a bay. On phones cap this at 2.
* Verified exchange quality: test (9a) is an energy sweep and it fails (13 of 30 cases within 1.1x of the ball's energy; 4 of 6 configurations at 2 m/s, 1 of 6 at 10 m/s). An earlier 3-case version of the
  same test (not in the final file) saw momentum errors of 5 to 9 %. So treat the exchange as trustworthy for resting and slow contact only. If a cannon body hits a soft member faster than
  about 3 m/s, apply the host's own `onImpact` energy rule to decide the break (call the existing `fracture`-style path), and clamp the impulse you return: `|j| <= m_body * 8 m/s`.

## 5. Fracture, `onImpact` and fragments

* Soft members break by themselves (strain limits from the material). Subscribe once: `soft.onBreak = ({ kind, a, b, index }) => { ... }`. It fires per bar, so aggregate to one event per bay
  (`soft.dBay[index]`) and rate-limit sound: `Snd.fracture(o, 'bend')` at most once per 150 ms per member. Fire/heat/crush from `updateStructures` still apply through the member's `o.m`.
* Impact fracture should stay with `onImpact` (`body.addEventListener('collide', ...)`, L1639 / L1677): a cannon body hits the *mirrored collider*, not a cannon body, so `collide` will not fire for a
  soft member. Compute the same energy (`0.5 * v_rel^2 * share`, with `v_rel` from `c.v` and the soft contact velocity) inside step 3 above for any collider whose `j` was large this tick, and if
  it exceeds `MATB.str` call `softFracture(o)`: snap the bay under the contact (`soft.dAct[c] = 0` for the bars of `soft.dBay === bay`), which separates the member into two pieces.
* Pieces: each tick (or on `onBreak`) call `soft.pieces()`. For a piece with `!pinned && !supported && count >= 6` convert to a rigid fragment: build the cannon body as `spawn` / `fracture` do
  (box of the piece's AABB `lo`/`hi`, `mass = piece.mass`, `velocity = piece.vel`, orientation from the line between its first and last section centres), push it onto `frags` (cap 80, the
  existing `depositFrag` path recycles the oldest), then `soft.removePiece(piece.comp)`. Pieces with fewer than 6 particles become grains: `spawnGrain` with `vol = piece.mass / density`.
  Pieces that are still pinned or supported stay soft (a half-snapped cantilever keeps swaying).
* Angular velocity of a freshly separated piece is lost with this conversion; add `omega = sum(m r x v) / I` if it matters visually.

## 6. Existing block structures (`placeBlock`, `buildSlot`, `freeBlocks`, `sites`, `updateStructures`)

Leave them alone. They are rigid cannon bodies with an energy rule, a load-and-crush rule and an NPC builder that depends on `o.placed`. The soft solver would be worse at all three
(NOTES.md, limitation 3). Two optional bridges:

1. **Soft members resting on blocks.** A plank laid across two placed blocks: the blocks are cannon bodies, so they appear as box colliders for the plank (section 4) and receive its weight
   as impulses, which feeds `updateStructures` through the normal cannon contacts. No change to the block code.
2. **Breakable mortar as cannon constraints** (future, not in this prototype): the `buildBlockCluster` weld rule (tension limit, shear limit plus friction times compression, persisting for ~6
   checks) can be applied to cannon contact forces between `placed` blocks: read the contact equation impulse of each block-block contact from `world.contacts` each tick, divide by dt, and call
   `fracture`-style separation when the weld rule fires. Capacities to start from: mortar tension 0.3 MPa times the shared face area, shear 1.5x that plus 0.6 x normal force.

## 7. Phone cost and limits

Measured on this PC (node v24.18.0, not a phone): about 0.13 microseconds per particle per sweep, 3.80 ms mean per 60 Hz frame for 2886 particles at 4 substeps x 1 sweep (9016 bars, 1728 welds),
6.96 ms at 8 x 1, 11.52 ms at 8 x 2, 2.35 ms with sleeping on and the scene at rest (the 1446 non-masonry particles slept). The phone factor is assumed to be 3 to 5x, which is **unmeasured**:

| budget item | rule |
|---|---|
| awake particles | at most ~800 awake at the phone tier (4 x 1) is a safe starting point: about 1.0 ms here, about 3 to 5 ms on a phone by the assumed factor. Raise only after timing on the S23 |
| substeps x sweeps | phone 4 x 1, desktop 8 x 1, quality 8 x 2. Cost is linear in the product |
| members | beams: bays of 1.5x thickness (a 3 m, 0.22 m timber beam = 9 bays, 50 particles, about 180 bars, 72 collision triangles); ropes 12 to 24 links; sails up to 20 x 15; jelly up to 5 x 5 x 5 |
| sleeping | always `sleep: true` on phones. A piece sleeps after 1 s below 2e-5 m/s, wakes when a collider enters it, a moving piece touches it, or `wakeAll()` (terrain edit, gravity change) |
| pairs | `pairs: false` unless loose pieces exist; the hash pass is about 0.4 ms per 3000 particles |
| colliders | at most 6 to 8 mirrored bodies per structure; triangles only touched when a collider's box reaches them |
| fast colliders | `maxSubstepBoost` 2 on phones |
| worker | the solver is typed-array only. To move it off the main thread, copy the heightfield to a `Float32Array` grid (the callback cannot cross), post `pos` (3N floats) back each tick, and send collider updates in. About 36 KB per tick for 3000 particles |
| settling | build, then call `soft.relax(120)` on a hidden frame (about 1 s of sim per beam) so a spawned bridge does not sag visibly over several seconds |

## 8. Save and load

`saveWorld` / `loadWorld` / `snapshotWorld` / `worldUndo` already exist. Per `SoftWorld`, store the typed-array prefixes `pos`, `prev`, `vel`, `dRest`, `dAct`, `wAct`, `tAct`, `dOver`, `wOver`, `dead`,
plus `time`, `stepCount`, `nBroken` and the construction recipe (builder name, arguments, seed). Rebuild with the same seed and builders in the same order, then overwrite those arrays
(constraint creation order and the scatter PRNG are deterministic, so the indices line up). `soft.checksum()` is available to assert that a reload matches.

## 9. Order of work

1. Add the module import, one `SoftWorld`, the heightfield link, `wakeAll()` on terrain edits (no visible change).
2. Add `soft` blocks to `MATB`; build timber beams as soft members only in a debug spawn (`__sc.softBeam()`), render with a `THREE.LineSegments` from `softlab.html`'s `syncVisuals` or, better, a skinned
   box mesh bent by the section centres (the 5-particle sections give a spline of centres and a frame).
3. Section 4 loop with one box collider and a ball; check `c.j` signs with a falling crate on a plank.
4. Fragments (section 5) and sound; then swap-on-span logic in `updateStructures`; then ropes and sails.
5. Time on the phone; set the particle cap from the measurement.

## 10. Things that bite

* `softsolver.js` expects SI units and **y up**; Squall Cove is y up, metres: no conversion.
* `buildBlockCluster` origin must rest on the ground (`groundY`); beams pinned to a cannon body need that body's motion pushed into the pinned particles every tick.
* `world.step(dt)` takes the *frame* dt (here always 1/60); calling it with a variable dt works (substeps scale with `substepHz`) but changes cost.
* The `heightfield` callback is called per particle per sweep near the ground: keep it to the bilinear terrain read (`groundAt`), not the wave field.
* `Math.random` is never used inside the solver; keep it that way in host code that feeds it (collider updates) if replays matter.
