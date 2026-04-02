import { defineConfig, devices } from '@playwright/test';

/**
 * E2E test configuration for DocIntel frontend.
 *
 * Run with:
 *   npm run test:e2e           — headless Chromium
 *   npm run test:e2e:ui        — interactive Playwright UI
 *
 * Expects the full stack (frontend + backend + DB + Redis) to be running.
 * Override BASE_URL env var to point at a different host.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,       // WS + upload tests share DB state
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['list'],
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
