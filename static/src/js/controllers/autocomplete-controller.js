import { Controller } from 'stimulus';

export default class extends Controller {
  static targets = ['results', 'result', 'form', 'input'];
  static values = { search: String };

  typeahead() {
    this.searchValue = this.inputTarget.value.trim();
  }

  close(event) {
    if (event.code === 'Escape' && this.resultTargets.length > 0) {
      this.resultsTarget.textContent = '';
      this.resultsTarget.setAttribute('src', '');
    }
  }
  searchValueChanged() {
    if (this.searchValue.length > 3) {
      this.formTarget.requestSubmit();
    }
  }
}
