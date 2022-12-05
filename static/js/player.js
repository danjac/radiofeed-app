import Alpine from "alpinejs";

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

                this.$refs.audio.load();
            },
            destroy() {
                this.clearTimer();
            },
            loaded(event) {
                if (this.isLoaded) {
                    return;
                }

                this.duration = event.target.duration || 0;

                event.target.currentTime = currentTime;
                this.runtime = Math.floor(event.target.currentTime);

                if (startPlayer) {
                    event.target.play().catch(this.handleError.bind(this));
                }

                this.isLoaded = true;
            },
            timeUpdate(event) {
                this.runtime = Math.floor(event.target.currentTime);
            },
            ended() {
                this.pause();
                this.runtime = 0;
                this.sendTimeUpdate();
            },
            play() {
                this.isPlaying = true;
                this.startTimer();
            },
            pause() {
                this.isPlaying = false;
                this.clearTimer();
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
                console.error(error);
            },
        }),
    );
});
