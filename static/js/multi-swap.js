(function () {
    /** @type {import("../htmx").HtmxInternalApi} */
    let api;

    htmx.defineExtension("multi-swap", {
        init(apiRef) {
            api = apiRef;
        },
        isInlineSwap(swapStyle) {
            return swapStyle.indexOf("multi:") === 0;
        },
        handleSwap(swapStyle, _target, fragment, settleInfo) {
            if (swapStyle.indexOf("multi:") === 0) {
                const selectorToSwapStyle = {};
                const elements = swapStyle
                    .replace(/^multi\s*:\s*/, "")
                    .split(/\s*,\s*/);

                elements.map(element => {
                    const split = element.split(/\s*:\s*/);
                    const elementSelector = split[0];
                    const elementSwapStyle =
                        typeof split[1] !== "undefined"
                            ? split[1]
                            : "innerHTML";

                    if (elementSelector.charAt(0) !== "#") {
                        console.error(
                            "HTMX multi-swap: unsupported selector '" +
                                elementSelector +
                                "'. Only ID selectors starting with '#' are supported.",
                        );
                        return;
                    }

                    selectorToSwapStyle[elementSelector] = elementSwapStyle;
                });

                for (let selector in selectorToSwapStyle) {
                    const swapStyle = selectorToSwapStyle[selector];
                    const elementToSwap = fragment.querySelector(selector);
                    if (elementToSwap) {
                        api.oobSwap(swapStyle, elementToSwap, settleInfo);
                    } else {
                        console.warn(
                            "HTMX multi-swap: selector '" +
                                selector +
                                "' not found in source content.",
                        );
                    }
                }

                return true;
            }
        },
    });
})();
