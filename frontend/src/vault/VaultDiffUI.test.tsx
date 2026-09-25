import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider } from '../i18n/LanguageContext'
import { VaultDiffUI } from './VaultDiffUI'

function jsonResponse(body: unknown) {
  return { ok: true, json: async () => body } as Response
}

const PENDING_CHANGE = {
  id: 'change_1',
  path: 'Concepts/Window Functions.md',
  operation: 'replace_managed_section',
  section: 'Summary',
  content: 'Window functions compute a value across a set of rows.',
  status: 'pending',
  error: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  applied_at: null,
}

describe('VaultDiffUI', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows a no-pending-changes message when the list is empty', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ changes: [] })))

    render(<VaultDiffUI />, { wrapper: LanguageProvider })

    expect(await screen.findByText('No pending changes.')).toBeInTheDocument()
  })

  it('expands a change to show before/after content', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ changes: [PENDING_CHANGE] })),
    )

    render(<VaultDiffUI />, { wrapper: LanguageProvider })

    const row = await screen.findByRole('button', { name: /Window Functions.md/ })
    fireEvent.click(row)

    expect(screen.getByText('(current content not available via this API)')).toBeInTheDocument()
    expect(
      screen.getByText('Window functions compute a value across a set of rows.'),
    ).toBeInTheDocument()
  })

  it('shows "(new file)" as before for a create_file operation', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({ changes: [{ ...PENDING_CHANGE, operation: 'create_file', section: null }] }),
      ),
    )

    render(<VaultDiffUI />, { wrapper: LanguageProvider })

    fireEvent.click(await screen.findByRole('button', { name: /Window Functions.md/ }))

    expect(screen.getByText('(new file)')).toBeInTheDocument()
  })

  it('approves a change and shows the updated status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (url.endsWith('/apply') && init?.method === 'POST') {
          return Promise.resolve(
            jsonResponse({ ...PENDING_CHANGE, status: 'applied', applied_at: '2026-01-02T00:00:00Z' }),
          )
        }
        return Promise.resolve(jsonResponse({ changes: [PENDING_CHANGE] }))
      }),
    )

    render(<VaultDiffUI />, { wrapper: LanguageProvider })

    fireEvent.click(await screen.findByRole('button', { name: /Window Functions.md/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))

    await waitFor(() => expect(screen.getByText('applied')).toBeInTheDocument())
  })

  it('rejects a change and shows the updated status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (url.endsWith('/reject') && init?.method === 'POST') {
          return Promise.resolve(jsonResponse({ ...PENDING_CHANGE, status: 'rejected' }))
        }
        return Promise.resolve(jsonResponse({ changes: [PENDING_CHANGE] }))
      }),
    )

    render(<VaultDiffUI />, { wrapper: LanguageProvider })

    fireEvent.click(await screen.findByRole('button', { name: /Window Functions.md/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Reject' }))

    await waitFor(() => expect(screen.getByText('rejected')).toBeInTheDocument())
  })

  it('rescans the vault and shows a summary', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (url.endsWith('/vault/scan') && init?.method === 'POST') {
          return Promise.resolve(
            jsonResponse({ files_scanned: 12, managed_files: 5, changed_files: 2, errors: [] }),
          )
        }
        return Promise.resolve(jsonResponse({ changes: [] }))
      }),
    )

    render(<VaultDiffUI />, { wrapper: LanguageProvider })
    await screen.findByText('No pending changes.')

    fireEvent.click(screen.getByRole('button', { name: 'Rescan vault' }))

    expect(
      await screen.findByText('Scanned 12 files -- 2 changed, 0 error(s).'),
    ).toBeInTheDocument()
  })
})
