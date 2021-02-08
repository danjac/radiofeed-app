import { Controller } from 'stimulus';

export default class extends Controller {
  static targets: string[] = ['item'];
  static classes: string[] = ['toggle'];

  toggle() {
    const toggleClass: string = this.hasToggleClass ? this.toggleClass : 'hidden';
    this.itemTargets.forEach((item: HTMLElement) => {
      item.classList.toggle(toggleClass);
    });
  }
}
