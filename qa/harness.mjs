// Squall Cove QA harness: one static server + ONE headless Chrome at a time (tracked PID, killed by tree on close).
// Used by qa/parity-check.js, qa/shoot.mjs and tools/edition-check.mjs. Never uses a broad process kill.
import fs from 'fs'; import os from 'os'; import path from 'path'; import http from 'http'; import { spawn, spawnSync } from 'child_process'; import { fileURLToPath } from 'url';
export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg', '.glb': 'model/gltf-binary', '.webmanifest': 'application/manifest+json', '.mp3': 'audio/mpeg', '.ogg': 'audio/ogg', '.wav': 'audio/wav', '.svg': 'image/svg+xml', '.txt': 'text/plain', '.bin': 'application/octet-stream' };

// Static server. The service worker scope in sw.js is /squall-cove/, so we serve the folder under both / and /squall-cove/.
export function startServer(root = ROOT, port = 0, overrides = {}) {
  const stats = { hits: [] };
  const srv = http.createServer((req, res) => {
    try {
      let p = decodeURIComponent(req.url.split('?')[0]); stats.hits.push(p);
      if (p.startsWith('/squall-cove/')) p = p.slice('/squall-cove'.length);
      if (p === '/') p = '/index.html';
      if (overrides[p] !== undefined) { res.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'text/plain', 'Cache-Control': 'no-cache' }); res.end(overrides[p]); return; }
      const f = path.join(root, p); if (!f.startsWith(root) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); res.end('nf'); return; }
      const st = fs.statSync(f), ext = path.extname(f).toLowerCase(); const h = { 'Content-Type': MIME[ext] || 'application/octet-stream', 'Cache-Control': 'no-cache', 'Accept-Ranges': 'bytes' };
      const rg = req.headers.range && /bytes=(\d*)-(\d*)/.exec(req.headers.range);
      if (rg) { const a = rg[1] ? +rg[1] : 0, b = rg[2] ? +rg[2] : st.size - 1; res.writeHead(206, { ...h, 'Content-Range': `bytes ${a}-${b}/${st.size}`, 'Content-Length': b - a + 1 }); fs.createReadStream(f, { start: a, end: b }).pipe(res); return; }
      res.writeHead(200, { ...h, 'Content-Length': st.size }); fs.createReadStream(f).pipe(res);
    } catch (e) { try { res.writeHead(500); res.end(String(e)); } catch (_) { } }
  });
  return new Promise(r => srv.listen(port, '127.0.0.1', () => r({ port: srv.address().port, stats, setOverride: (p, c) => { overrides[p] = c; }, close: () => new Promise(x => { srv.closeAllConnections && srv.closeAllConnections(); srv.close(x); }) })));
}

const chromePath = () => process.env.CHROME || ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe'].find(p => fs.existsSync(p));

// One browser. opts: {w,h,mobile,dpr,extraArgs}. Returns {send,ev,snap,errs,close,pid}
export async function launch(opts) {
  const dbg = 9300 + Math.floor(Math.random() * 600), prof = fs.mkdtempSync(path.join(os.tmpdir(), 'sc-prof-'));
  const args = ['--headless=new', '--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox', '--mute-audio', `--user-data-dir=${prof}`, `--remote-debugging-port=${dbg}`, `--window-size=${opts.w},${opts.h}`, ...(opts.extraArgs || []), 'about:blank'];
  const chrome = spawn(chromePath(), args, { stdio: 'ignore' });
  const errs = [], pend = new Map(); let ws, id = 0; const handlers = [];
  const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pend.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = async (expr, quiet) => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) { if (!quiet) errs.push('eval: ' + ((r.exceptionDetails.exception && r.exceptionDetails.exception.description) || r.exceptionDetails.text).slice(0, 240)); return null; } return r.result.value; };
  let list; for (let k = 0; k < 60; k++) { try { list = await (await fetch(`http://127.0.0.1:${dbg}/json`)).json(); if (list.some(t => t.type === 'page')) break; } catch (e) { } await sleep(400); }
  ws = new WebSocket(list.find(t => t.type === 'page').webSocketDebuggerUrl); await new Promise(r => ws.onopen = r);
  ws.onmessage = (m) => { const d = JSON.parse(m.data);
    if (d.method === 'Runtime.exceptionThrown') errs.push(String((d.params.exceptionDetails.exception && d.params.exceptionDetails.exception.description) || d.params.exceptionDetails.text).slice(0, 300));
    if (d.method === 'Runtime.consoleAPICalled' && d.params.type === 'error') errs.push('console.error: ' + d.params.args.map(a => a.value || a.description).join(' ').slice(0, 300));
    for (const h of handlers) h(d);
    if (d.id && pend.has(d.id)) { const p = pend.get(d.id); pend.delete(d.id); d.error ? p.rej(new Error(JSON.stringify(d.error))) : p.res(d.result); } };
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: opts.w, height: opts.h, deviceScaleFactor: opts.dpr || 1, mobile: !!opts.mobile });
  if (opts.mobile) await send('Emulation.setTouchEmulationEnabled', { enabled: true });
  const shot = async (file) => { const r = await send('Page.captureScreenshot', { format: 'png' }); const buf = Buffer.from(r.data, 'base64'); if (file) fs.writeFileSync(file, buf); return buf; };
  const tap = async (x, y, touch = true) => { if (touch) { await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y, id: 1 }] }); await sleep(60); await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] }); } else { await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 }); await sleep(40); await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 }); } };
  let closed = false;
  const close = async () => { if (closed) return; closed = true; try { ws.close(); } catch (e) { } try { spawnSync('taskkill', ['/PID', String(chrome.pid), '/T', '/F'], { stdio: 'ignore' }); } catch (e) { } try { chrome.kill(); } catch (e) { } await sleep(700); try { fs.rmSync(prof, { recursive: true, force: true }); } catch (e) { } };
  return { send, ev, shot, tap, errs, close, pid: chrome.pid, on: (h) => handlers.push(h) };
}

// load the game and wait for the loading card to finish; retries once on a failed start
export async function loadGame(b, url, tries = 2) {
  for (let t = 0; t < tries; t++) {
    await b.send('Page.navigate', { url });
    for (let k = 0; k < 80; k++) { await sleep(1500); if (await b.ev("!!(document.getElementById('loading')&&document.getElementById('loading').classList.contains('done'))", true)) { await sleep(1200); return true; } const m = await b.ev("(document.getElementById('loadMsg')||{}).textContent||''", true); if (/could not start/.test(m || '')) break; }
  }
  return false;
}
export const clickText = (sel, txt) => `(()=>{const b=[...document.querySelectorAll('${sel}')].find(b=>b.textContent.trim().toLowerCase().startsWith('${txt.toLowerCase()}')&&!b.hidden); if(b){b.click(); return 'ok'} return 'nobtn:${txt}'})()`;
export const PROFILES = {
  portrait: { name: 'portrait', ed: 'phone', w: 390, h: 844, mobile: true, dpr: 1 },
  landscape: { name: 'landscape', ed: 'phone', w: 844, h: 390, mobile: true, dpr: 1 },
  desktop: { name: 'desktop', ed: 'desktop', w: 1400, h: 860, mobile: false, dpr: 1 },
};
