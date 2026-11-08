<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  initialTab: {
    type: String,
    default: 'leads',
  },
})

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const KEY_STORAGE = 'fwaj_admin_key'
const TABS = ['leads', 'moderation', 'portfolio', 'logs']

const adminKey = ref(sessionStorage.getItem(KEY_STORAGE) || '')
const keyInput = ref(adminKey.value)
const unlocked = ref(false)
const unlocking = ref(false)
const authError = ref(null)
const loading = ref(false)
const loadError = ref(null)
const activeTab = ref(TABS.includes(props.initialTab) ? props.initialTab : 'leads')

const stats = ref(null)
const leads = ref([])
const moderation = ref({ roasts: [], board: [] })
const projects = ref([])
const resume = ref(null)
const adminLogs = ref([])
const actionMessage = ref(null)
const actionError = ref(null)
const busyId = ref(null)

const emptyProjectForm = () => ({
  title: '',
  category: 'Engineering',
  problem: '',
  build: '',
  outcome: '',
  stack: '',
  repo_url: '',
  live_url: '',
  include_in_resume: true,
})

const projectForm = ref(emptyProjectForm())
const editingProjectId = ref(null)
const projectBusy = ref(false)

const resumeForm = ref({
  name: '',
  headline: '',
  location: '',
  email: '',
  phone: '',
  summary: '',
  skillsText: '',
  experience: [],
  education: [],
})
const resumeBusy = ref(false)

const pendingRoasts = computed(() => moderation.value.roasts || [])
const pendingBoard = computed(() => moderation.value.board || [])

