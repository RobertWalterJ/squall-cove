/* Squall Cove service worker. Touches ONLY its own caches. Two kinds:
   squall-cove-vN        the page and icons. Replaced on each release (bump VERSION).
   squall-cove-assets-aN heavy, rarely changing files (assets/ and audio/). NOT replaced on a release, so a
                         release downloads about 1.5 MB, not 18 to 46 MB. Bump ASSETS only if an asset file
                         changes its CONTENT under the same name (this re-downloads everything once). */
const VERSION = 'v9.7.0';      // v9.7.0: AC-130 sensor station (gimballed camera locked on a ground point, Thermal / Night vision / Colour, three weapons, interior sound mix, Gunship operator role; the gunship now flies at about 520 m in a left-wing-down orbit and only a missile can hurt it). v9.6.0: AC-130 gunship (Vulcan bursts with spin-up and spin-down, Bofors strings, 105 mm howitzer every 6 to 8 s; per-surface impact sounds, near and far stems, voice budgets, prop drone and creak). v9.5.0: gunfire and explosion effects (travelling tracers by calibre, muzzle flashes, impacts per surface, shockwaves, lingering fires, horizon flashes). v9.4.0: phone edition push-ready (layout ladder, 48 px targets, tilt aim, wake lock, haptics, lost-graphics recovery, governor, touch tactical map). v9.3.0: stable asset cache split out (releases no longer re-download assets); phone edition. v9.2.0: static start menu, Lemnos real maps, cheats panel.
const ASSETS = 'a1';
const CACHE = 'squall-cove-' + VERSION;
const ACACHE = 'squall-cove-assets-' + ASSETS;
const MINE = /^squall-cove-(v[\d.]+|assets-a[\d.]+)$/;
const isAsset = (p) => /\/squall-cove\/(assets|audio)\//.test(p);
self.addEventListener('install', (e) => { self.skipWaiting(); e.waitUntil(caches.open(CACHE).then(c => c.addAll(['./', 'index.html', 'icon-192.png', 'icon-512.png']).catch(() => {})).then(() => caches.open(ACACHE)).then(c => Promise.all(['assets/map_lemnos_myrina_thumb.jpg', 'assets/map_lemnos_mudros_thumb.jpg', 'assets/map_lemnos_airport_thumb.jpg'].map(u => c.match(u).then(h => h || c.add(u)).catch(() => {}))))); });      // thumbs are fetched once, never again on a release
self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    const ks = (await caches.keys()).filter(k => MINE.test(k));
    const ac = await caches.open(ACACHE);
    // One-time move: assets held by older per-version caches are copied into the stable cache before those caches go.
    for (const k of ks) {
      if (k === CACHE || k === ACACHE || !/^squall-cove-v/.test(k)) continue;
      try { const old = await caches.open(k); for (const rq of await old.keys()) { if (isAsset(new URL(rq.url).pathname) && !(await ac.match(rq))) { const rs = await old.match(rq); if (rs) await ac.put(rq, rs); } } } catch (err) { }
    }
    await Promise.all(ks.filter(k => k !== CACHE && k !== ACACHE).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});
self.addEventListener('fetch', (e) => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== location.origin || !url.pathname.startsWith('/squall-cove/')) return;   // other apps and CDNs: not ours
  if (url.pathname.endsWith('/manifest.webmanifest')) return;                                                         // never cached, always fresh
  const bucket = () => caches.open(isAsset(url.pathname) ? ACACHE : CACHE);
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req).then(r => { if (r.ok) caches.open(CACHE).then(c => c.put('index.html', r.clone())); return r; }).catch(() => caches.open(CACHE).then(c => c.match('index.html'))));
    return;
  }
  e.respondWith(bucket().then(c => c.match(req).then(hit => hit || fetch(req).then(r => { if (r.ok) c.put(req, r.clone()); return r; }))));
});
