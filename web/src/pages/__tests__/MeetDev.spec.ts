import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import MeetDev from '@/pages/MeetDev.vue'

describe('MeetDev.vue', () => {
  it('renders the dev bio, education, experience, stack, and contact links', () => {
    const wrapper = mount(MeetDev)

    expect(wrapper.text()).toContain('ERICKSON KINYUA WACHIRA')
    expect(wrapper.text()).toContain('B.Sc. Information Technology')
    expect(wrapper.text()).toContain('Karatina University')
    expect(wrapper.text()).toContain('2027')
    expect(wrapper.text()).toContain('Judiciary of Kenya')
    expect(wrapper.text()).toContain('Nairobi, Kenya')
    expect(wrapper.text()).toContain('FastAPI')
    expect(wrapper.text()).toContain('Vue 3')

    const links = wrapper.findAll('a').map((link) => link.attributes('href'))
    expect(links).toContain('https://github.com/wachiraericksonkinyua')
    expect(links).toContain('https://www.linkedin.com/in/erickson-kinyua-28b7b2327')
    expect(links.some((href) => href?.endsWith('/api/resume'))).toBe(true)

    wrapper.unmount()
  })
})
