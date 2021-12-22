import Alpine from 'alpinejs';
import 'htmx.org';

import Player from './player';

(function () {
    window.jCasts = {
        Player,
    };

    Alpine.start();
})();
