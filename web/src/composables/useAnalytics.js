const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const SESSION_KEY = 'fwaj_analytics_session'

function getSessionId() {
  try {
    const existing = sessionStorage.getItem(SESSION_KEY)
    if (existing) return existing
    const generated =
      (globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function')
        ? globalThis.crypto.randomUUID()
        : `s_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
    sessionStorage.setItem(SESSION_KEY, generated)
    return generated
  } catch {
    return 'anonymous'
  }
}

/**
 * Fire-and-forget anonymous funnel event. Analytics must never break the UI,
 * so every failure is swallowed.
 */
export function trackEvent(name, session = getSessionId()) {
  try {
    void fetch(`${API_URL}/api/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, session }),
      keepalive: true,
    }).catch(() => {})
  } catch {
    // Ignore storage/network failures.
  }
}
