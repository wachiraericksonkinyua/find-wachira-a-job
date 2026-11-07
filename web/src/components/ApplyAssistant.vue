<script setup>
import { computed, onMounted, ref } from 'vue'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const STATUS_OPTIONS = ['saved', 'drafted', 'applied', 'interview', 'closed']

const url = ref('')
const rawJd = ref('')
const analyzing = ref(false)
const analyzeError = ref(null)
const analysis = ref(null)

const drafting = ref(false)
const draftError = ref(null)
const draft = ref(null)
const copied = ref(false)

const jobs = ref([])
const jobsError = ref(null)
const statusBusyId = ref(null)
const statusError = ref(null)

const canAnalyze = computed(
  () =>
    !analyzing.value &&
    (url.value.trim().length > 0 || rawJd.value.trim().length >= 20)
)

const scoreColor = computed(() => {
  const score = analysis.value?.score ?? 0
  if (score >= 75) return '#3DF5A6'
  if (score >= 50) return '#FFC857'
  return '#FF4D8D'
})

async function requestJson(target, options) {
  const response = await fetch(target, options)
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

async function loadJobs() {
  jobsError.value = null
  try {
    const data = await requestJson(`${API_URL}/api/apply/jobs`)
    jobs.value = Array.isArray(data) ? data : []
  } catch (err) {
    jobsError.value = err.message || 'Could not load the application tracker.'
  }
}

async function analyzeJob() {
  if (!canAnalyze.value) return

  analyzing.value = true
  analyzeError.value = null
  analysis.value = null
  draft.value = null
  draftError.value = null

  try {
    analysis.value = await requestJson(`${API_URL}/api/apply/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: url.value.trim() || null,
        raw_jd: rawJd.value.trim() || null,
      }),
    })
    await loadJobs()
  } catch (err) {
    analyzeError.value = err.message || 'The job could not be analyzed.'
  } finally {
    analyzing.value = false
  }
}

async function generateDraft() {
  if (!analysis.value?.job_id || drafting.value) return

  drafting.value = true
  draftError.value = null
  draft.value = null
  copied.value = false

  try {
    draft.value = await requestJson(`${API_URL}/api/apply/draft`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: analysis.value.job_id }),
    })
    await loadJobs()
  } catch (err) {
    draftError.value = err.message || 'The draft could not be generated.'
  } finally {
    drafting.value = false
  }
}

async function copyDraft() {
  if (!draft.value?.cover_letter) return
  try {
    await navigator.clipboard.writeText(draft.value.cover_letter)
    copied.value = true
  } catch {
    copied.value = false
  }
}

async function updateStatus(job, event) {
  const status = event.target.value
  statusBusyId.value = job.id
  statusError.value = null

  try {
    const updated = await requestJson(`${API_URL}/api/apply/jobs/${job.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
    job.status = updated.status
    if (analysis.value?.job_id === job.id) {
      analysis.value.status = updated.status
    }
  } catch (err) {
    statusError.value = err.message || 'The status could not be updated.'
    event.target.value = job.status
  } finally {
    statusBusyId.value = null
  }
}

onMounted(loadJobs)
</script>

<template>
  <section id="apply" class="mt-16 scroll-mt-24">
    <div class="panel p-6 md:p-8">
      <div class="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <p class="font-pixel text-[10px] text-[#FFC857] mb-2">
            HUMAN-IN-THE-LOOP // NO AUTO-SUBMIT
          </p>
          <h2 class="font-orbitron text-2xl md:text-3xl font-bold">
            APPLY ASSISTANT <span class="text-[#FF4D8D]">(SSRF-HARDENED)</span>
          </h2>
          <p class="text-[#8FA6C8] mt-2 max-w-2xl">
            Analyze a public job URL or paste the JD, then generate a grounded
            cover letter and three CV bullet tips from Wachira's real case studies.
            Every draft is yours to review and send manually.
          </p>
        </div>
        <div class="flex items-center gap-2 border border-[#FF4D8D]/50 bg-[#2A1220] px-3 py-2">
          <span class="h-2 w-2 rounded-full bg-[#FF4D8D]" aria-hidden="true" />
          <span class="font-mono-tech text-[10px] text-[#FF4D8D]">
            PRIVATE IPs BLOCKED
          </span>
        </div>
      </div>

      <div class="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <!-- Analyze form -->
        <div class="border border-[#22345E] bg-[#050914] p-4">
          <h3 class="font-mono-tech text-xs text-[#19E3FF] mb-3">01 // JOB INPUT</h3>

          <label class="grid gap-1 mb-3">
            <span class="font-mono-tech text-[10px] text-[#8FA6C8]">
              PUBLIC JOB URL <span class="text-[#8FA6C8]/60">(optional)</span>
            </span>
            <input
              v-model="url"
              type="url"
              maxlength="2000"
              :disabled="analyzing"
              placeholder="https://company.example/jobs/backend"
              class="bg-[#02060F] border border-[#22345E] px-3 py-2 font-mono-tech text-xs text-[#E6F1FF] placeholder:text-[#8FA6C8]/60 focus:outline-none focus:border-[#19E3FF] disabled:opacity-60"
            />
          </label>

          <label class="grid gap-1">
            <span class="font-mono-tech text-[10px] text-[#8FA6C8]">
              OR PASTE THE JD
              <span class="text-[#8FA6C8]/60">({{ rawJd.length }}/12000)</span>
            </span>
            <textarea
              v-model="rawJd"
              rows="7"
              maxlength="12000"
              :disabled="analyzing"
              placeholder="Paste the job description if the URL is private or unavailable..."
              class="w-full resize-y bg-[#02060F] border border-[#22345E] px-3 py-2 font-mono-tech text-xs leading-relaxed text-[#E6F1FF] placeholder:text-[#8FA6C8]/60 focus:outline-none focus:border-[#19E3FF] disabled:opacity-60"
            />
          </label>

          <div class="flex flex-wrap items-center gap-3 mt-3">
            <button
              type="button"
              @click="analyzeJob"
              :disabled="!canAnalyze"
              class="px-4 py-2 bg-[#19E3FF] text-[#06101F] font-orbitron text-xs font-bold hover:opacity-90 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ analyzing ? 'ANALYZING...' : 'ANALYZE JOB' }}
            </button>
            <span class="font-mono-tech text-[9px] text-[#8FA6C8]">
              DNS checked // 100 KB cap // no redirects
            </span>
          </div>

          <p v-if="analyzeError" role="alert" class="mt-3 font-mono-tech text-xs text-[#FF4D8D]">
            {{ analyzeError }}
          </p>

          <div
            v-if="analysis"
            role="status"
            aria-live="polite"
            class="mt-4 border border-[#22345E] bg-[#0A0F1F] p-3"
          >
            <div class="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p class="font-mono-tech text-[10px] text-[#8FA6C8]">TARGET ROLE</p>
                <h4 class="font-orbitron text-sm font-bold text-[#E6F1FF]">
                  {{ analysis.title }}
                </h4>
              </div>
              <p class="font-orbitron text-2xl font-black" :style="{ color: scoreColor }">
                {{ analysis.score }}
                <span class="text-[10px] text-[#8FA6C8]">/100</span>
              </p>
            </div>

            <div class="mt-3 grid gap-2 sm:grid-cols-2">
              <div>
                <p class="font-mono-tech text-[9px] text-[#3DF5A6] mb-1">MATCHED</p>
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="skill in analysis.matched"
                    :key="skill"
                    class="px-1.5 py-0.5 border border-[#3DF5A6]/50 bg-[#0D2A24] font-mono-tech text-[9px] text-[#3DF5A6]"
                  >
                    {{ skill }}
                  </span>
                  <span v-if="!analysis.matched?.length" class="text-[10px] text-[#8FA6C8]">
                    None detected
                  </span>
                </div>
              </div>
              <div>
                <p class="font-mono-tech text-[9px] text-[#FF4D8D] mb-1">GAPS</p>
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="gap in analysis.gaps"
                    :key="gap"
                    class="px-1.5 py-0.5 border border-[#FF4D8D]/50 bg-[#2A1220] font-mono-tech text-[9px] text-[#FF4D8D]"
                  >
                    {{ gap }}
                  </span>
                  <span v-if="!analysis.gaps?.length" class="text-[10px] text-[#8FA6C8]">
                    None listed
                  </span>
                </div>
              </div>
            </div>

            <button
              type="button"
              @click="generateDraft"
              :disabled="drafting"
              class="mt-4 px-4 py-2 bg-[#FFC857] text-[#06101F] font-orbitron text-xs font-bold hover:opacity-90 cursor-pointer disabled:opacity-50"
            >
              {{ drafting ? 'DRAFTING FROM REAL FACTS...' : 'GENERATE COVER LETTER + 3 TIPS' }}
            </button>
          </div>
        </div>

        <!-- Draft side-by-side with citations -->
        <div class="border border-[#22345E] bg-[#050914] p-4">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
            <h3 class="font-mono-tech text-xs text-[#3DF5A6]">02 // GROUNDED DRAFT</h3>
            <span class="font-mono-tech text-[9px] text-[#FFC857]">
              REVIEW BEFORE SENDING
            </span>
          </div>

          <p v-if="draftError" role="alert" class="font-mono-tech text-xs text-[#FF4D8D]">
            {{ draftError }}
          </p>
          <p v-else-if="!draft" class="text-xs text-[#8FA6C8]">
            Analyze a job first, then generate a draft grounded in the case studies.
          </p>

          <template v-else>
            <div class="flex flex-wrap items-center gap-2 mb-3">
              <span class="px-2 py-0.5 border border-[#3DF5A6] bg-[#0D2A24] font-mono-tech text-[9px] text-[#3DF5A6]">
                HUMAN REVIEW REQUIRED
              </span>
              <span class="font-mono-tech text-[9px] text-[#8FA6C8]">
                No auto-submit tool is connected.
              </span>
              <button
                type="button"
                @click="copyDraft"
                class="ml-auto px-2 py-1 border border-[#19E3FF] font-mono-tech text-[10px] text-[#19E3FF] hover:bg-[#19E3FF] hover:text-[#06101F] cursor-pointer"
              >
                {{ copied ? 'COPIED' : 'COPY DRAFT' }}
              </button>
            </div>

            <pre class="max-h-[340px] overflow-y-auto whitespace-pre-wrap break-words border border-[#22345E] bg-[#02060F] p-3 font-mono-tech text-[11px] leading-relaxed text-[#E6F1FF]">{{ draft.cover_letter }}</pre>

            <div class="mt-4">
              <h4 class="font-mono-tech text-[10px] text-[#FFC857] mb-2">3 CV BULLET TIPS</h4>
              <ul class="grid gap-2">
                <li
                  v-for="(tip, index) in draft.bullet_tips"
                  :key="index"
                  class="border-l-2 border-[#FFC857] bg-[#2A2410]/40 px-2 py-1 text-xs text-[#E6F1FF]"
                >
                  {{ tip }}
                </li>
              </ul>
            </div>

            <div class="mt-4">
              <h4 class="font-mono-tech text-[10px] text-[#19E3FF] mb-2">
                SOURCE CITATIONS
              </h4>
              <div class="grid gap-2">
                <article
                  v-for="citation in draft.citations"
                  :key="`${citation.project_slug}-${citation.section}`"
                  class="border border-[#22345E] bg-[#0A0F1F] p-2"
                >
                  <div class="flex flex-wrap items-center justify-between gap-2">
                    <p class="font-mono-tech text-[10px] text-[#E6F1FF]">
                      {{ citation.project_title }}
                      <span class="text-[#8FA6C8]">// {{ citation.section }}</span>
                    </p>
                    <span class="font-mono-tech text-[9px] text-[#3DF5A6]">
                      {{ (citation.similarity * 100).toFixed(1) }}% MATCH
                    </span>
                  </div>
                  <p class="mt-1 text-[10px] text-[#8FA6C8] leading-relaxed">
                    {{ citation.text }}
                  </p>
                </article>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- Application tracker -->
      <div class="mt-6 border border-[#22345E] bg-[#0A0F1F] p-4">
        <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
          <h3 class="font-mono-tech text-xs text-[#19E3FF]">
            03 // APPLICATION TRACKER
          </h3>
          <button
            type="button"
            @click="loadJobs"
            class="font-mono-tech text-[10px] text-[#8FA6C8] hover:text-[#19E3FF] cursor-pointer"
          >
            REFRESH
          </button>
        </div>

        <p v-if="jobsError" class="font-mono-tech text-xs text-[#FF4D8D]">{{ jobsError }}</p>
        <p v-else-if="!jobs.length" class="text-xs text-[#8FA6C8]">
          No tracked applications yet. Analyze a job to create one.
        </p>
        <p v-if="statusError" class="mb-2 font-mono-tech text-xs text-[#FF4D8D]">
          {{ statusError }}
        </p>

        <div v-if="jobs.length" class="grid gap-2">
          <article
            v-for="job in jobs"
            :key="job.id"
            class="flex flex-wrap items-center justify-between gap-3 border border-[#22345E] bg-[#050914] px-3 py-2"
          >
            <div class="min-w-0">
              <p class="font-orbitron text-xs font-bold text-[#E6F1FF] truncate">
                {{ job.title }}
              </p>
              <p class="font-mono-tech text-[9px] text-[#8FA6C8]">
                SCORE {{ job.score }} // {{ job.id.slice(0, 8) }}
              </p>
            </div>
            <label class="flex items-center gap-2">
              <span class="sr-only">Status for {{ job.title }}</span>
              <select
                :value="job.status"
                :disabled="statusBusyId === job.id"
                @change="updateStatus(job, $event)"
                class="bg-[#02060F] border border-[#22345E] px-2 py-1 font-mono-tech text-[10px] text-[#E6F1FF] focus:outline-none focus:border-[#3DF5A6] disabled:opacity-60"
              >
                <option v-for="status in STATUS_OPTIONS" :key="status" :value="status">
                  {{ status.toUpperCase() }}
                </option>
              </select>
            </label>
          </article>
        </div>
      </div>

      <div class="mt-4 border border-[#FFC857]/40 bg-[#2A2410]/30 px-4 py-3">
        <p class="font-mono-tech text-[10px] text-[#FFC857] leading-relaxed">
          SAFETY: URL fetches allow only http/https, reject private/loopback/link-local
          addresses before connecting, do not follow redirects, time out after 5
          seconds, and cap the response at 100 KB. Fetched JDs are treated as
          untrusted data. The assistant never submits an application.
        </p>
      </div>
    </div>
  </section>
</template>
