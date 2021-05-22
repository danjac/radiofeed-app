export function lazyLoadImages(elt) {
  const lazyImages = [].slice.call(elt.querySelectorAll('img.lazy'));

  if ('IntersectionObserver' in window) {
    const lazyImageObserver = new IntersectionObserver(function (entries, observer) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          const { target } = entry;
          target.src = target.dataset.src;
          target.classList.remove('lazy');
          lazyImageObserver.unobserve(target);
        }
      });
    });

    lazyImages.forEach(function (img) {
      lazyImageObserver.observe(img);
    });
  } else {
    lazyImages.forEach(function (img) {
      img.src = img.dataset.src;
      img.classList.remove('lazy');
    });
  }
}

export function percent(nominator, denominator) {
  if (!denominator || !nominator) {
    return 0;
  }

  if (denominator > nominator) {
    return 100;
  }

  return (denominator / nominator) * 100;
}
