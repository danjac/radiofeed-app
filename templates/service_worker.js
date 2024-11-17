/* {% load static %} */
// This is the "Offline page" service worker

importScripts("https://storage.googleapis.com/workbox-cdn/releases/7.3.0/workbox-sw.js");

const CACHE = "serviceworker-cache";

{% get_static_assets as assets %}

const assets = [
    {% for asset in assets %}
        "{{ asset }}",
    {% endfor %}
];

if (workbox.navigationPreload.isSupported()) {
    workbox.navigationPreload.enable();
}

self.addEventListener("install", async (event) => {
    event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(assets)));
});

self.addEventListener("fetch", (event) => {
    event.respondWith(
        (async () => {
            const cache = await caches.open(CACHE);
            const cachedResponse = await cache.match(event.request);

            if (cachedResponse) {
                console.log("Fetched from cache:", event.request.url);
                return cachedResponse;
            }

            try {
                return await fetch(event.request);
            } catch {
                return await cache.match(offlineFallbackPage);
            }
        })()
    );
});
