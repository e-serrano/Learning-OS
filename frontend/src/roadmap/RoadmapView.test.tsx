import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { RoadmapView } from './RoadmapView'

function jsonResponse(body: unknown, ok = true) {
  return { ok, json: async () => body } as Response
}

function errorResponse(code: string, message: string, status = 404) {
  return {
    ok: false,
    status,
    json: async () => ({ detail: { error: { code, message, details: {} } } }),
  } as Response
}

const ROADMAP = {
  id: 'roadmap_1',
  goal_id: 'goal_1',
  version: 2,
  status: 'active',
  nodes: [
    { id: 'a', title: 'Window Functions', domain: 'sql', status: 'learning', mastery: 2.5, confidence: 40, importance: 4 },
    { id: 'b', title: 'Subqueries', domain: 'sql', status: 'mastered', mastery: 5, confidence: 90, importance: 3 },
  ],
  edges: [{ source_id: 'b', target_id: 'a', relation: 'PREREQUISITE_OF' }],
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/goals/:goalId/roadmap" element={<RoadmapView />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('RoadmapView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders nodes with mastery and derived prerequisites', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(ROADMAP)))

    renderAt('/goals/goal_1/roadmap')

    expect(await screen.findByText('Window Functions')).toBeInTheDocument()
    expect(screen.getByText('Subqueries')).toBeInTheDocument()
    expect(screen.getByText('50% mastery')).toBeInTheDocument()
    expect(screen.getByText('Requires: Subqueries')).toBeInTheDocument()
    expect(screen.getByText('v2')).toBeInTheDocument()
  })

  it('shows a generate CTA when no roadmap exists yet', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(errorResponse('NOT_FOUND', "No roadmap generated yet for goal 'goal_1'")),
    )

    renderAt('/goals/goal_1/roadmap')

    expect(
      await screen.findByText('No roadmap has been generated for this goal yet.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate roadmap' })).toBeInTheDocument()
  })

  it('generates a roadmap and then shows its nodes', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((_input: RequestInfo | URL, init?: RequestInit) => {
        if (init?.method === 'POST') {
          return Promise.resolve(jsonResponse(ROADMAP))
        }
        return Promise.resolve(errorResponse('NOT_FOUND', 'not found'))
      }),
    )

    renderAt('/goals/goal_1/roadmap')

    const generateButton = await screen.findByRole('button', { name: 'Generate roadmap' })
    fireEvent.click(generateButton)

    await waitFor(() => expect(screen.getByText('Window Functions')).toBeInTheDocument())
  })
})
