import { Controller } from 'stimulus';

export default class extends Controller {
  static values: any = {
    text: String,
  };

  confirm(event: Event) {
    if (!window.confirm(this.textValue)) {
      event.preventDefault();
    }
  }
}
