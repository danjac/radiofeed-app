import Sortable from 'sortablejs';

import { sendJSON } from './utils';

(function () {
  window.dragDrop = (elt, options) => {
    const { csrfToken, url } = options;

    const update = () => {
      const items = Array.from(elt.querySelectorAll('[data-draggable]')).map(
        (target) => target.dataset.id
      );
      if (items.length > 0) {
        sendJSON(url, csrfToken, {
          items,
        });
      }
    };

    Sortable.create(elt, {
      handle: '.handle',
      animation: 150,
      group: 'shared',
      onAdd: update,
      onRemove: update,
      onUpdate: update,
    });
  };
})();
