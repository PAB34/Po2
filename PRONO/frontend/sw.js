/* Service worker minimal — sert uniquement à satisfaire les critères
 * d'installabilité PWA (Chrome/Android). Ne met JAMAIS en cache l'API,
 * le HTML, le JS ou le CSS : l'app affiche des données live et change
 * souvent, un cache agressif causerait des bugs de version périmée.
 * Seules les icônes (vraiment statiques) sont mises en cache. */
const CACHE_NAME = "prono-static-v2";
const STATIC_ASSETS = [
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/maskable-512.png",
];

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)).catch(() => {})
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  // Icônes : cache-first (vraiment statiques, jamais de raison de changer).
  if (url.pathname.startsWith("/icons/")) {
    event.respondWith(
      caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
    return;
  }
  // Tout le reste (HTML, JS, CSS, /api/*) : toujours le réseau, jamais de cache.
  event.respondWith(fetch(event.request));
});
