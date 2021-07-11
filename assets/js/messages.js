export default function Messages() {
  return {
    messages: [],
    addMessages(messages) {
      messages.forEach((message) => this.addMessage(message));
    },
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
