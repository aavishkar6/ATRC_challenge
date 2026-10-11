const assert=require('node:assert/strict');
const fs=require('node:fs');
const engine=require('../demo/engine.js');
const data=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const fixtures=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
let assertions=0,maxError=0;
function check(condition,message){assert.ok(condition,message);assertions++;}
for(const fixture of fixtures){
  const m=data.markets[fixture.market],p=m.months[fixture.month],c={...p.baseline};
  c.frequency*=fixture.multiplier;
  const r=engine.run(m,p,c);
  r.prediction.forEach((y,i)=>{const error=Math.abs(y-fixture.prediction[i]);maxError=Math.max(error,maxError);check(error<=1e-5+1e-4*Math.abs(fixture.prediction[i]),'Python/JS parity');});
}
for(const m of Object.values(data.markets))for(const p of Object.values(m.months)){
  const base=engine.run(m,p,p.baseline);
  check(Math.abs(base.total-base.baseline)<1e-6,'Reset restores prediction');
  for(const key of ['frequency','gauge','load','nonlocal']){
    const limit=key==='frequency'?Math.max(10,p.baseline.frequency*2):key==='gauge'?Math.max(650,p.baseline.gauge*1.3):key==='load'?Math.max(1,p.baseline.load):1;
    let previous=null;
    for(let i=0;i<=20;i++){
      const c={...p.baseline,[key]:limit*i/20},r=engine.run(m,p,c);
      check(Number.isFinite(r.total)&&r.total>=0,'Finite scenario');
      if(previous!==null) check(key==='nonlocal'?r.total<=previous+1e-5:r.total>=previous-1e-5,'Correct slider direction');
      if(!m.linked)check(Math.abs(r.total-base.total)<1e-6,'Unsupported market is invariant');
      previous=r.total;
    }
  }
  assert.throws(()=>engine.run(m,p,{...p.baseline,load:NaN}),RangeError);assertions++;
  assert.throws(()=>engine.run(m,p,{...p.baseline,nonlocal:1.1}),RangeError);assertions++;
}
console.log(JSON.stringify({assertions,max_absolute_parity_error:maxError,passed:true}));
