# Physics core audit (Oct 2026)

Added: `PHYS` (one table of g, water and air density, step, cell size) and `LEDGER` (every 2 s: loose ground m3, surface water m3, soil water, cargo mass, counts). The Cove report shows the ledger.

Results (headless, standard map):
- Grain conservation: poured sand 120, earth 200, rock 150 m3 gave a ledger change of exactly 120, 200, 150 (ratio 1.000) after 60 s.
- Time-step independence: a 300 m3 sand pile after 45 s at 60 fps vs 30 fps: peak 5.85 vs 5.88 m, profile within 0.1 m, total 300 in both.
- Wave energy: ripple field is clamped (cap rises with impact energy, decays back to 0.6 m), so drops of 1 t and 1000 t are stable.

Still open: water conservation (springs, rain, evaporation, ocean level), lava ledger, single material flag per cell, per-cell constant sweep, soft structures (see softlab/).
