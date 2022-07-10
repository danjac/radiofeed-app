import Alpine from "alpinejs";

ok: document.addEventListener("alpine:init", () => {
    Alpine.data(
        "player",
        (
            autoplay = false,
            currentTime = 0,
            csrfToken = null,
            timeUpdateUrl = null,
        ) => ({
            autoplay,
            currentTime,
            csrfToken,
            timeUpdateUrl,
            runtime: 0,
            duration: 0,
            rate: 1.0,
            isError: false,
            isLoaded: false,
            isPaused: false,
            isPlaying: false,
            timer: null,
            counters: {
                current: "00:00:00",
                total: "00:00:00",
            },
            init() {
                this.$watch("runtime", value => {
                    this.counters.current = this.formatCounter(value);
                });

                this.$watch("duration", value => {
                    this.counters.total = this.formatCounter(value);
                });

                this.$watch("rate", value => {
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

                event.target.currentTime = this.currentTime;

                this.isError = false;
                this.duration = event.target.duration || 0;
                this.loadState();

                if (this.autoplay) {
                    event.target.play().catch(this.handleError.bind(this));
                } else {
                    this.pause();
                }

                this.isLoaded = true;
            },
            timeUpdate(event) {
                this.runtime = Math.floor(event.target.currentTime);

                this.isPlaying = true;
                this.isError = false;
            },
            play() {
                this.isPaused = false;
                this.isPlaying = true;
                this.isError = false;
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

                const handleEvent = fn => {
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
                            return handleEvent(this.incrementRate);
                        case "-":
                            return handleEvent(this.decrementRate);
                        case "0":
                            return handleEvent(this.resetRate);
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
            incrementRate() {
                this.changeRate(0.1);
            },
            decrementRate() {
                this.changeRate(-0.1);
            },
            resetRate() {
                this.setRate(1.0);
            },
            changeRate(increment) {
                const newValue = Math.max(
                    0.5,
                    Math.min(2.0, parseFloat(this.rate) + increment),
                );
                this.setRate(newValue);
            },
            setRate(value) {
                this.rate = value;
                this.saveState();
            },
            loadState() {
                const state = sessionStorage.getItem("player");
                const { autoplay, rate } = state
                    ? JSON.parse(state)
                    : {
                          autoplay: false,
                          rate: 1.0,
                      };
                this.autoplay = autoplay || this.autoplay;
                this.rate = rate || 1.0;
            },
            saveState() {
                sessionStorage.setItem(
                    "player",
                    JSON.stringify({
                        autoplay: this.isPlaying,
                        rate: this.rate,
                    }),
                );
            },
            formatCounter(value) {
                if (isNaN(value) || value < 0) return "00:00:00";
                const duration = Math.floor(value);
                return [
                    Math.floor(duration / 3600),
                    Math.floor((duration % 3600) / 60),
                    Math.floor(duration % 60),
                ]
                    .map(t => t.toString().padStart(2, "0"))
                    .join(":");
            },
            getMediaMetadata() {
                const dataTag = document.getElementById("player-metadata");
                const metadata = JSON.parse(dataTag?.textContent || "{}");

                if (metadata && Object.keys(metadata).length > 0) {
                    return new MediaMetadata(metadata);
                }
                return null;
            },
            handleError(error) {
                this.pause();
                this.isError = true;
                console.error(error);
            },
        }),
    );
});
