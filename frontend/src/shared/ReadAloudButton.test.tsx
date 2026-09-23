import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ReadAloudButton } from './ReadAloudButton'

class FakeUtterance {
  text: string
  onend: (() => void) | null = null
  onerror: (() => void) | null = null
  constructor(text: string) {
    this.text = text
  }
}

describe('ReadAloudButton', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders nothing when the browser has no speechSynthesis support', () => {
    const { container } = render(<ReadAloudButton text="hello" />)

    expect(container).toBeEmptyDOMElement()
  })

  it('speaks the given text on click', () => {
    const speak = vi.fn()
    const cancel = vi.fn()
    vi.stubGlobal('speechSynthesis', { speak, cancel })
    vi.stubGlobal('SpeechSynthesisUtterance', FakeUtterance)

    render(<ReadAloudButton text="A window function computes a value." />)
    fireEvent.click(screen.getByRole('button', { name: 'Read aloud' }))

    expect(speak).toHaveBeenCalledTimes(1)
    const utterance = speak.mock.calls[0][0] as FakeUtterance
    expect(utterance.text).toBe('A window function computes a value.')
    expect(screen.getByRole('button', { name: 'Stop reading' })).toBeInTheDocument()
  })

  it('cancels speech when clicked again while speaking', () => {
    const speak = vi.fn()
    const cancel = vi.fn()
    vi.stubGlobal('speechSynthesis', { speak, cancel })
    vi.stubGlobal('SpeechSynthesisUtterance', FakeUtterance)

    render(<ReadAloudButton text="hello" />)
    fireEvent.click(screen.getByRole('button', { name: 'Read aloud' }))
    fireEvent.click(screen.getByRole('button', { name: 'Stop reading' }))

    expect(cancel).toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Read aloud' })).toBeInTheDocument()
  })

  it('resets to idle when the utterance ends', () => {
    const speak = vi.fn()
    vi.stubGlobal('speechSynthesis', { speak, cancel: vi.fn() })
    vi.stubGlobal('SpeechSynthesisUtterance', FakeUtterance)

    render(<ReadAloudButton text="hello" />)
    fireEvent.click(screen.getByRole('button', { name: 'Read aloud' }))
    const utterance = speak.mock.calls[0][0] as FakeUtterance
    act(() => utterance.onend?.())

    expect(screen.getByRole('button', { name: 'Read aloud' })).toBeInTheDocument()
  })

  it('disables the button when there is no text', () => {
    vi.stubGlobal('speechSynthesis', { speak: vi.fn(), cancel: vi.fn() })
    vi.stubGlobal('SpeechSynthesisUtterance', FakeUtterance)

    render(<ReadAloudButton text="   " />)

    expect(screen.getByRole('button', { name: 'Read aloud' })).toBeDisabled()
  })
})
