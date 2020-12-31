import { Controller } from 'stimulus';

import { connectStreamSource, disconnectStreamSource } from '@hotwired/turbo';

export default class extends Controller {
  static values = {
    url: String,
  };

  connect() {
    console.log('socket url:', this.urlValue);
    this.source = new WebSocket('ws://' + window.location.host + this.urlValue);
    // this.source = new WebSocket(this.socketUrlValue);
    connectStreamSource(this.source);
  }

  disconnect() {
    disconnectStreamSource(this.source);
    this.source = null;
  }
}
