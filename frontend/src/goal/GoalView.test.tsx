import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { GoalView } from './GoalView'

function jsonResponse(body: unknown) {
  return { ok: true, json: async () => body } as Response
}

const ACTIVE_GOAL = {
  id: 'goal_1',
  title: 'Learn SQL',
  description: 'Get comfortable with window functions.',
  domain: null,
  target_level: 'professional',
  status: 'active',
  priority: 3,
  deadline: null,
  available_minutes_per_week: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const PROGRESS = {
  mastery: 0.75,
  concepts_total: 8,
  mastered: 3,
  weak: 1,
  due_reviews: 4,
  recent_sessions: 2,
}

function renderGoalView() {
  return render(
    <MemoryRouter initialEntries={['/goals/goal_1']}>
      <Routes>
        <Route path="/goals/:goalId" element={<GoalView />} />
      </Routes>
    </MemoryRouter>,
  )
}

function mockFetchFor(goal: typeof ACTIVE_GOAL, progress: typeof PROGRESS) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.match(/\/goals\/[^/]+\/pause$/)) {
        return Promise.resolve(jsonResponse({ ...goal, status: 'paused' }))
      }
      if (url.match(/\/goals\/[^/]+\/complete$/)) {
        return Promise.resolve(jsonResponse({ ...goal, status: 'completed' }))
      }
      if (url.match(/\/goals\/[^/]+\/progress$/)) {
        return Promise.resolve(jsonResponse(progress))
      }
      if (url.match(/\/goals\/[^/]+$/)) {
        return Promise.resolve(jsonResponse(goal))
      }
      return Promise.reject(new Error(`unexpected fetch: ${url} ${init?.method ?? 'GET'}`))
    }),
  )
}

describe('GoalView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the goal title, mastery, and stats', async () => {
    mockFetchFor(ACTIVE_GOAL, PROGRESS)

    renderGoalView()

    expect(await screen.findByRole('heading', { name: 'Learn SQL' })).toBeInTheDocument()
    expect(screen.getByText('Get comfortable with window functions.')).toBeInTheDocument()
    expect(screen.getByText('75% mastery')).toBeInTheDocument()
    expect(screen.getByText('8')).toBeInTheDocument()
    expect(screen.getByText('weak')).toBeInTheDocument()
  })

  it('links to the roadmap and knowledge explorer', async () => {
    mockFetchFor(ACTIVE_GOAL, PROGRESS)

    renderGoalView()

    await screen.findByRole('heading', { name: 'Learn SQL' })
    expect(screen.getByRole('link', { name: 'Roadmap' })).toHaveAttribute(
      'href',
      '/goals/goal_1/roadmap',
    )
    expect(screen.getByRole('link', { name: 'Knowledge explorer' })).toHaveAttribute(
      'href',
      '/goals/goal_1/knowledge',
    )
  })

  it('shows pause/complete actions for an active goal and pausing updates the status tag', async () => {
    mockFetchFor(ACTIVE_GOAL, PROGRESS)

    renderGoalView()

    await screen.findByRole('heading', { name: 'Learn SQL' })
    fireEvent.click(screen.getByRole('button', { name: 'Pause goal' }))

    await waitFor(() => expect(screen.getByText('paused')).toBeInTheDocument())
  })

  it('hides lifecycle actions for a non-active goal', async () => {
    mockFetchFor({ ...ACTIVE_GOAL, status: 'draft' }, PROGRESS)

    renderGoalView()

    await screen.findByRole('heading', { name: 'Learn SQL' })
    expect(screen.queryByRole('button', { name: 'Pause goal' })).not.toBeInTheDocument()
  })
})
