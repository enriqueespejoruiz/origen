/* Origen — service worker. Red primero para lo propio (los deploys se ven al instante);
   cache solo como respaldo offline para la captura en campo. */
const CACHE = 'origen-v2';
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
  if (req.method !== 'GET') return;                         // nunca interceptar acciones (POST)
  const url = new URL(req.url);
  const sameOrigin = url.origin === location.origin;

  // Datos y acciones: siempre red, sin cache.
  if (sameOrigin && /^\/(api|capture|lots|consignments|lead|intake|healthz|auth|share)\b/.test(url.pathname)) return;

  // Páginas y estáticos propios: RED PRIMERO, cache de respaldo (deploys instantáneos + offline).
  if (sameOrigin) {
    e.respondWith(
      fetch(req).then(r => { if (r.ok) { const cp = r.clone(); caches.open(CACHE).then(c => c.put(req, cp)); } return r; })
                .catch(() => caches.match(req).then(c => c || (req.mode === 'navigate' ? caches.match('/capturar') : undefined)))
    );
    return;
  }

  // Terceros (fuentes): cache primero.
  e.respondWith(
    caches.match(req).then(cached => cached || fetch(req).then(r => {
      if (r.ok) { const cp = r.clone(); caches.open(CACHE).then(c => c.put(req, cp)); }
      return r;
    }))
  );
});
