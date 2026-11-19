const DEFAULT_API_URL = import.meta.env?.PROD
  ? 'https://yebeen23-emotion-wall-api.hf.space'
  : 'http://127.0.0.1:8000'
const API_URL = (import.meta.env?.VITE_API_URL || DEFAULT_API_URL).replace(/\/+$/, '')

export async function analyzeText(text, { language = 'auto', fetchImpl = fetch, timeoutMs = 90000 } = {}) {
  if (!['auto', 'ko', 'en'].includes(language)) throw new Error('지원하지 않는 분석 언어입니다.')
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetchImpl(`${API_URL}/analyze`, {
      method: 'POST', signal: controller.signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, language }),
    })
    if (!response.ok) throw new Error(`서버 오류: ${response.status}`)
    return await response.json()
  } finally {
    clearTimeout(timeout)
  }
}
