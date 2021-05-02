import 'alpinejs';
import 'htmx.org';

import Player from './player';

window.App = {
  init(htmx, { csrfToken }) {
    this.csrfToken = csrfToken;

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

    return this;
  },
  player(options) {
    return Player(htmx, { csrfToken: this.csrfToken, ...options });
  },
};
