
import './style.scss'
import brandLogo from './assets/emotion-wall-logo.png'
import { createLedView } from './led-view.js'
import { ballGradient, previewPixel, LED_LAYOUT } from './led-model.js'

// 백엔드 주소: 배포 시 VITE_API_URL 환경변수로 지정 (없으면 로컬 서버 사용)
const API_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')

// =====================================
// 1. 감정별 표시 설정
// A파트 palette.json 기준
// =====================================

const emotionConfig = [
  { key: 'joy', name: '기쁨', color: '#FFD23F' },
  { key: 'love', name: '사랑/따뜻함', color: '#FF7EB6' },
  { key: 'surprise', name: '놀람', color: '#2EC4B6' },
  { key: 'sadness', name: '슬픔', color: '#3A5CBE' },
  { key: 'anger', name: '분노', color: '#E63946' },
  { key: 'fear', name: '두려움/불안', color: '#5E3C99' },
  { key: 'neutral', name: '뚜렷한 감정 없음', color: '#FFE9C7' },
]

// =====================================
// 2. 화면 생성
// =====================================

document.querySelector('#app').innerHTML = `
  <main class="emotion-app">

    <!-- 헤더 -->
    <header class="app-header">
      <div class="brand">
        <img class="brand-icon" src="${brandLogo}" alt="" width="36" height="36" aria-hidden="true">
        <strong>Emotion Wall</strong>
      </div>
      <span class="menu-icon" aria-hidden="true">☰</span>
    </header>

    <!-- 소개 -->
    <section class="intro">
      <h1>오늘 당신의 감정을<br>분석해볼까요?</h1>
    </section>

    <!-- 감정 입력 -->
    <section class="input-section">
      <textarea
        id="emotionText"
        maxlength="500"
        placeholder="오늘 기분이나 생각을 자유롭게 적어주세요..."
        aria-label="감정 입력"
      ></textarea>

      <div class="char-count">
        <span id="count">0</span> / 500
      </div>

      <button id="submitButton" type="button">
        감정 분석하기
      </button>
    </section>

    <p id="analysisError" class="analysis-error" role="alert" hidden></p>

    <!-- 분석 결과 -->
    <section id="resultSection" class="result-section" hidden>

      <div class="result-header">
        <h2>분석 결과</h2>
        <span id="resultDate"></span>
      </div>

      <!-- 도넛 차트 + 감정 비율 -->
      <div class="result-content">

        <div class="donut-wrapper">
          <div
            class="donut-chart"
            id="donutChart"
            role="img"
            aria-label="감정 비율 도넛 차트"
          >
            <div class="donut-center">
              <span class="emotion-marker" id="emotionMarker" aria-hidden="true"></span>
              <small>주요 감정</small>
              <strong id="mainEmotion">-</strong>
            </div>
          </div>
        </div>

        <div class="emotion-list" id="emotionList"></div>

      </div>

      <!-- 3×4 감정 말랑이 -->
      <h3>나의 감정 말랑이</h3>

      <div
        id="ballGrid"
        class="ball-grid"
        aria-label="감정별 색상이 적용된 말랑이 12개"
      ></div>

      <section id="ledSection" class="led-section" hidden aria-label="LED 전송 결과와 효과 미리보기"></section>


    </section>

  </main>
`

// =====================================
// 3. HTML 요소 연결
// =====================================

const textarea = document.querySelector('#emotionText')
const count = document.querySelector('#count')
const button = document.querySelector('#submitButton')
const resultSection = document.querySelector('#resultSection')

const donutChart = document.querySelector('#donutChart')
const mainEmotion = document.querySelector('#mainEmotion')
const emotionList = document.querySelector('#emotionList')
const resultDate = document.querySelector('#resultDate')
const ballGrid = document.querySelector('#ballGrid')
const analysisError = document.querySelector('#analysisError')
let ballElements = []
const ledView = createLedView(document.querySelector('#ledSection'), (model, elapsed) => {
  ballElements.forEach((ball, index) => {
    const row = Math.floor(index / 4), column = index % 4
    ball.style.setProperty('--ball-gradient', ballGradient(model, row, column, elapsed))
    const layout = LED_LAYOUT[row]
    const rgb = previewPixel(model, layout.row, (column + .5) * layout.count / 4, elapsed)
    ball.style.setProperty('--ball-rgb', rgb.join(','))
  })
})

// =====================================
// 4. 입력 글자 수 표시
// =====================================

textarea.addEventListener('input', () => {
  count.textContent = textarea.value.length
})

// =====================================
// 5. 감정 분석 버튼
// =====================================

