export const sendJSON = (url, csrfToken, data, options) =>
  fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    body: JSON.stringify(data || {}),
    headers: {
      'X-CSRFToken': csrfToken,
      'Content-Type': 'application/json',
    },
    ...options,
  });

export const dispatch = (el, event, detail = {}) => {
  el.dispatchEvent(
    new CustomEvent(event, {
      detail,
      bubbles: true,
    })
  );
};

export const formatDuration = (value) => {
  if (isNaN(value) || value < 0) return '00:00:00';
  const duration = Math.floor(value);
  const hours = Math.floor(duration / 3600);
  const minutes = Math.floor((duration % 3600) / 60);
  const seconds = Math.floor(duration % 60);
  return [hours, minutes, seconds].map((t) => t.toString().padStart(2, '0')).join(':');
};

export const percent = (nominator, denominator) => {
  if (!denominator || !nominator) {
    return 0;
  }

  if (denominator > nominator) {
    return 100;
  }

  return (denominator / nominator) * 100;
};
