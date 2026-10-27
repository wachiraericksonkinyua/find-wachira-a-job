<script setup>
import { ref, onMounted } from 'vue'
import { useStream } from '../composables/useStream'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const projects = ref([])
const loading = ref(true)
const error = ref(null)

// For the Monkey Judgment stream - we'll keep track of the active stream here
const monkeyStream = ref(null)

onMounted(async () => {
  try {
    const response = await fetch(`${API_URL}/api/projects`)
    if (!response.ok) throw new Error('Failed to load projects')
    projects.value = await response.json()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})

// Monkey judgment handler
const askMonkey = (project) => {
  // If we already have a stream, stop it
  if (monkeyStream.value) monkeyStream.value.stopStream()
  
  // Create a new stream for this project
  const stream = useStream()
  monkeyStream.value = stream
  
  const context = encodeURIComponent(`Tell me about the ${project.title} project build.`)
  stream.startStream(`${API_URL}/api/pet/judgment?action=inspect_project&context=${context}`)
}
</script>

<template>
  <section id="projects" class="mt-16 scroll-mt-24">
    <h2 class="font-orbitron text-2xl md:text-3xl font-bold mb-8">CASE STUDIES</h2>
    
    <div v-if="loading" class="text-[#8FA6C8]">Loading projects...</div>
    <div v-else-if="error" class="text-[#FF4D8D]">{{ error }}</div>
    
    <div v-else class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      <div v-for="p in projects" :key="p.id" class="panel p-6 flex flex-col">
        <h3 class="font-orbitron text-xl font-bold mb-1">{{ p.title }}</h3>
        
        <div class="flex flex-wrap gap-2 mb-4">
          <span v-for="tech in p.stack" :key="tech" class="px-2 py-0.5 bg-[#0D1630] border border-[#22345E] text-[#19E3FF] text-[10px] font-mono-tech">
            {{ tech }}
          </span>
        </div>
        
        <div class="flex-grow space-y-4 mb-6">
          <div>
            <h4 class="text-[10px] font-pixel text-[#19E3FF] mb-1">PROBLEM</h4>
            <p class="text-sm text-[#E6F1FF] leading-relaxed">{{ p.problem }}</p>
          </div>
          <div>
            <h4 class="text-[10px] font-pixel text-[#19E3FF] mb-1">BUILD</h4>
            <p class="text-sm text-[#E6F1FF] leading-relaxed">{{ p.build }}</p>
          </div>
          <div>
            <h4 class="text-[10px] font-pixel text-[#19E3FF] mb-1">OUTCOME</h4>
            <p class="text-sm text-[#E6F1FF] leading-relaxed">{{ p.outcome }}</p>
          </div>
        </div>

        <button 
          @click="askMonkey(p)"
          class="w-full py-2 border border-[#19E3FF] text-[#19E3FF] hover:bg-[#19E3FF] hover:text-[#06101F] font-bold font-mono-tech text-xs transition-colors"
        >
          ASK MONKEY ABOUT THIS BUILD
        </button>
      </div>
    </div>
  </section>
</template>
