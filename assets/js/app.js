import 'alpinejs';
import 'htmx.org';

import './dragdrop';
import './player';

import { lazyLoadImages } from './utils';

document.addEventListener('htmx:afterSwap', (event) => {
  // workaround for https://github.com/bigskysoftware/htmx/issues/456
  if (event.target.id === 'content') {
    window.scrollTo(0, event.target.offsetTop - 160);
  }
});

document.addEventListener('htmx:load', (event) => lazyLoadImages(event.detail.elt));
document.addEventListener('DOMContentLoaded', lazyLoadImages(document));
