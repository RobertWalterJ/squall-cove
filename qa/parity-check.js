#!/usr/bin/env node
// Squall Cove parity guard: ONE command that runs every release check (rule 6 in EDITION-RULES.md, section 6.4 in MOBILE-UX-PLAN.md).
//   node qa/parity-check.js                 everything below (about 25 minutes with the software renderer; one headless Chrome at a time)
//   node qa/parity-check.js --quick         skip the full screen sweep (static checks, feature matrix, desktop goldens, console)
//   node qa/parity-check.js --update-goldens   rewrite the desktop golden images (then say so in QA-LOG.md)
// Steps:
//   1. static: CSS scope + stacking lint (qa/css-lint.mjs), service worker rules, version strings agree
//   2. feature matrix (qa/parity-matrix.json): every key binding and every control in the code is in the table; every phone control exists in the phone edition
//      and every desktop control in the desktop edition; anything the phone omits is a recorded choice with a reason
//   3. desktop regression: five golden screens at 1400x860 compared with a tolerance (the 3D view is hidden so only the interface is compared)
//   4. console clean in both editions
//   5. full sweep (unless --quick): every screen at 390x844, 844x390 and 1400x860 through qa/measure-ui.js (overlaps, targets under 48 px, clipped text,
//      two modals at once, controls covered by something, sideways scroll), screenshots saved to qa/shots/
const fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..'), argv = process.argv.slice(2);
const QUICK = argv.includes('--quick'), UPDATE = argv.includes('--update-goldens');
const GOLD = path.join(ROOT, 'qa', 'golden'), TOL_PIXELS = 0.005, TOL_CHANNEL = 28;
const results = []; const fail = (area, msg) => results.push({ ok: false, area, msg }); const pass = (area, msg) => results.push({ ok: true, area, msg });

