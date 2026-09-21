import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AssessmentUI } from './AssessmentUI'

function jsonResponse(body: unknown) {
  return { ok: true, json: async () => body } as Response
}

const ASSESSMENT = {
  assessment_id: 'activity_1',
  session_id: 'session_1',
  goal_id: 'goal_1',
  concept_id: 'window_functions',
  status: 'active',
  exercise: {
    exercise_id: 'exercise_1',
    type: 'scenario',
    difficulty: 4,
    prompt: 'Apply window functions to a new dataset.',
    success_criteria: ['Uses RANK() correctly'],
    hints: ['Think about ties'],
  },
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/assessments/:assessmentId" element={<AssessmentUI />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AssessmentUI', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('loads the assessment and shows the exercise prompt', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(ASSESSMENT)))

    renderAt('/assessments/activity_1')

    expect(
      await screen.findByText('Apply window functions to a new dataset.'),
    ).toBeInTheDocument()
    expect(screen.getByText('Uses RANK() correctly')).toBeInTheDocument()
  })

  it('submits an answer and shows transfer/independence badges', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.endsWith('/answer')) {
          return Promise.resolve(
            jsonResponse({
              evaluation: {
                correctness: 0.9,
                reasoning: 0.8,
                independence: 0.7,
                transfer: 0.8,
                feedback: 'Transferred well.',
                misconceptions: [],
              },
              transfer_demonstrated: true,
              independence_demonstrated: true,
              updated_concepts: [{ concept_id: 'window_functions', mastery: 3, status: 'usable' }],
            }),
          )
        }
        return Promise.resolve(jsonResponse(ASSESSMENT))
      }),
    )

    renderAt('/assessments/activity_1')
    await screen.findByText('Apply window functions to a new dataset.')

    fireEvent.change(screen.getByLabelText('Your answer'), {
      target: { value: 'SELECT RANK() OVER (...) FROM shipments;' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Submit answer' }))

    expect(await screen.findByText('Transfer demonstrated')).toBeInTheDocument()
    expect(screen.getByText('Independence demonstrated')).toBeInTheDocument()
    expect(screen.getByText('Transferred well.')).toBeInTheDocument()
  })

  it('completes the assessment after answering', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.endsWith('/answer')) {
          return Promise.resolve(
            jsonResponse({
              evaluation: {
                correctness: 0.3,
                reasoning: 0.3,
                independence: 0.2,
                transfer: 0.2,
                feedback: 'Needs more practice.',
                misconceptions: ['Missed the PARTITION BY clause'],
              },
              transfer_demonstrated: false,
              independence_demonstrated: false,
              updated_concepts: [],
            }),
          )
        }
        if (url.endsWith('/complete')) {
          return Promise.resolve(jsonResponse({ session_id: 'session_1', status: 'completed' }))
        }
        return Promise.resolve(jsonResponse(ASSESSMENT))
      }),
    )

    renderAt('/assessments/activity_1')
    await screen.findByText('Apply window functions to a new dataset.')

    fireEvent.change(screen.getByLabelText('Your answer'), { target: { value: 'x' } })
    fireEvent.click(screen.getByRole('button', { name: 'Submit answer' }))

    expect(await screen.findByText('Missed the PARTITION BY clause')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Complete assessment' }))

    await waitFor(() => expect(screen.getByText('Assessment complete')).toBeInTheDocument())
  })
})
