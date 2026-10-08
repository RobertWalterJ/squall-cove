// Screenshot + measure sweep of every screen. usage: node qa/shoot.mjs [portrait|landscape|desktop|all] [outDir=qa/shots]
// One headless Chrome at a time. Writes <profile>_NN_<state>.png and report.json (overlaps, small targets, clipped, extra modals).
import fs from 'fs'; import path from 'path';
import { ROOT, sleep, startServer, launch, loadGame, clickText, PROFILES } from './harness.mjs';
const which = process.argv[2] || 'all', out = path.resolve(process.argv[3] || path.join(ROOT, 'qa', 'shots'));
fs.mkdirSync(out, { recursive: true });
const measure = fs.readFileSync(path.join(ROOT, 'qa', 'measure-ui.js'), 'utf8');
const NOISE = /loadMsg|fpHint/;

export async function sweep(P, base, outDir, opts = {}) {
  const b = await launch(P); const rep = { profile: P.name, states: [], fails: [] };
  try {
    const ok = await loadGame(b, `${base}index.html?map=port&nointro=1&gov=best&edition=${P.ed}`);
    if (!ok) { rep.fails.push('game did not load'); return rep; }
    await b.ev("(document.getElementById('help')||{}).hidden=true;1", true);
    const phone = P.ed === 'phone'; let n = 0;
    const snap = async (name, pre, wait = 900, o = {}) => {
      if (pre) await b.ev(pre); await sleep(wait);
      const file = path.join(outDir, `${P.name}_${String(++n).padStart(2, '0')}_${name}.png`);
      await b.shot(file); const m = await b.ev(measure) || {};
      const row = { name, file: path.basename(file), modal: m.modal, modals: m.modals, overlaps: (m.overlaps || []).filter(x => !NOISE.test(x)), small: phone ? m.small : [], clipped: phone ? m.clipped : [], covered: phone ? m.covered : [], hscroll: phone ? m.hscroll : false, tight: phone ? (m.tight || []) : [], note: o.note };
      if (phone && (m.modals || []).length > 1) row.multi = m.modals;
      rep.states.push(row); return row;
    };
    const E = (s) => b.ev(s);
    // ---- sandbox on the Port map
    await snap('sandbox', null, 600);
    await snap('sandbox_selected', "(()=>{const bo=__sc.boats[0]; if(bo){__sc.selectBoat(bo);} return 1})()", 900);
    await snap('sandbox_deselected', "(()=>{__sc.setSel&&__sc.setSel([]);const d=document.getElementById('bDesel'); if(d&&!d.hidden)d.click(); return 1})()", 500);
    await snap('menu', "document.getElementById('bMenu').click();1");
    await snap('menu_closed', "document.getElementById('menuSheet').hidden=true;1", 300);
    await snap('log', "document.getElementById('bLog').click();1", 700);
    await snap('log_closed', "(()=>{const l=document.getElementById('log'); if(l)l.hidden=true; const c=l&&l.querySelector('button'); return 1})()", 300);
    await snap('help', "document.getElementById('bHelp')?document.getElementById('bHelp').click():0;(document.getElementById('menuSheet')||{}).hidden=true; (document.getElementById('help')||{}).hidden=false;1", 700);
    await snap('help_closed', "(document.getElementById('help')||{}).hidden=true;1", 300);
    await snap('side_pane', "document.getElementById('bMore')&&document.getElementById('bMore').click();1", 800);
    await snap('side_closed', "(()=>{const c=document.getElementById('sClose'); c&&c.click(); return 1})()", 400);
    for (const t of ['place', 'land', 'sky']) await snap('tool_' + t, `(()=>{__sc.setTool('${t}'); return 1})()`, 900);
    await snap('tool_select', "(()=>{__sc.setTool('select'); return 1})()", 500);
    await snap('helm', "(()=>{const bo=__sc.boats[0]; __sc.selectBoat(bo); const m=document.getElementById('bMode'); if(m&&!m.hidden) m.click(); return __sc.mode})()", 1500);
    await snap('helm_left', "(()=>{if(__sc.mode==='helm') __sc.toggleMode(); __sc.setSel([]); return __sc.mode})()", 800);
    await snap('inspector', "(()=>{try{const d=__sc.addDevice({x:__sc.god.tgt.x,z:__sc.god.tgt.z,t:20,r:26}); const dv=__sc.devices[__sc.devices.length-1]; __sc.openInspector(dv); return !!dv}catch(e){return String(e)}})()", 900);
    await snap('inspector_closed', "(()=>{const i=document.getElementById('iClose'); i&&i.click(); return 1})()", 400);
    // ---- battle flow
    await snap('command_sandbox', '__sc.openCommand();1', 900);
    await snap('setup', "(()=>{document.getElementById('tablet').hidden=true; __sc.openBattleSetup(); return 1})()", 900);
    await snap('battle', clickText('#bSetup button', 'Begin battle'), 14000);
    for (const t of ['fire', 'map', 'support', 'points']) await snap('command_' + t, `(()=>{__sc.openCommand('${t}'); return 1})()`, 900);
    await snap('fire_armed', "(()=>{__sc.openCommand('fire'); const w=document.querySelector('#tablet .wrow'); if(w) w.click(); return !!w})()", 900);
    await snap('fire_cancelled', "(()=>{const c=document.getElementById('fireCancel'); if(c) c.click(); document.getElementById('tablet').hidden=true; return !!c})()", 500);
    await snap('tactical_map', "(()=>{document.getElementById('tablet').hidden=true; const t=document.getElementById('tmBtn'); if(t)t.click(); return 1})()", 1500);
    { const r = await b.ev("(()=>{const c=document.querySelector('#tmap canvas'); if(!c) return null; const r=c.getBoundingClientRect(); return [r.left+r.width*0.55, r.top+r.height*0.45]})()"); if (r) await b.tap(r[0], r[1], phone); }
    await snap('tactical_map_pick', null, 900);
    await snap('tactical_map_closed', "(()=>{const m=document.getElementById('tmap'); const x=m&&[...m.querySelectorAll('button')].find(q=>/back|close/i.test(q.textContent)); if(x)x.click(); return 1})()", 600);
    await snap('battle_overview', "(()=>{document.getElementById('tablet').hidden=true; return 1})()", 400);
    await snap('side_pick', "document.getElementById('bSideBtn').click();1", 900);
    await snap('side_pick_closed', "(()=>{const s=document.getElementById('bSpawn'); s.hidden=true; return 1})()", 300);
    await snap('fp', "(()=>{__sc.playBattle('blue'); return 1})()", 6000);
    if (phone) { await snap('fp_squad_ring', '(()=>{__sc.sqdWheelOpen(); return 1})()', 1200); await E('__sc.sqdWheelClose(false);1'); }
    await snap('fp_vehicle', "(()=>{try{const p=__sc.fp.p; const c=__sc.bvMake(Object.keys(__sc.BVSPEC)[0],'blue',p.x+3,p.z+3,0); if(!c) return 'nocar'; return __sc.bvEnter(c,c.seats[0])}catch(e){return String(e)}})()", 2500);
    await E("(()=>{try{__sc.bvLeaveKey()}catch(e){} return 1})()");
    await snap('fp_scoped', "(()=>{const z=document.getElementById('fpZoom'); z&&z.click(); return 1})()", 800); await E("(()=>{const z=document.getElementById('fpZoom'); z&&z.click(); return 1})()");
    await snap('fp_menu', "(()=>{const t=document.getElementById('fpTab'); t&&t.click(); return 1})()", 900);
    await E("(()=>{const t=document.getElementById('tablet'); t.hidden=true; return 1})()");
    await snap('deploy', "(()=>{__sc.hurt(__sc.fp.p,999,null,false); return 1})()", 3000);
    await snap('end', '(()=>{__sc.BATTLE.tickets.red=0; return 1})()', 4000);
    // ---- start menu (its own navigation)
    await b.send('Page.navigate', { url: `${base}index.html?menu=1&edition=${P.ed}` }); await sleep(5000);
    await snap('startmenu', null, 600);
    // the start menu must be the only thing on screen, and nothing behind it may be visible or pressable
    const leak = await b.ev(`(()=>{ const bt=document.getElementById('boot'); if(!bt||getComputedStyle(bt).display==='none') return ['start menu not shown']; const bad=[];
      for(let x=0.05;x<1;x+=0.18) for(let y=0.04;y<1;y+=0.12){ const el=document.elementFromPoint(innerWidth*x,innerHeight*y); if(el&&!bt.contains(el)) bad.push('point '+x.toFixed(2)+','+y.toFixed(2)+' is '+(el.id||el.tagName)); }
      for(const e of document.body.children){ if(e===bt||['SCRIPT','STYLE','LINK','svg','TITLE'].includes(e.tagName)) continue; const cs=getComputedStyle(e); if(cs.display!=='none'&&cs.visibility!=='hidden'&&e.getBoundingClientRect().width>0&&cs.pointerEvents!=='none') bad.push('visible outside menu: '+(e.id||e.tagName)); }
      const ver=document.getElementById('bVer'); if(!ver||!bt.contains(ver)) bad.push('version label not inside the menu'); return bad; })()`);
    if (leak && leak.length) rep.fails.push('start menu: ' + leak.slice(0, 4).join(' | '));
    await snap('startmenu_scrolled', "(()=>{const w=document.getElementById('boot'); w.scrollTop=99999; return 1})()", 500);
  } catch (e) { rep.fails.push('harness: ' + (e.stack || e)); }
  for (const e of b.errs) rep.fails.push('page error: ' + e);
  await b.close(); return rep;
}

