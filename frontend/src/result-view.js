import { chartModel } from './chart-model.js'
import { ballGradient, ballPixel } from './led-model.js'

export function createResultView(root) {
  const find = selector => root.querySelector(selector)
  const section = find('#resultSection'), grid = find('#ballGrid')
  let balls = []

  // Touch feedback never sends LED commands or opens color details.
  grid.addEventListener('click', event => {
    const ball = event.target.closest('.emotion-ball')
    if (!ball || !grid.contains(ball)) return
    ball.classList.remove('squish')
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    void ball.offsetWidth
    ball.classList.add('squish')
  })
  grid.addEventListener('animationend', event => {
    if (event.animationName === 'ball-squish') event.target.classList.remove('squish')
  })

  function render(data) {
    const { emotions, main, glow, gradient } = chartModel(data)
    find('#donutChart').style.background = gradient
    find('#mainEmotion').textContent = main.name
    find('#emotionMarker').style.background = main.color
    document.documentElement.style.setProperty('--emotion-glow', glow.join(', '))
    find('#emotionList').innerHTML = emotions.map(emotion => `
      <div class="emotion-row">
        <span class="emotion-dot" style="background:${emotion.color}"></span>
        <span class="emotion-name">${emotion.name}</span>
        <div class="emotion-bar"><div style="width:${emotion.value}%;background:${emotion.color}"></div></div>
        <span class="emotion-percent">${Math.round(emotion.value)}%</span>
      </div>
    `).join('')
    grid.style.gridTemplateColumns = 'repeat(4, minmax(0, 1fr))'
    grid.innerHTML = Array.from({ length: 12 }, (_, index) => `
      <button type="button" class="emotion-ball"
        aria-label="${['맨 위', '가운데', '맨 아래'][Math.floor(index / 4)]} 줄 감정색 말랑이 ${index % 4 + 1} 눌러보기"></button>
    `).join('')
    balls = [...grid.children]
    find('#resultDate').textContent = new Date().toLocaleString('ko-KR')
  }

  function paintBalls(model, elapsed) {
    balls.forEach((ball, index) => {
      const row = Math.floor(index / 4), column = index % 4
      ball.style.setProperty('--ball-gradient', ballGradient(model, row, column, elapsed))
      ball.style.setProperty('--ball-rgb', ballPixel(model, row, column + .5, elapsed).join(','))
    })
  }

  function show() {
    section.hidden = false
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    section.scrollIntoView({ behavior: reduced ? 'instant' : 'smooth', block: 'start' })
  }

  return { render, paintBalls, show }
}
