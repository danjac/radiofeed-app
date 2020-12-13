import axios from 'axios';
import { Controller } from 'stimulus';
import { useDispatch } from 'stimulus-use';

export default class extends Controller {
  static targets = [
    'audio',
    'buffer',
    'counter',
    'indicator',
    'pauseButton',
    'playButton',
    'progress',
    'progressBar',
  ];

  static classes = ['progress', 'buffer', 'progressPaused', 'bufferPaused'];

  static values = {
    episode: String,
    progressUrl: String,
    stopUrl: String,
    currentTime: Number,
    duration: Number,
    paused: Boolean,
  };

  connect() {
    useDispatch(this);
  }

  async initialize() {
    if (this.hasAudioTarget) {
      this.audioTarget.currentTime = this.currentTimeValue;
      try {
        await this.audioTarget.play();
      } catch (e) {
        this.pausedValue = true;
      }
    }
  }

  async open(event) {
    const { playUrl, episode, duration } = event.detail;

    this.episodeValue = episode;
    this.durationValue = duration;

    const response = await axios.post(playUrl);
    this.element.innerHTML = response.data;
    this.counterTarget.textContent = '-' + this.formatTime(this.durationValue);

    this.audioTarget.play();
  }

  close(event) {
    if (this.stopUrlValue) {
      axios.post(this.stopUrlValue);
    }
    this.element.innerHTML = '';
    this.episodeValue = '';
    this.durationValue = 0;

    this.lastUpdated = 0;
  }

  stop() {
    this.sendAjax('close', { episode: this.episode });
    this.close();
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
  }

  progress() {
    const { buffered } = this.audioTarget;
    this.bufferTarget.style.width = this.getPercentBuffered(buffered) + '%';
  }

  // observers

  pausedValueChanged() {
    if (this.hasPauseButtonTarget && this.hasPlayButtonTarget) {
      if (this.pausedValue) {
        this.pauseButtonTarget.classList.add('hidden');
        this.playButtonTarget.classList.remove('hidden');

        this.indicatorTarget.classList.remove(this.progressClass);
        this.indicatorTarget.classList.add(this.progressPausedClass);

        this.progressTarget.classList.remove(this.progressClass);
        this.progressTarget.classList.add(this.progressPausedClass);

        this.bufferTarget.classList.remove(this.bufferClass);
        this.bufferTarget.classList.add(this.bufferPausedClass);
      } else {
        this.pauseButtonTarget.classList.remove('hidden');
        this.playButtonTarget.classList.add('hidden');

        this.indicatorTarget.classList.add(this.progressClass);
        this.indicatorTarget.classList.remove(this.progressPausedClass);

        this.progressTarget.classList.add(this.progressClass);
        this.progressTarget.classList.remove(this.progressPausedClass);

        this.bufferTarget.classList.add(this.bufferClass);
        this.bufferTarget.classList.remove(this.bufferPausedClass);
      }
    }
  }

  currentTimeValueChanged() {
    if (this.hasProgressTarget && this.hasIndicatorTarget) {
      const pcComplete = this.getPercentComplete();

      this.progressTarget.style.width = pcComplete + '%';
      this.indicatorTarget.style.left = this.getCurrentPostion(pcComplete) + 'px';
    }

    if (this.hasCounterTarget) {
      this.counterTarget.textContent =
        '-' + this.formatTime(this.durationValue - this.currentTimeValue);
    }

    this.sendTimeUpdate();
  }

  getPercentBuffered(buffered) {
    const arr = [];
    for (let i = 0; i < buffered.length; ++i) {
      const start = buffered.start(i);
      const end = buffered.end(i);
      arr.push([start, end]);
    }

    if (arr.length === 0) {
      return 0;
    }

    const maxBuffered = arr.reduce(
      (acc, timeRange) => (timeRange[1] > acc ? timeRange[1] : acc),
      0
    );
    return (maxBuffered / this.durationValue) * 100 - this.getPercentComplete();
  }

  getPercentComplete() {
    if (!this.currentTimeValue || !this.durationValue) {
      return 0;
    }

    return (this.currentTimeValue / this.durationValue) * 100;
  }

  getCurrentPostion(pcComplete) {
    const clientWidth = this.progressBarTarget.clientWidth;

    let currentPosition, width;

    currentPosition = this.progressBarTarget.getBoundingClientRect().left - 16;

    if (clientWidth === 0) {
      width = 0;
    } else {
      // min 1rem to accomodate indicator
      const minWidth = (16 / clientWidth) * 100;
      width = pcComplete > minWidth ? pcComplete : minWidth;
    }

    if (width) {
      currentPosition += clientWidth * (width / 100);
    }

    return currentPosition;
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
