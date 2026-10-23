<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import { usePetStore } from '../stores/pet'
import { useStream } from '../composables/useStream'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

defineProps({
  professionalMode: {
    type: Boolean,
    default: false
  }
})

const pet = usePetStore()
const { desperation, label, mood, quip, loading, error } = storeToRefs(pet)
const {
  text: streamText,
  streaming: streamLoading,
  error: streamError,
  startStream,
  stopStream
} = useStream()

const shooed = ref(false)
const menuOpen = ref(false)
const cornerIndex = ref(0)
const flipRight = ref(false)

// One draft note per action that needs it. "book" has no note, so it is absent.
const notes = ref({
  link: '',
  lead: '',
  intro: '',
  know_person: ''
})

// Override sprite and quip when mouse interacts
const activeSprite = ref(null)
const customQuip = ref(null)
const monkeyBtn = ref(null)

// Safe corners that NEVER overlap the top navbar or bottom-right Book button
const corners = [
  'bottom-5 left-5',
  'top-20 left-5',
  'top-20 right-5'
]

const meterColor = computed(() => {
  if (desperation.value <= 25) return '#3DF5A6'
  if (desperation.value <= 50) return '#19E3FF'
  if (desperation.value <= 75) return '#FFC857'
  return '#FF4D8D'
})

// Errors win so a failed interaction is visible in the bubble. A live or
// finished judgment stays put until the next interaction clears it.
const speech = computed(() => {
  if (error.value) return error.value
  if (streamError.value) return streamError.value
  if (streamLoading.value || streamText.value) {
    return streamText.value || 'The monkey is judging you...'
  }
  if (customQuip.value) return customQuip.value
  return quip.value || 'Click me. I dare you.'
})

const currentSprite = computed(() => {
  if (activeSprite.value) return activeSprite.value
  return mood.value
})

async function submitRelief(type) {
  stopStream()
  streamText.value = ''
  streamError.value = null

  const data = await pet.interact(type, notes.value[type] || '')
  // On failure the store sets error; the bubble shows it and the menu stays open.
  if (!data) return null

  if (type in notes.value) notes.value[type] = ''
  // Clear local overrides so the server's fresh mood/quip take over.
  activeSprite.value = null
  customQuip.value = null
  menuOpen.value = false
  return data
}

async function bookInterview() {
  const data = await submitRelief('book')
  if (data) document.querySelector('#book')?.scrollIntoView({ behavior: 'smooth' })
}

function judgeScroll() {
  const context = encodeURIComponent('The recruiter is skimming the projects section.')
  activeSprite.value = 'judging'
  customQuip.value = null
  startStream(
    `${API_URL}/api/pet/judgment?action=scroll_projects&context=${context}`
  )
}

function hopCorner() {
  if (menuOpen.value) return
  cornerIndex.value = (cornerIndex.value + 1) % corners.length
  activeSprite.value = 'smug'
  customQuip.value = "Nope. You'll have to earn that click."
}

// --- DAY 6: JUDGY MOUSE TRACKING & DODGING ---
let stopTimer
let lastHopTime = 0 // Tracks when the monkey last dodged

function handleMouseMove(e) {
  if (menuOpen.value || shooed.value) return

  if (monkeyBtn.value) {
    const rect = monkeyBtn.value.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2

    // Mirror sprite left or right to look toward cursor
    flipRight.value = e.clientX > centerX

    // Dodge if cursor gets within 85px, ONLY if it hasn't dodged in the last 6 seconds!
    const distance = Math.hypot(e.clientX - centerX, e.clientY - centerY)
    const now = Date.now()
    if (distance < 85 && now - lastHopTime > 6000) {
      lastHopTime = now
      hopCorner()
      return
    }
  }

  activeSprite.value = 'judging'
  customQuip.value = "Oh, we're clicking things now? Bold."

  clearTimeout(stopTimer)
  stopTimer = window.setTimeout(() => {
    activeSprite.value = 'looking-away'
    customQuip.value = "Don't mind me. Not watching. Totally."
  }, 2000)
}

onMounted(() => {
  pet.fetchState()
  window.addEventListener('mousemove', handleMouseMove)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', handleMouseMove)
  clearTimeout(stopTimer)
  stopStream()
})
</script>

