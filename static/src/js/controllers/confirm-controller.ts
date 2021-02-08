import { Controller } from 'stimulus';

export default class extends Controller {
  static values: Object = {
    text: String,
  };

  confirm(event: Event) {
    if (!window.confirm(this.textValue)) {
      event.preventDefault();
    }
  }
}
