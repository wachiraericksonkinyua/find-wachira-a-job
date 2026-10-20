import { ref } from 'vue'
import { defineStore } from 'pinia'

// Day 6 will swap this for import.meta.env.VITE_API_URL.
const API_URL = 'http://127.0.0.1:8000'

export const usePetStore = defineStore('pet', () => {
  // Shared state: any component can read these and updates happen everywhere.
  const desperation = ref(0)
  const label = ref('Loading...')
  const mood = ref('sleeping')
  const quip = ref('')
  const loading = ref(false)
  const error = ref(null)

  // Copy the fields we care about from an API response into our refs.
  function applyState(data) {
    if (typeof data.desperation === 'number') desperation.value = data.desperation
    if (data.label) label.value = data.label
    if (data.mood) mood.value = data.mood
    if (data.quip) quip.value = data.quip
  }

  async function fetchState() {
    loading.value = true
    error.value = null

    try {
      const res = await fetch(`${API_URL}/api/pet/state`)
      if (!res.ok) throw new Error(`Could not read the meter (HTTP ${res.status})`)
      applyState(await res.json())
      return true
    } catch (err) {
      error.value = 'The monkey is offline. Try again in a moment.'
      console.error(err)
      return false
    } finally {
      loading.value = false
    }
  }

  async function interact(type, note = '') {
    loading.value = true
    error.value = null

    try {
      const res = await fetch(`${API_URL}/api/pet/interact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // Only send a note when there is one, so "book" stays a one-click action.
        body: JSON.stringify(note ? { type, note } : { type }),
      })

      const data = await res.json().catch(() => ({}))

      if (!res.ok) {
        // 429 sends a string detail; 422 sends an array of validation errors.
        const detail = data.detail
        error.value = Array.isArray(detail)
          ? detail[0]?.msg || 'That note did not pass validation.'
          : detail || `Something went wrong (HTTP ${res.status}).`
        return null
      }

      applyState(data)
      // The server forces "happy" right after a successful interaction.
      mood.value = 'happy'
      return data
    } catch (err) {
      error.value = 'The monkey could not reach the server.'
      console.error(err)
      return null
    } finally {
      loading.value = false
    }
  }

  return {
    desperation,
    label,
    mood,
    quip,
    loading,
    error,
    fetchState,
    interact,
  }
})
