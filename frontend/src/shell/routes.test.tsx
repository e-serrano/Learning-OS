import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AppRoutes } from './routes'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  )
}

describe('AppRoutes', () => {
  it('renders the dashboard placeholder at the root route', () => {
    renderAt('/')

    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })

  it('renders the reviews placeholder at /reviews', () => {
    renderAt('/reviews')

    expect(screen.getByRole('heading', { name: 'Reviews' })).toBeInTheDocument()
  })

  it('renders the goal placeholder for a goal-scoped route', () => {
    renderAt('/goals/goal_1')

    expect(screen.getByRole('heading', { name: 'Goal' })).toBeInTheDocument()
  })

  it('redirects an unknown path back to the dashboard', () => {
    renderAt('/does-not-exist')

    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })

  it('keeps the nav visible across routes', () => {
    renderAt('/vault')

    expect(screen.getByRole('link', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Vault Changes' })).toBeInTheDocument()
  })
})
