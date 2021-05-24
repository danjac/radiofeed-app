import 'alpinejs';
import 'htmx.org';

import dragDrop from './dragdrop';
import Player from './player';

function lazyLoadImages(elt) {
  elt.querySelectorAll('img.lazy').forEach((img) => {
    const observer = new IntersectionObserver((entries, observer) => {
      if (entries[0].isIntersecting) {
        window.htmx.trigger(img, 'lazyload');
        observer.disconnect();
      }
    });
    observer.observe(img);
  });
}

(function () {
  document.addEventListener('DOMContentLoaded', () => lazyLoadImages(document));
  document.addEventListener('htmx:load', (event) => lazyLoadImages(event.detail.elt));

  document.addEventListener('htmx:afterSwap', (event) => {
    // workaround for https://github.com/bigskysoftware/htmx/issues/456
    if (event.target.id === 'content') {
      window.scrollTo(0, event.target.offsetTop - 160);
    }
  });

  // globals
  //
  window.dragDrop = dragDrop;
  window.Player = Player;
})();
