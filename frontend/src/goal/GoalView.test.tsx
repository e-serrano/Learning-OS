import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { GoalView } from './GoalView'
import { LanguageProvider } from '../i18n/LanguageContext'

function FakeSessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  return <p>session id: {sessionId}</p>
}

function FakeProjectPage() {
  const { projectId } = useParams<{ projectId: string }>()
  return <p>project id: {projectId}</p>
}

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
        <Route path="/sessions/:sessionId" element={<FakeSessionPage />} />
        <Route path="/projects/:projectId" element={<FakeProjectPage />} />
      </Routes>
    </MemoryRouter>,
    { wrapper: LanguageProvider },
  )
}

function mockFetchFor(
  goal: typeof ACTIVE_GOAL,
  progress: typeof PROGRESS,
  extra?: { concepts?: unknown[]; onCreateProject?: () => unknown; projects?: unknown[] },
) {
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
      if (url.match(/\/goals\/[^/]+\/sessions$/) && init?.method === 'POST') {
        const body = JSON.parse((init.body as string) ?? '{}')
        return Promise.resolve(
          jsonResponse({
            id: 'session_1',
            goal_id: goal.id,
            mode: body.mode ?? 'guided',
            objective: 'Practice',
            status: 'active',
            started_at: '2026-01-01T00:00:00Z',
            ended_at: null,
          }),
        )
      }
      if (url.match(/\/goals\/[^/]+\/projects$/) && init?.method === 'POST') {
        return Promise.resolve(jsonResponse(extra?.onCreateProject?.() ?? {}))
      }
      if (url.match(/\/goals\/[^/]+\/projects$/)) {
        return Promise.resolve(jsonResponse({ projects: extra?.projects ?? [] }))
      }
      if (url.match(/\/goals\/[^/]+\/knowledge$/)) {
        return Promise.resolve(jsonResponse({ concepts: extra?.concepts ?? [] }))
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

  it('starts a session and navigates to it', async () => {
    mockFetchFor(ACTIVE_GOAL, PROGRESS)

    renderGoalView()

    await screen.findByRole('heading', { name: 'Learn SQL' })
    fireEvent.click(screen.getByRole('button', { name: 'Start session' }))

    await waitFor(() => expect(screen.getByText('session id: session_1')).toBeInTheDocument())
  })

  it('starts a session in the selected mode', async () => {
    mockFetchFor(ACTIVE_GOAL, PROGRESS)

    renderGoalView()

    await screen.findByRole('heading', { name: 'Learn SQL' })
    fireEvent.change(screen.getByLabelText('Session mode'), { target: { value: 'socratic' } })
    fireEvent.click(screen.getByRole('button', { name: 'Start session' }))

    await waitFor(() => expect(screen.getByText('session id: session_1')).toBeInTheDocument())
    const sessionCall = vi
      .mocked(fetch)
      .mock.calls.find(([input]) => String(input).match(/\/goals\/[^/]+\/sessions$/))
    expect(sessionCall).toBeDefined()
    expect(JSON.parse((sessionCall![1]?.body as string) ?? '{}').mode).toBe('socratic')
  })

  it('lists existing projects for the goal', async () => {
    mockFetchFor(ACTIVE_GOAL, PROGRESS, {
      projects: [
        {
          id: 'project_1',
          goal_id: 'goal_1',
          title: 'Build an ETL pipeline',
          objective: 'obj',
          difficulty: 3,
          status: 'active',
          concept_ids: ['window_functions'],
          success_criteria: [],
          artifact_path: null,
        },
      ],
    })

    renderGoalView()

    expect(await screen.findByRole('link', { name: 'Build an ETL pipeline' })).toHaveAttribute(
      'href',
      '/projects/project_1',
    )
  })

  it('starts a project using the goal concepts and navigates to it', async () => {
    mockFetchFor(ACTIVE_GOAL, PROGRESS, {
      concepts: [{ id: 'window_functions' }],
      onCreateProject: () => ({
        project: {
          id: 'project_1',
          goal_id: 'goal_1',
          title: 'Build an ETL pipeline',
          objective: 'obj',
          difficulty: 3,
          status: 'active',
          concept_ids: ['window_functions'],
          success_criteria: ['Uses a window function'],
          artifact_path: null,
        },
        session_id: 'session_1',
        tasks: [{ task_id: 'task_1', sequence: 1, description: 'Uses a window function', status: 'pending' }],
      }),
    })

    renderGoalView()

    await screen.findByRole('heading', { name: 'Learn SQL' })
    fireEvent.click(screen.getByRole('button', { name: 'Start project' }))

    await waitFor(() => expect(screen.getByText('project id: project_1')).toBeInTheDocument())
  })
})
