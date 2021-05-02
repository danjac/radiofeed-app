const formatDuration = (value) => {
  if (isNaN(value) || value < 0) return '00:00:00';
  const duration = Math.floor(value);

  const hours = Math.floor(duration / 3600);
  const minutes = Math.floor((duration % 3600) / 60);
  const seconds = Math.floor(duration % 60);

  return [hours, minutes, seconds].map((t) => t.toString().padStart(2, '0')).join(':');
};

const calcPercentComplete = (duration, currentTime) => {
  if (!currentTime || !duration) {
    return 0;
  }

  if (currentTime > duration) {
    return 100;
  }

  return (currentTime / duration) * 100;
};

export default function (htmx, options) {
  const { csrfToken, urls } = options;

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
    counter: '-00:00:00',
  };

  const playerInfoTag = document.getElementById('player-info');

  const instance = {
    ...defaults,
    initialize() {
      if (this.episode) {
        console.log('we have episode', this.episode);
        this.startAudio();
      }
      this.$watch('episode', (value) => {
        console.log('episode???', value);
        this.stopAudio();
        if (value) {
          this.startAudio();
        }
      });
      this.$watch('duration', (value) => {
        this.updateProgressBar(value, this.currentTime);
      });
      this.$watch('currentTime', (value) => {
        this.updateProgressBar(this.duration, value);
      });
    },
    openPlayer(event) {
      if (event) {
        const { episode, podcast, currentTime } = event.detail;
        this.episode = episode;
        this.podcast = podcast;
        this.currentTime = currentTime;
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
      console.log('resumed');
      this.isPlaying = true;
      this.isPaused = false;
      this.isWaiting = false;
    },
    paused() {
      console.log('paused');
      this.isPlaying = false;
      this.isPaused = true;
      this.isWaiting = false;
    },
    waiting() {
      console.log('waiting');
      this.isWaiting = true;
    },
    active() {
      console.log('active');
      this.isWaiting = false;
    },
    ended() {
      console.log('ended');
      this.$dispatch('close-player');
    },
    startAudio() {
      this.audio = new Audio(this.episode.mediaUrl);
      this.audio.currentTime = this.currentTime;
      const events = this.getAudioEvents();
      Object.keys(events).forEach((name) => {
        this.audio.addEventListener(name, events[name].bind(this));
      });
      this.audio.play().catch(() => this.audio.pause());
    },
    stopAudio() {
      if (this.audio) {
        this.audio.pause();
        const events = this.getAudioEvents();
        Object.keys(events).forEach((name) => {
          this.audio.removeEventListener(name, events[name].bind(this));
        });
        this.audio = null;
      }
    },
    getAudioEvents() {
      return {
        play: this.resumed,
        paused: this.paused,
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
      this.counter = '-' + formatDuration(duration - currentTime);
      const pcComplete = calcPercentComplete(duration, currentTime);
      this.$refs.indicator.style.left =
        this.calcCurrentIndicatorPosition(pcComplete) + 'px';
    },
    calcCurrentIndicatorPosition(pcComplete) {
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

  if (playerInfoTag) {
    return {
      ...instance,
      ...JSON.parse(playerInfoTag.textContent),
    };
  }

  return instance;
}
