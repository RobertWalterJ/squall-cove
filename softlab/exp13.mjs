import {SoftWorld,makeMaterial,MATERIALS,buildBeam} from './softsolver.js';
const W=0.1,H=0.1;
for (const [L,E] of [[0.8,1e10],[0.8,1e9],[1.6,1e9],[1.6,1e10]]) {
 const mat=makeMaterial({...MATERIALS.wood,youngs:E,yield:1e12,fracture:1e12,damping:1});
 const I=W*H**3/12, wl=mat.density*W*H*9.81, dEB=wl*L**4/(8*E*I);
 for (const [sub,it] of [[8,2],[8,4],[8,8],[16,4],[4,16],[32,2]]) {
 const w=new SoftWorld({substeps:sub,iterations:it});
 const b=buildBeam(w,{a:[0,5,0],b:[L,5,0],width:W,height:H,mat,pin:'start'});
 const t0=performance.now(); let st=300;
 const tr=[];
 for(let i=0;i<st;i++){ w.step(1/60); if(i%100==99) tr.push(((5-w.pos[b.tip.c*3+1])/dEB).toFixed(2)); }
 console.log('L',L,'E',E.toExponential(0),sub,it,'ratio traj',tr.join(' '),'EB mm',(dEB*1000).toFixed(2),'ms',((performance.now()-t0)/st).toFixed(2));
 }
}
