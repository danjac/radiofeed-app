import './dragDrop';
import './player';

import { getCsrfToken } from './utils';

(function () {
  window.onload = () => {
    // htmx events
    document.body.addEventListener('htmx:configRequest', (event) => {
      event.detail.headers['X-CSRFToken'] = getCsrfToken();
    });
    document.addEventListener('htmx:afterSwap', (event) => {
      // workaround for https://github.com/bigskysoftware/htmx/issues/456
      if (event.target.id === 'content') {
        window.scrollTo(0, event.target.offsetTop - 160);
      }
    });
  };
})();
