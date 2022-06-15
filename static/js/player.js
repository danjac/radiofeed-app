"use strict";
exports.__esModule = true;
var alpinejs_1 = require("alpinejs");
document.addEventListener("alpine:init", function () {
    alpinejs_1["default"].data("player", function (autoplay, mediaSrc, currentTime, csrfToken, timeUpdateUrl) {
        if (autoplay === void 0) { autoplay = false; }
        if (mediaSrc === void 0) { mediaSrc = null; }
        if (currentTime === void 0) { currentTime = 0; }
        if (csrfToken === void 0) { csrfToken = null; }
        if (timeUpdateUrl === void 0) { timeUpdateUrl = null; }
        return ({
            autoplay: autoplay,
            mediaSrc: mediaSrc,
            currentTime: currentTime,
            csrfToken: csrfToken,
            timeUpdateUrl: timeUpdateUrl,
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
                total: "00:00:00"
            },
            init: function () {
                var _this = this;
                this.$watch("runtime", function (value) {
                    _this.counters.current = _this.formatCounter(value);
                });
                this.$watch("duration", function (value) {
                    _this.counters.total = _this.formatCounter(value);
                });
                this.$watch("rate", function (value) {
                    _this.$refs.audio.rate = value;
                });
                this.$refs.audio.load();
                if ("mediaSession" in navigator) {
                    navigator.mediaSession.metadata = this.getMediaMetadata();
                }
            },
            destroy: function () {
                this.clearTimer();
            },
            loaded: function (event) {
                if (this.isLoaded) {
                    return;
                }
                var target = event.target;
                var _a = this.loadState(), rate = _a.rate, autoplay = _a.autoplay;
                this.isError = false;
                this.rate = rate || 1.0;
                this.autoplay = autoplay || this.autoplay;
                target.currentTime = this.currentTime;
                if (this.autoplay) {
                    target.play()["catch"](this.handleError.bind(this));
                }
                else {
                    this.pause();
                }
                this.duration = target.duration || 0;
                this.isLoaded = true;
            },
            timeUpdate: function (event) {
                var target = event.target;
                this.isPlaying = true;
                this.isError = false;
                this.runtime = Math.floor(target.currentTime);
            },
            play: function () {
                this.isPaused = false;
                this.isPlaying = true;
                this.isError = false;
                this.saveState();
                this.startTimer();
            },
            pause: function () {
                this.isPlaying = false;
                this.isPaused = true;
                this.saveState();
                this.clearTimer();
            },
            ended: function () {
                this.pause();
                this.runtime = 0;
                this.sendTimeUpdate();
            },
            buffering: function () {
                this.isPlaying = false;
            },
            error: function (event) {
                var target = event.target;
                this.handleError(target.error);
            },
            togglePlayPause: function () {
                if (this.isPaused) {
                    this.$refs.audio.play();
                }
                else {
                    this.$refs.audio.pause();
                }
            },
            skip: function () {
                if (this.isPlaying) {
                    this.$refs.audio.currentTime = this.runtime;
                }
            },
            skipTo: function (seconds) {
                if (this.isPlaying) {
                    this.$refs.audio.currentTime += seconds;
                }
            },
            skipBack: function () {
                this.skipTo(-10);
            },
            skipForward: function () {
                this.skipTo(10);
            },
            shortcuts: function (event) {
                var _this = this;
                var target = event.target;
                if (target.tagName.match(/INPUT|TEXTAREA/)) {
                    return;
                }
                var handleEvent = function (fn) {
                    event.preventDefault();
                    event.stopPropagation();
                    fn.bind(_this)();
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
            startTimer: function () {
                var _this = this;
                if (!this.timer) {
                    this.timer = setInterval(function () {
                        if (_this.isPlaying) {
                            _this.sendTimeUpdate();
                        }
                    }, 5000);
                }
            },
            clearTimer: function () {
                if (this.timer) {
                    clearInterval(this.timer);
                    this.timer = null;
                }
            },
            sendTimeUpdate: function () {
                fetch(this.timeUpdateUrl, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": this.csrfToken
                    },
                    body: new URLSearchParams({
                        current_time: this.runtime
                    })
                });
            },
            incrementRate: function () {
                this.changeRate(0.1);
            },
            decrementRate: function () {
                this.changeRate(-0.1);
            },
            resetRate: function () {
                this.setRate(1.0);
            },
            changeRate: function (increment) {
                var newValue = Math.max(0.5, Math.min(2.0, parseFloat(this.rate) + increment));
                this.setRate(newValue);
            },
            setRate: function (value) {
                this.rate = value;
                this.saveState();
            },
            loadState: function () {
                var state = sessionStorage.getItem("player");
                return state
                    ? JSON.parse(state)
                    : {
                        rate: 1.0,
                        autoplay: false
                    };
            },
            saveState: function () {
                sessionStorage.setItem("player", JSON.stringify({
                    rate: this.rate,
                    autoplay: this.isPlaying
                }));
            },
            formatCounter: function (value) {
                if (isNaN(value) || value < 0)
                    return "00:00:00";
                var duration = Math.floor(value);
                var hours = Math.floor(duration / 3600);
                var minutes = Math.floor((duration % 3600) / 60);
                var seconds = Math.floor(duration % 60);
                return [hours, minutes, seconds]
                    .map(function (t) { return t.toString().padStart(2, "0"); })
                    .join(":");
            },
            getMediaMetadata: function () {
                var dataTag = document.getElementById("player-metadata");
                if (!dataTag) {
                    return null;
                }
                var metadata = JSON.parse(dataTag.textContent || "");
                if (metadata && Object.keys(metadata).length > 0) {
                    return new MediaMetadata(metadata);
                }
                return null;
            },
            handleError: function (error) {
                this.pause();
                this.isError = true;
                console.error(error);
            }
        });
    });
});
