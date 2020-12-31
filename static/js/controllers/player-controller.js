import { Controller } from 'stimulus';
import { useDispatch } from 'stimulus-use';

export default class extends Controller {
  static targets = [
    'audio',
    'buffer',
    'counter',
    'controls',
    'indicator',
    'nextEpisode',
    'pauseButton',
    'playButton',
    'progress',
    'progressBar',
  ];

  static classes = ['active', 'inactive'];

  static values = {
    episode: Number,
    progressUrl: String,
    mediaUrl: String,
    markCompleteUrl: String,
    csrfToken: String,
    currentTime: Number,
    duration: Number,
    skipInterval: Number,
    error: Boolean,
    paused: Boolean,
    waiting: Boolean,
  };

  async initialize() {
    // Audio object is used instead of <audio> element to prevent resets
    // and skips with page transitions
    this.audio = new Audio();
    this.audio.preload = 'metadata';

    this.audio.addEventListener('progress', this.progress.bind(this));
    this.audio.addEventListener('timeupdate', this.timeUpdate.bind(this));
    this.audio.addEventListener('ended', this.ended.bind(this));
    this.audio.addEventListener('pause', this.paused.bind(this));
    this.audio.addEventListener('play', this.resumed.bind(this));
    this.audio.addEventListener('canplaythrough', this.canPlay.bind(this));
    this.audio.addEventListener('playing', this.canPlay.bind(this));
    this.audio.addEventListener('stalled', this.wait.bind(this));
    this.audio.addEventListener('loadedmetadata', this.loadedMetaData.bind(this));

    if (this.mediaUrlValue) {
      this.audio.src = this.mediaUrlValue;
      this.audio.currentTime = this.currentTimeValue;

      if (!this.enabled) {
        this.pausedValue = true;
      }

      if (this.pausedValue) {
        this.pause();
      } else {
        this.play();
      }
    }
  }

  connect() {
    useDispatch(this);
    // make sure audio is properly closed when controls are removed
    // from the DOM

    this.onTurboLoad = this.turboLoad.bind(this);

    document.documentElement.addEventListener('turbo:load', this.onTurboLoad, true);
    this.onTurboSubmitEnd = this.turboSubmitEnd.bind(this);

    document.documentElement.addEventListener(
      'turbo:submit-end',
      this.onTurboSubmitEnd,
      true
    );
  }

  disconnect() {
    document.documentElement.removeEventListener('turbo:load', this.onTurboLoad, true);
    document.documentElement.removeEventListener(
      'turbo:submit-end',
      this.onTurboSubmitEnd,
      true
    );
  }

  async ended() {
    const response = await this.fetchJSON(this.markCompleteUrlValue);
    const data = await response.json();
    // how to check if autoplay is on???
    if (data.autoplay && this.hasNextEpisodeTarget) {
      this.nextEpisodeTarget.requestSubmit();
    } else {
      this.closePlayer();
    }
  }

  async closePlayer() {
    this.durationValue = 0;
    this.lastUpdated = 0;
    this.episodeValue = '';
    this.mediaUrlValue = '';

    if (this.hasControlsTarget) {
      this.controlsTarget.remove();
    }

    this.stopAudio();
    this.dispatch('stop');
  }

  loadedMetaData() {
    this.durationValue = this.audio.duration;
  }

  pause() {
    this.audio.pause();
  }

  resumed() {
    this.enabled = true;
    this.pausedValue = false;
  }

  paused() {
    this.enabled = false;
    this.pausedValue = true;
  }

  play() {
    this.enabled = true;
    this.audio.play();
  }

  canPlay() {
    this.waitingValue = false;
  }

  wait() {
    this.waitingValue = true;
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

  stopAudio() {
    this.audio.src = '';
    this.audio.pause();
    this.enabled = false;
  }

  turboLoad() {
    // ensures audio is not "orphaned" if the controls are
    // removed through a turbo refresh
    if (!document.getElementById('player-controls')) {
      this.stopAudio();
    }
  }

  turboSubmitEnd(event) {
    const { fetchResponse } = event.detail;
    const headers = fetchResponse.response ? fetchResponse.response.headers : null;
    if (!headers) {
      return;
    }
    const action = headers && headers.get('X-Player-Action');
    if (!action) {
      return;
    }

    if (action === 'stop') {
      console.log('stop');
      this.closePlayer();
      return;
    }
    // default : play

    const episode = headers.get('X-Player-Episode');
    const currentTime = headers.get('X-Player-Current-Time');
    const mediaUrl = headers.get('X-Player-Media-Url');

    console.log('play:', episode, mediaUrl, currentTime);

    if (mediaUrl && mediaUrl != this.audio.src) {
      this.audio.src = this.mediaUrlValue = mediaUrl;
      if (currentTime) {
        this.audio.currentTime = parseFloat(currentTime);
      }
      this.play();
      if (episode) {
        this.dispatch('play', { episode });
      }
    }
  }

  // observers
  errorValueChanged() {
    this.toggleActiveMode();
  }

  pausedValueChanged() {
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
    this.sendTimeUpdate();
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

  async sendTimeUpdate() {
    if (!this.hasEpisodeValue) {
      return;
    }

    // should probably just use setInterval, but this is easier to stop/start

    // update every 10s or so
    const diff = Math.ceil(Math.abs(this.currentTimeValue - this.lastUpdated || 0));
    const sendUpdate = this.currentTimeValue && diff % 5 === 0;

    if (sendUpdate) {
      this.lastUpdated = this.currentTimeValue;
      this.fetchJSON(this.progressUrlValue, {
        currentTime: this.currentTimeValue,
      });
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
      this.audio.currentTime = this.currentTimeValue = position;
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