<template>
  <div 
    v-if="!professionalMode && !shooed" 
    :class="['fixed z-30 transition-all duration-500 select-none', corners[cornerIndex]]"
  >
    <!-- 1. CLICK MENU POPUP -->
    <div v-if="menuOpen" class="panel p-4 mb-3 w-64 text-left shadow-2xl">
      <div class="flex justify-between items-center mb-2">
        <span class="font-pixel text-[9px] text-[#19E3FF]">RELIEF MENU</span>
        <button @click="menuOpen = false" class="text-xs text-[#8FA6C8] hover:text-white cursor-pointer">✕</button>
      </div>

      <div class="mb-3">
        <div class="flex justify-between text-xs font-mono-tech mb-1">
          <span>DESPERATION: {{ label.toUpperCase() }}</span>
          <span>{{ desperation }}%</span>
        </div>
        <div class="w-full h-2 bg-[#050914] border border-[#22345E]">
          <div 
            class="h-full transition-all duration-300"
            :style="{ width: desperation + '%', backgroundColor: meterColor }"
          />
        </div>
      </div>

      <button
        @click="judgeScroll"
        :disabled="streamLoading"
        class="w-full mb-3 p-2 bg-[#19E3FF] text-[#06101F] font-bold text-xs hover:opacity-90 cursor-pointer disabled:opacity-50 disabled:cursor-wait"
      >
        {{ streamLoading ? 'JUDGING...' : 'JUDGE MY SCROLL' }}
      </button>

      <div class="flex flex-col gap-1.5 text-xs font-mono-tech">
        <div class="flex flex-col gap-1">
          <input
            v-model="notes.link"
            type="url"
            placeholder="Paste the job URL..."
            :disabled="loading"
            class="w-full bg-[#050914] border border-[#22345E] px-1.5 py-1 text-[11px] text-[#E6F1FF] placeholder:text-[#8FA6C8] focus:outline-none focus:border-[#19E3FF]"
          />
          <button @click="submitRelief('link')" :disabled="loading" class="p-1.5 bg-[#0D1630] border border-[#22345E] hover:border-[#19E3FF] text-left cursor-pointer disabled:opacity-50 disabled:cursor-wait">
            🔗 Share a link (-5%)
          </button>
        </div>

        <div class="flex flex-col gap-1">
          <input
            v-model="notes.lead"
            type="text"
            placeholder="Job board, company, or role..."
            :disabled="loading"
            class="w-full bg-[#050914] border border-[#22345E] px-1.5 py-1 text-[11px] text-[#E6F1FF] placeholder:text-[#8FA6C8] focus:outline-none focus:border-[#19E3FF]"
          />
          <button @click="submitRelief('lead')" :disabled="loading" class="p-1.5 bg-[#0D1630] border border-[#22345E] hover:border-[#19E3FF] text-left cursor-pointer disabled:opacity-50 disabled:cursor-wait">
            🎯 Drop a lead (-8%)
          </button>
        </div>

        <div class="flex flex-col gap-1">
          <input
            v-model="notes.intro"
            type="text"
            placeholder="Their name or profile link..."
            :disabled="loading"
            class="w-full bg-[#050914] border border-[#22345E] px-1.5 py-1 text-[11px] text-[#E6F1FF] placeholder:text-[#8FA6C8] focus:outline-none focus:border-[#19E3FF]"
          />
          <button @click="submitRelief('intro')" :disabled="loading" class="p-1.5 bg-[#0D1630] border border-[#22345E] hover:border-[#19E3FF] text-left cursor-pointer disabled:opacity-50 disabled:cursor-wait">
            🤝 Intro me to someone (-12%)
          </button>
        </div>

        <div class="flex flex-col gap-1">
          <input
            v-model="notes.know_person"
            type="text"
            placeholder="Name or profile link (no emails)..."
            :disabled="loading"
            class="w-full bg-[#050914] border border-[#22345E] px-1.5 py-1 text-[11px] text-[#E6F1FF] placeholder:text-[#8FA6C8] focus:outline-none focus:border-[#19E3FF]"
          />
          <button @click="submitRelief('know_person')" :disabled="loading" class="p-1.5 bg-[#0D1630] border border-[#22345E] hover:border-[#19E3FF] text-left cursor-pointer disabled:opacity-50 disabled:cursor-wait">
            🕵️ I know a person (-12%)
          </button>
        </div>

        <button @click="bookInterview" :disabled="loading" class="p-1.5 bg-[#3DF5A6] text-[#06101F] font-bold text-center cursor-pointer disabled:opacity-50 disabled:cursor-wait">
          📅 Book interview (-20%)
        </button>
      </div>

      <button @click="shooed = true" class="mt-2 w-full text-[11px] text-[#8FA6C8] hover:text-[#FF4D8D] cursor-pointer">
        Shoo monkey (hide)
      </button>
    </div>

    <!-- 2. SPEECH BUBBLE + MINI DESPERATION BAR -->
    <div class="panel px-3 py-2 mb-2 max-w-[210px] text-left">
      <p
        class="text-xs leading-tight"
        :class="(error || streamError) ? 'text-[#FF4D8D]' : 'text-[#E6F1FF]'"
      >
        {{ speech }}<span v-if="streamLoading" class="animate-pulse">|</span>
      </p>
      <div class="w-full h-1.5 bg-[#050914] mt-1.5 overflow-hidden">
        <div 
          class="h-full transition-all duration-300"
          :style="{ width: desperation + '%', backgroundColor: meterColor }"
        />
      </div>
      <button
        v-if="streamLoading"
        @click="stopStream"
        class="mt-1.5 font-pixel text-[8px] text-[#FF4D8D] hover:text-[#E6F1FF] cursor-pointer"
      >
        STOP STREAM
      </button>
    </div>

    <!-- 3. THE 96px FLOATING MONKEY SPRITE -->
    <div class="relative inline-block">
      <div v-if="currentSprite === 'sleeping'" class="zzz-container font-pixel text-[#19E3FF]">
        <span class="zzz z1">Z</span>
        <span class="zzz z2">z</span>
        <span class="zzz z3">z</span>
      </div>

      <button
        ref="monkeyBtn"
        @click="menuOpen = !menuOpen"
        @dblclick="hopCorner"
        title="Click for menu"
        class="w-16 h-16 md:w-24 md:h-24 cursor-pointer focus:outline-none"
      >
        <img
          :src="`/monkey/${currentSprite}.webp`"
          :alt="`Monkey mood: ${currentSprite}`"
          :class="[
            'w-full h-full object-contain drop-shadow-lg transition-transform duration-200',
            currentSprite === 'sleeping' ? 'monkey-breathe' : '',
            currentSprite === 'anxious' ? 'monkey-jitter' : '',
            flipRight ? 'scale-x-[-1]' : ''
          ]"
        />
      </button>
    </div>
  </div>
