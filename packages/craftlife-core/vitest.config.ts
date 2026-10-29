import { defineConfig } from "vitest/config";

/**
 * M02 — unit tests for the shared core utilities.
 *
 * `environment: "node"` because currency.ts and serverClock.ts are deliberately
 * pure: no DOM, no fetch, no clock reads. That purity is what lets the same
 * package run in the web app and (from M07) in React Native.
 */
export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/__tests__/**/*.test.ts"],
    globals: false,
    reporters: ["default"],
  },
});
