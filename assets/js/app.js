import Alpine from "alpinejs";
import htmx from "htmx.org/dist/htmx.esm";
import "./audio-player";

// initialize global HTMX instance

window.htmx = htmx;

window.htmx.config.historyCacheSize = 0;
window.htmx.config.refreshOnHistoryMiss = false;
window.htmx.config.scrollBehavior = "instant";
window.htmx.config.scrollIntoViewOnBoost = false;
window.htmx.config.useTemplateFragments = true;

// initialize global Alpine instance

window.Alpine = Alpine;
window.Alpine.start();

// HTMX: handle errors
// call a page redirect
document.body.addEventListener("htmx:responseError", () => {
    window.location.reload();
});
