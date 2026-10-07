# softlab: soft / deformable structure solver (prototype)

Files: `softsolver.js` (the solver, ES module, no dependencies), `softlab.html` (3D demo, three r160 from the CDN already used by `index.html`),
`verify.js` (quantitative checks, `node softlab/verify.js [--quick]`, prints a table and writes `verify-results.json`), `verify-output.txt` (last full run),
`INTEGRATION.md` (how it plugs into `index.html`). Nothing outside `softlab/` was touched.

## What it is

A particle solver. Every particle is a point mass with a collision radius. Structure comes from constraints between particles:

| constraint | meaning | per-material properties |
|---|---|---|
| distance bar | axial spring, k = E A / L0 | E, area, density, damping, plastic yield strain, fracture strain, crush strain, scatter |
| tetra | volume preservation, k = K / V0 | bulk modulus from E and Poisson |
| weld | 3-axis point joint with a normal (mortar, glue) | stiffness, break force (tension / shear / friction-aided shear) |

Contacts: heightfield callback `(x,z) => y`, spheres, oriented boxes (all report the reaction impulse and torque for the host), particle-particle contacts between
different connected pieces (with friction), and a "skin" so a ball cannot slip between widely spaced section particles: beam bay faces (triangles, exact sphere-triangle
closest point, sampled for boxes) and rope links (sampled edges).

Material descriptor: `makeMaterial({density, youngs, yield, fracture, damping, poisson, crush, scatter, snap})`. Stresses in Pa, strain limits are stress / E.

Builders (all return handles): `buildBeam` / `buildPlank` (square or rectangular section, 5 particles per section), `buildRope`, `buildCloth` (sail, with wind), `buildBlockCluster`
(masonry-like: 8-particle stone blocks plus mortar welds, optional tets), `buildJelly` (tet-meshed soft solid). `pieces()` / `removePiece()` hand broken chunks to a host.

Determinism: fixed iteration order, creation-order adjacency, seeded PRNG (mulberry32) only for strength scatter, no `Math.random`. Same seed gives a bit-identical state hash
(verified, test "extra"). The `heightfield` callback is the host's responsibility.

## Why vertex block descent and not XPBD

I built XPBD first (compliance-based, one Gauss-Seidel pass per substep, "small steps"). It was rejected on measured results, not taste:

* Its steady state is biased by the iteration count. With the standard start-from-the-gravity-advanced-prediction, a 0.8 m wooden cantilever (analytic tip 0.04 mm) came out
  at about 25 mm, the same for E = 1e9 and 1e10: stiffness was effectively set by the sweep count, not by the material. Even 32 substeps x 2 sweeps was still about 150x too soft.
* With a single sweep per substep it was energy-unstable on redundant stiff trusses (a rigid cube pumped from 17 J to 4e4 J); it needed a symmetric forward/backward pair.

Vertex Block Descent (Chen et al. 2024, Gauss-Seidel on the implicit-Euler energy with a local 3x3 Newton step per vertex, PSD Hessian) fixes the first problem structurally:
the sweep starts from "previous state plus velocity", so a structure at rest is an exact fixed point of the sweep and converges to the true static solution whatever the
sweep count. Only the time to converge depends on the sweep count. It is also deterministic per vertex, needs no global matrix, and a vertex costs about 125 ns per sweep here
(about 0.4 ms per sweep for 3000 particles on this PC). Augmented VBD (hard constraints with warm-started multipliers) was not implemented: contacts are projections and
welds are stiff springs with force-based breaking, which is the weakest part (see limitations).

Details that mattered, each found by a failing test:

* Under-relaxation: omega = 0.6 on the local step. omega = 1 blew up in undamped prestressed beams (energy +1.7e6 J on a 1.6 kJ beam), omega 0.75 still blew up in 3 of 18 ball-on-plank cases (2x to 12x energy), omega 0.6 had one mild case (1.27x); omega > 1 (SOR) is unstable.
* Free pieces (no pinned particle, no contact last substep) start from the full inertial prediction. Stiff Gauss-Seidel converges extremely slowly on rigid translation
  (a free beam fell 0.002 m in 2 s), so without this a fragment would hang in the air.
* Mass-proportional damping is applied relative to the piece's own centre-of-mass velocity when it is in free flight, otherwise falling chunks are slowed like in air.
* Contact push-out moves the previous position with it (a push is not velocity) and the contact is inelastic along the normal. Without this, ground contacts pop and a
  1 mm drop of a tower rebounds hard enough to break the mortar.
* Section-shape bars of beams (rings, spokes) are 1% of the section area and never fracture themselves; at 50% area the stiff section bars made settling 10 to 40x slower.

## Beam model (what "matches Euler-Bernoulli" rests on)

A section is 4 corner particles plus a centre particle. The 4 corner chords have area w h / 12 each so that sum(A y^2) = w h^3 / 12 about both axes (EI exact), the centre bar has
the remaining area (EA exact), and each bay carries one alternating diagonal per face sized for 0.7 x the Timoshenko shear stiffness. Strains in the corner chords are the
real outer-fibre strains, so yield and fracture stress limits apply to bending directly (verified in tests 4a and 4b). Bays default to 1.5 x the larger section dimension.
Torsion and weak-axis bending were not verified separately.

## Verification (full run, `node softlab/verify.js`, this PC, node v24.18.0)

12 of 14 pass. Numbers are in `verify-output.txt`.

