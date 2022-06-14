"use strict";
exports.__esModule = true;
var alpinejs_1 = require("alpinejs");
require("htmx.org");
require("./player");
// set global Alpine instance
window.Alpine = alpinejs_1["default"];
alpinejs_1["default"].start();
