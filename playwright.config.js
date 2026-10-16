// @ts-check
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/e2e',
  testMatch: /.*\.spec\.js/,
  timeout: 30000,
  expect: {
    timeout: 5000,
  },
  fullyParallel: false,
  workers: 1,
  reporter: [['list'], ['html', { outputFolder: 'tests/e2e/playwright-report', open: 'never' }]],
  use: {
    baseURL: 'http://localhost:8000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    headless: true,
  },
  projects: [
    {
      name: 'Desktop Chrome (1280px)',
      use: {
        browserName: 'chromium',
        viewport: { width: 1280, height: 800 },
      },
    },
    {
      name: 'Mobile Viewport (375px)',
      use: {
        browserName: 'chromium',
        viewport: { width: 375, height: 667 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
});
