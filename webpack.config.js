//webpack.config.js
const path = require('path');

module.exports = {
  devtool: "source-map",
  entry: {
    main: "./static/js/app.ts",
  },
  output: {
    path: path.resolve(__dirname, './static/dist'),
    filename: "bundle.js" // <--- Will be compiled to this single file
  },
  resolve: {
    extensions: [".ts", ".tsx", ".js"],
  },
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        loader: "ts-loader"
      }
    ]
  }
};
