<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'

defineProps({
  professionalMode: {
    type: Boolean,
    default: false
  }
})

const shooed = ref(false)
const menuOpen = ref(false)
const cornerIndex = ref(0)
const flipRight = ref(false)
const desperation = ref(68)

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

const meterInfo = computed(() => {
  if (desperation.value <= 25) return { label: 'Smug', color: '#3DF5A6' }
  if (desperation.value <= 50) return { label: 'Hungry', color: '#19E3FF' }
  if (desperation.value <= 75) return { label: 'Starving', color: '#FFC857' }
  return { label: 'Crying in binary', color: '#FF4D8D' }
})

const quip = computed(() => {
  if (customQuip.value) return customQuip.value
  if (desperation.value <= 25) return "I'm not unemployed, I'm between side quests."
  if (desperation.value <= 50) return 'Quietly preparing my next move, one application at a time.'
  if (desperation.value <= 75) return 'This job hunt is curated chaos, and I am surviving it.'
  return 'The bills are not going to pay themselves, but you could help.'
})

const currentSprite = computed(() => {
  if (activeSprite.value) return activeSprite.value
  if (desperation.value > 75) return 'anxious'
  if (desperation.value > 25) return 'smug'
  return 'sleeping'
})

function giveRelief(amount, message) {
  desperation.value = Math.max(0, desperation.value - amount)
  activeSprite.value = 'happy'
  customQuip.value = message
  menuOpen.value = false
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
  window.addEventListener('mousemove', handleMouseMove)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', handleMouseMove)
  clearTimeout(stopTimer)
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
          <span>DESPERATION: {{ meterInfo.label.toUpperCase() }}</span>
          <span>{{ desperation }}%</span>
        </div>
        <div class="w-full h-2 bg-[#050914] border border-[#22345E]">
          <div 
            class="h-full transition-all duration-300"
            :style="{ width: desperation + '%', backgroundColor: meterInfo.color }"
          />
        </div>
      </div>

      <div class="flex flex-col gap-1.5 text-xs font-mono-tech">
        <button @click="giveRelief(5, 'A link! You absolute legend.')" class="p-1.5 bg-[#0D1630] border border-[#22345E] hover:border-[#19E3FF] text-left cursor-pointer">
          🔗 Share a link (-5%)
        </button>
        <button @click="giveRelief(8, 'A lead! Writing that down immediately.')" class="p-1.5 bg-[#0D1630] border border-[#22345E] hover:border-[#19E3FF] text-left cursor-pointer">
          🎯 Drop a lead (-8%)
        </button>
        <button @click="giveRelief(12, 'An intro?! Best recruiter on the internet.')" class="p-1.5 bg-[#0D1630] border border-[#22345E] hover:border-[#19E3FF] text-left cursor-pointer">
          🤝 Intro me to someone (-12%)
        </button>
        <button @click="giveRelief(12, 'You know a person? Say less.')" class="p-1.5 bg-[#0D1630] border border-[#22345E] hover:border-[#19E3FF] text-left cursor-pointer">
          🕵️ I know a person (-12%)
        </button>
        <a href="#book" @click="giveRelief(20, 'An interview?! Excuse me while I fix my tie.')" class="p-1.5 bg-[#3DF5A6] text-[#06101F] font-bold text-center block">
          📅 Book interview (-20%)
        </a>
      </div>

      <button @click="shooed = true" class="mt-2 w-full text-[11px] text-[#8FA6C8] hover:text-[#FF4D8D] cursor-pointer">
        Shoo monkey (hide)
      </button>
    </div>

    <!-- 2. SPEECH BUBBLE + MINI DESPERATION BAR -->
    <div class="panel px-3 py-2 mb-2 max-w-[210px] text-left">
      <p class="text-xs text-[#E6F1FF] leading-tight">{{ quip }}</p>
      <div class="w-full h-1.5 bg-[#050914] mt-1.5 overflow-hidden">
        <div 
          class="h-full transition-all duration-300"
          :style="{ width: desperation + '%', backgroundColor: meterInfo.color }"
        />
      </div>
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