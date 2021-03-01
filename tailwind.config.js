/* eslint-disable */

const colors = require('tailwindcss/colors');

const sizes = [8, 14, 16, 18, 20, 24, 28];

module.exports = {
  darkMode: 'class',
  future: {
    removeDeprecatedGapUtilities: true,
    purgeLayersByDefault: true,
  },
  purge: {
    content: ['./templates/**/*.html', './static/src/js/**/*.js'],
    options: {
      safelist: [
        'type', // [type='checkbox']
        'animate-pulse',
      ]
        .concat(sizes.map((size) => `h-${size}`))
        .concat(sizes.map((size) => `w-${size}`)),
      keyframes: true,
    },
  },
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
