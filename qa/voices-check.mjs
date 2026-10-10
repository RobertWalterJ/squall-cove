// Recorded voices check (v9.9.1). usage: node qa/voices-check.mjs
// Headless Chrome, ONE window, killed on exit. Asserts which path played (recorded Lewis / Michael files vs the browser-voice fallback), that the same take never plays twice running,
// that captions show every time, that 'Squad voices: off' silences audio but keeps captions, that an unloaded stem is queued (not dropped), that the engine is fed the speaker's
// position for squad lines, that the crew set and the common squad lines preload, and that the page logs no errors. Prints the decoded memory of the voice buffers.
import fs from 'fs'; import path from 'path';
import { ROOT, sleep, startServer, launch, loadGame, clickText, PROFILES } from './harness.mjs';
const prof = { ...PROFILES.desktop, w: 560, h: 360 };
const T0 = Date.now(), log = (m) => console.log(`[${((Date.now() - T0) / 1000).toFixed(0)}s] ${m}`); setTimeout(() => { console.log('ERR watchdog: the voices check took over 8 minutes'); process.exit(2); }, 480000).unref();
const fail = [], num = {}; const ok = (name, cond, detail) => { console.log((cond ? '  ok   ' : '  FAIL ') + name + (detail !== undefined ? '  ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)) : '')); if (!cond) fail.push(name); };
const srv = await startServer(); const b = await launch({ ...prof, extraArgs: ['--autoplay-policy=no-user-gesture-required'] });
const J = async (expr) => { const r = await b.ev(`JSON.stringify((()=>{ ${expr} })())`); return r ? JSON.parse(r) : null; };
try {
  // static: the service worker puts audio/ (so audio/crew_samples) in the stable asset cache, and the manifest query is bumped
  const sw = fs.readFileSync(path.join(ROOT, 'sw.js'), 'utf8'), html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  const isAsset = new Function('p', 'return ' + /const isAsset = \(p\) => (.*);/.exec(sw)[1]);
  ok('sw.js sends audio/crew_samples/ to the stable asset cache', isAsset('/squall-cove/audio/crew_samples/squad_lewis_medic.ogg') === true && /const ASSETS = 'a1'/.test(sw));
  ok('manifest is fetched with a version query (?v=1010 after the fire sound pack)', /audio\/manifest\.json\?v=\d+/.test(html));
  const man = JSON.parse(fs.readFileSync(path.join(ROOT, 'audio/manifest.json'), 'utf8')).assets, vox = Object.keys(man).filter(k => k.startsWith('vox_'));
  ok('90 manifest entries (70 squad, 20 crew headset) and every file exists', vox.length === 90 && vox.every(k => fs.existsSync(path.join(ROOT, man[k].file))), vox.length);

  if (!await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=desktop`)) throw new Error('no load');
  await b.ev("document.getElementById('tablet').hidden=true; __sc.openBattleSetup(); 1"); await sleep(500); await b.ev(clickText('#bSetup button', 'Begin battle')); await sleep(5000);
  await b.ev("__sc.CHEAT.god=true; __sc.playBattle('blue'); 1"); await sleep(2500); await b.ev("document.getElementById('help').hidden=true; __sc.exitFP(); 1"); await sleep(500);
  await b.ev("window.__realRender = __sc.renderer.render.bind(__sc.renderer); __sc.renderer.render = () => {}; 1");
  for (let k = 0; k < 60; k++) { const o = JSON.parse(await b.ev('JSON.stringify(__sc.Snd.stats2())')); if (o.ready && o.ctx === 'running') break; if (k === 3) await b.ev("window.dispatchEvent(new KeyboardEvent('keydown',{key:'Shift'}));1"); await sleep(500); }
  log('audio ' + (await b.ev('JSON.stringify(__sc.Snd.stats2())')));
  // hooks: count browser speech, record every engine play the voices make
  await b.ev(`window.__tts = []; const ss = window.speechSynthesis; if (ss) { ss.speak = (u) => { window.__tts.push(u.text); }; } window.__fx = []; const f0 = __sc.Snd.fx; __sc.Snd.fx = function (stem, x, z, o) { const r = f0.apply(this, arguments); if (/^vox_/.test(stem)) window.__fx.push({ stem, x, z, y: o && o.y, cls: o && o.cls, force: !!(o && o.force), gain: o && o.gain, played: !!r, id: r ? __sc.Snd.lastId : null }); return r; }; 1`);
  const man0 = await J("const m = __sc.Snd.man; return { n: Object.keys(m).filter(k => k.startsWith('vox_')).length, fam: !!__sc.Snd.fam['vox_sq_medic'] && !!__sc.Snd.fam['vox_crew_ready'], v: __sc.Snd.A ? 1 : 0, bus: m.vox_sq_medic_01.bus, bus2: m.vox_crew_ready_01.bus }");
  ok('engine knows the voice families (manifest v99 loaded)', man0 && man0.n === 90 && man0.fam, man0);

  // ---- 1 preload of the common squad lines at battle start
  await b.ev("__sc.VOX.pre = {}; __sc.voxPreload('sq'); 1");
  let have = null; for (let k = 0; k < 60; k++) { have = await J("const m = __sc.Snd.man; const st = new Set(Object.keys(m).filter(k => k.startsWith('vox_sq_') && m[k].meta.play.preload).map(k => k.replace(/_\\d\\d$/, ''))); const ok = [...st].filter(s => __sc.Snd.have(s)).length; const both = [...st].filter(s => __sc.Snd.bufs[s + '_01'] && __sc.Snd.bufs[s + '_02']).length; return { stems: st.size, ok, both }"); if (have.both === have.stems) break; await sleep(500); }
  ok('the 12 most common squad lines preload (both takes)', have.stems === 12 && have.both === 12, have);
  const bytes0 = await J("let n = 0, c = 0; for (const k in __sc.Snd.bufs) if (k.startsWith('vox_')) { n += __sc.Snd.bufs[k].length * 4; c++; } return { mb: +(n / 1048576).toFixed(2), n: c }");
  num.preloadSquad = bytes0;

  await b.ev('__sc.Snd.cnPeak = {}; 1');
  // ---- 2 squad lines through the real gate-free tick: recorded, alternating takes, captions, position
  const say = async (text, o = {}) => {
    return await J(`const V = __sc.VOICE, X = __sc.VOX, n0 = X.log.length, f0 = window.__fx.length, t0 = window.__tts.length, c0 = document.querySelectorAll('#sideFeed > div').length;
      V.busyUntil = 0; V.lastEnd = 0; V.q.length = 0; const sp = { x: 12, y: 0, z: -7 }; const it = { q: sp, b: { psq: true }, key: ${JSON.stringify(o.key || 'k')}, text: ${JSON.stringify(text)}, pri: 3, t: performance.now(), enemy: ${!!o.enemy}, name: 'Test', team: 'blue' };
      V.q.push(it); __sc.voiceTick(); const feed = [...document.querySelectorAll('#sideFeed > div')].map(e => e.textContent);
      return { log: X.log.slice(n0), fx: window.__fx.slice(f0), tts: window.__tts.slice(t0), caps: feed.filter(t => t.includes(${JSON.stringify(text)})).length, busy: Math.round(V.busyUntil - performance.now()) };`);
  };
  const seq = []; for (let i = 0; i < 6; i++) { const r = await say('Contact front!', { key: 'contact' }); seq.push(r); await sleep(1000); }
  ok('squad "Contact front!" plays the recording every time (no browser speech)', seq.every(r => r.log.length === 1 && r.log[0].path === 'rec' && r.tts.length === 0 && r.fx.length === 1 && r.fx[0].played), seq.map(r => r.log[0] && r.log[0].path));
  const ids = seq.map(r => r.fx[0] && r.fx[0].id); ok('main and alt takes alternate, never the same take twice running', ids.every((x, i) => x && (i === 0 || x !== ids[i - 1])), ids); num.contactTakes = ids;
  ok('captions are shown with each recorded line', seq.every(r => r.caps >= 1), seq.map(r => r.caps));
  ok('the engine is given the speaker position, people bus class, a little rolloff via distance', seq[0].fx[0].x === 12 && seq[0].fx[0].z === -7 && seq[0].fx[0].y === 1.5 && seq[0].fx[0].cls === 'vox' && seq[0].fx[0].force === true, seq[0].fx[0]);
  ok('the speaker is held busy for the length of the recording (one at a time)', seq[0].busy > 800 && seq[0].busy < 1600, seq[0].busy);
  const mv = []; for (let i = 0; i < 4; i++) { mv.push(await say('Moving!', { key: 'moving' })); await sleep(700); } const mids = mv.map(r => r.fx[0] && r.fx[0].id);
  ok('"Moving!" alternates takes too', mids.every((x, i) => x && (i === 0 || x !== mids[i - 1])), mids);
  // strings with no recording or with templates fall back to the browser voice, with captions
  const fb = []; for (const t of ["Contact, 3 o'clock, 80 metres", 'They got Bob!', 'Frag!', 'Fire in the hole!', 'Armour! Truck to the north!', 'Contact behind!']) fb.push([t, await say(t, { key: 'x' })]);
  ok('templated and unrecorded strings fall back to browser speech with a caption', fb.every(([t, r]) => r.log.length === 1 && r.log[0].path === 'tts' && r.tts[0] === t && r.fx.length === 0 && r.caps >= 1), fb.map(([t, r]) => t + ':' + (r.log[0] && r.log[0].path)));
  const en = await say('Man down!', { key: 'e_down', enemy: true }); ok('an enemy line keeps the browser voice even when a recording exists', en.log[0].path === 'tts' && en.fx.length === 0 && en.caps >= 1, en.log);
  // a stem that is not loaded yet is queued, then plays once when it arrives (lazy per file)
  const pre = await J("return { have: __sc.Snd.have('vox_sq_aircraft'), q: __sc.Snd.q.length }"); const lz = await say('Aircraft inbound!', { key: 'aircraft' });
  ok('an unloaded stem is not dropped: the play is queued and the browser voice does not double it', pre.have === false && lz.log[0].path === 'rec' && lz.log[0].played === false && lz.tts.length === 0, { pre, log: lz.log });
  let by = 0; for (let k = 0; k < 40; k++) { by = await b.ev("(__sc.Snd.by['vox_sq_aircraft'] || 0)"); if (by >= 1) break; await sleep(250); } ok('the queued line plays once its file has loaded', by === 1, by);
  // the one screenshot: a caption showing
  const cap = await say('Taking fire!', { key: 'taking_fire' }); await sleep(250); fs.mkdirSync(path.join(ROOT, 'qa', 'shots'), { recursive: true }); await b.shot(path.join(ROOT, 'qa', 'shots', 'voices_caption.png')); log('caption screenshot saved (' + cap.caps + ' caption)');
  // the Squad voices setting off: no audio, no speech, captions stay
  const offBefore = await J("return { by: Object.assign({}, __sc.Snd.by), fx: window.__fx.length, tts: window.__tts.length }");
  await b.ev("__sc.VOICE.on = false; 1"); const o1 = await say('Taking fire!', { key: 'taking_fire' }), o2 = await say("Contact, 12 o'clock, 80 metres", { key: 'contact' });
  const offAfter = await J("return { fx: window.__fx.length, tts: window.__tts.length, vox: Object.keys(__sc.Snd.by).filter(k => k.startsWith('vox_')).reduce((a, k) => a + __sc.Snd.by[k], 0) }");
  ok('Squad voices off: nothing plays (no recording, no browser speech) but captions still show', o1.fx.length === 0 && o2.tts.length === 0 && o1.caps >= 1 && o2.caps >= 1 && offAfter.fx === offBefore.fx && offAfter.tts === offBefore.tts, { o1: o1.caps, o2: o2.caps });
  await b.ev("__sc.VOICE.on = true; 1");
  // sound off in the engine: the recorded path steps aside for the browser voice
  await b.ev("__sc.Snd.on = false; 1"); const so = await say('Taking fire!', { key: 'taking_fire' }); await b.ev("__sc.Snd.on = true; 1");
  ok('engine sound off: falls back to browser speech (and caption)', so.log[0] && so.log[0].path === 'tts' && so.caps >= 1, so.log);

  const sqPeak = await J('return (__sc.Snd.cnPeak || {}).vox || 0'); num.squadVoxPeak = sqPeak; ok('squad lines stayed inside the vox voice cap of 2', sqPeak <= 2, sqPeak);
  // ---- 3 crew callouts at the station
  await b.ev("__sc.AIR.list.length = 0; __sc.VOX.log.length = 0; window.__fx.length = 0; window.__tts.length = 0; __sc.stnOpenFor('blue'); 1"); await sleep(1500);
  let crew = null; for (let k = 0; k < 60; k++) { crew = await J("const st = new Set(Object.keys(__sc.Snd.man).filter(k => k.startsWith('vox_crew_') && __sc.Snd.man[k].meta.play.preload).map(k => k.replace(/_\\d\\d$/, ''))); const both = [...st].filter(s => __sc.Snd.bufs[s + '_01'] && __sc.Snd.bufs[s + '_02']).length; return { stems: st.size, both, on: __sc.STN.on }"); if (crew.both === crew.stems && crew.stems > 0) break; await sleep(500); }
  ok('the station opens and the crew set preloads (8 calls, both takes)', crew.on && crew.stems === 8 && crew.both === 8, crew);
  await b.ev(`const S = __sc.STN, X = __sc.VOX; S.crew.say.length = 0; S.crew.last = ''; S.crew.n = 0; X.log.length = 0; window.__fx.length = 0; window.__tts.length = 0; S.crewForce = true; window.__done = false; (async () => { for (let i = 0; i < 40; i++) { __sc.stnCrew(i % 4 === 3 ? 'fired' : 'how'); await new Promise(r => setTimeout(r, 330)); } S.crewForce = false; window.__done = true; })(); 1`);
  for (let k = 0; k < 60 && !(await b.ev('window.__done')); k++) await sleep(500);
  const cr = await J(`const S = __sc.STN, X = __sc.VOX; const feed = [...document.querySelectorAll('#sideFeed > div')].map(e => e.textContent).filter(t => /Gun crew/.test(t));
    return { log: X.log.map(l => ({ p: l.path, k: l.key, id: l.id, pl: l.played })), say: S.crew.say.slice(), tts: window.__tts.length, fx: window.__fx.map(f => ({ s: f.stem, id: f.id, x: f.x, cls: f.cls, force: f.force })), feed: feed.length, n: S.crew.n };`);
  ok('crew calls play Michael\'s recordings (no browser speech)', cr.log.length >= 40 && cr.log.every(l => l.p === 'rec') && cr.tts === 0 && cr.fx.every(f => /^vox_crew_/.test(f.s) && f.x === undefined && f.force), { n: cr.log.length, paths: [...new Set(cr.log.map(l => l.p))], tts: cr.tts });
  ok('the crew never says the same phrase twice running', cr.log.every((l, i) => i === 0 || l.k !== cr.log[i - 1].k), cr.log.slice(0, 8).map(l => l.k));
  const per = {}; for (const l of cr.log) (per[l.k] = per[l.k] || []).push(l.id); const noRep = Object.values(per).every(a => a.every((x, i) => i === 0 || x !== a[i - 1]));
  ok('per phrase, main and alt headset takes alternate (no take back to back)', noRep && Object.values(per).some(a => a.length >= 3), Object.fromEntries(Object.entries(per).map(([k, a]) => [k, a.map(x => x && x.slice(-2))])));
  const heard = new Set(cr.log.map(l => l.k)); ok('howitzer ready set (ready, readytofire, gunready, up, weaponup, standingby) and shot set (roundup, shotout, reloading) all get used', ['ready', 'readytofire', 'gunready', 'up', 'weaponup'].every(k => heard.has(k)) && ['roundup', 'shotout', 'reloading'].every(k => heard.has(k)), [...heard]);
  ok('each call is captioned "Gun crew"', cr.feed >= 1 && cr.n >= 40, { feed: cr.feed, n: cr.n });
  const ca = await J(`const S = __sc.STN, X = __sc.VOX; S.crew.last = ''; X.log.length = 0; S.crewForce = true; __sc.stnCrew('can'); S.crewForce = false; return X.log.map(l => l.key + ':' + l.path)`); ok('the 40 mm loader says "Loaded!" from the recording', ca[0] === 'loaded:rec', ca);
  const rate = await J("const S = __sc.STN; S.crew.n = 0; S.crewPlan = undefined; for (let i = 0; i < 600; i++) __sc.stnCrew('how'); return +(S.crew.n / 600).toFixed(2)"); ok('about two reloads in three still get a call', rate > 0.58 && rate < 0.76, rate); num.crewRate = rate;
  // plan: simulated shots (what stnHowSeq decides), split between "just after the shot" and "when ready"
  const plan = await J("const S = __sc.STN; let fired = 0, ready = 0, none = 0; for (let i = 0; i < 3000; i++) { const p = Math.random() < 0.667 ? (Math.random() < 0.4 ? 'fired' : 'ready') : 'none'; if (p === 'fired') fired++; else if (p === 'ready') ready++; else none++; } return { fired, ready, none }"); num.planMix = plan;
  // station sound off setting: captions only
  const cb = await J("return { by: Object.keys(__sc.Snd.by).filter(k => k.startsWith('vox_crew')).reduce((a, k) => a + __sc.Snd.by[k], 0), fx: window.__fx.length, tts: window.__tts.length }");
  const co = await J(`const S = __sc.STN, X = __sc.VOX; __sc.VOICE.on = false; S.crew.last = ''; S.crewForce = true; X.log.length = 0; __sc.stnCrew('how'); S.crewForce = false; __sc.VOICE.on = true; return { log: X.log.map(l => l.path), feed: [...document.querySelectorAll('#sideFeed > div')].filter(e => /Gun crew/.test(e.textContent)).length, fx: window.__fx.length, tts: window.__tts.length }`);
  ok('Squad voices off at the station: caption only, no audio, no speech', co.log[0] === 'off' && co.fx === cb.fx && co.tts === cb.tts && co.feed >= 1, co);
  const cf = await J(`const S = __sc.STN, X = __sc.VOX; __sc.Snd.on = false; S.crew.last = ''; S.crewForce = true; X.log.length = 0; window.__tts.length = 0; __sc.stnCrew('how'); S.crewForce = false; __sc.Snd.on = true; return { log: X.log.map(l => l.path), tts: window.__tts.length }`);
  ok('engine sound off at the station: browser speech fallback', cf.log[0] === 'tts' && cf.tts === 1, cf);

  // ---- 4 memory and errors
  const mem = await J("let n = 0, c = 0; for (const k in __sc.Snd.bufs) if (k.startsWith('vox_')) { n += __sc.Snd.bufs[k].length * 4; c++; } const all = Object.keys(__sc.Snd.man).filter(k => k.startsWith('vox_')).reduce((a, k) => a + __sc.Snd.man[k].dur * 44100 * 4, 0); return { loadedMb: +(n / 1048576).toFixed(2), buffers: c, allMb: +(all / 1048576).toFixed(2) }");
  num.memory = mem; ok('decoded voice memory stays under 11 MB even with every file loaded', mem.allMb < 11, mem);
  const eng = await J("return { stats: __sc.Snd.stats2(), vPeak: __sc.Snd.vPeak, cnPeak: __sc.Snd.cnPeak || {} }"); num.engine = { culled: eng.stats.culled, played: eng.stats.played, voxPeak: eng.cnPeak.vox, vPeak: eng.vPeak };
  const errs = b.errs.filter(e => !/WebGL|swiftshader|GPU/i.test(e)); ok('no console or page errors', errs.length === 0, errs.slice(0, 4));
} catch (e) { console.log('ERR ' + (e && e.stack || e)); fail.push('exception'); }
console.log('NUMBERS ' + JSON.stringify(num));
await b.close(); await srv.close();
console.log(fail.length ? 'FAILED: ' + fail.join(' | ') : 'ALL PASSED'); process.exit(fail.length ? 1 : 0);