button.addEventListener('click', async () => {
  const text = textarea.value.trim()

  if (!text) {
    alert('감정을 표현하는 문장을 입력해 주세요.')
    textarea.focus()
    return
  }

  
  analysisError.hidden = true
  ledView.pending()
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 90000)
  button.disabled = true
  button.innerHTML = `
    <span class="loading-spinner" aria-hidden="true"></span>
    <span>감정을 분석하고 있어요...</span>
  `
  button.setAttribute('aria-busy', 'true')


  try {
    // FastAPI 서버로 분석 요청
    const response = await fetch(`${API_URL}/analyze`, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text }),
    })

    if (!response.ok) {
      throw new Error(`서버 오류: ${response.status}`)
    }

    const data = await response.json()

    // =====================================
    // 6. 감정별 비율 계산
    // =====================================

    const scores = data.scores ?? data.emotions

    if (!scores) {
      throw new Error('감정 분석 데이터가 없습니다.')
    }

    const emotions = emotionConfig.map(emotion => ({
      ...emotion,
      value: (scores[emotion.key] ?? 0) * 100,
    }))

    // =====================================
    // Soft Glow Step 4
    // 감정 비율에 따른 배경빛 계산
    // =====================================

    const colorMix = emotions.reduce(
      (acc, emotion) => {
        const hex = emotion.color.replace('#', '')
        const r = parseInt(hex.slice(0, 2), 16)
        const g = parseInt(hex.slice(2, 4), 16)
        const b = parseInt(hex.slice(4, 6), 16)

        const weight = emotion.value / 100

        acc.r += r * weight
        acc.g += g * weight
        acc.b += b * weight
        acc.total += weight

        return acc
      },
      { r: 0, g: 0, b: 0, total: 0 }
    )

    if (colorMix.total > 0) {
      const r = Math.round(colorMix.r / colorMix.total)
      const g = Math.round(colorMix.g / colorMix.total)
      const b = Math.round(colorMix.b / colorMix.total)

      document.documentElement.style.setProperty(
        '--emotion-glow',
        `${r}, ${g}, ${b}`
      )
    }

    const total = emotions.reduce(
      (sum, emotion) => sum + emotion.value,
      0
    )

    if (total <= 0) {
      throw new Error('감정 분석 결과가 비어 있습니다.')
    }

    // =====================================
    // 7. 도넛 차트
    // =====================================

    let current = 0

    const gradient = emotions.map(emotion => {
      const start = current
      current += (emotion.value / total) * 100

      return `${emotion.color} ${start}% ${current}%`
    }).join(', ')

    donutChart.style.background = `conic-gradient(${gradient})`

    // =====================================
    // 8. 대표 감정
    // =====================================

    const mainKey = data.dominant ?? data.main_emotion

    const main = emotionConfig.find(
      emotion => emotion.key === mainKey
    ) ?? emotions.reduce(
      (a, b) => a.value >= b.value ? a : b
    )

    mainEmotion.textContent = main.name
    document.querySelector('#emotionMarker').style.background = main.color

    // =====================================
    // 9. 감정별 비율 막대그래프
    // =====================================

    emotionList.innerHTML = emotions.map(emotion => `
      <div class="emotion-row">

        <span
          class="emotion-dot"
          style="background:${emotion.color}"
        ></span>

        <span class="emotion-name">
          ${emotion.name}
        </span>

        <div class="emotion-bar">
          <div
            style="
              width:${emotion.value}%;
              background:${emotion.color};
            "
          ></div>
        </div>

        <span class="emotion-percent">
          ${Math.round(emotion.value)}%
        </span>

      </div>
    `).join('')

    // =====================================
    // 10. Soft Glow 감정 말랑이
    // =====================================

    // Match the physical layout: top/middle dominant color; bottom ranked palette.
    ballGrid.style.gridTemplateColumns = 'repeat(4, minmax(0, 1fr))'
    ballGrid.innerHTML = Array.from({ length: 12 }, (_, index) => `
      <div class="emotion-ball" role="img"
        aria-label="${['맨 위', '가운데', '맨 아래'][Math.floor(index / 4)]} 줄 감정색 말랑이 ${index % 4 + 1}"></div>
    `).join('')
    ballElements = [...ballGrid.children]
    ledView.update(data)

    // =====================================
    // 11. 분석 날짜 표시
    // =====================================

    resultDate.textContent = new Date().toLocaleString('ko-KR')

    // 결과 영역 표시
    resultSection.hidden = false

    // 분석 결과로 부드럽게 자동 스크롤
    const reduceMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)'
    ).matches

    resultSection.scrollIntoView({
      behavior: reduceMotion ? 'instant' : 'smooth',
      block: 'start'
    })


  } catch (error) {
    console.error(error)
    analysisError.textContent = error.name === 'AbortError'
      ? '분석 응답이 늦어지고 있어요. 잠시 후 다시 시도해주세요.'
      : '감정 분석 서버에 연결하지 못했어요. 인터넷 연결과 서버 실행 상태를 확인하고 다시 시도해주세요.'
    analysisError.hidden = false

  } finally {
    clearTimeout(timeout)
    button.disabled = false
    button.textContent = '감정 분석하기'
    button.removeAttribute('aria-busy')
  }
})
