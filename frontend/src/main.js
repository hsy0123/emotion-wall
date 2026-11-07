
import './style.scss'

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
  { key: 'neutral', name: '평온/중립', color: '#FFE9C7' },
]

// =====================================
// 2. 화면 생성
// =====================================

document.querySelector('#app').innerHTML = `
  <main class="emotion-app">

    <!-- 헤더 -->
    <header class="app-header">
      <div class="brand">
        <span class="brand-icon">✿</span>
        <strong>Emotion Wall</strong>
      </div>
      <span class="menu-icon" aria-hidden="true">☰</span>
    </header>

    <!-- 소개 -->
    <section class="intro">
      <h1>오늘 당신의 감정을<br>분석해볼까요? 💜</h1>
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
              <span class="emotion-face">☺</span>
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

      <div
  id="ballInfo"
  class="ball-info"
  role="status"
  aria-live="polite"
>
  말랑이를 터치하면 색상 정보를 볼 수 있어요.
</div>


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

    if (!Array.isArray(data.leds) || !data.grid) {
      throw new Error('말랑이 색상 데이터가 없습니다.')
    }

    // A파트 grid 설정 적용
    ballGrid.style.display = 'grid'
    ballGrid.style.gridTemplateColumns =
      `repeat(${data.grid.cols}, minmax(0, 1fr))`

    ballGrid.style.gap = '12px'
    ballGrid.style.marginTop = '24px'

    // 배선 index와 실제 화면 위치(row, col)는
    // 다를 수 있으므로 위치를 명시적으로 지정
    
    ballGrid.innerHTML = data.leds
      .map((led, index) => {
        const [r, g, b] = led.rgb

        return `
          <button
            type="button"
            class="emotion-ball"
            style="
              --ball-rgb: ${r}, ${g}, ${b};
              --ball-delay: ${index * 70}ms;
              grid-row: ${led.row + 1};
              grid-column: ${led.col + 1};
            "
            data-index="${led.index}"
            data-rgb="${r}, ${g}, ${b}"
            aria-label="감정 말랑이 ${led.index + 1}, RGB ${r}, ${g}, ${b}"
            aria-pressed="false"
          ></button>
        `
      })
      .join('')

    // =====================================
    // 11. 분석 날짜 표시
    // =====================================

    resultDate.textContent = new Date().toLocaleString('ko-KR')

    // 결과 영역 표시
    resultSection.hidden = false

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
    alert('감정 분석에 실패했습니다: ' + error.message)

  } finally {
    button.disabled = false
    button.textContent = '감정 분석하기'
    button.removeAttribute('aria-busy')
  }
})

/* =====================================
   STEP 8: 말랑이 터치 이벤트
===================================== */


const ballInfo = document.querySelector('#ballInfo')

ballGrid.addEventListener('click', (event) => {
  const ball = event.target.closest('.emotion-ball')
  if (!ball || !ballGrid.contains(ball)) return

  // 말랑이 클릭 애니메이션
  ball.classList.remove('squish')
  void ball.offsetWidth
  ball.classList.add('squish')

  // 선택 상태 변경
  ballGrid.querySelectorAll('.emotion-ball').forEach(item => {
    item.classList.remove('selected')
    item.setAttribute('aria-pressed', 'false')
  })

  ball.classList.add('selected')
  ball.setAttribute('aria-pressed', 'true')

  // RGB 정보 표시
  const index = Number(ball.dataset.index) + 1
  const rgb = ball.dataset.rgb
  const values = rgb.split(',').map(Number)
    .map(v => Math.max(0, Math.min(255, v)))
    .join(', ')

  ballInfo.innerHTML = `
    <div class="ball-info-title">말랑이 ${index}</div>
    <div class="ball-info-color">
      <span class="ball-color-chip"
            style="background: rgb(${values})"></span>
      <span>RGB (${values})</span>
    </div>
  `
})
