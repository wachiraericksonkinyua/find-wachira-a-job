<template>
  <div class="panel p-5 mt-8">
    <h3 class="font-orbitron text-lg text-[#19E3FF] mb-4">Excuse Buster</h3>
    <div class="controls flex gap-2 mb-4">
      <label for="excuse-select" class="sr-only">Select an excuse to debunk</label>
      <select id="excuse-select" v-model="selectedId" :disabled="streaming" class="bg-[#0A0F1F] border border-[#22345E] text-[#E6F1FF] p-2 flex-grow">
        <option value="" disabled>Select an excuse...</option>
        <option v-for="excuse in excuses" :key="excuse.id" :value="excuse.id">
          {{ excuse.text }}
        </option>
      </select>
      <button @click="debunk" :disabled="!selectedId || streaming" class="px-4 py-2 bg-[#19E3FF] text-[#06101F] font-bold disabled:opacity-50">
        {{ streaming ? 'Debunking...' : 'Debunk' }}
      </button>
    </div>

    <div class="output-box p-4 border border-[#22345E] bg-[#06101F] min-h-[120px] font-mono text-sm">
      <p v-if="error" class="text-[#FF4D8D]">{{ error }}</p>
      <pre v-else class="whitespace-pre-wrap">{{ text || "Select an excuse and let the monkey tear it apart." }}</pre>
      <div v-if="streaming" class="text-[#19E3FF] animate-pulse">_</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useStream } from '../composables/useStream';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const excuses = ref([]);
const selectedId = ref('');
const { text, streaming, error, startStream } = useStream();

onMounted(async () => {
  try {
    const response = await fetch(`${API_URL}/api/excuses`);
    if (!response.ok) throw new Error('Could not load excuses');
    excuses.value = await response.json();
  } catch (e) {
    error.value = "Failed to load excuses";
  }
});

const debunk = () => {
  if (!selectedId.value) return;
  startStream(`${API_URL}/api/excuse-buster`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ excuse_id: selectedId.value }),
  });
};
</script>
