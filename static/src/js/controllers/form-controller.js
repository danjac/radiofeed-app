import { Controller } from 'stimulus';

export default class extends Controller {
  static values = {
    submitting: Boolean,
  };

  submit(event) {
    if (this.submittingValue) {
      event.preventDefault();
      return;
    }
    this.submittingValue = true;
  }

  submittingValueChanged() {
    if (this.submittingValue) {
      this.element.classList.add('submitting');
      Array.from(this.element.elements).forEach((el) =>
        el.setAttribute('readonly', true)
      );
    }
  }
}
