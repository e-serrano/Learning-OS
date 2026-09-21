import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const VAULT_PATH = path.resolve(__dirname, 'fixtures/vault')

/** Fresh-install E2E (docs/TASKS.md T120, dep T110): install →
 * onboarding → vault → provider → goal. Runs against the real backend
 * (`playwright.config.ts` boots it against a disposable database that
 * is deleted and re-migrated before every run, docs/TASKS.md T120) and
 * the real frontend dev server -- no mocked `fetch`, unlike every
 * Vitest test under `src/`. Uses the mock AI provider: `POST
 * /onboarding/ai-provider/validate` only calls `check_provider_capability`
 * (T018), not the full `AIOrchestrator.generate()` pipeline that needs a
 * canned `MockProvider` response -- so this scenario (through creating
 * the first goal) never hits the "MockProvider has no configured
 * response" wall every other E2E-adjacent page in Phase 11 ran into
 * during manual verification. */
test('fresh install reaches the dashboard and creates a first goal', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Welcome to Learning OS' })).toBeVisible()
  await page.getByLabel('Vault folder path').fill(VAULT_PATH)
  await page.getByRole('button', { name: 'Scan vault' }).click()
  await expect(page.getByText(/Found \d+ Markdown file/)).toBeVisible()
  await page.getByRole('button', { name: 'Continue' }).click()

  await expect(page.getByRole('heading', { name: 'Choose an AI provider' })).toBeVisible()
  await page.getByRole('button', { name: /Mock \(offline, deterministic\)/ }).click()
  await page.getByRole('button', { name: 'Continue' }).click()

  await expect(page.getByRole('heading', { name: /Connect Mock/ })).toBeVisible()
  await page.getByLabel('Model').fill('mock-1')
  await page.getByRole('button', { name: 'Test connection' }).click()

  await expect(page.getByRole('heading', { name: 'Ready to go' })).toBeVisible()
  await page.getByRole('button', { name: 'Finish setup' }).click()

  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()

  await page.getByLabel('What do you want to learn?').fill('Learn advanced SQL')
  await page.getByRole('button', { name: 'Create goal' }).click()

  await expect(page.getByText('Learn advanced SQL')).toBeVisible()
  await expect(page.getByText('draft')).toBeVisible()
})
