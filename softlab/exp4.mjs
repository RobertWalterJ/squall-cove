import {SoftWorld,makeMaterial,MATERIALS,buildBeam} from './softsolver.js';
const mat=makeMaterial({...MATERIALS.wood,yield:1e12,fracture:1e12,damping:0.0});
// hanging mass on a bar
let w=new SoftWorld({substeps:8});
const a=w.addParticle(0,5,0,0), b=w.addParticle(0,4,0,1);
w.pin(a); const c=w.addDistance(a,b,mat,1e-4);
for(let i=0;i<60;i++) w.step(1/60);
console.log('bar stretch mm',(1-(5-w.pos[4]))*-1000, 'expected', 9.81*1/(1e10*1e-4)*1*1000);
// 2 triangles 
w=new SoftWorld({substeps:8});
const ids=[];for(let i=0;i<4;i++) ids.push(w.addParticle(i,5,0,i?0.1:0));
w.pin(ids[0]);
for(let i=0;i<3;i++) w.addDistance(ids[i],ids[i+1],mat,1e-3);
for(let i=0;i<120;i++){ w.step(1/60); if(i%20==0) console.log(i, w.energy().total.toExponential(3), w.pos[ids[3]*3+1].toFixed(4));}
