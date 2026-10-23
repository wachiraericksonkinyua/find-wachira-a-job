import { ref } from 'vue'

export function useStream() {
  const text = ref('')
  const streaming = ref(false)
  const error = ref(null)

  let controller = null

  function stopStream() {
    if (controller) {
      controller.abort()
      controller = null
    }
    streaming.value = false
  }

  function handleLine(rawLine) {
    const line = rawLine.replace(/\r$/, '')
    if (!line.startsWith('data:')) return false

    const payload = line.slice(5).trimStart()
    if (!payload) return false
    if (payload === '[DONE]') return true

    let message
    try {
      message = JSON.parse(payload)
    } catch {
      return false
    }

    if (typeof message.token === 'string') text.value += message.token
    if (typeof message.error === 'string') error.value = message.error

    return false
  }

  async function startStream(url, options = {}) {
    stopStream()

    const active = new AbortController()
    controller = active

    const { signal: _ignored, ...fetchOptions } = options

    text.value = ''
    error.value = null
    streaming.value = true

    let reader = null

    try {
      const res = await fetch(url, { ...fetchOptions, signal: active.signal })

      if (!res.ok) {
        const raw = await res.text()
        let detail
        try {
          detail = JSON.parse(raw)?.detail
        } catch {
          detail = null
        }
        throw new Error(
          typeof detail === 'string' ? detail : `Stream failed (HTTP ${res.status})`
        )
      }

      if (!res.body) throw new Error('This browser cannot read streams.')

      reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let done = false

      while (!done) {
        const { value, done: readerDone } = await reader.read()
        if (active.signal.aborted) return
        if (readerDone) break

        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (handleLine(line)) {
            done = true
            break
          }
        }
      }

      if (!done) {
        buffer += decoder.decode()
        if (buffer) handleLine(buffer)
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        error.value = err.message || 'The stream could not be read.'
      }
    } finally {
      if (reader) {
        try {
          await reader.cancel()
        } catch {
          // The stream may already be closed or aborted.
        }
        try {
          reader.releaseLock()
        } catch {
          // Ignore a lock that was already released by cancel().
        }
      }

      if (controller === active) {
        controller = null
        streaming.value = false
      }
    }
  }

  return {
    text,
    streaming,
    error,
    startStream,
    stopStream,
  }
}
