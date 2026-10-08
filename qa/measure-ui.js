(() => {
  // UI measure for one on-screen state. Evaluated inside the page. Returns {modal, modals, n, overlaps, small, clipped, hscroll, covered}.
  // overlaps : two visible boxes overlap by more than 6 px each way (within the top modal if one is open)
  // small    : visible interactive boxes under 48 px on the short side (phone edition rule)
  // clipped  : visible text/controls cut off by the screen edge
  // modals   : every full surface that is open at once (the ladder allows one)
  // covered  : a visible control that is not the topmost thing at its own centre (something sits on it)
  const MODAL_IDS = ['intro', 'help', 'menuSheet', 'bSetup', 'tablet', 'bSpawn', 'log', 'people', 'fleet', 'cheatSheet', 'tmap', 'inspector', 'bOver', 'side'];
  const els = MODAL_IDS.map(i => document.getElementById(i)).filter(Boolean);
  const shown = (m) => { const r = m.getBoundingClientRect(); const cs = getComputedStyle(m); return !m.hidden && cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 120 && r.height > 120 && r.right > 0 && r.left < innerWidth && r.bottom > 0 && r.top < innerHeight; };
  const open = els.filter(shown);
  const topmost = open.length ? open.slice().sort((a, b) => (+getComputedStyle(b).zIndex || 0) - (+getComputedStyle(a).zIndex || 0))[0] : null;
  const root = topmost || document.body;
  const vis = (e) => { const r = e.getBoundingClientRect(); if (r.width < 6 || r.height < 6) return null; const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity < 0.05) return null; if (r.right <= 0 || r.bottom <= 0 || r.left >= innerWidth || r.top >= innerHeight) return null; for (let p = e; p && p !== document.body; p = p.parentElement) { if (p.hidden || getComputedStyle(p).display === 'none') return null; } return r; };
  const items = [];
  for (const e of root.querySelectorAll('*')) {
    if (e.closest && e.closest('#sqMarks')) continue;
    if (['CANVAS', 'svg', 'use', 'path', 'SCRIPT', 'STYLE'].includes(e.tagName)) continue;
    const cs = getComputedStyle(e); const leafText = e.children.length === 0 && e.textContent.trim().length > 0;
    const iact = ['BUTTON', 'INPUT', 'SELECT', 'A'].includes(e.tagName) || e.getAttribute('role') === 'button';
    const fixedBox = (cs.position === 'fixed' || cs.position === 'absolute') && (cs.backgroundColor !== 'rgba(0, 0, 0, 0)' || cs.borderTopWidth !== '0px');
    if (!(leafText || iact || fixedBox)) continue;
    let r = vis(e); if (!r) continue;
    if (cs.display === 'inline' && !iact) continue;          // words flowing inside a line are not boxes
    const raw = { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height };
    let L = r.left, T = r.top, R = r.right, B = r.bottom, inScroller = false;
    for (let q = e.parentElement; q && q !== document.body; q = q.parentElement) { const o = getComputedStyle(q); if (/(auto|scroll|hidden)/.test(o.overflowY + o.overflowX)) { const c = q.getBoundingClientRect(); if (q.scrollWidth > q.clientWidth + 2 || q.scrollHeight > q.clientHeight + 2) inScroller = true; L = Math.max(L, c.left); T = Math.max(T, c.top); R = Math.min(R, c.right); B = Math.min(B, c.bottom); } }
    if (R - L < 6 || B - T < 6) continue; r = { left: L, top: T, right: R, bottom: B, width: R - L, height: B - T };
    if (r.width > innerWidth * 0.95 && r.height > innerHeight * 0.95) continue;
    let st = false; for (let q = e; q && q !== document.body; q = q.parentElement) { if (getComputedStyle(q).position === 'sticky') { st = true; break; } }
    items.push({ e, r, raw, iact, leafText, inScroller, st, id: (e.id || (typeof e.className === 'string' ? e.className.split(' ')[0] : '') || e.tagName) + (leafText && !iact ? ':' + e.textContent.trim().slice(0, 14) : '') });
  }
  const box = (a) => '[' + Math.round(a.r.left) + ',' + Math.round(a.r.top) + ' ' + Math.round(a.r.width) + 'x' + Math.round(a.r.height) + ']';
  const overlaps = [];
  for (let i = 0; i < items.length; i++) for (let j = i + 1; j < items.length; j++) {
    const a = items[i], b = items[j]; if (a.e.contains(b.e) || b.e.contains(a.e) || a.st !== b.st) continue;
    const x = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left), y = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
    if (x > 6 && y > 6) overlaps.push(String(a.id).slice(0, 30) + ' ' + box(a) + ' x ' + String(b.id).slice(0, 30) + ' ' + box(b));
  }
  const small = items.filter(a => a.iact && !a.e.disabled && Math.min(a.raw.width, a.raw.height) < 47.5 && !(a.e.tagName === 'INPUT' && /range|checkbox|radio/.test(a.e.type) && a.r.height >= 24)).map(a => String(a.id).slice(0, 30) + ' ' + box(a));
  const clipped = items.filter(a => (a.leafText || a.iact) && !a.inScroller && (a.raw.left < -2 || a.raw.right > innerWidth + 2 || a.raw.top < -2 || a.raw.bottom > innerHeight + 2)).map(a => String(a.id).slice(0, 30) + ' ' + box(a));
  const covered = [];
  for (const a of items) { if (!a.iact || a.st || a.inScroller) continue; const cx = (a.r.left + a.r.right) / 2, cy = (a.r.top + a.r.bottom) / 2; const t = document.elementFromPoint(cx, cy); if (t && t !== a.e && !a.e.contains(t) && !t.contains(a.e)) { const cs = getComputedStyle(t); if (cs.pointerEvents !== 'none') covered.push(String(a.id).slice(0, 26) + ' under ' + (t.id || t.className || t.tagName).toString().slice(0, 26)); } }
  const tight = []; const btn = items.filter(a => a.iact && !a.inScroller && Math.min(a.r.width, a.r.height) >= 40);
  for (let i = 0; i < btn.length; i++) for (let j = i + 1; j < btn.length; j++) { const a = btn[i], b = btn[j]; if (a.e.contains(b.e) || b.e.contains(a.e)) continue;
    const ox = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left), oy = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
    const gx = -ox, gy = -oy; if ((oy > 12 && gx >= 0 && gx < 7.5) || (ox > 12 && gy >= 0 && gy < 7.5)) tight.push(String(a.id).slice(0, 22) + ' ' + box(a) + ' | ' + String(b.id).slice(0, 22) + ' ' + box(b) + ' gap ' + Math.round(Math.min(gx < 0 ? 99 : gx, gy < 0 ? 99 : gy))); }
  const names = (l) => l.map(m => m.id);
  return { modal: topmost ? topmost.id : null, modals: names(open), n: items.length, overlaps: overlaps.slice(0, 30), small: small.slice(0, 40), clipped: clipped.slice(0, 20), covered: covered.slice(0, 20), hscroll: document.documentElement.scrollWidth > innerWidth + 1, tight: tight.slice(0, 20) };
})()
