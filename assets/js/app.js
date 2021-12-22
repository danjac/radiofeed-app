import Alpine from 'alpinejs';
import 'htmx.org';

import Messages from './messages';
import Player from './player';

(function () {
    window.jCasts = {
        Messages,
        Player,
    };

    Alpine.start();
})();
