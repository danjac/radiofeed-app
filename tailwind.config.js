/* eslint-disable */

const plugin = require("tailwindcss/plugin");

module.exports = {
    mode: "jit",
    darkMode: "media",
    future: {
        removeDeprecatedGapUtilities: true,
        purgeLayersByDefault: true,
    },
    content: ["./templates/**/*.html"],
    keyframes: true,
    variants: {
        textColor: ["responsive", "hover", "focus", "visited", "dark"],
    },
    plugins: [
        // https://www.crocodile.dev/blog/css-transitions-with-tailwind-and-htmx
        plugin(function ({ addVariant }) {
            addVariant("htmx-settling", [
                "&.htmx-settling",
                ".htmx-settling &",
            ]);
            addVariant("htmx-request", ["&.htmx-request", ".htmx-request &"]);
            addVariant("htmx-swapping", [
                "&.htmx-swapping",
                ".htmx-swapping &",
            ]);
            addVariant("htmx-added", ["&.htmx-added", ".htmx-added &"]);
        }),
        require("@tailwindcss/forms"),
        require("@tailwindcss/typography"),
    ],
    theme: {
        extend: {
            spacing: {
                128: "32rem",
            },
        },
    },
};
