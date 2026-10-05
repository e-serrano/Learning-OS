import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider } from '../i18n/LanguageContext'
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

const STATUS_WITH_OPENROUTER = {
  ...STATUS_WITH_ANTHROPIC,
  provider_id: 'openrouter',
  model: 'qwen/qwen3.8-27b:free',
  ai_providers: [
    {
      id: 'p1',
      provider_id: 'openrouter',
      model: 'qwen/qwen3.8-27b:free',
      base_url: 'https://openrouter.ai/api/v1',
      credential_ref: 'openrouter:abc',
      fallback_model: 'custom/already-saved-fallback',
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

    render(<AIProviderSettings />, { wrapper: LanguageProvider })

    expect(await screen.findByLabelText('AI provider')).toHaveValue('anthropic')
    expect(screen.getByLabelText('Model')).toHaveValue('claude-sonnet-5')
  })

  it('shows the API key field only for a provider that requires one', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(STATUS_WITH_ANTHROPIC)))

    render(<AIProviderSettings />, { wrapper: LanguageProvider })
    await screen.findByLabelText('AI provider')

    expect(screen.getByLabelText('API key')).toBeInTheDocument()
    expect(screen.queryByLabelText('Endpoint URL')).not.toBeInTheDocument()
  })

  it('shows the endpoint URL field for ollama, prefilled, and no API key field', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(STATUS_WITH_OLLAMA)))

    render(<AIProviderSettings />, { wrapper: LanguageProvider })
    await screen.findByLabelText('AI provider')

    expect(screen.getByLabelText('Endpoint URL')).toHaveValue('http://localhost:11434')
    expect(screen.queryByLabelText('API key')).not.toBeInTheDocument()
  })

  it('prefills the fallback model from the saved config, not the provider suggestion', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(STATUS_WITH_OPENROUTER)))

    render(<AIProviderSettings />, { wrapper: LanguageProvider })

    expect(await screen.findByLabelText('Fallback model (optional)')).toHaveValue(
      'custom/already-saved-fallback',
    )
  })

  it('saves the current fallback model value, not the provider suggestion', async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/onboarding/status')) {
        return Promise.resolve(jsonResponse(STATUS_WITH_OPENROUTER))
      }
      if (url.endsWith('/onboarding/ai-provider')) {
        return Promise.resolve(jsonResponse({ onboarding_step: 'AI_PROVIDER' }))
      }
      if (url.endsWith('/onboarding/ai-provider/validate')) {
        return Promise.resolve(jsonResponse({ onboarding_step: 'VALIDATE', ok: true, reason: null }))
      }
      return Promise.reject(new Error(`unexpected fetch: ${url}`))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<AIProviderSettings />, { wrapper: LanguageProvider })
    await screen.findByLabelText('Fallback model (optional)')

    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'sk-or-new' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save & test connection' }))

    await screen.findByText('Connected successfully.')
    const call = fetchMock.mock.calls.find((args: unknown[]) =>
      String(args[0]).endsWith('/onboarding/ai-provider'),
    )
    expect(JSON.parse((call![1]?.body as string) ?? '{}').fallback_model).toBe(
      'custom/already-saved-fallback',
    )
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

    render(<AIProviderSettings />, { wrapper: LanguageProvider })
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

    render(<AIProviderSettings />, { wrapper: LanguageProvider })
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

    render(<AIProviderSettings />, { wrapper: LanguageProvider })
    await screen.findByLabelText('AI provider')

    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'sk-ant-new' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save & test connection' }))
    await screen.findByText('Connected successfully.')

    expect(screen.getByLabelText('API key')).toHaveValue('')
  })

  describe('providers saved earlier (docs/TASKS.md T162)', () => {
    const STATUS_WITH_TWO_SAVED = {
      ...STATUS_WITH_ANTHROPIC,
      ai_providers: [
        ...STATUS_WITH_ANTHROPIC.ai_providers,
        {
          id: 'p2',
          provider_id: 'openrouter',
          model: 'or/model',
          base_url: 'https://openrouter.ai/api/v1',
          credential_ref: 'openrouter:xyz',
          fallback_model: 'or/fallback',
          enabled: true,
          is_default: false,
        },
      ],
    }

    function stubFetch() {
      const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.endsWith('/onboarding/status')) {
          return Promise.resolve(jsonResponse(STATUS_WITH_TWO_SAVED))
        }
        if (url.endsWith('/onboarding/ai-provider')) {
          return Promise.resolve(jsonResponse({ onboarding_step: 'AI_PROVIDER' }))
        }
        return Promise.resolve(jsonResponse({ onboarding_step: 'VALIDATE', ok: true, reason: null }))
      })
      vi.stubGlobal('fetch', fetchMock)
      return fetchMock
    }

    it('restores a previously saved provider\'s own model, endpoint and fallback when switching back to it', async () => {
      stubFetch()
      render(<AIProviderSettings />, { wrapper: LanguageProvider })
      await screen.findByLabelText('AI provider')

      fireEvent.change(screen.getByLabelText('AI provider'), { target: { value: 'openrouter' } })

      expect(screen.getByLabelText('Model')).toHaveValue('or/model')
      expect(screen.getByLabelText('Endpoint URL')).toHaveValue('https://openrouter.ai/api/v1')
      expect(screen.getByLabelText('Fallback model (optional)')).toHaveValue('or/fallback')
    })

    it('does not require retyping the API key for a provider that already has one saved', async () => {
      stubFetch()
      render(<AIProviderSettings />, { wrapper: LanguageProvider })
      await screen.findByLabelText('AI provider')

      fireEvent.change(screen.getByLabelText('AI provider'), { target: { value: 'openrouter' } })

      expect(screen.getByLabelText('API key')).not.toBeRequired()
      expect(screen.getByText(/A key is already saved for this provider/)).toBeInTheDocument()
    })

    it('still requires an API key for a provider with nothing saved', async () => {
      stubFetch()
      render(<AIProviderSettings />, { wrapper: LanguageProvider })
      await screen.findByLabelText('AI provider')

      fireEvent.change(screen.getByLabelText('AI provider'), { target: { value: 'openai' } })

      expect(screen.getByLabelText('API key')).toBeRequired()
      expect(screen.queryByText(/A key is already saved/)).not.toBeInTheDocument()
    })

    it('validates with no credential when the saved key is being reused', async () => {
      const fetchMock = stubFetch()
      render(<AIProviderSettings />, { wrapper: LanguageProvider })
      await screen.findByLabelText('AI provider')

      fireEvent.change(screen.getByLabelText('AI provider'), { target: { value: 'openrouter' } })
      fireEvent.click(screen.getByRole('button', { name: 'Save & test connection' }))

      await screen.findByText('Connected successfully.')
      const call = fetchMock.mock.calls.find((args: unknown[]) =>
        String(args[0]).endsWith('/onboarding/ai-provider/validate'),
      )
      expect(JSON.parse((call![1]?.body as string) ?? '{}').credential).toBeNull()
    })
  })

  describe('Ollama installed models (docs/TASKS.md T163)', () => {
    function stubFetch(models: Response | Error) {
      const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/onboarding/ollama/models')) {
          return models instanceof Error ? Promise.reject(models) : Promise.resolve(models)
        }
        if (url.endsWith('/onboarding/status')) {
          return Promise.resolve(jsonResponse(STATUS_WITH_OLLAMA))
        }
        if (url.endsWith('/onboarding/ai-provider')) {
          return Promise.resolve(jsonResponse({ onboarding_step: 'AI_PROVIDER' }))
        }
        return Promise.resolve(jsonResponse({ onboarding_step: 'VALIDATE', ok: true, reason: null }))
      })
      vi.stubGlobal('fetch', fetchMock)
      return fetchMock
    }

    const optionNames = (select: HTMLElement) =>
      Array.from((select as HTMLSelectElement).options).map((o) => o.value)

    it('turns the model and fallback fields into dropdowns of the installed models', async () => {
      const fetchMock = stubFetch(jsonResponse({ models: ['llama3:latest', 'qwen3:8b'] }))
      render(<AIProviderSettings />, { wrapper: LanguageProvider })

      const model = await screen.findByRole('combobox', { name: 'Model' })

      expect(optionNames(model)).toEqual(['llama3:latest', 'qwen3:8b'])
      expect(optionNames(screen.getByLabelText('Fallback model (optional)'))).toEqual([
        '',
        'llama3:latest',
        'qwen3:8b',
      ])
      const asked = fetchMock.mock.calls.find((args: unknown[]) =>
        String(args[0]).includes('/onboarding/ollama/models'),
      )
      expect(String(asked![0])).toContain(encodeURIComponent('http://localhost:11434'))
    })

    it('keeps the saved model selected when Ollama lists it with a :latest tag', async () => {
      stubFetch(jsonResponse({ models: ['qwen3:8b', 'llama3:latest'] }))
      render(<AIProviderSettings />, { wrapper: LanguageProvider })

      await screen.findByRole('combobox', { name: 'Model' })

      expect(screen.getByLabelText('Model')).toHaveValue('llama3:latest')
    })

    it('snaps a model that is not installed to the first installed one', async () => {
      stubFetch(jsonResponse({ models: ['mistral:7b', 'qwen3:8b'] }))
      render(<AIProviderSettings />, { wrapper: LanguageProvider })

      await screen.findByRole('combobox', { name: 'Model' })

      expect(screen.getByLabelText('Model')).toHaveValue('mistral:7b')
    })

    it('saves the model and fallback picked from the dropdowns', async () => {
      const fetchMock = stubFetch(jsonResponse({ models: ['llama3:latest', 'qwen3:8b'] }))
      render(<AIProviderSettings />, { wrapper: LanguageProvider })
      await screen.findByRole('combobox', { name: 'Model' })

      fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'qwen3:8b' } })
      fireEvent.change(screen.getByLabelText('Fallback model (optional)'), {
        target: { value: 'llama3:latest' },
      })
      fireEvent.click(screen.getByRole('button', { name: 'Save & test connection' }))

      await screen.findByText('Connected successfully.')
      const call = fetchMock.mock.calls.find((args: unknown[]) =>
        String(args[0]).endsWith('/onboarding/ai-provider'),
      )
      const body = JSON.parse((call![1]?.body as string) ?? '{}')
      expect(body.model).toBe('qwen3:8b')
      expect(body.fallback_model).toBe('llama3:latest')
    })

    it('stays free-text, with a hint, when Ollama cannot be reached', async () => {
      stubFetch(new Error('network down'))
      render(<AIProviderSettings />, { wrapper: LanguageProvider })

      expect(await screen.findByText(/Could not list the models installed in Ollama/)).toBeInTheDocument()
      expect(screen.getByRole('textbox', { name: 'Model' })).toHaveValue('llama3')
    })

    it('stays free-text, with a hint, when Ollama has no models installed', async () => {
      stubFetch(jsonResponse({ models: [] }))
      render(<AIProviderSettings />, { wrapper: LanguageProvider })

      expect(await screen.findByText(/has no models installed/)).toBeInTheDocument()
      expect(screen.getByRole('textbox', { name: 'Model' })).toHaveValue('llama3')
    })

    it('does not ask Ollama for models when another provider is selected', async () => {
      const fetchMock = vi.fn().mockResolvedValue(jsonResponse(STATUS_WITH_ANTHROPIC))
      vi.stubGlobal('fetch', fetchMock)
      render(<AIProviderSettings />, { wrapper: LanguageProvider })
      await screen.findByLabelText('AI provider')

      await new Promise((resolve) => setTimeout(resolve, 600))

      expect(
        fetchMock.mock.calls.some((args: unknown[]) =>
          String(args[0]).includes('/onboarding/ollama/models'),
        ),
      ).toBe(false)
    })
  })

  it('shows an error message when the initial status fetch fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: { error: { code: 'UNKNOWN_ERROR', message: 'boom' } } }),
      }),
    )

    render(<AIProviderSettings />, { wrapper: LanguageProvider })

    expect(await screen.findByText('boom')).toBeInTheDocument()
  })
})
