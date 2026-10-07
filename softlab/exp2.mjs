import {SoftWorld,makeMaterial,MATERIALS,buildBeam} from './softsolver.js';
const mat=makeMaterial({...MATERIALS.wood,yield:1e12,fracture:1e12,damping:0.5});
for (const it of [1,2]) {
 const w=new SoftWorld({substeps:8,iterations:it});
 const b=buildBeam(w,{a:[0,5,0],b:[2,5,0],width:0.1,height:0.1,mat,pin:'start'});
 const out=[];
 for(let i=0;i<120;i++){ w.step(1/60); if(i%15==0) out.push(((5-w.pos[b.tip.c*3+1])*1000).toFixed(2)); }
 console.log(it,out.join(' '), w.energy());
}
