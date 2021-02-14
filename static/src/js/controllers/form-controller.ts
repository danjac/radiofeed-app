import { Controller } from 'stimulus';

export default class extends Controller {
  element: HTMLFormElement;
  submittingValue: Boolean;

  static values = {
    submitting: Boolean,
  };

  submit(event: Event) {
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