const statsCards = computed(() => [
  { label: 'LEADS + BOOKINGS', value: leads.value.length, color: '#19E3FF' },
  { label: 'PENDING ROASTS', value: pendingRoasts.value.length, color: '#FF4D8D' },
  { label: 'PENDING BOARD', value: pendingBoard.value.length, color: '#FFC857' },
  { label: 'CUSTOM PROJECTS', value: projects.value.length, color: '#3DF5A6' },
  { label: 'TOTAL EVENTS', value: stats.value?.total_events ?? '—', color: '#19E3FF' },
  { label: 'RESUME PROJECTS', value: resume.value?.projects?.length ?? '—', color: '#3DF5A6' },
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
async function loadLeads() {
  const data = await requestJson(`${API_URL}/api/admin/leads`)
  leads.value = data.leads || []
}
async function loadModeration() {
  moderation.value = await requestJson(`${API_URL}/api/admin/moderation`)
}
async function loadProjects() {
  projects.value = await requestJson(`${API_URL}/api/admin/projects`)
}
async function loadResume() {
  const response = await fetch(`${API_URL}/api/resume.json`)
  if (!response.ok) throw new Error('Could not load the resume state.')
  const data = await response.json()
  resume.value = data
  resumeForm.value = {
    name: data.name || '',
    headline: data.headline || '',
    location: data.location || '',
    email: data.email || '',
    phone: data.phone || '',
    summary: data.summary || '',
    skillsText: (data.skills || [])
      .map((group) => `${group.group}: ${(group.items || []).join(', ')}`)
      .join('\n'),
    experience: (data.experience || []).map((job) => ({
      ...job,
      bulletsText: (job.bullets || []).join('\n'),
    })),
    education: (data.education || []).map((school) => ({
      ...school,
      detailsText: (school.details || []).join('\n'),
    })),
  }
}
async function loadLogs() {
  adminLogs.value = await requestJson(`${API_URL}/api/admin/logs?limit=100`)
}

async function loadAll() {
  loading.value = true
  loadError.value = null
  const results = await Promise.allSettled([
    loadStats(),
    loadLeads(),
    loadModeration(),
    loadProjects(),
    loadResume(),
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
  leads.value = []
  moderation.value = { roasts: [], board: [] }
  projects.value = []
  resume.value = null
  adminLogs.value = []
}

function flash(message) {
  actionMessage.value = message
  actionError.value = null
  window.setTimeout(() => {
    actionMessage.value = null
  }, 3500)
}

async function approveRoast(roast) {
  busyId.value = roast.id
  actionError.value = null
  try {
    await requestJson(`${API_URL}/api/admin/roast/${roast.id}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note: 'Approved in dashboard.' }),
    })
    flash('Roast approved and pushed live.')
    await Promise.allSettled([loadModeration(), loadStats(), loadLogs()])
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
    await requestJson(`${API_URL}/api/admin/roast/${roast.id}`, { method: 'DELETE' })
    flash('Roast deleted.')
    await Promise.allSettled([loadModeration(), loadStats(), loadLogs()])
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
    flash(`Board submission ${action}d.`)
    await Promise.allSettled([loadModeration(), loadStats(), loadLogs()])
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
    category: project.category || 'Engineering',
    problem: project.problem,
    build: project.build,
    outcome: project.outcome,
    stack: (project.stack || []).join(', '),
    repo_url: project.repo_url || '',
    live_url: project.demo_url || '',
    include_in_resume: project.include_in_resume !== false,
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
      category: projectForm.value.category || 'Engineering',
      problem: projectForm.value.problem,
      build: projectForm.value.build,
      outcome: projectForm.value.outcome,
      stack: projectForm.value.stack
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
      repo_url: projectForm.value.repo_url || null,
      live_url: projectForm.value.live_url || null,
      include_in_resume: projectForm.value.include_in_resume,
    }
    const url = editingProjectId.value
      ? `${API_URL}/api/admin/projects/${editingProjectId.value}`
      : `${API_URL}/api/admin/projects`
    await requestJson(url, {
      method: editingProjectId.value ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    flash(
      editingProjectId.value
        ? 'Project updated. Resume PDF will regenerate on the next download.'
        : 'Project added. Resume PDF will regenerate on the next download.'
    )
    resetProjectForm()
    await Promise.allSettled([loadProjects(), loadResume(), loadStats(), loadLogs()])
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
    flash('Project removed. Resume PDF will regenerate on the next download.')
    await Promise.allSettled([loadProjects(), loadResume(), loadStats(), loadLogs()])
  } catch (err) {
    actionError.value = err.message || 'The project could not be removed.'
  } finally {
    busyId.value = null
  }
}

function parseSkills(text) {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [group, ...rest] = line.split(':')
      const items = rest
        .join(':')
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
      return { group: group.trim(), items }
    })
    .filter((group) => group.group)
}

async function saveResume() {
  resumeBusy.value = true
  actionError.value = null
  try {
    const payload = {
      name: resumeForm.value.name,
      headline: resumeForm.value.headline,
      location: resumeForm.value.location,
      email: resumeForm.value.email,
      phone: resumeForm.value.phone,
      summary: resumeForm.value.summary,
      skills: parseSkills(resumeForm.value.skillsText),
      experience: resumeForm.value.experience.map((job) => ({
        role: job.role,
        company: job.company,
        start: job.start,
        end: job.end,
        location: job.location,
        bullets: job.bulletsText
          .split('\n')
          .map((bullet) => bullet.trim())
          .filter(Boolean),
      })),
      education: resumeForm.value.education.map((school) => ({
        degree: school.degree,
        school: school.school,
        start: school.start,
        end: school.end,
        location: school.location,
        details: school.detailsText
          .split('\n')
          .map((detail) => detail.trim())
          .filter(Boolean),
      })),
    }
    const data = await requestJson(`${API_URL}/api/admin/resume`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    resume.value = data.resume
    flash('Resume saved. The PDF will reflect this on the next download.')
    await Promise.allSettled([loadLogs()])
  } catch (err) {
    actionError.value = err.message || 'The resume could not be saved.'
  } finally {
    resumeBusy.value = false
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
        Review every lead, clear the moderation queue, and edit the live resume.
        Changes regenerate the downloadable PDF on the next request.
      </p>
    </header>

    <section v-if="!unlocked" class="panel max-w-lg p-6">
      <h2 class="font-orbitron text-xl font-bold">UNLOCK ADMIN</h2>
      <p class="mt-2 text-sm text-[#A9BCD9]">
        Enter the value of <code class="text-[#19E3FF]">ADMIN_API_KEY</code> from
        your backend environment. It is stored in this browser tab's session only.
      </p>
      <form class="mt-4 grid gap-3" @submit.prevent="unlock">
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
      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
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

      <div class="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div v-for="card in statsCards" :key="card.label" class="stat-card">
          <p class="stat-label">{{ card.label }}</p>
          <p class="stat-value" :style="{ color: card.color }">{{ card.value }}</p>
        </div>
      </div>

      <!-- Tab 1: Leads, links and bookings -->
      <section v-if="activeTab === 'leads'" class="grid gap-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h2 class="page-title text-2xl">LEADS, LINKS &amp; BOOKINGS</h2>
          <span class="font-mono-tech text-[10px] text-[#8FA6C8]">{{ leads.length }} records</span>
        </div>
        <div class="panel overflow-x-auto p-0">
          <table class="w-full min-w-[720px] text-left text-xs">
            <thead class="border-b border-[#22345E] bg-[#0A0F1F] font-mono-tech text-[10px] text-[#8FA6C8]">
              <tr>
                <th class="px-3 py-2">KIND</th>
                <th class="px-3 py-2">NAME / COMPANY</th>
                <th class="px-3 py-2">CONTACT</th>
                <th class="px-3 py-2">NOTES</th>
                <th class="px-3 py-2">CREATED</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="lead in leads" :key="lead.id" class="border-b border-[#22345E]/50">
                <td class="px-3 py-2 font-mono-tech text-[10px] text-[#19E3FF]">{{ lead.kind }}</td>
                <td class="px-3 py-2 text-[#E6F1FF]">
                  {{ lead.name || '—' }}
                  <span v-if="lead.company" class="block text-[10px] text-[#8FA6C8]">{{ lead.company }}</span>
                </td>
                <td class="px-3 py-2 text-[#A9BCD9]">{{ lead.contact || '—' }}</td>
                <td class="px-3 py-2 text-[#A9BCD9]">{{ lead.notes || '—' }}</td>
                <td class="px-3 py-2 font-mono-tech text-[9px] text-[#8FA6C8]">{{ formatDate(lead.created_at) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-if="!leads.length" class="p-4 text-sm text-[#8FA6C8]">No bookings or monkey-menu leads yet.</p>
        </div>
      </section>

      <!-- Tab 2: Moderation queue -->
      <section v-else-if="activeTab === 'moderation'" class="grid gap-6">
        <div>
          <h2 class="page-title text-2xl">ROAST MODERATION QUEUE</h2>
          <div class="mt-3 grid gap-4">
            <article v-for="roast in pendingRoasts" :key="roast.id" class="panel p-4">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <span class="font-mono-tech text-[10px] text-[#FFC857]">PENDING</span>
                <span class="font-mono-tech text-[9px] text-[#8FA6C8]">{{ formatDate(roast.created_at) }}</span>
              </div>
              <p v-if="roast.target" class="mt-2 font-mono-tech text-[10px] text-[#FF4D8D]">TARGET: {{ roast.target }}</p>
              <p class="mt-2 text-sm text-[#E6F1FF]">{{ roast.text }}</p>
              <div class="mt-3 flex gap-2">
                <button type="button" class="btn-primary-small" :disabled="busyId === roast.id" @click="approveRoast(roast)">APPROVE</button>
                <button type="button" class="btn-ghost" :disabled="busyId === roast.id" @click="removeRoast(roast)">DELETE</button>
              </div>
            </article>
            <p v-if="!pendingRoasts.length" class="text-sm text-[#8FA6C8]">No pending roasts.</p>
          </div>
        </div>

        <div>
          <h2 class="page-title text-2xl">TALENT BOARD QUEUE</h2>
          <div class="mt-3 grid gap-4">
            <article v-for="entry in pendingBoard" :key="entry.id" class="panel p-4">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <span class="font-mono-tech text-[10px] text-[#FFC857]">PENDING</span>
                <span class="font-mono-tech text-[9px] text-[#8FA6C8]">{{ formatDate(entry.created_at) }}</span>
              </div>
              <p class="mt-2 font-orbitron text-sm font-bold">{{ entry.name }} // {{ entry.role }}</p>
              <p class="mt-1 text-xs text-[#A9BCD9]">{{ entry.pitch }}</p>
              <div class="mt-3 flex gap-2">
                <button type="button" class="btn-primary-small" :disabled="busyId === entry.id" @click="moderateBoard(entry, 'approve')">APPROVE</button>
                <button type="button" class="btn-ghost" :disabled="busyId === entry.id" @click="moderateBoard(entry, 'reject')">REJECT</button>
              </div>
            </article>
            <p v-if="!pendingBoard.length" class="text-sm text-[#8FA6C8]">No pending board entries.</p>
          </div>
        </div>
      </section>

      <!-- Tab 3: Portfolio + live resume -->
      <section v-else-if="activeTab === 'portfolio'" class="grid gap-8">
        <form class="panel grid gap-3 p-5" @submit.prevent="saveProject">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <h2 class="font-orbitron text-xl font-bold">
              {{ editingProjectId ? 'EDIT PROJECT / SKILL CARD' : 'ADD PROJECT / SKILL CARD' }}
            </h2>
            <button v-if="editingProjectId" type="button" class="btn-secondary" @click="resetProjectForm">
              CANCEL EDIT
            </button>
          </div>
          <p class="font-mono-tech text-[10px] text-[#3DF5A6]">
            Cards marked "include in resume" are added to the PDF and RAG index.
          </p>
          <div class="grid gap-3 md:grid-cols-2">
            <label class="grid gap-1 md:col-span-2">
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">TITLE</span>
              <input v-model="projectForm.title" required minlength="3" maxlength="120" class="input-tech" />
            </label>
            <label class="grid gap-1">
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">CATEGORY</span>
              <input v-model="projectForm.category" maxlength="60" class="input-tech" placeholder="AI & Full-Stack" />
            </label>
            <label class="grid gap-1">
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">STACK (COMMA-SEPARATED)</span>
              <input v-model="projectForm.stack" class="input-tech" placeholder="FastAPI, PostgreSQL, Vue 3" />
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
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">LIVE URL</span>
              <input v-model="projectForm.live_url" type="url" class="input-tech" placeholder="https://..." />
            </label>
            <label class="grid gap-1">
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">GITHUB / REPO URL</span>
              <input v-model="projectForm.repo_url" type="url" class="input-tech" placeholder="https://github.com/..." />
            </label>
            <label class="flex items-center gap-2 md:col-span-2">
              <input v-model="projectForm.include_in_resume" type="checkbox" class="h-4 w-4 accent-[#19E3FF]" />
              <span class="font-mono-tech text-[10px] text-[#A9BCD9]">INCLUDE IN RESUME PDF</span>
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
                <p class="font-mono-tech text-[9px] text-[#8FA6C8]">
                  {{ project.category || 'Engineering' }} · {{ (project.stack || []).join(' · ') }}
                </p>
                <p class="mt-1 font-mono-tech text-[9px]" :class="project.include_in_resume !== false ? 'text-[#3DF5A6]' : 'text-[#FFC857]'">
                  {{ project.include_in_resume !== false ? 'IN RESUME' : 'HIDDEN FROM RESUME' }}
                </p>
              </div>
              <div class="flex gap-2">
                <button type="button" class="btn-secondary" @click="editProject(project)">EDIT</button>
                <button type="button" class="btn-ghost" :disabled="busyId === project.id" @click="removeProject(project)">DELETE</button>
              </div>
            </div>
            <p class="mt-2 text-xs text-[#A9BCD9]">{{ project.outcome }}</p>
          </article>
          <p v-if="!projects.length" class="text-sm text-[#8FA6C8]">
            No custom projects yet. The base case studies remain available.
          </p>
        </div>

        <form class="panel grid gap-4 p-5" @submit.prevent="saveResume">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <h2 class="font-orbitron text-xl font-bold">LIVE RESUME EDITOR</h2>
            <a :href="`${API_URL}/api/resume`" download class="btn-secondary">DOWNLOAD PDF</a>
          </div>
          <div class="grid gap-3 md:grid-cols-2">
            <label class="grid gap-1">
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">NAME</span>
              <input v-model="resumeForm.name" class="input-tech" />
            </label>
            <label class="grid gap-1">
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">HEADLINE</span>
              <input v-model="resumeForm.headline" class="input-tech" />
            </label>
            <label class="grid gap-1">
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">LOCATION</span>
              <input v-model="resumeForm.location" class="input-tech" />
            </label>
            <label class="grid gap-1">
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">EMAIL</span>
              <input v-model="resumeForm.email" type="email" class="input-tech" />
            </label>
            <label class="grid gap-1">
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">PHONE</span>
              <input v-model="resumeForm.phone" class="input-tech" />
            </label>
          </div>
          <label class="grid gap-1">
            <span class="font-mono-tech text-[10px] text-[#8FA6C8]">SUMMARY</span>
            <textarea v-model="resumeForm.summary" rows="4" class="input-tech resize-y" />
          </label>
          <label class="grid gap-1">
            <span class="font-mono-tech text-[10px] text-[#8FA6C8]">SKILLS (ONE GROUP PER LINE: "Backend: Python, FastAPI")</span>
            <textarea v-model="resumeForm.skillsText" rows="5" class="input-tech resize-y" />
          </label>

          <div class="grid gap-3">
            <h3 class="font-mono-tech text-xs text-[#19E3FF]">EXPERIENCE</h3>
            <div v-for="(job, index) in resumeForm.experience" :key="`job-${index}`" class="border border-[#22345E] p-3">
              <div class="grid gap-2 md:grid-cols-2">
                <input v-model="job.role" class="input-tech" placeholder="Role" />
                <input v-model="job.company" class="input-tech" placeholder="Company" />
                <input v-model="job.start" class="input-tech" placeholder="Start" />
                <input v-model="job.end" class="input-tech" placeholder="End" />
              </div>
              <textarea v-model="job.bulletsText" rows="3" class="input-tech mt-2 w-full resize-y" placeholder="One bullet per line" />
            </div>
          </div>

          <div class="grid gap-3">
            <h3 class="font-mono-tech text-xs text-[#19E3FF]">EDUCATION</h3>
            <div v-for="(school, index) in resumeForm.education" :key="`school-${index}`" class="border border-[#22345E] p-3">
              <div class="grid gap-2 md:grid-cols-2">
                <input v-model="school.degree" class="input-tech" placeholder="Degree" />
                <input v-model="school.school" class="input-tech" placeholder="School" />
                <input v-model="school.start" class="input-tech" placeholder="Start" />
                <input v-model="school.end" class="input-tech" placeholder="End" />
              </div>
              <textarea v-model="school.detailsText" rows="2" class="input-tech mt-2 w-full resize-y" placeholder="One detail per line" />
            </div>
          </div>

          <button type="submit" class="btn-primary w-fit" :disabled="resumeBusy">
            {{ resumeBusy ? 'SAVING...' : 'SAVE LIVE RESUME' }}
          </button>
        </form>
      </section>

      <!-- Audit logs -->
      <section v-else-if="activeTab === 'logs'" class="panel p-5">
        <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
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
            <p class="mt-1 text-[#D7E4F8]">{{ log.detail || '—' }}</p>
            <p class="mt-0.5 text-[#8FA6C8]">target: {{ log.target || '—' }} · actor: {{ log.actor }}</p>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
