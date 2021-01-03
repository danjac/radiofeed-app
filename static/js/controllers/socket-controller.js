import { Controller } from 'stimulus';
import ReconnectingWebSocket from 'reconnecting-websocket';

import { connectStreamSource, disconnectStreamSource } from '@hotwired/turbo';

export default class extends Controller {
  static values = {
    url: String,
  };

  initialize() {
    // ensure socket is closed properly on full page unload
    document.addEventListener('beforeunload', () => {
      this.disconnect();
    });
  }

  connect() {
    const protocol = window.location.protocol == 'https:' ? 'wss' : 'ws';
    const url = protocol + '://' + window.location.host + this.urlValue;
    console.log('open socket:', this.urlValue);
    this.socket = new ReconnectingWebSocket(url);
    connectStreamSource(this.socket);
  }

  disconnect() {
    if (this.socket) {
      console.log('close socket:', this.urlValue);
      disconnectStreamSource(this.socket);
      this.socket.close();
    }
    this.socket = null;
  }
}
