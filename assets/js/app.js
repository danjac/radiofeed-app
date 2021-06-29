import Alpine from 'alpinejs';
import 'htmx.org';

import DragDrop from './dragdrop';
import Messages, { dispatchMessage } from './messages';
import Player from './player';

(function () {
  window.DragDrop = DragDrop;
  window.Messages = Messages;
  window.Player = Player;
  window.dispatchMessage = dispatchMessage;
  Alpine.start();
})();
