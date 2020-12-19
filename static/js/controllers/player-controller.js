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

  static classes = ['active', 'inactive'];

  static values = {
    episode: String,
    progressUrl: String,
    stopUrl: String,
    pauseUrl: String,
    resumeUrl: String,
    currentTime: Number,
    duration: Number,
    paused: Boolean,
    waiting: Boolean,
  };

  connect() {
    useDispatch(this);
  }

  async initialize() {
    if (this.hasAudioTarget) {
      this.audioTarget.currentTime = this.currentTimeValue;
      try {
        if (this.pausedValue) {
          await this.audioTarget.pause();
        } else {
          await this.audioTarget.play();
        }
      } catch (e) {
        this.pausedValue = true;
      }
    }
  }

  async open(event) {
    // TBD: include currentTime i.e. for episodes in progress
    const { playUrl, episode, currentTime, duration } = event.detail;

    this.episodeValue = episode;
    this.durationValue = duration;

    const response = await axios.post(playUrl, { current_time: currentTime });
    this.element.innerHTML = response.data;
    this.counterTarget.textContent = '-' + this.formatTime(this.durationValue);

    if (currentTime) {
      this.audioTarget.currentTime = currentTime;
    }

    this.audioTarget.play();
  }

  close() {
    this.closePlayer();
  }

  stop() {
    this.dispatch('close', {
      episode: this.episodeValue,
      currentTime: this.currentTimeValue,
    });
    this.closePlayer();
  }

  async closePlayer() {
    this.element.innerHTML = '';
    this.durationValue = 0;
    this.lastUpdated = 0;
    if (this.stopUrlValue) {
      const response = await axios.post(this.stopUrlValue);
      this.dispatch('update', response.data);
    }
    this.episodeValue = '';
  }

  pause() {
    this.pausedValue = true;
    this.audioTarget.pause();
    if (this.pauseUrlValue) {
      axios.post(this.pauseUrlValue);
    }
  }

  play() {
    this.pausedValue = false;
    this.audioTarget.play();
    if (this.resumeUrlValue) {
      axios.post(this.resumeUrlValue);
    }
  }

  canPlay() {
    this.waitingValue = false;
  }

  wait() {
    this.waitingValue = true;
  }

  timeUpdate() {
    const { currentTime } = this.audioTarget;
    this.currentTimeValue = currentTime;
  }

  progress() {
    const { buffered } = this.audioTarget;
    this.bufferTarget.style.width = this.getPercentBuffered(buffered) + '%';
  }

  skip(event) {
    const position = this.getPosition(event.clientX);
    if (!isNaN(position) && position > -1) {
      this.skipTo(position);
    }
  }

  skipBack() {
    this.skipTo(this.audioTarget.currentTime - 15);
  }

  skipForward() {
    this.skipTo(this.audioTarget.currentTime + 15);
  }

  // observers

  pausedValueChanged() {
    this.toggleActiveMode();
  }

  waitingValueChanged() {
    this.toggleActiveMode();
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

    this.sendTimeUpdate(false);
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

  async sendTimeUpdate(immediate) {
    if (!this.hasEpisodeValue) {
      return;
    }
    // update every 10s or so
    let sendUpdate = immediate;
    if (!sendUpdate) {
      const diff = Math.ceil(Math.abs(this.currentTimeValue - this.lastUpdated || 0));
      sendUpdate = this.currentTimeValue && diff % 10 === 0;
    }
    if (sendUpdate) {
      this.lastUpdated = this.currentTimeValue;
      const response = await axios.post(this.progressUrlValue, {
        current_time: this.currentTimeValue,
      });
      this.dispatch('update', response.data);
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

  getPosition(clientX) {
    if (!isNaN(clientX)) {
      const { left } = this.progressBarTarget.getBoundingClientRect();
      const width = this.progressBarTarget.clientWidth;
      let position = clientX - left;
      return Math.ceil(this.durationValue * (position / width));
    } else {
      return -1;
    }
  }

  skipTo(position) {
    if (!isNaN(position) && !this.pausedValue && !this.waitingValue) {
      this.audioTarget.currentTime = this.currentTimeValue = position;
      this.sendTimeUpdate(true);
    }
  }

  toggleActiveMode() {
    const inactive = this.pausedValue || this.waitingValue;
    if (this.hasPauseButtonTarget && this.hasPlayButtonTarget) {
      if (inactive) {
        this.pauseButtonTarget.classList.add('hidden');
        this.playButtonTarget.classList.remove('hidden');

        this.element.classList.remove(this.activeClass);
        this.element.classList.add(this.inactiveClass);
      } else {
        this.pauseButtonTarget.classList.remove('hidden');
        this.playButtonTarget.classList.add('hidden');

        this.element.classList.add(this.activeClass);
        this.element.classList.remove(this.inactiveClass);
      }
    }
  }
}
