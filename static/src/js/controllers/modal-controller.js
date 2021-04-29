import { Controller } from 'stimulus';

export default class extends Controller {
  static targets = ['close', 'content'];

  close() {
    // empty content of frame and reset src
    this.element.textContent = '';
    this.element.removeAttribute('src');
  }

  closeOnEsc(event) {
    if (event.code === 'Escape') {
      this.close();
    }
  }

  clickOutside(event) {
    event.preventDefault();
    this.close();
  }
}
