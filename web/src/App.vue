<script setup>
import { onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { trackEvent } from './composables/useAnalytics'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const route = useRoute()
const mobileOpen = ref(false)
const apiOnline = ref(false)

const primaryNav = [
  { to: '/projects', label: 'PROJECTS' },
  { to: '/match', label: 'MATCH' },
  { to: '/wall', label: 'WALL' },
  { to: '/lab', label: 'LAB' },
  { to: '/board', label: 'BOARD' },
  { to: '/apply', label: 'APPLY' },
]

const secondaryNav = [
  { to: '/meet', label: 'MEET' },
  { to: '/logs', label: 'LOGS' },
  { to: '/admin', label: 'ADMIN' },
]

watch(
  () => route.fullPath,
  () => {
    mobileOpen.value = false
    trackEvent('page_view')
  }
)

onMounted(async () => {
  trackEvent('page_view')
  try {
    const response = await fetch(`${API_URL}/health`)
    apiOnline.value = response.ok
  } catch {
    apiOnline.value = false
  }
})
</script>

<template>
  <div class="min-h-screen pb-20">
    <a href="#main-content" class="skip-link">Skip to content</a>

    <header class="site-header">
      <div class="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3">
        <RouterLink to="/" class="group flex items-center gap-2" aria-label="Find Wachira a Job home">
          <span class="flex h-8 w-8 items-center justify-center border border-[#19E3FF]/60 bg-[#0D2230] font-orbitron text-xs font-black text-[#19E3FF]">
            FW
          </span>
          <span class="hidden sm:block">
            <span class="block font-orbitron text-xs font-black tracking-wider text-[#E6F1FF]">
              FIND WACHIRA A JOB
            </span>
            <span class="block font-mono-tech text-[9px] text-[#8FA6C8]">
              AI + FULL-STACK PORTFOLIO
            </span>
          </span>
        </RouterLink>

        <nav class="hidden items-center gap-1 lg:flex" aria-label="Primary navigation">
          <RouterLink
            v-for="item in primaryNav"
            :key="item.to"
            :to="item.to"
            class="nav-link"
            active-class="nav-link-active"
          >
            {{ item.label }}
          </RouterLink>
        </nav>

        <div class="flex items-center gap-2">
          <span class="hidden items-center gap-1.5 md:flex">
            <span
              class="h-2 w-2 rounded-full"
              :class="apiOnline ? 'bg-[#3DF5A6]' : 'bg-[#FF4D8D]'"
              aria-hidden="true"
            />
            <span class="font-mono-tech text-[9px] text-[#8FA6C8]">
              API {{ apiOnline ? 'ONLINE' : 'OFFLINE' }}
            </span>
          </span>

          <nav class="hidden items-center gap-1 md:flex" aria-label="Secondary navigation">
            <RouterLink
              v-for="item in secondaryNav"
              :key="item.to"
              :to="item.to"
              class="nav-link nav-link-muted"
              active-class="nav-link-active"
            >
              {{ item.label }}
            </RouterLink>
          </nav>

          <RouterLink to="/contact" class="hidden sm:inline-flex btn-primary-small">
            BOOK
          </RouterLink>

          <button
            type="button"
            class="mobile-menu-button lg:hidden"
            :aria-expanded="mobileOpen"
            aria-controls="mobile-navigation"
            @click="mobileOpen = !mobileOpen"
          >
            <span class="sr-only">Toggle navigation</span>
            {{ mobileOpen ? '✕' : '☰' }}
          </button>
        </div>
      </div>

      <nav
        v-if="mobileOpen"
        id="mobile-navigation"
        class="border-t border-[#22345E] bg-[#0A0F1F] px-4 py-3 lg:hidden"
        aria-label="Mobile navigation"
      >
        <div class="grid gap-1">
          <RouterLink
            v-for="item in [...primaryNav, ...secondaryNav, { to: '/contact', label: 'CONTACT' }]"
            :key="item.to"
            :to="item.to"
            class="nav-link"
            active-class="nav-link-active"
          >
            {{ item.label }}
          </RouterLink>
        </div>
      </nav>
    </header>

    <main id="main-content">
      <RouterView />
    </main>

    <footer class="mt-16 border-t border-[#22345E] bg-[#070D1B]">
      <div class="mx-auto grid max-w-7xl gap-5 px-4 py-8 md:grid-cols-3">
        <div>
          <p class="font-orbitron text-sm font-bold text-[#E6F1FF]">FIND WACHIRA A JOB</p>
          <p class="mt-2 text-xs text-[#8FA6C8]">
            A recruiter-facing AI portfolio by Erickson Kinyua Wachira.
            Nairobi, Kenya.
          </p>
        </div>
        <div>
          <p class="font-mono-tech text-[10px] text-[#3DF5A6] mb-2">EXPLORE</p>
          <div class="grid grid-cols-2 gap-1">
            <RouterLink v-for="item in [...primaryNav, ...secondaryNav]" :key="item.to" :to="item.to" class="footer-link">
              {{ item.label }}
            </RouterLink>
          </div>
        </div>
        <div>
          <p class="font-mono-tech text-[10px] text-[#FFC857] mb-2">CONTACT</p>
          <a href="mailto:ericksonkinyua681@gmail.com" class="footer-link block">EMAIL</a>
          <a href="https://github.com/wachiraericksonkinyua" target="_blank" rel="noopener noreferrer" class="footer-link block">GITHUB</a>
          <a href="https://www.linkedin.com/in/erickson-kinyua-28b7b2327" target="_blank" rel="noopener noreferrer" class="footer-link block">LINKEDIN</a>
        </div>
      </div>
    </footer>
  </div>
</template>
