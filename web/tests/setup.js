// Vitest test setup for Vue 3 + Pinia components
import { vi, beforeAll, afterAll } from 'vitest'

// jsdom lacks a few browser APIs the components touch.
global.fetch = vi.fn()

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Expected error paths log to console.error; keep the test output readable.
const originalError = console.error
beforeAll(() => {
  console.error = (...args) => {
    const first = args[0]
    const text = first instanceof Error ? first.message : String(first ?? '')
    if (
      text.includes('Could not read the meter') ||
      text.includes('The monkey could not reach') ||
      text.includes('Network error') ||
      text.includes('Failed to fetch') ||
      text.includes('bad json')
    ) {
      return
    }
    originalError(...args)
  }
})
afterAll(() => {
  console.error = originalError
})