import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import Interrogate from '@/components/Interrogate.vue'

const encoder = new TextEncoder()

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

describe('Interrogate.vue', () => {
  let wrapper

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
    wrapper = mount(Interrogate)
  })

  afterEach(() => {
    wrapper.unmount()
  })

  describe('initial state', () => {
    it('renders the interrogator panel', () => {
      expect(wrapper.find('.panel').exists()).toBe(true)
      expect(wrapper.text()).toContain('INTERROGATE THE JOB DESCRIPTION')
      expect(wrapper.text()).toContain('UNTRUSTED INPUT IS SANDBOXED')
    })

    it('starts with empty fields', () => {
      const inputs = wrapper.findAll('input[type="text"]')
      expect(inputs[0].element.value).toBe('')
      expect(inputs[1].element.value).toBe('')
      expect(wrapper.find('textarea').element.value).toBe('')
    })

    it('shows a 0 / 6000 character count', () => {
      expect(wrapper.text()).toContain('0 / 6000')
    })

    it('shows the minimum length hint', () => {
      expect(wrapper.text()).toContain('At least 20 characters')
    })

    it('disables submit until the JD is valid', () => {
      expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    })

    it('renders both action buttons', () => {
      expect(wrapper.text()).toContain('LOAD SAMPLE JD')
      expect(wrapper.text()).toContain('TRY PROMPT INJECTION')
    })

    it('shows the awaiting-verdict placeholder', () => {
      expect(wrapper.text()).toContain('Awaiting a job description. No verdict yet.')
    })
  })

  describe('JD validation', () => {
    it('updates the character count while typing', async () => {
      await wrapper.find('textarea').setValue('a'.repeat(25))
      expect(wrapper.text()).toContain('25 / 6000')
      expect(wrapper.text()).toContain('Ready to scan')
    })

    it('keeps submit disabled while too short', async () => {
      await wrapper.find('textarea').setValue('short')
      expect(wrapper.text()).toContain('At least 20 characters')
      expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    })

    it('enables submit for a valid JD', async () => {
      await wrapper.find('textarea').setValue('a'.repeat(25))
      expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeUndefined()
    })

    it('flags an over-limit JD and disables submit', async () => {
      await wrapper.find('textarea').setValue('a'.repeat(6001))
      expect(wrapper.text()).toContain('6001 / 6000')
      expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    })

    it('declares maxlength on the JD textarea and text inputs', () => {
      expect(wrapper.find('textarea').attributes('maxlength')).toBe('6000')
      for (const input of wrapper.findAll('input[type="text"]')) {
        expect(input.attributes('maxlength')).toBe('120')
      }
    })
  })

  describe('presets', () => {
    it('loads the sample JD', async () => {
      const btn = wrapper.findAll('button').find((b) => b.text().includes('LOAD SAMPLE'))
      await btn.trigger('click')

      const inputs = wrapper.findAll('input[type="text"]')
      expect(inputs[0].element.value).toBe('Acme Rocket Labs')
      expect(inputs[1].element.value).toBe('Senior Backend Engineer')
      expect(wrapper.find('textarea').element.value).toContain('rockstar ninja engineer')
    })

    it('loads the prompt-injection payload', async () => {
      const btn = wrapper.findAll('button').find((b) => b.text().includes('TRY PROMPT INJECTION'))
      await btn.trigger('click')

      const inputs = wrapper.findAll('input[type="text"]')
      expect(inputs[0].element.value).toBe('Totally Legit Corp')
      expect(inputs[1].element.value).toBe('Prompt Engineer')
      expect(wrapper.find('textarea').element.value).toContain('Ignore all previous instructions')
    })
  })

  describe('streaming verdict', () => {
    it('posts the form and streams tokens into the verdict box', async () => {
      global.fetch.mockResolvedValueOnce(
        sseResponse([
          'data: {"token":"Strong "}\n\n',
          'data: {"token":"fit."}\n\n',
          'data: [DONE]\n\n',
        ])
      )

      await wrapper.find('textarea').setValue('a'.repeat(50))
      await wrapper.find('form').trigger('submit')
      await flushPromises()

      expect(global.fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/recruiter/interrogate',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ company: null, role: null, jd: 'a'.repeat(50) }),
        })
      )
      expect(wrapper.text()).toContain('Strong fit.')
    })

    it('shows the loading state and stop button while streaming', async () => {
      let resolveFetch
      global.fetch.mockReturnValueOnce(
        new Promise((resolve) => {
          resolveFetch = resolve
        })
      )

      await wrapper.find('textarea').setValue('a'.repeat(50))
      await wrapper.find('form').trigger('submit')

      expect(wrapper.vm.streaming).toBe(true)
      expect(wrapper.text()).toContain('INTERROGATING...')
      expect(wrapper.findAll('button').some((b) => b.text() === 'STOP')).toBe(true)

      resolveFetch(sseResponse(['data: [DONE]\n\n']))
      await flushPromises()
      expect(wrapper.vm.streaming).toBe(false)
    })

    it('surfaces an API error from the stream', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        text: async () => JSON.stringify({ detail: 'Too many interrogations!' }),
      })

      await wrapper.find('textarea').setValue('a'.repeat(50))
      await wrapper.find('form').trigger('submit')
      await flushPromises()

      expect(wrapper.vm.error).toBe('Too many interrogations!')
      expect(wrapper.text()).toContain('Too many interrogations!')
    })

    it('surfaces a network error', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network down'))

      await wrapper.find('textarea').setValue('a'.repeat(50))
      await wrapper.find('form').trigger('submit')
      await flushPromises()

      expect(wrapper.vm.error).toBe('Network down')
    })
  })

  describe('verdict display', () => {
    it('shows a trailing cursor while streaming', async () => {
      wrapper.vm.verdict = 'Streaming verdict'
      wrapper.vm.streaming = true
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('Streaming verdict')
      expect(wrapper.text()).toContain('|')
    })

    it('hides the cursor once complete', async () => {
      wrapper.vm.verdict = 'Final verdict'
      wrapper.vm.streaming = false
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('Final verdict')
      expect(wrapper.text()).not.toContain('|')
    })

    it('renders an error message', async () => {
      wrapper.vm.error = 'API connection failed'
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('API connection failed')
    })
  })

  describe('form fields', () => {
    it('accepts a company name and role', async () => {
      const inputs = wrapper.findAll('input[type="text"]')
      await inputs[0].setValue('Test Company')
      await inputs[1].setValue('Senior Engineer')

      expect(inputs[0].element.value).toBe('Test Company')
      expect(inputs[1].element.value).toBe('Senior Engineer')
    })
  })
})