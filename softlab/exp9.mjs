import {SoftWorld,makeMaterial,MATERIALS,buildRope} from './softsolver.js';
const mat=makeMaterial({...MATERIALS.rope,damping:1});
for (const [sub,it,N] of [[8,1,30],[8,4,30],[16,1,30],[8,1,10]]) {
 const w=new SoftWorld({substeps:sub,iterations:it});
 const r=buildRope(w,{a:[0,5,0],b:[6,5,0],slack:1.3,segments:N,radius:0.02,mat,pin:'both',sag:0.5,mat});
 const t0=performance.now();
 const out=[];
 for(let i=0;i<60*10;i++){ w.step(1/60); if(i%120==119) out.push(((5-w.pos[r.ids[N/2]*3+1])).toFixed(3)); }
 console.log(sub,it,N,'mid sag',out.join(' '),'KE',w.energy().kinetic.toExponential(1),'ms',((performance.now()-t0)/600).toFixed(3));
}
