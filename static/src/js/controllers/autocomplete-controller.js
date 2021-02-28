import { Controller } from 'stimulus';

export default class extends Controller {
  static targets = ['results', 'result', 'form', 'input'];
  static values = { search: String };
  static classes = ['selected'];

  connect() {
    this.index = 0;
    this.selectedTarget = null;
  }

  typeahead() {
    this.searchValue = this.inputTarget.value.trim();
  }

  navigate(event) {
    if (this.resultTargets.length === 0) {
      return;
    }

    switch (event.code) {
      case 'Escape':
        this.handleClose();
        return;
      case 'Enter':
        this.handleSelect(event);
        return;
      case 'ArrowDown':
        this.handleNextResult(event, 1);
        break;
      case 'ArrowUp':
        this.handleNextResult(event, -1);
        break;
      default:
    }
  }

  handleSelect(event) {
    event.preventDefault();
    event.stopPropagation();

    if (this.selectedTarget) {
      this.selectedTarget.click();
    }
  }

  handleNextResult(event, position) {
    if (!position) {
      return;
    }

    this.selectedTarget = this.resultTargets[this.index];

    if (this.selectedTarget) {
      this.index += position;
    } else {
      this.index = 0;
      this.inputTarget.focus();
    }

    this.resultTargets.forEach((target) => {
      if (target === this.selectedTarget) {
        target.classList.add(this.selectedClass);
      } else {
        target.classList.remove(this.selectedClass);
      }
    });
  }

  handleClose() {
    this.resultsTarget.textContent = '';
    this.resultsTarget.setAttribute('src', '');
  }

  searchValueChanged() {
    if (this.searchValue.length > 3) {
      this.formTarget.requestSubmit();
    }
  }
}
