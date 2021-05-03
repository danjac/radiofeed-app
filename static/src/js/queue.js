import Sortable from 'sortablejs';

export default function (app, options) {
  const { url } = options;
  return {
    initialize() {
      const update = this.update.bind(this);
      Sortable.create(this.$el, {
        handle: '.handle',
        animation: 150,
        group: 'shared',
        onAdd: update,
        onRemove: update,
        onUpdate: update,
      });
    },

    update() {
      const items = Array.from(this.$el.querySelectorAll('[data-draggable]')).map(
        (target) => target.dataset.id
      );
      if (items.length > 0) {
        app.sendJSON(url, { items });
      }
    },
  };
}
