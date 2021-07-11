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

      const index = this.messages.length - 1;

      setTimeout(() => {
        this.messages[index].show = false;
      }, 1500);
    },
  };
}
