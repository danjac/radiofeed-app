import { Controller } from 'stimulus';

export default class extends Controller {
  static targets = ['item'];
  static classes = ['toggle'];

  toggle(event) {
    //event.preventDefault();
    //event.stopPropagation();

    const toggleClass = this.hasToggleClass ? this.toggleClass : 'hidden';
    this.itemTargets.forEach((item) => {
      item.classList.toggle(toggleClass);
    });
  }
}
