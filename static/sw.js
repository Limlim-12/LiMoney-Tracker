// 1. Increment this version number every time you push a big update!
const CACHE_NAME = "limoney-v2";  // changed from v1 to v2

const ASSETS = [
  "/",
  "/static/design.css",
  "/static/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];

// Install: Cache files
self.addEventListener("install", (event) => {
  self.skipWaiting(); // Force this new service worker to become active immediately
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)),
  );
});

// Activate: Clean up old caches (The Fix!)
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log("Deleting old cache:", key);
            return caches.delete(key); // Delete v1 if we are now on v2
          }
        })
      );
    })
  );
  self.clients.claim(); // Take control of all open tabs immediately
});

// Fetch: Serve from cache, falling back to network
self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    }),
  );
});