/* Origen — service worker. Red primero para lo propio (los deploys se ven al instante);
   cache solo como respaldo offline para la captura en campo. */
const CACHE = 'origen-v3';
const SHELL = ['/capturar', '/manifest.webmanifest', '/static/icon-192.png'];
const CANONICAL = 'https://origen-711831043664.us-central1.run.app';
// Una sola URL: en cualquier otro origen (alias de Cloud Run), el SW se autodestruye
// y deja pasar la red para que el redirect 308 del servidor lleve al canónico.
const FOREIGN = location.origin !== CANONICAL && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1';

self.addEventListener('install', e => {
  if (FOREIGN) { self.skipWaiting(); return; }
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  if (FOREIGN) {
    e.waitUntil(
      caches.keys().then(ks => Promise.all(ks.map(k => caches.delete(k))))
        .then(() => self.registration.unregister())
        .then(() => self.clients.matchAll({ type: 'window' }))
        .then(cs => cs.forEach(c => c.navigate(CANONICAL + new URL(c.url).pathname)))
    );
    return;
  }
  e.waitUntil(
    caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if (FOREIGN) return;                                      // origen alias: red directa (redirige el servidor)
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
