import { Controller } from 'stimulus';
import { useDispatch } from 'stimulus-use';

export default class extends Controller {
  static targets = ['playButton', 'stopButton'];

  static values = {
    id: String,
    duration: Number,
    currentTime: Number,
    playUrl: String,
    playing: Boolean,
  };

  connect() {
    useDispatch(this);
  }

  play() {
    this.playingValue = true;
    this.dispatch('play', {
      episode: this.idValue,
      currentTime: this.currentTimeValue,
      duration: this.durationValue,
      playUrl: this.playUrlValue,
    });
  }

  stop() {
    this.playingValue = false;
    this.dispatch('stop');
  }

  open(event) {
    // another episode is started
    const { episode } = event.detail;
    if (episode !== this.idValue) {
      this.playingValue = false;
    }
  }

  close(event) {
    const { currentTime, episode } = event.detail;
    // player is closed
    this.playingValue = false;
    if (episode === this.idValue) {
      this.currentTimeValue = currentTime;
    }
  }

  playingValueChanged() {
    if (this.playingValue) {
      this.playButtonTarget.classList.add('hidden');
      this.stopButtonTarget.classList.remove('hidden');
    } else {
      this.playButtonTarget.classList.remove('hidden');
      this.stopButtonTarget.classList.add('hidden');
    }
  }
}
