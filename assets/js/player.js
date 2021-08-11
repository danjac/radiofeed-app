const playerObj = {
  autoplay: false,
  counter: '00:00:00',
  currentTime: 0,
  duration: 0,
  errMsg: null,
  isLoaded: false,
  isPaused: false,
  isPlaying: false,
  playbackRate: 1.0,
  defaultPlaybackRate: 1.0,
  showPlayer: true,
  keys: {
    enable: 'player-enabled',
    playbackRate: 'player-playback-rate',
  },

  init() {
    this.$watch('duration', (value) => {
      this.counter = formatDuration(value - this.currentTime);
    });
    this.$watch('currentTime', (value) => {
      this.counter = formatDuration(this.duration - value);
    });

    this.$watch('playbackRate', (value) => {
      this.$refs.audio.playbackRate = value;
    });

    this.shortcuts = {
      '+': this.incrementPlaybackRate,
      '-': this.decrementPlaybackRate,
      Digit0: this.resetPlaybackRate,
      ArrowLeft: this.skipBack,
      ArrowRight: this.skipForward,
      Delete: this.closePlayer,
      Space: this.togglePlayPause,
    };

    this.$refs.audio.currentTime = this.currentTime;
    this.$refs.audio.load();

    this.lastTimeUpdate = null;

    if ('mediaSession' in navigator) {
      navigator.mediaSession.metadata = getMediaMetadata();
    }
  },

  shortcut(event) {
    if (!this.shortcuts || !this.$refs.audio) {
      return;
    }

    if (
      event.ctrlKey ||
      event.altKey ||
      /^(INPUT|SELECT|TEXTAREA)$/.test(event.target.tagName)
    ) {
      return;
    }

    const handler = this.shortcuts[event.key] || this.shortcuts[event.code];

    if (handler) {
      event.preventDefault();
      event.stopPropagation();
      handler.bind(this)();
    }
  },

  clearSession() {
    sessionStorage.removeItem(this.keys.enable);
  },

  // audio events
  loaded() {
    if (this.isLoaded) {
      return;
    }

    this.errMsg = null;

    this.playbackRate = parseFloat(
      sessionStorage.getItem(this.keys.playbackRate) || this.defaultPlaybackRate
    );

    if (this.autoplay || sessionStorage.getItem(this.keys.enable)) {
      this.$refs.audio.play().catch((err) => {
        this.isPaused = true;
        this.isPlaying = false;
        this.errMsg = getAudioError(err);
      });
    } else {
      this.isPaused = true;
    }

    this.duration = this.$refs.audio.duration;
    this.isLoaded = true;
  },

  error() {
    this.isPlaying = false;
    this.errMsg = getAudioError(this.$refs.audio.error);
  },

  timeUpdate() {
    this.isPlaying = true;
    if (this.$refs.audio) {
      this.currentTime = Math.floor(this.$refs.audio.currentTime);
      this.sendTimeUpdate();
    }
  },

  buffering() {
    this.isPlaying = false;
  },

  resumed() {
    this.isPaused = false;
    this.isPlaying = true;
    this.errMsg = null;
    sessionStorage.setItem(this.keys.enable, true);
  },

  paused() {
    this.isPlaying = false;
    this.isPaused = true;
    this.clearSession();
  },

  incrementPlaybackRate() {
    this.changePlaybackRate(0.1);
  },

  decrementPlaybackRate() {
    this.changePlaybackRate(-0.1);
  },

  resetPlaybackRate() {
    this.setPlaybackRate(this.defaultPlaybackRate);
  },

  changePlaybackRate(increment) {
    const newValue = Math.max(
      0.5,
      Math.min(2.0, parseFloat(this.playbackRate) + increment)
    );
    this.setPlaybackRate(newValue);
  },

  setPlaybackRate(value) {
    this.playbackRate = value;
    sessionStorage.setItem(this.keys.playbackRate, value);
  },

  skip() {
    if (!this.isPaused) {
      this.$refs.audio.currentTime = this.currentTime;
    }
  },
  skipBack() {
    if (!this.isPaused) {
      this.$refs.audio.currentTime -= 10;
    }
  },

  skipForward() {
    if (!this.isPaused) {
      this.$refs.audio.currentTime += 10;
    }
  },

  closePlayer() {
    this.stopPlayer(this.urls.closePlayer);
  },

  ended() {
    this.stopPlayer(this.urls.playNext);
  },

  togglePlayPause() {
    if (this.isPaused) {
      this.$refs.audio.play();
    } else {
      this.$refs.audio.pause();
    }
  },

  stopPlayer(url) {
    this.mediaSrc = null;
    this.shortcuts = null;

    this.$refs.audio.pause();
    this.clearSession();

    window.htmx.ajax('POST', url, {
      target: this.$el,
      source: this.$el,
    });
  },

  sendTimeUpdate() {
    const time = Math.round(this.currentTime);
    if (time % 5 === 0 && this.lastTimeUpdate !== time) {
      fetch(this.urls.timeUpdate, {
        method: 'POST',
        headers: { 'X-CSRFToken': this.csrfToken },
        body: new URLSearchParams({ current_time: time }),
      })
        .then((response) => {
          if (response.status === 204) {
            this.lastTimeUpdate = time;
          }
        })
        .catch((err) => console.log(err));
    }
  },
};

function getAudioError(err) {
  if (err.code === 0) {
    // autoplay not allowed: user has to manually click "Play" button
    return 'Press Play button to continue';
  }

  let msg = 'Press Reload button to continue';

  if (err.code) {
    msg += ' (ERR: ' + err.code + ')';
  }
  return msg;
}

function formatDuration(value) {
  if (isNaN(value) || value < 0) return '00:00:00';
  const duration = Math.floor(value);
  const hours = Math.floor(duration / 3600);
  const minutes = Math.floor((duration % 3600) / 60);
  const seconds = Math.floor(duration % 60);
  return [hours, minutes, seconds].map((t) => t.toString().padStart(2, '0')).join(':');
}

function getMediaMetadata() {
  const dataTag = document.getElementById('player-metadata');
  if (!dataTag) {
    return null;
  }

  const metadata = JSON.parse(dataTag.textContent);

  if (metadata && Object.keys(metadata).length > 0) {
    return new window.MediaMetadata(metadata);
  }
  return null;
}

export default function Player(options) {
  return {
    ...playerObj,
    ...options,
  };
}
