import { Controller } from 'stimulus';
import { useDebounce } from 'stimulus-use';

export default class extends Controller {
  connect() {
    useDebounce(this);
  }

  click() {}
}
