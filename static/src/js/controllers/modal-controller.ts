import { Controller } from 'stimulus';

export default class extends Controller {
  static targets: string[] = ['close', 'modal'];

  close() {
    // empty content of frame and reset src
    this.modalTarget.textContent = '';
    this.modalTarget.removeAttribute('src');
  }

  closeOnEsc(event: Event) {
    if (event.which === 27) {
      this.close();
    }
  }
}
