/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { configDefaults } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/setupTests.ts'],
    // e2e/ holds Playwright specs (docs/TASKS.md T120), run via
    // `npm run test:e2e`, not Vitest -- Vitest's default include glob
    // would otherwise also pick up `e2e/*.spec.ts` and fail to run
    // Playwright's `test()` outside a Playwright test run.
    exclude: [...configDefaults.exclude, 'e2e/**'],
  },
})
