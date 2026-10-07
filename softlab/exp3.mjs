import {SoftWorld,makeMaterial,MATERIALS,buildBeam} from './softsolver.js';
const mat=makeMaterial({...MATERIALS.wood,yield:1e12,fracture:1e12,damping:0.5});
const w=new SoftWorld({substeps:8,iterations:1});
const b=buildBeam(w,{a:[0,5,0],b:[2,5,0],width:0.1,height:0.1,mat,pin:'start'});
console.log('E0',w.energy().elastic, 'n',w.n,'masses',w.mass[0],w.mass[10],w.mass[w.n-1]);
for(let i=0;i<30;i++){ w.step(1/60); const e=w.energy(); console.log(i,e.elastic.toExponential(3),e.kinetic.toExponential(3),((5-w.pos[b.tip.c*3+1])*1000).toFixed(2)); }
// find the max-strain constraint
let worst=0,wi=-1; for(let c=0;c<w.nd;c++){ const a=w.da[c]*3,b2=w.db[c]*3; const l=Math.hypot(w.pos[a]-w.pos[b2],w.pos[a+1]-w.pos[b2+1],w.pos[a+2]-w.pos[b2+2]); const s=Math.abs(l-w.dRest[c])/w.dRest[c]; if(s>worst){worst=s;wi=c;} }
console.log('worst strain',worst,'c',wi,'tag',w.dTag[wi],'k',w.dK[wi],'a,b',w.da[wi],w.db[wi]);
