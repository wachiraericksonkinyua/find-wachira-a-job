import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import AdminDashboard from '@/pages/AdminDashboard.vue'

const STATS = {
  events: { page_view: 12, cv_open: 3 },
  total_events: 15,
  total_bookings: 4,
  board: { approved: 2, pending: 1, total: 3 },
  redteam: { total_attempts: 9, blocked_attacks: 6, successful_breaks: 1 },
}

const ROASTS = [
  {
    id: 'r1',
    text: 'The portfolio is strong but the intro should get to the point faster.',
    advice: 'Lead with proof.',
    status: 'pending',
    created_at: '2026-11-07T10:00:00+00:00',
  },
  {
    id: 'r2',
    text: 'Great security demos.',
    advice: null,
    status: 'approved',
    created_at: '2026-11-07T09:00:00+00:00',
  },
]

const BOARD = [
  {
    id: 'b1',
    name: 'Njeri Wambui',
    role: 'Data Analyst',
    pitch: 'SQL and Python analyst open to junior roles.',
    link: 'https://github.com/njeri',
    status: 'pending',
    created_at: '2026-11-07T08:00:00+00:00',
  },
]

const PROJECTS = [
  {
    id: 'p1',
    title: 'Warehouse Signal API',
    problem: 'Stockouts were invisible.',
    build: 'FastAPI + PostgreSQL.',
    outcome: 'Alerts before stockouts.',
    stack: ['FastAPI', 'PostgreSQL'],
    repo_url: 'https://github.com/example/warehouse',
    demo_url: 'https://example.com/demo',
  },
]

const LOGS = [
  {
    id: 1,
    created_at: '2026-11-07T11:00:00+00:00',
    actor: 'owner',
    action: 'project.create',
    target: 'p1',
    detail: 'Added project: Warehouse Signal API',
  },
]

function json(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }
}

function mockAdminApi() {
  const fetchMock = vi.fn().mockImplementation((url: string) => {
    const target = String(url)
    if (target.endsWith('/api/admin/stats')) return Promise.resolve(json(STATS))
    if (target.includes('/api/admin/roasts/') && target.endsWith('/approve')) {
      return Promise.resolve(json({ id: 'r1', status: 'approved' }))
    }
    if (target.includes('/api/admin/roasts/') && target.endsWith('/reject')) {
      return Promise.resolve(json({ id: 'r1', status: 'rejected' }))
    }
    if (target.includes('/api/admin/roasts')) return Promise.resolve(json(ROASTS))
    if (target.includes('/api/admin/board')) return Promise.resolve(json(BOARD))
    if (target.includes('/api/admin/projects')) return Promise.resolve(json(PROJECTS))
    if (target.includes('/api/admin/logs')) return Promise.resolve(json(LOGS))
    return Promise.resolve(json({}))
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('AdminDashboard.vue', () => {
  let wrapper: any

  beforeEach(() => {
    sessionStorage.clear()
    vi.restoreAllMocks()
    mockAdminApi()
  })

  afterEach(() => {
    wrapper?.unmount()
    sessionStorage.clear()
    vi.unstubAllGlobals()
  })

  it('unlocks with a stored key and renders overview stats', async () => {
    sessionStorage.setItem('fwaj_admin_key', 'test-key')
    wrapper = mount(AdminDashboard, {
      global: { stubs: { RouterLink: true } },
    })
    await flushPromises()

    expect(wrapper.vm.unlocked).toBe(true)
    expect(wrapper.text()).toContain('ADMIN DASHBOARD')
    expect(wrapper.text()).toContain('TOTAL EVENTS')
    expect(wrapper.text()).toContain('15')
    expect(wrapper.text()).toContain('PENDING ROASTS')
    expect(wrapper.text()).toContain('PENDING BOARD')
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/admin/stats'),
      expect.objectContaining({
        headers: expect.objectContaining({ 'X-Admin-Key': 'test-key' }),
      })
    )
  })

  it('moderates a pending roast and updates its status', async () => {
    sessionStorage.setItem('fwaj_admin_key', 'test-key')
    wrapper = mount(AdminDashboard, {
      global: { stubs: { RouterLink: true } },
    })
    await flushPromises()

    const roastTab = wrapper.findAll('button').find((button: any) => button.text() === 'ROASTS')
    await roastTab.trigger('click')
    expect(wrapper.text()).toContain('The portfolio is strong')

    const approve = wrapper.findAll('button').find((button: any) => button.text() === 'APPROVE')
    await approve.trigger('click')
    await flushPromises()

    expect(wrapper.vm.roasts[0].status).toBe('approved')
  })

  it('shows the project management form and custom projects', async () => {
    sessionStorage.setItem('fwaj_admin_key', 'test-key')
    wrapper = mount(AdminDashboard, {
      global: { stubs: { RouterLink: true } },
    })
    await flushPromises()

    const projectsTab = wrapper.findAll('button').find((button: any) => button.text() === 'PROJECTS')
    await projectsTab.trigger('click')

    expect(wrapper.text()).toContain('ADD PROJECT')
    expect(wrapper.text()).toContain('Warehouse Signal API')
    expect(wrapper.text()).toContain('Saving regenerates the downloadable PDF resume')
  })

  it('shows an auth error for a rejected key', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(json({ detail: 'Invalid admin key.' }, 401))
    )
    sessionStorage.setItem('fwaj_admin_key', 'wrong-key')
    wrapper = mount(AdminDashboard, {
      global: { stubs: { RouterLink: true } },
    })
    await flushPromises()

    expect(wrapper.vm.unlocked).toBe(false)
    expect(wrapper.text()).toContain('Invalid admin key.')
  })
})
