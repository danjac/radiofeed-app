import { Controller } from 'stimulus';
export default class extends Controller {
  static targets = ['match'];
  static classes = ['active'];
  static values = { regex: String, exact: Boolean };

  connect() {
    const { pathname } = window.location;

    const href = (
      this.element.getAttribute('href') || this.matchTarget.getAttribute('href')
    ).split(/[?#]/)[0];

    const matches = this.hasExactValue
      ? pathname === href
      : this.hasRegexValue
      ? pathname.match(this.regexValue)
      : pathname.startsWith(href);
    if (matches) {
      this.element.classList.add(this.activeClass);
    }
  }
}
