import Sortable from 'sortablejs';

import { sendJSON } from './utils';

export default function dragDrop(elt, options) {
  const { url, csrfToken } = options;

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
}
