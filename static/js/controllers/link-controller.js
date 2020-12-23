import { Controller } from 'stimulus';
import Turbo from '@hotwired/turbo';

export default class extends Controller {
  // Turns any element into a link

  static values = {
    url: String,
  };

  visit() {
    Turbo.visit(this.urlValue);
  }
}
