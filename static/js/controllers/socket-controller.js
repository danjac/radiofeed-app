import { Controller } from 'stimulus';

import { connectStreamSource, disconnectStreamSource } from '@hotwired/turbo';

export default class extends Controller {
  static values = {
    url: String,
  };

  connect() {
    const protocol = window.location.protocol == 'https:' ? 'wss' : 'ws';
    const url = protocol + '://' + window.location.host + this.urlValue;
    this.source = new WebSocket(url);
    connectStreamSource(this.source);
  }

  disconnect() {
    disconnectStreamSource(this.source);
    this.source = null;
  }
}
