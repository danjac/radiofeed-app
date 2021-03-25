import { Controller } from 'stimulus';

import hoverintent from 'hoverintent';

export default class extends Controller {
  static values = {
    interval: Number,
    sensitivity: Number,
  };

  connect() {
    const interval = this.intervalValue || 50;
    const sensitivity = this.sensitivityValue || 5;

    this.element.querySelectorAll('a').forEach((el) => {
      if (el.dataset.turbo === 'false') {
        return;
      }

      let prefetcher;
      hoverintent(
        el,
        () => {
          const href = el.getAttribute('href');
          if (!href.match(/^\//)) {
            return;
          }
          if (prefetcher) {
            if (prefetcher.getAttribute('href') !== href) {
              prefetcher.setAttribute('href', href);
            }
          } else {
            const link = document.createElement('link');
            link.setAttribute('rel', 'prefetch');
            link.setAttribute('href', href);
            prefetcher = document.head.appendChild(link);
          }
        },
        () => {},
        {
          interval,
          sensitivity,
        }
      );
    });
  }
}
