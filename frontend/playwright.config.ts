import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  timeout: 100_000,
  expect: { timeout: 90_000 },
  use: {
    baseURL: process.env.DOCS_RAG_BASE_URL ?? 'http://127.0.0.1:8000',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1366, height: 900 } } },
    { name: 'mobile', use: { viewport: { width: 320, height: 800 }, isMobile: true, hasTouch: true } },
  ],
})
