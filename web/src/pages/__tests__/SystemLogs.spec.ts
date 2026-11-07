import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import SystemLogs from '@/pages/SystemLogs.vue'

const LOGS = {
  generated_at: '2026-11-07T12:00:00+00:00',
  health: { status: 'ok', database: 'postgres' },
  vector_store: 'pgvector',
  indexed_chunks: 12,
  llm_providers: ['groq', 'gemini'],
  security_controls: ['one', 'two', 'three'],
  rate_limits: [
    { name: 'llm', max_requests: 5, window_seconds: 60, active_clients: 2 },
    { name: 'board', max_requests: 20, window_seconds: 60, active_clients: 0 },
  ],
  requests: [
    {
      request_id: 'abc12345deadbeef',
      method: 'GET',
      path: '/api/projects',
      status: 200,
      duration_ms: 12.4,
      created_at: '2026-11-07T12:00:00+00:00',
    },
    {
      request_id: 'bad99999deadbeef',
      method: 'POST',
      path: '/api/admin/projects',
      status: 401,
      duration_ms: 2.1,
      created_at: '2026-11-07T12:00:01+00:00',
    },
  ],
}

describe('SystemLogs.vue', () => {
  let wrapper: any

  beforeEach(() => {
    vi.restoreAllMocks()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => LOGS })
    )
  })

  afterEach(() => {
    wrapper?.unmount()
    vi.unstubAllGlobals()
  })

  it('renders health, vector, rate limits, and the request feed', async () => {
    wrapper = mount(SystemLogs)
    await flushPromises()

    expect(wrapper.text()).toContain('SYSTEM LOGS')
    expect(wrapper.text()).toContain('ONLINE')
    expect(wrapper.text()).toContain('pgvector')
    expect(wrapper.text()).toContain('12 chunks indexed')
    expect(wrapper.text()).toContain('GROQ + GEMINI')
    expect(wrapper.text()).toContain('llm')
    expect(wrapper.text()).toContain('5 / 60s')
    expect(wrapper.text()).toContain('/api/projects')
    expect(wrapper.text()).toContain('12.4ms')
  })

  it('shows an error when telemetry is unreachable', async () => {
    ;(global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ detail: 'telemetry offline' }),
    })

    wrapper = mount(SystemLogs)
    await flushPromises()

    expect(wrapper.text()).toContain('telemetry offline')
  })
})
