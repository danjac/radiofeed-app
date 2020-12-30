import { Controller } from 'stimulus';
import { useDispatch, useDebounce } from 'stimulus-use';

export default class extends Controller {
  static targets = ['playButton', 'stopButton'];
  static debounces = ['play', 'stop'];

  static values = {
    episode: Number,
    mediaUrl: String,
    playUrl: String,
    playing: Boolean,
  };

  connect() {
    useDispatch(this);
    useDebounce(this, { wait: 500 });
  }

  close() {
    this.playingValue = false;
  }

  play() {
    this.playingValue = true;
    this.dispatch('play', {
      episode: this.episodeValue,
      playUrl: this.playUrlValue,
      mediaUrl: this.mediaUrlValue,
    });
  }

  stop() {
    this.playingValue = false;
    this.dispatch('stop');
  }

  start(event) {
    // episode is started from player
    const { episode } = event.detail;
    this.playingValue = episode === this.episodeValue;
  }

  playingValueChanged() {
    if (this.hasPlayButtonTarget && this.hasStopButtonTarget) {
      if (this.playingValue) {
        this.playButtonTarget.classList.add('hidden');
        this.stopButtonTarget.classList.remove('hidden');
      } else {
        this.playButtonTarget.classList.remove('hidden');
        this.stopButtonTarget.classList.add('hidden');
      }
    }
  }
}
