import Alpine from "alpinejs";
import "htmx.org";
import "./audio-player";

// global HTMX configuration
// https://htmx.org/docs/#config

// htmx.config.historyCacheSize = 0;
// htmx.config.refreshOnHistoryMiss = false;
// htmx.config.scrollBehavior = "smooth";
// htmx.config.scrollIntoViewOnBoost = false;
// htmx.config.useTemplateFragments = true;

// initialize global Alpine instance

window.Alpine = Alpine;
window.Alpine.start();
