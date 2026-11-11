// Physical display order; row IDs retain their existing USB/data mapping.
export const LED_LAYOUT = [
  { row: 2, label: '맨 위', count: 21 },
  { row: 1, label: '가운데', count: 21 },
  { row: 0, label: '맨 아래', count: 22 },
]
// The RGB palette mirrors color_mapper.py; the soft web chart keeps its own palette.
export const LED_COLORS = {
  joy: [255, 210, 0], love: [255, 0, 90], surprise: [0, 220, 255],
  sadness: [0, 25, 255], anger: [255, 0, 0], fear: [125, 0, 255],
  calm: [0, 255, 65], neutral: [255, 85, 0],
}
export const LABELS = { joy: '기쁨', love: '사랑', surprise: '놀람', sadness: '슬픔', anger: '분노', fear: '불안', calm: '차분함', neutral: '뚜렷한 감정 없음' }
const validRGB = v => Array.isArray(v) && v.length >= 3 && v.slice(0, 3).every(c => Number.isInteger(c) && c >= 0 && c <= 255)
const periodOr = (value, fallback, min = 900, max = 6000) => Number.isFinite(value) && value >= min && value <= max ? value : fallback

export function estimatedPeriod(scores, intensity) {
  const weights = { anger: 1, fear: .75, surprise: .45, sadness: -.25, neutral: .1, love: -.35, joy: -.55, calm: -.7 }
  let total = 0, activation = 0
  for (const [emotion, score] of Object.entries(scores)) {
    if (!(emotion in weights) || !Number.isFinite(score) || score < 0 || score > 1) return 3200
    total += score; activation += weights[emotion] * score
  }
  if (!total) return 3200
  activation /= total
  let rate = activation >= 0 ? 1/3.2 + activation * (1/.9 - 1/3.2) : 1/3.2 + (-activation/.7) * (1/6 - 1/3.2)
  if (Number.isFinite(intensity) && intensity >= 0 && intensity <= 1) rate *= .55 + .45 * intensity
  return Math.max(900, Math.min(6000, Math.round(1000/rate)))
}

export function ledViewModel(data) {
  const led = data.led ?? {}
  const scores = data.scores ?? data.emotions ?? {}
  const motion = data.motion ?? {}
  const ranked = Object.entries(scores).filter(([k, v]) => LED_COLORS[k] && k !== 'neutral' && Number.isFinite(v) && v > 0)
    .sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k]) => k)
  if (!ranked.length) ranked.push('neutral')
  const palette = Array.isArray(led.top_emotions) ? led : motion
  const names = Array.isArray(palette.top_emotions) && palette.top_emotions.length === 3 && palette.top_emotions.every(k => LED_COLORS[k]) ? palette.top_emotions : [...ranked]
  while (names.length < 3) names.push(names[0])
  const primary = LED_COLORS[names[0]]
  const colors = Array.isArray(palette.top_colors) && palette.top_colors.length === 3 && palette.top_colors.every(validRGB)
    ? palette.top_colors.map(v => v.slice(0, 3)) : names.map(k => LED_COLORS[k])
  const fallbackPeriod = periodOr(motion.flow_period_ms, estimatedPeriod(scores, data.intensity))
  const period = periodOr(led.flow_period_ms, fallbackPeriod)
  const fallbackTop = periodOr(motion.top_flow_period_ms, Math.max(600, Math.min(2400, Math.round(period * .55))), 600, 2400)
  const leftPeriod = periodOr(led.left_flow_period_ms, fallbackTop, 600, 2400)
  let state = 'unavailable', title = 'LED 전송 정보 없음', detail = '이 서버는 LED 전송 상태를 제공하지 않습니다. 아래는 표현 예시입니다.'
  if (led.enabled === false) {
    state = 'preview'; title = '미리보기 모드'; detail = '감정 분석은 완료됐어요. 이 서버에서는 USB LED 전송이 꺼져 있습니다.'
  } else if (led.sent === true) {
    state = 'sent'; title = 'LED 명령 전달 확인'; detail = 'ESP32의 수신 응답을 받았습니다. 실제 발광 상태는 직접 확인해주세요.'
  } else if (led.enabled === true) {
    state = 'error'; title = '분석 완료 · LED 전송 실패'
    const error = String(led.error ?? '').toLowerCase()
    detail = /busy|errno 16/.test(error) ? 'Arduino 시리얼 모니터나 같은 USB 포트를 쓰는 프로그램을 닫고 다시 분석해주세요.'
      : /no such file|errno 2|not found/.test(error) ? 'USB 연결과 서버에 설정된 포트 이름을 확인한 뒤 다시 분석해주세요.'
      : /err,format|err,top|rejected/.test(error) ? '최신 LED 코드를 보드에 업로드했는지 확인해주세요.'
      : /timeout|ack/.test(error) ? '보드의 수신 응답이 없습니다. USB 연결과 업로드한 코드를 확인해주세요.'
      : 'USB 연결·포트 설정을 확인해주세요. 감정 분석 결과는 아래에서 볼 수 있습니다.'
  }
  return { state, title, detail, names, colors, primary: validRGB(led.rgbw) ? led.rgbw.slice(0, 3) : primary,
    period, leftPeriod, estimated: !Number.isFinite(led.left_flow_period_ms) && !Number.isFinite(motion.top_flow_period_ms) }
}

const wrap = n => ((n % 1) + 1) % 1
const smooth = t => t * t * (3 - 2 * t)
export const BALL_PERIOD_MS = 12000

// Blend across the whole interval; no held colors or narrow transition bands.
// RGB interpolation avoids traversing unrelated hues around the HSV color wheel.
function interpolatePalette(colors, position) {
  const p = wrap(position) * 3, anchor = Math.floor(p)
  const fraction = p - anchor
  const t = smooth(fraction)
  const a = colors[anchor], b = colors[(anchor + 1) % 3]
  return a.map((value, channel) => value + (b[channel] - value) * t)
}

export function paletteColor(colors, position) {
  return interpolatePalette(colors, position).map(Math.round)
}

// A wider blend softens the three-color joins without introducing extra hues.
function softBallColor(colors, position) {
  const samples = [-.065, 0, .065].map(offset => interpolatePalette(colors, position + offset))
  return samples[1].map((value, channel) =>
    Number(((samples[0][channel] + 2 * value + samples[2][channel]) / 4).toFixed(2)))
}

export function previewPixel(model, row, index, elapsed) {
  if (row !== 0) return [...model.primary]
  return paletteColor(model.colors, elapsed / model.leftPeriod - index / 22)
}

// The soft balls intentionally use a slower, independent display period.
// Their palette and row assignment still follow the actual emotion commands.
export function ballPixel(model, displayRow, columnPosition, elapsed) {
  if (displayRow !== 2) return [...model.primary]
  return softBallColor(model.colors, elapsed / BALL_PERIOD_MS - columnPosition / 4)
}

export function ballGradient(model, displayRow, column, elapsed) {
  const stops = Array.from({length: 33}, (_, i) =>
    `rgba(${ballPixel(model, displayRow, column + i / 32, elapsed).join(',')}, 0.38) ${i * 3.125}%`)
  return `linear-gradient(90deg, ${stops.join(', ')})`
}
