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
    isPlaying: false,
    isPaused: false,
    isWaiting: false,
  };

  const playerInfoTag = document.getElementById('player-info');

  const instance = {
    ...defaults,
    initialize() {},
    openPlayer(event) {
      const { episode, podcast, currentTime } = event.detail;
      this.episode = episode;
      this.podcast = podcast;
      this.currentTime = currentTime;
      this.$nextTick(() => {
        this.$refs.audio.play();
        // hook up any htmx events
        htmx.process(this.$el);
        // set up watchers
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
      this.duration = this.$refs.audio.duration;
    },
    timeUpdate() {
      if (this.$refs.audio) {
        this.currentTime = this.$refs.audio.currentTime;
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
      //this.isPlaying = true;
      //this.isPaused = false;
      //this.isWaiting = false;
    },
    paused() {
      console.log('paused');
      //this.isPlaying = false;
      //this.isPaused = true;
      //this.isWaiting = false;
    },
    waiting() {
      console.log('waiting');
      //this.isWaiting = true;
    },
    active() {
      console.log('active');
      //this.isWaiting = false;
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
