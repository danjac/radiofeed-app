import { Controller } from 'stimulus';
import { visit } from '@hotwired/turbo';

export default class extends Controller {
  static values = {
    leftUrl: String,
    rightUrl: String,
    initialPosition: Number,
    disabled: Boolean,
  };

  start(event) {
    this.initialPositionValue = event.touches[0].clientX;
  }
  move(event) {
    if (!this.initialPositionValue || this.disabledValue) {
      return;
    }
    const currentPosition = event.touches[0].clientX;
    const diff = this.initialPositionValue - currentPosition;

    if (diff > 0 && this.leftUrlValue) {
      this.disabledValue = true;
      visit(this.leftUrlValue);
    } else if (diff < 0 && this.rightUrlValue) {
      this.disabledValue = true;
      visit(this.rightUrlValue);
    }
    this.initialPrightionValue = 0;
  }
}
