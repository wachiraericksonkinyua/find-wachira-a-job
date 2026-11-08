import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import Projects from '@/components/Projects.vue'

const PROJECTS = [
  {
    id: 'rag-1',
    title: 'Production RAG pipelines',
    category: 'AI & Full-Stack',
    problem: 'Answers need to be grounded in real documents.',
    build: 'FastAPI plus pgvector retrieval with citations.',
    outcome: 'Every answer is traceable.',
    stack: ['FastAPI', 'pgvector'],
    repo_url: 'https://github.com/example/rag',
    demo_url: null,
    reactions: { heart: 2, roast: 0 },
  },
  {
    id: 'printer-2',
    title: 'Fixing printers that smell fear',
    category: 'IT Specialist Hustle',
    problem: 'Printers break at the worst possible time.',
    build: 'Structured triage and spooler recovery.',
    outcome: 'Fewer repeat faults.',
    stack: ['Windows', 'Networking'],
    repo_url: null,
    demo_url: null,
    reactions: { heart: 0, roast: 0 },
  },
]

function jsonResponse(body) {
  return { ok: true, json: async () => body }
}

describe('Projects swipe deck', () => {
  let wrapper

  beforeEach(async () => {
    vi.resetAllMocks()
    global.fetch.mockResolvedValueOnce(jsonResponse(PROJECTS))
    wrapper = mount(Projects)
    await flushPromises()
  })

  afterEach(() => {
    wrapper.unmount()
  })

  it('loads the deck and shows the first project', () => {
    expect(wrapper.text()).toContain('SWIPE DECK')
    expect(wrapper.text()).toContain('Production RAG pipelines')
    expect(wrapper.text()).toContain('1 / 2')
    expect(wrapper.text()).toContain('AI & Full-Stack')
  })

  it('switches to grid mode', async () => {
    const gridButton = wrapper.findAll('button').find((button) => button.text() === 'GRID MODE')
    await gridButton.trigger('click')
    expect(wrapper.text()).toContain('PROJECT GRID')
    expect(wrapper.text()).toContain('Fixing printers that smell fear')
  })

  it('hearts a project and advances the deck', async () => {
    global.fetch.mockResolvedValueOnce(jsonResponse({ heart: 3, roast: 0 }))
    const heartButton = wrapper.findAll('button').find((button) => button.text().includes('HEART'))
    await heartButton.trigger('click')
    await flushPromises()

    expect(global.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/projects/rag-1/react',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ reaction: 'heart' }),
      })
    )
    expect(wrapper.text()).toContain('Fixing printers that smell fear')
  })

  it('opens the quick roast input and submits to the moderation queue', async () => {
    const roastButton = wrapper.findAll('button').find((button) => button.text().includes('ROAST IT'))
    await roastButton.trigger('click')

    expect(wrapper.text()).toContain('DROP A QUICK ROAST')

    const textarea = wrapper.find('textarea')
    await textarea.setValue('The stack list is longer than my commute.')

    global.fetch.mockResolvedValueOnce(
      jsonResponse({ id: 'r1', status: 'pending', message: 'queued' })
    )
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(global.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/roast-wall',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          text: 'The stack list is longer than my commute.',
          target: 'AI & Full-Stack',
        }),
      })
    )
    expect(wrapper.text()).toContain('Ugali')
  })

  it('opens the case-study detail modal when the card body is clicked', async () => {
    await wrapper.find('.swipe-card').trigger('click')
    expect(wrapper.text()).toContain('CASE STUDY')
    expect(wrapper.text()).toContain('FastAPI plus pgvector retrieval with citations.')
  })
})
