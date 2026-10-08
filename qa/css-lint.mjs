// CSS scope and stacking lint for index.html (rules 1 and 4 in EDITION-RULES.md). Static, no browser needed.
//  1. A rule that styles a phone-only control (the phone stack, selection bar, touch buttons, ...) must live under .ed-phone or body.touch,
//     unless its selector is on the baseline list in qa/css-scope-allow.json (shared base rules, each with a reason).
//  2. env(safe-area ...) outside :root, the start menu and the baseline list is flagged: use the --safe-* tokens.
//  3. Every z-index of 3 or more must be a --z-* token, and every token used must be defined in :root.
//  4. backdrop-filter may not reach the phone: an unscoped use needs a body.ed-phone override.
// usage: node qa/css-lint.mjs [--update-baseline]      (also called by qa/parity-check.js)
import fs from 'fs'; import path from 'path'; import { ROOT } from './harness.mjs';
const PHONE_MARKERS = ['#phoneStack', '#selBar', '#cmdRow', '#orientHint', 'modal-open', '#fpHUp', '#fpHDn', '#fpHL', '#fpHR', '#fpReload', '#fpZoom', '#fpSquad', '#fpStance', '#fpJump', '#fpUse', '#fpStick', '#fpLook', '#fpKnob', '#sqWheel', '.fpBtns', '#fpTab', '.fpTop'];
const SCOPES = ['.ed-phone', '.touch', 'ed-phone'];
export function lint() {
  const html = fs.readFileSync(process.env.LINT_HTML || path.join(ROOT, 'index.html'), 'utf8'); const allowF = path.join(ROOT, 'qa', 'css-scope-allow.json');
  const allow = fs.existsSync(allowF) ? JSON.parse(fs.readFileSync(allowF, 'utf8')) : { selectors: {}, env: {} };
  const errors = [], warns = [], seen = { selectors: {}, env: {} };
  const blocks = [...html.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map(m => m[1]);
  // JS-injected stylesheets are plain strings too
  for (const m of html.matchAll(/st\.textContent\s*=\s*'((?:[^'\\]|\\.)*)'/g)) blocks.push(m[1]);
  const rules = [];
  for (const raw of blocks) {
    const css = raw.replace(/\/\*[\s\S]*?\*\//g, ''); let i = 0; const stack = [];
    const walk = (txt, at) => { let depth = 0, start = 0, pre = ''; for (let k = 0; k < txt.length; k++) { const c = txt[k]; if (c === '{') { if (depth === 0) { pre = txt.slice(start, k).trim(); start = k + 1; } depth++; } else if (c === '}') { depth--; if (depth === 0) { const body = txt.slice(start, k); if (pre.startsWith('@')) { if (/^@(media|supports|layer)/.test(pre)) walk(body, (at ? at + ' ' : '') + pre); } else rules.push({ sel: pre, body, at }); start = k + 1; pre = ''; } } } };
    walk(css, '');
  }
  const scoped = (sel) => SCOPES.some(s => sel.includes(s));
  for (const r of rules) {
    const sels = r.sel.split(/,(?![^(]*\))/).map(s => s.trim()).filter(Boolean);
    for (const sel of sels) {
      const marks = PHONE_MARKERS.filter(m => sel.includes(m));
      if (marks.length && !scoped(sel)) { const hidden = /^\s*display:\s*none\s*(!important)?\s*;?\s*$/.test(r.body); const key = sel; if (!hidden) { seen.selectors[key] = 1; if (!(key in (allow.selectors || {}))) errors.push(`phone control styled outside .ed-phone / .touch: "${sel}"  { ${r.body.trim().slice(0, 70)}... }`); } }
    }
    if (/env\(safe-area/.test(r.body) && !r.sel.split(',').every(s => scoped(s.trim()) || /^(:root|html|body|#boot)/.test(s.trim()) || /#boot/.test(s))) { const key = r.sel.trim(); seen.env[key] = 1; if (!(key in (allow.env || {}))) errors.push(`env(safe-area) outside a phone scope: "${r.sel.trim().slice(0, 80)}" (use the --safe-* tokens)`); }
    for (const m of r.body.matchAll(/z-index:\s*([^;}]+)/g)) { const v = m[1].trim(); if (/^var\(--z-[a-z-]+\)$/.test(v) || /^calc\(var\(--z-[a-z-]+\)\s*[+-]\s*\d+\)$/.test(v)) continue; if (v === 'auto') continue; const n = parseFloat(v); if (!isNaN(n) && Math.abs(n) <= 2) continue; errors.push(`z-index not on the ladder: "${r.sel.trim().slice(0, 60)}" z-index:${v}`); }
    if (/backdrop-filter\s*:\s*(?!none)/.test(r.body) && !scoped(r.sel)) seen.bf = (seen.bf || []).concat(r.sel.trim());
  }
  const rootBody = (rules.find(r => r.sel.trim() === ':root' && /--z-sheet/.test(r.body)) || { body: '' }).body;
  const defined = new Set([...rootBody.matchAll(/--(z-[a-z-]+)\s*:/g)].map(m => m[1]));
  for (const m of html.matchAll(/var\(--(z-[a-z-]+)\)/g)) if (!defined.has(m[1])) errors.push(`z token --${m[1]} is used but not defined in :root`);
  if (seen.bf && seen.bf.length) { const override = rules.some(r => scoped(r.sel) && /backdrop-filter\s*:\s*none/.test(r.body)); if (!override) errors.push('backdrop-filter used on shared rules (' + seen.bf.slice(0, 3).join(' | ') + ') with no body.ed-phone override'); }
  // anything allow-listed that no longer exists is stale
  for (const k of Object.keys(allow.selectors || {})) if (!seen.selectors[k]) warns.push(`stale baseline entry (selector no longer found): ${k}`);
  return { errors, warns, seen, rules: rules.length, defined: [...defined] };
}
if (import.meta.url.endsWith(process.argv[1].replace(/\\/g, '/').split('/').pop())) {
  const r = lint(); const upd = process.argv.includes('--update-baseline');
  if (upd) { const allowF = path.join(ROOT, 'qa', 'css-scope-allow.json'); const old = fs.existsSync(allowF) ? JSON.parse(fs.readFileSync(allowF, 'utf8')) : { selectors: {}, env: {} }; const out = { _note: 'Shared base rules that style a phone control without a phone scope. Each is a default or hidden-on-desktop rule that the phone overrides under body.ed-phone / body.touch. Add a reason for every entry.', selectors: {}, env: {} }; for (const k of Object.keys(r.seen.selectors)) out.selectors[k] = old.selectors[k] || 'shared base rule (hidden or neutral on desktop; phone overrides it under .ed-phone / .touch)'; for (const k of Object.keys(r.seen.env)) out.env[k] = old.env[k] || 'safe-area token definition or boot menu'; fs.writeFileSync(allowF, JSON.stringify(out, null, 1)); console.log('baseline written: ' + Object.keys(out.selectors).length + ' selectors, ' + Object.keys(out.env).length + ' env rules'); }
  console.log(`css-lint: ${r.rules} rules, ${r.defined.length} z tokens`); for (const w of r.warns) console.log('  warn ' + w); for (const e of r.errors) console.log('  FAIL ' + e); console.log(r.errors.length ? `css-lint: ${r.errors.length} problem(s)` : 'css-lint: ok'); process.exit(r.errors.length && !upd ? 1 : 0);
}
