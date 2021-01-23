import { Controller } from 'stimulus';

export default class extends Controller {
  static values = {
    text: String,
  };

  confirm(event) {
    if (!window.confirm(this.textValue)) {
      event.preventDefault();
    }
  }
}
