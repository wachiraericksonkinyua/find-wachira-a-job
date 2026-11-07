<script setup>
import { computed, onMounted, ref } from 'vue'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const roasts = ref([])
const loading = ref(true)
const error = ref(null)
const deckIndex = ref(0)
let touchStartX = 0

const form = ref({ text: '', advice: '' })
const submitting = ref(false)
const submitError = ref(null)
const submitted = ref(null)

const currentRoast = computed(() => roasts.value[deckIndex.value] || null)

async function loadRoasts() {
  loading.value = true
  error.value = null
  try {
    const response = await fetch(`${API_URL}/api/roasts`)
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw new Error(data?.detail || `Roast wall failed (HTTP ${response.status}).`)
    }
    roasts.value = Array.isArray(data) ? data : []
    deckIndex.value = 0
  } catch (err) {
    error.value = err.message || 'Could not load the roast wall.'
  } finally {
    loading.value = false
  }
}

function nextRoast() {
  if (!roasts.value.length) return
  deckIndex.value = (deckIndex.value + 1) % roasts.value.length
}

function previousRoast() {
  if (!roasts.value.length) return
  deckIndex.value = (deckIndex.value - 1 + roasts.value.length) % roasts.value.length
}

function onTouchStart(event) {
  touchStartX = event.changedTouches?.[0]?.clientX ?? 0
}

function onTouchEnd(event) {
  const endX = event.changedTouches?.[0]?.clientX ?? touchStartX
  const delta = endX - touchStartX
  if (Math.abs(delta) < 45) return
  if (delta < 0) nextRoast()
  else previousRoast()
}

async function submitRoast() {
  if (submitting.value) return
  submitting.value = true
  submitError.value = null
  submitted.value = null

  try {
    const response = await fetch(`${API_URL}/api/roasts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: form.value.text,
        advice: form.value.advice || null,
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
    form.value = { text: '', advice: '' }
  } catch (err) {
    submitError.value = err.message || 'The roast could not be submitted.'
  } finally {
    submitting.value = false
  }
}

onMounted(loadRoasts)
</script>

<template>
  <div class="grid gap-6">
    <!-- Swipe deck -->
    <section class="panel p-5 md:p-7" aria-label="Roast swipe deck">
      <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <p class="page-kicker text-[#FF4D8D]">SWIPE DECK</p>
          <h2 class="font-orbitron text-xl font-bold">ANONYMOUS FEEDBACK</h2>
        </div>
        <span v-if="roasts.length" class="font-mono-tech text-[10px] text-[#8FA6C8]">
          {{ deckIndex + 1 }} / {{ roasts.length }}
        </span>
      </div>

      <p v-if="loading" class="font-mono-tech text-xs text-[#19E3FF]">Loading approved roasts...</p>
      <p v-else-if="error" role="alert" class="font-mono-tech text-xs text-[#FF4D8D]">{{ error }}</p>
      <div v-else-if="!roasts.length" class="border border-[#22345E] bg-[#050914] p-6 text-center">
        <p class="font-mono-tech text-xs text-[#8FA6C8]">
          No approved roasts yet. Be the first to leave honest, anonymous feedback.
        </p>
      </div>

      <div
        v-else-if="currentRoast"
        class="roast-card"
        tabindex="0"
        @keydown.left.prevent="previousRoast"
        @keydown.right.prevent="nextRoast"
        @touchstart.passive="onTouchStart"
        @touchend.passive="onTouchEnd"
      >
        <span class="px-2 py-0.5 border border-[#FF4D8D]/60 bg-[#2A1220] font-mono-tech text-[9px] text-[#FF4D8D]">
          ANONYMOUS // MODERATED
        </span>
        <blockquote class="font-orbitron text-lg md:text-2xl leading-snug mt-4 text-[#E6F1FF]">
          “{{ currentRoast.text }}”
        </blockquote>
        <p v-if="currentRoast.advice" class="mt-4 border-l-2 border-[#3DF5A6] pl-3 text-sm text-[#A9BCD9]">
          <span class="font-mono-tech text-[10px] text-[#3DF5A6]">ADVICE:</span>
          {{ currentRoast.advice }}
        </p>
        <div class="flex flex-wrap items-center gap-2 mt-5">
          <button type="button" class="btn-secondary" @click="previousRoast">← PREV</button>
          <button type="button" class="btn-primary" @click="nextRoast">NEXT →</button>
          <span class="font-mono-tech text-[9px] text-[#8FA6C8] ml-auto">Swipe or use arrow keys</span>
        </div>
      </div>
    </section>

    <!-- Full wall -->
    <section v-if="roasts.length" aria-labelledby="wall-title">
      <h2 id="wall-title" class="page-title text-2xl mb-3">THE WALL</h2>
      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <article v-for="roast in roasts" :key="roast.id" class="panel p-4">
          <p class="text-sm text-[#E6F1FF] leading-relaxed">“{{ roast.text }}”</p>
          <p v-if="roast.advice" class="mt-3 text-xs text-[#A9BCD9] border-l-2 border-[#3DF5A6] pl-2">
            {{ roast.advice }}
          </p>
          <p class="mt-3 font-mono-tech text-[9px] text-[#8FA6C8]">ANONYMOUS · APPROVED</p>
        </article>
      </div>
    </section>

    <!-- Submission -->
    <section class="panel p-5 md:p-6" aria-labelledby="roast-submit-title">
      <div class="flex flex-wrap items-start justify-between gap-3 mb-3">
        <div>
          <p class="page-kicker text-[#3DF5A6]">LEAVE FEEDBACK</p>
          <h2 id="roast-submit-title" class="font-orbitron text-xl font-bold">
            POST A ROAST OR ADVICE
          </h2>
        </div>
        <span class="font-mono-tech text-[9px] text-[#FFC857]">PENDING REVIEW</span>
      </div>

      <p class="text-xs text-[#A9BCD9] mb-4">
        No name, company, email, or account is collected. Every submission is
        manually moderated before it appears publicly.
      </p>

      <form @submit.prevent="submitRoast" class="grid gap-3">
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
        <label class="grid gap-1">
          <span class="font-mono-tech text-[10px] text-[#8FA6C8]">
            ADVICE <span class="text-[#8FA6C8]/60">(optional, {{ form.advice.length }}/280)</span>
          </span>
          <textarea
            v-model="form.advice"
            rows="2"
            maxlength="280"
            :disabled="submitting"
            placeholder="One concrete thing that would make it better."
            class="input-tech w-full resize-y"
          />
        </label>

        <p v-if="submitError" role="alert" class="font-mono-tech text-xs text-[#FF4D8D]">
          {{ submitError }}
        </p>
        <p v-if="submitted" role="status" aria-live="polite" class="font-mono-tech text-xs text-[#3DF5A6]">
          {{ submitted.message }} Reference: {{ submitted.id.slice(0, 8) }}
        </p>

        <button type="submit" :disabled="submitting" class="btn-primary w-fit">
          {{ submitting ? 'SUBMITTING...' : 'SUBMIT ANONYMOUSLY' }}
        </button>
      </form>
    </section>
  </div>
</template>
