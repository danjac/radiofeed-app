import { Controller } from 'stimulus';
import Sortable from 'sortablejs';

export default class extends Controller {
  static targets = ['draggable'];

  static values = {
    draggable: String,
    group: String,
    url: String,
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
    if (this.hasUrlValue) {
      const items = [];
      this.draggableTargets.forEach((target) => {
        if (target.dataset.group === this.group) {
          items.push(target.dataset.id);
        }
      });
      //axios.post(this.urlValue, { items });
    }
  }

  get group() {
    return this.groupValue || 'shared';
  }
}
