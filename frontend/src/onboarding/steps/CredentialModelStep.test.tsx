import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider } from '../../i18n/LanguageContext'
import { CredentialModelStep } from './CredentialModelStep'

function jsonResponse(body: unknown) {
  return { ok: true, json: async () => body } as Response
}

/** docs/TASKS.md T124 (secrets/security audit): the API key is only ever
 * meant to live in this form's own React state long enough to send it once
 * -- never in localStorage, never logged, and never left behind after the
 * request settles, whether it succeeds or fails. */
describe('CredentialModelStep', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  function renderStep(onValidated = vi.fn(), providerId = 'openai', baseUrl: string | null = null) {
    render(
      <CredentialModelStep
        providerId={providerId}
        baseUrl={baseUrl}
        onValidated={onValidated}
        onBack={vi.fn()}
      />,
      { wrapper: LanguageProvider },
    )
  }

  it('renders the API key field as a password input that never autocompletes', () => {
    renderStep()
    const input = screen.getByLabelText('API key') as HTMLInputElement
    expect(input.type).toBe('password')
    expect(input.autocomplete).toBe('off')
  })

  it('clears the API key from state after a successful validation', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/ai-provider/validate')) {
          return Promise.resolve(jsonResponse({ onboarding_step: 'VALIDATE', ok: true, reason: null }))
        }
        if (url.includes('/ai-provider')) {
          return Promise.resolve(jsonResponse({ onboarding_step: 'VALIDATE' }))
        }
        if (url.includes('/status')) {
          return Promise.resolve(
            jsonResponse({
              onboarding_step: 'VALIDATE',
              vault_path: '/vault',
              provider_id: 'openai',
              model: 'gpt-5',
              language: 'en',
              ai_providers: [],
            }),
          )
        }
        return Promise.reject(new Error(`unexpected fetch: ${url}`))
      }),
    )
    renderStep()

    fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'gpt-5' } })
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'sk-super-secret' } })
    fireEvent.click(screen.getByText('Test connection'))

    await waitFor(() => expect(screen.getByLabelText('API key')).toHaveValue(''))
  })

  it('prefills OpenRouter with its suggested daily-use and fallback models, with reasoning/fallback hints', () => {
    renderStep(vi.fn(), 'openrouter')

    expect(screen.getByLabelText('Model')).toHaveValue('qwen/qwen3.8-27b:free')
    expect(screen.getByText('nvidia/nemotron-3-ultra:free')).toBeInTheDocument()
    expect(screen.getByLabelText('Fallback model (optional)')).toHaveValue('openrouter/free')
    expect(screen.getByText('deepseek/deepseek-r1:free')).toBeInTheDocument()
  })

  it('leaves model and fallback model blank for a provider with no suggested defaults', () => {
    renderStep(vi.fn(), 'openai')

    expect(screen.getByLabelText('Model')).toHaveValue('')
    expect(screen.getByLabelText('Fallback model (optional)')).toHaveValue('')
  })

  it('submits the fallback model the user typed', async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/ai-provider/validate')) {
        return Promise.resolve(jsonResponse({ onboarding_step: 'VALIDATE', ok: true, reason: null }))
      }
      if (url.includes('/ai-provider')) {
        return Promise.resolve(jsonResponse({ onboarding_step: 'VALIDATE' }))
      }
      if (url.includes('/status')) {
        return Promise.resolve(
          jsonResponse({
            onboarding_step: 'VALIDATE',
            vault_path: '/vault',
            provider_id: 'openrouter',
            model: 'qwen/qwen3.8-27b:free',
            language: 'en',
            ai_providers: [],
          }),
        )
      }
      return Promise.reject(new Error(`unexpected fetch: ${url}`))
    })
    vi.stubGlobal('fetch', fetchMock)
    renderStep(vi.fn(), 'openrouter', 'https://openrouter.ai/api/v1')

    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'sk-or-secret' } })
    fireEvent.click(screen.getByText('Test connection'))

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/ai-provider'),
        expect.objectContaining({
          body: JSON.stringify({
            provider_id: 'openrouter',
            model: 'qwen/qwen3.8-27b:free',
            base_url: 'https://openrouter.ai/api/v1',
            fallback_model: 'openrouter/free',
          }),
        }),
      ),
    )
  })

  it('clears the API key from state after a failed validation, not just a successful one', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/ai-provider/validate')) {
          return Promise.resolve(
            jsonResponse({ onboarding_step: 'AI_PROVIDER', ok: false, reason: 'invalid key' }),
          )
        }
        if (url.includes('/ai-provider')) {
          return Promise.resolve(jsonResponse({ onboarding_step: 'AI_PROVIDER' }))
        }
        return Promise.reject(new Error(`unexpected fetch: ${url}`))
      }),
    )
    renderStep()

    fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'gpt-5' } })
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'sk-super-secret' } })
    fireEvent.click(screen.getByText('Test connection'))

    await screen.findByText(/Connection failed/)
    expect(screen.getByLabelText('API key')).toHaveValue('')
  })
})
