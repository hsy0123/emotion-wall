import { ledViewModel, previewPixel, LABELS, LED_LAYOUT } from './led-model.js'

export function createLedView(root, onFrame = () => {}) {
  root.innerHTML = `
    <div class="led-heading"><div><span class="eyebrow">EMOTION IN LIGHT</span><h3>빛으로 보는 나의 감정</h3></div><span class="led-badge" id="ledBadge"></span></div>
    <p class="led-message">가장 크게 느껴지는 감정과 그 곁의 감정들을 빛의 흐름으로 만나보세요.</p>
    <p class="led-message">감정의 강도에 따라 빛의 흐름도 달라져요.<br>격한 마음은 빠르게, 차분한 마음은 느리게 흐릅니다.</p>
    <ol class="led-ranking" id="ledRanking"></ol>
    <div class="led-preview" aria-label="위, 가운데, 아래 세 줄의 빛 효과 예시">
      ${LED_LAYOUT.map(({ count: n, row, label }) => `<div class="led-column"><span class="led-row-label">${label}</span><div class="led-strip" data-row="${row}" aria-hidden="true">${Array.from({length:n}, () => '<i class="led-pixel"></i>').join('')}</div><span class="led-speed" data-row="${row}"></span></div>`).join('')}
    </div>
    <p class="led-message">시간이 짧을수록 빠르게 움직여요.</p>
    <div class="led-preview-footer"><p id="ledPreviewNote"></p><button type="button" class="preview-toggle" aria-pressed="false">미리보기 멈추기</button></div>`
  const badge = root.querySelector('#ledBadge')
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
      badge.textContent = model.state === 'sent' ? '전달 확인' : model.state === 'error' ? '전송 실패' : '빛 미리보기'
      const rankedEntries = model.names.map((name, index) => ({name, color: model.colors[index]}))
        .filter((item, index, items) => item.name !== 'neutral' && items.findIndex(other => other.name === item.name) === index)
      ranking.replaceChildren(...rankedEntries.map(({name, color}, i) => {
        const li = document.createElement('li'), dot = document.createElement('span')
        dot.className = 'rank-color'; dot.style.background = `rgb(${color.join(',')})`
        li.append(dot, document.createTextNode(`${i === 0 ? '가장 큰 감정' : '함께 느끼는'} · ${LABELS[name]}`)); return li
      }))
      if (!rankedEntries.length) {
        const li = document.createElement('li'); li.textContent = '뚜렷한 감정이 없어 기본색으로 표현해요.'; ranking.append(li)
      }
      speedLabels.forEach(el => { const row = Number(el.dataset.row); el.textContent = `색상 이동 주기 · ${((row ? model.period : model.leftPeriod)/1000).toFixed(2)}초` })
      note.textContent = '화면은 빛의 움직임을 미리 보여주는 예시예요. 재생과 멈추기는 화면에만 적용됩니다.'
      paint(); sync()
    },
  }
}
