/* Shared with Node verification. No network calls or dependencies. */
(function(root) {
  'use strict';
  function sum(a) { return a.reduce((s,x)=>s+x,0); }
  function interpolate(xs, ys, x) {
    if(x<xs[0] || x>xs[xs.length-1]) throw new RangeError('Outside exported response curve');
    let lo=0, hi=xs.length-1;
    while(hi-lo>1) { const mid=(lo+hi)>>1; if(xs[mid]<=x) lo=mid; else hi=mid; }
    return ys[lo]+(ys[hi]-ys[lo])*(x-xs[lo])/(xs[hi]-xs[lo]);
  }
  function effect(m,x) {
    if(m.kind==='linear') return m.elasticity*Math.log1p(x);
    if(m.kind==='gam') return interpolate(m.curve.log_x,m.curve.effect,Math.log1p(x));
    return 0;
  }
  function exposures(values, feature) {
    const w=feature==='p2p_7d'?Array(7).fill(1/7):Array.from({length:28},(_,i)=>.75**i/(1-.75**28)*.25);
    return values.map((_,i)=>w.reduce((s,v,j)=>s+(i>=j?values[i-j]*v:0),0));
  }
  function predict(m,p,x,i) {
    if(m.kind==='chain') return x*p.chain_ratio;
    return Math.max(0,(p.prediction[i]+1)*Math.exp(effect(m,x)-effect(m,p.exposure[i]))-1);
  }
  function run(m,p,controls) {
    const b=p.baseline;
    for(const k of ['frequency','gauge','load','nonlocal']) {
      if(!Number.isFinite(controls[k]) || controls[k]<0) throw new RangeError('Invalid '+k);
    }
    if(controls.nonlocal>1) throw new RangeError('Invalid transfer/transit share');
    const seats=controls.frequency/7*p.dates.length*controls.gauge;
    const pax=seats*controls.load*b.infant_multiplier;
    const p2p=pax*(1-controls.nonlocal);
    const baseP2P=sum(p.p2p);
    const multiplier=m.linked && baseP2P>0?p2p/baseP2P:1;
    const e=exposures(p.history.concat(p.p2p.map(x=>x*multiplier)),m.feature).slice(p.history.length);
    const prediction=e.map((x,i)=>predict(m,p,x,i));
    const outside=e.filter(x=>x<m.training_range[0] || x>m.training_range[1]).length;
    return {prediction, exposure:e, total:sum(prediction), baseline:sum(p.prediction),
      seats,pax,p2p:m.linked?p2p:0,multiplier,outside};
  }
  const api={sum, effect, exposures, predict, run};
  if(typeof module!=='undefined' && module.exports) module.exports=api;
  root.Scenario=api;
})(typeof globalThis!=='undefined'?globalThis:this);
