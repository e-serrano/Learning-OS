import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SettingsView } from './SettingsView'

function jsonResponse(body: unknown) {
  return { ok: true, json: async () => body } as Response
}

const SETTINGS = {
  language: 'en',
  supported_languages: { en: 'English', es: 'Spanish', fr: 'French' },
}

describe('SettingsView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the current language once loaded', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SETTINGS)))

    render(<SettingsView />)

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

    render(<SettingsView />)
    await screen.findByLabelText('Language')

    fireEvent.change(screen.getByLabelText('Language'), { target: { value: 'es' } })

    expect(await screen.findByText('Saved.')).toBeInTheDocument()
    expect(screen.getByLabelText('Language')).toHaveValue('es')
  })

  it('shows an error message when loading fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: { error: { code: 'UNKNOWN_ERROR', message: 'boom' } } }),
      }),
    )

    render(<SettingsView />)

    expect(await screen.findByText('boom')).toBeInTheDocument()
  })
})
