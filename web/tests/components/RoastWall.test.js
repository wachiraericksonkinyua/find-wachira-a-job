import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import RoastWall from '@/components/RoastWall.vue'

const ROASTS = [
  {
    id: '1',
    author: '@anonymous_dev',
    target: 'Portfolio UI',
    text: 'This portfolio has more features than my last startup.',
    advice: null,
    created_at: '2026-01-01T10:00:00Z',
  },
  {
    id: '2',
    author: '@anonymous_dev',
    target: 'Printer Whisperer',
    text: 'The printer jokes are doing a lot of heavy lifting.',
    advice: 'Keep them.',
    created_at: '2026-01-02T10:00:00Z',
  },
]

function jsonResponse(body) {
  return { ok: true, json: async () => body }
}

describe('RoastWall', () => {
  let wrapper

  beforeEach(async () => {
    vi.resetAllMocks()
    global.fetch.mockResolvedValueOnce(jsonResponse(ROASTS))
    wrapper = mount(RoastWall)
    await flushPromises()
  })

  afterEach(() => {
    wrapper.unmount()
  })

  it('renders approved roasts with anonymous authors and target tags', () => {
    expect(wrapper.text()).toContain('@anonymous_dev')
    expect(wrapper.text()).toContain('TARGET: Portfolio UI')
    expect(wrapper.text()).toContain('TARGET: Printer Whisperer')
    expect(wrapper.text()).toContain('This portfolio has more features')
    expect(wrapper.text()).toContain('2 roasts')
  })

  it('offers preset target tags and a custom option', () => {
    const options = wrapper.findAll('option').map((option) => option.text())
    expect(options).toContain('Portfolio UI')
    expect(options).toContain('Custom target...')
  })

  it('submits an anonymous roast with the selected target', async () => {
    global.fetch.mockResolvedValueOnce(
      jsonResponse({
        id: 'new',
        status: 'pending',
        message:
          'Sent to the moderation queue! Once Erickson approves it, it goes live on the wall.',
      })
    )

    await wrapper.find('textarea').setValue('That resume font is a war crime.')
    await wrapper.find('select').setValue('AI Lab')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(global.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/roast-wall',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          text: 'That resume font is a war crime.',
          target: 'AI Lab',
        }),
      })
    )
    expect(wrapper.text()).toContain(
      'Sent to the moderation queue! Once Erickson approves it, it goes live on the wall.'
    )
  })

  it('accepts a custom target tag', async () => {
    global.fetch.mockResolvedValueOnce(
      jsonResponse({ id: 'new', status: 'pending', message: 'queued' })
    )

    wrapper.vm.form.target = '__custom__'
    await wrapper.vm.$nextTick()
    const customInput = wrapper.find('input[type="text"]')
    await customInput.setValue('That landing page')
    await wrapper.find('textarea').setValue('Too many colors, pick three.')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(global.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/roast-wall',
      expect.objectContaining({
        body: JSON.stringify({
          text: 'Too many colors, pick three.',
          target: 'That landing page',
        }),
      })
    )
  })
})
