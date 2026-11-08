<script setup>
import { computed, onMounted, ref } from 'vue'
import { useStream } from '../composables/useStream'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const projects = ref([])
const loading = ref(true)
const error = ref(null)
const selectedProject = ref(null)
const deckIndex = ref(0)
const viewMode = ref('swipe')
const reactionError = ref(null)
const monkeyStates = ref({})

const roastOpen = ref(false)
const roastDraft = ref('')
const roastBusy = ref(false)
const roastMessage = ref(null)
const roastError = ref(null)
let touchStartX = 0

const COMEBACKS = [
  'Ugali the Monkey ate that roast and asked for seconds. Noted, anonymous human.',
  'Ugali says: bold words from someone who has never debugged a printer at 2 AM.',
  'Ugali reviewed your roast, sighed, and added it to the moderation queue anyway.',
  'Ugali says fair point, then went back to judging your browser tabs.',
]

const currentProject = computed(() => projects.value[deckIndex.value] || null)
const deckProgress = computed(() =>
  projects.value.length ? `${deckIndex.value + 1} / ${projects.value.length}` : '0 / 0'
)

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
  resetRoast()
}

function previousProject() {
  if (!projects.value.length) return
  deckIndex.value = (deckIndex.value - 1 + projects.value.length) % projects.value.length
  resetRoast()
}

function resetRoast() {
  roastOpen.value = false
  roastDraft.value = ''
  roastMessage.value = null
  roastError.value = null
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
    const response = await fetch(`${API_URL}/api/projects/${project.id}/react`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reaction }),
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw new Error(data?.detail || `Reaction failed (HTTP ${response.status}).`)
    }
    project.reactions = data
    if (reaction === 'heart' && viewMode.value === 'swipe') nextProject()
  } catch (err) {
    reactionError.value = err.message || 'Could not save that reaction.'
  }
}

function openRoastForm() {
  selectedProject.value = null
  roastOpen.value = true
  roastMessage.value = null
  roastError.value = null
}

