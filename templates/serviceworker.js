{% load static %}

var staticCacheName = 'radiofeed-' + new Date().getTime();
var filesToCache = [
  '{% url "offline" %}',
  '{% static debug|yesno:'dev/app.css,dist/app.css' %}',
  '{% static debug|yesno:'dev/app.js,dist/app.js' %}',
  '{% static 'img/wave.png' %}'
];

// Cache on install
self.addEventListener('install', (event) => {
  this.skipWaiting();
  event.waitUntil(
    caches.open(staticCacheName).then((cache) => {
      return cache.addAll(filesToCache);
    })
  );
});

// Clear cache on activate
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((cacheName) => cacheName.startsWith('radiofeed-'))
          .filter((cacheName) => cacheName !== staticCacheName)
          .map((cacheName) => caches.delete(cacheName))
      );
    })
  );
});

// Serve from Cache
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches
      .match(event.request)
      .then((response) => {
        return response || fetch(event.request);
      })
      .catch(() => {
        return caches.match('{% url "offline" %}');
      })
  );
});
