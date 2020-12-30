import { Controller } from 'stimulus';

export default class extends Controller {
  static targets = ['item'];
  static classes = ['toggle'];

  toggle() {
    const toggleClass = this.hasToggleClass ? this.toggleClass : 'hidden';
    this.itemTargets.forEach((item) => {
      item.classList.toggle(toggleClass);
    });
  }
}
