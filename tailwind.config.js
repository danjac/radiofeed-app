/* eslint-disable */

const colors = require('tailwindcss/colors');

module.exports = {
    mode: 'jit',
    darkMode: 'media',
    future: {
        removeDeprecatedGapUtilities: true,
        purgeLayersByDefault: true,
    },
    content: [
        './templates/**/*.html',
        './assets/js/**/*.js',
        './tailwind-safelist.txt',
    ],
    keyframes: true,
    theme: {
        extend: {
            colors: {
                orange: colors.orange,
            },
        },
    },
    variants: {
        textColor: ['responsive', 'hover', 'focus', 'visited', 'dark'],
    },
    plugins: [require('@tailwindcss/forms')],
};
