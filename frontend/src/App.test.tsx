import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

function mockStatusResponse(onboarding_step: string) {
  return {
    ok: true,
    json: async () => ({
      onboarding_step,
      vault_path: null,
      provider_id: null,
      model: null,
      language: 'en',
      ai_providers: [],
    }),
  }
}

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the vault step once onboarding status resolves to WELCOME', async () => {
    vi.mocked(fetch).mockResolvedValue(mockStatusResponse('WELCOME') as Response)

    render(<App />)

    expect(
      await screen.findByRole('heading', { name: 'Welcome to Learning OS' }),
    ).toBeInTheDocument()
  })

  it('shows a loading state before the status request resolves', () => {
    vi.mocked(fetch).mockReturnValue(new Promise(() => {}))

    render(<App />)

    expect(screen.getByText('Loading…')).toBeInTheDocument()
  })
})
