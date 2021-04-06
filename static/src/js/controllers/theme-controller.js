import { Controller } from 'stimulus';

export default class extends Controller {
  toggle() {
    document.documentElement.classList.toggle('dark');
  }
}
