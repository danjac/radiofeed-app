{% load static %}
const cacheName = "app-cache-{{ request.site.domain }}";

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(cacheName).then(function(cache) {
      return cache.addAll(
        [
          "{% static debug|yesno:'dev/app.css,dist/app.css' %}",
          "{% static debug|yesno:'dev/app.js,dist/app.js' %}"
        ].map(url => new Request(url, {mode: 'no-cors'}))
      );
    })
  );
});

// deletes old cache
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.filter(function(cacheName) {
        }).map(function(cacheName) {
          return caches.delete(cacheName);
        })
      );
    })
  );
});

self.addEventListener('fetch', function(event) {

  const url = new URL(event.request.url);
    if (!/\.(jpg|png|gif|webp|css|js).*$/.test(url.pathname) || !/^(http|https):$/.test(url.protocol))  {
    return;
  }

  event.respondWith(
    caches.open(cacheName).then(function(cache) {
      return cache.match(event.request).then(function (response) {
        return response || fetch(new Request(event.request.url, {mode: 'no-cors'})).then(function(response) {
          //console.log('caching', event.request.url)
          cache.put(event.request, response.clone());
          return response;
        }).catch(function() { console.log('Unable to cache', event.request.url) });
      });
    })
  );
});

