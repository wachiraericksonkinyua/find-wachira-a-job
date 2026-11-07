<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  initialTab: {
    type: String,
    default: 'overview',
  },
})

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const KEY_STORAGE = 'fwaj_admin_key'
const TABS = ['overview', 'roasts', 'board', 'projects', 'logs']

const adminKey = ref(sessionStorage.getItem(KEY_STORAGE) || '')
const keyInput = ref(adminKey.value)
const unlocked = ref(false)
const unlocking = ref(false)
const authError = ref(null)
const loading = ref(false)
const loadError = ref(null)
const activeTab = ref(TABS.includes(props.initialTab) ? props.initialTab : 'overview')

const stats = ref(null)
const roasts = ref([])
const boardEntries = ref([])
const projects = ref([])
const adminLogs = ref([])
const actionMessage = ref(null)
const actionError = ref(null)
const busyId = ref(null)

const emptyProjectForm = () => ({
  title: '',
  problem: '',
  build: '',
  outcome: '',
  stack: '',
  repo_url: '',
  demo_url: '',
})

const projectForm = ref(emptyProjectForm())
const editingProjectId = ref(null)
const projectBusy = ref(false)

const pendingRoasts = computed(() => roasts.value.filter((roast) => roast.status === 'pending'))
const pendingBoard = computed(() => boardEntries.value.filter((entry) => entry.status === 'pending'))

const statsCards = computed(() => [
  { label: 'TOTAL EVENTS', value: stats.value?.total_events ?? '—', color: '#19E3FF' },
  { label: 'BOOKINGS', value: stats.value?.total_bookings ?? '—', color: '#3DF5A6' },
  { label: 'PENDING ROASTS', value: pendingRoasts.value.length, color: '#FF4D8D' },
  { label: 'PENDING BOARD', value: pendingBoard.value.length, color: '#FFC857' },
  { label: 'PROJECTS', value: projects.value.length, color: '#19E3FF' },
  { label: 'CTF ATTEMPTS', value: stats.value?.redteam?.total_attempts ?? '—', color: '#FF4D8D' },
])

function adminHeaders() {
  return { 'X-Admin-Key': adminKey.value }
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      ...adminHeaders(),
    },
  })
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = data?.detail
    throw new Error(
      Array.isArray(detail)
        ? detail.map((item) => item?.msg).filter(Boolean).join('; ')
        : detail || `Request failed (HTTP ${response.status}).`
    )
  }
  return data
}

async function loadStats() {
  stats.value = await requestJson(`${API_URL}/api/admin/stats`)
}
async function loadRoasts() {
  roasts.value = await requestJson(`${API_URL}/api/admin/roasts`)
}
async function loadBoard() {
  boardEntries.value = await requestJson(`${API_URL}/api/admin/board`)
}
async function loadProjects() {
  projects.value = await requestJson(`${API_URL}/api/admin/projects`)
}
async function loadLogs() {
  adminLogs.value = await requestJson(`${API_URL}/api/admin/logs?limit=100`)
}

async function loadAll() {
  loading.value = true
  loadError.value = null
  const results = await Promise.allSettled([
    loadStats(),
    loadRoasts(),
    loadBoard(),
    loadProjects(),
    loadLogs(),
  ])
  const failures = results.filter((result) => result.status === 'rejected')
  if (failures.length) {
    loadError.value = failures
      .map((result) => result.reason?.message)
      .filter(Boolean)
      .join(' · ')
  }
  loading.value = false
}

async function unlock() {
  const candidate = keyInput.value.trim()
  if (!candidate) {
    authError.value = 'Enter the ADMIN_API_KEY.'
    return
  }

  adminKey.value = candidate
  unlocking.value = true
  authError.value = null
  try {
    // Validate the key against a protected endpoint before showing the shell.
    await loadStats()
    sessionStorage.setItem(KEY_STORAGE, candidate)
    unlocked.value = true
    await loadAll()
  } catch (err) {
    authError.value = err.message || 'Admin authentication failed.'
    sessionStorage.removeItem(KEY_STORAGE)
  } finally {
    unlocking.value = false
  }
}

