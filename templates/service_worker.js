{% load static %}

// This is the "Offline page" service worker

importScripts(
    "https://storage.googleapis.com/workbox-cdn/releases/7.3.0/workbox-sw.js",
);

const CACHE = "radiofeed-cache";

const offlineFallbackPage = "{% static 'offline.html' %}";

if (workbox.navigationPreload.isSupported()) {
    workbox.navigationPreload.enable();
}

self.addEventListener("message", (event) => {
    if (event.data && event.data.type === "SKIP_WAITING") {
        self.skipWaiting();
    }
});

self.addEventListener("install", async (event) => {
    event.waitUntil(
        caches.open(CACHE).then((cache) => cache.add(offlineFallbackPage)),
    );
});

self.addEventListener("fetch", (event) => {
    if (event.request.mode === "navigate") {
        event.respondWith(
            (async () => {
                try {
                    const preloadResp = await event.preloadResponse;
                    if (preloadResp) {
                        return preloadResp;
                    }
                    return await fetch(event.request);
                } catch {
                    const cache = await caches.open(CACHE);
                    return await cache.match(offlineFallbackPage);
                }
            })(),
        );
    }
});
