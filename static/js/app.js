import Alpine from "alpinejs";
import "htmx.org";
import "./audio-player";

// set global Alpine instance
window.Alpine = Alpine;

Alpine.start();

document.body.addEventListener("htmx:beforeSwap", function (event) {
    switch (event.detail.xhr.status) {
        case 400:
        case 422:
            // allow invalid form responses to swap as we are using this as a signal that
            // a form was submitted with bad data and want to rerender with the errors
            event.detail.shouldSwap = true;
            event.detail.isError = false;
            break;
    }
});
