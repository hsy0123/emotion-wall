import test from 'node:test'
import assert from 'node:assert/strict'
import { chartModel } from '../src/chart-model.js'
import { analyzeText } from '../src/api-client.js'

test('chart preserves seven emotion labels, neutral meaning and weighted glow', () => {
  const m=chartModel({scores:{joy:.6,love:.4},dominant:'joy'})
  assert.equal(m.emotions.length,7)
  assert.equal(m.main.name,'기쁨')
  assert.match(m.gradient,/conic-gradient/)
  assert.deepEqual(m.glow,[255,176,111])
  assert.equal(m.emotions.find(e=>e.key==='neutral').name,'뚜렷한 감정 없음')
})
test('legacy response aliases and invalid scores are handled', () => {
  assert.equal(chartModel({emotions:{sadness:1},main_emotion:'sadness'}).main.key,'sadness')
  for(const scores of [{},{joy:NaN},{joy:-1},{joy:2}]) assert.throws(()=>chartModel({scores}))
})
test('API client keeps request contract, HTTP errors and abort timeout', async () => {
  let observed
  const data=await analyzeText('hello',{fetchImpl:async (url,init)=>{
    observed={url,init};return {ok:true,json:async()=>({scores:{joy:1}})}
  }})
  assert.ok(observed.url.endsWith('/analyze'))
  assert.equal(observed.init.method,'POST')
  assert.deepEqual(JSON.parse(observed.init.body),{text:'hello'})
  assert.equal(data.scores.joy,1)
  await assert.rejects(analyzeText('test',{fetchImpl:async()=>({ok:false,status:500})}),/500/)
  await assert.rejects(analyzeText('test',{timeoutMs:5,fetchImpl:(_,init)=>new Promise((resolve,reject)=>{
    init.signal.addEventListener('abort',()=>reject(new DOMException('timeout','AbortError')))
  })}),{name:'AbortError'})
})
