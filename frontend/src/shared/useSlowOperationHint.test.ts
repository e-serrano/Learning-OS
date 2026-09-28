import { renderHook } from '@testing-library/react'
import { act } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useSlowOperationHint } from './useSlowOperationHint'

describe('useSlowOperationHint', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('starts false', () => {
    const { result } = renderHook(() => useSlowOperationHint(true, 8000))
    expect(result.current).toBe(false)
  })

  it('stays false when not active, even after the delay elapses', () => {
    const { result } = renderHook(() => useSlowOperationHint(false, 8000))
    act(() => vi.advanceTimersByTime(10000))
    expect(result.current).toBe(false)
  })

  it('becomes true once active for longer than the delay', () => {
    const { result } = renderHook(() => useSlowOperationHint(true, 8000))
    act(() => vi.advanceTimersByTime(8000))
    expect(result.current).toBe(true)
  })

  it('resets to false once active goes back to false', () => {
    const { result, rerender } = renderHook(({ active }) => useSlowOperationHint(active, 8000), {
      initialProps: { active: true },
    })
    act(() => vi.advanceTimersByTime(8000))
    expect(result.current).toBe(true)

    rerender({ active: false })
    expect(result.current).toBe(false)
  })
})
