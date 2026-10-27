<script setup>
import { computed, ref } from 'vue'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const MIN_JD = 20
const MAX_JD = 6000

const role = ref('')
const jd = ref('')
const loading = ref(false)
const error = ref(null)
const result = ref(null)

const PRESETS = [
  {
    label: 'LOAD BACKEND + M-PESA JD',
    role: 'Senior Backend Engineer',
    jd: `Senior Backend Engineer - Nairobi (Hybrid)

Requirements:
- 5+ years building Python APIs with FastAPI and PostgreSQL
- Strong REST API design and Pydantic validation
- Hands-on M-Pesa Daraja STK Push integration and webhook callback handling
- Docker, Linux, and CI-ready test pipelines
- Experience owning features end to end

You will design payment flows, harden callbacks, and ship reliable backend services.`
  },
  {
    label: 'LOAD AI + FULL-STACK JD',
    role: 'AI Full-Stack Engineer',
    jd: `AI Full-Stack Engineer - Remote or Nairobi

Requirements:
- Build LLM pipelines with structured outputs, prompt engineering, and prompt-injection defenses
- Vue 3 frontends with Pinia state and clean loading/error states
- FastAPI backends, SSE streaming, and PostgreSQL or Supabase
- Experience with rate limiting, validation, and deterministic fallbacks
- Comfortable shipping features across the stack

You will turn ambiguous product ideas into grounded, testable AI features.`
  }
]

const trimmedJd = computed(() => jd.value.trim())
const jdCount = computed(() => jd.value.length)
const jdTooShort = computed(() => trimmedJd.value.length < MIN_JD)
const jdTooLong = computed(() => jdCount.value > MAX_JD)
const canSubmit = computed(
  () => !loading.value && !jdTooShort.value && !jdTooLong.value
)

const scoreColor = computed(() => {
  if (!result.value) return '#19E3FF'
  if (result.value.score >= 75) return '#3DF5A6'
  if (result.value.score >= 50) return '#FFC857'
  return '#FF4D8D'
})

const scoreLabel = computed(() => {
  if (!result.value) return ''
  if (result.value.score >= 75) return 'STRONG FIT'
  if (result.value.score >= 50) return 'PARTIAL FIT'
  return 'WEAK FIT'
})

const scoreLabelClass = computed(() => {
  if (!result.value) return 'border-[#22345E] text-[#8FA6C8]'
  if (result.value.score >= 75) return 'border-[#3DF5A6] text-[#3DF5A6]'
  if (result.value.score >= 50) return 'border-[#FFC857] text-[#FFC857]'
  return 'border-[#FF4D8D] text-[#FF4D8D]'
})

function sectionClass(section) {
  if (section === 'problem') return 'border-[#FF4D8D] bg-[#2A1220] text-[#FF4D8D]'
  if (section === 'outcome') return 'border-[#3DF5A6] bg-[#0D2A24] text-[#3DF5A6]'
  return 'border-[#19E3FF] bg-[#0D2230] text-[#19E3FF]'
}

function loadPreset(preset) {
  role.value = preset.role
  jd.value = preset.jd
  result.value = null
  error.value = null
}

function resetForm() {
  role.value = ''
  jd.value = ''
  result.value = null
  error.value = null
}

