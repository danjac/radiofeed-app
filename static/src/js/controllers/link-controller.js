import { Controller } from 'stimulus';
import { visit } from '@hotwired/turbo';

export default class extends Controller {
  static values = {
    url: String,
  };

  visit() {
    visit(this.urlValue);
  }
}
