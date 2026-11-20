import test from 'node:test'
import assert from 'node:assert/strict'
import { translate, setLanguage, getLanguage } from '../src/i18n.js'

test('site language selects Korean or English without automatic detection', () => {
  setLanguage('en')
  assert.equal(getLanguage(), 'en')
  assert.equal(translate('말랑콜리'), 'mallangcholy')
  setLanguage('ko')
  assert.equal(translate('말랑콜리'), '말랑콜리')
  setLanguage('auto')
  assert.equal(getLanguage(), 'ko')
})
test('dynamic emotion rankings, timing and accessible bubble labels are localized', () => {
  assert.equal(translate('함께 느끼는 · 불안', 'en'), 'Also feeling · Anxiety')
  assert.equal(translate('색상 이동 주기 · 3.72초', 'en'), 'Color cycle · 3.72 s')
  assert.equal(translate('맨 아래 줄 감정색 말랑이 4 눌러보기', 'en'), 'Tap bottom row bubble 4')
  assert.equal(translate('미리보기 재생', 'en'), 'Play preview')
})
