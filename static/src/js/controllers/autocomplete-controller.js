import { Controller } from 'stimulus';

export default class extends Controller {
  static targets = ['results', 'result', 'form', 'input'];
  static values = { search: String };

  connect() {
    this.index = 0;
  }

  typeahead(event) {
    console.log('typeahead...', event.code);
    if (event.code === 'escape') {
      return;
    }
    this.searchValue = this.inputTarget.value.trim();
  }

  navigate(event) {
    console.log('navigate...', event.code);
    if (this.resultTargets.length === 0) {
      return;
    }
    let position, target;

    switch (event.code) {
      case 'Escape':
        this.close();
        break;
      case 'ArrowDown':
        position = 1;
        break;
      case 'ArrowUp':
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
      target.focus();
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

  close() {
    this.inputTarget.value = '';
    this.searchValue = '';
    console.log('resultstarget', this.resultstarget);
    this.resultsTarget.textContent = '';
    this.resultsTarget.setAttribute('src', '');
  }
}
