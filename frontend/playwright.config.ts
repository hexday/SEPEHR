// SEPEHR Frontend — Playwright Configuration

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ["html", { outputFolder: "playwright-report" }],
    ["list"],
  ],

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    // RTL viewport matching typical Android phone
    viewport: { width: 390, height: 844 },
    locale: "fa-IR",
  },

  projects: [
    // Mobile Chrome (Android simulation — primary target)
    {
      name: "Mobile Chrome",
      use: {
        ...devices["Pixel 7"],
        locale: "fa-IR",
      },
    },
    // Desktop browser
    {
      name: "Desktop Chrome",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1280, height: 720 },
      },
    },
    // iOS Safari
    {
      name: "Mobile Safari",
      use: {
        ...devices["iPhone 14"],
        locale: "fa-IR",
      },
    },
  ],

  // Dev server for local testing
  webServer: process.env.CI
    ? undefined
    : {
        command: "npm run dev",
        url: "http://localhost:3000",
        reuseExistingServer: !process.env.CI,
        timeout: 60000,
      },
});
