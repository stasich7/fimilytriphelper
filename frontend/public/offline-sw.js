const APP_CACHE = "family-trip-helper-app-v1";
const API_CACHE = "family-trip-helper-api-v1";
const MEDIA_CACHE = "family-trip-helper-media-v1";

const APP_SHELL = [
  "/",
  "/family-trip-v4.png",
  "/family-trip-v5.png",
  "/chips/map-chip-1.png",
  "/chips/map-chip-2.png",
  "/chips/map-chip-3.png",
  "/chips/map-chip-4.png",
  "/chips/map-chip-5.png",
  "/chips/map-chip-6.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(APP_CACHE)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

async function cacheFirst(request, cacheName) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }

  const response = await fetch(request);
  const cache = await caches.open(cacheName);
  await cache.put(request, response.clone());
  return response;
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);

  try {
    const response = await fetch(request);
    if (response.ok || response.type === "opaque") {
      await cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    throw error;
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== "GET") {
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(networkFirst(request, APP_CACHE).catch(() => caches.match("/")));
    return;
  }

  if (url.pathname.startsWith("/api/v1/")) {
    event.respondWith(networkFirst(request, API_CACHE));
    return;
  }

  if (
    url.origin === self.location.origin &&
    (url.pathname.startsWith("/assets/") ||
      url.pathname.startsWith("/maps/") ||
      url.pathname.startsWith("/chips/") ||
      url.pathname.startsWith("/family-trip-"))
  ) {
    event.respondWith(cacheFirst(request, MEDIA_CACHE));
    return;
  }

  if (url.hostname === "storage.familytrip.stasich7.ru") {
    event.respondWith(networkFirst(request, MEDIA_CACHE));
  }
});
