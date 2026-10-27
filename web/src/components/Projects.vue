<script setup>
import { ref, onMounted } from 'vue'
import { useStream } from '../composables/useStream'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const projects = ref([])
const loading = ref(true)
const error = ref(null)

// Track monkey state per project
const monkeyStates = ref({})

onMounted(async () => {
  try {
    const response = await fetch(`${API_URL}/api/projects`)
    if (!response.ok) throw new Error('Failed to load projects')
    projects.value = await response.json()
    // Initialize states
    projects.value.forEach(p => {
        monkeyStates.value[p.id] = useStream()
    })
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})

// Monkey judgment handler
const askMonkey = (project) => {
  const stream = monkeyStates.value[project.id]
  if (stream.streaming.value) stream.stopStream()
  
  stream.startStream(`${API_URL}/api/projects/${project.id}/inspect`)
}
</script>

<template>
  <section id="projects" class="mt-16 scroll-mt-24">
    <h2 class="font-orbitron text-2xl md:text-3xl font-bold mb-8">CASE STUDIES</h2>
    
    <div v-if="loading" class="text-[var(--text-muted)]">Loading projects...</div>
    <div v-else-if="error" class="text-[var(--danger)]">{{ error }}</div>
    
    <div v-else class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      <div v-for="p in projects" :key="p.id" class="panel p-6 flex flex-col">
        <h3 class="font-orbitron text-xl font-bold mb-1">{{ p.title }}</h3>
        
        <div class="flex flex-wrap gap-2 mb-4">
          <span v-for="tech in p.stack" :key="tech" class="px-2 py-0.5 bg-[var(--panel-bg)] border border-[var(--border)] text-[var(--accent)] text-[10px] font-mono-tech">
            {{ tech }}
          </span>
        </div>
        
        <div class="flex-grow space-y-4 mb-6">
          <div>
            <h4 class="text-[10px] font-pixel text-[var(--accent)] mb-1">PROBLEM</h4>
            <p class="text-sm text-[var(--text-main)] leading-relaxed">{{ p.problem }}</p>
          </div>
          <div>
            <h4 class="text-[10px] font-pixel text-[var(--accent)] mb-1">BUILD</h4>
            <p class="text-sm text-[var(--text-main)] leading-relaxed">{{ p.build }}</p>
          </div>
          <div>
            <h4 class="text-[10px] font-pixel text-[var(--accent)] mb-1">OUTCOME</h4>
            <p class="text-sm text-[var(--text-main)] leading-relaxed">{{ p.outcome }}</p>
          </div>
        </div>

        <button 
          @click="askMonkey(p)"
          class="w-full mb-3 py-2 border border-[var(--accent)] text-[var(--accent)] hover:bg-[var(--accent)] hover:text-[var(--bg)] font-bold font-mono-tech text-xs transition-colors"
        >
          {{ monkeyStates[p.id].streaming.value ? 'MONKEY IS THINKING...' : 'ASK MONKEY ABOUT THIS BUILD' }}
        </button>

        <!-- Display area for the stream -->
        <div v-if="monkeyStates[p.id].text.value || monkeyStates[p.id].streaming.value || monkeyStates[p.id].error.value" 
            class="mt-2 p-3 bg-[var(--panel-bg)] border border-[var(--border)] text-sm text-[var(--text-main)] italic">
          <span v-if="monkeyStates[p.id].error.value" class="text-[var(--danger)]">{{ monkeyStates[p.id].error.value }}</span>
          <span v-else>{{ monkeyStates[p.id].text.value || '...' }}</span>
        </div>
      </div>
    </div>
  </section>
</template>
