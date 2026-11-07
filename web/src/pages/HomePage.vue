<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import CinematicLanding from '../components/CinematicLanding.vue'
import BookSection from '../components/BookSection.vue'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const stats = ref({
  projects: '—',
  chunks: '—',
  levels: 4,
  controls: 8,
})

const pathways = [
  {
    to: '/projects',
    code: '01',
    title: 'CASE STUDIES',
    body: 'Open the project deck, inspect a build, or leave a reaction.',
  },
  {
    to: '/wall',
    code: '02',
    title: 'ROAST WALL',
    body: 'Anonymous, moderated recruiter feedback. No company names exposed.',
  },
  {
    to: '/lab',
    code: '03',
    title: 'RED TEAM LAB',
    body: 'Try four prompt-injection defenses and capture the fake flags.',
  },
  {
    to: '/apply',
    code: '04',
    title: 'APPLY ASSISTANT',
    body: 'SSRF-hardened job analysis and human-reviewed cover-letter drafts.',
  },
  {
    to: '/meet',
    code: '05',
    title: 'MEET THE DEV',
    body: 'The short version: who Erickson is, what he builds, and how to reach him.',
  },
]

onMounted(async () => {
  try {
    const [telemetry, projects] = await Promise.allSettled([
      fetch(`${API_URL}/api/telemetry`).then((res) => (res.ok ? res.json() : null)),
      fetch(`${API_URL}/api/projects`).then((res) => (res.ok ? res.json() : null)),
    ])
    if (telemetry.status === 'fulfilled' && telemetry.value) {
      stats.value.chunks = telemetry.value.indexed_chunks ?? '—'
      stats.value.controls = telemetry.value.security_controls?.length ?? 8
    }
    if (projects.status === 'fulfilled' && Array.isArray(projects.value)) {
      stats.value.projects = projects.value.length
    }
  } catch {
    // The home page still works if the API is offline.
  }
})
</script>

<template>
  <div class="page-shell">
    <CinematicLanding />

    <section class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 mb-10" aria-label="Quick stats">
      <div class="stat-card">
        <p class="stat-label">SHIPPED PROJECTS</p>
        <p class="stat-value">{{ stats.projects }}</p>
      </div>
      <div class="stat-card">
        <p class="stat-label">RAG CHUNKS</p>
        <p class="stat-value">{{ stats.chunks }}</p>
      </div>
      <div class="stat-card">
        <p class="stat-label">CTF LEVELS</p>
        <p class="stat-value">{{ stats.levels }}</p>
      </div>
      <div class="stat-card">
        <p class="stat-label">SECURITY CONTROLS</p>
        <p class="stat-value">{{ stats.controls }}</p>
      </div>
    </section>

    <section class="grid gap-6 lg:grid-cols-[1.15fr_0.85fr] mb-12">
      <div class="panel p-6 md:p-8">
        <p class="page-kicker text-[#19E3FF]">THE 10-SECOND PITCH</p>
        <h1 class="font-orbitron text-3xl md:text-5xl font-black leading-tight mt-2">
          FIND <span class="bg-[#19E3FF] text-[#06101F] px-2">WACHIRA</span> A JOB
        </h1>
        <p class="text-[#A9BCD9] text-lg mt-4 max-w-2xl">
          Final-year B.Sc. IT engineer at Karatina University building production-style
          backends with <b class="text-[#E6F1FF]">FastAPI & PostgreSQL</b>, modern
          <b class="text-[#E6F1FF]">Vue.js</b> interfaces, and hardened
          <b class="text-[#E6F1FF]">AI/LLM pipelines</b>.
        </p>
        <div class="flex flex-wrap gap-3 mt-6">
          <RouterLink to="/projects" class="btn-primary">VIEW PROJECTS →</RouterLink>
          <RouterLink to="/match" class="btn-secondary">RUN A JD MATCH</RouterLink>
          <RouterLink to="/contact" class="btn-ghost">BOOK AN INTERVIEW</RouterLink>
        </div>
      </div>

      <div class="panel p-6 md:p-8">
        <p class="page-kicker text-[#3DF5A6]">WHY THIS SITE IS DIFFERENT</p>
        <ul class="mt-4 grid gap-3 text-sm text-[#A9BCD9]">
          <li class="border-l-2 border-[#19E3FF] pl-3">
            Claims are grounded in real resume and project data, not model memory.
          </li>
          <li class="border-l-2 border-[#3DF5A6] pl-3">
            Every interactive feature has a deterministic offline fallback.
          </li>
          <li class="border-l-2 border-[#FFC857] pl-3">
            Security is demonstrated: prompt-injection CTF, SSRF checks, moderation.
          </li>
          <li class="border-l-2 border-[#FF4D8D] pl-3">
            Human-in-the-loop by design: drafts and actions are reviewed, never auto-sent.
          </li>
        </ul>
      </div>
    </section>

    <section class="mb-12" aria-labelledby="pathways-title">
      <div class="flex flex-wrap items-end justify-between gap-3 mb-4">
        <div>
          <p class="page-kicker text-[#FFC857]">NO ENDLESS SCROLLING</p>
          <h2 id="pathways-title" class="page-title">PICK A PATH</h2>
        </div>
        <RouterLink to="/meet" class="font-mono-tech text-xs text-[#19E3FF] hover:text-[#3DF5A6]">
          MEET THE DEV →
        </RouterLink>
      </div>

      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <RouterLink
          v-for="pathway in pathways"
          :key="pathway.to"
          :to="pathway.to"
          class="path-card group"
        >
          <span class="font-pixel text-[9px] text-[#19E3FF]">{{ pathway.code }}</span>
          <h3 class="font-orbitron text-lg font-bold mt-2 group-hover:text-[#19E3FF]">
            {{ pathway.title }}
          </h3>
          <p class="text-sm text-[#A9BCD9] mt-2 leading-relaxed">{{ pathway.body }}</p>
          <span class="font-mono-tech text-[10px] text-[#3DF5A6] mt-4">OPEN →</span>
        </RouterLink>
      </div>
    </section>

    <BookSection />
  </div>
</template>
