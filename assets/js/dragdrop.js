import Sortable from 'sortablejs';

export default function ({ csrfToken, url }) {
  return {
    init() {
      const update = () => {
        const items = Array.from(this.$el.querySelectorAll('[data-draggable]')).map(
          (target) => target.dataset.id
        );

        if (items.length > 0) {
          const body = new URLSearchParams();
          items.forEach((item) => body.append('items', item));
          fetch(url, {
            body,
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
          }).catch((err) => console.error(err));
        }
      };
      Sortable.create(this.$el, {
        handle: '.handle',
        animation: 150,
        group: 'shared',
        onAdd: update,
        onRemove: update,
        onUpdate: update,
      });
    },
  };
}
