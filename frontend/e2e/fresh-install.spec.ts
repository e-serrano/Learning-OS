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

  // A fresh install has no stored AppConfig.language yet, so it defaults
  // to Spanish (docs/TASKS.md T147, user request: Spanish preferred) --
  // every onboarding/dashboard string below asserts the Spanish copy,
  // not the English one this scenario used before that default changed.
  await expect(page.getByRole('heading', { name: 'Bienvenido a Learning OS' })).toBeVisible()
  await page.getByLabel('Ruta de la carpeta del vault').fill(VAULT_PATH)
  await page.getByRole('button', { name: 'Escanear vault' }).click()
  await expect(page.getByText(/archivos? Markdown/)).toBeVisible()
  await page.getByRole('button', { name: 'Continuar' }).click()

  await expect(page.getByRole('heading', { name: 'Elige un proveedor de IA' })).toBeVisible()
  await page.getByRole('button', { name: /Mock \(offline, deterministic\)/ }).click()
  await page.getByRole('button', { name: 'Continuar' }).click()

  await expect(page.getByRole('heading', { name: /Conectar con Mock/ })).toBeVisible()
  await page.getByLabel('Modelo').fill('mock-1')
  await page.getByRole('button', { name: 'Probar conexión' }).click()

  await expect(page.getByRole('heading', { name: 'Todo preparado' })).toBeVisible()
  await page.getByRole('button', { name: 'Finalizar configuración' }).click()

  await expect(page.getByRole('heading', { name: 'Panel' })).toBeVisible()

  await page.getByLabel('¿Qué quieres aprender?').fill('Learn advanced SQL')
  await page.getByRole('button', { name: 'Crear objetivo' }).click()

  await expect(page.getByText('Learn advanced SQL')).toBeVisible()
  await expect(page.getByText('draft')).toBeVisible()
})
