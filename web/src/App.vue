<script setup>
import { ref, onMounted } from 'vue'
import Pet from './components/Pet.vue'

// Reactive state variables
const apiOnline = ref(false)
const professionalMode = ref(false)

// Lifecycle Hook: Runs automatically when the component mounts on the screen
onMounted(async () => {
  try {
    // Ping your local FastAPI backend to verify it's awake
    const res = await fetch('http://127.0.0.1:8000/health')
    const data = await res.json()
    apiOnline.value = (data.status === 'ok')
  } catch (err) {
    console.error('Backend offline:', err)
    apiOnline.value = false
  }
})
</script>

<template>
  <div class="min-h-screen pb-24">
    
    <!-- Top Sticky Navigation Bar -->
    <header class="border-b border-[#22345E] bg-[#0A0F1F]/90 sticky top-0 z-10 backdrop-blur">
      <div class="max-w-4xl mx-auto px-5 py-3 flex items-center justify-between">
        
        <!-- FastAPI Server Health Indicator -->
        <div class="flex items-center gap-2">
          <span :class="['w-2.5 h-2.5 rounded-full', apiOnline ? 'bg-[#3DF5A6]' : 'bg-[#FF4D8D]']" />
          <span class="font-mono-tech text-xs text-[#8FA6C8]">
            API: {{ apiOnline ? 'ONLINE' : 'OFFLINE' }}
          </span>
        </div>

        <!-- Playful / Professional Mode Toggle Button -->
        <button
          @click="professionalMode = !professionalMode"
          class="px-3 py-1 border border-[#22345E] bg-[#101A33] text-xs font-mono-tech text-[#E6F1FF] cursor-pointer hover:border-[#19E3FF]"
        >
          MODE: {{ professionalMode ? 'PROFESSIONAL 👔' : 'PLAYFUL 👾' }}
        </button>
      </div>
    </header>

    <!-- Main Content Area -->
    <main class="max-w-4xl mx-auto px-5 pt-10">
      
      <!-- 10-Second Recruiter Pitch (Above the Fold) -->
      <section class="mb-8">
        <p class="font-pixel text-[10px] text-[#19E3FF] mb-2">
          NAIROBI, KENYA // AVAILABLE FOR INTERNSHIPS & JUNIOR ROLES
        </p>
        <h1 class="font-orbitron text-3xl md:text-5xl font-black tracking-tight mb-3">
          FIND <span class="bg-[#19E3FF] text-[#06101F] px-2">WACHIRA</span> A JOB
        </h1>
        <p class="text-[#8FA6C8] text-lg max-w-2xl">
          Final-year B.Sc. IT Engineer building production backends with <b>FastAPI & PostgreSQL</b>, modern <b>Vue.js</b> interfaces, and hardened <b>AI/LLM pipelines</b>.
        </p>
      </section>

      <!-- The Pet Component (Passes down the professionalMode property) -->
      <Pet :professionalMode="professionalMode" />
    </main>

    <!-- Sticky Floating "Book Interview" Button -->
    <div class="fixed bottom-5 right-5 z-20">
      <a
        href="#book"
        class="panel inline-flex items-center gap-3 px-6 py-3 font-orbitron font-bold text-sm shadow-lg hover:opacity-90 transition-opacity"
        style="background: var(--leaf); color: #06101F;"
      >
        <span>BOOK INTERVIEW</span>
        <span class="font-pixel text-[10px]">→</span>
      </a>
    </div>

  </div>
</template>