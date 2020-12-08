import { Controller } from 'stimulus';
import Turbolinks from 'turbolinks';

export default class extends Controller {
  // Turns any element into local

  static values = {
    url: String,
    external: Boolean,
  };

  visit() {
    if (this.externalValue) {
      window.location.href = this.urlValue;
    } else {
      Turbolinks.visit(this.urlValue);
    }
  }
}
