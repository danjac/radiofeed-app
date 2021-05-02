import { dispatch, formatDuration, percent } from './utils';

export default function (htmx, options) {
  const { csrfToken, urls } = options;

  let timer;

  const doFetch = (url, options) => {
    options = options || {};
    const body = options.body || new FormData();
    body.append('csrfmiddlewaretoken', csrfToken);
    return fetch(url, {
      body,
      method: 'POST',
      credentials: 'same-origin',
      ...options,
    });
  };

  const defaults = {
    episode: null,
    podcast: null,
    currentTime: 0,
    duration: 0,
    audio: null,
    isPlaying: false,
    isPaused: false,
    isWaiting: false,
    playbackRate: 1.0,
    counter: '-00:00:00',
  };

  const instance = {
    ...defaults,
    initialize() {
      if (this.episode) {
        this.startPlayer(this.episode.mediaUrl);
      }
      this.$watch('episode', (value) => {
        this.stopPlayer();
        if (value) {
          this.startPlayer(value.mediaUrl);
        }
      });
      this.$watch('duration', (value) => {
        this.updateProgressBar(value, this.currentTime);
      });
      this.$watch('currentTime', (value) => {
        this.updateProgressBar(this.duration, value);
      });
    },
    playEpisode($event) {
      const { url } = $event.detail;
      doFetch(url)
        .then((response) => response.json())
        .then((data) => {
          this.openPlayer(data);
        });
    },
    openPlayer(data) {
      if (data) {
        const { episode, podcast, currentTime, metadata } = data;
        this.episode = episode;
        this.podcast = podcast;
        this.currentTime = currentTime;

        if (metadata && 'mediaSession' in navigator) {
          if (Object.keys(metadata).length > 0) {
            navigator.mediaSession.metadata = new window.MediaMetadata(metadata);
          } else {
            navigator.mediaSession.metadata = null;
          }
        }
        dispatch(this.$el, 'open-player', data);
      }
      this.$nextTick(() => {
        // re-hook up any htmx events
        htmx.process(this.$el);
      });
    },
    closePlayer() {
      doFetch(urls.closePlayer);
      this.episode = null;
      this.podcast = null;
      this.currentTime = 0;
    },
    // audio events
    loaded() {
      this.duration = this.audio.duration;
    },
    timeUpdate() {
      if (this.audio) {
        this.currentTime = this.audio.currentTime;
        /*
          const body = new FormData();
          body.append('current_time', this.currentTime);
          doFetch(urls.timeUpdate, {
            body,
          });
          */
      }
    },
    resumed() {
      this.isPlaying = true;
      this.isPaused = false;
      this.isWaiting = false;
    },
    paused() {
      this.isPlaying = false;
      this.isPaused = true;
      this.isWaiting = false;
    },
    waiting() {
      this.isWaiting = true;
    },
    active() {
      this.isWaiting = false;
    },
    ended() {
      doFetch(urls.playNextEpisode)
        .then((response) => response.json())
        .then((data) => {
          if (Object.keys(data).length === 0) {
            dispatch(this.$el, 'close-player');
          } else {
            this.openPlayer(data);
          }
        });
    },
    shortcuts(event) {
      // ignore if inside an input element
      if (!this.audio) {
        return;
      }

      if (/^(INPUT|SELECT|TEXTAREA)$/.test(event.target.tagName)) {
        return;
      }
      const handlers = {
        '+': this.incrementPlaybackRate,
        '-': this.decrementPlaybackRate,
        ArrowLeft: this.skipBack,
        ArrowRight: this.skipForward,
        Space: this.togglePause,
        //Delete: this.closePlayer,
      };

      const handler = handlers[event.code] || handlers[event.key];

      if (handler) {
        event.preventDefault();
        handler.bind(this)();
      }
    },

    incrementPlaybackRate() {
      this.changePlaybackRate(0.1);
    },
    decrementPlaybackRate() {
      this.changePlaybackRate(-0.1);
    },

    changePlaybackRate(increment) {
      const value = this.playbackRate;
      let newValue = value + increment;
      if (newValue > 2.0) {
        newValue = 2.0;
      } else if (newValue < 0.5) {
        newValue = 0.5;
      }
      this.audio.playbackRate = this.playbackRate = newValue;
    },

    skip({ clientX }) {
      // user clicks on progress bar
      const position = this.getProgressBarPosition(clientX);
      if (!isNaN(position) && position > -1) {
        this.skipTo(position);
      }
    },

    skipBack() {
      this.skipTo(this.audio.currentTime - 10);
    },

    skipForward() {
      this.skipTo(this.audio.currentTime + 10);
    },

    skipTo(position) {
      if (!isNaN(position) && !this.isPaused) {
        this.audio.currentTime = position;
      }
    },

    togglePause() {
      if (this.isPaused) {
        this.audio.play();
      } else {
        this.audio.pause();
      }
    },
    startPlayer(mediaUrl) {
      this.audio = new Audio(mediaUrl);
      this.audio.currentTime = this.currentTime;

      const events = this.getAudioEvents();
      Object.keys(events).forEach((name) => {
        this.audio.addEventListener(name, events[name].bind(this));
      });

      this.audio.play().catch((e) => {
        console.log(e);
        this.isPaused = true;
      });
      timer = setInterval(this.sendCurrentTimeUpdate.bind(this), 5000);
    },
    stopPlayer() {
      if (this.audio) {
        this.audio.pause();
        const events = this.getAudioEvents();
        Object.keys(events).forEach((name) => {
          this.audio.removeEventListener(name, events[name].bind(this));
        });
        this.audio = null;
      }
      if (timer) {
        clearInterval(timer);
      }
    },
    sendCurrentTimeUpdate() {
      if (this.audio && !this.isPaused && !this.isWaiting && this.currentTime) {
        const body = new FormData();
        body.append('current_time', this.currentTime);
        doFetch(urls.timeUpdate, {
          body,
        });
      }
    },
    getAudioEvents() {
      return {
        play: this.resumed,
        pause: this.paused,
        error: this.waiting,
        suspend: this.waiting,
        stalled: this.waiting,
        canplaythrough: this.active,
        canplay: this.active,
        playing: this.active,
        loadedmetadata: this.loaded,
        ended: this.ended,
        timeupdate: this.timeUpdate,
      };
    },
    updateProgressBar(duration, currentTime) {
      if (this.audio) {
        this.counter = '-' + formatDuration(duration - currentTime);
        const pcComplete = percent(duration, currentTime);
        // TBD: just use a prop
        this.$refs.indicator.style.left = this.getIndicatorPosition(pcComplete) + 'px';
      }
    },
    getProgressBarPosition(clientX) {
      if (!isNaN(clientX)) {
        const { left } = this.$refs.progressBar.getBoundingClientRect();
        const width = this.$refs.progressBar.clientWidth;
        let position = clientX - left;
        return Math.ceil(this.duration * (position / width));
      } else {
        return -1;
      }
    },
    getIndicatorPosition(pcComplete) {
      const clientWidth = this.$refs.progressBar.clientWidth;
      let currentPosition, width;

      currentPosition = this.$refs.progressBar.getBoundingClientRect().left - 24;

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
    },
  };

  const playerInfoTag = document.getElementById('player-info');

  if (playerInfoTag) {
    return {
      ...instance,
      ...JSON.parse(playerInfoTag.textContent),
    };
  }

  return instance;
}
