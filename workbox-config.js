module.exports = {
    globDirectory: 'static/',
    globPatterns: [
        '**/*.{css,js,png,webp,xcf,html}'
    ],
    swDest: 'static/sw.js',
    ignoreURLParametersMatching: [
        /^utm_/,
        /^fbclid$/
    ]
};
