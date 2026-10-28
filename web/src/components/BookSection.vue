<script setup>
import { computed, ref } from 'vue'
import { usePetStore } from '../stores/pet'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const petStore = usePetStore()

const emptyForm = () => ({
  name: '',
  company: '',
  contact: '',
  role: '',
  preferred_time: '',
  message: ''
})

const form = ref(emptyForm())
const submitting = ref(false)
const error = ref(null)
const success = ref(null)

const canSubmit = computed(
  () => !submitting.value && form.value.name.trim().length >= 2 && form.value.contact.trim().length >= 3
)

async function submitBooking() {
  if (!canSubmit.value) return

  submitting.value = true
  error.value = null
  success.value = null

  try {
    const response = await fetch(`${API_URL}/api/book`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value)
    })
    const data = await response.json().catch(() => null)

    if (!response.ok) {
      const detail = data?.detail
      throw new Error(
        Array.isArray(detail)
          ? detail.map((item) => item?.msg).filter(Boolean).join('; ')
          : detail || `Booking failed (HTTP ${response.status}).`
      )
    }

    success.value = {
      name: form.value.name.trim(),
      company: form.value.company.trim()
    }
    form.value = emptyForm()
    await petStore.fetchState()
  } catch (err) {
    error.value = err.message || 'The booking could not be sent.'
  } finally {
    submitting.value = false
  }
}

const adminOpen = ref(false)
const adminKey = ref('')
const adminLoading = ref(false)
const adminError = ref(null)
const leads = ref(null)
const LEAD_TYPES = new Set(['link', 'lead', 'intro', 'know_person'])

const petLeads = computed(() =>
  (leads.value?.pet_leads || []).filter((lead) => LEAD_TYPES.has(lead.type))
)
const bookings = computed(() => leads.value?.bookings || [])

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

async function fetchLeads() {
  adminLoading.value = true
  adminError.value = null

  try {
    const response = await fetch(`${API_URL}/api/admin/leads`, {
      headers: { 'X-Admin-Key': adminKey.value }
    })
    const data = await response.json().catch(() => null)

    if (!response.ok) {
      if (response.status === 401) sessionStorage.removeItem('admin_api_key')
      throw new Error(data?.detail || `Could not load leads (HTTP ${response.status}).`)
    }

    leads.value = data
  } catch (err) {
    adminError.value = err.message || 'Could not load the leads.'
  } finally {
    adminLoading.value = false
  }
}

async function toggleAdmin() {
  if (adminOpen.value) {
    adminOpen.value = false
    return
  }

  let key = sessionStorage.getItem('admin_api_key') || ''
  if (!key) {
    key = (window.prompt('Enter the X-Admin-Key') || '').trim()
    if (!key) return
    sessionStorage.setItem('admin_api_key', key)
  }

  adminKey.value = key
  adminOpen.value = true
  await fetchLeads()
}

function changeAdminKey() {
  sessionStorage.removeItem('admin_api_key')
  adminKey.value = ''
  adminOpen.value = false
  leads.value = null
  adminError.value = null
}
</script>

