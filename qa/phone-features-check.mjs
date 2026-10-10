// Behaviour checks for the phone edition features that a screenshot cannot show. usage: node qa/phone-features-check.mjs
// One headless Chrome, 390x844 touch. Browser APIs the headless build lacks (vibrate, wake lock, battery) are replaced by recording stubs.
//   one modal at a time + the Back button, wake lock while playing, haptics, tilt aiming (off by default, opt-in, sensitivity), the helicopter is ride-only,
//   lost-graphics recovery, orientation hint (shown in portrait first person, hidden in landscape, dismissible), the smoothness governor and low-battery saver.
import { ROOT, sleep, startServer, launch, loadGame, clickText } from './harness.mjs';
const srv = await startServer(); const base = `http://127.0.0.1:${srv.port}/`; const ok = [], fails = [];
const check = (c, good, bad) => (c ? ok.push(good) : fails.push(bad));
const STUBS = `window.__vib=[]; navigator.vibrate=(p)=>{__vib.push(p); return true};
window.__wl={req:0,rel:0}; Object.defineProperty(navigator,'wakeLock',{value:{request: async()=>{__wl.req++; return {release(){__wl.rel++}, addEventListener(){}}}},configurable:true});
window.__bat={charging:false,level:0.9,addEventListener(){}}; Object.defineProperty(navigator,'getBattery',{value: async()=>window.__bat,configurable:true});`;
async function run(name, url, P, body) {
  const b = await launch(P); await b.send('Page.addScriptToEvaluateOnNewDocument', { source: STUBS });
  try { if (!(await loadGame(b, url))) { fails.push(name + ': game did not start'); } else { await b.ev("(document.getElementById('help')||{}).hidden=true;1", true); await body(b); } } catch (e) { fails.push(name + ': ' + (e.stack || e)); }
  for (const e of b.errs) fails.push(name + ' page error: ' + e); await b.close();
}
const P = { w: 390, h: 844, mobile: true, dpr: 1 };
await run('features', `${base}index.html?map=port&nointro=1&gov=auto&edition=phone`, P, async (b) => {
  const open = () => b.ev("[...['tablet','bSetup','menuSheet','help','inspector','tmap','bSpawn'].filter(i=>{const e=document.getElementById(i);return e&&!e.hidden})]");
  // ---- one modal at a time
  await b.ev("__sc.openCommand('fire');1"); await sleep(400);
  check((await b.ev("document.body.classList.contains('modal-open')")) && (await open()).join() === 'tablet', 'Command opens alone and tags the page modal-open', 'Command did not open cleanly: ' + await open());
  await b.ev("__sc.openBattleSetup();1"); await sleep(500);
  let o = await open(); check(o.join() === 'bSetup', 'opening Battle setup closed Command: one modal', 'two modals open: ' + o.join());
  // ---- the Back button closes the top sheet
  await b.ev("history.back();1"); await sleep(600); o = await open();
  check(o.length === 0 && !(await b.ev("document.body.classList.contains('modal-open')")), 'Back closed the sheet and cleared modal-open', 'Back did not close the sheet: ' + o.join());
  await b.ev("document.getElementById('bMenu').click();1"); await sleep(400); await b.ev("__sc.openCommand('fire');1"); await sleep(400);
  check((await open()).join() === 'tablet', 'Command opened over the Menu closes the Menu', 'Menu stayed open under Command: ' + await open());
  await b.ev("__sc.openCommand('map'); document.getElementById('tablet').hidden=true;1"); await sleep(400);
  // ---- haptics: a button press pulses 8 ms; the stub records it
  await b.ev("__vib.length=0;1"); const r = await b.ev("(()=>{const e=document.getElementById('bLog').getBoundingClientRect(); return [e.left+e.width/2,e.top+e.height/2]})()"); await b.tap(r[0], r[1], true); await sleep(500);
  check((await b.ev('__vib')).includes(8), 'a button press vibrates 8 ms', 'no 8 ms pulse after a tap: ' + JSON.stringify(await b.ev('__vib')));
  await b.ev("document.getElementById('menuSheet').hidden=true;1"); await sleep(300);
  // ---- tilt settings exist, off by default, and the slider is stored
  await b.ev("document.getElementById('bMenu').click(); document.querySelector('.mtabs [data-mt=settings]').click();1"); await sleep(500);
  const g = await b.ev("(()=>{const v=(i)=>{const e=document.getElementById(i); const r=e.getBoundingClientRect(); return e&&!e.closest('[hidden]')&&r.height>0?Math.round(r.height):0}; return {gyro:document.getElementById('mGyro').textContent, gh:v('mGyro'), vib:v('mVib'), perf:v('mPerf'), k:v('mGyroK'), on:__sc.PH.S.gyro}})()");
  check(g && /off/.test(g.gyro) && !g.on && g.gh >= 48 && g.vib >= 48 && g.perf >= 48 && g.k > 0, 'Settings shows Aim by tilting (off), Vibration, Smoothness and the sensitivity slider', 'Settings controls are wrong: ' + JSON.stringify(g));
  await b.ev("(()=>{const k=document.getElementById('mGyroK'); k.value='1.6'; k.dispatchEvent(new Event('input',{bubbles:true})); return 1})()");
  check((await b.ev("__sc.PH.S.gyroK")) === 1.6 && (await b.ev("localStorage.getItem('squall-cove-gyro-k')")) === '1.6', 'the sensitivity slider is stored under a squall-cove key', 'the slider did not store 1.6');
  await b.ev("document.getElementById('menuSheet').hidden=true;1"); await sleep(300);
  // ---- battle, wake lock, back in play
  await b.ev("__sc.openBattleSetup();1"); await sleep(600); await b.ev(clickText('#bSetup button', 'Begin battle')); await sleep(16000);
  await sleep(1800); const wl = await b.ev('__wl'); check(wl.req >= 1, 'wake lock requested once the battle is on', 'no wake lock request in a battle: ' + JSON.stringify(wl));
  await b.ev("document.getElementById('bMenu').click();1"); let wl2 = null; for (let i = 0; i < 16; i++) { await sleep(500); wl2 = await b.ev('__wl'); if (wl2.rel >= 1) break; }
  check(wl2.rel >= 1, 'wake lock released while the Menu is open', 'wake lock was not released with the Menu open: ' + JSON.stringify(wl2));
  await b.ev("document.getElementById('menuSheet').hidden=true;1"); await sleep(2000); const wl3 = await b.ev('__wl'); check(wl3.req >= 2, 'wake lock taken again when play resumes', 'wake lock not re-taken: ' + JSON.stringify(wl3));
  await b.ev("__sc.openCommand('fire');1"); await sleep(300); await b.ev("document.getElementById('tablet').hidden=true;1"); await sleep(300);
  await b.ev("history.back();1"); await sleep(700);
  check(await b.ev("!document.getElementById('menuSheet').hidden"), 'Back in the middle of a battle opens the Menu instead of leaving', 'Back in a battle did not open the Menu');
  await b.ev("document.getElementById('menuSheet').hidden=true;1"); await sleep(300);
  // ---- first person: orientation hint, tilt aim, helicopter
  await b.ev("__sc.playBattle('blue');1"); await sleep(6000);
  const oh = await b.ev("(()=>{const e=document.getElementById('orientHint'); const cs=getComputedStyle(e); return {hidden:e.hidden, display:cs.display}})()");
  check(oh && !oh.hidden && oh.display !== 'none', 'portrait first person suggests landscape (a card, not a lock)', 'orientation hint missing in portrait: ' + JSON.stringify(oh));
  { const html = (await import('fs')).readFileSync(ROOT + '/index.html', 'utf8'); check(!/orientation\.lock\(/.test(html), 'nothing calls screen.orientation.lock (the hint only suggests)', 'the page calls screen.orientation.lock'); }
  await b.send('Emulation.setDeviceMetricsOverride', { width: 844, height: 390, deviceScaleFactor: 1, mobile: true }); await sleep(800);
  const oh2 = await b.ev("getComputedStyle(document.getElementById('orientHint')).display"); check(oh2 === 'none', 'the hint disappears in landscape', 'the hint still shows in landscape: ' + oh2);
  await b.send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true }); await sleep(800);
  { const rr = await b.ev("(()=>{const e=document.getElementById('orientOk').getBoundingClientRect(); return [e.left+e.width/2,e.top+e.height/2]})()"); await b.tap(rr[0], rr[1], true); await sleep(500); }
  check(await b.ev("document.getElementById('orientHint').hidden && localStorage.getItem('squall-cove-orient')==='1'"), 'Got it hides the hint and remembers', 'the hint was not dismissed');
  const tilt = async () => { const y0 = await b.ev('__sc.fp.yaw'); await b.ev("window.dispatchEvent(new DeviceMotionEvent('devicemotion',{rotationRate:{alpha:0,beta:0,gamma:40},interval:16}));1"); return (await b.ev('__sc.fp.yaw')) - y0; };
  check(Math.abs(await tilt()) < 1e-9, 'tilt aiming does nothing while it is off (the default)', 'tilt moved the view with the setting off');
  await b.ev("__sc.PH.gyroSet(true);1"); await sleep(300); const dy = await tilt();
  check(dy > 0.001 && dy < 0.05, `tilt aiming turns the view a little once it is on (${dy.toFixed(4)} rad for 40 deg/s)`, 'tilt on gave an unexpected turn: ' + dy);
  await b.ev("document.getElementById('bMenu')&&0; __sc.openCommand('fire');1"); await sleep(300); const dm = await tilt(); check(Math.abs(dm) < 1e-9, 'tilt is ignored while a sheet is open', 'tilt moved the view under a sheet'); await b.ev("document.getElementById('tablet').hidden=true;1");
  await b.ev("__sc.PH.gyroSet(false);1");
  const heli = await b.ev(`(()=>{ try { const p=__sc.fp.p; const k=Object.keys(__sc.BVH)[0]; const c=__sc.bvHeliMake(k,'blue',p.x+8,p.z,0); if(!c) return 'noheli'; const before=__sc.fp.veh?1:0; const r=__sc.bvEnter(c, c.seats[0]); return JSON.stringify({r, seat: __sc.fp.vseat && __sc.fp.vseat.kind, veh: !!__sc.fp.veh}) } catch(e){ return 'err '+e } })()`);
  let hj = null; try { hj = JSON.parse(heli); } catch (e) { }
  check(hj && (hj.seat === 'pass' || hj.r === false), 'the helicopter pilot seat is not offered on the phone: you ride as a passenger or are refused with a message', 'helicopter seat check: ' + heli);
  await b.ev("try{__sc.bvLeaveKey()}catch(e){};1");
  // ---- lost graphics and recovery
  const fr0 = await b.ev('__sc.renderer.info.render.frame');
  await b.ev("(()=>{const gl=__sc.renderer.getContext(); const x=gl.getExtension('WEBGL_lose_context'); window.__lose=x; x.loseContext(); return 1})()"); await sleep(700);
  const cardShown = await b.ev("!document.getElementById('ctxCard').hidden"); check(cardShown, 'a plain card appears when the graphics are lost', 'no card after the context was lost');
  await b.ev("window.__lose.restoreContext();1"); await sleep(2500);
  const cardGone = await b.ev("document.getElementById('ctxCard').hidden"), fr1 = await b.ev('__sc.renderer.info.render.frame'); await sleep(1500); const fr2 = await b.ev('__sc.renderer.info.render.frame');
  check(cardGone && fr2 > fr1, 'the card goes away and drawing resumes after the context is restored', `after restore: card hidden=${cardGone}, frames ${fr1} -> ${fr2}`);
  // ---- regression (v9.9.18): losing the graphics at different moments must never make the frame loop throw (three reads a null program log: "reading 'trim'")
  for (let i = 0; i < 5; i++) { await b.ev("window.__lose.loseContext();1"); await sleep(250 + i * 130); await b.ev("window.__lose.restoreContext();1"); await sleep(900); }
  check(!b.errs.some(e => /frame error/.test(e)), 'no frame error through load, a battle, first person, Settings and five lose/restore cycles', 'a frame error was logged: ' + b.errs.filter(e => /frame error/.test(e)).join(' | '));
  // ---- governor: the headless software renderer is slow, so auto must have stepped the resolution down by now
  await b.ev("(()=>{ let t=performance.now()+100000; for(let i=0;i<90;i++){ t+=30; __sc.govFrame(t); } return 1 })()"); const gv = await b.ev('({steps:__sc.GOV.steps, dpr:__sc.GOV.dpr, cap:__sc.GOV.cap, mode:__sc.GOV.perf})');
  check(gv.steps.length > 0 && gv.dpr < 1.5, `the governor stepped down on a slow renderer: ${gv.steps.join(', ')}`, 'the governor did not react to slow frames: ' + JSON.stringify(gv));
});
// a low battery on load (the stub reports 12 percent before the page starts)
{
  const b = await launch(P); await b.send('Page.addScriptToEvaluateOnNewDocument', { source: STUBS.replace('level:0.9', 'level:0.12') });
  try { if (await loadGame(b, `${base}index.html?map=port&nointro=1&gov=auto&edition=phone`)) { await sleep(1500); const s = await b.ev('({low:__sc.GOV.lowBat, cap:__sc.GOV.cap, dpr:__sc.GOV.dpr})'); check(s.low && s.cap === 30 && s.dpr <= 1, 'below 20 percent battery the saver turns on by itself (1.0 and 30 fps)', 'low battery did not switch on the saver: ' + JSON.stringify(s)); } else fails.push('battery: game did not start'); } catch (e) { fails.push('battery: ' + e); }
  for (const e of b.errs) fails.push('battery page error: ' + e); await b.close();
}
await srv.close();
console.log('\n== phone-features-check'); for (const o of ok) console.log('  ok   ' + o); for (const f of fails) console.log('  FAIL ' + f); console.log(fails.length ? `\nphone-features-check: ${fails.length} failure(s)` : '\nphone-features-check: all green'); process.exit(fails.length ? 1 : 0);
