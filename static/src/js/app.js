import 'htmx.org';
import 'alpinejs';

const { htmx } = window;

htmx.defineExtension('intersect', {
  onEvent(name, event) {
    if (name === 'htmx:afterProcessNode') {
      const { elt } = event.detail;

      const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            htmx.trigger(elt, 'enter');
            observer.disconnect();
          }
        });
      });
      observer.observe(elt);
    }
  },
});