async function submitRoast() {
  if (!currentProject.value || roastBusy.value) return
  if (roastDraft.value.trim().length < 5) {
    roastError.value = 'Give the monkey at least 5 characters.'
    return
  }

  roastBusy.value = true
  roastError.value = null
  try {
    const response = await fetch(`${API_URL}/api/roast-wall`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: roastDraft.value.trim(),
        target: currentProject.value.category || currentProject.value.title,
      }),
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      const detail = data?.detail
      throw new Error(
        Array.isArray(detail)
          ? detail.map((item) => item?.msg).filter(Boolean).join('; ')
          : detail || `Roast failed (HTTP ${response.status}).`
      )
    }
    roastMessage.value =
      COMEBACKS[Math.floor(Math.random() * COMEBACKS.length)] ||
      'Ugali the Monkey added it to the moderation queue.'
    roastDraft.value = ''
    window.setTimeout(() => {
      nextProject()
    }, 900)
  } catch (err) {
    roastError.value = err.message || 'The roast could not be submitted.'
  } finally {
    roastBusy.value = false
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
      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p class="page-kicker text-[#19E3FF]">CASE STUDIES</p>
          <h2 class="font-orbitron text-2xl font-bold">
            {{ viewMode === 'swipe' ? 'SWIPE DECK' : 'PROJECT GRID' }}
          </h2>
        </div>
        <div class="flex items-center gap-2" role="group" aria-label="View mode">
          <button
            type="button"
            class="nav-link"
            :class="{ 'nav-link-active': viewMode === 'swipe' }"
            @click="viewMode = 'swipe'"
          >
            SWIPE MODE
          </button>
          <button
            type="button"
            class="nav-link"
            :class="{ 'nav-link-active': viewMode === 'grid' }"
            @click="viewMode = 'grid'"
          >
            GRID MODE
          </button>
          <span class="font-mono-tech text-[10px] text-[#8FA6C8]">{{ deckProgress }}</span>
        </div>
      </div>

      <!-- Swipe deck -->
      <div v-if="viewMode === 'swipe' && currentProject" class="panel p-5 md:p-7 mb-8">
        <div
          class="swipe-card relative border border-[#22345E] bg-[#050914] p-5 md:p-6"
          tabindex="0"
          role="button"
          :aria-label="`Open case study for ${currentProject.title}`"
          @click="openProject(currentProject)"
          @keydown.left.prevent="previousProject"
          @keydown.right.prevent="nextProject"
          @keydown.enter.prevent="openProject(currentProject)"
          @touchstart.passive="onTouchStart"
          @touchend.passive="onTouchEnd"
        >
          <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="border border-[#19E3FF]/50 bg-[#0D2230] px-2 py-0.5 font-mono-tech text-[9px] text-[#19E3FF]">
              {{ currentProject.category || 'ENGINEERING' }}
            </span>
            <span class="font-mono-tech text-[10px] text-[#8FA6C8]">{{ deckProgress }}</span>
          </div>

          <h3 class="mt-4 font-orbitron text-2xl font-bold md:text-3xl">
            {{ currentProject.title }}
          </h3>
          <div class="mt-3 flex flex-wrap gap-2">
            <span
              v-for="tech in currentProject.stack"
              :key="tech"
              class="border border-[#22345E] bg-[#0A0F1F] px-2 py-0.5 font-mono-tech text-[10px] text-[#19E3FF]"
            >
              {{ tech }}
            </span>
          </div>
          <p class="mt-4 max-w-3xl text-sm leading-relaxed text-[#A9BCD9]">
            {{ currentProject.problem }}
          </p>

          <div v-if="roastOpen" class="mt-5 border border-[#FF4D8D]/40 bg-[#150A12] p-4" @click.stop>
            <p class="font-mono-tech text-[10px] text-[#FF4D8D]">
              🔥 DROP A QUICK ROAST ON THIS SKILL/PROJECT
            </p>
            <form class="mt-3 grid gap-2" @submit.prevent="submitRoast">
              <textarea
                v-model="roastDraft"
                rows="2"
                maxlength="280"
                required
                minlength="5"
                class="input-tech w-full resize-y"
                placeholder="Be honest. Ugali is listening."
                :disabled="roastBusy"
              />
              <div class="flex flex-wrap items-center gap-2">
                <button type="submit" class="btn-primary-small" :disabled="roastBusy">
                  {{ roastBusy ? 'SENDING...' : 'SEND ROAST' }}
                </button>
                <button type="button" class="btn-ghost" @click="resetRoast">CANCEL</button>
                <span class="font-mono-tech text-[9px] text-[#8FA6C8]">
                  {{ roastDraft.length }}/280 · target: {{ currentProject.category }}
                </span>
              </div>
              <p v-if="roastMessage" role="status" aria-live="polite" class="font-mono-tech text-[10px] text-[#3DF5A6]">
                {{ roastMessage }}
              </p>
              <p v-if="roastError" role="alert" class="font-mono-tech text-[10px] text-[#FF4D8D]">
                {{ roastError }}
              </p>
            </form>
          </div>

          <div v-else class="mt-5 flex flex-wrap items-center gap-2">
            <button
              type="button"
              class="btn-primary"
              :aria-label="`Heart ${currentProject.title}`"
              @click.stop="reactToProject(currentProject, 'heart')"
            >
              ♥ HEART {{ currentProject.reactions?.heart || 0 }}
            </button>
            <button
              type="button"
              class="btn-ghost"
              :aria-label="`Roast ${currentProject.title}`"
              @click.stop="openRoastForm"
            >
              🔥 ROAST IT
            </button>
            <button type="button" class="btn-secondary" @click.stop="openProject(currentProject)">
              OPEN CASE STUDY
            </button>
            <span class="ml-auto flex gap-2">
              <button type="button" class="btn-secondary" @click.stop="previousProject">←</button>
              <button type="button" class="btn-secondary" @click.stop="nextProject">→</button>
            </span>
          </div>
          <p v-if="reactionError" role="alert" class="mt-3 font-mono-tech text-[10px] text-[#FF4D8D]">
            {{ reactionError }}
          </p>
          <p class="mt-3 font-mono-tech text-[9px] text-[#8FA6C8]">
            Swipe or use arrow keys · click the card for the deep dive
          </p>
        </div>
      </div>

      <!-- Grid -->
      <div v-else class="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
        <article
          v-for="project in projects"
          :key="project.id"
          class="panel flex flex-col p-5 transition-colors hover:border-[#19E3FF]/70"
          tabindex="0"
          role="button"
          :aria-label="`Open case study for ${project.title}`"
          @click="openProject(project)"
          @keydown.enter.prevent="openProject(project)"
          @keydown.space.prevent="openProject(project)"
        >
          <span class="w-fit border border-[#19E3FF]/40 px-1.5 py-0.5 font-mono-tech text-[9px] text-[#19E3FF]">
            {{ project.category || 'ENGINEERING' }}
          </span>
          <h3 class="mt-2 font-orbitron text-lg font-bold">{{ project.title }}</h3>
          <div class="mt-2 flex flex-wrap gap-1.5">
            <span
              v-for="tech in project.stack.slice(0, 4)"
              :key="tech"
              class="border border-[#22345E] px-1.5 py-0.5 font-mono-tech text-[9px] text-[#19E3FF]"
            >
              {{ tech }}
            </span>
          </div>
          <p class="mt-3 flex-grow text-xs leading-relaxed text-[#A9BCD9] line-clamp-3">
            {{ project.problem }}
          </p>
          <div class="mt-4 flex items-center justify-between gap-2">
            <div class="flex gap-1">
              <button
                type="button"
                class="border border-[#3DF5A6]/50 px-2 py-1 font-mono-tech text-[10px] text-[#3DF5A6] hover:bg-[#0D2A24]"
                :aria-label="`Heart ${project.title}`"
                @click.stop="reactToProject(project, 'heart')"
              >
                ♥ {{ project.reactions?.heart || 0 }}
              </button>
              <button
                type="button"
                class="border border-[#FF4D8D]/50 px-2 py-1 font-mono-tech text-[10px] text-[#FF4D8D] hover:bg-[#2A1220]"
                :aria-label="`Roast ${project.title}`"
                @click.stop="openProject(project)"
              >
                🔥 ROAST
              </button>
            </div>
            <span class="font-mono-tech text-[10px] text-[#19E3FF]">OPEN →</span>
          </div>
        </article>
      </div>
    </template>

    <!-- Detail modal -->
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
            <p class="page-kicker text-[#19E3FF]">CASE STUDY · {{ selectedProject.category }}</p>
            <h2 id="project-modal-title" class="font-orbitron text-2xl font-bold md:text-3xl">
              {{ selectedProject.title }}
            </h2>
          </div>
          <button type="button" class="btn-secondary" @click="closeProject">CLOSE</button>
        </div>

        <div class="mt-3 flex flex-wrap gap-2">
          <span
            v-for="tech in selectedProject.stack"
            :key="tech"
            class="border border-[#22345E] bg-[#0A0F1F] px-2 py-0.5 font-mono-tech text-[10px] text-[#19E3FF]"
          >
            {{ tech }}
          </span>
        </div>

        <div class="mt-5 grid gap-4">
          <section>
            <h3 class="mb-1 font-pixel text-[10px] text-[#FFC857]">PROBLEM</h3>
            <p class="text-sm leading-relaxed text-[#D7E4F8]">{{ selectedProject.problem }}</p>
          </section>
          <section>
            <h3 class="mb-1 font-pixel text-[10px] text-[#3DF5A6]">BUILD</h3>
            <p class="text-sm leading-relaxed text-[#D7E4F8]">{{ selectedProject.build }}</p>
          </section>
          <section>
            <h3 class="mb-1 font-pixel text-[10px] text-[#19E3FF]">OUTCOME</h3>
            <p class="text-sm leading-relaxed text-[#D7E4F8]">{{ selectedProject.outcome }}</p>
          </section>
        </div>

        <div class="mt-5 flex flex-wrap items-center gap-2">
          <button type="button" class="btn-primary" @click="reactToProject(selectedProject, 'heart')">
            ♥ HEART {{ selectedProject.reactions?.heart || 0 }}
          </button>
          <button type="button" class="btn-ghost" @click="openRoastForm">
            🔥 ROAST IT
          </button>
          <a
            v-if="selectedProject.demo_url || selectedProject.live_url"
            :href="selectedProject.demo_url || selectedProject.live_url"
            target="_blank"
            rel="noopener noreferrer"
            class="btn-secondary"
          >
            LIVE ↗
          </a>
          <a
            v-if="selectedProject.repo_url"
            :href="selectedProject.repo_url"
            target="_blank"
            rel="noopener noreferrer"
            class="btn-secondary"
          >
            GITHUB ↗
          </a>
          <span
            v-if="!selectedProject.demo_url && !selectedProject.live_url && !selectedProject.repo_url"
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