<template>
  <section id="book" class="mt-16 scroll-mt-24">
    <div class="panel p-6 md:p-8">
      <div class="flex flex-wrap items-end justify-between gap-3 mb-5">
        <div>
          <p class="font-pixel text-[10px] text-[#19E3FF] mb-2">READY TO TALK?</p>
          <h2 class="font-orbitron text-2xl md:text-3xl font-bold">BOOK AN INTERVIEW</h2>
          <p class="text-[#8FA6C8] mt-2 max-w-2xl">
            Send the role, the team, or a time that works. The monkey watches every
            real booking and gets a little less desperate.
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          <a
            href="mailto:ericksonkinyua681@gmail.com?subject=Interview%20request"
            class="px-3 py-2 border border-[#3DF5A6] bg-[#0D2A24] text-[#3DF5A6] font-mono-tech text-xs hover:bg-[#3DF5A6] hover:text-[#06101F]"
          >
            EMAIL
          </a>
          <a
            href="https://www.linkedin.com/in/erickson-kinyua-28b7b2327"
            target="_blank"
            rel="noopener noreferrer"
            class="px-3 py-2 border border-[#19E3FF] bg-[#0D2230] text-[#19E3FF] font-mono-tech text-xs hover:bg-[#19E3FF] hover:text-[#06101F]"
          >
            LINKEDIN
          </a>
        </div>
      </div>

      <div
        v-if="success"
        role="status"
        aria-live="polite"
        class="mb-5 border border-[#3DF5A6] bg-[#0D2A24] px-4 py-3 font-mono-tech text-sm text-[#3DF5A6] shadow-[0_0_28px_rgba(61,245,166,0.35)]"
      >
        INTERVIEW REQUEST RECEIVED // Thanks, {{ success.name }}. The monkey just felt
        the desperation drop.
      </div>

      <div
        v-if="error"
        role="alert"
        class="mb-5 border border-[#FF4D8D] bg-[#2A1220] px-4 py-3 font-mono-tech text-sm text-[#FF4D8D]"
      >
        {{ error }}
      </div>

      <form @submit.prevent="submitBooking" class="grid gap-4">
        <div class="grid gap-4 md:grid-cols-2">
          <label class="grid gap-1">
            <span class="font-mono-tech text-xs text-[#8FA6C8]">
              NAME <span class="text-[#FF4D8D]">*</span>
            </span>
            <input
              v-model="form.name"
              type="text"
              required
              minlength="2"
              maxlength="100"
              :disabled="submitting"
              placeholder="Your name"
              class="bg-[#050914] border border-[#22345E] px-3 py-2 text-sm text-[#E6F1FF] placeholder:text-[#8FA6C8] focus:outline-none focus:border-[#19E3FF] disabled:opacity-60"
            />
          </label>

          <label class="grid gap-1">
            <span class="font-mono-tech text-xs text-[#8FA6C8]">COMPANY</span>
            <input
              v-model="form.company"
              type="text"
              maxlength="120"
              :disabled="submitting"
              placeholder="Company or team"
              class="bg-[#050914] border border-[#22345E] px-3 py-2 text-sm text-[#E6F1FF] placeholder:text-[#8FA6C8] focus:outline-none focus:border-[#19E3FF] disabled:opacity-60"
            />
          </label>

          <label class="grid gap-1">
            <span class="font-mono-tech text-xs text-[#8FA6C8]">
              EMAIL / PHONE / LINKEDIN <span class="text-[#FF4D8D]">*</span>
            </span>
            <input
              v-model="form.contact"
              type="text"
              required
              minlength="3"
              maxlength="160"
              :disabled="submitting"
              placeholder="How should Wachira reply?"
              class="bg-[#050914] border border-[#22345E] px-3 py-2 text-sm text-[#E6F1FF] placeholder:text-[#8FA6C8] focus:outline-none focus:border-[#19E3FF] disabled:opacity-60"
            />
          </label>

          <label class="grid gap-1">
            <span class="font-mono-tech text-xs text-[#8FA6C8]">ROLE</span>
            <input
              v-model="form.role"
              type="text"
              maxlength="120"
              :disabled="submitting"
              placeholder="Role or team"
              class="bg-[#050914] border border-[#22345E] px-3 py-2 text-sm text-[#E6F1FF] placeholder:text-[#8FA6C8] focus:outline-none focus:border-[#19E3FF] disabled:opacity-60"
            />
          </label>

          <label class="grid gap-1 md:col-span-2">
            <span class="font-mono-tech text-xs text-[#8FA6C8]">PREFERRED TIME</span>
            <input
              v-model="form.preferred_time"
              type="text"
              maxlength="120"
              :disabled="submitting"
              placeholder="e.g. Tuesday morning, Nairobi time"
              class="bg-[#050914] border border-[#22345E] px-3 py-2 text-sm text-[#E6F1FF] placeholder:text-[#8FA6C8] focus:outline-none focus:border-[#19E3FF] disabled:opacity-60"
            />
          </label>

          <label class="grid gap-1 md:col-span-2">
            <span class="font-mono-tech text-xs text-[#8FA6C8]">MESSAGE</span>
            <textarea
              v-model="form.message"
              rows="4"
              maxlength="1000"
              :disabled="submitting"
              placeholder="Anything useful before the call..."
              class="w-full resize-y bg-[#050914] border border-[#22345E] px-3 py-2 text-sm leading-relaxed text-[#E6F1FF] placeholder:text-[#8FA6C8] focus:outline-none focus:border-[#19E3FF] disabled:opacity-60"
            />
          </label>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            :disabled="!canSubmit"
            class="px-4 py-2 bg-[#19E3FF] text-[#06101F] font-bold font-mono-tech text-xs hover:opacity-90 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ submitting ? 'SENDING REQUEST...' : 'BOOK INTERVIEW' }}
          </button>
          <span class="font-mono-tech text-[11px] text-[#8FA6C8]">
            Rate-limited to keep the spam bots out.
          </span>
        </div>
      </form>

      <div class="mt-6 border-t border-[#22345E] pt-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <p class="font-pixel text-[10px] text-[#22345E]">ADMIN // VIEW LEADS</p>
          <div class="flex gap-2">
            <button
              v-if="adminOpen"
              type="button"
              @click="changeAdminKey"
              class="px-2 py-1 border border-[#22345E] bg-[#0D1630] text-[#8FA6C8] font-mono-tech text-[10px] hover:border-[#FF4D8D] hover:text-[#FF4D8D] cursor-pointer"
            >
              CHANGE KEY
            </button>
            <button
              type="button"
              @click="toggleAdmin"
              class="px-2 py-1 border border-[#22345E] bg-[#0D1630] text-[#8FA6C8] font-mono-tech text-[10px] hover:border-[#19E3FF] hover:text-[#19E3FF] cursor-pointer"
            >
              {{ adminOpen ? 'HIDE LEADS' : 'ADMIN // VIEW LEADS' }}
            </button>
          </div>
        </div>

        <div v-if="adminOpen" class="mt-4 grid gap-4">
          <p v-if="adminLoading" class="font-mono-tech text-xs text-[#19E3FF]">
            Loading leads...
          </p>
          <p v-else-if="adminError" class="font-mono-tech text-xs text-[#FF4D8D]">
            {{ adminError }}
          </p>

          <template v-else-if="leads">
            <div>
              <h3 class="font-mono-tech text-[11px] text-[#3DF5A6] mb-2">
                BOOKINGS // {{ bookings.length }}
              </h3>
              <p v-if="!bookings.length" class="text-xs text-[#8FA6C8]">No bookings yet.</p>
              <div class="grid gap-2">
                <article
                  v-for="booking in bookings"
                  :key="booking.id"
                  class="border border-[#22345E] bg-[#050914] p-3"
                >
                  <div class="flex flex-wrap items-start justify-between gap-2">
                    <p class="font-orbitron text-sm font-bold text-[#E6F1FF]">
                      {{ booking.name }}
                      <span v-if="booking.company" class="text-[#8FA6C8]">
                        // {{ booking.company }}
                      </span>
                    </p>
                    <span class="font-mono-tech text-[10px] text-[#8FA6C8]">
                      {{ formatDate(booking.created_at) }}
                    </span>
                  </div>
                  <p class="mt-1 font-mono-tech text-xs text-[#19E3FF]">
                    {{ booking.contact }}
                    <span v-if="booking.role" class="text-[#8FA6C8]">// {{ booking.role }}</span>
                  </p>
                  <p v-if="booking.preferred_time" class="mt-1 text-xs text-[#FFC857]">
                    Preferred: {{ booking.preferred_time }}
                  </p>
                  <p v-if="booking.message" class="mt-2 text-sm text-[#8FA6C8]">
                    {{ booking.message }}
                  </p>
                </article>
              </div>
            </div>

            <div>
              <h3 class="font-mono-tech text-[11px] text-[#19E3FF] mb-2">
                PET LEADS // {{ petLeads.length }}
              </h3>
              <p v-if="!petLeads.length" class="text-xs text-[#8FA6C8]">
                No pet leads yet.
              </p>
              <div class="grid gap-2">
                <article
                  v-for="(lead, index) in petLeads"
                  :key="`${lead.timestamp || lead.created_at}-${index}`"
                  class="border border-[#22345E] bg-[#050914] p-3"
                >
                  <div class="flex flex-wrap items-center justify-between gap-2">
                    <span class="px-2 py-0.5 border border-[#19E3FF] bg-[#0D2230] text-[#19E3FF] font-mono-tech text-[10px]">
                      {{ lead.type.toUpperCase() }}
                    </span>
                    <span class="font-mono-tech text-[10px] text-[#8FA6C8]">
                      {{ formatDate(lead.timestamp || lead.created_at) }}
                    </span>
                  </div>
                  <p class="mt-2 text-sm text-[#E6F1FF] break-words">
                    {{ lead.note || 'No note provided.' }}
                  </p>
                </article>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </section>
</template>
