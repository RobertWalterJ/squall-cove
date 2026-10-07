import {SoftWorld,makeMaterial,MATERIALS,buildBeam} from './softsolver.js';
const mat=makeMaterial({...MATERIALS.wood,yield:1e12,fracture:1e12,damping:0.5});
const L=2,W=0.1,H=0.1;
const I=W*H**3/12, wl=mat.density*W*H*9.81, dEB=wl*L**4/(8*mat.youngs*I);
for (const [sub,it] of [[8,1],[8,2],[16,1],[8,4]]) {
 const w=new SoftWorld({substeps:sub,iterations:it});
 const b=buildBeam(w,{a:[0,5,0],b:[L,5,0],width:W,height:H,mat,pin:'start'});
 const t0=performance.now();
 for(let i=0;i<60*8;i++) w.step(1/60);
 const tip=w.pos[b.tip.c*3+1]; 
 console.log(sub,it,'tip drop',(5-tip)*1000,'mm  EB',dEB*1000,'mm ratio',(5-tip)/dEB, 'ms/step',(performance.now()-t0)/480, 'n',w.n,'nd',w.nd);
}
