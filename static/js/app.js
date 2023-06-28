import Alpine from "alpinejs";
import "htmx.org";
import "./audio-player";

// set global Alpine instance
window.Alpine = Alpine;

Alpine.start();
document.body.addEventListener("htmx:beforeSwap", function (event) {
    if (event.detail.xhr.status === 422) {
        // allow 422 responses to swap as we are using this as a signal that
        // a form was submitted with bad data and want to rerender with the
        // errors
        //
        // set isError to false to avoid error logging in console
        event.detail.shouldSwap = true;
        event.detail.isError = false;
    }
});
