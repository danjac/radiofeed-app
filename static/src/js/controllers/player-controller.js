import { renderStreamMessage } from '@hotwired/turbo';
import { Controller } from 'stimulus';

export default class extends Controller {
  static targets = [
    'audio',
    'closeButton',
    'counter',
    'indicator',
    'pauseButton',
    'playbackRate',
    'playButton',
    'progressBar',
  ];

  static classes = ['active', 'inactive'];

  static values = {
    csrfToken: String,
    currentTime: Number,
    duration: Number,
    mediaUrl: String,
    metadata: Object,
    newEpisode: Boolean,
    paused: Boolean,
    playbackRate: Number,
    playNextUrl: String,
    timeupdateUrl: String,
    timeupdateSending: Boolean,
    timeupdateSent: Number,
    waiting: Boolean,
  };

  // events
  //
  connect() {
    this.playbackRateValue = parseFloat(sessionStorage.getItem('playback-rate') || 1.0);

    // automatically pause unless new episode or enabled
    if (!sessionStorage.getItem('player-enabled') && !this.newEpisodeValue) {
      this.pause();
    }
  }

  async ended() {
    const response = await this.doFetch(this.playNextUrlValue, {
      headers: { Accept: 'text/vnd.turbo-stream.html' },
    });
    const html = await response.text();
    renderStreamMessage(html);
  }

  loadedMetaData() {
    this.durationValue = this.audioTarget.duration;
  }

  async play() {
    try {
      await this.audioTarget.play();
    } catch (e) {
      console.error(e);
      this.pausedValue = true;
    }
  }

  pause() {
    this.audioTarget.pause();
  }

  shortcuts(event) {
    // ignore if inside an input element
    //
    if (/^(INPUT|SELECT|TEXTAREA)$/.test(event.target.tagName)) {
      return;
    }

    const handlers = {
      '+': this.incrementPlaybackRate,
      '-': this.decrementPlaybackRate,
      ArrowLeft: this.skipBack,
      ArrowRight: this.skipForward,
      Delete: this.closePlayer,
      Space: this.togglePause,
    };

    const handler = handlers[event.code] || handlers[event.key];

    if (handler) {
      event.preventDefault();
      handler.bind(this)();
    }
  }

  togglePause() {
    if (this.pausedValue) {
      this.play();
    } else {
      this.pause();
    }
  }

  resumed() {
    this.pausedValue = false;
    this.waitingValue = false;
    sessionStorage.setItem('player-enabled', true);
  }

  paused() {
    this.pausedValue = true;
    sessionStorage.removeItem('player-enabled');
  }

  wait(event) {
    this.waitingValue = true;
  }

  canPlay() {
    this.waitingValue = false;
  }

  timeUpdate() {
    // playing time update
    const { currentTime } = this.audioTarget;
    this.currentTimeValue = currentTime;
    this.waitingValue = false;
  }

  incrementPlaybackRate() {
    this.changePlaybackRate(0.1);
  }

  decrementPlaybackRate() {
    this.changePlaybackRate(-0.1);
  }

  skip({ clientX }) {
    // user clicks on progress bar
    const position = this.calcEventPosition(clientX);
    if (!isNaN(position) && position > -1) {
      this.skipTo(position);
    }
  }

  showPosition({ clientX }) {
    const position = this.calcEventPosition(clientX);
    if (!isNaN(position)) {
      this.progressBarTarget.setAttribute('title', this.formatTime(position));
    }
  }

  skipBack() {
    this.skipTo(this.audioTarget.currentTime - 10);
  }

  skipForward() {
    this.skipTo(this.audioTarget.currentTime + 10);
  }

  mediaUrlValueChanged() {
    this.audioTarget.src = this.mediaUrlValue;
    this.audioTarget.currentTime = this.currentTimeValue;

    if (this.mediaUrlValue && !this.pausedValue) {
      this.play();
    } else {
      this.pause();
    }
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
    this.toggleActiveMode();
  }

  waitingValueChanged() {
    this.toggleActiveMode();
  }

  durationValueChanged() {
    this.updateCounter(this.durationValue);
    this.updateProgressBar();
  }

  currentTimeValueChanged() {
    this.updateCounter(this.durationValue - this.currentTimeValue);
    this.updateProgressBar();
    this.sendCurrentTimeUpdate();
  }

