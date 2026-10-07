import {SoftWorld,makeMaterial,MATERIALS,buildBeam} from './softsolver.js';
for (const E of [1e6,1e8,1e10]) for (const [sub,it] of [[8,1],[1,1],[1,8],[8,8],[8,30]]){
const mat=makeMaterial({...MATERIALS.wood,youngs:E,yield:1e12,fracture:1e12,damping:0.0});
const w=new SoftWorld({substeps:sub,iterations:it});
const b=buildBeam(w,{a:[0,5,0],b:[0.1,5,0],width:0.1,height:0.1,mat,pin:'start',segments:1});
let out=[];
for(let i=0;i<120;i++){ w.step(1/60); if(i%40==39) out.push(w.energy().elastic.toExponential(1)); }
console.log('E',E,'sub',sub,'it',it,out.join(' '));
}
