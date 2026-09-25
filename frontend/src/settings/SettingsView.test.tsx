import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider } from '../i18n/LanguageContext'
import { SettingsView } from './SettingsView'

function jsonResponse(body: unknown) {
  return { ok: true, json: async () => body } as Response
}

const SETTINGS = {
  language: 'en',
  supported_languages: { en: 'English', es: 'Spanish', fr: 'French' },
  git_auto_commit: false,
  git_available: true,
}

describe('SettingsView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the current language once loaded', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SETTINGS)))

    render(<SettingsView />, { wrapper: LanguageProvider })

    expect(await screen.findByLabelText('Language')).toHaveValue('en')
    expect(screen.getByRole('option', { name: 'Spanish' })).toBeInTheDocument()
  })

  it('saves the selected language and confirms', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((_input: RequestInfo | URL, init?: RequestInit) => {
        if (init?.method === 'PATCH') {
          return Promise.resolve(jsonResponse({ ...SETTINGS, language: 'es' }))
        }
        return Promise.resolve(jsonResponse(SETTINGS))
      }),
    )

    render(<SettingsView />, { wrapper: LanguageProvider })
    await screen.findByLabelText('Language')

    fireEvent.change(screen.getByLabelText('Language'), { target: { value: 'es' } })

    // The confirmation itself renders in the just-selected language --
    // switching to Spanish flips the whole UI immediately, this message
    // included (docs/TASKS.md T147).
    expect(await screen.findByText('Guardado.')).toBeInTheDocument()
    expect(screen.getByLabelText('Idioma')).toHaveValue('es')
  })

  it('shows an error message when loading fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: { error: { code: 'UNKNOWN_ERROR', message: 'boom' } } }),
      }),
    )

    render(<SettingsView />, { wrapper: LanguageProvider })

    expect(await screen.findByText('boom')).toBeInTheDocument()
  })

  it('enables the git auto-commit checkbox when the vault is a git repo', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SETTINGS)))

    render(<SettingsView />, { wrapper: LanguageProvider })

    const checkbox = await screen.findByLabelText('Git auto-commit')
    expect(checkbox).not.toBeChecked()
    expect(checkbox).toBeEnabled()
  })

  it('disables the git auto-commit checkbox when the vault is not a git repo', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ ...SETTINGS, git_available: false })),
    )

    render(<SettingsView />, { wrapper: LanguageProvider })

    expect(await screen.findByLabelText('Git auto-commit')).toBeDisabled()
    expect(screen.getByText('Your configured vault is not a git repository, so this is unavailable.')).toBeInTheDocument()
  })

  it('toggles git auto-commit and confirms', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((_input: RequestInfo | URL, init?: RequestInit) => {
        if (init?.method === 'PATCH') {
          return Promise.resolve(jsonResponse({ ...SETTINGS, git_auto_commit: true }))
        }
        return Promise.resolve(jsonResponse(SETTINGS))
      }),
    )

    render(<SettingsView />, { wrapper: LanguageProvider })
    const checkbox = await screen.findByLabelText('Git auto-commit')

    fireEvent.click(checkbox)

    expect(await screen.findByText('Saved.')).toBeInTheDocument()
    expect(checkbox).toBeChecked()
  })
})
