import { Controller } from 'stimulus';
import Sortable from 'sortablejs';

export default class extends Controller {
  static classes = ['handle'];
  static targets = ['draggable'];

  static values = {
    group: String,
    url: String,
    csrfToken: String,
  };

  connect() {
    // set put: false to prevent
    //
    const handle = '.' + this.handleClass;

    this.sortable = Sortable.create(this.element, {
      handle,
      animation: 150,
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
