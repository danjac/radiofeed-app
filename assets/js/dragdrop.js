import Sortable from 'sortablejs';

export default function ({ url }) {
  return {
    init() {
      const update = () => {
        const items = Array.from(this.$el.querySelectorAll('[data-draggable]')).map(
          (target) => target.dataset.id
        );

        if (items.length > 0) {
          window.htmx.ajax('POST', url, { source: this.$el, values: { items } });
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
