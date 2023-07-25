import Alpine from "alpinejs";
import htmx from "htmx.org";
import "./audio-player";

// global HTMX configuration
// https://htmx.org/docs/#config

htmx.config.historyCacheSize = 0;
htmx.config.refreshOnHistoryMiss = false;
htmx.config.useTemplateFragments = true;

// set global Alpine instance
window.Alpine = Alpine;

Alpine.start();

document.body.addEventListener("htmx:beforeSwap", function (event) {
    // allow invalid form responses to swap as we are using this as a signal that
    // a form was submitted with bad data and want to rerender with the errors
    if (event.detail.xhr.status === 422) {
        event.detail.shouldSwap = true;
        event.detail.isError = false;
    }
});