// the list of things that fail a release for one profile (desktop only fails on page errors and a leaking start menu: its screens are not measured for targets)
export function report(rep) {
  const bad = []; const phone = rep.profile !== 'desktop';
  for (const s of rep.states) { if (!phone) continue; for (const x of s.overlaps) bad.push(`${s.name}: overlap ${x}`); for (const x of s.small) bad.push(`${s.name}: target under 48 px ${x}`); for (const x of s.clipped) bad.push(`${s.name}: cut off by the screen edge ${x}`); for (const x of s.covered) bad.push(`${s.name}: covered ${x}`); if (s.multi) bad.push(`${s.name}: ${s.multi.length} modals open at once (${s.multi.join(', ')})`); if (s.hscroll) bad.push(`${s.name}: sideways page scroll`); }
  for (const f of rep.fails) bad.push(f); return bad;
}
if (import.meta.url.endsWith(process.argv[1].replace(/\\/g, '/').split('/').pop())) {
  const srv = await startServer(); const base = `http://127.0.0.1:${srv.port}/`; const all = [];
  for (const k of Object.keys(PROFILES)) { if (which !== 'all' && which !== k) continue; const r = await sweep(PROFILES[k], base, out); all.push(r);
    console.log(`\n== ${r.profile}`); for (const s of r.states) { const bad = s.overlaps.length + s.small.length + s.clipped.length + s.covered.length + (s.multi ? 1 : 0) + (s.hscroll ? 1 : 0);
      console.log(`  ${s.name.padEnd(22)} modal=${String(s.modal).padEnd(10)} ${bad ? 'ISSUES ' + bad : 'ok'}`);
      for (const x of s.overlaps.slice(0, 4)) console.log('     overlap ' + x); for (const x of s.small.slice(0, 6)) console.log('     small   ' + x); for (const x of s.clipped.slice(0, 4)) console.log('     clipped ' + x); for (const x of s.covered.slice(0, 4)) console.log('     covered ' + x); if (s.multi) console.log('     modals  ' + s.multi.join(',')); if (s.hscroll) console.log('     hscroll'); for (const x of (s.tight||[]).slice(0, 4)) console.log('     gap<8   ' + x); }
    for (const f of r.fails) console.log('  FAIL ' + f); }
  fs.writeFileSync(path.join(out, `report_${which}.json`), JSON.stringify(all, null, 1)); await srv.close(); process.exit(0);
}
