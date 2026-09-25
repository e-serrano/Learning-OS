import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Dashboard } from './Dashboard'
import { LanguageProvider } from '../i18n/LanguageContext'

function jsonResponse(body: unknown) {
  return { ok: true, json: async () => body } as Response
}

const GOAL_1 = {
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
}

const ZERO_PROGRESS = {
  mastery: 0,
  concepts_total: 0,
  mastered: 0,
  weak: 0,
  due_reviews: 0,
  recent_sessions: 0,
}

function renderDashboard() {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
    { wrapper: LanguageProvider },
  )
}

describe('Dashboard', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the create-goal form when there are no goals yet', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ goals: [] })),
    )

    renderDashboard()

    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByLabelText('What do you want to learn?')).toBeInTheDocument()
    expect(screen.getByText("You're all caught up -- no reviews due.")).toBeInTheDocument()
  })

  it('renders a goal card with its mastery and due reviews', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.match(/\/goals\/[^/]+\/progress$/)) {
          return Promise.resolve(
            jsonResponse({ ...ZERO_PROGRESS, mastery: 0.5, concepts_total: 4, mastered: 1, weak: 1, due_reviews: 2 }),
          )
        }
        return Promise.resolve(jsonResponse({ goals: [GOAL_1] }))
      }),
    )

    renderDashboard()

    expect(await screen.findByText('Learn SQL')).toBeInTheDocument()
    expect(screen.getByText('50% mastery')).toBeInTheDocument()
    expect(screen.getByText('You have 2 reviews due.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Review now' })).toBeInTheDocument()
  })

  it('creates a goal and refreshes the list', async () => {
    let created = false
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (url.endsWith('/goals') && init?.method === 'POST') {
          created = true
          return Promise.resolve(jsonResponse(GOAL_1))
        }
        if (url.endsWith('/goals')) {
          return Promise.resolve(jsonResponse({ goals: created ? [GOAL_1] : [] }))
        }
        if (url.match(/\/goals\/[^/]+\/progress$/)) {
          return Promise.resolve(jsonResponse(ZERO_PROGRESS))
        }
        return Promise.reject(new Error(`unexpected fetch: ${url}`))
      }),
    )

    renderDashboard()

    const titleInput = await screen.findByLabelText('What do you want to learn?')
    fireEvent.change(titleInput, { target: { value: 'Learn SQL' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create goal' }))

    await waitFor(() => expect(screen.getByText('Learn SQL')).toBeInTheDocument())
  })
})
