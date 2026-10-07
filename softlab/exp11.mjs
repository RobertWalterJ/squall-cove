import {SoftWorld,makeMaterial} from './softsolver.js';
for (const E of [1e5,1e6,1e7,1e8]) for (const [sub,it] of [[8,1],[8,8],[1,1],[1,50]]) {
const mat=makeMaterial({density:600,youngs:E,yield:1e12,fracture:1e12,damping:0});
const w=new SoftWorld({substeps:sub,iterations:it,gravity:[0,0,0]});
const c=[];for(let q=0;q<8;q++) c.push(w.addParticle((q&1)*0.1,5+((q>>1)&1)*0.1,((q>>2)&1)*0.1,0.06));
for(let q=0;q<8;q++)for(let r=q+1;r<8;r++){const d=q^r; if(d===1||d===2||d===4||d===3||d===5||d===6) w.addDistance(c[q],c[r],mat,0.0025);}
w.pos[0]-=0.002; w.pos[7*3+1]+=0.002;
const e0=w.energy().elastic; const out=[];
for(let i=0;i<300;i++){ w.step(1/60); if(i%100==99) out.push(w.energy().total.toExponential(1)); }
console.log('E',E,'sub',sub,'it',it,'e0',e0.toExponential(1),out.join(' '));
}
