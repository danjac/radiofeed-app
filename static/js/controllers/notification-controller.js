import { Controller } from 'stimulus';

export default class extends Controller {
  // permanently or temporarily remove notifications e.g.
  // flash messages or cookie banners
  //

  static values = {
    timeout: Number,
    storageKey: String,
  };

  connect() {
    if (this.hasStorageKeyValue && window.localStorage.getItem(this.storageKeyValue)) {
      // automatically remove if storage key present
      this.remove();
    } else if (this.hasTimeoutValue && this.timeoutValue > 0) {
      // automatically toggle elements on page load after timeout
      setTimeout(() => this.remove(), this.timeoutValue);
    }
  }

  remove() {
    if (this.hasStorageKeyValue) {
      window.localStorage.setItem(this.storageKeyValue, true);
    }
    this.element.remove();
  }
}
