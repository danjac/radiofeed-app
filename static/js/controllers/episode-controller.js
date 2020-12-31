import { Controller } from 'stimulus';
import useTurbo from '~/turbo';

export default class extends Controller {
  static targets = ['playButton', 'stopButton'];

  static values = {
    episode: String,
  };

  connect() {
    useTurbo(this);
  }

  turboSubmitEnd(event) {
    const { fetchResponse } = event.detail;
    const headers = fetchResponse.response ? fetchResponse.response.headers : null;
    if (!headers) {
      return;
    }
    const action = headers.get('X-Player-Action');
    // not a player action, ignore
    if (!action) {
      return;
    }

    if (action === 'stop') {
      this.toggleOnStop();
    } else {
      this.toggleOnPlay(headers.get('X-Player-Episode'));
    }
  }

  toggleOnPlay(episode) {
    if (episode === this.episodeValue) {
      this.playButtonTarget.classList.add('hidden');
      this.stopButtonTarget.classList.remove('hidden');
    } else {
      this.toggleOnStop();
    }
  }

  toggleOnStop() {
    this.playButtonTarget.classList.remove('hidden');
    this.stopButtonTarget.classList.add('hidden');
  }
}
