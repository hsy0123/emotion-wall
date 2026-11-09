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

test('model intensity accelerates preview and server timing remains authoritative', () => {
  const low=ledViewModel({scores:{anger:.5,joy:.5},intensity:0})
  const high=ledViewModel({scores:{anger:.5,joy:.5},intensity:1})
  assert.ok(high.period<low.period)
  const server=ledViewModel({scores:{joy:1},intensity:0,motion:{flow_period_ms:3100,top_flow_period_ms:1705}})
  assert.equal(server.period,3100);assert.equal(server.leftPeriod,1705);assert.equal(server.estimated,false)
})

test('neutral is excluded from emotion ranking; missing ranks repeat real colors', () => {
  const m=ledViewModel({scores:{love:.5,neutral:.3,joy:.2}})
  assert.deepEqual(m.names,['love','joy','love'])
  assert.deepEqual(m.primary,[255,0,90])
  const fallback=ledViewModel({scores:{neutral:1}})
  assert.deepEqual(fallback.names,['neutral','neutral','neutral'])
})

test('balls hold the primary color on the first two rows and loop slowly on the last', async () => {
  const {ballPixel, ballGradient, BALL_PERIOD_MS}=await import('../src/led-model.js')
  const m=ledViewModel({scores:{joy:.5,love:.3,surprise:.2}})
  assert.equal(BALL_PERIOD_MS,12000)
  for (const time of [0,300,2000,6000]) for(let column=0;column<4;column++) {
    assert.deepEqual(ballPixel(m,0,column,time),m.primary)
    assert.deepEqual(ballPixel(m,1,column,time),m.primary)
    assert.equal(typeof ballGradient(m,2,column,time),'string')
  }
  assert.deepEqual(ballPixel(m,2,0,0),ballPixel(m,2,0,12000))
  assert.notDeepEqual(ballPixel(m,2,0,0),ballPixel(m,2,0,4000))
  for(let time=0;time<12000;time+=100) {
    const a=ballPixel(m,2,0,time), b=ballPixel(m,2,0,time+100)
    assert.ok(a.every((value,ch)=>Math.abs(value-b[ch])<36))
  }
})

test('gradient uses the selected RGB colors directly without HSV rainbow hues', async () => {
  const {paletteColor}=await import('../src/led-model.js')
  const colors=[[255,210,0],[255,0,90],[0,220,255]]
  assert.deepEqual(paletteColor(colors,0),colors[0])
  assert.deepEqual(paletteColor(colors,1/3),colors[1])
  assert.deepEqual(paletteColor(colors,2/3),colors[2])
  for(let i=0;i<300;i++) {
    const rgb=paletteColor(colors,i/300)
    assert.ok(!(rgb[0]<60 && rgb[1]>180 && rgb[2]<60),'no unrelated pure green')
    assert.ok(!(rgb[0]<60 && rgb[1]<60 && rgb[2]>180),'no unrelated pure blue')
  }
})

test('palette blends continuously instead of holding then snapping', async () => {
  const {paletteColor,ballGradient}=await import('../src/led-model.js')
  const colors=[[255,210,0],[255,0,90],[0,220,255]]
  assert.notDeepEqual(paletteColor(colors,.1),colors[0])
  for(let i=0;i<1000;i++) {
    const a=paletteColor(colors,i/1000),b=paletteColor(colors,(i+1)/1000)
    assert.ok(a.every((v,ch)=>Math.abs(v-b[ch])<=2))
  }
  const css=ballGradient(ledViewModel({scores:{joy:.5,love:.3,surprise:.2}}),2,0,1000)
  assert.equal((css.match(/rgba\(/g)||[]).length,17)
  const alphas = [...css.matchAll(/rgba\([^)]*,\s*([\d.]+)\)/g)].map(match => Number(match[1]))
  assert.equal(alphas.length, 17)
  assert.ok(alphas.every(alpha => alpha > 0 && alpha < 1))
})
