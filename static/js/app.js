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
