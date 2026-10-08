import { startServer, launch, loadGame, PROFILES } from './harness.mjs';
import fs from 'fs';
const srv = await startServer(); const base = `http://127.0.0.1:${srv.port}/`; const out = {};
for (const k of ['desktop', 'portrait']) {
  const P = PROFILES[k]; const b = await launch(P);
  await loadGame(b, `${base}index.html?map=port&nointro=1&edition=${P.ed}`);
  out[P.ed] = await b.ev(`(()=>({ keys:(window.__sc.KEYMAP||[]).map(r=>r[0]+'|'+r[1]), btns:[...document.querySelectorAll('button[id]')].map(e=>e.id+(e.hidden?'(h)':'')) }))()`);
  await b.close();
}
fs.writeFileSync(process.argv[2], JSON.stringify(out, null, 1)); await srv.close();
