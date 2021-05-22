import Sortable from 'sortablejs';

export default function dragDrop(elt, url) {
  const update = () => {
    const items = Array.from(elt.querySelectorAll('[data-draggable]')).map(
      (target) => target.dataset.id
    );

    if (items.length > 0) {
      window.htmx.ajax('POST', url, { values: { items } });
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
