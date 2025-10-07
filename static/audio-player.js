document.addEventListener("alpine:init", () => {
    window.Alpine.data(
        "audioPlayer",
        (
            csrfHeader = null,
            csrfToken = null,
            metadataTag = null,
            currentTime = 0,
            startPlayer = false,
            timeUpdateUrl = null,
        ) => ({
            csrfHeader,
            csrfToken,
            currentTime,
            timeUpdateUrl,
            isLoaded: false,
            isPlaying: false,
            isRetrying: false,
            isUpdating: false,
            duration: 0,
            runtime: 0,
            skipSeconds: 10,
            timer: null,
            loadingTime: 30,
            updateInterval: 6,
            counters: {
                current: "00:00:00",
                remaining: "00:00:00",
                preview: "00:00:00",
            },
            // EVENTS
            init() {
                if ("mediaSession" in navigator) {
                    const metadata = parseJsonTag(metadataTag);
                    if (Object.keys(metadata).length > 0) {
                        navigator.mediaSession.metadata = new MediaMetadata(
                            metadata,
                        );
                    }
                }

                this.$watch("runtime", (value) => {
                    this.updateProgressBar();
                    this.counters.current = formatCounter(value);
                    this.counters.remaining = formatCounter(
                        this.duration - value,
                    );
                });

                this.$watch("duration", (value) => {
                    this.counters.remaining = formatCounter(value);
                });

                this.$refs.audio.load();

                // As the load() event does not trigger error callback in case of failure
                // we'll check after a given interval if the audio has started playing
                const interval = setInterval(() => {
                    clearInterval(interval);
                    if (!this.isLoaded && this.$refs.audio) {
                        const { currentSrc } = this.$refs.audio;
                        this.playbackError(
                            `Audio failed to load or start within timeout limit of ${this.loadingTime}s`,
                            `Audio is unavailable. Please try again later or
                            <a href="${currentSrc}" rel="noopener noreferrer" download>
                            download the file</a> to listen to the audio on your device.`,
                        );
                    }
                }, this.loadingTime * 1000);
            },
            destroy() {
                this.clearUpdateTimer();
            },
            async loaded(event) {
                if (this.isLoaded) {
                    return;
                }

                // reset duration based on the audio metadata
                this.duration = event.target.duration || 0;
                this.$refs.audio.currentTime = currentTime; // Set the playback position
                this.runtime = Math.floor(this.$refs.audio.currentTime); // Update runtime

                if (startPlayer) {
                    try {
                        await this.$refs.audio.play();
                    } catch (error) {
                        this.playbackError(
                            error,
                            `Failed to start audio playback.
                            <button @click="window.location.reload()">
                            Reload to continue</button>`,
                        );
                    }
                }

                this.isLoaded = true;
            },
            timeUpdate(event) {
                const { currentTime } = event.target;
                this.runtime = Math.floor(currentTime);
            },
            ended() {
                this.pause();
                this.runtime = 0;
                this.sendTimeUpdate();
            },
            play() {
                this.isPlaying = true;
                this.startUpdateTimer();
            },
            pause() {
                this.isPlaying = false;
                this.clearUpdateTimer();
            },
            error(event) {
                this.playbackError(
                    event.target.error,
                    `An error occurred while playing the audio.
                    <button @click="window.location.reload()">
                    Reload to continue</button>`,
                );
            },
            togglePlayPause() {
                if (this.isPlaying) {
                    this.$refs.audio.pause();
                } else {
                    this.$refs.audio.play();
                }
            },
            skip(event) {
                // move current time to current position on range
                this.skipTo(event.target.value);
            },
            skipBack() {
                this.skipBy(-this.skipSeconds);
            },
            skipForward() {
                this.skipBy(this.skipSeconds);
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
            // PROPERTIES
            get canPlayPause() {
                return this.isLoaded;
            },
            get canSkip() {
                return this.isLoaded && this.isPlaying;
            },
            get status() {
                if (!this.isLoaded) {
                    return "Loading";
                }
                if (!this.isPlaying) {
                    return "Paused";
                }
                return this.counters.preview;
            },
            playbackError(error, content) {
                // Set error state in UI and show CTA
                console.error("Audio playback error", error);
                this.$dispatch("cta", {
                    dismissable: true,
                    content,
                });
            },
            skipBy(seconds) {
                // move current time +/- seconds
                this.skipTo(this.$refs.audio.currentTime + seconds);
            },
            skipTo(position) {
                if (this.isPlaying) {
                    // ensure seconds within bounds of audio duration
                    newTime = Math.max(
                        0,
                        Math.min(this.$refs.audio.duration, position),
                    );
                    this.$refs.audio.currentTime = newTime;
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
            startUpdateTimer() {
                if (!this.updateTimer) {
                    this.updateTimer = setInterval(() => {
                        if (this.isPlaying && !this.isUpdating) {
                            this.sendTimeUpdate();
                        }
                    }, this.updateInterval * 1000);
                }
            },
            clearUpdateTimer() {
                if (this.updateTimer) {
                    clearInterval(this.updateTimer);
                    this.isUpdating = false;
                    this.updateTimer = null;
                }
            },
            async sendTimeUpdate() {
                if (!this.isUpdating) {
                    this.isUpdating = true;
                    try {
                        await fetch(this.timeUpdateUrl, {
                            method: "POST",
                            headers: {
                                [this.csrfHeader]: this.csrfToken,
                            },
                            body: new URLSearchParams({
                                current_time: this.runtime,
                                duration: parseInt(this.duration),
                            }),
                        });
                    } catch (error) {
                        console.error("Failed to send time update", error);
                    } finally {
                        this.isUpdating = false;
                    }
                }
            },
            setPreviewCounter(position) {
                if (this.isPlaying) {
                    const { clientWidth } = this.$refs.range;
                    const percent = position / clientWidth;
                    const value = Math.floor(percent * this.duration);
                    this.counters.preview = formatCounter(value);
                }
            },
        }),
    );
});

const parseJsonTag = (tagname) => {
    const tagElement = document.getElementById(tagname);
    return JSON.parse(tagElement?.textContent || "{}");
};

const formatCounter = (value) => {
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
};
