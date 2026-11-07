<script setup>
import { computed, onMounted, ref } from 'vue'
import { useStream } from '../composables/useStream'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const projects = ref([])
const loading = ref(true)
const error = ref(null)
const selectedProject = ref(null)
const deckIndex = ref(0)
const reactionError = ref(null)
let touchStartX = 0

const monkeyStates = ref({})

const currentProject = computed(() => projects.value[deckIndex.value] || null)

onMounted(async () => {
  try {
    const response = await fetch(`${API_URL}/api/projects`)
    if (!response.ok) throw new Error('Failed to load projects')
    projects.value = await response.json()
    projects.value.forEach((project) => {
      monkeyStates.value[project.id] = useStream()
    })
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})

const streamValue = (id, key) => {
  const value = monkeyStates.value[id]?.[key]
  return value && typeof value === 'object' && 'value' in value ? value.value : value
}

function openProject(project) {
  selectedProject.value = project
}

function closeProject() {
  selectedProject.value = null
}

function nextProject() {
  if (!projects.value.length) return
  deckIndex.value = (deckIndex.value + 1) % projects.value.length
}

function previousProject() {
  if (!projects.value.length) return
  deckIndex.value = (deckIndex.value - 1 + projects.value.length) % projects.value.length
}

function onTouchStart(event) {
  touchStartX = event.changedTouches?.[0]?.clientX ?? 0
}

function onTouchEnd(event) {
  const endX = event.changedTouches?.[0]?.clientX ?? touchStartX
  const delta = endX - touchStartX
  if (Math.abs(delta) < 45) return
  if (delta < 0) nextProject()
  else previousProject()
}

async function reactToProject(project, reaction) {
  reactionError.value = null
  try {
    const response = await fetch(`${API_URL}/api/projects/${project.id}/reactions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reaction }),
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw new Error(data?.detail || `Reaction failed (HTTP ${response.status}).`)
    }
    project.reactions = data
  } catch (err) {
    reactionError.value = err.message || 'Could not save that reaction.'
  }
}

function askMonkey(project) {
  const stream = monkeyStates.value[project.id]
  if (!stream) return
  if (streamValue(project.id, 'streaming')) stream.stopStream()
  stream.startStream(`${API_URL}/api/projects/${project.id}/inspect`)
}
</script>

<template>
  <section id="projects">
    <p v-if="loading" class="font-mono-tech text-xs text-[#19E3FF]">Loading project deck...</p>
    <p v-else-if="error" role="alert" class="font-mono-tech text-xs text-[#FF4D8D]">{{ error }}</p>

    <template v-else>
      <!-- Swipe deck -->
      <div v-if="currentProject" class="panel p-5 md:p-7 mb-8">
        <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div>
            <p class="page-kicker text-[#19E3FF]">SWIPE DECK</p>
            <h2 class="font-orbitron text-xl font-bold">PROJECT CASE STUDIES</h2>
          </div>
          <span class="font-mono-tech text-[10px] text-[#8FA6C8]">
            {{ deckIndex + 1 }} / {{ projects.length }}
          </span>
        </div>

        <div
          class="border border-[#22345E] bg-[#050914] p-5"
          tabindex="0"
          @keydown.left.prevent="previousProject"
          @keydown.right.prevent="nextProject"
          @touchstart.passive="onTouchStart"
          @touchend.passive="onTouchEnd"
        >
          <h3 class="font-orbitron text-2xl md:text-3xl font-bold">{{ currentProject.title }}</h3>
          <div class="flex flex-wrap gap-2 mt-3">
            <span
              v-for="tech in currentProject.stack"
              :key="tech"
              class="px-2 py-0.5 border border-[#22345E] bg-[#0A0F1F] font-mono-tech text-[10px] text-[#19E3FF]"
            >
              {{ tech }}
            </span>
          </div>
          <p class="text-sm text-[#A9BCD9] leading-relaxed mt-4 max-w-3xl">
            {{ currentProject.problem }}
          </p>

          <div class="flex flex-wrap items-center gap-2 mt-5">
            <button
              type="button"
              class="btn-primary"
              @click.stop="reactToProject(currentProject, 'heart')"
            >
              ♥ {{ currentProject.reactions?.heart || 0 }}
            </button>
            <button
              type="button"
              class="btn-ghost"
              @click.stop="reactToProject(currentProject, 'roast')"
            >
              🔥 {{ currentProject.reactions?.roast || 0 }}
            </button>
            <button type="button" class="btn-secondary" @click="openProject(currentProject)">
              OPEN CASE STUDY
            </button>
            <span class="flex gap-2 ml-auto">
              <button type="button" class="btn-secondary" @click="previousProject">←</button>
              <button type="button" class="btn-secondary" @click="nextProject">→</button>
            </span>
          </div>
          <p v-if="reactionError" role="alert" class="mt-3 font-mono-tech text-[10px] text-[#FF4D8D]">
            {{ reactionError }}
          </p>
        </div>
      </div>

      <!-- Grid -->
      <div class="flex items-end justify-between gap-3 mb-4">
        <div>
          <p class="page-kicker text-[#3DF5A6]">ALL BUILDS</p>
          <h2 class="font-orbitron text-2xl font-bold">PROJECT GRID</h2>
        </div>
        <span class="font-mono-tech text-[10px] text-[#8FA6C8]">{{ projects.length }} projects</span>
      </div>

      <div class="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
        <article
          v-for="project in projects"
          :key="project.id"
          class="panel p-5 flex flex-col cursor-pointer hover:border-[#19E3FF]/70 transition-colors"
          tabindex="0"
          role="button"
          :aria-label="`Open case study for ${project.title}`"
          @click="openProject(project)"
          @keydown.enter.prevent="openProject(project)"
          @keydown.space.prevent="openProject(project)"
        >
          <h3 class="font-orbitron text-lg font-bold">{{ project.title }}</h3>
          <div class="flex flex-wrap gap-1.5 mt-2">
            <span
              v-for="tech in project.stack.slice(0, 4)"
              :key="tech"
              class="px-1.5 py-0.5 border border-[#22345E] font-mono-tech text-[9px] text-[#19E3FF]"
            >
              {{ tech }}
            </span>
          </div>
          <p class="text-xs text-[#A9BCD9] leading-relaxed mt-3 line-clamp-3 flex-grow">
            {{ project.problem }}
          </p>
          <div class="flex items-center justify-between gap-2 mt-4">
            <div class="flex gap-1">
              <button
                type="button"
                class="px-2 py-1 border border-[#3DF5A6]/50 font-mono-tech text-[10px] text-[#3DF5A6] hover:bg-[#0D2A24]"
                :aria-label="`Heart ${project.title}`"
                @click.stop="reactToProject(project, 'heart')"
              >
                ♥ {{ project.reactions?.heart || 0 }}
              </button>
              <button
                type="button"
                class="px-2 py-1 border border-[#FF4D8D]/50 font-mono-tech text-[10px] text-[#FF4D8D] hover:bg-[#2A1220]"
                :aria-label="`Roast ${project.title}`"
                @click.stop="reactToProject(project, 'roast')"
              >
                🔥 {{ project.reactions?.roast || 0 }}
              </button>
            </div>
            <span class="font-mono-tech text-[10px] text-[#19E3FF]">OPEN →</span>
          </div>
        </article>
      </div>
    </template>

    <!-- Immersive detail modal -->
    <div
      v-if="selectedProject"
      class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/80 p-4 pt-10"
      role="presentation"
      @click.self="closeProject"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="project-modal-title"
        class="panel w-full max-w-3xl p-5 md:p-7"
      >
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p class="page-kicker text-[#19E3FF]">CASE STUDY</p>
            <h2 id="project-modal-title" class="font-orbitron text-2xl md:text-3xl font-bold">
              {{ selectedProject.title }}
            </h2>
          </div>
          <button type="button" class="btn-secondary" @click="closeProject">CLOSE</button>
        </div>

        <div class="flex flex-wrap gap-2 mt-3">
          <span
            v-for="tech in selectedProject.stack"
            :key="tech"
            class="px-2 py-0.5 border border-[#22345E] bg-[#0A0F1F] font-mono-tech text-[10px] text-[#19E3FF]"
          >
            {{ tech }}
          </span>
        </div>

        <div class="grid gap-4 mt-5">
          <section>
            <h3 class="font-pixel text-[10px] text-[#FFC857] mb-1">PROBLEM</h3>
            <p class="text-sm text-[#D7E4F8] leading-relaxed">{{ selectedProject.problem }}</p>
          </section>
          <section>
            <h3 class="font-pixel text-[10px] text-[#3DF5A6] mb-1">BUILD</h3>
            <p class="text-sm text-[#D7E4F8] leading-relaxed">{{ selectedProject.build }}</p>
          </section>
          <section>
            <h3 class="font-pixel text-[10px] text-[#19E3FF] mb-1">OUTCOME</h3>
            <p class="text-sm text-[#D7E4F8] leading-relaxed">{{ selectedProject.outcome }}</p>
          </section>
        </div>

        <div class="flex flex-wrap items-center gap-2 mt-5">
          <button type="button" class="btn-primary" @click="reactToProject(selectedProject, 'heart')">
            ♥ HEART {{ selectedProject.reactions?.heart || 0 }}
          </button>
          <button type="button" class="btn-ghost" @click="reactToProject(selectedProject, 'roast')">
            🔥 ROAST {{ selectedProject.reactions?.roast || 0 }}
          </button>
          <a
            v-if="selectedProject.demo_url"
            :href="selectedProject.demo_url"
            target="_blank"
            rel="noopener noreferrer"
            class="btn-secondary"
          >
            VERIFY LIVE ↗
          </a>
          <a
            v-if="selectedProject.repo_url"
            :href="selectedProject.repo_url"
            target="_blank"
            rel="noopener noreferrer"
            class="btn-secondary"
          >
            VIEW SOURCE ↗
          </a>
          <span
            v-if="!selectedProject.demo_url && !selectedProject.repo_url"
            class="font-mono-tech text-[10px] text-[#8FA6C8]"
          >
            Verification link not added yet.
          </span>
        </div>

        <div class="mt-5 border-t border-[#22345E] pt-4">
          <button type="button" class="btn-secondary" @click="askMonkey(selectedProject)">
            {{ streamValue(selectedProject.id, 'streaming') ? 'MONKEY IS THINKING...' : 'ASK MONKEY ABOUT THIS BUILD' }}
          </button>
          <div
            v-if="streamValue(selectedProject.id, 'text') || streamValue(selectedProject.id, 'streaming') || streamValue(selectedProject.id, 'error')"
            class="mt-3 border border-[#22345E] bg-[#02060F] p-3 font-mono-tech text-xs text-[#D7E4F8]"
          >
            <span v-if="streamValue(selectedProject.id, 'error')" class="text-[#FF4D8D]">
              {{ streamValue(selectedProject.id, 'error') }}
            </span>
            <span v-else>{{ streamValue(selectedProject.id, 'text') || '...' }}</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
