import {SoftWorld,makeMaterial,MATERIALS,buildBeam} from './softsolver.js';
const mat=makeMaterial({...MATERIALS.wood,yield:1e12,fracture:1e12,damping:0.0});
for (const segs of [1,2,4,8]){
const w=new SoftWorld({substeps:8,iterations:1});
const b=buildBeam(w,{a:[0,5,0],b:[0.1*segs,5,0],width:0.1,height:0.1,mat,pin:'start',segments:segs});
let out=[];
for(let i=0;i<120;i++){ w.step(1/60); if(i%30==29) out.push(w.energy().elastic.toExponential(2)+'/'+((5-w.pos[b.tip.c*3+1])*1000).toFixed(3)); }
console.log(segs,w.nd,out.join(' '));
}
