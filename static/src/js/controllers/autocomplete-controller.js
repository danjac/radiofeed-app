import { Controller } from 'stimulus';

export default class extends Controller {
  static targets = ['results', 'result', 'form', 'input'];
  static values = { search: String };

  connect() {
    this.index = 0;
  }

  typeahead() {
    this.searchValue = this.inputTarget.value.trim();
  }

  navigate(event) {
    event.preventDefault();
    event.stopPropagation();

    let position, target;

    switch (event.code) {
      case 'escape':
        this.resultsTarget.textContent = '';
        this.resultsTarget.setAttribute('src', '');
        break;
      case 'down':
        position = 1;
        break;
      case 'up':
        position = -1;
        break;
      default:
        position = 0;
    }

    if (position) {
      target = this.resultTargets[this.index];
    }

    if (target) {
      this.index += position;
    } else {
      this.index = 0;
      this.inputTarget.focus();
    }
  }

  searchValueChanged() {
    if (this.searchValue.length > 3) {
      this.formTarget.requestSubmit();
    }
  }
}