function logout() {
  adminKey.value = ''
  keyInput.value = ''
  unlocked.value = false
  sessionStorage.removeItem(KEY_STORAGE)
  stats.value = null
  roasts.value = []
  boardEntries.value = []
  projects.value = []
  adminLogs.value = []
}

function flash(message) {
  actionMessage.value = message
  actionError.value = null
  window.setTimeout(() => {
    actionMessage.value = null
  }, 3500)
}

async function moderateRoast(roast, action) {
  busyId.value = roast.id
  actionError.value = null
  try {
    const result = await requestJson(
      `${API_URL}/api/admin/roasts/${roast.id}/${action}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: action === 'approve' ? 'Approved in dashboard.' : 'Rejected in dashboard.' }),
      }
    )
    roast.status = result.status
    flash(`Roast ${action}d.`)
    await Promise.allSettled([loadStats(), loadLogs()])
  } catch (err) {
    actionError.value = err.message || 'Roast moderation failed.'
  } finally {
    busyId.value = null
  }
}

async function removeRoast(roast) {
  busyId.value = roast.id
  actionError.value = null
  try {
    await requestJson(`${API_URL}/api/admin/roasts/${roast.id}`, { method: 'DELETE' })
    roasts.value = roasts.value.filter((item) => item.id !== roast.id)
    flash('Roast deleted.')
    await Promise.allSettled([loadStats(), loadLogs()])
  } catch (err) {
    actionError.value = err.message || 'Could not delete the roast.'
  } finally {
    busyId.value = null
  }
}

async function moderateBoard(entry, action) {
  busyId.value = entry.id
  actionError.value = null
  try {
    await requestJson(`${API_URL}/api/admin/board/${entry.id}/${action}`, {
      method: 'POST',
    })
    entry.status = action === 'approve' ? 'approved' : 'rejected'
    flash(`Board submission ${action}d.`)
    await Promise.allSettled([loadStats(), loadLogs()])
  } catch (err) {
    actionError.value = err.message || 'Board moderation failed.'
  } finally {
    busyId.value = null
  }
}

function editProject(project) {
  editingProjectId.value = project.id
  projectForm.value = {
    title: project.title,
    problem: project.problem,
    build: project.build,
    outcome: project.outcome,
    stack: (project.stack || []).join(', '),
    repo_url: project.repo_url || '',
    demo_url: project.demo_url || '',
  }
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function resetProjectForm() {
  editingProjectId.value = null
  projectForm.value = emptyProjectForm()
}

async function saveProject() {
  projectBusy.value = true
  actionError.value = null
  try {
    const payload = {
      title: projectForm.value.title,
      problem: projectForm.value.problem,
      build: projectForm.value.build,
      outcome: projectForm.value.outcome,
      stack: projectForm.value.stack
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
      repo_url: projectForm.value.repo_url || null,
      demo_url: projectForm.value.demo_url || null,
    }
    const url = editingProjectId.value
      ? `${API_URL}/api/admin/projects/${editingProjectId.value}`
      : `${API_URL}/api/admin/projects`
    await requestJson(url, {
      method: editingProjectId.value ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    flash(editingProjectId.value ? 'Project updated. Resume PDF regenerated.' : 'Project added. Resume PDF regenerated.')
    resetProjectForm()
    await Promise.allSettled([loadProjects(), loadStats(), loadLogs()])
  } catch (err) {
    actionError.value = err.message || 'The project could not be saved.'
  } finally {
    projectBusy.value = false
  }
}

async function removeProject(project) {
  busyId.value = project.id
  actionError.value = null
  try {
    await requestJson(`${API_URL}/api/admin/projects/${project.id}`, { method: 'DELETE' })
    projects.value = projects.value.filter((item) => item.id !== project.id)
    if (editingProjectId.value === project.id) resetProjectForm()
    flash('Project removed. Resume PDF regenerated.')
    await Promise.allSettled([loadProjects(), loadStats(), loadLogs()])
  } catch (err) {
    actionError.value = err.message || 'The project could not be removed.'
  } finally {
    busyId.value = null
  }
}

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

onMounted(() => {
  if (adminKey.value) unlock()
})
</script>

<template>
  <div class="page-shell">
    <header class="page-header">
      <p class="page-kicker text-[#FF4D8D]">OWNER-ONLY CONTROL ROOM</p>
      <h1 class="page-title">ADMIN DASHBOARD</h1>
      <p class="page-copy">
        Moderate anonymous roasts and peer submissions, manage portfolio projects,
        review audit logs, and regenerate the resume PDF.
      </p>
    </header>

    <section v-if="!unlocked" class="panel max-w-lg p-6">
      <h2 class="font-orbitron text-xl font-bold">UNLOCK ADMIN</h2>
      <p class="text-sm text-[#A9BCD9] mt-2">
        Enter the value of <code class="text-[#19E3FF]">ADMIN_API_KEY</code> from
        your backend environment. It is stored in this browser tab's session only.
      </p>
      <form class="grid gap-3 mt-4" @submit.prevent="unlock">
        <label class="grid gap-1">
          <span class="font-mono-tech text-[10px] text-[#8FA6C8]">ADMIN KEY</span>
          <input
            v-model="keyInput"
            type="password"
            autocomplete="current-password"
            required
            class="input-tech w-full"
            placeholder="X-Admin-Key"
          />
        </label>
        <p v-if="authError" role="alert" class="font-mono-tech text-xs text-[#FF4D8D]">{{ authError }}</p>
        <button type="submit" class="btn-primary w-fit" :disabled="unlocking">
          {{ unlocking ? 'VERIFYING...' : 'UNLOCK DASHBOARD' }}
        </button>
      </form>
    </section>

    <template v-else>
      <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
        <nav class="flex flex-wrap gap-1" aria-label="Admin tabs">
          <button
            v-for="tab in TABS"
            :key="tab"
            type="button"
            class="nav-link"
            :class="{ 'nav-link-active': activeTab === tab }"
            @click="activeTab = tab"
          >
            {{ tab.toUpperCase() }}
          </button>
        </nav>
        <div class="flex items-center gap-2">
          <a :href="`${API_URL}/api/resume`" download class="btn-secondary">DOWNLOAD RESUME</a>
          <button type="button" class="btn-ghost" @click="logout">LOCK</button>
        </div>
      </div>

      <p v-if="actionMessage" role="status" aria-live="polite" class="mb-3 font-mono-tech text-xs text-[#3DF5A6]">
        {{ actionMessage }}
      </p>
      <p v-if="actionError" role="alert" class="mb-3 font-mono-tech text-xs text-[#FF4D8D]">
        {{ actionError }}
      </p>
      <p v-if="loadError" role="alert" class="mb-3 font-mono-tech text-xs text-[#FFC857]">
        Partial load: {{ loadError }}
      </p>
      <p v-if="loading" class="mb-3 font-mono-tech text-xs text-[#19E3FF]">Loading dashboard...</p>

      <!-- Overview -->
      <section v-if="activeTab === 'overview'">
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 mb-6">
          <div v-for="card in statsCards" :key="card.label" class="stat-card">
            <p class="stat-label">{{ card.label }}</p>
            <p class="stat-value" :style="{ color: card.color }">{{ card.value }}</p>
          </div>
        </div>
        <div class="grid gap-4 md:grid-cols-2">
          <div class="panel p-5">
            <h2 class="font-mono-tech text-xs text-[#FF4D8D] mb-2">QUICK ACTIONS</h2>
            <div class="flex flex-wrap gap-2">
              <button type="button" class="btn-primary" @click="activeTab = 'roasts'">MODERATE ROASTS</button>
              <button type="button" class="btn-secondary" @click="activeTab = 'board'">REVIEW BOARD</button>
              <button type="button" class="btn-secondary" @click="activeTab = 'projects'">ADD PROJECT</button>
              <button type="button" class="btn-secondary" @click="activeTab = 'logs'">AUDIT LOGS</button>
            </div>
          </div>
          <div class="panel p-5">
            <h2 class="font-mono-tech text-xs text-[#3DF5A6] mb-2">SYSTEM SNAPSHOT</h2>
            <p class="text-xs text-[#A9BCD9]">Funnel events: {{ stats?.total_events ?? '—' }}</p>
            <p class="text-xs text-[#A9BCD9]">Board approved: {{ stats?.board?.approved ?? '—' }}</p>
            <p class="text-xs text-[#A9BCD9]">Red-team blocked: {{ stats?.redteam?.blocked_attacks ?? '—' }}</p>
            <RouterLink to="/logs" class="btn-secondary mt-3">OPEN SYSTEM LOGS →</RouterLink>
          </div>
        </div>
      </section>

      <!-- Roasts -->
      <section v-else-if="activeTab === 'roasts'" class="grid gap-4">
        <h2 class="page-title text-2xl">ROAST MODERATION</h2>
        <article v-for="roast in roasts" :key="roast.id" class="panel p-4">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="font-mono-tech text-[10px]" :class="roast.status === 'pending' ? 'text-[#FFC857]' : roast.status === 'approved' ? 'text-[#3DF5A6]' : 'text-[#8FA6C8]'">
              {{ roast.status.toUpperCase() }}
            </span>
            <span class="font-mono-tech text-[9px] text-[#8FA6C8]">{{ formatDate(roast.created_at) }}</span>
          </div>
          <p class="text-sm text-[#E6F1FF] mt-2">{{ roast.text }}</p>
          <p v-if="roast.advice" class="text-xs text-[#A9BCD9] mt-1">Advice: {{ roast.advice }}</p>
          <div class="flex flex-wrap gap-2 mt-3">
            <button
              v-if="roast.status !== 'approved'"
              type="button"
              class="btn-primary-small"
              :disabled="busyId === roast.id"
              @click="moderateRoast(roast, 'approve')"
            >
              APPROVE
            </button>
            <button
              v-if="roast.status === 'pending'"
              type="button"
              class="btn-ghost"
              :disabled="busyId === roast.id"
              @click="moderateRoast(roast, 'reject')"
            >
              REJECT
            </button>
            <button
              type="button"
              class="btn-secondary"
              :disabled="busyId === roast.id"
              @click="removeRoast(roast)"
            >
              DELETE
            </button>
          </div>
        </article>
        <p v-if="!roasts.length" class="text-sm text-[#8FA6C8]">No roast submissions yet.</p>
      </section>

      <!-- Board -->
      <section v-else-if="activeTab === 'board'" class="grid gap-4">
        <h2 class="page-title text-2xl">TALENT BOARD MODERATION</h2>
        <article v-for="entry in boardEntries" :key="entry.id" class="panel p-4">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="font-mono-tech text-[10px]" :class="entry.status === 'pending' ? 'text-[#FFC857]' : entry.status === 'approved' ? 'text-[#3DF5A6]' : 'text-[#8FA6C8]'">
              {{ entry.status.toUpperCase() }}
            </span>
            <span class="font-mono-tech text-[9px] text-[#8FA6C8]">{{ formatDate(entry.created_at) }}</span>
          </div>
          <p class="font-orbitron text-sm font-bold mt-2">{{ entry.name }} // {{ entry.role }}</p>
          <p class="text-xs text-[#A9BCD9] mt-1">{{ entry.pitch }}</p>
          <a :href="entry.link" target="_blank" rel="noopener noreferrer" class="font-mono-tech text-[10px] text-[#19E3FF]">
            {{ entry.link }}
          </a>
          <div v-if="entry.status === 'pending'" class="flex gap-2 mt-3">
            <button type="button" class="btn-primary-small" :disabled="busyId === entry.id" @click="moderateBoard(entry, 'approve')">APPROVE</button>
            <button type="button" class="btn-ghost" :disabled="busyId === entry.id" @click="moderateBoard(entry, 'reject')">REJECT</button>
          </div>
        </article>
        <p v-if="!boardEntries.length" class="text-sm text-[#8FA6C8]">No board submissions yet.</p>
      </section>

      <!-- Projects -->
      <section v-else-if="activeTab === 'projects'" class="grid gap-6">
        <form class="panel p-5 grid gap-3" @submit.prevent="saveProject">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <h2 class="font-orbitron text-xl font-bold">
              {{ editingProjectId ? 'EDIT PROJECT' : 'ADD PROJECT' }}
            </h2>
            <button v-if="editingProjectId" type="button" class="btn-secondary" @click="resetProjectForm">
              CANCEL EDIT
            </button>
          </div>
          <p class="font-mono-tech text-[10px] text-[#3DF5A6]">
            Saving regenerates the downloadable PDF resume and adds the project to the RAG index.
          </p>
          <div class="grid gap-3 md:grid-cols-2">
            <label class="grid gap-1 md:col-span-2">
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">TITLE</span>
              <input v-model="projectForm.title" required minlength="3" maxlength="120" class="input-tech" />
            </label>
            <label class="grid gap-1 md:col-span-2">
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">PROBLEM</span>
              <textarea v-model="projectForm.problem" required minlength="10" rows="2" class="input-tech resize-y" />
            </label>
            <label class="grid gap-1 md:col-span-2">
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">BUILD</span>
              <textarea v-model="projectForm.build" required minlength="10" rows="3" class="input-tech resize-y" />
            </label>
            <label class="grid gap-1 md:col-span-2">
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">OUTCOME</span>
              <textarea v-model="projectForm.outcome" required minlength="5" rows="2" class="input-tech resize-y" />
            </label>
            <label class="grid gap-1">
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">STACK (COMMA-SEPARATED)</span>
              <input v-model="projectForm.stack" class="input-tech" placeholder="FastAPI, PostgreSQL, Vue 3" />
            </label>
            <label class="grid gap-1">
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">VERIFY / DEMO URL</span>
              <input v-model="projectForm.demo_url" type="url" class="input-tech" placeholder="https://..." />
            </label>
            <label class="grid gap-1 md:col-span-2">
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">REPOSITORY URL</span>
              <input v-model="projectForm.repo_url" type="url" class="input-tech" placeholder="https://github.com/..." />
            </label>
          </div>
          <button type="submit" class="btn-primary w-fit" :disabled="projectBusy">
            {{ projectBusy ? 'SAVING...' : editingProjectId ? 'UPDATE PROJECT' : 'ADD PROJECT' }}
          </button>
        </form>

        <div class="grid gap-3">
          <h2 class="page-title text-2xl">CUSTOM PROJECTS</h2>
          <article v-for="project in projects" :key="project.id" class="panel p-4">
            <div class="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h3 class="font-orbitron font-bold">{{ project.title }}</h3>
                <p class="font-mono-tech text-[9px] text-[#8FA6C8]">{{ (project.stack || []).join(' · ') }}</p>
              </div>
              <div class="flex gap-2">
                <button type="button" class="btn-secondary" @click="editProject(project)">EDIT</button>
                <button type="button" class="btn-ghost" :disabled="busyId === project.id" @click="removeProject(project)">DELETE</button>
              </div>
            </div>
            <p class="text-xs text-[#A9BCD9] mt-2">{{ project.outcome }}</p>
          </article>
          <p v-if="!projects.length" class="text-sm text-[#8FA6C8]">
            No custom projects yet. The base case studies remain available.
          </p>
        </div>
      </section>

      <!-- Audit logs -->
      <section v-else-if="activeTab === 'logs'" class="panel p-5">
        <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
          <h2 class="font-orbitron text-xl font-bold">OWNER AUDIT LOG</h2>
          <RouterLink to="/logs" class="btn-secondary">PUBLIC SYSTEM LOGS →</RouterLink>
        </div>
        <div class="max-h-[520px] overflow-y-auto bg-[#02060F] p-3 font-mono-tech text-[10px]">
          <p v-if="!adminLogs.length" class="text-[#8FA6C8]">No admin actions recorded yet.</p>
          <div v-for="log in adminLogs" :key="`${log.created_at}-${log.action}-${log.target}`" class="border-b border-[#22345E]/50 py-2">
            <div class="flex flex-wrap justify-between gap-2">
              <span class="text-[#3DF5A6]">{{ log.action }}</span>
              <span class="text-[#8FA6C8]">{{ formatDate(log.created_at) }}</span>
            </div>
            <p class="text-[#D7E4F8] mt-1">{{ log.detail || '—' }}</p>
            <p class="text-[#8FA6C8] mt-0.5">target: {{ log.target || '—' }} · actor: {{ log.actor }}</p>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
