import 'alpinejs';
import 'htmx.org';

import morphdom from 'morphdom';

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
  document.addEventListener('DOMContentLoaded', () => lazyLoadImages(document));

  window.htmx.defineExtension('morphdom-swap', {
    isInlineSwap: function (swapStyle) {
      return swapStyle === 'morphdom';
    },

    handleSwap: function (swapStyle, target, fragment) {
      if (swapStyle === 'morphdom') {
        if (fragment.nodeType === Node.DOCUMENT_FRAGMENT_NODE) {
          morphdom(target, fragment.firstElementChild);
          return [target];
        } else {
          morphdom(target, fragment.outerHTML);
          return [target];
        }
      }
    },
  });

  // globals
  //
  window.dragDrop = dragDrop;
  window.Player = Player;
})();
