import {SoftWorld,makeMaterial,MATERIALS,buildBeam} from './softsolver.js';
const mat=makeMaterial({...MATERIALS.wood,yield:1e12,fracture:1e12,damping:0.0});
const w=new SoftWorld({substeps:8,iterations:1});
const b=buildBeam(w,{a:[0,5,0],b:[0.1,5,0],width:0.1,height:0.1,mat,pin:'start',segments:1});
for(let s=0;s<6;s++){ w.step(1/60);
 let list=[]; for(let c=0;c<w.nd;c++){ const a=w.da[c]*3,b2=w.db[c]*3; const l=Math.hypot(w.pos[a]-w.pos[b2],w.pos[a+1]-w.pos[b2+1],w.pos[a+2]-w.pos[b2+2]); list.push([c,w.dTag[c],((l-w.dRest[c])/w.dRest[c]).toExponential(1), w.dK[c].toExponential(1)]); }
 if(s==5) console.log(list.filter(x=>Math.abs(+x[2])>1e-3).map(x=>x.join(':')).join('\n'));
 console.log(s, w.energy().elastic);
}
console.log(Array.from(w.invM.slice(0,10)), Array.from(w.pinned.slice(0,10)));
