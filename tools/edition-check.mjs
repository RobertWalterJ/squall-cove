// Squall Cove edition guard. Loads the game headless in the phone edition (390x844 and 844x390) and the desktop edition (1400x860),
// walks every screen (sandbox, Menu, Command tabs, tactical map, battle setup, battle, first person, squad ring, deploy, end, start menu),
// saves screenshots to qa/shots/ and FAILS (exit 1) on a page error, an overlap, a target under 48 px, text cut off by the screen edge,
// two modals at once, a control covered by something, a sideways scroll, or a start menu that leaks the game behind it.
// This is the same sweep that qa/parity-check.js runs; run `node qa/parity-check.js` for the whole release gate (adds lint, feature matrix, goldens).
// usage: node tools/edition-check.mjs [outDir=qa/shots]      env PASS=portrait|landscape|desktop runs one profile
// One headless Chrome at a time (tracked PID, killed by tree). It serves the folder itself, so no server needs to be running.
import path from 'path'; import fs from 'fs';
import { ROOT, startServer, PROFILES } from '../qa/harness.mjs';
import { sweep, report } from '../qa/shoot.mjs';
const out = path.resolve(process.argv[2] || path.join(ROOT, 'qa', 'shots')); fs.mkdirSync(out, { recursive: true });
const srv = await startServer(); const base = `http://127.0.0.1:${srv.port}/`; let bad = 0;
for (const k of Object.keys(PROFILES)) {
  if (process.env.PASS && process.env.PASS !== k) continue;
  const rep = await sweep(PROFILES[k], base, out); const f = report(rep); bad += f.length;
  console.log(`\n== ${k}: ${f.length ? 'FAIL' : 'ok'} (${rep.states.length} screens)`); for (const x of f) console.log('  FAIL ' + x);
}
await srv.close(); console.log(bad ? `\nedition-check: ${bad} failure(s). Screenshots in ${out}` : `\nedition-check: all passes ok. Screenshots in ${out}`); process.exit(bad ? 1 : 0);
