import { Controller } from 'stimulus';

export default class extends Controller {
  static targets = ['item'];
  static classes = ['toggle'];
  static values = { scroll: Boolean };

  toggle() {
    const toggleClass = this.hasToggleClass ? this.toggleClass : 'hidden';
    this.itemTargets.forEach((item) => {
      item.classList.toggle(toggleClass);
    });
    if (this.scrollValue) {
      document.body.scrollTop = 0;
    }
  }
}
