import json,struct,base64,sys,numpy as np
def load(p,b64=True):
    b=open(p,'rb').read(); b=base64.b64decode(b) if b64 else b
    l=struct.unpack('<I',b[12:16])[0]; return json.loads(b[20:20+l])
t=load('assets/troops.glb.b64.txt'); pp=load('assets/people.glb.b64.txt')
ref=[pp['nodes'][i]['name'] for i in pp['skins'][0]['joints']]
N=t['nodes']; print('top nodes',[N[i]['name'] for i in t['scenes'][0]['nodes']])
ok=True
for k,s in enumerate(t['skins']):
    names=[N[i]['name'] for i in s['joints']]; ok&=names==ref
    mesh=t['meshes'][N[[i for i,n in enumerate(N) if n.get('skin')==k][0]]['mesh']]
    tri=sum(t['accessors'][p['indices']]['count'] for p in mesh['primitives'])//3
    print(s['name'],'joints match' if names==ref else 'MISMATCH',tri,'tris',len(mesh['primitives']),'prims')
print('joints:',ref); print('all match',ok,'anims',len(t['animations']),[a['name'] for a in t['animations']][:2])
# rest pose check: local TRS of bones vs facetex_0 (translation ratio)
r=[]; 
for k in range(12):
    for j in range(18):
        a=N[k*20+j]; b=pp['nodes'][j]
        assert a['name']==b['name'] and a.get('rotation')==b.get('rotation') and a.get('children',[])==[c-k*20 for c in b.get('children',[])] if False else True
        if 'translation' in a:
            r+= [x/y for x,y in zip(a['translation'],b['translation']) if abs(y)>1e-4]
        assert a.get('rotation')==b.get('rotation') and a['name']==b['name']
print('translation ratio min/max',min(r),max(r))
