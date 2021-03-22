/* eslint-disable */
module.exports = {
  plugins: [
    require('postcss-import'),
    require('@tailwindcss/jit')('./tailwind.config.js'),
    require('autoprefixer'),
    require('cssnano', { preset: 'default' }),
  ],
};
