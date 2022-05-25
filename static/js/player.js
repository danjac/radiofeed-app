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
                this.$watch("currentTime", (value) => {
                    this.counters.current = this.formatCounter(value);
                });

                this.$watch("duration", (value) => {
                    this.counters.total = this.formatCounter(value);
                });

                this.$watch("playbackRate", (value) => {
                    this.$refs.audio.playbackRate = value;
                });

                this.counters.current = this.formatCounter(this.currentTime);
                this.counters.total = this.formatCounter(this.duration);

                console.log("[audio] init", this);

                this.$refs.audio.currentTime = this.currentTime;
                this.$refs.audio.load();

                if ("mediaSession" in navigator) {
                    navigator.mediaSession.metadata = this.getMediaMetadata();
                }
            },
            destroy() {
                console.log("[audio] destroy", this);
                this.clearTimer();
            },
            loaded(event) {
                this.logEvent(event);

                if (this.isLoaded) {
                    return;
                }

                const { playbackRate, autoplay } = this.loadState();

                this.playbackError = null;
                this.playbackRate = playbackRate || 1.0;
                this.autoplay = autoplay || this.autoplay;

                if (this.autoplay) {
                    this.$refs.audio.play().catch(this.handleError);
                } else {
                    this.pause();
                }

                this.duration = this.$refs.audio.duration;
                this.isLoaded = true;
            },
            timeUpdate(event) {
                this.logEvent(event);
                this.isPlaying = true;
                this.playbackError = null;
                this.currentTime = Math.floor(this.$refs.audio.currentTime);
            },
            play(event) {
                this.logEvent(event);
                this.isPaused = false;
                this.isPlaying = true;
                this.playbackError = null;
                this.saveState();
                this.startTimer();
            },
            pause(event) {
                this.logEvent(event);
                this.isPlaying = false;
                this.isPaused = true;
                this.saveState();
                this.clearTimer();
            },
            ended(event) {
                this.logEvent(event);
                this.pause();
                this.currentTime = 0;
                this.sendTimeUpdate();
            },
            buffering(event) {
                this.logEvent(event);
                this.isPlaying = false;
            },
            error(event) {
                this.logEvent(event);
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
                    this.$refs.audio.currentTime = this.currentTime;
                }
            },
            skipBack() {
                if (this.isPlaying) {
                    this.$refs.audio.currentTime -= 10;
                }
            },
            skipForward() {
                if (this.isPlaying) {
                    this.$refs.audio.currentTime += 10;
                }
            },
            shortcuts(event) {
                if (event.target.tagName.match(/INPUT|TEXTAREA/)) {
                    return;
                }

                if (!event.ctrlKey && !event.altKey) {
                    switch (event.code) {
                        case "Space":
                            event.preventDefault();
                            event.stopPropagation();
                            this.togglePlayPause();
                            return;
                        case "ArrowRight":
                            event.preventDefault();
                            event.stopPropagation();
                            this.skipForward();
                            return;
                        case "ArrowLeft":
                            event.preventDefault();
                            event.stopPropagation();
                            this.skipBack();
                            return;
                    }
                }

                // playback rate
                if (event.altKey) {
                    switch (event.key) {
                        case "+":
                            event.preventDefault();
                            event.stopPropagation();
                            this.incrementPlaybackRate();
                            return;
                        case "-":
                            event.preventDefault();
                            event.stopPropagation();
                            this.decrementPlaybackRate();
                            return;
                        case "0":
                            event.preventDefault();
                            event.stopPropagation();
                            this.resetPlaybackRate();
                            return;
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
                        current_time: this.currentTime,
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
            logEvent(event) {
                if (event) {
                    console.log("[audio]", event.type);
                }
            },
            handleError(error) {
                this.pause();
                this.playbackError = error;
                console.error(this.playbackError);
            },
        })
    );
});
