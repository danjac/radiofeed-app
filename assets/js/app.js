import Alpine from 'alpinejs';
import 'htmx.org';

import DragDrop from './dragdrop';
import Player from './player';

(function () {
  window.DragDrop = DragDrop;
  window.Player = Player;
  Alpine.start();
})();
