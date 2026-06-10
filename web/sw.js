/* Origen — service worker (app-shell offline para la captura en campo) */
const CACHE = 'origen-v1';
const SHELL = ['/capturar', '/manifest.webmanifest', '/static/icon-192.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;                    // nunca interceptar la captura/sync (POST)
  const url = new URL(req.url);
  // El API siempre va directo a la red (captura, lotes, dossier, leads):
  if (url.origin === location.origin && /^\/(capture|lots|lead|intake|healthz)/.test(url.pathname)) return;

  if (req.mode === 'navigate') {                       // páginas: red primero, cache de respaldo
    e.respondWith(
      fetch(req).then(r => { const cp = r.clone(); caches.open(CACHE).then(c => c.put(req, cp)); return r; })
                .catch(() => caches.match('/capturar'))
    );
    return;
  }
  // estáticos / fuentes: cache primero, luego red
  e.respondWith(
    caches.match(req).then(cached => cached || fetch(req).then(r => {
      const ok = r.ok && (url.origin === location.origin || url.host.includes('gstatic') || url.host.includes('googleapis'));
      if (ok) { const cp = r.clone(); caches.open(CACHE).then(c => c.put(req, cp)); }
      return r;
    }).catch(() => cached))
  );
});