  playbackRateValueChanged() {
    this.audioTarget.playbackRate = this.playbackRateValue;

    if (this.hasPlaybackRateTarget) {
      this.playbackRateTarget.textContent = this.playbackRateValue.toFixed(1) + 'x';
    }
  }

  metadataValueChanged() {
    if ('mediaSession' in navigator) {
      if (Object.keys(this.metadataValue).length > 0) {
        navigator.mediaSession.metadata = new window.MediaMetadata(this.metadataValue);
      } else {
        navigator.mediaSession.metadata = null;
      }
    }
  }

  changePlaybackRate(increment) {
    let newValue = this.playbackRateValue + increment;
    if (newValue > 2.0) {
      newValue = 2.0;
    } else if (newValue < 0.5) {
      newValue = 0.5;
    }
    this.playbackRateValue = newValue;
    sessionStorage.setItem('playback-rate', this.playbackRateValue);
  }

  updateProgressBar() {
    if (this.hasIndicatorTarget) {
      const pcComplete = this.calcPercentComplete();
      this.indicatorTarget.style.left =
        this.calcCurrentIndicatorPosition(pcComplete) + 'px';
    }
  }

  updateCounter(value) {
    if (this.hasCounterTarget) {
      this.counterTarget.textContent = this.formatTime(value);
    }
  }

  calcPercentComplete() {
    if (!this.currentTimeValue || !this.durationValue) {
      return 0;
    }

    if (this.currentTimeValue > this.durationValue) {
      return 100;
    }

    return (this.currentTimeValue / this.durationValue) * 100;
  }

  calcEventPosition(clientX) {
    if (!isNaN(clientX)) {
      const { left } = this.progressBarTarget.getBoundingClientRect();
      const width = this.progressBarTarget.clientWidth;
      let position = clientX - left;
      return Math.ceil(this.durationValue * (position / width));
    } else {
      return -1;
    }
  }

  calcCurrentIndicatorPosition(pcComplete) {
    const clientWidth = this.progressBarTarget.clientWidth;

    let currentPosition, width;

    currentPosition = this.progressBarTarget.getBoundingClientRect().left - 24;

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

  formatTime(value) {
    if (isNaN(value) || value < 0) return '00:00:00';
    const duration = Math.floor(value);

    const hours = Math.floor(duration / 3600);
    const minutes = Math.floor((duration % 3600) / 60);
    const seconds = Math.floor(duration % 60);

    return [hours, minutes, seconds]
      .map((t) => t.toString().padStart(2, '0'))
      .join(':');
  }

  closePlayer() {
    this.closeButtonTarget.click();
  }

  skipTo(position) {
    if (!isNaN(position) && !this.pausedValue && !this.waitingValue) {
      this.audioTarget.currentTime = this.currentTimeValue = position;
    }
  }

  toggleActiveMode() {
    const inactive = this.pausedValue || this.waitingValue;
    if (inactive) {
      this.element.classList.add(this.inactiveClass);
      this.element.classList.remove(this.activeClass);
    } else {
      this.element.classList.remove(this.inactiveClass);
      this.element.classList.add(this.activeClass);
    }
  }

  async sendCurrentTimeUpdate() {
    // sends current time to server
    const now = new Date().getTime();

    // ignore if waiting/paused/empty or less than 5s since last send
    if (
      !this.currentTimeValue ||
      !this.mediaUrlValue ||
      this.waitingValue ||
      this.pausedValue ||
      this.timeupdateSendingValue ||
      now - this.timeupdateSentValue < 5000
    ) {
      return;
    }

    this.timeupdateSendingValue = true;

    const body = new FormData();
    body.append('current_time', this.currentTimeValue);
    try {
      await this.doFetch(this.timeupdateUrlValue, { body });
    } finally {
      this.timeupdateSentValue = now;
      this.timeupdateSendingValue = false;
    }
  }

  doFetch(url, options = {}) {
    const body = options.body || new FormData();
    body.append('csrfmiddlewaretoken', this.csrfTokenValue);
    return fetch(url, {
      body,
      method: 'POST',
      credentials: 'same-origin',
      ...options,
    });
  }
}
