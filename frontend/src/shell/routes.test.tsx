import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AppRoutes } from './routes'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  )
}

describe('AppRoutes', () => {
  beforeEach(() => {
    // Dashboard (T111) fetches goals on mount even when the route under
    // test isn't "/" -- MemoryRouter still mounts the whole route tree.
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ goals: [] }) }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the dashboard at the root route', async () => {
    renderAt('/')

    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })

  it('renders the reviews placeholder at /reviews', () => {
    renderAt('/reviews')

    expect(screen.getByRole('heading', { name: 'Reviews' })).toBeInTheDocument()
  })

  it('renders the goal placeholder for a goal-scoped route', () => {
    renderAt('/goals/goal_1')

    expect(screen.getByRole('heading', { name: 'Goal' })).toBeInTheDocument()
  })

  it('redirects an unknown path back to the dashboard', async () => {
    renderAt('/does-not-exist')

    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })

  it('keeps the nav visible across routes', () => {
    renderAt('/vault')

    expect(screen.getByRole('link', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Vault Changes' })).toBeInTheDocument()
  })
})
