/* eslint-disable */

const colors = require('tailwindcss/colors');

module.exports = {
  mode: 'jit',
  darkMode: 'media',
  future: {
    removeDeprecatedGapUtilities: true,
    purgeLayersByDefault: true,
  },
  purge: {
    content: ['./templates/**/*.html', './static/src/js/**/*.js', './safelist.txt'],
    keyframes: true,
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
