import { defineConfig } from "vitest/config";

/**
 * M02 — unit tests for the web app's pure logic modules.
 *
 * Deliberately `environment: "node"`, and deliberately scoped to the modules
 * that hold no React: `shellState.ts` and `cycleUtils.ts` are written to be
 * testable without a DOM, and pulling in jsdom plus @testing-library would add
 * a heavy dependency to assert arithmetic (UPDATE_RULES.md §8).
 *
 * The one DOM API these modules touch is localStorage, which the shellState
 * test stubs directly — a dozen lines, versus a whole browser environment.
 *
 * Kept separate from vite.config.ts so the production build is untouched.
 */
export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/__tests__/**/*.test.ts"],
    globals: false,
    reporters: ["default"],
  },
});
