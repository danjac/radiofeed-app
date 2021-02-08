import { Controller } from 'stimulus';

export default class extends Controller {
  timeoutValue: number;

  static values: any = {
    timeout: Number,
  };

  connect() {
    if (this.timeoutValue && this.timeoutValue > 0) {
      setTimeout(() => this.remove(), this.timeoutValue);
    }
  }

  remove() {
    this.element.remove();
  }
}
