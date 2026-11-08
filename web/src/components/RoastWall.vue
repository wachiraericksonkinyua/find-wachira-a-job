<script setup>
import { computed, onMounted, ref } from 'vue'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const PRESET_TAGS = [
  'Portfolio UI',
  'Printer Whisperer',
  'Ugali the Monkey',
  'AI Lab',
  'Resume Copy',
  'General',
]

const roasts = ref([])
const loading = ref(true)
const error = ref(null)

const form = ref({ text: '', target: PRESET_TAGS[0], customTarget: '' })
const submitting = ref(false)
const submitError = ref(null)
const submitted = ref(null)

const effectiveTarget = computed(() => {
  if (form.value.target === '__custom__') return form.value.customTarget.trim()
  return form.value.target
})

async function loadRoasts() {
  loading.value = true
  error.value = null
  try {
    const response = await fetch(`${API_URL}/api/roast-wall`)
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw new Error(data?.detail || `Roast wall failed (HTTP ${response.status}).`)
    }
    roasts.value = Array.isArray(data) ? data : []
  } catch (err) {
    error.value = err.message || 'Could not load the roast wall.'
  } finally {
    loading.value = false
  }
}

async function submitRoast() {
  if (submitting.value) return
  submitting.value = true
  submitError.value = null
  submitted.value = null

  try {
    const response = await fetch(`${API_URL}/api/roast-wall`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: form.value.text,
        target: effectiveTarget.value || null,
      }),
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      const detail = data?.detail
      throw new Error(
        Array.isArray(detail)
          ? detail.map((item) => item?.msg).filter(Boolean).join('; ')
          : detail || `Submission failed (HTTP ${response.status}).`
      )
    }
    submitted.value = data
    form.value = { text: '', target: PRESET_TAGS[0], customTarget: '' }
  } catch (err) {
    submitError.value = err.message || 'The roast could not be submitted.'
  } finally {
    submitting.value = false
  }
}

function formatDate(value) {
  if (!value) return 'just now'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

onMounted(loadRoasts)
</script>

<template>
  <div class="grid gap-6">
    <section class="panel p-5 md:p-7" aria-label="Roast wall feed">
      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p class="page-kicker text-[#FF4D8D]">APPROVED · ANONYMOUS</p>
          <h2 class="font-orbitron text-xl font-bold">LIVE FROM THE WALL</h2>
        </div>
        <span class="font-mono-tech text-[10px] text-[#8FA6C8]">
          {{ roasts.length }} {{ roasts.length === 1 ? 'roast' : 'roasts' }}
        </span>
      </div>

      <p v-if="loading" class="font-mono-tech text-xs text-[#19E3FF]">Loading approved roasts...</p>
      <p v-else-if="error" role="alert" class="font-mono-tech text-xs text-[#FF4D8D]">{{ error }}</p>
      <div v-else-if="!roasts.length" class="border border-[#22345E] bg-[#050914] p-6 text-center">
        <p class="font-mono-tech text-xs text-[#8FA6C8]">
          No approved roasts yet. Be the first to leave honest, anonymous feedback.
        </p>
      </div>

      <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <article
          v-for="roast in roasts"
          :key="roast.id"
          class="roast-card flex flex-col border border-[#22345E] bg-[#050914] p-4"
        >
          <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="font-mono-tech text-[10px] text-[#3DF5A6]">
              {{ roast.author || '@anonymous_dev' }}
            </span>
            <span class="font-mono-tech text-[9px] text-[#8FA6C8]">
              {{ formatDate(roast.created_at) }}
            </span>
          </div>
          <span
            v-if="roast.target"
            class="mt-2 w-fit border border-[#FF4D8D]/50 bg-[#2A1220] px-2 py-0.5 font-mono-tech text-[9px] text-[#FF4D8D]"
          >
            TARGET: {{ roast.target }}
          </span>
          <blockquote class="mt-3 flex-grow text-sm leading-relaxed text-[#E6F1FF]">
            “{{ roast.text }}”
          </blockquote>
          <p v-if="roast.advice" class="mt-3 border-l-2 border-[#3DF5A6] pl-2 text-xs text-[#A9BCD9]">
            {{ roast.advice }}
          </p>
        </article>
      </div>
    </section>

    <section class="panel p-5 md:p-6" aria-labelledby="roast-submit-title">
      <div class="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p class="page-kicker text-[#3DF5A6]">LEAVE FEEDBACK</p>
          <h2 id="roast-submit-title" class="font-orbitron text-xl font-bold">
            POST A ROAST
          </h2>
        </div>
        <span class="font-mono-tech text-[9px] text-[#FFC857]">PENDING REVIEW</span>
      </div>

      <p class="mb-4 text-xs text-[#A9BCD9]">
        No name, company, email, or IP address is collected. Every submission is
        manually moderated before it appears publicly. Public cards show only
        <span class="text-[#3DF5A6]">@anonymous_dev</span>.
      </p>

      <form class="grid gap-3" @submit.prevent="submitRoast">
        <label class="grid gap-1">
          <span class="font-mono-tech text-[10px] text-[#8FA6C8]">TARGET TAG</span>
          <select v-model="form.target" class="input-tech w-full">
            <option v-for="tag in PRESET_TAGS" :key="tag" :value="tag">{{ tag }}</option>
            <option value="__custom__">Custom target...</option>
          </select>
        </label>
        <label v-if="form.target === '__custom__'" class="grid gap-1">
          <span class="font-mono-tech text-[10px] text-[#8FA6C8]">CUSTOM TARGET (MAX 80)</span>
          <input
            v-model="form.customTarget"
            type="text"
            maxlength="80"
            class="input-tech w-full"
            placeholder="e.g. That resume font"
          />
        </label>
        <label class="grid gap-1">
          <span class="font-mono-tech text-[10px] text-[#8FA6C8]">
            ROAST <span class="text-[#8FA6C8]/60">({{ form.text.length }}/280)</span>
          </span>
          <textarea
            v-model="form.text"
            rows="3"
            required
            minlength="5"
            maxlength="280"
            :disabled="submitting"
            placeholder="What should be sharper, clearer, or more honest?"
            class="input-tech w-full resize-y"
          />
        </label>

        <p v-if="submitError" role="alert" class="font-mono-tech text-xs text-[#FF4D8D]">
          {{ submitError }}
        </p>
        <p v-if="submitted" role="status" aria-live="polite" class="font-mono-tech text-xs text-[#3DF5A6]">
          {{ submitted.message }}
        </p>

        <button type="submit" :disabled="submitting" class="btn-primary w-fit">
          {{ submitting ? 'SUBMITTING...' : 'SUBMIT ANONYMOUSLY' }}
        </button>
      </form>
    </section>
  </div>
</template>
