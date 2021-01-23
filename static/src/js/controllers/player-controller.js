import { Controller } from 'stimulus';
import { useDispatch } from 'stimulus-use';
import useTurbo from '../turbo';

export default class extends Controller {
  static targets = [
    'audio',
    'controls',
    'counter',
    'indicator',
    'nextEpisode',
    'pauseButton',
    'playButton',
    'progressBar',
  ];

  static classes = ['active', 'inactive'];

  static values = {
    csrfToken: String,
    currentTime: Number,
    duration: Number,
    markCompleteUrl: String,
    mediaUrl: String,
    paused: Boolean,
    timeupdateUrl: String,
    waiting: Boolean,
  };

  // events

  async initialize() {
    // Audio object is used instead of <audio> element to prevent resets
    // and skips with page transitions
    //
    this.initAudio();

    this.audio.currentTime = this.currentTimeValue;
    this.audio.src = this.mediaUrlValue;

    this.pausedValue = !this.enabled;

    if (this.audio && this.mediaUrlValue) {
      if (this.pausedValue) {
        this.pause();
      } else {
        this.play();
      }
    }
  }

  connect() {
    useDispatch(this);
    useTurbo(this);
  }

  async ended() {
    this.cancelTimeUpdateTimer();
    this.fetchJSON(this.markCompleteUrlValue);
    if (this.hasNextEpisodeTarget) {
      this.nextEpisodeTarget.requestSubmit();
    } else {
      this.closePlayer();
    }
  }

  async closePlayer() {
    this.durationValue = 0;
    this.mediaUrlValue = '';

    if (this.hasControlsTarget) {
      this.controlsTarget.remove();
    }
    this.closeAudio();
    this.cancelTimeUpdateTimer();
    this.dispatch('closePlayer');
  }

  loadedMetaData() {
    this.durationValue = this.audio.duration;
  }

  async play() {
    try {
      await this.audio.play();
    } catch (e) {
      console.error(e);
      this.pausedValue = true;
    }
  }

  pause() {
    this.audio.pause();
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

  wait() {
    this.waitingValue = true;
  }

  canPlay() {
    this.waitingValue = false;
  }

  timeUpdate() {
    // playing time update
    const { currentTime } = this.audio;
    this.currentTimeValue = currentTime;
    this.waitingValue = false;
  }

  skip(event) {
    // user clicks on progress bar
    const position = this.calcEventPosition(event.clientX);
    if (!isNaN(position) && position > -1) {
      this.skipTo(position);
    }
  }

  skipBack() {
    this.skipTo(this.audio.currentTime - 10);
  }

  skipForward() {
    this.skipTo(this.audio.currentTime + 10);
  }

  turboLoad() {
    // ensures audio is not "orphaned" if the controls are
    // removed through a turbo refresh - disconnect() isn't always called
    if (!document.getElementById('player-controls')) {
      this.closeAudio();
      this.cancelTimeUpdateTimer();
    }
  }

  turboSubmitEnd(event) {
    const { fetchResponse } = event.detail;
    const headers = fetchResponse.response ? fetchResponse.response.headers : null;
    if (!headers || !headers.has('X-Player')) {
      return;
    }
    const { action, episode, mediaUrl, currentTime } = JSON.parse(
      headers.get('X-Player')
    );
    if (action === 'stop') {
      console.log('close player');
      this.closePlayer();
      return;
    }
    // default : play
    //
    this.mediaUrlValue = mediaUrl;
    this.currentTimeValue = parseFloat(currentTime || 0);

    this.initAudio();

    this.audio.currentTime = this.currentTimeValue;
    this.audio.src = this.mediaUrlValue;

    this.play();
    this.dispatch('openPlayer', { episode });

    console.log('play:', mediaUrl, currentTime);
  }

  // observers
  pausedValueChanged() {
    if (this.hasPauseButtonTarget && this.playButtonTarget) {
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
      this.counterTarget.textContent = this.formatTimeRemaining(value);
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

  formatTimeRemaining(value) {
    if (!value || value < 0) return '00:00:00';
    const duration = Math.floor(parseInt(value));

    const hours = Math.floor(duration / 3600);
    const minutes = Math.floor((duration % 3600) / 60);
    const seconds = Math.floor(duration % 60);

    return (
      '-' +
      [hours, minutes, seconds].map((t) => t.toString().padStart(2, '0')).join(':')
    );
  }

  skipTo(position) {
    if (!isNaN(position) && !this.pausedValue && !this.waitingValue) {
      this.audio.currentTime = this.currentTimeValue = position;
    }
  }

  toggleActiveMode() {
    const inactive = this.pausedValue || this.waitingValue;
    if (inactive) {
      this.element.classList.add(this.inactiveClass);
      this.element.classList.remove(this.activeClass);
      this.cancelTimeUpdateTimer();
    } else {
      this.element.classList.remove(this.inactiveClass);
      this.element.classList.add(this.activeClass);
      this.startTimeUpdateTimer();
    }
  }

  initAudio() {
    console.log('initAudio');
    if (!this.audio) {
      this.audio = new Audio();
      this.audio.preload = 'metadata';

      this.audioListeners = {
        canplaythrough: this.canPlay.bind(this),
        ended: this.ended.bind(this),
        loadedmetadata: this.loadedMetaData.bind(this),
        play: this.resumed.bind(this),
        playing: this.canPlay.bind(this),
        pause: this.paused.bind(this),
        seeking: this.wait.bind(this),
        suspend: this.wait.bind(this),
        stalled: this.wait.bind(this),
        waiting: this.wait.bind(this),
        error: this.wait.bind(this),
        timeupdate: this.timeUpdate.bind(this),
      };
      Object.keys(this.audioListeners).forEach((event) =>
        this.audio.addEventListener(event, this.audioListeners[event])
      );
    }
  }

  closeAudio() {
    if (this.audio) {
      Object.keys(this.audioListeners || {}).forEach((event) =>
        this.audio.removeEventListener(event, this.audioListeners[event])
      );

      this.audio.src = '';
      this.audio.pause();
      this.audio = null;
      this.enabled = false;
    }
  }

  startTimeUpdateTimer() {
    if (!this.timeupdateTimer) {
      this.timeupdateTimer = setInterval(this.sendTimeUpdate.bind(this), 5000);
    }
  }

  cancelTimeUpdateTimer() {
    if (this.timeupdateTimer) {
      clearInterval(this.timeupdateTimer);
      this.timeupdateTimer = null;
    }
  }

  sendTimeUpdate() {
    if (this.currentTimeValue) {
      this.fetchJSON(this.timeupdateUrlValue, {
        currentTime: this.currentTimeValue,
      });
    }
  }

  fetchJSON(url, body) {
    return fetch(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': this.csrfTokenValue,
        'Content-Type': 'application/json',
      },
      credentials: 'same-origin',
      body: JSON.stringify(body || {}),
    });
  }

  set enabled(enabled) {
    if (enabled) {
      sessionStorage.setItem('player-enabled', true);
    } else {
      sessionStorage.removeItem('player-enabled');
    }
  }

  get enabled() {
    return !!sessionStorage.getItem('player-enabled');
  }
}
