import sys, os, glob
from PIL import Image
d = sys.argv[1]; kinds = ['desert','urban','sniper','medic','engineer','pilot','officer','militia','riot','special','heavy','port_worker']
for view in ('front', 'back'):
    W, H = 240, 400; sheet = Image.new('RGB', (W * 6, H * 6), (210, 214, 218))
    for i, k in enumerate(kinds):
        for n in range(3):
            im = Image.open(os.path.join(d, f'trooper2_{k}_{n}_{view}.png')).convert('RGB').resize((W, H))
            col = (i % 2) * 3 + n; row = i // 2
            sheet.paste(im, (col * W, row * H))
    sheet.save(os.path.join(d, f'contact_{view}.png'))
# heads
W = 180; sheet = Image.new('RGB', (W * 9, W * 4), (210, 214, 218))
for i, k in enumerate(kinds):
    for n in range(3):
        im = Image.open(os.path.join(d, f'trooper2_{k}_{n}_head.png')).convert('RGB').resize((W, W))
        c = (i % 3) * 3 + n; r = i // 3
        sheet.paste(im, (c * W, r * W))
sheet.save(os.path.join(d, 'contact_heads.png'))
