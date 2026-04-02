import '@testing-library/jest-dom'

// Mock WebSocket globally
class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  readyState = MockWebSocket.OPEN
  onopen: ((ev: Event) => void) | null = null
  onclose: ((ev: CloseEvent) => void) | null = null
  onmessage: ((ev: MessageEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null

  constructor(public url: string) {
    setTimeout(() => this.onopen?.(new Event('open')), 0)
  }

  send(_data: string) {}
  close() {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.(new CloseEvent('close'))
  }
}

Object.defineProperty(global, 'WebSocket', { value: MockWebSocket, writable: true })

// Silence console.error in tests unless explicitly tested
const originalError = console.error
beforeEach(() => {
  console.error = (...args: unknown[]) => {
    if (typeof args[0] === 'string' && args[0].includes('Warning:')) return
    originalError(...args)
  }
})
afterEach(() => {
  console.error = originalError
})
