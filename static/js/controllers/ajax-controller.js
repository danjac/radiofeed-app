import axios from 'axios';
import Turbo from '@hotwired/turbo';
import { Controller } from 'stimulus';
import { useDebounce, useThrottle } from 'stimulus-use';

export default class extends Controller {
  static targets = ['fragment'];
  static debounces = ['sendAjax'];
  static values = {
    confirm: String,
    debounce: Number,
    throttle: Number,
    redirect: String,
    remove: Boolean,
    replace: Boolean,
    url: String,
    params: Object,
  };

  connect() {
    if (this.hasDebounceValue) {
      useDebounce(this, { wait: this.debounceValue });
    }
    if (this.hasThrottleValue) {
      useThrottle(this, { wait: this.throttleValue });
    }
  }

  get(event) {
    event.preventDefault();
    this.sendAjax('GET');
  }

  post(event) {
    event.preventDefault();
    this.sendAjax('POST');
  }

  put(event) {
    event.preventDefault();
    this.sendAjax('POST');
  }

  delete(event) {
    event.preventDefault();
    this.sendAjax('DELETE');
  }

  async sendAjax(method) {
    if (this.hasConfirmValue && !window.confirm(this.confirmValue)) {
      return;
    }

    const url = this.urlValue || this.element.getAttribute('href');

    const headers = {
      'Turbo-Referrer': location.href,
    };

    // request server return an HTML fragment to insert into DOM
    //
    if (this.hasReplaceValue) {
      headers['X-Request-Fragment'] = true;
    }

    const response = await axios({
      headers,
      method,
      url,
      data: this.paramsValue,
    });

    if (this.hasRedirectValue) {
      if (this.redirectValue !== 'none') Turbo.visit(this.redirectValue);
      return;
    }

    // remove target
    if (this.hasRemoveValue) {
      if (this.hasFragmentTargets) {
        this.fragmentTargets.forEach((target) => target.remove());
      } else {
        this.element.remove();
      }
      return;
    }

    const contentType = response.headers['content-type'];

    if (this.hasReplaceValue && contentType.match(/html/)) {
      if (this.hasFragmentTargets) {
        this.fragmentTargets.forEach((target) => (target.innerHTML = response.data));
      } else {
        this.element.innerHTML = response.data;
      }
      return;
    }

    // default behaviour: redirect passed down in header
    if (contentType.match(/javascript/)) {
      /* eslint-disable-next-line no-eval */
      eval(response.data);
    }
  }
}
