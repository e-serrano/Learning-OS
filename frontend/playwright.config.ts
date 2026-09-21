import { defineConfig, devices } from '@playwright/test'

/** E2E config (docs/TASKS.md T120). Boots the real backend against a
 * disposable database (`backend/scripts/run_e2e_backend.py`, deletes
 * and re-migrates it every run so "fresh install" is actually fresh)
 * plus the real frontend dev server, then drives both with a real
 * browser -- no mocked `fetch`, unlike every Vitest test in `src/`. */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'uv run python scripts/run_e2e_backend.py',
      cwd: '../backend',
      url: 'http://127.0.0.1:8000/api/v1/health',
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
