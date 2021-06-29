export default function Messages() {
  return {
    messages: [],
    addMessage(message) {
      this.messages.push({
        ...message,
        show: true,
      });
      setTimeout(() => {
        this.messages[this.messages.length - 1].show = false;
      }, 1500);
    },
  };
}

export function dispatchMessage(message) {
  const event = new CustomEvent('add-message', {
    detail: message,
  });
  window.dispatchEvent(event);
}
