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
        const visible = this.messages.filter((msg) => msg.show);
        visible[visible.length - 1].show = false;
      }, 1500);
    },
  };
}
