import Alpine from "alpinejs";

interface PlayerState {
    autoplay: boolean;
    rate: number;
}

document.addEventListener("alpine:init", () => {
    Alpine.data(
        "player",
        (
            autoplay = false,
            mediaSrc = null,
            currentTime = 0,
            csrfToken = null,
            timeUpdateUrl = null,
        ) => ({
            autoplay,
            mediaSrc,
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
            init(): void {
                this.$watch("runtime", (value: string) => {
                    this.counters.current = this.formatCounter(value);
                });

                this.$watch("duration", (value: string) => {
                    this.counters.total = this.formatCounter(value);
                });

                this.$watch("rate", (value: string) => {
                    this.$refs.audio.rate = value;
                });

                this.$refs.audio.load();

                if ("mediaSession" in navigator) {
                    navigator.mediaSession.metadata = this.getMediaMetadata();
                }
            },
            destroy(): void {
                this.clearTimer();
            },
            loaded(event: Event): void {
                if (this.isLoaded) {
                    return;
                }

                const target = event.target as HTMLMediaElement;

                const { rate, autoplay } = this.loadState();

                this.isError = false;
                this.rate = rate || 1.0;
                this.autoplay = autoplay || this.autoplay;

                target.currentTime = this.currentTime;

                if (this.autoplay) {
                    target.play().catch(this.handleError.bind(this));
                } else {
                    this.pause();
                }

                this.duration = target.duration || 0;
                this.isLoaded = true;
            },
            timeUpdate(event: Event): void {
                const target = event.target as HTMLMediaElement;

                this.isPlaying = true;
                this.isError = false;
                this.runtime = Math.floor(target.currentTime);
            },
            play(): void {
                this.isPaused = false;
                this.isPlaying = true;
                this.isError = false;
                this.saveState();
                this.startTimer();
            },
            pause(): void {
                this.isPlaying = false;
                this.isPaused = true;
                this.saveState();
                this.clearTimer();
            },
            ended(): void {
                this.pause();
                this.runtime = 0;
                this.sendTimeUpdate();
            },
            buffering(): void {
                this.isPlaying = false;
            },
            error(event: Event): void {
                const target = event.target as HTMLMediaElement;
                this.handleError(target.error);
            },
            togglePlayPause(): void {
                if (this.isPaused) {
                    this.$refs.audio.play();
                } else {
                    this.$refs.audio.pause();
                }
            },
            skip(): void {
                if (this.isPlaying) {
                    this.$refs.audio.currentTime = this.runtime;
                }
            },
            skipTo(seconds: number): void {
                if (this.isPlaying) {
                    this.$refs.audio.currentTime += seconds;
                }
            },
            skipBack(): void {
                this.skipTo(-10);
            },
            skipForward(): void {
                this.skipTo(10);
            },
            shortcuts(event: KeyboardEvent): void {
                const target = event.target as HTMLElement;
                if (target.tagName.match(/INPUT|TEXTAREA/)) {
                    return;
                }

                const handleEvent = (fn: Function) => {
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
            startTimer(): void {
                if (!this.timer) {
                    this.timer = setInterval(() => {
                        if (this.isPlaying) {
                            this.sendTimeUpdate();
                        }
                    }, 5000);
                }
            },
            clearTimer(): void {
                if (this.timer) {
                    clearInterval(this.timer);
                    this.timer = null;
                }
            },
            sendTimeUpdate(): void {
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
            incrementRate(): void {
                this.changeRate(0.1);
            },
            decrementRate(): void {
                this.changeRate(-0.1);
            },
            resetRate(): void {
                this.setRate(1.0);
            },
            changeRate(increment: number): void {
                const newValue = Math.max(
                    0.5,
                    Math.min(2.0, parseFloat(this.rate) + increment),
                );
                this.setRate(newValue);
            },
            setRate(value: number): void {
                this.rate = value;
                this.saveState();
            },
            loadState(): PlayerState {
                const state = sessionStorage.getItem("player");
                return state
                    ? <PlayerState>JSON.parse(state)
                    : {
                          rate: 1.0,
                          autoplay: false,
                      };
            },
            saveState(): void {
                sessionStorage.setItem(
                    "player",
                    JSON.stringify(<PlayerState>{
                        rate: this.rate,
                        autoplay: this.isPlaying,
                    }),
                );
            },
            formatCounter(value: number): string {
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
            getMediaMetadata(): MediaMetadata | null {
                const dataTag = document.getElementById("player-metadata");
                if (!dataTag) {
                    return null;
                }

                const metadata = JSON.parse(dataTag.textContent || "");

                if (metadata && Object.keys(metadata).length > 0) {
                    return new MediaMetadata(metadata);
                }
                return null;
            },
            handleError(error: Error): void {
                this.pause();
                this.isError = true;
                console.error(error);
            },
        }),
    );
});
