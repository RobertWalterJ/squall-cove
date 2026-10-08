// Start-menu maps check. usage: node qa/menu-maps-check.mjs shots   -> screenshots of the start menu (desktop 1400x860, phone portrait, phone landscape) into qa/shots/menu_*.png
//                           node qa/menu-maps-check.mjs load [ids]  -> picks each map in the menu, presses Start, and checks the terrain type, a non-flat height field and no console errors (desktop edition)
// One headless Chrome at a time (qa/harness.mjs).
import fs from 'fs'; import path from 'path';
import { ROOT, sleep, startServer, launch, PROFILES } from './harness.mjs';
const what = process.argv[2] || 'shots', srv = await startServer(), base = `http://127.0.0.1:${srv.port}/`, fail = [];
const out = path.join(ROOT, 'qa', 'shots'); fs.mkdirSync(out, { recursive: true });
setTimeout(() => { console.log('ERR watchdog'); process.exit(2); }, 1500000).unref();
try {
  if (what === 'shots') {
    for (const P of [PROFILES.desktop, PROFILES.portrait, PROFILES.landscape]) {
      const b = await launch(P);
      try {
        await b.send('Page.navigate', { url: `${base}index.html?menu=1&edition=${P.ed}` }); await sleep(6000);
        const m = await b.ev(`(()=>{ const r = (s) => { const e = document.querySelector(s); if (!e) return null; const q = e.getBoundingClientRect(); return [Math.round(q.top), Math.round(q.bottom)] };
          const vis = [...document.querySelectorAll('#bMaps .bmap,#bMaps .bgrp')].filter(e => !e.hidden).map(e => (e.dataset.map || e.textContent) + '@' + Math.round(e.getBoundingClientRect().top)); 
          return JSON.stringify({ vh: innerHeight, go: r('#bGo'), vis, hscroll: document.documentElement.scrollWidth > innerWidth }) })()`);
        const o = JSON.parse(m); console.log(P.name, JSON.stringify(o));
        if (o.go && o.go[1] > o.vh + 1) fail.push(P.name + ': the Start button is below the fold'); if (o.hscroll) fail.push(P.name + ': horizontal scroll');
        await b.shot(path.join(out, `menu_${P.name}.png`));
      } finally { await b.close(); }
    }
  } else {
    const ids = (process.argv[3] ? process.argv[3].split(',') : ['cove', 'cove_large', 'archipelago', 'atoll', 'fjord', 'volcanic', 'valley', 'barrier', 'port', 'urban', 'desert', 'lemnos_myrina', 'lemnos_mudros', 'lemnos_airport']);
    for (const id of ids) {
      const b = await launch(PROFILES.desktop); let res = 'ERR';
      try {
        await b.ev("localStorage.clear();1", true);
        await b.send('Page.navigate', { url: `${base}index.html?menu=1&edition=desktop` }); await sleep(5000);
        const pick = await b.ev(`(()=>{ const e = document.querySelector('#bMaps .bmap[data-map="${id}"]'); if (!e || e.hidden) return 'missing'; e.click(); const so = document.querySelector('#bOpts [data-opt="sound"]'); if (so && so.getAttribute('aria-pressed') === 'true') so.click(); const g = document.getElementById('bGo'); const lbl = g.textContent; g.click(); return lbl })()`);
        let done = false; for (let k = 0; k < 100 && !done; k++) { await sleep(2000); done = await b.ev("!!(document.getElementById('loading')&&document.getElementById('loading').classList.contains('done'))", true); }
        const info = done ? JSON.parse(await b.ev(`(()=>{ const S = __sc; let mn = 1e9, mx = -1e9, n = 0, wet = 0; for (let x = -200; x <= 200; x += 25) for (let z = -200; z <= 200; z += 25) { const h = S.heightAt(x, z); mn = Math.min(mn, h); mx = Math.max(mx, h); n++; if (h < 0) wet++; } return JSON.stringify({ t: S.MAP.t, mn: +mn.toFixed(1), mx: +mx.toFixed(1), wetPct: Math.round(100 * wet / n) }) })()`)) : null;
        const ok = pick !== 'missing' && done && info && info.t === (id === 'cove_large' ? 'cove' : id) && info.mx - info.mn > 3 && b.errs.length === 0;
        res = (ok ? 'OK   ' : 'FAIL ') + id + ' ' + JSON.stringify(info) + (b.errs.length ? ' errors: ' + b.errs.slice(0, 2).join(' / ') : '') + (pick === 'missing' ? ' (no card)' : ''); if (!ok) fail.push(id);
      } catch (e) { res = 'FAIL ' + id + ' ' + e.message; fail.push(id); } finally { await b.close(); }
      console.log(res);
    }
  }
  console.log(fail.length ? 'FAIL: ' + fail.join(', ') : 'ok');
} catch (e) { console.log('ERR', e.message); fail.push(e.message); } finally { await srv.close(); }
process.exit(fail.length ? 1 : 0);
