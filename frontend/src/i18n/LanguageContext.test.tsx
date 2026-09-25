import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider, useTranslation } from './LanguageContext'

function jsonResponse(body: unknown) {
  return { ok: true, json: async () => body } as Response
}

function Consumer() {
  const { language, setLanguage, t } = useTranslation()
  return (
    <div>
      <span data-testid="language">{language}</span>
      <span data-testid="translated">{t('nav.settings')}</span>
      <span data-testid="missing-key">{t('does.not.exist')}</span>
      <button type="button" onClick={() => setLanguage(language === 'en' ? 'es' : 'en')}>
        toggle
      </button>
    </div>
  )
}

describe('LanguageProvider', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('throws when useTranslation is called outside a LanguageProvider', () => {
    // Swallow the expected console.error React logs for the thrown render error.
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<Consumer />)).toThrow('useTranslation must be used within a LanguageProvider')
    spy.mockRestore()
  })

  it('starts as English before GET /settings resolves', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockReturnValue(new Promise(() => {})), // never resolves
    )

    render(
      <LanguageProvider>
        <Consumer />
      </LanguageProvider>,
    )

    expect(screen.getByTestId('language')).toHaveTextContent('en')
    expect(screen.getByTestId('translated')).toHaveTextContent('Settings')
  })

  it('upgrades to the backend-configured language once GET /settings resolves', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          language: 'es',
          supported_languages: { en: 'English', es: 'Spanish' },
          git_auto_commit: false,
          git_available: false,
        }),
      ),
    )

    render(
      <LanguageProvider>
        <Consumer />
      </LanguageProvider>,
    )

    await waitFor(() => expect(screen.getByTestId('language')).toHaveTextContent('es'))
    expect(screen.getByTestId('translated')).toHaveTextContent('Ajustes')
  })

  it('ignores an unsupported stored language and stays on the default', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          language: 'fr',
          supported_languages: { en: 'English', es: 'Spanish', fr: 'French' },
          git_auto_commit: false,
          git_available: false,
        }),
      ),
    )

    render(
      <LanguageProvider>
        <Consumer />
      </LanguageProvider>,
    )
    await screen.findByTestId('language')

    // give the fetch a tick to resolve without ever seeing 'fr' applied
    await new Promise((r) => setTimeout(r, 0))
    expect(screen.getByTestId('language')).toHaveTextContent('en')
  })

  it('stays on the default when the settings fetch fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))

    render(
      <LanguageProvider>
        <Consumer />
      </LanguageProvider>,
    )

    await new Promise((r) => setTimeout(r, 0))
    expect(screen.getByTestId('language')).toHaveTextContent('en')
  })

  it('falls back to the key itself for a missing translation', () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => {})))

    render(
      <LanguageProvider>
        <Consumer />
      </LanguageProvider>,
    )

    expect(screen.getByTestId('missing-key')).toHaveTextContent('does.not.exist')
  })

  it('updates optimistically and persists via PATCH /settings/language', async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/settings/language') && init?.method === 'PATCH') {
        return Promise.resolve(
          jsonResponse({
            language: 'es',
            supported_languages: { en: 'English', es: 'Spanish' },
            git_auto_commit: false,
            git_available: false,
          }),
        )
      }
      return Promise.resolve(
        jsonResponse({
          language: 'en',
          supported_languages: { en: 'English', es: 'Spanish' },
          git_auto_commit: false,
          git_available: false,
        }),
      )
    })
    vi.stubGlobal('fetch', fetchMock)

    render(
      <LanguageProvider>
        <Consumer />
      </LanguageProvider>,
    )
    await screen.findByTestId('language')

    fireEvent.click(screen.getByRole('button', { name: 'toggle' }))

    // optimistic: flips before the PATCH settles
    expect(screen.getByTestId('language')).toHaveTextContent('es')

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/settings/language'),
        expect.objectContaining({ method: 'PATCH' }),
      ),
    )
  })
})
