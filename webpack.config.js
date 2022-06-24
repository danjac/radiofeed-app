const path = require("path");

module.exports = {
    devtool: "source-map",
    entry: {
        main: "./static/js/app.js",
    },
    output: {
        path: path.resolve(__dirname, "./static/dist"),
        filename: "bundle.js",
    },
    resolve: {
        extensions: [".js"],
    },
};
