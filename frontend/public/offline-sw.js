const APP_CACHE = "family-trip-helper-app-v1";
const API_CACHE = "family-trip-helper-api-v1";
const MEDIA_CACHE = "family-trip-helper-media-v1";
const NETWORK_TIMEOUT_MS = 3000;

const APP_SHELL = [
  "/",
  "/manifest.webmanifest",
  "/favicon.svg",
  "/favicon-32.png",
  "/apple-touch-icon.png",
  "/icon-192.png",
  "/icon-512.png",
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
    const response = await fetchWithTimeout(request, NETWORK_TIMEOUT_MS);
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

async function fetchWithTimeout(request, timeoutMs) {
  const controller = new AbortController();
  const timeoutID = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(request, { signal: controller.signal });
  } finally {
    clearTimeout(timeoutID);
  }
}

async function navigationFallback(request) {
  try {
    const response = await fetchWithTimeout(request, NETWORK_TIMEOUT_MS);
    const cache = await caches.open(APP_CACHE);
    await cache.put(request, response.clone());
    return response;
  } catch (error) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    return caches.match("/");
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== "GET") {
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(navigationFallback(request));
    return;
  }

  if (url.pathname.startsWith("/api/v1/")) {
    if (self.navigator && self.navigator.onLine === false) {
      event.respondWith(caches.match(request).then((response) => response || networkFirst(request, API_CACHE)));
      return;
    }

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
