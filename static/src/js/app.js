import 'alpinejs';
import 'htmx.org';

import Player from './player';
import Queue from './queue';
import { JSONClient } from './utils';

window.App = {
  initialize({ csrfToken, htmx }) {
    this.csrfToken = csrfToken;
    this.sendJSON = JSONClient(csrfToken);
    this.configHtmx(htmx);
    return this;
  },

  configHtmx(htmx) {
    htmx.defineExtension('intersect', {
      onEvent(name, event) {
        if (name === 'htmx:afterProcessNode') {
          const { elt } = event.detail;

          const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
              if (entry.isIntersecting) {
                htmx.trigger(elt, 'enter');
                observer.disconnect();
              }
            });
          });
          observer.observe(elt);
        }
      },
    });

    document.body.addEventListener('htmx:configRequest', (event) => {
      event.detail.headers['X-CSRFToken'] = this.csrfToken;
    });

    this.htmx = htmx;
  },
  player(options) {
    return Player(this, options);
  },
  queue(options) {
    return Queue(this, options);
  },
};
