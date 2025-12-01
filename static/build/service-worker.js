importScripts(
    "https://storage.googleapis.com/workbox-cdn/releases/7.3.0/workbox-sw.js",
);

if (workbox.navigationPreload.isSupported()) {
    workbox.navigationPreload.enable();
}

self.addEventListener("fetch", (event) => {
    if (event.request.mode === "navigate") {
        event.respondWith(
            (async () => {
                try {
                    const preloadResponse = await event.preloadResponse;
                    if (preloadResponse) {
                        return preloadResponse;
                    }
                    return await fetch(event.request);
                } catch (error) {
                    return new Response("Offline", {
                        status: 503,
                        statusText: "Service Unavailable",
                    });
                }
            })(),
        );
    }
});
