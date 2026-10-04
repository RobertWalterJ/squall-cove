/* Squall Cove service worker: cache-first so it installs and runs offline. Bump V on each release. */
const V = 'sc-v4.3.3';
self.addEventListener('install', (e) => { self.skipWaiting(); e.waitUntil(caches.open(V).then(c => c.addAll(['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png']).catch(() => {}))); });
self.addEventListener('activate', (e) => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  const nav = e.request.mode === 'navigate';
  e.respondWith((nav ? fetch(e.request).catch(() => caches.match('index.html')) : caches.match(e.request).then(hit => hit || fetch(e.request))).then(async (r) => {
    if (r && (r.ok || r.type === 'opaque') && !nav) { const c = await caches.open(V); c.put(e.request, r.clone()).catch(() => {}); }
    else if (r && r.ok && nav) { const c = await caches.open(V); c.put('index.html', r.clone()).catch(() => {}); }
    return r;
  }));
});
