import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["tests/**/*.test.ts"],
    environment: "node",
    // Pass-through console output so LDD trajectory ([IMP:N][fn][PHASE] …)
    // is visible on every run, not only on failure. Matches lesson_28 convention.
    disableConsoleIntercept: true,
  },
});
