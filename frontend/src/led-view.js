import { ledViewModel, previewPixel, LABELS, LED_LAYOUT } from './led-model.js'

export function createLedView(root, onFrame = () => {}) {
  root.innerHTML = `
    <div class="led-heading"><div><span class="eyebrow">EMOTION IN LIGHT</span><h3>빛으로 보는 나의 감정</h3></div><span class="led-badge" id="ledBadge"></span></div>
    <p class="led-message" id="ledMessage" role="status" aria-live="polite"></p>
    <ol class="led-ranking" id="ledRanking"></ol>
    <div class="led-preview" aria-label="위, 가운데, 아래 세 줄의 빛 효과 예시">
      ${LED_LAYOUT.map(({ count: n, row, label }) => `<div class="led-column"><span class="led-row-label">${label}</span><div class="led-strip" data-row="${row}" aria-hidden="true">${Array.from({length:n}, () => '<i class="led-pixel"></i>').join('')}</div><span class="led-speed" data-row="${row}"></span></div>`).join('')}
    </div>
    <p class="led-message">감정이 격할수록 빠르게, 차분할수록 천천히 흘러요. 이동 주기가 짧을수록 빠릅니다.</p>
    <div class="led-preview-footer"><p id="ledPreviewNote"></p><button type="button" class="preview-toggle" aria-pressed="false">미리보기 멈추기</button></div>`
  const badge = root.querySelector('#ledBadge'), message = root.querySelector('#ledMessage')
  const ranking = root.querySelector('#ledRanking'), note = root.querySelector('#ledPreviewNote')
  const strips = [...root.querySelectorAll('.led-strip')].map(el => ({ row: Number(el.dataset.row), pixels: [...el.children] }))
  const speedLabels = [...root.querySelectorAll('.led-speed')]
  const toggle = root.querySelector('.preview-toggle')
  const media = window.matchMedia('(prefers-reduced-motion: reduce)')
  let model = null, paused = media.matches, frame = 0, lastTime = null, elapsed = 0
  function paint() {
    strips.forEach(({ pixels, row }) => pixels.forEach((pixel, i) => {
      const color = previewPixel(model, row, i, elapsed).join(',')
      pixel.style.setProperty('--pixel-rgb', color)
    }))
    onFrame(model, elapsed)
  }
  function tick(time) {
    frame = 0
    if (!model || paused || document.hidden) { lastTime = null; return }
    if (lastTime !== null) elapsed += Math.min(time - lastTime, 100)
    lastTime = time
    paint()
    frame = requestAnimationFrame(tick)
  }
  function sync() {
    cancelAnimationFrame(frame); lastTime = null
    toggle.textContent = paused ? '미리보기 재생' : '미리보기 멈추기'
    toggle.setAttribute('aria-pressed', String(paused))
    if (model && !paused && !document.hidden) frame = requestAnimationFrame(tick)
  }
  toggle.addEventListener('click', () => { paused = !paused; sync() })
  media.addEventListener('change', () => { paused = media.matches; sync() })
  document.addEventListener('visibilitychange', sync)
  return {
    pending() {
      root.hidden = true
      cancelAnimationFrame(frame); model = null
    },
    update(data) {
      model = ledViewModel(data); elapsed = 0
      root.hidden = false; root.dataset.state = model.state
      badge.textContent = model.state === 'sent' ? '전달 확인' : model.state === 'error' ? '전송 실패' : '표현 예시'
      message.textContent = `${model.title} — ${model.detail}`
      const rankedEntries = model.names.map((name, index) => ({name, color: model.colors[index]}))
        .filter((item, index, items) => item.name !== 'neutral' && items.findIndex(other => other.name === item.name) === index)
      ranking.replaceChildren(...rankedEntries.map(({name, color}, i) => {
        const li = document.createElement('li'), dot = document.createElement('span')
        dot.className = 'rank-color'; dot.style.background = `rgb(${color.join(',')})`
        li.append(dot, document.createTextNode(`${i+1}순위 ${LABELS[name]}`)); return li
      }))
      if (!rankedEntries.length) {
        const li = document.createElement('li'); li.textContent = '뚜렷한 감정이 없어 기본색으로 표현해요.'; ranking.append(li)
      }
      speedLabels.forEach(el => { const row = Number(el.dataset.row); el.textContent = `${model.estimated ? '예상 ' : ''}${((row ? model.period : model.leftPeriod)/1000).toFixed(2)}초 / 주기` })
      note.textContent = '화면은 효과를 이해하기 위한 예시입니다. 실제 LED의 색 전환·밝기·방향은 다를 수 있어요. 말랑이는 이 예시보다 천천히 움직입니다. 재생·멈추기는 이 미리보기에만 적용됩니다.'
      paint(); sync()
    },
  }
}
