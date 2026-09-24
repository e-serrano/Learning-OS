import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SqlSandbox } from './SqlSandbox'

function jsonResponse(body: unknown) {
  return { ok: true, json: async () => body } as Response
}

describe('SqlSandbox', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('is collapsed by default', () => {
    render(<SqlSandbox />)

    expect(screen.queryByLabelText('SQL')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try it: run SQL' })).toBeInTheDocument()
  })

  it('runs a query and shows the result table', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          columns: ['n'],
          rows: [[1]],
          row_count: 1,
          truncated: false,
          statement_count: 1,
          error: null,
        }),
      ),
    )

    render(<SqlSandbox />)
    fireEvent.click(screen.getByRole('button', { name: 'Try it: run SQL' }))
    fireEvent.change(screen.getByLabelText('SQL'), { target: { value: 'SELECT 1 AS n' } })
    fireEvent.click(screen.getByRole('button', { name: 'Run' }))

    expect(await screen.findByRole('columnheader', { name: 'n' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '1' })).toBeInTheDocument()
  })

  it('shows a query error inline instead of a result table', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          columns: [],
          rows: [],
          row_count: 0,
          truncated: false,
          statement_count: 1,
          error: 'near "SELEKT": syntax error',
        }),
      ),
    )

    render(<SqlSandbox />)
    fireEvent.click(screen.getByRole('button', { name: 'Try it: run SQL' }))
    fireEvent.change(screen.getByLabelText('SQL'), { target: { value: 'SELEKT 1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Run' }))

    expect(await screen.findByText('near "SELEKT": syntax error')).toBeInTheDocument()
  })
})
