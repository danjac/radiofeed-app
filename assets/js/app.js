import 'alpinejs';
import 'htmx.org';

import dragDrop from './dragdrop';
import lazyLoadImages from './lazyload';
import Player from './player';

(function () {
  document.addEventListener('htmx:load', (event) => lazyLoadImages(event.detail.elt));
  document.addEventListener('DOMContentLoaded', () => lazyLoadImages(document));

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
