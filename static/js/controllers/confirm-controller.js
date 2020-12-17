import { Controller } from 'stimulus';

export default class extends Controller {
  // opens confirm dialog. Use in cases where you can't use
  // with the ajax controller
  static values = {
    text: String,
  };

  confirm(event) {
    if (!window.confirm(this.textValue)) {
      event.preventDefault();
    }
  }
}
