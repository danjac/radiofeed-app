import Alpine from "alpinejs";

const SESSION_KEY = "audio-player";

document.addEventListener("alpine:init", () => {
    Alpine.data(
        "player",
        (
            startPlayer = false,
            currentTime = 0,
            csrfToken = null,
            timeUpdateUrl = null,
        ) => ({
            currentTime,
            csrfToken,
            timeUpdateUrl,
            runtime: 0,
            duration: 0,
            isError: false,
            isLoaded: false,
            isPlaying: false,
            timer: null,
            counters: {
                current: "00:00:00",
                total: "00:00:00",
            },
            init() {
                if ("mediaSession" in navigator) {
                    navigator.mediaSession.metadata = this.getMediaMetadata();
                }

                this.$watch("runtime", value => {
                    const percent =
                        value && this.duration
                            ? (value / this.duration) * 100
                            : 0;
                    this.$refs.range.style.setProperty(
                        "--webkitProgressPercent",
                        `${percent}%`,
                    );
                    this.counters.current = this.formatCounter(value);
                });

                this.$watch("duration", value => {
                    this.counters.total = this.formatCounter(value);
                });

                this.$watch("isPlaying", value => {
                    if (value) {
                        this.isPlaying = true;
                        this.isError = false;
                        this.setPlayerState(true);
                        this.startTimer();
                    } else {
                        this.isPlaying = false;
                        this.setPlayerState(false);
                        this.clearTimer();
                    }
                });

                this.$refs.audio.load();
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

                startPlayer = startPlayer || this.getPlayerState();

                if (startPlayer) {
                    event.target.play().catch(this.handleError.bind(this));
                } else {
                    this.pause();
                }

                this.isLoaded = true;
            },
            timeUpdate(event) {
                this.runtime = Math.floor(event.target.currentTime);
                this.isPlaying = true;
            },
            play() {
                this.isPlaying = true;
            },
            pause() {
                this.isPlaying = false;
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
                if (this.isPlaying) {
                    this.$refs.audio.pause();
                } else {
                    this.$refs.audio.play();
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
            getPlayerState() {
                return !!sessionStorage.getItem(SESSION_KEY);
            },
            setPlayerState(active) {
                if (active) {
                    sessionStorage.setItem(SESSION_KEY, "true");
                } else {
                    sessionStorage.removeItem(SESSION_KEY);
                }
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
