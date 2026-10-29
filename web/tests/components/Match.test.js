import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import Match from '@/components/Match.vue'

const VALID_RESULT = {
  score: 85,
  verdict: 'Excellent fit for a backend role.',
  matched_skills: ['Python', 'FastAPI', 'PostgreSQL'],
  gaps: ['Kubernetes'],
  citations: [
    {
      project_slug: 'ayutech',
      project_title: 'AyuTech',
      section: 'build',
      text: 'FastAPI + M-Pesa integration',
      similarity: 0.92,
    },
  ],
}

function jsonResponse(body) {
  return { ok: true, json: async () => body }
}

describe('Match.vue', () => {
  let wrapper

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
    wrapper = mount(Match)
  })

  afterEach(() => {
    wrapper.unmount()
  })

  describe('initial state', () => {
    it('renders the match engine panel', () => {
      expect(wrapper.find('.panel').exists()).toBe(true)
      expect(wrapper.text()).toContain('RAG MATCH ENGINE')
      expect(wrapper.text()).toContain('SCORE & CITATIONS')
    })

    it('starts with empty form fields', () => {
      expect(wrapper.find('input[type="text"]').element.value).toBe('')
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

    it('renders both preset buttons', () => {
      expect(wrapper.text()).toContain('LOAD BACKEND + M-PESA JD')
      expect(wrapper.text()).toContain('LOAD AI + FULL-STACK JD')
    })
  })

  describe('JD validation', () => {
    it('updates the character count while typing', async () => {
      await wrapper.find('textarea').setValue('a'.repeat(25))
      expect(wrapper.text()).toContain('25 / 6000')
      expect(wrapper.text()).toContain('Ready to score')
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

    it('declares maxlength on the textarea', () => {
      expect(wrapper.find('textarea').attributes('maxlength')).toBe('6000')
    })
  })

  describe('presets', () => {
    it('loads the backend preset', async () => {
      const btn = wrapper.findAll('button').find((b) => b.text().includes('LOAD BACKEND'))
      await btn.trigger('click')
      expect(wrapper.find('input[type="text"]').element.value).toBe('Senior Backend Engineer')
      expect(wrapper.find('textarea').element.value).toContain('M-Pesa Daraja STK Push')
    })

    it('loads the AI preset', async () => {
      const btn = wrapper.findAll('button').find((b) => b.text().includes('LOAD AI'))
      await btn.trigger('click')
      expect(wrapper.find('input[type="text"]').element.value).toBe('AI Full-Stack Engineer')
      expect(wrapper.find('textarea').element.value).toContain('LLM pipelines')
    })
  })

  describe('reset', () => {
    it('clears the form', async () => {
      await wrapper.find('textarea').setValue('Some job description here')
      await wrapper.find('input[type="text"]').setValue('Test Role')

      const reset = wrapper.findAll('button').find((b) => b.text() === 'RESET')
      await reset.trigger('click')

      expect(wrapper.find('textarea').element.value).toBe('')
      expect(wrapper.find('input[type="text"]').element.value).toBe('')
      expect(wrapper.vm.error).toBeNull()
    })
  })

  describe('submitting', () => {
    it('posts role + jd to /api/match', async () => {
      global.fetch.mockResolvedValueOnce(jsonResponse(VALID_RESULT))

      await wrapper.find('input[type="text"]').setValue('Backend Engineer')
      await wrapper.find('textarea').setValue('a'.repeat(40))
      await wrapper.find('form').trigger('submit')
      await flushPromises()

      expect(global.fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/match',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ role: 'Backend Engineer', jd: 'a'.repeat(40) }),
        })
      )
    })

    it('shows the loading state while pending', async () => {
      let resolveFetch
      global.fetch.mockReturnValueOnce(
        new Promise((resolve) => {
          resolveFetch = resolve
        })
      )

      await wrapper.find('textarea').setValue('a'.repeat(50))
      await wrapper.find('form').trigger('submit')

      expect(wrapper.vm.loading).toBe(true)
      expect(wrapper.text()).toContain('SCORING MATCH...')
      expect(wrapper.text()).toContain('Retrieving project evidence')

      resolveFetch(jsonResponse(VALID_RESULT))
      await flushPromises()
      expect(wrapper.vm.loading).toBe(false)
    })

    it('renders the score, verdict, skills, gaps and citations', async () => {
      global.fetch.mockResolvedValueOnce(jsonResponse(VALID_RESULT))

      await wrapper.find('textarea').setValue('a'.repeat(50))
      await wrapper.find('form').trigger('submit')
      await flushPromises()

      expect(wrapper.text()).toContain('85')
      expect(wrapper.text()).toContain('STRONG FIT')
      expect(wrapper.text()).toContain('Excellent fit for a backend role.')
      expect(wrapper.text()).toContain('Python')
      expect(wrapper.text()).toContain('Kubernetes')
      expect(wrapper.text()).toContain('AyuTech')
      expect(wrapper.text()).toContain('92.0% MATCH')
    })

    it('surfaces an API error', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        json: async () => ({ detail: 'Too many match requests!' }),
      })

      await wrapper.find('textarea').setValue('a'.repeat(50))
      await wrapper.find('form').trigger('submit')
      await flushPromises()

      expect(wrapper.vm.error).toBe('Too many match requests!')
      expect(wrapper.text()).toContain('Too many match requests!')
    })

    it('surfaces a network error', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'))

      await wrapper.find('textarea').setValue('a'.repeat(50))
      await wrapper.find('form').trigger('submit')
      await flushPromises()

      expect(wrapper.vm.error).toBe('Network error')
    })

    it('surfaces a malformed JSON response', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => {
          throw new Error('bad json')
        },
      })

      await wrapper.find('textarea').setValue('a'.repeat(50))
      await wrapper.find('form').trigger('submit')
      await flushPromises()

      expect(wrapper.vm.error).toBeTruthy()
    })
  })

  describe('result rendering', () => {
    it('colors the score green for a strong fit', async () => {
      wrapper.vm.result = { ...VALID_RESULT, score: 80 }
      await wrapper.vm.$nextTick()
      expect(wrapper.find('.font-orbitron.text-3xl').element.style.color).toBe('rgb(61, 245, 166)')
    })

    it('colors the score amber for a partial fit', async () => {
      wrapper.vm.result = { ...VALID_RESULT, score: 60 }
      await wrapper.vm.$nextTick()
      expect(wrapper.find('.font-orbitron.text-3xl').element.style.color).toBe('rgb(255, 200, 87)')
    })

    it('colors the score red for a weak fit', async () => {
      wrapper.vm.result = { ...VALID_RESULT, score: 30 }
      await wrapper.vm.$nextTick()
      expect(wrapper.find('.font-orbitron.text-3xl').element.style.color).toBe('rgb(255, 77, 141)')
    })

    it('sets the progress bar width to the score', async () => {
      wrapper.vm.result = { ...VALID_RESULT, score: 65 }
      await wrapper.vm.$nextTick()
      expect(wrapper.find('.h-full.transition-all').element.style.width).toBe('65%')
    })

    it('renders each matched skill', async () => {
      wrapper.vm.result = { ...VALID_RESULT, matched_skills: ['Python', 'FastAPI'], gaps: [] }
      await wrapper.vm.$nextTick()
      const skills = wrapper.findAll('span').filter((s) => ['Python', 'FastAPI'].includes(s.text()))
      expect(skills).toHaveLength(2)
    })

    it('renders each gap', async () => {
      wrapper.vm.result = { ...VALID_RESULT, matched_skills: [], gaps: ['Docker', 'Kubernetes'] }
      await wrapper.vm.$nextTick()
      const gaps = wrapper.findAll('span').filter((s) => ['Docker', 'Kubernetes'].includes(s.text()))
      expect(gaps).toHaveLength(2)
    })

    it('shows empty-state copy when there are no matches or gaps', async () => {
      wrapper.vm.result = { ...VALID_RESULT, matched_skills: [], gaps: [], citations: [] }
      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('No explicit skill matches detected.')
      expect(wrapper.text()).toContain('No major gaps detected.')
    })

    it('renders citation section badges', async () => {
      wrapper.vm.result = {
        ...VALID_RESULT,
        citations: [
          { project_slug: 'a', project_title: 'A', section: 'problem', text: '', similarity: 0.5 },
          { project_slug: 'b', project_title: 'B', section: 'build', text: '', similarity: 0.5 },
          { project_slug: 'c', project_title: 'C', section: 'outcome', text: '', similarity: 0.5 },
        ],
      }
      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('PROBLEM')
      expect(wrapper.text()).toContain('BUILD')
      expect(wrapper.text()).toContain('OUTCOME')
      expect(wrapper.text()).toContain('3 CITATIONS')
    })
  })
})