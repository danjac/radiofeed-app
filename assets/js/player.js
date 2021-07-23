const playerObj = {
  counter: '00:00:00',
  currentTime: 0,
  duration: 0,
  isLoaded: false,
  isPaused: false,
  isPlaying: false,
  isError: false,
  playbackRate: 1.0,
  showPlayer: true,
  storageKey: 'player-enabled',
  unlock: false,

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
      Delete: this.close,
      Space: this.togglePlay,
    };

    this.$refs.audio.currentTime = this.currentTime;
    this.$refs.audio.load();

    this.timer = setInterval(this.sendTimeUpdate.bind(this), 5000);

    if ('mediaSession' in navigator) {
      navigator.mediaSession.metadata = getMediaMetadata();
    }
  },

  shortcut(event) {
    if (!this.shortcuts) {
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

  // audio events
  loaded() {
    if (this.isLoaded) {
      return;
    }

    this.isError = false;

    if (!this.unlock && !sessionStorage.getItem(this.storageKey)) {
      this.isPaused = true;
    } else {
      this.$refs.audio.play().catch((err) => {
        console.error(err);
        this.isPaused = true;
        this.isError = true;
      });
    }

    this.duration = this.$refs.audio.duration;
    this.isLoaded = true;
  },

  error() {
    console.log(this.$refs.audio.error);
    this.isError = true;
  },

  timeUpdate() {
    this.currentTime = Math.floor(this.$refs.audio.currentTime);
  },

  resumed() {
    this.isPlaying = true;
    this.isPaused = false;
    this.isError = false;
    sessionStorage.setItem(this.storageKey, true);
  },

  waiting() {
    this.isPlaying = false;
  },

  playing() {
    if (!this.isPaused) {
      this.isPlaying = true;
    }
  },

  paused() {
    this.isPlaying = false;
    this.isPaused = true;
    sessionStorage.removeItem(this.storageKey);
  },

  incrementPlaybackRate() {
    this.changePlaybackRate(0.1);
  },

  decrementPlaybackRate() {
    this.changePlaybackRate(-0.1);
  },

  resetPlaybackRate() {
    this.playbackRate = 1.0;
  },

  changePlaybackRate(increment) {
    const newValue = Math.max(
      0.5,
      Math.min(2.0, parseFloat(this.playbackRate) + increment)
    );
    this.playbackRate = newValue;
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

  close(url) {
    this.mediaSrc = null;
    this.shortcuts = null;

    this.$refs.audio.pause();

    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }

    window.htmx.ajax('POST', url || this.urls.closePlayer, {
      target: this.$el,
      source: this.$el,
    });
  },

  ended() {
    this.close(this.urls.markComplete);
  },

  togglePlay() {
    if (this.isPaused) {
      this.$refs.audio.play();
    } else {
      this.$refs.audio.pause();
    }
  },

  canSendTimeUpdate() {
    return this.isLoaded && !this.isPaused && !!this.currentTime;
  },

  sendTimeUpdate() {
    if (this.canSendTimeUpdate()) {
      fetch(this.urls.timeUpdate, {
        method: 'POST',
        headers: { 'X-CSRFToken': this.csrfToken },
        body: new URLSearchParams({ current_time: this.currentTime }),
      }).catch((err) => console.error(err));
    }
  },
};

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
