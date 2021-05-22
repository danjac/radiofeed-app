import 'alpinejs';
import 'htmx.org';

import dragDrop from './dragdrop';
import Player from './player';

export function lazyLoadImages(elt) {
  const lazyImages = [].slice.call(elt.querySelectorAll('img.lazy'));

  if ('IntersectionObserver' in window) {
    const lazyImageObserver = new IntersectionObserver(function (entries, observer) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          const { target } = entry;
          target.src = target.dataset.src;
          target.classList.remove('lazy');
          lazyImageObserver.unobserve(target);
        }
      });
    });

    lazyImages.forEach(function (img) {
      lazyImageObserver.observe(img);
    });
  } else {
    lazyImages.forEach(function (img) {
      img.src = img.dataset.src;
      img.classList.remove('lazy');
    });
  }
}

(function () {
  // events
  document.addEventListener('htmx:afterSwap', (event) => {
    // workaround for https://github.com/bigskysoftware/htmx/issues/456
    if (event.target.id === 'content') {
      window.scrollTo(0, event.target.offsetTop - 160);
    }
  });

  document.addEventListener('htmx:load', (event) => lazyLoadImages(event.detail.elt));
  document.addEventListener('DOMContentLoaded', lazyLoadImages(document));

  // globals
  //
  window.dragDrop = dragDrop;
  window.Player = Player;
})();
