import { Controller } from 'stimulus';
import { useDispatch, useDebounce } from 'stimulus-use';

export default class extends Controller {
  static targets = ['playButton', 'stopButton', 'currentTime'];
  static classes = ['completed'];
  static debounces = ['play', 'stop'];

  static values = {
    episode: Number,
    duration: Number,
    duration: String,
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
      episode: this.episodeValue,
      currentTime: this.currentTimeValue,
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
    this.playingValue = episode === this.episodeValue;
  }

  close(event) {
    const { currentTime, episode, completed } = event.detail;
    // player is closed
    this.playingValue = false;
    if (episode === this.episodeValue) {
      this.currentTimeValue = currentTime;
    }
    if (completed) {
      this.currentTimeTarget.classList.add(this.completedClass);
      this.currentTimeTarget.textContent = this.durationValue;
    }
  }

  update({ detail: { episode, time_remaining, completed } }) {
    if (episode && episode === this.episodeValue) {
      if (completed) {
        this.currentTimeValue = 0;
        this.currentTimeTarget.textContent = this.durationValue;
        this.currentTimeTarget.classList.add(this.completedClass);
      } else if (time_remaining) {
        this.currentTimeTarget.textContent = '~' + time_remaining;
      } else {
        this.currentTimeTarget.textContent = this.durationValue;
      }
    }
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
