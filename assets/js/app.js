import 'alpinejs';
import 'htmx.org';

import dragDrop from './dragdrop';
import Player from './player';

(function () {
  window.dragDrop = dragDrop;
  window.Player = Player;
})();
