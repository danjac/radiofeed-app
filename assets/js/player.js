const playerObj = {
  autoplay: false,
  currentTime: 0,
  duration: 0,
  isError: false,
  isLoaded: false,
  isPaused: false,
  isPlaying: false,
  playbackRate: 1.0,
  defaultPlaybackRate: 1.0,
  showPlayer: true,
  counters: {
    current: '00:00:00',
    duration: '00:00:00',
  },
  keys: {
    enable: 'player-enabled',
    playbackRate: 'player-playback-rate',
  },

  init() {
    this.$watch('currentTime', (value) => {
      this.counters.current = formatDuration(value);
    });

    this.$watch('duration', (value) => {
      this.counters.duration = formatDuration(value);
    });

    this.$watch('playbackRate', (value) => {
      this.$refs.audio.playbackRate = value;
    });

    this.counters.current = formatDuration(this.currentTime);
    this.counters.duration = formatDuration(this.duration);

    this.$refs.audio.currentTime = this.currentTime;
    this.$refs.audio.load();

    this.lastTimeUpdate = null;

    if ('mediaSession' in navigator) {
      navigator.mediaSession.metadata = getMediaMetadata();
    }
  },

  shortcuts(event) {
    if (event.ctrlKey || event.altKey || event.target.tagName.match(/INPUT|TEXTAREA/)) {
      return;
    }

    switch (event.code) {
      case 'Space':
        event.preventDefault();
        event.stopPropagation();
        this.togglePlayPause();
        return;
      case 'ArrowRight':
        event.preventDefault();
        event.stopPropagation();
        this.skipForward();
        return;
      case 'ArrowLeft':
        event.preventDefault();
        event.stopPropagation();
        this.skipBack();
        return;
    }

    switch (event.key) {
      case '+':
        event.preventDefault();
        event.stopPropagation();
        this.incrementPlaybackRate();
        return;
      case '-':
        event.preventDefault();
        event.stopPropagation();
        this.decrementPlaybackRate();
        return;
      case '0':
        event.preventDefault();
        event.stopPropagation();
        this.resetPlaybackRate();
        return;
    }
  },

  // audio events
  loaded() {
    if (this.isLoaded) {
      return;
    }

    this.isError = false;

    this.playbackRate = parseFloat(
      sessionStorage.getItem(this.keys.playbackRate) || this.defaultPlaybackRate
    );

    if (this.autoplay || sessionStorage.getItem(this.keys.enable)) {
      this.$refs.audio.play().catch((err) => {
        this.isPaused = true;
        this.isPlaying = false;
        this.isError = true;
      });
    } else {
      this.isPaused = true;
      this.isPlaying = false;
    }

    this.duration = this.$refs.audio.duration;
    this.isLoaded = true;
  },

  error() {
    this.isPlaying = false;
    this.isError = true;
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
    this.isError = false;
    sessionStorage.setItem(this.keys.enable, true);
  },

  paused() {
    this.isPlaying = false;
    this.isPaused = true;
    this.disable();
  },

  disable() {
    sessionStorage.removeItem(this.keys.enable);
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

  ended() {
    this.$refs.playNext.click();
  },

  togglePlayPause() {
    if (this.isPaused) {
      this.$refs.audio.play();
    } else {
      this.$refs.audio.pause();
    }
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
