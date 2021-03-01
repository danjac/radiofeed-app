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
        'animate-pulse',
        'h-8',
        'w-8',
        'h-16',
        'w-16',
        'h-20',
        'w-20',
        'h-24',
        'w-24',
        'h-28',
        'w-28',
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
