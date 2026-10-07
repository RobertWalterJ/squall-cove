import {SoftWorld,makeMaterial,MATERIALS,buildBeam} from './softsolver.js';
const L=1.2,h=0.1,W=0.1; const I=W*h**3/12,S=I/(h/2);
const brittle=makeMaterial({...MATERIALS.wood,yield:1e13,fracture:6e7,damping:1,scatter:0});
const w=new SoftWorld({substepHz:480});
const b=buildBeam(w,{a:[0,5,0],b:[L,5,0],width:W,height:h,mat:brittle,pin:'start'});
const ev=[]; w.onBreak=(e)=>ev.push([w.time.toFixed(2),w.da[e.index],w.db[e.index],w.dTag[e.index]]);
const Pf=(6e7*S-600*0.01*9.81*L*L/2)/L;
let P=0.6*Pf; let broken=false;
const tip=()=>b.tip.all; 
for(let i=0;i<60*400 && !ev.length;i++){ if(i%180==0){P+=0.02*Pf;} for(const q of tip()) w.setForce(q,0,-P/5,0); w.step(1/60);}
console.log('first break at P',P,'t',w.time);
for(let sec=0;sec<10;sec++){ for(let i=0;i<60;i++) w.step(1/60); console.log('t+',sec+1,'broken',w.nBroken,'pieces',w.componentSizes().join(','),'tip y',w.pos[b.tip.c*3+1].toFixed(3)); }
// list remaining bars with high strain near root
let rem=[]; for(let c=0;c<w.nd;c++){ if(!w.dAct[c]) continue; const a=w.da[c]*3,bb=w.db[c]*3; if(w.pos[a]<0.5&&w.pos[bb]<0.5){ const l=Math.hypot(w.pos[a]-w.pos[bb],w.pos[a+1]-w.pos[bb+1],w.pos[a+2]-w.pos[bb+2]); rem.push([c,w.dTag[c],((l-w.dRest[c])/w.dRest[c]).toFixed(4)]);}}
console.log(rem.filter(r=>Math.abs(+r[2])>0.003).map(r=>r.join(':')).join(' '));
console.log(ev.slice(0,12).map(e=>e.join('/')).join(' '));
