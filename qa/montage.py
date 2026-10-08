# usage: python qa/montage.py [--cols N] out.png in1.png in2.png ...   (contact sheet for review)
import sys
from PIL import Image
a=sys.argv[1:]; cols=0
if a[0]=='--cols': cols=int(a[1]); a=a[2:]
out=a[0]; ims=[Image.open(p).convert('RGB') for p in a[1:]]
cols=cols or len(ims); gap=6
rows=[ims[i:i+cols] for i in range(0,len(ims),cols)]
W=max(sum(i.width for i in r)+gap*(len(r)-1) for r in rows); H=sum(max(i.height for i in r) for r in rows)+gap*(len(rows)-1)
m=Image.new('RGB',(W,H),(255,0,255)); y=0
for r in rows:
    x=0
    for i in r: m.paste(i,(x,y)); x+=i.width+gap
    y+=max(i.height for i in r)+gap
m.save(out)
