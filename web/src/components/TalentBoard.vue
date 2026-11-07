<script setup>
import { onMounted, ref } from 'vue'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const listings = ref([])
const loading = ref(true)
const error = ref(null)

const modalOpen = ref(false)
const form = ref({ name: '', role: '', pitch: '', link: '' })
const submitting = ref(false)
const submitError = ref(null)
const submission = ref(null)
const tokenCopied = ref(false)

const takedownId = ref('')
const takedownToken = ref('')
const takedownBusy = ref(false)
const takedownError = ref(null)
const takedownMessage = ref(null)

async function requestJson(url, options) {
  const response = await fetch(url, options)
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

async function loadBoard() {
  loading.value = true
  error.value = null
  try {
    const data = await requestJson(`${API_URL}/api/board`)
    listings.value = Array.isArray(data) ? data : []
  } catch (err) {
    error.value = err.message || 'Could not load the talent board.'
  } finally {
    loading.value = false
  }
}

function openModal() {
  modalOpen.value = true
  submission.value = null
  submitError.value = null
  tokenCopied.value = false
}

function closeModal() {
  modalOpen.value = false
  submitError.value = null
}

async function submitProfile() {
  if (submitting.value) return
  submitError.value = null
  submission.value = null

  if (!form.value.link.trim().startsWith('https://')) {
    submitError.value = 'The profile link must start with https://'
    return
  }

  submitting.value = true
  try {
    const data = await requestJson(`${API_URL}/api/board/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: form.value.name,
        role: form.value.role,
        pitch: form.value.pitch,
        link: form.value.link,
      }),
    })
    submission.value = data
    form.value = { name: '', role: '', pitch: '', link: '' }
    await loadBoard()
  } catch (err) {
    submitError.value = err.message || 'The profile could not be submitted.'
  } finally {
    submitting.value = false
  }
}

async function copyToken() {
  if (!submission.value?.takedown_token) return
  try {
    await navigator.clipboard.writeText(submission.value.takedown_token)
    tokenCopied.value = true
  } catch {
    tokenCopied.value = false
  }
}

async function removeProfile() {
  if (takedownBusy.value) return
  takedownBusy.value = true
  takedownError.value = null
  takedownMessage.value = null

  try {
    const data = await requestJson(`${API_URL}/api/board/takedown`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: takedownId.value.trim(),
        token: takedownToken.value.trim(),
      }),
    })
    takedownMessage.value = data.removed
      ? 'PROFILE REMOVED // the listing is no longer stored.'
      : 'Nothing was removed.'
    takedownId.value = ''
    takedownToken.value = ''
    submission.value = null
    await loadBoard()
  } catch (err) {
    takedownError.value = err.message || 'The profile could not be removed.'
  } finally {
    takedownBusy.value = false
  }
}

onMounted(loadBoard)
</script>

<template>
  <section id="talent" class="mt-16 scroll-mt-24">
    <div class="panel p-6 md:p-8">
      <div class="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <p class="font-pixel text-[10px] text-[#3DF5A6] mb-2">
            PEER NETWORK // OPT-IN ONLY
          </p>
          <h2 class="font-orbitron text-2xl md:text-3xl font-bold">CURATED TALENT BOARD</h2>
          <p class="text-[#8FA6C8] mt-2 max-w-2xl">
            Approved peer profiles from other builders. No emails, no scraped data,
            no auto-approval. Every submission is manually reviewed first.
          </p>
        </div>
        <button
          type="button"
          @click="openModal"
          class="px-4 py-2 bg-[#3DF5A6] text-[#06101F] font-mono-tech text-xs font-bold hover:opacity-90 cursor-pointer"
        >
          SUBMIT YOUR PROFILE (PEER OPT-IN)
        </button>
      </div>

      <p v-if="loading" class="font-mono-tech text-xs text-[#19E3FF]">
        Loading approved profiles...
      </p>
      <p v-else-if="error" role="alert" class="font-mono-tech text-xs text-[#FF4D8D]">
        {{ error }}
      </p>
      <p v-else-if="!listings.length" class="text-sm text-[#8FA6C8]">
        No approved profiles yet. Be the first to opt in.
      </p>

      <div v-else class="grid gap-4 md:grid-cols-2">
        <article
          v-for="entry in listings"
          :key="entry.id"
          class="border border-[#22345E] bg-[#050914] p-4 flex flex-col"
        >
          <div class="flex items-start justify-between gap-3">
            <div>
              <h3 class="font-orbitron text-base font-bold text-[#E6F1FF]">
                {{ entry.name }}
              </h3>
              <p class="font-mono-tech text-[11px] text-[#3DF5A6] mt-0.5">
                {{ entry.role }}
              </p>
            </div>
            <span class="px-2 py-0.5 border border-[#3DF5A6]/60 bg-[#0D2A24] font-mono-tech text-[9px] text-[#3DF5A6]">
              APPROVED
            </span>
          </div>
          <p class="text-sm text-[#8FA6C8] leading-relaxed mt-3 flex-grow">
            {{ entry.pitch }}
          </p>
          <a
            :href="entry.link"
            target="_blank"
            rel="noopener noreferrer"
            class="mt-4 inline-flex items-center gap-2 font-mono-tech text-[11px] text-[#19E3FF] hover:text-[#3DF5A6]"
          >
            VIEW PROFILE →
          </a>
        </article>
      </div>

      <div class="mt-5 border border-[#22345E] bg-[#0A0F1F] px-4 py-3">
        <p class="font-mono-tech text-[10px] text-[#8FA6C8] leading-relaxed">
          <span class="text-[#FFC857]">PRIVACY:</span> public fields are name, role,
          pitch, and an https link. No email is collected or displayed. Pending
          entries stay invisible until an admin approves them. Keep your takedown
          token private so you can remove your own listing.
        </p>
      </div>
    </div>

    <!-- Peer opt-in modal -->
    <div
      v-if="modalOpen"
      class="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-black/75 p-4 pt-16"
      role="presentation"
      @click.self="closeModal"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="talent-submit-title"
        class="panel w-full max-w-2xl p-5 md:p-6"
        @keydown.esc="closeModal"
      >
        <div class="flex items-start justify-between gap-3 mb-4">
          <div>
            <p class="font-pixel text-[9px] text-[#3DF5A6] mb-1">PEER OPT-IN</p>
            <h3 id="talent-submit-title" class="font-orbitron text-xl font-bold">
              SUBMIT YOUR PROFILE
            </h3>
          </div>
          <button
            type="button"
            @click="closeModal"
            aria-label="Close submission dialog"
            class="px-2 py-1 border border-[#22345E] font-mono-tech text-xs text-[#8FA6C8] hover:border-[#FF4D8D] hover:text-[#FF4D8D] cursor-pointer"
          >
            CLOSE
          </button>
        </div>

        <div
          v-if="submission"
          role="status"
          aria-live="polite"
          class="border border-[#3DF5A6] bg-[#0D2A24] p-4"
        >
          <p class="font-mono-tech text-xs text-[#3DF5A6]">
            PENDING REVIEW // your profile is saved and hidden until approval.
          </p>
          <p class="font-mono-tech text-[10px] text-[#8FA6C8] mt-2">
            Save this private takedown token. It is shown once.
          </p>
          <div class="mt-2 flex flex-wrap items-center gap-2">
            <code class="break-all border border-[#22345E] bg-[#02060F] px-2 py-1 font-mono-tech text-[10px] text-[#FFC857]">
              {{ submission.takedown_token }}
            </code>
            <button
              type="button"
              @click="copyToken"
              class="px-2 py-1 border border-[#19E3FF] font-mono-tech text-[10px] text-[#19E3FF] hover:bg-[#19E3FF] hover:text-[#06101F] cursor-pointer"
            >
              {{ tokenCopied ? 'COPIED' : 'COPY TOKEN' }}
            </button>
          </div>
          <p class="font-mono-tech text-[10px] text-[#8FA6C8] mt-2">
            Entry ID: <span class="text-[#E6F1FF]">{{ submission.id }}</span>
          </p>
        </div>

        <form v-else @submit.prevent="submitProfile" class="grid gap-3">
          <div class="grid gap-3 sm:grid-cols-2">
            <label class="grid gap-1">
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">NAME</span>
              <input
                v-model="form.name"
                type="text"
                required
                minlength="2"
                maxlength="60"
                :disabled="submitting"
                placeholder="Your name"
                class="bg-[#02060F] border border-[#22345E] px-3 py-2 text-sm text-[#E6F1FF] placeholder:text-[#8FA6C8]/60 focus:outline-none focus:border-[#3DF5A6] disabled:opacity-60"
              />
            </label>
            <label class="grid gap-1">
              <span class="font-mono-tech text-[10px] text-[#8FA6C8]">ROLE</span>
              <input
                v-model="form.role"
                type="text"
                required
                minlength="2"
                maxlength="80"
                :disabled="submitting"
                placeholder="e.g. Junior Backend Engineer"
                class="bg-[#02060F] border border-[#22345E] px-3 py-2 text-sm text-[#E6F1FF] placeholder:text-[#8FA6C8]/60 focus:outline-none focus:border-[#3DF5A6] disabled:opacity-60"
              />
            </label>
          </div>
          <label class="grid gap-1">
            <span class="font-mono-tech text-[10px] text-[#8FA6C8]">
              PITCH <span class="text-[#8FA6C8]/60">({{ form.pitch.length }}/240)</span>
            </span>
            <textarea
              v-model="form.pitch"
              rows="3"
              required
              minlength="10"
              maxlength="240"
              :disabled="submitting"
              placeholder="What should peers and recruiters know about you?"
              class="w-full resize-y bg-[#02060F] border border-[#22345E] px-3 py-2 text-sm leading-relaxed text-[#E6F1FF] placeholder:text-[#8FA6C8]/60 focus:outline-none focus:border-[#3DF5A6] disabled:opacity-60"
            />
          </label>
          <label class="grid gap-1">
            <span class="font-mono-tech text-[10px] text-[#8FA6C8]">PUBLIC HTTPS LINK</span>
            <input
              v-model="form.link"
              type="url"
              required
              maxlength="500"
              :disabled="submitting"
              placeholder="https://github.com/you or https://your-portfolio.dev"
              class="bg-[#02060F] border border-[#22345E] px-3 py-2 text-sm text-[#E6F1FF] placeholder:text-[#8FA6C8]/60 focus:outline-none focus:border-[#3DF5A6] disabled:opacity-60"
            />
          </label>

          <p class="font-mono-tech text-[10px] text-[#8FA6C8] leading-relaxed">
            <span class="text-[#FFC857]">PRIVACY NOTICE:</span> you are opting in to
            a public peer listing. Do not submit an email, phone number, or private
            data. The link is shown publicly and is not checked beyond the https
            scheme.
          </p>

          <p v-if="submitError" role="alert" class="font-mono-tech text-xs text-[#FF4D8D]">
            {{ submitError }}
          </p>

          <button
            type="submit"
            :disabled="submitting"
            class="px-4 py-2 bg-[#3DF5A6] text-[#06101F] font-orbitron text-xs font-bold hover:opacity-90 cursor-pointer disabled:opacity-50"
          >
            {{ submitting ? 'SUBMITTING FOR REVIEW...' : 'SUBMIT FOR REVIEW' }}
          </button>
        </form>

        <div class="mt-5 border-t border-[#22345E] pt-4">
          <p class="font-mono-tech text-[10px] text-[#8FA6C8] mb-2">
            REMOVE A LISTING // paste your entry id and takedown token
          </p>
          <form @submit.prevent="removeProfile" class="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
            <input
              v-model="takedownId"
              type="text"
              required
              placeholder="Entry ID"
              class="bg-[#02060F] border border-[#22345E] px-2 py-1.5 font-mono-tech text-[11px] text-[#E6F1FF] placeholder:text-[#8FA6C8]/60 focus:outline-none focus:border-[#FF4D8D]"
            />
            <input
              v-model="takedownToken"
              type="password"
              required
              placeholder="Takedown token"
              class="bg-[#02060F] border border-[#22345E] px-2 py-1.5 font-mono-tech text-[11px] text-[#E6F1FF] placeholder:text-[#8FA6C8]/60 focus:outline-none focus:border-[#FF4D8D]"
            />
            <button
              type="submit"
              :disabled="takedownBusy"
              class="px-3 py-1.5 border border-[#FF4D8D] font-mono-tech text-[10px] text-[#FF4D8D] hover:bg-[#FF4D8D] hover:text-[#06101F] cursor-pointer disabled:opacity-50"
            >
              {{ takedownBusy ? 'REMOVING...' : 'REMOVE' }}
            </button>
          </form>
          <p v-if="takedownError" role="alert" class="mt-2 font-mono-tech text-[10px] text-[#FF4D8D]">
            {{ takedownError }}
          </p>
          <p v-if="takedownMessage" role="status" class="mt-2 font-mono-tech text-[10px] text-[#3DF5A6]">
            {{ takedownMessage }}
          </p>
        </div>
      </div>
    </div>
  </section>
</template>
