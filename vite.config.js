import { defineConfig } from "vite";
import path from "path";

export default defineConfig({
    build: {
        outDir: path.resolve(__dirname, "static", "dist"),
        assetsDir: ".",
        sourcemap: true,
        emptyOutDir: false,
        rollupOptions: {
            input: {
                main: path.resolve("static", "js", "app.js"),
            },
            output: {
                entryFileNames: "bundle.js",
            },
        },
    },
});
