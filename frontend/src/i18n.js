// UI language also selects the analysis model. Keep user input untouched.
const english = {
  '언어 설정': 'Language',
  '말랑콜리': 'mallangcholy',
  '오늘 당신의 감정을': 'How are you', '분석해볼까요?': 'feeling today?',
  '오늘의 마음을 자유롭게 적어주세요.': 'Share how you feel today.',
  '감정 입력': 'How you feel', '감정 분석하기': 'Explore my emotions',
  '감정을 분석하고 있어요...': 'Exploring your emotions...',
  '감정을 표현하는 문장을 입력해 주세요.': 'Please write a sentence about how you feel.',
  '분석 응답이 늦어지고 있어요. 잠시 후 다시 시도해주세요.': 'This is taking longer than expected. Please try again shortly.',
  '감정 분석 서버에 연결하지 못했어요. 인터넷 연결과 서버 실행 상태를 확인하고 다시 시도해주세요.': 'We could not reach the analysis service. Please check your connection and try again.',
  '분석 결과': 'Your emotions', '주요 감정': 'Main emotion',
  '감정 비율 도넛 차트': 'Emotion distribution chart',
  '나의 감정 말랑이': 'My emotion bubbles',
  '나의 감정 말랑이를 화면에서 미리 확인하세요. 말랑이를 눌러보세요.': 'Preview your emotion bubbles. Give them a gentle tap.',
  '감정별 색상이 적용된 말랑이 12개': 'Twelve bubbles colored by emotion',
  'LED 전송 결과와 효과 미리보기': 'LED status and light preview',
  '빛으로 보는 나의 감정': 'My emotions in light',
  '가장 크게 느껴지는 감정과 그 곁의 감정들을 빛의 흐름으로 만나보세요.': 'Watch your strongest emotion and the feelings alongside it flow through light.',
  '감정의 강도에 따라 빛의 흐름도 달라져요.': 'The light flows with the intensity of your emotions.',
  '격한 마음은 빠르게, 차분한 마음은 느리게 흐릅니다.': 'Intense feelings move faster; calmer feelings drift slowly.',
  '시간이 짧을수록 빠르게 움직여요.': 'A shorter cycle means a faster flow.',
  '화면은 빛의 움직임을 미리 보여주는 예시예요. 재생과 멈추기는 화면에만 적용됩니다.': 'This is an on-screen light preview. Play and pause affect only this preview.',
  '미리보기 재생': 'Play preview', '미리보기 멈추기': 'Pause preview',
  '위, 가운데, 아래 세 줄의 빛 효과 예시': 'Three rows of animated lights',
  '뚜렷한 감정이 없어 기본색으로 표현해요.': 'No clear emotion was detected. Showing the default color.',
  '한국어로 분석': 'Analyzed in Korean', '영어로 분석': 'Analyzed in English',
  '기쁨': 'Joy', '사랑/따뜻함': 'Love / Warmth', '사랑': 'Love', '놀람': 'Surprise',
  '슬픔': 'Sadness', '분노': 'Anger', '두려움/불안': 'Fear / Anxiety', '불안': 'Anxiety',
  '차분함': 'Calm', '뚜렷한 감정 없음': 'No clear emotion',
}
let language = 'ko'
try { if (localStorage.getItem('mallangcholy-language') === 'en') language = 'en' } catch {}
export const getLanguage = () => language
export function setLanguage(value) {
  language = value === 'en' ? 'en' : 'ko'
  try { localStorage.setItem('mallangcholy-language', language) } catch {}
}
export function translate(text, locale = language) {
  if (locale !== 'en') return text
  if (english[text]) return english[text]
  let match = text.match(/^색상 이동 주기 · ([\d.]+)초$/)
  if (match) return `Color cycle · ${match[1]} s`
  match = text.match(/^(가장 큰 감정|함께 느끼는) · (.+)$/)
  if (match) return `${match[1] === '가장 큰 감정' ? 'Strongest emotion' : 'Also feeling'} · ${english[match[2]] ?? match[2]}`
  match = text.match(/^(맨 위|가운데|맨 아래) 줄 감정색 말랑이 (\d+) 눌러보기$/)
  if (match) return `Tap ${ {'맨 위':'top','가운데':'middle','맨 아래':'bottom'}[match[1]] } row bubble ${match[2]}`
  match = text.match(/^(맨 위|가운데|맨 아래) 빛 효과$/)
  if (match) return `${ {'맨 위':'Top','가운데':'Middle','맨 아래':'Bottom'}[match[1]] } row lights`
  return text
}
// Remember source strings so switching languages also updates existing results.
const sources = new WeakMap()
function localizeValue(node, key, current, write) {
  let values = sources.get(node)
  if (!values) { values = {}; sources.set(node, values) }
  const prior = values[key]
  const source = prior && current === prior.output ? prior.source : current
  const output = translate(source.trim())
  values[key] = { source, output }
  write(output)
}
export function localize(root) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  while (walker.nextNode()) {
    const node = walker.currentNode
    if (!node.textContent.trim() || node.parentElement.closest('textarea, option, #resultDate')) continue
    localizeValue(node, 'text', node.textContent, value => { node.textContent = value })
  }
  for (const element of root.querySelectorAll('[aria-label], [placeholder]')) {
    for (const attr of ['aria-label', 'placeholder']) {
      if (element.hasAttribute(attr)) localizeValue(element, attr, element.getAttribute(attr), value => element.setAttribute(attr, value))
    }
  }
  document.documentElement.lang = language
  document.title = language === 'en' ? 'mallangcholy' : '말랑콜리 · mallangcholy'
  const date = root.querySelector('#resultDate')
  if (date?.dataset.timestamp) date.textContent = new Date(Number(date.dataset.timestamp)).toLocaleString(language === 'en' ? 'en-US' : 'ko-KR', { year: 'numeric', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
