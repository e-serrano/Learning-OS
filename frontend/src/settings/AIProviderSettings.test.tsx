import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AIProviderSettings } from './AIProviderSettings'

function jsonResponse(body: unknown) {
  return { ok: true, json: async () => body } as Response
}

const STATUS_WITH_ANTHROPIC = {
  onboarding_step: 'COMPLETE',
  vault_path: '/vault',
  provider_id: 'anthropic',
  model: 'claude-sonnet-5',
  language: 'en',
  ai_providers: [
    {
      id: 'p1',
      provider_id: 'anthropic',
      model: 'claude-sonnet-5',
      base_url: null,
      credential_ref: 'anthropic:abc',
      enabled: true,
      is_default: true,
    },
  ],
}

const STATUS_WITH_OLLAMA = {
  ...STATUS_WITH_ANTHROPIC,
  provider_id: 'ollama',
  model: 'llama3',
  ai_providers: [
    {
      id: 'p1',
      provider_id: 'ollama',
      model: 'llama3',
      base_url: 'http://localhost:11434',
      credential_ref: null,
      enabled: true,
      is_default: true,
    },
  ],
}

describe('AIProviderSettings', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('prefills the current provider and model', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(STATUS_WITH_ANTHROPIC)))

    render(<AIProviderSettings />)

    expect(await screen.findByLabelText('AI provider')).toHaveValue('anthropic')
    expect(screen.getByLabelText('Model')).toHaveValue('claude-sonnet-5')
  })

  it('shows the API key field only for a provider that requires one', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(STATUS_WITH_ANTHROPIC)))

    render(<AIProviderSettings />)
    await screen.findByLabelText('AI provider')

    expect(screen.getByLabelText('API key')).toBeInTheDocument()
    expect(screen.queryByLabelText('Endpoint URL')).not.toBeInTheDocument()
  })

  it('shows the endpoint URL field for ollama, prefilled, and no API key field', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(STATUS_WITH_OLLAMA)))

    render(<AIProviderSettings />)
    await screen.findByLabelText('AI provider')

    expect(screen.getByLabelText('Endpoint URL')).toHaveValue('http://localhost:11434')
    expect(screen.queryByLabelText('API key')).not.toBeInTheDocument()
  })

  it('saves and reports a successful connection', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.endsWith('/onboarding/status')) {
          return Promise.resolve(jsonResponse(STATUS_WITH_ANTHROPIC))
        }
        if (url.endsWith('/onboarding/ai-provider')) {
          return Promise.resolve(jsonResponse({ onboarding_step: 'AI_PROVIDER' }))
        }
        if (url.endsWith('/onboarding/ai-provider/validate')) {
          return Promise.resolve(
            jsonResponse({ onboarding_step: 'VALIDATE', ok: true, reason: null }),
          )
        }
        return Promise.reject(new Error(`unexpected fetch: ${url}`))
      }),
    )

    render(<AIProviderSettings />)
    await screen.findByLabelText('AI provider')

    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'sk-ant-new' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save & test connection' }))

    expect(await screen.findByText('Connected successfully.')).toBeInTheDocument()
  })

  it('reports a failed connection with the reason', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.endsWith('/onboarding/status')) {
          return Promise.resolve(jsonResponse(STATUS_WITH_ANTHROPIC))
        }
        if (url.endsWith('/onboarding/ai-provider')) {
          return Promise.resolve(jsonResponse({ onboarding_step: 'AI_PROVIDER' }))
        }
        if (url.endsWith('/onboarding/ai-provider/validate')) {
          return Promise.resolve(
            jsonResponse({
              onboarding_step: 'AI_PROVIDER',
              ok: false,
              reason: 'Your credit balance is too low',
            }),
          )
        }
        return Promise.reject(new Error(`unexpected fetch: ${url}`))
      }),
    )

    render(<AIProviderSettings />)
    await screen.findByLabelText('AI provider')

    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'sk-ant-broke' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save & test connection' }))

    expect(
      await screen.findByText('Connection failed: Your credit balance is too low'),
    ).toBeInTheDocument()
  })

  it('clears the API key field after every submit attempt', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.endsWith('/onboarding/status')) {
          return Promise.resolve(jsonResponse(STATUS_WITH_ANTHROPIC))
        }
        if (url.endsWith('/onboarding/ai-provider')) {
          return Promise.resolve(jsonResponse({ onboarding_step: 'AI_PROVIDER' }))
        }
        return Promise.resolve(jsonResponse({ onboarding_step: 'VALIDATE', ok: true, reason: null }))
      }),
    )

    render(<AIProviderSettings />)
    await screen.findByLabelText('AI provider')

    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'sk-ant-new' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save & test connection' }))
    await screen.findByText('Connected successfully.')

    expect(screen.getByLabelText('API key')).toHaveValue('')
  })

  it('shows an error message when the initial status fetch fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: { error: { code: 'UNKNOWN_ERROR', message: 'boom' } } }),
      }),
    )

    render(<AIProviderSettings />)

    expect(await screen.findByText('boom')).toBeInTheDocument()
  })
})
