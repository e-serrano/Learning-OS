import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { KnowledgeExplorer } from './KnowledgeExplorer'

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
})
