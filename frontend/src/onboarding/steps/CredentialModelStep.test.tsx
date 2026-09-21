import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
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

  function renderStep(onValidated = vi.fn()) {
    render(
      <CredentialModelStep
        providerId="openai"
        baseUrl={null}
        onValidated={onValidated}
        onBack={vi.fn()}
      />,
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
