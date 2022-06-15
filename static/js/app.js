"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const alpinejs_1 = __importDefault(require("alpinejs"));
require("htmx.org");
require("./player");
window.Alpine = alpinejs_1.default;
alpinejs_1.default.start();
