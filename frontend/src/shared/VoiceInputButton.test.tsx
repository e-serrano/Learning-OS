import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { VoiceInputButton } from './VoiceInputButton'

class FakeSpeechRecognition {
  lang = ''
  interimResults = false
  continuous = false
  onresult: ((event: { results: { length: number; [i: number]: { 0: { transcript: string } } } }) => void) | null =
    null
  onerror: (() => void) | null = null
  onend: (() => void) | null = null
  start = vi.fn()
  stop = vi.fn(() => this.onend?.())

  emitResult(transcript: string) {
    this.onresult?.({ results: { length: 1, 0: { 0: { transcript } } } })
  }
}

/** Stubbing the constructor as a plain `vi.fn()` breaks `new Ctor()` --
 * vitest wraps `mockImplementation`'s callback as an arrow function
 * internally, and arrow functions cannot be used with `new`. A regular
 * function that explicitly returns the instance is a valid constructor
 * (JS: a constructor returning an object makes `new` yield that object
 * instead of `this`), and still lets each test capture the instance. */
function stubSpeechRecognition(): { instance: FakeSpeechRecognition | null } {
  const holder: { instance: FakeSpeechRecognition | null } = { instance: null }
  vi.stubGlobal(
    'SpeechRecognition',
    function SpeechRecognitionStub() {
      holder.instance = new FakeSpeechRecognition()
      return holder.instance
    },
  )
  return holder
}

describe('VoiceInputButton', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders nothing when the browser has no SpeechRecognition support', () => {
    const { container } = render(<VoiceInputButton onTranscript={() => {}} />)

    expect(container).toBeEmptyDOMElement()
  })

  it('starts listening on click and reports the transcript', () => {
    const holder = stubSpeechRecognition()
    const onTranscript = vi.fn()

    render(<VoiceInputButton onTranscript={onTranscript} />)
    fireEvent.click(screen.getByRole('button', { name: 'Speak answer' }))

    expect(holder.instance).not.toBeNull()
    expect(holder.instance!.start).toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Stop listening' })).toBeInTheDocument()

    holder.instance!.emitResult('a window function')

    expect(onTranscript).toHaveBeenCalledWith('a window function')
  })

  it('stops listening when the recognizer ends', () => {
    const holder = stubSpeechRecognition()

    render(<VoiceInputButton onTranscript={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: 'Speak answer' }))
    act(() => holder.instance!.onend?.())

    expect(screen.getByRole('button', { name: 'Speak answer' })).toBeInTheDocument()
  })

  it('stops the recognizer when clicked again while listening', () => {
    const holder = stubSpeechRecognition()

    render(<VoiceInputButton onTranscript={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: 'Speak answer' }))
    fireEvent.click(screen.getByRole('button', { name: 'Stop listening' }))

    expect(holder.instance!.stop).toHaveBeenCalled()
  })

  it('disables the button when disabled is passed', () => {
    stubSpeechRecognition()

    render(<VoiceInputButton onTranscript={() => {}} disabled />)

    expect(screen.getByRole('button', { name: 'Speak answer' })).toBeDisabled()
  })
})
