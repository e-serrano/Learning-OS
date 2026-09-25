import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider } from '../i18n/LanguageContext'
import { ReviewsUI } from './ReviewsUI'

function jsonResponse(body: unknown) {
  return { ok: true, json: async () => body } as Response
}

const REVIEW_1 = {
  id: 'review_1',
  concept_id: 'window_functions',
  goal_id: 'goal_1',
  scheduled_at: '2026-01-01T00:00:00Z',
  completed_at: null,
  interval_days: 4,
  stability: null,
  difficulty: null,
  status: 'scheduled',
}

const REVIEW_2 = { ...REVIEW_1, id: 'review_2', concept_id: 'subqueries' }

describe('ReviewsUI', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the caught-up message when there are no reviews due', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ reviews: [] })))

    render(<ReviewsUI />, { wrapper: LanguageProvider })

    expect(
      await screen.findByText("You're all caught up -- no reviews due."),
    ).toBeInTheDocument()
  })

  it('shows the first due review and a progress count', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ reviews: [REVIEW_1, REVIEW_2] })),
    )

    render(<ReviewsUI />, { wrapper: LanguageProvider })

    expect(await screen.findByText('window_functions')).toBeInTheDocument()
    expect(screen.getByText('1 of 2')).toBeInTheDocument()
  })

  it('submits a review and advances to the next one', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (init?.method === 'POST' && url.includes('/complete')) {
          return Promise.resolve(
            jsonResponse({
              completed_review: { ...REVIEW_1, status: 'completed', completed_at: '2026-01-01T00:00:00Z' },
              next_review: { ...REVIEW_1, id: 'review_1_next', interval_days: 8 },
              concept: { concept_id: 'window_functions', mastery: 3, retention: 80, status: 'usable' },
            }),
          )
        }
        return Promise.resolve(jsonResponse({ reviews: [REVIEW_1, REVIEW_2] }))
      }),
    )

    render(<ReviewsUI />, { wrapper: LanguageProvider })
    await screen.findByText('window_functions')

    fireEvent.change(screen.getByLabelText('What do you recall?'), {
      target: { value: 'ROW_NUMBER assigns a unique rank per row.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Submit' }))

    expect(await screen.findByText('Next review in 8 days.')).toBeInTheDocument()
    expect(screen.getByText('80% retention')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Next review' }))
    await waitFor(() => expect(screen.getByText('subqueries')).toBeInTheDocument())
    expect(screen.getByText('2 of 2')).toBeInTheDocument()
  })

  it('shows Done as the button label on the last review', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (init?.method === 'POST' && url.includes('/complete')) {
          return Promise.resolve(
            jsonResponse({
              completed_review: { ...REVIEW_1, status: 'completed' },
              next_review: { ...REVIEW_1, id: 'review_1_next', interval_days: 1 },
              concept: { concept_id: 'window_functions', mastery: 2, retention: 60, status: 'developing' },
            }),
          )
        }
        return Promise.resolve(jsonResponse({ reviews: [REVIEW_1] }))
      }),
    )

    render(<ReviewsUI />, { wrapper: LanguageProvider })
    await screen.findByText('window_functions')

    fireEvent.change(screen.getByLabelText('What do you recall?'), { target: { value: 'x' } })
    fireEvent.click(screen.getByRole('button', { name: 'Submit' }))

    expect(await screen.findByRole('button', { name: 'Done' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Done' }))
    await waitFor(() =>
      expect(screen.getByText("You're all caught up -- no reviews due.")).toBeInTheDocument(),
    )
  })
})
