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
    episode: Number,
    progressUrl: String,
    mediaUrl: String,
    stopUrl: String,
    markCompleteUrl: String,
    csrfToken: String,
    currentTime: Number,
    duration: Number,
    skipInterval: Number,
    error: Boolean,
    paused: Boolean,
    waiting: Boolean,
  };

  connect() {
    useDispatch(this);
    // check if player ID is present, close audio if not
    // we could also check value...
  }

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

    this.audio.currentTime = this.currentTimeValue;

    if (this.mediaUrlValue) {
      this.audio.src = this.mediaUrlValue;

      // sessionStorage toggle is set to prevent automatically starting
      // player if opening in another tab.

      if (!sessionStorage.getItem('player-enabled')) {
        this.pausedValue = true;
      }

      try {
        if (this.pausedValue) {
          await this.audio.pause();
        } else {
          await this.audio.play();
        }
      } catch (e) {
        console.error(e);
        this.errorValue = true;
      }
    }

    // make sure audio is properly closed when controls are removed
    // from the DOM
    document.documentElement.addEventListener('turbo:load', () => {
      if (!document.getElementById('player-controls')) {
        this.audio.src = '';
      }
    });

    document.documentElement.addEventListener(
      'turbo:submit-end',
      ({ detail: { fetchResponse } }) => {
        const currentTime = fetchResponse.response.headers.get('X-Player-Current-Time');
        const mediaUrl = fetchResponse.response.headers.get('X-Player-Media-Url');
        if (mediaUrl) {
          this.audio.src = mediaUrl;
          if (currentTime) {
            this.audio.currentTime = parseFloat(currentTime);
          }
          this.audio.play();
        } else {
          this.audio.src = '';
          this.audio.pause();
        }
      }
    );
  }

  async open(event) {
    // new episode is loaded into player
    const { playUrl, episode } = event.detail;

    this.episodeValue = episode;

    this.dispatch('start', { episode });

    const response = await this.fetchJSON(playUrl);
    const currentTime = response.headers.get('X-Player-Current-Time');
    const mediaUrl = response.headers.get('X-Player-Media-Url');

    if (!mediaUrl) {
      console.log('No URL found in X-Player-Media-Url-Header');
      this.closePlayer();
      return;
    }

    this.audio.src = this.mediaUrlValue = mediaUrl;

    this.element.innerHTML = await response.text();

    sessionStorage.setItem('player-enabled', true);

    if (currentTime) {
      this.audio.currentTime = parseFloat(currentTime);
    }

    this.audio.play();
  }

  close() {
    this.audio.pause();
    this.dispatch('close', {
      episode: this.episodeValue,
    });
    this.closePlayer(this.stopUrlValue);
  }

  ended() {
    // episode is completed
    this.dispatch('close', {
      episode: this.episodeValue,
    });
    this.closePlayer(this.markCompleteUrlValue);
  }

  async closePlayer(stopUrl) {
    if (stopUrl) {
      const response = await this.fetchJSON(stopUrl);
      const { nextEpisode } = await response.json();
      if (nextEpisode) {
        this.open({ detail: nextEpisode });
        return;
      }
    }
    this.element.innerHTML = '';
    this.durationValue = 0;
    this.lastUpdated = 0;
    this.episodeValue = '';

    sessionStorage.removeItem('player-enabled');
  }

  loadedMetaData() {
    this.durationValue = this.audio.duration;
  }

  pause() {
    this.audio.pause();
  }

  resumed() {
    sessionStorage.setItem('player-enabled', true);
    this.pausedValue = false;
  }

  paused() {
    sessionStorage.removeItem('player-enabled');
    this.pausedValue = true;
  }

  async play() {
    this.errorValue = false;

    try {
      await this.audio.play();
    } catch (e) {
      console.error(e);
      this.errorValue = true;
    }
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
}
