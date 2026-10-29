import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePetStore } from '@/stores/pet'

describe('Pet Store', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = usePetStore()
    vi.resetAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('initial state', () => {
    it('has correct default values', () => {
      expect(store.desperation).toBe(0)
      expect(store.label).toBe('Loading...')
      expect(store.mood).toBe('sleeping')
      expect(store.quip).toBe('')
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })
  })

  describe('fetchState', () => {
    it('sets loading true during fetch', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          desperation: 42,
          label: 'Hungry',
          mood: 'smug',
          quip: 'Feed me',
        }),
      })

      const promise = store.fetchState()
      expect(store.loading).toBe(true)

      await promise
      expect(store.loading).toBe(false)
    })

    it('applies state from successful response', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          desperation: 75,
          label: 'Starving',
          mood: 'anxious',
          quip: 'I need a job!',
          relief_gained: 5,
        }),
      })

      await store.fetchState()

      expect(store.desperation).toBe(75)
      expect(store.label).toBe('Starving')
      expect(store.mood).toBe('anxious')
      expect(store.quip).toBe('I need a job!')
      expect(store.error).toBeNull()
    })

    it('handles 429 rate limit error with generic offline message', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        json: async () => ({ detail: 'Too many interactions! Let the monkey breathe a bit.' }),
      })

      await store.fetchState()

      expect(store.error).toBe('The monkey is offline. Try again in a moment.')
      expect(store.loading).toBe(false)
    })

    it('handles 422 validation error with generic offline message', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({
          detail: [{ msg: 'Note is required for this action' }],
        }),
      })

      await store.fetchState()

      expect(store.error).toBe('The monkey is offline. Try again in a moment.')
    })

    it('handles network error with generic offline message', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Failed to fetch'))

      await store.fetchState()

      expect(store.error).toBe('The monkey is offline. Try again in a moment.')
      expect(store.loading).toBe(false)
    })

    it('ignores unknown fields in response', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          desperation: 50,
          label: 'Hungry',
          mood: 'smug',
          quip: 'Hello',
          unknown_field: 'should be ignored',
        }),
      })

      await store.fetchState()

      expect(store.desperation).toBe(50)
      expect(store.unknown_field).toBeUndefined()
    })
  })

  describe('interact', () => {
    it('sends correct payload for action with note', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          desperation: 30,
          label: 'Hungry',
          mood: 'smug',
          quip: 'Thanks!',
        }),
      })

      await store.interact('link', 'https://example.com/job')

      expect(global.fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/pet/interact',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ type: 'link', note: 'https://example.com/job' }),
        })
      )
    })

    it('omits note for book action', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          desperation: 10,
          label: 'Smug',
          mood: 'sleeping',
          quip: 'Booked!',
        }),
      })

      await store.interact('book', '')

      expect(global.fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/pet/interact',
        expect.objectContaining({
          body: JSON.stringify({ type: 'book' }),
        })
      )
    })

    it('returns data on success and forces happy mood', async () => {
      store.error = 'Previous error'

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          desperation: 20,
          label: 'Smug',
          mood: 'sleeping',
          quip: 'All good',
        }),
      })

      const result = await store.interact('lead', 'Great lead!')

      expect(result).toEqual({
        desperation: 20,
        label: 'Smug',
        mood: 'sleeping',
        quip: 'All good',
      })
      expect(store.error).toBeNull()
      expect(store.mood).toBe('happy') // forced happy mood on success
    })

    it('returns null on 429 and sets error from response', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        json: async () => ({ detail: 'Rate limited!' }),
      })

      const result = await store.interact('link', 'test')

      expect(result).toBeNull()
      expect(store.error).toBe('Rate limited!')
    })

    it('returns null on 422 and sets validation error', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({
          detail: [{ msg: 'Note too long' }],
        }),
      })

      const result = await store.interact('link', 'x'.repeat(300))

      expect(result).toBeNull()
      expect(store.error).toBe('Note too long')
    })

    it('returns null on network error', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'))

      const result = await store.interact('lead', 'test')

      expect(result).toBeNull()
      expect(store.error).toBe('The monkey could not reach the server.')
    })

    it('handles malformed error response', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({}),
      })

      const result = await store.interact('link', 'test')

      expect(result).toBeNull()
      expect(store.error).toBe('Something went wrong (HTTP 500).')
    })
  })
})