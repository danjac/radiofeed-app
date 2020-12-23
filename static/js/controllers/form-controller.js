import { Controller } from 'stimulus';

export default class extends Controller {
  connect() {
    document.addEventListener('turbo:submit-end', this.handleSubmit.bind(this));
  }

  disconnect() {
    document.removeEventListener('turbo:submit-end', this.handleSubmit.bind(this));
  }

  handleSubmit(event) {
    console.log('HANDLE SUBMIT', event.detail);
  }
}
