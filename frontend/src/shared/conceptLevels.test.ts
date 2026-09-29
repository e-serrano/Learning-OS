import { describe, expect, it } from 'vitest'
import { computeLevels, orderByPrerequisite } from './conceptLevels'

interface Item {
  id: string
}

function item(id: string): Item {
  return { id }
}

function prereq(source_id: string, target_id: string) {
  return { source_id, target_id, relation: 'PREREQUISITE_OF' }
}

describe('computeLevels', () => {
  it('puts every item at level 0 when there are no prerequisite edges', () => {
    const levels = computeLevels([item('a'), item('b')], [])

    expect(levels.get('a')).toBe(0)
    expect(levels.get('b')).toBe(0)
  })

  it('sits a dependent one level below its prerequisite', () => {
    const levels = computeLevels([item('a'), item('b')], [prereq('a', 'b')])

    expect(levels.get('a')).toBe(0)
    expect(levels.get('b')).toBe(1)
  })

  it('uses the deepest chain when an item has more than one prerequisite', () => {
    // a -> c, b -> c, a -> d -> e -> c: c's deepest chain is through e
    const levels = computeLevels(
      [item('a'), item('b'), item('c'), item('d'), item('e')],
      [prereq('a', 'c'), prereq('b', 'c'), prereq('a', 'd'), prereq('d', 'e'), prereq('e', 'c')],
    )

    expect(levels.get('c')).toBe(3)
  })

  it('ignores edges that are not PREREQUISITE_OF', () => {
    const levels = computeLevels(
      [item('a'), item('b')],
      [{ source_id: 'a', target_id: 'b', relation: 'RELATED_TO' }],
    )

    expect(levels.get('b')).toBe(0)
  })

  it('ignores edges pointing outside the given item set', () => {
    const levels = computeLevels([item('a')], [prereq('missing', 'a')])

    expect(levels.get('a')).toBe(0)
  })

  it('does not infinite-loop on a cycle, and still assigns every item a level', () => {
    const levels = computeLevels([item('a'), item('b')], [prereq('a', 'b'), prereq('b', 'a')])

    expect(levels.get('a')).toBeDefined()
    expect(levels.get('b')).toBeDefined()
  })
})

describe('orderByPrerequisite', () => {
  it('keeps the original order when there are no prerequisite edges', () => {
    const items = [item('b'), item('a')]

    expect(orderByPrerequisite(items, []).map((i) => i.id)).toEqual(['b', 'a'])
  })

  it('moves a prerequisite before the item that depends on it', () => {
    const items = [item('c'), item('b'), item('a')] // reverse dependency order
    const edges = [prereq('a', 'b'), prereq('b', 'c')]

    expect(orderByPrerequisite(items, edges).map((i) => i.id)).toEqual(['a', 'b', 'c'])
  })

  it('keeps items at the same level in their original relative order', () => {
    // a -> c, b -> c: a and b are both foundational (level 0), c depends on both
    const items = [item('c'), item('b'), item('a')]
    const edges = [prereq('a', 'c'), prereq('b', 'c')]

    expect(orderByPrerequisite(items, edges).map((i) => i.id)).toEqual(['b', 'a', 'c'])
  })

  it('still returns every item when the edges contain a cycle', () => {
    const items = [item('a'), item('b')]
    const edges = [prereq('a', 'b'), prereq('b', 'a')]

    expect(orderByPrerequisite(items, edges).map((i) => i.id).sort()).toEqual(['a', 'b'])
  })
})
