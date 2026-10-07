import {SoftWorld,makeMaterial,MATERIALS,buildBeam} from './softsolver.js';
const L=2,W=0.1,H=0.1;
for (const E of [1e8,1e9,1e10]) {
 const mat=makeMaterial({...MATERIALS.wood,youngs:E,yield:1e12,fracture:1e12,damping:0.5});
 const I=W*H**3/12, wl=mat.density*W*H*9.81, dEB=wl*L**4/(8*E*I);
 for (const [sub,it] of [[8,1],[8,4],[16,4],[64,1],[32,2],[8,16],[16,16]]) {
 const w=new SoftWorld({substeps:sub,iterations:it});
 const b=buildBeam(w,{a:[0,5,0],b:[L,5,0],width:W,height:H,mat,pin:'start'});
 const t0=performance.now(); let st=240;
 for(let i=0;i<st;i++) w.step(1/60);
 const tip=5-w.pos[b.tip.c*3+1], ek=w.energy().kinetic;
 console.log('E',E.toExponential(0),sub,it,'drop mm',(tip*1000).toFixed(2),'EB',(dEB*1000).toFixed(2),'ratio',(tip/dEB).toFixed(2),'KE',ek.toExponential(1),'ms',((performance.now()-t0)/st).toFixed(2));
 }
}
