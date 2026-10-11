'use strict';
const $=id=>document.getElementById(id), fmt=(x,d=0)=>x.toLocaleString('en-GB',{maximumFractionDigits:d}), pct=x=>(100*x).toFixed(1)+'%';
const keys=['frequency','gauge','load','nonlocal'];
let activeMarket, activePeriod;
for(const name of Object.keys(DATA.markets)) $('market').add(new Option(name.toLowerCase().replace(/\b\w/g,c=>c.toUpperCase()),name));
for(const month of DATA.months) $('month').add(new Option(new Date(month+'-15T12:00:00').toLocaleDateString('en-GB',{month:'long',year:'numeric'}),month));
$('market').value='UNITED KINGDOM'; $('month').value='2025-07';
function chart(id,series,options={}) {
  const svg=$(id), W=440,H=225,L=49,R=15,T=14,B=32;
  svg.setAttribute('viewBox',`0 0 ${W} ${H}`);
  const points=series.flatMap(s=>s.points).filter(p=>p[1]!==null && Number.isFinite(p[1]));
  const xmax=Math.max(...points.map(p=>p[0]),1), ymax=Math.max(...points.map(p=>p[1]),1)*1.12;
  const sx=x=>L+x/xmax*(W-L-R), sy=y=>H-B-y/ymax*(H-T-B);
  let out='';
  for(let i=0;i<4;i++){const y=ymax*i/3;out+=`<line x1="${L}" y1="${sy(y)}" x2="${W-R}" y2="${sy(y)}" stroke="#e4e9e1"/><text x="${L-8}" y="${sy(y)+3}" text-anchor="end">${y>=1000?fmt(y/1000,1)+'k':fmt(y)}</text>`;}
  for(let i=0;i<4;i++){const x=xmax*i/3;out+=`<text x="${sx(x)}" y="${H-10}" text-anchor="middle">${options.days?Math.round(x+1):fmt(x)}</text>`;}
  for(const s of series){let path='',open=false;for(const [x,y] of s.points){if(y===null || !Number.isFinite(y)){open=false;continue;}path+=(open?'L':'M')+sx(x).toFixed(2)+','+sy(y).toFixed(2);open=true;}out+=`<path d="${path}" fill="none" stroke="${s.color}" stroke-width="${s.width||2}" ${s.dash?'stroke-dasharray="5 4"':''}/>`;}
  if(options.marker) out+=`<circle cx="${sx(options.marker[0])}" cy="${sy(options.marker[1])}" r="5" fill="#17322f" stroke="#dcf78c" stroke-width="3"/>`;
  svg.innerHTML=out;
}
function update(){
  const m=activeMarket,p=activePeriod,c=Object.fromEntries(keys.map(k=>[k,+$(k).value]));
  keys.forEach(k=>$(k+'-value').textContent=k==='load'||k==='nonlocal'?pct(c[k]):fmt(c[k],k==='frequency'?1:0));
  const r=Scenario.run(m,p,c), diff=r.total-r.baseline;
  $('total').textContent=fmt(r.total);$('base').textContent=fmt(r.baseline);
  $('delta').textContent=`${diff>=0?'+':''}${fmt(diff)} guest-days · ${r.baseline?(diff>=0?'+':'')+pct(diff/r.baseline):'—'} vs baseline`;
  $('elasticity').textContent=m.elasticity!==null?fmt(m.elasticity,2)+'×':(m.linked?'Curve':'—');
  $('sensitivity-note').textContent=m.elasticity!==null?'Elasticity of Guests + 1 to exposure + 1':(m.linked?'Inspect the response below':'Seasonal fallback · no aviation link');
  for(const k of ['seats','pax','p2p']) $(k).textContent=fmt(r[k]);
  const warns=[];
  if(!m.linked) warns.push('No same-name origin in flight data. Aviation controls are disabled; this is a seasonal forecast.');
  if(m.linked&&r.outside) warns.push(`${r.outside}/${p.dates.length} scenario days are outside the market’s training exposure range. Treat this as extrapolation.`);
  if(c.load>1) warns.push('Load factor exceeds 100%: a supplied-data exception, not a feasible seat occupancy.');
  if(p.baseline.infant_fallback) warns.push('Infant-excluded counts are incomplete this month; load factor uses total passengers.');
  $('warning').textContent=warns.join(' ')||'Within the observed training exposure range. The response is an association under an assumed origin-to-nationality bridge.';
  $('warning').className='notice'+(warns.length?' warn':'');
  chart('daily',[{points:p.prediction.map((v,i)=>[i,v]),color:'#94a7a0',dash:true},{points:p.actual.map((v,i)=>[i,v]),color:'#c75c32',width:1.5},{points:r.prediction.map((v,i)=>[i,v]),color:'#087e70',width:2.7}],{days:true});
  const i=Math.floor(p.dates.length/2), xmax=Math.max(m.training_range[1],...r.exposure,1)*1.1;
  const curve=Array.from({length:100},(_,j)=>{const x=xmax*j/99;return [x,Scenario.predict(m,p,x,i)];});
  chart('response',[{points:curve,color:'#087e70',width:2.7}],{marker:[r.exposure[i],r.prediction[i]]});
  $('formula').textContent=m.kind==='linear'?`Guests + 1 = calendar-and-trend baseline × (1 + passenger exposure)^${m.elasticity.toFixed(3)}`:m.kind==='chain'?'Guests = monthly empirical coefficient × passenger exposure':m.kind==='gam'?'Guests + 1 = calendar-and-trend baseline × exp(monotonic exposure curve)':'Guests + 1 = calendar-and-trend baseline';
  $('explanation').textContent=m.linked?`This flight plan changes monthly P2P passengers by ${pct(r.multiplier-1)}. The model uses ${m.feature==='p2p_7d'?'a seven-day average':'a 28-day geometric exposure kernel with assumed mean stay 4 days'}, so the effect builds during the month. Earlier days retain their observed passenger history. Monthly calendar effects, weekday effects and trend are held fixed. The formula includes a training-residual smearing correction; forecasts are floored at zero.`:'This nationality has no direct flight-origin match. The baseline uses month, weekday and trend, without an inferred aviation response.';
}
function reset(){
  activeMarket=DATA.markets[$('market').value];activePeriod=activeMarket.months[$('month').value];
  const b=activePeriod.baseline;
  $('frequency').max=Math.max(10,b.frequency*2);$('frequency-max').textContent=fmt(+$('frequency').max,1);
  $('gauge').min=Math.min(50,b.gauge);$('gauge').max=Math.max(650,b.gauge*1.3);$('gauge-max').textContent=fmt(+$('gauge').max)+' seats';
  $('load').max=Math.max(1,b.load);$('load-max').textContent=pct(+$('load').max);
  keys.forEach(k=>{$(k).value=b[k];$(k).disabled=!activeMarket.linked;});
  ['grow','cut','close'].forEach(k=>$(k).disabled=!activeMarket.linked);
  $('period-note').textContent={selection:'Model-selection period · observed Guests available',calibration:'Error-calibration period · observed Guests available',audit:'Final audit period · observed Guests available',unlabeled:'Supplied future period · no observed Guests labels'}[activePeriod.split];
  update();
}
keys.forEach(k=>$(k).addEventListener('input',update));
['market','month'].forEach(k=>$(k).addEventListener('change',reset));$('reset').onclick=reset;
for(const [id,factor] of [['grow',1.2],['cut',.8],['close',0]]) $(id).onclick=()=>{$('frequency').value=activePeriod.baseline.frequency*factor;update();};
$('scores').innerHTML=DATA.scores.map(s=>`<tr class="${s.model===DATA.summary.selected?'selected':''}"><td>${s.model}${s.model===DATA.summary.selected?' <span class="pill">SELECTED</span>':''}</td><td>${pct(s.wmape)}</td><td>${pct(s.aggregate_wmape)}</td></tr>`).join('');
$('audit-market').textContent=pct(DATA.summary.audit.wmape);$('audit-all').textContent=pct(DATA.summary.audit.aggregate_wmape);
$('band-note').textContent=`May’s empirical 10th–90th percentile daily error band covered ${pct(DATA.summary.audit.daily_band_coverage)} of June–July observations. It is not shown as a calibrated scenario confidence interval.`;
reset();
