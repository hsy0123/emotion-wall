const API_URL = (import.meta.env?.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')

export async function analyzeText(text, { fetchImpl = fetch, timeoutMs = 90000 } = {}) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetchImpl(`${API_URL}/analyze`, {
      method: 'POST', signal: controller.signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })
    if (!response.ok) throw new Error(`서버 오류: ${response.status}`)
    return await response.json()
  } finally {
    clearTimeout(timeout)
  }
}
