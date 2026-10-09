// Pose contact sheets for stance, crouch-walk, prone and crawl (v9.9.7). usage: node qa/stance-shots.mjs poses|drop|weapons [out.png]
// One screenshot per sheet, two panels (top and bottom) rendered with scissor into the same picture, soldiers in profile facing right. Simulated time only (window.__qaHold).
//   poses:   top flat ground: stand, crouch, crouch-walk, crouch-run, prone, crawl (two phases). bottom: the same lying and crouched poses on a slope.
//   drop:    top the drop to the ground in eight steps (stand, crouch, then 1.25 ... 2.0 of the way to prone). bottom: one crawl cycle in eight phases.
//   weapons: seven weapon classes lying (top) and crouched (bottom).
import fs from 'fs'; import path from 'path';
import { sleep, startServer, launch, loadGame, ROOT } from './harness.mjs';
const sheet = process.argv[2] || 'poses', out = path.resolve(process.argv[3] || path.join(ROOT, 'qa', 'shots', `stance_${sheet}.png`)); fs.mkdirSync(path.dirname(out), { recursive: true });
const W = 1600, H = 1000;
const srv = await startServer(), b = await launch({ name: 'shots', ed: 'desktop', w: W, h: H, mobile: false, dpr: 1 });
const J = async (expr) => { const r = await b.ev(`JSON.stringify((()=>{ ${expr} })())`); return r ? JSON.parse(r) : null; };
try {
  if (!await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=desktop`, 3)) throw new Error('no load');
  await b.ev("document.getElementById('help').hidden=true; window.__qaHold=true; __sc.ensureWeapons && __sc.ensureWeapons(); 1"); await sleep(3000);
  const flat = await J(`const sc=__sc; let best=null, bd=1e9; for (let x=-100;x<=100;x+=4) for (let z=-100;z<=100;z+=4) { const h0=sc.standY(x,z); if (h0<1.0) continue; let ok=true, mn=1e9, mx=-1e9; for (let k=-16;k<=16&&ok;k+=2) for (let j=-2;j<=2;j++) { const h=sc.standY(x+j*2,z+k); if (h<0.9) {ok=false;break;} mn=Math.min(mn,h); mx=Math.max(mx,h); } if (ok && mx-mn<0.08) { const d=Math.hypot(x,z); if (d<bd) {bd=d;best={x,z};} } } return best;`);
  const slope = await J(`const sc=__sc; const out=[]; for (let x=-110;x<=110;x+=3) for (let z=-110;z<=110;z+=3) { const hs=[]; let ok=true; for (let k=-6;k<=6;k+=1.5) { const h=sc.standY(x,z+k); if (h<0.9) {ok=false;break;} hs.push(h);} if(!ok) continue; const sl=(hs[hs.length-1]-hs[0])/12; let dev=0; hs.forEach((h,i)=>{ dev=Math.max(dev,Math.abs(h-(hs[0]+sl*i*1.5))); }); const cross=Math.abs(sc.standY(x+3,z)-sc.standY(x-3,z))/6; if (Math.abs(sl)>0.08 && dev<0.2 && cross<0.12) out.push({x,z,slope:sl,dev}); } out.sort((a,b)=>Math.abs(b.slope)-Math.abs(a.slope)); return out[0]||null;`);
  console.log('flat', JSON.stringify(flat), 'slope', JSON.stringify(slope));
  // item: [label, stance, moving, run, phase, weapon]
  const S = (st, mv, run, ph, w) => ({ st, mv: !!mv, run: !!run, ph: ph || 0, w: w || 'rifle' });
  const PH = (k) => k * Math.PI / 4;
  const panels = { poses: [
      { at: flat, sp: 2.5, items: [S(0, 0, 0, 0, 'rifle'), S(1, 0, 0, 0, 'smg'), S(1, 1, 0, 1.1, 'rifle'), S(1, 1, 1, 0.5, 'lmg'), S(2, 0, 0, 0, 'sniper'), S(2, 1, 0, 0.9, 'rifle'), S(2, 1, 0, 3.9, 'shotgun')] },
      { at: slope || flat, sp: 3.0, items: [S(1, 0, 0, 0, 'rpg'), S(1, 1, 0, 1.1, 'pistol'), S(2, 0, 0, 0, 'lmg'), S(2, 1, 0, 0.9, 'smg'), S(2, 1, 0, 3.9, 'rifle')] }],
    drop: [
      { at: flat, sp: 2.6, items: [0, 0.5, 1, 1.25, 1.5, 1.75, 1.9, 2.0].map(v => S(v)) },
      { at: flat, sp: 2.55, items: [0, 1, 2, 3, 4, 5, 6, 7].map(k => S(2, 1, 0, PH(k) + 0.3)) }],
    weapons: [
      { at: flat, sp: 2.8, items: ['rifle', 'smg', 'shotgun', 'lmg', 'rpg', 'pistol', 'sniper'].map(w => S(2, 0, 0, 0, w)) },
      { at: flat, sp: 1.6, items: ['rifle', 'smg', 'shotgun', 'lmg', 'rpg', 'pistol', 'sniper'].map(w => S(1, 1, 0, 0.6, w)) }] }[sheet];
  await J(`const sc=__sc, T=sc.THREE; window.__sheet=${JSON.stringify(panels)}; let n=0; window.__people=[];
    __sheet.forEach((pn, pi)=>{ pn.q=[]; pn.items.forEach((it,i)=>{ const x=pn.at.x, z=pn.at.z-(pn.items.length-1)/2*pn.sp+i*pn.sp; const q=sc.makePerson(2+((n++)%4),x,z); q.y=sc.standY(x,z); q.heading=0; sc.makeBotOf(q,'blue',it.w); q.forceStance=it.st; q.bot.stF=it.st; pn.q.push(q); __people.push(q); }); }); return 1;`);
  await J(`for (let i=0;i<170;i++) __sc.qaTick(1/60); return 1`);
  // one more step with the moving ones given an order and their phase
  await J(`const sc=__sc; __sheet.forEach(pn=>pn.items.forEach((it,i)=>{ const q=pn.q[i]; if (it.mv) { q.run=it.run; q.order={x:q.x,z:q.z+60}; q.bot.myOrder=q.order; q.walkK=1; q.runK=it.run?1:0; q.ph=it.ph-0.02; } })); sc.qaTick(1/60); return 1;`);
  await J(`const sc=__sc; __sheet.forEach(pn=>pn.items.forEach((it,i)=>{ const q=pn.q[i]; q.order=null; q.route=null; q.x=pn.at.x; q.z=pn.at.z-(pn.items.length-1)/2*pn.sp+i*pn.sp; q.y=sc.standY(q.x,q.z); q.gn=null; for (let k=0;k<14;k++) sc.placeBody(q,1/60); q.obj.updateMatrixWorld(true); })); return 1;`);
  await J(`const sc=__sc, T=sc.THREE; for (const el of [...document.body.children]) if (!el.contains(sc.renderer.domElement) && el !== sc.renderer.domElement) el.style.display='none'; const l=new T.DirectionalLight(0xffffff,2.4); l.position.set(-14,30,-18); sc.scene.add(l); sc.scene.add(new T.HemisphereLight(0xffffff,0x887766,1.3)); return 1;`);
  const view = (pi, top) => `{ __sheet.forEach((pn2, j) => pn2.q.forEach(q => { q.obj.visible = (j === ${pi}); })); const sc=__sc, cam=sc.camera, pn=__sheet[${pi}], gy=sc.standY(pn.at.x,pn.at.z); const wid=(pn.items.length)*pn.sp+1.6, vh=wid/(${W}/${H / 2}); cam.fov=28; cam.aspect=${W}/${H / 2}; cam.updateProjectionMatrix(); const dist=vh/(2*Math.tan(14*Math.PI/180)); cam.position.set(pn.at.x-dist, gy+vh*0.28+0.5, pn.at.z); cam.up.set(0,1,0); cam.lookAt(pn.at.x, gy+vh*0.28, pn.at.z); const r=sc.renderer; r.setScissorTest(true); r.setViewport(0, ${top ? H / 2 : 0}, ${W}, ${H / 2}); r.setScissor(0, ${top ? H / 2 : 0}, ${W}, ${H / 2}); r.render(sc.scene, cam); }`;
  const draw = `const sc=__sc; sc.renderer.setPixelRatio(1); sc.renderer.setSize(${W},${H},true); sc.renderer.autoClear=false; sc.renderer.setScissorTest(false); sc.renderer.setViewport(0,0,${W},${H}); sc.renderer.clear(); ${view(0, true)} ${view(1, false)} return 1;`;
  await J(draw); await sleep(400); await J(draw);
  await b.shot(out); console.log('shot', out, 'errs', JSON.stringify(b.errs.slice(0, 3)));
} catch (e) { console.log('FAIL', e && e.stack || e); } finally { await b.close(); await srv.close(); }
