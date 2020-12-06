import axios from 'axios';
import { Controller } from 'stimulus';

export default class extends Controller {
  // handles playback stuff
  static targets = [
    'audio',
    'counter',
    'playButton',
    'pauseButton',
    'progress',
    'buffer',
    'indicator',
  ];

  static values = {
    episode: String,
    progressUrl: String,
    currentTime: Number,
    duration: Number,
    paused: Boolean,
  };

  initialize() {
    console.log('current time at initialization', this.currentTimeValue);
    this.audioTarget.currentTime = this.currentTimeValue;
    // TBD : value to determine whether to play immediately or not
    this.audioTarget.play();
  }

  pause() {
    this.pausedValue = true;
    this.audioTarget.pause();
  }

  play() {
    this.pausedValue = false;
    this.audioTarget.play();
  }

  skipBack() {
    this.audioTarget.currentTime -= 15;
  }

  skipForward() {
    this.audioTarget.currentTime += 15;
  }

  timeUpdate() {
    const { currentTime } = this.audioTarget;
    this.currentTimeValue = currentTime;

    const pcComplete = this.getPercentComplete();

    this.progressTarget.style.width = pcComplete + '%';
    this.indicatorTarget.style.left = this.getCurrentPostion(pcComplete) + 'px';

    this.sendTimeUpdate();
  }

  progress() {
    const { buffered } = this.audioTarget;
    this.bufferTarget.style.width = this.getPercentBuffered(buffered) + '%';
  }

  getBuffered(buffered) {
    const rv = [];
    for (let i = 0; i < buffered.length; ++i) {
      const start = buffered.start(i);
      const end = buffered.end(i);
      rv.push([start, end]);
    }
    return rv;
  }

  getPercentComplete() {
    if (!this.currentTimeValue || !this.durationValue) {
      return 0;
    }

    return (this.currentTimeValue / this.durationValue) * 100;
  }

  getPercentBuffered(buffered) {
    buffered = this.getBuffered(buffered);
    if (buffered.length === 0) {
      return 0;
    }
    const maxBuffered = buffered.reduce(
      (acc, timeRange) => (timeRange[1] > acc ? timeRange[1] : acc),
      0
    );
    return (maxBuffered / this.durationValue) * 100 - this.getPercentComplete();
  }

  getProgressWidth(pcComplete) {
    const clientWidth = this.element.clientWidth;
    let completeWidth = 0;
    if (clientWidth === 0) {
      return 0;
    } else {
      // min 1rem to accomodate indicator
      const minWidth = (16 / clientWidth) * 100;
      return pcComplete > minWidth ? pcComplete : minWidth;
    }
  }

  getCurrentPostion(pcComplete) {
    let currentPosition = this.progressTarget.getBoundingClientRect().left - 16;
    const width = this.getProgressWidth(pcComplete);
    if (width) {
      currentPosition += this.element.clientWidth * (width / 100);
    }
    return currentPosition;
  }

  pausedValueChanged() {
    if (this.hasPauseButtonTarget && this.hasPlayButtonTarget) {
      if (this.pausedValue) {
        this.pauseButtonTarget.classList.add('hidden');
        this.playButtonTarget.classList.remove('hidden');
      } else {
        this.pauseButtonTarget.classList.remove('hidden');
        this.playButtonTarget.classList.add('hidden');
      }
    }
  }

  currentTimeValueChanged() {
    if (this.hasCounterTarget) {
      this.counterTarget.textContent =
        '-' + this.formatTime(this.durationValue - this.currentTimeValue);
    }
  }

  sendTimeUpdate() {
    // update every 15s or so
    const diff = Math.ceil(Math.abs(this.currentTimeValue - this.lastUpdated || 0));
    if (diff % 15 === 0) {
      axios.post(this.progressUrlValue, { current_time: this.currentTimeValue });
      this.lastUpdated = this.currentTimeValue;
    }
  }

  formatTime(value) {
    if (!value || value < 0) return '00:00:00';
    const duration = Math.floor(parseInt(value));

    const hours = Math.floor(duration / 3600);
    const minutes = Math.floor((duration % 3600) / 60);
    const seconds = Math.floor(duration % 60);

    return [hours, minutes, seconds]
      .map((t) => t.toString().padStart(2, '0'))
      .join(':');
  }
}
