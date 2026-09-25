import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider } from '../i18n/LanguageContext'
import { TutorChat } from './TutorChat'

function jsonResponse(body: unknown) {
  return { ok: true, json: async () => body } as Response
}

const CONCEPTS = {
  concepts: [
    { id: 'concept_1', title: 'Window Functions' },
    { id: 'concept_2', title: 'Subqueries' },
  ],
}

const OPENING_TURN = {
  mode: 'question',
  content: 'What is a window function?',
  check_for_understanding: null,
  next_activity: null,
}

describe('TutorChat', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('loads concepts and shows the tutor opening question', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/knowledge')) return Promise.resolve(jsonResponse(CONCEPTS))
        return Promise.resolve(jsonResponse(OPENING_TURN))
      }),
    )

    render(<TutorChat sessionId="session_1" goalId="goal_1" onEnd={vi.fn()} />, {
      wrapper: LanguageProvider,
    })

    expect(await screen.findByText('What is a window function?')).toBeInTheDocument()
    expect(screen.getByLabelText('Concept')).toHaveValue('concept_1')
  })

  it('sends a message and appends both turns to the transcript', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (url.includes('/knowledge')) return Promise.resolve(jsonResponse(CONCEPTS))
        if (init?.body && JSON.parse(init.body as string).message === 'It aggregates per row.') {
          return Promise.resolve(
            jsonResponse({ ...OPENING_TURN, content: 'Good, can you give an example?' }),
          )
        }
        return Promise.resolve(jsonResponse(OPENING_TURN))
      }),
    )

    render(<TutorChat sessionId="session_1" goalId="goal_1" onEnd={vi.fn()} />, {
      wrapper: LanguageProvider,
    })
    await screen.findByText('What is a window function?')

    fireEvent.change(screen.getByPlaceholderText('Type your response…'), {
      target: { value: 'It aggregates per row.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByText('It aggregates per row.')).toBeInTheDocument()
    expect(await screen.findByText('Good, can you give an example?')).toBeInTheDocument()
  })

  it('locks the concept picker once the conversation has started', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/knowledge')) return Promise.resolve(jsonResponse(CONCEPTS))
        return Promise.resolve(jsonResponse(OPENING_TURN))
      }),
    )

    render(<TutorChat sessionId="session_1" goalId="goal_1" onEnd={vi.fn()} />, {
      wrapper: LanguageProvider,
    })
    await screen.findByText('What is a window function?')

    fireEvent.change(screen.getByPlaceholderText('Type your response…'), {
      target: { value: 'Not sure yet.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(screen.getByLabelText('Concept')).toBeDisabled())
  })

  it('shows a message and an end button when the goal has no concepts', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ concepts: [] })))
    const onEnd = vi.fn()

    render(<TutorChat sessionId="session_1" goalId="goal_1" onEnd={onEnd} />, {
      wrapper: LanguageProvider,
    })

    expect(
      await screen.findByText('This goal has no concepts yet -- generate a roadmap first.'),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'End session' }))
    expect(onEnd).toHaveBeenCalled()
  })
})
