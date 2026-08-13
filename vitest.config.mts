import { cloudflareTest } from "@cloudflare/vitest-pool-workers";
import { defineConfig } from "vitest/config";

export default defineConfig({
  define: {
    PACKAGE_VERSION: JSON.stringify("3.2.1"),
  },
  plugins: [
    cloudflareTest({
      wrangler: { configPath: "./wrangler.jsonc" },
    }),
  ],
  test: {
    deps: {
      optimizer: {
        ssr: {
          enabled: true,
          include: [
            "mathjax-full",
            "mathjax-full/js/mathjax.js",
            "mathjax-full/js/adaptors/liteAdaptor.js",
            "mathjax-full/js/handlers/html.js",
            "mathjax-full/js/input/tex.js",
            "mathjax-full/js/input/tex/AllPackages.js",
            "mathjax-full/js/output/svg.js",
          ],
        },
      },
    },
  },
});
