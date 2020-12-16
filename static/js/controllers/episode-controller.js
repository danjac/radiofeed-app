import { Controller } from 'stimulus';
import { useDispatch, useDebounce } from 'stimulus-use';

export default class extends Controller {
  static targets = ['playButton', 'stopButton', 'currentTime'];
  static debounces = ['play', 'stop'];

  static values = {
    id: String,
    duration: Number,
    currentTime: Number,
    playUrl: String,
    playing: Boolean,
  };

  connect() {
    useDispatch(this);
    useDebounce(this, { wait: 500 });
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

  update({ detail: { episode, time_remaining, completed, duration } }) {
    if (episode === this.idValue) {
      if (time_remaining && !completed) {
        this.currentTimeTarget.textContent = '~' + time_remaining;
      } else {
        this.currentTimeTarget.textContent = duration;
      }
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
