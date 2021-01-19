import { Controller } from 'stimulus';
import { useDispatch } from 'stimulus-use';
import useTurbo from '../turbo';

export default class extends Controller {
  static targets = [
    'audio',
    'buffer',
    'controls',
    'counter',
    'indicator',
    'nextEpisode',
    'pauseButton',
    'playButton',
    'progress',
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
    skipInterval: Number,
    timeupdateUrl: String,
    waiting: Boolean,
  };

  // events

  async initialize() {
    // Audio object is used instead of <audio> element to prevent resets
    // and skips with page transitions
    //
    this.initAudio();

    this.audio.src = this.mediaUrlValue;
    this.audio.currentTime = this.currentTimeValue;

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

  progress() {
    // buffer update
    const { buffered } = this.audio;
    if (this.hasBufferTarget) {
      this.bufferTarget.style.width = this.getPercentBuffered(buffered) + '%';
    }
  }

  skip(event) {
    // user clicks on progress bar
    const position = this.getPosition(event.clientX);
    if (!isNaN(position) && position > -1) {
      this.skipTo(position);
    }
  }

  skipBack() {
    this.skipTo(this.audio.currentTime - this.skipIntervalValue);
  }

  skipForward() {
    this.skipTo(this.audio.currentTime + this.skipIntervalValue);
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

    this.audio.src = this.mediaUrlValue;
    this.audio.currentTime = this.currentTimeValue;

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
    if (this.durationValue) {
      if (this.hasCounterTarget) {
        this.counterTarget.textContent = '-' + this.formatTime(this.durationValue);
      }
    } else if (this.hasCounterTarget) {
      this.counterTarget.textContent = '00:00:00';
    }
    this.updateProgressBar();
  }

  currentTimeValueChanged() {
    this.updateProgressBar();
  }

  updateProgressBar() {
    if (this.hasProgressTarget && this.hasIndicatorTarget) {
      const pcComplete = this.getPercentComplete();
      this.progressTarget.style.width = pcComplete + '%';
      this.indicatorTarget.style.left =
        this.getCurrentIndicatorPosition(pcComplete) + 'px';
    }

    if (this.hasCounterTarget) {
      this.counterTarget.textContent =
        '-' + this.formatTime(this.durationValue - this.currentTimeValue);
    }
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

    if (this.currentTimeValue > this.durationValue) {
      return 100;
    }

    return (this.currentTimeValue / this.durationValue) * 100;
  }

  getCurrentIndicatorPosition(pcComplete) {
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
        progress: this.progress.bind(this),
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
