import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { KnowledgeExplorer } from './KnowledgeExplorer'

function FakeAssessmentPage() {
  const { assessmentId } = useParams<{ assessmentId: string }>()
  return <p>assessment id: {assessmentId}</p>
}

function jsonResponse(body: unknown) {
  return { ok: true, json: async () => body } as Response
}

const CONCEPT_A = {
  id: 'a',
  title: 'Window Functions',
  domain: 'sql',
  status: 'weak',
  mastery: 1.5,
  confidence: 30,
  importance: 4,
  retention: 20,
  last_practiced: '2026-01-01T00:00:00Z',
  next_review: '2026-01-05T00:00:00Z',
  obsidian_path: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const CONCEPT_B = { ...CONCEPT_A, id: 'b', title: 'Subqueries', status: 'mastered', mastery: 5 }

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/goals/:goalId/knowledge" element={<KnowledgeExplorer />} />
        <Route path="/assessments/:assessmentId" element={<FakeAssessmentPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('KnowledgeExplorer', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('lists concepts with status and mastery', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ concepts: [CONCEPT_A, CONCEPT_B] })),
    )

    renderAt('/goals/goal_1/knowledge')

    expect(await screen.findByText('Window Functions')).toBeInTheDocument()
    expect(screen.getByText('Subqueries')).toBeInTheDocument()
  })

  it('shows an empty state when nothing matches the filter', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ concepts: [] })))

    renderAt('/goals/goal_1/knowledge')

    expect(await screen.findByText('No concepts match.')).toBeInTheDocument()
  })

  it('expands a concept to show stats and relations', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/relations')) {
          return Promise.resolve(
            jsonResponse({
              relations: [{ source_id: 'a', target_id: 'b', relation: 'RELATED_TO', weight: null }],
            }),
          )
        }
        return Promise.resolve(jsonResponse({ concepts: [CONCEPT_A, CONCEPT_B] }))
      }),
    )

    renderAt('/goals/goal_1/knowledge')

    const row = await screen.findByRole('button', { name: /Window Functions/ })
    fireEvent.click(row)

    expect(await screen.findByText('30% confidence')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText(/related to → Subqueries/)).toBeInTheDocument())
  })

  it('starts a transfer assessment and navigates to it', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (url.endsWith('/assessments') && init?.method === 'POST') {
          return Promise.resolve(
            jsonResponse({
              assessment_id: 'activity_1',
              session_id: 'session_1',
              goal_id: 'goal_1',
              concept_id: 'a',
              status: 'active',
              exercise: {
                exercise_id: 'exercise_1',
                type: 'scenario',
                difficulty: 3,
                prompt: 'p',
                success_criteria: [],
                hints: [],
              },
            }),
          )
        }
        return Promise.resolve(jsonResponse({ concepts: [CONCEPT_A, CONCEPT_B] }))
      }),
    )

    renderAt('/goals/goal_1/knowledge')

    const row = await screen.findByRole('button', { name: /Window Functions/ })
    fireEvent.click(row)
    fireEvent.click(await screen.findByRole('button', { name: 'Start transfer assessment' }))

    await waitFor(() =>
      expect(screen.getByText('assessment id: activity_1')).toBeInTheDocument(),
    )
  })

  it('refetches when the status filter changes', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ concepts: [CONCEPT_A] }))
    vi.stubGlobal('fetch', fetchMock)

    renderAt('/goals/goal_1/knowledge')
    await screen.findByText('Window Functions')

    fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'weak' } })

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/goals/goal_1/knowledge?status=weak'),
        expect.anything(),
      ),
    )
  })

  it('switching to graph view fetches relations for every concept and renders nodes', async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/concepts/a/relations')) {
        return Promise.resolve(
          jsonResponse({
            relations: [{ source_id: 'a', target_id: 'b', relation: 'PREREQUISITE_OF', weight: null }],
          }),
        )
      }
      if (url.includes('/relations')) {
        return Promise.resolve(jsonResponse({ relations: [] }))
      }
      return Promise.resolve(jsonResponse({ concepts: [CONCEPT_A, CONCEPT_B] }))
    })
    vi.stubGlobal('fetch', fetchMock)

    renderAt('/goals/goal_1/knowledge')
    await screen.findByText('Window Functions')

    fireEvent.click(screen.getByRole('button', { name: 'Graph' }))

    expect(await screen.findByRole('img', { name: 'Concept graph' })).toBeInTheDocument()
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/concepts/a/relations'),
        expect.anything(),
      ),
    )
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/concepts/b/relations'),
        expect.anything(),
      ),
    )
  })

  it('selecting a node in graph view shows its detail panel', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/relations')) {
          return Promise.resolve(jsonResponse({ relations: [] }))
        }
        return Promise.resolve(jsonResponse({ concepts: [CONCEPT_A, CONCEPT_B] }))
      }),
    )

    renderAt('/goals/goal_1/knowledge')
    await screen.findByText('Window Functions')
    fireEvent.click(screen.getByRole('button', { name: 'Graph' }))
    await screen.findByRole('img', { name: 'Concept graph' })

    fireEvent.click(screen.getByRole('button', { name: 'Window Functions' }))

    expect(await screen.findByText('30% confidence')).toBeInTheDocument()
  })
})
