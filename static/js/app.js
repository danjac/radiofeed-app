import Alpine from "alpinejs";
import "htmx.org";
import "./audio-player";

// set global Alpine instance
window.Alpine = Alpine;

Alpine.start();

document.body.addEventListener("htmx:beforeSwap", function (event) {
    // unprocessable entity
    if (event.detail.xhr.status === 422) {
        event.detail.shouldSwap = true;
        event.detail.isError = false;
    }
});
