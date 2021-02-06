import { Controller } from 'stimulus';
import Sortable from 'sortablejs';

export default class extends Controller {
  static targets = ['draggable'];

  static values = {
    draggable: String,
    group: String,
    url: String,
    csrfToken: String,
  };

  connect() {
    // set put: false to prevent
    this.sortable = Sortable.create(this.element, {
      animation: 150,
      draggable: this.draggableValue || '.draggable',
      group: this.group,
      onAdd: this.add.bind(this),
      onRemove: this.remove.bind(this),
      onUpdate: this.update.bind(this),
    });
  }

  add() {
    this.update();
  }

  remove() {
    this.update();
  }

  update() {
    const items = this.draggableTargets.map((target) => target.dataset.id);
    if (items) {
      const body = new FormData();

      body.append('csrfmiddlewaretoken', this.csrfTokenValue);
      items.forEach((item) => {
        body.append('items', item);
      });

      fetch(this.urlValue, {
        body,
        method: 'POST',
        credentials: 'same-origin',
      });
    }
  }

  get group() {
    return this.groupValue || 'shared';
  }
}
