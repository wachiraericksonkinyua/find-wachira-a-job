import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ExcuseBuster from '@/components/ExcuseBuster.vue'

const encoder = new TextEncoder()

const EXCUSES = [
  { id: 1, text: "They're overqualified" },
  { id: 2, text: 'Not enough experience' },
]

function excusesResponse() {
  return { ok: true, json: async () => EXCUSES }
}

function sseResponse(frames) {
  let index = 0
  return {
    ok: true,
    body: {
      getReader() {
        return {
          read() {
            if (index >= frames.length) return Promise.resolve({ done: true, value: undefined })
            return Promise.resolve({ done: false, value: encoder.encode(frames[index++]) })
          },
          cancel: () => Promise.resolve(),
          releaseLock: () => {},
        }
      },
    },
  }
}

async function mountAndLoad() {
  global.fetch = vi.fn().mockResolvedValueOnce(excusesResponse())
  const wrapper = mount(ExcuseBuster)
  await flushPromises()
  return wrapper
}

describe('ExcuseBuster.vue', () => {
  let wrapper

  afterEach(() => {
    if (wrapper) wrapper.unmount()
    wrapper = null
  })

  describe('initial state', () => {
    it('renders the panel and placeholder', async () => {
      wrapper = await mountAndLoad()
      expect(wrapper.find('.panel').exists()).toBe(true)
      expect(wrapper.text()).toContain('Excuse Buster')
      expect(wrapper.text()).toContain('Select an excuse and let the monkey tear it apart.')
    })

    it('disables the debunk button with no selection', async () => {
      wrapper = await mountAndLoad()
      const btn = wrapper.find('button')
      expect(btn.attributes('disabled')).toBeDefined()
      expect(btn.text()).toBe('Debunk')
    })
  })

  describe('loading excuses', () => {
    it('fetches and lists excuses on mount', async () => {
      wrapper = await mountAndLoad()

      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/excuses')
      const options = wrapper.findAll('option')
      expect(options).toHaveLength(3) // placeholder + two excuses
      expect(options[1].text()).toBe("They're overqualified")
      expect(options[2].text()).toBe('Not enough experience')
    })

    it('shows an error when the request fails', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({ ok: false, status: 500 })
      wrapper = mount(ExcuseBuster)
      await flushPromises()

      expect(wrapper.vm.error).toBe('Failed to load excuses')
      expect(wrapper.text()).toContain('Failed to load excuses')
    })
  })

  describe('selection', () => {
    it('enables debunk once an excuse is selected', async () => {
      wrapper = await mountAndLoad()
      await wrapper.find('select').setValue('1')

      expect(wrapper.find('button').attributes('disabled')).toBeUndefined()
    })
  })

  describe('debunking', () => {
    it('posts the selected excuse and streams the response', async () => {
      wrapper = await mountAndLoad()
      await wrapper.find('select').setValue('1')

      global.fetch.mockResolvedValueOnce(
        sseResponse([
          'data: {"token":"Overqualified "}\n\n',
          'data: {"token":"is a myth."}\n\n',
          'data: [DONE]\n\n',
        ])
      )
      await wrapper.find('button').trigger('click')
      await flushPromises()

      expect(global.fetch).toHaveBeenLastCalledWith(
        'http://localhost:8000/api/excuse-buster',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ excuse_id: 1 }),
        })
      )
      expect(wrapper.text()).toContain('Overqualified is a myth.')
    })

    it('shows the streaming state while pending', async () => {
      wrapper = await mountAndLoad()
      await wrapper.find('select').setValue('1')

      let resolveFetch
      global.fetch.mockReturnValueOnce(
        new Promise((resolve) => {
          resolveFetch = resolve
        })
      )
      await wrapper.find('button').trigger('click')

      expect(wrapper.vm.streaming).toBe(true)
      expect(wrapper.find('button').text()).toBe('Debunking...')
      expect(wrapper.find('button').attributes('disabled')).toBeDefined()

      resolveFetch(sseResponse(['data: [DONE]\n\n']))
      await flushPromises()
      expect(wrapper.vm.streaming).toBe(false)
    })

    it('surfaces a stream error', async () => {
      wrapper = await mountAndLoad()
      await wrapper.find('select').setValue('1')

      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        text: async () => JSON.stringify({ detail: 'Too many requests!' }),
      })
      await wrapper.find('button').trigger('click')
      await flushPromises()

      expect(wrapper.vm.error).toBe('Too many requests!')
      expect(wrapper.text()).toContain('Too many requests!')
    })
  })
})