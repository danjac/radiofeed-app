import { Controller } from 'stimulus';

export default class extends Controller {
  modalTarget: HTMLElement;

  static targets: string[] = ['close', 'modal'];

  close() {
    // empty content of frame and reset src
    this.modalTarget.textContent = '';
    this.modalTarget.removeAttribute('src');
  }

  closeOnEsc(event: KeyboardEvent) {
    if (event.code === 'Escape') {
      this.close();
    }
  }
}
