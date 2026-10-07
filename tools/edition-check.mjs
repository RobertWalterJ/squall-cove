// Squall Cove edition guard. Loads the game headless in the phone edition (390x844 and 844x390) and the
// desktop edition (1400x860), walks the main screens, saves screenshots, and FAILS (exit 1) on any page
// error or console error, and on any UI overlap in the phone edition.
// usage: node tools/edition-check.mjs [baseUrl=http://localhost:8773/] [outDir]   (serve the folder first: python serve.py)
// One headless Chrome at a time; it is killed at the end of each pass.
import fs from 'fs'; import os from 'os'; import path from 'path'; import { spawn } from 'child_process';
const base = process.argv[2] || 'http://localhost:8773/', out = process.argv[3] || path.join(os.tmpdir(), 'sc-edition-check');
const chromePath = process.env.CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const ovl = fs.readFileSync(new URL('./edition-ovl.js', import.meta.url), 'utf8');
fs.mkdirSync(out, { recursive: true });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const click = (sel, txt) => `(()=>{const b=[...document.querySelectorAll('${sel}')].find(b=>b.textContent.trim().toLowerCase().startsWith('${txt.toLowerCase()}')); if(b){b.click(); return 'ok'} return 'nobtn:${txt}'})()`;
const PASSES = [
  { name: 'phone-portrait', ed: 'phone', w: 390, h: 844, mobile: true, strict: true },
  { name: 'phone-landscape', ed: 'phone', w: 844, h: 390, mobile: true, strict: true },
  { name: 'desktop', ed: 'desktop', w: 1400, h: 860, mobile: false, strict: false },
];
async function pass(P) {
  const port = 9300 + Math.floor(Math.random() * 500), prof = fs.mkdtempSync(path.join(os.tmpdir(), 'sc-prof-'));
  const chrome = spawn(chromePath, ['--headless=new', '--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox', `--user-data-dir=${prof}`, `--remote-debugging-port=${port}`, `--window-size=${P.w},${P.h}`, 'about:blank'], { stdio: 'ignore' });
  const errs = [], fails = [], notes = []; let ws, id = 0; const pend = new Map();
  const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pend.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) { errs.push('eval: ' + JSON.stringify(r.exceptionDetails).slice(0, 200)); return null; } return r.result.value; };
  try {
    let list; for (let k = 0; k < 40; k++) { try { list = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); if (list.length) break; } catch (e) { } await sleep(500); }
    ws = new WebSocket(list.find(t => t.type === 'page').webSocketDebuggerUrl); await new Promise(r => ws.onopen = r);
    ws.onmessage = (m) => { const d = JSON.parse(m.data);
      if (d.method === 'Runtime.exceptionThrown') errs.push(String((d.params.exceptionDetails.exception && d.params.exceptionDetails.exception.description) || d.params.exceptionDetails.text).slice(0, 300));
      if (d.method === 'Runtime.consoleAPICalled' && d.params.type === 'error') errs.push('console.error: ' + d.params.args.map(a => a.value || a.description).join(' ').slice(0, 300));
      if (d.id && pend.has(d.id)) { const p = pend.get(d.id); pend.delete(d.id); d.error ? p.rej(new Error(JSON.stringify(d.error))) : p.res(d.result); } };
    await send('Page.enable'); await send('Runtime.enable');
    await send('Emulation.setDeviceMetricsOverride', { width: P.w, height: P.h, deviceScaleFactor: 1, mobile: P.mobile });
    if (P.mobile) await send('Emulation.setTouchEmulationEnabled', { enabled: true });
    await send('Page.navigate', { url: `${base}index.html?map=port&nointro=1&edition=${P.ed}` });
    for (let k = 0; k < 90; k++) { await sleep(2000); if (await ev("!!(document.getElementById('loading')&&document.getElementById('loading').classList.contains('done'))")) break; }
    const edOk = await ev("document.body.classList.contains('ed-" + P.ed + "')"); if (!edOk) fails.push('body.ed-' + P.ed + ' class missing');
    const snap = async (n, pre, wait = 800) => {
      if (pre) await ev(pre); await sleep(wait);
      const r = await send('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(path.join(out, `${P.name}_${n}.png`), Buffer.from(r.data, 'base64'));
      const o = await ev(ovl); const ov = ((o && o.overlaps) || []).filter(x => !/loadMsg|fpHint/.test(x));
      if (ov.length) { (P.strict ? fails : notes).push(`${n}: ${ov.length} overlap(s): ${ov.slice(0, 3).join(' | ')}`); }
    };
    await snap('01_overview', "document.getElementById('help')&&(document.getElementById('help').hidden=true);1");
    await snap('02_menu', "document.getElementById('bMenu').click();1"); await snap('03_menu_closed', "document.getElementById('menuSheet').hidden=true;1");
    await snap('04_command', '__sc.openCommand();1');
    await snap('05_setup', "(()=>{document.getElementById('tablet').hidden=true; __sc.openBattleSetup(); return 1})()");
    await snap('06_battle', click('#bSetup button', 'Begin battle'), 14000);
    await snap('07_battle_command', '__sc.openCommand();1'); await snap('08_battle_overview', "(()=>{document.getElementById('tablet').hidden=true; return 1})()");
    await snap('09_fp', "(()=>{__sc.playBattle('blue'); return 1})()", 6000);
    if (P.ed === 'phone') { await snap('10_fp_ring', '(()=>{__sc.sqdWheelOpen(); return 1})()', 1200); await ev('__sc.sqdWheelClose(false);1'); }
    await snap('11_deploy', "(()=>{__sc.hurt(__sc.fp.p,999,null,false); return 1})()", 3000);
    await snap('12_end', '(()=>{__sc.BATTLE.tickets.red=0; return 1})()', 4000);
    // the start menu must be the only thing on screen, and nothing behind it may be visible or tappable
    await send('Page.navigate', { url: `${base}index.html?menu=1&edition=${P.ed}` }); await sleep(5000);
    const leak = await ev(`(()=>{ const bt=document.getElementById('boot'); if(!bt||getComputedStyle(bt).display==='none') return ['start menu not shown']; const bad=[];
      for(let x=0.05;x<1;x+=0.18) for(let y=0.04;y<1;y+=0.12){ const el=document.elementFromPoint(innerWidth*x,innerHeight*y); if(el&&!bt.contains(el)) bad.push('point '+x.toFixed(2)+','+y.toFixed(2)+' is '+(el.id||el.tagName)); }
      for(const e of document.body.children){ if(e===bt||['SCRIPT','STYLE','LINK','svg','TITLE'].includes(e.tagName)) continue; const cs=getComputedStyle(e); if(cs.display!=='none'&&cs.visibility!=='hidden'&&e.getBoundingClientRect().width>0&&cs.pointerEvents!=='none') bad.push('visible outside menu: '+(e.id||e.tagName)); }
      const ver=document.getElementById('bVer'); if(!ver||!bt.contains(ver)) bad.push('version label not inside the menu'); return bad; })()`);
    if (leak && leak.length) fails.push('start menu: ' + leak.slice(0, 4).join(' | '));
    const r = await send('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(path.join(out, `${P.name}_00_startmenu.png`), Buffer.from(r.data, 'base64'));
  } catch (e) { fails.push('harness: ' + (e.stack || e)); }
  try { ws && ws.close(); } catch (e) { } try { chrome.kill(); } catch (e) { } await sleep(800); try { fs.rmSync(prof, { recursive: true, force: true }); } catch (e) { }
  for (const e of errs) fails.push('page error: ' + e);
  console.log(`\n== ${P.name}: ${fails.length ? 'FAIL' : 'ok'}`); for (const f of fails) console.log('  FAIL ' + f); for (const n of notes) console.log('  note ' + n);
  return fails.length;
}
const only = process.env.PASS; let bad = 0; for (const P of PASSES) if (!only || P.name === only) bad += await pass(P);   // PASS=desktop to run one
console.log(bad ? `\nedition-check: ${bad} failure(s). Screenshots in ${out}` : `\nedition-check: all passes ok. Screenshots in ${out}`); process.exit(bad ? 1 : 0);
