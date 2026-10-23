/**
 * KalmiPrep Progressive Service Worker
 * Caches core vendor scripts, styles, and web fonts for instant page loads.
 * Protects test sessions and secure areas by passing them directly to the network.
 */

const CACHE_NAME = 'kalmiprep-static-v3';

const STATIC_ASSETS = [
  '/static/css/styles.css',
  '/static/vendor/katex/katex.min.css',
  '/static/vendor/katex/katex.min.js',
  '/static/vendor/katex/contrib/auto-render.min.js',
  '/static/vendor/gsap/gsap.min.js',
  '/static/vendor/htmx/htmx.min.js',
  '/static/vendor/lucide/lucide.min.js',
  '/static/vendor/mathjs/math.min.js',
  '/static/js/calculator/validator.js',
  '/static/js/calculator/formatter.js',
  '/static/js/calculator/engine.js',
  '/static/js/calculator/memento.js',
  '/static/js/calculator/controller.js',
  '/static/js/store.js',
  '/static/js/nav_orb.js',
  '/static/js/prefetch.js'
];

// URLs that MUST always bypass cache
const BYPASS_ROUTES = [
  /\/practice\/session\//,
  /\/admin\//,
  /\/accounts\//
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.warn('[SW] Non-critical cache preload warning:', err);
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Only handle GET requests from the same origin
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }

  // Bypass cache for active exam sessions, admin, and authentication
  if (BYPASS_ROUTES.some((route) => route.test(url.pathname))) {
    return;
  }

  // Static assets (CSS, JS, Fonts, Images): Cache-First strategy
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(event.request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseToCache);
            });
          }
          return networkResponse;
        });
      })
    );
    return;
  }

  // HTML pages: Network-First with Cache Fallback
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // If valid response, clone into cache for offline view
          if (response && response.status === 200) {
            const responseToCache = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseToCache);
            });
          }
          return response;
        })
        .catch(() => {
          return caches.match(event.request);
        })
    );
  }
});
