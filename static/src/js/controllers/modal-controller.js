import { Controller } from 'stimulus';

export default class extends Controller {
  static targets = ['close'];

  close() {
    this.closeTarget.click();
  }

  closeOnEsc(event) {
    if (event.which === 27) {
      this.close();
    }
  }
}
