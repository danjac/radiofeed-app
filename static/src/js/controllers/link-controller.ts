import { Controller } from 'stimulus';
import { visit } from '@hotwired/turbo';

export default class extends Controller {
  // Turns any element into a link

  urlValue: string;

  static values: any = {
    url: String,
  };

  visit() {
    visit(this.urlValue);
  }
}
