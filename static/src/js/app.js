import 'htmx.org';
import 'alpinejs';

const maybeIntersect = (elt) => {
  console.log('interect goes here');
};

const { htmx } = window;

htmx.defineExtension('intersect', {
  onEvent(name, event) {
    if (name === 'htmx:afterProcessNode') {
      const { elt } = event.detail;
      const observer = new IntersectionObserver((entries) => {});
    }
  },
});
