import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SessionUI } from './SessionUI'

function jsonResponse(body: unknown, ok = true, status = 200) {
  return { ok, status, json: async () => body } as Response
}

function errorResponse(code: string, message: string, status: number) {
  return {
    ok: false,
    status,
    json: async () => ({ detail: { error: { code, message, details: {} } } }),
  } as Response
}

const SESSION = {
  id: 'session_1',
  goal_id: 'goal_1',
  mode: 'guided',
  objective: 'Practice',
  status: 'active',
  started_at: '2026-01-01T00:00:00Z',
  ended_at: null,
}

const ACTIVITY_1 = {
  activity_id: 'activity_1',
  type: 'exercise',
  content: {
    exercise_id: 'exercise_1',
    type: 'sql',
    difficulty: 3,
    prompt: 'Write a query using ROW_NUMBER().',
    success_criteria: ['Uses ROW_NUMBER()'],
    hints: ['Think about ordering'],
  },
}

const ACTIVITY_2 = {
  activity_id: 'activity_2',
  type: 'exercise',
  content: {
    exercise_id: 'exercise_2',
    type: 'sql',
    difficulty: 3,
    prompt: 'Write a query using RANK().',
    success_criteria: [],
    hints: [],
  },
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/sessions/:sessionId" element={<SessionUI />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('SessionUI', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('loads the session and shows the first activity', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.endsWith('/next')) return Promise.resolve(jsonResponse(ACTIVITY_1))
        return Promise.resolve(jsonResponse(SESSION))
      }),
    )

    renderAt('/sessions/session_1')

    expect(await screen.findByText('Write a query using ROW_NUMBER().')).toBeInTheDocument()
    expect(screen.getByText('Uses ROW_NUMBER()')).toBeInTheDocument()
  })

  it('reveals hints on demand', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.endsWith('/next')) return Promise.resolve(jsonResponse(ACTIVITY_1))
        return Promise.resolve(jsonResponse(SESSION))
      }),
    )

    renderAt('/sessions/session_1')
    await screen.findByText('Write a query using ROW_NUMBER().')

    expect(screen.queryByText('Think about ordering')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Show hints' }))
    expect(screen.getByText('Think about ordering')).toBeInTheDocument()
  })

  it('submits an answer and shows evaluation with a continue button', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.endsWith('/next')) return Promise.resolve(jsonResponse(ACTIVITY_1))
        if (url.endsWith('/answer')) {
          return Promise.resolve(
            jsonResponse({
              evaluation: {
                id: 'eval_1',
                correctness: 0.9,
                reasoning: 0.8,
                completeness: 0.85,
                independence: 0.7,
                transfer: 0.6,
                misconceptions: [],
                feedback: 'Good job.',
                recommended_action: 'advance',
              },
              knowledge_updates: [
                {
                  concept_id: 'window_functions',
                  mastery: 3,
                  status: 'usable',
                  mistakes_recorded: 0,
                  next_review_scheduled_at: '2026-01-05T00:00:00Z',
                },
              ],
              next_activity: ACTIVITY_2,
            }),
          )
        }
        return Promise.resolve(jsonResponse(SESSION))
      }),
    )

    renderAt('/sessions/session_1')
    await screen.findByText('Write a query using ROW_NUMBER().')

    fireEvent.change(screen.getByLabelText('Your answer'), {
      target: { value: 'SELECT ROW_NUMBER() OVER (ORDER BY id) FROM t;' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Submit answer' }))

    expect(await screen.findByText('Good job.')).toBeInTheDocument()
    expect(screen.getByText('90%')).toBeInTheDocument()
    expect(screen.getByText('window_functions: usable')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
    await waitFor(() =>
      expect(screen.getByText('Write a query using RANK().')).toBeInTheDocument(),
    )
  })

  it('shows finish session when there is no next activity', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.endsWith('/next')) return Promise.resolve(jsonResponse(ACTIVITY_1))
        if (url.endsWith('/answer')) {
          return Promise.resolve(
            jsonResponse({
              evaluation: {
                id: 'eval_1',
                correctness: 0.5,
                reasoning: 0.5,
                completeness: 0.5,
                independence: 0.5,
                transfer: 0.5,
                misconceptions: ['Forgot the ORDER BY clause'],
                feedback: 'Close.',
                recommended_action: 'retry',
              },
              knowledge_updates: [],
              next_activity: null,
            }),
          )
        }
        if (url.endsWith('/complete')) {
          return Promise.resolve(jsonResponse({ ...SESSION, status: 'completed' }))
        }
        return Promise.resolve(jsonResponse(SESSION))
      }),
    )

    renderAt('/sessions/session_1')
    await screen.findByText('Write a query using ROW_NUMBER().')

    fireEvent.change(screen.getByLabelText('Your answer'), { target: { value: 'x' } })
    fireEvent.click(screen.getByRole('button', { name: 'Submit answer' }))

    expect(await screen.findByText('Forgot the ORDER BY clause')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Finish session' }))

    await waitFor(() => expect(screen.getByText('Session complete')).toBeInTheDocument())
  })

  it('shows a no-candidates message when the goal has nothing to work on', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.endsWith('/next')) {
          return Promise.resolve(
            errorResponse('SESSION_STATE_ERROR', 'No activity candidates for this goal', 409),
          )
        }
        return Promise.resolve(jsonResponse(SESSION))
      }),
    )

    renderAt('/sessions/session_1')

    expect(await screen.findByText('Nothing to work on yet')).toBeInTheDocument()
  })

  it('shows session complete immediately for an already-completed session', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ ...SESSION, status: 'completed' })),
    )

    renderAt('/sessions/session_1')

    expect(await screen.findByText('Session complete')).toBeInTheDocument()
  })
})
