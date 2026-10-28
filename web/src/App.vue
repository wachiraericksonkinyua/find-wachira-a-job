<script setup>
import { computed, ref, onMounted } from 'vue'
import Pet from './components/Pet.vue'
import Projects from './components/Projects.vue'
import Match from './components/Match.vue'
import Interrogate from './components/Interrogate.vue'
import ExcuseBuster from './components/ExcuseBuster.vue'
import BookSection from './components/BookSection.vue'

// Reactive state variables
const apiOnline = ref(false)
const professionalMode = ref(false)

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const telemetry = ref(null)

const vectorLabel = computed(() => {
  if (!telemetry.value) return 'VECTOR DB: SYNCING...'
  const chunks = telemetry.value.indexed_chunks ?? 0
  return telemetry.value.vector_store === 'pgvector'
    ? `VECTOR DB: PGVECTOR (${chunks} CHUNKS)`
    : 'VECTOR DB: LOCAL COSINE'
})

const llmLabel = computed(() => {
  const providers = telemetry.value?.llm_providers || []
  if (!providers.length) return 'LLM: NOT CONFIGURED'
  return `LLM: ${providers.join(' + ').toUpperCase()} FALLBACK`
})

const securityLabel = computed(() => 'SECURITY: OWASP LLM01 + RATE LIMITED')

// Lifecycle Hook: Runs automatically when the component mounts on the screen
onMounted(async () => {
  try {
    const res = await fetch(`${API_URL}/api/telemetry`)
    if (!res.ok) throw new Error(`Telemetry failed (HTTP ${res.status})`)
    const data = await res.json()
    telemetry.value = data
    apiOnline.value = data.status === 'ok'
  } catch (err) {
    console.error('Telemetry unavailable, trying health check:', err)
    try {
      const res = await fetch(`${API_URL}/health`)
      if (!res.ok) throw new Error(`Health failed (HTTP ${res.status})`)
      const data = await res.json()
      apiOnline.value = data.status === 'ok'
    } catch (healthErr) {
      console.error('Backend offline:', healthErr)
      apiOnline.value = false
    }
  }
})
</script>