</template>

<style scoped>
@keyframes breathe {
  0%, 100% { transform: scale(1) translateY(0); }
  50% { transform: scale(1.05) translateY(-3px); }
}
.monkey-breathe {
  animation: breathe 3s ease-in-out infinite;
}

@keyframes floatZ {
  0% { opacity: 0; transform: translateY(0) scale(0.8); }
  50% { opacity: 1; }
  100% { opacity: 0; transform: translateY(-22px) translateX(8px) scale(1.2); }
}
.zzz-container {
  position: absolute;
  top: -10px;
  right: 8px;
  pointer-events: none;
}
.zzz {
  position: absolute;
  font-size: 10px;
  opacity: 0;
  animation: floatZ 2.4s infinite;
}
.z2 { animation-delay: 0.8s; right: -8px; }
.z3 { animation-delay: 1.6s; right: -16px; }

@keyframes jitter {
  0%, 100% { transform: translate(0, 0); }
  25% { transform: translate(-2px, 1px); }
  50% { transform: translate(2px, -1px); }
  75% { transform: translate(-1px, -2px); }
}
.monkey-jitter {
  animation: jitter 0.18s infinite;
}

@media (prefers-reduced-motion: reduce) {
  .monkey-breathe, .monkey-jitter, .zzz {
    animation: none !important;
  }
}
</style>