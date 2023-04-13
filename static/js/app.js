import Alpine from "alpinejs";
import htmx from "htmx.org";
import "./player";

// set global Alpine instance
window.Alpine = Alpine;

window.htmx = htmx;

Alpine.start();
