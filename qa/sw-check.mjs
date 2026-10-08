// Service worker check in a real headless Chrome (rule 7 and 8 in EDITION-RULES.md). usage: node qa/sw-check.mjs
// 1. an "old release" cache holding an asset, plus another app's cache and a lookalike cache, are put on the origin
// 2. the real sw.js is registered: its activate must move the asset into squall-cove-assets-a1, delete only the old squall-cove-v* cache,
//    and leave the other app's cache, the lookalike cache and the localStorage keys alone
// 3. a second "release" (same sw.js with a higher VERSION) is served and installed: the page cache is replaced and NO file under assets/ or audio/ is fetched again
// 4. offline: the page cache serves the app shell with the network off
import fs from 'fs'; import path from 'path';
import { ROOT, sleep, startServer, launch } from './harness.mjs';
const sw = fs.readFileSync(path.join(ROOT, 'sw.js'), 'utf8'), cur = /const VERSION = '(v[\d.]+)'/.exec(sw)[1], next = 'v' + (cur.slice(1).split('.').map((n, i) => i === 2 ? +n + 1 : n).join('.'));
const srv = await startServer(ROOT, 0, {}); const O = `http://127.0.0.1:${srv.port}/squall-cove/`; const fails = [], ok = [];
const check = (c, good, bad) => (c ? ok.push(good) : fails.push(bad));
const b = await launch({ w: 800, h: 600, mobile: false });
try {
  await b.send('Page.navigate', { url: O + 'qa/sw-probe.html' }); await sleep(1500);
  await b.ev('seedOld()');
  const reg = await b.ev(`register('/squall-cove/sw.js')`); await sleep(800);
  const s1 = await b.ev('snap()');
  check(/sw\.js activated/.test(reg || ''), 'sw.js registered and activated in Chrome', 'sw.js did not activate: ' + reg);
  check(s1.keys.includes('squall-cove-' + cur) && s1.keys.includes('squall-cove-assets-a1'), `caches squall-cove-${cur} and squall-cove-assets-a1 exist`, 'expected caches missing: ' + s1.keys.join(', '));
  check(!s1.keys.includes('squall-cove-v9.2.0'), 'the old per-version cache was deleted', 'the old squall-cove-v9.2.0 cache is still there');
  check(s1.moved === 'OLD ASSET', 'the asset was moved into the stable assets cache before the old cache went', 'the old asset was not migrated (got ' + s1.moved + ')');
  check(s1.other === 'NOT MINE' && s1.keys.includes('hinterland-v3'), "another app's cache (hinterland-v3) is untouched", "another app's cache was changed or deleted");
  check(s1.notes === 'similar name, not mine', 'a lookalike cache (squall-cove-notes) is untouched: the MINE regex is exact', 'the lookalike cache squall-cove-notes was touched');
  check(s1.ls[0] === 'keep me' && s1.ls[1] === '{"keep":1}', 'localStorage keys are untouched', 'a localStorage key was lost');
  // second release: same file, higher VERSION
  srv.setOverride('/sw.js', sw.replace(`'${cur}'`, `'${next}'`));
  const before = srv.stats.hits.length;
  await b.ev(`window.__want='squall-cove-${next}'; update()`); await sleep(1500);
  const s2 = await b.ev('snap()'), hits = srv.stats.hits.slice(before).filter(h => /\/squall-cove\/(assets|audio)\//.test(h));
  check(s2.keys.includes('squall-cove-' + next) && !s2.keys.includes('squall-cove-' + cur), `release ${next}: new page cache in, ${cur} deleted`, `after the update the caches are: ${s2.keys.join(', ')}`);
  check(s2.keys.includes('squall-cove-assets-a1') && JSON.stringify(s2.assets) === JSON.stringify(s1.assets), 'the assets cache is the same after the release', 'the assets cache changed on a release');
  check(hits.length === 0, 'the release fetched no file from assets/ or audio/', 'the release re-fetched: ' + hits.join(', '));
  // offline
  await b.send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: 0, uploadThroughput: 0 });
  await b.send('Page.navigate', { url: O + 'index.html?menu=1' }); await sleep(2500);
  const off = await b.ev("({ title: document.title, boot: !!document.getElementById('boot'), len: document.documentElement.outerHTML.length })");
  check(off && off.boot && off.len > 100000, 'offline: the app shell opens from the page cache', 'offline the app shell did not open: ' + JSON.stringify(off));
} catch (e) { fails.push('harness: ' + (e.stack || e)); }
await b.close(); await srv.close();
console.log('\n== sw-check'); for (const o of ok) console.log('  ok   ' + o); for (const f of fails) console.log('  FAIL ' + f); console.log(fails.length ? `\nsw-check: ${fails.length} failure(s)` : '\nsw-check: all green'); process.exit(fails.length ? 1 : 0);
