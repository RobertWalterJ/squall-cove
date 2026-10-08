// Regression check: in first person on the desktop edition the canvas is what sits at the screen centre, a click asks for the pointer lock,
// and when the lock is refused plain mouse movement still turns the view. usage: node qa/aim-check.mjs
import { sleep, startServer, launch, loadGame, clickText, PROFILES } from './harness.mjs';
const srv = await startServer(); const b = await launch(PROFILES.desktop); let fail = [];
try {
  if (!await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=desktop`)) throw new Error('no load');
  await b.ev("__sc.openCommand();1"); await sleep(400); await b.ev("document.getElementById('tablet').hidden=true; __sc.openBattleSetup(); 1"); await sleep(500);
  await b.ev(clickText('#bSetup button', 'Begin battle')); await sleep(5000); await b.ev("__sc.CHEAT.god=true;__sc.playBattle('blue');1"); await sleep(3000);
  await b.ev("window.__locks=0; document.getElementById('c').requestPointerLock=function(){window.__locks++; return Promise.reject(new Error('refused'))}; 1");
  const top = await b.ev("(()=>{const e=document.elementFromPoint(innerWidth/2,innerHeight/2); if(!e) return 'none'; const cs=getComputedStyle(e); return (e.id||e.tagName)+'|pe='+cs.pointerEvents+'|z='+cs.zIndex+'|parent='+(e.parentElement&&e.parentElement.id)})()");
  if (top.split('|')[0] !== 'c') fail.push('element at the screen centre is ' + top + ', not the canvas');
  await b.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 700, y: 430 }); await b.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: 700, y: 430, button: 'left', clickCount: 1, buttons: 1 }); await b.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: 700, y: 430, button: 'left', clickCount: 1 });
  await sleep(300); const n = await b.ev('window.__locks'); if (!(n >= 1)) fail.push('a click did not request the pointer lock');
  const y0 = await b.ev('__sc.fp.yaw'); for (let i = 1; i <= 8; i++) { await b.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 700 + i * 15, y: 430 }); await sleep(60); }
  const y1 = await b.ev('__sc.fp.yaw'); if (Math.abs(y1 - y0) < 0.05) fail.push('mouse movement without pointer lock did not turn the view (' + y0 + ' -> ' + y1 + ')');
  console.log(fail.length ? 'FAIL: ' + fail.join(' | ') : 'ok: canvas on top, click requests lock, free-look works (' + n + ' lock requests, yaw ' + (+y0).toFixed(2) + ' -> ' + (+y1).toFixed(2) + ')');
} catch (e) { console.log('ERR', e.message); fail.push(e.message); } finally { await b.close(); await srv.close(); }
process.exit(fail.length ? 1 : 0);
