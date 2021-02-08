import { Controller } from 'stimulus';

export default class extends Controller {
  textValue: string;

  static values: any = {
    text: String,
  };

  confirm(event: Event) {
    if (!window.confirm(this.textValue)) {
      event.preventDefault();
    }
  }
}
