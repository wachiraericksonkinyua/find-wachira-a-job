<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const logs = ref(null)
const loading = ref(true)
const error = ref(null)
const lastUpdated = ref(null)
let timer = null

const requests = computed(() => logs.value?.requests || [])
const rateLimits = computed(() => logs.value?.rate_limits || [])

const healthLabel = computed(() => {
  if (!logs.value) return 'UNKNOWN'
  return logs.value.health?.status === 'ok' ? 'ONLINE' : 'DEGRADED'
})

const healthColor = computed(() =>
  healthLabel.value === 'ONLINE' ? '#3DF5A6' : '#FF4D8D'
)

function statusColor(status) {
  if (status >= 500) return '#FF4D8D'
  if (status >= 400) return '#FFC857'
  return '#3DF5A6'
}

async function loadLogs() {
  loading.value = !logs.value
  error.value = null
  try {
    const response = await fetch(`${API_URL}/api/system/logs`)
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw new Error(data?.detail || `Logs failed (HTTP ${response.status}).`)
    }
    logs.value = data
    lastUpdated.value = new Date()
  } catch (err) {
    error.value = err.message || 'Could not reach the system log feed.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadLogs()
  timer = window.setInterval(loadLogs, 5000)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div class="page-shell">
    <header class="page-header">
      <p class="page-kicker text-[#3DF5A6]">LIVE TELEMETRY</p>
      <h1 class="page-title">SYSTEM LOGS</h1>
      <p class="page-copy">
        Container health, vector index status, active rate limits, and a
        request-id feed. No client IPs or secrets are exposed here.
      </p>
    </header>

    <div class="flex flex-wrap items-center gap-3 mb-5">
      <span
        class="px-2 py-1 border font-mono-tech text-[10px]"
        :style="{ color: healthColor, borderColor: healthColor }"
      >
        ● {{ healthLabel }}
      </span>
      <span v-if="lastUpdated" class="font-mono-tech text-[10px] text-[#8FA6C8]">
        LAST REFRESH: {{ lastUpdated.toLocaleTimeString() }}
      </span>
      <button type="button" class="btn-secondary ml-auto" @click="loadLogs">
        REFRESH NOW
      </button>
    </div>

    <p v-if="loading" class="font-mono-tech text-xs text-[#19E3FF]">Connecting to telemetry...</p>
    <p v-else-if="error" role="alert" class="font-mono-tech text-xs text-[#FF4D8D]">{{ error }}</p>

    <template v-else-if="logs">
      <section class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 mb-6">
        <div class="stat-card">
          <p class="stat-label">CONTAINER</p>
          <p class="stat-value text-xl" :style="{ color: healthColor }">{{ healthLabel }}</p>
          <p class="font-mono-tech text-[9px] text-[#8FA6C8] mt-1">
            DB: {{ logs.health?.database }}
          </p>
        </div>
        <div class="stat-card">
          <p class="stat-label">VECTOR STORE</p>
          <p class="stat-value text-xl text-[#19E3FF]">{{ logs.vector_store }}</p>
          <p class="font-mono-tech text-[9px] text-[#8FA6C8] mt-1">
            {{ logs.indexed_chunks }} chunks indexed
          </p>
        </div>
        <div class="stat-card">
          <p class="stat-label">LLM PROVIDERS</p>
          <p class="stat-value text-base text-[#FFC857]">
            {{ logs.llm_providers?.length ? logs.llm_providers.join(' + ').toUpperCase() : 'FALLBACK ONLY' }}
          </p>
        </div>
        <div class="stat-card">
          <p class="stat-label">SECURITY CONTROLS</p>
          <p class="stat-value text-xl text-[#3DF5A6]">{{ logs.security_controls?.length || 0 }}</p>
          <p class="font-mono-tech text-[9px] text-[#8FA6C8] mt-1">active</p>
        </div>
      </section>

      <div class="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
        <section class="panel p-5">
          <h2 class="font-mono-tech text-xs text-[#FFC857] mb-3">ACTIVE RATE LIMITS</h2>
          <div class="grid gap-2">
            <div
              v-for="limit in rateLimits"
              :key="limit.name"
              class="flex items-center justify-between gap-2 border-b border-[#22345E]/60 pb-1 font-mono-tech text-[10px]"
            >
              <span class="text-[#D7E4F8]">{{ limit.name }}</span>
              <span class="text-[#8FA6C8]">
                {{ limit.max_requests }} / {{ limit.window_seconds }}s ·
                {{ limit.active_clients }} clients
              </span>
            </div>
          </div>
        </section>

        <section class="panel p-0 overflow-hidden">
          <div class="flex items-center justify-between gap-2 border-b border-[#22345E] bg-[#0A0F1F] px-4 py-3">
            <h2 class="font-mono-tech text-xs text-[#3DF5A6]">REQUEST FEED</h2>
            <span class="font-mono-tech text-[9px] text-[#8FA6C8]">latest {{ requests.length }}</span>
          </div>
          <div class="max-h-[420px] overflow-y-auto bg-[#02060F] p-3 font-mono-tech text-[10px] leading-relaxed">
            <p v-if="!requests.length" class="text-[#8FA6C8]">No requests recorded yet.</p>
            <div
              v-for="request in requests"
              :key="request.request_id"
              class="grid grid-cols-[auto_auto_1fr_auto] gap-2 border-b border-[#22345E]/40 py-1"
            >
              <span class="text-[#8FA6C8]">{{ request.request_id.slice(0, 8) }}</span>
              <span :style="{ color: statusColor(request.status) }">{{ request.status }}</span>
              <span class="truncate text-[#D7E4F8]">{{ request.method }} {{ request.path }}</span>
              <span class="text-[#8FA6C8]">{{ request.duration_ms }}ms</span>
            </div>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>
