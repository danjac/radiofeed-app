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
    'loading',
    'title',
  ];

  static classes = ['active', 'inactive'];

  static values = {
    episode: Number,
    progressUrl: String,
    mediaUrl: String,
    stopUrl: String,
    pauseUrl: String,
    markCompleteUrl: String,
    resumeUrl: String,
    currentTime: Number,
    duration: Number,
    skipInterval: Number,
    error: Boolean,
    paused: Boolean,
    waiting: Boolean,
    loading: Boolean,
  };

  connect() {
    useDispatch(this);
  }

  async initialize() {
    this.audio = new Audio();
    this.audio.preload = 'metadata';

    this.audio.addEventListener('progress', this.progress.bind(this));
    this.audio.addEventListener('timeupdate', this.timeUpdate.bind(this));
    this.audio.addEventListener('ended', this.ended.bind(this));
    this.audio.addEventListener('canplaythrough', this.canPlay.bind(this));
    this.audio.addEventListener('playing', this.canPlay.bind(this));
    this.audio.addEventListener('stalled', this.wait.bind(this));
    this.audio.addEventListener('loadedmetadata', this.loadedMetaData.bind(this));

    this.audio.currentTime = this.currentTimeValue;

    if (this.mediaUrlValue) {
      this.audio.src = this.mediaUrlValue;
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
  }

  async open(event) {
    const { playUrl, mediaUrl, episode, currentTime } = event.detail;

    this.audio.src = this.mediaUrlValue = mediaUrl;

    this.loadingValue = true;
    this.errorValue = false;

    this.episodeValue = episode;

    this.dispatch('start', { episode });

    const response = await axios.post(playUrl, { current_time: currentTime });

    this.element.innerHTML = response.data;

    if (currentTime) {
      this.audio.currentTime = currentTime;
    }

    try {
      await this.audio.play();
    } catch (e) {
      console.error(e);
      this.errorValue = true;
    } finally {
      this.loadingValue = false;
    }
  }

  close() {
    this.closePlayer(this.stopUrlValue);
  }

  stop() {
    this.audio.pause();
    this.dispatch('close', {
      episode: this.episodeValue,
      currentTime: this.currentTimeValue,
    });
    this.closePlayer(this.stopUrlValue);
  }

  loadedMetaData() {
    this.durationValue = this.audio.duration;
  }

  ended() {
    this.dispatch('close', {
      episode: this.episodeValue,
      currentTime: this.currentTimeValue,
      completed: true,
    });
    this.closePlayer(this.markCompleteUrlValue);
  }

  async closePlayer(stopUrl) {
    if (stopUrl) {
      try {
        const response = await axios.post(stopUrl);
        this.dispatch('update', response.data);
        if (response.data.next_episode) {
          const { next_episode } = response.data;
          this.open({
            detail: {
              ...next_episode,
              mediaUrl: next_episode.media_url,
              playUrl: next_episode.play_url,
            },
          });
          return;
        }
      } catch (e) {
        console.error(e);
      }
    }
    this.element.innerHTML = '';
    this.durationValue = 0;
    this.lastUpdated = 0;
    this.episodeValue = '';
  }

  pause() {
    this.pausedValue = true;
    this.audio.pause();
    if (this.pauseUrlValue) {
      axios.post(this.pauseUrlValue);
    }
  }

  async play() {
    this.errorValue = false;
    this.pausedValue = false;
    try {
      await this.audio.play();
    } catch (e) {
      console.error(e);
      this.errorValue = true;
    }
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
    const { currentTime } = this.audio;
    this.currentTimeValue = currentTime;
  }

  progress() {
    const { buffered } = this.audio;
    if (this.hasBufferTarget) {
      this.bufferTarget.style.width = this.getPercentBuffered(buffered) + '%';
    }
  }

  skip(event) {
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
  }

  loadingValueChanged() {
    this.toggleActiveMode();
    if (this.hasTitleTarget && this.hasLoadingTarget) {
      if (this.loadingValue) {
        this.titleTargets.forEach((target) => target.classList.add('hidden'));
        this.loadingTargets.forEach((target) => target.classList.remove('hidden'));
      } else {
        this.titleTargets.forEach((target) => target.classList.remove('hidden'));
        this.loadingTargets.forEach((target) => target.classList.add('hidden'));
      }
    }
  }

  currentTimeValueChanged() {
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

    // update every 10s or so
    const diff = Math.ceil(Math.abs(this.currentTimeValue - this.lastUpdated || 0));
    const sendUpdate = this.currentTimeValue && diff % 10 === 0;

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
      this.audio.currentTime = this.currentTimeValue = position;
    }
  }

  toggleActiveMode() {
    const inactive =
      this.pausedValue || this.waitingValue || this.loadingValue || this.errorValue;
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
