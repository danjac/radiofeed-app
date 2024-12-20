importScripts(
    "https://storage.googleapis.com/workbox-cdn/releases/7.3.0/workbox-sw.js",
);

if (workbox.navigationPreload.isSupported()) {
    workbox.navigationPreload.enable();
}
