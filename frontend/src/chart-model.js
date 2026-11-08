// Soft chart colors are independent from the physical LED palette.
export const EMOTIONS = [
  { key: 'joy', name: '기쁨', color: '#FFD23F' },
  { key: 'love', name: '사랑/따뜻함', color: '#FF7EB6' },
  { key: 'surprise', name: '놀람', color: '#2EC4B6' },
  { key: 'sadness', name: '슬픔', color: '#3A5CBE' },
  { key: 'anger', name: '분노', color: '#E63946' },
  { key: 'fear', name: '두려움/불안', color: '#5E3C99' },
  { key: 'neutral', name: '뚜렷한 감정 없음', color: '#FFE9C7' },
]

export function chartModel(data) {
  const scores = data.scores ?? data.emotions
  if (!scores) throw new Error('감정 분석 데이터가 없습니다.')
  const emotions = EMOTIONS.map(emotion => {
    const score = scores[emotion.key] ?? 0
    if (!Number.isFinite(score) || score < 0 || score > 1) throw new Error('유효하지 않은 감정 비율입니다.')
    return { ...emotion, value: score * 100 }
  })
  const total = emotions.reduce((sum, emotion) => sum + emotion.value, 0)
  if (total <= 0) throw new Error('감정 분석 결과가 비어 있습니다.')
  let position = 0
  const stops = emotions.map(emotion => {
    const start = position
    position += emotion.value / total * 100
    return `${emotion.color} ${start}% ${position}%`
  })
  const glow = [1, 3, 5].map(offset => Math.round(emotions.reduce((sum, emotion) =>
    sum + parseInt(emotion.color.slice(offset, offset + 2), 16) * emotion.value / total, 0)))
  const main = emotions.find(emotion => emotion.key === (data.dominant ?? data.main_emotion))
    ?? emotions.reduce((a, b) => a.value >= b.value ? a : b)
  return { emotions, main, glow, gradient: `conic-gradient(${stops.join(', ')})` }
}
