import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider } from './LanguageContext'
import { LanguageToggle } from './LanguageToggle'

function jsonResponse(body: unknown) {
  return { ok: true, json: async () => body } as Response
}

function settingsResponse(language: string) {
  return jsonResponse({
    language,
    supported_languages: { en: 'English', es: 'Spanish' },
    git_auto_commit: false,
    git_available: false,
  })
}

describe('LanguageToggle', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the Spanish flag (the language a click switches TO) while English is active', () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => {})))

    render(
      <LanguageProvider>
        <LanguageToggle />
      </LanguageProvider>,
    )

    const button = screen.getByRole('button', { name: 'Switch to Spanish' })
    expect(button).toHaveTextContent('🇪🇸')
  })

  it('shows the British flag (switch back to English) once Spanish is active', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(settingsResponse('es')))

    render(
      <LanguageProvider>
        <LanguageToggle />
      </LanguageProvider>,
    )

    const button = await screen.findByRole('button', { name: 'Cambiar a inglés' })
    expect(button).toHaveTextContent('🇬🇧')
  })

  it('clicking it persists the switch via PATCH /settings/language', async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/settings/language') && init?.method === 'PATCH') {
        return Promise.resolve(settingsResponse('es'))
      }
      return Promise.resolve(settingsResponse('en'))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(
      <LanguageProvider>
        <LanguageToggle />
      </LanguageProvider>,
    )
    await screen.findByRole('button', { name: 'Switch to Spanish' })

    fireEvent.click(screen.getByRole('button', { name: 'Switch to Spanish' }))

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/settings/language'),
        expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ language: 'es' }) }),
      ),
    )
    expect(await screen.findByRole('button', { name: 'Cambiar a inglés' })).toBeInTheDocument()
  })
})
