<script setup>
import { ref, computed } from 'vue'

// 1. Accept properties passed from the parent component (App.vue)
defineProps({
  professionalMode: Boolean
})

// 2. Reactive state: hunger level percentage (starts at 28%)
const hunger = ref(28)

// 3. Computed property: updates the pet's face and quip automatically when hunger changes
const currentMood = computed(() => {
  if (hunger.value < 25) {
    return {
      name: 'STARVING',
      face: '( x _ x )',
      color: 'var(--chili)',
      quip: 'Running on fumes. Feed me Ugali or hire Wachira immediately.'
    }
  }
  if (hunger.value < 55) {
    return {
      name: 'GRUMPY',
      face: '( - _ - )',
      color: '#FBE3A0',
      quip: 'I have reviewed 400 job descriptions today. Impress me.'
    }
  }
  if (hunger.value < 85) {
    return {
      name: 'FOCUSED',
      face: '( o _ o )',
      color: 'var(--ugali)',
      quip: 'Systems optimal. Ready to match your JD against Wachira’s stack.'
    }
  }
  return {
    name: 'HYPED',
    face: '( ^ _ ^ )',
    color: 'var(--leaf)',
    quip: 'Peak Ugali power! Send the offer letter right now!'
  }
})

// Functions to modify the reactive hunger state
function feedUgali() {
  hunger.value = Math.min(100, hunger.value + 20) // Cannot go above 100%
}

function drainEnergy() {
  hunger.value = Math.max(0, hunger.value - 20) // Cannot go below 0%
}
</script>

<template>
  <!-- If professional mode is ON, show a clean, executive summary card -->
  <div v-if="professionalMode" class="panel p-5 mb-6 text-left">
    <div class="flex items-center justify-between">
      <span class="font-mono-tech text-sm text-[#19E3FF]">CANDIDATE_STATUS</span>
      <span class="font-pixel text-[10px] text-[#3DF5A6]">AVAILABLE FOR HIRE</span>
    </div>
    <p class="text-[#8FA6C8] mt-2 text-base">
      AI & Full-Stack Engineer specializing in Python (FastAPI), Vue.js, PostgreSQL (Supabase), and LLM Security.
    </p>
  </div>

  <!-- If professional mode is OFF, show the interactive guardian pet -->
  <div v-else class="panel p-6 mb-6 text-left">
    <div class="flex flex-wrap items-center justify-between gap-2 mb-4">
      <div>
        <span class="font-pixel text-[10px] text-[#19E3FF] block mb-1">
          GUARDIAN PET // MOOD: {{ currentMood.name }}
        </span>
        <p class="text-[#8FA6C8] text-sm">{{ currentMood.quip }}</p>
      </div>
      <!-- Dynamic text color based on mood -->
      <div 
        class="font-mono-tech text-2xl px-4 py-2 bg-[#050914] border border-[#22345E]"
        :style="{ color: currentMood.color }"
      >
        {{ currentMood.face }}
      </div>
    </div>

    <!-- Hunger Progress Bar -->
    <div class="mb-4">
      <div class="flex justify-between text-xs font-mono-tech mb-1">
        <span>UGALI_ENERGY_RESERVE</span>
        <span>{{ hunger }}%</span>
      </div>
      <div class="w-full h-3 bg-[#050914] border border-[#22345E] overflow-hidden">
        <div 
          class="h-full transition-all duration-300"
          :style="{ width: hunger + '%', backgroundColor: currentMood.color }"
        />
      </div>
    </div>

    <!-- Interactive Buttons -->
    <div class="flex gap-3">
      <button
        @click="feedUgali"
        class="px-4 py-2 bg-[#19E3FF] text-[#06101F] font-bold text-sm cursor-pointer hover:opacity-90"
      >
        + Feed Ugali (+20%)
      </button>
      <button
        @click="drainEnergy"
        class="px-3 py-2 border border-[#22345E] text-[#8FA6C8] text-sm cursor-pointer hover:text-white"
      >
        - Drain Energy
      </button>
    </div>
  </div>
</template>