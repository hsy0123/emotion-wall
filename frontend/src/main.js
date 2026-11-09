import './style.scss'
import { appTemplate } from './app-template.js'
import { analyzeText } from './api-client.js'
import { createResultView } from './result-view.js'
import { createLedView } from './led-view.js'

const app = document.querySelector('#app')
app.innerHTML = appTemplate
const textarea = app.querySelector('#emotionText')
const button = app.querySelector('#submitButton')
const errorMessage = app.querySelector('#analysisError')
const results = createResultView(app)
const lights = createLedView(app.querySelector('#ledSection'), results.paintBalls)

textarea.addEventListener('input', () => {
  app.querySelector('#count').textContent = textarea.value.length
})

button.addEventListener('click', async () => {
  const text = textarea.value.trim()
  if (!text) {
    alert('감정을 표현하는 문장을 입력해 주세요.')
    textarea.focus()
    return
  }
  errorMessage.hidden = true
  lights.pending()
  button.disabled = true
  button.setAttribute('aria-busy', 'true')
  button.innerHTML = '<span class="loading-spinner" aria-hidden="true"></span><span>감정을 분석하고 있어요...</span>'
  try {
    const data = await analyzeText(text)
    results.render(data)
    lights.update(data)
    results.show()
  } catch (error) {
    console.error(error)
    errorMessage.textContent = error.name === 'AbortError'
      ? '분석 응답이 늦어지고 있어요. 잠시 후 다시 시도해주세요.'
      : '감정 분석 서버에 연결하지 못했어요. 인터넷 연결과 서버 실행 상태를 확인하고 다시 시도해주세요.'
    errorMessage.hidden = false
  } finally {
    button.disabled = false
    button.textContent = '감정 분석하기'
    button.removeAttribute('aria-busy')
  }
})