async function submitMatch() {
  if (!canSubmit.value) return

  loading.value = true
  error.value = null
  result.value = null

  try {
    const response = await fetch(`${API_URL}/api/match`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        role: role.value.trim() || null,
        jd: trimmedJd.value
      })
    })

    if (!response.ok) {
      let detail = `Request failed with status ${response.status}`
      const body = await response.json().catch(() => null)
      if (body?.detail) {
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      }
      throw new Error(detail)
    }

    result.value = await response.json()
  } catch (err) {
    error.value = err.message || 'The match engine could not be reached.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section id="match" class="mt-16 scroll-mt-24">
    <div class="panel p-6 md:p-8">
      <div class="flex flex-wrap items-end justify-between gap-3 mb-5">
        <div>
          <p class="font-pixel text-[10px] text-[#19E3FF] mb-2">RAG TOOL // MATCH ENGINE</p>
          <h2 class="font-orbitron text-2xl md:text-3xl font-bold">
            RAG MATCH ENGINE // SCORE &amp; CITATIONS
          </h2>
          <p class="text-[#8FA6C8] mt-2 max-w-2xl">
            Paste a job description. The engine retrieves the closest project evidence,
            scores the fit, names the gaps, and shows exactly which chunks it used.
          </p>
        </div>
        <span class="font-mono-tech text-[10px] text-[#8FA6C8]">
          TOP-K RETRIEVAL + GROUNDED SCORING
        </span>
      </div>

      <form @submit.prevent="submitMatch" class="grid gap-4">
        <label class="grid gap-1">
          <span class="font-mono-tech text-xs text-[#8FA6C8]">
            TARGET ROLE <span class="text-[#22345E]">(OPTIONAL)</span>
          </span>
          <input
            v-model="role"
            type="text"
            maxlength="120"
            placeholder="e.g. Junior Backend Engineer"
            :disabled="loading"
            class="bg-[#050914] border border-[#22345E] px-3 py-2 text-sm text-[#E6F1FF] placeholder:text-[#8FA6C8] focus:outline-none focus:border-[#19E3FF] disabled:opacity-60"
          />
        </label>

        <label class="grid gap-1">
          <span class="font-mono-tech text-xs text-[#8FA6C8]">
            JOB DESCRIPTION <span class="text-[#FF4D8D]">*</span>
          </span>
          <textarea
            v-model="jd"
            rows="8"
            maxlength="6000"
            placeholder="Paste the full job description here..."
            :disabled="loading"
            class="w-full resize-y bg-[#050914] border border-[#22345E] px-3 py-2 text-sm leading-relaxed text-[#E6F1FF] placeholder:text-[#8FA6C8] focus:outline-none focus:border-[#19E3FF] disabled:opacity-60"
          />
          <div class="flex flex-wrap justify-between gap-2 font-mono-tech text-[11px]">
            <span :class="jdTooShort && jdCount > 0 ? 'text-[#FFC857]' : 'text-[#8FA6C8]'">
              {{ jdTooShort ? `At least ${MIN_JD} characters` : 'Ready to score' }}
            </span>
            <span :class="jdTooLong ? 'text-[#FF4D8D]' : 'text-[#8FA6C8]'">
              {{ jdCount }} / {{ MAX_JD }}
            </span>
          </div>
        </label>

        <div class="flex flex-wrap gap-2">
          <button
            v-for="preset in PRESETS"
            :key="preset.label"
            type="button"
            :disabled="loading"
            @click="loadPreset(preset)"
            class="px-3 py-2 border border-[#22345E] bg-[#0D1630] text-[#E6F1FF] font-mono-tech text-xs hover:border-[#19E3FF] hover:text-[#19E3FF] cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ preset.label }}
          </button>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <button
            type="submit"
            :disabled="!canSubmit"
            class="px-4 py-2 bg-[#19E3FF] text-[#06101F] font-bold font-mono-tech text-xs hover:opacity-90 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ loading ? 'SCORING MATCH...' : 'RUN MATCH ENGINE' }}
          </button>

          <button
            type="button"
            :disabled="loading"
            @click="resetForm"
            class="px-3 py-2 border border-[#22345E] bg-[#0D1630] text-[#E6F1FF] font-mono-tech text-xs hover:border-[#FF4D8D] hover:text-[#FF4D8D] cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            RESET
          </button>
        </div>
      </form>

      <div
        v-if="error"
        role="alert"
        class="mt-5 border border-[#FF4D8D] bg-[#2A1220] px-3 py-2 font-mono-tech text-sm text-[#FF4D8D]"
      >
        {{ error }}
      </div>

      <div v-if="loading" class="mt-6 border border-[#22345E] bg-[#050914] px-4 py-6 text-center">
        <p class="font-mono-tech text-sm text-[#19E3FF] animate-pulse">
          Retrieving project evidence and scoring the match...
        </p>
      </div>

      <div v-else-if="result" class="mt-6 grid gap-5" aria-live="polite">
        <div class="border border-[#22345E] bg-[#050914] p-4 md:p-5">
          <div class="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p class="font-mono-tech text-[10px] text-[#8FA6C8]">MATCH SCORE</p>
              <p class="font-orbitron text-3xl md:text-5xl font-black" :style="{ color: scoreColor }">
                {{ result.score }}<span class="text-base md:text-lg text-[#8FA6C8]"> / 100</span>
              </p>
            </div>
            <span class="px-2 py-1 border font-mono-tech text-[10px]" :class="scoreLabelClass">
              {{ scoreLabel }}
            </span>
          </div>

          <div class="mt-4 h-2 w-full overflow-hidden border border-[#22345E] bg-[#101A33]">
            <div
              class="h-full transition-all duration-500"
              :style="{ width: `${result.score}%`, backgroundColor: scoreColor }"
            />
          </div>

          <p class="mt-4 text-[#E6F1FF] leading-relaxed">{{ result.verdict }}</p>
        </div>

        <div class="grid gap-4 md:grid-cols-2">
          <div class="border border-[#22345E] bg-[#050914] p-4">
            <h3 class="font-mono-tech text-[11px] text-[#3DF5A6] mb-3">MATCHED SKILLS</h3>
            <div v-if="result.matched_skills.length" class="flex flex-wrap gap-2">
              <span
                v-for="skill in result.matched_skills"
                :key="skill"
                class="px-2 py-1 border border-[#3DF5A6] bg-[#0D2A24] text-[#3DF5A6] text-[11px] font-mono-tech"
              >
                {{ skill }}
              </span>
            </div>
            <p v-else class="text-sm text-[#8FA6C8]">No explicit skill matches detected.</p>
          </div>

          <div class="border border-[#22345E] bg-[#050914] p-4">
            <h3 class="font-mono-tech text-[11px] text-[#FFC857] mb-3">HONEST GAPS</h3>
            <div v-if="result.gaps.length" class="flex flex-wrap gap-2">
              <span
                v-for="gap in result.gaps"
                :key="gap"
                class="px-2 py-1 border border-[#FFC857] bg-[#2A2410] text-[#FFC857] text-[11px] font-mono-tech"
              >
                {{ gap }}
              </span>
            </div>
            <p v-else class="text-sm text-[#3DF5A6]">No major gaps detected.</p>
          </div>
        </div>

        <div class="border border-[#22345E] bg-[#050914] p-4">
          <h3 class="font-mono-tech text-[11px] text-[#19E3FF] mb-3">
            RETRIEVED EVIDENCE // {{ result.citations.length }} CITATIONS
          </h3>

          <div class="grid gap-3">
            <article
              v-for="(citation, index) in result.citations"
              :key="`${citation.project_slug}-${citation.section}-${index}`"
              class="border border-[#22345E] bg-[#0D1630] p-4"
            >
              <div class="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p class="font-orbitron text-sm font-bold text-[#E6F1FF]">
                    {{ citation.project_title }}
                  </p>
                  <span
                    class="inline-block mt-1 px-2 py-0.5 border font-mono-tech text-[10px]"
                    :class="sectionClass(citation.section)"
                  >
                    {{ citation.section.toUpperCase() }}
                  </span>
                </div>
                <span class="font-mono-tech text-xs text-[#19E3FF]">
                  {{ (citation.similarity * 100).toFixed(1) }}% MATCH
                </span>
              </div>
              <p class="mt-3 text-sm leading-relaxed text-[#8FA6C8]">{{ citation.text }}</p>
            </article>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
