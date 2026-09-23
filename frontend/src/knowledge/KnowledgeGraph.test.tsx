import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { Concept, ConceptRelation } from '../api/knowledge'
import { KnowledgeGraph } from './KnowledgeGraph'

function concept(overrides: Partial<Concept> & { id: string; title: string }): Concept {
  return {
    domain: 'sql',
    status: 'learning',
    mastery: 2,
    confidence: 40,
    importance: 3,
    retention: 50,
    last_practiced: null,
    next_review: null,
    obsidian_path: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

const SUBQUERIES = concept({ id: 'a', title: 'Subqueries', status: 'mastered' })
const WINDOW_FUNCTIONS = concept({ id: 'b', title: 'Window Functions', status: 'weak' })

describe('KnowledgeGraph', () => {
  it('renders a node per concept', () => {
    render(
      <KnowledgeGraph
        concepts={[SUBQUERIES, WINDOW_FUNCTIONS]}
        relations={[]}
        selectedId={null}
        onSelect={() => {}}
      />,
    )

    expect(screen.getByRole('button', { name: 'Subqueries' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Window Functions' })).toBeInTheDocument()
  })

  it('renders nothing when there are no concepts', () => {
    const { container } = render(
      <KnowledgeGraph concepts={[]} relations={[]} selectedId={null} onSelect={() => {}} />,
    )

    expect(container.querySelector('svg')).not.toBeInTheDocument()
  })

  it('draws a prerequisite edge only between concepts that are both present', () => {
    const relations: ConceptRelation[] = [
      { source_id: 'a', target_id: 'b', relation: 'PREREQUISITE_OF', weight: null },
      { source_id: 'a', target_id: 'missing', relation: 'PREREQUISITE_OF', weight: null },
    ]

    const { container } = render(
      <KnowledgeGraph
        concepts={[SUBQUERIES, WINDOW_FUNCTIONS]}
        relations={relations}
        selectedId={null}
        onSelect={() => {}}
      />,
    )

    expect(container.querySelectorAll('.kg-edge')).toHaveLength(1)
    expect(container.querySelector('.kg-edge-prerequisite_of')).toHaveAttribute(
      'marker-end',
      'url(#kg-arrow)',
    )
  })

  it('places a prerequisite concept in a row above the concept it unlocks', () => {
    const relations: ConceptRelation[] = [
      { source_id: 'a', target_id: 'b', relation: 'PREREQUISITE_OF', weight: null },
    ]

    render(
      <KnowledgeGraph
        concepts={[SUBQUERIES, WINDOW_FUNCTIONS]}
        relations={relations}
        selectedId={null}
        onSelect={() => {}}
      />,
    )

    const prereqNode = screen.getByRole('button', { name: 'Subqueries' })
    const dependentNode = screen.getByRole('button', { name: 'Window Functions' })
    const prereqY = Number(prereqNode.getAttribute('transform')?.match(/,\s*([\d.]+)\)/)?.[1])
    const dependentY = Number(dependentNode.getAttribute('transform')?.match(/,\s*([\d.]+)\)/)?.[1])

    expect(prereqY).toBeLessThan(dependentY)
  })

  it('calls onSelect when a node is clicked', () => {
    const onSelect = vi.fn()
    render(
      <KnowledgeGraph
        concepts={[SUBQUERIES]}
        relations={[]}
        selectedId={null}
        onSelect={onSelect}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Subqueries' }))

    expect(onSelect).toHaveBeenCalledWith('a')
  })

  it('marks the selected node', () => {
    render(
      <KnowledgeGraph
        concepts={[SUBQUERIES]}
        relations={[]}
        selectedId="a"
        onSelect={() => {}}
      />,
    )

    expect(screen.getByRole('button', { name: 'Subqueries' })).toHaveClass('kg-node-selected')
  })

  it('truncates long titles', () => {
    const longTitled = concept({
      id: 'c',
      title: 'A Very Long Concept Title That Should Be Truncated',
    })

    render(
      <KnowledgeGraph concepts={[longTitled]} relations={[]} selectedId={null} onSelect={() => {}} />,
    )

    expect(screen.getByText('A Very Long Conce…')).toBeInTheDocument()
  })
})
