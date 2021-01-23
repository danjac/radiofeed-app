import { Controller } from 'stimulus';

export default class extends Controller {
  static targets = ['playButton', 'stopButton'];

  static values = {
    episode: Number,
  };

  start({ detail: { episode } }) {
    if (episode === this.episodeValue) {
      this.playButtonTarget.classList.add('hidden');
      this.stopButtonTarget.classList.remove('hidden');
    } else {
      this.stop();
    }
  }

  stop() {
    this.playButtonTarget.classList.remove('hidden');
    this.stopButtonTarget.classList.add('hidden');
  }
}
