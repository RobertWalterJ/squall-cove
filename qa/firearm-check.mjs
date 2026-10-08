// The overview fire control must not be active in first person. usage: node qa/firearm-check.mjs
import { sleep, startServer, launch, loadGame, PROFILES } from './harness.mjs';
const srv = await startServer(), b = await launch(PROFILES.desktop), fail = [];
try {
  if (!await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=desktop`)) throw new Error('no load');
  const st = async () => JSON.parse(await b.ev(`JSON.stringify({ armed: __sc.FIRE.armed, hidden: document.getElementById('fireArm').hidden, mode: __sc.mode })`));
  await b.ev("__sc.setFire('lightning');1"); const a = await st(); if (a.armed !== 'lightning' || a.hidden) fail.push('arming in the overview did not show the pill ' + JSON.stringify(a));
  await b.ev("__sc.enterFP();1"); await sleep(1500); const f = await st(); if (f.mode !== 'fp') fail.push('did not enter first person ' + JSON.stringify(f)); if (f.armed !== null || !f.hidden) fail.push('still armed in first person ' + JSON.stringify(f));
  await b.ev("__sc.setFire('lightning');1"); const g = await st(); if (g.armed !== null || !g.hidden) fail.push('armed while in first person ' + JSON.stringify(g));
  console.log(fail.length ? 'FAIL: ' + fail.join(' | ') : 'ok: arming in the overview shows the pill; first person clears it and refuses to arm');
} catch (e) { console.log('ERR', e.message); fail.push(e.message); } finally { await b.close(); await srv.close(); }
process.exit(fail.length ? 1 : 0);
