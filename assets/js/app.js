import Alpine from 'alpinejs';
import 'htmx.org';

import DragDrop from './dragdrop';
import Messages from './messages';
import Player from './player';

(function () {
  window.jCasts = {
    DragDrop,
    Messages,
    Player,
  };

  // clear HTMX history cache
  localStorage.removeItem('htmx-history-cache');

  Alpine.start();
})();
