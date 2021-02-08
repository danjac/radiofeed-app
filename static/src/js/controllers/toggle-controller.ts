import { Controller } from 'stimulus';

export default class extends Controller {
  itemTargets: HTMLElement[];

  hasToggleClass: boolean;

  toggleClass: string;

  static targets: string[] = ['item'];
  static classes: string[] = ['toggle'];

  toggle() {
    const toggleClass: string = this.hasToggleClass ? this.toggleClass : 'hidden';
    this.itemTargets.forEach((item) => {
      item.classList.toggle(toggleClass);
    });
  }
}
