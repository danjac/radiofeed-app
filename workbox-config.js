module.exports = {
    globDirectory: "static/",
    globPatterns: ["**/*.{css,js,png,webp,html}"],
    swDest: "static/service-worker.js",
    ignoreURLParametersMatching: [/^utm_/, /^fbclid$/],
    runtimeCaching: [
        {
            urlPattern: /\/static\/.*/,
            handler: "CacheFirst",
        },
    ],
};
