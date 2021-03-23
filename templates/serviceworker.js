{% load static %}
const cacheName = "app-cache";

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(cacheName).then(function(cache) {
      return cache.addAll(
        [
          "{% static debug|yesno:'dev/app.css,dist/app.css' %}",
          "{% static debug|yesno:'dev/app.js,dist/app.js' %}"
        ]
      );
    })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.open(cacheName).then(function(cache) {
      if (!/^https?:$/i.test(new URL(request.url).protocol)) return;
      return cache.match(event.request).then(function (response) {
        return response || fetch(event.request).then(function(response) {
          cache.put(event.request, response.clone());
          return response;
        });
      });
    })
  );
});
