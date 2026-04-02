import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatInterface } from '../components/ChatInterface'

const defaultProps = {
  selectedAction: 'qa',
  selectedDocIds: [],
}

// Helper to build a mock streaming fetch response
function mockFetch(streamText: string, ok = true) {
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(streamText))
      controller.close()
    },
  })
  return vi.fn().mockResolvedValue({
    ok,
    body: stream,
    getReader: () => stream.getReader(),
  } as unknown as Response)
}

describe('ChatInterface', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.restoreAllMocks()
  })

  it('renders the empty state with prompt hints', () => {
    render(<ChatInterface {...defaultProps} />)
    expect(screen.getByText(/intelligent analysis/i)).toBeInTheDocument()
    expect(screen.getByText(/summarize key findings/i)).toBeInTheDocument()
  })

  it('renders the message input field', () => {
    render(<ChatInterface {...defaultProps} />)
    expect(screen.getByPlaceholderText(/ask anything/i)).toBeInTheDocument()
  })

  it('send button is disabled when input is empty', () => {
    render(<ChatInterface {...defaultProps} />)
    expect(screen.getByLabelText('Send message')).toBeDisabled()
  })

  it('send button becomes enabled when input has text', async () => {
    render(<ChatInterface {...defaultProps} />)
    const input = screen.getByPlaceholderText(/ask anything/i)
    await userEvent.type(input, 'Hello')
    expect(screen.getByLabelText('Send message')).toBeEnabled()
  })

  it('clicking a hint populates the input field', async () => {
    render(<ChatInterface {...defaultProps} />)
    fireEvent.click(screen.getByText('Summarize key findings'))
    expect(screen.getByPlaceholderText(/ask anything/i)).toHaveValue('Summarize key findings')
  })

  it('displays user message after submit', async () => {
    global.fetch = mockFetch('The answer is 42.')

    render(<ChatInterface {...defaultProps} />)
    const input = screen.getByPlaceholderText(/ask anything/i)
    await userEvent.type(input, 'What is the answer?')
    fireEvent.click(screen.getByLabelText('Send message'))

    await waitFor(() => {
      expect(screen.getByText('What is the answer?')).toBeInTheDocument()
    })
  })

  it('displays streaming assistant response', async () => {
    global.fetch = mockFetch('The answer is 42.')

    render(<ChatInterface {...defaultProps} />)
    await userEvent.type(screen.getByPlaceholderText(/ask anything/i), 'Test question')
    fireEvent.click(screen.getByLabelText('Send message'))

    await waitFor(() => {
      expect(screen.getByText(/the answer is 42/i)).toBeInTheDocument()
    })
  })

  it('clears input after message is sent', async () => {
    global.fetch = mockFetch('Response.')

    render(<ChatInterface {...defaultProps} />)
    const input = screen.getByPlaceholderText(/ask anything/i)
    await userEvent.type(input, 'A question')
    fireEvent.click(screen.getByLabelText('Send message'))

    await waitFor(() => {
      expect(input).toHaveValue('')
    })
  })

  it('shows typing indicator while waiting for response', async () => {
    // Slow fetch that never resolves within the test window
    global.fetch = vi.fn().mockImplementation(
      () => new Promise(() => {}) // never resolves
    )

    render(<ChatInterface {...defaultProps} />)
    await userEvent.type(screen.getByPlaceholderText(/ask anything/i), 'slow question')
    fireEvent.click(screen.getByLabelText('Send message'))

    await waitFor(() => {
      expect(screen.getByText(/agent analyzing/i)).toBeInTheDocument()
    })
  })

  it('shows error message when fetch fails', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false } as Response)

    render(<ChatInterface {...defaultProps} />)
    await userEvent.type(screen.getByPlaceholderText(/ask anything/i), 'broken query')
    fireEvent.click(screen.getByLabelText('Send message'))

    await waitFor(() => {
      expect(screen.getByText(/encountered an issue/i)).toBeInTheDocument()
    })
  })

  it('shows the selected action in the header', () => {
    render(<ChatInterface selectedAction="summarize" selectedDocIds={[]} />)
    expect(screen.getByText('summarize')).toBeInTheDocument()
  })

  it('shows source count in the header', () => {
    render(<ChatInterface selectedAction="qa" selectedDocIds={['a', 'b', 'c']} />)
    expect(screen.getByText('3 Sources Active')).toBeInTheDocument()
  })

  it('does not submit when input is only whitespace', async () => {
    global.fetch = vi.fn()

    render(<ChatInterface {...defaultProps} />)
    const input = screen.getByPlaceholderText(/ask anything/i)
    await userEvent.type(input, '   ')
    fireEvent.submit(input.closest('form')!)

    expect(global.fetch).not.toHaveBeenCalled()
  })
})
