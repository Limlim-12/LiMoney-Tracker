const CACHE_NAME = "limoney-v3";
const STATIC_ASSETS = [
  "/static/design.css",
  "/static/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];

// Install: Cache only the static assets (CSS, Images), NOT the HTML pages
self.addEventListener("install", (event) => {
  self.skipWaiting(); // Force activation
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .catch((error) => {
        console.warn("Service worker install cache failed:", error);
      })
  );
});

// Activate: Delete old caches immediately
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

// Fetch: The Smart Strategy
self.addEventListener("fetch", (event) => {
  const { request } = event;

  // 1. Only handle GET requests
  if (request.method !== "GET") return;

  // 2. Ignore cross-origin requests (Google Fonts, etc.)
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // 3. NETWORK ONLY for Navigations (The Fix!)
  // This ensures the user ALWAYS gets the latest HTML from the server.
  if (request.mode === "navigate") {
    event.respondWith(fetch(request));
    return;
  }

  // 4. Check if it's a static file (CSS, JS, Image)
  const isStaticRequest =
    url.pathname.startsWith("/static/") ||
    ["style", "script", "image", "font"].includes(request.destination);

  // 5. If it's NOT static (e.g., API calls), go to Network
  if (!isStaticRequest) {
    event.respondWith(fetch(request));
    return;
  }

  // 6. Stale-While-Revalidate for Static Assets
  // Serve from cache first, but update the cache in the background
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(request).then((networkResponse) => {
        const clone = networkResponse.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        return networkResponse;
      });
    })
  );
});