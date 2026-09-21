import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ProjectView } from './ProjectView'

function jsonResponse(body: unknown) {
  return { ok: true, json: async () => body } as Response
}

const PROJECT = {
  id: 'project_1',
  goal_id: 'goal_1',
  title: 'Build an ETL pipeline',
  objective: 'Rank top products per warehouse using window functions.',
  difficulty: 3,
  status: 'active',
  concept_ids: ['window_functions'],
  success_criteria: ['Uses at least one window function'],
  artifact_path: null,
}

const TASKS = [{ task_id: 'task_1', sequence: 1, description: 'Uses at least one window function', status: 'pending' }]

function renderAt(path: string, state?: unknown) {
  return render(
    <MemoryRouter initialEntries={[{ pathname: path, state }]}>
      <Routes>
        <Route path="/projects/:projectId" element={<ProjectView />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProjectView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the project header and objective', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(PROJECT)))

    renderAt('/projects/project_1')

    expect(await screen.findByRole('heading', { name: 'Build an ETL pipeline' })).toBeInTheDocument()
    expect(
      screen.getByText('Rank top products per warehouse using window functions.'),
    ).toBeInTheDocument()
  })

  it('shows a note when tasks were not carried over from creation', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(PROJECT)))

    renderAt('/projects/project_1')

    expect(
      await screen.findByText(
        "Tasks aren't available after leaving this page -- reopen it right after starting the project to submit deliverables.",
      ),
    ).toBeInTheDocument()
  })

  it('lists tasks passed via navigation state and submits a deliverable', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/submit')) {
          return Promise.resolve(
            jsonResponse({
              task_id: 'task_1',
              task_status: 'completed',
              evaluation: {
                correctness: 0.9,
                reasoning: 0.8,
                independence: 0.8,
                transfer: 0.7,
                feedback: 'Solid work.',
                misconceptions: [],
              },
              updated_concepts: [],
            }),
          )
        }
        return Promise.resolve(jsonResponse(PROJECT))
      }),
    )

    renderAt('/projects/project_1', { tasks: TASKS })

    const taskHeader = await screen.findByRole('button', {
      name: /Uses at least one window function/,
    })
    fireEvent.click(taskHeader)

    fireEvent.change(screen.getByLabelText('Deliverable'), {
      target: { value: 'https://github.com/x/y' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Submit' }))

    expect(await screen.findByText('Solid work.')).toBeInTheDocument()
    await waitFor(() => expect(screen.getAllByText('completed').length).toBeGreaterThan(0))
  })
})
