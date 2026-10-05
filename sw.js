/* Squall Cove service worker. Touches ONLY its own caches (squall-cove-vN). Bump VERSION on each release. */
const VERSION = 'v5.8.0';
const CACHE = 'squall-cove-' + VERSION;
const MINE = /^squall-cove-v[\d.]+$/;
self.addEventListener('install', (e) => { self.skipWaiting(); e.waitUntil(caches.open(CACHE).then(c => c.addAll(['./', 'index.html', 'icon-192.png', 'icon-512.png']).catch(() => {}))); });
self.addEventListener('activate', (e) => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => MINE.test(k) && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', (e) => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== location.origin || !url.pathname.startsWith('/squall-cove/')) return;   // other apps and CDNs: not ours
  if (url.pathname.endsWith('/manifest.webmanifest')) return;                                                         // never cached, always fresh
  const own = () => caches.open(CACHE);
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req).then(r => { if (r.ok) own().then(c => c.put('index.html', r.clone())); return r; }).catch(() => own().then(c => c.match('index.html'))));
    return;
  }
  e.respondWith(own().then(c => c.match(req).then(hit => hit || fetch(req).then(r => { if (r.ok) c.put(req, r.clone()); return r; }))));
});