function staticChecks(css) {
  const r = css.lint(); for (const e of r.errors) fail('css', e); for (const w of r.warns) console.log('  warn ' + w); if (!r.errors.length) pass('css', `scope and ladder lint ok (${r.rules} rules, ${r.defined.length} z tokens)`);
  const sw = fs.readFileSync(path.join(ROOT, 'sw.js'), 'utf8'), html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  const need = [[/const MINE = \/\^squall-cove-\(v\[\\d\.\]\+\|assets-a\[\\d\.\]\+\)\$\//, 'MINE regex is exact (only squall-cove-* caches are touched)'], [/caches\.open\(isAsset/, 'cache lookups go through caches.open, never global caches.match']];
  for (const [re, what] of need) re.test(sw) ? pass('sw', what) : fail('sw', 'sw.js: ' + what + ' is not true any more');
  if (/[^.\w]caches\.match\(/.test(sw)) fail('sw', 'sw.js calls global caches.match()'); if (!/manifest\.webmanifest'\)\) return/.test(sw)) fail('sw', 'sw.js must never cache manifest.webmanifest');
  const v = (/const VERSION = 'v([\d.]+)'/.exec(sw) || [])[1]; const shown = (/'v([\d.]+) ' \+ ED\.id/.exec(html) || [])[1];
  if (!v || !shown) fail('sw', 'cannot read the version strings'); else if (!v.startsWith(shown)) fail('sw', `sw.js VERSION v${v} and the on-screen version v${shown} disagree (bump both)`); else pass('sw', `VERSION v${v} matches the on-screen v${shown}`);
  const man = JSON.parse(fs.readFileSync(path.join(ROOT, 'manifest.webmanifest'), 'utf8')), pin = JSON.parse(fs.readFileSync(path.join(ROOT, 'qa', 'parity-matrix.json'), 'utf8')).manifestPin; for (const k of Object.keys(pin)) if (man[k] !== pin[k]) fail('sw', `manifest ${k} changed from ${pin[k]} to ${man[k]}: Robert must uninstall and reinstall (EDITION-RULES.md rule 8)`); if (man.id !== undefined && man.id !== '/squall-cove/') fail('sw', `manifest id is ${man.id}: it must be unique to this app (/squall-cove/), never the origin root`); if (!results.some(r => !r.ok && r.msg.startsWith('manifest'))) pass('sw', 'manifest id, scope and start_url unchanged');
  for (const k of [...html.matchAll(/localStorage\.(?:get|set)Item\('([^']+)'/g)].map(m => m[1])) if (!/^(squall-cove|sc-)/.test(k)) fail('storage', `localStorage key without the squall-cove prefix: ${k}`);
}

async function main() {
  const H = await import('./harness.mjs'); const css = await import('./css-lint.mjs'); const shoot = await import('./shoot.mjs'); const meas = fs.readFileSync(path.join(ROOT, 'qa', 'measure-ui.js'), 'utf8');
  staticChecks(css);
  const srv = await H.startServer(); const base = `http://127.0.0.1:${srv.port}/`; const matrix = JSON.parse(fs.readFileSync(path.join(ROOT, 'qa', 'parity-matrix.json'), 'utf8'));
  const inv = {};
  // ---- 2 + 4: feature matrix and console, one load per edition
  for (const key of ['desktop', 'portrait']) {
    const P = H.PROFILES[key], b = await H.launch(P);
    try {
      if (!(await H.loadGame(b, `${base}index.html?map=port&nointro=1&edition=${P.ed}`))) { fail('load', `${P.ed}: the game did not start`); continue; }
      await b.ev("(document.getElementById('help')||{}).hidden=true;1", true);
      inv[P.ed] = await b.ev(`(()=>{ const q=(s)=>[...document.querySelectorAll(s)]; return { keys:(window.__sc.KEYMAP||[]).map(r=>r[0]+'|'+r[1]), ids:q('button[id], [role=button][id]').map(e=>e.id), has:{} }; })()`);
      // controls that only exist after a state change are checked by their own "show" step
      for (const c of matrix.capabilities) {
        const side = P.ed === 'phone' ? 'phone' : 'desktop', spec = c[side];
        const omit = typeof c[side + 'Omit'] === 'string' ? c[side + 'Omit'] : (side === 'phone' && typeof c.desktopOnly === 'string') ? c.desktopOnly : (side === 'desktop' && typeof c.phoneOnly === 'string') ? c.phoneOnly : null;
        if (omit !== null) { if (omit.length < 6) fail('matrix', `${c.id}: omitted on ${side} without a reason`); continue; }
        if (!spec) { fail('matrix', `${c.id}: no ${side} control and no reason (add ${side}Omit with a reason, or a control)`); continue; }
        if (spec.show) await b.ev(spec.show, true);
        if (spec.sel) for (const one of String(spec.sel).split(',').map(x => x.trim()).filter(Boolean)) {
          const found = await b.ev(`(()=>{ const e=document.querySelector(${JSON.stringify(one)}); if(!e) return 'missing'; const r=e.getBoundingClientRect(); const cs=getComputedStyle(e); const vis=!e.hidden&&cs.display!=='none'&&r.width>0&&r.height>0; return vis?'visible:'+Math.round(Math.min(r.width,r.height)):'hidden'; })()`);
          if (found === 'missing') fail('matrix', `${c.id}: ${side} control ${one} does not exist`);
          else if (spec.visible && !/^visible/.test(found)) fail('matrix', `${c.id}: ${side} control ${one} is ${found} but should be visible`);
          else if (side === 'phone' && spec.visible && +found.split(':')[1] < 48) fail('matrix', `${c.id}: phone control ${one} is ${found.split(':')[1]} px, under 48`);
        } else if (!spec.gesture || !/[A-Za-z]{3,}/.test(spec.gesture)) fail('matrix', `${c.id}: ${side} needs a selector or a gesture in words`);
        if (spec.after) await b.ev(spec.after, true);
      }
      const errs = b.errs.filter(e => !/Failed to load resource|favicon/.test(e)); if (errs.length) for (const e of errs.slice(0, 5)) fail('console', `${P.ed}: ${e}`); else pass('console', `${P.ed}: no console errors after load`);
      if (P.ed === 'desktop') await goldens(b, H, base, meas);
    } catch (e) { fail('harness', `${P.ed}: ${e.stack || e}`); }
    await b.close();
  }
  // every key binding and every control in the code is in the table
  const covered = new Set(), sels = new Set(); for (const c of matrix.capabilities) { for (const k of c.covers || []) covered.add(k); for (const s of ['desktop', 'phone']) if (c[s] && c[s].sel) for (const q of String(c[s].sel).split(',')) { const m = /^#([\w-]+)/.exec(q.trim()); if (m) sels.add(m[1]); } }
  const ign = matrix.ignoreKeys || {}, ignC = matrix.ignoreControls || {};
  for (const ed of Object.keys(inv)) {
    for (const k of inv[ed].keys) if (!covered.has(k) && !(k in ign)) fail('matrix', `key binding not in the matrix: "${k}" (add it to a capability's covers, or to ignoreKeys with a reason)`);
    for (const id of inv[ed].ids) if (!sels.has(id) && !ignC[id] && !(matrix.ignorePrefixes || []).some(p => id.startsWith(p.prefix))) fail('matrix', `${ed}: control #${id} is not in the matrix (add a capability, or ignoreControls with a reason)`);
  }
  for (const k of Object.keys(ign)) if (typeof ign[k] !== 'string' || ign[k].length < 6) fail('matrix', `ignoreKeys "${k}" needs a reason`);
  if (!results.some(r => !r.ok && r.area === 'matrix')) pass('matrix', `${matrix.capabilities.length} capabilities: every key and control is accounted for, every phone omission has a reason`);
  await srv.close();
  for (const [label, file, what] of [['service worker', 'sw-check.mjs', 'migration, other apps untouched, no asset re-fetch, offline'], ['phone features', 'phone-features-check.mjs', 'one modal, Back, wake lock, haptics, tilt, helicopter, lost graphics, hint, governor']]) {
    const r = require('child_process').spawnSync(process.execPath, [path.join(ROOT, 'qa', file)], { encoding: 'utf8', maxBuffer: 1 << 26 }); const lines = (r.stdout || '').split(String.fromCharCode(10)).filter(l => /^  (ok|FAIL)/.test(l));
    if (r.status === 0) pass(label, `real Chrome: ${lines.length} checks ok (${what})`); else { for (const l of lines.filter(l => /FAIL/.test(l))) fail(label, l.replace(/^\s*FAIL\s*/, '')); if (!lines.some(l => /FAIL/.test(l))) fail(label, `${file} exited ${r.status} ${(r.stderr || '').slice(0, 200)}`); }
  }
  // ---- 5: the full sweep
  if (!QUICK) {
    const srv2 = await H.startServer(); const b2 = `http://127.0.0.1:${srv2.port}/`; fs.mkdirSync(path.join(ROOT, 'qa', 'shots'), { recursive: true });
    for (const k of ['portrait', 'landscape', 'desktop']) { const rep = await shoot.sweep(H.PROFILES[k], b2, path.join(ROOT, 'qa', 'shots')); const bad = shoot.report(rep); for (const f of bad) fail('sweep:' + k, f); if (!bad.length) pass('sweep:' + k, `${rep.states.length} screens clean`); }
    await srv2.close();
  }
  console.log('\n== parity-check');
  for (const r of results) console.log((r.ok ? '  ok   ' : '  FAIL ') + r.area.padEnd(14) + r.msg);
  const bad = results.filter(r => !r.ok).length; console.log(bad ? `\nparity-check: ${bad} failure(s)` : '\nparity-check: all green'); process.exit(bad ? 1 : 0);
}

// golden screens: the 3D view and anything that moves on its own are hidden, then the page is compared with the stored image
async function goldens(b, H, base, meas) {
  fs.mkdirSync(GOLD, { recursive: true });
  const hide = "(()=>{let s=document.getElementById('goldenMask'); if(!s){s=document.createElement('style'); s.id='goldenMask'; s.textContent='canvas,.inst,#feedCol,#notes,#killFeed,#sideFeed,#logN,#bTip,#loading,#sBody,#rose,.xh,#fpHint,#fpPrompt,#sqHud,#sqMarks,.ico-live{visibility:hidden!important} *{animation:none!important;transition:none!important;caret-color:transparent!important} body{background:#0c1a20!important}'; document.head.appendChild(s);} return 1})()";
  const steps = [
    ['overview', "(()=>{__sc.setSel([]); document.getElementById('menuSheet').hidden=true; const t=document.getElementById('tablet'); if(t) t.hidden=true; return 1})()"],
    ['command', "(()=>{__sc.openCommand('fire'); return 1})()"],
    ['setup', "(()=>{document.getElementById('tablet').hidden=true; __sc.openBattleSetup(); return 1})()"],
    ['menu', "(()=>{document.getElementById('bSetup').hidden=true; document.getElementById('bMenu').click(); return 1})()"],
    ['firstperson', "(()=>{document.getElementById('menuSheet').hidden=true; __sc.enterFP(__sc.people[0]); return 1})()"],
  ];
  const compare = async (name, buf) => {
    const file = path.join(GOLD, `desktop_${name}.png`);
    if (UPDATE || !fs.existsSync(file)) { fs.writeFileSync(file, buf); pass('golden', `${name}: ${UPDATE ? 'golden updated' : 'golden created (first run)'}`); return; }
    const gold = fs.readFileSync(file).toString('base64'), now = buf.toString('base64');
    const d = await b.ev(`(async()=>{ const load=(b64)=>new Promise((res,rej)=>{const i=new Image(); i.onload=()=>res(i); i.onerror=rej; i.src='data:image/png;base64,'+b64;}); const [a,c]=await Promise.all([load(${JSON.stringify(gold)}), load(${JSON.stringify(now)})]); if(a.width!==c.width||a.height!==c.height) return {size:true}; const k=(im)=>{const cv=document.createElement('canvas'); cv.width=im.width; cv.height=im.height; const x=cv.getContext('2d'); x.drawImage(im,0,0); return x.getImageData(0,0,im.width,im.height).data}; const A=k(a), B=k(c); let n=0; for(let i=0;i<A.length;i+=4){ if(Math.max(Math.abs(A[i]-B[i]),Math.abs(A[i+1]-B[i+1]),Math.abs(A[i+2]-B[i+2]))>${TOL_CHANNEL}) n++; } return {frac:n/(A.length/4)}; })()`);
    const nf = path.join(GOLD, `desktop_${name}.new.png`);
    if (!d || d.size) { fail('golden', `${name}: size differs from the golden`); fs.writeFileSync(nf, buf); }
    else if (d.frac > TOL_PIXELS) { fail('golden', `${name}: ${(d.frac * 100).toFixed(2)} percent of pixels differ (limit ${(TOL_PIXELS * 100).toFixed(1)}). If the change is intended run --update-goldens and note "golden updated" in QA-LOG.md. New image: qa/golden/desktop_${name}.new.png`); fs.writeFileSync(nf, buf); }
    else { pass('golden', `${name}: ${(d.frac * 100).toFixed(3)} percent differ`); try { fs.rmSync(nf); } catch (e) { } }
  };
  await b.ev(hide, true);
  for (const [name, pre] of steps) { await b.ev(pre, true); await H.sleep(900); await b.ev(hide, true); await compare(name, await b.shot(null)); }
  // the start menu is its own page
  await b.send('Page.navigate', { url: `${base}index.html?menu=1&edition=desktop` }); await H.sleep(5000);
  await b.ev("(()=>{let s=document.getElementById('goldenMask'); if(!s){s=document.createElement('style'); s.id='goldenMask'; s.textContent='#bVer{visibility:hidden!important} *{animation:none!important;transition:none!important}'; document.head.appendChild(s);} return 1})()", true); await H.sleep(400);
  await compare('startmenu', await b.shot(null));
}
main().catch(e => { console.error(e); process.exit(2); });
