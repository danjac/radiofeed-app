import Alpine from "alpinejs";

document.addEventListener("alpine:init", () => {
    Alpine.data(
        "player",
        (
            autoplay = false,
            mediaSrc = null,
            currentTime = 0,
            csrfToken = null,
            timeUpdateUrl = null
        ) => ({
            autoplay,
            mediaSrc,
            currentTime,
            csrfToken,
            timeUpdateUrl,
            runtime: 0,
            duration: 0,
            isLoaded: false,
            isPaused: false,
            isPlaying: false,
            timer: null,
            playbackError: null,
            playbackRate: 1.0,
            counters: {
                current: "00:00:00",
                total: "00:00:00",
            },
            init() {
                this.$watch("runtime", (value) => {
                    this.counters.current = this.formatCounter(value);
                });

                this.$watch("duration", (value) => {
                    this.counters.total = this.formatCounter(value);
                });

                this.$watch("playbackRate", (value) => {
                    this.$refs.audio.playbackRate = value;
                });

                this.$refs.audio.load();

                if ("mediaSession" in navigator) {
                    navigator.mediaSession.metadata = this.getMediaMetadata();
                }
            },
            destroy() {
                this.clearTimer();
            },
            loaded(event) {
                if (this.isLoaded) {
                    return;
                }

                const { playbackRate, autoplay } = this.loadState();

                this.playbackError = null;
                this.playbackRate = playbackRate || 1.0;
                this.autoplay = autoplay || this.autoplay;

                event.target.currentTime = this.currentTime;

                if (this.autoplay) {
                    event.target.play().catch(this.handleError.bind(this));
                } else {
                    this.pause();
                }

                this.duration = event.target.duration;
                this.isLoaded = true;
            },
            timeUpdate(event) {
                this.isPlaying = true;
                this.playbackError = null;
                this.runtime = Math.floor(event.target.currentTime);
            },
            play() {
                this.isPaused = false;
                this.isPlaying = true;
                this.playbackError = null;
                this.saveState();
                this.startTimer();
            },
            pause() {
                this.isPlaying = false;
                this.isPaused = true;
                this.saveState();
                this.clearTimer();
            },
            ended() {
                this.pause();
                this.runtime = 0;
                this.sendTimeUpdate();
            },
            buffering() {
                this.isPlaying = false;
            },
            error(event) {
                this.handleError(event.target.error);
            },
            togglePlayPause() {
                if (this.isPaused) {
                    this.$refs.audio.play();
                } else {
                    this.$refs.audio.pause();
                }
            },
            skip() {
                if (this.isPlaying) {
                    this.$refs.audio.currentTime = this.runtime;
                }
            },
            skipTo(seconds) {
                if (this.isPlaying) {
                    this.$refs.audio.currentTime += seconds;
                }
            },
            skipBack() {
                this.skipTo(-10);
            },
            skipForward() {
                this.skipTo(10);
            },
            shortcuts(event) {
                if (event.target.tagName.match(/INPUT|TEXTAREA/)) {
                    return;
                }

                const handleEvent = (fn) => {
                    event.preventDefault();
                    event.stopPropagation();
                    fn.bind(this)();
                };

                if (!event.ctrlKey && !event.altKey) {
                    switch (event.code) {
                        case "Space":
                            return handleEvent(this.togglePlayPause);
                        case "ArrowRight":
                            return handleEvent(this.skipForward);
                        case "ArrowLeft":
                            return handleEvent(this.skipBack);
                    }
                }

                // playback rate
                if (event.altKey) {
                    switch (event.key) {
                        case "+":
                            return handleEvent(this.incrementPlaybackRate);
                        case "-":
                            return handleEvent(this.decrementPlaybackRate);
                        case "0":
                            return handleEvent(this.resetPlaybackRate);
                    }
                }
            },
            startTimer() {
                if (!this.timer) {
                    this.timer = setInterval(() => {
                        if (this.isPlaying) {
                            this.sendTimeUpdate();
                        }
                    }, 5000);
                }
            },
            clearTimer() {
                if (this.timer) {
                    clearInterval(this.timer);
                    this.timer = null;
                }
            },
            sendTimeUpdate() {
                fetch(this.timeUpdateUrl, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": this.csrfToken,
                    },
                    body: new URLSearchParams({
                        current_time: this.runtime,
                    }),
                });
            },
            incrementPlaybackRate() {
                this.changePlaybackRate(0.1);
            },
            decrementPlaybackRate() {
                this.changePlaybackRate(-0.1);
            },
            resetPlaybackRate() {
                this.setPlaybackRate(1.0);
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
                this.saveState();
            },
            loadState() {
                const state = sessionStorage.getItem("player");
                return state
                ? JSON.parse(state)
                : {
                    playbackRate: 1.0,
                    autoplay: false,
                };
            },
            saveState() {
                sessionStorage.setItem(
                    "player",
                    JSON.stringify({
                        playbackRate: this.playbackRate,
                        autoplay: this.isPlaying,
                    })
                );
            },
            formatCounter(value) {
                if (isNaN(value) || value < 0) return "00:00:00";
                const duration = Math.floor(value);
                const hours = Math.floor(duration / 3600);
                const minutes = Math.floor((duration % 3600) / 60);
                const seconds = Math.floor(duration % 60);
                return [hours, minutes, seconds]
                    .map((t) => t.toString().padStart(2, "0"))
                    .join(":");
            },
            getMediaMetadata() {
                const dataTag = document.getElementById("player-metadata");
                if (!dataTag) {
                    return null;
                }

                const metadata = JSON.parse(dataTag.textContent);

                if (metadata && Object.keys(metadata).length > 0) {
                    return new window.MediaMetadata(metadata);
                }
                return null;
            },
            handleError(error) {
                this.pause();
                this.playbackError = error;
                console.error(this.playbackError);
            },
        })
    );
});