<template>
  <div class="min-h-screen pb-24">
    
    <!-- Top Sticky Navigation Bar -->
    <header class="border-b border-[#22345E] bg-[#0A0F1F]/90 sticky top-0 z-10 backdrop-blur">
      <div class="max-w-4xl mx-auto px-5 py-3 flex items-center justify-between">
        
        <!-- FastAPI Server Health Indicator -->
        <div class="flex items-center gap-2">
          <span :class="['w-2.5 h-2.5 rounded-full', apiOnline ? 'bg-[#3DF5A6]' : 'bg-[#FF4D8D]']" />
          <span class="font-mono-tech text-xs text-[#8FA6C8]">
            API: {{ apiOnline ? 'ONLINE' : 'OFFLINE' }}
          </span>
        </div>

        <!-- Playful / Professional Mode Toggle Button -->
        <button
          @click="professionalMode = !professionalMode"
          class="px-3 py-1 border border-[#22345E] bg-[#101A33] text-xs font-mono-tech text-[#E6F1FF] cursor-pointer hover:border-[#19E3FF]"
        >
          MODE: {{ professionalMode ? 'PROFESSIONAL 👔' : 'PLAYFUL 👾' }}
        </button>
      </div>
    </header>

    <!-- Main Content Area -->
    <main class="max-w-4xl mx-auto px-5 pt-10">
      <div class="mb-6 flex flex-wrap gap-2 font-mono-tech text-[10px]">
        <span class="px-2 py-1 border border-[#19E3FF] bg-[#0D2230] text-[#19E3FF]">
          {{ vectorLabel }}
        </span>
        <span class="px-2 py-1 border border-[#3DF5A6] bg-[#0D2A24] text-[#3DF5A6]">
          {{ llmLabel }}
        </span>
        <span class="px-2 py-1 border border-[#FFC857] bg-[#2A2410] text-[#FFC857]">
          {{ securityLabel }}
        </span>
      </div>

      <!-- 10-Second Recruiter Pitch (Above the Fold) -->
      <section class="mb-8">
        <p class="font-pixel text-[10px] text-[#19E3FF] mb-2">
          NAIROBI, KENYA // AVAILABLE FOR INTERNSHIPS & JUNIOR ROLES
        </p>
        <h1 class="font-orbitron text-3xl md:text-5xl font-black tracking-tight mb-3">
          FIND <span class="bg-[#19E3FF] text-[#06101F] px-2">WACHIRA</span> A JOB
        </h1>
        <p class="text-[#8FA6C8] text-lg max-w-2xl">
          Final-year B.Sc. IT Engineer building production backends with <b>FastAPI & PostgreSQL</b>, modern <b>Vue.js</b> interfaces, and hardened <b>AI/LLM pipelines</b>.
        </p>

        <!-- Quick Contact Links -->
        <nav aria-label="Contact links" class="mt-5 flex flex-wrap items-center gap-2">
          <a
            href="https://github.com/wachiraericksonkinyua"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub profile"
            class="group inline-flex focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#19E3FF] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0A0F1F]"
          >
            <span class="panel inline-flex items-center gap-2 px-3 py-2 font-mono-tech text-xs text-[#E6F1FF] transition-colors group-hover:border-[#19E3FF] group-hover:text-[#19E3FF]">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 .5C5.73.5.5 5.73.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.56 0-.27-.01-1.16-.02-2.1-3.2.7-3.88-1.54-3.88-1.54-.52-1.33-1.28-1.68-1.28-1.68-1.05-.72.08-.71.08-.71 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.55-.29-5.23-1.28-5.23-5.68 0-1.25.45-2.28 1.18-3.08-.12-.29-.51-1.46.11-3.05 0 0 .96-.31 3.15 1.18a10.9 10.9 0 0 1 5.74 0c2.19-1.49 3.15-1.18 3.15-1.18.62 1.59.23 2.76.11 3.05.73.8 1.18 1.83 1.18 3.08 0 4.41-2.69 5.39-5.25 5.67.41.35.77 1.04.77 2.1 0 1.52-.01 2.74-.01 3.11 0 .31.21.67.8.56A11.5 11.5 0 0 0 23.5 12C23.5 5.73 18.27.5 12 .5z" />
              </svg>
              GITHUB
            </span>
          </a>

          <a
            href="https://www.linkedin.com/in/erickson-kinyua-28b7b2327"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="LinkedIn profile"
            class="group inline-flex focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#19E3FF] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0A0F1F]"
          >
            <span class="panel inline-flex items-center gap-2 px-3 py-2 font-mono-tech text-xs text-[#E6F1FF] transition-colors group-hover:border-[#19E3FF] group-hover:text-[#19E3FF]">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M20.45 20.45h-3.55v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.13 1.45-2.13 2.94v5.67H9.37V9h3.41v1.56h.05c.47-.9 1.63-1.85 3.36-1.85 3.6 0 4.26 2.37 4.26 5.45v6.29zM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12zM7.12 20.45H3.56V9h3.56v11.45z" />
              </svg>
              LINKEDIN
            </span>
          </a>

          <a
            href="mailto:ericksonkinyua681@gmail.com"
            aria-label="Email ericksonkinyua681@gmail.com"
            class="group inline-flex focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#19E3FF] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0A0F1F]"
          >
            <span class="panel inline-flex items-center gap-2 px-3 py-2 font-mono-tech text-xs text-[#E6F1FF] transition-colors group-hover:border-[#19E3FF] group-hover:text-[#19E3FF]">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <rect x="3" y="5" width="18" height="14" rx="2" />
                <path d="m3 7 9 6 9-6" />
              </svg>
              EMAIL
            </span>
          </a>

          <a
            :href="`${API_URL}/api/resume`"
            download="wachira-erickson-kinyua-resume.pdf"
            aria-label="Download resume"
            class="group inline-flex focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#19E3FF] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0A0F1F]"
          >
            <span class="panel inline-flex items-center gap-2 px-3 py-2 font-mono-tech text-xs text-[#E6F1FF] transition-colors group-hover:border-[#19E3FF] group-hover:text-[#19E3FF]">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M12 3v12m0 0 4-4m-4 4-4-4" />
                <path d="M4 21h16" />
              </svg>
              RESUME
            </span>
          </a>
        </nav>
      </section>

      <!-- The Pet Component (Passes down the professionalMode property) -->
      <Pet :professionalMode="professionalMode" />
      <Projects />
      <Match />
      <Interrogate />
      <ExcuseBuster />

      <!-- Booking / contact target for the sticky CTA and the pet menu -->

      <BookSection />
    </main>

    <!-- Sticky Floating "Book Interview" Button -->
    <div class="fixed bottom-5 right-5 z-20">
      <a
        href="#book"
        class="panel inline-flex items-center gap-3 px-6 py-3 font-orbitron font-bold text-sm shadow-lg hover:opacity-90 transition-opacity"
        style="background: var(--leaf); color: #06101F;"
      >
        <span>BOOK INTERVIEW</span>
        <span class="font-pixel text-[10px]">→</span>
      </a>
    </div>

  </div>
</template>