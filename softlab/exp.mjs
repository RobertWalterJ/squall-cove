import {SoftWorld,makeMaterial,MATERIALS,buildBeam} from './softsolver.js';
for (const dmp of [0,0.2]) for (const bend of [0.002,0.004,0.006,0.008]) for (const [sub,it] of [[4,1],[8,1],[4,2]]) {
 const mat=makeMaterial({...MATERIALS.wood,yield:1e12,fracture:1e12,damping:dmp,scatter:0});
 const w=new SoftWorld({substeps:sub,iterations:it});
 buildBeam(w,{a:[0,20,0],b:[1.2,20,0],width:0.1,height:0.1,mat});
 for (let i=0;i<w.n;i++){ const x=w.pos[i*3]; w.pos[i*3+1]+=bend*Math.sin(Math.PI*x/1.2); w.prev[i*3+1]=w.pos[i*3+1]; }
 const e0=w.energy(); let emax=e0.total; const c0=w.centreOfMass();
 for(let i=0;i<120;i++){ w.step(1/60); const e=w.energy(); if(e.total>emax) emax=e.total; }
 const c1=w.centreOfMass();
 console.log('damp',dmp,'bend',bend,'sub',sub,'it',it,'Eel0',e0.elastic.toFixed(0),'Emax-E0',(emax-e0.total).toExponential(1),'COMfall',(c0[1]-c1[1]).toFixed(2));
}
