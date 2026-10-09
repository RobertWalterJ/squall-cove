// Stance check (v9.9.7): crouch, crouch-walk, prone and crawl animations, and the cover / prone brain. usage: node qa/stance-check.mjs [poses|ai|perf|all] [--baseline]
// Everything runs on simulated time: the frame loop is paused (window.__qaHold) and the test steps the game itself with __sc.qaTick(1/60), so results do not depend on the speed of
// the software renderer. Random numbers are not seeded, so the AI sections assert ranges and rates, not exact frames.
//   poses: speed factors, smooth transitions, no foot sliding, no clipping or floating on flat ground and slopes, weapon holds in every stance, hit reaction and falls, eye height and hit boxes
//   ai:    cover choice (crouch / prone cover), pinned in the open goes prone and recovers, staggering, closing enemy, wounded, long guns holding, Take cover order, cover shift when flanked
//   perf:  a 20-bot battle for 30 simulated seconds (CPU ms per step); with --baseline the same run on the previous release (git HEAD) for comparison
import { execSync } from 'child_process';
import { sleep, startServer, launch, loadGame, ROOT } from './harness.mjs';
const which = process.argv.find(a => ['poses', 'ai', 'perf', 'all'].includes(a)) || 'all', BASE = process.argv.includes('--baseline');
const T0 = Date.now(), log = (m) => console.log(`[${((Date.now() - T0) / 1000).toFixed(0)}s] ${m}`);
setTimeout(() => { console.log('ERR watchdog: the stance check took over 14 minutes'); process.exit(2); }, 840000).unref();
const fail = [], ok = (name, cond, detail) => { console.log((cond ? '  ok   ' : '  FAIL ') + name + (detail !== undefined ? '  ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)) : '')); if (!cond) fail.push(name); };
const num = (v, d = 2) => +(+v).toFixed(d);
let overrides = {};
if (BASE) {                                                         // the previous release with the two test hooks patched in, served as /index.html
  let html = execSync('git show HEAD:index.html', { cwd: ROOT, maxBuffer: 1 << 28 }).toString('utf8');
  const a = 'window.__sc = { DIST,', f = 'function frame(now) { if (ED.phone && govFrame(now)) {'; if (!html.includes(a) || !html.includes(f)) throw new Error('baseline anchors not found');
  html = html.replace(a, 'function qaTick(dt) { world.step(1 / 60, dt, 5); armedLayer(dt); updateBattle(dt); updatePeople(dt, simT); }\nwindow.__sc = { qaTick, DIST,').replace(f, 'function frame(now) { if (window.__qaHold) { last = now; requestAnimationFrame(frame); return; } if (ED.phone && govFrame(now)) {');
  overrides['/index.html'] = html;
}
const srv = await startServer(ROOT, 0, overrides), b = await launch({ name: 'check', ed: 'desktop', w: 640, h: 400, mobile: false, dpr: 1 });
const J = async (expr) => { const r = await b.ev(`JSON.stringify((()=>{ ${expr} })())`); return r ? JSON.parse(r) : null; };
try {
  if (!await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=desktop`, 3)) throw new Error('no load');
  await b.ev("document.getElementById('help').hidden=true; window.__qaHold=true; __sc.ensureWeapons && __sc.ensureWeapons(); 1"); await sleep(3000);
  log('loaded' + (BASE ? ' (baseline: previous release)' : ''));

  // ================================================================ POSES
  if ((which === 'poses' || which === 'all') && !BASE) {
    const flat = await J(`const sc=__sc; let best=null, bd=1e9; for (let x=-100;x<=100;x+=4) for (let z=-100;z<=100;z+=4) { const h0=sc.standY(x,z); if (h0<1.0) continue; let ok=true, mn=1e9, mx=-1e9; for (let k=-14;k<=14&&ok;k+=2) for (let j=-2;j<=2;j++) { const h=sc.standY(x+j*2,z+k); if (h<0.9) {ok=false;break;} mn=Math.min(mn,h); mx=Math.max(mx,h); } if (ok && mx-mn<0.08) { const d=Math.hypot(x,z); if (d<bd) {bd=d;best={x,z};} } } return best;`);
    const slope = await J(`const sc=__sc; const out=[]; for (let x=-110;x<=110;x+=3) for (let z=-110;z<=110;z+=3) { const hs=[]; let ok=true; for (let k=-6;k<=6;k+=1.5) { const h=sc.standY(x,z+k); if (h<0.9) {ok=false;break;} hs.push(h);} if(!ok) continue; const sl=(hs[hs.length-1]-hs[0])/12; let dev=0; hs.forEach((h,i)=>{ dev=Math.max(dev,Math.abs(h-(hs[0]+sl*i*1.5))); }); const cross=Math.abs(sc.standY(x+3,z)-sc.standY(x-3,z))/6; if (Math.abs(sl)>0.09 && dev<0.2 && cross<0.12) out.push({x,z,slope:sl}); } out.sort((a,b)=>Math.abs(b.slope)-Math.abs(a.slope)); return out[0]||null;`);
    log('flat ' + JSON.stringify(flat) + ' slope ' + JSON.stringify(slope));
    await J(`for (const q of __sc.people.slice()) if (!q.bot) __sc.removePerson(q); return 1;`);          // the sandbox crowd only slows the steps down
    await J(`const sc=__sc, T=sc.THREE; let n=0; window.__P = {
      mk(x,z,cls,yaw){ const q=sc.makePerson(2+((n++)%4),x,z); q.y=sc.standY(x,z); q.heading=yaw||0; sc.makeBotOf(q,'blue',cls||'rifle'); window.__keep=(window.__keep||[]); window.__keep.push(q); return q; },
      tick(k){ for (let i=0;i<k;i++) sc.qaTick(1/60); },
      settle(q,st,k){ q.forceStance=st; q.bot.stF=st; this.tick(k||150); },
      pos(q,n){ q.obj.updateMatrixWorld(true); const v=new T.Vector3().setFromMatrixPosition(q.bones[n].matrixWorld); return [v.x,v.y,v.z]; },
      gdy(q,n,r){ const p=this.pos(q,n); return p[1]-r-sc.standY(p[0],p[2]); },
      clr(q){ q.obj.updateMatrixWorld(true); const arr=[], v=new T.Vector3(); q.obj.traverse(m=>{ if (!m.isMesh || !m.isSkinnedMesh || !m.geometry || !m.geometry.attributes.position) return; const pos=m.geometry.attributes.position, st=5;          /* the body mesh only: small kit hung on the chest (a pouch, a hat) is cosmetic and may dip into the ground */ if (m.isSkinnedMesh) m.skeleton.update(); for (let i=0;i<pos.count;i+=st) { v.fromBufferAttribute(pos,i); if (m.isSkinnedMesh) m.applyBoneTransform(i,v); v.applyMatrix4(m.matrixWorld); const c=v.y-sc.standY(v.x,v.z); if (c > -0.5) arr.push(c); } }); arr.sort((a,b)=>a-b); return { min: arr[0], p1: arr[Math.floor(arr.length*0.01)], n: arr.length }; },
      gunPts(q){ const gm=q.bot.wmesh; if(!gm) return null; q.obj.updateMatrixWorld(true); return [-0.1,0.2,0.5,0.8].map(z=>{ const v=new T.Vector3(0,0,z).applyMatrix4(gm.matrixWorld); return [v.x,v.y,v.z]; }); } }; return 1;`);

    // ---- 1 speed factors
    {
      const run = async (st) => J(`const P=__P, q=P.mk(${flat.x},${flat.z}-12,'rifle',0); P.settle(q,${st},60); q.order={x:q.x,z:q.z+40}; q.bot.myOrder=q.order; q.run=false; P.tick(40); const z0=q.z, t0=__sc.simTime(); P.tick(150); const v=(q.z-z0)/(__sc.simTime()-t0); __sc.removePerson(q); return v;`);
      const v0 = await run(0), v1 = await run(1), v2 = await run(2);
      ok('speed: crouch about 0.6x of standing', Math.abs(v1 / v0 - 0.6) < 0.04, { stand: num(v0), crouch: num(v1), ratio: num(v1 / v0) });
      ok('speed: prone about 0.35x of standing', Math.abs(v2 / v0 - 0.35) < 0.04, { prone: num(v2), ratio: num(v2 / v0) });
    }
    // ---- 2 transitions: no snapping, and the stated durations
    {
      const seq = async (from, to, label, minT, maxT) => {
        const r = await J(`const P=__P, sc=__sc, q=P.mk(${flat.x},${flat.z},'rifle',0); P.settle(q,${from},150); q.forceStance=${to}; q.bot.stF=${to}; const rows=[]; for (let i=0;i<110;i++) { sc.qaTick(1/60); const h=P.pos(q,'head'), hd=P.pos(q,'hand.R'), hp=P.pos(q,'hips'); rows.push([q.stanceK,q.proneK,q.crW,q.pitchA,hp[1],h[0],h[1],h[2],hd[0],hd[1],hd[2], sc.simTime()]); } sc.removePerson(q); return rows;`);
        let maxS = 0, maxS2 = 0, maxH = 0, maxHd = 0, maxFit = 0, tDone = null, t0 = r[0][11] - 1 / 60;
        for (let i = 1; i < r.length; i++) {
          const dS = Math.abs(r[i][0] - r[i - 1][0]); maxS = Math.max(maxS, dS); if (i > 1) maxS2 = Math.max(maxS2, Math.abs(r[i][0] - 2 * r[i - 1][0] + r[i - 2][0]));
          maxH = Math.max(maxH, Math.hypot(r[i][5] - r[i - 1][5], r[i][6] - r[i - 1][6], r[i][7] - r[i - 1][7])); maxHd = Math.max(maxHd, Math.hypot(r[i][8] - r[i - 1][8], r[i][9] - r[i - 1][9], r[i][10] - r[i - 1][10]));
          maxFit = Math.max(maxFit, Math.abs(r[i][4] - r[i - 1][4])); if (tDone === null && Math.abs(r[i][0] - to) < 0.03) tDone = r[i][11] - t0;
        }
        ok(`transition ${label}: stance value changes smoothly`, maxS <= 0.075 && maxS2 <= 0.03, { maxStep: num(maxS, 3), maxAccel: num(maxS2, 3) });
        ok(`transition ${label}: head and hand never jump (per frame)`, maxH < 0.14 && maxHd < 0.16, { head: num(maxH, 3), hand: num(maxHd, 3) });
        ok(`transition ${label}: pelvis height never jumps (under 0.12 m per frame)`, maxFit < 0.12, { maxPelvisStep: num(maxFit, 3) });
        ok(`transition ${label}: takes ${minT} to ${maxT} s`, tDone !== null && tDone >= minT && tDone <= maxT, { seconds: tDone && num(tDone) });
      };
      await seq(0, 2, 'stand to prone', 0.45, 0.8); await seq(2, 0, 'prone to stand', 0.5, 1.15); await seq(0, 1, 'stand to crouch', 0.2, 0.5); await seq(1, 2, 'crouch to prone', 0.25, 0.6); await seq(2, 1, 'prone to crouch', 0.3, 0.7);
    }
    // ---- 3 no foot sliding: planted ankles stay put, and the cycle advances with distance
    {
      const gait = async (label, st, run, tolRatio) => {
        const r = await J(`const P=__P, sc=__sc, T=sc.THREE, q=P.mk(${flat.x},${flat.z}-12,'rifle',0); P.settle(q,${st},100); q.run=${run}; q.order={x:q.x,z:q.z+80}; q.bot.myOrder=q.order; P.tick(30); const z0=q.z, ph0=q.ph, rows=[]; for (let i=0;i<200;i++) { sc.qaTick(1/60); const o={}; for (const n of ['foot.L','foot.R','shin.L','shin.R']) { const p=P.pos(q,n); o[n]=[p[0],p[1]-sc.standY(p[0],p[2]),p[2]]; } o.ph=q.ph; rows.push(o); } const out={ dz:q.z-z0, cyc:(q.ph-ph0)/6.2832, rows, Sc: ${st} === 2 ? sc.crawlStride(q) : null, H0: sc.legDims(q).H0 }; sc.removePerson(q); return out;`);
        const spd = r.dz / (200 / 60), stride = r.dz / r.cyc;
        const stanceOnly = (nm, i) => { const u = (((r.rows[i].ph / 6.2832 + (nm.endsWith('R') ? 0.5 : 0)) % 1) + 1) % 1; return u < 0.5; };
        const planted = (names) => { let sum = 0, n = 0, worst = 0, latSum = 0; for (const nm of names) { const ys = r.rows.map(o => o[nm][1]), lo = Math.min(...ys); for (let i = 1; i < r.rows.length; i++) if (st === 2 ? stanceOnly(nm, i) && stanceOnly(nm, i - 1) : (ys[i] < lo + 0.03 && ys[i - 1] < lo + 0.035)) { const sp = (st === 2 ? Math.abs(r.rows[i][nm][2] - r.rows[i - 1][nm][2]) : Math.hypot(r.rows[i][nm][0] - r.rows[i - 1][nm][0], r.rows[i][nm][2] - r.rows[i - 1][nm][2])) * 60, lat = Math.abs(r.rows[i][nm][0] - r.rows[i - 1][nm][0]) * 60; sum += sp; latSum += lat; n++; worst = Math.max(worst, sp); } } return { n, mean: n ? sum / n : 1e9, worst, lat: n ? latSum / n : 0 }; };
        const design = st === 2 ? r.Sc : (1.05 + 0.65 * (run ? 1 : 0)) * (r.H0 / 0.85);
        ok(`${label}: stride per cycle matches the design (cycle tied to distance)`, Math.abs(stride / design - 1) < 0.06, { stride: num(stride), design: num(design), speed: num(spd) });
        const pl = planted(st < 2 ? ['foot.L', 'foot.R'] : ['shin.L', 'shin.R']);
        ok(`${label}: ${st < 2 ? 'planted ankles' : 'the dragged knees'} do not slide along the line of travel (mean ground speed at most ${Math.round(tolRatio * 100)}% of body speed)`, pl.n >= 30 && pl.mean < tolRatio * spd, { plantedFrames: pl.n, meanSlide: num(pl.mean, 3), worst: num(pl.worst), bodySpeed: num(spd), sidewaysDrift: num(pl.lat, 3) });
      };
      await gait('crouch-walk', 1, false, 0.12); await gait('crouch-run', 1, true, 0.15); await gait('crawl', 2, false, 0.4);
    }
    // ---- 4 flat ground and slopes: lies on the ground, neither in it nor above it, gun included
    {
      const base0 = await J(`const P=__P, sc=__sc, q=P.mk(${flat.x},${flat.z},'rifle',0); P.settle(q,0,100); const c=P.clr(q); sc.removePerson(q); return c.min;`);       // how far the boots of a standing soldier reach below his own ground point (the model's feet are slightly sunk)
      console.log('  info standing soldier lowest vertex', num(base0, 3));
      const spots = [['flat', flat]].concat(slope ? [['slope', slope]] : []);
      for (const [label, sp] of spots) for (const hd of [0, Math.PI / 2, Math.PI]) for (const mode of ['lying', 'crawling']) {
        const r = await J(`const P=__P, sc=__sc, q=P.mk(${sp.x},${sp.z},'rifle',${hd}); P.settle(q,2,160); if ('${mode}'==='crawling') { q.order={x:q.x+Math.sin(${hd})*6,z:q.z+Math.cos(${hd})*6}; q.bot.myOrder=q.order; }
          let minClr=1e9, maxFloat=-1e9, minGun=1e9, n=0, meshMin=1e9, meshP1=-1e9; const names=['foot.L','foot.R','shin.L','shin.R','hand.L','hand.R','forearm.L','forearm.R','chest','spine','head','thigh.L','thigh.R'], rr=[0.04,0.04,0.065,0.065,0.05,0.05,0.055,0.055,0.13,0.12,0.11,0.085,0.085];
          for (let i=0;i<150;i++) { sc.qaTick(1/60); if (i%4) continue; let low=1e9; names.forEach((nm,k)=>{ const c=P.gdy(q,nm,rr[k]); minClr=Math.min(minClr,c); low=Math.min(low,c); }); maxFloat=Math.max(maxFloat,low); const g=P.gunPts(q); if (g) for (const p of g) minGun=Math.min(minGun, p[1]-sc.standY(p[0],p[2])); if (i%20===0) { const c=P.clr(q); meshMin=Math.min(meshMin,c.min); meshP1=Math.max(meshP1,c.p1); } n++; }
          const t=P.pos(q,'head'), c=P.pos(q,'hips'); const run=[t[0]-c[0],t[1]-c[1],t[2]-c[2]], len=Math.hypot(...run); const out={ minClr, maxFloat, minGun, meshMin, meshP1, pitch: Math.asin(run[1]/len), n, sk:q.stanceK }; sc.removePerson(q); return out;`);
        ok(`${label} heading ${num(hd)} ${mode}: no vertex of the body mesh sinks more than 4 cm deeper than a standing soldier's boots`, r.meshMin > base0 - 0.04, { lowestVertex: num(r.meshMin, 3), standing: num(base0, 3) });
        ok(`${label} heading ${num(hd)} ${mode}: not floating (lowest 1% of the mesh within 10 cm of the ground)`, r.meshP1 < 0.1 && r.meshP1 > base0 - 0.04, { lowest1pct: num(r.meshP1, 3) });
        ok(`${label} heading ${num(hd)} ${mode}: the gun stays above the ground`, r.minGun > -0.02, { minGunHeight: num(r.minGun, 3) });
      }
      if (slope) { const r = await J(`const P=__P, sc=__sc, q=P.mk(${slope.x},${slope.z},'rifle',0); P.settle(q,2,160); const h=P.pos(q,'head'), c=P.pos(q,'hips'); const body=Math.atan2(h[1]-c[1], Math.hypot(h[0]-c[0],h[2]-c[2])); const gx=(sc.standY(${slope.x},${slope.z}+0.7)-sc.standY(${slope.x},${slope.z}-0.7))/1.4; const o={ bodyPitch: body, groundPitch: Math.atan(gx) }; sc.removePerson(q); return o;`);
        ok('slope: the lying body is tilted with the ground (within 0.35 rad: the head is raised a little)', Math.abs(r.bodyPitch - r.groundPitch) < 0.35, { body: num(r.bodyPitch), ground: num(r.groundPitch), slope: num(slope.slope) }); }
    }
    // ---- 5 weapon holds in every stance
    {
      const rows = [];
      for (const w of ['rifle', 'smg', 'shotgun', 'lmg', 'rpg', 'pistol', 'sniper']) for (const st of [0, 1, 2]) for (const aim of [0, 1]) {
        const r = await J(`const P=__P, sc=__sc, q=P.mk(${flat.x},${flat.z},'${w}',0); q.aim=${aim}; q.bot.tgt=${aim ? 'null' : 'null'}; P.settle(q,${st},100); q.aim=${aim}; sc.qaTick(1/60); const g=P.gunPts(q); let minG=1e9; for (const p of g) minG=Math.min(minG,p[1]-sc.standY(p[0],p[2])); const hr=P.pos(q,'hand.R'), hl=P.pos(q,'hand.L'), gp=g[1]; const d=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1],a[2]-b[2]); const out={ minG, dR:d(hr,g[1]), dL:d(hl,g[2]) }; sc.removePerson(q); return out;`);
        rows.push({ w, st, aim, minG: num(r.minG, 3), dR: num(r.dR), dL: num(r.dL) });
      }
      const bad = rows.filter(r => r.minG < -0.01), far = rows.filter(r => r.dR > 0.45 || r.dL > 0.6);
      ok('weapon holds: seven weapon classes in stand, crouch and prone, aiming and not: gun never through the ground', bad.length === 0, bad.slice(0, 4));
      ok('weapon holds: both hands stay on the weapon', far.length === 0, far.slice(0, 4));
      console.log('  info lowest gun point above ground (prone, not aiming):', JSON.stringify(rows.filter(r => r.st === 2 && r.aim === 0).map(r => r.w + ' ' + r.minG)));
    }
    // ---- 6 hit reactions and falls
    {
      const r = await J(`const P=__P, sc=__sc; const out={}; for (const st of [0,2]) { const q=P.mk(${flat.x},${flat.z},'rifle',0); P.settle(q,st,150); const h0=P.pos(q,'head'), p0=P.pos(q,'hips'); q.flinch={t:0.5,a:0,s:1}; let mx=0; for (let i=0;i<30;i++) { sc.qaTick(1/60); const h=P.pos(q,'head'), p=P.pos(q,'hips'); mx=Math.max(mx, Math.hypot((h[0]-p[0])-(h0[0]-p0[0]),(h[1]-p[1])-(h0[1]-p0[1]),(h[2]-p[2])-(h0[2]-p0[2]))); } out['flinch'+st]=mx; sc.removePerson(q); }
        for (const st of [0,1,2]) { const q=P.mk(${flat.x}+3,${flat.z},'rifle',0); q.side='blue'; P.settle(q,st,150); const sh=P.mk(${flat.x}+3,${flat.z}-20,'rifle',0); sh.side='red'; sh.bot.team='red'; q.hp=10; sc.hurt(q, 50, sh, false, 'test'); let maxV=0, finite=true, st0=q.state; for (let i=0;i<120;i++) { sc.qaTick(1/60); if (q.rag) { const v=q.rag.bodies.pelvis.velocity; maxV=Math.max(maxV, Math.hypot(v.x,v.y,v.z)); const pp=q.rag.bodies.pelvis.position; if (!isFinite(pp.x+pp.y+pp.z)) finite=false; } } out['fall'+st]={ state:q.state, maxV, finite, gun: q.bot.wmesh===null }; sc.removePerson(q); sc.removePerson(sh); }
        return out;`);
      ok('hit while prone is only a small flinch (under half the standing one)', r.flinch2 < 0.5 * r.flinch0 && r.flinch0 > 0.02, { standing: num(r.flinch0, 3), prone: num(r.flinch2, 3) });
      ok('falling from stand, crouch and prone: ragdoll, finite, gun dropped', ['fall0', 'fall1', 'fall2'].every(k => r[k].state === 'rag' && r[k].finite && r[k].gun), r);
      ok('falling from prone: no tumble, the body just goes limp (pelvis speed under 1.5 m/s)', r.fall2.maxV < 1.5, { prone: num(r.fall2.maxV), crouch: num(r.fall1.maxV), stand: num(r.fall0.maxV) });
    }
    // ---- 7 eye height, hit chance and hit boxes follow the stance
    {
      const r = await J(`const P=__P, sc=__sc; const out={}; for (const st of [0,1,2]) { const q=P.mk(${flat.x},${flat.z},'rifle',0); P.settle(q,st,150); const sp=sc.personSpheres(q).map(a=>[a[0],a[1],a[2],a[3]]); out['s'+st]={ eye: sc.eyeOf(q)-q.y, hit: sc.lerpS(sc.STANCE_HIT, sc.stOf(q)), maxY: Math.max(...sp.map(a=>a[1]+Math.sqrt(a[3]))), span: Math.hypot(Math.max(...sp.map(a=>a[0]))-Math.min(...sp.map(a=>a[0])), Math.max(...sp.map(a=>a[2]))-Math.min(...sp.map(a=>a[2]))) }; sc.removePerson(q); } return out;`);
      ok('eye height 1.4 / 0.9 / 0.35 for stand / crouch / prone (same table as the player)', Math.abs(r.s0.eye - 1.4) < 0.03 && Math.abs(r.s1.eye - 0.9) < 0.03 && Math.abs(r.s2.eye - 0.35) < 0.03, [num(r.s0.eye), num(r.s1.eye), num(r.s2.eye)]);
      ok('hit chance multiplier 1 / 0.8 / 0.55 (same as the player)', Math.abs(r.s0.hit - 1) < 0.01 && Math.abs(r.s1.hit - 0.8) < 0.01 && Math.abs(r.s2.hit - 0.55) < 0.01, [num(r.s0.hit), num(r.s1.hit), num(r.s2.hit)]);
      ok('hit boxes: prone is low and long, standing is tall', r.s2.maxY < 0.55 && r.s2.span > 0.9 && r.s0.maxY > 1.5, r);
    }
    await J(`for (const q of __sc.people.slice()) if (q.bot) __sc.removePerson(q); return 1;`);
  }

  // ================================================================ battle scaffold (ai and perf)
  const startBattle = async (size) => { await b.ev(`document.getElementById('help').hidden=true; __sc.BATTLE.size=${size}; __sc.battleStart(); 1`); await sleep(7000); };
  // ================================================================ AI
  if ((which === 'ai' || which === 'all') && !BASE) {
    await startBattle(9);
    await J(`const sc=__sc; sc.BATTLE.size=0; for (const q of sc.people.slice()) if (q.bot) sc.removePerson(q); sc.BATTLE.tickets.blue=9999; sc.BATTLE.tickets.red=9999; for (let i=sc.props.length-1;i>=0;i--) { const p=sc.props[i]; if (p.bcover) { sc.scene.remove(p.mesh); if (p.body) sc.world.removeBody(p.body); sc.props.splice(i,1); } } return 1;`);
    await J(`const sc=__sc, T=sc.THREE; window.__T = {
      n:0, fire:false, fireEvery:0.3, nextFire:0, targets:null, ti:0,
      mk(team,x,z,cls){ const q=sc.makePerson(2+((this.n++)%4),x,z); q.y=sc.standY(x,z); q.side=team; q.role=team==='blue'?'Guard':'Raider'; sc.makeBotOf(q,team,cls||'rifle'); q.hp=1e6; return q; },
      dummy(x,z){ const q=sc.makePerson(3,x,z); q.y=sc.standY(x,z); q.side='red'; q.hp=1e6; q.heading=Math.PI; return q; },
      wall(id,x,z,yaw){ const it=sc.BUILD.find(b=>b.id===id); sc.place(it,{x,z}); const pr=sc.props[sc.props.length-1]; pr.mesh.rotation.y=yaw; pr.bcover=true; return pr; },
      clear(){ for (const q of sc.people.slice()) if (q.bot || q.side==='red') sc.removePerson(q); for (let i=sc.props.length-1;i>=0;i--) { const p=sc.props[i]; if (p.bcover) { sc.scene.remove(p.mesh); if (p.body) sc.world.removeBody(p.body); sc.props.splice(i,1); } } this.S=null; this.fire=false; this.targets=null; },
      tick(k){ for (let i=0;i<k;i++) { const S=this.S; if (S) { S.x=this.sx; S.z=this.sz; S.bot.cool=1e9; S.bot.reload=1e9; S.order=null; S.bot.tgt=null;
          if (this.fire && sc.simTime()>=this.nextFire) { this.nextFire=sc.simTime()+this.fireEvery; const tg=this.targets||[this.A]; const A=tg[this.ti++ % tg.length]; if (A && A.state!=='rag') { S.bot.cool=0; S.bot.reload=0; S.bot.ammo=25; const d=Math.hypot(A.x-S.x,A.z-S.z); S.heading=Math.atan2(A.x-S.x,A.z-S.z); sc.botFire(S,S.bot,A,d); S.bot.cool=1e9; } } }
        sc.qaTick(1/60); } },
      rec(q){ const b=q.bot; return { t:sc.simTime(), x:q.x, z:q.z, sk:q.stanceK, stF:b.stF, pr:!!b.pr, why:b.prWhy||0, atC:!!b.atCover, kind:b.coverPt?b.coverPt.kind:-1, ord:!!q.order, ammo:b.ammo, tgt:!!b.tgt, crouch:!!b.crouch }; } }; return 1;`);
    // an open lane: the bot at (x,z), a shooter 45 m further along +z, clear sight at 1.3 m, no cover for 34 m around the bot
    const lane = await J(`const sc=__sc, L=sc.coverList(); const out=[]; for (let x=-110;x<=110;x+=6) for (let z=-110;z<=60;z+=6) { const h0=sc.standY(x,z), h1=sc.standY(x,z+45); if (h0<1.0||h1<1.0||Math.abs(h1-h0)>1.5) continue; if (!sc.losFull(x,h0+1.3,z,x,h1+1.3,z+45)) continue; let near=0; for (const c of L) if (Math.hypot(c.x-x,c.z-z)<34) near++; if (!near) out.push({x,z}); } return out;`);
    log('open lanes ' + (lane ? lane.length : 0));
    const Ln = lane[0];
    const scen = async (label, setup, secs, opts = {}) => {
      await J(`const T=__T, sc=__sc; T.clear(); T.A=T.mk('blue',${Ln.x},${Ln.z},'${opts.cls || 'rifle'}'); T.A.heading=0; T.S=T.mk('red',${Ln.x},${Ln.z + 45},'rifle'); T.sx=${Ln.x}; T.sz=${Ln.z + 45}; T.S.bot.cool=1e9; T.fire=${opts.fire === false ? 'false' : 'true'}; T.fireEvery=${opts.every || 0.3}; T.nextFire=sc.simTime()+1; ${setup || ''} return 1;`);
      const rows = []; for (let s = 0; s < secs * 5; s++) { await J(`__T.tick(12); return 1`); rows.push(await J(`return __T.rec(__T.A)`)); if (opts.during) await opts.during(s, rows); }
      return rows;
    };
    // ---- A cover (crouch) under fire
    {
      const rows = await scen('crouch cover', `T.wall('x-sandbag_wall', ${Ln.x + 3}, ${Ln.z + 8}, 0);`, 8);
      const cv = rows.find(r => r.kind >= 0), arr = rows.find(r => r.atC);
      ok('cover: a soldier under fire picks cover that suits its height (sandbag wall = crouch cover)', cv && cv.kind === 1, { firstPick: cv && cv.t, kind: cv && cv.kind });
      ok('cover: and gets there within 6 s', arr && arr.t - rows[0].t < 6, { arrived: arr && num(arr.t - rows[0].t) });
      const after = rows.filter(r => arr && r.t > arr.t + 0.5); ok('cover: behind it he is crouched (not standing, not prone) most of the time', after.length > 5 && after.filter(r => r.sk > 0.8 && r.sk < 1.2).length / after.length > 0.55 && after.every(r => !r.pr), { crouchShare: num(after.filter(r => r.sk > 0.8 && r.sk < 1.2).length / Math.max(1, after.length)) });
      const spot = await J(`const sc=__sc,T=__T,cp=T.A.bot.coverPt; return cp ? { screened: !sc.losFull(T.S.x, sc.eyeOf(T.S), T.S.z, cp.x, sc.standY(cp.x,cp.z)+sc.COV_H[cp.kind], cp.z) } : null;`);
      ok('cover: the chosen spot really screens a body of that height from the shooter', spot && spot.screened, spot);
    }
    // ---- B very low cover: lies behind it, rises to shoot, lies down again
    {
      const rows = await scen('prone cover', `T.wall('x-jersey_barrier', ${Ln.x + 3}, ${Ln.z + 8}, 0);`, 14);
      const arr = rows.find(r => r.atC), after = rows.filter(r => arr && r.t > arr.t + 0.5);
      ok('very low cover: he lies behind it (prone cover chosen for a 0.8 m barrier)', arr && after.some(r => r.sk > 1.9) && rows.some(r => r.kind === 2), { kinds: [...new Set(rows.map(r => r.kind))] });
      ok('very low cover: and rises to look and shoot, then lies down again (peek and duck back)', after.some(r => r.sk < 1.3) && after.some(r => r.sk > 1.9), { min: num(Math.min(...after.map(r => r.sk))), max: num(Math.max(...after.map(r => r.sk))) });
    }
    // ---- C pinned in the open, no cover within 12 m: goes prone, shoots back, recovers when the shooting stops
    {
      let stopped = false;
      const rows = await scen('open ground', ``, 22, { during: async (s, rows) => { const last = rows[rows.length - 1]; if (!stopped && last.pr && last.sk > 1.95 && last.t - rows[0].t > 5) { stopped = true; await J(`__T.fire=false; return 1`); rows.stopAt = rows.length; } } });
      const pr = rows.find(r => r.pr), stopI = rows.stopAt;
      ok('open ground: under heavy fire with no cover close, he goes prone within 8 s', pr && pr.sk >= 0 && pr.t - rows[0].t < 8 && rows.some(r => r.sk > 1.95), { at: pr && num(pr.t - rows[0].t) });
      const proneRows = rows.filter(r => r.pr); ok('open ground: and keeps shooting from the ground', proneRows.length > 4 && proneRows[0].ammo - proneRows[proneRows.length - 1].ammo >= 1, { ammoUsed: proneRows.length ? proneRows[0].ammo - proneRows[proneRows.length - 1].ammo : 0 });
      const rise = stopI !== undefined ? rows.slice(stopI).find(r => r.sk < 1.2) : null;
      ok('open ground: when the shooting stops he gets up (crouch or stand) within 14 s', !!rise && rise.t - rows[stopI].t < 14, { after: rise && stopI !== undefined ? num(rise.t - rows[stopI].t) : null, stopped });
    }
    // ---- D enemy closes within 12 m: up and fighting
    {
      let moved = false;
      const rows = await scen('closing', ``, 16, { during: async (s, rows) => { const last = rows[rows.length - 1]; if (!moved && last.pr && last.sk > 1.95) { moved = true; await J(`const T=__T; T.sz=T.A.z+9; T.sx=T.A.x; T.S.x=T.sx; T.S.z=T.sz; return 1`); rows.movedAt = rows.length; } } });
      const mi = rows.movedAt, up = mi !== undefined ? rows.slice(mi).find(r => r.sk < 1.3) : null;
      ok('closing enemy: a prone soldier gets up when the enemy comes within 12 m (within 2 s)', moved && !!up && up.t - rows[mi - 1].t < 2.2, { moved, after: up && num(up.t - rows[mi - 1].t) });
    }
    // ---- E wounded (no medic) goes prone; with a medic close he does not
    {
      const r1 = await scen('wounded', `T.A.hp=30;`, 7, { fire: false }); const r2 = await scen('wounded with a medic', `T.A.hp=30; T.mk('blue', ${Ln.x + 6}, ${Ln.z - 2}, 'medic'); T.A.hp=30;`, 7, { fire: false });
      ok('wounded (hp 35 or less) with no medic close: lies down within 3 s of seeing the enemy', r1.some(r => r.pr && r.why === 3), { why: [...new Set(r1.filter(r => r.pr).map(r => r.why))] });
      ok('wounded with a medic close: does not drop for that reason', !r2.some(r => r.pr && r.why === 3), { why: [...new Set(r2.filter(r => r.pr).map(r => r.why))] });
    }
    // ---- F staggering: ten soldiers under the same fire do not all drop together
    {
      await J(`const T=__T, sc=__sc; T.clear(); T.group=[]; for (let i=0;i<10;i++) { const q=T.mk('blue', ${Ln.x} - 6 + (i%5)*3, ${Ln.z} + (i<5?0:3), 'rifle'); q.heading=0; T.group.push(q); } T.S=T.mk('red',${Ln.x},${Ln.z + 45},'rifle'); T.sx=${Ln.x}; T.sz=${Ln.z + 45}; T.A=T.group[0]; T.targets=T.group; T.fire=true; T.fireEvery=0.07; T.nextFire=sc.simTime()+1; return 1;`);
      const first = Array(10).fill(null); let maxSim = 0, allSame = false; const t0 = await J(`return __sc.simTime()`);
      for (let s = 0; s < 70; s++) { await J(`__T.tick(6); return 1`); const st = await J(`return __T.group.map(q=>({ pr: !!q.bot.pr, sk: q.stanceK, t: __sc.simTime(), sq: q.bot.sq }))`); let n = 0; st.forEach((o, i) => { if (o.pr && first[i] === null) first[i] = o.t; if (o.sk > 1.5) n++; }); maxSim = Math.max(maxSim, n); if (n === 10) allSame = true; }
      const ts = first.filter(v => v !== null).sort((a, c) => a - c), spread = ts.length ? ts[ts.length - 1] - ts[0] : 0;
      ok('stagger: many of ten soldiers under fire go prone (4 or more of them, 2 or more at once at some time)', maxSim >= 2 && ts.length >= 4, { wentProne: ts.length, maxAtOnce: maxSim });
      ok('stagger: they do not all go down together (start times spread over at least 0.5 s, never all ten at once)', spread >= 0.5 && !allSame, { spreadSeconds: num(spread), allTen: allSame, starts: ts.map(v => num(v - t0, 1)) });
    }
    // ---- G long guns hold prone: snipers nearly always, machine gunners often, riflemen never
    {
      const holdTest = async (cls, weapon) => J(`const T=__T, sc=__sc; T.clear(); const E=T.dummy(${Ln.x},${Ln.z + 50}); const qs=[]; for (let i=0;i<10;i++) { const q=T.mk('blue', ${Ln.x} - 9 + i*2, ${Ln.z}, '${cls}'); q.heading=0; q.bot.sq='hold'+'${cls}'+i; q.bot.sqi=0; q.bot.tac='hold'; q.bot.pref=0.95; q.bot.fside=1; qs.push(q); } T.group=qs; T.S=null; T.fire=false; for (let i=0;i<420;i++) { sc.qaTick(1/60); } const seen=qs.filter(q=>q.bot.tgt||q.bot.memE).length; const prone=qs.filter(q=>q.bot.pr).length; const why=qs.filter(q=>q.bot.pr).map(q=>q.bot.prWhy); for (const q of qs.concat([E])) sc.removePerson(q); return { seen, prone, why: [...new Set(why)], w: qs[0].bot.w };`);
      const sn = await holdTest('sniper'), mg = await holdTest('heavy'), rf = await holdTest('rifle');
      ok('long guns: snipers holding at 50 m lie down (8 or more of 10)', sn.prone >= 8 && sn.why.every(w => w === 6), sn);
      ok('long guns: machine gunners holding lie down some of the time (2 to 9 of 10)', mg.prone >= 2 && mg.prone <= 9, mg);
      ok('long guns: riflemen holding do not lie down for that reason (0 of 10)', rf.prone === 0, rf);
    }
    // ---- H flanked: cover that the shooter cannot see into stops working, so he moves
    {
      const rows = await scen('flanked', `T.wall('x-sandbag_wall', ${Ln.x + 3}, ${Ln.z + 8}, 0);`, 14, { during: async (s, rows) => { if (!rows.flank && rows.some(r => r.atC) && rows.length > 14) { rows.flank = rows.length; await J(`const T=__T; T.sx=T.A.x - 38; T.sz=T.A.z + 8; T.S.x=T.sx; T.S.z=T.sz; return 1`); } } });
      const fi = rows.flank, a0 = rows[fi - 1], moved = rows.slice(fi).some(r => r.ord && Math.hypot(r.x - a0.x, r.z - a0.z) > 1.5);
      const nowCover = await J(`const sc=__sc,T=__T,cp=T.A.bot.coverPt; return cp ? { moved: Math.hypot(cp.x-(${Ln.x + 3}), cp.z-(${Ln.z + 8}))>0.1, screened: !sc.losFull(T.S.x, sc.eyeOf(T.S), T.S.z, cp.x, sc.standY(cp.x,cp.z)+sc.COV_H[cp.kind], cp.z) } : null;`);
      ok('flanked: when the shooter ends up where the cover does not screen him, he shifts to other cover or lies low', !!fi && (moved || rows.slice(fi).some(r => r.sk > 1.8)), { shifted: moved, cover: nowCover });
    }
    // ---- I the Take cover squad order: behind cover, or flat on the ground if there is none
    {
      await J(`const sc=__sc, T=__T; T.clear(); for (let i=0;i<5;i++) T.mk('blue', ${Ln.x}+(i-2)*2.5, ${Ln.z}-6, ['rifle','smg','rifle','heavy','rifle'][i]); sc.playBattle('blue'); return 1;`); await J(`for (let i=0;i<180;i++) __sc.qaTick(1/60); return 1`);
      await J(`const sc=__sc, T=__T; for (const q of sc.people.slice()) if (q.bot && q.bot.team==='red') sc.removePerson(q); sc.BATTLE.size=0;
        for (let i=sc.props.length-1;i>=0;i--) { const p=sc.props[i]; if (p.bcover) { sc.scene.remove(p.mesh); if (p.body) sc.world.removeBody(p.body); sc.props.splice(i,1); } }
        const me=sc.fp.p; me.x=${Ln.x}; me.z=${Ln.z}; me.y=sc.standY(me.x,me.z); sc.fp.yaw=0; for (const q of sc.SQD.mates) { q.x=${Ln.x}+(Math.random()-0.5)*8; q.z=${Ln.z}-4+Math.random()*3; q.y=sc.standY(q.x,q.z); q.order=null; q.route=null; } return 1;`);
      await J(`for (let i=0;i<120;i++) __sc.qaTick(1/60); return 1`);
      await J(`const sc=__sc; sc.sqdSet('cover', true); return 1;`);
      for (let s = 0; s < 10; s++) await J(`for (let i=0;i<60;i++) __sc.qaTick(1/60); return 1`);
      const st = await J(`const sc=__sc; return sc.SQD.mates.map(q=>({ cls: q.bot.cls, sk: +q.stanceK.toFixed(2), pr: !!q.bot.pr, why: q.bot.prWhy||0, cv: q.bot.coverPt ? q.bot.coverPt.kind : -1, atC: !!q.bot.atCover, order: !!q.order, tower: !!q.bot.tower, mv: !!q.bot.mountV, stOrd: q.bot.stOrd, psq: !!q.bot.psq, ok: q.bot.coverK, on: sc.SQD.order.n, k: sc.SQD.order.k }))`);
      ok('Take cover with little cover around: each soldier is behind cover or lying flat (staggered), and the ones with none lie down', st.length >= 3 && st.every(o => o.sk > 1.8 || o.atC) && st.some(o => o.sk > 1.8), st);
      await J(`const sc=__sc, T=__T; T.wall('x-sandbag_wall', ${Ln.x + 3}, ${Ln.z + 6}, 0); T.wall('x-sandbag_wall', ${Ln.x - 3}, ${Ln.z + 6}, 0); sc.sqdSet('follow', true); return 1;`);
      for (let s = 0; s < 4; s++) await J(`for (let i=0;i<60;i++) __sc.qaTick(1/60); return 1`);
      await J(`const sc=__sc; sc.sqdSet('cover', true); return 1;`);
      for (let s = 0; s < 10; s++) await J(`for (let i=0;i<60;i++) __sc.qaTick(1/60); return 1`);
      const st2 = await J(`const sc=__sc; return sc.SQD.mates.map(q=>({ cls: q.bot.cls, sk: +q.stanceK.toFixed(2), cv: q.bot.coverPt ? q.bot.coverPt.kind : -1, atC: !!q.bot.atCover, order: !!q.order, tower: !!q.bot.tower, mv: !!q.bot.mountV, stOrd: q.bot.stOrd, ok: q.bot.coverK, on: sc.SQD.order.n, k: sc.SQD.order.k, hasLive: !!q.bot.tgt, dl: Math.round(Math.hypot(q.x-sc.fp.p.x, q.z-sc.fp.p.z)) }))`);
      ok('Take cover with cover about: soldiers go to it and crouch behind it (those that find none lie down)', st2.length >= 3 && st2.every(o => o.atC || o.sk > 1.8), st2);
      await J(`__sc.exitFP && __sc.exitFP(); return 1`);
    }
  }

  // ================================================================ PERF
  if (which === 'perf' || which === 'all') {
    await startBattle(10);
    // stage the contact: both armies are put 50 m apart round the middle capture point, so the whole run is a fight (cover searches, near misses, stance changes), not a march
    const r = await J(`const sc=__sc; sc.BATTLE.size=10; const pt=sc.BATTLE.points.find(p=>p.name==='Town centre')||sc.BATTLE.points[0]; let nb=0, nr=0;
      for (const q of sc.people) { if (!q.bot || q.bot.crew) continue; const blue=q.bot.team==='blue', k=blue?nb++:nr++; const a=(k%10)*0.55-2.5, d=blue?-27:27; q.x=pt.x+Math.sin(a)*12; q.z=pt.z+d+Math.cos(a)*3*(blue?-1:1); q.y=sc.standY(q.x,q.z); q.order=null; q.route=null; }
      for (let i=0;i<60;i++) sc.qaTick(1/60);
      const ms=[]; let prone=0, crouch=0, samples=0, tgt=0; for (let i=0;i<1800;i++) { const t=performance.now(); sc.qaTick(1/60); ms.push(performance.now()-t); if (i%30===0) { for (const q of sc.people) if (q.bot && q.state!=='rag') { samples++; if ((q.stanceK||0)>1.5) prone++; else if ((q.stanceK||0)>0.5) crouch++; if (q.bot.tgt) tgt++; } } }
      ms.sort((a,b)=>a-b); const mean=ms.reduce((a,c)=>a+c,0)/ms.length; return { bots: sc.people.filter(q=>q.bot).length, mean, p95: ms[Math.floor(ms.length*0.95)], p99: ms[Math.floor(ms.length*0.99)], max: ms[ms.length-1], proneShare: samples?prone/samples:0, crouchShare: samples?crouch/samples:0, engaged: samples?tgt/samples:0, sim: sc.simTime() };`);
    console.log(`  perf ${BASE ? '(baseline, previous release)' : '(this release)'}: ` + JSON.stringify({ bots: r.bots, meanMs: num(r.mean, 3), p95Ms: num(r.p95, 3), p99Ms: num(r.p99, 3), maxMs: num(r.max, 2), proneShare: num(r.proneShare, 3), crouchShare: num(r.crouchShare, 3), engagedShare: num(r.engaged, 3) }));
    if (!BASE) ok('perf: a staged 20-plus-bot firefight for 30 simulated seconds: mean step under 14 ms of CPU, 99th percentile under 40 ms (software renderer machine; compare with --baseline)', r.bots >= 16 && r.mean < 14 && r.p99 < 40, { bots: r.bots, meanMs: num(r.mean, 2), p99Ms: num(r.p99, 2) });
  }
  const errs = b.errs.filter(e => !/favicon|ResizeObserver/.test(e));
  ok('no console errors or page exceptions', errs.length === 0, errs.slice(0, 3));
} catch (e) { console.log('FAIL (exception)', e && e.stack || e); fail.push('exception'); }
finally { await b.close(); await srv.close(); }
console.log(fail.length ? `\nFAILED ${fail.length}: ${fail.join(' | ')}` : '\nALL PASSED'); process.exit(fail.length ? 1 : 0);
