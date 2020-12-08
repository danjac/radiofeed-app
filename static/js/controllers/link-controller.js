import { Controller } from 'stimulus';
import Turbolinks from 'turbolinks';

export default class extends Controller {
  // Turns any element into a link

  static values = {
    url: String,
  };

  visit() {
    Turbolinks.visit(this.urlValue);
  }
}
