/* eslint-disable */

const colors = require('tailwindcss/colors');

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
      ],
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
