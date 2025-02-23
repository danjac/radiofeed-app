document.addEventListener("alpine:init", () => {
    window.Alpine.data(
        "audioPlayer",
        (
            csrfHeader = null,
            csrfToken = null,
            currentTime = 0,
            metadataTag = null,
            startPlayer = false,
            timeUpdateUrl = null,
        ) => ({
            csrfHeader,
            csrfToken,
            currentTime,
            timeUpdateUrl,
            duration: 0,
            isError: false,
            isLoaded: false,
            isPlaying: false,
            isRetrying: false,
            isUpdating: false,
            runtime: 0,
            skipSeconds: 10,
            timer: null,
            updateInterval: 6,
            maxRetries: 3,

            counters: {
                current: "00:00:00",
                remaining: "00:00:00",
                preview: "00:00:00",
            },
            init() {
                if (metadataTag && "mediaSession" in navigator) {
                    navigator.mediaSession.metadata =
                        this.getMediaMetadata(metadataTag);
                }

                this.$watch("runtime", (value) => {
                    this.updateProgressBar();
                    this.counters.current = this.formatCounter(value);
                    this.counters.remaining = this.formatCounter(
                        this.duration - value,
                    );
                });

                this.$watch("duration", (value) => {
                    this.counters.remaining = this.formatCounter(value);
                });

                this.$refs.audio.load();
            },
            destroy() {
                this.clearTimer();
            },
            async loaded(event) {
                if (this.isLoaded) {
                    return;
                }

                this.duration = event.target.duration || 0;
                this.$refs.audio.currentTime = currentTime; // Set the playback position
                this.runtime = Math.floor(this.$refs.audio.currentTime); // Update runtime

                if (startPlayer) {
                    await this.$refs.audio.play();
                }

                this.isLoaded = true;
                this.isError = false;
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
                console.error("Audio playback error", event.target.error);
                this.isError = true;
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
                this.skipTo(-this.skipSeconds);
            },
            skipForward() {
                this.skipTo(this.skipSeconds);
            },
            shortcuts(event) {
                if (
                    event.ctrlKey ||
                    event.altKey ||
                    event.target.tagName.match(/INPUT|TEXTAREA/)
                ) {
                    return;
                }

                const handleEvent = (fn) => {
                    event.preventDefault();
                    event.stopPropagation();
                    fn.bind(this)();
                };

                switch (event.code) {
                    case "Space":
                        return handleEvent(this.togglePlayPause);
                    case "ArrowRight":
                        return handleEvent(this.skipForward);
                    case "ArrowLeft":
                        return handleEvent(this.skipBack);
                }
            },
            updateProgressBar() {
                const percent =
                    this.runtime && this.duration
                    ? (this.runtime / this.duration) * 100
                    : 0;
                this.$refs.range.style.setProperty(
                    "--webkitProgressPercent",
                    `${percent}%`,
                );
            },
            startTimer() {
                if (!this.timer) {
                    this.timer = setInterval(() => {
                        if (this.isPlaying & !this.isUpdating) {
                            this.sendTimeUpdate();
                        }
                    }, this.updateInterval * 1000);
                }
            },
            clearTimer() {
                if (this.timer) {
                    clearInterval(this.timer);
                    this.isUpdating = false;
                    this.timer = null;
                }
            },
            async sendTimeUpdate() {
                this.isUpdating = true;
                await fetch(this.timeUpdateUrl, {
                    method: "POST",
                    headers: {
                        [this.csrfHeader]: this.csrfToken,
                    },
                    body: new URLSearchParams({
                        current_time: this.runtime,
                    }),
                });
                this.isUpdating = false;
            },
            setPreviewCounter(position) {
                if (this.isPlaying) {
                    const { clientWidth } = this.$refs.range;
                    const percent = position / clientWidth;
                    const value = Math.floor(percent * this.duration);
                    this.counters.preview = this.formatCounter(value);
                }
            },
            formatCounter(value) {
                if (isNaN(value) || value < 0) {
                    return "00:00:00";
                }

                const duration = Math.floor(value);
                return [
                    Math.floor(duration / 3600),
                    Math.floor((duration % 3600) / 60),
                    Math.floor(duration % 60),
                ]
                    .map((t) => t.toString().padStart(2, "0"))
                    .join(":");
            },
            getMediaMetadata(tagName) {
                const dataTag = document.getElementById(tagName);
                const metadata = dataTag
                    ? JSON.parse(dataTag.textContent || "{}")
                    : {};

                if (metadata && Object.keys(metadata).length > 0) {
                    return new MediaMetadata(metadata);
                }
                return null;
            },
            get canPlayPause() {
                return this.isLoaded && !this.isError;
            },
            get canSkip() {
                return this.isLoaded && this.isPlaying && !this.isError;
            },
            get status() {
                if (this.isError) {
                    return "Error";
                }
                if (!this.isLoaded) {
                    return "Loading";
                }
                if (!this.isPlaying) {
                    return "Paused";
                }
                return this.counters.preview;
            },
        }),
    );
});