| test | result |
|---|---|
| (1) cantilever tip vs Euler-Bernoulli, 1.2 m wood, 8 bays | 0.188 mm vs 0.183 mm: +2.65 % (limit 10 %). Soft E=2e7 variant (1a): +2.47 %. Settles to 5 % in 1.5 s |
| (1b) L/h = 16, same settings | ratio 0.97 at 4 s, 1.02 at 8 s, 1.014 at 40 s. Settling time grows roughly with bays squared |
| (2) hanging chain vs catenary, 24 links | mid sag 1409.0 mm vs 1407.5 mm analytic (+0.11 %); worst node deviation 0.11 % of sag (limit 5 %) |
| (3) free fall, no collisions, energy | never grows (+0.000 J) in 3 cases incl. 8 mm and 20 mm pre-bends at 4 and 8 substeps; COM falls 19.64 to 19.66 m vs 19.62 m (0.1 to 0.2 %) |
| (4a) beam past yield | elastic control returns to -0.005 mm; plastic beam stays 88.7 mm bent (76.7 % of the 115.7 mm peak). The crude hinge estimate says ~70 mm, so 27 % more than that estimate |
| (4b) beam past fracture | first break at 8464 N vs 8298 N analytic (+2.0 %, that is the load-step size); snaps into 2 pieces (5 + 40 particles), `pieces()` mass sums to the beam mass |
| (5) 30 / 60 / 120 Hz | identical to 0.000 % with a fixed 480 Hz substep rate; with a fixed 8 substeps per frame (h varies 4x) spread 4e-5 %. Limit was 10 % |
| (6) cost, 2886 particles, 9016 bars, 1728 welds, 72 contacts | phone tier (4 substeps x 1 sweep) mean 3.80 ms (p95 4.06, max 5.85) per 60 Hz frame; default tier (8 x 1) 6.96 ms; quality (8 x 2) 11.52 ms. Sleeping on, scene at rest, no wind: 2.35 ms (the masonry cluster never sleeps, the other 1446 particles do). Budget used: 5.5 ms for the phone tier on this PC. A phone core is guessed at 3 to 5x slower: 11 to 19 ms for the phone tier, **not measured on a phone** |
| (7) volume constraints | jelly cube volume -0.08 % at rest on the ground |
| (8) sleeping (opt-in) | tip -0.67 % vs EB, sleeps at 4.6 s, 0.005 ms per frame asleep, wakes when a collider arrives |
| (extra) determinism | identical state hash on two runs |
| **(9a) 80 kg ball hits a free 36 kg plank, energy** | **FAIL: 13 of 30 cases keep total kinetic energy within 1.1x of the ball's (2 m/s: 4/6, 4 m/s: 4/6, 6 m/s: 2/6, 8 m/s: 2/6, 10 m/s: 1/6); worst case 45.6x** |
| **(9) masonry tower hit by an 80 kg ball at 6 m/s** | **FAIL: it stands for 6 s with no breaks (height 2.529 m), but after the hit total kinetic energy reaches 22.8x the ball's and z-momentum 2.1x** |

## Known limitations (honest list)

1. **Fast impacts are not energy-faithful** (9a, 9). A bar near its fracture strain stores kilojoules; contact push plus fracture releases it. Quasi-static and gentle loading
   (up to roughly 2 to 3 m/s on a plank) is fine, 6 m/s and above is not. The host should keep deciding impact breakage with its existing energy rule (`onImpact`) and use the
   solver for sustained load, sag and slow collapse.
2. **Stiff members respond softly and late to sudden loads.** The static answer is exact but the transient lags (a plank under an 80 kg ball showed several times the analytic
   dynamic deflection and a peak force of 2 to 3x analytic during development runs that are not in `verify.js`). Slender members also take seconds to reach equilibrium
   (1.5 s at 8 bays, ~8 s at 16 bays). Call `relax()` after building, or build already settled. A banded block solve along each beam would fix both; not done.
3. **Masonry is the weakest area.** Stone is softened to E = 3 GPa and plastic at 60 MPa, welds are capped at 3.2e8 N/m per m2, and a stack placed 1 mm above the ground breaks
   its mortar on touchdown (`groundY` in `buildBlockCluster` removes that drop). Colliders only see particles, so a ball can pass through a 0.5 m block face between the
   corner particles. Blocks keep their shape only through bars; interpenetration of separated blocks is limited to corner-sphere contacts. For the game's existing block
   structures keep the cannon rigid bodies (see INTEGRATION.md).
4. **Fracture is filtered.** A bar must stay over its strain limit for 6 checks (check rate 240 Hz at 480 Hz substeps, about 25 ms) unless over by 5x. This suppresses solver noise but
   delays impact fracture. Brittle materials (`snap: true`: wood, stone) break the whole bay when one chord fails; ductile ones break bar by bar.
5. Plasticity is elastic-perfectly-plastic by rest-length flow, no hardening, and the truss section yields all at once (no shape factor).
6. Cloth has no skin (particles only) and no self-collision; ropes collide through their links; there is no beam-beam or rope-rope contact except between separate pieces.
7. Particle-particle contact exists only between different connected pieces; a piece does not collide with itself.
8. Everything is single-threaded JS; sleeping is per connected piece and uses speed < 2e-5 m/s for 1 s, which only truly settled pieces reach.
9. Cost numbers are from desktop node; the phone factor is an assumption.

## Tiers

`substeps` x `iterations` per 60 Hz frame (or `substepHz` for a fixed substep rate): phone 4 x 1, default 8 x 1, quality 8 x 2. `maxSpeed` 80 m/s clamps runaway particles and a
NaN guard freezes any particle that goes non-finite (`world.nanGuard` counts them).
