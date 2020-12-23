import axios from 'axios';
import Turbo from '@hotwired/turbo';

import { Controller } from 'stimulus';

export default class extends Controller {
  async submit(event) {
    event.preventDefault();

    const referrer = location.href;
    const method = this.element.getAttribute('method');
    const url = this.element.getAttribute('action');

    const data = new FormData(this.element);

    if (method.toLowerCase() === 'get') {
      Turbo.visit(url + '?' + new URLSearchParams(data).toString());
      return;
    }

    const response = await axios({
      data,
      method,
      url,
      headers: {
        'Turbo-Referrer': referrer,
      },
    });

    const contentType = response.headers['content-type'];

    if (contentType.match(/html/)) {
      // errors in form, re-render
      Turbo.controller.cache.put(referrer, Turbo.Snapshot.wrap(response.data));
      Turbo.visit(referrer, {
        action: 'restore',
      });
    } else if (contentType.match(/javascript/)) {
      /* eslint-disable-next-line no-eval */
      eval(response.data);
    }
  }
}
