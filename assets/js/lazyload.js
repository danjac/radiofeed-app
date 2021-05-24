// "revealed" trigger has some buggy behavior around scrolling to top that randomly breaks
// this can probably be removed with htmx 1.4+ as we can just use IntersectionObserver directly
export default function lazyLoadImages(elt) {
  const lazyImages = [].slice.call(elt.querySelectorAll('img.lazy'));

  if ('IntersectionObserver' in window) {
    const lazyImageObserver = new IntersectionObserver(function (entries, observer) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          const { target } = entry;
          target.classList.remove('lazy');
          target.dispatchEvent(
            new CustomEvent('lazyload', { detail: { elt: target } })
          );
          lazyImageObserver.unobserve(target);
        }
      });
    });

    lazyImages.forEach(function (img) {
      lazyImageObserver.observe(img);
    });
  }
}
