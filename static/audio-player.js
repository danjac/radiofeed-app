document.addEventListener("alpine:init", () => {
    window.Alpine.data(
        "audioPlayer",
        (
            csrfHeader = null,
            csrfToken = null,
            currentTime = 0,
            metadataTag = null,
            startPlayer = false,
            sizeInBytes = 0,
            duration = 0,
            timeUpdateUrl = null,
        ) => ({
            csrfHeader,
            csrfToken,
            currentTime,
            duration,
            timeUpdateUrl,
            isLoaded: false,
            isPlaying: false,
            isRetrying: false,
            isUpdating: false,
            runtime: 0,
            skipSeconds: 10,
            timer: null,
            updateInterval: 6,
            minLoadingTime: 6,
            maxLoadingTime: 30,
            counters: {
                current: "00:00:00",
                remaining: "00:00:00",
                preview: "00:00:00",
            },
            // EVENTS
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

                // As the load() event does not trigger error callback in case of failure
                // we'll check after a given interval if the audio has started playing
                const interval = setInterval(
                    () => {
                        // check the isLoaded flag
                        if (this.isLoaded) {
                            clearInterval(interval); // Success, clear the interval
                        } else {
                            // Timeout occurred, set error state and show CTA
                            this.handleError(
                                new Error(
                                    "Audio failed to load or start within timeout limit",
                                ),
                                `Audio is unavailable. Please try again later or click the
                            Download link to listen to the audio directly.`,
                            );
                            clearInterval(interval); // Failure, clear the interval
                        }
                    },
                    this.getLoadingInterval(sizeInBytes, duration),
                );
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
                        this.handleError(
                            error,
                            "Failed to start audio playback. Reload to contine.",
                        );
                    }
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
                this.startUpdateTimer();
            },
            pause() {
                this.isPlaying = false;
                this.clearUpdateTimer();
            },
            error(event) {
                this.handleError(
                    event.target.error,
                    `An error occurred while playing the audio.
                    Reload to continue.`,
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
            handleError(error, content) {
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
                this.isUpdating = true;
                try {
                    await fetch(this.timeUpdateUrl, {
                        method: "POST",
                        headers: {
                            [this.csrfHeader]: this.csrfToken,
                        },
                        body: new URLSearchParams({
                            current_time: this.runtime,
                        }),
                    });
                } catch (error) {
                    console.error("Failed to send time update", error);
                } finally {
                    this.isUpdating = false;
                }
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
            getLoadingInterval(sizeInBytes, duration) {
                // calculate the loading timeout based on the file size
                //

                // seconds based on file size: 1s/1MB
                // if size is 0, estimate based on duration: 1s/min
                let totalSeconds;

                if (sizeInBytes > 0) {
                    totalSeconds = sizeInBytes / (1024 * 1024);
                } else if (duration > 0) {
                    totalSeconds = duration / 60;
                } else {
                    totalSeconds = this.maxLoadingTime;
                }

                return (
                    Math.min(
                        this.maxLoadingTime,
                        Math.max(this.minLoadingTime, totalSeconds),
                    ) * 1000
                );
            },
        }),
    );
});
