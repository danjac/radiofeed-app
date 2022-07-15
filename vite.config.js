import path from "path";
import { defineConfig } from "vite";

export default defineConfig({
    build: {
        outDir: path.resolve(__dirname, "static"),
        emptyOutDir: false,
        sourcemap: true,
        rollupOptions: {
            input: {
                main: path.resolve("static", "js", "app.js"),
            },
            output: {
                entryFileNames: "dist/bundle.js",
            },
        },
    },
});
