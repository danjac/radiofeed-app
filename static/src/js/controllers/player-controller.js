import { Controller } from 'stimulus';

export default class extends Controller {
  static targets = [
    'audio',
    'controls',
    'counter',
    'indicator',
    'pauseButton',
    'playbackRate',
    'playButton',
    'playNextButton',
    'progressBar',
    'stopButton',
  ];

  static classes = ['active', 'inactive'];

  static values = {
    csrfToken: String,
    currentTime: Number,
    duration: Number,
    mediaUrl: String,
    metadata: Object,
    paused: Boolean,
    playbackRate: Number,
    playbackRateUrl: String,
    timeupdateUrl: String,
    timeupdateSent: Number,
    waiting: Boolean,
  };

  // events

  ended() {
    this.cancelTimeUpdateTimer();
    if (this.hasPlayNextButtonTarget) {
      this.playNextButtonTarget.click();
    } else {
      this.stopButtonTarget.click();
    }
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
    // ignore if player not running or inside an input element
    if (!this.hasControlsTarget || this.isInputTarget(event)) {
      return;
    }

    switch (event.code) {
      case 'Space':
        event.preventDefault();
        this.togglePause();
        return;
      case 'ArrowLeft':
        event.preventDefault();
        this.skipBack();
        return;
      case 'ArrowRight':
        event.preventDefault();
        this.skipForward();
        return;
      case 'Delete':
        event.preventDefault();
        this.stopButtonTarget.click();
        return;
      case 'Tab':
        if (event.shiftKey && this.hasPlayNextButtonTarget) {
          event.preventDefault();
          this.playNextButtonTarget.click();
          return;
        }
      default:
    }

    switch (event.key) {
      case '-':
        event.preventDefault();
        this.decrementPlaybackRate();
        return;

      case '+':
        event.preventDefault();
        this.incrementPlaybackRate();
        return;
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
    this.enabled = true;
    this.pausedValue = false;
    this.waitingValue = false;
  }

  paused() {
    this.enabled = false;
    this.pausedValue = true;
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

    if (this.mediaUrlValue) {
      if (this.pausedValue) {
        this.pause();
      } else {
        this.play();
      }
    } else {
      this.audioTarget.pause();
    }
    this.toggleActiveMode();
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
    this.sendPlaybackRateUpdate();
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

  sendPlaybackRateUpdate() {
    this.sendPlayerStatusUpdate(this.playbackRateUrlValue, {
      playback_rate: this.playbackRateValue.toFixed(1),
    });
  }

  async sendCurrentTimeUpdate() {
    if (this.shouldSendCurrentTimeUpdate()) {
      await this.sendPlayerStatusUpdate(this.timeupdateUrlValue, {
        current_time: this.currentTimeValue,
      });
      this.timeupdateSentValue = new Date().getTime();
    }
  }

  shouldSendCurrentTimeUpdate() {
    // send every 5s if player is running
    if (!this.currentTimeValue || !this.mediaUrlValue || this.pausedValue) {
      return false;
    }
    return new Date().getTime() - this.timeupdateSentValue > 5000;
  }

  sendPlayerStatusUpdate(url, formData) {
    const body = new FormData();

    Object.keys(formData).forEach((key) => {
      body.append(key, formData[key]);
    });

    body.append('csrfmiddlewaretoken', this.csrfTokenValue);

    return fetch(url, {
      body,
      method: 'POST',
      credentials: 'same-origin',
    });
  }

  isInputTarget(event) {
    return /^(INPUT|SELECT|TEXTAREA)$/.test(event.target.tagName);
  }

  set enabled(enabled) {
    if (enabled) {
      sessionStorage.setItem('player-enabled', 'true');
    } else {
      sessionStorage.removeItem('player-enabled');
    }
  }

  get enabled() {
    return !!sessionStorage.getItem('player-enabled');
  }
}
