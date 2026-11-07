import { ledViewModel, previewPixel, LABELS } from './led-model.js'

export function createLedView(root) {
  root.innerHTML = `
    <div class="led-heading"><div><span class="eyebrow">EMOTION IN LIGHT</span><h3>빛으로 보는 나의 감정</h3></div><span class="led-badge" id="ledBadge"></span></div>
    <p class="led-message" id="ledMessage" role="status" aria-live="polite"></p>
    <ol class="led-ranking" id="ledRanking"></ol>
    <div class="led-preview" aria-label="왼쪽 22개, 가운데 21개, 오른쪽 21개의 LED 표현 예시">
      ${[22,21,21].map((n, row) => `<div class="led-column"><span class="led-row-label">${['왼쪽','가운데','오른쪽'][row]} · ${n}개</span><div class="led-strip" data-row="${row}" aria-hidden="true">${Array.from({length:n}, () => '<i class="led-pixel"></i>').join('')}</div><span class="led-speed"></span></div>`).join('')}
    </div>
    <div class="led-preview-footer"><p id="ledPreviewNote"></p><button type="button" class="preview-toggle" aria-pressed="false">움직임 멈추기</button></div>`
  const badge = root.querySelector('#ledBadge'), message = root.querySelector('#ledMessage')
  const ranking = root.querySelector('#ledRanking'), note = root.querySelector('#ledPreviewNote')
  const strips = [...root.querySelectorAll('.led-strip')].map(el => [...el.children])
  const speedLabels = [...root.querySelectorAll('.led-speed')]
  const toggle = root.querySelector('.preview-toggle')
  const media = window.matchMedia('(prefers-reduced-motion: reduce)')
  let model = null, paused = media.matches, frame = 0, lastTime = null, elapsed = 0
  function paint() {
    strips.forEach((pixels, row) => pixels.forEach((pixel, i) => {
      const color = previewPixel(model, row, i, elapsed).join(',')
      pixel.style.setProperty('--pixel-rgb', color)
    }))
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
    toggle.textContent = paused ? '움직임 재생' : '움직임 멈추기'
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
      ranking.replaceChildren(...model.names.map((name, i) => {
        const li = document.createElement('li'), dot = document.createElement('span')
        dot.className = 'rank-color'; dot.style.background = `rgb(${model.colors[i].join(',')})`
        li.append(dot, document.createTextNode(`${i+1}순위 ${LABELS[name]}`)); return li
      }))
      speedLabels.forEach((el, row) => { el.textContent = `${model.estimated ? '예상 ' : ''}${((row ? model.period : model.leftPeriod)/1000).toFixed(2)}초 / 회전` })
      note.textContent = '화면은 효과를 이해하기 위한 예시입니다. 실제 LED의 밝기·방향·전환 시점은 다를 수 있어요.'
      paint(); sync()
    },
  }
}
