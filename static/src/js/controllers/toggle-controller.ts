import { Controller } from 'stimulus';

export default class extends Controller {
  static targets: String[] = ['item'];
  static classes: String[] = ['toggle'];

  toggle() {
    const toggleClass: String = this.hasToggleClass ? this.toggleClass : 'hidden';
    this.itemTargets.forEach((item: HTMLElement) => {
      item.classList.toggle(toggleClass);
    });
  }
}
