import test from 'node:test'
import assert from 'node:assert/strict'
import { ledViewModel, previewPixel, LED_LAYOUT } from '../src/led-model.js'
const base = { dominant: 'joy', scores: { joy: .6, sadness: .3, anger: .1 } }
test('old/cloud API is explicitly a preview, never claims hardware success', () => {
  assert.equal(ledViewModel(base).state, 'unavailable')
  assert.equal(ledViewModel({...base,led:{enabled:false,sent:false}}).state, 'preview')
})
test('ACK and real timing/color response are reflected', () => {
  const m = ledViewModel({...base, led:{enabled:true,sent:true,rgbw:[255,210,0,0],top_emotions:['joy','sadness','anger'],top_colors:[[255,210,0,0],[0,25,255,0],[255,0,0,0]],flow_period_ms:4000,left_flow_period_ms:2200}})
  assert.equal(m.state,'sent');assert.equal(m.leftPeriod,2200);assert.equal(m.period,4000)
  assert.equal(m.estimated,false);assert.deepEqual(m.names,['joy','sadness','anger'])
})
test('hardware failure preserves analysis and gives actionable guidance', () => {
  assert.match(ledViewModel({...base,led:{enabled:true,sent:false,error:'Resource busy'}}).detail,/시리얼 모니터/)
  assert.match(ledViewModel({...base,led:{enabled:true,sent:false,error:'No such file or directory'}}).detail,/포트 이름/)
  assert.match(ledViewModel({...base,led:{enabled:true,sent:false,error:'ERR,FORMAT'}}).detail,/업로드/)
})
test('preview moves, closes its loop and stays finite for all 64 LEDs', () => {
  const m = ledViewModel(base)
  let changed = false
  for (let row=0;row<3;row++) for(let i=0;i<(row===0?22:21);i++) {
    const rgb = previewPixel(m,row,i,0)
    assert.ok(rgb.every(v=>Number.isInteger(v)&&v>=0&&v<=255))
    const full = previewPixel(m,row,i,row===0?m.leftPeriod:m.period)
    assert.ok(rgb.every((v,ch)=>Math.abs(v-full[ch])<=1))
    if (rgb.join() !== previewPixel(m,row,i,500).join()) changed=true
  }
  assert.ok(changed)
})
test('invalid server palette falls back to valid local colors', () => {
  const m=ledViewModel({...base,led:{top_emotions:['<bad>'],top_colors:[[NaN,1,2]],left_flow_period_ms:-1}})
  assert.deepEqual(m.names,['joy','sadness','anger']);assert.ok(m.leftPeriod>=600)
})

test('cloud preview estimates emotion-driven speed without USB', () => {
  assert.ok(ledViewModel({scores:{anger:1}}).leftPeriod < ledViewModel({scores:{joy:1}}).leftPeriod)
  assert.equal(ledViewModel({scores:{sadness:1}}).state,'unavailable')
})

test('physical top/middle/bottom order preserves the 22-LED ranked row', () => {
  assert.deepEqual(LED_LAYOUT.map(x=>[x.label,x.row,x.count]), [['맨 위',2,21],['가운데',1,21],['맨 아래',0,22]])
  assert.equal(LED_LAYOUT.reduce((n,x)=>n+x.count,0),64)
  const m=ledViewModel({scores:{joy:.6,sadness:.4},led:{flow_period_ms:4000,left_flow_period_ms:2000}})
  assert.equal(LED_LAYOUT[2].row,0)
  assert.notDeepEqual(previewPixel(m,LED_LAYOUT[2].row,0,0),previewPixel(m,LED_LAYOUT[2].row,0,500))
})
