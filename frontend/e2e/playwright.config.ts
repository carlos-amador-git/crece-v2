import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright configuration for CRECE v2.0 E2E smoke tests.
 *
 * Runs against a locally-running Next.js dev server on port 3000.
 * Only chromium is used to keep the suite lightweight.
 */
export default defineConfig({
  testDir: ".",
  testMatch: "**/*.spec.ts",

  /* Fail the build on CI if test.only was left in source */
  forbidOnly: !!process.env.CI,

  /* Retry once on CI to absorb flakiness; zero retries locally */
  retries: process.env.CI ? 1 : 0,

  /* Single worker keeps resource use predictable */
  workers: 1,

  /* Reporter: list for local, html for CI */
  reporter: process.env.CI ? "html" : "list",

  /* Shared settings for all tests */
  use: {
    baseURL: process.env.BASE_URL || "http://localhost:3005",

    /* Capture screenshot on failure for post-mortem analysis */
    screenshot: "only-on-failure",

    /* Capture trace on first retry (CI only) */
    trace: "on-first-retry",

    /* Reasonable navigation timeout */
    navigationTimeout: 15_000,
    actionTimeout: 10_000,
  },

  /* Single browser project */
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  /* Output directory for screenshots, traces, and videos */
  outputDir: "./test-results",

  /* Optionally start the dev server before running tests */
  // Uncomment the block below if you want Playwright to start `next dev` automatically.
  // webServer: {
  //   command: "npm run dev",
  //   url: "http://localhost:3000",
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 60_000,
  // },
});
