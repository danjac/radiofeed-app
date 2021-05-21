import { sendJSON, percent } from './utils';

const storageKey = 'player-enabled';

const defaults = {
  currentTime: 0,
  duration: 0,
  isPlaying: false,
  isPaused: false,
  isLoaded: false,
  isStalled: false,
  playbackRate: 1.0,
  counter: '00:00:00',
};

const formatDuration = (value) => {
  if (isNaN(value) || value < 0) return '00:00:00';
  const duration = Math.floor(value);
  const hours = Math.floor(duration / 3600);
  const minutes = Math.floor((duration % 3600) / 60);
  const seconds = Math.floor(duration % 60);
  return [hours, minutes, seconds].map((t) => t.toString().padStart(2, '0')).join(':');
};

const getMediaMetadata = () => {
  const dataTag = document.getElementById('player-metadata');
  if (!dataTag) {
    return null;
  }

  const metadata = JSON.parse(dataTag.textContent);

  if (metadata && Object.keys(metadata).length > 0) {
    return new window.MediaMetadata(metadata);
  }
  return null;
};

(function () {
  window.Player = (options) => {
    const { mediaSrc, currentTime, runImmediately, csrfToken, urls } = options || {};

    let timer;

    return {
      mediaSrc,
      ...defaults,

      initialize() {
        this.$watch('duration', (value) => {
          this.updateProgressBar(value, this.currentTime);
        });
        this.$watch('currentTime', (value) => {
          this.updateProgressBar(this.duration, value);
        });
        this.openPlayer();
      },

      openPlayer() {
        this.stopPlayer();
        if ('mediaSession' in navigator) {
          navigator.mediaSession.metadata = getMediaMetadata();
        }
        this.$nextTick(() => this.$refs.audio.load());
      },

      // audio events
      loaded() {
        if (!this.$refs.audio || this.isLoaded) {
          return;
        }
        this.$refs.audio.currentTime = currentTime;
        if (runImmediately || sessionStorage.getItem(storageKey)) {
          this.$refs.audio
            .play()
            .then(() => {
              timer = setInterval(this.sendCurrentTimeUpdate.bind(this), 5000);
            })
            .catch((e) => {
              console.log(e);
              this.isPaused = true;
            });
        } else {
          this.isPaused = true;
        }
        this.duration = this.$refs.audio.duration;
        this.isLoaded = true;
      },

      timeUpdate() {
        this.currentTime = this.$refs.audio.currentTime;
      },
      resumed() {
        this.isPlaying = true;
        this.isPaused = false;
        this.isStalled = false;
        sessionStorage.setItem(storageKey, true);
      },

      paused() {
        this.isPlaying = false;
        this.isPaused = true;
        this.isStalled = false;
      },

      shortcuts(event) {
        if (
          /^(INPUT|SELECT|TEXTAREA)$/.test(event.target.tagName) ||
          event.ctrlKey ||
          event.altKey
        ) {
          return;
        }

        switch (event.key) {
          case '+':
            event.preventDefault();
            this.incrementPlaybackRate();
            return;
          case '-':
            event.preventDefault();
            this.decrementPlaybackRate();
            return;
        }

        switch (event.code) {
          case 'ArrowLeft':
            event.preventDefault();
            this.skipBack();
            return;
          case 'ArrowRight':
            event.preventDefault();
            this.skipForward();
            return;
          case 'Space':
            event.preventDefault();
            this.togglePause();
            return;
          case 'Delete':
            event.preventDefault();
            this.close();
        }
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

      skip({ clientX }) {
        const position = this.getProgressBarPosition(clientX);
        if (!isNaN(position) && position > -1) {
          this.skipTo(position);
        }
      },

      skipBack() {
        this.$refs.audio && this.skipTo(this.$refs.audio.currentTime - 10);
      },

      skipForward() {
        this.$refs.audio && this.skipTo(this.$refs.audio.currentTime + 10);
      },

      skipTo(position) {
        if (!isNaN(position) && !this.isPaused && !this.isStalled) {
          this.$refs.audio.currentTime = position;
        }
      },

      play() {
        this.$refs.audio && this.$refs.audio.play();
      },

      pause() {
        this.$refs.audio && this.$refs.audio.pause();
        sessionStorage.removeItem(storageKey);
      },

      error() {
        console.error('Playback Error:', this.$refs.audio.error);
        this.isStalled = true;
      },

      stalled() {
        console.log('Playback Stalled');
        this.isStalled = true;
      },

      close(url) {
        this.stopPlayer();

        window.htmx.ajax('POST', url || urls.closePlayer, {
          target: '#player',
        });
      },

      ended() {
        this.close(urls.playNextEpisode);
      },

      togglePause() {
        if (!this.isStalled) {
          if (this.isPaused) {
            this.play();
          } else {
            this.pause();
          }
        }
      },

      stopPlayer() {
        if (this.$refs.audio) {
          this.$refs.audio.pause();
          this.$refs.audio = null;
        }
        if (timer) {
          clearInterval(timer);
          timer = null;
        }
      },

      sendCurrentTimeUpdate() {
        if (this.isLoaded && !this.isPaused && this.currentTime) {
          sendJSON(urls.timeUpdate, csrfToken, {
            currentTime: this.currentTime,
          });
        }
      },

      updateProgressBar(duration, currentTime) {
        if (this.$refs.indicator && this.$refs.progressBar) {
          this.counter = formatDuration(duration - currentTime);
          const pcComplete = percent(duration, currentTime);
          if (this.$refs.indicator) {
            this.$refs.indicator.style.left =
              this.getIndicatorPosition(pcComplete) + 'px';
          }
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
  };
})();
