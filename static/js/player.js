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

                this.$refs.audio.currentTime = this.currentTime;
                this.$refs.audio.load();

                if ("mediaSession" in navigator) {
                    navigator.mediaSession.metadata = this.getMediaMetadata();
                }
            },
            destroy() {
                this.clearTimer();
            },
            startTimer() {
                this.timer = setInterval(() => {
                    if (this.isPlaying) {
                        this.sendTimeUpdate();
                    }
                }, 5000);
            },
            clearTimer() {
                if (this.timer) {
                    clearInterval(this.timer);
                }
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
            loaded() {
                if (this.isLoaded) {
                    return;
                }

                const { playbackRate, autoplay } = this.loadSettings();

                this.playbackRate = playbackRate || 1.0;
                this.autoplay = autoplay || this.autoplay;

                if (this.autoplay) {
                    this.$refs.audio.play().catch(() => {
                        this.isPaused = true;
                        this.isPlaying = false;
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
            },
            timeUpdate() {
                this.isPlaying = true;
                this.currentTime = Math.floor(this.$refs.audio.currentTime);
            },
            buffering() {
                this.isPlaying = false;
            },
            resumed() {
                this.isPaused = false;
                this.isPlaying = true;
                this.saveSettings();
                this.startTimer();
            },
            paused() {
                this.isPlaying = false;
                this.isPaused = true;
                this.saveSettings();
                this.clearTimer();
            },
            ended() {
                this.currentTime = 0;
                this.isPlaying = false;
                this.isPaused = true;
                this.clearTimer();
                this.sendTimeUpdate();
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
                this.saveSettings();
            },
            loadSettings() {
                const settings = sessionStorage.getItem("player");
                return settings
                ? JSON.parse(settings)
                : {
                    playbackRate: 1.0,
                    autoplay: false,
                };
            },
            saveSettings() {
                sessionStorage.setItem(
                    "player",
                    JSON.stringify({
                        playbackRate: this.playbackRate,
                        autoplay: this.isPlaying,
                    })
                );
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
            togglePlayPause() {
                if (this.isPaused) {
                    this.$refs.audio.play();
                } else {
                    this.$refs.audio.pause();
                }
            },
        })
    );
});
