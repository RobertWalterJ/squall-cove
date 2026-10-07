import {SoftWorld,makeMaterial,MATERIALS} from './softsolver.js';
const mat=makeMaterial({density:600,youngs:1e8,yield:1e12,fracture:1e12,damping:0});
for (const diag of [0,1,2]) {
const w=new SoftWorld({substeps:8,iterations:1,gravity:[0,0,0]});
const c=[];for(let q=0;q<8;q++) c.push(w.addParticle((q&1)*0.1,5+((q>>1)&1)*0.1,((q>>2)&1)*0.1,0.06));
for(let q=0;q<8;q++)for(let r=q+1;r<8;r++){const d=q^r; if(d===1||d===2||d===4|| (diag>=1&&(d===3||d===5||d===6)) || (diag>=2&&d===7)) w.addDistance(c[q],c[r],mat,0.0025*0.1/0.1*1);}
// perturb
w.pos[0]-=0.002; w.pos[7*3+1]+=0.002;
const out=[];
for(let i=0;i<300;i++){ w.step(1/60); if(i%50==49) out.push(w.energy().total.toExponential(2)); }
console.log('diag',diag,'nd',w.nd,out.join(' '));
}
