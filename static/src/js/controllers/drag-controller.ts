import { Controller } from 'stimulus';
// @ts-ignore
import Sortable from 'sortablejs';

export default class extends Controller {
  handleClass: string;

  draggableTargets: HTMLElement[];

  csrfTokenValue: string;
  groupValue: string;
  urlValue: string;

  static targets: string[] = ['draggable'];

  static classes: string[] = ['handle'];

  static values: any = {
    group: String,
    url: String,
    csrfToken: String,
  };

  connect() {
    // set put: false to prevent
    //
    const handle = '.' + this.handleClass;

    // @ts-ignore
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

  get group(): string {
    return this.groupValue || 'shared';
  }
}
