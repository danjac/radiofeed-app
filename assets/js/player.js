const storageKey = 'player-enabled';

const defaults = {
  currentTime: 0,
  duration: 0,
  isPlaying: false,
  isPaused: false,
  isLoaded: false,
  showPlayer: true,
  playbackRate: 1.0,
  counter: '00:00:00',
};

export default function Player(options) {
  const { mediaSrc, currentTime, runImmediately, urls } = options || {};

  let timer;

  const isLocked = !runImmediately && !sessionStorage.getItem(storageKey);

  return {
    mediaSrc,
    ...defaults,

    init() {
      this.$watch('duration', (value) => {
        this.counter = formatDuration(value - this.currentTime);
      });
      this.$watch('currentTime', (value) => {
        this.counter = formatDuration(this.duration - value);
      });

      this.$refs.audio.load();
    },

    // audio events
    loaded() {
      if (this.isLoaded) {
        return;
      }
      this.$refs.audio.currentTime = currentTime;

      if (isLocked) {
        this.isPaused = true;
      } else {
        this.$refs.audio
          .play()
          .then(() => this.startTimer())
          .catch((e) => {
            console.log(e);
            this.isPaused = true;
          });
      }

      this.duration = this.$refs.audio.duration;
      this.isLoaded = true;

      if ('mediaSession' in navigator) {
        navigator.mediaSession.metadata = getMediaMetadata();
      }
    },

    timeUpdate() {
      this.currentTime = Math.floor(this.$refs.audio.currentTime);
    },

    resumed() {
      this.isPlaying = true;
      this.isPaused = false;
      sessionStorage.setItem(storageKey, true);
    },

    paused() {
      this.isPlaying = false;
      this.isPaused = true;
      sessionStorage.removeItem(storageKey);
    },

    incrementPlaybackRate() {
      this.changePlaybackRate(0.1);
    },

    decrementPlaybackRate() {
      this.changePlaybackRate(-0.1);
    },

    changePlaybackRate(increment) {
      const newValue = Math.max(
        0.5,
        Math.min(2.0, parseFloat(this.playbackRate) + increment)
      );
      this.$refs.audio.playbackRate = this.playbackRate = newValue;
    },

    skip() {
      this.$refs.audio.currentTime = this.currentTime;
    },

    skipBack() {
      this.$refs.audio.currentTime -= 10;
    },

    skipForward() {
      this.$refs.audio.currentTime += 10;
    },

    close(url) {
      this.mediaSrc = null;

      if ('mediaSession' in navigator) {
        navigator.mediaSession.metadata = null;
      }

      this.$refs.audio.pause();

      if (timer) {
        clearInterval(timer);
        timer = null;
      }

      window.htmx.ajax('POST', url || urls.closePlayer, {
        target: this.$el,
        source: this.$el,
      });
    },

    ended() {
      this.close(urls.playNextEpisode);
    },

    togglePlay() {
      if (this.isPaused) {
        this.$refs.audio.play();
      } else {
        this.$refs.audio.pause();
      }
    },

    startTimer() {
      timer = setInterval(this.sendTimeUpdate.bind(this), 5000);
    },

    canSendTimeUpdate() {
      return this.isLoaded && !this.isPaused && !!this.currentTime;
    },

    sendTimeUpdate() {
      this.canSendTimeUpdate() &&
        window.htmx.ajax('POST', urls.timeUpdate, {
          source: this.$el,
          values: { current_time: this.currentTime },
        });
    },
  };
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
