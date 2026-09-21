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
    // Dashboard (T111) and GoalView (T112) fetch on mount regardless of
    // which route is under test -- react-router still mounts <AppShell>.
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.match(/\/goals\/[^/]+\/progress$/)) {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              mastery: 0,
              concepts_total: 0,
              mastered: 0,
              weak: 0,
              due_reviews: 0,
              recent_sessions: 0,
            }),
          })
        }
        if (url.match(/\/goals\/[^/]+\/projects$/)) {
          return Promise.resolve({ ok: true, json: async () => ({ projects: [] }) })
        }
        if (url.match(/\/goals\/[^/]+$/)) {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              id: 'goal_1',
              title: 'Learn SQL',
              description: null,
              domain: null,
              target_level: 'professional',
              status: 'active',
              priority: 3,
              deadline: null,
              available_minutes_per_week: null,
              created_at: '2026-01-01T00:00:00Z',
              updated_at: '2026-01-01T00:00:00Z',
            }),
          })
        }
        if (url.match(/\/reviews\/today$/)) {
          return Promise.resolve({ ok: true, json: async () => ({ reviews: [] }) })
        }
        if (url.match(/\/vault\/changes$/)) {
          return Promise.resolve({ ok: true, json: async () => ({ changes: [] }) })
        }
        return Promise.resolve({ ok: true, json: async () => ({ goals: [] }) })
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the dashboard at the root route', async () => {
    renderAt('/')

    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })

  it('renders the reviews UI at /reviews', async () => {
    renderAt('/reviews')

    expect(await screen.findByRole('heading', { name: 'Reviews' })).toBeInTheDocument()
  })

  it('renders the goal view for a goal-scoped route', async () => {
    renderAt('/goals/goal_1')

    expect(await screen.findByRole('heading', { name: 'Learn SQL' })).toBeInTheDocument()
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
